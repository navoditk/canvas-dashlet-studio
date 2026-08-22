# Evidence: Treasury Reference Milestone

## Milestone name

Treasury Curve reference dashlet — explicit fixture/EOD provider-selection contract, Canvas agent-tool schemas, and mode-aware iframe refresh.

## Validation date

2026-08-21

## Commit SHA

`1286475` ("Complete Treasury mode-aware Canvas workflow") on branch `navoditk-automatic-lamp`, itself built directly on `5b0bcf7` ("Add explicit Treasury fixture and EOD modes"), which is the current tip of `navoditk-treasury-curve-reference`.

## Architecture exercised

```text
Copilot agent tool call ──┐
                          ├─▶ Canvas ToolProxy (allowlist + schema validation) ─┐
Canvas iframe fetch("./api/...") ─────────────────────────────────────────────┼─▶ FastAPI dashlet (dashlets/treasury_curve_dashlet.py)
                                                                               └─▶ Provider (fixture | Treasury.gov EOD)
```

Both consumers (iframe JavaScript and the Copilot agent) invoke the same three `agent-tool`-tagged FastAPI operations: `get_treasury_curve`, `get_treasury_curve_slopes`, `compare_treasury_curves`. See [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) sections 4–5 for the general dual-use contract this instance implements.

## Direct FastAPI verification summary

Ran the dashlet directly with `uv run uvicorn dashlets.treasury_curve_dashlet:app` on a loopback port and exercised it with `curl`, confirming:

| Check | Result |
|---|---|
| `GET /health` | `{"status":"ready"}` |
| `data_mode` required on all 3 Treasury operations | Confirmed via `app.openapi()` — `required: true` on every operation |
| `data_mode` enum | `TreasuryDataMode` component schema: `{"type":"string","enum":["fixture","eod"]}` |
| `date` parameter (curve, slopes) | Optional string, no format keyword in the live schema, described as `YYYY-MM-DD`, defaults to latest fixture date when omitted |
| `base_date` / `compare_date` (compare) | Both required strings, `YYYY-MM-DD` |
| Missing `data_mode` | `422` |
| Invalid `data_mode=live` | `422` with `"Input should be 'fixture' or 'eod'"` (no fixture fallback) |
| Untagged/internal routes (`/api/treasury/fixture-dates`, `/metadata`, `/`) | Present in OpenAPI but **not** tagged `agent-tool`, so never selected as tools |

## Fixture-mode result

```json
{
  "source": "synthetic-fixture",
  "source_url": null,
  "observation_date": "2026-08-19",
  "data_mode": "fixture",
  "is_stale": false
}
```

Curve, slopes (`2s10s`, `3m10y`, `5s30s`) and comparison endpoints all returned deterministic fixture values consistently across repeated calls.

## EOD-mode result

```json
{
  "source": "treasury-gov",
  "source_url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value_month=<redacted-month>",
  "observation_date": "2026-08-19",
  "data_mode": "eod",
  "is_stale": false
}
```

Confirmed live against the real Treasury.gov feed for curve and slopes endpoints — distinct values from the fixture set, correct `source`/`source_url`/`data_mode` provenance, no fixture data ever substituted.

## Screenshot

![Treasury Curve Monitor in EOD mode, showing the observation/comparison date controls, Data Mode selector, curve chart, 2s10s/3m10y slope cards, and yield/comparison tables](images/treasury-canvas-eod.png)

Captured 2026-08-21 from the live Dashlet Studio Canvas with the Treasury Curve dashlet active, Data Mode set to `eod`, observation date `2026-08-19` and comparison date `2026-08-18`. The Canvas control-panel sidebar (which exposed a transient local port, PID and loopback URL) was cropped out before saving. The dashlet's `provenanceText` line renders further down the page than this capture; its live value for this exact view is the sanitized EOD example already shown above under "EOD-mode result".

## iframe endpoint-path evidence

The Treasury dashlet's inline Alpine client fetches `./api/treasury/curve`, `./api/treasury/slopes`, `./api/treasury/compare` — the identical mount-relative paths and `operation_id`s used by the agent-tool proxy. Verified by reading `dashlets/treasury_curve_dashlet.py`'s inline `<script>` and by executing the real script in a Node `vm` sandbox (`tests/js/treasury-client-mode.test.mjs`, 6/6 passing) to confirm mode-change behavior end to end.

## Agent-tool endpoint-path evidence

Live Canvas session (`dashlet-studio` extension, Treasury Curve dashlet active) invoked all three tools directly as the agent:

- `get_treasury_curve(data_mode=fixture)` → fixture curve, correct provenance
- `get_treasury_curve_slopes(data_mode=fixture)` → `2s10s=-2bps`, `3m10y=-72bps`, `5s30s=+40bps`
- `compare_treasury_curves(base_date=2026-08-18, compare_date=2026-08-19, data_mode=fixture)` → deterministic per-maturity deltas
- `get_treasury_curve(data_mode=eod)` — see **Known limitations** below (request timed out at the proxy layer; confirmed via direct FastAPI call instead, no fallback occurred)

The Canvas runtime diagnostics log shows `Proxy request: GET http://127.0.0.1:<port>/api/treasury/curve?data_mode=...` for every one of these calls, using the exact same path the iframe uses.

## Tool-isolation negative tests

- `get_dashlet_summary` invoked while Treasury Curve was the active dashlet → rejected: `"Operation \"get_dashlet_summary\" is not approved"`.
- `get_dashlet_summary` invoked while Hello was active → succeeded normally (`{"title":"Hello Dashlet","message":"Smoke test successful", ...}`), confirming Hello Dashlet behavior is unaffected by the Treasury changes.

## Process-lifecycle results

Live Canvas session actions:

1. `select_dashlet(hello)` → Hello auto-started, healthy, `get_dashlet_summary` approved.
2. `select_dashlet(treasury-curve)` + `start_dashlet` → prior Hello process cleanly stopped (`exit code=143`, i.e. SIGTERM), new Treasury Uvicorn process started, health check passed, 3 Treasury operations approved.
3. `stop_dashlet` → Treasury process stopped cleanly (`exit code=143`), `activeDashletId` returned to `null`, `approvedOperations` emptied.
4. Confirmed no orphaned Uvicorn process remained bound to the session's dashlet port after stop (`lsof -i :<port>` returned nothing for this session's process once stopped).

## Python test summary

```text
uv run pytest -q
15 failed, 50 passed, 1 warning
```

All 15 failures are pre-existing and unrelated to this milestone's two bounded fixes — they stem from an earlier commit (`5b0bcf7`) that renamed the provenance field from `live` to `eod`/`fixture` without updating a subset of `tests/test_treasury_curve_dashlet.py` and `tests/test_treasury_provider.py` assertions. Confirmed identical failure count/names both before and after this session's changes via `git stash` A/B comparison. Not fixed here per explicit scope ("do not modify provider behavior, financial calculations, operation IDs, or process-management code").

## Node test summary

```text
npm test (.github/extensions/dashlet-studio): 34 passed, 0 failed
node --test tests/js/treasury-client-mode.test.mjs: 6 passed, 0 failed
```

New tests added this milestone: 7 in `treasury-tool-schemas.test.mjs` (enum/required/date-params/`additionalProperties`/`get_dashlet_summary`-untouched/operation-id-match/frozen-immutability) and 6 in `treasury-client-mode.test.mjs` (mode-change reload behavior, stale-response guarding, EOD-failure provenance safety).

## Provenance example (sanitized)

```json
{
  "source": "synthetic-fixture",
  "source_url": null,
  "observation_date": "2026-08-19",
  "retrieved_at": "2026-08-21T23:47:46Z",
  "data_mode": "fixture",
  "is_stale": false
}
```

```json
{
  "source": "treasury-gov",
  "source_url": "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml?data=daily_treasury_yield_curve&field_tdr_date_value_month=<redacted>",
  "observation_date": "2026-08-19",
  "retrieved_at": "2026-08-21T23:48:36Z",
  "data_mode": "eod",
  "is_stale": false
}
```

(Loopback ports and absolute local filesystem paths are intentionally omitted from all evidence above.)

## Known limitations

- **EOD proxy timeout, not a correctness bug:** live Treasury.gov EOD fetches took 8–19 seconds in this session, exceeding the Canvas `ToolProxy`'s existing `requestTimeoutMs: 5000` setting. The agent call surfaced as `"This operation was aborted"` rather than returning data — but it never fell back to fixture data, and a direct FastAPI call (bypassing only the proxy's client-side timeout) confirmed the EOD response completes successfully with correct `treasury-gov` provenance. This timeout is pre-existing process-management configuration, out of scope for this milestone's two bounded fixes, and is called out here as a real limitation rather than silently omitted.
- Capability input schemas for Treasury tools are a Milestone-2 compatibility bridge (see the `TODO` in `treasury-tool-schemas.mjs`) — a future milestone should derive these from approved OpenAPI operations generically instead of maintaining a manual per-operation map.
- No automated browser/DOM test harness exists; iframe mode-change behavior is verified via a Node `vm` sandbox executing the real inline script, not a real browser.
- 15 pre-existing Python test failures (see above) remain unresolved — out of scope for this milestone.
- 9 pre-existing `ruff` findings remain, all in `scripts/live_treasury_check.py`, unrelated to this milestone.
- No CI workflow exists yet in this repository (`.github/workflows/` is empty) — see [`docs/PROGRESS.md`](../PROGRESS.md) Resume-here section for the recommended first follow-up task.
- The genuine Canvas screenshot embedded above shows only the EOD-mode view; a fixture-mode screenshot was not captured in this session (optional per the original request).

## Related documents

- [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) — component boundaries and dual-use business-operation contract.
- [`docs/ROADMAP.md`](../ROADMAP.md) — staged execution plan this milestone completes Day 1–2 of.
- [`docs/PROGRESS.md`](../PROGRESS.md) — milestone checklist, evidence links and the `## Resume here` section for next steps.
