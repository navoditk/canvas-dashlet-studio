import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashlets.hello_dashlet import app

client = TestClient(app)


def test_root_contains_mount_relative_summary_fetch() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "./api/summary" in response.text


def test_health_route() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_summary_route_shape() -> None:
    response = client.get("/api/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Hello Dashlet"
    assert payload["message"] == "Smoke test successful"
    assert isinstance(payload["generated_at"], str)
    assert payload["source"] == "fixture"
    assert payload["data_mode"] == "fixture"


def test_openapi_summary_operation_metadata() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    openapi = response.json()
    operation = openapi["paths"]["/api/summary"]["get"]
    assert operation["operationId"] == "get_dashlet_summary"
    assert "agent-tool" in operation["tags"]


def test_metadata_route_shape() -> None:
    response = client.get("/metadata")
    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Hello Dashlet"
    assert payload["version"] == "0.1.0"
    assert payload["data_mode"] == "fixture"
    assert payload["supported_endpoints"] == ["/api/summary"]


def test_metadata_route_is_not_an_agent_tool() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    openapi = response.json()
    operation = openapi["paths"]["/metadata"]["get"]
    assert "tags" not in operation or "agent-tool" not in operation.get("tags", [])
