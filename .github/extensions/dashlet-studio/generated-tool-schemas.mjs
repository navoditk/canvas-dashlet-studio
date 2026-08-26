// GENERATED FILE -- DO NOT EDIT BY HAND.
// Regenerate with: uv run python scripts/generate_tool_schemas.py
//
// Each entry is derived from the real OpenAPI output of an agent-tool-tagged
// FastAPI operation (see dashlets/*.py), not hand-maintained per operation.

export const AGENT_TOOL_PARAMETER_SCHEMAS = Object.freeze({
    "get_dashlet_summary": Object.freeze({
        "type": "object",
        "additionalProperties": false,
        "required": Object.freeze([]),
        "properties": Object.freeze({}),
    }),
    "get_treasury_curve": Object.freeze({
        "type": "object",
        "additionalProperties": false,
        "required": Object.freeze(["data_mode"]),
        "properties": Object.freeze({
            "date": Object.freeze({
                "type": "string",
                "description": "Observation date in YYYY-MM-DD format. Omit to use the latest available fixture date.",
            }),
            "data_mode": Object.freeze({
                "type": "string",
                "enum": Object.freeze(["fixture", "eod"]),
                "description": "Required treasury data mode. Allowed values: fixture, eod.",
            }),
        }),
    }),
    "get_treasury_curve_slopes": Object.freeze({
        "type": "object",
        "additionalProperties": false,
        "required": Object.freeze(["data_mode"]),
        "properties": Object.freeze({
            "date": Object.freeze({
                "type": "string",
                "description": "Observation date in YYYY-MM-DD format. Omit to use the latest available fixture date.",
            }),
            "data_mode": Object.freeze({
                "type": "string",
                "enum": Object.freeze(["fixture", "eod"]),
                "description": "Required treasury data mode. Allowed values: fixture, eod.",
            }),
        }),
    }),
    "compare_treasury_curves": Object.freeze({
        "type": "object",
        "additionalProperties": false,
        "required": Object.freeze(["base_date", "compare_date", "data_mode"]),
        "properties": Object.freeze({
            "base_date": Object.freeze({
                "type": "string",
                "description": "Required base observation date in YYYY-MM-DD format.",
            }),
            "compare_date": Object.freeze({
                "type": "string",
                "description": "Required comparison observation date in YYYY-MM-DD format.",
            }),
            "data_mode": Object.freeze({
                "type": "string",
                "enum": Object.freeze(["fixture", "eod"]),
                "description": "Required treasury data mode. Allowed values: fixture, eod.",
            }),
        }),
    }),
    "get_portfolio_exposures": Object.freeze({
        "type": "object",
        "additionalProperties": false,
        "required": Object.freeze([]),
        "properties": Object.freeze({
            "date": Object.freeze({
                "type": "string",
                "description": "Observation date in YYYY-MM-DD format. Omit to use the latest available fixture date.",
            }),
        }),
    }),
    "get_top_concentrations": Object.freeze({
        "type": "object",
        "additionalProperties": false,
        "required": Object.freeze([]),
        "properties": Object.freeze({
            "date": Object.freeze({
                "type": "string",
                "description": "Observation date in YYYY-MM-DD format. Omit to use the latest available fixture date.",
            }),
            "top_n": Object.freeze({
                "type": "integer",
                "description": "Number of top concentrations to return (1-20).",
            }),
        }),
    }),
    "compare_portfolio_exposures": Object.freeze({
        "type": "object",
        "additionalProperties": false,
        "required": Object.freeze(["base_date", "compare_date"]),
        "properties": Object.freeze({
            "base_date": Object.freeze({
                "type": "string",
                "description": "Required base observation date in YYYY-MM-DD format.",
            }),
            "compare_date": Object.freeze({
                "type": "string",
                "description": "Required comparison observation date in YYYY-MM-DD format.",
            }),
        }),
    }),
});
