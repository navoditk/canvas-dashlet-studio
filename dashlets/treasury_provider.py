from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import Enum
from pathlib import Path
from typing import Protocol

import httpx

from treasury_fixture import CurvePoint, Provenance, TreasuryCurveResponse, load_fixture, to_curve_response

# Feed URL. Month is substituted at call time: YYYYMM format.
TREASURY_FEED_URL = (
    "https://home.treasury.gov/resource-center/data-chart-center/"
    "interest-rates/pages/xml"
    "?data=daily_treasury_yield_curve&field_tdr_date_value_month={month}"
)

# XML namespaces used in the Atom feed.
FEED_NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "d": "http://schemas.microsoft.com/ado/2007/08/dataservices",
    "m": "http://schemas.microsoft.com/ado/2007/08/dataservices/metadata",
}

# Ordered mapping: XML field name → canonical maturity label and maturity_years.
# Entries not needed for existing slopes are included for completeness.
MATURITY_MAP: list[tuple[str, str, float]] = [
    ("BC_1MONTH",  "1M",  1 / 12),
    ("BC_2MONTH",  "2M",  2 / 12),
    ("BC_3MONTH",  "3M",  0.25),
    ("BC_6MONTH",  "6M",  0.5),
    ("BC_1YEAR",   "1Y",  1.0),
    ("BC_2YEAR",   "2Y",  2.0),
    ("BC_3YEAR",   "3Y",  3.0),
    ("BC_5YEAR",   "5Y",  5.0),
    ("BC_7YEAR",   "7Y",  7.0),
    ("BC_10YEAR",  "10Y", 10.0),
    ("BC_20YEAR",  "20Y", 20.0),
    ("BC_30YEAR",  "30Y", 30.0),
]


class TreasuryDataMode(str, Enum):
    FIXTURE = "fixture"
    EOD = "eod"


class ProviderError(Exception):
    """Raised by providers for controlled, user-visible failures."""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class TreasuryProvider(Protocol):
    data_mode: str  # "fixture" or "live"

    def get_curve(self, observation_date: str) -> TreasuryCurveResponse:
        """Return a TreasuryCurveResponse for the given YYYY-MM-DD date string.
        Raise ProviderError for any controlled failure.
        """
        ...


class FixtureTreasuryProvider:
    data_mode = "fixture"

    def __init__(self, fixture_dir: Path) -> None:
        self._fixture_dir = fixture_dir

    def get_curve(self, observation_date: str) -> TreasuryCurveResponse:
        _parse_observation_date(observation_date)  # validate format before filesystem access
        fixture_path = self._fixture_dir / f"curve_{observation_date}.json"
        if not fixture_path.exists():
            raise ProviderError(
                "fixture_not_found",
                f"No fixture found for date: {observation_date}",
            )
        fixture = load_fixture(fixture_path)
        available = sorted(p.stem.removeprefix("curve_") for p in self._fixture_dir.glob("curve_*.json"))
        latest = available[-1] if available else observation_date
        is_stale = observation_date != latest
        return to_curve_response(fixture, is_stale=is_stale)


@dataclass
class ParsedCurveDay:
    observation_date: date
    # Each point: (xml_field, maturity_label, maturity_years, yield_percent)
    points: list[tuple[str, str, float, float]]


def parse_treasury_feed(xml_text: str, source_url: str) -> list[ParsedCurveDay]:
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        raise ProviderError("feed_parse_error", f"Invalid XML from Treasury feed: {exc}") from exc

    days: list[ParsedCurveDay] = []

    for entry in root.findall("atom:entry", FEED_NS):
        props = entry.find(".//m:properties", FEED_NS)
        if props is None:
            continue

        raw_date = props.findtext("d:NEW_DATE", namespaces=FEED_NS)
        if not raw_date:
            continue

        try:
            observation_date = date.fromisoformat(raw_date[:10])
        except ValueError as exc:
            raise ProviderError("feed_date_error", f"Unparseable date in feed: {raw_date!r}") from exc

        points: list[tuple[str, str, float, float]] = []

        for xml_field, label, maturity_years in MATURITY_MAP:
            el = props.find(f"d:{xml_field}", FEED_NS)
            if el is None:
                continue
            # m:null="true" means the value was not published that day
            if el.get(f"{{{FEED_NS['m']}}}null", "false").lower() == "true":
                continue
            if el.text is None:
                continue
            try:
                yield_val = float(el.text)
            except ValueError:
                continue
            points.append((xml_field, label, maturity_years, yield_val))

        if points:
            days.append(ParsedCurveDay(observation_date=observation_date, points=points))

    return days


def _parse_observation_date(observation_date_str: str) -> date:
    # strptime enforces strict YYYY-MM-DD; fromisoformat accepts YYYYMMDD in Python 3.11+
    try:
        return datetime.strptime(observation_date_str, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ProviderError(
            "invalid_date",
            f"Invalid observation date: {observation_date_str!r}. Expected YYYY-MM-DD.",
        ) from exc


def fetch_treasury_feed(observation_date_str: str) -> tuple[str, str]:
    """Fetch the monthly Treasury XML feed that contains observation_date_str.
    Returns (xml_text, source_url). Raises ProviderError on any failure.
    """
    obs_date = _parse_observation_date(observation_date_str)
    month = obs_date.strftime("%Y%m")
    url = TREASURY_FEED_URL.format(month=month)

    timeout = httpx.Timeout(connect=5.0, read=15.0, write=5.0, pool=5.0)

    try:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(url)
    except httpx.TimeoutException as exc:
        raise ProviderError("feed_timeout", f"Treasury feed timed out: {exc}") from exc
    except httpx.RequestError as exc:
        raise ProviderError("feed_network_error", f"Treasury feed network error: {exc}") from exc

    if response.status_code != 200:
        raise ProviderError(
            "feed_http_error",
            f"Treasury feed returned HTTP {response.status_code}",
        )

    return response.text, url


def normalize_to_curve_response(
    days: list[ParsedCurveDay],
    observation_date_str: str,
    source_url: str,
    retrieved_at: datetime,
) -> TreasuryCurveResponse:
    obs_date = _parse_observation_date(observation_date_str)

    matched = next((d for d in days if d.observation_date == obs_date), None)
    if matched is None:
        raise ProviderError(
            "date_not_in_feed",
            f"No data for {observation_date_str} in the Treasury feed "
            f"(feed may not yet include this date or it is a non-business day).",
        )

    points = [
        CurvePoint(
            maturity_label=label,
            maturity_years=maturity_years,
            yield_percent=yield_percent,
        )
        for _xml_field, label, maturity_years, yield_percent in matched.points
    ]

    provenance = Provenance(
        source="treasury-gov",
        data_mode="eod",
        observation_date=obs_date,
        retrieved_at=retrieved_at,
        source_url=source_url,
        is_stale=False,
    )

    return TreasuryCurveResponse(points=points, provenance=provenance)


class PublicTreasuryProvider:
    data_mode = "eod"

    def get_curve(self, observation_date: str) -> TreasuryCurveResponse:
        xml_text, source_url = fetch_treasury_feed(observation_date)
        days = parse_treasury_feed(xml_text, source_url)
        return normalize_to_curve_response(
            days,
            observation_date,
            source_url,
            retrieved_at=datetime.now(UTC),
        )


def make_provider(
    data_mode: str, fixture_dir: Path
) -> FixtureTreasuryProvider | PublicTreasuryProvider:
    if data_mode == "fixture":
        return FixtureTreasuryProvider(fixture_dir)
    if data_mode == "eod":
        return PublicTreasuryProvider()
    raise ValueError(f"Unknown data_mode: {data_mode!r}. Expected 'fixture' or 'eod'.")


def resolve_provider(
    data_mode: TreasuryDataMode, fixture_dir: Path
) -> FixtureTreasuryProvider | PublicTreasuryProvider:
    registry: dict[TreasuryDataMode, FixtureTreasuryProvider | PublicTreasuryProvider] = {
        TreasuryDataMode.FIXTURE: FixtureTreasuryProvider(fixture_dir),
        TreasuryDataMode.EOD: PublicTreasuryProvider(),
    }
    return registry[data_mode]
