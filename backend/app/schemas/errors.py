from typing import Any

from pydantic import BaseModel, Field


class ApiErrorResponse(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
