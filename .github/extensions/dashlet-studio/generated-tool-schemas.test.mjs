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

test("schema map and each schema's properties are frozen (immutable)", () => {
    assert.ok(Object.isFrozen(AGENT_TOOL_PARAMETER_SCHEMAS));
    for (const schema of Object.values(AGENT_TOOL_PARAMETER_SCHEMAS)) {
        assert.ok(Object.isFrozen(schema));
        assert.ok(Object.isFrozen(schema.properties));
        assert.ok(Object.isFrozen(schema.required));
    }
});
