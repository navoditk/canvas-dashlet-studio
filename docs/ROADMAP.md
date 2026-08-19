# 2–3 Day Project Roadmap

Assumption: 4–5 focused hours per day. Complete the installation guide before Day 1.

## Learning model

- 65% building and debugging.
- 20% targeted tutorials immediately before their use.
- 10% architecture and code reading.
- 5% progress evidence and retrospective.

Do not complete long courses before starting. Read only the sections required for the next implementation block.

## Day 1 — Understand and manually build the artifact

### Milestone

One Treasury Curve dashlet works directly in a browser and passes the core contract tests.

### Block 1: FastAPI artifact fundamentals — 40 minutes

Read:

- FastAPI First Steps: <https://fastapi.tiangolo.com/tutorial/first-steps/>
- HTML/custom responses: <https://fastapi.tiangolo.com/advanced/custom-response/>
- Response models: <https://fastapi.tiangolo.com/tutorial/response-model/>

Learn:

- `FastAPI` application construction.
- `HTMLResponse`.
- Pydantic response models.
- OpenAPI operation IDs, descriptions and tags.

Evidence:

- Explain why `/` is not an agent tool.
- Inspect `/openapi.json` manually.

### Block 2: Browser UI without a build system — 40 minutes

Read:

- Alpine Start Here: <https://alpinejs.dev/start-here>
- Tailwind Play CDN: <https://tailwindcss.com/docs/installation/play-cdn>
- Plotly Getting Started: <https://plotly.com/javascript/getting-started/>
- Plotly functions: <https://plotly.com/javascript/plotlyjs-function-reference/>

Learn only:

- Alpine `x-data`, `x-init`, `x-model`, `x-show`, `x-for` and event syntax.
- Tailwind grid, flex, spacing, typography, tables and responsive classes.
- Plotly line/scatter charts and `Plotly.react`.
- Browser `fetch`, errors and JSON.

### Block 3: Implement the framework manually — 60 minutes

Create:

- Dashlet metadata model.
- Provenance model.
- Application factory.
- Standard `/health` and `/metadata` routes.
- Embedded page helper.
- `agent-tool` tag convention.

Do not ask an agent to generate the entire framework. Use an agent to explain unfamiliar FastAPI behavior and review each completed component.

### Block 4: Build Treasury Curve Monitor manually — 90 minutes

Features:

- Curve date.
- Optional comparison date.
- Nominal Treasury curve.
- Basis-point changes.
- 2s10s and 5s30s values.
- Loading, empty and error states.
- Provenance footer.

Endpoints:

```text
GET /
GET /health
GET /metadata
GET /api/curve
GET /api/curve/compare
```

Use a recorded fixture first. Add official live/EOD retrieval only after the fixture path works.

### Block 5: Contract tests and retrospective — 45 minutes

Test:

- Module imports.
- `app` is a FastAPI instance.
- Required routes exist.
- HTML loads.
- OpenAPI is valid.
- Tool operations have response schemas and unique IDs.
- Data includes provenance.
- Fixture path is deterministic.

Update `PROGRESS.md` with:

- Commands run.
- Screenshot or URL.
- Tests passed.
- What was manually learned.
- Problems to fix on Day 2.

## Day 2 — Canvas, process lifecycle and agent tools

### Milestone

Copilot Canvas starts the Treasury dashlet, displays it in an iframe and invokes one data endpoint as a tool.

### Block 1: Canvas extension model — 35 minutes

Read:

- Canvas extensions: <https://docs.github.com/en/copilot/how-tos/github-copilot-app/working-with-canvas-extensions>
- Copilot App customization: <https://docs.github.com/en/copilot/how-tos/github-copilot-app/customize-github-copilot-app>
- Agent sessions: <https://docs.github.com/en/copilot/how-tos/github-copilot-app/agent-sessions>

Learn:

- Project versus user scope.
- `package.json` and `extension.mjs`.
- Canvas UI actions versus agent-callable capabilities.
- Shared state.

### Block 2: Process lifecycle — 60 minutes

Read relevant sections of:

- Node child processes: <https://nodejs.org/api/child_process.html>

Implement:

- Free port selection.
- `spawn()` with argument arrays and `shell: false`.
- stdout/stderr capture.
- Startup timeout.
- `/health` polling.
- Restart and process-tree shutdown.

Manually inspect this code. It is a core platform responsibility and should not be accepted as opaque agent output.

### Block 3: Create Canvas extension — 60 minutes

Use the Copilot App `/create-canvas` workflow to scaffold a project-scoped extension.

Capabilities:

```text
list_dashlets
open_dashlet
restart_dashlet
stop_dashlet
validate_dashlet
list_dashlet_tools
```

Canvas UI:

- Dashlet selector.
- Process status.
- iframe.
- Validation errors.
- Available tools.
- Restart/stop controls.

### Block 4: OpenAPI-to-tool bridge — 60 minutes

Implement one full proxy path:

```text
get_treasury_curve tool
    → argument validation
    → local FastAPI request
    → response validation
    → structured result returned to Copilot
```

Test from Canvas:

> Retrieve the curve and identify the largest adjacent maturity change.

Confirm from logs that the endpoint was called through the tool proxy.

Add automated proof of the dual-use contract:

- The iframe and proxy call the same FastAPI operation.
- A tagged, allowlisted operation becomes a tool.
- An untagged operation does not become a tool.
- Invalid tool arguments are rejected before provider execution.
- Provenance fields are unchanged through the proxy.

### Block 5: Agentic modification — 45 minutes

Ask Copilot to add or revise one feature, such as comparison-date highlighting.

Require the agent to:

1. Read the contract and web-authoring guide.
2. Propose a bounded plan.
3. Modify the Python source.
4. Run validation and tests.
5. Restart the process.
6. Verify the iframe.

Update `PROGRESS.md` with the tool trace and restart evidence.

## Day 3 — Agent-generated reuse and publication

### Milestone

At least three business-use-case dashlets use the framework, CI passes and the gallery is deployed from GitHub.

### Block 1: Durable agent guidance — 45 minutes

Read:

- Copilot custom instructions: <https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-custom-instructions>
- Copilot skills: <https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/add-skills>
- Codex AGENTS.md: <https://developers.openai.com/codex/agent-configuration/agents-md>
- Codex best practices: <https://developers.openai.com/codex/learn/best-practices>
- Claude Code memory: <https://docs.anthropic.com/en/docs/claude-code/memory>

Create:

- Canonical `AGENTS.md`.
- Concise tool-specific instruction files.
- Dashlet creation workflow.
- Dashlet review workflow.

### Block 2: Generate Portfolio Exposure and Concentration — 60 minutes

Agent requirements:

- Reuse framework unchanged unless blocked.
- Read mock positions and optional benchmark weights.
- Calculate sector, issuer, long, short and net exposures deterministically.
- Display exposure bars and a concentration table.
- Provide typed exposure, concentration and snapshot-comparison endpoints.
- Expose at least one of those same UI data operations as an approved agent tool.
- Include provenance and fixture tests.

Developer task: review the generated endpoint and browser flow rather than rewriting it.

### Block 3: Generate Portfolio Scenario Impact — 60 minutes

Agent requirements:

- Use positions containing duration, spread-duration, beta or scenario sensitivities.
- Accept bounded rate, spread and equity shocks.
- Calculate impact in deterministic Python code.
- Display total impact, contribution bars and a position-level table.
- Provide typed run, contribution and comparison endpoints.
- Expose the scenario run or contribution operation as an approved agent tool.
- Reject unsupported or unbounded shocks.

Use a different coding agent to review the generated change.

### Optional Block 3B: Generate Issuer Research Monitor — 45–60 minutes

Complete only if the first three applications and Canvas/tool path are stable.

Agent requirements:

- Use recorded SEC fixtures first and public SEC data second.
- Normalize revenue, operating margin, leverage and cash-flow measures.
- Display metric trends and a recent-filing timeline.
- Preserve accession/source links and reporting periods.
- Provide typed company-facts, trends and filing-list endpoints.
- Expose the facts or trends operation as an approved agent tool.
- Do not add document embeddings or RAG.

### Block 4: Gallery and CI — 50 minutes

Implement:

- `gallery.py` mounting each validated dashlet.
- Contract tests for every module.
- Ruff and Pytest in GitHub Actions.
- Secret scan.
- OpenAPI/tool-schema checks.
- Mount-relative path checks.

### Block 5: Publish to Render — 40 minutes

Follow:

- <https://render.com/docs/deploy-fastapi>

Verify:

- Gallery URL opens.
- Each dashlet URL opens directly.
- One URL works in an iframe test page.
- Server-side data endpoints work.
- No secret is visible in browser source or requests.

### Block 6: Final review — 30 minutes

Use a different agent to review:

- Architecture boundaries.
- Unsafe process execution.
- Tool overexposure.
- Arbitrary network access.
- Missing timeouts.
- Mount-relative paths.
- Test gaps.

Update `PROGRESS.md` and open any deferred issues.

## If only two days are available

Complete:

- Day 1 in full.
- Day 2 in full.
- From Day 3: durable instructions, one generated dashlet, CI and GitHub publication.

Defer Render and the third dashlet until the following session. The full local Canvas/tool vertical slice is more valuable than five disconnected dashboards.

## Stretch work after the three-day project

1. Complete Issuer Research Monitor if deferred during the sprint.
2. Macro Regime Monitor.
3. Periodically refreshed Market Monitor.
4. Local artifact storage API.
5. Draft/published lifecycle.
6. Structured audit events.
7. OpenTelemetry instrumentation.
8. Container sandbox.
9. Mock user roles and tool policies.
