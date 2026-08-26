import { createServer } from "node:http";
import { joinSession, createCanvas } from "@github/copilot-sdk/extension";
import { DashletRuntime } from "./dashlet-runtime.mjs";
import { ToolProxy } from "./tool-proxy.mjs";
import { createControlApiHandler, createControlToken, renderCanvasPage } from "./control-server.mjs";
import { installProcessCleanupHandlers } from "./process-cleanup.mjs";
import { AGENT_TOOL_PARAMETER_SCHEMAS } from "./generated-tool-schemas.mjs";

// Defensive fallback only: every operationId in REGISTERED_TOOL_IDS is
// expected to have a generated entry in AGENT_TOOL_PARAMETER_SCHEMAS (see
// the drift-guard test in generated-tool-schemas.test.mjs). This exists so a
// future operationId that is approved in DASHLET_REGISTRY before its schema
// is regenerated fails safe (accepts nothing) rather than not registering at
// all.
const DEFAULT_TOOL_PARAMETER_SCHEMA = Object.freeze({
    type: "object",
    additionalProperties: false,
    required: Object.freeze([]),
    properties: Object.freeze({}),
});

const DASHLET_REGISTRY = Object.freeze({
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
const REGISTERED_TOOL_IDS = [
    ...new Set(Object.values(DASHLET_REGISTRY).flatMap((entry) => entry.approvedTools)),
];
const TOOL_DESCRIPTIONS = Object.freeze({
    get_dashlet_summary: "Get the typed summary from the local hello dashlet. This proxies GET /api/summary.",
    get_treasury_curve: "Get the deterministic Treasury curve for one observation date.",
    get_treasury_curve_slopes: "Get canonical Treasury curve slopes for one observation date.",
    compare_treasury_curves: "Compare two Treasury curves and return basis-point deltas by maturity.",
});

const canvasServers = new Map();

let sessionRef = null;
let selectedDashletId = "hello";
let activeDashletId = null;

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
    allowlist: new Set(DASHLET_REGISTRY[selectedDashletId].approvedTools),
});

async function refreshToolsFromOpenApi() {
    const info = await proxy.refresh();
    await runtime.log(`Approved operations: ${info.approvedOperationIds.join(", ") || "(none)"}`);
    return info;
}

function currentStatusPayload() {
    return {
        selectedDashletId,
        activeDashletId,
        availableDashlets: Object.values(DASHLET_REGISTRY).map((entry) => ({
            id: entry.id,
            displayName: entry.displayName,
        })),
        runtime: runtime.getState(),
        approvedOperations: proxy.listApprovedOperations(),
    };
}

function assertKnownDashletId(dashletId) {
    if (!Object.hasOwn(DASHLET_REGISTRY, dashletId)) {
        throw new Error(`Unknown dashlet ID "${dashletId}"`);
    }
}

function selectedDashlet() {
    return DASHLET_REGISTRY[selectedDashletId];
}

function isTransitionInProgress() {
    const { status } = runtime.getState();
    return status === "starting" || status === "stopping";
}

async function setSelectedDashlet(dashletId) {
    assertKnownDashletId(dashletId);
    if (isTransitionInProgress()) {
        throw new Error("Cannot change dashlet selection while start/stop is in progress");
    }
    selectedDashletId = dashletId;
    await runtime.log(`Selected dashlet changed to ${dashletId}`);
}

async function startSelectedDashlet() {
    const target = selectedDashlet();
    if (isTransitionInProgress()) {
        throw new Error("Cannot start while another lifecycle operation is in progress");
    }

    if (runtime.getState().status === "running" && activeDashletId && activeDashletId !== target.id) {
        await runtime.stop();
        proxy.clear();
        activeDashletId = null;
    }

    await runtime.start({
        moduleTarget: target.module,
        dashletId: target.id,
    });
    activeDashletId = target.id;
    proxy.setAllowlist(new Set(target.approvedTools));
    await refreshToolsFromOpenApi();
}

async function stopDashlet() {
    if (isTransitionInProgress()) {
        throw new Error("Cannot stop while another lifecycle operation is in progress");
    }
    await runtime.stop();
    proxy.clear();
    activeDashletId = null;
}

async function restartDashlet() {
    const target = selectedDashlet();
    if (isTransitionInProgress()) {
        throw new Error("Cannot restart while another lifecycle operation is in progress");
    }
    if (runtime.getState().status === "running" && activeDashletId && activeDashletId !== target.id) {
        await stopDashlet();
        await startSelectedDashlet();
        return;
    }
    await runtime.restart({
        moduleTarget: target.module,
        dashletId: target.id,
    });
    activeDashletId = target.id;
    proxy.setAllowlist(new Set(target.approvedTools));
    await refreshToolsFromOpenApi();
}

async function ensureRuntimeReady({ autoStart = false } = {}) {
    if (runtime.getState().status !== "running") {
        if (!autoStart) {
            throw new Error("Dashlet is not running");
        }
        await startSelectedDashlet();
        return;
    }
    if (!activeDashletId || !DASHLET_REGISTRY[activeDashletId]) {
        throw new Error("Active dashlet state is unavailable");
    }
    if (activeDashletId !== selectedDashletId) {
        if (!autoStart) {
            throw new Error("Selected dashlet is not active");
        }
        await startSelectedDashlet();
        return;
    }
    proxy.setAllowlist(new Set(DASHLET_REGISTRY[activeDashletId].approvedTools));
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
        getStatusPayload: currentStatusPayload,
        setSelectedDashlet,
        startSelectedDashlet,
        stopDashlet,
        restartDashlet,
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
    tools: REGISTERED_TOOL_IDS.map((operationId) => ({
        name: operationId,
        description: TOOL_DESCRIPTIONS[operationId] ?? `Proxy approved dashlet operation "${operationId}".`,
        parameters: AGENT_TOOL_PARAMETER_SCHEMAS[operationId] ?? DEFAULT_TOOL_PARAMETER_SCHEMA,
        handler: async (args) => {
            try {
                await ensureRuntimeReady();
                const result = await proxy.invoke(operationId, args ?? {});
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
    })),
    canvases: [
        createCanvas({
            id: "dashlet-studio",
            displayName: "Dashlet Studio",
            description:
                "Run and inspect approved FastAPI dashlets (Hello and Treasury Curve) with runtime controls and gated tools.",
            actions: [
                {
                    name: "select_dashlet",
                    description: "Select the approved dashlet ID for subsequent start/restart actions",
                    inputSchema: {
                        type: "object",
                        additionalProperties: false,
                        required: ["dashletId"],
                        properties: {
                            dashletId: {
                                type: "string",
                                enum: Object.keys(DASHLET_REGISTRY),
                            },
                        },
                    },
                    handler: async ({ input }) => {
                        await setSelectedDashlet(input?.dashletId);
                        return currentStatusPayload();
                    },
                },
                {
                    name: "start_dashlet",
                    description: "Start the selected local dashlet process",
                    handler: async () => {
                        await startSelectedDashlet();
                        return currentStatusPayload();
                    },
                },
                {
                    name: "stop_dashlet",
                    description: "Stop the active local dashlet process",
                    handler: async () => {
                        await stopDashlet();
                        return currentStatusPayload();
                    },
                },
                {
                    name: "restart_dashlet",
                    description: "Restart the selected local dashlet process",
                    handler: async () => {
                        await restartDashlet();
                        return currentStatusPayload();
                    },
                },
                {
                    name: "get_runtime_status",
                    description: "Get runtime status and diagnostics for the active dashlet",
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
                    await ensureRuntimeReady({ autoStart: true });
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
                    activeDashletId = null;
                }
            },
        }),
    ],
});

sessionRef = session;
await session.log("Dashlet Studio extension loaded");

installProcessCleanupHandlers({ runtime, proxy, canvasServers, processRef: process });
