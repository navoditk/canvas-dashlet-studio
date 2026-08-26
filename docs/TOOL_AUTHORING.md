# Agent Tool Authoring

How a dashlet operation becomes a Copilot agent tool. Read `docs/ARCHITECTURE.md` §5 first for the end-to-end flow; this document is the step-by-step for adding one.

## 1. The two gates

An operation becomes a Copilot tool only when **both** are true:

1. Its FastAPI route decorator includes `tags=[dashlet_framework.AGENT_TOOL_TAG]`.
2. Its `operation_id` is listed in that dashlet's `approvedTools` in `DASHLET_REGISTRY` (`.github/extensions/dashlet-studio/extension.mjs`).

Neither alone is sufficient — this is deliberate defense in depth (`ARCHITECTURE.md` §5's "dual-use business-operation requirement"). A tagged-but-not-allowlisted operation is invisible to Copilot; an allowlisted-but-untagged `operationId` will never match anything `selectApprovedOperations` finds in the OpenAPI document.

## 2. Adding a new tool, step by step

1. In the dashlet file, add `tags=[AGENT_TOOL_TAG]` to the route decorator (import `AGENT_TOOL_TAG` from `dashlet_framework`).
2. Give it a globally unique `operation_id`, a `response_model`, and a clear `description` — the description becomes the tool description an agent reads if you don't override it in step 4.
3. In `extension.mjs`, add the `operation_id` to the dashlet's entry in `DASHLET_REGISTRY.approvedTools`.
4. In `extension.mjs`'s `TOOL_DESCRIPTIONS`, add an agent-facing description if the OpenAPI `description` isn't itself a good tool description (the fallback is `Proxy approved dashlet operation "<id>".`, which is not a good default — always add a real one).
5. Regenerate tool schemas: `uv run python scripts/generate_tool_schemas.py`. Commit the resulting change to `generated-tool-schemas.mjs`.
6. Add a test to `.github/extensions/dashlet-studio/generated-tool-schemas.test.mjs` (or extend the existing generic assertions) confirming the new operation's schema shape.
7. Verify: `uv run python scripts/generate_tool_schemas.py --check` passes (this is what CI runs — it will fail the build if you forgot step 5).

## 3. Where tool parameter schemas actually come from

Canvas registers tools once, statically, at `joinSession()` — before any dashlet process is running, so there's no live `/openapi.json` to query at that point. `scripts/generate_tool_schemas.py` works around this by importing each registered dashlet's FastAPI app directly and reading its real `app.openapi()` output at generation time, converting every `agent-tool`-tagged operation's query parameters into a JSON Schema. The result is committed to `generated-tool-schemas.mjs`.

This means: **the schema is only ever as fresh as the last time someone ran the generator.** That's why CI runs it in `--check` mode on every push — to catch exactly the case where a query parameter changed but the generated file wasn't regenerated. If `--check` fails, the fix is always `uv run python scripts/generate_tool_schemas.py`, never hand-editing the generated file.

## 4. Parameter naming and typing

- Only `in: "query"` parameters are considered (`ToolProxy`/the generator both ignore path/header/cookie parameters — dashlets in this project only use query parameters for tool-exposed operations).
- An optional parameter (Python `str | None = None`) becomes a non-required schema property; a required parameter (`= Query(...)`) becomes a required schema property. This falls straight out of FastAPI's own OpenAPI output — don't hand-adjust required-ness in the generated file.
- An enum-typed parameter (like Treasury's `data_mode: TreasuryDataMode`) is resolved from the OpenAPI `components.schemas` `$ref` into an inline `enum` in the generated schema — see `_resolve_schema` in `scripts/generate_tool_schemas.py` if you need to extend what shapes it understands.

## 5. Testing tool exposure

For every new tool, verify (mirroring the existing Treasury/Hello tests):

- **Positive:** the operation appears in `AGENT_TOOL_PARAMETER_SCHEMAS` after generation, with the right required/optional fields.
- **Negative — tag without allowlist:** an operation tagged `agent-tool` but not in `approvedTools` is never selected by `selectApprovedOperations` (see `tool-proxy.test.mjs`).
- **Negative — allowlist without tag:** don't allowlist an `operation_id` that isn't actually tagged; add a test asserting the untagged route stays out of `agent-tool` tags in OpenAPI (see `test_openapi_operation_ids_and_agent_tool_tags` pattern).
- **Cross-dashlet isolation:** a tool from dashlet A must be rejected while dashlet B is active, and vice versa (see the `ToolProxy allowlist switch isolates Hello and Treasury tools` test) — this matters more as more dashlets are added, since the failure mode (a stale allowlist from a previous dashlet leaking into the next) only shows up with 2+ dashlets registered.
- **Invalid arguments fail before any provider call:** a missing required argument or an unknown argument should be rejected by `validateToolArgs` client-side, never reach the dashlet process at all.

## 6. What never becomes a tool

`/`, `/health`, `/metadata`, and any administrative or internal route are never tagged `agent-tool`, regardless of what's in `approvedTools`. If a route shouldn't be callable by an agent under any circumstance, the correct fix is to never tag it — don't rely on the allowlist alone to keep it hidden.
