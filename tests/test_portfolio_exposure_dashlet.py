import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashlets.portfolio_exposure_dashlet import app

client = TestClient(app)


def test_health_route() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_fixture_dates_endpoint_returns_sorted_dates() -> None:
    response = client.get("/api/portfolio/fixture-dates")
    assert response.status_code == 200
    assert response.json()["available_dates"] == ["2026-08-18", "2026-08-19"]


def test_metadata_endpoint_returns_typed_contract() -> None:
    response = client.get("/metadata")
    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Portfolio Exposure Dashlet"
    assert payload["version"] == "0.1.0"
    assert payload["data_mode"] == "fixture"
    assert payload["default_observation_date"] == "2026-08-19"
    assert payload["available_fixture_dates"] == ["2026-08-18", "2026-08-19"]
    assert payload["supported_endpoints"] == [
        "/api/portfolio/fixture-dates",
        "/api/portfolio/exposures",
        "/api/portfolio/concentration",
        "/api/portfolio/compare",
    ]


def test_exposures_endpoint_returns_typed_payload() -> None:
    response = client.get("/api/portfolio/exposures", params={"date": "2026-08-19"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["observation_date"] == "2026-08-19"
    assert payload["provenance"]["source"] == "synthetic-fixture"
    assert payload["provenance"]["data_mode"] == "fixture"
    assert payload["totals"]["net_market_value"] == pytest.approx(10_650_000.0)
    assert len(payload["sector_exposures"]) == 5
    assert len(payload["issuer_exposures"]) == 12


def test_exposures_endpoint_omitted_date_uses_latest_available_and_is_not_stale() -> None:
    response = client.get("/api/portfolio/exposures")
    assert response.status_code == 200
    payload = response.json()
    assert payload["observation_date"] == "2026-08-19"
    assert payload["provenance"]["is_stale"] is False


def test_exposures_endpoint_older_date_is_marked_stale() -> None:
    response = client.get("/api/portfolio/exposures", params={"date": "2026-08-18"})
    assert response.status_code == 200
    assert response.json()["provenance"]["is_stale"] is True


def test_unknown_fixture_date_returns_404() -> None:
    response = client.get("/api/portfolio/exposures", params={"date": "2099-01-01"})
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["error_code"] == "fixture_not_found"


def test_concentration_endpoint_ranks_by_absolute_net_weight() -> None:
    response = client.get("/api/portfolio/concentration", params={"date": "2026-08-19", "top_n": 3})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["top_issuer_exposures"]) == 3
    weights = [abs(row["net_weight_pct"]) for row in payload["top_issuer_exposures"]]
    assert weights == sorted(weights, reverse=True)
    assert payload["top_issuer_exposures"][0]["issuer"] == "TechCore Inc"


def test_concentration_endpoint_default_top_n_is_five() -> None:
    response = client.get("/api/portfolio/concentration", params={"date": "2026-08-19"})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["top_issuer_exposures"]) == 5
    assert len(payload["top_sector_exposures"]) == 5


def test_concentration_endpoint_rejects_top_n_out_of_range() -> None:
    too_low = client.get("/api/portfolio/concentration", params={"date": "2026-08-19", "top_n": 0})
    too_high = client.get("/api/portfolio/concentration", params={"date": "2026-08-19", "top_n": 21})
    assert too_low.status_code == 422
    assert too_high.status_code == 422


def test_compare_endpoint_returns_deterministic_sector_deltas() -> None:
    response = client.get(
        "/api/portfolio/compare",
        params={"base_date": "2026-08-18", "compare_date": "2026-08-19"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["base_observation_date"] == "2026-08-18"
    assert payload["compare_observation_date"] == "2026-08-19"
    assert len(payload["sector_deltas"]) == 5
    technology = next(row for row in payload["sector_deltas"] if row["sector"] == "Technology")
    assert technology["delta_market_value"] == pytest.approx(150_000.0)


def test_compare_endpoint_same_dates_yields_zero_deltas() -> None:
    response = client.get(
        "/api/portfolio/compare",
        params={"base_date": "2026-08-19", "compare_date": "2026-08-19"},
    )
    assert response.status_code == 200
    for row in response.json()["sector_deltas"]:
        assert row["delta_market_value"] == pytest.approx(0.0)
        assert row["delta_weight_pct"] == pytest.approx(0.0)


def test_compare_endpoint_requires_both_dates() -> None:
    missing_compare = client.get("/api/portfolio/compare", params={"base_date": "2026-08-18"})
    missing_base = client.get("/api/portfolio/compare", params={"compare_date": "2026-08-19"})
    assert missing_compare.status_code == 422
    assert missing_base.status_code == 422


def test_compare_endpoint_unknown_date_returns_404() -> None:
    response = client.get(
        "/api/portfolio/compare",
        params={"base_date": "2026-08-19", "compare_date": "2099-01-01"},
    )
    assert response.status_code == 404


def test_openapi_operation_ids_and_agent_tool_tags() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    openapi = response.json()

    exposures_op = openapi["paths"]["/api/portfolio/exposures"]["get"]
    concentration_op = openapi["paths"]["/api/portfolio/concentration"]["get"]
    compare_op = openapi["paths"]["/api/portfolio/compare"]["get"]
    fixture_dates_op = openapi["paths"]["/api/portfolio/fixture-dates"]["get"]
    metadata_op = openapi["paths"]["/metadata"]["get"]

    assert exposures_op["operationId"] == "get_portfolio_exposures"
    assert concentration_op["operationId"] == "get_top_concentrations"
    assert compare_op["operationId"] == "compare_portfolio_exposures"
    assert fixture_dates_op["operationId"] == "list_portfolio_fixture_dates"
    assert metadata_op["operationId"] == "get_portfolio_dashlet_metadata"

    assert "agent-tool" in exposures_op["tags"]
    assert "agent-tool" in concentration_op["tags"]
    assert "agent-tool" in compare_op["tags"]
    assert "tags" not in fixture_dates_op or "agent-tool" not in fixture_dates_op.get("tags", [])
    assert "tags" not in metadata_op or "agent-tool" not in metadata_op.get("tags", [])


def test_root_page_returns_html_shell() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text
    assert "<title>Portfolio Exposure Dashlet</title>" in html
    assert 'x-data="portfolioApp"' in html
    assert 'id="sector-chart"' in html


def test_root_page_contains_expected_controls_and_state_hooks() -> None:
    html = client.get("/").text
    assert 'x-model="selectedDate"' in html
    assert 'x-model="compareDate"' in html
    assert '@click="loadExposures"' in html
    assert '@click="loadComparison"' in html
    assert 'x-text="provenanceText"' in html


def test_root_page_uses_mount_relative_api_fetch_paths() -> None:
    html = client.get("/").text
    assert 'fetch("./api/portfolio/fixture-dates")' in html
    assert 'fetch(`./api/portfolio/exposures${query}`)' in html
    assert 'fetch(`./api/portfolio/concentration${query}`)' in html
    assert 'fetch(`./api/portfolio/compare?${params.toString()}`)' in html
