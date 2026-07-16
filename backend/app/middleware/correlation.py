from typing import cast
from uuid import UUID, uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.request_context import correlation_id_var

CORRELATION_ID_HEADER = "X-Correlation-ID"


def is_valid_correlation_id(value: str) -> bool:
    try:
        UUID(value)
    except ValueError:
        return False
    return True


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:  # type: ignore[no-untyped-def]
        incoming_correlation_id = request.headers.get(CORRELATION_ID_HEADER)
        correlation_id = (
            incoming_correlation_id
            if incoming_correlation_id and is_valid_correlation_id(incoming_correlation_id)
            else str(uuid4())
        )

        token = correlation_id_var.set(correlation_id)
        try:
            response = cast(Response, await call_next(request))
        finally:
            correlation_id_var.reset(token)

        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response
