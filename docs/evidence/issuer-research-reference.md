# Evidence: Issuer Research Reference Milestone

## Milestone name

Issuer Research dashlet — fourth and final originally-planned reference use case, and the only one built on **real public data by default** rather than mock data, per explicit user request.

## Validation date

2026-08-27. Direct-FastAPI, automated-test, and real-live-network sections are complete. Live-Canvas-specific sections are **not yet completed** — deliberately deferred, same recorded reasoning as Portfolio Exposure and Portfolio Scenario Impact (see `docs/PROGRESS.md` "Resume here").

## Commit SHAs

`9dddbbe` (extraction/normalization module), `c61a1da` (providers), `a385dad` (fixture-generation script + real fixture data), `4b71388` (dashlet + tests), and the Canvas-registration/docs commit that follows this evidence doc — all on `main`.

## Architecture exercised

```text
Copilot agent tool call ──┐
                          ├─▶ Canvas ToolProxy (allowlist + generated-schema validation) ─┐
Canvas iframe fetch("./api/...") ──────────────────────────────────────────────────────┼─▶ FastAPI dashlet (dashlets/issuer_research_dashlet.py)
                                                                                         └─▶ FixtureIssuerProvider (recorded) or PublicIssuerProvider (live SEC EDGAR)
```

Both consumers (iframe JavaScript and the Copilot agent) invoke the same three `agent-tool`-tagged FastAPI operations: `get_company_facts`, `get_financial_trends`, `list_recent_filings`. Unlike the two Portfolio dashlets, this one has a real, meaningful `live` data mode — `PublicIssuerProvider` fetches directly from [SEC EDGAR's public APIs](https://www.sec.gov/os/webmaster-faq#developers) (`data.sec.gov`), verified live and working before any code was written.

## Direct FastAPI verification summary

| Check | Result |
|---|---|
| `GET /health` | `{"status":"ready"}` |
| `GET /metadata` | `data_mode: "fixture,live"`, `default_ticker: "AAPL"`, `available_fixture_tickers: ["AAPL", "MSFT"]` |
| `get_company_facts` parameters | `ticker` (required), `data_mode` (required, enum `["fixture","live"]`) |
| `get_financial_trends` parameters | `ticker`, `data_mode` (both required), `years` (optional, bounded 1–5) |
| `list_recent_filings` parameters | `ticker`, `data_mode` (both required), `limit` (optional, bounded 1–8), `form_type` (optional) |
| `years=10` (out of range) | `422` |
| Unknown `ticker=ZZZZ` in fixture mode | `404`, `{"error_code": "unknown_ticker", "message": "No recorded fixture for ticker: ZZZZ. Available: AAPL, MSFT"}` |
| `data_mode=bogus` | `422` — native FastAPI enum validation (see §"data_mode is a real enum" below), not a custom error path |
| Untagged/internal routes (`/api/issuer/companies`, `/metadata`, `/`) | Present in OpenAPI but **not** tagged `agent-tool` |

## `data_mode` is a real Python enum, not a validated string

Earlier in this milestone, `data_mode` was typed as a plain `str` with a manual validation function producing a custom `invalid_data_mode` error. This was corrected before shipping to match Treasury's `TreasuryDataMode` pattern exactly: `data_mode: IssuerDataMode` is the literal parameter type. The practical effect, verified directly:

```json
{"detail": [{"type": "enum", "loc": ["query", "data_mode"], "msg": "Input should be 'fixture' or 'live'", "input": "bogus", "ctx": {"expected": "'fixture' or 'live'"}}]}
```

FastAPI/Pydantic reject an invalid value natively, and — more importantly for the agent-tool path — the `enum: ["fixture", "live"]` constraint now appears directly in `/openapi.json`, which means it's also present in the Copilot-visible generated tool schema (`scripts/generate_tool_schemas.py` derives it automatically; see `generated-tool-schemas.test.mjs`'s `get_company_facts` assertion).

## Fixture-mode result (real recorded data, not synthetic)

```json
{
  "cik": "0000320193",
  "ticker": "AAPL",
  "company_name": "Apple Inc.",
  "fiscal_year": 2025,
  "period_end": "2025-09-27",
  "revenue": {
    "value": 416161000000.0,
    "accession_number": "0000320193-25-000079",
    "source_url": "https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/0000320193-25-000079-index.htm"
  },
  "operating_margin_pct": 31.970799762591884
}
```

Every number here is genuine, publicly disclosed Apple financial data, recorded by `scripts/generate_issuer_fixtures.py` from the real SEC API and frozen for deterministic testing — not invented. The `source_url` resolves to the actual EDGAR filing index page.

## A real bug found and fixed: NVIDIA's XBRL concept migration

While verifying against companies beyond the two fixture tickers, a live call for NVIDIA returned fiscal year 2022 as the "latest" data — implausible, since NVIDIA's fiscal year ends in late January and the session's "today" was August 2026.

Root cause, confirmed by inspecting NVIDIA's raw SEC data directly: NVIDIA reported revenue under `RevenueFromContractWithCustomerExcludingAssessedTax` through FY2022 (period end `2022-01-30`), then migrated to the plain `Revenues` tag from FY2023 onward (period ends through `2026-01-25`). The original concept-selection logic picked the first candidate concept in priority order that had *any* data — since the old tag still had historical entries, it "won" and the newer `Revenues` data was never even inspected.

Fixed via `issuer_fixture._most_recent_concept`, which instead picks whichever candidate concept's annual data covers the most recent period end:

```text
AAPL concept= RevenueFromContractWithCustomerExcludingAssessedTax periods= [2021-09-25 .. 2025-09-27]
MSFT concept= RevenueFromContractWithCustomerExcludingAssessedTax periods= [2022-06-30 .. 2026-06-30]
NVDA concept= Revenues                                            periods= [2022-01-30 .. 2026-01-25]  (fixed; was locking onto the old tag through 2022-01-30 only)
```

A regression test (`test_extract_annual_periods_picks_concept_with_most_recent_data_not_first_in_priority_order`) reproduces the exact failure mode with synthetic data. The committed AAPL/MSFT fixtures were regenerated through the fixed code path; output was byte-identical, confirming no regression for the two companies that don't exhibit this issue.

## A second bug found and fixed: the tool-schema generator's string escaping

Registering this dashlet and regenerating `generated-tool-schemas.mjs` crashed with a JS syntax error. Root cause: `scripts/generate_tool_schemas.py`'s JS-literal serializer used `repr(value).replace("'", '"')` — a naive transform that corrupts any string containing a quote character. This dashlet's `data_mode` description contains `'fixture'`/`'live'` in single quotes, which the naive replace turned into unterminated JS string literals.

Fixed by replacing the entire hand-rolled serializer with `json.dumps()` (a strict subset of JS syntax, correctly escapes everything) plus a small runtime `deepFreeze()` helper embedded in the generated file. Verified the replacement still deep-freezes every nested level exactly as the existing immutability tests expect (`Object.isFrozen` checked directly on the top-level map, each schema, each schema's `properties`, each schema's `required` array, and nested property objects — not just a shallow check).

This was a real, generalizable bug in shared infrastructure (not specific to Issuer Research) that had simply never been exercised by a description string containing a quote before.

## Real, unmocked live-mode verification

Beyond the fully-mocked `httpx.Client` unit tests (required for the automated suite, per `docs/DATA_ACCESS.md` §6), a real `uvicorn` process was booted and hit with a genuine, unmocked network call against actual SEC EDGAR, for a ticker outside the fixture set:

```text
GET /api/issuer/facts?ticker=GOOGL&data_mode=live
→ company_name: "Alphabet Inc."
→ fiscal_year: 2025
→ revenue: 402836000000.0
→ provenance.source: "sec-edgar-live"
```

This is Alphabet's real, publicly disclosed FY2025 revenue, fetched live through the exact same code path the agent-tool proxy would use.

## iframe endpoint-path evidence

The dashlet's inline Alpine client fetches `./api/issuer/companies`, `./api/issuer/facts`, `./api/issuer/trends`, `./api/issuer/filings` — the identical mount-relative paths and `operationId`s used by the agent-tool proxy. Covered automatically by the generic contract test `tests/test_dashlet_contract.py::test_root_page_uses_mount_relative_fetch_paths` (this dashlet was added to `scripts/generate_tool_schemas.py`'s `DASHLET_MODULES`, requiring zero new contract-test code).

## Agent-tool endpoint-path evidence

**TODO — requires a live Canvas session.**

1. Open a Copilot session with this repository, invoke the `dashlet-studio` Canvas extension.
2. `select_dashlet(issuer-research)`, then `start_dashlet`. Confirm the iframe loads.
3. Ask Copilot each of the following, and record the tool call, arguments, and returned values:
   - *"Use the issuer research tool to get Apple's latest company facts, fixture mode."* → expect `get_company_facts(ticker="AAPL", data_mode="fixture")`, revenue ≈ $416.2B.
   - *"Use the issuer research tool to get NVIDIA's financial trends over the last 5 years, live from SEC EDGAR."* → expect `get_financial_trends(ticker="NVDA", data_mode="live", years=5)`, fiscal years through 2026.
   - *"Use the issuer research tool to list Microsoft's recent 10-K filings, fixture mode."* → expect `list_recent_filings(ticker="MSFT", data_mode="fixture", form_type="10-K")`.
4. Confirm in the Canvas runtime diagnostics log that each call shows `Proxy request: GET .../api/issuer/...` on the same host:port the iframe is pointed at.

## Tool-isolation negative tests

**TODO — requires a live Canvas session.** Same recommendation as the other two dashlets: with three dashlets now sharing this gap, one combined pass covering all of them (plus refreshing Treasury's) is more efficient than separate passes.

## Process-lifecycle results

**TODO — requires a live Canvas session.**

## Python test summary

```text
uv run pytest tests/test_issuer_fixture.py tests/test_issuer_provider.py tests/test_issuer_research_dashlet.py -q
51 passed

uv run pytest -q   # full suite
216 passed, 1 warning in 0.32s
```

## Node test summary

```text
npm test (.github/extensions/dashlet-studio): 45 passed, 0 failed
```

Includes two Issuer-Research-specific assertions in `generated-tool-schemas.test.mjs`: `get_company_facts` requires `ticker`/`data_mode` with `data_mode` as an exact `["fixture","live"]` enum (and explicitly re-asserts the literal `'fixture'`/`'live'` text survives generation intact, as a regression guard for the string-escaping bug above); `get_financial_trends`/`list_recent_filings` expose their own optional parameters correctly.

## Provenance examples (sanitized)

```json
{"source": "sec-edgar-recorded", "source_url": null, "observation_date": "2025-09-27", "data_mode": "fixture", "is_stale": true}
{"source": "sec-edgar-live", "source_url": "https://data.sec.gov/api/xbrl/companyfacts/CIK0001652044.json", "observation_date": "2025-12-31", "data_mode": "live", "is_stale": false}
```

`is_stale` is `true` for every fixture-mode response by convention (a frozen recorded snapshot is inherently potentially behind live SEC data) and `false` for live mode.

## Known limitations

- **No live Canvas verification yet** (agent-tool endpoint-path evidence, tool-isolation negative tests, process-lifecycle results, and a Canvas-embedded screenshot are all TODO above), and **no standalone browser screenshot yet either** — deliberately deferred alongside the same gap for Portfolio Exposure and Portfolio Scenario Impact.
- SEC's ~10,388 registered filers use heterogeneous, sometimes-migrating XBRL tagging (see the NVIDIA bug above). This dashlet tries a short, ordered list of known revenue concept tags and picks whichever covers the most recent period — a ticker using an entirely different, unlisted concept, or with no XBRL history at all, returns a controlled `missing_financial_data` error, not partial/best-effort data.
- Leverage ratio (`total_liabilities / stockholders_equity`) is a simplified proxy, not a regulatory or bank-style leverage ratio — appropriate for a general research dashlet, not for financial-institution-specific analysis.
- The Canvas `ToolProxy`'s 5-second request timeout (already flagged as a Treasury EOD risk) has not been specifically measured against live SEC EDGAR calls through the Canvas tool proxy — only verified via direct FastAPI/uvicorn, which has no such timeout.
- Independent code review has not yet been completed for this dashlet (see `docs/PROGRESS.md` Milestone 4 evidence) — implemented directly by Claude Code this session, review still open, same as the other two.

## Related documents

- [`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) — component boundaries and dual-use business-operation contract.
- [`docs/DASHLET_CONTRACT.md`](../DASHLET_CONTRACT.md), [`docs/DATA_ACCESS.md`](../DATA_ACCESS.md), [`docs/WEB_AUTHORING.md`](../WEB_AUTHORING.md), [`docs/TOOL_AUTHORING.md`](../TOOL_AUTHORING.md) — the contract this dashlet was built against.
- [`docs/PROGRESS.md`](../PROGRESS.md) — Milestone 4 checklist and evidence, including the open independent-review item.
- [`docs/evidence/portfolio-scenario-reference.md`](portfolio-scenario-reference.md) — the previous dashlet's evidence doc, and the template this one follows.
