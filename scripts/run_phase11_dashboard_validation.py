#!/usr/bin/env python3
"""Validate Phase 11 dashboard packs against fresh, run-scoped Splunk data."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import time
from typing import Any, Dict
from types import SimpleNamespace


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


def required_environment(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError("{} must be supplied through the environment".format(name))
    return value


def observed(run: Any) -> bool:
    required = [item for item in run.channel_results if item.required]
    return bool(required) and all(
        any(
            evidence.stage == "SPLUNK_OBSERVED"
            and evidence.state == EvidenceState.PROVEN
            for evidence in channel.evidence
        )
        for channel in required
    )


def observe(
    generation: UnifiedGenerationService,
    run: Any,
    transport: TelemetryTransportConfig,
) -> Any:
    for _ in range(20):
        run = generation.observe(run.run_id, transport)
        if observed(run):
            return run
        time.sleep(1)
    return run


def main() -> int:
    artifact_root = Path(
        required_environment("NETSPOUT_TEST_ARTIFACT_ROOT")
    ).resolve()
    artifact_root.mkdir(parents=True, exist_ok=True)
    password = required_environment("SPLUNK_PASSWORD")
    hec_token = required_environment("NETSPOUT_HEC_TOKEN")
    os.environ["NETSPOUT_SPLUNK_PASSWORD"] = password
    os.environ.setdefault("NETSPOUT_SPLUNK_USER", "admin")
    os.environ.setdefault(
        "NETSPOUT_SPLUNK_REST_URL",
        "https://127.0.0.1:8089/services/search/jobs/export",
    )

    transport = TelemetryTransportConfig(
        hec_enabled=True,
        hec_url="https://127.0.0.1:8088/services/collector",
        hec_token=hec_token,
        hec_index="idx_network_ops",
        hec_ssl_verify=False,
        hec_allow_insecure_tls=True,
    )
    catalog = NetSpoutCatalog(str(ROOT / "catalog"))
    dashboard_service = catalog.get_dashboard_recipe_service()
    dashboard_service.evidence_store.storage_dir = artifact_root / "dashboard-evidence"
    dashboard_service.evidence_store.storage_dir.mkdir(parents=True, exist_ok=True)
    generation = UnifiedGenerationService(catalog=catalog)

    eligible = [
        item
        for item in dashboard_service.catalog_summary()["dashboards"]
        if item["state"] == "ELIGIBLE"
    ]
    runs: Dict[str, Any] = {}
    runtime_results: Dict[str, Dict[str, Any]] = {}
    output_path = artifact_root / "phase11-dashboard-live-validation.json"
    if (
        os.environ.get("NETSPOUT_PHASE11_REUSE_RUNS") == "1"
        and output_path.exists()
    ):
        prior = json.loads(output_path.read_text(encoding="utf-8"))
        runtime_results = prior.get("runtime_scenarios", {})
        runs = {
            scenario_id: SimpleNamespace(run_id=result["run_id"])
            for scenario_id, result in runtime_results.items()
            if result.get("run_id")
        }
    forced = {
        item.strip()
        for item in os.environ.get(
            "NETSPOUT_PHASE11_FORCE_SCENARIOS", ""
        ).split(",")
        if item.strip()
    }
    for scenario_id in forced:
        runs.pop(scenario_id, None)
        runtime_results.pop(scenario_id, None)

    for runtime_scenario_id in sorted(
        {item["runtime_scenario_id"] for item in eligible} - set(runs)
    ):
        print("runtime: {}".format(runtime_scenario_id), flush=True)
        request = UnifiedGenerationRequest(
            mode=GenerationMode.SCENARIO,
            selection_id=runtime_scenario_id,
            count=6,
            rate_eps=10,
            scenario_parameters={"seed": 1111},
        )
        preflight = generation.preflight(request, transport)
        if preflight.state.value == "BLOCKED":
            runtime_results[runtime_scenario_id] = {
                "preflight": preflight.model_dump(mode="json"),
                "error": "preflight blocked",
            }
            continue
        run = observe(generation, generation.run(request, transport), transport)
        runs[runtime_scenario_id] = run
        runtime_results[runtime_scenario_id] = {
            "run_id": run.run_id,
            "status": run.status,
            "all_required_splunk_observed": observed(run),
            "required_sources": [
                {
                    "source_id": channel.source_id,
                    "status": channel.status,
                    "splunk_observed": any(
                        evidence.stage == "SPLUNK_OBSERVED"
                        and evidence.state == EvidenceState.PROVEN
                        for evidence in channel.evidence
                    ),
                    "evidence": [
                        {
                            "stage": evidence.stage,
                            "state": evidence.state.value,
                            "count": evidence.count,
                            "detail": evidence.detail,
                        }
                        for evidence in channel.evidence
                    ],
                    "errors": channel.errors,
                }
                for channel in run.channel_results
                if channel.required
            ],
            "preflight": preflight.model_dump(mode="json"),
        }

    dashboards = []
    for item in eligible:
        print("dashboard: {}".format(item["dashboard_id"]), flush=True)
        run = runs.get(item["runtime_scenario_id"])
        if run is None:
            dashboards.append(
                {
                    "dashboard_id": item["dashboard_id"],
                    "scenario_id": item["scenario_id"],
                    "runtime_scenario_id": item["runtime_scenario_id"],
                    "maturity": "VALIDATION_FAILED",
                    "failures": ["runtime scenario did not produce a run"],
                }
            )
            continue
        pack = dashboard_service.generate(
            item["dashboard_id"],
            run_id=run.run_id,
            index=transport.hec_index,
        )
        panel_results: Dict[str, Any] = {}
        failures = []
        for panel in pack.panels:
            if not panel.executable or not panel.query:
                continue
            rows = []
            error = None
            for attempt in range(3):
                rows, error = generation.execute_bounded_spl(panel.query, transport)
                fields = {field for row in rows for field in row}
                if error or set(panel.expected_shape).issubset(fields):
                    break
                if attempt < 2:
                    time.sleep(1)
            if error:
                failures.append("{}: {}".format(panel.panel_id, error))
            else:
                panel_results[panel.panel_id] = rows
        runtime_result = runtime_results[item["runtime_scenario_id"]]
        source_observations = {
            source["source_id"]: bool(source.get("splunk_observed"))
            for source in runtime_result.get("required_sources", [])
        }
        evidence = dashboard_service.validate(
            pack,
            panel_results,
            evidence_refs=["run:{}".format(run.run_id)],
            execution_failures=failures,
            source_coverage_validated=bool(
                runtime_result.get("all_required_splunk_observed")
            ),
            source_observations=source_observations,
        )
        exported = dashboard_service.export_dashboard_studio(pack)
        dashboards.append(
            {
                "dashboard_id": item["dashboard_id"],
                "scenario_id": item["scenario_id"],
                "runtime_scenario_id": item["runtime_scenario_id"],
                "run_id": run.run_id,
                "recipe_ids": [panel.recipe_id for panel in pack.panels],
                "topology_ref": pack.topology_ref,
                "shared_entity_graph": pack.entity_graph["shared_with_scenario"],
                "observed_fields": evidence.observed_fields,
                "spl_validated": evidence.spl_validated,
                "data_validated": evidence.data_validated,
                "visually_validated": False,
                "maturity": evidence.maturity.value,
                "failures": evidence.failures,
                "export_valid": exported["validation"]["valid"],
                "deployment_status": exported["deployment"][
                    "deployment_status"
                ],
            }
        )

    result = {
        "schema_version": "1.0.0",
        "classification": "CURRENT_RUN_EVIDENCE",
        "runtime_scenarios": runtime_results,
        "dashboards": dashboards,
        "counts": {
            "eligible": len(eligible),
            "generated": len(dashboards),
            "spl_validated": sum(item.get("spl_validated", False) for item in dashboards),
            "data_validated": sum(item.get("data_validated", False) for item in dashboards),
            "visually_validated": 0,
            "dashboard_ready": 0,
            "export_validated": sum(item.get("export_valid", False) for item in dashboards),
        },
        "security": {
            "credentials_serialized": False,
            "customer_data_used": False,
            "tls_scope": (
                "Existing localhost self-signed lab endpoint only; certificate "
                "verification remains required outside this explicit lab transport."
            ),
        },
        "visual_acceptance": {
            "state": "PENDING",
            "reason": "DASHBOARD_V2_HANDOFF.md was not available.",
        },
    }
    output_path.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(output_path), **result["counts"]}, indent=2))
    return 0 if result["counts"]["data_validated"] == len(eligible) else 1


if __name__ == "__main__":
    raise SystemExit(main())
