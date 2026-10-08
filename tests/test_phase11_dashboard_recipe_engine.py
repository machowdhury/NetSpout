import copy
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch
import urllib.error

import pytest
from fastapi.testclient import TestClient

from netspout_core.catalog import NetSpoutCatalog
from netspout_core.dashboard_recipes import (
    DashboardMaturity,
    DashboardRecipeRegistry,
    DashboardRecipeService,
)
from netspout_core.cisco_scenario_factory import CiscoScenarioFactoryService
from netspout_core.gnmi.splunk_e2e import GnmiSplunkBridge


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
GOLDEN = {
    "C100-ENT-001",
    "C100-SP-001",
    "C100-DC-001",
    "C100-SEC-001",
    "C100-CRI-002",
}
SECURITY = {
    "SEC-P9-A-TRAFFIC-FLOOD",
    "SEC-P9-B-DNS-ANOMALY",
    "SEC-P9-C-BEACONING",
    "SEC-P9-D-INTERNAL-RECON",
    "SEC-P9-E-DNS-TUNNEL",
    "SEC-P9-F-CROSS-SOURCE",
}
INDUSTRIES = {
    "financial-services",
    "healthcare",
    "manufacturing",
}


@pytest.fixture()
def service():
    catalog = NetSpoutCatalog(str(ROOT / "catalog"))
    with tempfile.TemporaryDirectory() as directory:
        specification = catalog.get_dashboard_recipe_service().registry.model_dump(
            mode="json"
        )
        yield DashboardRecipeService(
            specification,
            catalog,
            catalog._extension_packs,
            catalog._industry_registry,
            CiscoScenarioFactoryService().catalog.scenarios,
            evidence_dir=directory,
        )


def test_registry_has_reusable_recipe_and_visualization_depth(service):
    assert 15 <= len(service.registry.recipes) <= 25
    assert len(service.registry.recipes) == 19
    assert len(service.registry.visualizations) == 11
    assert len({item.family for item in service.registry.recipes}) >= 12


def test_generic_eligibility_discovers_all_required_references(service):
    catalog = service.catalog_summary()
    assert len(catalog["dashboards"]) == 16
    assert catalog["eligible_count"] == 14
    eligible = [item for item in catalog["dashboards"] if item["state"] == "ELIGIBLE"]
    assert GOLDEN <= {item["scenario_id"] for item in eligible}
    assert SECURITY <= {item["scenario_id"] for item in eligible}
    assert INDUSTRIES == {
        item["industry_id"] for item in eligible if item["industry_id"]
    }


def test_immature_scenarios_have_honest_research_status(service):
    result = service.eligibility("scenario-rfc5424-link-state-lifecycle")
    assert result.state.value == "RESEARCH_REQUIRED"
    assert any("maturity" in reason for reason in result.reasons)
    with pytest.raises(ValueError, match="not eligible"):
        service.generate("scenario-rfc5424-link-state-lifecycle")


def test_cisco_service_provider_uses_authoritative_runtime_mapping(service):
    result = service.eligibility("scenario-c100-sp-001")
    assert result.scenario_id == "C100-SP-001"
    assert result.runtime_scenario_id == "test-correlated-interface-degradation"
    assert result.scenario_maturity == "GOLDEN"


def test_dashboard_pack_references_contracts_and_shared_graph(service):
    pack = service.generate(
        "scenario-c100-cri-002",
        run_id="phase11-run-cri-001",
    )
    assert pack.entity_graph["shared_with_scenario"] is True
    assert pack.entity_graph["nodes"]
    assert pack.entity_graph["relationships"]
    assert len(pack.source_contracts) == 2
    assert len(pack.splunk_contracts) == 2
    assert pack.investigation_recipe_ids
    assert pack.cim_status == "NOT_ESTABLISHED"
    assert pack.maturity == DashboardMaturity.GENERATED


def test_every_executable_panel_is_bounded_and_run_scoped(service):
    pack = service.generate(
        "scenario-sec-p9-f-cross-source",
        run_id="phase11-run-security-001",
    )
    executable = [item for item in pack.panels if item.executable]
    assert executable
    for panel in executable:
        assert 'netspout_run_id="phase11-run-security-001"' in panel.query
        assert "earliest=-15m" in panel.query
        assert "latest=now" in panel.query
        assert "| join" not in panel.query.lower()


def test_recipe_schema_rejects_unbounded_spl(service):
    payload = service.registry.model_dump(mode="json")
    payload["recipes"][0]["query_template"] = (
        'search index="{index}" {sourcetype_filter} '
        'netspout_run_id="{run_id}" | stats count'
    )
    with pytest.raises(ValueError, match="bounded time range"):
        DashboardRecipeRegistry.model_validate(payload)


def test_optional_visualization_dependency_falls_back(service):
    recipe = copy.deepcopy(service.registry.recipes[0])
    recipe.visualization_ids = ["network-diagram-viz"]
    result = service._resolve_visualization(recipe)
    assert result["requested"] == "network-diagram-viz"
    assert result["selected"] == "splunk-table"
    assert result["state"] == "FALLBACK:NOT_VERIFIED"


def test_data_validation_is_independent_from_scenario_maturity(service):
    pack = service.generate(
        "scenario-c100-ent-001",
        run_id="phase11-run-ent-001",
    )
    panel_results = {}
    for panel in pack.panels:
        if panel.executable:
            panel_results[panel.panel_id] = [
                {field: "1" for field in panel.expected_shape}
            ]
    result = service.validate(pack, panel_results, evidence_refs=["test:evidence"])
    assert result.maturity == DashboardMaturity.DATA_VALIDATED
    assert result.spl_validated is True
    assert result.data_validated is True
    assert service.eligibility(pack.dashboard_id).scenario_maturity == "GOLDEN"
    regenerated = service.generate(pack.dashboard_id, run_id=pack.run_id)
    assert regenerated.maturity == DashboardMaturity.DATA_VALIDATED


def test_shape_failure_is_recorded_without_promoting_dashboard(service):
    pack = service.generate(
        "scenario-sec-p9-b-dns-anomaly",
        run_id="phase11-run-dns-001",
    )
    panel_results = {
        panel.panel_id: [{}]
        for panel in pack.panels
        if panel.executable
    }
    result = service.validate(pack, panel_results)
    assert result.maturity == DashboardMaturity.SPL_VALIDATED
    assert result.data_validated is False
    assert result.failures


def test_visual_validation_requires_data_validation(service):
    with pytest.raises(ValueError, match="data validation"):
        service.mark_visual_validation(
            "scenario-c100-ent-001",
            "missing-run",
            "screenshot:missing",
            export_validated=True,
        )


def test_export_adapter_produces_valid_dashboard_studio_json(service):
    pack = service.generate(
        "scenario-c100-dc-001",
        run_id="phase11-run-dc-001",
    )
    result = service.export_dashboard_studio(pack)
    definition = result["definition"]
    assert result["format"] == "SPLUNK_DASHBOARD_STUDIO_JSON"
    assert result["validation"]["valid"] is True
    assert set(definition) == {
        "title",
        "description",
        "inputs",
        "defaults",
        "visualizations",
        "dataSources",
        "layout",
        "expressions",
        "applicationProperties",
    }
    assert result["deployment"]["deployment_status"] == "PREVIEW_ONLY"
    assert result["deployment"]["overwrite_allowed"] is False
    assert all(
        item["type"].startswith("splunk.")
        for item in definition["visualizations"].values()
    )


def test_drilldowns_use_stable_declared_tokens(service):
    allowed = {
        "source",
        "phase",
        "entity",
        "relationship",
        "investigation",
        "business_capability",
    }
    for recipe in service.registry.recipes:
        for drilldown in recipe.drilldowns:
            assert drilldown.token in allowed
            assert drilldown.field
            assert drilldown.semantics


@pytest.mark.parametrize(
    "industry_id",
    sorted(INDUSTRIES),
)
def test_industry_dashboards_add_modeled_business_recipe(service, industry_id):
    pack = service.generate("industry-{}".format(industry_id), run_id="industry-run")
    assert pack.industry_id == industry_id
    assert any(
        item.recipe_id == "dashboard-business-dependency-impact"
        for item in pack.panels
    )
    assert any("MODELED_IMPACT" in item.evidence_requirements for item in pack.panels)


def test_api_catalog_pack_export_and_run_binding():
    from app.main import app

    client = TestClient(app)
    response = client.get("/api/dashboards")
    assert response.status_code == 200
    assert response.json()["eligible_count"] == 14

    response = client.get(
        "/api/dashboards/scenario-c100-ent-001",
        params={"run_id": "phase11-api-run"},
    )
    assert response.status_code == 200
    assert response.json()["scenario_id"] == "C100-ENT-001"

    response = client.get(
        "/api/dashboards/scenario-c100-ent-001/export",
        params={"run_id": "phase11-api-run"},
    )
    assert response.status_code == 200
    assert response.json()["validation"]["valid"] is True

    response = client.get("/api/dashboards/scenario-c100-ent-001/export")
    assert response.status_code == 200
    assert response.json()["deployment"]["deployment_status"] == "PREVIEW_ONLY"

    response = client.post(
        "/api/dashboards/scenario-c100-ent-001/validate",
        json={"run_id": "missing-run"},
    )
    assert response.status_code == 404


def test_gate13e_hec_readiness_retries_connection_refusal_with_bounds():
    class ReadyResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self, _size):
            return b'{"text":"HEC is healthy","code":17}'

    attempts = [
        urllib.error.URLError(ConnectionRefusedError()),
        urllib.error.URLError(ConnectionRefusedError()),
        ReadyResponse(),
    ]
    bridge = GnmiSplunkBridge(readiness_timeout_sec=1.0)
    with patch(
        "netspout_core.gnmi.splunk_e2e.urllib.request.urlopen",
        side_effect=attempts,
    ):
        result = bridge.wait_for_hec_ready()
    assert result["ready"] is True
    assert result["attempts"] == 3
    assert result["elapsed_ms"] <= 1000
