from fastapi import APIRouter

from app.modules.production.presentation.routes import (
    completion,
    exports,
    materials,
    orders,
    stages,
)

router = APIRouter(prefix="/production")
router.include_router(materials.router)
router.include_router(stages.router)
router.include_router(completion.router)
router.include_router(exports.router)
router.include_router(orders.router)
