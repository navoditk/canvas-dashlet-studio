from __future__ import annotations

from fastapi import FastAPI

AGENT_TOOL_TAG = "agent-tool"


def create_dashlet_app(*, title: str, version: str) -> FastAPI:
    """Construct a FastAPI app with the routes every dashlet must expose.

    Registers GET /health here since it is identical across every dashlet.
    /metadata is intentionally not registered here: its response shape is
    dashlet-specific, so each dashlet defines its own /metadata route using
    a dashlet-specific response model.
    """
    app = FastAPI(title=title, version=version)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ready"}

    return app
