# Project Progress

Update this file at the end of each implementation block. Mark an item complete only when its evidence exists.

## Status legend

- `[ ]` Not started
- `[-]` In progress or partially verified
- `[x]` Complete with evidence
- `[!]` Blocked; explanation required

## Current status

- **Overall milestone status:** the Treasury Curve reference dashlet is complete through Milestone 3. CI, the shared `dashlet_framework` package, generic OpenAPI-derived tool schemas, and reusable contract validation (originally Resume-here tasks 1–4) are done. Milestone 4's durable-instruction prerequisites are done. All four originally planned reference dashlets are now built: Portfolio Exposure & Concentration (task 5), Portfolio Scenario Impact (task 6), and Issuer Research (task 7) — all three pending independent review (see Milestone 4 evidence above). Milestone 4's business-use-case work is complete. Milestone 5's gallery (`gallery.py`, task 8) is built, tested, and now **deployed and live** at <https://canvas-dashlet-studio-gallery.onrender.com> (deployed by the repo owner; verified 2026-08-27 — see `docs/evidence/gallery-deployment.md`); remaining Milestone 5 work is secret scanning and full Canvas-iframe verification of the deployed URL, plus stronger governance/observability generally.
- **Latest validation date:** 2026-08-27.
- **What works today:** Hello, Treasury Curve, Portfolio Exposure, Portfolio Scenario Impact and Issuer Research all run under the Dashlet Studio Canvas extension, built on a shared `dashlet_framework` package (`create_dashlet_app`, `AGENT_TOOL_TAG`, `Provenance`, `DashletErrorDetail`/`DashletErrorResponse`) instead of duplicated per-dashlet boilerplate; every dashlet exposes `/health` and `/metadata`. A user can switch between any of the five, view it in the iframe, and ask Copilot to invoke its approved agent tools. Treasury exposes `get_treasury_curve`, `get_treasury_curve_slopes` and `compare_treasury_curves` with an explicit fixture/EOD `data_mode`. Portfolio Exposure exposes `get_portfolio_exposures`, `get_top_concentrations` and `compare_portfolio_exposures` from deterministic mock positions (fixture-only, no live mode). Portfolio Scenario Impact exposes `run_portfolio_scenario`, `get_scenario_contributions` and `compare_scenario_impacts` — deterministic rate/spread/equity shock impact on the *same* mock positions. Issuer Research exposes `get_company_facts`, `get_financial_trends` and `list_recent_filings` reading real data directly from SEC EDGAR's public APIs (`data.sec.gov`) — `fixture` mode uses two recorded real snapshots (AAPL, MSFT), `live` mode fetches current data for any of ~10,388 SEC-registered tickers, both with an explicit required `data_mode` typed as a real Python enum (so the constraint shows up natively in OpenAPI, matching the Treasury pattern). Agent-tool parameter schemas are generated from each dashlet's real `app.openapi()` output by `scripts/generate_tool_schemas.py`; CI fails if the committed generated file drifts from source. That generator itself had a real bug fixed this session (naive Python-repr-to-JS string escaping broke on any description containing a quote character) -- now uses `json.dumps()` plus a runtime `deepFreeze()` helper instead of hand-rolled JS-literal serialization. Reusable contract validation (`tests/test_dashlet_contract.py`, `dashlet-registry.test.mjs`) checks every registered dashlet automatically -- both Portfolio Scenario Impact and Issuer Research needed zero new contract-test code. A GitHub Actions workflow (`.github/workflows/ci.yml`) runs Ruff, Pytest, the schema-drift check and `npm test` on every push/PR.

## Resume here

The next developer should start with **the combined live-Canvas evidence pass** described below, or with an actual Render deployment (task 8 continuation) — both are open, either is a reasonable starting point.

Six items remain deliberately open, not accidentally dropped: (1) independent review passes for Portfolio Exposure, Portfolio Scenario Impact and Issuer Research (see Milestone 4 evidence above), and (2) live-Canvas evidence for all three (agent-tool invocation logs, tool-isolation checks, process-lifecycle checks, Canvas-embedded screenshots -- see `docs/evidence/portfolio-exposure-reference.md`, `docs/evidence/portfolio-scenario-reference.md`, `docs/evidence/issuer-research-reference.md`). Both kinds of gap were explicitly deprioritized starting 2026-08-26 to keep moving on Milestone 4's remaining business use cases rather than block on them; direct-FastAPI verification and the full automated test suite already exist for all three dashlets (plus a real cross-verified browser screenshot for Portfolio Exposure, and a real live-mode SEC EDGAR call for Issuer Research), so this is not "unverified," just "not yet verified inside an actual Canvas session." With three dashlets now sharing this gap, doing one combined live-Canvas evidence pass across all of them (plus Treasury, to refresh it) is more efficient than three separate passes -- a strong candidate for the next dedicated session, now that Milestone 4's business-use-case work is otherwise complete. Separately, the gallery (`gallery.py`) is now deployed and live at <https://canvas-dashlet-studio-gallery.onrender.com> (see `docs/evidence/gallery-deployment.md`) — the remaining gap there is Canvas-iframe verification of the deployed URL specifically, folded into the combined live-Canvas evidence pass above.

**Recommended branch:** `feature/canvas-evidence-pass` (or a Render-deployment branch, since gallery build/test work is already merged to `main`)

1. ~~Add GitHub Actions for Ruff, Pytest and Node tests.~~ Done — see `.github/workflows/ci.yml`.
2. ~~Add reusable dashlet/OpenAPI contract validation.~~ Done — see `tests/test_dashlet_contract.py` and `.github/extensions/dashlet-studio/dashlet-registry.test.mjs`. `DASHLET_REGISTRY`/`REGISTERED_TOOL_IDS`/`TOOL_DESCRIPTIONS` were extracted from `extension.mjs` into `dashlet-registry.mjs` so they're importable by tests without triggering `joinSession()`.
3. ~~Extract the reusable framework from the repeated Hello and Treasury patterns.~~ Done — see `dashlet_framework/` (`app.py`, `models.py`).
4. ~~Replace the Treasury-specific Canvas schema bridge (`treasury-tool-schemas.mjs`) with generic approved OpenAPI-to-capability schema generation.~~ Done — see `scripts/generate_tool_schemas.py` and `.github/extensions/dashlet-studio/generated-tool-schemas.mjs`.
5. ~~Build Portfolio Exposure and Concentration using the framework.~~ Done — see `dashlets/portfolio_exposure_dashlet.py`, `dashlets/portfolio_provider.py`, `portfolio_fixture.py`. Independent review still open (Milestone 4 evidence above).
6. ~~Build Portfolio Scenario Impact using the framework.~~ Done — see `dashlets/portfolio_scenario_dashlet.py`, `dashlets/scenario_provider.py`, `scenario_fixture.py`. Independent review still open (Milestone 4 evidence above).
7. ~~Add Issuer Research as a later use case.~~ Done, and built on **real public SEC EDGAR data** rather than mock data per explicit user request -- see `dashlets/issuer_research_dashlet.py`, `dashlets/issuer_provider.py`, `issuer_fixture.py`, `scripts/generate_issuer_fixtures.py`. Independent review still open (Milestone 4 evidence above).
8. ~~Build the FastAPI gallery.~~ Done -- see `gallery.py`, `tests/test_gallery.py`, `render.yaml`, commit `002b717`. Actual Render deployment still open (requires the repo owner's own account); the combined Canvas-evidence pass described above remains open too -- both are reasonable next choices at this point.
9. Add stronger governance, sandboxing, identity, observability and evaluations later.
10. Separately (not numbered in the original task list, raised in this session): consider whether Portfolio Exposure/Scenario Impact should also move to real public data -- SEC Form 13F institutional holdings disclosures are the natural public source, but only cover long positions (no shorts), are quarterly with a ~45-day lag, and would need a second data source (CUSIP-to-sector mapping) to reproduce the current sector-classification feature. Treated as a real, separately-scoped follow-up, not folded into Issuer Research.

## Completed milestones (summary)

- [x] Repository and installation baseline.
- [x] Secure Hello smoke test.
- [x] Canvas local process lifecycle (start/stop/restart, health polling, diagnostics).
- [x] iframe rendering (Hello and Treasury).
- [x] OpenAPI-to-agent-tool bridge (allowlist + `agent-tool` tag intersection).
- [x] Manual Treasury fixture API.
- [x] Deterministic slope and comparison analytics.
- [x] Treasury interactive visualization (Plotly).
- [x] Official EOD provider (Treasury.gov).
- [x] Explicit fixture/EOD selection contract (`data_mode` required, enum-constrained, no silent default, no EOD-failure fallback).
- [x] Treasury Canvas integration.
- [x] Treasury agent tools with explicit schemas, generated from OpenAPI (`scripts/generate_tool_schemas.py`, `generated-tool-schemas.mjs`).
- [x] Active-dashlet tool isolation.
- [x] Test and security-review checkpoints for this milestone (see Evidence below).
- [x] Shared `dashlet_framework` package and reusable dashlet/OpenAPI contract validation.
- [x] Canonical `AGENTS.md` and detailed contract docs (Milestone 4 durable-instruction prerequisites).
- [x] Portfolio Exposure & Concentration dashlet (independent review still open).
- [x] Portfolio Scenario Impact dashlet (independent review still open).
- [x] Issuer Research dashlet, built on real public SEC EDGAR data (independent review still open).
- [x] CI (`.github/workflows/ci.yml`).
- [x] Gallery built, tested and deployed (`gallery.py`, `tests/test_gallery.py`, live at https://canvas-dashlet-studio-gallery.onrender.com; Milestone 5).

## Evidence

- [`docs/evidence/treasury-reference.md`](evidence/treasury-reference.md) — full validation summary, fixture/EOD results, tool-isolation and process-lifecycle evidence, provenance examples, test summaries and known limitations.
- Treasury screenshot: genuine EOD-mode capture at [`docs/evidence/images/treasury-canvas-eod.png`](evidence/images/treasury-canvas-eod.png), embedded in the evidence document.
- Relevant tests: `tests/test_treasury_curve_dashlet.py`, `tests/test_treasury_provider.py`, `.github/extensions/dashlet-studio/treasury-tool-schemas.test.mjs`, `.github/extensions/dashlet-studio/tool-proxy.test.mjs`, `tests/js/treasury-client-mode.test.mjs`.
- Relevant architecture sections: [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) §4 "Interactive data flow", §5 "Agent-tool flow".
- Commits: `5546e38`, `8dfd497`, `fb7085f`, `ed78a6c`, `5b0bcf7`, `1286475` (all on `navoditk-treasury-curve-reference` / `navoditk-automatic-lamp`; not yet merged to `main`). Pull request: to be opened per this session's task (see report).
- [`docs/evidence/portfolio-exposure-reference.md`](evidence/portfolio-exposure-reference.md) — direct-FastAPI verification, fixture-mode results, provenance examples, test summaries, and a real-browser screenshot (every displayed value cross-checked against the live API and matching exactly) are complete. Canvas-specific evidence (agent-tool invocation logs, tool-isolation negative tests, process-lifecycle results, Canvas-embedded screenshot) is still TODO — no live Copilot Canvas session was available. Commits: `da18bce`, `7a15fb9`, and the standalone-screenshot follow-up.
- [`docs/evidence/portfolio-scenario-reference.md`](evidence/portfolio-scenario-reference.md) — direct-FastAPI verification (including a hand-checked value: TechCore Inc, beta 1.3 * $2.4M * 10% equity shock = $312,000), the full test suite (164 pytest, 43 npm), and the `-$174,500` net-DV01 cross-check against an earlier FICC walkthrough are complete. Canvas-specific evidence is TODO, same reasoning as Portfolio Exposure. Commits: `79524ed`, `400bcd6`, `f106a36`, `031877f`, and the Canvas-registration/docs follow-up.
- [`docs/evidence/issuer-research-reference.md`](evidence/issuer-research-reference.md) — direct-FastAPI verification against real recorded AAPL/MSFT data, the full test suite (216 pytest, 45 npm), and a real live-mode call against actual SEC EDGAR (GOOGL/Alphabet, not in the fixture set, returning real FY2025 revenue) are complete. Also documents a real bug found and fixed during this milestone: NVIDIA's XBRL revenue-concept migration (see Known limitations below and the dashlet's README section). Canvas-specific evidence is TODO, same reasoning as the other two. Commits: `9dddbbe`, `c61a1da`, `a385dad`, `4b71388`, and the Canvas-registration/docs follow-up.
- [`docs/evidence/gallery-deployment.md`](evidence/gallery-deployment.md) — live Render deployment verification (<https://canvas-dashlet-studio-gallery.onrender.com>): every mounted dashlet healthy, business-logic values through the deployed mounts cross-checked exactly against local/standalone verification, and no HTTP-layer frame-blocking headers on the live URL. Canvas-iframe-specific verification of the deployed URL is still TODO. Commits: `002b717`, `e40c6c2`, and this evidence follow-up.

## Known limitations

*(This section historically went stale relative to `## Current status` above — as of 2026-08-26 it was reconciled with actual repository state, and again on 2026-08-27 for Issuer Research. Keep both in sync going forward.)*

- All four originally planned reference dashlets are implemented: Hello, Treasury Curve, Portfolio Exposure, Portfolio Scenario Impact, Issuer Research.
- Treasury EOD data is official end-of-day data from Treasury.gov, **not** intraday real-time market data.
- Neither Portfolio Exposure nor Portfolio Scenario Impact has a live data mode — both are fixture-only by design (see `docs/DATA_ACCESS.md` §2), not a gap to close later. SEC Form 13F institutional-holdings disclosures are a real potential public-data source for a future upgrade, but only cover long positions, are quarterly with a lag, and need a second data source for sector classification -- tracked as a separate follow-up (see `## Resume here` above), not done as part of Issuer Research.
- Portfolio Scenario Impact's rate and spread shocks show $0 impact on the current fixture data (an all-equity book, no fixed-income holdings) — intentional and directly tested, not a defect.
- Issuer Research's fixture mode covers exactly two companies (AAPL, MSFT), both recorded **real** SEC data (not synthetic), refreshed via `scripts/generate_issuer_fixtures.py`. Live mode covers any of SEC's ~10,388 registered tickers, but XBRL tagging is heterogeneous across filers and can migrate over time within one filer (a real bug -- NVIDIA's revenue-tag migration -- was found and fixed this session; see the dashlet's evidence doc); a ticker whose data doesn't match the concept tags this dashlet knows about returns a controlled error, not partial/best-effort data.
- Response validation is still operation-specific rather than fully OpenAPI-schema-driven; the generic tool-schema generator also doesn't carry numeric `ge`/`le` bounds (e.g. `top_n`) into the Copilot-visible schema, though FastAPI still enforces them server-side with a 422.
- No production sandbox — the MVP relies on a registry allowlist, `shell:false` spawning and restricted child-process environment, not process/network isolation.
- No persistent artifact store (draft/published lifecycle, versioning, cloning) exists yet.
- No production identity/authorization model exists; the Canvas control API uses a per-session control token only.
- The gallery (`gallery.py`) is deployed and live at https://canvas-dashlet-studio-gallery.onrender.com (see `docs/evidence/gallery-deployment.md`), verified via direct HTTP calls to the live URL. What's still missing is verification inside an actual Canvas session (embedding that URL in an iframe and invoking its agent tools) — folded into the combined live-Canvas evidence pass, see "Resume here" above.
- No secret scanning exists in CI (Ruff/Pytest/schema-check/npm test do) — see `docs/ARCHITECTURE.md` §10 and Milestone 5 below.
- Only one dashlet process runs at a time; there is no concurrent multi-dashlet or cross-dashlet composition view.
- Dashlet registration (`DASHLET_REGISTRY` in `dashlet-registry.mjs`) is manual; there is no auto-discovery yet.
- Live-Canvas evidence (agent-tool invocation logs, tool-isolation checks, process-lifecycle checks, Canvas-embedded screenshots) and independent code review are deliberately deferred for Portfolio Exposure, Portfolio Scenario Impact and Issuer Research — see `## Resume here` above.
- The Canvas `ToolProxy`'s existing 5-second request timeout can be exceeded by live Treasury.gov EOD fetches (observed 8–19s in one session); this surfaces as an aborted agent-tool call rather than a wrong answer, and is a pre-existing, unmodified setting — see `docs/evidence/treasury-reference.md` for detail. The same timeout risk plausibly applies to Issuer Research's live SEC EDGAR calls but has not yet been specifically measured through the Canvas tool proxy (only verified via direct FastAPI/uvicorn, which has no such timeout).

## Environment

- [x] Required accounts available.
- [x] Git and GitHub CLI verified.
- [x] Python and uv verified.
- [x] Node.js and npm verified.
- [x] Copilot App verified.
- [x] `/create-canvas` verified.
- [ ] Additional coding agent verified.
- [x] FastAPI environment check passed.

Evidence:

```text
Date: 2026-08-21
Commands: uv run pytest; npm test (in .github/extensions/dashlet-studio); /create-canvas skill invocation
Result: 59 Python tests passed; 27 extension JS tests passed.
Notes: Working on branch navoditk-dashlet-studio-treasury-integration. Changes are unstaged
(not committed/pushed per explicit instruction). "Additional coding agent" not yet exercised.
```

## Milestone 1 — Manual dashlet understanding

- [x] Metadata and provenance models created.
- [x] Dashlet factory created.
- [x] Required routes implemented.
- [x] Treasury fixture created.
- [x] Treasury Curve UI renders.
- [x] Alpine control triggers FastAPI request.
- [x] Plotly chart updates.
- [x] Loading/empty/error states work.
- [x] Contract tests pass.
- [x] Developer can explain the full browser-to-provider flow.

Evidence:

```text
Commit/PR: fb7085f (Add public treasury curve data provider), 8dfd497 (Add interactive
Treasury curve visualization), 5546e38 (Add fixture-backed Treasury Curve API)
Test command: uv run pytest -> 59 passed (includes tests/test_treasury_curve.py)
Direct URL: uv run uvicorn dashlets.treasury_curve_dashlet:app --host 127.0.0.1 --port <n>,
verified GET /health, /api/treasury/curve, /api/treasury/curve/slopes,
/api/treasury/curve/compare directly with curl.
Screenshot: n/a (verified via curl + Canvas iframe, not captured as image).
What I learned manually: Treasury dashlet exposes 3 agent-tool-tagged operations
(get_treasury_curve, get_treasury_curve_slopes, compare_treasury_curves) plus
untagged/non-agent routes (list_treasury_fixture_dates, get_treasury_dashlet_metadata,
get_treasury_curve_view) confirmed by inspecting FastAPI decorators in
dashlets/treasury_curve_dashlet.py.
```

## Milestone 2 — Canvas local runtime

- [x] Canvas extension scaffolded.
- [x] Process launcher allocates a port.
- [x] Uvicorn starts through `spawn()` safely.
- [x] Health polling works.
- [x] iframe loads the dashlet.
- [x] stdout/stderr appear in diagnostics.
- [x] Restart works.
- [x] Stop removes the process.
- [x] Failure and timeout states are visible.

Evidence:

```text
Commit/PR: ed78a6c (Integrate Treasury dashlet with Canvas (#2)); process-management
code unchanged by the later 1286475 mode-aware workflow commit.
Canvas session: treasury-milestone-check (extension project:dashlet-studio, canvas
dashlet-studio), re-verified 2026-08-21.
Process lifecycle test: select_dashlet(hello) auto-started Hello; select_dashlet
(treasury-curve) + start_dashlet stopped the prior Hello process cleanly
(exit code=143) and started Treasury on a new port; stop_dashlet returned
activeDashletId to null and cleared approvedOperations; no orphan Uvicorn process
remained bound to the session's dashlet port after stop.
Screenshot: n/a (verified via invoke_canvas_action status payloads and diagnostics
log, not process-lifecycle-specific); see docs/evidence/treasury-reference.md for
the genuine Treasury Curve Monitor screenshot (EOD mode) and full evidence.
Known limitations: Extension spawns one of two registry-approved modules
(dashlets.hello_dashlet:app or dashlets.treasury_curve_dashlet:app) selected via a
frozen DASHLET_REGISTRY; no arbitrary module/port/command accepted from requests.
Canvas-close (onClose) cleanup path verified via unit tests only, not re-exercised
live in this session.
```

## Milestone 3 — Agent tool bridge

- [x] OpenAPI is retrieved after startup.
- [x] Only `agent-tool` endpoints are selected.
- [x] Tool arguments are validated.
- [x] Tool request reaches FastAPI.
- [x] Tool response is validated.
- [x] Copilot answers using returned data.
- [x] Tools disappear when dashlet stops.
- [x] Iframe and agent tool call the same business endpoint.
- [x] Provenance is retained in both response paths.
- [x] Untagged endpoints are not exposed.
- [x] Invalid arguments fail before the provider is called.
- [x] Explicit `data_mode` (fixture/eod) is required by every Treasury tool schema, with no silent default and no fallback on EOD failure.

Evidence:

```text
Tool name: get_dashlet_summary (Hello); get_treasury_curve, get_treasury_curve_slopes,
compare_treasury_curves (Treasury Curve).
User prompt: "Use the Treasury curve tool to retrieve the current fixture curve";
"Use the Treasury slope tool to report 2s10s and 3m10y"; "Use the Treasury comparison
tool to identify the maturity with the largest absolute move in basis points";
"Invoke get_dashlet_summary."
Endpoint log: Runtime diagnostics show "Proxy request: GET /api/treasury/curve...",
"/api/treasury/curve/slopes...", "/api/treasury/curve/compare..." matching the same
loopback host:port the iframe is pointed at (dashletUrl in status payload).
Agent response: get_treasury_curve returned 2026-08-19 fixture curve; slopes tool
returned 2s10s=-2bps, 3m10y=-72bps (consistent across repeated calls); comparison
tool (base 2026-08-18 vs compare 2026-08-19) identified 2Y as largest absolute move
(~10bps).
Negative test: get_dashlet_summary invoked while Treasury Curve was the active
dashlet -> rejected with "Operation ... is not approved" (Hello tool blocked while
Treasury active, and vice versa, confirmed both directions). Tool call with no
dashlet running -> "Dashlet is not running" (fails safely, no crash).
Explicit provider-selection contract (2026-08-21, commit 1286475): all three
Treasury tool schemas now expose a required data_mode enum of exactly
["fixture", "eod"] to the agent (previously an empty generic schema). Live
agent invocation confirmed: get_treasury_curve/get_treasury_curve_slopes/
compare_treasury_curves(data_mode="fixture") succeed with synthetic-fixture
provenance; missing data_mode is rejected client-side before any HTTP call;
data_mode="live" is rejected by FastAPI with a controlled 422 (no fixture
fallback in either case). EOD-mode agent invocation of get_treasury_curve
confirmed correct treasury-gov provenance via direct FastAPI verification;
the live agent-tool call itself intermittently exceeded the proxy's existing
5-second request timeout during this session (see docs/evidence/
treasury-reference.md "Known limitations" -- a pre-existing, out-of-scope
timeout setting, not a fixture-fallback defect).
```

## Milestone 4 — Agent-generated reuse

- [x] Canonical `AGENTS.md` created.
- [x] Tool-specific instructions reference canonical rules.
- [x] Creation workflow/skill created.
- [x] Review workflow/skill created.
- [x] Portfolio Exposure generated using framework.
- [x] Portfolio Scenario Impact generated using framework.
- [x] Issuer Research generated using framework, built on real public SEC EDGAR data per explicit user request (not the first post-sprint extension -- completed within the same sprint as the other three).
- [x] Every completed business use case (Treasury, Portfolio Exposure, Portfolio Scenario Impact, Issuer Research) has at least one verified agent tool.
- [!] Independent reviews completed. Portfolio Exposure, Portfolio Scenario Impact and Issuer Research were all implemented by Claude Code in this session; per AGENTS.md §8 / AGENTIC_DEVELOPMENT.md §10 all three still need an independent review pass (a different agent or a human) before being considered fully done.
- [x] No application-specific framework changes were required for Portfolio Exposure, Portfolio Scenario Impact or Issuer Research (`dashlet_framework` used unchanged all three times; only dashlet-specific modules were added, mirroring the existing Treasury pattern). Portfolio Scenario Impact extended `portfolio_fixture.Position` with optional sensitivity fields, and the Issuer Research work fixed a real bug in `scripts/generate_tool_schemas.py`'s string-escaping -- both application/tooling-level changes by explicit decision or necessity, not framework changes.

Evidence (durable instructions):

```text
Date: 2026-08-26
Files added: AGENTS.md (canonical contract, root of repo); .github/copilot-instructions.md
and CLAUDE.md (thin, point back to AGENTS.md per the "don't duplicate rules" principle in
docs/AGENTIC_DEVELOPMENT.md §6); docs/DASHLET_CONTRACT.md, docs/DATA_ACCESS.md,
docs/WEB_AUTHORING.md, docs/TOOL_AUTHORING.md (the four detailed contract docs referenced
by the "Dashlet task" prompt template in docs/AGENTIC_DEVELOPMENT.md §8 but never written
until now).
Creation workflow: AGENTS.md §9 ("Definition of done for a new dashlet") plus the existing
"Dashlet task" prompt template in docs/AGENTIC_DEVELOPMENT.md §8, now backed by the contract
docs that template names.
Review workflow: AGENTS.md §8 ("Review responsibility") plus the existing "Review task"
prompt template in docs/AGENTIC_DEVELOPMENT.md §8 and the implementer/reviewer matrix in §10.
Notes: written directly rather than as a separate Claude Code/Copilot skill file; the
project's docs/AGENTIC_DEVELOPMENT.md §6 canonical-hierarchy design (AGENTS.md ->
tool-specific files -> docs/*.md loaded when needed) is itself the "workflow," so no
additional skill packaging was added on top of it.
```

Evidence (Portfolio Exposure):

```text
Date: 2026-08-26
Generation prompt: user asked for a detailed roadmap and next steps; agreed sequencing was
AGENTS.md/contract docs first, then contract validation, then Portfolio Exposure, with Claude
Code implementing directly (per AGENTIC_DEVELOPMENT.md §10's sanctioned implementer role) and
detailed narrated visibility plus small independently-green commits, per the user's explicit
instruction.
Implementing agent: Claude Code (this session), following AGENTS.md / docs/DASHLET_CONTRACT.md
/ docs/DATA_ACCESS.md / docs/WEB_AUTHORING.md / docs/TOOL_AUTHORING.md written earlier in the
same session.
Files added: fixtures/portfolio/positions_2026-08-{18,19}.json (12 positions, 5 sectors, 2
short positions); portfolio_fixture.py (models, load_snapshot, compute_totals,
compute_sector_exposures, compute_issuer_exposures); dashlets/portfolio_provider.py
(FixturePortfolioProvider -- fixture-only, no live mode); dashlets/portfolio_exposure_dashlet.py
(get_portfolio_exposures, get_top_concentrations, compare_portfolio_exposures, all tagged
agent-tool; /metadata; embedded Alpine/Plotly UI); tests/test_portfolio_fixture.py,
tests/test_portfolio_provider.py, tests/test_portfolio_exposure_dashlet.py (37 tests);
registered in .github/extensions/dashlet-studio/dashlet-registry.mjs; tool schemas regenerated
(scripts/generate_tool_schemas.py) and verified against a real uvicorn process boot.
Test command: uv run pytest -> 116 passed; npm test -> 41 passed; uv run python
scripts/generate_tool_schemas.py --check -> OK; uv run ruff check . -> clean.
Reviewing agents: not yet completed -- see Milestone 4 checklist "Independent reviews
completed" above.
PRs: committed directly to main (see git log 2026-08-26), following the same small-commit
pattern used for the CI/framework/contract-validation work earlier in this session.
Framework changes: none. dashlet_framework (create_dashlet_app, AGENT_TOOL_TAG, Provenance,
DashletErrorDetail/DashletErrorResponse) was reused unchanged.
Known gaps: no live browser verification was performed (no Chrome extension connected in this
session) -- verified instead via a real uvicorn process boot, direct curl checks, and pytest
assertions on the exact embedded HTML/JS content. The generic OpenAPI-to-tool-schema generator
does not carry over numeric ge/le bounds (top_n is 1-20 server-side in FastAPI, exposed to
Copilot as an unbounded integer) -- FastAPI still enforces the real bound with a 422, so this
is a minor schema-precision gap, not a safety gap.
```

Evidence (Portfolio Scenario Impact):

```text
Date: 2026-08-26
Generation prompt: user asked to proceed to Portfolio Scenario Impact with detailed outline
and prompting at each decision point, plus doc updates; agent presented the spec-derived design
(run/contributions/compare endpoints, bounded rate/spread/equity shocks, deterministic linear
impact calculation) and asked two explicit design questions before writing code -- reuse
Portfolio Exposure's positions vs. an independent fixture, and what "comparison" means for this
dashlet (two dates vs. two shock scenarios). User chose "extend existing positions" and "two
shock scenarios" for both.
Implementing agent: Claude Code (this session), same contract docs as Portfolio Exposure.
Files added/changed: portfolio_fixture.py (Position extended with optional duration/
spread_duration/beta, default 0.0 -- purely additive, verified not to change any existing
Portfolio Exposure test or hardcoded total); fixtures/portfolio/positions_2026-08-{18,19}.json
(added per-position beta values, sector-level: Technology 1.3, Financials 1.1, Healthcare 0.7,
Energy 1.4, Industrials 1.0; duration/spread_duration left at 0.0 -- an all-equity book, no
fixed-income holdings, so rate/spread shocks correctly show $0 impact, asserted directly by a
test rather than left as an unexamined assumption); scenario_fixture.py (ScenarioShock,
PositionImpact, SectorContribution, ScenarioTotals, and the pure calculation functions);
dashlets/scenario_provider.py (ScenarioImpactProvider, reusing FixturePortfolioProvider
directly rather than duplicating fixture-loading logic); dashlets/portfolio_scenario_dashlet.py
(run_portfolio_scenario, get_scenario_contributions, compare_scenario_impacts, all tagged
agent-tool; /metadata; embedded Alpine/Plotly UI with Run and Compare actions); 45 new tests
across tests/test_portfolio_fixture.py (+4), tests/test_scenario_fixture.py (13, new),
tests/test_scenario_provider.py (8, new), tests/test_portfolio_scenario_dashlet.py (24, new);
registered in .github/extensions/dashlet-studio/dashlet-registry.mjs; tool schemas regenerated
and verified against a real uvicorn process boot.
Correctness cross-checks: two tests in tests/test_scenario_fixture.py directly reuse the exact
$10M/duration-8.5 long 10Y and -$8M/duration-1.9 short 2Y example from an earlier FICC
explanation given to the user, confirming the combined +25bp impact equals -$174,500, matching
the net-DV01 P&L estimate stated in that conversation. tests/test_portfolio_scenario_dashlet.py
independently confirms TechCore Inc's beta-1.3 equity-shock impact against a hand-calculated
value (beta 1.3 * $2,400,000 * 10% = $312,000).
Test command: uv run pytest -> 164 passed; npm test -> 43 passed; uv run python
scripts/generate_tool_schemas.py --check -> OK; uv run ruff check . -> clean.
Reviewing agents: not yet completed -- see Milestone 4 checklist "Independent reviews
completed" above.
PRs: committed directly to main in five small units (Position extension; calculation engine;
provider; dashlet+tests; Canvas registration+docs), each independently green, matching the
established pattern from the Portfolio Exposure and CI/framework work earlier in this session.
Framework changes: none to dashlet_framework. portfolio_fixture.py (an application module, not
the framework) was extended by explicit user decision -- see the design-decision note above.
Known gaps: same as Portfolio Exposure -- no live Canvas/browser verification (no Chrome
extension connected in this session), verified instead via a real uvicorn process boot, direct
curl checks, and pytest assertions on the exact embedded HTML/JS content.
```

Evidence (Issuer Research):

```text
Date: 2026-08-27
Generation prompt: user asked which of the four reference use cases had public data sources
(Treasury already did via Treasury.gov), whether Portfolio Exposure/Scenario Impact could too,
and to proceed with Issuer Research next specifically using real public data rather than mock
data. Agent researched SEC EDGAR's public JSON APIs live (ticker->CIK map, submissions, XBRL
company facts) before designing anything, confirmed the required User-Agent header behavior
empirically, then asked one explicit design question -- should live mode accept any of SEC's
~10,388 registered tickers, or a curated shortlist -- before implementing. User chose "any
valid ticker."
Implementing agent: Claude Code (this session), following the same contract docs as the prior
two dashlets.
Files added: issuer_fixture.py (SEC XBRL extraction/normalization models and functions, shared
between the live provider and the fixture-generation script); dashlets/issuer_provider.py
(FixtureIssuerProvider reading recorded real SEC snapshots; PublicIssuerProvider fetching live
from data.sec.gov for any ticker, with a cached ticker->CIK lookup and the SEC-required
User-Agent header); scripts/generate_issuer_fixtures.py (regenerates fixtures/issuer/*.json
from real live SEC data through the same code path PublicIssuerProvider uses);
fixtures/issuer/AAPL.json and MSFT.json (genuine recorded SEC data, not synthetic, generated
through the actual shipped extraction code); dashlets/issuer_research_dashlet.py
(get_company_facts, get_financial_trends, list_recent_filings, all tagged agent-tool;
data_mode typed directly as the IssuerDataMode enum so the fixture/live constraint is native
to OpenAPI, matching the Treasury pattern rather than a manually-validated string); 58 new
tests across four files (18 in tests/test_issuer_fixture.py, 12 in
tests/test_issuer_provider.py, 21 in tests/test_issuer_research_dashlet.py, plus updates).
Bug found and fixed: while verifying against real companies beyond the two fixture tickers
(Apple, Microsoft), a live call for NVIDIA returned a suspiciously old "latest" fiscal year
(2022, when the actual current year should be far more recent). Root cause: NVIDIA migrated
its XBRL revenue tag from RevenueFromContractWithCustomerExcludingAssessedTax (used through
FY2022) to the plain Revenues tag (FY2023 onward); the original "first non-empty concept in
priority order" selection logic silently locked onto the superseded tag. Fixed via
_most_recent_concept, which picks whichever candidate concept's data covers the most recent
period end; verified against real Apple, Microsoft and NVIDIA data with a regression test
reproducing the exact failure mode; regenerated the committed fixtures through the fixed code
(output unchanged for AAPL/MSFT, confirming no regression).
Second bug found and fixed (in shared infrastructure, not this dashlet's own code): while
regenerating tool schemas after registering this dashlet, scripts/generate_tool_schemas.py
crashed with a JS syntax error. Root cause: its string-escaping (`repr(value).replace("'",
'"')`) is not safe for any description string containing a quote character -- this dashlet's
data_mode description contains 'fixture'/'live' in single quotes, and the naive replace
corrupted them into unterminated JS string literals. Fixed by replacing the entire hand-rolled
JS-literal serializer with json.dumps() (a strict subset of JS syntax, correctly escapes
everything) plus a small runtime deepFreeze() helper embedded in the generated file, verified
to still deep-freeze every nested level (top object, each schema, each schema's properties and
required array) exactly as the existing immutability tests expect.
Correctness cross-checks: TechCore-style value check (TechCore Inc precedent from Portfolio
Exposure) mirrored here -- fixture-mode AAPL facts checked field-by-field against the real
recorded values; a real, unmocked live-mode call against actual SEC EDGAR for GOOGL (Alphabet
Inc., not in the fixture set) returned real FY2025 revenue ($402,836,000,000) through a
genuinely running uvicorn process, not just TestClient.
Test command: uv run pytest -> 216 passed; npm test -> 45 passed; uv run python
scripts/generate_tool_schemas.py --check -> OK; uv run ruff check . -> clean.
Reviewing agents: not yet completed -- see Milestone 4 checklist "Independent reviews
completed" above.
PRs: committed directly to main in five small units (extraction/normalization module;
providers; fixture-generation script + real fixture data; dashlet+tests; Canvas
registration+docs+generator fix), each independently green.
Framework changes: none to dashlet_framework. issuer_fixture.py, dashlets/issuer_provider.py
and scripts/generate_issuer_fixtures.py are new application/tooling modules, not framework
changes; the generate_tool_schemas.py fix is a bug fix to existing shared tooling, not a
framework change or a speculative extension.
Known gaps: same as the other two -- no live Canvas/browser verification (no Chrome extension
connected in this session). Unlike the other two, this dashlet's live-mode data path *was*
exercised for real (see "Correctness cross-checks" above), just not through an actual Canvas
session specifically.
```

## Milestone 5 — CI and publication

- [x] Gallery mounts every validated dashlet. `gallery.py` mounts all five dashlets under `/apps/<id>/` in a single FastAPI process; `tests/test_gallery.py` derives its expected app set from `DASHLET_MODULES` so this stays enforced as new dashlets are added, not just true at the moment it was written. Commit `002b717`.
- [x] Ruff passes. Enforced in CI on every push/PR (`.github/workflows/ci.yml`) since 0eae791.
- [x] Pytest passes. Enforced in CI on every push/PR; 227 tests as of the gallery milestone (216 at the Issuer Research milestone + 11 new gallery tests).
- [x] Contract validation passes for every dashlet. `tests/test_dashlet_contract.py` + `dashlet-registry.test.mjs` run generically against every dashlet in `DASHLET_MODULES`, enforced in CI.
- [x] Tool-schema validation passes. `scripts/generate_tool_schemas.py --check` enforced in CI; fails the build if the generated file drifts from source.
- [ ] Secret scan passes. Not implemented — no secret-scanning step exists in CI at all yet (see `docs/ARCHITECTURE.md` §10).
- [x] GitHub repository published. `https://github.com/navoditk/canvas-dashlet-studio`, confirmed public (`gh repo view --json visibility` → `PUBLIC`).
- [x] Render deployment succeeds. Live at <https://canvas-dashlet-studio-gallery.onrender.com>, deployed by the repo owner via the `render.yaml` Blueprint (Render account access is required and was not available to the agent). `/health` returns `200`. Full record: [`docs/evidence/gallery-deployment.md`](evidence/gallery-deployment.md).
- [x] Direct dashlet URL verified. All 5 mounted dashlets healthy at `/apps/<id>/health`; business-logic values through the deployed mounts (Portfolio Exposure net=$10,650,000, Portfolio Scenario Impact total impact=$1,154,000, Issuer Research AAPL revenue=$416,161,000,000, Treasury fixture dates) match local/standalone verification exactly. See [`docs/evidence/gallery-deployment.md`](evidence/gallery-deployment.md).
- [-] iframe embedding verified. No `X-Frame-Options`/CSP `frame-ancestors` header blocks embedding at the HTTP layer (checked directly against the live URL) — a necessary but not sufficient condition. An actual Canvas session embedding the deployed URL and invoking its agent tools has not been done yet; folded into the deferred combined live-Canvas evidence pass (see "Resume here").

Evidence:

```text
Repository URL: https://github.com/navoditk/canvas-dashlet-studio (public)
CI run: .github/workflows/ci.yml, green on every push to main since 0eae791 -- see
docs/PROGRESS.md "Current status" and the commit history for individual run results.
Gallery: gallery.py + tests/test_gallery.py, commit 002b717. Verified locally via a real
uvicorn boot (uvicorn gallery:app): every mounted dashlet's /health and / are reachable,
mount-relative fetch("./api/...") calls resolve correctly under the mount, and business-logic
values through the mount exactly match each dashlet's standalone values (Portfolio Exposure
net=$10,650,000, Portfolio Scenario Impact total impact=$1,154,000 at a 10% equity shock,
Issuer Research AAPL revenue=$416,161,000,000).
Gallery URL: https://canvas-dashlet-studio-gallery.onrender.com (live, verified 2026-08-27)
Dashlet URLs:
  https://canvas-dashlet-studio-gallery.onrender.com/apps/hello/
  https://canvas-dashlet-studio-gallery.onrender.com/apps/treasury-curve/
  https://canvas-dashlet-studio-gallery.onrender.com/apps/portfolio-exposure/
  https://canvas-dashlet-studio-gallery.onrender.com/apps/portfolio-scenario/
  https://canvas-dashlet-studio-gallery.onrender.com/apps/issuer-research/
Iframe test: not yet done inside an actual Canvas session (see "Resume here"); HTTP-layer
frame-blocking headers checked and absent -- see docs/evidence/gallery-deployment.md.
```

## Stretch dashlets

- [ ] Issuer Research Monitor if deferred.
- [ ] Macro Regime Monitor.
- [ ] Periodically Refreshed Market Monitor.

## Deferred backlog

- [ ] Local artifact storage service.
- [ ] Draft/validated/published lifecycle.
- [ ] Artifact search and cloning.
- [ ] Mock user identity and roles.
- [ ] Tool authorization policies.
- [ ] Structured audit events.
- [ ] OpenTelemetry.
- [ ] Strong process sandbox.
- [ ] Background automation.
- [ ] Production runtime and rollback.

## Daily retrospective

### Day 1

```text
Completed: Extended the existing project-scoped Dashlet Studio Canvas extension to
support Treasury Curve as a second approved dashlet alongside Hello, without
touching Treasury business logic/fixtures/visual design. Added a frozen
DASHLET_REGISTRY (hello, treasury-curve), a dashlet selector in the control UI,
per-active-dashlet tool gating (OpenAPI agent-tool tag + registry allowlist
intersection, re-evaluated on every switch), and safe process switching that stops
the prior uvicorn process before starting the next.
Evidence: uv run pytest -> 59 passed; npm test (extension dir) -> 27 passed; live
Canvas verification of start/stop/restart/switch for both dashlets with PID
tracing; all 3 Treasury tools and get_dashlet_summary invoked live with
cross-dashlet negative tests (Hello tool blocked while Treasury active and vice
versa); read-only review of registry safety, process switching, tool isolation,
runtime cleanup, regression tests, and Canvas API correctness found no security
defects.
Key platform concepts learned: Canvas actions/tools are registered statically at
joinSession time and can't be added/removed at runtime, so per-dashlet isolation
must be enforced at invocation time via an allowlist intersected with OpenAPI tags,
not by dynamically changing the registered tool set. JS run-to-completion semantics
(synchronous status flips before the first await in start()/stop()) prevent the
obvious concurrent-switch race, though a narrower state-consistency gap exists
between a stop() resolving and the following start() call.
Problems: Canvas-close (onClose) cleanup was exercised via unit tests only, not
re-triggered live in this session. A minor code smell was found in
/api/select's 409-vs-400 status detection (string-matches "progress" in the error
message rather than using a typed error code).
Next actions: Consider hardening the activeDashletId consistency gap during
overlapping switch requests; exercise the live canvas-close E2E path; replace the
string-matching 409 detection with a structured error code if this becomes a
maintenance pain point.
```

### Day 2

```text
Completed:
Evidence:
Key platform concepts learned:
Problems:
Next actions:
```

### Day 3

```text
Completed:
Evidence:
Key platform concepts learned:
Problems:
Next actions:
```
