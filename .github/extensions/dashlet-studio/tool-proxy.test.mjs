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
        "/api/treasury/curve": {
            get: {
                operationId: "get_treasury_curve",
                tags: ["agent-tool"],
                parameters: [{ name: "date", in: "query", required: false, schema: { type: "string" } }],
                responses: { 200: { description: "ok" } },
            },
        },
        "/api/treasury/slopes": {
            get: {
                operationId: "get_treasury_curve_slopes",
                tags: ["agent-tool"],
                parameters: [{ name: "date", in: "query", required: false, schema: { type: "string" } }],
                responses: { 200: { description: "ok" } },
            },
        },
        "/api/treasury/compare": {
            get: {
                operationId: "compare_treasury_curves",
                tags: ["agent-tool"],
                parameters: [
                    { name: "base_date", in: "query", required: true, schema: { type: "string" } },
                    { name: "compare_date", in: "query", required: true, schema: { type: "string" } },
                ],
                responses: { 200: { description: "ok" } },
            },
        },
        "/api/treasury/view": {
            get: {
                operationId: "get_treasury_curve_view",
                tags: ["ui-only"],
                parameters: [{ name: "date", in: "query", required: false, schema: { type: "string" } }],
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
    const observedPaths = [];
    const runtime = {
        fetchOpenApi: async () => SAMPLE_OPENAPI,
        request: async (pathName) => {
            observedPaths.push(pathName);
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
    assert.deepEqual(observedPaths, ["/api/summary"]);
    await assert.rejects(() => proxy.invoke("other_tagged_but_not_allowlisted", {}), /not approved/);
});

test("ToolProxy routes query args for Treasury tools", async () => {
    const observedPaths = [];
    const runtime = {
        fetchOpenApi: async () => SAMPLE_OPENAPI,
        request: async (pathName) => {
            observedPaths.push(pathName);
            return { ok: true };
        },
    };
    const proxy = new ToolProxy({
        runtime,
        allowlist: new Set(["get_treasury_curve", "get_treasury_curve_slopes", "compare_treasury_curves"]),
    });
    await proxy.refresh();

    await proxy.invoke("get_treasury_curve", { date: "2026-08-19" });
    await proxy.invoke("get_treasury_curve_slopes", {});
    await proxy.invoke("compare_treasury_curves", {
        base_date: "2026-08-18",
        compare_date: "2026-08-19",
    });

    assert.deepEqual(observedPaths, [
        "/api/treasury/curve?date=2026-08-19",
        "/api/treasury/slopes",
        "/api/treasury/compare?base_date=2026-08-18&compare_date=2026-08-19",
    ]);
});

test("ToolProxy enforces required args and blocks unknown args", async () => {
    const runtime = {
        fetchOpenApi: async () => SAMPLE_OPENAPI,
        request: async () => ({ ok: true }),
    };
    const proxy = new ToolProxy({
        runtime,
        allowlist: new Set(["compare_treasury_curves"]),
    });
    await proxy.refresh();
    await assert.rejects(() => proxy.invoke("compare_treasury_curves", { base_date: "2026-08-18" }), /requires argument "compare_date"/);
    await assert.rejects(
        () => proxy.invoke("compare_treasury_curves", { base_date: "2026-08-18", compare_date: "2026-08-19", evil: 1 }),
        /does not accept argument "evil"/,
    );
});

test("ToolProxy allowlist switch isolates Hello and Treasury tools", async () => {
    const runtime = {
        fetchOpenApi: async () => SAMPLE_OPENAPI,
        request: async (pathName) => {
            if (pathName.startsWith("/api/summary")) {
                return {
                    title: "Hello Dashlet",
                    message: "Smoke test successful",
                    generated_at: "2026-01-01T00:00:00Z",
                    source: "fixture",
                    data_mode: "fixture",
                };
            }
            return { ok: true };
        },
    };
    const proxy = new ToolProxy({ runtime, allowlist: new Set(["get_dashlet_summary"]) });
    await proxy.refresh();
    await proxy.invoke("get_dashlet_summary", {});
    await assert.rejects(() => proxy.invoke("get_treasury_curve", {}), /not approved/);

    proxy.setAllowlist(new Set(["get_treasury_curve", "compare_treasury_curves"]));
    await proxy.refresh();
    await proxy.invoke("get_treasury_curve", {});
    await assert.rejects(() => proxy.invoke("get_dashlet_summary", {}), /not approved/);
    await assert.rejects(() => proxy.invoke("get_treasury_curve_view", {}), /not approved/);
});
