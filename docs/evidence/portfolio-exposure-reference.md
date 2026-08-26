# Evidence: Portfolio Exposure Reference Milestone

## Milestone name

Portfolio Exposure & Concentration dashlet — second business-use-case dashlet built on `dashlet_framework`, exercising the framework's reusability outside Treasury.

## Validation date

2026-08-26. Direct-FastAPI, automated-test, and standalone-browser sections are complete. Live-Canvas-specific sections (agent-tool invocation logs, tool isolation, process lifecycle) are **not yet completed** — see the TODO markers below; no Canvas/Copilot session was available in the session that built this dashlet, only a standalone browser screenshot of the dashlet running directly under `uvicorn`.

## Commit SHA

`da18bce` ("Add Portfolio Exposure & Concentration dashlet") on `main`.

## Architecture exercised

```text
Copilot agent tool call ──┐
                          ├─▶ Canvas ToolProxy (allowlist + generated-schema validation) ─┐
Canvas iframe fetch("./api/...") ──────────────────────────────────────────────────────┼─▶ FastAPI dashlet (dashlets/portfolio_exposure_dashlet.py)
                                                                                         └─▶ FixturePortfolioProvider (fixture-only, no live mode)
```

Both consumers (iframe JavaScript and the Copilot agent) invoke the same three `agent-tool`-tagged FastAPI operations: `get_portfolio_exposures`, `get_top_concentrations`, `compare_portfolio_exposures`. See [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) §4–5 for the general dual-use contract this instance implements, and [`docs/DATA_ACCESS.md`](../DATA_ACCESS.md) §2 for why this dashlet has no live data mode (unlike Treasury).

## Direct FastAPI verification summary

Ran the dashlet directly with `uv run uvicorn dashlets.portfolio_exposure_dashlet:app` on a loopback port and exercised it with `curl`:

| Check | Result |
|---|---|
| `GET /health` | `{"status":"ready"}` |
| `GET /metadata` | `data_mode: "fixture"`, `default_observation_date: "2026-08-19"`, `available_fixture_dates: ["2026-08-18", "2026-08-19"]` |
| `get_portfolio_exposures` parameters (from `/openapi.json`) | `date` optional; no required params |
| `get_top_concentrations` parameters | `date`, `top_n` both optional (FastAPI enforces `1 <= top_n <= 20` server-side, returns 422 outside that range) |
| `compare_portfolio_exposures` parameters | `base_date`, `compare_date` both **required** |
| `top_n=25` (out of range) | `422` |
| Unknown `date=2099-01-01` | `404`, `{"error_code": "fixture_not_found", "message": "No portfolio fixture found for date: 2099-01-01"}` |
| Untagged/internal routes (`/api/portfolio/fixture-dates`, `/metadata`, `/`) | Present in OpenAPI but **not** tagged `agent-tool` |

## Fixture-mode result (only mode — no live provider exists for this dashlet)

```json
{
  "source": "synthetic-fixture",
  "source_url": null,
  "observation_date": "2026-08-19",
  "retrieved_at": "2026-08-26T20:14:07.919308Z",
  "data_mode": "fixture",
  "is_stale": false
}
```

Totals for the same request:

```json
{"long_market_value": 11400000.0, "short_market_value": 750000.0, "net_market_value": 10650000.0, "gross_market_value": 12150000.0}
```

These match the hand-calculated totals from the 12-position fixture (`fixtures/portfolio/positions_2026-08-19.json`) and are asserted exactly in `tests/test_portfolio_provider.py::test_get_exposures_totals_match_known_fixture_values`.

## iframe endpoint-path evidence

The dashlet's inline Alpine client fetches `./api/portfolio/fixture-dates`, `./api/portfolio/exposures`, `./api/portfolio/concentration`, `./api/portfolio/compare` — the identical mount-relative paths and `operationId`s used by the agent-tool proxy. Verified by reading `dashlets/portfolio_exposure_dashlet.py`'s inline `<script>` and by the generic contract test `tests/test_dashlet_contract.py::test_root_page_uses_mount_relative_fetch_paths`, which asserts no absolute `fetch("/...")` path appears anywhere in the rendered page.

## Standalone browser verification (screenshot)

Captured live in a real browser against `uv run uvicorn dashlets.portfolio_exposure_dashlet:app` — not through Canvas, but a genuine interactive session against the real running dashlet (Observation Date `2026-08-18`, Comparison Date `2026-08-19`, after clicking **Load** then **Compare**):

![Portfolio Exposure Monitor, standalone browser, 2026-08-18 with 2026-08-19 comparison loaded](images/portfolio-exposure-standalone.png)

Every value on screen was independently cross-checked against a direct `curl` call to the same running server (`GET /api/portfolio/exposures?date=2026-08-18` and `GET /api/portfolio/compare?base_date=2026-08-19&compare_date=2026-08-18`) and matches exactly:

| On screen | Direct API | Match |
|---|---|---|
| Long Market Value: $11,050,000 | `long_market_value: 11050000.0` | ✅ |
| Short Market Value: $650,000 | `short_market_value: 650000.0` | ✅ |
| Net Market Value: $10,400,000 | `net_market_value: 10400000.0` | ✅ |
| Sector chart bars (Energy 0.5M, Financials 3.3M, Healthcare 1.95M, Industrials 1.55M, Technology 3.1M) | `sector_exposures[*].net_market_value` | ✅ |
| Top issuer: TechCore Inc, Technology, +21.2% | `net_weight_pct: 21.153846...` | ✅ |
| Meridian Bank, Financials, +17.3% | `net_weight_pct: 17.307692...` | ✅ |
| BioAxis Therapeutics, Healthcare, +12.0% | `net_weight_pct: 12.019231...` | ✅ |
| Sector Exposure Change: Energy +0.6%, Financials +0.3%, Healthcare -0.0%, Industrials -0.1% | `compare?base_date=2026-08-19&compare_date=2026-08-18` deltas | ✅ |

This confirms the full UI → fetch → FastAPI → provider → calculation → render path works correctly end to end in a real browser, including the Load/Compare interaction, chart rendering, and both tables. What it does **not** confirm is the Canvas-specific path (iframe mounting, control-panel status, the agent-tool proxy) — that's the remaining TODO below.

## Agent-tool endpoint-path evidence

**TODO — requires a live Canvas session (not completed in this session; no browser tool connected).**

To capture this evidence:

1. Open a Copilot session with this repository, invoke the `dashlet-studio` Canvas extension.
2. `select_dashlet(portfolio-exposure)`, then `start_dashlet`. Confirm the iframe loads and the sector chart / concentration table populate.
3. Ask Copilot each of the following, and record the tool call, arguments, and returned values:
   - *"Use the portfolio tool to get exposures for 2026-08-19."* → expect `get_portfolio_exposures`, net exposure ≈ $10,650,000.
   - *"Use the portfolio tool to show me the top 3 issuer concentrations for 2026-08-19."* → expect `get_top_concentrations(top_n=3)`, top result `TechCore Inc` at ≈22.5%.
   - *"Use the portfolio tool to compare exposure between 2026-08-18 and 2026-08-19."* → expect `compare_portfolio_exposures`, Technology sector delta ≈ +$150,000.
4. Confirm in the Canvas runtime diagnostics log that each call shows `Proxy request: GET http://127.0.0.1:<port>/api/portfolio/...` — the same host:port the iframe is pointed at (`dashletUrl` in the status payload) — proving the agent path and the iframe path hit the identical running process.

## Tool-isolation negative tests

**TODO — requires a live Canvas session.**

Suggested checks (mirroring `docs/evidence/treasury-reference.md`'s pattern):

- While `portfolio-exposure` is active, invoke a Treasury or Hello tool (e.g. `get_treasury_curve`) → expect rejection: `"Operation ... is not approved"`.
- While Treasury or Hello is active, invoke a Portfolio tool (e.g. `get_portfolio_exposures`) → expect the same rejection, confirming isolation holds in both directions.
- This isolation logic is already covered by an automated test (`ToolProxy allowlist switch isolates Hello and Treasury tools` in `tool-proxy.test.mjs`), but that test only exercises Hello↔Treasury switching, not Portfolio Exposure specifically — a live check (or a new automated test extending that pattern to three dashlets) would close this gap.

## Process-lifecycle results

**TODO — requires a live Canvas session.**

Suggested checks: `select_dashlet(portfolio-exposure)` from Hello or Treasury correctly stops the prior process (exit code 143 / SIGTERM) and starts a new Uvicorn process on a fresh port; `stop_dashlet` returns `activeDashletId` to `null` and clears `approvedOperations`; no orphaned process remains bound to the port after stop (`lsof -i :<port>`).

## Python test summary

```text
uv run pytest tests/test_portfolio_fixture.py tests/test_portfolio_provider.py tests/test_portfolio_exposure_dashlet.py -q
37 passed, 1 warning in 0.21s

uv run pytest -q   # full suite, includes the above plus generic contract validation
116 passed, 1 warning in 0.25s
```

## Node test summary

```text
npm test (.github/extensions/dashlet-studio): 41 passed, 0 failed
```

Includes `dashlet-registry.test.mjs` (registry shape, no cross-dashlet tool-id collisions) and the Portfolio-specific assertions added to `generated-tool-schemas.test.mjs` (`get_portfolio_exposures`/`get_top_concentrations` expose only optional `date`(+`top_n`); `compare_portfolio_exposures` requires `base_date`/`compare_date` and has no `data_mode`, unlike Treasury).

## Provenance example (sanitized)

```json
{
  "source": "synthetic-fixture",
  "source_url": null,
  "observation_date": "2026-08-19",
  "retrieved_at": "2026-08-26T20:14:07.919308Z",
  "data_mode": "fixture",
  "is_stale": false
}
```

## Canvas screenshot

**Not yet captured** — see the standalone screenshot above for a genuine, cross-verified browser capture of the dashlet itself. This section is specifically for the *Canvas-embedded* view (iframe + control-panel chrome), which still requires a live Copilot Canvas session. To capture: open Dashlet Studio Canvas with `portfolio-exposure` active, load a date, run a comparison, screenshot the page (crop out any transient local port/PID/loopback URL from the control-panel sidebar, matching the redaction already done for the Treasury screenshot), save as `docs/evidence/images/portfolio-exposure-canvas.png`, and link it here.

## Known limitations

- **No live Canvas verification yet** (agent-tool endpoint-path evidence, tool-isolation negative tests, process-lifecycle results, and the Canvas-embedded screenshot are all TODO above). The dashlet itself *is* now verified working end-to-end in a real browser (see "Standalone browser verification" above, with every displayed value cross-checked against the live API) — what remains is Canvas-specific: the iframe embedding, the control-panel chrome, and the agent-tool proxy path. **Deliberately deprioritized on 2026-08-26** to move on to Milestone 4's remaining business use cases rather than block on it — see `docs/PROGRESS.md` "Resume here" for the reasoning. Revisit once there are enough dashlets to make one combined live-Canvas evidence pass worthwhile.
- No live holdings provider exists for this dashlet — fixture-only, by design (see `docs/DATA_ACCESS.md` §2), not a gap to close later.
- Independent code review has not yet been completed for this dashlet (see `docs/PROGRESS.md` Milestone 4 evidence) — implemented directly by Claude Code this session, review still open.
- The generic OpenAPI-to-tool-schema generator does not carry `top_n`'s `ge=1, le=20` bounds into the Copilot-visible schema; FastAPI still enforces the real bound server-side with a 422 (verified above), so this is a schema-precision gap, not a safety gap.

## Related documents

- [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) — component boundaries and dual-use business-operation contract.
- [`docs/DASHLET_CONTRACT.md`](../DASHLET_CONTRACT.md), [`docs/DATA_ACCESS.md`](../DATA_ACCESS.md), [`docs/WEB_AUTHORING.md`](../WEB_AUTHORING.md), [`docs/TOOL_AUTHORING.md`](../TOOL_AUTHORING.md) — the contract this dashlet was built against.
- [`docs/PROGRESS.md`](../PROGRESS.md) — Milestone 4 checklist and evidence, including the open independent-review item.
- [`docs/evidence/treasury-reference.md`](treasury-reference.md) — the template this document follows, and the only dashlet so far with a completed live-Canvas evidence pass.
