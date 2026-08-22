// Behavioral tests for the Treasury Curve dashlet's client-side Alpine
// component, specifically the data-mode switch orchestration added to fix
// requirement #8/#9 of the explicit provider-selection contract (see the
// `onDataModeChange`/`applyDataModeChange` methods in
// dashlets/treasury_curve_dashlet.py).
//
// There is no bundler or browser test harness in this repo for the inline
// Alpine script, so this test extracts the real inline <script> block from
// the FastAPI-rendered page (via `uv run python`) and executes it in a
// Node `vm` sandbox with a fake `Alpine`/`document`/`fetch`, giving true
// behavioral coverage of the exact shipped code rather than a duplicate
// reimplementation.
import test from "node:test";
import assert from "node:assert/strict";
import vm from "node:vm";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = path.resolve(__dirname, "..", "..");

function renderDashletHtml() {
    return execFileSync(
        "uv",
        ["run", "python", "-c", "from dashlets.treasury_curve_dashlet import index; print(index())"],
        { cwd: REPO_ROOT, encoding: "utf8", maxBuffer: 10 * 1024 * 1024 },
    );
}

function extractInlineTreasuryScript(html) {
    const scriptBlocks = [...html.matchAll(/<script(?:\s[^>]*)?>([\s\S]*?)<\/script>/g)].map((m) => m[1]);
    const target = scriptBlocks.find((block) => block.includes("treasuryApp"));
    if (!target) {
        throw new Error("Could not find inline treasuryApp <script> block in rendered HTML");
    }
    return target;
}

// Loads the real "treasuryApp" Alpine.data() factory out of the live template
// and returns a fresh component instance each time it's called.
//
// Each returned app instance gets its own isolated `fetch` implementation via
// `app.__setFetch(impl)`, so tests never leak mocks across sandboxed contexts.
function loadTreasuryAppFactory() {
    const html = renderDashletHtml();
    const scriptSource = extractInlineTreasuryScript(html);

    const registered = {};
    let activeFetchImpl = async () => {
        throw new Error("No fetch mock configured for this test");
    };
    const sandbox = {
        document: {
            addEventListener(eventName, callback) {
                if (eventName === "alpine:init") {
                    callback();
                }
            },
        },
        Alpine: {
            data(name, factory) {
                registered[name] = factory;
            },
        },
        URLSearchParams,
        fetch: (...args) => activeFetchImpl(...args),
        console,
    };
    vm.createContext(sandbox);
    vm.runInContext(scriptSource, sandbox, { filename: "treasuryApp-inline.js" });

    if (typeof registered.treasuryApp !== "function") {
        throw new Error("treasuryApp factory was not registered by the inline script");
    }
    const factory = registered.treasuryApp;
    return () => {
        const app = factory();
        app.__setFetch = (impl) => {
            activeFetchImpl = impl;
        };
        return app;
    };
}

const makeTreasuryApp = loadTreasuryAppFactory();

function makeApp(overrides = {}) {
    const app = makeTreasuryApp();
    // Avoid depending on Plotly/DOM for chart rendering in this headless harness.
    app.renderCurveChart = () => {};
    Object.assign(app, overrides);
    return app;
}

function jsonResponse(body, { ok = true, status = 200 } = {}) {
    return {
        ok,
        status,
        json: async () => body,
    };
}

function curvePayload(mode, observationDate) {
    return {
        points: [
            { maturity_label: "3M", maturity_years: 0.25, yield_percent: 4.9 },
            { maturity_label: "10Y", maturity_years: 10, yield_percent: 4.2 },
        ],
        provenance: {
            source: mode === "fixture" ? "synthetic-fixture" : "treasury-gov",
            data_mode: mode,
            observation_date: observationDate,
            retrieved_at: "2026-08-19T00:00:00Z",
            is_stale: false,
        },
    };
}

function slopesPayload(mode, observationDate) {
    return {
        observation_date: observationDate,
        slopes: [
            { name: "2s10s", value_bps: -70 },
            { name: "3m10y", value_bps: -50 },
        ],
        provenance: curvePayload(mode, observationDate).provenance,
    };
}

function comparisonPayload(mode, baseDate, compareDate) {
    return {
        base_observation_date: baseDate,
        compare_observation_date: compareDate,
        points: [{ maturity_label: "10Y", maturity_years: 10, base_yield_percent: 4.2, compare_yield_percent: 4.1, delta_bps: -10 }],
        provenance: {
            source: mode === "fixture" ? "synthetic-fixture" : "treasury-gov",
            data_mode: mode,
            observation_date: baseDate,
            retrieved_at: "2026-08-19T00:00:00Z",
            is_stale: false,
        },
    };
}

test("mode change reloads curve and slopes with the newly selected mode", async () => {
    const seenUrls = [];
    const app = makeApp({
        selectedDataMode: "eod",
        selectedDate: "2026-08-19",
    });
    app.__setFetch(async (url) => {
        seenUrls.push(url);
        if (url.includes("/api/treasury/curve")) {
            return jsonResponse(curvePayload("eod", "2026-08-19"));
        }
        if (url.includes("/api/treasury/slopes")) {
            return jsonResponse(slopesPayload("eod", "2026-08-19"));
        }
        throw new Error(`Unexpected fetch: ${url}`);
    });

    await app.onDataModeChange();

    const curveCall = seenUrls.find((u) => u.includes("/api/treasury/curve"));
    const slopesCall = seenUrls.find((u) => u.includes("/api/treasury/slopes"));
    assert.ok(curveCall, "expected a curve request");
    assert.ok(slopesCall, "expected a slopes request");
    assert.ok(curveCall.includes("data_mode=eod"), `curve request should use eod: ${curveCall}`);
    assert.ok(slopesCall.includes("data_mode=eod"), `slopes request should use eod: ${slopesCall}`);
    assert.equal(app.statusText, "Curve loaded");
    assert.equal(app.curvePoints.length, 2);
});

test("mode change reloads comparison when both comparison dates are selected", async () => {
    const seenUrls = [];
    const app = makeApp({
        selectedDataMode: "eod",
        selectedDate: "2026-08-19",
        compareDate: "2026-08-18",
    });
    app.__setFetch(async (url) => {
        seenUrls.push(url);
        if (url.includes("/api/treasury/curve")) return jsonResponse(curvePayload("eod", "2026-08-19"));
        if (url.includes("/api/treasury/slopes")) return jsonResponse(slopesPayload("eod", "2026-08-19"));
        if (url.includes("/api/treasury/compare")) return jsonResponse(comparisonPayload("eod", "2026-08-19", "2026-08-18"));
        throw new Error(`Unexpected fetch: ${url}`);
    });

    await app.onDataModeChange();

    const compareCall = seenUrls.find((u) => u.includes("/api/treasury/compare"));
    assert.ok(compareCall, "expected a comparison request to be issued");
    assert.ok(compareCall.includes("data_mode=eod"), `comparison request should use eod: ${compareCall}`);
    assert.equal(app.comparisonPoints.length, 1);
    assert.equal(app.statusText, "Comparison loaded");
});

test("mode change does not issue a comparison request when required dates are absent", async () => {
    const seenUrls = [];
    const app = makeApp({
        selectedDataMode: "eod",
        selectedDate: "2026-08-19",
        compareDate: "", // comparison date not selected
        comparisonPoints: [{ maturity_label: "10Y", maturity_years: 10, base_yield_percent: 1, compare_yield_percent: 2, delta_bps: 100 }],
        lastComparisonBaseDate: "2026-08-01",
        lastComparisonDate: "2026-08-02",
    });
    app.__setFetch(async (url) => {
        seenUrls.push(url);
        if (url.includes("/api/treasury/curve")) return jsonResponse(curvePayload("eod", "2026-08-19"));
        if (url.includes("/api/treasury/slopes")) return jsonResponse(slopesPayload("eod", "2026-08-19"));
        throw new Error(`Unexpected fetch during mode change without comparison dates: ${url}`);
    });

    await app.onDataModeChange();

    assert.ok(
        !seenUrls.some((u) => u.includes("/api/treasury/compare")),
        "must not call the comparison endpoint when a required date is missing",
    );
    // Stale comparison results from a previous mode must not be retained/mislabeled.
    // (Compared via length/isArray rather than assert.deepEqual([]) because the
    // vm sandbox's Array constructor is a distinct cross-realm object from the
    // one in this file, which assert's structural equality treats as unequal.)
    assert.ok(Array.isArray(app.comparisonPoints));
    assert.equal(app.comparisonPoints.length, 0);
    assert.equal(app.lastComparisonBaseDate, "");
    assert.equal(app.lastComparisonDate, "");
});

test("applyDataModeChange refuses to apply a result once a newer mode change has been requested", async () => {
    // Directly exercises the token guard used by onDataModeChange: if
    // dataModeToken has moved on by the time a (slow) curve fetch resolves,
    // the stale call must return without touching curvePoints/comparison state.
    const app = makeApp({
        selectedDataMode: "fixture",
        selectedDate: "2026-08-19",
        curvePoints: [{ maturity_label: "SENTINEL", maturity_years: 1, yield_percent: 0 }],
    });
    app.__setFetch(async (url) => {
        if (url.includes("/api/treasury/curve")) return jsonResponse(curvePayload("fixture", "2026-08-19"));
        if (url.includes("/api/treasury/slopes")) return jsonResponse(slopesPayload("fixture", "2026-08-19"));
        throw new Error(`Unexpected fetch: ${url}`);
    });

    const staleToken = app.dataModeToken + 1; // pretend a request was issued...
    app.dataModeToken = staleToken + 1; // ...then immediately superseded by a newer one

    await app.applyDataModeChange(staleToken);

    assert.deepEqual(
        app.curvePoints,
        [{ maturity_label: "SENTINEL", maturity_years: 1, yield_percent: 0 }],
        "a superseded (stale) token must not mutate curvePoints",
    );
});

test("mode change converges on the latest selected mode even when an earlier request resolves later", async () => {
    const app = makeApp({
        selectedDataMode: "fixture",
        selectedDate: "2026-08-19",
    });

    let releaseFixtureFetch;
    const fixtureFetchGate = new Promise((resolve) => {
        releaseFixtureFetch = resolve;
    });

    app.__setFetch(async (url) => {
        if (url.includes("/api/treasury/curve")) {
            if (url.includes("data_mode=fixture")) {
                // Simulate a slow fixture response that only resolves once the
                // test explicitly releases it (after the mode has already moved
                // on to eod below).
                await fixtureFetchGate;
                return jsonResponse(curvePayload("fixture", "2026-08-19"));
            }
            return jsonResponse(curvePayload("eod", "2026-08-19"));
        }
        if (url.includes("/api/treasury/slopes")) {
            const mode = url.includes("data_mode=fixture") ? "fixture" : "eod";
            return jsonResponse(slopesPayload(mode, "2026-08-19"));
        }
        throw new Error(`Unexpected fetch: ${url}`);
    });

    const firstChange = app.onDataModeChange(); // fixture, hangs on fetch
    await Promise.resolve(); // let the fixture fetch call start

    app.selectedDataMode = "eod";
    const secondChange = app.onDataModeChange(); // eod, queued behind the first

    releaseFixtureFetch();
    await Promise.all([firstChange, secondChange]);

    // The final, settled state must reflect eod (the last selected mode), not
    // the slower fixture response that started first.
    assert.equal(app.curvePoints[0].yield_percent, curvePayload("eod", "2026-08-19").points[0].yield_percent);
    assert.equal(app.provenanceText.includes("mode=eod"), true, `expected eod provenance, got: ${app.provenanceText}`);
});

test("EOD failure does not relabel retained fixture data/provenance as eod", async () => {
    const app = makeApp({
        selectedDataMode: "fixture",
        selectedDate: "2026-08-19",
    });
    app.__setFetch(async (url) => {
        if (url.includes("/api/treasury/curve")) return jsonResponse(curvePayload("fixture", "2026-08-19"));
        if (url.includes("/api/treasury/slopes")) return jsonResponse(slopesPayload("fixture", "2026-08-19"));
        throw new Error(`Unexpected fetch: ${url}`);
    });
    await app.onDataModeChange(); // establish retained fixture curve + provenance
    const retainedCurvePoints = app.curvePoints;
    const retainedProvenanceText = app.provenanceText;
    assert.ok(retainedProvenanceText.includes("mode=fixture"));

    // Now switch to eod, where the curve request fails (e.g. upstream feed down).
    app.selectedDataMode = "eod";
    app.__setFetch(async (url) => {
        if (url.includes("/api/treasury/curve")) {
            return jsonResponse({ detail: { error_code: "feed_timeout", message: "Treasury feed timed out" } }, { ok: false, status: 504 });
        }
        throw new Error(`Unexpected fetch during failure case: ${url}`);
    });

    await app.onDataModeChange();

    assert.equal(app.statusText, "Error");
    // Retained data and its provenance label must be untouched by the failed
    // eod attempt - never relabeled as eod while still showing fixture data.
    assert.deepEqual(app.curvePoints, retainedCurvePoints);
    assert.equal(app.provenanceText, retainedProvenanceText);
    assert.ok(app.provenanceText.includes("mode=fixture"));
    assert.ok(!app.provenanceText.includes("mode=eod"));
});
