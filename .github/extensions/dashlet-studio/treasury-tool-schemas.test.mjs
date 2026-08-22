import test from "node:test";
import assert from "node:assert/strict";
import { TREASURY_TOOL_PARAMETER_SCHEMAS, DEFAULT_TOOL_PARAMETER_SCHEMA } from "./treasury-tool-schemas.mjs";

const TREASURY_OPERATION_IDS = ["get_treasury_curve", "get_treasury_curve_slopes", "compare_treasury_curves"];

test("all three Treasury capabilities expose a required data_mode enum of exactly fixture/eod", () => {
    for (const operationId of TREASURY_OPERATION_IDS) {
        const schema = TREASURY_TOOL_PARAMETER_SCHEMAS[operationId];
        assert.ok(schema, `expected a schema for ${operationId}`);
        assert.equal(schema.type, "object");
        assert.ok(Object.hasOwn(schema.properties, "data_mode"), `${operationId} must expose data_mode`);
        assert.deepEqual(schema.properties.data_mode.enum, ["fixture", "eod"]);
        assert.ok(schema.required.includes("data_mode"), `${operationId} must require data_mode`);
    }
});

test("get_treasury_curve and get_treasury_curve_slopes expose only their own date parameter", () => {
    for (const operationId of ["get_treasury_curve", "get_treasury_curve_slopes"]) {
        const schema = TREASURY_TOOL_PARAMETER_SCHEMAS[operationId];
        assert.deepEqual(Object.keys(schema.properties).sort(), ["data_mode", "date"]);
        // date is optional per FastAPI (anyOf[string, null]); only data_mode is required.
        assert.deepEqual(schema.required, ["data_mode"]);
        assert.equal(schema.properties.date.type, "string");
        assert.equal(schema.properties.date.format, "date");
    }
});

test("compare_treasury_curves exposes base_date/compare_date matching FastAPI requiredness", () => {
    const schema = TREASURY_TOOL_PARAMETER_SCHEMAS.compare_treasury_curves;
    assert.deepEqual(Object.keys(schema.properties).sort(), ["base_date", "compare_date", "data_mode"]);
    // base_date and compare_date are both required in FastAPI/OpenAPI.
    assert.deepEqual([...schema.required].sort(), ["base_date", "compare_date", "data_mode"]);
    assert.equal(schema.properties.base_date.type, "string");
    assert.equal(schema.properties.base_date.format, "date");
    assert.equal(schema.properties.compare_date.type, "string");
    assert.equal(schema.properties.compare_date.format, "date");
});

test("Treasury tool schemas reject additional unsupported properties", () => {
    for (const operationId of TREASURY_OPERATION_IDS) {
        const schema = TREASURY_TOOL_PARAMETER_SCHEMAS[operationId];
        assert.equal(schema.additionalProperties, false, `${operationId} must set additionalProperties: false`);
    }
});

test("get_dashlet_summary is not part of the Treasury schema map and keeps the generic default schema", () => {
    assert.equal(TREASURY_TOOL_PARAMETER_SCHEMAS.get_dashlet_summary, undefined);
    assert.equal(DEFAULT_TOOL_PARAMETER_SCHEMA.type, "object");
    assert.equal(DEFAULT_TOOL_PARAMETER_SCHEMA.additionalProperties, true);
    assert.deepEqual(DEFAULT_TOOL_PARAMETER_SCHEMA.properties, {});
});

test("Treasury operation IDs and allowlists referenced by the schema map remain unchanged", () => {
    // Guards against silent operationId drift between the schema map and the
    // registry/allowlist wired up in extension.mjs.
    assert.deepEqual(Object.keys(TREASURY_TOOL_PARAMETER_SCHEMAS).sort(), [...TREASURY_OPERATION_IDS].sort());
});

test("schema map objects are frozen (immutable)", () => {
    assert.ok(Object.isFrozen(TREASURY_TOOL_PARAMETER_SCHEMAS));
    for (const operationId of TREASURY_OPERATION_IDS) {
        assert.ok(Object.isFrozen(TREASURY_TOOL_PARAMETER_SCHEMAS[operationId]));
        assert.ok(Object.isFrozen(TREASURY_TOOL_PARAMETER_SCHEMAS[operationId].properties));
    }
    assert.ok(Object.isFrozen(DEFAULT_TOOL_PARAMETER_SCHEMA));
});
