from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from treasury_fixture import (
    CurveComparisonPoint,
    CurveSlope,
    Provenance,
    TreasuryCurveResponse,
    compare_curves,
    compute_curve_slopes,
    load_fixture,
    to_curve_response,
)
from dashlets.treasury_provider import ProviderError

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "treasury"
DATE_EXAMPLES = ["2026-08-19"]
CANONICAL_SLOPE_NAMES = ["2s10s", "3m10y", "5s30s"]

OBSERVATION_DATE_DESCRIPTION = (
    "Observation date in YYYY-MM-DD format. Omit to use the latest available fixture date."
)
BASE_DATE_DESCRIPTION = "Required base observation date in YYYY-MM-DD format."
COMPARE_DATE_DESCRIPTION = "Required comparison observation date in YYYY-MM-DD format."


class TreasuryCurveSlopesResponse(BaseModel):
    observation_date: date
    slopes: list[CurveSlope]
    provenance: Provenance


class TreasuryCurveComparisonResponse(BaseModel):
    base_observation_date: date
    compare_observation_date: date
    points: list[CurveComparisonPoint]
    provenance: Provenance


class TreasuryCurveViewResponse(BaseModel):
    observation_date: date
    curve: TreasuryCurveResponse
    slopes: list[CurveSlope]


class TreasuryFixtureDatesResponse(BaseModel):
    available_dates: list[str]


class TreasuryDashletMetadataResponse(BaseModel):
    title: str
    version: str
    data_mode: str
    default_curve_date: str
    canonical_slopes: list[str]
    supported_endpoints: list[str]
    available_fixture_dates: list[str]


class DashletErrorDetail(BaseModel):
    error_code: str
    message: str


class DashletErrorResponse(BaseModel):
    detail: DashletErrorDetail


app = FastAPI(title="Treasury Curve Dashlet", version="0.1.0")


def _optional_date_query(description: str):
    return Query(
        default=None,
        description=description,
        examples=DATE_EXAMPLES,
    )


def _required_date_query(description: str):
    return Query(
        ...,
        description=description,
        examples=DATE_EXAMPLES,
    )


def _fixture_path_for_date(observation_date: str) -> Path:
    return FIXTURE_DIR / f"curve_{observation_date}.json"


def _parse_date(observation_date: str) -> date:
    try:
        return datetime.strptime(observation_date, "%Y-%m-%d").replace(tzinfo=UTC).date()
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "invalid_date",
                "message": f"Invalid date: {observation_date}. Expected YYYY-MM-DD",
            },
        ) from exc


def _list_available_fixture_dates() -> list[str]:
    dates: list[str] = []
    for fixture_path in FIXTURE_DIR.glob("curve_*.json"):
        date_str = fixture_path.stem.removeprefix("curve_")
        _parse_date(date_str)
        dates.append(date_str)
    return sorted(set(dates))


def _latest_available_date_str() -> str:
    available = _list_available_fixture_dates()
    if not available:
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "no_fixtures_available",
                "message": "No Treasury fixtures are available.",
            },
        )
    return max(available)


def _resolve_observation_date_str(observation_date: str | None) -> str:
    if observation_date is not None:
        return observation_date
    return _latest_available_date_str()


def _load_fixture_for_date(observation_date: str):
    _parse_date(observation_date)
    fixture_path = _fixture_path_for_date(observation_date)
    if not fixture_path.exists():
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "fixture_not_found",
                "message": f"No fixture found for date: {observation_date}",
            },
        )
    return load_fixture(fixture_path)


def _curve_response_with_freshness(fixture) -> TreasuryCurveResponse:
    latest = _latest_available_date_str()
    is_stale = fixture.observation_date.isoformat() != latest
    return to_curve_response(fixture, is_stale=is_stale)


def _compute_slopes_or_422(points) -> list[CurveSlope]:
    try:
        return compute_curve_slopes(points)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "missing_slope_maturity", "message": str(exc)},
        ) from exc


def _compare_curves_or_422(base_points, compare_points):
    try:
        return compare_curves(base_points, compare_points)
    except ValueError as exc:
        raise HTTPException(
            status_code=422,
            detail={"error_code": "maturity_mismatch", "message": str(exc)},
        ) from exc


_PROVIDER_STATUS_MAP: dict[str, int] = {
    "fixture_not_found":  404,
    "date_not_in_feed":   404,
    "invalid_date":       422,
    "feed_parse_error":   502,
    "feed_date_error":    502,
    "feed_http_error":    502,
    "feed_timeout":       504,
    "feed_network_error": 502,
}


def _provider_error_to_http(exc: ProviderError) -> HTTPException:
    status_code = _PROVIDER_STATUS_MAP.get(exc.error_code, 502)
    raise HTTPException(
        status_code=status_code,
        detail={"error_code": exc.error_code, "message": exc.message},
    )


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Treasury Curve Dashlet</title>

  <!-- Pinned CDN versions -->
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4.0.6"></script>
</head>
<body class="bg-slate-50 text-slate-900 min-h-screen">
  <main class="max-w-7xl mx-auto px-4 py-6 space-y-6" x-data="treasuryApp">
    <header class="flex items-center justify-between gap-4">
      <h1 class="text-2xl font-semibold">Treasury Curve Monitor</h1>
      <p class="text-sm text-slate-600">
        Status:
        <span class="font-medium" x-text="statusText">Idle</span>
      </p>
    </header>

    <section class="bg-white rounded-lg border border-slate-200 p-4">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
        <label class="block">
          <span class="text-sm text-slate-700">Observation Date</span>
          <select class="mt-1 w-full rounded-md border-slate-300" x-model="selectedDate">
            <option value="">Select date</option>
            <template x-for="d in availableDates" :key="'obs-' + d">
              <option :value="d" x-text="d"></option>
            </template>
          </select>
        </label>

        <label class="block">
          <span class="text-sm text-slate-700">Comparison Date</span>
          <select class="mt-1 w-full rounded-md border-slate-300" x-model="compareDate">
            <option value="">Select date</option>
            <template x-for="d in availableDates" :key="'cmp-' + d">
              <option :value="d" x-text="d"></option>
            </template>
          </select>
        </label>

        <button
          type="button"
          class="rounded-md bg-slate-900 text-white px-4 py-2"
          :disabled="isLoadingCurve || isLoadingComparison"
          :class="(isLoadingCurve || isLoadingComparison) ? 'opacity-60 cursor-not-allowed' : ''"
          @click="loadCurve">
          Load
        </button>

        <button
          type="button"
          class="rounded-md bg-slate-700 text-white px-4 py-2"
          :disabled="isLoadingCurve || isLoadingComparison"
          :class="(isLoadingCurve || isLoadingComparison) ? 'opacity-60 cursor-not-allowed' : ''"
          @click="loadComparison">
          Compare
        </button>
      </div>
    </section>

    <section class="bg-white rounded-lg border border-slate-200 p-4">
      <h2 class="text-lg font-medium mb-3">Treasury Curve</h2>
      <div id="curve-chart" class="w-full h-[420px]" aria-label="Treasury curve chart"></div>
    </section>

    <section class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <article class="bg-white rounded-lg border border-slate-200 p-4">
        <h3 class="text-sm text-slate-600">2s10s</h3>
        <p class="text-2xl font-semibold" x-text="slope2s10sText">--</p>
      </article>

      <article class="bg-white rounded-lg border border-slate-200 p-4">
        <h3 class="text-sm text-slate-600">3m10y</h3>
        <p class="text-2xl font-semibold" x-text="slope3m10yText">--</p>
      </article>
    </section>

    <section class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <article class="bg-white rounded-lg border border-slate-200 p-4">
        <h3 class="text-lg font-medium mb-3">Maturity / Yield</h3>
        <table class="min-w-full text-sm">
          <thead>
            <tr class="text-left border-b border-slate-200">
              <th class="py-2">Maturity</th>
              <th class="py-2">Yield (%)</th>
            </tr>
          </thead>
          <tbody>
            <template x-if="curvePoints.length === 0">
                <tr>
                <td class="py-2 text-slate-500" colspan="2">No data loaded.</td>
                </tr>
            </template>
            <template x-for="point in curvePoints" :key="point.maturity_label">
                <tr class="border-b border-slate-100">
                <td class="py-2" x-text="point.maturity_label"></td>
                <td class="py-2" x-text="point.yield_percent"></td>
                </tr>
            </template>
          </tbody>
        </table>
      </article>

      <article class="bg-white rounded-lg border border-slate-200 p-4">
        <h3 class="text-lg font-medium mb-3">Changes vs Observation Date (bps)</h3>
        <table class="min-w-full text-sm">
          <thead>
            <tr class="text-left border-b border-slate-200">
              <th class="py-2">Maturity</th>
              <th class="py-2">Change (bps)</th>
            </tr>
          </thead>
          <tbody>
            <template x-if="comparisonPoints.length === 0">
              <tr>
                <td class="py-2 text-slate-500" colspan="2">No comparison loaded.</td>
              </tr>
            </template>
            <template x-for="row in comparisonPoints" :key="row.maturity_label">
              <tr class="border-b border-slate-100">
                <td class="py-2" x-text="row.maturity_label"></td>
                <td class="py-2" x-text="formatBps(row.delta_bps)"></td>
              </tr>
            </template>
          </tbody>
        </table>
      </article>
    </section>

    <section class="bg-amber-50 border border-amber-200 rounded-lg p-3" x-show="isLoadingCurve || isLoadingComparison">
      <p class="text-sm text-amber-800" x-text="loadingText">Loading Treasury data...</p>
    </section>

    <section class="bg-rose-50 border border-rose-200 rounded-lg p-3" x-show="errorMessage">
      <p class="text-sm text-rose-700" x-text="errorMessage"></p>
    </section>

    <footer class="text-xs text-slate-500 border-t border-slate-200 pt-3">
      <p x-text="provenanceText">Provenance: not loaded</p>
    </footer>
  </main>
  <script>
    document.addEventListener("alpine:init", () => {
      Alpine.data("treasuryApp", () => ({
        statusText: "Booting",
        loadingText: "Loading Treasury data...",
        isLoadingCurve: false,
        isLoadingComparison: false,
        errorMessage: "",
        availableDates: [],
        selectedDate: "",
        compareDate: "",
        curvePoints: [],
        comparisonPoints: [],
        slopesByName: {},
        slope2s10sText: "--",
        slope3m10yText: "--",
        provenanceText: "Provenance: not loaded",
        lastCurveDate: "",
        lastComparisonBaseDate: "",
        lastComparisonDate: "",

        async init() {
          this.statusText = "Initializing";
          await this.loadAvailableDates();
          await this.loadCurve();
        },

        async parseErrorMessage(response, fallbackMessage) {
          try {
            const payload = await response.json();
            const detail = payload && payload.detail;
            if (detail && typeof detail.message === "string" && detail.message.length > 0) {
              return detail.message;
            }
          } catch (_) {
            // Ignore parsing errors and use the fallback below.
          }
          return `${fallbackMessage}: ${response.status}`;
        },

        applyCurveProvenance(provenance) {
          if (!provenance) {
            this.provenanceText = "Provenance: unavailable";
            return;
          }

          const retrievedAt = provenance.retrieved_at || "unknown";
          const staleLabel = provenance.is_stale ? "yes" : "no";
          const curveDate = this.lastCurveDate || provenance.observation_date || "n/a";

          this.provenanceText =
            `Provenance: source=${provenance.source}, mode=${provenance.data_mode}, curve_date=${curveDate}, stale=${staleLabel}, retrieved_at=${retrievedAt}`;
        },

        applyComparisonProvenance(provenance) {
          if (!provenance) {
            return;
          }

          const retrievedAt = provenance.retrieved_at || "unknown";
          const staleLabel = provenance.is_stale ? "yes" : "no";
          const baseDate = this.lastComparisonBaseDate || "n/a";
          const compareDate = this.lastComparisonDate || "n/a";

          this.provenanceText =
            `Provenance: source=${provenance.source}, mode=${provenance.data_mode}, curve_date=${this.lastCurveDate || provenance.observation_date || "n/a"}, compare_base=${baseDate}, compare_date=${compareDate}, stale=${staleLabel}, retrieved_at=${retrievedAt}`;
        },

        async loadAvailableDates() {
          this.errorMessage = "";
          try {
            const response = await fetch("./api/treasury/fixture-dates");
            if (!response.ok) {
              throw new Error(await this.parseErrorMessage(response, "Failed to load fixture dates"));
            }

            const payload = await response.json();
            this.availableDates = Array.isArray(payload.available_dates) ? payload.available_dates : [];

            if (!this.selectedDate && this.availableDates.length > 0) {
              this.selectedDate = this.availableDates[this.availableDates.length - 1];
            }
            if (!this.compareDate && this.availableDates.length > 1) {
              this.compareDate = this.availableDates[this.availableDates.length - 2];
            }
          } catch (err) {
            this.errorMessage = String(err);
            this.statusText = "Error";
          }
        },

        renderCurveChart() {
          const x = this.curvePoints.map((p) => p.maturity_label);
          const y = this.curvePoints.map((p) => p.yield_percent);

          const trace = {
            x,
            y,
            type: "scatter",
            mode: "lines+markers",
            name: "Treasury Curve",
            line: { width: 3 },
            marker: { size: 7 },
          };

          const layout = {
            title: this.selectedDate ? `Treasury Curve (${this.selectedDate})` : "Treasury Curve",
            margin: { t: 48, r: 24, b: 48, l: 56 },
            xaxis: { title: "Maturity" },
            yaxis: { title: "Yield (%)" },
            showlegend: false,
          };

          const config = {
            displaylogo: false,
            responsive: true,
          };

          Plotly.react("curve-chart", [trace], layout, config);
        },

        applySlopeCards() {
          const s2s10s = this.slopesByName["2s10s"];
          const s3m10y = this.slopesByName["3m10y"];

          this.slope2s10sText =
            s2s10s && typeof s2s10s.slope_bps === "number" ? `${s2s10s.slope_bps.toFixed(1)} bps` : "--";

          this.slope3m10yText =
            s3m10y && typeof s3m10y.slope_bps === "number" ? `${s3m10y.slope_bps.toFixed(1)} bps` : "--";
        },

        async loadSlopes() {
          const query = this.selectedDate ? `?date=${encodeURIComponent(this.selectedDate)}` : "";
          const response = await fetch(`./api/treasury/slopes${query}`);
          if (!response.ok) {
            throw new Error(await this.parseErrorMessage(response, "Failed to load slopes"));
          }

          const payload = await response.json();
          const slopes = Array.isArray(payload.slopes) ? payload.slopes : [];
          this.slopesByName = Object.fromEntries(slopes.map((s) => [s.name, s]));
          this.applySlopeCards();
        },

        async loadCurve() {
          if (this.isLoadingCurve || this.isLoadingComparison) {
            return;
          }

          this.isLoadingCurve = true;
          this.loadingText = "Loading curve and slopes...";
          this.errorMessage = "";
          this.statusText = "Loading curve";
          this.slopesByName = {};
          this.slope2s10sText = "--";
          this.slope3m10yText = "--";

          try {
            const query = this.selectedDate ? `?date=${encodeURIComponent(this.selectedDate)}` : "";
            const response = await fetch(`./api/treasury/curve${query}`);
            if (!response.ok) {
              throw new Error(await this.parseErrorMessage(response, "Failed to load curve"));
            }

            const payload = await response.json();
            this.curvePoints = Array.isArray(payload.points) ? payload.points : [];
            this.lastCurveDate = payload.provenance?.observation_date || this.selectedDate || "";
            this.renderCurveChart();
            await this.loadSlopes();
            this.applyCurveProvenance(payload.provenance);

            this.statusText = "Curve loaded";
          } catch (err) {
            this.errorMessage = String(err);
            this.statusText = "Error";
          } finally {
            this.isLoadingCurve = false;
          }
        },

        formatBps(value) {
          if (typeof value !== "number" || Number.isNaN(value)) {
            return "--";
          }
          const sign = value > 0 ? "+" : "";
          return `${sign}${value.toFixed(1)} bps`;
        },

        async loadComparison() {
          if (this.isLoadingCurve || this.isLoadingComparison) {
            return;
          }

          this.errorMessage = "";
          if (!this.selectedDate || !this.compareDate) {
            this.errorMessage = "Select both observation and comparison dates.";
            this.statusText = "Error";
            return;
          }

          this.isLoadingComparison = true;
          this.loadingText = "Loading comparison deltas...";
          this.statusText = "Loading comparison";
          this.comparisonPoints = [];

          try {
            const query = `?base_date=${encodeURIComponent(this.selectedDate)}&compare_date=${encodeURIComponent(this.compareDate)}`;
            const response = await fetch(`./api/treasury/compare${query}`);
            if (!response.ok) {
              throw new Error(await this.parseErrorMessage(response, "Failed to load comparison"));
            }

            const payload = await response.json();
            this.comparisonPoints = Array.isArray(payload.points) ? payload.points : [];
            this.lastComparisonBaseDate = payload.base_observation_date || this.selectedDate || "";
            this.lastComparisonDate = payload.compare_observation_date || this.compareDate || "";
            this.applyComparisonProvenance(payload.provenance);
            this.statusText = "Comparison loaded";
          } catch (err) {
            this.errorMessage = String(err);
            this.statusText = "Error";
          } finally {
            this.isLoadingComparison = false;
          }
        },
      }));
    });
  </script>
</body>
</html>
"""


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ready"}


@app.get(
    "/metadata",
    operation_id="get_treasury_dashlet_metadata",
    summary="Get Treasury Dashlet Metadata",
    description="Return deterministic metadata describing data mode, supported routes, canonical slopes, and available fixture dates.",
    response_description="Typed Treasury dashlet metadata.",
    response_model=TreasuryDashletMetadataResponse,
)
def metadata() -> TreasuryDashletMetadataResponse:
    return TreasuryDashletMetadataResponse(
        title=app.title,
        version=app.version,
        data_mode="fixture",
        default_curve_date=_latest_available_date_str(),
        canonical_slopes=CANONICAL_SLOPE_NAMES,
        supported_endpoints=[
            "/api/treasury/fixture-dates",
            "/api/treasury/view",
            "/api/treasury/curve",
            "/api/treasury/slopes",
            "/api/treasury/compare",
        ],
        available_fixture_dates=_list_available_fixture_dates(),
    )


@app.get(
    "/api/treasury/fixture-dates",
    operation_id="list_treasury_fixture_dates",
    summary="List Treasury Fixture Dates",
    description="List available deterministic Treasury fixture observation dates for discovery and UI selection.",
    response_description="Sorted list of available fixture dates.",
    response_model=TreasuryFixtureDatesResponse,
)
def list_treasury_fixture_dates() -> TreasuryFixtureDatesResponse:
    return TreasuryFixtureDatesResponse(available_dates=_list_available_fixture_dates())


@app.get(
    "/api/treasury/view",
    operation_id="get_treasury_curve_view",
    summary="Get Treasury Curve View",
    description="Return deterministic curve points and canonical slopes together for one observation date.",
    response_description="Typed Treasury curve, canonical slopes, and shared provenance.",
    responses={
        404: {"model": DashletErrorResponse, "description": "Fixture not found for the requested date."},
        422: {"model": DashletErrorResponse, "description": "Invalid date format."},
    },
    response_model=TreasuryCurveViewResponse,
)
def get_treasury_curve_view(
    date: str | None = _optional_date_query(description=OBSERVATION_DATE_DESCRIPTION),
) -> TreasuryCurveViewResponse:
    resolved_date = _resolve_observation_date_str(date)
    fixture = _load_fixture_for_date(resolved_date)
    curve_response = _curve_response_with_freshness(fixture)
    slopes = _compute_slopes_or_422(curve_response.points)
    return TreasuryCurveViewResponse(
        observation_date=fixture.observation_date,
        curve=curve_response,
        slopes=slopes,
    )


@app.get(
    "/api/treasury/curve",
    operation_id="get_treasury_curve",
    tags=["agent-tool"],
    summary="Get Treasury Curve",
    description="Return a deterministic fixture-backed Treasury curve for a single observation date.",
    response_description="Typed Treasury curve points and provenance.",
    responses={
        404: {"model": DashletErrorResponse, "description": "Fixture not found for the requested date."},
        422: {"model": DashletErrorResponse, "description": "Invalid date format."},
    },
    response_model=TreasuryCurveResponse,
)
def get_treasury_curve(
    date: str | None = _optional_date_query(description=OBSERVATION_DATE_DESCRIPTION),
) -> TreasuryCurveResponse:
    resolved_date = _resolve_observation_date_str(date)
    fixture = _load_fixture_for_date(resolved_date)
    return _curve_response_with_freshness(fixture)


@app.get(
    "/api/treasury/slopes",
    operation_id="get_treasury_curve_slopes",
    tags=["agent-tool"],
    summary="Get Canonical Curve Slopes",
    description="Return deterministic canonical slope pairs (2s10s, 3m10y and 5s30s) for one observation date.",
    response_description="Canonical slope metrics with provenance.",
    responses={
        404: {"model": DashletErrorResponse, "description": "Fixture not found for the requested date."},
        422: {
            "model": DashletErrorResponse,
            "description": "Invalid date format or a required slope maturity is missing from the fixture.",
        },
    },
    response_model=TreasuryCurveSlopesResponse,
)
def get_curve_slopes(
    date: str | None = _optional_date_query(description=OBSERVATION_DATE_DESCRIPTION),
) -> TreasuryCurveSlopesResponse:
    resolved_date = _resolve_observation_date_str(date)
    fixture = _load_fixture_for_date(resolved_date)
    curve_response = _curve_response_with_freshness(fixture)
    slopes = _compute_slopes_or_422(curve_response.points)
    return TreasuryCurveSlopesResponse(
        observation_date=fixture.observation_date,
        slopes=slopes,
        provenance=curve_response.provenance,
    )


@app.get(
    "/api/treasury/compare",
    operation_id="compare_treasury_curves",
    tags=["agent-tool"],
    summary="Compare Treasury Curves",
    description="Compare two deterministic fixture-backed Treasury curves and return maturity-level basis-point deltas.",
    response_description="Per-maturity curve comparison points with provenance.",
    responses={
        404: {"model": DashletErrorResponse, "description": "Fixture not found for at least one requested date."},
        422: {
            "model": DashletErrorResponse,
            "description": "Invalid date format or the two curves do not share the same maturities.",
        },
    },
    response_model=TreasuryCurveComparisonResponse,
)
def compare_treasury_curves(
    base_date: str = _required_date_query(description=BASE_DATE_DESCRIPTION),
    compare_date: str = _required_date_query(description=COMPARE_DATE_DESCRIPTION),
) -> TreasuryCurveComparisonResponse:
    base_fixture = _load_fixture_for_date(base_date)
    compare_fixture = _load_fixture_for_date(compare_date)

    base_curve = _curve_response_with_freshness(base_fixture)
    compare_curve = _curve_response_with_freshness(compare_fixture)
    comparison_points = _compare_curves_or_422(base_curve.points, compare_curve.points)
    latest_date = _latest_available_date_str()
    is_stale = (
      base_fixture.observation_date.isoformat() != latest_date
      or compare_fixture.observation_date.isoformat() != latest_date
    )

    return TreasuryCurveComparisonResponse(
        base_observation_date=base_fixture.observation_date,
        compare_observation_date=compare_fixture.observation_date,
        points=comparison_points,
        provenance=Provenance(
            source="synthetic-fixture",
            data_mode=base_fixture.fixture_meta.data_mode,
            observation_date=base_fixture.observation_date,
            retrieved_at=datetime.now(UTC),
            is_stale=is_stale,
        ),
    )