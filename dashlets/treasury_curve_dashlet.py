from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from treasury_fixture import (
    CurveComparisonPoint,
    CurveSlope,
    Provenance,
    TreasuryCurveResponse,
    compare_curves,
    compute_curve_slopes,
    load_fixture,
    to_curve_response,
)

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "treasury"
DATE_EXAMPLES = ["2026-08-19"]
CANONICAL_SLOPE_NAMES = ["2s10s", "3m10y", "5s30s"]

OBSERVATION_DATE_DESCRIPTION = (
    "Observation date in YYYY-MM-DD format. Omit to use the latest available fixture date."
)
BASE_DATE_DESCRIPTION = "Required base observation date in YYYY-MM-DD format."
COMPARE_DATE_DESCRIPTION = "Required comparison observation date in YYYY-MM-DD format."


class TreasuryCurveSlopesResponse(BaseModel):
    observation_date: date
    slopes: list[CurveSlope]
    provenance: Provenance


class TreasuryCurveComparisonResponse(BaseModel):
    base_observation_date: date
    compare_observation_date: date
    points: list[CurveComparisonPoint]
    provenance: Provenance


class TreasuryCurveViewResponse(BaseModel):
    observation_date: date
    curve: TreasuryCurveResponse
    slopes: list[CurveSlope]


class TreasuryFixtureDatesResponse(BaseModel):
    available_dates: list[str]


class TreasuryDashletMetadataResponse(BaseModel):
    title: str
    version: str
    data_mode: str
    default_curve_date: str
    canonical_slopes: list[str]
    supported_endpoints: list[str]
    available_fixture_dates: list[str]


class DashletErrorDetail(BaseModel):
    error_code: str
    message: str


class DashletErrorResponse(BaseModel):
    detail: DashletErrorDetail


app = FastAPI(title="Treasury Curve Dashlet", version="0.1.0")


def _optional_date_query(description: str):
    return Query(
        default=None,
        description=description,
        examples=DATE_EXAMPLES,
    )


def _required_date_query(description: str):
    return Query(
        ...,
        description=description,
        examples=DATE_EXAMPLES,
    )


def _fixture_path_for_date(observation_date: str) -> Path:
    return FIXTURE_DIR / f"curve_{observation_date}.json"


def _parse_date(observation_date: str) -> date:
    try:
        return datetime.strptime(observation_date, "%Y-%m-%d").replace(tzinfo=UTC).date()
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "invalid_date",
                "message": f"Invalid date: {observation_date}. Expected YYYY-MM-DD",
            },
        ) from exc


def _list_available_fixture_dates() -> list[str]:
    dates: list[str] = []
    for fixture_path in FIXTURE_DIR.glob("curve_*.json"):
        date_str = fixture_path.stem.removeprefix("curve_")
        _parse_date(date_str)
        dates.append(date_str)
    return sorted(set(dates))


def _latest_available_date_str() -> str:
    available = _list_available_fixture_dates()
    if not available:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "no_fixtures_available",
                "message": "No Treasury fixtures are available.",
            },
        )
    return max(available)


def _resolve_observation_date_str(observation_date: str | None) -> str:
    if observation_date is not None:
        return observation_date
    return _latest_available_date_str()


def _load_fixture_for_date(observation_date: str):
    _parse_date(observation_date)
    fixture_path = _fixture_path_for_date(observation_date)
    if not fixture_path.exists():
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "fixture_not_found",
                "message": f"No fixture found for date: {observation_date}",
            },
        )
    return load_fixture(fixture_path)


def _curve_response_with_freshness(fixture) -> TreasuryCurveResponse:
    latest = _latest_available_date_str()
    is_stale = fixture.observation_date.isoformat() != latest
    return to_curve_response(fixture, is_stale=is_stale)


def _compute_slopes_or_422(points) -> list[CurveSlope]:
    try:
        return compute_curve_slopes(points)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "missing_slope_maturity", "message": str(exc)},
        ) from exc


def _compare_curves_or_422(base_points, compare_points):
    try:
        return compare_curves(base_points, compare_points)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "maturity_mismatch", "message": str(exc)},
        ) from exc


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """<!doctype html>
<html>
<head><meta charset=\"utf-8\" /><title>Treasury Curve Dashlet</title></head>
<body>
  <h1>Treasury Curve Dashlet</h1>
  <p>Deterministic fixture-backed endpoints are available under <code>/api/treasury/*</code>.</p>
</body>
</html>
"""


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ready"}


@app.get(
    "/metadata",
    operation_id="get_treasury_dashlet_metadata",
    summary="Get Treasury Dashlet Metadata",
    description="Return deterministic metadata describing data mode, supported routes, canonical slopes, and available fixture dates.",
    response_description="Typed Treasury dashlet metadata.",
    response_model=TreasuryDashletMetadataResponse,
)
def metadata() -> TreasuryDashletMetadataResponse:
    return TreasuryDashletMetadataResponse(
        title=app.title,
        version=app.version,
        data_mode="fixture",
        default_curve_date=_latest_available_date_str(),
        canonical_slopes=CANONICAL_SLOPE_NAMES,
        supported_endpoints=[
            "/api/treasury/fixture-dates",
            "/api/treasury/view",
            "/api/treasury/curve",
            "/api/treasury/slopes",
            "/api/treasury/compare",
        ],
        available_fixture_dates=_list_available_fixture_dates(),
    )


@app.get(
    "/api/treasury/fixture-dates",
    operation_id="list_treasury_fixture_dates",
    summary="List Treasury Fixture Dates",
    description="List available deterministic Treasury fixture observation dates for discovery and UI selection.",
    response_description="Sorted list of available fixture dates.",
    response_model=TreasuryFixtureDatesResponse,
)
def list_treasury_fixture_dates() -> TreasuryFixtureDatesResponse:
    return TreasuryFixtureDatesResponse(available_dates=_list_available_fixture_dates())


@app.get(
    "/api/treasury/view",
    operation_id="get_treasury_curve_view",
    summary="Get Treasury Curve View",
    description="Return deterministic curve points and canonical slopes together for one observation date.",
    response_description="Typed Treasury curve, canonical slopes, and shared provenance.",
    responses={
        404: {"model": DashletErrorResponse, "description": "Fixture not found for the requested date."},
        422: {"model": DashletErrorResponse, "description": "Invalid date format."},
    },
    response_model=TreasuryCurveViewResponse,
)
def get_treasury_curve_view(
    date: str | None = _optional_date_query(description=OBSERVATION_DATE_DESCRIPTION),
) -> TreasuryCurveViewResponse:
    resolved_date = _resolve_observation_date_str(date)
    fixture = _load_fixture_for_date(resolved_date)
    curve_response = _curve_response_with_freshness(fixture)
    slopes = _compute_slopes_or_422(curve_response.points)
    return TreasuryCurveViewResponse(
        observation_date=fixture.observation_date,
        curve=curve_response,
        slopes=slopes,
    )


@app.get(
    "/api/treasury/curve",
    operation_id="get_treasury_curve",
    tags=["agent-tool"],
    summary="Get Treasury Curve",
    description="Return a deterministic fixture-backed Treasury curve for a single observation date.",
    response_description="Typed Treasury curve points and provenance.",
    responses={
        404: {"model": DashletErrorResponse, "description": "Fixture not found for the requested date."},
        422: {"model": DashletErrorResponse, "description": "Invalid date format."},
    },
    response_model=TreasuryCurveResponse,
)
def get_treasury_curve(
    date: str | None = _optional_date_query(description=OBSERVATION_DATE_DESCRIPTION),
) -> TreasuryCurveResponse:
    resolved_date = _resolve_observation_date_str(date)
    fixture = _load_fixture_for_date(resolved_date)
    return _curve_response_with_freshness(fixture)


@app.get(
    "/api/treasury/slopes",
    operation_id="get_treasury_curve_slopes",
    tags=["agent-tool"],
    summary="Get Canonical Curve Slopes",
    description="Return deterministic canonical slope pairs (2s10s, 3m10y and 5s30s) for one observation date.",
    response_description="Canonical slope metrics with provenance.",
    responses={
        404: {"model": DashletErrorResponse, "description": "Fixture not found for the requested date."},
        422: {
            "model": DashletErrorResponse,
            "description": "Invalid date format or a required slope maturity is missing from the fixture.",
        },
    },
    response_model=TreasuryCurveSlopesResponse,
)
def get_curve_slopes(
    date: str | None = _optional_date_query(description=OBSERVATION_DATE_DESCRIPTION),
) -> TreasuryCurveSlopesResponse:
    resolved_date = _resolve_observation_date_str(date)
    fixture = _load_fixture_for_date(resolved_date)
    curve_response = _curve_response_with_freshness(fixture)
    slopes = _compute_slopes_or_422(curve_response.points)
    return TreasuryCurveSlopesResponse(
        observation_date=fixture.observation_date,
        slopes=slopes,
        provenance=curve_response.provenance,
    )


@app.get(
    "/api/treasury/compare",
    operation_id="compare_treasury_curves",
    tags=["agent-tool"],
    summary="Compare Treasury Curves",
    description="Compare two deterministic fixture-backed Treasury curves and return maturity-level basis-point deltas.",
    response_description="Per-maturity curve comparison points with provenance.",
    responses={
        404: {"model": DashletErrorResponse, "description": "Fixture not found for at least one requested date."},
        422: {
            "model": DashletErrorResponse,
            "description": "Invalid date format or the two curves do not share the same maturities.",
        },
    },
    response_model=TreasuryCurveComparisonResponse,
)
def compare_treasury_curves(
    base_date: str = _required_date_query(description=BASE_DATE_DESCRIPTION),
    compare_date: str = _required_date_query(description=COMPARE_DATE_DESCRIPTION),
) -> TreasuryCurveComparisonResponse:
    base_fixture = _load_fixture_for_date(base_date)
    compare_fixture = _load_fixture_for_date(compare_date)

    base_curve = _curve_response_with_freshness(base_fixture)
    compare_curve = _curve_response_with_freshness(compare_fixture)
    comparison_points = _compare_curves_or_422(base_curve.points, compare_curve.points)

    return TreasuryCurveComparisonResponse(
        base_observation_date=base_fixture.observation_date,
        compare_observation_date=compare_fixture.observation_date,
        points=comparison_points,
        provenance=Provenance(
            source="synthetic-fixture",
            data_mode=base_fixture.fixture_meta.data_mode,
            observation_date=base_fixture.observation_date,
            retrieved_at=datetime.now(UTC),
            is_stale=base_fixture.observation_date.isoformat() != _latest_available_date_str(),
        ),
    )