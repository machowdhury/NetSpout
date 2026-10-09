#!/usr/bin/env python3
"""Run bounded Phase 12 scenarios and preserve fresh Splunk evidence."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from netspout_core.catalog import NetSpoutCatalog
from netspout_core.models import TelemetryTransportConfig
from netspout_core.unified_generation import (
    EvidenceState,
    GenerationMode,
    UnifiedGenerationRequest,
    UnifiedGenerationService,
)


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError("{} must be supplied through the environment".format(name))
    return value


def stage_proven(run: Any, stage: str) -> bool:
    return any(
        item.stage == stage and item.state == EvidenceState.PROVEN
        for item in run.evidence
    )


def observe(
    service: UnifiedGenerationService,
    run: Any,
    transport: TelemetryTransportConfig,
) -> Any:
    for _ in range(20):
        run = service.observe(run.run_id, transport)
        if stage_proven(run, "SPLUNK_OBSERVED"):
            return run
        time.sleep(1)
    return run


def execute_until(
    service: UnifiedGenerationService,
    query: str,
    transport: TelemetryTransportConfig,
    predicate: Any,
) -> Any:
    rows: List[Dict[str, Any]] = []
    error = None
    for _ in range(12):
        rows, error = service.execute_bounded_spl(query, transport)
        if error is not None or predicate(rows):
            return rows, error
        time.sleep(1)
    return rows, error


def main() -> int:
    artifact_root = Path(required("NETSPOUT_TEST_ARTIFACT_ROOT")).resolve()
    output_dir = artifact_root / "phase12"
    output_dir.mkdir(parents=True, exist_ok=True)
    password = required("SPLUNK_PASSWORD")
    token = required("NETSPOUT_HEC_TOKEN")
    os.environ["NETSPOUT_SPLUNK_PASSWORD"] = password
    os.environ.setdefault("NETSPOUT_SPLUNK_USER", "admin")
    os.environ.setdefault(
        "NETSPOUT_SPLUNK_REST_URL",
        "https://127.0.0.1:8089/services/search/jobs/export",
    )
    transport = TelemetryTransportConfig(
        hec_enabled=True,
        hec_url="https://127.0.0.1:8088/services/collector",
        hec_token=token,
        hec_index="idx_network_ops",
        hec_ssl_verify=False,
        hec_allow_insecure_tls=True,
    )
    catalog = NetSpoutCatalog(str(ROOT / "catalog"))
    service = UnifiedGenerationService(catalog=catalog)
    scenario_ids = [
        "AI-001", "AI-002", "AI-003", "AI-004", "AI-005", "AI-006",
        "SC-001", "SC-002", "SC-003", "SC-004", "SC-005",
        "P12-XD-001", "P12-XD-002",
    ]
    scenarios: List[Dict[str, Any]] = []
    for offset, scenario_id in enumerate(scenario_ids):
        print("phase12: {}".format(scenario_id), flush=True)
        request = UnifiedGenerationRequest(
            mode=GenerationMode.SCENARIO,
            selection_id=scenario_id,
            count=5,
            rate_eps=20,
            scenario_parameters={"seed": 1200 + offset},
        )
        preflight = service.preflight(request, transport)
        if preflight.state.value == "BLOCKED":
            scenarios.append(
                {
                    "scenario_id": scenario_id,
                    "preflight": preflight.model_dump(mode="json"),
                    "status": "BLOCKED",
                }
            )
            continue
        run = observe(service, service.run(request, transport), transport)
        investigation = {}
        for _ in range(12):
            investigation = service.run_investigation(
                run.run_id,
                "p12-investigate-{}".format(scenario_id.lower()),
                transport,
            )
            if investigation["status"] == "FAILED" or investigation["result_count"] > 0:
                break
            time.sleep(1)
        scenario = next(
            item
            for item in service.capabilities()["scenarios"]
            if item["scenario_id"] == scenario_id
        )
        detection = scenario["detection_validation"][0]
        detection_query = detection["spl"].replace("$run_id$", run.run_id)
        expected_outcome = next(
            item["expected_outcome"]
            for item in service.capabilities()["scenarios"]
            if item["scenario_id"] == scenario_id
        )
        outcome_query = (
            'search index="idx_network_ops" sourcetype="{}" '
            'netspout_run_id="{}" earliest=-15m latest=now '
            "| spath | stats count by outcome"
        ).format(run.events[0].sourcetype, run.run_id)
        outcome_rows, outcome_error = execute_until(
            service,
            outcome_query,
            transport,
            lambda rows: expected_outcome
            in {str(row.get("outcome")) for row in rows},
        )
        outcomes = {
            str(row.get("outcome"))
            for row in outcome_rows
            if row.get("outcome") is not None
        }
        detection_rows, detection_error = execute_until(
            service,
            detection_query,
            transport,
            lambda rows: bool(rows),
        )
        baseline_rows, baseline_error = service.execute_bounded_spl(
            (
                'search index="idx_network_ops" sourcetype="{}" '
                'netspout_run_id="{}" earliest=-15m latest=now '
                '| spath | search netspout_phase="BASELINE" outcome="{}" '
                "| stats count"
            ).format(run.events[0].sourcetype, run.run_id, expected_outcome),
            transport,
        )
        baseline_count = (
            int(baseline_rows[0].get("count", 0)) if baseline_rows else 0
        )
        scenarios.append(
            {
                "scenario_id": scenario_id,
                "run_id": run.run_id,
                "status": run.status,
                "source_ids": run.source_ids,
                "sourcetype": run.events[0].sourcetype,
                "generated_events": len(run.events),
                "evidence": [
                    item.model_dump(mode="json") for item in run.evidence
                ],
                "splunk_observed": stage_proven(run, "SPLUNK_OBSERVED"),
                "fields_verified": stage_proven(run, "FIELDS_VERIFIED"),
                "investigation": investigation,
                "detection": {
                    "detection_id": detection["detection_id"],
                    "executed": detection_error is None,
                    "result_rows": detection_rows,
                    "error": detection_error,
                    "expected_evidence_matched": expected_outcome in outcomes,
                    "false_positive_behavior_tested": (
                        baseline_error is None and baseline_count == 0
                    ),
                    "baseline_rows": baseline_rows,
                    "baseline_error": baseline_error,
                    "production_portability_assessed": False,
                },
                "outcome_search": {
                    "rows": outcome_rows,
                    "error": outcome_error,
                    "expected_outcome": expected_outcome,
                },
                "preflight": preflight.model_dump(mode="json"),
            }
        )

    summary = {
        "implemented": len(scenarios),
        "splunk_observed": sum(bool(item.get("splunk_observed")) for item in scenarios),
        "fields_verified": sum(bool(item.get("fields_verified")) for item in scenarios),
        "investigations_succeeded": sum(
            item.get("investigation", {}).get("status") == "SUCCEEDED"
            for item in scenarios
        ),
        "detections_executed": sum(
            bool(item.get("detection", {}).get("executed"))
            for item in scenarios
        ),
        "expected_evidence_matched": sum(
            bool(item.get("detection", {}).get("expected_evidence_matched"))
            for item in scenarios
        ),
        "false_positive_behavior_tested": sum(
            bool(item.get("detection", {}).get("false_positive_behavior_tested"))
            for item in scenarios
        ),
    }
    payload = {
        "schema_version": "1.0.0",
        "classification": "CURRENT_RUN_LIVE_SPLUNK_EVIDENCE",
        "protocol_versions": {"mcp": "2025-11-25", "a2a": "1.0.0", "slsa": "1.1"},
        "execution": {
            "synthetic": True,
            "offline_source": True,
            "external_protocol_contact": False,
            "repository_or_package_execution": False,
            "credentials_serialized": False,
            "tls_scope": "Existing loopback self-signed Splunk lab endpoint only.",
        },
        "scenarios": scenarios,
        "summary": summary,
    }
    output = output_dir / "phase12-live-validation.json"
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(output), **summary}, indent=2), flush=True)
    return 0 if (
        summary["splunk_observed"] == len(scenario_ids)
        and summary["expected_evidence_matched"] == len(scenario_ids)
        and summary["false_positive_behavior_tested"] == len(scenario_ids)
    ) else 1


if __name__ == "__main__":
    raise SystemExit(main())
