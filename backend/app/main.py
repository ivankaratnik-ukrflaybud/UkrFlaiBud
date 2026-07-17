from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import configure_logging
from app.middleware.correlation import CorrelationIdMiddleware
from app.modules.identity.application.services import IdentityService
from app.repositories.sqlalchemy_unit_of_work import SQLAlchemyUnitOfWork


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        openapi_url="/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(CorrelationIdMiddleware)

    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api/v1")

    @app.on_event("startup")
    async def bootstrap_identity() -> None:
        async with SQLAlchemyUnitOfWork() as unit_of_work:
            await IdentityService(unit_of_work).bootstrap_admin()

    return app


app = create_app()
