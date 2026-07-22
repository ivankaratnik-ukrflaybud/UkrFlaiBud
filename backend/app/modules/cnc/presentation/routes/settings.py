from fastapi import APIRouter, Depends

from app.modules.identity.presentation.dependencies import require_permission

router = APIRouter()

REJECTION_REASONS = [
    "пошкодження матеріалу",
    "помилка програми",
    "поломка інструмента",
    "помилка оператора",
    "невідповідність розміру",
    "інше",
]


@router.get("/settings/rejection-reasons", dependencies=[Depends(require_permission("cnc.read"))])
async def rejection_reasons() -> dict[str, list[str]]:
    return {"items": REJECTION_REASONS}
