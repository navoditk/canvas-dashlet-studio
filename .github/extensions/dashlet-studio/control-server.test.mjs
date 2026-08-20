import test from "node:test";
import assert from "node:assert/strict";
import { createServer, request as httpRequest } from "node:http";
import { once } from "node:events";
import { createControlApiHandler } from "./control-server.mjs";

function createFakeRuntime() {
    let state = {
        status: "idle",
        port: null,
        pid: null,
        dashletUrl: null,
        lastError: null,
        restarts: 0,
        diagnostics: [],
        timeouts: {},
    };

    return {
        start: async () => {
            state = { ...state, status: "running", port: 9900, dashletUrl: "http://127.0.0.1:9900" };
        },
        stop: async () => {
            state = { ...state, status: "idle", port: null, dashletUrl: null };
        },
        restart: async () => {
            state = { ...state, status: "running", restarts: state.restarts + 1, port: 9901, dashletUrl: "http://127.0.0.1:9901" };
        },
        getState: () => state,
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
    const runtime = createFakeRuntime();
    const proxy = { clear: () => {} };
    const server = createServer();
    await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
    const address = server.address();
    const port = typeof address === "object" && address ? address.port : 0;
    const host = `127.0.0.1:${port}`;
    const origin = `http://${host}`;
    const token = "test-token";

    const getStatusPayload = () => ({
        runtime: runtime.getState(),
        approvedOperations: [{ operationId: "get_dashlet_summary", method: "GET", pathName: "/api/summary" }],
    });

    const handler = createControlApiHandler({
        runtime,
        proxy,
        getStatusPayload,
        refreshToolsFromOpenApi: async () => {},
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
        await testFn({ port, host, origin, token });
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

test("GET cannot start stop or restart", async () => {
    await withTestServer(async ({ port, host, origin, token }) => {
        for (const path of ["/api/start", "/api/stop", "/api/restart"]) {
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
