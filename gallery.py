from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from dashlets.hello_dashlet import app as hello_app
from dashlets.issuer_research_dashlet import app as issuer_research_app
from dashlets.portfolio_exposure_dashlet import app as portfolio_exposure_app
from dashlets.portfolio_scenario_dashlet import app as portfolio_scenario_app
from dashlets.treasury_curve_dashlet import app as treasury_curve_app

# Mount paths mirror the dashlet ids registered in
# .github/extensions/dashlet-studio/dashlet-registry.mjs -- the same id is
# used for Canvas's local process launcher and for this hosted gallery, so
# there is one naming scheme, not two. Each mounted app's embedded HTML uses
# mount-relative fetch("./api/...") calls (see docs/WEB_AUTHORING.md §3),
# which is exactly what makes the same dashlet file work unmodified whether
# served standalone at "/" or mounted here under "/apps/<id>/".
GALLERY_APPS: dict[str, tuple[str, FastAPI]] = {
    "hello": ("Hello Dashlet", hello_app),
    "treasury-curve": ("Treasury Curve", treasury_curve_app),
    "portfolio-exposure": ("Portfolio Exposure", portfolio_exposure_app),
    "portfolio-scenario": ("Portfolio Scenario Impact", portfolio_scenario_app),
    "issuer-research": ("Issuer Research", issuer_research_app),
}

app = FastAPI(title="Canvas Dashlet Studio Gallery", version="0.1.0")

for dashlet_id, (_display_name, sub_app) in GALLERY_APPS.items():
    app.mount(f"/apps/{dashlet_id}", sub_app)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ready"}


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    links = "\n".join(
        f'      <li><a href="/apps/{dashlet_id}/">{display_name}</a> &mdash; '
        f'<code>/apps/{dashlet_id}/</code></li>'
        for dashlet_id, (display_name, _sub_app) in GALLERY_APPS.items()
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Canvas Dashlet Studio Gallery</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 24px; max-width: 720px; }}
    li {{ margin: 8px 0; }}
    code {{ color: #59636e; }}
  </style>
</head>
<body>
  <h1>Canvas Dashlet Studio Gallery</h1>
  <p>Validated dashlets, hosted directly and available for iframe embedding.</p>
  <ul>
{links}
  </ul>
</body>
</html>
"""
