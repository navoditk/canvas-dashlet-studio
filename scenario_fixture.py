from __future__ import annotations

from pydantic import BaseModel

from portfolio_fixture import Position


class ScenarioShock(BaseModel):
    """A bounded, explicit multi-factor shock. Enforcing the bounds is the
    caller's job (FastAPI Query(ge=..., le=...) on the dashlet endpoints) --
    this model just carries the three factors through the calculation.
    """

    rate_shock_bps: float = 0.0  # parallel rate shock, in basis points
    spread_shock_bps: float = 0.0  # parallel credit spread shock, in basis points
    equity_shock_pct: float = 0.0  # equity market shock, in percent


class PositionImpact(BaseModel):
    issuer: str
    sector: str
    market_value: float
    rate_impact: float
    spread_impact: float
    equity_impact: float
    total_impact: float


class SectorContribution(BaseModel):
    sector: str
    total_impact: float
    impact_pct_of_total: float  # this sector's share of the portfolio's total scenario impact


class ScenarioTotals(BaseModel):
    rate_impact: float
    spread_impact: float
    equity_impact: float
    total_impact: float
    portfolio_net_market_value: float
    total_impact_pct: float  # total_impact as a percentage of portfolio net market value


def compute_position_impact(position: Position, shock: ScenarioShock) -> PositionImpact:
    """Deterministic first-order (linear) approximation of P&L impact.

    Rate and spread shocks are yield-factor shocks: a positive shock (yields
    rising / spreads widening) reduces the value of a long, positive-duration
    position, hence the negative sign -- this is the same inverse
    price/yield relationship described in docs/DATA_ACCESS.md and the
    Treasury dashlet. Equity shocks move with beta in the same direction as
    the shock; no sign flip.

    Short positions (negative market_value) fall out correctly with no
    special-casing: multiplying a negative market_value by a positive
    duration/beta and a positive shock naturally produces the opposite-signed
    impact of the equivalent long position.
    """
    rate_impact = -position.duration * position.market_value * (shock.rate_shock_bps / 10_000.0)
    spread_impact = -position.spread_duration * position.market_value * (shock.spread_shock_bps / 10_000.0)
    equity_impact = position.beta * position.market_value * (shock.equity_shock_pct / 100.0)
    total_impact = rate_impact + spread_impact + equity_impact
    return PositionImpact(
        issuer=position.issuer,
        sector=position.sector,
        market_value=position.market_value,
        rate_impact=rate_impact,
        spread_impact=spread_impact,
        equity_impact=equity_impact,
        total_impact=total_impact,
    )


def compute_position_impacts(positions: list[Position], shock: ScenarioShock) -> list[PositionImpact]:
    impacts = [compute_position_impact(position, shock) for position in positions]
    return sorted(impacts, key=lambda impact: impact.issuer)


def compute_scenario_totals(
    position_impacts: list[PositionImpact], *, net_market_value: float
) -> ScenarioTotals:
    rate_impact = sum(impact.rate_impact for impact in position_impacts)
    spread_impact = sum(impact.spread_impact for impact in position_impacts)
    equity_impact = sum(impact.equity_impact for impact in position_impacts)
    total_impact = rate_impact + spread_impact + equity_impact
    total_impact_pct = (total_impact / net_market_value * 100.0) if net_market_value else 0.0
    return ScenarioTotals(
        rate_impact=rate_impact,
        spread_impact=spread_impact,
        equity_impact=equity_impact,
        total_impact=total_impact,
        portfolio_net_market_value=net_market_value,
        total_impact_pct=total_impact_pct,
    )


def compute_sector_contributions(
    position_impacts: list[PositionImpact], *, total_impact: float
) -> list[SectorContribution]:
    """Note: impact_pct_of_total divides by the *scenario's total impact*,
    not portfolio net market value. When offsetting sector impacts nearly
    cancel out (total_impact close to zero), these percentages can become
    large or unstable -- a known property of attribution percentages in
    general, not specific to this implementation. Mirrors the existing
    exact-zero guard used for net_weight_pct in portfolio_fixture.py rather
    than adding a new near-zero epsilon heuristic.
    """
    by_sector: dict[str, float] = {}
    for impact in position_impacts:
        by_sector[impact.sector] = by_sector.get(impact.sector, 0.0) + impact.total_impact

    contributions = [
        SectorContribution(
            sector=sector,
            total_impact=sector_impact,
            impact_pct_of_total=(sector_impact / total_impact * 100.0) if total_impact else 0.0,
        )
        for sector, sector_impact in by_sector.items()
    ]
    return sorted(contributions, key=lambda contribution: contribution.sector)
