from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from pydantic import BaseModel, field_validator


class FixtureMeta(BaseModel):
    note: str
    data_mode: str


class Position(BaseModel):
    issuer: str
    sector: str
    market_value: float  # positive = long exposure, negative = short exposure
    duration: float = 0.0  # rate-duration, years. 0.0 = no rate sensitivity (e.g. pure equity).
    spread_duration: float = 0.0  # credit spread-duration, years. 0.0 = no credit sensitivity.
    beta: float = 0.0  # equity market beta. 0.0 = no equity-factor sensitivity.


class PortfolioSnapshotFixture(BaseModel):
    observation_date: date
    positions: list[Position]
    fixture_meta: FixtureMeta

    @field_validator("positions")
    @classmethod
    def _reject_empty_positions(cls, positions: list[Position]) -> list[Position]:
        if not positions:
            raise ValueError("Fixture must contain at least one position")
        return positions


def load_snapshot(path: str | Path) -> PortfolioSnapshotFixture:
    raw_text = Path(path).read_text()
    payload = json.loads(raw_text)
    return PortfolioSnapshotFixture.model_validate(payload)


class PortfolioTotals(BaseModel):
    long_market_value: float
    short_market_value: float  # positive magnitude of short exposure
    net_market_value: float
    gross_market_value: float


def compute_totals(positions: list[Position]) -> PortfolioTotals:
    long_mv = sum(p.market_value for p in positions if p.market_value > 0)
    short_mv = sum(-p.market_value for p in positions if p.market_value < 0)
    return PortfolioTotals(
        long_market_value=long_mv,
        short_market_value=short_mv,
        net_market_value=long_mv - short_mv,
        gross_market_value=long_mv + short_mv,
    )


class SectorExposure(BaseModel):
    sector: str
    long_market_value: float
    short_market_value: float
    net_market_value: float
    net_weight_pct: float  # net_market_value as a percentage of portfolio net_market_value


class IssuerExposure(BaseModel):
    issuer: str
    sector: str
    long_market_value: float
    short_market_value: float
    net_market_value: float
    net_weight_pct: float  # net_market_value as a percentage of portfolio net_market_value


def _weight_pct(net_value: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return (net_value / denominator) * 100.0


def compute_sector_exposures(positions: list[Position], *, net_denominator: float) -> list[SectorExposure]:
    by_sector: dict[str, list[Position]] = {}
    for position in positions:
        by_sector.setdefault(position.sector, []).append(position)

    exposures = []
    for sector, sector_positions in by_sector.items():
        long_mv = sum(p.market_value for p in sector_positions if p.market_value > 0)
        short_mv = sum(-p.market_value for p in sector_positions if p.market_value < 0)
        net_mv = long_mv - short_mv
        exposures.append(
            SectorExposure(
                sector=sector,
                long_market_value=long_mv,
                short_market_value=short_mv,
                net_market_value=net_mv,
                net_weight_pct=_weight_pct(net_mv, net_denominator),
            )
        )
    return sorted(exposures, key=lambda exposure: exposure.sector)


def compute_issuer_exposures(positions: list[Position], *, net_denominator: float) -> list[IssuerExposure]:
    by_issuer: dict[tuple[str, str], list[Position]] = {}
    for position in positions:
        by_issuer.setdefault((position.issuer, position.sector), []).append(position)

    exposures = []
    for (issuer, sector), issuer_positions in by_issuer.items():
        long_mv = sum(p.market_value for p in issuer_positions if p.market_value > 0)
        short_mv = sum(-p.market_value for p in issuer_positions if p.market_value < 0)
        net_mv = long_mv - short_mv
        exposures.append(
            IssuerExposure(
                issuer=issuer,
                sector=sector,
                long_market_value=long_mv,
                short_market_value=short_mv,
                net_market_value=net_mv,
                net_weight_pct=_weight_pct(net_mv, net_denominator),
            )
        )
    return sorted(exposures, key=lambda exposure: exposure.issuer)
