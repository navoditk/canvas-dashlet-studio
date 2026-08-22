# References

Verified, official documentation for every technology used in this project. Every URL below was fetched and confirmed to resolve before being added here. Prefer primary/official sources over tutorials or videos; entries flagged "optional" are deeper study, not required reading.

## GitHub Copilot App

- **GitHub Copilot app overview** — <https://docs.github.com/en/copilot/how-tos/github-copilot-app> — Entry point for the desktop agent-driven development app used to run this project's Canvas sessions. Read first, before anything else in this list.
- **Working with canvas extensions in the GitHub Copilot app** — <https://docs.github.com/en/copilot/how-tos/github-copilot-app/working-with-canvas-extensions> — Explains what a canvas extension is and how it differs from a chat session; read before touching `.github/extensions/dashlet-studio/`.

## Canvas extensions

- **Working with canvas extensions in the GitHub Copilot app** — <https://docs.github.com/en/copilot/how-tos/github-copilot-app/working-with-canvas-extensions> — Same as above; the authoritative reference for canvas extension concepts (this dashlet extension is one).

## Copilot agent sessions and worktrees

- **Working with agent sessions in the GitHub Copilot app** — <https://docs.github.com/en/copilot/how-tos/github-copilot-app/agent-sessions> — Describes isolated per-session workspaces (this repository's sessions run in git worktrees) and session modes (interactive/plan/autopilot). Read before starting a new session on this repository.

## Copilot custom instructions

- **Adding repository custom instructions for GitHub Copilot** — <https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/add-custom-instructions/add-repository-instructions> — How to give Copilot durable, repository-specific guidance; relevant to the planned `AGENTS.md` work in Milestone 4 (see `docs/PROGRESS.md`).

## FastAPI

- **FastAPI documentation** — <https://fastapi.tiangolo.com/> — The web framework every dashlet is built on. Required reading before modifying any `dashlets/*.py` file.

## Pydantic

- **Pydantic documentation** — <https://docs.pydantic.dev/latest/> — Typed request/response models and validation used throughout the dashlets and Treasury provider. Required reading before changing any response model.

## OpenAPI

- **OpenAPI Initiative** — <https://www.openapis.org/> — The specification FastAPI's `/openapi.json` implements and that the Canvas tool proxy parses to discover agent-tool operations. Read to understand the schema the tool proxy consumes.

## HTTPX

- **HTTPX documentation** — <https://www.python-httpx.org/> — The HTTP client used by the Treasury provider to call Treasury.gov in EOD mode. Read before changing `dashlets/treasury_provider.py`'s network calls.

## Alpine.js

- **Alpine.js documentation** — <https://alpinejs.dev/> — The lightweight JavaScript framework used for all embedded dashlet interactivity (including the Treasury Data Mode selector and mode-change logic). Required reading before editing any dashlet's inline `<script>`.

## Tailwind CSS

- **Tailwind CSS documentation** — <https://tailwindcss.com/docs> — Utility-first CSS framework used for dashlet styling. Optional deeper study; only needed when changing visual layout.

## Plotly.js

- **Plotly JavaScript Open Source Graphing Library** — <https://plotly.com/javascript/> — Charting library used to render the Treasury yield curve and comparison visuals. Read before changing any `Plotly.react`/`Plotly.newPlot` call.

## Node child-process management

- **Node.js `child_process` module documentation** — <https://nodejs.org/api/child_process.html> — Underlies the Canvas extension's safe local process launcher (`dashlet-runtime.mjs`), including `spawn()` with `shell: false`. Required reading before changing process-lifecycle code.

## `uv`

- **uv documentation** — <https://docs.astral.sh/uv/> — The Python package/project manager used for all dependency management and command execution (`uv sync`, `uv run ...`) in this repository. Read first if `uv` is unfamiliar.

## U.S. Treasury daily interest-rate data

- **Daily Treasury Par Yield Curve Rates** — <https://home.treasury.gov/resource-center/data-chart-center/interest-rates/TextView?type=daily_treasury_yield_curve> — The official, public, no-key data source the Treasury provider's `eod` mode fetches from. Read to understand the real data behind `data_mode=eod` responses.

## Pytest

- **Pytest documentation** — <https://docs.pytest.org/en/stable/> — Testing framework used for the Python contract, provider and dashlet tests under `tests/`. Required reading before adding or changing a Python test.

## GitHub Actions

- **GitHub Actions documentation** — <https://docs.github.com/en/actions> — Required reading for the top-priority Resume-here task in `docs/PROGRESS.md`: adding CI for Ruff, Pytest and the Node test suite (no workflow exists yet in this repository).

## Web security for loopback/local applications

- **Same-origin policy — MDN** — <https://developer.mozilla.org/en-US/docs/Web/Security/Defenses/Same-origin_policy> — Background for why the Canvas iframe and tool proxy both talk only to an explicit `dashletUrl`/allowlisted operation set rather than arbitrary origins, and why no browser-side provider credentials are used. Read before changing any cross-origin or credential-handling code in the extension.

## Optional hosting/publication

- **Deploy a FastAPI app — Render** — <https://render.com/docs/deploy-fastapi> (optional) — Referenced by `docs/PROPOSAL.md`/`docs/ROADMAP.md` for the future Milestone 5 gallery-hosting stage. Not required until that stage begins; no gallery or Render deployment exists yet in this repository.

---

Linked from the root [`README.md`](../README.md) (§18 "References") and from [`docs/ROADMAP.md`](ROADMAP.md).
