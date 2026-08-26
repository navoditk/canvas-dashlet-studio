# AGENTS.md

Canonical instructions for any agent (or human) making changes to this repository. Tool-specific files (`.github/copilot-instructions.md`, `CLAUDE.md`) point back here rather than repeating these rules — if you find a rule duplicated elsewhere, this file wins.

Read this file before changing any file in the repository.

## 1. What this project is

Canvas Dashlet Studio is a GitHub Copilot Canvas extension plus a small Python/FastAPI runtime for **dashlets**: single-file financial monitors that render in a Canvas iframe and expose a subset of their own typed operations to Copilot as agent tools.

The one contract that matters more than any other: **one typed business operation, two consumers.** The dashlet's embedded JavaScript and the Copilot agent both call the exact same FastAPI endpoint. There is no separate "agent version" of any calculation or data fetch. If you find yourself writing logic that only the agent path or only the UI path would exercise, stop — that is very likely a contract violation.

## 2. Required reading before specific tasks

| Task | Read first |
|---|---|
| Any change | This file |
| Creating or modifying a dashlet | [`docs/DASHLET_CONTRACT.md`](docs/DASHLET_CONTRACT.md), [`docs/DATA_ACCESS.md`](docs/DATA_ACCESS.md), [`docs/WEB_AUTHORING.md`](docs/WEB_AUTHORING.md) |
| Exposing or changing an agent tool | [`docs/TOOL_AUTHORING.md`](docs/TOOL_AUTHORING.md) |
| Canvas extension / process launcher | [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) §5–6, `.github/extensions/dashlet-studio/` |
| Anything touching `dashlet_framework/` | §5 below — framework changes require justification, not just convenience |

## 3. Commands

```bash
uv sync                                    # install Python dependencies
uv run ruff check .                        # lint (must be clean)
uv run pytest                              # Python contract/provider/dashlet tests
uv run python scripts/generate_tool_schemas.py         # regenerate Canvas tool schemas from OpenAPI
uv run python scripts/generate_tool_schemas.py --check  # verify the generated file is not stale (what CI runs)
cd .github/extensions/dashlet-studio && npm test        # Canvas extension tests
```

All four (`ruff`, `pytest`, the schema `--check`, `npm test`) run in `.github/workflows/ci.yml` on every push/PR. Run them locally before considering any change finished.

## 4. The dashlet contract, summarized

Every dashlet is one Python file under `dashlets/`, built with `dashlet_framework.create_dashlet_app(title=..., version=...)`. That factory already registers `GET /health`. Every dashlet must additionally provide:

- `GET /` — returns the embedded HTML/Alpine/Plotly page. Never an agent tool.
- `GET /metadata` — deterministic identity/capability payload (see Treasury or Hello for the pattern). Never an agent tool.
- `GET/POST /api/...` — typed data/analytics endpoints, each with a Pydantic `response_model`, a unique `operation_id`, and `tags=[dashlet_framework.AGENT_TOOL_TAG]` **only** on the operations that should become Copilot tools.
- Every data-bearing response includes provenance: use `dashlet_framework.Provenance` (source, source_url, observation_date, retrieved_at, data_mode, is_stale). Never fabricate or omit it.
- Errors use `dashlet_framework.DashletErrorDetail` / `DashletErrorResponse` with a stable `error_code`, not ad hoc dicts.
- All fetches from the embedded JavaScript use mount-relative paths (`fetch("./api/...")`), never absolute paths — the same dashlet must work standalone and mounted under a gallery.
- Loading, empty and error UI states are required, not optional polish.
- Data-mode selection (fixture vs. live/EOD), if the dashlet has one, must be explicit and required with no default and no silent fallback between modes on failure — this is a deliberate, hardened pattern from the Treasury dashlet (see `docs/evidence/treasury-reference.md`), not a style preference.

## 5. Framework rules

`dashlet_framework/` (`app.py`, `models.py`) exists specifically so dashlets stop re-implementing `/health`, error shapes and provenance by hand. Two rules:

- **Reuse it.** Do not hand-roll a `/health` route, an error-response model, or a provenance model in a new dashlet — import from `dashlet_framework`.
- **Do not extend it speculatively.** Do not add something to `dashlet_framework` "because a future dashlet might need it." Add to the framework only when a *second real dashlet* actually needs the same thing, and say so explicitly in the PR description. This project's own stated principle is to keep the framework smaller than the applications it enables — see `docs/PROPOSAL.md` §3.1. If you're blocked because the current contract makes an application impossible, stop and explain the general change needed rather than quietly reshaping the framework around one app.

## 6. Agent-tool rules

- Only operations tagged `AGENT_TOOL_TAG` **and** present in the Canvas extension's `DASHLET_REGISTRY.approvedTools` allowlist (`.github/extensions/dashlet-studio/extension.mjs`) become Copilot tools. Both conditions are required; neither alone is sufficient.
- Canvas tools are registered once, statically, at `joinSession()` — **before any dashlet process is running.** This is why tool parameter schemas cannot be fetched live; they are generated ahead of time by `scripts/generate_tool_schemas.py` from each dashlet's real `app.openapi()` output. After adding or changing any `agent-tool`-tagged operation's parameters, regenerate the schema file and commit the result — CI will fail the build otherwise (`--check` mode).
- Never hand-edit `.github/extensions/dashlet-studio/generated-tool-schemas.mjs` — it is a generated file; the header says so.
- New dashlet registration in `extension.mjs` (`DASHLET_REGISTRY`, `TOOL_DESCRIPTIONS`) is still manual today — there is no auto-discovery yet. Add the entry deliberately as part of the same change that adds the dashlet.

## 7. Must / must not

Agents must:
- Read this file before changing files.
- Reuse `dashlet_framework` rather than duplicating its responsibilities.
- Keep each dashlet a single Python application file.
- Embed HTML and JavaScript in Python (no separate frontend build artifact per dashlet).
- Use Alpine.js, Tailwind CSS and Plotly.js only, for MVP web UI.
- Use relative `./api/...` requests from embedded JavaScript.
- Keep provider/data-access calls server-side only.
- Include loading, empty and error UI states.
- Include provenance on every data response.
- Tag agent-tool endpoints explicitly and register them in the Canvas allowlist.
- Run `ruff`, `pytest`, the schema `--check`, and `npm test` before calling a change done.
- Explain any new dependency before adding it.

Agents must not:
- Add React, TypeScript, a bundler, or any frontend framework.
- Embed credentials or accept arbitrary external URLs from a request.
- Expose every OpenAPI route as a tool automatically — exposure is opt-in via tag + allowlist.
- Build background schedulers inside a dashlet process.
- Bypass review to publish generated Python directly.
- Modify `dashlet_framework` to accommodate one application without documenting the general need (§5).
- Hand-edit `generated-tool-schemas.mjs`.

## 8. Review responsibility

Per `docs/AGENTIC_DEVELOPMENT.md` §10: a generated dashlet should be reviewed by a different agent (or a human) than the one that implemented it. When an agent implements a new dashlet end-to-end, say so explicitly in the PR/commit description and request an independent review pass before merge — do not self-certify a generated dashlet as done.

## 9. Definition of done for a new dashlet

- Built on `dashlet_framework`, satisfying §4 above.
- Fixture-backed deterministic tests exist (pytest) covering the required routes, at least one agent-tool operation, and provenance.
- At least one UI data operation is also exposed as an approved agent tool (the dual-use contract, §1).
- Registered in `extension.mjs`'s `DASHLET_REGISTRY`; tool schemas regenerated and committed.
- `ruff`, `pytest`, the schema `--check`, and `npm test` all pass.
- `README.md` and `docs/PROGRESS.md` updated to reflect the new dashlet.
- Independent review completed (§8).
