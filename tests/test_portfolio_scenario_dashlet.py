import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashlets.portfolio_scenario_dashlet import app

client = TestClient(app)


def test_health_route() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_fixture_dates_endpoint_returns_sorted_dates() -> None:
    response = client.get("/api/scenario/fixture-dates")
    assert response.status_code == 200
    assert response.json()["available_dates"] == ["2026-08-18", "2026-08-19"]


def test_metadata_endpoint_returns_typed_contract() -> None:
    response = client.get("/metadata")
    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Portfolio Scenario Impact Dashlet"
    assert payload["version"] == "0.1.0"
    assert payload["data_mode"] == "fixture"
    assert payload["default_observation_date"] == "2026-08-19"
    assert payload["supported_endpoints"] == [
        "/api/scenario/fixture-dates",
        "/api/scenario/run",
        "/api/scenario/contributions",
        "/api/scenario/compare",
    ]


def test_run_endpoint_zero_shock_returns_zero_impact() -> None:
    response = client.get("/api/scenario/run", params={"date": "2026-08-19"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["observation_date"] == "2026-08-19"
    assert payload["totals"]["total_impact"] == pytest.approx(0.0)
    assert len(payload["position_impacts"]) == 12
    assert len(payload["sector_contributions"]) == 5


def test_run_endpoint_equity_shock_matches_known_fixture_value() -> None:
    response = client.get(
        "/api/scenario/run", params={"date": "2026-08-19", "equity_shock_pct": 10.0}
    )
    assert response.status_code == 200
    payload = response.json()
    # TechCore Inc: beta 1.3 * $2,400,000 * 10% = $312,000
    techcore = next(p for p in payload["position_impacts"] if p["issuer"] == "TechCore Inc")
    assert techcore["equity_impact"] == pytest.approx(312_000.0)
    assert payload["totals"]["equity_impact"] == pytest.approx(1_154_000.0)
    assert payload["totals"]["total_impact"] == pytest.approx(1_154_000.0)


def test_run_endpoint_rate_and_spread_shocks_are_zero_for_this_all_equity_book() -> None:
    response = client.get(
        "/api/scenario/run",
        params={"date": "2026-08-19", "rate_shock_bps": 100.0, "spread_shock_bps": 100.0},
    )
    assert response.status_code == 200
    totals = response.json()["totals"]
    assert totals["rate_impact"] == 0.0
    assert totals["spread_impact"] == 0.0
    assert totals["total_impact"] == 0.0


def test_run_endpoint_omitted_date_uses_latest_available() -> None:
    response = client.get("/api/scenario/run")
    assert response.status_code == 200
    assert response.json()["observation_date"] == "2026-08-19"


def test_run_endpoint_unknown_date_returns_404() -> None:
    response = client.get("/api/scenario/run", params={"date": "2099-01-01"})
    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "fixture_not_found"


@pytest.mark.parametrize(
    "params",
    [
        {"rate_shock_bps": 999},
        {"rate_shock_bps": -999},
        {"spread_shock_bps": 999},
        {"spread_shock_bps": -999},
        {"equity_shock_pct": 999},
        {"equity_shock_pct": -999},
    ],
)
def test_run_endpoint_rejects_out_of_bounds_shocks(params: dict) -> None:
    response = client.get("/api/scenario/run", params=params)
    assert response.status_code == 422


def test_contributions_endpoint_ranks_by_absolute_impact() -> None:
    response = client.get(
        "/api/scenario/contributions", params={"equity_shock_pct": 10.0, "top_n": 3}
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["top_position_impacts"]) == 3
    impacts = [abs(p["total_impact"]) for p in payload["top_position_impacts"]]
    assert impacts == sorted(impacts, reverse=True)
    assert payload["top_position_impacts"][0]["issuer"] == "TechCore Inc"


def test_contributions_endpoint_default_top_n_is_five() -> None:
    response = client.get("/api/scenario/contributions", params={"equity_shock_pct": 10.0})
    assert response.status_code == 200
    assert len(response.json()["top_position_impacts"]) == 5


def test_contributions_endpoint_rejects_top_n_out_of_range() -> None:
    too_low = client.get("/api/scenario/contributions", params={"top_n": 0})
    too_high = client.get("/api/scenario/contributions", params={"top_n": 21})
    assert too_low.status_code == 422
    assert too_high.status_code == 422


def test_compare_endpoint_returns_deterministic_sector_deltas() -> None:
    response = client.get(
        "/api/scenario/compare",
        params={"equity_pct_a": 10.0, "equity_pct_b": -10.0},
    )
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["sector_deltas"]) == 5
    technology = next(row for row in payload["sector_deltas"] if row["sector"] == "Technology")
    # Symmetric +10%/-10% shock -> impact_b == -impact_a, delta == -2 * impact_a
    assert technology["impact_b"] == pytest.approx(-technology["impact_a"])
    assert technology["delta"] == pytest.approx(-2 * technology["impact_a"])


def test_compare_endpoint_identical_scenarios_yield_zero_deltas() -> None:
    response = client.get(
        "/api/scenario/compare",
        params={"equity_pct_a": 10.0, "equity_pct_b": 10.0},
    )
    assert response.status_code == 200
    for row in response.json()["sector_deltas"]:
        assert row["delta"] == pytest.approx(0.0)


def test_compare_endpoint_unknown_date_returns_404() -> None:
    response = client.get("/api/scenario/compare", params={"date": "2099-01-01"})
    assert response.status_code == 404


def test_openapi_operation_ids_and_agent_tool_tags() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    openapi = response.json()

    run_op = openapi["paths"]["/api/scenario/run"]["get"]
    contrib_op = openapi["paths"]["/api/scenario/contributions"]["get"]
    compare_op = openapi["paths"]["/api/scenario/compare"]["get"]
    fixture_dates_op = openapi["paths"]["/api/scenario/fixture-dates"]["get"]
    metadata_op = openapi["paths"]["/metadata"]["get"]

    assert run_op["operationId"] == "run_portfolio_scenario"
    assert contrib_op["operationId"] == "get_scenario_contributions"
    assert compare_op["operationId"] == "compare_scenario_impacts"
    assert fixture_dates_op["operationId"] == "list_scenario_fixture_dates"
    assert metadata_op["operationId"] == "get_scenario_dashlet_metadata"

    assert "agent-tool" in run_op["tags"]
    assert "agent-tool" in contrib_op["tags"]
    assert "agent-tool" in compare_op["tags"]
    assert "tags" not in fixture_dates_op or "agent-tool" not in fixture_dates_op.get("tags", [])
    assert "tags" not in metadata_op or "agent-tool" not in metadata_op.get("tags", [])


def test_root_page_returns_html_shell() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text
    assert "<title>Portfolio Scenario Impact Dashlet</title>" in html
    assert 'x-data="scenarioApp"' in html
    assert 'id="contribution-chart"' in html


def test_root_page_contains_expected_controls_and_state_hooks() -> None:
    html = client.get("/").text
    assert 'x-model="selectedDate"' in html
    assert 'x-model.number="rateShockBps"' in html
    assert 'x-model.number="spreadShockBps"' in html
    assert 'x-model.number="equityShockPct"' in html
    assert '@click="runScenario"' in html
    assert '@click="compareScenarios"' in html
    assert 'x-text="provenanceText"' in html


def test_root_page_uses_mount_relative_api_fetch_paths() -> None:
    html = client.get("/").text
    assert 'fetch("./api/scenario/fixture-dates")' in html
    assert 'fetch(`./api/scenario/run${query}`)' in html
    assert 'fetch(`./api/scenario/contributions${query}`)' in html
    assert 'fetch(`./api/scenario/compare?${params.toString()}`)' in html
