import sys
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from portfolio_fixture import (
    Position,
    compute_issuer_exposures,
    compute_sector_exposures,
    compute_totals,
    load_snapshot,
)


def test_snapshot_loads_and_has_expected_date() -> None:
    snapshot = load_snapshot("fixtures/portfolio/positions_2026-08-19.json")
    assert snapshot.observation_date == date(2026, 8, 19)
    assert len(snapshot.positions) == 12


def test_position_scenario_fields_default_to_zero() -> None:
    position = Position(issuer="A", sector="Technology", market_value=100.0)
    assert position.duration == 0.0
    assert position.spread_duration == 0.0
    assert position.beta == 0.0


def test_position_scenario_fields_accept_explicit_values() -> None:
    position = Position(
        issuer="A", sector="Technology", market_value=100.0,
        duration=5.0, spread_duration=2.0, beta=1.3,
    )
    assert position.duration == 5.0
    assert position.spread_duration == 2.0
    assert position.beta == 1.3


def test_real_fixtures_have_sector_beta_and_zero_duration() -> None:
    snapshot = load_snapshot("fixtures/portfolio/positions_2026-08-19.json")
    for position in snapshot.positions:
        assert position.beta > 0.0, f"{position.issuer} should have a nonzero equity beta"
        assert position.duration == 0.0, f"{position.issuer} is an equity position with no rate duration"
        assert position.spread_duration == 0.0, f"{position.issuer} is an equity position with no spread duration"


def test_empty_positions_rejected(tmp_path) -> None:
    bad_file = tmp_path / "empty.json"
    bad_file.write_text(
        """
        {
          "fixture_meta": {"note": "Deterministic synthetic test fixture. Not live positions.", "data_mode": "fixture"},
          "observation_date": "2026-08-19",
          "positions": []
        }
        """
    )

    with pytest.raises(ValidationError, match="at least one position"):
        load_snapshot(bad_file)


def test_compute_totals_separates_long_short_net_gross() -> None:
    positions = [
        Position(issuer="A", sector="Technology", market_value=1_000_000.0),
        Position(issuer="B", sector="Technology", market_value=-200_000.0),
        Position(issuer="C", sector="Financials", market_value=500_000.0),
    ]

    totals = compute_totals(positions)

    assert totals.long_market_value == pytest.approx(1_500_000.0)
    assert totals.short_market_value == pytest.approx(200_000.0)
    assert totals.net_market_value == pytest.approx(1_300_000.0)
    assert totals.gross_market_value == pytest.approx(1_700_000.0)


def test_compute_totals_all_long_has_zero_short() -> None:
    positions = [Position(issuer="A", sector="Technology", market_value=1_000_000.0)]
    totals = compute_totals(positions)
    assert totals.short_market_value == 0.0
    assert totals.net_market_value == totals.long_market_value


def test_compute_sector_exposures_aggregates_by_sector() -> None:
    positions = [
        Position(issuer="A", sector="Technology", market_value=1_000_000.0),
        Position(issuer="B", sector="Technology", market_value=-200_000.0),
        Position(issuer="C", sector="Financials", market_value=500_000.0),
    ]

    exposures = compute_sector_exposures(positions, net_denominator=1_300_000.0)

    by_sector = {e.sector: e for e in exposures}
    assert by_sector["Technology"].long_market_value == pytest.approx(1_000_000.0)
    assert by_sector["Technology"].short_market_value == pytest.approx(200_000.0)
    assert by_sector["Technology"].net_market_value == pytest.approx(800_000.0)
    assert by_sector["Financials"].net_market_value == pytest.approx(500_000.0)


def test_compute_sector_exposures_weight_pct_sums_to_one_hundred() -> None:
    positions = [
        Position(issuer="A", sector="Technology", market_value=1_000_000.0),
        Position(issuer="C", sector="Financials", market_value=500_000.0),
    ]
    totals = compute_totals(positions)
    exposures = compute_sector_exposures(positions, net_denominator=totals.net_market_value)
    assert sum(e.net_weight_pct for e in exposures) == pytest.approx(100.0)


def test_compute_sector_exposures_zero_denominator_yields_zero_weight() -> None:
    positions = [
        Position(issuer="A", sector="Technology", market_value=1_000_000.0),
        Position(issuer="B", sector="Technology", market_value=-1_000_000.0),
    ]
    exposures = compute_sector_exposures(positions, net_denominator=0.0)
    assert exposures[0].net_weight_pct == 0.0


def test_compute_sector_exposures_sorted_alphabetically() -> None:
    positions = [
        Position(issuer="A", sector="Technology", market_value=100.0),
        Position(issuer="B", sector="Energy", market_value=100.0),
        Position(issuer="C", sector="Financials", market_value=100.0),
    ]
    exposures = compute_sector_exposures(positions, net_denominator=300.0)
    assert [e.sector for e in exposures] == ["Energy", "Financials", "Technology"]


def test_compute_issuer_exposures_nets_multiple_lots_of_same_issuer() -> None:
    positions = [
        Position(issuer="A", sector="Technology", market_value=1_000_000.0),
        Position(issuer="A", sector="Technology", market_value=-300_000.0),
        Position(issuer="B", sector="Financials", market_value=500_000.0),
    ]

    exposures = compute_issuer_exposures(positions, net_denominator=1_200_000.0)

    by_issuer = {e.issuer: e for e in exposures}
    assert by_issuer["A"].long_market_value == pytest.approx(1_000_000.0)
    assert by_issuer["A"].short_market_value == pytest.approx(300_000.0)
    assert by_issuer["A"].net_market_value == pytest.approx(700_000.0)


def test_compute_issuer_exposures_sorted_alphabetically() -> None:
    positions = [
        Position(issuer="Zeta", sector="Technology", market_value=100.0),
        Position(issuer="Alpha", sector="Energy", market_value=100.0),
    ]
    exposures = compute_issuer_exposures(positions, net_denominator=200.0)
    assert [e.issuer for e in exposures] == ["Alpha", "Zeta"]


def test_real_fixtures_totals_are_deterministic_across_loads() -> None:
    snapshot1 = load_snapshot("fixtures/portfolio/positions_2026-08-19.json")
    snapshot2 = load_snapshot("fixtures/portfolio/positions_2026-08-19.json")
    totals1 = compute_totals(snapshot1.positions)
    totals2 = compute_totals(snapshot2.positions)
    assert totals1 == totals2
