import test from "node:test";
import assert from "node:assert/strict";
import { createServer, request as httpRequest } from "node:http";
import { once } from "node:events";
import { createControlApiHandler } from "./control-server.mjs";

function createHarnessState() {
    const runtimeState = {
        status: "idle",
        port: null,
        pid: null,
        dashletUrl: null,
        moduleTarget: null,
        activeDashletId: null,
        lastError: null,
        restarts: 0,
        diagnostics: [],
        timeouts: {},
    };
    const availableDashlets = [
        { id: "hello", displayName: "Hello Dashlet", module: "dashlets.hello_dashlet:app" },
        { id: "treasury-curve", displayName: "Treasury Curve", module: "dashlets.treasury_curve_dashlet:app" },
    ];
    let selectedDashletId = "hello";
    let activeDashletId = null;
    let runningPid = 11000;
    let startCalls = 0;
    let stopCalls = 0;

    const validateKnownDashlet = (dashletId) => {
        if (!availableDashlets.some((entry) => entry.id === dashletId)) {
            throw new Error(`Unknown dashlet ID "${dashletId}"`);
        }
    };

    return {
        runtimeState,
        getStatusPayload: () => ({
            selectedDashletId,
            activeDashletId,
            availableDashlets: availableDashlets.map((entry) => ({ id: entry.id, displayName: entry.displayName })),
            runtime: { ...runtimeState },
            approvedOperations:
                activeDashletId === "hello"
                    ? [{ operationId: "get_dashlet_summary", method: "GET", pathName: "/api/summary" }]
                    : activeDashletId === "treasury-curve"
                      ? [
                            { operationId: "get_treasury_curve", method: "GET", pathName: "/api/treasury/curve" },
                            {
                                operationId: "get_treasury_curve_slopes",
                                method: "GET",
                                pathName: "/api/treasury/slopes",
                            },
                            {
                                operationId: "compare_treasury_curves",
                                method: "GET",
                                pathName: "/api/treasury/compare",
                            },
                        ]
                      : [],
        }),
        setSelectedDashlet: async (dashletId) => {
            validateKnownDashlet(dashletId);
            if (runtimeState.status === "starting" || runtimeState.status === "stopping") {
                throw new Error("Cannot change dashlet selection while start/stop is in progress");
            }
            selectedDashletId = dashletId;
        },
        startSelectedDashlet: async () => {
            validateKnownDashlet(selectedDashletId);
            runtimeState.status = "starting";
            if (activeDashletId && activeDashletId !== selectedDashletId) {
                stopCalls += 1;
            }
            startCalls += 1;
            runningPid += 1;
            activeDashletId = selectedDashletId;
            runtimeState.status = "running";
            runtimeState.pid = runningPid;
            runtimeState.port = 9000 + startCalls;
            runtimeState.moduleTarget = availableDashlets.find((entry) => entry.id === activeDashletId)?.module ?? null;
            runtimeState.activeDashletId = activeDashletId;
            runtimeState.dashletUrl = runtimeState.port ? `http://127.0.0.1:${runtimeState.port}` : null;
            runtimeState.diagnostics = [
                ...runtimeState.diagnostics,
                {
                    at: new Date().toISOString(),
                    level: "info",
                    message: `start:${activeDashletId}:${runtimeState.moduleTarget}`,
                },
            ];
        },
        stopDashlet: async () => {
            stopCalls += 1;
            runtimeState.status = "stopping";
            runtimeState.status = "idle";
            runtimeState.pid = null;
            runtimeState.port = null;
            runtimeState.moduleTarget = null;
            runtimeState.activeDashletId = null;
            runtimeState.dashletUrl = null;
            activeDashletId = null;
        },
        restartDashlet: async () => {
            runtimeState.restarts += 1;
            await Promise.resolve();
            if (activeDashletId) {
                stopCalls += 1;
            }
            await Promise.resolve();
            runtimeState.status = "running";
            runningPid += 1;
            startCalls += 1;
            activeDashletId = selectedDashletId;
            runtimeState.pid = runningPid;
            runtimeState.port = 9000 + startCalls;
            runtimeState.moduleTarget = availableDashlets.find((entry) => entry.id === activeDashletId)?.module ?? null;
            runtimeState.activeDashletId = activeDashletId;
            runtimeState.dashletUrl = runtimeState.port ? `http://127.0.0.1:${runtimeState.port}` : null;
        },
        getCounters: () => ({ startCalls, stopCalls }),
    };
}

function makeRequest({ port, path, method, headers = {}, body }) {
    return new Promise((resolve, reject) => {
        const req = httpRequest(
            {
                host: "127.0.0.1",
                port,
                path,
                method,
                headers,
            },
            (res) => {
                const chunks = [];
                res.on("data", (chunk) => chunks.push(chunk));
                res.on("end", () => {
                    resolve({
                        statusCode: res.statusCode,
                        headers: res.headers,
                        body: Buffer.concat(chunks).toString("utf8"),
                    });
                });
            },
        );
        req.on("error", reject);
        if (body) {
            req.write(body);
        }
        req.end();
    });
}

async function withTestServer(testFn) {
    const harness = createHarnessState();
    const server = createServer();
    await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
    const address = server.address();
    const port = typeof address === "object" && address ? address.port : 0;
    const host = `127.0.0.1:${port}`;
    const origin = `http://${host}`;
    const token = "test-token";

    const handler = createControlApiHandler({
        getStatusPayload: harness.getStatusPayload,
        setSelectedDashlet: harness.setSelectedDashlet,
        startSelectedDashlet: harness.startSelectedDashlet,
        stopDashlet: harness.stopDashlet,
        restartDashlet: harness.restartDashlet,
        expectedHost: host,
        expectedOrigin: origin,
        controlToken: token,
        renderPage: () => "<html><body>ok</body></html>",
    });
    server.on("request", (req, res) => {
        handler(req, res).catch(() => {
            res.statusCode = 500;
            res.end("error");
        });
    });

    try {
        await testFn({ port, host, origin, token, harness });
    } finally {
        server.close();
        await once(server, "close");
    }
}

function authHeaders({ host, origin, token }) {
    return {
        Host: host,
        Origin: origin,
        "X-Dashlet-Control-Token": token,
    };
}

test("missing token is rejected", async () => {
    await withTestServer(async ({ port, host, origin }) => {
        const response = await makeRequest({
            port,
            path: "/api/status",
            method: "POST",
            headers: { Host: host, Origin: origin },
        });
        assert.equal(response.statusCode, 401);
    });
});

test("incorrect token is rejected", async () => {
    await withTestServer(async ({ port, host, origin }) => {
        const response = await makeRequest({
            port,
            path: "/api/status",
            method: "POST",
            headers: authHeaders({ host, origin, token: "wrong-token" }),
        });
        assert.equal(response.statusCode, 401);
    });
});

test("incorrect host is rejected", async () => {
    await withTestServer(async ({ port, origin, token }) => {
        const response = await makeRequest({
            port,
            path: "/api/status",
            method: "POST",
            headers: authHeaders({ host: "127.0.0.1:1", origin, token }),
        });
        assert.equal(response.statusCode, 403);
    });
});

test("incorrect origin is rejected", async () => {
    await withTestServer(async ({ port, host, token }) => {
        const response = await makeRequest({
            port,
            path: "/api/status",
            method: "POST",
            headers: authHeaders({ host, origin: "http://example.com", token }),
        });
        assert.equal(response.statusCode, 403);
    });
});

test("GET cannot start stop restart or select", async () => {
    await withTestServer(async ({ port, host, origin, token }) => {
        for (const path of ["/api/start", "/api/stop", "/api/restart", "/api/select"]) {
            const response = await makeRequest({
                port,
                path,
                method: "GET",
                headers: authHeaders({ host, origin, token }),
            });
            assert.equal(response.statusCode, 405);
        }
    });
});

test("valid same-origin POST with valid token succeeds", async () => {
    await withTestServer(async ({ port, host, origin, token }) => {
        const response = await makeRequest({
            port,
            path: "/api/start",
            method: "POST",
            headers: authHeaders({ host, origin, token }),
        });
        assert.equal(response.statusCode, 200);
        const payload = JSON.parse(response.body);
        assert.equal(payload.runtime.status, "running");
        assert.equal(payload.selectedDashletId, "hello");
        assert.equal(payload.activeDashletId, "hello");
    });
});

test("unknown dashlet ID is rejected", async () => {
    await withTestServer(async ({ port, host, origin, token }) => {
        const response = await makeRequest({
            port,
            path: "/api/select",
            method: "POST",
            headers: {
                ...authHeaders({ host, origin, token }),
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ dashletId: "evil-module" }),
        });
        assert.equal(response.statusCode, 400);
        assert.match(response.body, /Unknown dashlet ID/);
    });
});

test("registry values cannot be overridden by request input", async () => {
    await withTestServer(async ({ port, host, origin, token }) => {
        const response = await makeRequest({
            port,
            path: "/api/select",
            method: "POST",
            headers: {
                ...authHeaders({ host, origin, token }),
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                dashletId: "treasury-curve",
                module: "os.system:danger",
                command: "rm -rf /",
                url: "http://evil.local",
                port: 1,
            }),
        });
        assert.equal(response.statusCode, 400);
        assert.match(response.body, /Unknown field \\"module\\"/);
    });
});

test("switching from Treasury to Hello records stop of prior process", async () => {
    await withTestServer(async ({ port, host, origin, token, harness }) => {
        const selectTreasury = await makeRequest({
            port,
            path: "/api/select",
            method: "POST",
            headers: {
                ...authHeaders({ host, origin, token }),
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ dashletId: "treasury-curve" }),
        });
        assert.equal(selectTreasury.statusCode, 200);

        const startTreasury = await makeRequest({
            port,
            path: "/api/start",
            method: "POST",
            headers: authHeaders({ host, origin, token }),
        });
        assert.equal(startTreasury.statusCode, 200);
        const treasuryPayload = JSON.parse(startTreasury.body);
        assert.equal(treasuryPayload.runtime.moduleTarget, "dashlets.treasury_curve_dashlet:app");

        const selectHello = await makeRequest({
            port,
            path: "/api/select",
            method: "POST",
            headers: {
                ...authHeaders({ host, origin, token }),
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ dashletId: "hello" }),
        });
        assert.equal(selectHello.statusCode, 200);

        const startHello = await makeRequest({
            port,
            path: "/api/start",
            method: "POST",
            headers: authHeaders({ host, origin, token }),
        });
        assert.equal(startHello.statusCode, 200);
        const helloPayload = JSON.parse(startHello.body);
        assert.equal(helloPayload.runtime.moduleTarget, "dashlets.hello_dashlet:app");
        assert.equal(helloPayload.activeDashletId, "hello");
        assert.equal(harness.getCounters().stopCalls >= 1, true);
    });
});

test("token is absent from status response and diagnostics", async () => {
    await withTestServer(async ({ port, host, origin, token }) => {
        const response = await makeRequest({
            port,
            path: "/api/status",
            method: "POST",
            headers: authHeaders({ host, origin, token }),
        });
        assert.equal(response.statusCode, 200);
        assert.equal(response.body.includes(token), false);
    });
});

test("permissive CORS is absent", async () => {
    await withTestServer(async ({ port, host, origin, token }) => {
        const response = await makeRequest({
            port,
            path: "/api/status",
            method: "POST",
            headers: authHeaders({ host, origin, token }),
        });
        assert.equal(response.statusCode, 200);
        assert.equal(response.headers["access-control-allow-origin"], undefined);
    });
});

test("arbitrary command path and URL inputs are rejected", async () => {
    await withTestServer(async ({ port, host, origin, token }) => {
        const body = JSON.stringify({ command: "rm -rf /", url: "http://evil.local", port: 4444 });
        const response = await makeRequest({
            port,
            path: "/api/exec",
            method: "POST",
            headers: {
                ...authHeaders({ host, origin, token }),
                "Content-Type": "application/json",
                "Content-Length": String(Buffer.byteLength(body)),
            },
            body,
        });
        assert.equal(response.statusCode, 404);
    });
});
