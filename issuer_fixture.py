from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from pydantic import BaseModel

# Concept names tried in order; different filers (and different eras of the
# same filer, post/pre ASC 606 adoption) use different XBRL revenue tags.
REVENUE_CONCEPTS: list[str] = [
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "Revenues",
    "RevenueFromContractWithCustomerIncludingAssessedTax",
]
OPERATING_INCOME_CONCEPTS: list[str] = ["OperatingIncomeLoss"]
ASSETS_CONCEPTS: list[str] = ["Assets"]
LIABILITIES_CONCEPTS: list[str] = ["Liabilities"]
EQUITY_CONCEPTS: list[str] = ["StockholdersEquity"]
OPERATING_CASH_FLOW_CONCEPTS: list[str] = ["NetCashProvidedByUsedInOperatingActivities"]

FILING_FORMS_OF_INTEREST = ("10-K", "10-Q", "8-K")


class FixtureMeta(BaseModel):
    note: str
    data_mode: str
    recorded_at: date | None = None  # None for live (not recorded, fetched fresh)


class FinancialFact(BaseModel):
    period_end: date
    period_start: date | None = None  # None for balance-sheet (instant) facts
    value: float
    accession_number: str
    filed: date
    fiscal_year: int


class PeriodFacts(BaseModel):
    period_end: date
    revenue: FinancialFact | None = None
    operating_income: FinancialFact | None = None
    operating_cash_flow: FinancialFact | None = None
    total_assets: FinancialFact | None = None
    total_liabilities: FinancialFact | None = None
    stockholders_equity: FinancialFact | None = None


class FilingRecord(BaseModel):
    form: str
    filing_date: date
    report_date: date | None = None
    accession_number: str
    primary_document: str


class IssuerSnapshot(BaseModel):
    cik: str
    ticker: str
    company_name: str
    sic: str
    sic_description: str
    revenue_concept: str
    periods: list[PeriodFacts]
    filings: list[FilingRecord]
    fixture_meta: FixtureMeta


def load_snapshot(path: str | Path) -> IssuerSnapshot:
    raw_text = Path(path).read_text()
    payload = json.loads(raw_text)
    return IssuerSnapshot.model_validate(payload)


class NormalizedMetrics(BaseModel):
    fiscal_year: int
    period_end: date
    revenue: float | None
    operating_margin_pct: float | None
    leverage_ratio: float | None  # total_liabilities / stockholders_equity
    operating_cash_flow: float | None


def compute_operating_margin_pct(revenue: float | None, operating_income: float | None) -> float | None:
    if revenue is None or operating_income is None or revenue == 0:
        return None
    return operating_income / revenue * 100.0


def compute_leverage_ratio(total_liabilities: float | None, stockholders_equity: float | None) -> float | None:
    if total_liabilities is None or stockholders_equity is None or stockholders_equity == 0:
        return None
    return total_liabilities / stockholders_equity


def normalize_period(period: PeriodFacts) -> NormalizedMetrics:
    """The fiscal_year label is derived from period_end.year, not from any
    individual fact's raw `fy` field. SEC's `fy` is filing-context metadata
    (which fiscal year's filing reported this data point), not the fiscal
    year the data covers -- it can repeat across genuinely different period
    ends (e.g. a company's FY2023, FY2024 and FY2025 10-Ks can all carry
    fy=2025 on some line items). period_end.year is unambiguous.
    """
    revenue = period.revenue.value if period.revenue else None
    operating_income = period.operating_income.value if period.operating_income else None
    liabilities = period.total_liabilities.value if period.total_liabilities else None
    equity = period.stockholders_equity.value if period.stockholders_equity else None
    operating_cash_flow = period.operating_cash_flow.value if period.operating_cash_flow else None

    return NormalizedMetrics(
        fiscal_year=period.period_end.year,
        period_end=period.period_end,
        revenue=revenue,
        operating_margin_pct=compute_operating_margin_pct(revenue, operating_income),
        leverage_ratio=compute_leverage_ratio(liabilities, equity),
        operating_cash_flow=operating_cash_flow,
    )


def _first_available_concept(gaap_facts: dict, concept_names: list[str]) -> tuple[str | None, list[dict]]:
    for name in concept_names:
        concept = gaap_facts.get(name)
        if concept and "USD" in concept.get("units", {}):
            return name, concept["units"]["USD"]
    return None, []


def _annual_facts_by_period_end(entries: list[dict]) -> dict[str, dict]:
    """Keep only 10-K, full-fiscal-year entries, keyed by period end date.
    Later entries in SEC's list win (a later filing's restated comparative
    figure supersedes an earlier one for the same period).
    """
    by_end: dict[str, dict] = {}
    for entry in entries:
        if entry.get("form") == "10-K" and entry.get("fp") == "FY":
            by_end[entry["end"]] = entry
    return by_end


def _fact_or_none(by_end: dict[str, dict], period_end: str, has_start: bool) -> FinancialFact | None:
    entry = by_end.get(period_end)
    if not entry:
        return None
    return FinancialFact(
        period_end=entry["end"],
        period_start=entry.get("start") if has_start else None,
        value=entry["val"],
        accession_number=entry["accn"],
        filed=entry["filed"],
        fiscal_year=entry["fy"],
    )


def extract_annual_periods_from_xbrl(
    company_facts_json: dict, *, max_periods: int = 5
) -> tuple[str | None, list[PeriodFacts]]:
    """Extract up to `max_periods` most recent distinct annual (10-K) fiscal
    periods from a raw SEC company-facts JSON payload (the exact shape
    returned by data.sec.gov/api/xbrl/companyfacts/CIK##########.json).

    Returns (revenue_concept_name_used, periods_oldest_to_newest).
    """
    gaap = company_facts_json.get("facts", {}).get("us-gaap", {})

    revenue_concept, revenue_entries = _first_available_concept(gaap, REVENUE_CONCEPTS)
    _, op_income_entries = _first_available_concept(gaap, OPERATING_INCOME_CONCEPTS)
    _, ocf_entries = _first_available_concept(gaap, OPERATING_CASH_FLOW_CONCEPTS)
    _, assets_entries = _first_available_concept(gaap, ASSETS_CONCEPTS)
    _, liabilities_entries = _first_available_concept(gaap, LIABILITIES_CONCEPTS)
    _, equity_entries = _first_available_concept(gaap, EQUITY_CONCEPTS)

    revenue_by_end = _annual_facts_by_period_end(revenue_entries)
    op_income_by_end = _annual_facts_by_period_end(op_income_entries)
    ocf_by_end = _annual_facts_by_period_end(ocf_entries)
    assets_by_end = _annual_facts_by_period_end(assets_entries)
    liabilities_by_end = _annual_facts_by_period_end(liabilities_entries)
    equity_by_end = _annual_facts_by_period_end(equity_entries)

    period_ends = sorted(revenue_by_end.keys())[-max_periods:]

    periods = [
        PeriodFacts(
            period_end=period_end,
            revenue=_fact_or_none(revenue_by_end, period_end, True),
            operating_income=_fact_or_none(op_income_by_end, period_end, True),
            operating_cash_flow=_fact_or_none(ocf_by_end, period_end, True),
            total_assets=_fact_or_none(assets_by_end, period_end, False),
            total_liabilities=_fact_or_none(liabilities_by_end, period_end, False),
            stockholders_equity=_fact_or_none(equity_by_end, period_end, False),
        )
        for period_end in period_ends
    ]
    return revenue_concept, periods


def extract_recent_filings(
    submissions_json: dict, *, forms: tuple[str, ...] = FILING_FORMS_OF_INTEREST, limit: int = 8
) -> list[FilingRecord]:
    """Extract up to `limit` most recent filings of interest from a raw SEC
    submissions JSON payload (data.sec.gov/submissions/CIK##########.json).
    """
    recent = submissions_json.get("filings", {}).get("recent", {})
    forms_list = recent.get("form", [])
    filings: list[FilingRecord] = []
    for i in range(len(forms_list)):
        if forms_list[i] not in forms:
            continue
        filings.append(
            FilingRecord(
                form=forms_list[i],
                filing_date=recent["filingDate"][i],
                report_date=recent["reportDate"][i] or None,
                accession_number=recent["accessionNumber"][i],
                primary_document=recent["primaryDocument"][i],
            )
        )
        if len(filings) >= limit:
            break
    return filings


def filing_source_url(cik: str, accession_number: str) -> str:
    """The canonical EDGAR filing index page for one accession number."""
    cik_no_leading_zeros = str(int(cik))
    accession_no_dashes = accession_number.replace("-", "")
    return (
        f"https://www.sec.gov/Archives/edgar/data/{cik_no_leading_zeros}/"
        f"{accession_no_dashes}/{accession_number}-index.htm"
    )


def build_snapshot_from_live_json(
    *, submissions_json: dict, company_facts_json: dict, data_mode: str, recorded_at: date | None = None
) -> IssuerSnapshot:
    """Assemble an IssuerSnapshot from raw SEC API responses. Used by both
    PublicIssuerProvider (data_mode="live", recorded_at=None) and
    scripts/generate_issuer_fixtures.py (data_mode="fixture",
    recorded_at=today) -- the same extraction logic either way.
    """
    revenue_concept, periods = extract_annual_periods_from_xbrl(company_facts_json)
    filings = extract_recent_filings(submissions_json)
    note = (
        "Recorded real SEC EDGAR data, frozen for deterministic testing. Not live."
        if data_mode == "fixture"
        else "Live SEC EDGAR data, fetched at request time."
    )
    return IssuerSnapshot(
        cik=str(submissions_json["cik"]).zfill(10),
        ticker=submissions_json["tickers"][0] if submissions_json.get("tickers") else "",
        company_name=submissions_json["name"],
        sic=submissions_json.get("sic", ""),
        sic_description=submissions_json.get("sicDescription", ""),
        revenue_concept=revenue_concept or "",
        periods=periods,
        filings=filings,
        fixture_meta=FixtureMeta(note=note, data_mode=data_mode, recorded_at=recorded_at),
    )
