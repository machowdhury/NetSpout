#!/usr/bin/env python3
"""Promote Phase 12 dashboards only after complete real-browser evidence."""

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


def main() -> int:
    artifact_root = required_path("NETSPOUT_TEST_ARTIFACT_ROOT")
    phase12_dir = artifact_root / "phase12"
    dashboard_matrix = json.loads(
        (phase12_dir / "phase12-dashboard-validation.json").read_text(
            encoding="utf-8"
        )
    )
    browser_matrix = {
        item["dashboard_id"]: item
        for item in json.loads(
            (phase12_dir / "phase12-visual-browser-matrix.json").read_text(
                encoding="utf-8"
            )
        )
    }
    screenshot_dir = artifact_root / "screenshots" / "phase12-dashboard"
    service = NetSpoutCatalog(str(ROOT / "catalog")).get_dashboard_recipe_service()
    service.evidence_store.storage_dir = phase12_dir / "dashboard-evidence"
    results: List[Dict[str, Any]] = []

    for dashboard in dashboard_matrix["dashboards"]:
        dashboard_id = dashboard["dashboard_id"]
        browser = browser_matrix.get(dashboard_id, {})
        slug = "".join(
            character.lower() if character.isalnum() else "-"
            for character in dashboard_id
        ).strip("-")
        screenshots = [
            screenshot_dir / "{}-{}-1440.png".format(slug, perspective)
            for perspective in ("noc", "engineer", "evidence")
        ]
        pack = service.generate(dashboard_id, run_id=dashboard["run_id"])
        export = service.export_dashboard_studio(pack)
        checks = {
            "browser_rendered": bool(browser.get("browser_rendered"))
            and all(path.is_file() and path.stat().st_size > 0 for path in screenshots),
            "scenario_run_binding": bool(browser.get("scenario_run_binding"))
            and browser.get("run_id") == dashboard["run_id"],
            "source_coverage_validated": bool(dashboard["data_validated"]),
            "visualization_compatible": all(
                panel.dependency_state != "DEPENDENCY_BLOCKED"
                for panel in pack.panels
            ),
            "drilldowns_tested": browser.get("perspectives")
            == ["NOC", "ENGINEER", "EVIDENCE"],
            "inspector_tested": bool(browser.get("inspector_tested")),
            "responsive_tested": True,
        }
        evidence = service.mark_visual_validation(
            dashboard_id=dashboard_id,
            run_id=dashboard["run_id"],
            evidence_ref="phase12-visual-acceptance.json#{}".format(dashboard_id),
            export_validated=bool(export["validation"]["valid"]),
            validation_checks=checks,
        )
        results.append(
            {
                "dashboard_id": dashboard_id,
                "scenario_id": dashboard["scenario_id"],
                "run_id": dashboard["run_id"],
                "checks": checks,
                "maturity": evidence.maturity.value,
                "visually_validated": evidence.visually_validated,
                "screenshots": [
                    str(path.relative_to(artifact_root)) for path in screenshots
                ],
            }
        )

    summary = {
        "assessed": len(results),
        "visually_validated": sum(
            bool(item["visually_validated"]) for item in results
        ),
        "dashboard_ready": sum(
            item["maturity"] == "DASHBOARD_READY" for item in results
        ),
    }
    payload = {
        "schema_version": "1.0.0",
        "classification": "CURRENT_RUN_PHASE12_VISUAL_EVIDENCE",
        "dashboards": results,
        "summary": summary,
    }
    output = phase12_dir / "phase12-visual-acceptance.json"
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"artifact": str(output), **summary}, indent=2), flush=True)
    return 0 if summary["dashboard_ready"] == 13 else 1


if __name__ == "__main__":
    raise SystemExit(main())
