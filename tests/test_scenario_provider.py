import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashlets.scenario_provider import ProviderError, ScenarioImpactProvider
from scenario_fixture import ScenarioShock

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "portfolio"


def test_list_available_dates_matches_portfolio_provider() -> None:
    provider = ScenarioImpactProvider(FIXTURE_DIR)
    assert provider.list_available_dates() == ["2026-08-18", "2026-08-19"]


def test_run_scenario_zero_shock_yields_zero_total_impact() -> None:
    provider = ScenarioImpactProvider(FIXTURE_DIR)
    result = provider.run_scenario("2026-08-19", ScenarioShock())
    assert result.totals.total_impact == pytest.approx(0.0)
    assert len(result.position_impacts) == 12


def test_run_scenario_equity_shock_produces_nonzero_impact() -> None:
    provider = ScenarioImpactProvider(FIXTURE_DIR)
    result = provider.run_scenario("2026-08-19", ScenarioShock(equity_shock_pct=10.0))
    assert result.totals.equity_impact != 0.0
    assert result.totals.total_impact == pytest.approx(result.totals.equity_impact)


def test_run_scenario_rate_and_spread_shocks_are_zero_for_this_all_equity_book() -> None:
    # All 12 fixture positions have duration=0.0 and spread_duration=0.0
    # (see portfolio_fixture.py / fixtures/portfolio) -- this book has no
    # fixed-income holdings, so a rate or spread shock should correctly
    # show zero impact, not a fabricated nonzero number.
    provider = ScenarioImpactProvider(FIXTURE_DIR)
    result = provider.run_scenario(
        "2026-08-19", ScenarioShock(rate_shock_bps=100.0, spread_shock_bps=100.0)
    )
    assert result.totals.rate_impact == 0.0
    assert result.totals.spread_impact == 0.0
    assert result.totals.total_impact == 0.0


def test_run_scenario_provenance_matches_exposures_provenance() -> None:
    provider = ScenarioImpactProvider(FIXTURE_DIR)
    result = provider.run_scenario("2026-08-19", ScenarioShock(equity_shock_pct=5.0))
    assert result.provenance.source == "synthetic-fixture"
    assert result.provenance.data_mode == "fixture"
    assert result.provenance.observation_date.isoformat() == "2026-08-19"
    assert result.provenance.is_stale is False


def test_run_scenario_older_date_is_marked_stale() -> None:
    provider = ScenarioImpactProvider(FIXTURE_DIR)
    result = provider.run_scenario("2026-08-18", ScenarioShock(equity_shock_pct=5.0))
    assert result.provenance.is_stale is True


def test_run_scenario_raises_for_missing_date() -> None:
    provider = ScenarioImpactProvider(FIXTURE_DIR)
    with pytest.raises(ProviderError) as exc_info:
        provider.run_scenario("2099-01-01", ScenarioShock())
    assert exc_info.value.error_code == "fixture_not_found"


def test_run_scenario_sector_contributions_cover_all_five_sectors() -> None:
    provider = ScenarioImpactProvider(FIXTURE_DIR)
    result = provider.run_scenario("2026-08-19", ScenarioShock(equity_shock_pct=10.0))
    assert len(result.sector_contributions) == 5
