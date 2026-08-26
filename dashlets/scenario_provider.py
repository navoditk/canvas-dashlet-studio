from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from dashlet_framework import Provenance
from dashlets.portfolio_provider import FixturePortfolioProvider, ProviderError
from scenario_fixture import (
    PositionImpact,
    ScenarioShock,
    ScenarioTotals,
    SectorContribution,
    compute_position_impacts,
    compute_scenario_totals,
    compute_sector_contributions,
)

__all__ = ["ProviderError", "ScenarioImpactProvider", "ScenarioImpactResult"]


class ScenarioImpactResult(BaseModel):
    position_impacts: list[PositionImpact]
    totals: ScenarioTotals
    sector_contributions: list[SectorContribution]
    provenance: Provenance


class ScenarioImpactProvider:
    """Applies deterministic shock scenarios to the same portfolio positions
    Portfolio Exposure reads. Reuses FixturePortfolioProvider directly for
    fixture loading/date-listing rather than re-implementing it -- this is
    the "same portfolio, multiple lenses" reuse described in
    docs/evidence and AGENTS.md, sharing the data-access layer between two
    otherwise independent dashlet FastAPI processes.
    """

    def __init__(self, fixture_dir: Path) -> None:
        self._portfolio_provider = FixturePortfolioProvider(fixture_dir)

    def list_available_dates(self) -> list[str]:
        return self._portfolio_provider.list_available_dates()

    def run_scenario(self, observation_date: str, shock: ScenarioShock) -> ScenarioImpactResult:
        exposures = self._portfolio_provider.get_exposures(observation_date)
        position_impacts = compute_position_impacts(exposures.positions, shock)
        totals = compute_scenario_totals(position_impacts, net_market_value=exposures.totals.net_market_value)
        total_impact = totals.total_impact
        sector_contributions = compute_sector_contributions(position_impacts, total_impact=total_impact)
        return ScenarioImpactResult(
            position_impacts=position_impacts,
            totals=totals,
            sector_contributions=sector_contributions,
            provenance=exposures.provenance,
        )
