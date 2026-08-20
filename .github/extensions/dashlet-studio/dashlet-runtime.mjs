import { createServer } from "node:net";
import { spawn } from "node:child_process";

const HEALTH_POLL_INTERVAL_MS = 300;
const SHUTDOWN_GRACE_MS = 3000;
const DIAGNOSTIC_LIMIT = 50;
const ENV_ALLOWLIST = ["PATH", "HOME", "TMPDIR", "LANG", "LC_ALL"];

function nowIso() {
    return new Date().toISOString();
}

function delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

async function withTimeout(promise, timeoutMs, timeoutMessage) {
    let timer;
    try {
        return await Promise.race([
            promise,
            new Promise((_, reject) => {
                timer = setTimeout(() => reject(new Error(timeoutMessage)), timeoutMs);
            }),
        ]);
    } finally {
        if (timer) {
            clearTimeout(timer);
        }
    }
}

async function findOpenPort(host = "127.0.0.1") {
    const server = createServer();
    await new Promise((resolve, reject) => {
        server.once("error", reject);
        server.listen(0, host, () => resolve());
    });

    const address = server.address();
    const port = typeof address === "object" && address ? address.port : undefined;
    await new Promise((resolve) => server.close(() => resolve()));
    if (!port) {
        throw new Error("Failed to allocate a local port");
    }
    return port;
}

function waitForExit(child) {
    if (!child || child.exitCode !== null || child.signalCode !== null) {
        return Promise.resolve();
    }
    return new Promise((resolve) => child.once("exit", () => resolve()));
}

async function killProcessTree(child) {
    if (!child || child.exitCode !== null || child.signalCode !== null) {
        return;
    }

    if (process.platform === "win32") {
        child.kill("SIGTERM");
        await withTimeout(waitForExit(child), SHUTDOWN_GRACE_MS, "Timed out waiting for process to stop").catch(() => {
            child.kill("SIGKILL");
        });
        await waitForExit(child);
        return;
    }

    const groupPid = -child.pid;
    try {
        process.kill(groupPid, "SIGTERM");
    } catch {
        child.kill("SIGTERM");
    }

    await withTimeout(waitForExit(child), SHUTDOWN_GRACE_MS, "Timed out waiting for process group to stop").catch(() => {
        try {
            process.kill(groupPid, "SIGKILL");
        } catch {
            child.kill("SIGKILL");
        }
    });
    await waitForExit(child);
}

async function fetchJsonWithTimeout(url, timeoutMs) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const response = await fetch(url, { signal: controller.signal });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status} from ${url}`);
        }
        return await response.json();
    } finally {
        clearTimeout(timer);
    }
}

function buildChildEnv(parentEnv = process.env) {
    const env = {};
    for (const key of ENV_ALLOWLIST) {
        const value = parentEnv[key];
        if (typeof value === "string" && value.length > 0) {
            env[key] = value;
        }
    }
    env.PYTHONUNBUFFERED = "1";
    env.PYTHONDONTWRITEBYTECODE = "1";
    return env;
}

export class DashletRuntime {
    constructor(options = {}) {
        this.cwd = options.cwd ?? process.cwd();
        this.startupTimeoutMs = options.startupTimeoutMs ?? 20_000;
        this.healthTimeoutMs = options.healthTimeoutMs ?? 1_500;
        this.requestTimeoutMs = options.requestTimeoutMs ?? 5_000;
        this.status = "idle";
        this.port = null;
        this.child = null;
        this.lastError = null;
        this.diagnostics = [];
        this.restarts = 0;
        this.sessionLog = options.sessionLog;
        this.spawnFn = options.spawnFn ?? spawn;
        this.startPromise = null;
    }

    addDiagnostic(level, message) {
        const entry = { at: nowIso(), level, message };
        this.diagnostics.push(entry);
        if (this.diagnostics.length > DIAGNOSTIC_LIMIT) {
            this.diagnostics.shift();
        }
    }

    async log(message, level = "info") {
        this.addDiagnostic(level, message);
        if (this.sessionLog) {
            await this.sessionLog(message, level).catch(() => {});
        }
    }

    getBaseUrl() {
        if (!this.port) {
            return null;
        }
        return `http://127.0.0.1:${this.port}`;
    }

    getState() {
        return {
            status: this.status,
            port: this.port,
            pid: this.child?.pid ?? null,
            dashletUrl: this.getBaseUrl(),
            lastError: this.lastError,
            restarts: this.restarts,
            diagnostics: [...this.diagnostics],
            timeouts: {
                startupTimeoutMs: this.startupTimeoutMs,
                healthTimeoutMs: this.healthTimeoutMs,
                requestTimeoutMs: this.requestTimeoutMs,
            },
        };
    }

    async waitForHealthy(baseUrl) {
        const deadline = Date.now() + this.startupTimeoutMs;
        while (Date.now() < deadline) {
            try {
                const health = await fetchJsonWithTimeout(`${baseUrl}/health`, this.healthTimeoutMs);
                if (health && typeof health === "object" && health.status) {
                    return;
                }
            } catch {
                // keep polling until startup deadline.
            }
            await delay(HEALTH_POLL_INTERVAL_MS);
        }
        throw new Error(`Startup timeout after ${this.startupTimeoutMs}ms waiting for /health`);
    }

    attachProcessLogs(child) {
        if (child.stdout) {
            child.stdout.on("data", (chunk) => {
                const text = String(chunk).trim();
                if (text) {
                    this.addDiagnostic("info", `[uvicorn] ${text}`);
                }
            });
        }
        if (child.stderr) {
            child.stderr.on("data", (chunk) => {
                const text = String(chunk).trim();
                if (text) {
                    this.addDiagnostic("warning", `[uvicorn] ${text}`);
                }
            });
        }
        child.on("exit", (code, signal) => {
            const detail = `Dashlet process exited (code=${String(code)}, signal=${String(signal)})`;
            this.addDiagnostic(code === 0 ? "info" : "error", detail);
            this.child = null;
            this.port = null;
            if (this.status !== "stopping" && this.status !== "idle") {
                this.status = "error";
                this.lastError = detail;
            } else if (this.status === "stopping") {
                this.status = "idle";
            }
        });
    }

    async start() {
        if (this.child && this.status === "running") {
            return this.getState();
        }
        if (this.startPromise) {
            return this.startPromise;
        }

        this.startPromise = (async () => {
            this.status = "starting";
            this.lastError = null;
            this.port = await findOpenPort("127.0.0.1");
            const args = [
                "run",
                "uvicorn",
                "dashlets.hello_dashlet:app",
                "--host",
                "127.0.0.1",
                "--port",
                String(this.port),
            ];

            await this.log(`Starting dashlet with: uv ${args.join(" ")}`);

            const child = this.spawnFn("uv", args, {
                cwd: this.cwd,
                shell: false,
                detached: process.platform !== "win32",
                stdio: ["ignore", "pipe", "pipe"],
                env: buildChildEnv(),
            });
            this.child = child;
            this.attachProcessLogs(child);

            try {
                const baseUrl = this.getBaseUrl();
                await this.waitForHealthy(baseUrl);
                this.status = "running";
                await this.log(`Dashlet is healthy at ${baseUrl}`);
                return this.getState();
            } catch (error) {
                this.status = "error";
                this.lastError = error instanceof Error ? error.message : String(error);
                await this.log(this.lastError, "error");
                await this.stop();
                throw error;
            } finally {
                this.startPromise = null;
            }
        })();

        return this.startPromise;
    }

    async stop() {
        if (this.startPromise) {
            await this.startPromise.catch(() => {});
        }
        if (!this.child) {
            this.status = "idle";
            this.port = null;
            return this.getState();
        }
        this.status = "stopping";
        await this.log("Stopping dashlet process");
        const child = this.child;
        await killProcessTree(child);
        this.child = null;
        this.port = null;
        this.status = "idle";
        await this.log("Dashlet stopped");
        return this.getState();
    }

    async restart() {
        this.restarts += 1;
        await this.log("Restart requested");
        await this.stop();
        return this.start();
    }

    async fetchOpenApi() {
        const baseUrl = this.getBaseUrl();
        if (!baseUrl) {
            throw new Error("Dashlet is not running");
        }
        return fetchJsonWithTimeout(`${baseUrl}/openapi.json`, this.requestTimeoutMs);
    }

    async request(pathname, options = {}) {
        const baseUrl = this.getBaseUrl();
        if (!baseUrl) {
            throw new Error("Dashlet is not running");
        }
        const method = options.method ?? "GET";
        const url = `${baseUrl}${pathname}`;
        await this.log(`Proxy request: ${method} ${url}`);
        const controller = new AbortController();
        const timer = setTimeout(() => controller.abort(), this.requestTimeoutMs);
        try {
            const response = await fetch(url, {
                method,
                headers: options.headers,
                body: options.body,
                signal: controller.signal,
            });
            if (!response.ok) {
                throw new Error(`HTTP ${response.status} from ${pathname}`);
            }
            return await response.json();
        } finally {
            clearTimeout(timer);
        }
    }

    async dispose() {
        await this.stop();
    }
}

export { findOpenPort, withTimeout };
export { buildChildEnv };
