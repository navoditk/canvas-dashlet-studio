# Evidence: Gallery Render Deployment

## Milestone name

Milestone 5 — `gallery.py` deployed to Render as a live, hosted FastAPI process mounting every validated dashlet.

## Validation date

2026-08-27. Deployment was created and verified by the repository owner (Render account access is required and was not available to the agent); verification below was performed directly against the live URL.

## Commit SHAs

`002b717` (`gallery.py` + `tests/test_gallery.py`), `e40c6c2` (`render.yaml` + docs) — both on `main`.

## Deployment record

- **Platform:** Render, free-tier web service, defined by `render.yaml` (repo root) as a Blueprint.
- **Build command:** `pip install uv && uv sync --no-dev`
- **Start command:** `uv run uvicorn gallery:app --host 0.0.0.0 --port $PORT`
- **Live base URL:** <https://canvas-dashlet-studio-gallery.onrender.com>

## Verification summary

All checks below were run directly against the live Render URL (not a local process) via `curl`.

| Check | Result |
|---|---|
| `GET /health` | `200`, `{"status":"ready"}` |
| `GET /` (landing page) | `200`, HTML listing all 5 mounted dashlets with correct `/apps/<id>/` links |
| `GET /apps/hello/health` | `200`, `{"status":"ready"}` |
| `GET /apps/treasury-curve/health` | `200`, `{"status":"ready"}` |
| `GET /apps/portfolio-exposure/health` | `200`, `{"status":"ready"}` |
| `GET /apps/portfolio-scenario/health` | `200`, `{"status":"ready"}` |
| `GET /apps/issuer-research/health` | `200`, `{"status":"ready"}` |
| `GET /apps/portfolio-scenario/` response headers | No `X-Frame-Options` or `Content-Security-Policy: frame-ancestors` header present — nothing at the HTTP layer blocks iframe embedding of the deployed gallery |

## Cross-verification against known standalone/local values

Each business dashlet's data endpoint was called through its deployed mount and compared against the exact values already verified locally (see `docs/evidence/portfolio-exposure-reference.md`, `docs/evidence/portfolio-scenario-reference.md`, `docs/evidence/issuer-research-reference.md`, and the local gallery verification in `docs/PROGRESS.md` Milestone 5). All matched exactly:

| Dashlet | Live-mount call | Result | Matches local value |
|---|---|---|---|
| Treasury Curve | `GET /apps/treasury-curve/api/treasury/fixture-dates` | `{"available_dates": ["2026-08-18", "2026-08-19"]}` | Yes |
| Portfolio Exposure | `GET /apps/portfolio-exposure/api/portfolio/exposures` | `totals.net_market_value = 10650000.0` | Yes — matches `docs/evidence/portfolio-exposure-reference.md` |
| Portfolio Scenario Impact | `GET /apps/portfolio-scenario/api/scenario/run?equity_shock_pct=10` | `totals.total_impact = 1154000.0`, `totals.rate_impact = 0.0`, `totals.spread_impact = 0.0` | Yes — matches `docs/evidence/portfolio-scenario-reference.md` |
| Issuer Research | `GET /apps/issuer-research/api/issuer/facts?ticker=AAPL&data_mode=fixture` | `revenue.value = 416161000000.0`, `revenue.fiscal_year = 2025` | Yes — matches `docs/evidence/issuer-research-reference.md` |

This confirms the deployed gallery is running the identical code path as local verification, not a divergent build — the same fixture data, the same deterministic calculations, and the same mount-relative `fetch("./api/...")` resolution (proven structurally by `tests/test_gallery.py`, and now confirmed live).

## What this evidence does and does not cover

- **Covers:** the gallery is live, publicly reachable, every mounted dashlet is healthy, and business-logic values through the deployed mount are correct and match local/standalone verification exactly.
- **Does not cover:** an actual Canvas session embedding the deployed URL in an iframe and invoking its agent tools end-to-end. That remains part of the deferred combined live-Canvas evidence pass described in `docs/PROGRESS.md` "Resume here" — the header check above (no frame-blocking headers) is a necessary but not sufficient condition for that.
- **Cold starts:** Render's free plan spins the service down after ~15 minutes of inactivity; the first request after an idle period takes longer (cold start) before responding. This is a platform characteristic, not a defect in `gallery.py`.

## Known limitations

- Free-tier hosting: no custom domain, cold starts after idle, shared infrastructure. Acceptable for an MVP-stage reference implementation, not representative of a production SLA.
- No secret scanning in CI (see `docs/ARCHITECTURE.md` §10) — unrelated to this deployment specifically, but relevant to any public-facing hosting.
