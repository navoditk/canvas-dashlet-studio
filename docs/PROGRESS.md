# Project Progress

Update this file at the end of each implementation block. Mark an item complete only when its evidence exists.

## Status legend

- `[ ]` Not started
- `[-]` In progress or partially verified
- `[x]` Complete with evidence
- `[!]` Blocked; explanation required

## Environment

- [ ] Required accounts available.
- [ ] Git and GitHub CLI verified.
- [ ] Python and uv verified.
- [ ] Node.js and npm verified.
- [ ] Copilot App verified.
- [ ] `/create-canvas` verified.
- [ ] Additional coding agent verified.
- [ ] FastAPI environment check passed.

Evidence:

```text
Date:
Commands:
Result:
Notes:
```

## Milestone 1 — Manual dashlet understanding

- [ ] Metadata and provenance models created.
- [ ] Dashlet factory created.
- [ ] Required routes implemented.
- [ ] Treasury fixture created.
- [ ] Treasury Curve UI renders.
- [ ] Alpine control triggers FastAPI request.
- [ ] Plotly chart updates.
- [ ] Loading/empty/error states work.
- [ ] Contract tests pass.
- [ ] Developer can explain the full browser-to-provider flow.

Evidence:

```text
Commit/PR:
Test command:
Direct URL:
Screenshot:
What I learned manually:
```

## Milestone 2 — Canvas local runtime

- [ ] Canvas extension scaffolded.
- [ ] Process launcher allocates a port.
- [ ] Uvicorn starts through `spawn()` safely.
- [ ] Health polling works.
- [ ] iframe loads the dashlet.
- [ ] stdout/stderr appear in diagnostics.
- [ ] Restart works.
- [ ] Stop removes the process.
- [ ] Failure and timeout states are visible.

Evidence:

```text
Commit/PR:
Canvas session:
Process lifecycle test:
Screenshot:
Known limitations:
```

## Milestone 3 — Agent tool bridge

- [ ] OpenAPI is retrieved after startup.
- [ ] Only `agent-tool` endpoints are selected.
- [ ] Tool arguments are validated.
- [ ] Tool request reaches FastAPI.
- [ ] Tool response is validated.
- [ ] Copilot answers using returned data.
- [ ] Tools disappear when dashlet stops.
- [ ] Iframe and agent tool call the same business endpoint.
- [ ] Provenance is retained in both response paths.
- [ ] Untagged endpoints are not exposed.
- [ ] Invalid arguments fail before the provider is called.

Evidence:

```text
Tool name:
User prompt:
Endpoint log:
Agent response:
Negative test:
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
Completed:
Evidence:
Key platform concepts learned:
Problems:
Next actions:
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
