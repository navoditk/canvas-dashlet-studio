# Web Authoring Patterns

How to write a dashlet's embedded HTML/JS page. See `dashlets/treasury_curve_dashlet.py`'s `index()` for the full reference implementation.

## 1. No build step, by design

`AGENTS.md` §7 prohibits React, TypeScript, a bundler, or any frontend framework. Every dashlet's UI is one `HTMLResponse` string returned from `GET /`, using three pinned CDN scripts:

```html
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4.0.6"></script>
```

Pin exact versions (as above), so a dashlet's behavior doesn't silently change when a CDN-hosted "latest" tag moves. If you need a newer version, bump it deliberately and re-verify.

## 2. Alpine.js component pattern

One `x-data` component per page, registered on `alpine:init`:

```html
<main x-data="treasuryApp">
<script>
document.addEventListener("alpine:init", () => {
  Alpine.data("treasuryApp", () => ({
    // state
    isLoadingCurve: false,
    errorMessage: "",
    curvePoints: [],

    // lifecycle
    async init() { /* initial load */ },

    // actions
    async loadCurve() { /* fetch, render, handle errors */ },
  }));
});
</script>
```

Keep state flat and explicit (`isLoadingCurve`, `errorMessage`, not a generic `state` blob) — it makes the required loading/empty/error states (§4) straightforward to wire into `x-show`.

## 3. Mount-relative fetch paths — mandatory

```js
const response = await fetch("./api/treasury/curve" + query);
```

Never `fetch("/api/...")` (absolute) or a hardcoded host. The same dashlet file must work both standalone (served at `/`) and mounted under a gallery path (`/apps/<id>/`) without any code change — only a relative path survives that remounting. This is checked by `test_root_page_uses_mount_relative_api_fetch_paths` in `tests/test_treasury_curve_dashlet.py`; write the equivalent test for every new dashlet.

## 4. Required UI states

Every dashlet's page must visibly handle:

- **Loading** — a visible indicator while a request is in flight (`x-show="isLoading..."`), with buttons disabled during the request (`:disabled="isLoading..."`) so a user can't fire overlapping requests.
- **Empty** — what renders before any data has loaded, or when a response legitimately has zero rows ("No data loaded." table row, not a blank table).
- **Error** — the actual error message from the response, not a generic "something went wrong." See `parseErrorMessage` in `treasury_curve_dashlet.py`'s inline script: it reads `detail.message` from the dashlet's own error shape (`docs/DASHLET_CONTRACT.md` §4) before falling back to a generic message.

## 5. Provenance in the UI

Every data view shows its provenance, not just the data — source, data mode (if applicable), observation date, staleness, and retrieval time. See the `provenanceText` computed string in Treasury's Alpine component. A user should never be unable to tell whether they're looking at fixture data, live data, or stale data.

## 6. Charts

Use `Plotly.react(elementId, [trace], layout, config)`, not `Plotly.newPlot` — `react` diffs against the existing plot and avoids a full re-render/flicker on every data refresh. Set `displaylogo: false` and `responsive: true` in `config` for every chart.

## 7. Guarding against out-of-order responses

If a control (like Treasury's Data Mode selector) can trigger overlapping requests — a user changes it again before the first request resolves — guard against the stale response winning. Treasury's pattern is a monotonically increasing token (`dataModeToken`) checked after each `await`; a response only gets applied if its token still matches the latest request. See `onDataModeChange`/`applyDataModeChange` in `treasury_curve_dashlet.py` for the full implementation and the comments explaining why each check exists.

## 8. Styling

Tailwind utility classes only; no custom stylesheet per dashlet beyond what's already inline. Keep visual patterns (card borders, spacing, status colors) consistent with the existing dashlets rather than inventing new ones — a PM switching between monitors should not perceive a different design language per app.
