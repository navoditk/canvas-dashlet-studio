import { createServer } from "node:http";
import { joinSession, createCanvas } from "@github/copilot-sdk/extension";
import { DashletRuntime } from "./dashlet-runtime.mjs";
import { ToolProxy } from "./tool-proxy.mjs";
import { createControlApiHandler, createControlToken, renderCanvasPage } from "./control-server.mjs";
import { installProcessCleanupHandlers } from "./process-cleanup.mjs";

const ALLOWLIST = new Set(["get_dashlet_summary"]);
const canvasServers = new Map();

let sessionRef = null;

const runtime = new DashletRuntime({
    startupTimeoutMs: 20_000,
    healthTimeoutMs: 1_500,
    requestTimeoutMs: 5_000,
    sessionLog: async (message, level) => {
        if (!sessionRef) {
            return;
        }
        await sessionRef.log(message, { level });
    },
});

const proxy = new ToolProxy({
    runtime,
    allowlist: ALLOWLIST,
});

async function refreshToolsFromOpenApi() {
    const info = await proxy.refresh();
    await runtime.log(`Approved operations: ${info.approvedOperationIds.join(", ") || "(none)"}`);
    return info;
}

function currentStatusPayload() {
    return {
        runtime: runtime.getState(),
        approvedOperations: proxy.listApprovedOperations(),
    };
}

async function ensureRunningAndLoaded() {
    if (runtime.getState().status !== "running") {
        await runtime.start();
    }
    await refreshToolsFromOpenApi();
}

async function startCanvasServer(instanceId) {
    const server = createServer();
    await new Promise((resolve) => server.listen(0, "127.0.0.1", resolve));
    const address = server.address();
    const port = typeof address === "object" && address ? address.port : 0;
    const controlToken = createControlToken();
    const expectedHost = `127.0.0.1:${port}`;
    const expectedOrigin = `http://${expectedHost}`;
    const controlHandler = createControlApiHandler({
        runtime,
        proxy,
        getStatusPayload: currentStatusPayload,
        refreshToolsFromOpenApi,
        expectedHost,
        expectedOrigin,
        controlToken,
        renderPage: () => renderCanvasPage(controlToken),
    });
    server.on("request", (req, res) => {
        controlHandler(req, res).catch((error) => {
            const message = error instanceof Error ? error.message : "Control server error";
            res.statusCode = 500;
            res.setHeader("Content-Type", "application/json; charset=utf-8");
            res.end(JSON.stringify({ error: message }));
        });
    });
    return {
        instanceId,
        server,
        url: `http://127.0.0.1:${port}/`,
    };
}

const session = await joinSession({
    // Tool registration is static for this smoke test; runtime invocation is lifecycle-gated
    // by ensureRunningAndLoaded() and ToolProxy's live OpenAPI allowlist checks.
    tools: [
        {
            name: "get_dashlet_summary",
            description:
                "Get the typed summary from the local hello dashlet. This proxies GET /api/summary.",
            parameters: {
                type: "object",
                additionalProperties: false,
                properties: {},
            },
            handler: async (args) => {
                try {
                    await ensureRunningAndLoaded();
                    const result = await proxy.invoke("get_dashlet_summary", args ?? {});
                    return {
                        resultType: "success",
                        textResultForLlm: JSON.stringify(result),
                    };
                } catch (error) {
                    return {
                        resultType: "failure",
                        textResultForLlm: error instanceof Error ? error.message : String(error),
                    };
                }
            },
        },
    ],
    canvases: [
        createCanvas({
            id: "dashlet-studio",
            displayName: "Dashlet Studio",
            description:
                "Run and inspect the hello FastAPI dashlet, with runtime controls and the get_dashlet_summary tool.",
            actions: [
                {
                    name: "start_dashlet",
                    description: "Start the local hello dashlet process",
                    handler: async () => {
                        await runtime.start();
                        await refreshToolsFromOpenApi();
                        return currentStatusPayload();
                    },
                },
                {
                    name: "stop_dashlet",
                    description: "Stop the local hello dashlet process",
                    handler: async () => {
                        await runtime.stop();
                        proxy.clear();
                        return currentStatusPayload();
                    },
                },
                {
                    name: "restart_dashlet",
                    description: "Restart the local hello dashlet process",
                    handler: async () => {
                        await runtime.restart();
                        await refreshToolsFromOpenApi();
                        return currentStatusPayload();
                    },
                },
                {
                    name: "get_runtime_status",
                    description: "Get runtime status and diagnostics for the hello dashlet",
                    handler: async () => currentStatusPayload(),
                },
            ],
            open: async (ctx) => {
                let canvasServer = canvasServers.get(ctx.instanceId);
                if (!canvasServer) {
                    canvasServer = await startCanvasServer(ctx.instanceId);
                    canvasServers.set(ctx.instanceId, canvasServer);
                }
                try {
                    await ensureRunningAndLoaded();
                } catch (error) {
                    await runtime.log(
                        `Startup failed on open: ${error instanceof Error ? error.message : String(error)}`,
                        "error",
                    );
                }
                return {
                    title: "Dashlet Studio",
                    status: runtime.getState().status,
                    url: canvasServer.url,
                };
            },
            onClose: async (ctx) => {
                const canvasServer = canvasServers.get(ctx.instanceId);
                if (canvasServer) {
                    canvasServers.delete(ctx.instanceId);
                    await new Promise((resolve) => canvasServer.server.close(() => resolve()));
                }
                if (canvasServers.size === 0) {
                    await runtime.dispose();
                    proxy.clear();
                }
            },
        }),
    ],
});

sessionRef = session;
await session.log("Dashlet Studio extension loaded");

installProcessCleanupHandlers({ runtime, proxy, canvasServers, processRef: process });
