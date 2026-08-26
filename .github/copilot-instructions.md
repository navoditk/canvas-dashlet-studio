# Copilot instructions for Canvas Dashlet Studio

Read [`/AGENTS.md`](../AGENTS.md) first — it is canonical for architecture, the dashlet contract, framework rules, agent-tool rules, and the must/must-not list. This file only adds Copilot-specific notes; it does not repeat AGENTS.md.

## Copilot App / Canvas specifics

- This repository's Canvas extension lives at `.github/extensions/dashlet-studio/`. Use the existing `DashletRuntime`/`ToolProxy`/control-server pieces there rather than building a new process launcher or tool bridge.
- When asked to create or modify a dashlet from a Canvas session, follow the "Dashlet task" prompt template in [`docs/AGENTIC_DEVELOPMENT.md`](../docs/AGENTIC_DEVELOPMENT.md) §8: read `AGENTS.md`, `docs/DASHLET_CONTRACT.md`, `docs/DATA_ACCESS.md` and `docs/WEB_AUTHORING.md` first, implement using the existing framework, and stop and explain rather than silently reshaping `dashlet_framework` if the current contract seems to block the request.
- When asked to change the Canvas extension itself (process lifecycle, tool proxy, control server), read `docs/ARCHITECTURE.md` §5–6 first and treat process-management code as something to inspect closely, not accept as opaque generated output — see the "manual-build policy" in `docs/AGENTIC_DEVELOPMENT.md` §3.
- After adding or changing any `agent-tool`-tagged operation, run `uv run python scripts/generate_tool_schemas.py` and commit the regenerated `generated-tool-schemas.mjs` — do not hand-edit it.
