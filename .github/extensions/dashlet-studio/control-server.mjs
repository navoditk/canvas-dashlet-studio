import { randomBytes, timingSafeEqual } from "node:crypto";

export const CONTROL_TOKEN_HEADER = "x-dashlet-control-token";

function jsonResponse(res, code, payload) {
    res.statusCode = code;
    res.setHeader("Content-Type", "application/json; charset=utf-8");
    res.end(JSON.stringify(payload));
}

function getHeader(req, name) {
    const value = req.headers?.[name];
    if (Array.isArray(value)) {
        return value[0] ?? "";
    }
    return typeof value === "string" ? value : "";
}

function safeTokenEqual(expectedToken, receivedToken) {
    if (typeof receivedToken !== "string" || receivedToken.length === 0) {
        return false;
    }
    const expected = Buffer.from(expectedToken, "utf8");
    const actual = Buffer.from(receivedToken, "utf8");
    if (expected.length !== actual.length) {
        return false;
    }
    return timingSafeEqual(expected, actual);
}

export function createControlToken() {
    return randomBytes(32).toString("base64url");
}

function authorizeControlRequest(req, expectedHost, expectedOrigin, controlToken) {
    const host = getHeader(req, "host");
    if (host !== expectedHost) {
        return { authorized: false, statusCode: 403, payload: { error: "Forbidden host" } };
    }

    const origin = getHeader(req, "origin");
    if (origin !== expectedOrigin) {
        return { authorized: false, statusCode: 403, payload: { error: "Forbidden origin" } };
    }

    const providedToken = getHeader(req, CONTROL_TOKEN_HEADER);
    if (!safeTokenEqual(controlToken, providedToken)) {
        return { authorized: false, statusCode: 401, payload: { error: "Unauthorized token" } };
    }
    return { authorized: true };
}

function parsePath(req, expectedOrigin) {
    try {
        const url = new URL(req.url ?? "/", expectedOrigin);
        return url.pathname;
    } catch {
        return null;
    }
}

function rejectInvalidMethod(res, allowed) {
    res.statusCode = 405;
    res.setHeader("Allow", allowed);
    jsonResponse(res, 405, { error: "Method not allowed" });
}

async function readJsonBody(req, maxBytes = 4096) {
    const chunks = [];
    let total = 0;
    for await (const chunk of req) {
        total += chunk.length;
        if (total > maxBytes) {
            throw new Error("Request body too large");
        }
        chunks.push(chunk);
    }
    if (chunks.length === 0) {
        return {};
    }
    const text = Buffer.concat(chunks).toString("utf8");
    if (text.trim().length === 0) {
        return {};
    }
    const parsed = JSON.parse(text);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
        throw new Error("Request JSON body must be an object");
    }
    return parsed;
}

export function renderCanvasPage(controlToken) {
    return `<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>Dashlet Studio</title>
  <style>
    body {
      margin: 0;
      font-family: var(--font-sans, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif);
      background: var(--background-color-default, #fff);
      color: var(--text-color-default, #1f2328);
    }
    .layout {
      display: grid;
      grid-template-columns: 320px 1fr;
      height: 100vh;
    }
    .panel {
      border-right: 1px solid var(--border-color-default, #d1d9e0);
      padding: 12px;
      overflow: auto;
    }
    .controls button {
      margin-right: 8px;
      margin-bottom: 8px;
    }
    .muted { color: var(--text-color-muted, #59636e); }
    .diag {
      white-space: pre-wrap;
      font-family: var(--font-mono, "SFMono-Regular", Consolas, monospace);
      font-size: 12px;
      border: 1px solid var(--border-color-default, #d1d9e0);
      border-radius: 6px;
      padding: 8px;
      max-height: 260px;
      overflow: auto;
      background: rgba(127, 127, 127, 0.06);
    }
    iframe {
      width: 100%;
      height: 100%;
      border: none;
      background: #fff;
    }
  </style>
</head>
<body>
  <div class="layout">
    <section class="panel">
      <h2>Dashlet Studio</h2>
      <p class="muted">Smoke-test controls for approved local FastAPI dashlets.</p>
      <div>
        <label for="dashletSelect"><strong>Selected dashlet:</strong></label><br/>
        <select id="dashletSelect"></select>
      </div>
      <div class="controls">
        <button id="startBtn" type="button">Start</button>
        <button id="stopBtn" type="button">Stop</button>
        <button id="restartBtn" type="button">Restart</button>
      </div>
      <div id="status"></div>
      <h3>Approved operations</h3>
      <div id="ops" class="diag">[]</div>
      <h3>Diagnostics</h3>
      <div id="diagnostics" class="diag"></div>
    </section>
    <section>
      <iframe id="dashletFrame" src="about:blank" title="Hello Dashlet"></iframe>
    </section>
  </div>
  <script>
    const CONTROL_TOKEN = ${JSON.stringify(controlToken)};
    let pending = false;
    async function controlPost(path) {
      const response = await fetch(path, {
        method: "POST",
        headers: {
          "X-Dashlet-Control-Token": CONTROL_TOKEN,
          "Content-Type": "application/json"
        },
        body: "{}"
      });
      if (!response.ok) {
        const body = await response.text();
        throw new Error(body || "Request failed");
      }
      return response.json();
    }
    async function controlPostJson(path, payload) {
      const response = await fetch(path, {
        method: "POST",
        headers: {
          "X-Dashlet-Control-Token": CONTROL_TOKEN,
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload ?? {})
      });
      if (!response.ok) {
        const body = await response.text();
        throw new Error(body || "Request failed");
      }
      return response.json();
    }
    async function getStatus() {
      return controlPost("/api/status");
    }
    function render(state) {
      const runtime = state.runtime;
      const select = document.getElementById("dashletSelect");
      const options = Array.isArray(state.availableDashlets) ? state.availableDashlets : [];
      const desired = state.selectedDashletId || "";
      const previousValue = select.value;
      select.innerHTML = "";
      for (const option of options) {
        const entry = document.createElement("option");
        entry.value = option.id;
        entry.textContent = option.displayName;
        if (option.id === desired) {
          entry.selected = true;
        }
        select.appendChild(entry);
      }
      if (desired && select.value !== desired) {
        select.value = desired;
      } else if (!desired && previousValue) {
        select.value = previousValue;
      }
      const transitionLocked = runtime.status === "starting" || runtime.status === "stopping" || pending;
      select.disabled = transitionLocked;
      document.getElementById("startBtn").disabled = transitionLocked;
      document.getElementById("stopBtn").disabled = transitionLocked;
      document.getElementById("restartBtn").disabled = transitionLocked;
      document.getElementById("status").innerHTML = [
        "<p><strong>Status:</strong> " + runtime.status + "</p>",
        "<p><strong>Selected:</strong> " + (state.selectedDashletId ?? "n/a") + "</p>",
        "<p><strong>Active:</strong> " + (state.activeDashletId ?? "none") + "</p>",
        "<p><strong>Port:</strong> " + (runtime.port ?? "n/a") + "</p>",
        "<p><strong>PID:</strong> " + (runtime.pid ?? "n/a") + "</p>",
        "<p><strong>Dashlet URL:</strong> " + (runtime.dashletUrl ?? "n/a") + "</p>",
        "<p><strong>Module:</strong> " + (runtime.moduleTarget ?? "n/a") + "</p>",
        "<p><strong>Last error:</strong> " + (runtime.lastError ?? "none") + "</p>"
      ].join("");
      document.getElementById("ops").textContent = JSON.stringify(state.approvedOperations, null, 2);
      const diag = (runtime.diagnostics || []).map((d) => "[" + d.at + "] " + d.level + " " + d.message).join("\\n");
      document.getElementById("diagnostics").textContent = diag || "No diagnostics yet.";
      const frame = document.getElementById("dashletFrame");
      if (runtime.dashletUrl && frame.getAttribute("src") !== runtime.dashletUrl + "/") {
        frame.setAttribute("src", runtime.dashletUrl + "/");
      }
      if (!runtime.dashletUrl) {
        frame.setAttribute("src", "about:blank");
      }
    }
    async function refresh() {
      try {
        render(await getStatus());
      } catch (error) {
        document.getElementById("diagnostics").textContent = String(error);
      }
    }
    async function runWithPending(work) {
      if (pending) {
        return;
      }
      pending = true;
      try {
        await work();
      } finally {
        pending = false;
        await refresh();
      }
    }
    document.getElementById("dashletSelect").addEventListener("change", async (event) => {
      const dashletId = event.target.value;
      await runWithPending(async () => {
        await controlPostJson("/api/select", { dashletId });
      });
    });
    document.getElementById("startBtn").addEventListener("click", async () => {
      await runWithPending(async () => {
        await controlPost("/api/start");
      });
    });
    document.getElementById("stopBtn").addEventListener("click", async () => {
      await runWithPending(async () => {
        await controlPost("/api/stop");
      });
    });
    document.getElementById("restartBtn").addEventListener("click", async () => {
      await runWithPending(async () => {
        await controlPost("/api/restart");
      });
    });
    setInterval(refresh, 1500);
    refresh();
  </script>
</body>
</html>`;
}

export function createControlApiHandler({
    getStatusPayload,
    setSelectedDashlet,
    startSelectedDashlet,
    stopDashlet,
    restartDashlet,
    expectedHost,
    expectedOrigin,
    controlToken,
    renderPage,
}) {
    return async function handleControlApi(req, res) {
        const pathname = parsePath(req, expectedOrigin);
        if (!pathname) {
            jsonResponse(res, 400, { error: "Invalid request URL" });
            return;
        }

        if (pathname === "/" && req.method === "GET") {
            res.statusCode = 200;
            res.setHeader("Content-Type", "text/html; charset=utf-8");
            res.end(renderPage());
            return;
        }

        const isApiPath = pathname.startsWith("/api/");
        if (!isApiPath) {
            res.statusCode = 404;
            res.end("Not found");
            return;
        }

        const authResult = authorizeControlRequest(req, expectedHost, expectedOrigin, controlToken);
        if (!authResult.authorized) {
            jsonResponse(res, authResult.statusCode, authResult.payload);
            return;
        }

        if (pathname === "/api/status") {
            if (req.method !== "POST") {
                rejectInvalidMethod(res, "POST");
                return;
            }
            jsonResponse(res, 200, getStatusPayload());
            return;
        }

        if (pathname === "/api/start") {
            if (req.method !== "POST") {
                rejectInvalidMethod(res, "POST");
                return;
            }
            try {
                await startSelectedDashlet();
                jsonResponse(res, 200, getStatusPayload());
            } catch (error) {
                const message = error instanceof Error ? error.message : "Start failed";
                jsonResponse(res, 500, { error: message });
            }
            return;
        }

        if (pathname === "/api/stop") {
            if (req.method !== "POST") {
                rejectInvalidMethod(res, "POST");
                return;
            }
            await stopDashlet();
            jsonResponse(res, 200, getStatusPayload());
            return;
        }

        if (pathname === "/api/restart") {
            if (req.method !== "POST") {
                rejectInvalidMethod(res, "POST");
                return;
            }
            try {
                await restartDashlet();
                jsonResponse(res, 200, getStatusPayload());
            } catch (error) {
                const message = error instanceof Error ? error.message : "Restart failed";
                jsonResponse(res, 500, { error: message });
            }
            return;
        }

        if (pathname === "/api/select") {
            if (req.method !== "POST") {
                rejectInvalidMethod(res, "POST");
                return;
            }
            try {
                const body = await readJsonBody(req);
                const allowedKeys = ["dashletId"];
                for (const key of Object.keys(body)) {
                    if (!allowedKeys.includes(key)) {
                        jsonResponse(res, 400, { error: `Unknown field "${key}"` });
                        return;
                    }
                }
                if (typeof body.dashletId !== "string" || body.dashletId.length === 0) {
                    jsonResponse(res, 400, { error: "dashletId is required" });
                    return;
                }
                await setSelectedDashlet(body.dashletId);
                jsonResponse(res, 200, getStatusPayload());
            } catch (error) {
                const message = error instanceof Error ? error.message : "Select failed";
                const statusCode = /progress/.test(message) ? 409 : 400;
                jsonResponse(res, statusCode, { error: message });
            }
            return;
        }

        res.statusCode = 404;
        res.end("Not found");
    };
}
