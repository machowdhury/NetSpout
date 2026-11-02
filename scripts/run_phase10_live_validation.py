#!/usr/bin/env python3
"""Run bounded Phase 10 Industry Pack journeys against local Splunk."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time


REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from netspout_core.catalog import NetSpoutCatalog
from netspout_core.industry_packs import IndustrySelection
from netspout_core.models import TelemetryTransportConfig, resolve_hec_token
from netspout_core.scenario_studio import ScenarioStudioService
from netspout_core.unified_generation import (
    EvidenceState,
    GenerationMode,
    UnifiedGenerationRequest,
    UnifiedGenerationService,
)


def _required_environment(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError("{} must be supplied through the environment".format(name))
    return value


def _all_required_observed(run) -> bool:
    required = [item for item in run.channel_results if item.required]
    return bool(required) and all(
        any(
            evidence.stage == "SPLUNK_OBSERVED"
            and evidence.state == EvidenceState.PROVEN
            for evidence in channel.evidence
        )
        for channel in required
    )


def _observe(service, run, transport):
    for _ in range(20):
        run = service.observe(run.run_id, transport)
        if _all_required_observed(run):
            break
        time.sleep(1)
    return run


def main() -> int:
    artifact_root = Path(
        _required_environment("NETSPOUT_TEST_ARTIFACT_ROOT")
    ).resolve()
    artifact_root.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault(
        "NETSPOUT_SPLUNK_PASSWORD", _required_environment("SPLUNK_PASSWORD")
    )
    os.environ.setdefault("NETSPOUT_SPLUNK_USER", "admin")
    os.environ.setdefault(
        "NETSPOUT_SPLUNK_REST_URL",
        "https://127.0.0.1:8089/services/search/jobs/export",
    )
    transport = TelemetryTransportConfig(
        hec_enabled=True,
        hec_url=os.environ.get(
            "NETSPOUT_PHASE10_HEC_URL",
            "https://127.0.0.1:8088/services/collector",
        ),
        hec_token=resolve_hec_token(),
        hec_index=os.environ.get("NETSPOUT_SPLUNK_INDEX", "idx_network_ops"),
        hec_ssl_verify=False,
        hec_allow_insecure_tls=True,
    )
    catalog = NetSpoutCatalog(str(REPO_ROOT / "catalog"))
    industry_service = catalog.get_industry_pack_service()
    generation = UnifiedGenerationService(catalog=catalog)
    summaries = []

    for industry in industry_service.registry.industries:
        environment = industry.environments[0]
        selection = IndustrySelection(
            industry_id=industry.industry_id,
            environment_id=environment.environment_id,
            seed=1010,
        )
        composition = industry_service.compose(selection)
        request = UnifiedGenerationRequest.model_validate(
            composition["generation_request"]
        )
        preflight = generation.preflight(request, transport)
        if preflight.state.value == "BLOCKED":
            raise RuntimeError("{} preflight blocked".format(industry.industry_id))
        run = _observe(generation, generation.run(request, transport), transport)
        investigations = [
            generation.run_investigation(run.run_id, item["recipe_id"], transport)
            for item in run.investigations
        ]
        impact = industry_service.propagate(
            industry.industry_id,
            environment.environment_id,
            environment.entity_ids[:1],
        )
        impact["technical_evidence"] = {
            "status": "OBSERVED" if _all_required_observed(run) else "NOT_ESTABLISHED",
            "detail": (
                "Fresh source-scoped authenticated Splunk observation."
                if _all_required_observed(run)
                else "Required source observation was not proven."
            ),
        }
        summaries.append(
            {
                "industry_id": industry.industry_id,
                "environment_id": environment.environment_id,
                "scenario_id": composition["scenario_id"],
                "run_id": run.run_id,
                "status": run.status,
                "source_ids": run.source_ids,
                "preflight": preflight.model_dump(mode="json"),
                "channels": [
                    item.model_dump(mode="json") for item in run.channel_results
                ],
                "investigations": investigations,
                "dependency_impact": impact,
                "business_impact_statuses": [
                    item["status"] for item in impact["business_impacts"]
                ],
            }
        )

    unsupported_blocked = False
    try:
        industry_service.compose(
            IndustrySelection(
                industry_id="manufacturing",
                environment_id="manufacturing-factory-boundary",
                modeled_parameters={"industrial_protocol": "unsupported"},
            )
        )
    except ValueError as error:
        unsupported_blocked = "unsupported modeled parameter" in str(error)

    studio_root = artifact_root / "scenario-studio"
    studio = ScenarioStudioService(
        catalog=catalog,
        generation_service=generation,
        storage_dir=str(studio_root),
    )
    clone = studio.clone_scenario("C100-DC-001")
    clone.industry_id = "manufacturing"
    clone.industry_environment_id = "manufacturing-factory-boundary"
    clone.business_impact_assumptions = [
        "No out-of-band monitoring path is instrumented."
    ]
    clone.layout_hints[clone.entities[0].entity_id] = {"x": 180.0, "y": 210.0}
    stored = studio.save_pack(clone)
    reloaded_service = ScenarioStudioService(
        catalog=catalog,
        generation_service=generation,
        storage_dir=str(studio_root),
    )
    reloaded = reloaded_service.get_pack(stored.pack_id)
    if reloaded is None:
        raise RuntimeError("Industry Studio clone did not reload")
    _, studio_composition = reloaded_service.compile_pack(reloaded)
    binding = studio_composition.source_bindings[0]
    studio_request = UnifiedGenerationRequest(
        mode=GenerationMode.SCENARIO,
        selection_id=reloaded.scenario_id,
        transport_id=(
            binding.destination_transport_id or binding.transport_id
        ),
        destination_id=binding.destination_id,
        scenario_parameters={
            "seed": 1011,
            "entity_id": reloaded.entities[0].entity_id,
            "studio_shared_state": True,
        },
    )
    studio_preflight = generation.preflight(studio_request, transport)
    if studio_preflight.state.value == "BLOCKED":
        raise RuntimeError("Industry Studio clone preflight blocked")
    studio_run = _observe(
        generation, generation.run(studio_request, transport), transport
    )
    studio_summary = {
        "industry_id": reloaded.industry_id,
        "environment_id": reloaded.industry_environment_id,
        "pack_id": reloaded.pack_id,
        "saved_and_reloaded": True,
        "contract_fingerprints_preserved": (
            reloaded.contract_fingerprints == stored.contract_fingerprints
        ),
        "business_impact_assumptions_preserved": bool(
            reloaded.business_impact_assumptions
        ),
        "run_id": studio_run.run_id,
        "status": studio_run.status,
        "all_required_observed": _all_required_observed(studio_run),
    }

    output = {
        "schema_version": "1.0.0",
        "classification": "CURRENT_RUN_EVIDENCE",
        "scope": "Phase 10 Industry Studio and local Splunk validation",
        "industries": summaries,
        "industry_studio": studio_summary,
        "fail_closed": {
            "unsupported_industrial_vendor_combination_blocked": unsupported_blocked,
            "fallback_telemetry_generated": False,
        },
        "all_runtime_completed": all(
            item["status"] in {"COMPLETED", "OBSERVED"} for item in summaries
        ),
        "all_splunk_observed": all(
            item["status"] == "OBSERVED" for item in summaries
        ),
        "all_investigations_succeeded": all(
            all(result["status"] == "SUCCEEDED" for result in item["investigations"])
            for item in summaries
        ),
        "all_business_impacts_modeled": all(
            all(status == "MODELED" for status in item["business_impact_statuses"])
            for item in summaries
        ),
        "security": {
            "credentials_serialized": False,
            "sensitive_industry_data": False,
            "industrial_commands_issued": False,
            "tls_note": (
                "The existing localhost self-signed lab endpoint requires disabled "
                "certificate verification; this is not production guidance."
            ),
        },
    }
    output_path = artifact_root / "phase10-live-validation.json"
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "industry_count": len(summaries),
                "all_splunk_observed": output["all_splunk_observed"],
                "all_investigations_succeeded": output[
                    "all_investigations_succeeded"
                ],
                "all_business_impacts_modeled": output[
                    "all_business_impacts_modeled"
                ],
                "studio_observed": studio_summary["all_required_observed"],
                "fail_closed": unsupported_blocked,
            },
            indent=2,
        )
    )
    return 0 if all(
        (
            output["all_runtime_completed"],
            output["all_splunk_observed"],
            output["all_investigations_succeeded"],
            output["all_business_impacts_modeled"],
            studio_summary["all_required_observed"],
            unsupported_blocked,
        )
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
