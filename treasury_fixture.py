from __future__ import annotations

import json
from datetime import UTC, date, datetime
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

# Fixed canonical maturity order (not lexicographic). Ordering is looked up by
# label so that a bad or inconsistent `maturity_years` value in a fixture
# cannot silently reorder the curve.
CANONICAL_MATURITY_ORDER: list[str] = [
    "1M", "1.5M", "2M", "3M", "4M", "6M",
    "1Y", "2Y", "3Y", "5Y", "7Y", "10Y", "20Y", "30Y",
]


class FixtureMeta(BaseModel):
    note:str
    data_mode:str

class Provenance(BaseModel):
    source: str
    source_url: str | None = None
    observation_date: date
    retrieved_at: datetime
    data_mode: str
    is_stale: bool

class CurvePoint(BaseModel):
    maturity_label:str
    maturity_years:float
    yield_percent:float

class TreasuryCurveResponse(BaseModel):
    points : list[CurvePoint]
    provenance: Provenance


class CurveSlope(BaseModel):
    name: str
    short_label: str
    long_label: str
    slope_bps: float


class CurveComparisonPoint(BaseModel):
    maturity_label: str
    maturity_years: float
    base_yield_percent: float
    compare_yield_percent: float
    delta_bps: float

class TreasuryPoint(BaseModel):
    maturity_label:str
    maturity_years:float = Field(..., gt=0)
    yield_percent:float

class TreasuryCurveFixture(BaseModel):
    observation_date: date
    curve:list[TreasuryPoint]
    fixture_meta: FixtureMeta

    @field_validator("curve")
    @classmethod
    def _reject_duplicate_maturities(cls, points: list[TreasuryPoint]) -> list[TreasuryPoint]:
        labels = [point.maturity_label for point in points]
        duplicates = sorted({label for label in labels if labels.count(label) > 1})
        if duplicates:
            raise ValueError(f"Duplicate maturity labels found in fixture: {duplicates}")
        return points


def _canonical_sort_key(point: TreasuryPoint) -> tuple[int, str]:
    try:
        index = CANONICAL_MATURITY_ORDER.index(point.maturity_label)
    except ValueError:
        # Unknown labels are not silently misordered; they sort after all
        # known canonical maturities, in stable label order.
        index = len(CANONICAL_MATURITY_ORDER)
    return (index, point.maturity_label)


def sort_curve_points(points:list[TreasuryPoint]) -> list[TreasuryPoint]:
    return sorted(points, key=_canonical_sort_key)

def is_canonical_curve(points: list[TreasuryPoint]) -> bool:
    keys = [_canonical_sort_key(point) for point in points]
    return keys == sorted(keys)

def load_fixture(path: str | Path) -> TreasuryCurveFixture:
    raw_text = Path(path).read_text()
    payload = json.loads(raw_text)
    fixture = TreasuryCurveFixture.model_validate(payload)
    fixture.curve = sort_curve_points(fixture.curve)
    return fixture

def map_point(point: TreasuryPoint) -> CurvePoint:
    return CurvePoint(
        maturity_label=point.maturity_label,
        maturity_years=point.maturity_years,
        yield_percent=point.yield_percent,
    )

def to_curve_response(
    fixture: TreasuryCurveFixture,
    *,
    is_stale: bool = False,
    source_url: str | None = None,
) -> TreasuryCurveResponse:
    sorted_points = sort_curve_points(fixture.curve)
    points = [map_point(point) for point in sorted_points]
    provenance = Provenance(
        source="synthetic-fixture",
        source_url=source_url,
        data_mode=fixture.fixture_meta.data_mode,
        observation_date=fixture.observation_date,
        retrieved_at=datetime.now(UTC),
        is_stale=is_stale,
    )
    return TreasuryCurveResponse(points=points, provenance=provenance)


def _yield_by_label(points: list[CurvePoint]) -> dict[str, float]:
    return {point.maturity_label: point.yield_percent for point in points}


def _slope_bps(yield_by_label: dict[str, float], short_label: str, long_label: str) -> float:
    if short_label not in yield_by_label or long_label not in yield_by_label:
        raise ValueError(f"Missing maturity required for slope: {short_label} or {long_label}")
    return (yield_by_label[long_label] - yield_by_label[short_label]) * 100.0


def compute_slopes_for_pairs(
    points: list[CurvePoint],
    pairs: list[tuple[str, str, str]],
) -> list[CurveSlope]:
    yield_lookup = _yield_by_label(points)
    return [
        CurveSlope(
            name=name,
            short_label=short_label,
            long_label=long_label,
            slope_bps=_slope_bps(yield_lookup, short_label, long_label),
        )
        for name, short_label, long_label in pairs
    ]


def compute_curve_slopes(points: list[CurvePoint]) -> list[CurveSlope]:
    canonical_pairs: list[tuple[str, str, str]] = [
        ("2s10s", "2Y", "10Y"),
        ("3m10y", "3M", "10Y"),
        ("5s30s", "5Y", "30Y"),
    ]
    return compute_slopes_for_pairs(points, canonical_pairs)


def _point_by_label(points: list[CurvePoint]) -> dict[str, CurvePoint]:
    return {point.maturity_label: point for point in points}


def compare_curves(
    base_points: list[CurvePoint], compare_points: list[CurvePoint]
) -> list[CurveComparisonPoint]:
    base_sorted = sorted(base_points, key=_canonical_sort_key)
    compare_lookup = _point_by_label(compare_points)

    base_labels = {point.maturity_label for point in base_points}
    compare_labels = {point.maturity_label for point in compare_points}
    if base_labels != compare_labels:
        raise ValueError("Maturity labels must match between base and comparison curves")

    compared: list[CurveComparisonPoint] = []
    for base_point in base_sorted:
        compare_point = compare_lookup[base_point.maturity_label]
        compared.append(
            CurveComparisonPoint(
                maturity_label=base_point.maturity_label,
                maturity_years=base_point.maturity_years,
                base_yield_percent=base_point.yield_percent,
                compare_yield_percent=compare_point.yield_percent,
                delta_bps=(compare_point.yield_percent - base_point.yield_percent) * 100.0,
            )
        )
    return compared