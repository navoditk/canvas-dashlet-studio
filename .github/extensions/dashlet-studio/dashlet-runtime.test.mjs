import test from "node:test";
import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import { DashletRuntime, findOpenPort, withTimeout, buildChildEnv } from "./dashlet-runtime.mjs";

test("findOpenPort returns a positive integer port", async () => {
    const port = await findOpenPort("127.0.0.1");
    assert.equal(Number.isInteger(port), true);
    assert.equal(port > 0, true);
});

test("withTimeout rejects slow promises", async () => {
    await assert.rejects(
        () =>
            withTimeout(
                new Promise((resolve) => setTimeout(resolve, 100)),
                10,
                "timed out",
            ),
        /timed out/,
    );
});

test("buildChildEnv allowlists environment and excludes secrets", () => {
    const childEnv = buildChildEnv({
        PATH: "/usr/bin",
        HOME: "/tmp/home",
        TMPDIR: "/tmp",
        LANG: "en_US.UTF-8",
        LC_ALL: "en_US.UTF-8",
        TEST_API_SECRET: "super-secret",
    });

    assert.equal(childEnv.PATH, "/usr/bin");
    assert.equal(childEnv.HOME, "/tmp/home");
    assert.equal(childEnv.TMPDIR, "/tmp");
    assert.equal(childEnv.LANG, "en_US.UTF-8");
    assert.equal(childEnv.LC_ALL, "en_US.UTF-8");
    assert.equal(childEnv.PYTHONUNBUFFERED, "1");
    assert.equal(childEnv.PYTHONDONTWRITEBYTECODE, "1");
    assert.equal("TEST_API_SECRET" in childEnv, false);
});

test("DashletRuntime serializes concurrent start calls", async () => {
    let spawnCalls = 0;
    const fakeChild = new EventEmitter();
    fakeChild.pid = 42424;
    fakeChild.exitCode = null;
    fakeChild.signalCode = null;
    fakeChild.stdout = new EventEmitter();
    fakeChild.stderr = new EventEmitter();
    fakeChild.kill = () => {
        fakeChild.exitCode = 0;
        fakeChild.emit("exit", 0, null);
    };

    const runtime = new DashletRuntime({
        spawnFn: () => {
            spawnCalls += 1;
            return fakeChild;
        },
    });
    runtime.waitForHealthy = async () => {};

    await Promise.all([runtime.start(), runtime.start()]);
    assert.equal(spawnCalls, 1);

    await runtime.stop();
});

test("DashletRuntime starts configured module target", async () => {
    let spawnCommand = null;
    let spawnArgs = null;
    const fakeChild = new EventEmitter();
    fakeChild.pid = 53535;
    fakeChild.exitCode = null;
    fakeChild.signalCode = null;
    fakeChild.stdout = new EventEmitter();
    fakeChild.stderr = new EventEmitter();
    fakeChild.kill = () => {
        fakeChild.exitCode = 0;
        fakeChild.emit("exit", 0, null);
    };

    const runtime = new DashletRuntime({
        spawnFn: (command, args) => {
            spawnCommand = command;
            spawnArgs = args;
            return fakeChild;
        },
    });
    runtime.waitForHealthy = async () => {};

    await runtime.start({
        moduleTarget: "dashlets.treasury_curve_dashlet:app",
        dashletId: "treasury-curve",
    });
    assert.equal(spawnCommand, "uv");
    assert.equal(spawnArgs[2], "dashlets.treasury_curve_dashlet:app");
    assert.equal(runtime.getState().moduleTarget, "dashlets.treasury_curve_dashlet:app");
    assert.equal(runtime.getState().activeDashletId, "treasury-curve");

    await runtime.stop();
});

test("DashletRuntime restart respawns process and clears old pid", async () => {
    const children = [];
    const runtime = new DashletRuntime({
        spawnFn: () => {
            const child = new EventEmitter();
            child.pid = 60000 + children.length;
            child.exitCode = null;
            child.signalCode = null;
            child.stdout = new EventEmitter();
            child.stderr = new EventEmitter();
            child.kill = () => {
                child.exitCode = 0;
                child.emit("exit", 0, null);
            };
            children.push(child);
            return child;
        },
    });
    runtime.waitForHealthy = async () => {};

    await runtime.start({ moduleTarget: "dashlets.hello_dashlet:app", dashletId: "hello" });
    const firstPid = runtime.getState().pid;
    await runtime.restart({ moduleTarget: "dashlets.treasury_curve_dashlet:app", dashletId: "treasury-curve" });
    const secondPid = runtime.getState().pid;

    assert.notEqual(firstPid, secondPid);
    assert.equal(runtime.getState().moduleTarget, "dashlets.treasury_curve_dashlet:app");
    assert.equal(children.length, 2);
    assert.equal(children[0].exitCode, 0);

    await runtime.stop();
});
