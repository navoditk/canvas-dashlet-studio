# Project Progress

Update this file at the end of each implementation block. Mark an item complete only when its evidence exists.

## Status legend

- `[ ]` Not started
- `[-]` In progress or partially verified
- `[x]` Complete with evidence
- `[!]` Blocked; explanation required

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
Commit/PR: Not committed yet (working tree changes on
navoditk-dashlet-studio-treasury-integration; user explicitly held commit/push).
Canvas session: dashlet-studio-verify-1 (extension project:dashlet-studio, canvas
dashlet-studio); reopened as dashlet-studio-verify-1 in current session.
Process lifecycle test: Started Hello (PID captured, default selection), selected +
started Treasury Curve (confirmed prior Hello PID stopped via SIGTERM/process-group
kill, new PID/port allocated for treasury_curve_dashlet), Stop verified process
removed and port/PID cleared, Restart verified PID rotation, switch back to Hello
verified Treasury PID stopped.
Screenshot: n/a (verified via invoke_canvas_action status payloads and diagnostics log).
Known limitations: Extension now spawns one of two registry-approved modules
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
```

## Milestone 4 — Agent-generated reuse

- [ ] Canonical `AGENTS.md` created.
- [ ] Tool-specific instructions reference canonical rules.
- [ ] Creation workflow/skill created.
- [ ] Review workflow/skill created.
- [ ] Portfolio Exposure generated using framework.
- [ ] Portfolio Scenario Impact generated using framework.
- [ ] Issuer Research generated or recorded as the first post-sprint extension.
- [ ] Every completed business use case has at least one verified agent tool.
- [ ] Independent reviews completed.
- [ ] No application-specific framework changes were required, or changes were justified.

Evidence:

```text
Generation prompts:
Implementing agents:
Reviewing agents:
PRs:
Framework changes:
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
