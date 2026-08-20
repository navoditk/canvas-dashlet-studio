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
      <p class="muted">Smoke-test controls for the local FastAPI process.</p>
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
    async function controlPost(path) {
      const response = await fetch(path, {
        method: "POST",
        headers: {
          "X-Dashlet-Control-Token": CONTROL_TOKEN
        }
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
      document.getElementById("status").innerHTML = [
        "<p><strong>Status:</strong> " + runtime.status + "</p>",
        "<p><strong>Port:</strong> " + (runtime.port ?? "n/a") + "</p>",
        "<p><strong>Dashlet URL:</strong> " + (runtime.dashletUrl ?? "n/a") + "</p>",
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
    document.getElementById("startBtn").addEventListener("click", async () => { await controlPost("/api/start"); await refresh(); });
    document.getElementById("stopBtn").addEventListener("click", async () => { await controlPost("/api/stop"); await refresh(); });
    document.getElementById("restartBtn").addEventListener("click", async () => { await controlPost("/api/restart"); await refresh(); });
    setInterval(refresh, 1500);
    refresh();
  </script>
</body>
</html>`;
}

export function createControlApiHandler({
    runtime,
    proxy,
    getStatusPayload,
    refreshToolsFromOpenApi,
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
                await runtime.start();
                await refreshToolsFromOpenApi();
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
            await runtime.stop();
            proxy.clear();
            jsonResponse(res, 200, getStatusPayload());
            return;
        }

        if (pathname === "/api/restart") {
            if (req.method !== "POST") {
                rejectInvalidMethod(res, "POST");
                return;
            }
            try {
                await runtime.restart();
                await refreshToolsFromOpenApi();
                jsonResponse(res, 200, getStatusPayload());
            } catch (error) {
                const message = error instanceof Error ? error.message : "Restart failed";
                jsonResponse(res, 500, { error: message });
            }
            return;
        }

        res.statusCode = 404;
        res.end("Not found");
    };
}
