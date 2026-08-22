// Live integration smoke test: exercises the real ToolProxy + Treasury tool
// schemas against a running FastAPI treasury dashlet (started separately on
// TREASURY_BASE_URL). Not part of the automated test suite; used for manual
// verification of the explicit provider-selection contract end-to-end.
import { ToolProxy, selectApprovedOperations } from "../../.github/extensions/dashlet-studio/tool-proxy.mjs";
import {
    TREASURY_TOOL_PARAMETER_SCHEMAS,
} from "../../.github/extensions/dashlet-studio/treasury-tool-schemas.mjs";

const BASE_URL = process.env.TREASURY_BASE_URL || "http://127.0.0.1:8791";

const runtime = {
    async fetchOpenApi() {
        const response = await fetch(`${BASE_URL}/openapi.json`);
        return response.json();
    },
    async request(pathname) {
        const response = await fetch(`${BASE_URL}${pathname}`);
        const body = await response.json().catch(() => ({}));
        if (!response.ok) {
            const err = new Error(`HTTP ${response.status}: ${JSON.stringify(body)}`);
            err.status = response.status;
            err.body = body;
            throw err;
        }
        return body;
    },
};

const allowlist = new Set(["get_treasury_curve", "get_treasury_curve_slopes", "compare_treasury_curves"]);
const proxy = new ToolProxy({ runtime, allowlist });

async function main() {
    const refreshInfo = await proxy.refresh();
    console.log("1) Approved operations after live refresh:", refreshInfo.approvedOperationIds);

    console.log("\n2) Agent-visible tool schema for get_treasury_curve (data_mode enum):");
    console.log(JSON.stringify(TREASURY_TOOL_PARAMETER_SCHEMAS.get_treasury_curve, null, 2));

    console.log("\n3) Canvas fixture-mode invocation (get_treasury_curve, data_mode=fixture, date=2026-08-19):");
    try {
        const fixtureResult = await proxy.invoke("get_treasury_curve", { date: "2026-08-19", data_mode: "fixture" });
        console.log("   OK -> provenance:", fixtureResult.provenance);
    } catch (err) {
        console.log("   FAILED:", err.message);
    }

    console.log("\n4) Canvas EOD-mode invocation (get_treasury_curve, data_mode=eod, date=2026-08-19):");
    try {
        const eodResult = await proxy.invoke("get_treasury_curve", { date: "2026-08-19", data_mode: "eod" });
        console.log("   OK -> provenance:", eodResult.provenance);
    } catch (err) {
        console.log("   EXPECTED-STYLE FAILURE (no fixture fallback occurred; error surfaced instead):", err.message);
    }

    console.log("\n5) Missing data_mode (should be rejected before reaching FastAPI/provider):");
    try {
        await proxy.invoke("get_treasury_curve", { date: "2026-08-19" });
        console.log("   UNEXPECTED SUCCESS");
    } catch (err) {
        console.log("   Rejected as expected:", err.message);
    }

    console.log("\n6) Invalid data_mode value 'live' (must be rejected, not silently treated as fixture):");
    try {
        const res = await proxy.invoke("get_treasury_curve", { date: "2026-08-19", data_mode: "live" });
        console.log("   UNEXPECTED SUCCESS:", res);
    } catch (err) {
        console.log("   Rejected as expected:", err.message);
    }
}

main().catch((err) => {
    console.error("Smoke test crashed:", err);
    process.exit(1);
});
