import sys
from datetime import date, datetime
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashlet_framework import (
    AGENT_TOOL_TAG,
    DashletErrorDetail,
    DashletErrorResponse,
    Provenance,
    create_dashlet_app,
)


def test_agent_tool_tag_value() -> None:
    assert AGENT_TOOL_TAG == "agent-tool"


def test_create_dashlet_app_sets_title_and_version() -> None:
    app = create_dashlet_app(title="Example Dashlet", version="1.2.3")
    assert app.title == "Example Dashlet"
    assert app.version == "1.2.3"


def test_create_dashlet_app_registers_health_route() -> None:
    app = create_dashlet_app(title="Example Dashlet", version="0.1.0")
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_create_dashlet_app_health_route_is_not_an_agent_tool() -> None:
    app = create_dashlet_app(title="Example Dashlet", version="0.1.0")
    client = TestClient(app)
    openapi = client.get("/openapi.json").json()
    operation = openapi["paths"]["/health"]["get"]
    assert "tags" not in operation or AGENT_TOOL_TAG not in operation.get("tags", [])


def test_provenance_round_trips_required_fields() -> None:
    provenance = Provenance(
        source="synthetic-fixture",
        source_url=None,
        observation_date=date(2026, 8, 19),
        retrieved_at=datetime.fromisoformat("2026-08-19T00:00:00+00:00"),
        data_mode="fixture",
        is_stale=False,
    )
    assert provenance.source == "synthetic-fixture"
    assert provenance.is_stale is False


def test_dashlet_error_response_shape() -> None:
    error = DashletErrorResponse(
        detail=DashletErrorDetail(error_code="example_error", message="Something went wrong")
    )
    assert error.detail.error_code == "example_error"
    assert error.detail.message == "Something went wrong"
