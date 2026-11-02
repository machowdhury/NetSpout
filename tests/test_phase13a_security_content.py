import hashlib
import importlib.util
import json
import threading
import time
from pathlib import Path

import pytest

from netspout_core.security_content_lab import (
    AttackDataReplayService,
    DetectionEvidenceStore,
    DetectionValidationOrchestrator,
    SecurityContentCatalog,
    validate_index_name,
    validate_read_only_spl,
)


ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "catalog" / "phase13a_splunk_security_content.json"
SOURCE_CATALOG = ROOT / "catalog" / "phase13_security_source_coverage.json"
FTD_DETECTION = "d36459b1-7901-401a-a67e-44426c15b168"
FTD_DATASET = (
    "/datasets/cisco_secure_firewall_threat_defense/"
    "react2shell/react2shell.log"
)


@pytest.fixture(scope="module")
def catalog():
    return SecurityContentCatalog(SNAPSHOT, SOURCE_CATALOG)


def test_pinned_metadata_inventory_and_offline_operation(catalog):
    summary = catalog.summary()
    assert summary["detections"] == 2181
    assert summary["analytic_stories"] == 365
    assert summary["attack_dataset_manifests"] == 1400
    assert summary["parse_failures"] == 0
    assert summary["live_validated_detections"] == 1
    assert summary["upstreams"]["security_content"]["commit"] == (
        "1b2142fdd2d1358b4ac6ad3dfc47e5e455e619e8"
    )
    assert summary["upstreams"]["attack_data"]["commit"] == (
        "4389fa7a4e74a7c083c0fbe448fa2c7c32378981"
    )


def test_invalid_yaml_is_rejected(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "phase13a_sync", ROOT / "scripts" / "sync_splunk_security_content.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(module)
    invalid = tmp_path / "invalid.yml"
    invalid.write_text("items: [unterminated", encoding="utf-8")
    with pytest.raises(Exception):
        module.load_yaml(invalid)


def test_duplicate_upstream_ids_are_quarantined_not_hidden(catalog):
    assert catalog.document["summary"]["duplicate_ids"] == 23
    duplicate = catalog.document["duplicate_ids"][0]
    assert duplicate["first_path"] != duplicate["duplicate_path"]


def test_dependency_resolution_is_conservative(catalog):
    detection = catalog.get_detection(FTD_DETECTION)
    assert detection
    dependencies = detection["dependencies"]
    assert dependencies["resolution"] == "RESOLVED"
    assert dependencies["sourcetypes"] == ["cisco:sfw:estreamer"]
    assert "cisco_secure_firewall" in dependencies["macros"]
    assert "signature_id" in dependencies["required_fields"]
    assert "not full SPL semantics" in dependencies["parser_scope"]


def test_unresolved_dependencies_remain_explicit(catalog):
    unresolved = [
        item
        for item in catalog.document["detections"]
        if item["dependencies"]["resolution"] == "DEPENDENCY_UNRESOLVED"
    ]
    assert unresolved
    assert all(item["dependencies"]["unresolved_reasons"] for item in unresolved)


@pytest.mark.parametrize(
    "status",
    [
        "MISSING_DATA_MODEL",
        "MISSING_LOOKUP",
        "MISSING_MACRO",
        "REQUIRES_TRANSFORMATION",
        "RESEARCH_REQUIRED",
    ],
)
def test_compatibility_matrix_contains_evidence_backed_statuses(catalog, status):
    assert catalog.summary()["compatibility_counts"][status] > 0


def test_replay_detection_does_not_promote_native_source_support(catalog):
    assessment = catalog.get_detection(FTD_DETECTION)["compatibility"]
    assert assessment["status"] == "REQUIRES_TRANSFORMATION"
    assert assessment["runtime_compatibility"] == "NOT_TESTED"
    assert assessment["production_detection_efficacy"] == "NOT_ESTABLISHED"


def test_search_filters_and_detection_detail(catalog):
    result = catalog.list_detections(
        query="React Server Components",
        technique="T1190",
        compatibility="REQUIRES_TRANSFORMATION",
    )
    assert result["total"] == 1
    assert result["items"][0]["content_id"] == FTD_DETECTION


def test_mitre_matrix_preserves_independent_counts(catalog):
    row = next(item for item in catalog.mitre_coverage() if item["technique"] == "T1190")
    assert row["detections"] >= 1
    assert row["test_data_available"] >= 1
    assert row["detection_validated"] == 1


@pytest.mark.parametrize(
    "query",
    [
        'search index="main" | outputlookup stolen.csv',
        'search index="main" | collect index=other',
        "| rest /services/server/info",
        "| inputlookup secrets.csv",
    ],
)
def test_untrusted_or_write_capable_spl_is_rejected(query):
    with pytest.raises(ValueError):
        validate_read_only_spl(query)


@pytest.mark.parametrize("index", ['main" | delete', "../main", "a b", ""])
def test_unsafe_index_selection_is_rejected(index):
    with pytest.raises(ValueError):
        validate_index_name(index)


class FakeDispatcher:
    def __init__(self, delay=0):
        self.payloads = []
        self.delay = delay

    def emit_hec(self, payload, *_args, **_kwargs):
        if self.delay:
            time.sleep(self.delay)
        self.payloads.append(payload)
        return True, "accepted"


def _local_replay_fixture(catalog, tmp_path, lines, dispatcher=None):
    service = AttackDataReplayService(
        catalog, dispatcher or FakeDispatcher(), work_dir=str(tmp_path)
    )
    local_id = hashlib.sha256(FTD_DATASET.encode()).hexdigest()
    target = service.root / local_id
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return service, local_id


def test_replay_preserves_event_and_source_metadata(catalog, tmp_path):
    dispatcher = FakeDispatcher()
    raw = {"EventType": "IntrusionEvent", "SignatureID": 65554}
    service, local_id = _local_replay_fixture(
        catalog, tmp_path, [json.dumps(raw)], dispatcher
    )
    result = service.replay(
        local_id=local_id,
        dataset_path=FTD_DATASET,
        index="idx_network_ops",
        hec_url="https://127.0.0.1:8088/services/collector/event",
        hec_token="runtime-only-test-value",
        timestamp_mode="PRESERVE",
        allow_insecure_tls=True,
    )
    assert result["status"] == "SENT"
    assert result["events_sent"] == 1
    assert dispatcher.payloads[0]["event"] == raw
    assert dispatcher.payloads[0]["sourcetype"] == "cisco:sfw:estreamer"
    assert dispatcher.payloads[0]["fields"]["netspout_evidence_path"] == (
        "SPLUNK_ATTACK_DATA_REPLAY"
    )
    assert "time" not in dispatcher.payloads[0]


def test_replay_cancellation_is_bounded(catalog, tmp_path):
    dispatcher = FakeDispatcher(delay=0.01)
    service, local_id = _local_replay_fixture(
        catalog,
        tmp_path,
        [json.dumps({"SignatureID": 65554}) for _ in range(100)],
        dispatcher,
    )
    run_id = "cancel-test"
    thread = threading.Thread(
        target=service.replay,
        kwargs={
            "local_id": local_id,
            "dataset_path": FTD_DATASET,
            "index": "idx_network_ops",
            "hec_url": "https://127.0.0.1:8088/services/collector/event",
            "hec_token": "runtime-only-test-value",
            "run_id": run_id,
        },
    )
    thread.start()
    for _ in range(50):
        try:
            service.cancel(run_id)
            break
        except KeyError:
            time.sleep(0.002)
    thread.join(timeout=3)
    assert not thread.is_alive()
    assert service.get_run(run_id)["status"] == "CANCELLED"
    assert service.get_run(run_id)["events_sent"] < 100


def test_path_traversal_and_unknown_size_fail_closed(catalog, tmp_path):
    service = AttackDataReplayService(catalog, FakeDispatcher(), work_dir=str(tmp_path))
    with pytest.raises(ValueError):
        service.retrieve("../../etc/passwd")
    unknown = next(
        file
        for dataset in catalog.document["datasets"]
        for file in dataset["files"]
        if file["size_bytes"] is None
    )
    with pytest.raises(ValueError, match="unknown"):
        service.retrieve(unknown["path"])


def test_replay_binds_retrieved_bytes_to_dataset_metadata(catalog, tmp_path):
    service = AttackDataReplayService(catalog, FakeDispatcher(), work_dir=str(tmp_path))
    with pytest.raises(ValueError, match="do not match"):
        service.replay(
            local_id="0" * 64,
            dataset_path=FTD_DATASET,
            index="idx_network_ops",
            hec_url="https://127.0.0.1:8088/services/collector/event",
            hec_token="runtime-only-test-value",
        )


def test_detection_positive_and_negative_controls(catalog, tmp_path):
    positive = DetectionValidationOrchestrator(
        catalog,
        lambda _query: ([{"signature_id": "65554"}], None),
        DetectionEvidenceStore(str(tmp_path / "positive")),
    )
    positive_result = positive.validate(
        detection_id=FTD_DETECTION,
        run_id="positive-control",
        index="idx_network_ops",
        expected_min_matches=1,
        control="POSITIVE",
        dataset_or_scenario_id=FTD_DATASET,
        indexed_event_count=1,
    )
    assert positive_result["status"] == "POSITIVE_CASE_VALIDATED"
    assert positive_result["matched_event_count"] == 1

    negative = DetectionValidationOrchestrator(
        catalog,
        lambda _query: ([], None),
        DetectionEvidenceStore(str(tmp_path / "negative")),
    )
    negative_result = negative.validate(
        detection_id=FTD_DETECTION,
        run_id="negative-control",
        index="idx_network_ops",
        expected_min_matches=0,
        control="NEGATIVE",
        dataset_or_scenario_id="no-matching-evidence",
        indexed_event_count=0,
    )
    assert negative_result["status"] == "NEGATIVE_CASE_VALIDATED"


def test_reviewed_spl_adaptation_has_no_empty_pipeline_commands(catalog, tmp_path):
    orchestrator = DetectionValidationOrchestrator(
        catalog,
        lambda _query: ([], None),
        DetectionEvidenceStore(str(tmp_path / "query")),
    )
    query, adaptations = orchestrator.prepare_query(
        catalog.get_detection(FTD_DETECTION),
        "bounded-run",
        "idx_network_ops",
    )
    assert "`" not in query
    assert not any(line.strip() == "|" for line in query.splitlines())
    assert "display-only security_content_ctime" in " ".join(adaptations)


def test_detection_search_failure_and_missing_dependency(catalog, tmp_path):
    failed = DetectionValidationOrchestrator(
        catalog,
        lambda _query: ([], "TimeoutError"),
        DetectionEvidenceStore(str(tmp_path / "failed")),
    )
    result = failed.validate(
        detection_id=FTD_DETECTION,
        run_id="timeout-control",
        index="idx_network_ops",
        expected_min_matches=1,
        control="POSITIVE",
        dataset_or_scenario_id=FTD_DATASET,
        indexed_event_count=1,
    )
    assert result["status"] == "SPL_EXECUTION_FAILED"

    blocked_detection = next(
        item
        for item in catalog.document["detections"]
        if catalog.compatibility(item)["status"] == "MISSING_MACRO"
    )
    blocked = failed.validate(
        detection_id=blocked_detection["content_id"],
        run_id="dependency-control",
        index="idx_network_ops",
        expected_min_matches=1,
        control="POSITIVE",
        dataset_or_scenario_id="none",
        indexed_event_count=0,
    )
    assert blocked["status"] == "DEPENDENCY_BLOCKED"


def test_coverage_matrix_is_machine_readable_and_pinned():
    matrix = json.loads(
        (ROOT / "catalog" / "phase13a_security_content_coverage.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(matrix["detections"]) == 2181
    assert matrix["upstreams"]["security_content"]["commit"] == (
        "1b2142fdd2d1358b4ac6ad3dfc47e5e455e619e8"
    )
