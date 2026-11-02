#!/usr/bin/env python3
"""Run guarded Phase 8C native-receiver and Splunk validation journeys."""

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
from netspout_core.unified_generation import (
    EvidenceState,
    GenerationMode,
    UnifiedGenerationRequest,
    UnifiedGenerationService,
)


SCENARIO_IDS = (
    "C100-ENT-001",
    "C100-DC-001",
    "C100-SEC-001",
    "C100-CRI-002",
)


def _required_environment(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError("{} must be supplied through the environment".format(name))
    return value


def _all_required_observed(run) -> bool:
    return bool(run.channel_results) and all(
        any(
            evidence.stage == "SPLUNK_OBSERVED"
            and evidence.state == EvidenceState.PROVEN
            for evidence in channel.evidence
        )
        for channel in run.channel_results
        if channel.required
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
            "NETSPOUT_PHASE8C_HEC_URL",
            "https://127.0.0.1:8088/services/collector",
        ),
        hec_token=resolve_hec_token(),
        hec_index=os.environ.get("NETSPOUT_SPLUNK_INDEX", "idx_network_ops"),
        hec_ssl_verify=False,
        hec_allow_insecure_tls=True,
    )
    service = UnifiedGenerationService(
        catalog=NetSpoutCatalog(str(REPO_ROOT / "catalog"))
    )
    summaries = []
    for scenario_id in SCENARIO_IDS:
        request = UnifiedGenerationRequest(
            mode=GenerationMode.SCENARIO,
            selection_id=scenario_id,
            transport_id="transport-local-hec",
            destination_id="destination-local-docker-splunk",
            scenario_parameters={"seed": 73},
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
        investigation = service.run_investigation(
            run.run_id,
            "investigate-{}-reference".format(scenario_id.lower()),
            transport,
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
                "investigation": investigation,
            }
        )
    output = {
        "schema_version": "1.0.0",
        "classification": "CURRENT_RUN_EVIDENCE",
        "scope": "Phase 8C native syslog receiver and local Splunk validation",
        "scenarios": summaries,
        "all_runtime_completed": all(
            item["status"] in {"COMPLETED", "OBSERVED"} for item in summaries
        ),
        "all_splunk_observed": all(
            item["status"] == "OBSERVED" for item in summaries
        ),
        "all_investigations_succeeded": all(
            item["investigation"]["status"] == "SUCCEEDED"
            and item["investigation"]["result_count"] > 0
            for item in summaries
        ),
        "security": {
            "credentials_serialized": False,
            "transport_scope": "localhost lab",
            "tls_note": (
                "The existing local self-signed lab endpoint requires disabled "
                "certificate verification; this is not production guidance."
            ),
        },
    }
    output_path = artifact_root / "phase8c-live-validation.json"
    output_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(output_path)
    return 0 if all(
        (
            output["all_runtime_completed"],
            output["all_splunk_observed"],
            output["all_investigations_succeeded"],
        )
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
