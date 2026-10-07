#!/usr/bin/env python3
"""Run bounded Phase 9 native DNS/flow and fresh Splunk validation journeys."""

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
from netspout_core.models import TelemetryTransportConfig, resolve_hec_token
from netspout_core.security_state import SUPPORTED_SECURITY_SCENARIOS
from netspout_core.scenario_studio import ScenarioStudioService, StudioParameter
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
            "NETSPOUT_PHASE9_HEC_URL",
            "https://127.0.0.1:8088/services/collector",
        ),
        hec_token=resolve_hec_token(),
        hec_index=os.environ.get("NETSPOUT_SPLUNK_INDEX", "idx_network_ops"),
        hec_ssl_verify=False,
        hec_allow_insecure_tls=True,
        native_flow_enabled=True,
    )
    service = UnifiedGenerationService(
        catalog=NetSpoutCatalog(str(REPO_ROOT / "catalog"))
    )
    summaries = []
    for scenario_id in sorted(SUPPORTED_SECURITY_SCENARIOS):
        request = UnifiedGenerationRequest(
            mode=GenerationMode.SCENARIO,
            selection_id=scenario_id,
            transport_id="transport-local-hec",
            destination_id="destination-local-docker-splunk",
            scenario_parameters={"seed": 909, "intensity": 1},
        )
        preflight = service.preflight(request, transport)
        if preflight.state.value == "BLOCKED":
            raise RuntimeError("{} preflight blocked".format(scenario_id))
        run = service.run(request, transport)
        for _ in range(20):
            run = service.observe(run.run_id, transport)
            if _all_required_observed(run):
                break
            time.sleep(1)
        investigations = []
        for recipe in run.investigations:
            investigations.append(
                service.run_investigation(
                    run.run_id, recipe["recipe_id"], transport
                )
            )
        summaries.append(
            {
                "scenario_id": scenario_id,
                "run_id": run.run_id,
                "status": run.status,
                "source_ids": run.source_ids,
                "preflight": preflight.model_dump(mode="json"),
                "evidence": [
                    item.model_dump(mode="json") for item in run.evidence
                ],
                "channels": [
                    item.model_dump(mode="json") for item in run.channel_results
                ],
                "validation": [
                    item.model_dump(mode="json") for item in run.validation
                ],
                "investigations": investigations,
            }
        )
    studio_root = artifact_root / "scenario-studio"
    studio = ScenarioStudioService(
        catalog=service.catalog,
        generation_service=service,
        storage_dir=str(studio_root),
    )
    clone = studio.clone_scenario("SEC-P9-C-BEACONING")
    clone.title = "Periodic Communication — Intensity 2 Private Clone"
    clone.parameters = [
        StudioParameter(
            parameter_id="intensity",
            state_key="flow.intensity",
            value_type="integer",
            default=2,
            minimum=1,
            maximum=3,
            description="Bounded modeled observation intensity.",
        )
    ]
    clone.layout_hints["test-endpoint-01"] = {"x": 160.0, "y": 220.0}
    stored = studio.save_pack(clone)
    reloaded_studio = ScenarioStudioService(
        catalog=service.catalog,
        generation_service=service,
        storage_dir=str(studio_root),
    )
    reloaded = reloaded_studio.get_pack(stored.pack_id)
    if reloaded is None:
        raise RuntimeError("Phase 9 Studio clone did not reload")
    _, studio_composition = reloaded_studio.compile_pack(reloaded)
    first_binding = studio_composition.source_bindings[0]
    studio_request = UnifiedGenerationRequest(
        mode=GenerationMode.SCENARIO,
        selection_id=reloaded.scenario_id,
        transport_id=(
            first_binding.destination_transport_id or first_binding.transport_id
        ),
        destination_id=first_binding.destination_id,
        scenario_parameters={
            "seed": 910,
            "intensity": 2,
            "entity_id": reloaded.entities[0].entity_id,
            "security_profile_scenario_id": reloaded.cloned_from_scenario_id,
        },
    )
    studio_preflight = service.preflight(studio_request, transport)
    if studio_preflight.state.value == "BLOCKED":
        raise RuntimeError("Phase 9 Studio clone preflight blocked")
    studio_run = service.run(studio_request, transport)
    for _ in range(20):
        studio_run = service.observe(studio_run.run_id, transport)
        if _all_required_observed(studio_run):
            break
        time.sleep(1)
    studio_summary = {
        "pack_id": reloaded.pack_id,
        "scenario_id": reloaded.scenario_id,
        "cloned_from_scenario_id": reloaded.cloned_from_scenario_id,
        "saved_and_reloaded": True,
        "contract_fingerprints_preserved": (
            reloaded.contract_fingerprints == stored.contract_fingerprints
        ),
        "modified_modeled_intensity": 2,
        "run_id": studio_run.run_id,
        "status": studio_run.status,
        "all_required_observed": _all_required_observed(studio_run),
    }
    output = {
        "schema_version": "1.0.0",
        "classification": "CURRENT_RUN_EVIDENCE",
        "scope": "Phase 9 bounded native DNS/IPFIX and local Splunk validation",
        "scenarios": summaries,
        "scenario_studio": studio_summary,
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
        "security": {
            "credentials_serialized": False,
            "targets": "localhost and IANA documentation addresses only",
            "offensive_execution": False,
            "tls_note": (
                "The existing localhost self-signed lab endpoint requires disabled "
                "certificate verification; this is not production guidance."
            ),
        },
    }
    output_path = artifact_root / "phase9-live-validation.json"
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "artifact": str(output_path),
                "scenario_count": len(summaries),
                "all_runtime_completed": output["all_runtime_completed"],
                "all_splunk_observed": output["all_splunk_observed"],
                "all_investigations_succeeded": output[
                    "all_investigations_succeeded"
                ],
            },
            indent=2,
        )
    )
    return 0 if all(
        (
            output["all_runtime_completed"],
            output["all_splunk_observed"],
            output["all_investigations_succeeded"],
            output["scenario_studio"]["all_required_observed"],
        )
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
