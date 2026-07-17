from fastapi import APIRouter

from app.api.v1.routes import health
from app.modules.identity.presentation.routes import router as identity_router
from app.modules.inventory.presentation.routes import (
    identity_scope_router,
)
from app.modules.inventory.presentation.routes import (
    router as inventory_router,
)
from app.modules.organizations.presentation.routes import router as organizations_router

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(identity_router, tags=["identity"])
api_router.include_router(identity_scope_router, tags=["identity"])
api_router.include_router(organizations_router, tags=["organization core"])
api_router.include_router(inventory_router, tags=["inventory"])
