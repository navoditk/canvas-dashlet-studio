import test from "node:test";
import assert from "node:assert/strict";
import { AGENT_TOOL_PARAMETER_SCHEMAS } from "./generated-tool-schemas.mjs";
import { REGISTERED_TOOL_IDS } from "./dashlet-registry.mjs";

const TREASURY_OPERATION_IDS = ["get_treasury_curve", "get_treasury_curve_slopes", "compare_treasury_curves"];

// This reads the real DASHLET_REGISTRY (via REGISTERED_TOOL_IDS), not a
// hand-copied list -- if a new operationId is approved in the registry
// without regenerating its schema, this test fails instead of the extension
// silently falling back to DEFAULT_TOOL_PARAMETER_SCHEMA at runtime.
test("every operationId approved in DASHLET_REGISTRY has a generated schema", () => {
    for (const operationId of REGISTERED_TOOL_IDS) {
        assert.ok(
            Object.hasOwn(AGENT_TOOL_PARAMETER_SCHEMAS, operationId),
            `expected a generated schema for ${operationId} (approved in DASHLET_REGISTRY)`,
        );
    }
});

test("every generated schema is a well-formed object schema", () => {
    for (const [operationId, schema] of Object.entries(AGENT_TOOL_PARAMETER_SCHEMAS)) {
        assert.equal(schema.type, "object", `${operationId} schema.type`);
        assert.equal(schema.additionalProperties, false, `${operationId} additionalProperties`);
        assert.ok(Array.isArray(schema.required), `${operationId} required must be an array`);
        assert.ok(typeof schema.properties === "object" && schema.properties !== null, `${operationId} properties`);
        for (const requiredName of schema.required) {
            assert.ok(
                Object.hasOwn(schema.properties, requiredName),
                `${operationId}: required "${requiredName}" must also be a property`,
            );
        }
    }
});

test("get_dashlet_summary has no parameters", () => {
    const schema = AGENT_TOOL_PARAMETER_SCHEMAS.get_dashlet_summary;
    assert.deepEqual(schema.required, []);
    assert.deepEqual(schema.properties, {});
});

test("all three Treasury capabilities expose a required data_mode enum of exactly fixture/eod", () => {
    for (const operationId of TREASURY_OPERATION_IDS) {
        const schema = AGENT_TOOL_PARAMETER_SCHEMAS[operationId];
        assert.ok(Object.hasOwn(schema.properties, "data_mode"), `${operationId} must expose data_mode`);
        assert.deepEqual(schema.properties.data_mode.enum, ["fixture", "eod"]);
        assert.ok(schema.required.includes("data_mode"), `${operationId} must require data_mode`);
    }
});

test("get_treasury_curve and get_treasury_curve_slopes expose only their own date parameter", () => {
    for (const operationId of ["get_treasury_curve", "get_treasury_curve_slopes"]) {
        const schema = AGENT_TOOL_PARAMETER_SCHEMAS[operationId];
        assert.deepEqual(Object.keys(schema.properties).sort(), ["data_mode", "date"]);
        // date is optional per FastAPI (anyOf[string, null]); only data_mode is required.
        assert.deepEqual(schema.required, ["data_mode"]);
        assert.equal(schema.properties.date.type, "string");
    }
});

test("compare_treasury_curves exposes base_date/compare_date matching FastAPI requiredness", () => {
    const schema = AGENT_TOOL_PARAMETER_SCHEMAS.compare_treasury_curves;
    assert.deepEqual(Object.keys(schema.properties).sort(), ["base_date", "compare_date", "data_mode"]);
    assert.deepEqual([...schema.required].sort(), ["base_date", "compare_date", "data_mode"]);
    assert.equal(schema.properties.base_date.type, "string");
    assert.equal(schema.properties.compare_date.type, "string");
});

test("get_portfolio_exposures and get_top_concentrations expose only optional date (+ top_n)", () => {
    const exposures = AGENT_TOOL_PARAMETER_SCHEMAS.get_portfolio_exposures;
    assert.deepEqual(Object.keys(exposures.properties).sort(), ["date"]);
    assert.deepEqual(exposures.required, []);

    const concentrations = AGENT_TOOL_PARAMETER_SCHEMAS.get_top_concentrations;
    assert.deepEqual(Object.keys(concentrations.properties).sort(), ["date", "top_n"]);
    assert.deepEqual(concentrations.required, []);
    assert.equal(concentrations.properties.top_n.type, "integer");
});

test("compare_portfolio_exposures requires base_date and compare_date, no data_mode", () => {
    const schema = AGENT_TOOL_PARAMETER_SCHEMAS.compare_portfolio_exposures;
    assert.deepEqual(Object.keys(schema.properties).sort(), ["base_date", "compare_date"]);
    assert.deepEqual([...schema.required].sort(), ["base_date", "compare_date"]);
    // Unlike Treasury, Portfolio Exposure has no live data source in this MVP
    // (see dashlets/portfolio_provider.py), so there is no data_mode parameter.
    assert.ok(!Object.hasOwn(schema.properties, "data_mode"));
});

test("run_portfolio_scenario and get_scenario_contributions expose bounded, all-optional shock parameters", () => {
    const run = AGENT_TOOL_PARAMETER_SCHEMAS.run_portfolio_scenario;
    assert.deepEqual(Object.keys(run.properties).sort(), [
        "date",
        "equity_shock_pct",
        "rate_shock_bps",
        "spread_shock_bps",
    ]);
    assert.deepEqual(run.required, []); // every shock defaults to 0.0 -- a zero-shock request is valid

    const contributions = AGENT_TOOL_PARAMETER_SCHEMAS.get_scenario_contributions;
    assert.deepEqual(Object.keys(contributions.properties).sort(), [
        "date",
        "equity_shock_pct",
        "rate_shock_bps",
        "spread_shock_bps",
        "top_n",
    ]);
    assert.equal(contributions.properties.top_n.type, "integer");
});

test("compare_scenario_impacts exposes two full independent shock specifications, no data_mode", () => {
    const schema = AGENT_TOOL_PARAMETER_SCHEMAS.compare_scenario_impacts;
    assert.deepEqual(Object.keys(schema.properties).sort(), [
        "date",
        "equity_pct_a",
        "equity_pct_b",
        "rate_bps_a",
        "rate_bps_b",
        "spread_bps_a",
        "spread_bps_b",
    ]);
    assert.deepEqual(schema.required, []);
    assert.ok(!Object.hasOwn(schema.properties, "data_mode"));
});

test("get_company_facts requires ticker and data_mode, data_mode is an enum of exactly fixture/live", () => {
    const schema = AGENT_TOOL_PARAMETER_SCHEMAS.get_company_facts;
    assert.deepEqual(Object.keys(schema.properties).sort(), ["data_mode", "ticker"]);
    assert.deepEqual([...schema.required].sort(), ["data_mode", "ticker"]);
    assert.deepEqual(schema.properties.data_mode.enum, ["fixture", "live"]);
    // Regression check: a prior generator bug corrupted this description's
    // embedded single-quoted 'fixture'/'live' references into invalid JS
    // syntax. Asserting the literal text survives generation intact.
    assert.ok(schema.properties.data_mode.description.includes("'fixture'"));
    assert.ok(schema.properties.data_mode.description.includes("'live'"));
});

test("get_financial_trends and list_recent_filings expose their own optional parameters plus required ticker/data_mode", () => {
    const trends = AGENT_TOOL_PARAMETER_SCHEMAS.get_financial_trends;
    assert.deepEqual(Object.keys(trends.properties).sort(), ["data_mode", "ticker", "years"]);
    assert.deepEqual([...trends.required].sort(), ["data_mode", "ticker"]);
    assert.equal(trends.properties.years.type, "integer");

    const filings = AGENT_TOOL_PARAMETER_SCHEMAS.list_recent_filings;
    assert.deepEqual(Object.keys(filings.properties).sort(), ["data_mode", "form_type", "limit", "ticker"]);
    assert.deepEqual([...filings.required].sort(), ["data_mode", "ticker"]);
});

test("schema map and each schema's properties are frozen (immutable)", () => {
    assert.ok(Object.isFrozen(AGENT_TOOL_PARAMETER_SCHEMAS));
    for (const schema of Object.values(AGENT_TOOL_PARAMETER_SCHEMAS)) {
        assert.ok(Object.isFrozen(schema));
        assert.ok(Object.isFrozen(schema.properties));
        assert.ok(Object.isFrozen(schema.required));
    }
});
