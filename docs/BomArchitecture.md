# BOM Architecture

Sprint 6 adds `backend/app/modules/bom` as a separate Clean Architecture module:

- `domain` defines specification, version and line enums.
- `infrastructure` contains SQLAlchemy models and repositories.
- `application` contains BOM rules, import validation and document renderers.
- `presentation` exposes `/api/v1/bom` REST endpoints.

## Versioning

Each specification is a separate document with explicit versions. Version `draft` rows can be edited. `approved` and `superseded` versions are immutable. A new draft version is created by copying an existing version and its lines.

## Display Name Snapshot

`bom_lines.display_name` is always stored on the line. Selecting an inventory item copies the item name only at creation time. Later inventory item name changes do not update BOM line names. Approval stores `bom_versions.snapshot_data`, which is used for reproducible approved exports.

## Manual and Inventory Lines

Inventory-linked lines reference `inventory_items.id` and keep a document-facing display name. Manual lines have no inventory item and are valid when they have a display name, quantity and unit. Both line types can be duplicated, deleted in draft, reordered and exported.

## Export Architecture

`BomService.prepare_document()` prepares document data. `application/documents.py` renders browser preview HTML, PDF, XLSX and XLSX import templates. API routes only call the service/renderers and set download headers.

## Reproducibility

Approved exports prefer stored `snapshot_data`. Draft exports use current line data. This keeps approved historical documents stable while allowing new draft versions to evolve.

## Approval Workflow

Draft versions can be edited, submitted for review, approved or copied. Approval marks earlier active approved versions as superseded, stores the snapshot and updates the parent specification status/current version.
