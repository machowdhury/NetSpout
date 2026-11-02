#!/usr/bin/env python3
"""Summarize the nine bounded Phase 12 Docker acceptance journeys."""

from __future__ import annotations

import json
import os
from pathlib import Path
import urllib.request
from typing import Any, Dict


def request_json(url: str, payload: Dict[str, Any] | None = None) -> Any:
    data = (
        json.dumps(payload).encode("utf-8")
        if payload is not None
        else None
    )
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST" if data is not None else "GET",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        return json.load(response)


def main() -> int:
    root_value = os.environ.get("NETSPOUT_TEST_ARTIFACT_ROOT", "").strip()
    if not root_value:
        raise RuntimeError("NETSPOUT_TEST_ARTIFACT_ROOT must be supplied")
    root = Path(root_value).resolve()
    phase12 = root / "phase12"
    live = json.loads((phase12 / "phase12-live-validation.json").read_text())
    dashboards = json.loads(
        (phase12 / "phase12-dashboard-validation.json").read_text()
    )
    visual = json.loads(
        (phase12 / "phase12-visual-acceptance.json").read_text()
    )
    browser = json.loads(
        (phase12 / "phase12-visual-browser-matrix.json").read_text()
    )
    by_scenario = {item["scenario_id"]: item for item in live["scenarios"]}
    browser_ids = {item["scenario_id"] for item in browser}
    catalog = request_json("http://127.0.0.1:8081/api/dashboards")
    studio = request_json(
        "http://127.0.0.1:8081/api/studio/packs/private-ai-002-clone"
    )
    unsafe = json.loads(json.dumps(studio))
    unsafe["entities"][0]["attributes"]["endpoint"] = (
        "https://external.invalid/mcp"
    )
    fail_closed = request_json(
        "http://127.0.0.1:8081/api/studio/packs/validate", unsafe
    )
    legacy_eligible = [
        item
        for item in catalog["dashboards"]
        if item["state"] == "ELIGIBLE"
        and not (
            item["scenario_id"].startswith("AI-")
            or item["scenario_id"].startswith("SC-")
            or item["scenario_id"].startswith("P12-XD-")
        )
    ]

    def observed(scenario_id: str) -> bool:
        item = by_scenario[scenario_id]
        return bool(
            item["splunk_observed"]
            and item["detection"]["expected_evidence_matched"]
            and scenario_id in browser_ids
        )

    journeys = {
        "A_INDIRECT_PROMPT_INJECTION": observed("AI-001"),
        "B_MCP_TOOL_MISUSE": observed("AI-002"),
        "C_A2A_DELEGATION": observed("AI-005"),
        "D_SUPPLY_CHAIN": observed("SC-001") and observed("SC-003"),
        "E_CROSS_DOMAIN": observed("P12-XD-001") and observed("P12-XD-002"),
        "F_DASHBOARD": (
            dashboards["summary"]["data_validated"] == 13
            and visual["summary"]["dashboard_ready"] == 13
        ),
        "G_SCENARIO_STUDIO": (
            studio["cloned_from_scenario_id"] == "AI-002"
            and any(
                item["parameter_id"] == "intensity" and item["default"] == 2
                for item in studio["parameters"]
            )
        ),
        "H_FAIL_CLOSED": (
            fail_closed["valid"] is False
            and any(
                item["check_id"] == "execution-containment"
                and item["state"] == "FAIL"
                for item in fail_closed["checks"]
            )
        ),
        "I_REGRESSION": (
            len(legacy_eligible) == 14 and catalog["eligible_count"] == 27
        ),
    }
    payload = {
        "schema_version": "1.0.0",
        "classification": "CURRENT_RUN_PACKAGED_DOCKER_EVIDENCE",
        "base_url": "http://127.0.0.1:8081",
        "journeys": journeys,
        "summary": {
            "passed": sum(journeys.values()),
            "total": len(journeys),
        },
    }
    output = phase12 / "phase12-docker-journeys.json"
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"artifact": str(output), **payload["summary"]}, indent=2))
    return 0 if all(journeys.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
