import sys
from datetime import UTC, date
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from treasury_fixture import (
    CurvePoint,
    compare_curves,
    compute_curve_slopes,
    compute_slopes_for_pairs,
    is_canonical_curve,
    load_fixture,
    to_curve_response,
)


def test_fixture_loads_and_has_expected_date() -> None:
    fixture = load_fixture("fixtures/treasury/curve_2026-08-19.json")
    assert fixture.observation_date == date(2026, 8, 19)
    assert len(fixture.curve) > 0


def test_curve_is_sorted_in_canonical_maturity_order() -> None:
    fixture = load_fixture("fixtures/treasury/curve_2026-08-19.json")
    years = [point.maturity_years for point in fixture.curve]
    assert years == sorted(years)
    assert is_canonical_curve(fixture.curve) is True


def test_invalid_fixture_rejected(tmp_path) -> None:
    bad_file = tmp_path / "bad.json"
    bad_file.write_text(
        """
        {
          "observation_date": "2026-08-19",
          "curve": [
            {"maturity_label": "bad", "maturity_years": -1, "yield_percent": 0.0}
          ]
        }
        """
    )

    with pytest.raises(ValidationError):
        load_fixture(bad_file)


def test_duplicate_maturity_label_rejected(tmp_path) -> None:
    bad_file = tmp_path / "duplicate.json"
    bad_file.write_text(
        """
        {
          "fixture_meta": {"note": "Deterministic synthetic test fixture. Not live market data.", "data_mode": "fixture"},
          "observation_date": "2026-08-19",
          "curve": [
            {"maturity_label": "2Y", "maturity_years": 2.0, "yield_percent": 4.20},
            {"maturity_label": "2Y", "maturity_years": 2.0, "yield_percent": 4.25}
          ]
        }
        """
    )

    with pytest.raises(ValidationError, match="Duplicate maturity labels"):
        load_fixture(bad_file)


def test_to_curve_response_includes_typed_provenance() -> None:
    fixture = load_fixture("fixtures/treasury/curve_2026-08-19.json")
    response = to_curve_response(fixture)
    assert response.provenance.source == "synthetic-fixture"
    assert response.provenance.data_mode == fixture.fixture_meta.data_mode
    assert response.provenance.observation_date == fixture.observation_date


def test_to_curve_response_provenance_is_timezone_aware_and_not_stale_by_default() -> None:
    fixture = load_fixture("fixtures/treasury/curve_2026-08-19.json")
    response = to_curve_response(fixture)
    assert response.provenance.retrieved_at.tzinfo is not None
    assert response.provenance.retrieved_at.tzinfo.utcoffset(response.provenance.retrieved_at) == UTC.utcoffset(None)
    assert response.provenance.is_stale is False
    assert response.provenance.source_url is None


def test_to_curve_response_keeps_canonical_order() -> None:
    fixture = load_fixture("fixtures/treasury/curve_2026-08-19.json")
    response = to_curve_response(fixture)
    years = [point.maturity_years for point in response.points]
    assert years == sorted(years)


def test_to_curve_response_preserves_point_count() -> None:
    fixture = load_fixture("fixtures/treasury/curve_2026-08-19.json")
    response = to_curve_response(fixture)
    assert len(response.points) == len(fixture.curve)


def test_to_curve_response_is_deterministic_apart_from_retrieval_timestamp() -> None:
    fixture = load_fixture("fixtures/treasury/curve_2026-08-19.json")
    response1 = to_curve_response(fixture)
    response2 = to_curve_response(fixture)
    assert response1.points == response2.points
    assert response1.provenance.model_dump(exclude={"retrieved_at"}) == (
        response2.provenance.model_dump(exclude={"retrieved_at"})
    )


def test_compute_curve_slopes_deterministic_values() -> None:
    points = [
        CurvePoint(maturity_label="3M", maturity_years=0.25, yield_percent=4.95),
        CurvePoint(maturity_label="2Y", maturity_years=2.0, yield_percent=3.00),
        CurvePoint(maturity_label="5Y", maturity_years=5.0, yield_percent=3.50),
        CurvePoint(maturity_label="10Y", maturity_years=10.0, yield_percent=4.25),
        CurvePoint(maturity_label="30Y", maturity_years=30.0, yield_percent=4.10),
    ]

    slopes = compute_curve_slopes(points)

    assert slopes[0].name == "2s10s"
    assert slopes[0].slope_bps == pytest.approx(125.0)
    assert slopes[1].name == "3m10y"
    assert slopes[1].slope_bps == pytest.approx(-70.0)
    assert slopes[2].name == "5s30s"
    assert slopes[2].slope_bps == pytest.approx(60.0)


def test_compute_curve_slopes_missing_maturity_raises() -> None:
    points = [
        CurvePoint(maturity_label="2Y", maturity_years=2.0, yield_percent=3.00),
        CurvePoint(maturity_label="5Y", maturity_years=5.0, yield_percent=3.50),
        CurvePoint(maturity_label="10Y", maturity_years=10.0, yield_percent=4.25),
    ]

    with pytest.raises(ValueError, match="Missing maturity required for slope"):
        compute_curve_slopes(points)


def test_compute_curve_slopes_stable_output_order() -> None:
    points = [
        CurvePoint(maturity_label="30Y", maturity_years=30.0, yield_percent=4.10),
        CurvePoint(maturity_label="10Y", maturity_years=10.0, yield_percent=4.25),
        CurvePoint(maturity_label="5Y", maturity_years=5.0, yield_percent=3.50),
        CurvePoint(maturity_label="3M", maturity_years=0.25, yield_percent=4.95),
        CurvePoint(maturity_label="2Y", maturity_years=2.0, yield_percent=3.00),
    ]

    slopes = compute_curve_slopes(points)

    assert [slope.name for slope in slopes] == ["2s10s", "3m10y", "5s30s"]


def test_compute_slopes_for_pairs_supports_parameterized_pairs() -> None:
    points = [
        CurvePoint(maturity_label="2Y", maturity_years=2.0, yield_percent=3.00),
        CurvePoint(maturity_label="5Y", maturity_years=5.0, yield_percent=3.50),
        CurvePoint(maturity_label="10Y", maturity_years=10.0, yield_percent=4.25),
        CurvePoint(maturity_label="30Y", maturity_years=30.0, yield_percent=4.10),
    ]

    slopes = compute_slopes_for_pairs(points, [("2s5s", "2Y", "5Y")])

    assert len(slopes) == 1
    assert slopes[0].name == "2s5s"
    assert slopes[0].short_label == "2Y"
    assert slopes[0].long_label == "5Y"
    assert slopes[0].slope_bps == pytest.approx(50.0)


def test_compute_slopes_for_pairs_missing_maturity_raises() -> None:
    points = [
        CurvePoint(maturity_label="2Y", maturity_years=2.0, yield_percent=3.00),
        CurvePoint(maturity_label="5Y", maturity_years=5.0, yield_percent=3.50),
    ]

    with pytest.raises(ValueError, match="Missing maturity required for slope"):
        compute_slopes_for_pairs(points, [("2s10s", "2Y", "10Y")])


def test_compare_curves_deterministic_deltas() -> None:
    base_points = [
        CurvePoint(maturity_label="2Y", maturity_years=2.0, yield_percent=3.00),
        CurvePoint(maturity_label="5Y", maturity_years=5.0, yield_percent=3.50),
        CurvePoint(maturity_label="10Y", maturity_years=10.0, yield_percent=4.25),
    ]
    compare_points = [
        CurvePoint(maturity_label="10Y", maturity_years=10.0, yield_percent=4.15),
        CurvePoint(maturity_label="2Y", maturity_years=2.0, yield_percent=3.10),
        CurvePoint(maturity_label="5Y", maturity_years=5.0, yield_percent=3.55),
    ]

    comparison = compare_curves(base_points, compare_points)

    assert [point.maturity_label for point in comparison] == ["2Y", "5Y", "10Y"]
    assert [point.delta_bps for point in comparison] == pytest.approx([10.0, 5.0, -10.0])


def test_compare_curves_maturity_labels_must_match() -> None:
    base_points = [
        CurvePoint(maturity_label="2Y", maturity_years=2.0, yield_percent=3.00),
        CurvePoint(maturity_label="10Y", maturity_years=10.0, yield_percent=4.25),
    ]
    compare_points = [
        CurvePoint(maturity_label="2Y", maturity_years=2.0, yield_percent=3.10),
        CurvePoint(maturity_label="30Y", maturity_years=30.0, yield_percent=4.15),
    ]

    with pytest.raises(ValueError, match="Maturity labels must match"):
        compare_curves(base_points, compare_points)


def test_compare_curves_stable_ordering_by_base_maturity() -> None:
    base_points = [
        CurvePoint(maturity_label="30Y", maturity_years=30.0, yield_percent=4.10),
        CurvePoint(maturity_label="2Y", maturity_years=2.0, yield_percent=3.00),
        CurvePoint(maturity_label="10Y", maturity_years=10.0, yield_percent=4.25),
    ]
    compare_points = [
        CurvePoint(maturity_label="10Y", maturity_years=10.0, yield_percent=4.20),
        CurvePoint(maturity_label="30Y", maturity_years=30.0, yield_percent=4.05),
        CurvePoint(maturity_label="2Y", maturity_years=2.0, yield_percent=3.05),
    ]

    comparison = compare_curves(base_points, compare_points)

    assert [point.maturity_label for point in comparison] == ["2Y", "10Y", "30Y"]