#!/usr/bin/env python3
"""Validate Phase 12 dashboard packs against preserved fresh run evidence."""

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
from netspout_core.unified_generation import UnifiedGenerationService


def required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError("{} must be supplied through the environment".format(name))
    return value


def main() -> int:
    artifact_root = Path(required("NETSPOUT_TEST_ARTIFACT_ROOT")).resolve()
    phase12_dir = artifact_root / "phase12"
    live_path = phase12_dir / "phase12-live-validation.json"
    live = json.loads(live_path.read_text(encoding="utf-8"))
    password = required("SPLUNK_PASSWORD")
    os.environ["NETSPOUT_SPLUNK_PASSWORD"] = password
    os.environ.setdefault("NETSPOUT_SPLUNK_USER", "admin")
    os.environ.setdefault(
        "NETSPOUT_SPLUNK_REST_URL",
        "https://127.0.0.1:8089/services/search/jobs/export",
    )
    transport = TelemetryTransportConfig(
        hec_enabled=True,
        hec_url="https://127.0.0.1:8088/services/collector",
        hec_token=required("NETSPOUT_HEC_TOKEN"),
        hec_index="idx_network_ops",
        hec_ssl_verify=False,
        hec_allow_insecure_tls=True,
    )
    catalog = NetSpoutCatalog(str(ROOT / "catalog"))
    dashboard_service = catalog.get_dashboard_recipe_service()
    dashboard_service.evidence_store.storage_dir = phase12_dir / "dashboard-evidence"
    dashboard_service.evidence_store.storage_dir.mkdir(parents=True, exist_ok=True)
    generation = UnifiedGenerationService(catalog=catalog)
    dashboards: List[Dict[str, Any]] = []

    for scenario in live["scenarios"]:
        scenario_id = scenario["scenario_id"]
        dashboard_id = "scenario-{}".format(scenario_id.lower())
        pack = dashboard_service.generate(
            dashboard_id,
            run_id=scenario["run_id"],
            index=transport.hec_index,
        )
        panel_results: Dict[str, Any] = {}
        failures = []
        for panel in pack.panels:
            if not panel.executable or not panel.query:
                continue
            rows = []
            error = None
            for attempt in range(4):
                rows, error = generation.execute_bounded_spl(panel.query, transport)
                fields = {field for row in rows for field in row}
                if error or set(panel.expected_shape).issubset(fields):
                    break
                if attempt < 3:
                    time.sleep(1)
            if error:
                failures.append("{}: {}".format(panel.panel_id, error))
            else:
                panel_results[panel.panel_id] = rows
        evidence = dashboard_service.validate(
            pack,
            panel_results,
            evidence_refs=[
                "phase12-live-validation.json#{}".format(scenario_id),
                "run:{}".format(scenario["run_id"]),
            ],
            execution_failures=failures,
            source_coverage_validated=bool(scenario["splunk_observed"]),
            source_observations={
                source_id: bool(scenario["splunk_observed"])
                for source_id in scenario["source_ids"]
            },
        )
        export = dashboard_service.export_dashboard_studio(pack)
        dashboards.append(
            {
                "dashboard_id": dashboard_id,
                "scenario_id": scenario_id,
                "run_id": scenario["run_id"],
                "recipe_ids": [panel.recipe_id for panel in pack.panels],
                "panel_count": len(pack.panels),
                "observed_fields": evidence.observed_fields,
                "spl_validated": evidence.spl_validated,
                "data_validated": evidence.data_validated,
                "maturity": evidence.maturity.value,
                "failures": evidence.failures,
                "export_valid": bool(export["validation"]["valid"]),
                "deployment_status": export["deployment"]["deployment_status"],
            }
        )

    summary = {
        "generated": len(dashboards),
        "spl_validated": sum(bool(item["spl_validated"]) for item in dashboards),
        "data_validated": sum(bool(item["data_validated"]) for item in dashboards),
        "export_validated": sum(bool(item["export_valid"]) for item in dashboards),
        "dashboard_ready": sum(item["maturity"] == "DASHBOARD_READY" for item in dashboards),
    }
    payload = {
        "schema_version": "1.0.0",
        "classification": "CURRENT_RUN_PHASE12_DASHBOARD_EVIDENCE",
        "dashboards": dashboards,
        "summary": summary,
    }
    output = phase12_dir / "phase12-dashboard-validation.json"
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(output), **summary}, indent=2), flush=True)
    return 0 if summary["data_validated"] == 13 and summary["export_validated"] == 13 else 1


if __name__ == "__main__":
    raise SystemExit(main())
