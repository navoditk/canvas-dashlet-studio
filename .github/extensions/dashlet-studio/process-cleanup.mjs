const HANDLERS_INSTALLED = Symbol.for("dashlet-studio.cleanup.handlers");
const CLEANUP_TIMEOUT_MS = 2_000;

function delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

async function withTimeout(promise, timeoutMs) {
    return Promise.race([promise, delay(timeoutMs)]);
}

async function closeCanvasServers(canvasServers) {
    const closes = [];
    for (const [, entry] of canvasServers) {
        closes.push(
            new Promise((resolve) => {
                entry.server.close(() => resolve());
            }),
        );
    }
    canvasServers.clear();
    await Promise.allSettled(closes);
}

export function createCleanupTask({ runtime, proxy, canvasServers }) {
    let cleanupPromise = null;
    return async function cleanupOnce() {
        if (cleanupPromise) {
            return cleanupPromise;
        }
        cleanupPromise = (async () => {
            await closeCanvasServers(canvasServers);
            await runtime.dispose();
            proxy.clear();
        })();
        return cleanupPromise;
    };
}

export function installProcessCleanupHandlers({
    runtime,
    proxy,
    canvasServers,
    processRef = process,
    cleanupTimeoutMs = CLEANUP_TIMEOUT_MS,
}) {
    if (processRef[HANDLERS_INSTALLED]) {
        return processRef[HANDLERS_INSTALLED];
    }

    const cleanupOnce = createCleanupTask({ runtime, proxy, canvasServers });

    const exitAfterCleanup = (code) => {
        withTimeout(cleanupOnce(), cleanupTimeoutMs).finally(() => {
            processRef.exit(code);
        });
    };

    const onSigterm = () => exitAfterCleanup(0);
    const onSigint = () => exitAfterCleanup(0);
    const onUncaughtException = () => exitAfterCleanup(1);
    const onUnhandledRejection = () => exitAfterCleanup(1);

    processRef.on("SIGTERM", onSigterm);
    processRef.on("SIGINT", onSigint);
    processRef.on("uncaughtException", onUncaughtException);
    processRef.on("unhandledRejection", onUnhandledRejection);

    const installed = {
        cleanupOnce,
        handlers: {
            onSigterm,
            onSigint,
            onUncaughtException,
            onUnhandledRejection,
        },
    };
    processRef[HANDLERS_INSTALLED] = installed;
    return installed;
}
