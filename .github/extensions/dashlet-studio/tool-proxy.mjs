const AGENT_TOOL_TAG = "agent-tool";
const REQUIRED_SUMMARY_FIELDS = ["title", "message", "generated_at", "source", "data_mode"];

function isObject(value) {
    return value !== null && typeof value === "object" && !Array.isArray(value);
}

function getOperations(openApiDocument) {
    if (!isObject(openApiDocument?.paths)) {
        return [];
    }
    const operations = [];
    for (const [pathName, pathItem] of Object.entries(openApiDocument.paths)) {
        if (!isObject(pathItem)) {
            continue;
        }
        for (const [method, op] of Object.entries(pathItem)) {
            const normalizedMethod = method.toUpperCase();
            if (!["GET", "POST", "PUT", "PATCH", "DELETE"].includes(normalizedMethod)) {
                continue;
            }
            if (!isObject(op) || typeof op.operationId !== "string") {
                continue;
            }
            operations.push({
                operationId: op.operationId,
                method: normalizedMethod,
                pathName,
                operation: op,
            });
        }
    }
    return operations;
}

export function selectApprovedOperations(openApiDocument, allowlist) {
    const approved = new Map();
    const operations = getOperations(openApiDocument);
    for (const item of operations) {
        const tags = Array.isArray(item.operation.tags) ? item.operation.tags : [];
        const allowlisted = allowlist.has(item.operationId);
        if (!allowlisted) {
            continue;
        }
        if (!tags.includes(AGENT_TOOL_TAG)) {
            continue;
        }
        approved.set(item.operationId, item);
    }
    return approved;
}

export function validateToolArgs(operation, args) {
    const parameters = Array.isArray(operation.operation.parameters) ? operation.operation.parameters : [];
    if (parameters.length === 0) {
        if (!isObject(args) || Object.keys(args).length === 0) {
            return;
        }
        throw new Error(`Operation ${operation.operationId} does not accept arguments`);
    }

    if (!isObject(args)) {
        throw new Error(`Operation ${operation.operationId} requires an object argument`);
    }
}

export function validateSummaryResponse(payload) {
    if (!isObject(payload)) {
        throw new Error("Tool response must be a JSON object");
    }
    for (const field of REQUIRED_SUMMARY_FIELDS) {
        if (typeof payload[field] !== "string" || payload[field].length === 0) {
            throw new Error(`Tool response is missing a valid "${field}" string field`);
        }
    }
    return payload;
}

export class ToolProxy {
    constructor({ runtime, allowlist }) {
        this.runtime = runtime;
        this.allowlist = allowlist;
        this.approvedOperations = new Map();
        this.openApiDocument = null;
    }

    clear() {
        this.approvedOperations = new Map();
        this.openApiDocument = null;
    }

    async refresh() {
        const openApi = await this.runtime.fetchOpenApi();
        const approved = selectApprovedOperations(openApi, this.allowlist);
        this.openApiDocument = openApi;
        this.approvedOperations = approved;
        return {
            approvedOperationIds: [...approved.keys()],
            openApiTitle: openApi?.info?.title ?? null,
        };
    }

    listApprovedOperations() {
        return [...this.approvedOperations.values()].map((item) => ({
            operationId: item.operationId,
            method: item.method,
            pathName: item.pathName,
        }));
    }

    async invoke(operationId, args = {}) {
        const operation = this.approvedOperations.get(operationId);
        if (!operation) {
            throw new Error(`Operation "${operationId}" is not approved`);
        }
        validateToolArgs(operation, args);
        const response = await this.runtime.request(operation.pathName, {
            method: operation.method,
        });
        if (operationId === "get_dashlet_summary") {
            // TODO(reusable-framework): replace this per-operation check with generic OpenAPI response validation.
            return validateSummaryResponse(response);
        }
        return response;
    }
}

export { AGENT_TOOL_TAG };
