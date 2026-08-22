// TODO(reusable-framework): These schemas are a Milestone 2 compatibility bridge.
// During reusable framework extraction, capability input schemas should be derived
// from the approved OpenAPI operations rather than manually maintained.
//
// Exact parameter names below were read directly from /openapi.json for
// get_treasury_curve, get_treasury_curve_slopes, and compare_treasury_curves
// (FastAPI app in dashlets/treasury_curve_dashlet.py):
//   - get_treasury_curve:        date (optional), data_mode (required enum)
//   - get_treasury_curve_slopes: date (optional), data_mode (required enum)
//   - compare_treasury_curves:   base_date (required), compare_date (required), data_mode (required enum)

const TREASURY_DATA_MODE_SCHEMA = Object.freeze({
    type: "string",
    enum: ["fixture", "eod"],
    description: "Required treasury data mode. Allowed values: fixture, eod.",
});

const TREASURY_OBSERVATION_DATE_SCHEMA = Object.freeze({
    type: "string",
    format: "date",
    description: "Observation date in YYYY-MM-DD format. Omit to use the latest available fixture date.",
});

export const TREASURY_TOOL_PARAMETER_SCHEMAS = Object.freeze({
    get_treasury_curve: Object.freeze({
        type: "object",
        additionalProperties: false,
        required: ["data_mode"],
        properties: Object.freeze({
            date: TREASURY_OBSERVATION_DATE_SCHEMA,
            data_mode: TREASURY_DATA_MODE_SCHEMA,
        }),
    }),
    get_treasury_curve_slopes: Object.freeze({
        type: "object",
        additionalProperties: false,
        required: ["data_mode"],
        properties: Object.freeze({
            date: TREASURY_OBSERVATION_DATE_SCHEMA,
            data_mode: TREASURY_DATA_MODE_SCHEMA,
        }),
    }),
    compare_treasury_curves: Object.freeze({
        type: "object",
        additionalProperties: false,
        required: ["base_date", "compare_date", "data_mode"],
        properties: Object.freeze({
            base_date: Object.freeze({
                type: "string",
                format: "date",
                description: "Required base observation date in YYYY-MM-DD format.",
            }),
            compare_date: Object.freeze({
                type: "string",
                format: "date",
                description: "Required comparison observation date in YYYY-MM-DD format.",
            }),
            data_mode: TREASURY_DATA_MODE_SCHEMA,
        }),
    }),
});

export const DEFAULT_TOOL_PARAMETER_SCHEMA = Object.freeze({
    type: "object",
    additionalProperties: true,
    properties: Object.freeze({}),
});
