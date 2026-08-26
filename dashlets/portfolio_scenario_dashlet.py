from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from dashlet_framework import AGENT_TOOL_TAG, DashletErrorResponse, Provenance
from dashlet_framework.app import create_dashlet_app
from dashlets.scenario_provider import ProviderError, ScenarioImpactProvider
from scenario_fixture import PositionImpact, ScenarioShock, ScenarioTotals, SectorContribution

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "portfolio"
DATE_EXAMPLES = ["2026-08-19"]

OBSERVATION_DATE_DESCRIPTION = (
    "Observation date in YYYY-MM-DD format. Omit to use the latest available fixture date."
)
RATE_SHOCK_DESCRIPTION = "Parallel rate shock, in basis points. Bounded -300 to +300."
SPREAD_SHOCK_DESCRIPTION = "Parallel credit spread shock, in basis points. Bounded -500 to +500."
EQUITY_SHOCK_DESCRIPTION = "Equity market shock, in percent. Bounded -50 to +50."

_provider = ScenarioImpactProvider(FIXTURE_DIR)


class ScenarioFixtureDatesResponse(BaseModel):
    available_dates: list[str]


class ScenarioDashletMetadataResponse(BaseModel):
    title: str
    version: str
    data_mode: str
    default_observation_date: str
    supported_endpoints: list[str]
    available_fixture_dates: list[str]


class ScenarioRunResponse(BaseModel):
    observation_date: date
    rate_shock_bps: float
    spread_shock_bps: float
    equity_shock_pct: float
    totals: ScenarioTotals
    position_impacts: list[PositionImpact]
    sector_contributions: list[SectorContribution]
    provenance: Provenance


class ScenarioContributionsResponse(BaseModel):
    observation_date: date
    rate_shock_bps: float
    spread_shock_bps: float
    equity_shock_pct: float
    top_position_impacts: list[PositionImpact]
    sector_contributions: list[SectorContribution]
    provenance: Provenance


class ScenarioLegTotals(BaseModel):
    rate_shock_bps: float
    spread_shock_bps: float
    equity_shock_pct: float
    totals: ScenarioTotals


class SectorImpactDelta(BaseModel):
    sector: str
    impact_a: float
    impact_b: float
    delta: float


class ScenarioComparisonResponse(BaseModel):
    observation_date: date
    scenario_a: ScenarioLegTotals
    scenario_b: ScenarioLegTotals
    sector_deltas: list[SectorImpactDelta]
    provenance: Provenance


app = create_dashlet_app(title="Portfolio Scenario Impact Dashlet", version="0.1.0")


def _optional_date_query(description: str):
    return Query(default=None, description=description, examples=DATE_EXAMPLES)


def _rate_shock_query(description: str):
    return Query(default=0.0, ge=-300.0, le=300.0, description=description)


def _spread_shock_query(description: str):
    return Query(default=0.0, ge=-500.0, le=500.0, description=description)


def _equity_shock_query(description: str):
    return Query(default=0.0, ge=-50.0, le=50.0, description=description)


_DATE_QUERY = _optional_date_query(OBSERVATION_DATE_DESCRIPTION)
_RATE_SHOCK_QUERY = _rate_shock_query(RATE_SHOCK_DESCRIPTION)
_SPREAD_SHOCK_QUERY = _spread_shock_query(SPREAD_SHOCK_DESCRIPTION)
_EQUITY_SHOCK_QUERY = _equity_shock_query(EQUITY_SHOCK_DESCRIPTION)
_RATE_SHOCK_QUERY_A = _rate_shock_query("Scenario A: " + RATE_SHOCK_DESCRIPTION)
_SPREAD_SHOCK_QUERY_A = _spread_shock_query("Scenario A: " + SPREAD_SHOCK_DESCRIPTION)
_EQUITY_SHOCK_QUERY_A = _equity_shock_query("Scenario A: " + EQUITY_SHOCK_DESCRIPTION)
_RATE_SHOCK_QUERY_B = _rate_shock_query("Scenario B: " + RATE_SHOCK_DESCRIPTION)
_SPREAD_SHOCK_QUERY_B = _spread_shock_query("Scenario B: " + SPREAD_SHOCK_DESCRIPTION)
_EQUITY_SHOCK_QUERY_B = _equity_shock_query("Scenario B: " + EQUITY_SHOCK_DESCRIPTION)
_TOP_N_QUERY = Query(default=5, ge=1, le=20, description="Number of top position impacts to return (1-20).")


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
  <title>Portfolio Scenario Impact Dashlet</title>

  <!-- Pinned CDN versions -->
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4.0.6"></script>
</head>
<body class="bg-slate-50 text-slate-900 min-h-screen">
  <main class="max-w-7xl mx-auto px-4 py-6 space-y-6" x-data="scenarioApp">
    <header class="flex items-center justify-between gap-4">
      <h1 class="text-2xl font-semibold">Portfolio Scenario Impact Explorer</h1>
      <p class="text-sm text-slate-600">
        Status:
        <span class="font-medium" x-text="statusText">Idle</span>
      </p>
    </header>

    <section class="bg-white rounded-lg border border-slate-200 p-4">
      <div class="grid grid-cols-1 md:grid-cols-5 gap-3 items-end">
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
          <span class="text-sm text-slate-700">Rate Shock (bps)</span>
          <input type="number" step="1" min="-300" max="300" class="mt-1 w-full rounded-md border-slate-300" x-model.number="rateShockBps">
        </label>

        <label class="block">
          <span class="text-sm text-slate-700">Spread Shock (bps)</span>
          <input type="number" step="1" min="-500" max="500" class="mt-1 w-full rounded-md border-slate-300" x-model.number="spreadShockBps">
        </label>

        <label class="block">
          <span class="text-sm text-slate-700">Equity Shock (%)</span>
          <input type="number" step="0.5" min="-50" max="50" class="mt-1 w-full rounded-md border-slate-300" x-model.number="equityShockPct">
        </label>

        <button
          type="button"
          class="rounded-md bg-slate-900 text-white px-4 py-2"
          :disabled="isLoadingRun || isLoadingCompare"
          :class="(isLoadingRun || isLoadingCompare) ? 'opacity-60 cursor-not-allowed' : ''"
          @click="runScenario">
          Run Scenario
        </button>
      </div>
    </section>

    <section class="bg-white rounded-lg border border-slate-200 p-4">
      <h2 class="text-lg font-medium mb-3">Impact Contribution by Sector</h2>
      <div id="contribution-chart" class="w-full h-[360px]" aria-label="Sector impact contribution chart"></div>
    </section>

    <section class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <article class="bg-white rounded-lg border border-slate-200 p-4">
        <h3 class="text-sm text-slate-600">Rate Impact</h3>
        <p class="text-2xl font-semibold" x-text="rateImpactText">--</p>
      </article>

      <article class="bg-white rounded-lg border border-slate-200 p-4">
        <h3 class="text-sm text-slate-600">Spread Impact</h3>
        <p class="text-2xl font-semibold" x-text="spreadImpactText">--</p>
      </article>

      <article class="bg-white rounded-lg border border-slate-200 p-4">
        <h3 class="text-sm text-slate-600">Equity Impact</h3>
        <p class="text-2xl font-semibold" x-text="equityImpactText">--</p>
      </article>

      <article class="bg-white rounded-lg border border-slate-200 p-4">
        <h3 class="text-sm text-slate-600">Total Impact</h3>
        <p class="text-2xl font-semibold" x-text="totalImpactText">--</p>
      </article>
    </section>

    <section class="bg-white rounded-lg border border-slate-200 p-4">
      <h3 class="text-lg font-medium mb-3">Top Position Impacts</h3>
      <table class="min-w-full text-sm">
        <thead>
          <tr class="text-left border-b border-slate-200">
            <th class="py-2">Issuer</th>
            <th class="py-2">Sector</th>
            <th class="py-2">Total Impact</th>
          </tr>
        </thead>
        <tbody>
          <template x-if="topPositionImpacts.length === 0">
            <tr>
              <td class="py-2 text-slate-500" colspan="3">No scenario run yet.</td>
            </tr>
          </template>
          <template x-for="row in topPositionImpacts" :key="row.issuer">
            <tr class="border-b border-slate-100">
              <td class="py-2" x-text="row.issuer"></td>
              <td class="py-2" x-text="row.sector"></td>
              <td class="py-2" x-text="formatMoney(row.total_impact)"></td>
            </tr>
          </template>
        </tbody>
      </table>
    </section>

    <section class="bg-white rounded-lg border border-slate-200 p-4">
      <h2 class="text-lg font-medium mb-3">Compare Two Scenarios</h2>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div class="space-y-2">
          <p class="text-sm font-medium text-slate-700">Scenario A</p>
          <div class="grid grid-cols-3 gap-2">
            <input type="number" step="1" placeholder="Rate bps" class="rounded-md border-slate-300" x-model.number="rateShockBpsA">
            <input type="number" step="1" placeholder="Spread bps" class="rounded-md border-slate-300" x-model.number="spreadShockBpsA">
            <input type="number" step="0.5" placeholder="Equity %" class="rounded-md border-slate-300" x-model.number="equityShockPctA">
          </div>
        </div>
        <div class="space-y-2">
          <p class="text-sm font-medium text-slate-700">Scenario B</p>
          <div class="grid grid-cols-3 gap-2">
            <input type="number" step="1" placeholder="Rate bps" class="rounded-md border-slate-300" x-model.number="rateShockBpsB">
            <input type="number" step="1" placeholder="Spread bps" class="rounded-md border-slate-300" x-model.number="spreadShockBpsB">
            <input type="number" step="0.5" placeholder="Equity %" class="rounded-md border-slate-300" x-model.number="equityShockPctB">
          </div>
        </div>
      </div>
      <button
        type="button"
        class="mt-3 rounded-md bg-slate-700 text-white px-4 py-2"
        :disabled="isLoadingRun || isLoadingCompare"
        :class="(isLoadingRun || isLoadingCompare) ? 'opacity-60 cursor-not-allowed' : ''"
        @click="compareScenarios">
        Compare
      </button>

      <table class="min-w-full text-sm mt-4">
        <thead>
          <tr class="text-left border-b border-slate-200">
            <th class="py-2">Sector</th>
            <th class="py-2">Impact A</th>
            <th class="py-2">Impact B</th>
            <th class="py-2">Delta</th>
          </tr>
        </thead>
        <tbody>
          <template x-if="sectorDeltas.length === 0">
            <tr>
              <td class="py-2 text-slate-500" colspan="4">No comparison loaded.</td>
            </tr>
          </template>
          <template x-for="row in sectorDeltas" :key="row.sector">
            <tr class="border-b border-slate-100">
              <td class="py-2" x-text="row.sector"></td>
              <td class="py-2" x-text="formatMoney(row.impact_a)"></td>
              <td class="py-2" x-text="formatMoney(row.impact_b)"></td>
              <td class="py-2" x-text="formatMoney(row.delta)"></td>
            </tr>
          </template>
        </tbody>
      </table>
    </section>

    <section class="bg-amber-50 border border-amber-200 rounded-lg p-3" x-show="isLoadingRun || isLoadingCompare">
      <p class="text-sm text-amber-800" x-text="loadingText">Loading scenario data...</p>
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
      Alpine.data("scenarioApp", () => ({
        statusText: "Booting",
        loadingText: "Loading scenario data...",
        isLoadingRun: false,
        isLoadingCompare: false,
        errorMessage: "",
        availableDates: [],
        selectedDate: "",
        rateShockBps: 0,
        spreadShockBps: 0,
        equityShockPct: 0,
        rateShockBpsA: 0,
        spreadShockBpsA: 0,
        equityShockPctA: 0,
        rateShockBpsB: 0,
        spreadShockBpsB: 0,
        equityShockPctB: 0,
        sectorContributions: [],
        topPositionImpacts: [],
        sectorDeltas: [],
        rateImpactText: "--",
        spreadImpactText: "--",
        equityImpactText: "--",
        totalImpactText: "--",
        provenanceText: "Provenance: not loaded",
        lastObservationDate: "",

        async init() {
          this.statusText = "Initializing";
          await this.loadAvailableDates();
          await this.runScenario();
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
          const sign = value > 0 ? "+" : "";
          return sign + "$" + Math.round(value).toLocaleString();
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
            const response = await fetch("./api/scenario/fixture-dates");
            if (!response.ok) {
              throw new Error(await this.parseErrorMessage(response, "Failed to load fixture dates"));
            }
            const payload = await response.json();
            this.availableDates = Array.isArray(payload.available_dates) ? payload.available_dates : [];
            if (!this.selectedDate && this.availableDates.length > 0) {
              this.selectedDate = this.availableDates[this.availableDates.length - 1];
            }
          } catch (err) {
            this.errorMessage = String(err);
            this.statusText = "Error";
          }
        },

        renderContributionChart() {
          const x = this.sectorContributions.map((s) => s.sector);
          const y = this.sectorContributions.map((s) => s.total_impact);

          const trace = {
            x,
            y,
            type: "bar",
            name: "Impact Contribution",
          };

          const layout = {
            title: "Impact Contribution by Sector",
            margin: { t: 48, r: 24, b: 48, l: 72 },
            xaxis: { title: "Sector" },
            yaxis: { title: "Impact ($)" },
            showlegend: false,
          };

          const config = { displaylogo: false, responsive: true };

          Plotly.react("contribution-chart", [trace], layout, config);
        },

        async runScenario() {
          if (this.isLoadingRun || this.isLoadingCompare) {
            return;
          }

          this.isLoadingRun = true;
          this.loadingText = "Running scenario...";
          this.errorMessage = "";
          this.statusText = "Running scenario";

          try {
            const params = new URLSearchParams({
              rate_shock_bps: String(this.rateShockBps),
              spread_shock_bps: String(this.spreadShockBps),
              equity_shock_pct: String(this.equityShockPct),
            });
            if (this.selectedDate) {
              params.set("date", this.selectedDate);
            }
            const query = `?${params.toString()}`;

            const runResponse = await fetch(`./api/scenario/run${query}`);
            if (!runResponse.ok) {
              throw new Error(await this.parseErrorMessage(runResponse, "Failed to run scenario"));
            }
            const runPayload = await runResponse.json();
            this.sectorContributions = Array.isArray(runPayload.sector_contributions)
              ? runPayload.sector_contributions
              : [];
            this.lastObservationDate = runPayload.observation_date || this.selectedDate || "";
            this.rateImpactText = this.formatMoney(runPayload.totals?.rate_impact);
            this.spreadImpactText = this.formatMoney(runPayload.totals?.spread_impact);
            this.equityImpactText = this.formatMoney(runPayload.totals?.equity_impact);
            this.totalImpactText = this.formatMoney(runPayload.totals?.total_impact);
            this.renderContributionChart();

            const contribResponse = await fetch(`./api/scenario/contributions${query}`);
            if (!contribResponse.ok) {
              throw new Error(await this.parseErrorMessage(contribResponse, "Failed to load contributions"));
            }
            const contribPayload = await contribResponse.json();
            this.topPositionImpacts = Array.isArray(contribPayload.top_position_impacts)
              ? contribPayload.top_position_impacts
              : [];

            this.applyProvenance(runPayload.provenance);
            this.statusText = "Scenario run complete";
          } catch (err) {
            this.errorMessage = String(err);
            this.statusText = "Error";
          } finally {
            this.isLoadingRun = false;
          }
        },

        async compareScenarios() {
          if (this.isLoadingRun || this.isLoadingCompare) {
            return;
          }

          this.isLoadingCompare = true;
          this.loadingText = "Comparing scenarios...";
          this.errorMessage = "";
          this.statusText = "Comparing scenarios";
          this.sectorDeltas = [];

          try {
            const params = new URLSearchParams({
              rate_bps_a: String(this.rateShockBpsA),
              spread_bps_a: String(this.spreadShockBpsA),
              equity_pct_a: String(this.equityShockPctA),
              rate_bps_b: String(this.rateShockBpsB),
              spread_bps_b: String(this.spreadShockBpsB),
              equity_pct_b: String(this.equityShockPctB),
            });
            if (this.selectedDate) {
              params.set("date", this.selectedDate);
            }
            const response = await fetch(`./api/scenario/compare?${params.toString()}`);
            if (!response.ok) {
              throw new Error(await this.parseErrorMessage(response, "Failed to compare scenarios"));
            }
            const payload = await response.json();
            this.sectorDeltas = Array.isArray(payload.sector_deltas) ? payload.sector_deltas : [];
            this.statusText = "Comparison loaded";
          } catch (err) {
            this.errorMessage = String(err);
            this.statusText = "Error";
          } finally {
            this.isLoadingCompare = false;
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
    operation_id="get_scenario_dashlet_metadata",
    summary="Get Portfolio Scenario Dashlet Metadata",
    description="Return deterministic metadata describing this dashlet's identity, data mode and supported routes.",
    response_description="Typed Portfolio Scenario dashlet metadata.",
    response_model=ScenarioDashletMetadataResponse,
)
def metadata() -> ScenarioDashletMetadataResponse:
    return ScenarioDashletMetadataResponse(
        title=app.title,
        version=app.version,
        data_mode="fixture",
        default_observation_date=_latest_available_date_str(),
        supported_endpoints=[
            "/api/scenario/fixture-dates",
            "/api/scenario/run",
            "/api/scenario/contributions",
            "/api/scenario/compare",
        ],
        available_fixture_dates=_provider.list_available_dates(),
    )


@app.get(
    "/api/scenario/fixture-dates",
    operation_id="list_scenario_fixture_dates",
    summary="List Scenario Fixture Dates",
    description="List available deterministic portfolio fixture observation dates for discovery and UI selection.",
    response_description="Sorted list of available fixture dates.",
    response_model=ScenarioFixtureDatesResponse,
)
def list_scenario_fixture_dates() -> ScenarioFixtureDatesResponse:
    return ScenarioFixtureDatesResponse(available_dates=_provider.list_available_dates())


@app.get(
    "/api/scenario/run",
    operation_id="run_portfolio_scenario",
    tags=[AGENT_TOOL_TAG],
    summary="Run Portfolio Scenario",
    description=(
        "Apply a bounded rate/spread/equity shock to one observation date's portfolio positions and return "
        "deterministic total impact, per-position impact and per-sector contribution."
    ),
    response_description="Typed scenario totals, position impacts, sector contributions and provenance.",
    responses={
        404: {"model": DashletErrorResponse, "description": "Fixture not found for the requested date."},
        422: {"model": DashletErrorResponse, "description": "A shock parameter is outside its supported bound."},
        502: {"model": DashletErrorResponse, "description": "Portfolio fixture is invalid."},
    },
    response_model=ScenarioRunResponse,
)
def run_portfolio_scenario(
    date: str | None = _DATE_QUERY,
    rate_shock_bps: float = _RATE_SHOCK_QUERY,
    spread_shock_bps: float = _SPREAD_SHOCK_QUERY,
    equity_shock_pct: float = _EQUITY_SHOCK_QUERY,
) -> ScenarioRunResponse:
    resolved_date = _resolve_observation_date_str(date)
    shock = ScenarioShock(
        rate_shock_bps=rate_shock_bps, spread_shock_bps=spread_shock_bps, equity_shock_pct=equity_shock_pct
    )
    try:
        result = _provider.run_scenario(resolved_date, shock)
    except ProviderError as exc:
        raise _provider_error_to_http(exc)
    return ScenarioRunResponse(
        observation_date=result.provenance.observation_date,
        rate_shock_bps=rate_shock_bps,
        spread_shock_bps=spread_shock_bps,
        equity_shock_pct=equity_shock_pct,
        totals=result.totals,
        position_impacts=result.position_impacts,
        sector_contributions=result.sector_contributions,
        provenance=result.provenance,
    )


@app.get(
    "/api/scenario/contributions",
    operation_id="get_scenario_contributions",
    tags=[AGENT_TOOL_TAG],
    summary="Get Scenario Contributions",
    description=(
        "Apply a bounded rate/spread/equity shock and return the top position-level contributions "
        "(ranked by absolute impact) plus per-sector contributions."
    ),
    response_description="Ranked position impacts, sector contributions and provenance.",
    responses={
        404: {"model": DashletErrorResponse, "description": "Fixture not found for the requested date."},
        422: {"model": DashletErrorResponse, "description": "A shock or top_n parameter is out of range."},
        502: {"model": DashletErrorResponse, "description": "Portfolio fixture is invalid."},
    },
    response_model=ScenarioContributionsResponse,
)
def get_scenario_contributions(
    date: str | None = _DATE_QUERY,
    rate_shock_bps: float = _RATE_SHOCK_QUERY,
    spread_shock_bps: float = _SPREAD_SHOCK_QUERY,
    equity_shock_pct: float = _EQUITY_SHOCK_QUERY,
    top_n: int = _TOP_N_QUERY,
) -> ScenarioContributionsResponse:
    resolved_date = _resolve_observation_date_str(date)
    shock = ScenarioShock(
        rate_shock_bps=rate_shock_bps, spread_shock_bps=spread_shock_bps, equity_shock_pct=equity_shock_pct
    )
    try:
        result = _provider.run_scenario(resolved_date, shock)
    except ProviderError as exc:
        raise _provider_error_to_http(exc)

    top_positions = sorted(result.position_impacts, key=lambda impact: abs(impact.total_impact), reverse=True)[
        :top_n
    ]

    return ScenarioContributionsResponse(
        observation_date=result.provenance.observation_date,
        rate_shock_bps=rate_shock_bps,
        spread_shock_bps=spread_shock_bps,
        equity_shock_pct=equity_shock_pct,
        top_position_impacts=top_positions,
        sector_contributions=result.sector_contributions,
        provenance=result.provenance,
    )


@app.get(
    "/api/scenario/compare",
    operation_id="compare_scenario_impacts",
    tags=[AGENT_TOOL_TAG],
    summary="Compare Scenario Impacts",
    description=(
        "Apply two independent bounded rate/spread/equity shocks (scenario A and scenario B) to the same "
        "observation date's portfolio and return each scenario's totals plus per-sector impact deltas."
    ),
    response_description="Both scenarios' totals, per-sector impact deltas and provenance.",
    responses={
        404: {"model": DashletErrorResponse, "description": "Fixture not found for the requested date."},
        422: {"model": DashletErrorResponse, "description": "A shock parameter is outside its supported bound."},
        502: {"model": DashletErrorResponse, "description": "Portfolio fixture is invalid."},
    },
    response_model=ScenarioComparisonResponse,
)
def compare_scenario_impacts(
    date: str | None = _DATE_QUERY,
    rate_bps_a: float = _RATE_SHOCK_QUERY_A,
    spread_bps_a: float = _SPREAD_SHOCK_QUERY_A,
    equity_pct_a: float = _EQUITY_SHOCK_QUERY_A,
    rate_bps_b: float = _RATE_SHOCK_QUERY_B,
    spread_bps_b: float = _SPREAD_SHOCK_QUERY_B,
    equity_pct_b: float = _EQUITY_SHOCK_QUERY_B,
) -> ScenarioComparisonResponse:
    resolved_date = _resolve_observation_date_str(date)
    shock_a = ScenarioShock(rate_shock_bps=rate_bps_a, spread_shock_bps=spread_bps_a, equity_shock_pct=equity_pct_a)
    shock_b = ScenarioShock(rate_shock_bps=rate_bps_b, spread_shock_bps=spread_bps_b, equity_shock_pct=equity_pct_b)
    try:
        result_a = _provider.run_scenario(resolved_date, shock_a)
        result_b = _provider.run_scenario(resolved_date, shock_b)
    except ProviderError as exc:
        raise _provider_error_to_http(exc)

    sectors_a = {contribution.sector: contribution for contribution in result_a.sector_contributions}
    sectors_b = {contribution.sector: contribution for contribution in result_b.sector_contributions}
    all_sectors = sorted(set(sectors_a) | set(sectors_b))

    deltas = []
    for sector in all_sectors:
        impact_a = sectors_a[sector].total_impact if sector in sectors_a else 0.0
        impact_b = sectors_b[sector].total_impact if sector in sectors_b else 0.0
        deltas.append(SectorImpactDelta(sector=sector, impact_a=impact_a, impact_b=impact_b, delta=impact_b - impact_a))

    return ScenarioComparisonResponse(
        observation_date=result_a.provenance.observation_date,
        scenario_a=ScenarioLegTotals(
            rate_shock_bps=rate_bps_a, spread_shock_bps=spread_bps_a, equity_shock_pct=equity_pct_a,
            totals=result_a.totals,
        ),
        scenario_b=ScenarioLegTotals(
            rate_shock_bps=rate_bps_b, spread_shock_bps=spread_bps_b, equity_shock_pct=equity_pct_b,
            totals=result_b.totals,
        ),
        sector_deltas=deltas,
        provenance=result_a.provenance,
    )
