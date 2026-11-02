import json
from pathlib import Path
import tempfile

import pytest
from fastapi.testclient import TestClient

from netspout_core.catalog import NetSpoutCatalog
from netspout_core.industry_packs import (
    EvidenceClassification,
    IndustryPack,
    IndustrySelection,
)
from netspout_core.scenario_studio import ScenarioStudioService
from netspout_core.unified_generation import UnifiedGenerationService


ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {"financial-services", "healthcare", "manufacturing"}


@pytest.fixture(scope="module")
def catalog():
    return NetSpoutCatalog(str(ROOT / "catalog"))


@pytest.fixture(scope="module")
def industry_service(catalog):
    return catalog.get_industry_pack_service()


def test_registry_has_exactly_three_real_industries(industry_service):
    assert {item.industry_id for item in industry_service.registry.industries} == EXPECTED
    assert all(item.environments for item in industry_service.registry.industries)
    assert all(item.business_capabilities for item in industry_service.registry.industries)


def test_industry_packs_are_discoverable_pack_definitions(catalog):
    registry = catalog.get_extension_pack_registry()
    industry_packs = [item for item in registry["packs"] if item["kind"] == "INDUSTRY"]
    assert {item["pack_id"] for item in industry_packs} == {
        "industry-financial-services",
        "industry-healthcare",
        "industry-manufacturing",
    }


@pytest.mark.parametrize("industry_id", sorted(EXPECTED))
def test_each_reference_is_runnable_and_splunk_validated(industry_service, industry_id):
    industry = industry_service.get(industry_id)
    environment = industry.environments[0]
    result = industry_service.compose(
        IndustrySelection(
            industry_id=industry_id,
            environment_id=environment.environment_id,
            seed=1010,
        )
    )
    assert result["scenario_id"] == environment.default_scenario_id
    assert result["source_ids"] == environment.telemetry_source_ids
    assert industry.maturity == "SPLUNK_VALIDATED"
    assert result["generation_request"]["scenario_parameters"]["seed"] == 1010


def test_dependency_propagation_is_deterministic(industry_service):
    first = industry_service.propagate(
        "financial-services",
        "financial-retail-branch",
        ["financial-device-branch-edge"],
    )
    second = industry_service.propagate(
        "financial-services",
        "financial-retail-branch",
        ["financial-device-branch-edge"],
    )
    assert first == second
    assert first["propagated_entity_ids"] == [
        "financial-app-payment-service",
        "financial-capability-payments",
        "financial-device-branch-edge",
        "financial-network-wan",
    ]


@pytest.mark.parametrize("industry_id", sorted(EXPECTED))
def test_business_impact_is_never_observed(industry_service, industry_id):
    industry = industry_service.get(industry_id)
    assert all(
        item.classification in {
            EvidenceClassification.MODELED,
            EvidenceClassification.INFERRED,
            EvidenceClassification.NOT_ESTABLISHED,
        }
        for item in industry.business_impacts
    )
    assert all(item.assumptions for item in industry.business_impacts)


def test_observed_technical_and_modeled_business_evidence_are_separate(industry_service):
    result = industry_service.compose(
        IndustrySelection(
            industry_id="healthcare",
            environment_id="healthcare-hospital-campus",
        )
    )
    assert result["technical_evidence_classification"] == "NOT_ESTABLISHED"
    assert result["business_impact_classification"] == "MODELED"
    assert result["impact_preview"]["business_impacts"]
    assert all(
        item["classification"] == "MODELED"
        for item in result["impact_preview"]["business_impacts"]
    )


def test_invalid_scenario_combination_fails_closed(industry_service):
    with pytest.raises(ValueError, match="not compatible"):
        industry_service.compose(
            IndustrySelection(
                industry_id="manufacturing",
                environment_id="manufacturing-factory-boundary",
                scenario_id="SEC-P9-E-DNS-TUNNEL",
            )
        )


def test_unsupported_modeled_telemetry_parameter_fails_closed(industry_service):
    with pytest.raises(ValueError, match="unsupported modeled parameter"):
        industry_service.compose(
            IndustrySelection(
                industry_id="manufacturing",
                environment_id="manufacturing-factory-boundary",
                modeled_parameters={"industrial_protocol": "modbus"},
            )
        )


def test_modeled_parameters_cannot_change_native_scenario_contract(industry_service):
    result = industry_service.compose(
        IndustrySelection(
            industry_id="financial-services",
            environment_id="financial-retail-branch",
            modeled_parameters={
                "affected_entity_ids": ["financial-device-branch-edge"],
                "impact_assumptions": ["No alternate path is instrumented."],
            },
        )
    )
    assert result["generation_request"]["scenario_parameters"] == {"seed": 1010}
    assert result["impact_preview"]["business_impacts"]


def test_unknown_affected_entity_fails_closed(industry_service):
    with pytest.raises(ValueError, match="unknown affected entity"):
        industry_service.propagate(
            "healthcare",
            "healthcare-hospital-campus",
            ["real-patient-device"],
        )


def test_graph_cycle_is_rejected(industry_service):
    payload = industry_service.get("healthcare").model_dump(mode="json")
    payload["dependencies"].append(
        {
            "dependency_id": "bad-cycle",
            "source_entity_id": "healthcare-capability-clinical-access",
            "target_entity_id": "healthcare-device-campus-edge",
            "relationship_type": "INVALID",
            "criticality": "HIGH",
            "assumption": "Test-only invalid cycle.",
        }
    )
    with pytest.raises(ValueError, match="cycle"):
        IndustryPack.model_validate(payload)


def test_no_sensitive_or_unsupported_industry_telemetry(industry_service):
    serialized = json.dumps(industry_service.catalog()).lower()
    assert "cardholder" in serialized
    assert "no patient" in serialized
    assert "no plc" in serialized
    forbidden_sources = {"plc", "modbus", "patient", "payment-transaction"}
    source_ids = {
        item.source_id
        for industry in industry_service.registry.industries
        for item in industry.telemetry_requirements
    }
    assert not source_ids.intersection(forbidden_sources)


def test_future_categories_are_not_registered_as_supported(industry_service):
    result = industry_service.catalog()
    assert "Retail" in result["future_categories"]
    assert len(result["industries"]) == 3


def test_industry_clone_preserves_contracts_and_context(catalog, industry_service):
    generation = UnifiedGenerationService(catalog=catalog)
    with tempfile.TemporaryDirectory() as directory:
        studio = ScenarioStudioService(
            catalog=catalog,
            generation_service=generation,
            storage_dir=directory,
        )
        composition = industry_service.compose(
            IndustrySelection(
                industry_id="manufacturing",
                environment_id="manufacturing-factory-boundary",
            )
        )
        draft = studio.clone_scenario(composition["scenario_id"])
        draft.industry_id = "manufacturing"
        draft.industry_environment_id = "manufacturing-factory-boundary"
        draft.business_impact_assumptions = ["No alternate path is instrumented."]
        fingerprints = dict(draft.contract_fingerprints)
        saved = studio.save_pack(draft)
        reloaded = studio.get_pack(saved.pack_id)
        assert reloaded.industry_id == "manufacturing"
        assert reloaded.industry_environment_id == "manufacturing-factory-boundary"
        assert reloaded.contract_fingerprints == fingerprints
        assert studio.validate_pack(reloaded).valid


def test_api_catalog_compose_and_studio_clone():
    from backend.app.main import app

    client = TestClient(app)
    response = client.get("/api/industries")
    assert response.status_code == 200
    assert len(response.json()["industries"]) == 3

    selection = {
        "industry_id": "financial-services",
        "environment_id": "financial-retail-branch",
        "seed": 1010,
        "modeled_parameters": {},
    }
    response = client.post("/api/industries/compose", json=selection)
    assert response.status_code == 200
    assert response.json()["scenario_id"] == "C100-CRI-002"

    response = client.post(
        "/api/industries/financial-services/studio-draft",
        json={
            **selection,
            "modeled_parameters": {
                "impact_assumptions": [
                    "A reviewed alternate-path assumption for this private clone."
                ]
            },
        },
    )
    assert response.status_code == 200
    assert response.json()["industry_id"] == "financial-services"
    assert response.json()["definition_only"] is False
    assert (
        "A reviewed alternate-path assumption for this private clone."
        in response.json()["business_impact_assumptions"]
    )


def test_api_rejects_unsupported_industrial_combination():
    from backend.app.main import app

    client = TestClient(app)
    response = client.post(
        "/api/industries/compose",
        json={
            "industry_id": "manufacturing",
            "environment_id": "manufacturing-factory-boundary",
            "scenario_id": "SEC-P9-E-DNS-TUNNEL",
            "modeled_parameters": {"industrial_protocol": "unsupported"},
        },
    )
    assert response.status_code == 409
    assert "not compatible" in response.json()["detail"]
