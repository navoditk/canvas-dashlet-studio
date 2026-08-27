import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gallery import GALLERY_APPS, app
from scripts.generate_tool_schemas import DASHLET_MODULES, _load_app

client = TestClient(app)


def test_gallery_mounts_exactly_the_same_apps_as_dashlet_modules() -> None:
    # This is the automated, continuously-enforced version of Milestone 5's
    # "Gallery mounts every validated dashlet" checklist item -- if a
    # dashlet is added to scripts/generate_tool_schemas.py's DASHLET_MODULES
    # (which every registered dashlet already must be, for contract
    # validation and tool-schema generation) without also adding it to
    # gallery.py's GALLERY_APPS, this test fails instead of the gallery
    # silently omitting it.
    expected_apps = {id(_load_app(module_target)) for module_target in DASHLET_MODULES}
    mounted_apps = {id(sub_app) for _display_name, sub_app in GALLERY_APPS.values()}
    assert mounted_apps == expected_apps


def test_gallery_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_gallery_index_lists_every_mounted_dashlet() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    html = response.text
    for dashlet_id in GALLERY_APPS:
        assert f'href="/apps/{dashlet_id}/"' in html


def test_every_mounted_dashlet_health_is_reachable() -> None:
    for dashlet_id in GALLERY_APPS:
        response = client.get(f"/apps/{dashlet_id}/health")
        assert response.status_code == 200, dashlet_id
        assert response.json() == {"status": "ready"}, dashlet_id


def test_every_mounted_dashlet_root_returns_html() -> None:
    for dashlet_id in GALLERY_APPS:
        response = client.get(f"/apps/{dashlet_id}/")
        assert response.status_code == 200, dashlet_id
        assert "text/html" in response.headers["content-type"], dashlet_id


def test_mounted_dashlet_without_trailing_slash_redirects() -> None:
    response = client.get("/apps/treasury-curve", follow_redirects=False)
    assert response.status_code in (307, 308)
    assert response.headers["location"] == "http://testserver/apps/treasury-curve/"


def test_mounted_treasury_curve_data_endpoint_matches_standalone_values() -> None:
    response = client.get("/apps/treasury-curve/api/treasury/curve", params={"data_mode": "fixture"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["provenance"]["source"] == "synthetic-fixture"
    assert len(payload["points"]) > 0


def test_mounted_portfolio_exposure_data_endpoint_matches_standalone_values() -> None:
    response = client.get("/apps/portfolio-exposure/api/portfolio/exposures")
    assert response.status_code == 200
    assert response.json()["totals"]["net_market_value"] == 10_650_000.0


def test_mounted_portfolio_scenario_data_endpoint_matches_standalone_values() -> None:
    response = client.get("/apps/portfolio-scenario/api/scenario/run", params={"equity_shock_pct": 10.0})
    assert response.status_code == 200
    assert response.json()["totals"]["total_impact"] == 1_154_000.0


def test_mounted_issuer_research_data_endpoint_matches_standalone_values() -> None:
    response = client.get("/apps/issuer-research/api/issuer/facts", params={"ticker": "AAPL", "data_mode": "fixture"})
    assert response.status_code == 200
    assert response.json()["revenue"]["value"] == 416_161_000_000.0


def test_mounted_dashlet_uses_relative_fetch_that_resolves_under_its_mount() -> None:
    # The whole point of the mount-relative fetch("./api/...") convention
    # (docs/WEB_AUTHORING.md §3): the same, unmodified HTML must resolve its
    # own fetch calls correctly regardless of whether it's served standalone
    # at "/" or mounted here under "/apps/<id>/".
    html = client.get("/apps/treasury-curve/").text
    assert 'fetch("./api/treasury/fixture-dates")' in html
    assert 'fetch("/' not in html
