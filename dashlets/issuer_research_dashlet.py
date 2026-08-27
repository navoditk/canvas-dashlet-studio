from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from dashlet_framework import AGENT_TOOL_TAG, DashletErrorResponse, Provenance
from dashlet_framework.app import create_dashlet_app
from dashlets.issuer_provider import IssuerDataMode, ProviderError, resolve_provider
from issuer_fixture import FilingRecord, FinancialFact, filing_source_url, normalize_period

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "issuer"

TICKER_DESCRIPTION = "Company ticker symbol, e.g. AAPL. Case-insensitive."
DATA_MODE_DESCRIPTION = (
    "Required data source. 'fixture' uses a small set of recorded real SEC snapshots "
    "(AAPL, MSFT) for deterministic testing. 'live' fetches current data from SEC EDGAR "
    "for any of the ~10,388 SEC-registered tickers."
)


class SourceFactOut(BaseModel):
    value: float
    period_end: date
    period_start: date | None
    fiscal_year: int
    accession_number: str
    filed: date
    source_url: str


class CompanyFactsResponse(BaseModel):
    cik: str
    ticker: str
    company_name: str
    sic: str
    sic_description: str
    fiscal_year: int
    period_end: date
    revenue: SourceFactOut | None
    operating_income: SourceFactOut | None
    operating_margin_pct: float | None
    total_assets: SourceFactOut | None
    total_liabilities: SourceFactOut | None
    stockholders_equity: SourceFactOut | None
    leverage_ratio: float | None
    operating_cash_flow: SourceFactOut | None
    provenance: Provenance


class TrendPointOut(BaseModel):
    fiscal_year: int
    period_end: date
    revenue: float | None
    operating_margin_pct: float | None
    leverage_ratio: float | None
    operating_cash_flow: float | None


class FinancialTrendsResponse(BaseModel):
    cik: str
    ticker: str
    company_name: str
    trend_points: list[TrendPointOut]
    provenance: Provenance


class FilingSummaryOut(BaseModel):
    form: str
    filing_date: date
    report_date: date | None
    accession_number: str
    primary_document: str
    source_url: str


class RecentFilingsResponse(BaseModel):
    cik: str
    ticker: str
    company_name: str
    filings: list[FilingSummaryOut]
    provenance: Provenance


class AvailableIssuersResponse(BaseModel):
    available_fixture_tickers: list[str]


class IssuerDashletMetadataResponse(BaseModel):
    title: str
    version: str
    data_mode: str
    default_ticker: str
    supported_endpoints: list[str]
    available_fixture_tickers: list[str]


app = create_dashlet_app(title="Issuer Research Dashlet", version="0.1.0")


def _ticker_query(description: str = TICKER_DESCRIPTION):
    return Query(..., min_length=1, max_length=10, description=description)


def _data_mode_query(description: str = DATA_MODE_DESCRIPTION):
    return Query(..., description=description)


_TICKER_QUERY = _ticker_query()
_DATA_MODE_QUERY = _data_mode_query()
_YEARS_QUERY = Query(default=5, ge=1, le=5, description="Number of most recent fiscal years to return (1-5).")
_LIMIT_QUERY = Query(default=8, ge=1, le=8, description="Number of most recent filings to return (1-8).")
_FORM_TYPE_QUERY = Query(
    default=None, description="Optional filter to one filing form type, e.g. '10-K'. Omit for all forms."
)


_PROVIDER_STATUS_MAP: dict[str, int] = {
    "unknown_ticker": 404,
    "ticker_not_found": 404,
    "missing_financial_data": 502,
    "sec_fetch_error": 502,
    "sec_timeout": 504,
    "sec_network_error": 502,
}


def _provider_error_to_http(exc: ProviderError) -> HTTPException:
    status_code = _PROVIDER_STATUS_MAP.get(exc.error_code, 502)
    raise HTTPException(status_code=status_code, detail={"error_code": exc.error_code, "message": exc.message})


def _to_source_fact_out(fact: FinancialFact | None, cik: str) -> SourceFactOut | None:
    if fact is None:
        return None
    return SourceFactOut(
        value=fact.value,
        period_end=fact.period_end,
        period_start=fact.period_start,
        fiscal_year=fact.fiscal_year,
        accession_number=fact.accession_number,
        filed=fact.filed,
        source_url=filing_source_url(cik, fact.accession_number),
    )


def _to_filing_summary_out(filing: FilingRecord, cik: str) -> FilingSummaryOut:
    return FilingSummaryOut(
        form=filing.form,
        filing_date=filing.filing_date,
        report_date=filing.report_date,
        accession_number=filing.accession_number,
        primary_document=filing.primary_document,
        source_url=filing_source_url(cik, filing.accession_number),
    )


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <title>Issuer Research Dashlet</title>

  <!-- Pinned CDN versions -->
  <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.14.1/dist/cdn.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/plotly.js-dist-min@2.35.2/plotly.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/@tailwindcss/browser@4.0.6"></script>
</head>
<body class="bg-slate-50 text-slate-900 min-h-screen">
  <main class="max-w-7xl mx-auto px-4 py-6 space-y-6" x-data="issuerApp">
    <header class="flex items-center justify-between gap-4">
      <h1 class="text-2xl font-semibold">Issuer Research Monitor</h1>
      <p class="text-sm text-slate-600">
        Status:
        <span class="font-medium" x-text="statusText">Idle</span>
      </p>
    </header>

    <section class="bg-white rounded-lg border border-slate-200 p-4">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-3 items-end">
        <label class="block">
          <span class="text-sm text-slate-700">Ticker</span>
          <input type="text" class="mt-1 w-full rounded-md border-slate-300 uppercase" x-model="ticker" placeholder="AAPL">
        </label>

        <label class="block">
          <span class="text-sm text-slate-700">Data Mode</span>
          <select class="mt-1 w-full rounded-md border-slate-300" x-model="dataMode">
            <option value="fixture">fixture (recorded)</option>
            <option value="live">live (SEC EDGAR)</option>
          </select>
        </label>

        <div class="block">
          <span class="text-sm text-slate-700">Fixture tickers</span>
          <div class="mt-1 flex gap-2">
            <template x-for="t in availableFixtureTickers" :key="t">
              <button type="button" class="rounded-md border border-slate-300 px-2 py-1 text-sm" @click="ticker = t">
                <span x-text="t"></span>
              </button>
            </template>
          </div>
        </div>

        <button
          type="button"
          class="rounded-md bg-slate-900 text-white px-4 py-2"
          :disabled="isLoading"
          :class="isLoading ? 'opacity-60 cursor-not-allowed' : ''"
          @click="loadIssuer">
          Load
        </button>
      </div>
    </section>

    <section class="bg-white rounded-lg border border-slate-200 p-4" x-show="companyName">
      <h2 class="text-lg font-medium" x-text="companyName">Company</h2>
      <p class="text-sm text-slate-600" x-text="sicDescription"></p>
    </section>

    <section class="bg-white rounded-lg border border-slate-200 p-4">
      <h2 class="text-lg font-medium mb-3">Revenue Trend</h2>
      <div id="trend-chart" class="w-full h-[360px]" aria-label="Revenue trend chart"></div>
    </section>

    <section class="grid grid-cols-1 md:grid-cols-4 gap-4">
      <article class="bg-white rounded-lg border border-slate-200 p-4">
        <h3 class="text-sm text-slate-600">Revenue</h3>
        <p class="text-2xl font-semibold" x-text="revenueText">--</p>
        <a class="text-xs text-blue-700 underline" :href="revenueSourceUrl" x-show="revenueSourceUrl" target="_blank" rel="noopener">Source</a>
      </article>

      <article class="bg-white rounded-lg border border-slate-200 p-4">
        <h3 class="text-sm text-slate-600">Operating Margin</h3>
        <p class="text-2xl font-semibold" x-text="operatingMarginText">--</p>
      </article>

      <article class="bg-white rounded-lg border border-slate-200 p-4">
        <h3 class="text-sm text-slate-600">Leverage Ratio</h3>
        <p class="text-2xl font-semibold" x-text="leverageText">--</p>
      </article>

      <article class="bg-white rounded-lg border border-slate-200 p-4">
        <h3 class="text-sm text-slate-600">Operating Cash Flow</h3>
        <p class="text-2xl font-semibold" x-text="cashFlowText">--</p>
      </article>
    </section>

    <section class="bg-white rounded-lg border border-slate-200 p-4">
      <h3 class="text-lg font-medium mb-3">Recent Filings</h3>
      <table class="min-w-full text-sm">
        <thead>
          <tr class="text-left border-b border-slate-200">
            <th class="py-2">Form</th>
            <th class="py-2">Filing Date</th>
            <th class="py-2">Report Date</th>
            <th class="py-2">Source</th>
          </tr>
        </thead>
        <tbody>
          <template x-if="filings.length === 0">
            <tr>
              <td class="py-2 text-slate-500" colspan="4">No filings loaded.</td>
            </tr>
          </template>
          <template x-for="row in filings" :key="row.accession_number">
            <tr class="border-b border-slate-100">
              <td class="py-2" x-text="row.form"></td>
              <td class="py-2" x-text="row.filing_date"></td>
              <td class="py-2" x-text="row.report_date || 'n/a'"></td>
              <td class="py-2"><a class="text-blue-700 underline" :href="row.source_url" target="_blank" rel="noopener">EDGAR</a></td>
            </tr>
          </template>
        </tbody>
      </table>
    </section>

    <section class="bg-amber-50 border border-amber-200 rounded-lg p-3" x-show="isLoading">
      <p class="text-sm text-amber-800">Loading issuer research data...</p>
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
      Alpine.data("issuerApp", () => ({
        statusText: "Booting",
        isLoading: false,
        errorMessage: "",
        ticker: "AAPL",
        dataMode: "fixture",
        availableFixtureTickers: [],
        companyName: "",
        sicDescription: "",
        trendPoints: [],
        filings: [],
        revenueText: "--",
        revenueSourceUrl: "",
        operatingMarginText: "--",
        leverageText: "--",
        cashFlowText: "--",
        provenanceText: "Provenance: not loaded",

        async init() {
          this.statusText = "Initializing";
          await this.loadAvailableFixtureTickers();
          await this.loadIssuer();
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
          return "$" + Math.round(value / 1_000_000).toLocaleString() + "M";
        },

        formatPct(value) {
          if (typeof value !== "number" || Number.isNaN(value)) {
            return "--";
          }
          return value.toFixed(1) + "%";
        },

        formatRatio(value) {
          if (typeof value !== "number" || Number.isNaN(value)) {
            return "--";
          }
          return value.toFixed(2) + "x";
        },

        applyProvenance(provenance) {
          if (!provenance) {
            this.provenanceText = "Provenance: unavailable";
            return;
          }
          const retrievedAt = provenance.retrieved_at || "unknown";
          const staleLabel = provenance.is_stale ? "yes" : "no";
          this.provenanceText =
            `Provenance: source=${provenance.source}, mode=${provenance.data_mode}, observation_date=${provenance.observation_date}, stale=${staleLabel}, retrieved_at=${retrievedAt}`;
        },

        async loadAvailableFixtureTickers() {
          try {
            const response = await fetch("./api/issuer/companies");
            if (!response.ok) {
              return;
            }
            const payload = await response.json();
            this.availableFixtureTickers = Array.isArray(payload.available_fixture_tickers)
              ? payload.available_fixture_tickers
              : [];
          } catch (_) {
            // Non-fatal: the ticker quick-select buttons just won't populate.
          }
        },

        renderTrendChart() {
          const x = this.trendPoints.map((p) => p.fiscal_year);
          const y = this.trendPoints.map((p) => p.revenue);

          const trace = { x, y, type: "bar", name: "Revenue" };
          const layout = {
            title: this.companyName ? `Revenue Trend (${this.companyName})` : "Revenue Trend",
            margin: { t: 48, r: 24, b: 48, l: 72 },
            xaxis: { title: "Fiscal Year", type: "category" },
            yaxis: { title: "Revenue ($)" },
            showlegend: false,
          };
          const config = { displaylogo: false, responsive: true };
          Plotly.react("trend-chart", [trace], layout, config);
        },

        async loadIssuer() {
          if (this.isLoading || !this.ticker) {
            return;
          }

          this.isLoading = true;
          this.errorMessage = "";
          this.statusText = "Loading";

          try {
            const params = new URLSearchParams({ ticker: this.ticker.toUpperCase(), data_mode: this.dataMode });
            const query = `?${params.toString()}`;

            const factsResponse = await fetch(`./api/issuer/facts${query}`);
            if (!factsResponse.ok) {
              throw new Error(await this.parseErrorMessage(factsResponse, "Failed to load company facts"));
            }
            const facts = await factsResponse.json();
            this.companyName = facts.company_name || "";
            this.sicDescription = facts.sic_description || "";
            this.revenueText = this.formatMoney(facts.revenue ? facts.revenue.value : null);
            this.revenueSourceUrl = facts.revenue ? facts.revenue.source_url : "";
            this.operatingMarginText = this.formatPct(facts.operating_margin_pct);
            this.leverageText = this.formatRatio(facts.leverage_ratio);
            this.cashFlowText = this.formatMoney(facts.operating_cash_flow ? facts.operating_cash_flow.value : null);
            this.applyProvenance(facts.provenance);

            const trendsResponse = await fetch(`./api/issuer/trends${query}`);
            if (!trendsResponse.ok) {
              throw new Error(await this.parseErrorMessage(trendsResponse, "Failed to load financial trends"));
            }
            const trends = await trendsResponse.json();
            this.trendPoints = Array.isArray(trends.trend_points) ? trends.trend_points : [];
            this.renderTrendChart();

            const filingsResponse = await fetch(`./api/issuer/filings${query}`);
            if (!filingsResponse.ok) {
              throw new Error(await this.parseErrorMessage(filingsResponse, "Failed to load filings"));
            }
            const filingsPayload = await filingsResponse.json();
            this.filings = Array.isArray(filingsPayload.filings) ? filingsPayload.filings : [];

            this.statusText = "Loaded";
          } catch (err) {
            this.errorMessage = String(err);
            this.statusText = "Error";
          } finally {
            this.isLoading = false;
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
    operation_id="get_issuer_dashlet_metadata",
    summary="Get Issuer Research Dashlet Metadata",
    description="Return deterministic metadata describing this dashlet's identity, supported data modes and routes.",
    response_description="Typed Issuer Research dashlet metadata.",
    response_model=IssuerDashletMetadataResponse,
)
def metadata() -> IssuerDashletMetadataResponse:
    fixture_provider = resolve_provider(IssuerDataMode.FIXTURE, FIXTURE_DIR)
    return IssuerDashletMetadataResponse(
        title=app.title,
        version=app.version,
        data_mode="fixture,live",
        default_ticker="AAPL",
        supported_endpoints=[
            "/api/issuer/companies",
            "/api/issuer/facts",
            "/api/issuer/trends",
            "/api/issuer/filings",
        ],
        available_fixture_tickers=fixture_provider.list_available_tickers(),
    )


@app.get(
    "/api/issuer/companies",
    operation_id="list_available_issuers",
    summary="List Available Fixture Issuers",
    description="List tickers available in fixture (recorded) mode. Live mode supports any SEC-registered ticker.",
    response_description="Sorted list of recorded fixture tickers.",
    response_model=AvailableIssuersResponse,
)
def list_available_issuers() -> AvailableIssuersResponse:
    fixture_provider = resolve_provider(IssuerDataMode.FIXTURE, FIXTURE_DIR)
    return AvailableIssuersResponse(available_fixture_tickers=fixture_provider.list_available_tickers())


@app.get(
    "/api/issuer/facts",
    operation_id="get_company_facts",
    tags=[AGENT_TOOL_TAG],
    summary="Get Company Facts",
    description=(
        "Return the latest normalized revenue, operating margin, leverage and operating cash flow for one "
        "issuer, with source accession numbers and filing links for every underlying fact."
    ),
    response_description="Typed latest-period company facts with source links and provenance.",
    responses={
        404: {"model": DashletErrorResponse, "description": "Ticker not found."},
        422: {"model": DashletErrorResponse, "description": "Invalid data_mode."},
        502: {"model": DashletErrorResponse, "description": "SEC EDGAR data unavailable or incomplete."},
        504: {"model": DashletErrorResponse, "description": "SEC EDGAR request timed out."},
    },
    response_model=CompanyFactsResponse,
)
def get_company_facts(
    ticker: str = _TICKER_QUERY,
    data_mode: IssuerDataMode = _DATA_MODE_QUERY,
) -> CompanyFactsResponse:
    provider = resolve_provider(data_mode, FIXTURE_DIR)
    try:
        result = provider.get_snapshot(ticker)
    except ProviderError as exc:
        raise _provider_error_to_http(exc)

    snapshot = result.snapshot
    if not snapshot.periods:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "no_financial_data", "message": f"No annual financial data for {ticker}"},
        )
    latest = snapshot.periods[-1]
    metrics = normalize_period(latest)
    cik = snapshot.cik

    return CompanyFactsResponse(
        cik=cik,
        ticker=snapshot.ticker,
        company_name=snapshot.company_name,
        sic=snapshot.sic,
        sic_description=snapshot.sic_description,
        fiscal_year=metrics.fiscal_year,
        period_end=latest.period_end,
        revenue=_to_source_fact_out(latest.revenue, cik),
        operating_income=_to_source_fact_out(latest.operating_income, cik),
        operating_margin_pct=metrics.operating_margin_pct,
        total_assets=_to_source_fact_out(latest.total_assets, cik),
        total_liabilities=_to_source_fact_out(latest.total_liabilities, cik),
        stockholders_equity=_to_source_fact_out(latest.stockholders_equity, cik),
        leverage_ratio=metrics.leverage_ratio,
        operating_cash_flow=_to_source_fact_out(latest.operating_cash_flow, cik),
        provenance=result.provenance,
    )


@app.get(
    "/api/issuer/trends",
    operation_id="get_financial_trends",
    tags=[AGENT_TOOL_TAG],
    summary="Get Financial Trends",
    description="Return normalized revenue, operating margin, leverage and cash-flow trends across recent fiscal years for one issuer.",
    response_description="Typed multi-year trend points with provenance.",
    responses={
        404: {"model": DashletErrorResponse, "description": "Ticker not found."},
        422: {"model": DashletErrorResponse, "description": "Invalid data_mode or years out of range."},
        502: {"model": DashletErrorResponse, "description": "SEC EDGAR data unavailable or incomplete."},
        504: {"model": DashletErrorResponse, "description": "SEC EDGAR request timed out."},
    },
    response_model=FinancialTrendsResponse,
)
def get_financial_trends(
    ticker: str = _TICKER_QUERY,
    data_mode: IssuerDataMode = _DATA_MODE_QUERY,
    years: int = _YEARS_QUERY,
) -> FinancialTrendsResponse:
    provider = resolve_provider(data_mode, FIXTURE_DIR)
    try:
        result = provider.get_snapshot(ticker)
    except ProviderError as exc:
        raise _provider_error_to_http(exc)

    snapshot = result.snapshot
    recent_periods = snapshot.periods[-years:]
    trend_points = [
        TrendPointOut(
            fiscal_year=metrics.fiscal_year,
            period_end=metrics.period_end,
            revenue=metrics.revenue,
            operating_margin_pct=metrics.operating_margin_pct,
            leverage_ratio=metrics.leverage_ratio,
            operating_cash_flow=metrics.operating_cash_flow,
        )
        for metrics in (normalize_period(period) for period in recent_periods)
    ]

    return FinancialTrendsResponse(
        cik=snapshot.cik,
        ticker=snapshot.ticker,
        company_name=snapshot.company_name,
        trend_points=trend_points,
        provenance=result.provenance,
    )


@app.get(
    "/api/issuer/filings",
    operation_id="list_recent_filings",
    tags=[AGENT_TOOL_TAG],
    summary="List Recent Filings",
    description="Return a recent filing timeline (10-K/10-Q/8-K) for one issuer, with source links to each filing.",
    response_description="Typed recent filings with source links and provenance.",
    responses={
        404: {"model": DashletErrorResponse, "description": "Ticker not found."},
        422: {"model": DashletErrorResponse, "description": "Invalid data_mode or limit out of range."},
        502: {"model": DashletErrorResponse, "description": "SEC EDGAR data unavailable or incomplete."},
        504: {"model": DashletErrorResponse, "description": "SEC EDGAR request timed out."},
    },
    response_model=RecentFilingsResponse,
)
def list_recent_filings(
    ticker: str = _TICKER_QUERY,
    data_mode: IssuerDataMode = _DATA_MODE_QUERY,
    limit: int = _LIMIT_QUERY,
    form_type: str | None = _FORM_TYPE_QUERY,
) -> RecentFilingsResponse:
    provider = resolve_provider(data_mode, FIXTURE_DIR)
    try:
        result = provider.get_snapshot(ticker)
    except ProviderError as exc:
        raise _provider_error_to_http(exc)

    snapshot = result.snapshot
    filings = snapshot.filings
    if form_type:
        filings = [f for f in filings if f.form == form_type]
    filings = filings[:limit]

    return RecentFilingsResponse(
        cik=snapshot.cik,
        ticker=snapshot.ticker,
        company_name=snapshot.company_name,
        filings=[_to_filing_summary_out(f, snapshot.cik) for f in filings],
        provenance=result.provenance,
    )
