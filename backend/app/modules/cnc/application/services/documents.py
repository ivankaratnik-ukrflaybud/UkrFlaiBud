from __future__ import annotations

from datetime import datetime
from io import BytesIO
from uuid import UUID

from openpyxl import Workbook  # type: ignore[import-untyped]
from reportlab.lib.pagesizes import A4, landscape  # type: ignore[import-untyped]
from reportlab.pdfbase import pdfmetrics  # type: ignore[import-untyped]
from reportlab.pdfbase.ttfonts import TTFont  # type: ignore[import-untyped]
from reportlab.pdfgen import canvas  # type: ignore[import-untyped]

from app.modules.cnc.application.services.common import CncServiceBase
from app.modules.cnc.infrastructure.repositories import (
    CncExecutionLogRepository,
    CncWorkOrderOutputRepository,
)


class CncDocumentService(CncServiceBase):
    async def preview_html(self, work_order_id: UUID) -> str:
        work_order = await self.get_work_order(work_order_id)
        outputs = await CncWorkOrderOutputRepository(self.session).list_for_work_order(
            work_order.id
        )
        rows = "".join(
            f"<tr><td>{output.part_code_snapshot}</td><td>{output.part_name_snapshot}</td>"
            f"<td>{output.planned_quantity}</td><td>{output.completed_quantity}</td>"
            f"<td>{output.rejected_quantity}</td></tr>"
            for output in outputs
        )
        return (
            "<!doctype html><html><head><meta charset='utf-8'><title>"
            f"{work_order.work_order_number}</title><style>"
            "@page{size:A4 landscape;margin:12mm;}"
            "body{font-family:'DejaVu Sans',Arial,sans-serif;margin:0;color:#111827;}"
            ".cnc-print-document{padding:12mm;}"
            "table{border-collapse:collapse;width:100%;}"
            "th,td{border:1px solid #6b7280;padding:4px;}"
            "thead{display:table-header-group;}tr{break-inside:avoid;}"
            "@media print{.cnc-print-document{padding:0;}}"
            "</style></head><body>"
            "<main class='cnc-print-document'>"
            "<h1>ТОВ «Укрфлайбуд»</h1><h2>ЗАВДАННЯ ЧПК</h2>"
            f"<p>Номер: {work_order.work_order_number}</p>"
            f"<p>Деталь: {work_order.part_name_snapshot or work_order.name}</p>"
            f"<p>Програма: {work_order.program_revision_snapshot or ''}</p>"
            f"<p>Матеріал: {work_order.material_name_snapshot or ''}</p>"
            "<table><thead><tr><th>Код</th><th>Деталь</th><th>План</th>"
            "<th>Виготовлено</th><th>Брак</th></tr></thead><tbody>"
            f"{rows}</tbody></table><p>Підписи: ____________</p></main></body></html>"
        )

    async def pdf(self, work_order_id: UUID) -> bytes:
        work_order = await self.get_work_order(work_order_id)
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=landscape(A4))
        try:
            pdfmetrics.registerFont(TTFont("DejaVuSans", "DejaVuSans.ttf"))
            pdf.setFont("DejaVuSans", 12)
        except Exception:
            pdf.setFont("Helvetica", 12)
        y = 800
        for line in [
            "ТОВ «Укрфлайбуд»",
            "ЗАВДАННЯ ЧПК",
            f"Номер: {work_order.work_order_number}",
            f"Деталь: {work_order.part_name_snapshot or work_order.name}",
            f"Статус: {work_order.status}",
            f"План: {work_order.planned_quantity}",
            f"Виготовлено: {work_order.completed_quantity}",
            f"Брак: {work_order.rejected_quantity}",
            f"Матеріал: {work_order.material_name_snapshot or ''}",
            f"Програма: {work_order.program_revision_snapshot or ''}",
            "Підписи: ____________________",
        ]:
            pdf.drawString(40, y, line)
            y -= 24
        pdf.showPage()
        pdf.save()
        return buffer.getvalue()

    async def xlsx(self, work_order_id: UUID) -> bytes:
        work_order = await self.get_work_order(work_order_id)
        outputs = await CncWorkOrderOutputRepository(self.session).list_for_work_order(
            work_order.id
        )
        logs = await CncExecutionLogRepository(self.session).list_for_work_order(work_order.id)
        workbook = Workbook()
        sheet = workbook.active
        sheet.page_setup.orientation = sheet.ORIENTATION_LANDSCAPE
        sheet.page_setup.paperSize = sheet.PAPERSIZE_A4
        sheet.title = "Завдання ЧПК"
        rows = [
            ["ТОВ «Укрфлайбуд»"],
            ["ЗАВДАННЯ ЧПК"],
            ["Номер", work_order.work_order_number],
            ["Деталь", work_order.part_name_snapshot or work_order.name],
            ["Статус", work_order.status],
            [],
            ["Код", "Деталь", "План", "Виготовлено", "Брак"],
        ]
        for row in rows:
            sheet.append(row)
        for output in outputs:
            sheet.append(
                [
                    output.part_code_snapshot,
                    output.part_name_snapshot,
                    output.planned_quantity,
                    output.completed_quantity,
                    output.rejected_quantity,
                ]
            )
        sheet.append([])
        sheet.append(["Історія"])
        for log in logs:
            sheet.append(
                [
                    _excel_value(log.event_at),
                    log.event_type,
                    log.quantity_good,
                    log.quantity_rejected,
                    log.reason,
                ]
            )
        stream = BytesIO()
        workbook.save(stream)
        return stream.getvalue()


def _excel_value(value: object) -> object:
    if isinstance(value, datetime) and value.tzinfo is not None:
        return value.replace(tzinfo=None)
    return value
