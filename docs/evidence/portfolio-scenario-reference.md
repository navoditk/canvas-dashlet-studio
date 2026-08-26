# Evidence: Portfolio Scenario Impact Reference Milestone

## Milestone name

Portfolio Scenario Impact dashlet — third business-use-case dashlet, second built on `dashlet_framework` without any framework changes, applying deterministic rate/spread/equity shocks to the same portfolio positions Portfolio Exposure reads.

## Validation date

2026-08-26. Direct-FastAPI, automated-test, and hand-verified-calculation sections are complete. Live-Canvas-specific sections are **not yet completed** — see the TODO markers below; this was an explicit, recorded decision (see `docs/PROGRESS.md` "Resume here"), not an oversight.

## Commit SHAs

`79524ed` (Position extension), `400bcd6` (calculation engine), `f106a36` (provider), `031877f` (dashlet + tests), and the Canvas-registration/docs commit that follows this evidence doc — all on `main`.

## Architecture exercised

```text
Copilot agent tool call ──┐
                          ├─▶ Canvas ToolProxy (allowlist + generated-schema validation) ─┐
Canvas iframe fetch("./api/...") ──────────────────────────────────────────────────────┼─▶ FastAPI dashlet (dashlets/portfolio_scenario_dashlet.py)
                                                                                         └─▶ ScenarioImpactProvider ─▶ FixturePortfolioProvider (shared with Portfolio Exposure)
```

Both consumers (iframe JavaScript and the Copilot agent) invoke the same three `agent-tool`-tagged FastAPI operations: `run_portfolio_scenario`, `get_scenario_contributions`, `compare_scenario_impacts`. `ScenarioImpactProvider` wraps `FixturePortfolioProvider` (from `dashlets/portfolio_provider.py`) directly rather than duplicating fixture-loading logic — the concrete realization of "same portfolio, multiple lenses" from the explicit design decision made before implementation.

## Direct FastAPI verification summary

Ran the dashlet directly with `uv run uvicorn dashlets.portfolio_scenario_dashlet:app` on a loopback port and exercised it with `curl`:

| Check | Result |
|---|---|
| `GET /health` | `{"status":"ready"}` |
| `GET /metadata` | `data_mode: "fixture"`, `default_observation_date: "2026-08-19"`, same `available_fixture_dates` as Portfolio Exposure (shared fixture directory) |
| `run_portfolio_scenario` parameters | `date`, `rate_shock_bps`, `spread_shock_bps`, `equity_shock_pct` — all optional, all default `0.0` |
| `get_scenario_contributions` parameters | same four plus `top_n` (optional, default 5, bounded 1–20) |
| `compare_scenario_impacts` parameters | `date` plus six shock parameters (`rate_bps_a/spread_bps_a/equity_pct_a`, `rate_bps_b/spread_bps_b/equity_pct_b`) — no `data_mode`, matching Portfolio Exposure's compare endpoint |
| `equity_shock_pct=999` (out of range) | `422` |
| Unknown `date=2099-01-01` | `404`, `{"error_code": "fixture_not_found", "message": "No portfolio fixture found for date: 2099-01-01"}` |
| Untagged/internal routes (`/api/scenario/fixture-dates`, `/metadata`, `/`) | Present in OpenAPI but **not** tagged `agent-tool` |

## Fixture-mode result and hand-verified calculation

```json
{
  "source": "synthetic-fixture",
  "source_url": null,
  "observation_date": "2026-08-19",
  "retrieved_at": "2026-08-26T22:42:11.191991Z",
  "data_mode": "fixture",
  "is_stale": false
}
```

`GET /api/scenario/run?equity_shock_pct=10` totals:

```json
{"rate_impact": 0.0, "spread_impact": 0.0, "equity_impact": 1154000.0, "total_impact": 1154000.0, "portfolio_net_market_value": 10650000.0, "total_impact_pct": 10.835680751173708}
```

`rate_impact` and `spread_impact` are exactly `0.0` — expected and asserted (`test_run_endpoint_rate_and_spread_shocks_are_zero_for_this_all_equity_book`), since all 12 fixture positions have `duration = 0.0` and `spread_duration = 0.0` (an all-equity book, no fixed-income holdings). `equity_impact` matches a hand calculation for the single largest position: TechCore Inc, `beta=1.3`, `market_value=$2,400,000`, `equity_shock_pct=10` → `1.3 × 2,400,000 × 0.10 = $312,000`, confirmed directly against the API response in `tests/test_portfolio_scenario_dashlet.py::test_run_endpoint_equity_shock_matches_known_fixture_value`.

## Calculation correctness: reuse of an earlier FICC walkthrough

Two tests in `tests/test_scenario_fixture.py` reuse the exact numeric example given earlier in this session while explaining fixed-income exposure/DV01 from first principles: a $10,000,000 position in a 10-year note with modified duration 8.5, and a -$8,000,000 (short) position in a 2-year note with modified duration 1.9, under a +25bp parallel rate shock.

- `test_rate_duration_position_loses_value_when_rates_rise`: the long 10Y position's impact is `-8.5 × 10,000,000 × (25/10,000) = -$212,500`.
- `test_short_rate_duration_position_gains_when_rates_rise`: the short 2Y position's impact is `-1.9 × (-8,000,000) × (25/10,000) = +$38,000`.
- `test_combined_10y_long_2y_short_matches_net_dv01_walkthrough`: the combined total is `-$174,500`, matching the net-DV01 P&L estimate given in that earlier explanation (`-Net DV01 × 25bp ≈ -$6,980 × 25 ≈ -$174,500`).

This is independent confirmation that the calculation engine's sign conventions and magnitude are correct for the general rate-duration case, not just for the specific (rate/spread-insensitive) fixture data currently shipped.

## iframe endpoint-path evidence

The dashlet's inline Alpine client fetches `./api/scenario/fixture-dates`, `./api/scenario/run`, `./api/scenario/contributions`, `./api/scenario/compare` — the identical mount-relative paths and `operationId`s used by the agent-tool proxy. Verified by reading `dashlets/portfolio_scenario_dashlet.py`'s inline `<script>` and by the generic contract test `tests/test_dashlet_contract.py::test_root_page_uses_mount_relative_fetch_paths`, which covers this dashlet automatically (it was added to `scripts/generate_tool_schemas.py`'s `DASHLET_MODULES`, with zero new contract-test code required).

## Standalone browser verification

**Not yet captured for this dashlet specifically.** Portfolio Exposure has a real, cross-verified browser screenshot (see `docs/evidence/portfolio-exposure-reference.md`); the same has not yet been done for Portfolio Scenario Impact. To capture: `uv run uvicorn dashlets.portfolio_scenario_dashlet:app --host 127.0.0.1 --port 8765`, open `http://127.0.0.1:8765/` in a browser, enter a shock, click **Run Scenario**, screenshot, and cross-check every displayed value against a direct `curl` call the same way `docs/evidence/portfolio-exposure-reference.md`'s standalone section does.

## Agent-tool endpoint-path evidence

**TODO — requires a live Canvas session.**

1. Open a Copilot session with this repository, invoke the `dashlet-studio` Canvas extension.
2. `select_dashlet(portfolio-scenario)`, then `start_dashlet`. Confirm the iframe loads and the contribution chart populates.
3. Ask Copilot each of the following, and record the tool call, arguments, and returned values:
   - *"Use the scenario tool to shock equities up 10% and show me the impact for 2026-08-19."* → expect `run_portfolio_scenario(equity_shock_pct=10)`, total impact ≈ +$1,154,000.
   - *"Use the scenario tool to show me the top 3 position impacts for a 10% equity shock."* → expect `get_scenario_contributions(equity_shock_pct=10, top_n=3)`, TechCore Inc first at +$312,000.
   - *"Use the scenario tool to compare a +10% equity shock against a -10% equity shock."* → expect `compare_scenario_impacts(equity_pct_a=10, equity_pct_b=-10)`, symmetric opposite-signed sector impacts.
4. Confirm in the Canvas runtime diagnostics log that each call shows `Proxy request: GET .../api/scenario/...` on the same host:port the iframe is pointed at.

## Tool-isolation negative tests

**TODO — requires a live Canvas session.** Suggested checks: while `portfolio-scenario` is active, invoke a tool from any other dashlet (Treasury, Hello, or Portfolio Exposure) → expect rejection; and vice versa. This is the fourth dashlet sharing this open item — see `docs/PROGRESS.md` "Resume here" for the recommendation to do one combined live-Canvas pass across all four rather than four separate ones.

## Process-lifecycle results

**TODO — requires a live Canvas session.** Same suggested checks as the other dashlets' evidence docs (clean process stop/start on `select_dashlet`, no orphaned process on `stop_dashlet`).

## Python test summary

```text
uv run pytest tests/test_scenario_fixture.py tests/test_scenario_provider.py tests/test_portfolio_scenario_dashlet.py -q
45 passed

uv run pytest -q   # full suite
164 passed, 1 warning in 0.28s
```

## Node test summary

```text
npm test (.github/extensions/dashlet-studio): 43 passed, 0 failed
```

Includes two Portfolio-Scenario-specific assertions in `generated-tool-schemas.test.mjs`: `run_portfolio_scenario`/`get_scenario_contributions` expose only optional, bounded shock parameters (no required fields — a zero-shock request is valid and meaningful); `compare_scenario_impacts` exposes all six shock parameters (two independent scenarios) and, like `compare_portfolio_exposures`, has no `data_mode`.

## Provenance example (sanitized)

```json
{
  "source": "synthetic-fixture",
  "source_url": null,
  "observation_date": "2026-08-19",
  "retrieved_at": "2026-08-26T22:42:11.191991Z",
  "data_mode": "fixture",
  "is_stale": false
}
```

## Known limitations

- **No live Canvas verification yet** and **no standalone browser screenshot yet** — see the TODO sections above. Deliberately deferred alongside the same gap for Portfolio Exposure; see `docs/PROGRESS.md` "Resume here" for the reasoning and the recommendation to do one combined pass covering all four dashlets.
- Rate and spread shocks show `$0` impact on the current fixture data by design (all-equity book, no fixed-income holdings) — not a defect; the underlying math is independently verified against synthetic non-zero-duration positions in `tests/test_scenario_fixture.py`.
- `impact_pct_of_total` (per-sector contribution percentage) divides by the scenario's total impact, not portfolio net market value. When offsetting sector impacts nearly cancel out, this can produce large or unstable percentages — a known property of attribution percentages generally, not specific to this implementation. Mirrors the existing exact-zero guard used elsewhere in the codebase (`portfolio_fixture._weight_pct`) rather than adding a new near-zero epsilon heuristic.
- The generic OpenAPI-to-tool-schema generator does not carry `ge`/`le` numeric bounds into the Copilot-visible schema for any of the six shock parameters or `top_n` — FastAPI still enforces the real bounds server-side with a `422` (verified above), so this is a schema-precision gap, not a safety gap. Same known limitation as Portfolio Exposure's `top_n`.
- Independent code review has not yet been completed for this dashlet (see `docs/PROGRESS.md` Milestone 4 evidence) — implemented directly by Claude Code this session, review still open, same as Portfolio Exposure.

## Related documents

- [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) — component boundaries and dual-use business-operation contract.
- [`docs/DASHLET_CONTRACT.md`](../DASHLET_CONTRACT.md), [`docs/DATA_ACCESS.md`](../DATA_ACCESS.md), [`docs/WEB_AUTHORING.md`](../WEB_AUTHORING.md), [`docs/TOOL_AUTHORING.md`](../TOOL_AUTHORING.md) — the contract this dashlet was built against.
- [`docs/PROGRESS.md`](../PROGRESS.md) — Milestone 4 checklist and evidence, including the open independent-review item.
- [`docs/evidence/portfolio-exposure-reference.md`](portfolio-exposure-reference.md) — the sibling dashlet this one shares fixture data and provider infrastructure with, and the template this document follows.
