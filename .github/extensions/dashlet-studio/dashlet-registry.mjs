// The registry of dashlets the Canvas extension is allowed to launch and the
// agent tools approved for each one. Split out from extension.mjs so it can
// be imported by tests without triggering extension.mjs's top-level
// joinSession() call. Keep DASHLET_MODULES in
// scripts/generate_tool_schemas.py in sync with the `module` value here when
// adding a dashlet -- see AGENTS.md §6.

export const DASHLET_REGISTRY = Object.freeze({
    hello: Object.freeze({
        id: "hello",
        displayName: "Hello Dashlet",
        module: "dashlets.hello_dashlet:app",
        approvedTools: Object.freeze(["get_dashlet_summary"]),
    }),
    "treasury-curve": Object.freeze({
        id: "treasury-curve",
        displayName: "Treasury Curve",
        module: "dashlets.treasury_curve_dashlet:app",
        approvedTools: Object.freeze(["get_treasury_curve", "get_treasury_curve_slopes", "compare_treasury_curves"]),
    }),
    "portfolio-exposure": Object.freeze({
        id: "portfolio-exposure",
        displayName: "Portfolio Exposure",
        module: "dashlets.portfolio_exposure_dashlet:app",
        approvedTools: Object.freeze([
            "get_portfolio_exposures",
            "get_top_concentrations",
            "compare_portfolio_exposures",
        ]),
    }),
    "portfolio-scenario": Object.freeze({
        id: "portfolio-scenario",
        displayName: "Portfolio Scenario Impact",
        module: "dashlets.portfolio_scenario_dashlet:app",
        approvedTools: Object.freeze([
            "run_portfolio_scenario",
            "get_scenario_contributions",
            "compare_scenario_impacts",
        ]),
    }),
});

export const REGISTERED_TOOL_IDS = [
    ...new Set(Object.values(DASHLET_REGISTRY).flatMap((entry) => entry.approvedTools)),
];

export const TOOL_DESCRIPTIONS = Object.freeze({
    get_dashlet_summary: "Get the typed summary from the local hello dashlet. This proxies GET /api/summary.",
    get_treasury_curve: "Get the deterministic Treasury curve for one observation date.",
    get_treasury_curve_slopes: "Get canonical Treasury curve slopes for one observation date.",
    compare_treasury_curves: "Compare two Treasury curves and return basis-point deltas by maturity.",
    get_portfolio_exposures: "Get deterministic long/short/net portfolio exposure by sector and issuer for one observation date.",
    get_top_concentrations: "Get the top issuer and sector concentrations by absolute net exposure weight for one observation date.",
    compare_portfolio_exposures: "Compare sector-level net portfolio exposure between two observation dates and return the deltas.",
    run_portfolio_scenario: "Apply a bounded rate/spread/equity shock to one observation date's portfolio and return deterministic total, position-level and sector-level impact.",
    get_scenario_contributions: "Apply a bounded rate/spread/equity shock and return the top position-level impact contributions plus per-sector contributions.",
    compare_scenario_impacts: "Compare two independent bounded rate/spread/equity shock scenarios on the same portfolio and return each scenario's totals plus per-sector impact deltas.",
});
