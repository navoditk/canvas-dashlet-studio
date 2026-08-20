from __future__ import annotations

from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel


class DashletSummary(BaseModel):
    title: str
    message: str
    generated_at: str
    source: str
    data_mode: str


app = FastAPI(title="Hello Dashlet", version="0.1.0")


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Hello Dashlet</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; margin: 24px; }
    .box { border: 1px solid #d1d9e0; border-radius: 8px; padding: 16px; max-width: 560px; }
    .row { margin: 8px 0; }
    .k { color: #59636e; width: 140px; display: inline-block; }
    .error { color: #b60205; margin-top: 12px; }
  </style>
</head>
<body>
  <h1>Hello Dashlet</h1>
  <div class="box">
    <div class="row"><span class="k">Title:</span><span id="title">loading...</span></div>
    <div class="row"><span class="k">Message:</span><span id="message">loading...</span></div>
    <div class="row"><span class="k">Generated At:</span><span id="generated_at">loading...</span></div>
    <div class="row"><span class="k">Source:</span><span id="source">loading...</span></div>
    <div class="row"><span class="k">Data Mode:</span><span id="data_mode">loading...</span></div>
    <div class="error" id="error"></div>
  </div>
  <script>
    async function loadSummary() {
      try {
        const response = await fetch("./api/summary");
        if (!response.ok) {
          throw new Error("Request failed: " + response.status);
        }
        const data = await response.json();
        for (const field of ["title", "message", "generated_at", "source", "data_mode"]) {
          document.getElementById(field).textContent = String(data[field] ?? "");
        }
      } catch (error) {
        document.getElementById("error").textContent = String(error);
      }
    }
    loadSummary();
  </script>
</body>
</html>
"""


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ready"}


@app.get(
    "/api/summary",
    operation_id="get_dashlet_summary",
    tags=["agent-tool"],
    response_model=DashletSummary,
)
def get_summary() -> DashletSummary:
    return DashletSummary(
        title="Hello Dashlet",
        message="Smoke test successful",
        generated_at=datetime.now(UTC).isoformat(),
        source="fixture",
        data_mode="fixture",
    )
