#!/usr/bin/env python
"""One-shot manual live data check. Not part of the automated test suite."""
from __future__ import annotations

import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashlets.treasury_provider import (
    ProviderError,
    fetch_treasury_feed,
    normalize_to_curve_response,
    parse_treasury_feed,
)

# Edit this to today's date (or the most recent business day)
OBSERVATION_DATE = "2026-08-20"


def main() -> None:
    print(f"Fetching Treasury feed for {OBSERVATION_DATE}...")
    try:
        xml_text, source_url = fetch_treasury_feed(OBSERVATION_DATE)
    except ProviderError as exc:
        print(f"FETCH FAILED: [{exc.error_code}] {exc.message}")
        sys.exit(1)

    print(f"Fetched {len(xml_text)} bytes from:\n  {source_url}\n")

    days = parse_treasury_feed(xml_text, source_url)
    print(f"Parsed {len(days)} day(s) from feed.")

    try:
        resp = normalize_to_curve_response(
            days, OBSERVATION_DATE, source_url, datetime.now(UTC)
        )
    except ProviderError as exc:
        print(f"NORMALIZE FAILED: [{exc.error_code}] {exc.message}")
        print("(This date may be a weekend or holiday — try the previous business day.)")
        sys.exit(1)

    print("\nProvenance:")
    p = resp.provenance
    print(f"  source:           {p.source}")
    print(f"  data_mode:        {p.data_mode}")
    print(f"  observation_date: {p.observation_date}")
    print(f"  retrieved_at:     {p.retrieved_at}")
    print(f"  source_url:       {p.source_url}")

    print(f"\nCurve points ({len(resp.points)} maturities):")
    for pt in resp.points:
        print(f"  {pt.maturity_label:>4}  {pt.yield_percent:.2f}%")

    # Sanity checks
    ten_year = next((pt for pt in resp.points if pt.maturity_label == "10Y"), None)
    assert len(resp.points) >= 10, f"Expected >=10 maturities, got {len(resp.points)}"
    assert ten_year is not None, "10Y maturity missing from live feed"
    assert 3.0 <= ten_year.yield_percent <= 6.0, f"10Y yield {ten_year.yield_percent} out of sanity range"
    assert p.retrieved_at.tzinfo is not None, "retrieved_at must be timezone-aware"
    assert "daily_treasury_yield_curve" in (p.source_url or ""), "Unexpected source URL"

    print("\nSanity checks passed.")
    print("Live check passed.")


if __name__ == "__main__":
    main()
