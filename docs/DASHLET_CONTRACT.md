# Dashlet Contract

The structural contract every file under `dashlets/` must satisfy. See [`AGENTS.md`](../AGENTS.md) §4 for the summary; this document goes into the specifics with real examples from `dashlets/hello_dashlet.py` and `dashlets/treasury_curve_dashlet.py`.

## 1. File shape

One Python file per dashlet, under `dashlets/`. It contains, in order:

1. Pydantic response models for this dashlet's data.
2. `app = dashlet_framework.create_dashlet_app(title=..., version=...)`.
3. Helper functions (date parsing, error mapping, provider selection) — private, prefixed `_`.
4. `GET /` returning the embedded HTML page.
5. `GET /metadata` returning this dashlet's identity/capability payload.
6. `GET`/`POST /api/...` data and analytics endpoints.

`GET /health` does **not** need to be written — `create_dashlet_app` already registers it, returning `{"status": "ready"}`.

## 2. `create_dashlet_app`

```python
from dashlet_framework.app import create_dashlet_app

app = create_dashlet_app(title="Portfolio Exposure Dashlet", version="0.1.0")
```

Do not construct `FastAPI(...)` directly in a dashlet file. The factory exists so every dashlet's `/health` behavior is identical by construction, not by convention.

## 3. Required routes

| Route | Required | Agent tool? | Notes |
|---|---|---|---|
| `GET /` | Yes | No | Returns `HTMLResponse` with the embedded page. See `docs/WEB_AUTHORING.md`. |
| `GET /health` | Yes (from factory) | No | Do not redefine. |
| `GET /metadata` | Yes | No | Deterministic identity/capability payload — see §4. |
| `GET`/`POST /api/...` | At least one | Explicitly selected | See `docs/TOOL_AUTHORING.md` for the tagging rule. |

`/metadata` exists so a caller (human or agent) can discover a dashlet's identity and capabilities without depending on OpenAPI internals. Follow the Treasury pattern:

```python
class TreasuryDashletMetadataResponse(BaseModel):
    title: str
    version: str
    data_mode: str
    default_curve_date: str
    canonical_slopes: list[str]
    supported_endpoints: list[str]
    available_fixture_dates: list[str]


@app.get("/metadata", operation_id="get_treasury_dashlet_metadata", response_model=TreasuryDashletMetadataResponse)
def metadata() -> TreasuryDashletMetadataResponse:
    return TreasuryDashletMetadataResponse(
        title=app.title,
        version=app.version,
        data_mode="fixture",
        default_curve_date=_latest_available_date_str(),
        canonical_slopes=CANONICAL_SLOPE_NAMES,
        supported_endpoints=["/api/treasury/curve", ...],
        available_fixture_dates=_list_available_fixture_dates(),
    )
```

The exact fields are dashlet-specific — Hello's is much smaller (`HelloDashletMetadataResponse`: title, version, data_mode, supported_endpoints). What's required is that `/metadata` exists and is never tagged `agent-tool`.

## 4. Response models and errors

Every `/api/...` operation needs:

- A Pydantic `response_model`.
- A unique `operation_id` (unique across the *entire* repository, not just within one dashlet — the tool-schema generator raises if two dashlets export the same `operationId`).
- A clear `description` (this becomes the agent-visible tool description if tagged).

Errors use the shared shapes from `dashlet_framework`:

```python
from dashlet_framework import DashletErrorDetail, DashletErrorResponse

raise HTTPException(
    status_code=404,
    detail={"error_code": "fixture_not_found", "message": f"No fixture found for date: {observation_date}"},
)
```

and declare the shape in the route decorator so it shows up correctly in OpenAPI:

```python
responses={404: {"model": DashletErrorResponse, "description": "Fixture not found for the requested date."}},
```

`error_code` values are a stable, dashlet-owned vocabulary (e.g. Treasury's `fixture_not_found`, `invalid_date`, `missing_slope_maturity`, `maturity_mismatch`) — pick names a client can branch on, not free-text messages.

## 5. Provenance

Every response that carries data (not `/health` or `/metadata`) includes a `dashlet_framework.Provenance`:

```python
from dashlet_framework import Provenance

Provenance(
    source="synthetic-fixture",      # or a live source name, e.g. "treasury-gov"
    source_url=None,                  # set when source is a live/external fetch
    observation_date=date(...),
    retrieved_at=datetime.now(UTC),
    data_mode="fixture",              # or whatever this dashlet's mode vocabulary is
    is_stale=False,
)
```

Never fabricate `retrieved_at` or omit `source`. If a value can't be determined, that's a signal the response shouldn't be returned successfully — raise a controlled error instead (see §4).

## 6. Explicit mode selection (when applicable)

If a dashlet can source data more than one way (fixture vs. live, as in Treasury's `fixture`/`eod`), the mode:

- Must be an explicit, required parameter with an enum of allowed values — never a default that silently picks one mode.
- Must never fall back from a failed live/EOD-style fetch to fixture data. A failure is a failure, surfaced with the real error, not silently masked with stale-looking-fresh data.

See `dashlets/treasury_curve_dashlet.py`'s `TreasuryDataMode` enum and `_DATA_MODE_QUERY` for the reference implementation, and `docs/evidence/treasury-reference.md` for why this was deliberately hardened (it was originally a looser, defaulted parameter).

## 7. Tests

Every dashlet needs a `tests/test_<dashlet>_dashlet.py` covering, at minimum:

- `/health` and `/metadata` return the expected shape.
- Every `/api/...` route returns the documented success shape for a valid fixture-backed request.
- Every documented error path (`404`, `422`, etc.) is actually reachable and returns the expected `error_code`.
- OpenAPI: correct `operationId`s, and `agent-tool` appears only on the operations meant to be tools (see `test_openapi_operation_ids_and_agent_tool_tags` in `tests/test_treasury_curve_dashlet.py` for the pattern).
- Provenance fields are present and correctly shaped.

Prefer fixture-backed, deterministic tests over anything that makes a real network call. If a dashlet has a live-data mode, put any live-network verification in a separate manual script under `scripts/` (see `scripts/live_treasury_check.py`), not in the automated `pytest` suite.
