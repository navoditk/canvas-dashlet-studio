import sys
from datetime import UTC, date, datetime
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashlets.treasury_curve_dashlet import app
from treasury_fixture import CurvePoint, Provenance, TreasuryCurveResponse

client = TestClient(app)


def test_health_route() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_fixture_dates_endpoint_returns_sorted_dates() -> None:
    response = client.get("/api/treasury/fixture-dates")
    assert response.status_code == 200
    payload = response.json()
    assert payload["available_dates"] == ["2026-08-18", "2026-08-19"]


def test_metadata_endpoint_returns_typed_contract() -> None:
    response = client.get("/metadata")
    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Treasury Curve Dashlet"
    assert payload["version"] == "0.1.0"
    assert payload["data_mode"] == "fixture"
    assert payload["default_curve_date"] == "2026-08-19"
    assert payload["canonical_slopes"] == ["2s10s", "3m10y", "5s30s"]
    assert payload["available_fixture_dates"] == ["2026-08-18", "2026-08-19"]
    assert payload["supported_endpoints"] == [
        "/api/treasury/fixture-dates",
        "/api/treasury/view",
        "/api/treasury/curve",
        "/api/treasury/slopes",
        "/api/treasury/compare",
    ]


def test_curve_view_endpoint_returns_curve_and_slopes() -> None:
    response = client.get("/api/treasury/view", params={"date": "2026-08-19"})
    assert response.status_code == 200
    payload = response.json()

    assert payload["observation_date"] == "2026-08-19"
    assert payload["curve"]["provenance"]["source"] == "synthetic-fixture"
    assert [point["maturity_label"] for point in payload["curve"]["points"]] == [
        "3M",
        "2Y",
        "5Y",
        "10Y",
        "30Y",
    ]
    assert [slope["name"] for slope in payload["slopes"]] == ["2s10s", "3m10y", "5s30s"]


def test_curve_endpoint_returns_typed_payload() -> None:
    response = client.get("/api/treasury/curve", params={"date": "2026-08-19"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["provenance"]["source"] == "synthetic-fixture"
    assert payload["provenance"]["data_mode"] == "fixture"
    assert payload["provenance"]["observation_date"] == "2026-08-19"
    assert [point["maturity_label"] for point in payload["points"]] == [
        "3M",
        "2Y",
        "5Y",
        "10Y",
        "30Y",
    ]


def test_slopes_endpoint_returns_named_slopes() -> None:
    response = client.get("/api/treasury/slopes", params={"date": "2026-08-19"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["observation_date"] == "2026-08-19"
    assert [slope["name"] for slope in payload["slopes"]] == ["2s10s", "3m10y", "5s30s"]


def test_compare_endpoint_returns_deterministic_deltas() -> None:
    response = client.get(
        "/api/treasury/compare",
        params={"base_date": "2026-08-18", "compare_date": "2026-08-19"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["base_observation_date"] == "2026-08-18"
    assert payload["compare_observation_date"] == "2026-08-19"
    assert len(payload["points"]) == 5
    assert [point["maturity_label"] for point in payload["points"]] == [
        "3M",
        "2Y",
        "5Y",
        "10Y",
        "30Y",
    ]


def test_openapi_operation_ids_and_agent_tool_tags() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    openapi = response.json()

    curve_op = openapi["paths"]["/api/treasury/curve"]["get"]
    slopes_op = openapi["paths"]["/api/treasury/slopes"]["get"]
    compare_op = openapi["paths"]["/api/treasury/compare"]["get"]
    fixture_dates_op = openapi["paths"]["/api/treasury/fixture-dates"]["get"]
    metadata_op = openapi["paths"]["/metadata"]["get"]
    view_op = openapi["paths"]["/api/treasury/view"]["get"]

    assert curve_op["operationId"] == "get_treasury_curve"
    assert slopes_op["operationId"] == "get_treasury_curve_slopes"
    assert compare_op["operationId"] == "compare_treasury_curves"
    assert fixture_dates_op["operationId"] == "list_treasury_fixture_dates"
    assert metadata_op["operationId"] == "get_treasury_dashlet_metadata"
    assert view_op["operationId"] == "get_treasury_curve_view"

    assert "agent-tool" in curve_op["tags"]
    assert "agent-tool" in slopes_op["tags"]
    assert "agent-tool" in compare_op["tags"]
    assert "tags" not in fixture_dates_op or "agent-tool" not in fixture_dates_op.get("tags", [])
    assert "tags" not in metadata_op or "agent-tool" not in metadata_op.get("tags", [])
    assert "tags" not in view_op or "agent-tool" not in view_op.get("tags", [])

    assert curve_op["summary"] == "Get Treasury Curve"
    assert slopes_op["summary"] == "Get Canonical Curve Slopes"
    assert compare_op["summary"] == "Compare Treasury Curves"
    assert fixture_dates_op["summary"] == "List Treasury Fixture Dates"
    assert metadata_op["summary"] == "Get Treasury Dashlet Metadata"
    assert view_op["summary"] == "Get Treasury Curve View"

    assert "deterministic fixture-backed" in curve_op["description"]
    assert "canonical slope pairs" in slopes_op["description"]
    assert "basis-point deltas" in compare_op["description"]

    curve_date_param = next(param for param in curve_op["parameters"] if param["name"] == "date")
    assert curve_date_param["description"] == (
        "Observation date in YYYY-MM-DD format. Omit to use the latest available fixture date."
    )
    assert curve_date_param["required"] is False

    compare_base_param = next(param for param in compare_op["parameters"] if param["name"] == "base_date")
    compare_date_param = next(param for param in compare_op["parameters"] if param["name"] == "compare_date")
    assert compare_base_param["description"] == "Required base observation date in YYYY-MM-DD format."
    assert compare_date_param["description"] == "Required comparison observation date in YYYY-MM-DD format."
    assert compare_base_param["required"] is True
    assert compare_date_param["required"] is True

    slope_param_names = [param["name"] for param in slopes_op.get("parameters", [])]
    assert "date" in slope_param_names
    assert "short_label" not in slope_param_names
    assert "long_label" not in slope_param_names
    assert "pairs" not in slope_param_names

    curve_error_404_schema = curve_op["responses"]["404"]["content"]["application/json"]["schema"]
    curve_error_422_schema = curve_op["responses"]["422"]["content"]["application/json"]["schema"]
    assert curve_error_404_schema["$ref"].endswith("/DashletErrorResponse")
    assert curve_error_422_schema["$ref"].endswith("/DashletErrorResponse")


def test_unknown_fixture_date_returns_404() -> None:
    response = client.get("/api/treasury/curve", params={"date": "2099-01-01"})
    assert response.status_code == 404
    detail = response.json()["detail"]
    assert detail["error_code"] == "fixture_not_found"
    assert "No fixture found for date" in detail["message"]


def test_curve_endpoint_rejects_invalid_date_format() -> None:
    response = client.get("/api/treasury/curve", params={"date": "20260819"})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error_code"] == "invalid_date"
    assert "Invalid date" in detail["message"]


def test_compare_endpoint_rejects_invalid_calendar_date() -> None:
    response = client.get(
        "/api/treasury/compare",
        params={"base_date": "2026-02-30", "compare_date": "2026-08-19"},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error_code"] == "invalid_date"
    assert "Invalid date" in detail["message"]


def test_compare_endpoint_requires_both_dates() -> None:
    missing_compare = client.get("/api/treasury/compare", params={"base_date": "2026-08-18"})
    missing_base = client.get("/api/treasury/compare", params={"compare_date": "2026-08-19"})
    assert missing_compare.status_code == 422
    assert missing_base.status_code == 422


def test_curve_endpoint_omitted_date_uses_latest_available_and_is_not_stale() -> None:
    response = client.get("/api/treasury/curve")
    assert response.status_code == 200
    payload = response.json()
    assert payload["provenance"]["observation_date"] == "2026-08-19"
    assert payload["provenance"]["is_stale"] is False


def test_curve_endpoint_older_date_is_marked_stale() -> None:
    response = client.get("/api/treasury/curve", params={"date": "2026-08-18"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["provenance"]["is_stale"] is True


def test_curve_endpoint_provenance_includes_timezone_aware_retrieved_at() -> None:
    response = client.get("/api/treasury/curve", params={"date": "2026-08-19"})
    assert response.status_code == 200
    provenance = response.json()["provenance"]
    assert "retrieved_at" in provenance
    assert provenance["retrieved_at"].endswith("+00:00") or provenance["retrieved_at"].endswith("Z")
    assert provenance["source_url"] is None


def test_slopes_endpoint_missing_required_maturity_returns_controlled_422(monkeypatch, tmp_path) -> None:
    from dashlets import treasury_curve_dashlet

    incomplete_fixture = tmp_path / "curve_2030-01-01.json"
    incomplete_fixture.write_text(
        """
        {
          "fixture_meta": {"note": "Deterministic synthetic test fixture. Not live market data.", "data_mode": "fixture"},
          "observation_date": "2030-01-01",
          "curve": [
            {"maturity_label": "2Y", "maturity_years": 2.0, "yield_percent": 4.00},
            {"maturity_label": "10Y", "maturity_years": 10.0, "yield_percent": 4.20}
          ]
        }
        """
    )
    monkeypatch.setattr(treasury_curve_dashlet, "FIXTURE_DIR", tmp_path)

    response = client.get("/api/treasury/slopes", params={"date": "2030-01-01"})

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error_code"] == "missing_slope_maturity"
    assert "Missing maturity required for slope" in detail["message"]


def test_compare_endpoint_mismatched_maturities_returns_controlled_422(monkeypatch, tmp_path) -> None:
    from dashlets import treasury_curve_dashlet

    base_fixture = tmp_path / "curve_2030-02-01.json"
    base_fixture.write_text(
        """
        {
          "fixture_meta": {"note": "Deterministic synthetic test fixture. Not live market data.", "data_mode": "fixture"},
          "observation_date": "2030-02-01",
          "curve": [
            {"maturity_label": "2Y", "maturity_years": 2.0, "yield_percent": 4.00},
            {"maturity_label": "10Y", "maturity_years": 10.0, "yield_percent": 4.20}
          ]
        }
        """
    )
    compare_fixture = tmp_path / "curve_2030-02-02.json"
    compare_fixture.write_text(
        """
        {
          "fixture_meta": {"note": "Deterministic synthetic test fixture. Not live market data.", "data_mode": "fixture"},
          "observation_date": "2030-02-02",
          "curve": [
            {"maturity_label": "2Y", "maturity_years": 2.0, "yield_percent": 4.05},
            {"maturity_label": "30Y", "maturity_years": 30.0, "yield_percent": 4.40}
          ]
        }
        """
    )
    monkeypatch.setattr(treasury_curve_dashlet, "FIXTURE_DIR", tmp_path)

    response = client.get(
        "/api/treasury/compare",
        params={"base_date": "2030-02-01", "compare_date": "2030-02-02"},
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["error_code"] == "maturity_mismatch"
    assert "Maturity labels must match" in detail["message"]


def test_root_page_returns_html_shell() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]

    html = response.text
    assert "<title>Treasury Curve Dashlet</title>" in html
    assert 'x-data="treasuryApp"' in html
    assert 'id="curve-chart"' in html


def test_root_page_contains_expected_controls_and_state_hooks() -> None:
    response = client.get("/")
    assert response.status_code == 200
    html = response.text

    assert 'x-model="selectedDate"' in html
    assert 'x-model="compareDate"' in html
    assert '@click="loadCurve"' in html
    assert '@click="loadComparison"' in html
    assert 'x-show="isLoadingCurve || isLoadingComparison"' in html
    assert 'x-text="provenanceText"' in html


def test_root_page_uses_mount_relative_api_fetch_paths() -> None:
    response = client.get("/")
    assert response.status_code == 200
    html = response.text

    assert 'fetch("./api/treasury/fixture-dates")' in html
    assert 'fetch(`./api/treasury/curve${query}`)' in html
    assert 'fetch(`./api/treasury/slopes${query}`)' in html
    assert 'fetch(`./api/treasury/compare${query}`)' in html


def test_root_page_contains_expanded_provenance_contract_tokens() -> None:
    response = client.get("/")
    assert response.status_code == 200
    html = response.text

    assert "curve_date=" in html
    assert "compare_base=" in html
    assert "compare_date=" in html
    assert "stale=" in html
    assert "retrieved_at=" in html


def test_compare_endpoint_marks_stale_when_either_observation_date_is_not_latest() -> None:
    response = client.get(
        "/api/treasury/compare",
        params={"base_date": "2026-08-18", "compare_date": "2026-08-19"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["provenance"]["is_stale"] is True


def test_compare_endpoint_same_latest_dates_are_not_stale() -> None:
    response = client.get(
        "/api/treasury/compare",
        params={"base_date": "2026-08-19", "compare_date": "2026-08-19"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["provenance"]["is_stale"] is False


def _stub_curve_response(observation_date: str, data_mode: str) -> TreasuryCurveResponse:
    return TreasuryCurveResponse(
        points=[
            CurvePoint(maturity_label="3M", maturity_years=0.25, yield_percent=4.90),
            CurvePoint(maturity_label="2Y", maturity_years=2.0, yield_percent=4.20),
            CurvePoint(maturity_label="5Y", maturity_years=5.0, yield_percent=4.00),
            CurvePoint(maturity_label="10Y", maturity_years=10.0, yield_percent=4.18),
            CurvePoint(maturity_label="30Y", maturity_years=30.0, yield_percent=4.40),
        ],
        provenance=Provenance(
            source=f"stub-{data_mode}",
            data_mode=data_mode,
            observation_date=date.fromisoformat(observation_date),
            retrieved_at=datetime.now(UTC),
            source_url=None,
            is_stale=False,
        ),
    )


def test_curve_endpoint_fixture_mode_calls_only_fixture_provider(monkeypatch) -> None:
    from dashlets import treasury_curve_dashlet

    calls = {"fixture": 0, "eod": 0}

    class StubProvider:
        def __init__(self, mode: str) -> None:
            self.mode = mode

        def get_curve(self, observation_date: str) -> TreasuryCurveResponse:
            calls[self.mode] += 1
            return _stub_curve_response(observation_date, self.mode)

    fixture_provider = StubProvider("fixture")
    eod_provider = StubProvider("eod")

    def resolver(mode, _fixture_dir):
        return fixture_provider if mode.value == "fixture" else eod_provider

    monkeypatch.setattr(treasury_curve_dashlet, "resolve_provider", resolver)

    response = client.get(
        "/api/treasury/curve",
        params={"date": "2026-08-19", "data_mode": "fixture"},
    )

    assert response.status_code == 200
    assert calls["fixture"] == 1
    assert calls["eod"] == 0
    assert response.json()["provenance"]["data_mode"] == "fixture"


def test_curve_endpoint_eod_mode_calls_only_eod_provider(monkeypatch) -> None:
    from dashlets import treasury_curve_dashlet

    calls = {"fixture": 0, "eod": 0}

    class StubProvider:
        def __init__(self, mode: str) -> None:
            self.mode = mode

        def get_curve(self, observation_date: str) -> TreasuryCurveResponse:
            calls[self.mode] += 1
            return _stub_curve_response(observation_date, self.mode)

    fixture_provider = StubProvider("fixture")
    eod_provider = StubProvider("eod")

    def resolver(mode, _fixture_dir):
        return fixture_provider if mode.value == "fixture" else eod_provider

    monkeypatch.setattr(treasury_curve_dashlet, "resolve_provider", resolver)

    response = client.get(
        "/api/treasury/curve",
        params={"date": "2026-08-19", "data_mode": "eod"},
    )

    assert response.status_code == 200
    assert calls["fixture"] == 0
    assert calls["eod"] == 1
    assert response.json()["provenance"]["data_mode"] == "eod"


def test_curve_endpoint_rejects_omitted_data_mode() -> None:
    response = client.get("/api/treasury/curve", params={"date": "2026-08-19"})
    assert response.status_code == 422


def test_curve_endpoint_rejects_unsupported_data_mode() -> None:
    response = client.get(
        "/api/treasury/curve",
        params={"date": "2026-08-19", "data_mode": "live"},
    )
    assert response.status_code == 422


def test_fixture_mode_performs_no_network_request(monkeypatch) -> None:
    from dashlets import treasury_provider

    called = {"httpx_client": 0}

    class TrackingClient:
        def __init__(self, *args, **kwargs):
            called["httpx_client"] += 1

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def get(self, _url):
            raise AssertionError("Fixture mode should never call remote HTTP")

    monkeypatch.setattr(treasury_provider.httpx, "Client", TrackingClient)

    response = client.get(
        "/api/treasury/curve",
        params={"date": "2026-08-19", "data_mode": "fixture"},
    )

    assert response.status_code == 200
    assert called["httpx_client"] == 0


def test_eod_failure_does_not_fallback_to_fixture(monkeypatch) -> None:
    from dashlets import treasury_curve_dashlet

    calls = {"fixture": 0, "eod": 0}

    class FixtureProvider:
        def get_curve(self, _observation_date: str) -> TreasuryCurveResponse:
            calls["fixture"] += 1
            return _stub_curve_response("2026-08-19", "fixture")

    class FailingEodProvider:
        def get_curve(self, _observation_date: str) -> TreasuryCurveResponse:
            calls["eod"] += 1
            raise treasury_curve_dashlet.ProviderError("feed_timeout", "timeout")

    fixture_provider = FixtureProvider()
    failing_eod_provider = FailingEodProvider()

    def resolver(mode, _fixture_dir):
        return fixture_provider if mode.value == "fixture" else failing_eod_provider

    monkeypatch.setattr(treasury_curve_dashlet, "resolve_provider", resolver)

    response = client.get(
        "/api/treasury/curve",
        params={"date": "2026-08-19", "data_mode": "eod"},
    )

    assert response.status_code == 504
    assert calls["eod"] == 1
    assert calls["fixture"] == 0
    detail = response.json()["detail"]
    assert detail["error_code"] == "feed_timeout"