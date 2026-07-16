from enum import StrEnum
from typing import Any, TypeVar

from pydantic import BaseModel, Field

MAX_PAGE_SIZE = 100
ItemT = TypeVar("ItemT")


class PageRequest(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=50, ge=1, le=MAX_PAGE_SIZE)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class PaginatedResponse[ItemT](BaseModel):
    items: list[ItemT]
    page: int
    page_size: int
    total: int


class SortDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"


class SortRequest(BaseModel):
    field: str = Field(min_length=1, max_length=120)
    direction: SortDirection = SortDirection.ASC


class FilterOperator(StrEnum):
    EQ = "eq"
    NE = "ne"
    LT = "lt"
    LTE = "lte"
    GT = "gt"
    GTE = "gte"
    CONTAINS = "contains"
    IN = "in"


class FilterRequest(BaseModel):
    field: str = Field(min_length=1, max_length=120)
    operator: FilterOperator = FilterOperator.EQ
    value: Any
