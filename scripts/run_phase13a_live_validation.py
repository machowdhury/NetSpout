#!/usr/bin/env python3
"""Run the reviewed Phase 13A positive/negative controls in a disposable lab."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from app.release_candidate import ReleaseCandidateConfiguration
from app.security_content_lab import (
    AttackDataReplayService,
    DetectionEvidenceStore,
    DetectionValidationOrchestrator,
    SecurityContentCatalog,
)
from app.telemetry_dispatcher import dispatcher


DETECTION_ID = "d36459b1-7901-401a-a67e-44426c15b168"
DATASET_PATH = (
    "/datasets/cisco_secure_firewall_threat_defense/"
    "react2shell/react2shell.log"
)
INDEX = "idx_network_ops"
POSITIVE_RUN_ID = "phase13a-positive-final"
NEGATIVE_RUN_ID = "phase13a-negative-final"


def main() -> int:
    password = os.environ.get("SPLUNK_PASSWORD")
    token = os.environ.get("SPLUNK_HEC_TOKEN")
    if not password or not token:
        raise SystemExit("Disposable-lab runtime credentials are required")

    configuration = ReleaseCandidateConfiguration()
    configuration.save(
        {
            "deployment_mode": "DOCKER_LAB",
            "splunk_deployment_type": "SPLUNK_ENTERPRISE",
            "hec_url": "https://127.0.0.1:8088/services/collector",
            "search_url": "https://127.0.0.1:8089/services/search/jobs/export",
            "auth_method": "HEC_TOKEN_AND_BASIC_SEARCH",
            "search_username": "admin",
            "hec_token": token,
            "search_secret": password,
            "indexes": [INDEX],
            "collectors": [],
            "guided_sample": False,
            "allow_insecure_tls": True,
        }
    )

    catalog = SecurityContentCatalog()
    replay_service = AttackDataReplayService(catalog, dispatcher)
    retrieval = replay_service.retrieve(DATASET_PATH)
    try:
        replay = replay_service.replay(
            local_id=retrieval["local_id"],
            dataset_path=DATASET_PATH,
            index=INDEX,
            hec_url="https://127.0.0.1:8088/services/collector/event",
            hec_token=token,
            timestamp_mode="CURRENT",
            allow_insecure_tls=True,
            run_id=POSITIVE_RUN_ID,
        )

        indexed_count = 0
        observation_error = None
        field_evidence = []
        for _ in range(12):
            rows, observation_error = configuration.execute_read_only_search(
                f'search index="{INDEX}" netspout_run_id="{POSITIVE_RUN_ID}" '
                "earliest=-15m latest=now | stats count as count"
            )
            if rows:
                indexed_count = int(rows[0].get("count", 0))
            if indexed_count:
                break
            time.sleep(2)
        if indexed_count:
            field_evidence, observation_error = configuration.execute_read_only_search(
                f'search index="{INDEX}" netspout_run_id="{POSITIVE_RUN_ID}" '
                "earliest=-15m latest=now | spath "
                "| eval signature_id=coalesce(signature_id,SignatureID), "
                "dest=coalesce(dest,ResponderIP) "
                "| table sourcetype EventType SignatureID signature_id dest"
            )
        detection_preflight, preflight_error = configuration.execute_read_only_search(
            f'search index="{INDEX}" sourcetype="cisco:sfw:estreamer" '
            f'netspout_run_id="{POSITIVE_RUN_ID}" earliest=-15m latest=now '
            "| spath | eval signature_id=coalesce(signature_id,SignatureID), "
            "dest=coalesce(dest,ResponderIP) "
            "| search EventType=IntrusionEvent signature_id=65554 "
            "| stats values(signature_id) as signature_id by dest"
        )

        evidence_store = DetectionEvidenceStore(
            str(Path("/tmp/netspout-phase13a-live-evidence"))
        )
        orchestrator = DetectionValidationOrchestrator(
            catalog,
            lambda query: configuration.execute_read_only_search(query),
            evidence_store,
        )
        positive = orchestrator.validate(
            detection_id=DETECTION_ID,
            run_id=POSITIVE_RUN_ID,
            index=INDEX,
            expected_min_matches=1,
            control="POSITIVE",
            dataset_or_scenario_id=DATASET_PATH,
            indexed_event_count=indexed_count,
        )
        negative = orchestrator.validate(
            detection_id=DETECTION_ID,
            run_id=NEGATIVE_RUN_ID,
            index=INDEX,
            expected_min_matches=0,
            control="NEGATIVE",
            dataset_or_scenario_id="NO_MATCHING_EVIDENCE",
            indexed_event_count=0,
        )
        result = {
            "retrieval": retrieval,
            "replay": replay,
            "fresh_indexed_events": indexed_count,
            "observation_error": observation_error,
            "required_field_evidence": field_evidence,
            "detection_preflight": detection_preflight,
            "preflight_error": preflight_error,
            "positive": positive,
            "negative": negative,
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if (
            replay["status"] == "SENT"
            and indexed_count >= 1
            and positive["status"] == "POSITIVE_CASE_VALIDATED"
            and negative["status"] == "NEGATIVE_CASE_VALIDATED"
        ) else 1
    finally:
        replay_service.cleanup(retrieval["local_id"])


if __name__ == "__main__":
    raise SystemExit(main())
