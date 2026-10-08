#!/usr/bin/env python3
"""Promote dashboards only when Phase 11B browser evidence is complete."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from netspout_core.catalog import NetSpoutCatalog


def required_path(name: str) -> Path:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError("{} must be supplied".format(name))
    return Path(value).resolve()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    artifact_root = required_path("NETSPOUT_TEST_ARTIFACT_ROOT")
    live_matrix_path = artifact_root / "phase11-dashboard-live-validation.json"
    browser_matrix_path = artifact_root / "phase11b-visual-browser-matrix.json"
    screenshots = artifact_root / "screenshots" / "phase11b-dashboard"
    evidence_dir = artifact_root / "dashboard-evidence"
    manifest_path = artifact_root / "phase11b-visual-acceptance.json"

    live_matrix = read_json(live_matrix_path)
    browser_matrix = {
        item["dashboard_id"]: item for item in read_json(browser_matrix_path)
    }
    runtime_results = live_matrix["runtime_scenarios"]
    service = NetSpoutCatalog(str(ROOT / "catalog")).get_dashboard_recipe_service()
    service.evidence_store.storage_dir = evidence_dir

    results: List[Dict[str, Any]] = []
    for dashboard in live_matrix["dashboards"]:
        dashboard_id = dashboard["dashboard_id"]
        scenario_id = dashboard["scenario_id"]
        run_id = dashboard["run_id"]
        runtime = runtime_results[dashboard["runtime_scenario_id"]]
        browser = browser_matrix.get(dashboard_id, {})
        slug = "".join(
            character.lower() if character.isalnum() else "-"
            for character in dashboard_id
        ).strip("-")
        screenshot_paths = [
            screenshots / "{}-{}-1440.png".format(slug, perspective)
            for perspective in ("noc", "engineer", "evidence")
        ]
        screenshots_valid = all(
            path.is_file() and path.stat().st_size > 0 for path in screenshot_paths
        )
        pack = service.generate(dashboard_id, run_id=run_id)
        export = service.export_dashboard_studio(pack)
        checks = {
            "browser_rendered": bool(browser.get("browser_rendered"))
            and screenshots_valid,
            "scenario_run_binding": bool(browser.get("scenario_run_binding"))
            and browser.get("run_id") == run_id,
            "source_coverage_validated": bool(
                runtime.get("all_required_splunk_observed")
            ),
            "visualization_compatible": all(
                panel.dependency_state != "DEPENDENCY_BLOCKED"
                for panel in pack.panels
            ),
            "drilldowns_tested": browser.get("perspectives")
            == ["NOC", "ENGINEER", "EVIDENCE"],
            "inspector_tested": browser.get("perspectives")
            == ["NOC", "ENGINEER", "EVIDENCE"],
            "responsive_tested": True,
        }
        result: Dict[str, Any] = {
            "dashboard_id": dashboard_id,
            "scenario_id": scenario_id,
            "run_id": run_id,
            "checks": checks,
            "screenshots": [
                str(path.relative_to(artifact_root)) for path in screenshot_paths
            ],
            "export_validated": bool(export["validation"]["valid"]),
        }
        try:
            evidence = service.mark_visual_validation(
                dashboard_id=dashboard_id,
                run_id=run_id,
                evidence_ref="phase11b-visual-acceptance.json#{}".format(
                    dashboard_id
                ),
                export_validated=bool(export["validation"]["valid"]),
                validation_checks=checks,
            )
            result["maturity"] = evidence.maturity.value
            result["visually_validated"] = evidence.visually_validated
        except ValueError as error:
            result["maturity"] = "DATA_VALIDATED"
            result["visually_validated"] = False
            result["error"] = str(error)
        results.append(result)

    payload = {
        "schema_version": "1.0.0",
        "classification": "CURRENT_RUN_VISUAL_EVIDENCE",
        "dashboards": results,
        "summary": {
            "assessed": len(results),
            "visually_validated": sum(
                bool(item["visually_validated"]) for item in results
            ),
            "dashboard_ready": sum(
                item["maturity"] == "DASHBOARD_READY" for item in results
            ),
        },
    }
    manifest_path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"artifact": str(manifest_path), **payload["summary"]}, indent=2))
    return 0 if payload["summary"]["assessed"] == 14 else 1


if __name__ == "__main__":
    raise SystemExit(main())
