from fastapi import APIRouter

from app.api.v1.routes import health
from app.modules.organizations.presentation.routes import router as organizations_router

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(organizations_router, tags=["organization core"])
