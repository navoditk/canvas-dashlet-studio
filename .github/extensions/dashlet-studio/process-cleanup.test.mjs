import test from "node:test";
import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import { createCleanupTask, installProcessCleanupHandlers } from "./process-cleanup.mjs";

function makeFakeServer(counter) {
    return {
        close(callback) {
            counter.count += 1;
            callback();
        },
    };
}

class FakeProcess extends EventEmitter {
    constructor() {
        super();
        this.exitCalls = [];
    }

    exit(code) {
        this.exitCalls.push(code);
    }
}

test("createCleanupTask is idempotent", async () => {
    let disposeCalls = 0;
    let clearCalls = 0;
    const closeCounter = { count: 0 };
    const canvasServers = new Map([["a", { server: makeFakeServer(closeCounter) }]]);
    const runtime = {
        dispose: async () => {
            disposeCalls += 1;
        },
    };
    const proxy = {
        clear: () => {
            clearCalls += 1;
        },
    };

    const cleanup = createCleanupTask({ runtime, proxy, canvasServers });
    await Promise.all([cleanup(), cleanup(), cleanup()]);

    assert.equal(disposeCalls, 1);
    assert.equal(clearCalls, 1);
    assert.equal(closeCounter.count, 1);
    assert.equal(canvasServers.size, 0);
});

test("process handlers are installed once and cleanup is bounded", async () => {
    const fakeProcess = new FakeProcess();
    let disposeCalls = 0;
    let clearCalls = 0;
    const closeCounter = { count: 0 };
    const canvasServers = new Map([["a", { server: makeFakeServer(closeCounter) }]]);
    const runtime = {
        dispose: async () => {
            disposeCalls += 1;
        },
    };
    const proxy = {
        clear: () => {
            clearCalls += 1;
        },
    };

    installProcessCleanupHandlers({
        runtime,
        proxy,
        canvasServers,
        processRef: fakeProcess,
        cleanupTimeoutMs: 25,
    });
    installProcessCleanupHandlers({
        runtime,
        proxy,
        canvasServers,
        processRef: fakeProcess,
        cleanupTimeoutMs: 25,
    });

    assert.equal(fakeProcess.listenerCount("SIGTERM"), 1);
    assert.equal(fakeProcess.listenerCount("SIGINT"), 1);
    assert.equal(fakeProcess.listenerCount("uncaughtException"), 1);
    assert.equal(fakeProcess.listenerCount("unhandledRejection"), 1);

    fakeProcess.emit("SIGTERM");
    await new Promise((resolve) => setTimeout(resolve, 40));

    assert.equal(fakeProcess.exitCalls[0], 0);
    assert.equal(disposeCalls, 1);
    assert.equal(clearCalls, 1);
    assert.equal(closeCounter.count, 1);
});

test("uncaughtException exits nonzero after cleanup", async () => {
    const fakeProcess = new FakeProcess();
    let disposeCalls = 0;
    const runtime = {
        dispose: async () => {
            disposeCalls += 1;
        },
    };
    const proxy = { clear: () => {} };
    const canvasServers = new Map();

    installProcessCleanupHandlers({
        runtime,
        proxy,
        canvasServers,
        processRef: fakeProcess,
        cleanupTimeoutMs: 25,
    });

    fakeProcess.emit("uncaughtException", new Error("boom"));
    await new Promise((resolve) => setTimeout(resolve, 40));

    assert.equal(fakeProcess.exitCalls.at(-1), 1);
    assert.equal(disposeCalls, 1);
});
