"""Generic contract validation, run against every registered dashlet.

Unlike tests/test_hello_dashlet.py or tests/test_treasury_curve_dashlet.py,
nothing here is specific to one dashlet. Adding a new dashlet to
scripts.generate_tool_schemas.DASHLET_MODULES makes it covered by every
check in this file automatically -- see docs/DASHLET_CONTRACT.md and
AGENTS.md for the contract these checks enforce.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from dashlet_framework import AGENT_TOOL_TAG
from scripts.generate_tool_schemas import DASHLET_MODULES, _load_app

APPS = {module_target: _load_app(module_target) for module_target in DASHLET_MODULES}


def _agent_tool_operations(openapi: dict):
    for path, path_item in openapi.get("paths", {}).items():
        for method, operation in path_item.items():
            if not isinstance(operation, dict) or "operationId" not in operation:
                continue
            if AGENT_TOOL_TAG in (operation.get("tags") or []):
                yield path, method, operation


def test_every_dashlet_exposes_health() -> None:
    for module_target, app in APPS.items():
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200, module_target
        assert response.json() == {"status": "ready"}, module_target


def test_every_dashlet_exposes_metadata_and_it_is_not_an_agent_tool() -> None:
    for module_target, app in APPS.items():
        client = TestClient(app)
        response = client.get("/metadata")
        assert response.status_code == 200, module_target

        openapi = client.get("/openapi.json").json()
        operation = openapi["paths"]["/metadata"]["get"]
        assert AGENT_TOOL_TAG not in (operation.get("tags") or []), module_target


def test_health_route_is_never_an_agent_tool() -> None:
    for module_target, app in APPS.items():
        openapi = app.openapi()
        operation = openapi["paths"]["/health"]["get"]
        assert AGENT_TOOL_TAG not in (operation.get("tags") or []), module_target


def test_root_page_is_never_an_agent_tool_and_returns_html() -> None:
    for module_target, app in APPS.items():
        openapi = app.openapi()
        if "/" not in openapi.get("paths", {}):
            continue
        operation = openapi["paths"]["/"]["get"]
        assert AGENT_TOOL_TAG not in (operation.get("tags") or []), module_target

        client = TestClient(app)
        response = client.get("/")
        assert response.status_code == 200, module_target
        assert "text/html" in response.headers["content-type"], module_target


def test_every_agent_tool_operation_has_a_unique_id_and_declared_response_model() -> None:
    seen_operation_ids: dict[str, str] = {}
    for module_target, app in APPS.items():
        openapi = app.openapi()
        for path, method, operation in _agent_tool_operations(openapi):
            operation_id = operation["operationId"]
            assert operation_id not in seen_operation_ids, (
                f"operationId {operation_id!r} is used by both "
                f"{seen_operation_ids.get(operation_id)} and {module_target} "
                "-- operationId must be unique across every registered dashlet"
            )
            seen_operation_ids[operation_id] = module_target

            responses = operation.get("responses", {})
            schema = responses.get("200", {}).get("content", {}).get("application/json", {}).get("schema", {})
            has_response_model = "$ref" in schema or "properties" in schema
            assert has_response_model, (
                f"{module_target} {method.upper()} {path} ({operation_id}) is tagged "
                f"{AGENT_TOOL_TAG} but has no declared Pydantic response_model"
            )


def test_root_page_uses_mount_relative_fetch_paths() -> None:
    for module_target, app in APPS.items():
        openapi = app.openapi()
        if "/" not in openapi.get("paths", {}):
            continue
        client = TestClient(app)
        html = client.get("/").text
        assert 'fetch("/' not in html, (
            f"{module_target}'s root page appears to use an absolute fetch path; "
            'use fetch("./api/...") so the dashlet works both standalone and mounted under a gallery'
        )
