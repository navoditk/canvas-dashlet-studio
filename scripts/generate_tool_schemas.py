#!/usr/bin/env python
"""Generate Canvas agent-tool parameter schemas from each dashlet's OpenAPI.

Canvas registers tools once, statically, at joinSession() time, before any
dashlet process is running -- so the extension cannot fetch /openapi.json
live at startup. This script is the alternative: it imports each registered
dashlet's FastAPI app directly, reads its real app.openapi() output, and
converts every agent-tool-tagged operation's query parameters into a JSON
Schema the Canvas extension can register as a tool's `parameters`.

Run this after changing any agent-tool-tagged endpoint's query parameters:

    uv run python scripts/generate_tool_schemas.py

Run with --check in CI to fail the build if the committed generated file is
stale relative to the current dashlet source:

    uv run python scripts/generate_tool_schemas.py --check
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashlet_framework import AGENT_TOOL_TAG

# Keep in sync with DASHLET_REGISTRY's `module` values in
# .github/extensions/dashlet-studio/dashlet-registry.mjs.
DASHLET_MODULES: list[str] = [
    "dashlets.hello_dashlet:app",
    "dashlets.treasury_curve_dashlet:app",
    "dashlets.portfolio_exposure_dashlet:app",
    "dashlets.portfolio_scenario_dashlet:app",
    "dashlets.issuer_research_dashlet:app",
]

OUTPUT_PATH = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "extensions"
    / "dashlet-studio"
    / "generated-tool-schemas.mjs"
)

GENERATOR_RELATIVE_PATH = "scripts/generate_tool_schemas.py"


def _load_app(module_target: str):
    module_name, _, attr = module_target.partition(":")
    import importlib

    module = importlib.import_module(module_name)
    return getattr(module, attr)


def _resolve_schema(schema: dict, components: dict) -> dict:
    """Resolve a single OpenAPI parameter schema to {type, enum?}.

    Handles the two shapes FastAPI actually emits for the query parameters
    this project uses: a `$ref` to a components.schemas enum (e.g.
    TreasuryDataMode), and an `anyOf: [{type: X}, {type: "null"}]` union for
    an optional plain-typed parameter. Anything else is passed through by
    type alone.
    """
    if "$ref" in schema:
        ref_name = schema["$ref"].rsplit("/", 1)[-1]
        resolved = components.get(ref_name, {})
        result: dict = {"type": resolved.get("type", "string")}
        if "enum" in resolved:
            result["enum"] = resolved["enum"]
        return result

    if "anyOf" in schema:
        non_null = [option for option in schema["anyOf"] if option.get("type") != "null"]
        if non_null:
            return _resolve_schema(non_null[0], components)
        return {"type": "string"}

    return {"type": schema.get("type", "string")}


def derive_operation_parameter_schema(operation: dict, components: dict) -> dict:
    """Convert one OpenAPI operation's query parameters into a tool schema.

    Generic across any operation: it reads whatever query parameters and
    requiredness FastAPI actually generated, rather than a hand-maintained
    per-operation map. additionalProperties is always False, including for
    zero-parameter operations, since no properties are ever valid there.
    """
    parameters = [p for p in operation.get("parameters", []) if p.get("in") == "query"]

    properties: dict = {}
    required: list[str] = []
    for parameter in parameters:
        name = parameter["name"]
        resolved = _resolve_schema(parameter.get("schema", {}), components)
        description = parameter.get("description")
        if description:
            resolved["description"] = description
        properties[name] = resolved
        if parameter.get("required"):
            required.append(name)

    return {
        "type": "object",
        "additionalProperties": False,
        "required": required,
        "properties": properties,
    }


def collect_agent_tool_schemas(module_targets: list[str]) -> dict[str, dict]:
    schemas: dict[str, dict] = {}
    for module_target in module_targets:
        app = _load_app(module_target)
        spec = app.openapi()
        components = spec.get("components", {}).get("schemas", {})
        for path_item in spec.get("paths", {}).values():
            for operation in path_item.values():
                tags = operation.get("tags") or []
                if AGENT_TOOL_TAG not in tags:
                    continue
                operation_id = operation["operationId"]
                if operation_id in schemas:
                    raise ValueError(
                        f"Duplicate agent-tool operationId across dashlets: {operation_id!r}"
                    )
                schemas[operation_id] = derive_operation_parameter_schema(operation, components)
    return schemas


def _js_literal(value, indent: int = 0) -> str:
    pad = "    " * indent
    inner_pad = "    " * (indent + 1)
    if isinstance(value, dict):
        if not value:
            return "Object.freeze({})"
        lines = [f"{inner_pad}{key!r}: {_js_literal(val, indent + 1)}," for key, val in value.items()]
        body = "\n".join(lines).replace("'", '"')
        return "Object.freeze({\n" + body + f"\n{pad}}})"
    if isinstance(value, list):
        if not value:
            return "Object.freeze([])"
        items = ", ".join(repr(item).replace("'", '"') for item in value)
        return f"Object.freeze([{items}])"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return repr(value).replace("'", '"')
    return str(value)


def render_module(schemas: dict[str, dict]) -> str:
    entries = "\n".join(
        f"    {operation_id!r}: {_js_literal(schema, 1)},".replace("'", '"')
        for operation_id, schema in schemas.items()
    )
    return f"""// GENERATED FILE -- DO NOT EDIT BY HAND.
// Regenerate with: uv run python {GENERATOR_RELATIVE_PATH}
//
// Each entry is derived from the real OpenAPI output of an agent-tool-tagged
// FastAPI operation (see dashlets/*.py), not hand-maintained per operation.

export const AGENT_TOOL_PARAMETER_SCHEMAS = Object.freeze({{
{entries}
}});
"""


def main() -> int:
    check_only = "--check" in sys.argv[1:]
    schemas = collect_agent_tool_schemas(DASHLET_MODULES)
    rendered = render_module(schemas)

    if check_only:
        current = OUTPUT_PATH.read_text() if OUTPUT_PATH.exists() else ""
        if current != rendered:
            print(f"STALE: {OUTPUT_PATH} does not match the current dashlet OpenAPI output.")
            print(f"Run: uv run python {GENERATOR_RELATIVE_PATH}")
            return 1
        print(f"OK: {OUTPUT_PATH} is up to date.")
        return 0

    OUTPUT_PATH.write_text(rendered)
    print(f"Wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
