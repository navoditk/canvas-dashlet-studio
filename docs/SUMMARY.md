# Canvas Dashlet Studio — Consolidated Summary

## 1. Purpose

This project prepares a developer to build GitHub Copilot Canvas extensions that create and run compact financial web applications called **dashlets**. A dashlet is a Python FastAPI application with embedded HTML and JavaScript. It runs as a local process, appears inside a Canvas iframe, retrieves live or end-of-day data, and exposes approved data or analytics operations to the Copilot agent as tools.

The 2–3 day MVP emphasizes platform understanding, a reusable core framework and agent-assisted development. The final repository should contain at least three working financial apps, automated validation, CI and a simple published gallery.

## 2. Core architectural principle

The central contract is **one typed business operation with two consumers**:

- The iframe UI calls a FastAPI endpoint using mount-relative JavaScript such as `fetch("./api/exposures")`.
- Copilot calls the same endpoint through a Canvas agent-tool proxy generated from its OpenAPI definition.

This prevents duplicated business logic and ensures the visual and conversational experiences use identical data, calculations and provenance.

Only endpoints explicitly tagged `agent-tool` and included in an extension allowlist become agent tools. Health, HTML, metadata, administrative and internal provider routes remain private.

## 3. Target user experience

1. A user describes a monitor or visualization in Copilot Canvas.
2. An agent creates or modifies a single-file Python dashlet.
3. Deterministic validation and tests run.
4. The Canvas extension starts Uvicorn on an available local port.
5. Canvas loads the application in an iframe.
6. The rendered JavaScript retrieves current data from FastAPI.
7. Copilot can invoke approved FastAPI operations as tools and reason over the structured results.
8. The validated source is committed to GitHub and published through a gallery host.

## 4. MVP technology stack

| Concern | Recommended technology |
|---|---|
| Agent experience | GitHub Copilot App and Canvas |
| Canvas extension | JavaScript and Node.js |
| Local process lifecycle | Node `child_process.spawn` with `shell: false` |
| Application runtime | Python, FastAPI and Uvicorn |
| API contracts | Pydantic and OpenAPI |
| Data providers | HTTPX, provider adapters and recorded fixtures |
| Browser experience | Embedded HTML, Alpine.js, Tailwind CSS and Plotly.js |
| Testing and linting | Pytest, FastAPI TestClient and Ruff |
| Repository automation | GitHub Actions |
| Prototype publication | Render-hosted FastAPI gallery |
| Coding assistance | Copilot, Copilot CLI, Codex and Claude Code |

React, TypeScript, a bundler, MCP, RAG and graph-based agent orchestration are not required for this MVP. REST endpoints are sufficient. These technologies can be introduced later only when a concrete requirement justifies them.

## 5. Repository deliverables

The target GitHub repository should contain:

- A small Canvas extension for launch, stop, restart, iframe display and tool registration.
- A reusable Python framework defining dashlet metadata, provider contracts, provenance and validation.
- One manually authored reference dashlet.
- At least two additional dashlets generated with the framework.
- Deterministic fixtures and provider tests.
- Agent-tool discovery, allowlisting and proxy tests.
- A gallery application mounting validated dashlets under stable paths.
- GitHub Actions for linting, tests, contract checks and secret scanning.
- Durable `AGENTS.md` and tool-specific development instructions.
- Installation, architecture, roadmap and progress documentation.

## 6. Business use cases

### Treasury Curve Monitor

Displays Treasury yields, curve slopes and comparisons across observation dates. This is the manually built reference app used to understand the entire contract.

Candidate tools: `get_treasury_curve`, `compare_treasury_curves`, `get_curve_slopes`.

### Portfolio Exposure and Concentration Monitor

Displays issuer, sector, long, short, net and benchmark-relative exposures using fixture positions and optional benchmark weights.

Candidate tools: `get_portfolio_exposures`, `get_top_concentrations`, `compare_portfolio_snapshots`.

### Portfolio Scenario Impact Explorer

Applies bounded rate, spread and equity shocks and displays total impact, contribution breakdowns and position-level results. Calculations remain deterministic Python functions rather than LLM-generated arithmetic.

Candidate tools: `run_portfolio_scenario`, `get_scenario_contributions`, `compare_scenarios`.

### Issuer Research Monitor

Displays public company facts, financial trends and recent filing information with source links and reporting periods. It is a stretch app or the first post-sprint extension.

Candidate tools: `get_company_facts`, `get_financial_trends`, `list_recent_filings`.

## 7. Data and agent-tool contract

Every completed business use case must expose at least one typed data or analytics operation to both the iframe and Copilot. Each exposed operation needs:

- A stable OpenAPI `operation_id` and useful description.
- Bounded, typed parameters.
- Pydantic request and response models.
- An explicit `agent-tool` tag.
- Inclusion in the extension allowlist.
- Source, observation time, retrieval time and fixture/live status.
- Deterministic error behavior and proxy timeout.

Automated tests must prove that tagged operations become tools, untagged operations do not, invalid arguments fail before provider execution, both consumers reach the same operation, and provenance survives the proxy unchanged.

## 8. Security and governance boundaries

The MVP provides practical guardrails rather than a production sandbox:

- Provider registry instead of arbitrary URLs.
- Server-side credentials only.
- Restricted child-process environment.
- No shell execution.
- Startup, health and request timeouts.
- Explicit endpoint and dependency allowlists.
- Process-tree cleanup.
- Contract, path and secret scanning.
- GitHub pull-request review before publication.

Later stages add identity propagation, role checks, approvals, filesystem/network isolation, stronger sandboxing, audit events and enterprise policies.

## 9. Project-driven learning plan

### Day 1 — Understand and build the dashlet contract

Install and verify Git, Python, `uv`, Node.js, GitHub CLI and the selected coding agents. Learn FastAPI routing, Pydantic models, OpenAPI, Alpine events and Plotly updates while manually building the Treasury Curve Monitor. Add fixture and live/EOD providers, provenance and endpoint tests.

**Outcome:** a browser-tested single-file app with deterministic tests and a documented contract.

### Day 2 — Build Canvas integration and agent tools

Implement the JavaScript Canvas extension and safe Python launcher. Add port selection, health polling, diagnostics, iframe loading, restart and cleanup. Retrieve OpenAPI, select tagged and allowlisted operations, register tool proxies and validate arguments and responses.

**Outcome:** a user can view the app in Canvas and ask Copilot a question that causes the same endpoint used by the UI to be invoked as a tool.

### Day 3 — Prove reuse, agentic development and publication

Create canonical repository instructions and bounded generation/review workflows. Use an agent to generate Portfolio Exposure and Scenario Impact without bypassing the framework, then use a different agent to review the changes. Add gallery mounting, CI, tool-schema tests and deployment to Render.

**Outcome:** at least three apps share the framework, CI passes, agent-tool access is verified and direct application URLs are available.

## 10. Recommended agent responsibilities

- **GitHub Copilot App:** primary user workflow, Canvas integration and final interaction testing.
- **Copilot CLI:** extension implementation, GitHub operations and workflow automation.
- **Codex:** Python framework, tests, refactoring and integration validation.
- **Claude Code:** independent architecture, security and generated-code review.
- **Developer:** manually builds the first vertical slice, understands boundaries, approves architectural changes and reviews evidence.

Agents should read canonical repository instructions, propose bounded plans, reuse the framework, run deterministic checks and provide evidence. The implementing and reviewing agents should differ where practical.

## 11. MVP definition of done

- Canvas reliably starts, stops, restarts and displays a dashlet.
- At least three financial apps use the same core framework.
- Each completed app exposes at least one approved typed operation to its UI and Copilot.
- Untagged routes cannot become tools.
- Invalid tool arguments never reach providers.
- Results preserve provenance across UI and agent paths.
- No credentials appear in browser code or requests.
- Contract tests, linting and GitHub Actions pass.
- The gallery provides direct URLs and at least one iframe embedding test succeeds.
- Milestones and evidence are recorded in `PROGRESS.md`.

## 12. Forward roadmap

1. **Artifact lifecycle:** save/load, versions, draft/published states, cloning and rollback.
2. **Governance and security:** identity, authorization, approvals and stronger isolation.
3. **Observability and evaluation:** audit events, traces, latency metrics, golden prompts and visual regression.
4. **Automation and shared runtime:** schedules, alerts, cached close snapshots, concurrency and quotas.
5. **Enterprise integration:** governed internal data catalog, policy engine and deployment platform.

## 13. Source-document guide

| Document | What it provides |
|---|---|
| `README.md` | Top-level scope, stack, use cases, core contract and roadmap |
| `INSTALL.md` | Prerequisites, installation commands and environment verification |
| `PROPOSAL.md` | Objectives, scope, deliverables, acceptance criteria, risks and later stages |
| `ARCHITECTURE.md` | Components, data/tool flows, runtime lifecycle, hosting and security boundaries |
| `ROADMAP.md` | Timed 2–3 day exercises, tutorials, checkpoints and deliverables |
| `AGENTIC_DEVELOPMENT.md` | Agent roles, repository guidance, prompts, review rules and evidence expectations |
| `PROGRESS.md` | Milestone checklist and evidence-recording template |

Start with `README.md`, use this summary for orientation, then follow `INSTALL.md` and `ROADMAP.md` during implementation.
