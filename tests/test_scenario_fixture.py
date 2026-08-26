import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from portfolio_fixture import Position
from scenario_fixture import (
    ScenarioShock,
    compute_position_impact,
    compute_position_impacts,
    compute_scenario_totals,
    compute_sector_contributions,
)


def test_zero_shock_yields_zero_impact() -> None:
    position = Position(issuer="A", sector="Technology", market_value=1_000_000.0, beta=1.3)
    impact = compute_position_impact(position, ScenarioShock())
    assert impact.rate_impact == 0.0
    assert impact.spread_impact == 0.0
    assert impact.equity_impact == 0.0
    assert impact.total_impact == 0.0


def test_equity_only_position_scales_with_beta_and_shock() -> None:
    position = Position(issuer="A", sector="Technology", market_value=1_000_000.0, beta=1.3)
    impact = compute_position_impact(position, ScenarioShock(equity_shock_pct=10.0))
    # +10% equity shock * beta 1.3 * $1M = +$130,000
    assert impact.equity_impact == pytest.approx(130_000.0)
    assert impact.rate_impact == 0.0
    assert impact.spread_impact == 0.0
    assert impact.total_impact == pytest.approx(130_000.0)


def test_rate_duration_position_loses_value_when_rates_rise() -> None:
    # The exact 10Y example from the FICC walkthrough: $10M market value,
    # duration 8.5, rates +25bp -> -$212,500.
    position = Position(issuer="10Y Note", sector="Rates", market_value=10_000_000.0, duration=8.5)
    impact = compute_position_impact(position, ScenarioShock(rate_shock_bps=25.0))
    assert impact.rate_impact == pytest.approx(-212_500.0)
    assert impact.total_impact == pytest.approx(-212_500.0)


def test_short_rate_duration_position_gains_when_rates_rise() -> None:
    # The exact 2Y short example from the FICC walkthrough: -$8M market
    # value, duration 1.9, rates +25bp -> +$38,000 (a short position
    # benefits when rates rise -- no special-casing needed for the sign).
    position = Position(issuer="2Y Note (short)", sector="Rates", market_value=-8_000_000.0, duration=1.9)
    impact = compute_position_impact(position, ScenarioShock(rate_shock_bps=25.0))
    assert impact.rate_impact == pytest.approx(38_000.0)


def test_combined_10y_long_2y_short_matches_net_dv01_walkthrough() -> None:
    long_10y = Position(issuer="10Y Note", sector="Rates", market_value=10_000_000.0, duration=8.5)
    short_2y = Position(issuer="2Y Note (short)", sector="Rates", market_value=-8_000_000.0, duration=1.9)
    shock = ScenarioShock(rate_shock_bps=25.0)
    impacts = compute_position_impacts([long_10y, short_2y], shock)
    total_impact = sum(impact.total_impact for impact in impacts)
    # -212,500 + 38,000 = -174,500, matching the net-DV01 P&L estimate
    # given earlier: -Net DV01 * 25bp ~= -$6,980 * 25 ~= -$174,500.
    assert total_impact == pytest.approx(-174_500.0)


def test_spread_duration_position_loses_value_when_spreads_widen() -> None:
    position = Position(issuer="Corp Bond", sector="Credit", market_value=5_000_000.0, spread_duration=4.0)
    impact = compute_position_impact(position, ScenarioShock(spread_shock_bps=50.0))
    # -4.0 * $5M * (50/10000) = -$100,000
    assert impact.spread_impact == pytest.approx(-100_000.0)


def test_combined_shock_sums_all_three_factors() -> None:
    position = Position(
        issuer="Mixed", sector="Multi-Asset", market_value=1_000_000.0,
        duration=5.0, spread_duration=2.0, beta=0.5,
    )
    shock = ScenarioShock(rate_shock_bps=10.0, spread_shock_bps=20.0, equity_shock_pct=5.0)
    impact = compute_position_impact(position, shock)
    expected_rate = -5.0 * 1_000_000.0 * (10.0 / 10_000.0)
    expected_spread = -2.0 * 1_000_000.0 * (20.0 / 10_000.0)
    expected_equity = 0.5 * 1_000_000.0 * (5.0 / 100.0)
    assert impact.rate_impact == pytest.approx(expected_rate)
    assert impact.spread_impact == pytest.approx(expected_spread)
    assert impact.equity_impact == pytest.approx(expected_equity)
    assert impact.total_impact == pytest.approx(expected_rate + expected_spread + expected_equity)


def test_compute_position_impacts_sorted_by_issuer() -> None:
    positions = [
        Position(issuer="Zeta", sector="Technology", market_value=100.0, beta=1.0),
        Position(issuer="Alpha", sector="Energy", market_value=100.0, beta=1.0),
    ]
    impacts = compute_position_impacts(positions, ScenarioShock(equity_shock_pct=10.0))
    assert [impact.issuer for impact in impacts] == ["Alpha", "Zeta"]


def test_compute_scenario_totals_sums_all_positions() -> None:
    positions = [
        Position(issuer="A", sector="Technology", market_value=1_000_000.0, beta=1.0),
        Position(issuer="B", sector="Energy", market_value=500_000.0, beta=2.0),
    ]
    impacts = compute_position_impacts(positions, ScenarioShock(equity_shock_pct=10.0))
    totals = compute_scenario_totals(impacts, net_market_value=1_500_000.0)
    # A: +100,000 (1.0 * 1M * 10%), B: +100,000 (2.0 * 0.5M * 10%)
    assert totals.equity_impact == pytest.approx(200_000.0)
    assert totals.total_impact == pytest.approx(200_000.0)
    assert totals.total_impact_pct == pytest.approx(200_000.0 / 1_500_000.0 * 100.0)


def test_compute_scenario_totals_zero_net_market_value_guard() -> None:
    positions = [Position(issuer="A", sector="Technology", market_value=100.0, beta=1.0)]
    impacts = compute_position_impacts(positions, ScenarioShock(equity_shock_pct=10.0))
    totals = compute_scenario_totals(impacts, net_market_value=0.0)
    assert totals.total_impact_pct == 0.0


def test_compute_sector_contributions_aggregates_by_sector() -> None:
    positions = [
        Position(issuer="A", sector="Technology", market_value=1_000_000.0, beta=1.0),
        Position(issuer="B", sector="Technology", market_value=500_000.0, beta=1.0),
        Position(issuer="C", sector="Energy", market_value=200_000.0, beta=1.0),
    ]
    shock = ScenarioShock(equity_shock_pct=10.0)
    impacts = compute_position_impacts(positions, shock)
    total_impact = sum(impact.total_impact for impact in impacts)
    contributions = compute_sector_contributions(impacts, total_impact=total_impact)
    by_sector = {c.sector: c for c in contributions}
    assert by_sector["Technology"].total_impact == pytest.approx(150_000.0)
    assert by_sector["Energy"].total_impact == pytest.approx(20_000.0)
    assert by_sector["Technology"].impact_pct_of_total == pytest.approx(150_000.0 / 170_000.0 * 100.0)


def test_compute_sector_contributions_zero_total_impact_guard() -> None:
    # Long and short equity positions that exactly offset -> total_impact 0.
    positions = [
        Position(issuer="A", sector="Technology", market_value=100.0, beta=1.0),
        Position(issuer="B", sector="Technology", market_value=-100.0, beta=1.0),
    ]
    shock = ScenarioShock(equity_shock_pct=10.0)
    impacts = compute_position_impacts(positions, shock)
    contributions = compute_sector_contributions(impacts, total_impact=0.0)
    assert contributions[0].impact_pct_of_total == 0.0


def test_compute_sector_contributions_sorted_alphabetically() -> None:
    positions = [
        Position(issuer="A", sector="Technology", market_value=100.0, beta=1.0),
        Position(issuer="B", sector="Energy", market_value=100.0, beta=1.0),
    ]
    shock = ScenarioShock(equity_shock_pct=10.0)
    impacts = compute_position_impacts(positions, shock)
    total_impact = sum(impact.total_impact for impact in impacts)
    contributions = compute_sector_contributions(impacts, total_impact=total_impact)
    assert [c.sector for c in contributions] == ["Energy", "Technology"]
