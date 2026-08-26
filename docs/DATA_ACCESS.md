# Data Access Patterns

How a dashlet should source, normalize and expose data. See `dashlets/treasury_provider.py` and `treasury_fixture.py` for the reference implementation this document describes.

## 1. Provider pattern

Data access lives in a separate `_provider.py`-style module (or, for fixture-only dashlets, a `_fixture.py` module), not inline in the dashlet's route handlers. A provider's job is narrow: given a request for data, return a typed response with provenance, or raise a `ProviderError` with a stable `error_code`.

```python
class ProviderError(Exception):
    def __init__(self, error_code: str, message: str) -> None:
        self.error_code = error_code
        self.message = message
```

The dashlet file maps `ProviderError.error_code` to an HTTP status via a small dict (see `_PROVIDER_STATUS_MAP` in `treasury_curve_dashlet.py`) and re-raises as `HTTPException`. Keep this mapping colocated with the dashlet, not the provider — the provider doesn't know about HTTP.

## 2. Fixture-first development

Build and test the fixture path before adding any live/network data source:

1. Write deterministic fixture data (JSON files under `fixtures/<dashlet-name>/`, or embedded Python constants for simple cases).
2. Write a `Fixture<X>Provider` that reads only from fixtures — no network calls, ever.
3. Get the dashlet fully working and tested against fixtures.
4. Only then, if the dashlet needs live/EOD data, add a second provider (e.g. `Public<X>Provider`) and an explicit mode parameter to select between them (see `docs/DASHLET_CONTRACT.md` §6).

This ordering isn't a style preference — it's what makes a dashlet reviewable and testable in CI without any external dependency, and it's how the Treasury reference dashlet was actually built (`docs/ROADMAP.md` Day 1 Block 4: "Use a recorded fixture first. Add official live/EOD retrieval only after the fixture path works.").

## 3. Fixture file conventions

Follow the Treasury pattern in `fixtures/treasury/curve_2026-08-19.json`:

- One file per logical snapshot (e.g. one observation date), named so the date/identity is visible in the filename.
- A `fixture_meta` block noting `data_mode` and a human-readable note that this is not live data.
- Validate on load with a Pydantic model (`TreasuryCurveFixture` in `treasury_fixture.py`) — reject malformed or duplicate-keyed fixtures at load time, not silently at read time.

## 4. Provenance is not optional

Every provider method that returns data constructs a `dashlet_framework.Provenance` (see `docs/DASHLET_CONTRACT.md` §5). A provider that can't determine `source`, `observation_date`, or `retrieved_at` should raise a `ProviderError`, not return a response with a guessed or empty provenance field.

`is_stale` means "this is not the most recent available observation," not "this data might be wrong." Compute it by comparing against the latest known observation (see `_curve_response_with_freshness` in `treasury_curve_dashlet.py`), don't hardcode `False`.

## 5. Network access rules

If a provider makes a real HTTP call (e.g. `PublicTreasuryProvider` fetching from Treasury.gov):

- Use `httpx` with an explicit timeout — no unbounded requests.
- The target URL must come from a fixed, reviewed constant in the provider module, never from a request parameter. Dashlets must not accept arbitrary external URLs (`AGENTS.md` §7).
- Map every failure mode explicitly: HTTP error status, timeout, unparseable response, and "the requested date isn't in the response" are each their own `error_code` (see `feed_http_error`, `feed_timeout`, `feed_parse_error`, `date_not_in_feed` in `treasury_provider.py`). Don't collapse them into one generic "fetch failed."
- Never retry into a fixture as a fallback. See `docs/DASHLET_CONTRACT.md` §6 — a failed live fetch is a failed request, not a reason to quietly substitute fixture data.

## 6. Testing providers

Provider tests (`tests/test_<name>_provider.py`) should cover, independent of any HTTP framework:

- Fixture provider: known-good date returns correct provenance and points; unknown date raises `fixture_not_found`.
- Live provider parsing logic: feed parsing tested against a recorded sample response (`SAMPLE_XML` pattern in `tests/test_treasury_provider.py`), not a real network call.
- Live provider HTTP error handling: mock the HTTP client (`unittest.mock.patch`) to simulate timeouts, non-200 responses, and malformed bodies — assert the correct `error_code` for each, without ever making a real request in the test suite.
