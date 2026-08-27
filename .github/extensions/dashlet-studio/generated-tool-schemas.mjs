// GENERATED FILE -- DO NOT EDIT BY HAND.
// Regenerate with: uv run python scripts/generate_tool_schemas.py
//
// Each entry is derived from the real OpenAPI output of an agent-tool-tagged
// FastAPI operation (see dashlets/*.py), not hand-maintained per operation.

function deepFreeze(value) {
    if (value && typeof value === "object" && !Object.isFrozen(value)) {
        Object.values(value).forEach(deepFreeze);
        Object.freeze(value);
    }
    return value;
}

export const AGENT_TOOL_PARAMETER_SCHEMAS = deepFreeze({
    "get_dashlet_summary": {
        "type": "object",
        "additionalProperties": false,
        "required": [],
        "properties": {}
    },
    "get_treasury_curve": {
        "type": "object",
        "additionalProperties": false,
        "required": [
            "data_mode"
        ],
        "properties": {
            "date": {
                "type": "string",
                "description": "Observation date in YYYY-MM-DD format. Omit to use the latest available fixture date."
            },
            "data_mode": {
                "type": "string",
                "enum": [
                    "fixture",
                    "eod"
                ],
                "description": "Required treasury data mode. Allowed values: fixture, eod."
            }
        }
    },
    "get_treasury_curve_slopes": {
        "type": "object",
        "additionalProperties": false,
        "required": [
            "data_mode"
        ],
        "properties": {
            "date": {
                "type": "string",
                "description": "Observation date in YYYY-MM-DD format. Omit to use the latest available fixture date."
            },
            "data_mode": {
                "type": "string",
                "enum": [
                    "fixture",
                    "eod"
                ],
                "description": "Required treasury data mode. Allowed values: fixture, eod."
            }
        }
    },
    "compare_treasury_curves": {
        "type": "object",
        "additionalProperties": false,
        "required": [
            "base_date",
            "compare_date",
            "data_mode"
        ],
        "properties": {
            "base_date": {
                "type": "string",
                "description": "Required base observation date in YYYY-MM-DD format."
            },
            "compare_date": {
                "type": "string",
                "description": "Required comparison observation date in YYYY-MM-DD format."
            },
            "data_mode": {
                "type": "string",
                "enum": [
                    "fixture",
                    "eod"
                ],
                "description": "Required treasury data mode. Allowed values: fixture, eod."
            }
        }
    },
    "get_portfolio_exposures": {
        "type": "object",
        "additionalProperties": false,
        "required": [],
        "properties": {
            "date": {
                "type": "string",
                "description": "Observation date in YYYY-MM-DD format. Omit to use the latest available fixture date."
            }
        }
    },
    "get_top_concentrations": {
        "type": "object",
        "additionalProperties": false,
        "required": [],
        "properties": {
            "date": {
                "type": "string",
                "description": "Observation date in YYYY-MM-DD format. Omit to use the latest available fixture date."
            },
            "top_n": {
                "type": "integer",
                "description": "Number of top concentrations to return (1-20)."
            }
        }
    },
    "compare_portfolio_exposures": {
        "type": "object",
        "additionalProperties": false,
        "required": [
            "base_date",
            "compare_date"
        ],
        "properties": {
            "base_date": {
                "type": "string",
                "description": "Required base observation date in YYYY-MM-DD format."
            },
            "compare_date": {
                "type": "string",
                "description": "Required comparison observation date in YYYY-MM-DD format."
            }
        }
    },
    "run_portfolio_scenario": {
        "type": "object",
        "additionalProperties": false,
        "required": [],
        "properties": {
            "date": {
                "type": "string",
                "description": "Observation date in YYYY-MM-DD format. Omit to use the latest available fixture date."
            },
            "rate_shock_bps": {
                "type": "number",
                "description": "Parallel rate shock, in basis points. Bounded -300 to +300."
            },
            "spread_shock_bps": {
                "type": "number",
                "description": "Parallel credit spread shock, in basis points. Bounded -500 to +500."
            },
            "equity_shock_pct": {
                "type": "number",
                "description": "Equity market shock, in percent. Bounded -50 to +50."
            }
        }
    },
    "get_scenario_contributions": {
        "type": "object",
        "additionalProperties": false,
        "required": [],
        "properties": {
            "date": {
                "type": "string",
                "description": "Observation date in YYYY-MM-DD format. Omit to use the latest available fixture date."
            },
            "rate_shock_bps": {
                "type": "number",
                "description": "Parallel rate shock, in basis points. Bounded -300 to +300."
            },
            "spread_shock_bps": {
                "type": "number",
                "description": "Parallel credit spread shock, in basis points. Bounded -500 to +500."
            },
            "equity_shock_pct": {
                "type": "number",
                "description": "Equity market shock, in percent. Bounded -50 to +50."
            },
            "top_n": {
                "type": "integer",
                "description": "Number of top position impacts to return (1-20)."
            }
        }
    },
    "compare_scenario_impacts": {
        "type": "object",
        "additionalProperties": false,
        "required": [],
        "properties": {
            "date": {
                "type": "string",
                "description": "Observation date in YYYY-MM-DD format. Omit to use the latest available fixture date."
            },
            "rate_bps_a": {
                "type": "number",
                "description": "Scenario A: Parallel rate shock, in basis points. Bounded -300 to +300."
            },
            "spread_bps_a": {
                "type": "number",
                "description": "Scenario A: Parallel credit spread shock, in basis points. Bounded -500 to +500."
            },
            "equity_pct_a": {
                "type": "number",
                "description": "Scenario A: Equity market shock, in percent. Bounded -50 to +50."
            },
            "rate_bps_b": {
                "type": "number",
                "description": "Scenario B: Parallel rate shock, in basis points. Bounded -300 to +300."
            },
            "spread_bps_b": {
                "type": "number",
                "description": "Scenario B: Parallel credit spread shock, in basis points. Bounded -500 to +500."
            },
            "equity_pct_b": {
                "type": "number",
                "description": "Scenario B: Equity market shock, in percent. Bounded -50 to +50."
            }
        }
    },
    "get_company_facts": {
        "type": "object",
        "additionalProperties": false,
        "required": [
            "ticker",
            "data_mode"
        ],
        "properties": {
            "ticker": {
                "type": "string",
                "description": "Company ticker symbol, e.g. AAPL. Case-insensitive."
            },
            "data_mode": {
                "type": "string",
                "enum": [
                    "fixture",
                    "live"
                ],
                "description": "Required data source. 'fixture' uses a small set of recorded real SEC snapshots (AAPL, MSFT) for deterministic testing. 'live' fetches current data from SEC EDGAR for any of the ~10,388 SEC-registered tickers."
            }
        }
    },
    "get_financial_trends": {
        "type": "object",
        "additionalProperties": false,
        "required": [
            "ticker",
            "data_mode"
        ],
        "properties": {
            "ticker": {
                "type": "string",
                "description": "Company ticker symbol, e.g. AAPL. Case-insensitive."
            },
            "data_mode": {
                "type": "string",
                "enum": [
                    "fixture",
                    "live"
                ],
                "description": "Required data source. 'fixture' uses a small set of recorded real SEC snapshots (AAPL, MSFT) for deterministic testing. 'live' fetches current data from SEC EDGAR for any of the ~10,388 SEC-registered tickers."
            },
            "years": {
                "type": "integer",
                "description": "Number of most recent fiscal years to return (1-5)."
            }
        }
    },
    "list_recent_filings": {
        "type": "object",
        "additionalProperties": false,
        "required": [
            "ticker",
            "data_mode"
        ],
        "properties": {
            "ticker": {
                "type": "string",
                "description": "Company ticker symbol, e.g. AAPL. Case-insensitive."
            },
            "data_mode": {
                "type": "string",
                "enum": [
                    "fixture",
                    "live"
                ],
                "description": "Required data source. 'fixture' uses a small set of recorded real SEC snapshots (AAPL, MSFT) for deterministic testing. 'live' fetches current data from SEC EDGAR for any of the ~10,388 SEC-registered tickers."
            },
            "limit": {
                "type": "integer",
                "description": "Number of most recent filings to return (1-8)."
            },
            "form_type": {
                "type": "string",
                "description": "Optional filter to one filing form type, e.g. '10-K'. Omit for all forms."
            }
        }
    }
});
