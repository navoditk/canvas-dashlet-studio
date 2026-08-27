import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashlets.issuer_research_dashlet import app

client = TestClient(app)


def test_health_route() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_available_issuers_endpoint() -> None:
    response = client.get("/api/issuer/companies")
    assert response.status_code == 200
    assert response.json()["available_fixture_tickers"] == ["AAPL", "MSFT"]


def test_metadata_endpoint_returns_typed_contract() -> None:
    response = client.get("/metadata")
    assert response.status_code == 200
    payload = response.json()
    assert payload["title"] == "Issuer Research Dashlet"
    assert payload["version"] == "0.1.0"
    assert payload["data_mode"] == "fixture,live"
    assert payload["default_ticker"] == "AAPL"
    assert payload["available_fixture_tickers"] == ["AAPL", "MSFT"]
    assert payload["supported_endpoints"] == [
        "/api/issuer/companies",
        "/api/issuer/facts",
        "/api/issuer/trends",
        "/api/issuer/filings",
    ]


# --- get_company_facts -------------------------------------------------


def test_facts_endpoint_fixture_mode_returns_real_apple_data() -> None:
    response = client.get("/api/issuer/facts", params={"ticker": "AAPL", "data_mode": "fixture"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["ticker"] == "AAPL"
    assert payload["company_name"] == "Apple Inc."
    assert payload["cik"] == "0000320193"
    assert payload["revenue"]["value"] > 0
    assert payload["revenue"]["source_url"].startswith("https://www.sec.gov/Archives/edgar/data/")
    assert payload["operating_margin_pct"] is not None
    assert payload["provenance"]["source"] == "sec-edgar-recorded"
    assert payload["provenance"]["data_mode"] == "fixture"


def test_facts_endpoint_ticker_is_case_insensitive() -> None:
    response = client.get("/api/issuer/facts", params={"ticker": "aapl", "data_mode": "fixture"})
    assert response.status_code == 200
    assert response.json()["ticker"] == "AAPL"


def test_facts_endpoint_second_fixture_ticker() -> None:
    response = client.get("/api/issuer/facts", params={"ticker": "MSFT", "data_mode": "fixture"})
    assert response.status_code == 200
    assert "MICROSOFT" in response.json()["company_name"].upper()


def test_facts_endpoint_unknown_ticker_in_fixture_mode_returns_404() -> None:
    response = client.get("/api/issuer/facts", params={"ticker": "ZZZZ", "data_mode": "fixture"})
    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "unknown_ticker"


def test_facts_endpoint_invalid_data_mode_returns_422() -> None:
    response = client.get("/api/issuer/facts", params={"ticker": "AAPL", "data_mode": "bogus"})
    assert response.status_code == 422
    # data_mode is typed as the IssuerDataMode enum directly (like Treasury's
    # TreasuryDataMode), so FastAPI/Pydantic reject it natively before the
    # request handler runs -- this also means the enum constraint shows up
    # in the generated OpenAPI schema (and therefore the Copilot tool
    # schema), not just as a runtime check.
    assert "fixture" in str(response.json()["detail"]) and "live" in str(response.json()["detail"])


def test_facts_endpoint_requires_ticker_and_data_mode() -> None:
    missing_ticker = client.get("/api/issuer/facts", params={"data_mode": "fixture"})
    missing_mode = client.get("/api/issuer/facts", params={"ticker": "AAPL"})
    assert missing_ticker.status_code == 422
    assert missing_mode.status_code == 422


# --- get_financial_trends ------------------------------------------------


def test_trends_endpoint_returns_all_five_years_by_default() -> None:
    response = client.get("/api/issuer/trends", params={"ticker": "AAPL", "data_mode": "fixture"})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["trend_points"]) == 5
    fiscal_years = [p["fiscal_year"] for p in payload["trend_points"]]
    assert fiscal_years == sorted(fiscal_years)  # ascending, oldest to newest


def test_trends_endpoint_years_bound_limits_result() -> None:
    response = client.get(
        "/api/issuer/trends", params={"ticker": "AAPL", "data_mode": "fixture", "years": 2}
    )
    assert response.status_code == 200
    assert len(response.json()["trend_points"]) == 2


def test_trends_endpoint_rejects_years_out_of_range() -> None:
    too_low = client.get("/api/issuer/trends", params={"ticker": "AAPL", "data_mode": "fixture", "years": 0})
    too_high = client.get("/api/issuer/trends", params={"ticker": "AAPL", "data_mode": "fixture", "years": 6})
    assert too_low.status_code == 422
    assert too_high.status_code == 422


# --- list_recent_filings --------------------------------------------------


def test_filings_endpoint_default_limit_is_eight() -> None:
    response = client.get("/api/issuer/filings", params={"ticker": "AAPL", "data_mode": "fixture"})
    assert response.status_code == 200
    payload = response.json()
    assert len(payload["filings"]) <= 8
    for filing in payload["filings"]:
        assert filing["source_url"].startswith("https://www.sec.gov/Archives/edgar/data/")


def test_filings_endpoint_form_type_filter() -> None:
    response = client.get(
        "/api/issuer/filings", params={"ticker": "MSFT", "data_mode": "fixture", "form_type": "10-K"}
    )
    assert response.status_code == 200
    payload = response.json()
    assert all(f["form"] == "10-K" for f in payload["filings"])
    assert len(payload["filings"]) >= 1


def test_filings_endpoint_rejects_limit_out_of_range() -> None:
    too_low = client.get("/api/issuer/filings", params={"ticker": "AAPL", "data_mode": "fixture", "limit": 0})
    too_high = client.get("/api/issuer/filings", params={"ticker": "AAPL", "data_mode": "fixture", "limit": 9})
    assert too_low.status_code == 422
    assert too_high.status_code == 422


# --- live mode routing (mocked httpx, no real network calls) --------------


def _json_response(payload: dict, status_code: int = 200) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    return response


def test_facts_endpoint_live_mode_routes_through_public_provider() -> None:
    ticker_map = {"0": {"cik_str": 9999999, "ticker": "LIVE", "title": "Live Corp"}}
    submissions = {
        "cik": "9999999",
        "name": "Live Corp",
        "sic": "7372",
        "sicDescription": "Services-Prepackaged Software",
        "tickers": ["LIVE"],
        "filings": {"recent": {"form": [], "filingDate": [], "reportDate": [], "accessionNumber": [], "primaryDocument": []}},
    }
    company_facts = {
        "cik": 9999999,
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {
                                "start": "2023-01-01",
                                "end": "2023-12-31",
                                "val": 42_000_000.0,
                                "accn": "0000000000-24-000001",
                                "filed": "2024-02-01",
                                "fy": 2024,
                                "fp": "FY",
                                "form": "10-K",
                            }
                        ]
                    }
                }
            }
        },
    }
    mock_client = MagicMock()
    mock_client.__enter__.return_value.get.side_effect = [
        _json_response(ticker_map),
        _json_response(submissions),
        _json_response(company_facts),
    ]
    with patch("dashlets.issuer_provider.httpx.Client", return_value=mock_client):
        response = client.get("/api/issuer/facts", params={"ticker": "LIVE", "data_mode": "live"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["company_name"] == "Live Corp"
    assert payload["revenue"]["value"] == 42_000_000.0
    assert payload["provenance"]["source"] == "sec-edgar-live"
    assert payload["provenance"]["is_stale"] is False


def test_facts_endpoint_live_mode_unknown_ticker_returns_404() -> None:
    ticker_map = {"0": {"cik_str": 1, "ticker": "OTHER", "title": "Other Corp"}}
    mock_client = MagicMock()
    mock_client.__enter__.return_value.get.side_effect = [_json_response(ticker_map)]
    with patch("dashlets.issuer_provider.httpx.Client", return_value=mock_client):
        response = client.get("/api/issuer/facts", params={"ticker": "NOPE", "data_mode": "live"})
    assert response.status_code == 404
    assert response.json()["detail"]["error_code"] == "ticker_not_found"


# --- OpenAPI / contract ----------------------------------------------------


def test_openapi_operation_ids_and_agent_tool_tags() -> None:
    response = client.get("/openapi.json")
    assert response.status_code == 200
    openapi = response.json()

    facts_op = openapi["paths"]["/api/issuer/facts"]["get"]
    trends_op = openapi["paths"]["/api/issuer/trends"]["get"]
    filings_op = openapi["paths"]["/api/issuer/filings"]["get"]
    companies_op = openapi["paths"]["/api/issuer/companies"]["get"]
    metadata_op = openapi["paths"]["/metadata"]["get"]

    assert facts_op["operationId"] == "get_company_facts"
    assert trends_op["operationId"] == "get_financial_trends"
    assert filings_op["operationId"] == "list_recent_filings"
    assert companies_op["operationId"] == "list_available_issuers"
    assert metadata_op["operationId"] == "get_issuer_dashlet_metadata"

    assert "agent-tool" in facts_op["tags"]
    assert "agent-tool" in trends_op["tags"]
    assert "agent-tool" in filings_op["tags"]
    assert "tags" not in companies_op or "agent-tool" not in companies_op.get("tags", [])
    assert "tags" not in metadata_op or "agent-tool" not in metadata_op.get("tags", [])


def test_root_page_returns_html_shell() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text
    assert "<title>Issuer Research Dashlet</title>" in html
    assert 'x-data="issuerApp"' in html
    assert 'id="trend-chart"' in html


def test_root_page_contains_expected_controls_and_state_hooks() -> None:
    html = client.get("/").text
    assert 'x-model="ticker"' in html
    assert 'x-model="dataMode"' in html
    assert '@click="loadIssuer"' in html
    assert 'x-text="provenanceText"' in html


def test_root_page_uses_mount_relative_api_fetch_paths() -> None:
    html = client.get("/").text
    assert 'fetch("./api/issuer/companies")' in html
    assert 'fetch(`./api/issuer/facts${query}`)' in html
    assert 'fetch(`./api/issuer/trends${query}`)' in html
    assert 'fetch(`./api/issuer/filings${query}`)' in html
