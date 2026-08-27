import json
import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashlets.issuer_provider import (
    FixtureIssuerProvider,
    IssuerDataMode,
    ProviderError,
    PublicIssuerProvider,
    resolve_provider,
)
from issuer_fixture import build_snapshot_from_live_json


def _sample_company_facts() -> dict:
    return {
        "cik": 1234567,
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {
                                "start": "2023-01-01",
                                "end": "2023-12-31",
                                "val": 1_000_000.0,
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


def _sample_submissions() -> dict:
    return {
        "cik": "1234567",
        "name": "Sample Corp",
        "sic": "7372",
        "sicDescription": "Services-Prepackaged Software",
        "tickers": ["SMPL"],
        "filings": {
            "recent": {
                "form": ["10-K"],
                "filingDate": ["2024-02-01"],
                "reportDate": ["2023-12-31"],
                "accessionNumber": ["0000000000-24-000001"],
                "primaryDocument": ["smpl-10k.htm"],
            }
        },
    }


def _write_fixture(fixture_dir: Path, ticker: str) -> None:
    snapshot = build_snapshot_from_live_json(
        submissions_json=_sample_submissions(),
        company_facts_json=_sample_company_facts(),
        data_mode="fixture",
        recorded_at=date(2026, 8, 26),
    )
    (fixture_dir / f"{ticker}.json").write_text(json.dumps(snapshot.model_dump(mode="json"), indent=2))


# --- FixtureIssuerProvider -------------------------------------------------


def test_fixture_provider_list_available_tickers(tmp_path) -> None:
    _write_fixture(tmp_path, "SMPL")
    _write_fixture(tmp_path, "OTHR")
    provider = FixtureIssuerProvider(tmp_path)
    assert provider.list_available_tickers() == ["OTHR", "SMPL"]


def test_fixture_provider_get_snapshot_returns_recorded_data(tmp_path) -> None:
    _write_fixture(tmp_path, "SMPL")
    provider = FixtureIssuerProvider(tmp_path)
    result = provider.get_snapshot("smpl")  # lowercase input should resolve
    assert result.snapshot.ticker == "SMPL"
    assert result.snapshot.company_name == "Sample Corp"
    assert result.provenance.source == "sec-edgar-recorded"
    assert result.provenance.data_mode == "fixture"
    assert result.provenance.is_stale is True
    assert result.provenance.observation_date == date(2023, 12, 31)


def test_fixture_provider_unknown_ticker_raises(tmp_path) -> None:
    _write_fixture(tmp_path, "SMPL")
    provider = FixtureIssuerProvider(tmp_path)
    with pytest.raises(ProviderError) as exc_info:
        provider.get_snapshot("UNKNOWN")
    assert exc_info.value.error_code == "unknown_ticker"


# --- PublicIssuerProvider ---------------------------------------------------


def _mock_client_returning(responses: list[MagicMock]):
    mock_client = MagicMock()
    mock_client.__enter__.return_value.get.side_effect = responses
    return mock_client


def _json_response(payload: dict, status_code: int = 200) -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = payload
    return response


def test_public_provider_resolves_ticker_and_fetches_snapshot() -> None:
    ticker_map = {"0": {"cik_str": 1234567, "ticker": "SMPL", "title": "Sample Corp"}}
    responses = [
        _json_response(ticker_map),
        _json_response(_sample_submissions()),
        _json_response(_sample_company_facts()),
    ]
    with patch("dashlets.issuer_provider.httpx.Client", return_value=_mock_client_returning(responses)):
        provider = PublicIssuerProvider()
        result = provider.get_snapshot("SMPL")

    assert result.snapshot.ticker == "SMPL"
    assert result.provenance.source == "sec-edgar-live"
    assert result.provenance.data_mode == "live"
    assert result.provenance.is_stale is False
    assert result.provenance.source_url is not None and result.provenance.source_url.startswith("https://")


def test_public_provider_caches_ticker_map_across_calls() -> None:
    ticker_map = {"0": {"cik_str": 1234567, "ticker": "SMPL", "title": "Sample Corp"}}
    responses = [
        _json_response(ticker_map),
        _json_response(_sample_submissions()),
        _json_response(_sample_company_facts()),
        # second get_snapshot call: no second ticker-map fetch, only submissions + facts
        _json_response(_sample_submissions()),
        _json_response(_sample_company_facts()),
    ]
    with patch("dashlets.issuer_provider.httpx.Client", return_value=_mock_client_returning(responses)) as mock_ctor:
        provider = PublicIssuerProvider()
        provider.get_snapshot("SMPL")
        provider.get_snapshot("SMPL")

    # 5 total client instantiations (one per _fetch_json call): 1 ticker map + 2*(submissions+facts)
    assert mock_ctor.call_count == 5


def test_public_provider_unknown_ticker_raises() -> None:
    ticker_map = {"0": {"cik_str": 1234567, "ticker": "SMPL", "title": "Sample Corp"}}
    with patch(
        "dashlets.issuer_provider.httpx.Client", return_value=_mock_client_returning([_json_response(ticker_map)])
    ):
        provider = PublicIssuerProvider()
        with pytest.raises(ProviderError) as exc_info:
            provider.get_snapshot("NOPE")
    assert exc_info.value.error_code == "ticker_not_found"


def test_public_provider_raises_on_timeout() -> None:
    mock_client = MagicMock()
    mock_client.__enter__.return_value.get.side_effect = httpx.TimeoutException("timed out")
    with patch("dashlets.issuer_provider.httpx.Client", return_value=mock_client):
        provider = PublicIssuerProvider()
        with pytest.raises(ProviderError) as exc_info:
            provider.get_snapshot("SMPL")
    assert exc_info.value.error_code == "sec_timeout"


def test_public_provider_raises_on_network_error() -> None:
    mock_client = MagicMock()
    mock_client.__enter__.return_value.get.side_effect = httpx.ConnectError("connection refused")
    with patch("dashlets.issuer_provider.httpx.Client", return_value=mock_client):
        provider = PublicIssuerProvider()
        with pytest.raises(ProviderError) as exc_info:
            provider.get_snapshot("SMPL")
    assert exc_info.value.error_code == "sec_network_error"


def test_public_provider_raises_on_non_200_status() -> None:
    responses = [_json_response({}, status_code=503)]
    with patch("dashlets.issuer_provider.httpx.Client", return_value=_mock_client_returning(responses)):
        provider = PublicIssuerProvider()
        with pytest.raises(ProviderError) as exc_info:
            provider.get_snapshot("SMPL")
    assert exc_info.value.error_code == "sec_fetch_error"


def test_public_provider_raises_missing_financial_data_when_no_periods() -> None:
    ticker_map = {"0": {"cik_str": 1234567, "ticker": "SMPL", "title": "Sample Corp"}}
    empty_facts = {"cik": 1234567, "facts": {"us-gaap": {}}}
    responses = [
        _json_response(ticker_map),
        _json_response(_sample_submissions()),
        _json_response(empty_facts),
    ]
    with patch("dashlets.issuer_provider.httpx.Client", return_value=_mock_client_returning(responses)):
        provider = PublicIssuerProvider()
        with pytest.raises(ProviderError) as exc_info:
            provider.get_snapshot("SMPL")
    assert exc_info.value.error_code == "missing_financial_data"


# --- resolve_provider --------------------------------------------------------


def test_resolve_provider_fixture_mode(tmp_path) -> None:
    provider = resolve_provider(IssuerDataMode.FIXTURE, tmp_path)
    assert isinstance(provider, FixtureIssuerProvider)


def test_resolve_provider_live_mode(tmp_path) -> None:
    provider = resolve_provider(IssuerDataMode.LIVE, tmp_path)
    assert isinstance(provider, PublicIssuerProvider)
