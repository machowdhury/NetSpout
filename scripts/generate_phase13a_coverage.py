#!/usr/bin/env python3
"""Generate the machine-readable Phase 13A compatibility and MITRE matrix."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from netspout_core.security_content_lab import SecurityContentCatalog  # noqa: E402


def main() -> int:
    catalog = SecurityContentCatalog(
        ROOT / "catalog" / "phase13a_splunk_security_content.json",
        ROOT / "catalog" / "phase13_security_source_coverage.json",
    )
    detections = []
    for detection in catalog.document["detections"]:
        assessment = catalog.compatibility(detection)
        evidence = catalog._validation_by_detection.get(detection["content_id"])
        detections.append(
            {
                "catalog_key": detection["catalog_key"],
                "content_id": detection["content_id"],
                "name": detection["name"],
                "upstream_commit": detection["repository_commit"],
                "file_path": detection["file_path"],
                "content_hash": detection["content_hash"],
                "spl_hash": detection["spl_hash"],
                "mitre_attack_ids": detection["mitre_attack_ids"],
                "data_source_names": detection["data_source_names"],
                "dependency_resolution": detection["dependencies"]["resolution"],
                "compatibility": assessment,
                "test_data_available": bool(detection["attack_data"]),
                "validation_status": evidence["status"] if evidence else "NOT_TESTED",
                "validation_evidence": evidence,
                "production_detection_efficacy": "NOT_ESTABLISHED",
            }
        )
    document = {
        "schema_version": "1.0.0",
        "upstreams": catalog.document["upstreams"],
        "summary": catalog.summary(),
        "detections": detections,
        "mitre_coverage": catalog.mitre_coverage(),
        "scope": (
            "Compatibility is conservative metadata analysis. It is not detection "
            "validation or production efficacy evidence."
        ),
    }
    output = ROOT / "catalog" / "phase13a_security_content_coverage.json"
    output.write_text(
        json.dumps(document, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(document["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
