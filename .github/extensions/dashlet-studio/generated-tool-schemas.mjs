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
    "run_portfolio_scenario": Object.freeze({
        "type": "object",
        "additionalProperties": false,
        "required": Object.freeze([]),
        "properties": Object.freeze({
            "date": Object.freeze({
                "type": "string",
                "description": "Observation date in YYYY-MM-DD format. Omit to use the latest available fixture date.",
            }),
            "rate_shock_bps": Object.freeze({
                "type": "number",
                "description": "Parallel rate shock, in basis points. Bounded -300 to +300.",
            }),
            "spread_shock_bps": Object.freeze({
                "type": "number",
                "description": "Parallel credit spread shock, in basis points. Bounded -500 to +500.",
            }),
            "equity_shock_pct": Object.freeze({
                "type": "number",
                "description": "Equity market shock, in percent. Bounded -50 to +50.",
            }),
        }),
    }),
    "get_scenario_contributions": Object.freeze({
        "type": "object",
        "additionalProperties": false,
        "required": Object.freeze([]),
        "properties": Object.freeze({
            "date": Object.freeze({
                "type": "string",
                "description": "Observation date in YYYY-MM-DD format. Omit to use the latest available fixture date.",
            }),
            "rate_shock_bps": Object.freeze({
                "type": "number",
                "description": "Parallel rate shock, in basis points. Bounded -300 to +300.",
            }),
            "spread_shock_bps": Object.freeze({
                "type": "number",
                "description": "Parallel credit spread shock, in basis points. Bounded -500 to +500.",
            }),
            "equity_shock_pct": Object.freeze({
                "type": "number",
                "description": "Equity market shock, in percent. Bounded -50 to +50.",
            }),
            "top_n": Object.freeze({
                "type": "integer",
                "description": "Number of top position impacts to return (1-20).",
            }),
        }),
    }),
    "compare_scenario_impacts": Object.freeze({
        "type": "object",
        "additionalProperties": false,
        "required": Object.freeze([]),
        "properties": Object.freeze({
            "date": Object.freeze({
                "type": "string",
                "description": "Observation date in YYYY-MM-DD format. Omit to use the latest available fixture date.",
            }),
            "rate_bps_a": Object.freeze({
                "type": "number",
                "description": "Scenario A: Parallel rate shock, in basis points. Bounded -300 to +300.",
            }),
            "spread_bps_a": Object.freeze({
                "type": "number",
                "description": "Scenario A: Parallel credit spread shock, in basis points. Bounded -500 to +500.",
            }),
            "equity_pct_a": Object.freeze({
                "type": "number",
                "description": "Scenario A: Equity market shock, in percent. Bounded -50 to +50.",
            }),
            "rate_bps_b": Object.freeze({
                "type": "number",
                "description": "Scenario B: Parallel rate shock, in basis points. Bounded -300 to +300.",
            }),
            "spread_bps_b": Object.freeze({
                "type": "number",
                "description": "Scenario B: Parallel credit spread shock, in basis points. Bounded -500 to +500.",
            }),
            "equity_pct_b": Object.freeze({
                "type": "number",
                "description": "Scenario B: Equity market shock, in percent. Bounded -50 to +50.",
            }),
        }),
    }),
});
