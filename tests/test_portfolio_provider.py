import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dashlets.portfolio_provider import FixturePortfolioProvider, ProviderError

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "fixtures" / "portfolio"


def test_list_available_dates_sorted() -> None:
    provider = FixturePortfolioProvider(FIXTURE_DIR)
    assert provider.list_available_dates() == ["2026-08-18", "2026-08-19"]


def test_get_exposures_for_known_date() -> None:
    provider = FixturePortfolioProvider(FIXTURE_DIR)
    result = provider.get_exposures("2026-08-19")
    assert result.provenance.data_mode == "fixture"
    assert result.provenance.source == "synthetic-fixture"
    assert result.provenance.is_stale is False


def test_get_exposures_for_older_date_is_marked_stale() -> None:
    provider = FixturePortfolioProvider(FIXTURE_DIR)
    result = provider.get_exposures("2026-08-18")
    assert result.provenance.is_stale is True


def test_get_exposures_raises_for_missing_date() -> None:
    provider = FixturePortfolioProvider(FIXTURE_DIR)
    with pytest.raises(ProviderError) as exc_info:
        provider.get_exposures("2099-01-01")
    assert exc_info.value.error_code == "fixture_not_found"


def test_get_exposures_provenance_fields_are_complete() -> None:
    provider = FixturePortfolioProvider(FIXTURE_DIR)
    result = provider.get_exposures("2026-08-19")
    p = result.provenance
    assert p.observation_date.isoformat() == "2026-08-19"
    assert p.retrieved_at is not None and p.retrieved_at.tzinfo is not None
    assert p.source_url is None


def test_get_exposures_totals_match_known_fixture_values() -> None:
    provider = FixturePortfolioProvider(FIXTURE_DIR)
    result = provider.get_exposures("2026-08-19")
    assert result.totals.long_market_value == pytest.approx(11_400_000.0)
    assert result.totals.short_market_value == pytest.approx(750_000.0)
    assert result.totals.net_market_value == pytest.approx(10_650_000.0)
    assert result.totals.gross_market_value == pytest.approx(12_150_000.0)


def test_get_exposures_sector_and_issuer_counts() -> None:
    provider = FixturePortfolioProvider(FIXTURE_DIR)
    result = provider.get_exposures("2026-08-19")
    assert len(result.sector_exposures) == 5
    assert len(result.issuer_exposures) == 12


def test_invalid_fixture_raises_provider_error(tmp_path) -> None:
    (tmp_path / "positions_2030-01-01.json").write_text(
        """
        {
          "fixture_meta": {"note": "bad", "data_mode": "fixture"},
          "observation_date": "2030-01-01",
          "positions": []
        }
        """
    )
    provider = FixturePortfolioProvider(tmp_path)
    with pytest.raises(ProviderError) as exc_info:
        provider.get_exposures("2030-01-01")
    assert exc_info.value.error_code == "invalid_fixture"
