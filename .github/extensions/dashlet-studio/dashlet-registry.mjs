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
});

export const REGISTERED_TOOL_IDS = [
    ...new Set(Object.values(DASHLET_REGISTRY).flatMap((entry) => entry.approvedTools)),
];

export const TOOL_DESCRIPTIONS = Object.freeze({
    get_dashlet_summary: "Get the typed summary from the local hello dashlet. This proxies GET /api/summary.",
    get_treasury_curve: "Get the deterministic Treasury curve for one observation date.",
    get_treasury_curve_slopes: "Get canonical Treasury curve slopes for one observation date.",
    compare_treasury_curves: "Compare two Treasury curves and return basis-point deltas by maturity.",
});
