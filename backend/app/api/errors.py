from typing import Any, cast

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.request_context import get_correlation_id
from app.models.base import (
    ConflictError,
    DomainError,
    EntityNotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.schemas.errors import ApiErrorResponse

UKRAINIAN_ERROR_MESSAGES = {
    "entity_not_found": "Сутність не знайдено.",
    "conflict": "Конфлікт даних.",
    "validation_error": "Помилка валідації.",
    "permission_denied": "Недостатньо прав.",
    "http_error": "Помилка HTTP-запиту.",
    "internal_server_error": "Внутрішня помилка сервера.",
}

DOMAIN_STATUS_CODES: dict[type[DomainError], int] = {
    EntityNotFoundError: status.HTTP_404_NOT_FOUND,
    ConflictError: status.HTTP_409_CONFLICT,
    ValidationError: status.HTTP_400_BAD_REQUEST,
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
}


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, cast(Any, domain_error_handler))
    app.add_exception_handler(RequestValidationError, cast(Any, request_validation_error_handler))
    app.add_exception_handler(HTTPException, cast(Any, http_exception_handler))
    app.add_exception_handler(Exception, unhandled_exception_handler)


async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    del request
    status_code = _status_for_domain_error(exc)
    return _error_response(
        status_code=status_code,
        code=exc.code,
        message=UKRAINIAN_ERROR_MESSAGES.get(exc.code, exc.message),
        details=exc.details,
    )


async def request_validation_error_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    del request
    return _error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="validation_error",
        message=UKRAINIAN_ERROR_MESSAGES["validation_error"],
        details={"errors": exc.errors()},
    )


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    del request
    return _error_response(
        status_code=exc.status_code,
        code="http_error",
        message=UKRAINIAN_ERROR_MESSAGES["http_error"],
        details={"detail": exc.detail},
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    del request, exc
    return _error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_server_error",
        message=UKRAINIAN_ERROR_MESSAGES["internal_server_error"],
        details={},
    )


def _status_for_domain_error(exc: DomainError) -> int:
    for error_type, status_code in DOMAIN_STATUS_CODES.items():
        if isinstance(exc, error_type):
            return status_code
    return status.HTTP_400_BAD_REQUEST


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
    details: dict[str, Any],
) -> JSONResponse:
    payload = ApiErrorResponse(
        code=code,
        message=message,
        details=details,
        correlation_id=get_correlation_id(),
    )
    headers = {}
    if payload.correlation_id:
        headers["X-Correlation-ID"] = payload.correlation_id
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(),
        headers=headers,
    )
