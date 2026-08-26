from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, ValidationError

from dashlet_framework import Provenance
from portfolio_fixture import (
    IssuerExposure,
    PortfolioTotals,
    Position,
    SectorExposure,
    compute_issuer_exposures,
    compute_sector_exposures,
    compute_totals,
    load_snapshot,
)


class ProviderError(Exception):
    def __init__(self, error_code: str, message: str) -> None:
        self.error_code = error_code
        self.message = message
        super().__init__(message)


class PortfolioExposureResult(BaseModel):
    positions: list[Position]
    totals: PortfolioTotals
    sector_exposures: list[SectorExposure]
    issuer_exposures: list[IssuerExposure]
    provenance: Provenance


class FixturePortfolioProvider:
    """Reads deterministic synthetic position snapshots from fixtures/portfolio/.

    There is no live provider for this dashlet: PROPOSAL.md's Portfolio
    Exposure use case is built from mock positions, not a real holdings
    feed, so unlike Treasury there is only one data mode. See
    docs/DATA_ACCESS.md §2.
    """

    def __init__(self, fixture_dir: Path) -> None:
        self._fixture_dir = fixture_dir

    def _fixture_path(self, observation_date: str) -> Path:
        return self._fixture_dir / f"positions_{observation_date}.json"

    def list_available_dates(self) -> list[str]:
        dates = {path.stem.removeprefix("positions_") for path in self._fixture_dir.glob("positions_*.json")}
        return sorted(dates)

    def get_exposures(self, observation_date: str) -> PortfolioExposureResult:
        fixture_path = self._fixture_path(observation_date)
        if not fixture_path.exists():
            raise ProviderError(
                "fixture_not_found", f"No portfolio fixture found for date: {observation_date}"
            )

        try:
            snapshot = load_snapshot(fixture_path)
        except ValidationError as exc:
            raise ProviderError("invalid_fixture", f"Portfolio fixture is invalid: {exc}") from exc

        totals = compute_totals(snapshot.positions)
        sector_exposures = compute_sector_exposures(snapshot.positions, net_denominator=totals.net_market_value)
        issuer_exposures = compute_issuer_exposures(snapshot.positions, net_denominator=totals.net_market_value)

        available = self.list_available_dates()
        latest = max(available) if available else observation_date
        is_stale = snapshot.observation_date.isoformat() != latest

        provenance = Provenance(
            source="synthetic-fixture",
            source_url=None,
            observation_date=snapshot.observation_date,
            retrieved_at=datetime.now(UTC),
            data_mode="fixture",
            is_stale=is_stale,
        )
        return PortfolioExposureResult(
            positions=snapshot.positions,
            totals=totals,
            sector_exposures=sector_exposures,
            issuer_exposures=issuer_exposures,
            provenance=provenance,
        )
