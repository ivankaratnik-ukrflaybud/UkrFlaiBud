from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.audit import AuditAction, AuditLog
from app.models.base import ConflictError, EntityNotFoundError, ValidationError
from app.modules.bom.application.documents import parse_import_xlsx
from app.modules.bom.domain.entities import (
    BomLineSourceType,
    BomVersionStatus,
    SpecificationStatus,
)
from app.modules.bom.infrastructure.models import (
    BomAttachmentModel,
    BomLineModel,
    BomSpecificationModel,
    BomVersionModel,
)
from app.modules.bom.infrastructure.repositories import (
    BomAttachmentRepository,
    BomLineRepository,
    BomSpecificationRepository,
    BomVersionRepository,
)
from app.modules.inventory.infrastructure.models import ItemModel, UnitOfMeasureModel
from app.modules.organizations.infrastructure.models import EmployeeModel, OrganizationModel
from app.repositories.sqlalchemy_audit import SQLAlchemyAuditLogRepository
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork
from app.schemas.pagination import PageRequest, SortDirection


class BomService:
    def __init__(self, unit_of_work: SQLAlchemyUnitOfWork) -> None:
        self.unit_of_work = unit_of_work

    @property
    def session(self) -> AsyncSession:
        if self.unit_of_work.session is None:
            raise RuntimeError("Unit of Work session is not active.")
        return self.unit_of_work.session

    async def create_specification(
        self, data: dict[str, Any], *, actor_id: UUID
    ) -> BomSpecificationModel:
        await self._ensure_organization(data["organization_id"])
        await self._ensure_employee(data["organization_id"], data.get("author_employee_id"))
        if data.get("product_item_id"):
            await self._ensure_item(data["organization_id"], data["product_item_id"])
        repository = BomSpecificationRepository(self.session)
        if await repository.exists_by_code(data["organization_id"], data["code"]):
            raise ConflictError(
                "Specification code must be unique within organization.", {"field": "code"}
            )
        specification = await repository.create(
            BomSpecificationModel(**data, created_by_user_id=actor_id)
        )
        await BomVersionRepository(self.session).create(
            BomVersionModel(
                bom_id=specification.id,
                version_number=1,
                status=BomVersionStatus.DRAFT.value,
                created_by_user_id=actor_id,
                effective_from=specification.effective_from,
                effective_to=specification.effective_to,
            )
        )
        await self._audit(
            action=AuditAction.CREATE.value,
            entity_type="bom_specification",
            entity_id=specification.id,
            actor_id=actor_id,
            after={"code": specification.code, "name": specification.name},
        )
        await self._commit_and_refresh(specification)
        return specification

    async def list_specifications(
        self,
        *,
        filters: dict[str, object],
        page: PageRequest,
        sort_by: str,
        sort_direction: SortDirection,
    ) -> tuple[list[BomSpecificationModel], int]:
        return await BomSpecificationRepository(self.session).list(
            filters=filters,
            sort_by=sort_by,
            sort_direction=sort_direction,
            limit=page.page_size,
            offset=page.offset,
        )

    async def get_specification(self, specification_id: UUID) -> BomSpecificationModel:
        specification = await BomSpecificationRepository(self.session).get(specification_id)
        if specification is None:
            raise EntityNotFoundError("Specification not found.", {"id": str(specification_id)})
        return specification

    async def update_specification(
        self,
        specification_id: UUID,
        data: dict[str, Any],
        *,
        expected_version: int | None,
        actor_id: UUID,
    ) -> BomSpecificationModel:
        specification = await self.get_specification(specification_id)
        self._ensure_version(specification, expected_version)
        if specification.status == SpecificationStatus.APPROVED.value:
            raise ValidationError("Approved specifications cannot be edited.")
        if specification.status == SpecificationStatus.ARCHIVED.value:
            raise ValidationError("Archived specifications cannot be edited.")
        organization_id = data.get("organization_id", specification.organization_id)
        if data.get("product_item_id") is not None:
            await self._ensure_item(organization_id, data["product_item_id"])
        await self._ensure_employee(organization_id, data.get("author_employee_id"))
        repository = BomSpecificationRepository(self.session)
        code = data.get("code", specification.code)
        if await repository.exists_by_code(organization_id, code, exclude_id=specification.id):
            raise ConflictError(
                "Specification code must be unique within organization.", {"field": "code"}
            )
        before = {
            "code": specification.code,
            "name": specification.name,
            "status": specification.status,
        }
        self._apply_updates(specification, data)
        await repository.update(specification)
        await self._audit(
            action=AuditAction.UPDATE.value,
            entity_type="bom_specification",
            entity_id=specification.id,
            actor_id=actor_id,
            before=before,
            after={
                "code": specification.code,
                "name": specification.name,
                "status": specification.status,
            },
        )
        await self._commit_and_refresh(specification)
        return specification

    async def archive_specification(
        self, specification_id: UUID, *, actor_id: UUID
    ) -> BomSpecificationModel:
        specification = await self.get_specification(specification_id)
        specification.status = SpecificationStatus.ARCHIVED.value
        specification.is_active = False
        await BomSpecificationRepository(self.session).update(specification)
        await self._audit(
            action=AuditAction.ARCHIVE.value,
            entity_type="bom_specification",
            entity_id=specification.id,
            actor_id=actor_id,
            after={"status": specification.status, "is_active": specification.is_active},
        )
        await self._commit_and_refresh(specification)
        return specification

    async def copy_specification(
        self, specification_id: UUID, data: dict[str, Any], *, actor_id: UUID
    ) -> BomSpecificationModel:
        source = await self.get_specification(specification_id)
        payload = {
            "organization_id": source.organization_id,
            "code": data["code"],
            "name": data.get("name") or f"{source.name} (копія)",
            "description": source.description,
            "product_item_id": source.product_item_id,
            "specification_type": source.specification_type,
            "status": SpecificationStatus.DRAFT.value,
            "current_version_number": 1,
            "effective_from": source.effective_from,
            "effective_to": source.effective_to,
            "author_employee_id": source.author_employee_id,
            "notes": source.notes,
            "is_active": True,
        }
        target = await self.create_specification(payload, actor_id=actor_id)
        source_version = await self.current_version(source.id)
        target_version = await self.current_version(target.id)
        await self._copy_lines(source_version.id, target_version.id)
        await self._commit_and_refresh(target)
        return target

    async def list_versions(self, specification_id: UUID) -> list[BomVersionModel]:
        await self.get_specification(specification_id)
        return await BomVersionRepository(self.session).list_for_specification(specification_id)

    async def get_version(self, version_id: UUID) -> BomVersionModel:
        version = await BomVersionRepository(self.session).get(version_id)
        if version is None:
            raise EntityNotFoundError("BOM version not found.", {"id": str(version_id)})
        return version

    async def current_version(self, specification_id: UUID) -> BomVersionModel:
        specification = await self.get_specification(specification_id)
        version = await self.session.scalar(
            select(BomVersionModel).where(
                BomVersionModel.bom_id == specification.id,
                BomVersionModel.version_number == specification.current_version_number,
            )
        )
        if version is None:
            raise EntityNotFoundError("Current BOM version not found.")
        return version

    async def update_version(
        self,
        version_id: UUID,
        data: dict[str, Any],
        *,
        expected_version: int | None,
        actor_id: UUID,
    ) -> BomVersionModel:
        version = await self.get_version(version_id)
        self._ensure_draft(version)
        self._ensure_version(version, expected_version)
        self._apply_updates(version, data)
        await BomVersionRepository(self.session).update(version)
        await self._audit(
            action=AuditAction.UPDATE.value,
            entity_type="bom_version",
            entity_id=version.id,
            actor_id=actor_id,
        )
        await self._commit_and_refresh(version)
        return version

    async def create_version(
        self, specification_id: UUID, data: dict[str, Any], *, actor_id: UUID
    ) -> BomVersionModel:
        specification = await self.get_specification(specification_id)
        if specification.status == SpecificationStatus.ARCHIVED.value:
            raise ValidationError("Archived specifications cannot create new versions.")
        source_id = data.get("source_version_id")
        source = (
            await self.get_version(source_id)
            if source_id
            else await self.current_version(specification.id)
        )
        if source.bom_id != specification.id:
            raise ValidationError("Source version must belong to the same specification.")
        next_number = (
            await BomVersionRepository(self.session).max_version_number(specification.id) + 1
        )
        version = await BomVersionRepository(self.session).create(
            BomVersionModel(
                bom_id=specification.id,
                version_number=next_number,
                version_label=data.get("version_label"),
                status=BomVersionStatus.DRAFT.value,
                change_reason=data.get("change_reason"),
                created_by_user_id=actor_id,
                effective_from=data.get("effective_from", source.effective_from),
                effective_to=data.get("effective_to", source.effective_to),
            )
        )
        await self._copy_lines(source.id, version.id)
        specification.current_version_number = next_number
        specification.status = SpecificationStatus.DRAFT.value
        await BomSpecificationRepository(self.session).update(specification)
        await self._audit(
            action=AuditAction.CREATE.value,
            entity_type="bom_version",
            entity_id=version.id,
            actor_id=actor_id,
            after={"version_number": next_number, "source_version_id": str(source.id)},
        )
        await self._commit_and_refresh(version)
        return version

    async def submit_review(self, version_id: UUID, *, actor_id: UUID) -> BomVersionModel:
        version = await self.get_version(version_id)
        self._ensure_draft(version)
        version.status = BomVersionStatus.UNDER_REVIEW.value
        specification = await self.get_specification(version.bom_id)
        specification.status = SpecificationStatus.UNDER_REVIEW.value
        await self._audit(
            action=AuditAction.UPDATE.value,
            entity_type="bom_version",
            entity_id=version.id,
            actor_id=actor_id,
            after={"status": version.status},
        )
        await self._commit_and_refresh(version)
        return version

    async def approve_version(self, version_id: UUID, *, actor_id: UUID) -> BomVersionModel:
        version = await self.get_version(version_id)
        if version.status not in {
            BomVersionStatus.DRAFT.value,
            BomVersionStatus.UNDER_REVIEW.value,
        }:
            raise ValidationError("Only draft or review versions can be approved.")
        specification = await self.get_specification(version.bom_id)
        previous_versions = await BomVersionRepository(self.session).list_for_specification(
            specification.id
        )
        now = datetime.now(UTC)
        for previous in previous_versions:
            if (
                previous.id != version.id
                and previous.status == BomVersionStatus.APPROVED.value
                and previous.effective_to is None
            ):
                previous.status = BomVersionStatus.SUPERSEDED.value
        version.status = BomVersionStatus.APPROVED.value
        version.approved_by_user_id = actor_id
        version.approved_at = now
        version.snapshot_data = await self.prepare_document(version.id, force_current=True)
        specification.status = SpecificationStatus.APPROVED.value
        specification.current_version_number = version.version_number
        specification.approved_at = now
        await self._audit(
            action=AuditAction.APPROVE.value,
            entity_type="bom_version",
            entity_id=version.id,
            actor_id=actor_id,
            after={"status": version.status, "snapshot": True},
        )
        await self._commit_and_refresh(version)
        return version

    async def supersede_version(self, version_id: UUID, *, actor_id: UUID) -> BomVersionModel:
        version = await self.get_version(version_id)
        if version.status != BomVersionStatus.APPROVED.value:
            raise ValidationError("Only approved versions can be superseded.")
        version.status = BomVersionStatus.SUPERSEDED.value
        await self._audit(
            action=AuditAction.UPDATE.value,
            entity_type="bom_version",
            entity_id=version.id,
            actor_id=actor_id,
            after={"status": version.status},
        )
        await self._commit_and_refresh(version)
        return version

    async def archive_version(self, version_id: UUID, *, actor_id: UUID) -> BomVersionModel:
        version = await self.get_version(version_id)
        if version.status == BomVersionStatus.ARCHIVED.value:
            return version
        if version.status in {BomVersionStatus.APPROVED.value, BomVersionStatus.SUPERSEDED.value}:
            version.snapshot_data = version.snapshot_data or await self.prepare_document(
                version.id, force_current=True
            )
        version.status = BomVersionStatus.ARCHIVED.value
        specification = await self.get_specification(version.bom_id)
        if specification.current_version_number == version.version_number:
            specification.status = SpecificationStatus.ARCHIVED.value
            specification.is_active = False
        await self._audit(
            action=AuditAction.ARCHIVE.value,
            entity_type="bom_version",
            entity_id=version.id,
            actor_id=actor_id,
            after={"status": version.status},
        )
        await self._commit_and_refresh(version)
        return version

    async def copy_version(
        self, version_id: UUID, data: dict[str, Any], *, actor_id: UUID
    ) -> BomVersionModel:
        source = await self.get_version(version_id)
        return await self.create_version(
            source.bom_id,
            {
                "source_version_id": source.id,
                "version_label": data.get("version_label"),
                "change_reason": data.get("change_reason"),
            },
            actor_id=actor_id,
        )

    async def list_lines(self, version_id: UUID) -> list[BomLineModel]:
        await self.get_version(version_id)
        return await BomLineRepository(self.session).list_for_version(version_id)

    async def add_line(
        self, version_id: UUID, data: dict[str, Any], *, actor_id: UUID
    ) -> BomLineModel:
        version = await self.get_version(version_id)
        self._ensure_draft(version)
        specification = await self.get_specification(version.bom_id)
        item: ItemModel | None = None
        if data.get("inventory_item_id"):
            item = await self._ensure_item(specification.organization_id, data["inventory_item_id"])
        unit = await self._ensure_unit(specification.organization_id, data["unit_of_measure_id"])
        await self._validate_parent(version_id, data.get("parent_line_id"), None)
        quantity = Decimal(str(data["quantity"]))
        waste_percentage = Decimal(str(data.get("waste_percentage", 0)))
        if quantity <= 0:
            raise ValidationError("Line quantity must be greater than zero.", {"field": "quantity"})
        if waste_percentage < 0 or waste_percentage > 100:
            raise ValidationError("Waste percentage must be from 0 to 100.")
        line_number = data.get("line_number") or await BomLineRepository(
            self.session
        ).next_line_number(version_id)
        display_name = data.get("display_name") or (item.name if item is not None else None)
        if not display_name:
            raise ValidationError("Line display name is required.", {"field": "display_name"})
        source_type = data.get("source_type") or (
            BomLineSourceType.INVENTORY_ITEM.value
            if item is not None
            else BomLineSourceType.MANUAL.value
        )
        line = await BomLineRepository(self.session).create(
            BomLineModel(
                bom_version_id=version_id,
                line_number=line_number,
                parent_line_id=data.get("parent_line_id"),
                inventory_item_id=data.get("inventory_item_id"),
                position_code=data.get("position_code") or (item.sku if item is not None else None),
                display_name=display_name,
                description=data.get("description"),
                quantity=quantity,
                unit_of_measure_id=unit.id,
                waste_percentage=waste_percentage,
                is_optional=data.get("is_optional", False),
                is_alternative=data.get("is_alternative", False),
                alternative_group=data.get("alternative_group"),
                reference_designator=data.get("reference_designator"),
                drawing_number=data.get("drawing_number")
                or (item.drawing_number if item else None),
                manufacturer=data.get("manufacturer") or (item.manufacturer if item else None),
                manufacturer_part_number=data.get("manufacturer_part_number")
                or (item.manufacturer_part_number if item else None),
                technical_requirements=data.get("technical_requirements"),
                notes=data.get("notes"),
                sort_order=data.get("sort_order") or line_number,
                source_type=source_type,
            )
        )
        await self._audit(
            action=AuditAction.CREATE.value,
            entity_type="bom_line",
            entity_id=line.id,
            actor_id=actor_id,
            after={"display_name": line.display_name, "quantity": str(line.quantity)},
        )
        await self._commit_and_refresh(line)
        return line

    async def update_line(
        self,
        version_id: UUID,
        line_id: UUID,
        data: dict[str, Any],
        *,
        expected_version: int | None,
        actor_id: UUID,
    ) -> BomLineModel:
        version = await self.get_version(version_id)
        self._ensure_draft(version)
        specification = await self.get_specification(version.bom_id)
        line = await self._get_line(version_id, line_id)
        self._ensure_version(line, expected_version)
        if data.get("inventory_item_id") is not None:
            await self._ensure_item(specification.organization_id, data["inventory_item_id"])
        if data.get("unit_of_measure_id") is not None:
            await self._ensure_unit(specification.organization_id, data["unit_of_measure_id"])
        await self._validate_parent(
            version_id, data.get("parent_line_id", line.parent_line_id), line.id
        )
        before = {
            "display_name": line.display_name,
            "quantity": str(line.quantity),
            "notes": line.notes,
        }
        if "quantity" in data and Decimal(str(data["quantity"])) <= 0:
            raise ValidationError("Line quantity must be greater than zero.", {"field": "quantity"})
        if "waste_percentage" in data:
            waste = Decimal(str(data["waste_percentage"]))
            if waste < 0 or waste > 100:
                raise ValidationError("Waste percentage must be from 0 to 100.")
        self._apply_updates(line, data)
        await BomLineRepository(self.session).update(line)
        after = {
            "display_name": line.display_name,
            "quantity": str(line.quantity),
            "notes": line.notes,
        }
        await self._audit(
            action=AuditAction.UPDATE.value,
            entity_type="bom_line",
            entity_id=line.id,
            actor_id=actor_id,
            before=before,
            after=after,
        )
        await self._commit_and_refresh(line)
        return line

    async def delete_line(self, version_id: UUID, line_id: UUID, *, actor_id: UUID) -> None:
        version = await self.get_version(version_id)
        self._ensure_draft(version)
        line = await self._get_line(version_id, line_id)
        await self.session.execute(delete(BomLineModel).where(BomLineModel.id == line.id))
        await self._audit(
            action=AuditAction.DELETE.value,
            entity_type="bom_line",
            entity_id=line.id,
            actor_id=actor_id,
            before={"display_name": line.display_name},
        )
        await self.unit_of_work.commit()

    async def reorder_lines(
        self, version_id: UUID, line_ids: list[UUID], *, actor_id: UUID
    ) -> list[BomLineModel]:
        version = await self.get_version(version_id)
        self._ensure_draft(version)
        lines = await BomLineRepository(self.session).list_for_version(version_id)
        line_by_id = {line.id: line for line in lines}
        if set(line_ids) != set(line_by_id):
            raise ValidationError("Reorder payload must contain every line exactly once.")
        for index, line_id in enumerate(line_ids, start=1):
            line_by_id[line_id].line_number = -index
            line_by_id[line_id].sort_order = index
        await self.session.flush()
        for index, line_id in enumerate(line_ids, start=1):
            line_by_id[line_id].line_number = index
        await self._audit(
            action="reorder",
            entity_type="bom_version",
            entity_id=version_id,
            actor_id=actor_id,
            after={"line_ids": [str(line_id) for line_id in line_ids]},
        )
        await self.unit_of_work.commit()
        return await BomLineRepository(self.session).list_for_version(version_id)

    async def duplicate_line(
        self, version_id: UUID, line_id: UUID, *, actor_id: UUID
    ) -> BomLineModel:
        source = await self._get_line(version_id, line_id)
        payload = self._line_payload(source)
        payload["line_number"] = await BomLineRepository(self.session).next_line_number(version_id)
        payload["sort_order"] = payload["line_number"]
        return await self.add_line(version_id, payload, actor_id=actor_id)

    async def prepare_document(
        self, version_id: UUID, *, force_current: bool = False
    ) -> dict[str, Any]:
        version = await self.get_version(version_id)
        if (
            not force_current
            and version.status
            in {
                BomVersionStatus.APPROVED.value,
                BomVersionStatus.SUPERSEDED.value,
                BomVersionStatus.ARCHIVED.value,
            }
            and version.snapshot_data
        ):
            return version.snapshot_data
        specification = await self.get_specification(version.bom_id)
        organization = await self.session.get(OrganizationModel, specification.organization_id)
        product_name = None
        if specification.product_item_id:
            product = await self.session.get(ItemModel, specification.product_item_id)
            product_name = product.name if product else None
        lines = await BomLineRepository(self.session).list_for_version(version.id)
        prepared_lines = [await self._line_snapshot(line) for line in lines]
        return {
            "organization_name": organization.name if organization else "UKRFLYBUD",
            "product_name": product_name,
            "specification": {
                "id": str(specification.id),
                "code": specification.code,
                "name": specification.name,
                "description": specification.description,
                "status": specification.status,
            },
            "version": {
                "id": str(version.id),
                "version_number": version.version_number,
                "version_label": version.version_label,
                "status": version.status,
                "effective_from": (
                    version.effective_from.isoformat() if version.effective_from else None
                ),
                "effective_to": version.effective_to.isoformat() if version.effective_to else None,
                "approved_at": version.approved_at.isoformat() if version.approved_at else None,
            },
            "lines": prepared_lines,
        }

    async def validate_import(self, version_id: UUID, content: bytes) -> dict[str, Any]:
        version = await self.get_version(version_id)
        self._ensure_draft(version)
        specification = await self.get_specification(version.bom_id)
        rows = parse_import_xlsx(content)
        results: list[dict[str, Any]] = []
        valid = True
        for row in rows:
            errors: list[str] = []
            name = str(row.get("Найменування") or "").strip()
            quantity = row.get("Кількість")
            unit_code = str(row.get("Одиниця виміру") or "").strip()
            item_code = str(row.get("Код позиції") or "").strip()
            if not name:
                errors.append("Найменування є обов'язковим.")
            try:
                if Decimal(str(quantity)) <= 0:
                    errors.append("Кількість має бути більше нуля.")
            except Exception:
                errors.append("Кількість має бути числом.")
            unit = await self._find_unit(specification.organization_id, unit_code)
            if unit is None:
                errors.append("Одиницю виміру не знайдено.")
            item = (
                await self._find_item(specification.organization_id, item_code)
                if item_code
                else None
            )
            valid = valid and not errors
            results.append(
                {
                    "row_number": row["_row_number"],
                    "valid": not errors,
                    "errors": errors,
                    "matched_inventory_item_id": str(item.id) if item else None,
                    "source_type": (
                        BomLineSourceType.INVENTORY_ITEM.value
                        if item
                        else BomLineSourceType.MANUAL.value
                    ),
                    "data": row,
                }
            )
        return {"valid": valid, "rows": results}

    async def import_lines(
        self, version_id: UUID, content: bytes, *, actor_id: UUID
    ) -> dict[str, Any]:
        validation = await self.validate_import(version_id, content)
        if not validation["valid"]:
            return validation
        version = await self.get_version(version_id)
        specification = await self.get_specification(version.bom_id)
        imported = 0
        for result in validation["rows"]:
            row = result["data"]
            unit = await self._find_unit(
                specification.organization_id, str(row["Одиниця виміру"]).strip()
            )
            if unit is None:
                raise ValidationError("Validated import lost unit match.")
            item_id = result["matched_inventory_item_id"]
            await self.add_line(
                version_id,
                {
                    "inventory_item_id": UUID(item_id) if item_id else None,
                    "position_code": row.get("Код позиції"),
                    "display_name": row.get("Найменування"),
                    "quantity": row.get("Кількість"),
                    "unit_of_measure_id": unit.id,
                    "manufacturer": row.get("Виробник"),
                    "manufacturer_part_number": row.get("Артикул виробника"),
                    "drawing_number": row.get("Креслення"),
                    "technical_requirements": row.get("Технічні вимоги"),
                    "notes": row.get("Примітка"),
                    "source_type": result["source_type"],
                },
                actor_id=actor_id,
            )
            imported += 1
        await self._audit(
            action=AuditAction.IMPORT_COMPLETED.value,
            entity_type="bom_version",
            entity_id=version_id,
            actor_id=actor_id,
            after={"rows": imported},
        )
        await self.unit_of_work.commit()
        return {"valid": True, "imported": imported, "rows": validation["rows"]}

    async def list_attachments(self, version_id: UUID) -> list[BomAttachmentModel]:
        await self.get_version(version_id)
        return await BomAttachmentRepository(self.session).list_for_version(version_id)

    async def add_attachment(
        self, version_id: UUID, data: dict[str, Any], *, actor_id: UUID
    ) -> BomAttachmentModel:
        version = await self.get_version(version_id)
        self._ensure_draft(version)
        if data["file_size"] > 25 * 1024 * 1024:
            raise ValidationError("Attachment exceeds allowed file size.")
        allowed = {
            "application/pdf",
            "image/png",
            "image/jpeg",
            "image/gif",
            "image/webp",
            "image/vnd.dwg",
            "image/vnd.dxf",
            "application/acad",
            "application/dwg",
            "application/dxf",
            "application/msword",
            "application/vnd.ms-excel",
            "application/vnd.oasis.opendocument.text",
            "application/vnd.oasis.opendocument.spreadsheet",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        allowed_suffixes = {
            ".pdf",
            ".dwg",
            ".dxf",
            ".png",
            ".jpg",
            ".jpeg",
            ".gif",
            ".webp",
            ".doc",
            ".docx",
            ".xls",
            ".xlsx",
            ".odt",
            ".ods",
        }
        suffix = (
            f".{data['filename'].rsplit('.', 1)[-1].lower()}" if "." in data["filename"] else ""
        )
        if data["mime_type"] not in allowed and suffix not in allowed_suffixes:
            raise ValidationError("Attachment file type is not allowed.")
        attachment = await BomAttachmentRepository(self.session).create(
            BomAttachmentModel(**data, bom_version_id=version_id, uploaded_by_user_id=actor_id)
        )
        await self._audit(
            action=AuditAction.CREATE.value,
            entity_type="bom_attachment",
            entity_id=attachment.id,
            actor_id=actor_id,
            after={"filename": attachment.filename},
        )
        await self._commit_and_refresh(attachment)
        return attachment

    async def delete_attachment(self, attachment_id: UUID, *, actor_id: UUID) -> None:
        attachment = await BomAttachmentRepository(self.session).get(attachment_id)
        if attachment is None:
            raise EntityNotFoundError("Attachment not found.", {"id": str(attachment_id)})
        version = await self.get_version(attachment.bom_version_id)
        self._ensure_draft(version)
        attachment.deleted_at = datetime.now(UTC)
        await self._audit(
            action=AuditAction.DELETE.value,
            entity_type="bom_attachment",
            entity_id=attachment.id,
            actor_id=actor_id,
            before={"filename": attachment.filename},
        )
        await self.unit_of_work.commit()

    async def _copy_lines(self, source_version_id: UUID, target_version_id: UUID) -> None:
        source_lines = await BomLineRepository(self.session).list_for_version(source_version_id)
        id_map: dict[UUID, UUID] = {}
        for source in source_lines:
            copied = BomLineModel(**self._line_payload(source), bom_version_id=target_version_id)
            await BomLineRepository(self.session).create(copied)
            id_map[source.id] = copied.id
        for source in source_lines:
            if source.parent_line_id and source.parent_line_id in id_map:
                copied = await self._get_line(target_version_id, id_map[source.id])
                copied.parent_line_id = id_map[source.parent_line_id]

    async def _commit_and_refresh(self, entity: object) -> None:
        await self.unit_of_work.commit()
        await self.unit_of_work.refresh(entity)

    def _line_payload(self, line: BomLineModel) -> dict[str, Any]:
        return {
            "line_number": line.line_number,
            "parent_line_id": line.parent_line_id,
            "inventory_item_id": line.inventory_item_id,
            "position_code": line.position_code,
            "display_name": line.display_name,
            "description": line.description,
            "quantity": line.quantity,
            "unit_of_measure_id": line.unit_of_measure_id,
            "waste_percentage": line.waste_percentage,
            "is_optional": line.is_optional,
            "is_alternative": line.is_alternative,
            "alternative_group": line.alternative_group,
            "reference_designator": line.reference_designator,
            "drawing_number": line.drawing_number,
            "manufacturer": line.manufacturer,
            "manufacturer_part_number": line.manufacturer_part_number,
            "technical_requirements": line.technical_requirements,
            "notes": line.notes,
            "sort_order": line.sort_order,
            "source_type": line.source_type,
        }

    async def _line_snapshot(self, line: BomLineModel) -> dict[str, Any]:
        unit = await self.session.get(UnitOfMeasureModel, line.unit_of_measure_id)
        item = (
            await self.session.get(ItemModel, line.inventory_item_id)
            if line.inventory_item_id
            else None
        )
        manufacturer_summary = " / ".join(
            value for value in [line.manufacturer, line.manufacturer_part_number] if value
        )
        return {
            "id": str(line.id),
            "line_number": line.line_number,
            "parent_line_id": str(line.parent_line_id) if line.parent_line_id else None,
            "inventory_item_id": str(line.inventory_item_id) if line.inventory_item_id else None,
            "inventory_item_name": item.name if item else None,
            "position_code": line.position_code,
            "display_name": line.display_name,
            "description": line.description,
            "quantity": str(line.quantity),
            "unit_name": unit.name if unit else "",
            "unit_symbol": unit.symbol if unit else "",
            "waste_percentage": str(line.waste_percentage),
            "is_optional": line.is_optional,
            "is_alternative": line.is_alternative,
            "alternative_group": line.alternative_group,
            "reference_designator": line.reference_designator,
            "drawing_number": line.drawing_number,
            "manufacturer": line.manufacturer,
            "manufacturer_part_number": line.manufacturer_part_number,
            "manufacturer_summary": manufacturer_summary,
            "technical_requirements": line.technical_requirements,
            "notes": line.notes,
            "sort_order": line.sort_order,
            "source_type": line.source_type,
        }

    async def _ensure_organization(self, organization_id: UUID) -> None:
        exists = await self.session.scalar(
            select(func.count())
            .select_from(OrganizationModel)
            .where(OrganizationModel.id == organization_id)
        )
        if not exists:
            raise EntityNotFoundError("Organization not found.", {"id": str(organization_id)})

    async def _ensure_employee(self, organization_id: UUID, employee_id: UUID | None) -> None:
        if employee_id is None:
            return
        employee = await self.session.get(EmployeeModel, employee_id)
        if employee is None or employee.deleted_at is not None:
            raise EntityNotFoundError("Employee not found.", {"id": str(employee_id)})
        if employee.organization_id != organization_id:
            raise ValidationError("Employee must belong to the same organization.")

    async def _ensure_item(self, organization_id: UUID, item_id: UUID) -> ItemModel:
        item = await self.session.get(ItemModel, item_id)
        if item is None or item.deleted_at is not None:
            raise EntityNotFoundError("Inventory item not found.", {"id": str(item_id)})
        if item.organization_id != organization_id:
            raise ValidationError("Inventory item must belong to the same organization.")
        return item

    async def _ensure_unit(self, organization_id: UUID, unit_id: UUID) -> UnitOfMeasureModel:
        unit = await self.session.get(UnitOfMeasureModel, unit_id)
        if unit is None or unit.deleted_at is not None:
            raise EntityNotFoundError("Unit of measure not found.", {"id": str(unit_id)})
        if unit.organization_id != organization_id:
            raise ValidationError("Unit of measure must belong to the same organization.")
        return unit

    async def _find_unit(
        self, organization_id: UUID, code_or_symbol: str
    ) -> UnitOfMeasureModel | None:
        if not code_or_symbol:
            return None
        return cast(
            UnitOfMeasureModel | None,
            await self.session.scalar(
                select(UnitOfMeasureModel).where(
                    UnitOfMeasureModel.organization_id == organization_id,
                    UnitOfMeasureModel.deleted_at.is_(None),
                    (UnitOfMeasureModel.code == code_or_symbol)
                    | (UnitOfMeasureModel.symbol == code_or_symbol)
                    | (UnitOfMeasureModel.name == code_or_symbol),
                )
            ),
        )

    async def _find_item(self, organization_id: UUID, code: str) -> ItemModel | None:
        if not code:
            return None
        return cast(
            ItemModel | None,
            await self.session.scalar(
                select(ItemModel).where(
                    ItemModel.organization_id == organization_id,
                    ItemModel.deleted_at.is_(None),
                    (ItemModel.sku == code) | (ItemModel.internal_part_number == code),
                )
            ),
        )

    async def _get_line(self, version_id: UUID, line_id: UUID) -> BomLineModel:
        line = await BomLineRepository(self.session).get_for_version(version_id, line_id)
        if line is None:
            raise EntityNotFoundError("BOM line not found.", {"id": str(line_id)})
        return line

    async def _validate_parent(
        self, version_id: UUID, parent_line_id: UUID | None, line_id: UUID | None
    ) -> None:
        if parent_line_id is None:
            return
        if parent_line_id == line_id:
            raise ValidationError("BOM line hierarchy cannot contain cycles.")
        parent = await self._get_line(version_id, parent_line_id)
        seen = {line_id} if line_id else set()
        while parent.parent_line_id is not None:
            if parent.parent_line_id in seen:
                raise ValidationError("BOM line hierarchy cannot contain cycles.")
            seen.add(parent.parent_line_id)
            parent = await self._get_line(version_id, parent.parent_line_id)

    @staticmethod
    def _ensure_version(entity: Any, expected_version: int | None) -> None:
        if expected_version is not None and entity.version != expected_version:
            raise ConflictError(
                "Entity version conflict.",
                {"expected_version": expected_version, "current_version": entity.version},
            )

    @staticmethod
    def _ensure_draft(version: BomVersionModel) -> None:
        if version.status != BomVersionStatus.DRAFT.value:
            raise ValidationError("Only draft BOM versions can be edited.")

    @staticmethod
    def _apply_updates(entity: Any, data: dict[str, Any]) -> None:
        for field, value in data.items():
            setattr(entity, field, value)

    async def _audit(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: UUID,
        actor_id: UUID | None,
        before: dict[str, Any] | None = None,
        after: dict[str, Any] | None = None,
    ) -> None:
        await SQLAlchemyAuditLogRepository(self.session).create(
            AuditLog(
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                actor_id=actor_id,
                before_data=before,
                after_data=after,
                correlation_id=None,
            )
        )
