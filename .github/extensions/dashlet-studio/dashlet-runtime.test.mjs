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
