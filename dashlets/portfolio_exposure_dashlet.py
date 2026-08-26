from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

from fastapi import HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from dashlet_framework import AGENT_TOOL_TAG, DashletErrorResponse, Provenance
from dashlet_framework.app import create_dashlet_app
from dashlets.portfolio_provider import FixturePortfolioProvider, ProviderError
from portfolio_fixture import IssuerExposure, PortfolioTotals, SectorExposure

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "portfolio"
DATE_EXAMPLES = ["2026-08-19"]

OBSERVATION_DATE_DESCRIPTION = (
    "Observation date in YYYY-MM-DD format. Omit to use the latest available fixture date."
)
BASE_DATE_DESCRIPTION = "Required base observation date in YYYY-MM-DD format."
COMPARE_DATE_DESCRIPTION = "Required comparison observation date in YYYY-MM-DD format."

_provider = FixturePortfolioProvider(FIXTURE_DIR)


class PortfolioExposuresResponse(BaseModel):
    observation_date: date
    totals: PortfolioTotals
    sector_exposures: list[SectorExposure]
    issuer_exposures: list[IssuerExposure]
    provenance: Provenance


class PortfolioConcentrationResponse(BaseModel):
    observation_date: date
    top_issuer_exposures: list[IssuerExposure]
    top_sector_exposures: list[SectorExposure]
    provenance: Provenance


class SectorExposureDelta(BaseModel):
    sector: str
    base_net_market_value: float
    compare_net_market_value: float
    delta_market_value: float
    delta_weight_pct: float


class PortfolioComparisonResponse(BaseModel):
    base_observation_date: date
    compare_observation_date: date
    sector_deltas: list[SectorExposureDelta]
    provenance: Provenance


class PortfolioFixtureDatesResponse(BaseModel):
    available_dates: list[str]


class PortfolioDashletMetadataResponse(BaseModel):
    title: str
    version: str
    data_mode: str
    default_observation_date: str
    supported_endpoints: list[str]
    available_fixture_dates: list[str]


app = create_dashlet_app(title="Portfolio Exposure Dashlet", version="0.1.0")


def _optional_date_query(description: str):
    return Query(default=None, description=description, examples=DATE_EXAMPLES)


def _required_date_query(description: str):
    return Query(..., description=description, examples=DATE_EXAMPLES)


def _latest_available_date_str() -> str:
    available = _provider.list_available_dates()
    if not available:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "no_fixtures_available", "message": "No portfolio fixtures are available."},
        )
    return max(available)


def _resolve_observation_date_str(observation_date: str | None) -> str:
    if observation_date is not None:
        return observation_date
    return _latest_available_date_str()


_PROVIDER_STATUS_MAP: dict[str, int] = {
    "fixture_not_found": 404,
    "invalid_fixture": 502,
}


def _provider_error_to_http(exc: ProviderError) -> HTTPException:
    status_code = _PROVIDER_STATUS_MAP.get(exc.error_code, 502)
    raise HTTPException(status_code=status_code, detail={"error_code": exc.error_code, "message": exc.message})


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Portfolio Exposure Dashlet</title>

  <!-- Pinned CDN versions -->
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4.0.6"></script>
</head>
<body class="bg-slate-50 text-slate-900 min-h-screen">
  <main class="max-w-7xl mx-auto px-4 py-6 space-y-6" x-data="portfolioApp">
    <header class="flex items-center justify-between gap-4">
      <h1 class="text-2xl font-semibold">Portfolio Exposure &amp; Concentration Monitor</h1>
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
          :disabled="isLoadingExposures || isLoadingComparison"
          :class="(isLoadingExposures || isLoadingComparison) ? 'opacity-60 cursor-not-allowed' : ''"
          @click="loadExposures">
          Load
        </button>

        <button
          type="button"
          class="rounded-md bg-slate-700 text-white px-4 py-2"
          :disabled="isLoadingExposures || isLoadingComparison"
          :class="(isLoadingExposures || isLoadingComparison) ? 'opacity-60 cursor-not-allowed' : ''"
          @click="loadComparison">
          Compare
        </button>
      </div>
    </section>

    <section class="bg-white rounded-lg border border-slate-200 p-4">
      <h2 class="text-lg font-medium mb-3">Net Exposure by Sector</h2>
      <div id="sector-chart" class="w-full h-[360px]" aria-label="Sector net exposure chart"></div>
    </section>

    <section class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <article class="bg-white rounded-lg border border-slate-200 p-4">
        <h3 class="text-sm text-slate-600">Long Market Value</h3>
        <p class="text-2xl font-semibold" x-text="longText">--</p>
      </article>

      <article class="bg-white rounded-lg border border-slate-200 p-4">
        <h3 class="text-sm text-slate-600">Short Market Value</h3>
        <p class="text-2xl font-semibold" x-text="shortText">--</p>
      </article>

      <article class="bg-white rounded-lg border border-slate-200 p-4">
        <h3 class="text-sm text-slate-600">Net Market Value</h3>
        <p class="text-2xl font-semibold" x-text="netText">--</p>
      </article>
    </section>

    <section class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <article class="bg-white rounded-lg border border-slate-200 p-4">
        <h3 class="text-lg font-medium mb-3">Top Issuer Concentrations</h3>
        <table class="min-w-full text-sm">
          <thead>
            <tr class="text-left border-b border-slate-200">
              <th class="py-2">Issuer</th>
              <th class="py-2">Sector</th>
              <th class="py-2">Net Weight</th>
            </tr>
          </thead>
          <tbody>
            <template x-if="topIssuers.length === 0">
              <tr>
                <td class="py-2 text-slate-500" colspan="3">No data loaded.</td>
              </tr>
            </template>
            <template x-for="row in topIssuers" :key="row.issuer">
              <tr class="border-b border-slate-100">
                <td class="py-2" x-text="row.issuer"></td>
                <td class="py-2" x-text="row.sector"></td>
                <td class="py-2" x-text="formatPct(row.net_weight_pct)"></td>
              </tr>
            </template>
          </tbody>
        </table>
      </article>

      <article class="bg-white rounded-lg border border-slate-200 p-4">
        <h3 class="text-lg font-medium mb-3">Sector Exposure Change (vs Comparison Date)</h3>
        <table class="min-w-full text-sm">
          <thead>
            <tr class="text-left border-b border-slate-200">
              <th class="py-2">Sector</th>
              <th class="py-2">Change (weight pts)</th>
            </tr>
          </thead>
          <tbody>
            <template x-if="sectorDeltas.length === 0">
              <tr>
                <td class="py-2 text-slate-500" colspan="2">No comparison loaded.</td>
              </tr>
            </template>
            <template x-for="row in sectorDeltas" :key="row.sector">
              <tr class="border-b border-slate-100">
                <td class="py-2" x-text="row.sector"></td>
                <td class="py-2" x-text="formatPct(row.delta_weight_pct)"></td>
              </tr>
            </template>
          </tbody>
        </table>
      </article>
    </section>

    <section class="bg-amber-50 border border-amber-200 rounded-lg p-3" x-show="isLoadingExposures || isLoadingComparison">
      <p class="text-sm text-amber-800" x-text="loadingText">Loading portfolio data...</p>
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
      Alpine.data("portfolioApp", () => ({
        statusText: "Booting",
        loadingText: "Loading portfolio data...",
        isLoadingExposures: false,
        isLoadingComparison: false,
        errorMessage: "",
        availableDates: [],
        selectedDate: "",
        compareDate: "",
        sectorExposures: [],
        topIssuers: [],
        sectorDeltas: [],
        longText: "--",
        shortText: "--",
        netText: "--",
        provenanceText: "Provenance: not loaded",
        lastObservationDate: "",

        async init() {
          this.statusText = "Initializing";
          await this.loadAvailableDates();
          await this.loadExposures();
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

        formatMoney(value) {
          if (typeof value !== "number" || Number.isNaN(value)) {
            return "--";
          }
          return "$" + Math.round(value).toLocaleString();
        },

        formatPct(value) {
          if (typeof value !== "number" || Number.isNaN(value)) {
            return "--";
          }
          const sign = value > 0 ? "+" : "";
          return `${sign}${value.toFixed(1)}%`;
        },

        applyProvenance(provenance) {
          if (!provenance) {
            this.provenanceText = "Provenance: unavailable";
            return;
          }
          const retrievedAt = provenance.retrieved_at || "unknown";
          const staleLabel = provenance.is_stale ? "yes" : "no";
          const obsDate = this.lastObservationDate || provenance.observation_date || "n/a";
          this.provenanceText =
            `Provenance: source=${provenance.source}, mode=${provenance.data_mode}, observation_date=${obsDate}, stale=${staleLabel}, retrieved_at=${retrievedAt}`;
        },

        async loadAvailableDates() {
          this.errorMessage = "";
          try {
            const response = await fetch("./api/portfolio/fixture-dates");
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

        renderSectorChart() {
          const x = this.sectorExposures.map((s) => s.sector);
          const y = this.sectorExposures.map((s) => s.net_market_value);

          const trace = {
            x,
            y,
            type: "bar",
            name: "Net Exposure",
          };

          const layout = {
            title: this.selectedDate ? `Net Exposure by Sector (${this.selectedDate})` : "Net Exposure by Sector",
            margin: { t: 48, r: 24, b: 48, l: 72 },
            xaxis: { title: "Sector" },
            yaxis: { title: "Net Market Value ($)" },
            showlegend: false,
          };

          const config = { displaylogo: false, responsive: true };

          Plotly.react("sector-chart", [trace], layout, config);
        },

        async loadExposures() {
          if (this.isLoadingExposures || this.isLoadingComparison) {
            return false;
          }

          this.isLoadingExposures = true;
          this.loadingText = "Loading exposures and concentrations...";
          this.errorMessage = "";
          this.statusText = "Loading exposures";

          try {
            const params = new URLSearchParams();
            if (this.selectedDate) {
              params.set("date", this.selectedDate);
            }
            const query = params.toString() ? `?${params.toString()}` : "";

            const exposuresResponse = await fetch(`./api/portfolio/exposures${query}`);
            if (!exposuresResponse.ok) {
              throw new Error(await this.parseErrorMessage(exposuresResponse, "Failed to load exposures"));
            }
            const exposuresPayload = await exposuresResponse.json();
            this.sectorExposures = Array.isArray(exposuresPayload.sector_exposures)
              ? exposuresPayload.sector_exposures
              : [];
            this.lastObservationDate = exposuresPayload.observation_date || this.selectedDate || "";
            this.longText = this.formatMoney(exposuresPayload.totals?.long_market_value);
            this.shortText = this.formatMoney(exposuresPayload.totals?.short_market_value);
            this.netText = this.formatMoney(exposuresPayload.totals?.net_market_value);
            this.renderSectorChart();

            const concentrationResponse = await fetch(`./api/portfolio/concentration${query}`);
            if (!concentrationResponse.ok) {
              throw new Error(await this.parseErrorMessage(concentrationResponse, "Failed to load concentration"));
            }
            const concentrationPayload = await concentrationResponse.json();
            this.topIssuers = Array.isArray(concentrationPayload.top_issuer_exposures)
              ? concentrationPayload.top_issuer_exposures
              : [];

            this.applyProvenance(exposuresPayload.provenance);
            this.statusText = "Exposures loaded";
            return true;
          } catch (err) {
            this.errorMessage = String(err);
            this.statusText = "Error";
            return false;
          } finally {
            this.isLoadingExposures = false;
          }
        },

        async loadComparison() {
          if (this.isLoadingExposures || this.isLoadingComparison) {
            return;
          }
          this.errorMessage = "";
          if (!this.selectedDate || !this.compareDate) {
            this.errorMessage = "Select both observation and comparison dates.";
            this.statusText = "Error";
            return;
          }

          this.isLoadingComparison = true;
          this.loadingText = "Loading sector exposure comparison...";
          this.statusText = "Loading comparison";
          this.sectorDeltas = [];

          try {
            const params = new URLSearchParams({
              base_date: this.compareDate,
              compare_date: this.selectedDate,
            });
            const response = await fetch(`./api/portfolio/compare?${params.toString()}`);
            if (!response.ok) {
              throw new Error(await this.parseErrorMessage(response, "Failed to load comparison"));
            }
            const payload = await response.json();
            this.sectorDeltas = Array.isArray(payload.sector_deltas) ? payload.sector_deltas : [];
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


@app.get(
    "/metadata",
    operation_id="get_portfolio_dashlet_metadata",
    summary="Get Portfolio Dashlet Metadata",
    description="Return deterministic metadata describing this dashlet's identity, data mode and supported routes.",
    response_description="Typed Portfolio dashlet metadata.",
    response_model=PortfolioDashletMetadataResponse,
)
def metadata() -> PortfolioDashletMetadataResponse:
    return PortfolioDashletMetadataResponse(
        title=app.title,
        version=app.version,
        data_mode="fixture",
        default_observation_date=_latest_available_date_str(),
        supported_endpoints=[
            "/api/portfolio/fixture-dates",
            "/api/portfolio/exposures",
            "/api/portfolio/concentration",
            "/api/portfolio/compare",
        ],
        available_fixture_dates=_provider.list_available_dates(),
    )


@app.get(
    "/api/portfolio/fixture-dates",
    operation_id="list_portfolio_fixture_dates",
    summary="List Portfolio Fixture Dates",
    description="List available deterministic portfolio fixture observation dates for discovery and UI selection.",
    response_description="Sorted list of available fixture dates.",
    response_model=PortfolioFixtureDatesResponse,
)
def list_portfolio_fixture_dates() -> PortfolioFixtureDatesResponse:
    return PortfolioFixtureDatesResponse(available_dates=_provider.list_available_dates())


@app.get(
    "/api/portfolio/exposures",
    operation_id="get_portfolio_exposures",
    tags=[AGENT_TOOL_TAG],
    summary="Get Portfolio Exposures",
    description="Return deterministic long/short/net portfolio exposure by sector and by issuer for one observation date.",
    response_description="Typed portfolio totals, sector exposures, issuer exposures and provenance.",
    responses={
        404: {"model": DashletErrorResponse, "description": "Fixture not found for the requested date."},
        502: {"model": DashletErrorResponse, "description": "Portfolio fixture is invalid."},
    },
    response_model=PortfolioExposuresResponse,
)
def get_portfolio_exposures(
    date: str | None = _optional_date_query(description=OBSERVATION_DATE_DESCRIPTION),
) -> PortfolioExposuresResponse:
    resolved_date = _resolve_observation_date_str(date)
    try:
        result = _provider.get_exposures(resolved_date)
    except ProviderError as exc:
        raise _provider_error_to_http(exc)
    return PortfolioExposuresResponse(
        observation_date=result.provenance.observation_date,
        totals=result.totals,
        sector_exposures=result.sector_exposures,
        issuer_exposures=result.issuer_exposures,
        provenance=result.provenance,
    )


@app.get(
    "/api/portfolio/concentration",
    operation_id="get_top_concentrations",
    tags=[AGENT_TOOL_TAG],
    summary="Get Top Portfolio Concentrations",
    description="Return the top issuer and sector concentrations by absolute net exposure weight for one observation date.",
    response_description="Ranked issuer and sector concentrations with provenance.",
    responses={
        404: {"model": DashletErrorResponse, "description": "Fixture not found for the requested date."},
        422: {"model": DashletErrorResponse, "description": "top_n out of the supported 1-20 range."},
        502: {"model": DashletErrorResponse, "description": "Portfolio fixture is invalid."},
    },
    response_model=PortfolioConcentrationResponse,
)
def get_top_concentrations(
    date: str | None = _optional_date_query(description=OBSERVATION_DATE_DESCRIPTION),
    top_n: int = Query(5, ge=1, le=20, description="Number of top concentrations to return (1-20)."),
) -> PortfolioConcentrationResponse:
    resolved_date = _resolve_observation_date_str(date)
    try:
        result = _provider.get_exposures(resolved_date)
    except ProviderError as exc:
        raise _provider_error_to_http(exc)

    top_issuers = sorted(result.issuer_exposures, key=lambda i: abs(i.net_weight_pct), reverse=True)[:top_n]
    top_sectors = sorted(result.sector_exposures, key=lambda s: abs(s.net_weight_pct), reverse=True)[:top_n]

    return PortfolioConcentrationResponse(
        observation_date=result.provenance.observation_date,
        top_issuer_exposures=top_issuers,
        top_sector_exposures=top_sectors,
        provenance=result.provenance,
    )


@app.get(
    "/api/portfolio/compare",
    operation_id="compare_portfolio_exposures",
    tags=[AGENT_TOOL_TAG],
    summary="Compare Portfolio Exposures",
    description="Compare sector-level net exposure between two observation dates and return the deltas.",
    response_description="Per-sector net exposure deltas with provenance.",
    responses={
        404: {"model": DashletErrorResponse, "description": "Fixture not found for at least one requested date."},
        502: {"model": DashletErrorResponse, "description": "Portfolio fixture is invalid."},
    },
    response_model=PortfolioComparisonResponse,
)
def compare_portfolio_exposures(
    base_date: str = _required_date_query(description=BASE_DATE_DESCRIPTION),
    compare_date: str = _required_date_query(description=COMPARE_DATE_DESCRIPTION),
) -> PortfolioComparisonResponse:
    try:
        base = _provider.get_exposures(base_date)
        compare = _provider.get_exposures(compare_date)
    except ProviderError as exc:
        raise _provider_error_to_http(exc)

    base_by_sector = {exposure.sector: exposure for exposure in base.sector_exposures}
    compare_by_sector = {exposure.sector: exposure for exposure in compare.sector_exposures}
    all_sectors = sorted(set(base_by_sector) | set(compare_by_sector))

    deltas = []
    for sector in all_sectors:
        base_exposure = base_by_sector.get(sector)
        compare_exposure = compare_by_sector.get(sector)
        base_net = base_exposure.net_market_value if base_exposure else 0.0
        compare_net = compare_exposure.net_market_value if compare_exposure else 0.0
        base_weight = base_exposure.net_weight_pct if base_exposure else 0.0
        compare_weight = compare_exposure.net_weight_pct if compare_exposure else 0.0
        deltas.append(
            SectorExposureDelta(
                sector=sector,
                base_net_market_value=base_net,
                compare_net_market_value=compare_net,
                delta_market_value=compare_net - base_net,
                delta_weight_pct=compare_weight - base_weight,
            )
        )

    is_stale = base.provenance.is_stale or compare.provenance.is_stale
    return PortfolioComparisonResponse(
        base_observation_date=base.provenance.observation_date,
        compare_observation_date=compare.provenance.observation_date,
        sector_deltas=deltas,
        provenance=Provenance(
            source=base.provenance.source,
            data_mode=base.provenance.data_mode,
            observation_date=base.provenance.observation_date,
            retrieved_at=datetime.now(UTC),
            source_url=base.provenance.source_url,
            is_stale=is_stale,
        ),
    )
