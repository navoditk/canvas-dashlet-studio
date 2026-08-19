# Revised Project Proposal

## 1. Purpose

Build a small Python-first platform that enables users and coding agents to create, run, inspect, share and publish interactive data applications called dashlets inside the GitHub Copilot App.

The proposal has two equally important goals:

1. Develop practical understanding of the platform architecture.
2. Practice reliable agentic software development using durable instructions, bounded tools, automated validation and independent review.

The first vertical slice will be built partly manually. Subsequent dashlets will increasingly be produced by coding agents using the framework and authoring guidance established during the manual phase.

## 2. Guiding principles

- Learn the runtime contract before automating generation.
- Complete one end-to-end vertical slice before adding breadth.
- Prefer Python and standard browser technologies over frontend build systems.
- Treat generated code as untrusted until validated.
- Keep the framework smaller than the applications it enables.
- Use GitHub as the authoritative development and review system.
- Use Render only as a simple prototype publication target.
- Defer enterprise infrastructure without losing its architectural extension points.
- Require provenance, explicit errors and deterministic tests from the beginning.

## 3. MVP scope

### 3.1 Core framework

Implement:

- Dashlet application factory.
- Standard metadata and provenance models.
- Required `/`, `/health` and `/metadata` routes.
- Typed data endpoint conventions.
- Explicit `agent-tool` endpoint tagging.
- Reusable embedded HTML shell.
- Contract validator.
- Recorded data fixtures.

### 3.2 Canvas and runtime

Implement:

- Project-scoped Canvas extension.
- Local port allocation.
- Python/Uvicorn process creation.
- Health polling and startup timeout.
- iframe loading.
- stdout/stderr collection.
- Restart and shutdown.
- OpenAPI discovery.
- Proxying of at least one approved endpoint as a real agent tool.

### 3.3 Reference dashlets

Defined business use cases:

1. Treasury Curve Monitor — manually built reference implementation.
2. Portfolio Exposure and Concentration Monitor — agent-generated implementation.
3. Portfolio Scenario Impact Explorer — agent-generated implementation.
4. Issuer Research Monitor — agent-generated implementation if time permits; otherwise the first post-sprint extension.

Stretch:

5. Macro Regime Monitor or Periodically Refreshed Market Monitor.

The initial sprint must complete at least three applications: the Treasury reference plus two agent-generated business use cases. The fourth use case demonstrates the next extension of the same framework without changing its central contracts.

#### Portfolio Exposure and Concentration Monitor

Business questions:

- Where are the largest sector, issuer, country and currency exposures?
- Which positions dominate active risk or market value?
- How concentrated is the portfolio?
- What changed between two portfolio snapshots?

Inputs and data:

- Mock or uploaded positions CSV.
- Optional benchmark weights fixture.
- Security-to-sector/issuer mapping fixture.

Visuals:

- Sector exposure bars.
- Top issuer concentration table.
- Long, short and net summaries.
- Portfolio-versus-benchmark active weights.

Agent tools:

- `get_portfolio_exposures`
- `get_top_concentrations`
- `compare_portfolio_snapshots`

#### Portfolio Scenario Impact Explorer

Business questions:

- What is the estimated portfolio impact of a rates, spread or equity shock?
- Which positions and sectors contribute most to the result?
- How do two scenarios compare?

Inputs and data:

- Mock positions with duration, spread duration, beta or scenario sensitivities.
- User-defined bounded shocks.
- Deterministic Python calculations.

Visuals:

- Total scenario impact.
- Contribution waterfall or horizontal bars.
- Position-level impact table.
- Side-by-side scenario comparison.

Agent tools:

- `run_portfolio_scenario`
- `get_scenario_contributions`
- `compare_scenarios`

The LLM must not calculate scenario results itself. It selects and calls deterministic FastAPI tools.

#### Issuer Research Monitor

Business questions:

- How are revenue, margins, leverage and cash flow evolving?
- What changed across recent reporting periods?
- Which source filing supports a displayed value?

Inputs and data:

- Public SEC company facts or recorded SEC fixtures.
- Filing metadata and source URLs.
- Normalized financial metrics.

Visuals:

- Revenue and margin trends.
- Leverage/cash-flow summary.
- Recent filing timeline.
- Source-linked facts table.

Agent tools:

- `get_company_facts`
- `get_financial_trends`
- `list_recent_filings`

This use case introduces structured research data and citation/provenance behavior without requiring document RAG in the MVP.

### 3.4 Agentic development framework

Implement:

- `AGENTS.md` as the canonical architecture and validation guidance.
- `.github/copilot-instructions.md` for Copilot-specific repository behavior.
- `CLAUDE.md` as a concise pointer to canonical project rules plus Claude-specific guidance.
- Dashlet creation skill or workflow.
- Dashlet review skill or workflow.
- Golden prompts and expected architectural characteristics.
- Independent review by a different agent from the implementer.

### 3.5 Publication

Implement:

- A single FastAPI gallery host.
- Each dashlet mounted at `/apps/{dashlet-id}/`.
- GitHub Actions validation.
- GitHub pull-request publication flow.
- Render deployment from the main branch.
- Direct browser URL.
- Optional iframe embedding with controlled headers.

## 4. Manual versus agentic work

### Manual learning slice

The developer should manually implement, with documentation and agent guidance available:

- Minimal FastAPI application with embedded HTML.
- Alpine-driven form state and `fetch()` call.
- One Plotly visualization.
- One typed data endpoint.
- One provenance response.
- Basic contract tests.
- Direct Uvicorn execution.

This establishes understanding of the complete artifact before delegating its generation.

### Agent-assisted framework work

Agents may implement bounded framework tasks, but the developer should inspect:

- FastAPI lifecycle.
- OpenAPI definitions.
- Process spawning.
- Port management.
- Tool schema conversion.
- iframe URL behavior.
- Error propagation.
- Process cleanup.

### Agent-generated expansion

After the manual reference passes all tests, agents generate additional dashlets from the contract and authoring guides. The developer evaluates whether the instructions and framework are sufficient rather than manually rewriting every artifact.

## 5. Clean target repository

```text
canvas-dashlet-studio/
├── .github/
│   ├── copilot-instructions.md
│   ├── extensions/canvas-dashlet-studio/
│   │   ├── package.json
│   │   └── extension.mjs
│   └── workflows/ci.yml
├── framework/
│   ├── __init__.py
│   ├── dashlet.py
│   ├── models.py
│   └── validation.py
├── launcher/
│   ├── process-manager.mjs
│   └── tool-discovery.mjs
├── dashlets/
│   ├── treasury_curve.py
│   ├── portfolio_exposure.py
│   ├── scenario_impact.py
│   └── issuer_research.py
├── fixtures/
├── tests/
├── docs/
│   ├── DASHLET_CONTRACT.md
│   ├── DATA_ACCESS.md
│   ├── WEB_AUTHORING.md
│   └── TOOL_AUTHORING.md
├── AGENTS.md
├── CLAUDE.md
├── ARCHITECTURE.md
├── INSTALL.md
├── PLAN.md
├── PROGRESS.md
├── README.md
├── gallery.py
└── pyproject.toml
```

Avoid deeper nesting until multiple implementations demonstrate a need for it.

## 6. Acceptance criteria

The MVP is complete when:

- A user can open the project-scoped Canvas.
- The extension starts a dashlet on a local port.
- The iframe loads the dashlet root page.
- Embedded JavaScript calls mount-relative FastAPI endpoints.
- The manually built Treasury monitor renders fixture and live/EOD data.
- At least two additional business-use-case dashlets use the same framework.
- Every completed business use case exposes at least one typed, allowlisted data or analytics operation as an agent tool.
- The same FastAPI operation serves the iframe JavaScript and the Canvas agent-tool proxy.
- Only explicitly tagged endpoints are exposed.
- Every data result includes provenance.
- Dashlets pass deterministic contract tests.
- The local process can restart and stop without leaving an orphan.
- GitHub Actions validates every dashlet.
- The gallery deploys to Render.
- Each published dashlet has a direct URL.
- At least one published URL is verified inside an iframe test page.

## 7. Deferred stages

### Stage 2: Managed artifact lifecycle

- Dedicated save/load API.
- Draft, validated, published and archived states.
- Artifact cloning.
- Version registry.
- Rollback metadata.
- Search and discovery.
- Local SQLite/filesystem implementation first.

### Stage 3: Governance and security

- User identity propagation.
- Ownership and role checks.
- Tool-level authorization.
- Approval workflows.
- Restricted environment variables.
- Filesystem and network allowlists.
- Stronger sandbox or container execution.
- Dependency allowlists and source scanning.

### Stage 4: Observability and evaluation

- Structured audit events.
- OpenTelemetry traces.
- Tool/provider latency metrics.
- Runtime status dashboard.
- Golden generation evaluations.
- Visual regression checks.
- Failure and recovery testing.

### Stage 5: Automation and production runtime

- Scheduled/background workflows.
- Cached market-close snapshots.
- Persistent alerts.
- Shared production runtime.
- Multi-user concurrency and quotas.
- Environment promotion and governed rollback.

### Stage 6: Enterprise integrations

- Approved internal data catalog.
- Enterprise identity provider.
- Central policy engine.
- Internal deployment and storage platform.
- Full provenance and audit integration.

## 8. Principal risks and mitigations

| Risk | Mitigation in MVP |
|---|---|
| Agent generates unsafe Python | Contract validator, dependency allowlist, review and restricted process environment |
| Too much scope for three days | One complete vertical slice first; three apps required, two stretch |
| Canvas work blocks application work | Validate the dashlet directly in a browser before Canvas integration |
| External API instability | Recorded fixtures in tests and explicit provider timeouts |
| Arbitrary endpoints become tools | Require explicit `agent-tool` tag and allowlist |
| Published app paths break | Require mount-relative `./api/...` fetch URLs |
| Agents introduce unnecessary frameworks | Durable instructions prohibit React, TypeScript and bundlers in MVP |
| Orphan local processes | Store process handles, enforce shutdown and add lifecycle tests |
| Public prototype exposes secrets | Provider calls remain server-side; no credentials in HTML, JS or URLs |

## 9. Recommended developer-tool strategy

- GitHub Copilot App: primary coordinator and Canvas validation environment.
- Copilot CLI: Canvas extension and GitHub workflow implementation.
- Codex: Python framework, tests, refactoring and integration validation.
- Claude Code: independent architecture/security review and generation-quality testing.
- VS Code: manual debugging and browser inspection.

The implementer and reviewer for a pull request should be different agents whenever practical.
