from __future__ import annotations

import sys
from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashlets.treasury_provider import (
    FixtureTreasuryProvider,
    ParsedCurveDay,
    ProviderError,
    fetch_treasury_feed,
    normalize_to_curve_response,
    parse_treasury_feed,
)

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "treasury"

SAMPLE_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"
      xmlns:d="http://schemas.microsoft.com/ado/2007/08/dataservices"
      xmlns:m="http://schemas.microsoft.com/ado/2007/08/dataservices/metadata">
  <entry>
    <content type="application/xml">
      <m:properties>
        <d:NEW_DATE>2026-08-19T00:00:00</d:NEW_DATE>
        <d:BC_3MONTH m:type="Edm.Double">4.90</d:BC_3MONTH>
        <d:BC_2YEAR  m:type="Edm.Double">4.20</d:BC_2YEAR>
        <d:BC_5YEAR  m:type="Edm.Double">4.00</d:BC_5YEAR>
        <d:BC_10YEAR m:type="Edm.Double">4.18</d:BC_10YEAR>
        <d:BC_30YEAR m:type="Edm.Double">4.40</d:BC_30YEAR>
        <d:BC_20YEAR m:null="true" />
      </m:properties>
    </content>
  </entry>
</feed>"""


def test_parse_treasury_feed_extracts_expected_points() -> None:
    days = parse_treasury_feed(SAMPLE_XML, "https://example.com/feed")
    assert len(days) == 1
    day = days[0]
    assert day.observation_date == date(2026, 8, 19)
    labels = [p[1] for p in day.points]
    assert "3M" in labels
    assert "2Y" in labels
    assert "5Y" in labels
    assert "10Y" in labels
    assert "30Y" in labels
    assert len(labels) == 5
    yields = {p[1]: p[3] for p in day.points}
    assert yields["10Y"] == 4.18


def test_parse_treasury_feed_raises_on_invalid_xml() -> None:
    with pytest.raises(ProviderError) as exc_info:
        parse_treasury_feed("<invalid>", "https://example.com")
    assert exc_info.value.error_code == "feed_parse_error"


def test_parse_treasury_feed_skips_null_fields() -> None:
    days = parse_treasury_feed(SAMPLE_XML, "https://example.com/feed")
    labels = [p[1] for p in days[0].points]
    assert "20Y" not in labels


def test_normalize_to_curve_response_maps_provenance() -> None:
    retrieved = datetime(2026, 8, 21, 12, 0, 0, tzinfo=UTC)
    days = [
        ParsedCurveDay(
            observation_date=date(2026, 8, 19),
            points=[("BC_10YEAR", "10Y", 10.0, 4.18)],
        )
    ]
    resp = normalize_to_curve_response(days, "2026-08-19", "https://example.com/feed", retrieved)
    assert resp.provenance.source == "treasury-gov"
    assert resp.provenance.data_mode == "eod"
    assert resp.provenance.is_stale is False
    assert resp.provenance.source_url == "https://example.com/feed"
    assert resp.provenance.retrieved_at == retrieved


def test_normalize_to_curve_response_raises_when_date_not_in_feed() -> None:
    retrieved = datetime(2026, 8, 21, 12, 0, 0, tzinfo=UTC)
    days = [
        ParsedCurveDay(
            observation_date=date(2026, 8, 19),
            points=[("BC_10YEAR", "10Y", 10.0, 4.18)],
        )
    ]
    with pytest.raises(ProviderError) as exc_info:
        normalize_to_curve_response(days, "2026-08-18", "https://example.com/feed", retrieved)
    assert exc_info.value.error_code == "date_not_in_feed"


def test_fetch_treasury_feed_returns_xml_and_url_on_200() -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "<feed/>"
    with patch("dashlets.treasury_provider.httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.get.return_value = mock_resp
        xml_text, url = fetch_treasury_feed("2026-08-19")
    assert xml_text == "<feed/>"
    assert "202608" in url


def test_fetch_treasury_feed_raises_on_http_error() -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 503
    with patch("dashlets.treasury_provider.httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.get.return_value = mock_resp
        with pytest.raises(ProviderError) as exc_info:
            fetch_treasury_feed("2026-08-19")
    assert exc_info.value.error_code == "feed_http_error"
    assert "503" in exc_info.value.message


def test_fetch_treasury_feed_raises_on_timeout() -> None:
    with patch("dashlets.treasury_provider.httpx.Client") as MockClient:
        MockClient.return_value.__enter__.return_value.get.side_effect = httpx.TimeoutException("timed out")
        with pytest.raises(ProviderError) as exc_info:
            fetch_treasury_feed("2026-08-19")
    assert exc_info.value.error_code == "feed_timeout"


def test_fixture_provider_returns_curve_for_known_date() -> None:
    provider = FixtureTreasuryProvider(FIXTURE_DIR)
    resp = provider.get_curve("2026-08-19")
    assert resp.provenance.data_mode == "fixture"
    assert resp.provenance.is_stale is False
    labels = [p.maturity_label for p in resp.points]
    assert "10Y" in labels


def test_fixture_provider_raises_for_missing_date() -> None:
    provider = FixtureTreasuryProvider(FIXTURE_DIR)
    with pytest.raises(ProviderError) as exc_info:
        provider.get_curve("2099-01-01")
    assert exc_info.value.error_code == "fixture_not_found"


def test_fixture_provider_provenance_fields_are_complete() -> None:
    provider = FixtureTreasuryProvider(FIXTURE_DIR)
    resp = provider.get_curve("2026-08-19")
    p = resp.provenance
    assert p.source == "synthetic-fixture"
    assert p.data_mode == "fixture"
    assert p.observation_date == date(2026, 8, 19)
    assert p.retrieved_at is not None and p.retrieved_at.tzinfo is not None
    assert p.source_url is None
    assert p.is_stale is False


def test_fixture_provider_older_date_is_marked_stale() -> None:
    provider = FixtureTreasuryProvider(FIXTURE_DIR)
    resp = provider.get_curve("2026-08-18")
    assert resp.provenance.is_stale is True


def test_live_provider_provenance_fields_are_complete() -> None:
    retrieved = datetime(2026, 8, 21, 9, 0, 0, tzinfo=UTC)
    source_url = "https://home.treasury.gov/feed?month=202608"
    days = [
        ParsedCurveDay(
            observation_date=date(2026, 8, 19),
            points=[("BC_10YEAR", "10Y", 10.0, 4.18)],
        )
    ]
    resp = normalize_to_curve_response(days, "2026-08-19", source_url, retrieved)
    p = resp.provenance
    assert p.source == "treasury-gov"
    assert p.data_mode == "eod"
    assert p.observation_date == date(2026, 8, 19)
    assert p.retrieved_at is not None and p.retrieved_at.tzinfo is not None
    assert p.source_url is not None and p.source_url.startswith("https://")
    assert p.is_stale is False


def test_live_provider_retrieved_at_is_utc() -> None:
    retrieved = datetime(2026, 8, 21, 9, 0, 0, tzinfo=UTC)
    days = [
        ParsedCurveDay(
            observation_date=date(2026, 8, 19),
            points=[("BC_10YEAR", "10Y", 10.0, 4.18)],
        )
    ]
    resp = normalize_to_curve_response(days, "2026-08-19", "https://example.com", retrieved)
    assert resp.provenance.retrieved_at.tzinfo is UTC


def test_live_provider_observation_date_matches_requested_date() -> None:
    retrieved = datetime(2026, 8, 21, 9, 0, 0, tzinfo=UTC)
    days = [
        ParsedCurveDay(
            observation_date=date(2026, 8, 18),
            points=[("BC_10YEAR", "10Y", 10.0, 4.12)],
        ),
        ParsedCurveDay(
            observation_date=date(2026, 8, 19),
            points=[("BC_10YEAR", "10Y", 10.0, 4.18)],
        ),
    ]
    resp = normalize_to_curve_response(days, "2026-08-18", "https://example.com", retrieved)
    assert resp.provenance.observation_date == date(2026, 8, 18)
    assert resp.points[0].yield_percent == 4.12
