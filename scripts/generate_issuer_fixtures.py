#!/usr/bin/env python
"""Generate/refresh recorded SEC EDGAR fixtures for Issuer Research.

Fetches real, live data from SEC EDGAR's public APIs for a small set of
tickers and freezes it into fixtures/issuer/<TICKER>.json for deterministic,
network-free automated testing (see docs/DATA_ACCESS.md §2, §6). This is
recorded real data, not synthetic/fictional data -- see issuer_fixture.py
and dashlets/issuer_provider.py for why Issuer Research's fixture path
differs from Treasury's/Portfolio Exposure's in that respect.

This is a manual maintenance script, not part of CI. Unlike
scripts/generate_tool_schemas.py (where drift from source is a bug this
script exists to catch), fixture data here legitimately going stale
relative to live SEC data is expected and fine -- that is the entire point
of a frozen snapshot. Re-run this periodically, or when adding a new
reference ticker:

    uv run python scripts/generate_issuer_fixtures.py
    uv run python scripts/generate_issuer_fixtures.py --tickers AAPL MSFT GOOGL
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashlets.issuer_provider import PublicIssuerProvider
from issuer_fixture import build_snapshot_from_live_json

DEFAULT_TICKERS = ["AAPL", "MSFT"]
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "issuer"


def generate_fixture(ticker: str, provider: PublicIssuerProvider) -> None:
    _, submissions, company_facts = provider.fetch_raw(ticker)
    snapshot = build_snapshot_from_live_json(
        submissions_json=submissions,
        company_facts_json=company_facts,
        data_mode="fixture",
        recorded_at=datetime.now(UTC).date(),
    )
    output_path = OUTPUT_DIR / f"{ticker}.json"
    output_path.write_text(json.dumps(snapshot.model_dump(mode="json"), indent=2) + "\n")
    print(f"Wrote {output_path} ({len(snapshot.periods)} periods, {len(snapshot.filings)} filings)")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tickers", nargs="+", default=DEFAULT_TICKERS, help="Tickers to fetch and freeze")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    provider = PublicIssuerProvider()
    for ticker in args.tickers:
        generate_fixture(ticker.upper(), provider)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
