from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.models.base import EntityNotFoundError


@pytest.mark.asyncio
async def test_unified_api_error_format() -> None:
    app = create_app()

    @app.get("/raise-domain-error")
    async def raise_domain_error() -> None:
        raise EntityNotFoundError("Missing.", details={"resource": "technical"})

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/raise-domain-error")

    assert response.status_code == 404
    payload = response.json()
    assert payload["code"] == "entity_not_found"
    assert payload["message"] == "Сутність не знайдено."
    assert payload["details"] == {"resource": "technical"}
    assert payload["correlation_id"]


@pytest.mark.asyncio
async def test_correlation_id_generation() -> None:
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"]


@pytest.mark.asyncio
async def test_incoming_correlation_id_propagation() -> None:
    app = create_app()
    correlation_id = str(uuid4())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get(
            "/api/v1/health",
            headers={"X-Correlation-ID": correlation_id},
        )

    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == correlation_id


def test_production_specific_order_routes_precede_generic_action_route() -> None:
    app = create_app()
    route_positions = {
        path: index
        for index, path in enumerate(app.openapi()["paths"])
        if path.startswith("/api/v1/production/orders/")
    }

    generic_position = route_positions["/api/v1/production/orders/{order_id}/{action}"]
    for specific_path in (
        "/api/v1/production/orders/{order_id}/reserve-materials",
        "/api/v1/production/orders/{order_id}/release-reservations",
        "/api/v1/production/orders/{order_id}/issue-materials",
        "/api/v1/production/orders/{order_id}/return-materials",
        "/api/v1/production/orders/{order_id}/consume-materials",
        "/api/v1/production/orders/{order_id}/scrap-materials",
        "/api/v1/production/orders/{order_id}/complete",
        "/api/v1/production/orders/{order_id}/preview",
        "/api/v1/production/orders/{order_id}/export/pdf",
        "/api/v1/production/orders/{order_id}/export/xlsx",
    ):
        assert route_positions[specific_path] < generic_position
