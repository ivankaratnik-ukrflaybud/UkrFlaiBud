import pytest
from pydantic import ValidationError

from app.schemas.pagination import MAX_PAGE_SIZE, PageRequest


def test_page_validation() -> None:
    with pytest.raises(ValidationError):
        PageRequest(page=0)


def test_maximum_page_size_validation() -> None:
    with pytest.raises(ValidationError):
        PageRequest(page_size=MAX_PAGE_SIZE + 1)


def test_page_offset() -> None:
    page = PageRequest(page=3, page_size=25)

    assert page.offset == 50
