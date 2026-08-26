import test from "node:test";
import assert from "node:assert/strict";
import { DASHLET_REGISTRY, REGISTERED_TOOL_IDS, TOOL_DESCRIPTIONS } from "./dashlet-registry.mjs";

test("every registry entry has the required shape", () => {
    for (const [key, entry] of Object.entries(DASHLET_REGISTRY)) {
        assert.equal(entry.id, key, `entry key must match its own id`);
        assert.ok(typeof entry.displayName === "string" && entry.displayName.length > 0, `${key}.displayName`);
        assert.match(entry.module, /^[a-zA-Z0-9_.]+:app$/, `${key}.module must be "module.path:app"`);
        assert.ok(Array.isArray(entry.approvedTools), `${key}.approvedTools must be an array`);
    }
});

test("no operationId is approved by more than one dashlet", () => {
    const owners = new Map();
    for (const [key, entry] of Object.entries(DASHLET_REGISTRY)) {
        for (const operationId of entry.approvedTools) {
            assert.ok(
                !owners.has(operationId),
                `operationId "${operationId}" is approved by both "${owners.get(operationId)}" and "${key}"`,
            );
            owners.set(operationId, key);
        }
    }
});

test("REGISTERED_TOOL_IDS is exactly the union of every dashlet's approvedTools", () => {
    const expected = new Set(Object.values(DASHLET_REGISTRY).flatMap((entry) => entry.approvedTools));
    assert.deepEqual(new Set(REGISTERED_TOOL_IDS), expected);
});

test("every registered tool has a non-default TOOL_DESCRIPTIONS entry", () => {
    for (const operationId of REGISTERED_TOOL_IDS) {
        assert.ok(
            Object.hasOwn(TOOL_DESCRIPTIONS, operationId),
            `"${operationId}" is approved but has no entry in TOOL_DESCRIPTIONS ` +
                `(it would fall back to a generic "Proxy approved dashlet operation" description)`,
        );
    }
});

test("every DASHLET_REGISTRY object is frozen (immutable)", () => {
    assert.ok(Object.isFrozen(DASHLET_REGISTRY));
    for (const entry of Object.values(DASHLET_REGISTRY)) {
        assert.ok(Object.isFrozen(entry));
        assert.ok(Object.isFrozen(entry.approvedTools));
    }
    assert.ok(Object.isFrozen(TOOL_DESCRIPTIONS));
});
