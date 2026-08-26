# Project Progress

Update this file at the end of each implementation block. Mark an item complete only when its evidence exists.

## Status legend

- `[ ]` Not started
- `[-]` In progress or partially verified
- `[x]` Complete with evidence
- `[!]` Blocked; explanation required

## Current status

- **Overall milestone status:** the Treasury Curve reference dashlet is complete through Milestone 3. CI, the shared `dashlet_framework` package, generic OpenAPI-derived tool schemas, and reusable contract validation (originally Resume-here tasks 1–4) are done. Milestone 4's durable-instruction prerequisites are done, and Portfolio Exposure & Concentration (task 5) is now also done, pending independent review (see Milestone 4 evidence above). Remaining Milestone 4 work: Portfolio Scenario Impact, Issuer Research.
- **Latest validation date:** 2026-08-26.
- **What works today:** Hello, Treasury Curve and Portfolio Exposure all run under the Dashlet Studio Canvas extension, built on a shared `dashlet_framework` package (`create_dashlet_app`, `AGENT_TOOL_TAG`, `Provenance`, `DashletErrorDetail`/`DashletErrorResponse`) instead of duplicated per-dashlet boilerplate; every dashlet exposes `/health` and `/metadata`. A user can switch between any of the three, view it in the iframe, and ask Copilot to invoke its approved agent tools. Treasury exposes `get_treasury_curve`, `get_treasury_curve_slopes` and `compare_treasury_curves` with an explicit fixture/EOD `data_mode`. Portfolio Exposure exposes `get_portfolio_exposures`, `get_top_concentrations` and `compare_portfolio_exposures` from deterministic mock positions (fixture-only, no live mode). Agent-tool parameter schemas are generated from each dashlet's real `app.openapi()` output by `scripts/generate_tool_schemas.py`; CI fails if the committed generated file drifts from source. Reusable contract validation (`tests/test_dashlet_contract.py`, `dashlet-registry.test.mjs`) checks every registered dashlet automatically. A GitHub Actions workflow (`.github/workflows/ci.yml`) runs Ruff, Pytest, the schema-drift check and `npm test` on every push/PR.

## Resume here

The next developer should start with **Task 6** below before anything else in this repository. Before that, consider closing out task 5's open item: an independent review pass of the Portfolio Exposure dashlet (see Milestone 4 evidence above) — it was implemented but not yet independently reviewed.

**Recommended branch:** `feature/portfolio-scenario-impact`

1. ~~Add GitHub Actions for Ruff, Pytest and Node tests.~~ Done — see `.github/workflows/ci.yml`.
2. ~~Add reusable dashlet/OpenAPI contract validation.~~ Done — see `tests/test_dashlet_contract.py` and `.github/extensions/dashlet-studio/dashlet-registry.test.mjs`. `DASHLET_REGISTRY`/`REGISTERED_TOOL_IDS`/`TOOL_DESCRIPTIONS` were extracted from `extension.mjs` into `dashlet-registry.mjs` so they're importable by tests without triggering `joinSession()`.
3. ~~Extract the reusable framework from the repeated Hello and Treasury patterns.~~ Done — see `dashlet_framework/` (`app.py`, `models.py`).
4. ~~Replace the Treasury-specific Canvas schema bridge (`treasury-tool-schemas.mjs`) with generic approved OpenAPI-to-capability schema generation.~~ Done — see `scripts/generate_tool_schemas.py` and `.github/extensions/dashlet-studio/generated-tool-schemas.mjs`.
5. ~~Build Portfolio Exposure and Concentration using the framework.~~ Done — see `dashlets/portfolio_exposure_dashlet.py`, `dashlets/portfolio_provider.py`, `portfolio_fixture.py`. Independent review still open (Milestone 4 evidence above).
6. **Build Portfolio Scenario Impact using the framework** (next).
7. Add Issuer Research as a later use case.
8. Build and publish the FastAPI gallery.
9. Add stronger governance, sandboxing, identity, observability and evaluations later.

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
- [ ] Portfolio Exposure, Portfolio Scenario Impact, Issuer Research (Milestone 4 — not started).
- [x] CI (`.github/workflows/ci.yml`).
- [ ] Gallery publication (Milestone 5 — not started).

## Evidence

- [`docs/evidence/treasury-reference.md`](evidence/treasury-reference.md) — full validation summary, fixture/EOD results, tool-isolation and process-lifecycle evidence, provenance examples, test summaries and known limitations.
- Treasury screenshot: genuine EOD-mode capture at [`docs/evidence/images/treasury-canvas-eod.png`](evidence/images/treasury-canvas-eod.png), embedded in the evidence document.
- Relevant tests: `tests/test_treasury_curve_dashlet.py`, `tests/test_treasury_provider.py`, `.github/extensions/dashlet-studio/treasury-tool-schemas.test.mjs`, `.github/extensions/dashlet-studio/tool-proxy.test.mjs`, `tests/js/treasury-client-mode.test.mjs`.
- Relevant architecture sections: [`docs/ARCHITECTURE.md`](ARCHITECTURE.md) §4 "Interactive data flow", §5 "Agent-tool flow".
- Commits: `5546e38`, `8dfd497`, `fb7085f`, `ed78a6c`, `5b0bcf7`, `1286475` (all on `navoditk-treasury-curve-reference` / `navoditk-automatic-lamp`; not yet merged to `main`). Pull request: to be opened per this session's task (see report).

## Known limitations

- Only Hello and Treasury Curve dashlets are currently implemented; Portfolio Exposure, Portfolio Scenario Impact and Issuer Research are not yet built.
- Treasury EOD data is official end-of-day data from Treasury.gov, **not** intraday real-time market data.
- Capability input schemas for the three Treasury tools are a Milestone-2 compatibility bridge (`treasury-tool-schemas.mjs`) — a manually maintained per-operation map, not yet derived generically from OpenAPI.
- Generic OpenAPI-derived capability registration (replacing the bridge above) remains future work — see Resume-here Task 4.
- Response validation is still operation-specific rather than fully OpenAPI-schema-driven.
- No production sandbox — the MVP relies on a registry allowlist, `shell:false` spawning and restricted child-process environment, not process/network isolation.
- No persistent artifact store (draft/published lifecycle, versioning, cloning) exists yet.
- No production identity/authorization model exists; the Canvas control API uses a per-session control token only.
- No hosted gallery exists yet; all verification has been against locally spawned Uvicorn processes.
- **No CI exists yet** — `.github/workflows/` is empty. This is the top-priority Resume-here task.
- The Canvas `ToolProxy`'s existing 5-second request timeout can be exceeded by live Treasury.gov EOD fetches (observed 8–19s in this session); this surfaces as an aborted agent-tool call rather than a wrong answer, and is a pre-existing, unmodified setting — see `docs/evidence/treasury-reference.md` for detail.

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
- [ ] Portfolio Scenario Impact generated using framework.
- [ ] Issuer Research generated or recorded as the first post-sprint extension.
- [x] Every completed business use case (Treasury, Portfolio Exposure) has at least one verified agent tool.
- [!] Independent reviews completed. Portfolio Exposure was implemented by Claude Code in this session; per AGENTS.md §8 / AGENTIC_DEVELOPMENT.md §10 it still needs an independent review pass (a different agent or a human) before being considered fully done.
- [x] No application-specific framework changes were required for Portfolio Exposure (`dashlet_framework` used unchanged; only dashlet-specific `portfolio_fixture.py`/`portfolio_provider.py` were added, mirroring the existing Treasury pattern).

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

## Milestone 5 — CI and publication

- [ ] Gallery mounts every validated dashlet.
- [ ] Ruff passes.
- [ ] Pytest passes.
- [ ] Contract validation passes for every dashlet.
- [ ] Tool-schema validation passes.
- [ ] Secret scan passes.
- [ ] GitHub repository published.
- [ ] Render deployment succeeds.
- [ ] Direct dashlet URL verified.
- [ ] iframe embedding verified.

Evidence:

```text
Repository URL:
CI run:
Gallery URL:
Dashlet URLs:
Iframe test:
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
