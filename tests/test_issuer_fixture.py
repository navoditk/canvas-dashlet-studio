import json
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from issuer_fixture import (
    FilingRecord,
    PeriodFacts,
    build_snapshot_from_live_json,
    compute_leverage_ratio,
    compute_operating_margin_pct,
    extract_annual_periods_from_xbrl,
    extract_recent_filings,
    filing_source_url,
    load_snapshot,
    normalize_period,
)


def _usd_entries(values: list[tuple[str, str, float, str, str, int]]) -> list[dict]:
    """values: (start_or_None, end, val, accn, filed, fy) -- start=None for instant facts."""
    entries = []
    for start, end, val, accn, filed, fy in values:
        entry = {"end": end, "val": val, "accn": accn, "filed": filed, "fy": fy, "fp": "FY", "form": "10-K"}
        if start:
            entry["start"] = start
        entries.append(entry)
    return entries


def _sample_company_facts(*, include_equity: bool = True, use_fallback_revenue: bool = False) -> dict:
    revenue_key = "Revenues" if use_fallback_revenue else "RevenueFromContractWithCustomerExcludingAssessedTax"
    gaap: dict = {
        revenue_key: {
            "units": {
                "USD": _usd_entries(
                    [
                        ("2022-01-01", "2022-12-31", 1_000_000.0, "0000000000-23-000001", "2023-02-01", 2023),
                        ("2023-01-01", "2023-12-31", 1_200_000.0, "0000000000-24-000001", "2024-02-01", 2024),
                    ]
                )
            }
        },
        "OperatingIncomeLoss": {
            "units": {
                "USD": _usd_entries(
                    [
                        ("2022-01-01", "2022-12-31", 200_000.0, "0000000000-23-000001", "2023-02-01", 2023),
                        ("2023-01-01", "2023-12-31", 300_000.0, "0000000000-24-000001", "2024-02-01", 2024),
                    ]
                )
            }
        },
        "NetCashProvidedByUsedInOperatingActivities": {
            "units": {
                "USD": _usd_entries(
                    [
                        ("2022-01-01", "2022-12-31", 180_000.0, "0000000000-23-000001", "2023-02-01", 2023),
                        ("2023-01-01", "2023-12-31", 250_000.0, "0000000000-24-000001", "2024-02-01", 2024),
                    ]
                )
            }
        },
        "Assets": {
            "units": {
                "USD": _usd_entries(
                    [
                        (None, "2022-12-31", 2_000_000.0, "0000000000-23-000001", "2023-02-01", 2023),
                        (None, "2023-12-31", 2_400_000.0, "0000000000-24-000001", "2024-02-01", 2024),
                    ]
                )
            }
        },
        "Liabilities": {
            "units": {
                "USD": _usd_entries(
                    [
                        (None, "2022-12-31", 800_000.0, "0000000000-23-000001", "2023-02-01", 2023),
                        (None, "2023-12-31", 900_000.0, "0000000000-24-000001", "2024-02-01", 2024),
                    ]
                )
            }
        },
    }
    if include_equity:
        gaap["StockholdersEquity"] = {
            "units": {
                "USD": _usd_entries(
                    [
                        (None, "2022-12-31", 1_200_000.0, "0000000000-23-000001", "2023-02-01", 2023),
                        (None, "2023-12-31", 1_500_000.0, "0000000000-24-000001", "2024-02-01", 2024),
                    ]
                )
            }
        }
    return {"cik": 1234567, "entityName": "Sample Corp", "facts": {"us-gaap": gaap}}


def _sample_submissions() -> dict:
    return {
        "cik": "1234567",
        "name": "Sample Corp",
        "sic": "7372",
        "sicDescription": "Services-Prepackaged Software",
        "tickers": ["SMPL"],
        "filings": {
            "recent": {
                "form": ["10-K", "4", "10-Q", "8-K", "8-K"],
                "filingDate": ["2024-02-01", "2024-01-15", "2023-11-01", "2023-10-01", "2023-09-01"],
                "reportDate": ["2023-12-31", "", "2023-09-30", "", ""],
                "accessionNumber": [
                    "0000000000-24-000001",
                    "0000000000-24-000000",
                    "0000000000-23-000005",
                    "0000000000-23-000004",
                    "0000000000-23-000003",
                ],
                "primaryDocument": ["smpl-10k.htm", "form4.xml", "smpl-10q.htm", "smpl-8k1.htm", "smpl-8k2.htm"],
            }
        },
    }


def test_extract_annual_periods_maps_all_concepts() -> None:
    revenue_concept, periods = extract_annual_periods_from_xbrl(_sample_company_facts())
    assert revenue_concept == "RevenueFromContractWithCustomerExcludingAssessedTax"
    assert len(periods) == 2
    latest = periods[-1]
    assert latest.period_end == date(2023, 12, 31)
    assert latest.revenue.value == 1_200_000.0
    assert latest.revenue.period_start == date(2023, 1, 1)
    assert latest.total_assets.value == 2_400_000.0
    assert latest.total_assets.period_start is None  # balance-sheet fact is instant


def test_extract_annual_periods_falls_back_to_second_revenue_concept() -> None:
    revenue_concept, periods = extract_annual_periods_from_xbrl(
        _sample_company_facts(use_fallback_revenue=True)
    )
    assert revenue_concept == "Revenues"
    assert periods[-1].revenue.value == 1_200_000.0


def test_extract_annual_periods_missing_concept_yields_none_fact() -> None:
    _, periods = extract_annual_periods_from_xbrl(_sample_company_facts(include_equity=False))
    assert periods[-1].stockholders_equity is None


def test_extract_annual_periods_respects_max_periods() -> None:
    _, periods = extract_annual_periods_from_xbrl(_sample_company_facts(), max_periods=1)
    assert len(periods) == 1
    assert periods[0].period_end == date(2023, 12, 31)


def test_extract_recent_filings_filters_to_forms_of_interest_and_limits() -> None:
    filings = extract_recent_filings(_sample_submissions(), limit=3)
    assert len(filings) == 3
    assert [f.form for f in filings] == ["10-K", "10-Q", "8-K"]  # "4" is skipped
    assert filings[0].report_date == date(2023, 12, 31)
    assert filings[1].report_date == date(2023, 9, 30)


def test_extract_recent_filings_missing_report_date_is_none() -> None:
    filings = extract_recent_filings(_sample_submissions(), forms=("8-K",), limit=5)
    assert all(f.report_date is None for f in filings)


def test_compute_operating_margin_pct() -> None:
    assert compute_operating_margin_pct(1_000_000.0, 250_000.0) == pytest.approx(25.0)


def test_compute_operating_margin_pct_zero_revenue_guard() -> None:
    assert compute_operating_margin_pct(0.0, 100.0) is None


def test_compute_operating_margin_pct_missing_values_guard() -> None:
    assert compute_operating_margin_pct(None, 100.0) is None
    assert compute_operating_margin_pct(100.0, None) is None


def test_compute_leverage_ratio() -> None:
    assert compute_leverage_ratio(900_000.0, 1_500_000.0) == pytest.approx(0.6)


def test_compute_leverage_ratio_zero_equity_guard() -> None:
    assert compute_leverage_ratio(900_000.0, 0.0) is None


def test_normalize_period_fiscal_year_derived_from_period_end_not_raw_fy() -> None:
    # Regression test: SEC's raw `fy` field is filing-context metadata, not
    # the fiscal year the data covers, and can repeat across genuinely
    # different period ends. fiscal_year must come from period_end.year.
    period = PeriodFacts.model_validate(
        {
            "period_end": "2023-12-31",
            "revenue": {
                "period_end": "2023-12-31",
                "period_start": "2023-01-01",
                "value": 1_200_000.0,
                "accession_number": "acc",
                "filed": "2024-02-01",
                "fiscal_year": 2099,  # deliberately wrong/irrelevant raw fy
            },
        }
    )
    metrics = normalize_period(period)
    assert metrics.fiscal_year == 2023


def test_normalize_period_full_metrics() -> None:
    _, periods = extract_annual_periods_from_xbrl(_sample_company_facts())
    metrics = normalize_period(periods[-1])
    assert metrics.fiscal_year == 2023
    assert metrics.revenue == 1_200_000.0
    assert metrics.operating_margin_pct == pytest.approx(300_000.0 / 1_200_000.0 * 100.0)
    assert metrics.leverage_ratio == pytest.approx(900_000.0 / 1_500_000.0)
    assert metrics.operating_cash_flow == 250_000.0


def test_filing_source_url_strips_leading_zeros_and_dashes() -> None:
    url = filing_source_url("0000320193", "0000320193-25-000079")
    assert url == (
        "https://www.sec.gov/Archives/edgar/data/320193/"
        "000032019325000079/0000320193-25-000079-index.htm"
    )


def test_build_snapshot_from_live_json_fixture_mode() -> None:
    snapshot = build_snapshot_from_live_json(
        submissions_json=_sample_submissions(),
        company_facts_json=_sample_company_facts(),
        data_mode="fixture",
        recorded_at=date(2026, 8, 26),
    )
    assert snapshot.ticker == "SMPL"
    assert snapshot.company_name == "Sample Corp"
    assert snapshot.cik == "0001234567"
    assert snapshot.fixture_meta.data_mode == "fixture"
    assert snapshot.fixture_meta.recorded_at == date(2026, 8, 26)
    assert len(snapshot.periods) == 2
    assert len(snapshot.filings) > 0


def test_build_snapshot_from_live_json_live_mode_has_no_recorded_at() -> None:
    snapshot = build_snapshot_from_live_json(
        submissions_json=_sample_submissions(), company_facts_json=_sample_company_facts(), data_mode="live"
    )
    assert snapshot.fixture_meta.data_mode == "live"
    assert snapshot.fixture_meta.recorded_at is None


def test_load_snapshot_round_trips(tmp_path) -> None:
    snapshot = build_snapshot_from_live_json(
        submissions_json=_sample_submissions(),
        company_facts_json=_sample_company_facts(),
        data_mode="fixture",
        recorded_at=date(2026, 8, 26),
    )
    path = tmp_path / "SMPL.json"
    path.write_text(json.dumps(snapshot.model_dump(mode="json"), indent=2))

    loaded = load_snapshot(path)
    assert loaded.ticker == "SMPL"
    assert loaded.periods[-1].revenue.value == 1_200_000.0


def test_filing_record_optional_report_date() -> None:
    record = FilingRecord(
        form="8-K",
        filing_date=date(2024, 1, 1),
        accession_number="0000000000-24-000000",
        primary_document="doc.htm",
    )
    assert record.report_date is None
