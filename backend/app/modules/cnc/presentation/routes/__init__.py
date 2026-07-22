from fastapi import APIRouter

from app.modules.cnc.presentation.routes import (
    execution,
    exports,
    machines,
    parts,
    programs,
    settings,
    sheets,
    tooling,
    work_orders,
)

router = APIRouter(prefix="/cnc")
router.include_router(machines.router)
router.include_router(tooling.router)
router.include_router(programs.router)
router.include_router(parts.router)
router.include_router(sheets.router)
router.include_router(work_orders.router)
router.include_router(execution.router)
router.include_router(exports.router)
router.include_router(settings.router)
