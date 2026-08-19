# Agentic Development Operating Model

## 1. Objective

Use coding agents extensively without losing the platform understanding required to maintain the system. Agents accelerate implementation; deterministic contracts, tests and human inspection establish trust.

## 2. Tool roles

| Tool | Primary responsibility |
|---|---|
| GitHub Copilot App | Primary project coordinator, Canvas creation, interactive testing, issue/PR lifecycle |
| Copilot CLI | Canvas extension, Node launcher and repository-integrated changes |
| Codex | Python framework, FastAPI applications, tests, refactoring and integration validation |
| Claude Code | Independent architecture/security review and alternative implementation critique |
| VS Code | Manual debugging, breakpoints, browser console and source inspection |

If only two agent tools are available, use Copilot App plus either Codex or Claude Code.

## 3. Manual-build policy

The developer manually implements or closely pairs with an agent on:

- The first FastAPI dashlet.
- The first embedded Alpine `fetch()` flow.
- The first Plotly rendering flow.
- Dashlet metadata and provenance contract.
- Process lifecycle and cleanup.
- First OpenAPI-to-tool proxy.

The objective is to explain every step in these paths without relying on generated code as a black box.

## 4. Agent-first policy

After the first vertical slice works, agents should handle:

- Repetitive dashlet implementations.
- Fixture generation.
- Contract-test expansion.
- Documentation synchronization.
- CI configuration.
- Refactoring duplicated patterns.
- Negative-test generation.
- Independent code review.

## 5. Issue workflow

Every agent task should begin with a bounded GitHub issue containing:

- Problem statement.
- Allowed files or component boundary.
- Acceptance criteria.
- Required tests.
- Prohibited scope expansion.
- Relevant documentation.

Recommended loop:

```text
Issue
  → implementation agent plan
  → branch
  → code + tests
  → local verification
  → pull request
  → independent agent review
  → human inspection
  → CI
  → merge
```

Do not allow multiple agents to edit overlapping files concurrently.

## 6. Canonical instruction hierarchy

```text
AGENTS.md
    Canonical architecture, commands, constraints and definition of done

.github/copilot-instructions.md
    Copilot-specific behavior and references to AGENTS.md

CLAUDE.md
    Claude-specific behavior and references to AGENTS.md

docs/*.md
    Detailed contracts, data patterns and UI patterns loaded when needed
```

Do not duplicate long rules across all instruction files. Duplication causes drift.

## 7. Required agent constraints

Agents must:

- Read `AGENTS.md` before changing files.
- Reuse the shared dashlet framework.
- Keep each dashlet a single Python application file.
- Embed HTML and JavaScript in Python.
- Use Alpine, Tailwind and Plotly only for MVP web UI.
- Use relative `./api/...` requests.
- Keep provider calls server-side.
- Include loading, empty and error states.
- Include provenance.
- Tag tool endpoints explicitly.
- Run contract tests.
- Explain any new dependency before adding it.

Agents must not:

- Add React, TypeScript, a bundler or a frontend framework.
- Embed credentials.
- Accept arbitrary external URLs.
- Expose all OpenAPI endpoints automatically.
- Build background schedulers inside dashlets.
- Bypass GitHub review to publish generated Python.
- Modify the framework to accommodate one app without documenting the general need.

## 8. Suggested implementation prompts

### Framework task

> Read AGENTS.md and the architecture documents. Implement the minimal dashlet application factory, metadata/provenance models and required routes. Do not implement a concrete dashboard or add frontend frameworks. Add contract tests and explain each public API.

### Dashlet task

> Read AGENTS.md, DASHLET_CONTRACT.md, DATA_ACCESS.md and WEB_AUTHORING.md. Implement the requested dashlet using the existing framework. Use fixture-backed tests, typed response models, mount-relative API calls, loading/empty/error states and provenance. Do not modify the framework unless the current contract makes the application impossible; if blocked, stop and explain the required general change.

### Canvas task

> Create a project-scoped Canvas extension using the existing launcher. It must start a selected dashlet, wait for health, load its root URL in an iframe, show status and expose only the documented capabilities. Do not add React, TypeScript or a second artifact format.

### Review task

> Review this pull request as a platform and security reviewer. Check process safety, endpoint/tool exposure, provider restrictions, mount-relative paths, provenance, error handling, lifecycle cleanup and contract-test coverage. Do not implement fixes. Report findings by severity with file references and recommended tests.

## 9. Agentic evaluation set

Maintain a small golden set:

| Prompt | Expected provider | Expected UI | Expected tools |
|---|---|---|---|
| Create a Treasury curve monitor | Treasury fixture/provider | Curve and comparison table | Curve retrieval/comparison |
| Show sector exposure | Portfolio fixture | Bar chart and table | Exposure/concentration |
| Shock rates up 50 bps | Portfolio sensitivities | Impact summary and contribution chart | Scenario run/contributions |
| Show issuer operating trends | SEC fixture/provider | Trends and filing timeline | Company facts/filings |
| Add a comparison date | Existing provider | Second curve and basis-point changes | Existing comparison tool |
| Refresh every minute | Existing provider | Bounded polling and timestamp | No new tool required |

Evaluate:

- Provider selection.
- Endpoint and arguments.
- Visualization choice.
- Tool exposure.
- Required UI states.
- Provenance.
- Prohibited dependency/network behavior.

## 10. Review responsibility matrix

| Change | Suggested implementer | Suggested reviewer |
|---|---|---|
| Python framework | Codex | Claude Code |
| Canvas extension | Copilot App/CLI | Codex |
| Process launcher | Copilot CLI | Claude Code or Codex |
| Treasury reference | Human + Codex | Copilot App visual review |
| Generated dashlet | Codex or Claude Code | Other agent |
| CI/publication | Codex | Copilot App |
