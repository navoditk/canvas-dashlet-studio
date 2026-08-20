import test from "node:test";
import assert from "node:assert/strict";
import { selectApprovedOperations, validateSummaryResponse, ToolProxy } from "./tool-proxy.mjs";

const SAMPLE_OPENAPI = {
    openapi: "3.1.0",
    info: { title: "Test API", version: "0.1.0" },
    paths: {
        "/api/summary": {
            get: {
                operationId: "get_dashlet_summary",
                tags: ["agent-tool"],
                responses: { 200: { description: "ok" } },
            },
        },
        "/api/internal": {
            get: {
                operationId: "internal_untagged",
                tags: ["internal"],
                responses: { 200: { description: "ok" } },
            },
        },
        "/api/other": {
            get: {
                operationId: "other_tagged_but_not_allowlisted",
                tags: ["agent-tool"],
                responses: { 200: { description: "ok" } },
            },
        },
    },
};

test("selectApprovedOperations requires both tag and allowlist", () => {
    const allowlist = new Set(["get_dashlet_summary"]);
    const approved = selectApprovedOperations(SAMPLE_OPENAPI, allowlist);
    assert.equal(approved.size, 1);
    assert.ok(approved.has("get_dashlet_summary"));
    assert.equal(approved.has("internal_untagged"), false);
    assert.equal(approved.has("other_tagged_but_not_allowlisted"), false);
});

test("validateSummaryResponse enforces required fields", () => {
    const valid = {
        title: "Hello",
        message: "World",
        generated_at: "2026-01-01T00:00:00Z",
        source: "fixture",
        data_mode: "fixture",
    };
    assert.deepEqual(validateSummaryResponse(valid), valid);
    assert.throws(() => validateSummaryResponse({ ...valid, message: "" }), /message/);
});

test("ToolProxy invokes approved operation and blocks unapproved ones", async () => {
    const runtime = {
        fetchOpenApi: async () => SAMPLE_OPENAPI,
        request: async (pathName) => {
            assert.equal(pathName, "/api/summary");
            return {
                title: "Hello Dashlet",
                message: "Smoke test successful",
                generated_at: "2026-01-01T00:00:00Z",
                source: "fixture",
                data_mode: "fixture",
            };
        },
    };
    const proxy = new ToolProxy({ runtime, allowlist: new Set(["get_dashlet_summary"]) });
    await proxy.refresh();
    const result = await proxy.invoke("get_dashlet_summary", {});
    assert.equal(result.title, "Hello Dashlet");
    await assert.rejects(() => proxy.invoke("other_tagged_but_not_allowlisted", {}), /not approved/);
});
