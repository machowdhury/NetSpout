# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/security_content_lab.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""Pinned Splunk Security Content discovery, compatibility, replay, and validation."""

from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
import threading
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Dict, List, Optional, Tuple
from urllib.parse import urlparse


COMPATIBILITY_STATUSES = {
    "VALIDATED_COMPATIBLE",
    "STRUCTURALLY_COMPATIBLE",
    "PARTIALLY_COMPATIBLE",
    "REQUIRES_TRANSFORMATION",
    "MISSING_SOURCE",
    "MISSING_REQUIRED_FIELDS",
    "MISSING_TA",
    "MISSING_MACRO",
    "MISSING_LOOKUP",
    "MISSING_DATA_MODEL",
    "RESEARCH_REQUIRED",
    "NOT_EVALUATED",
}
VALIDATION_STATUSES = {
    "NOT_TESTED",
    "DEPENDENCY_BLOCKED",
    "DATA_NOT_AVAILABLE",
    "SPL_EXECUTION_FAILED",
    "EXECUTED_NO_MATCH",
    "EXECUTED_MATCHED",
    "POSITIVE_CASE_VALIDATED",
    "NEGATIVE_CASE_VALIDATED",
    "VALIDATION_PASSED",
    "VALIDATION_FAILED",
}
SAFE_DATASET_EXTENSIONS = {".log", ".json", ".ndjson", ".xml", ".csv"}
MAX_DATASET_BYTES = 5 * 1024 * 1024
MAX_REPLAY_EVENTS = 2_000
SUPPORTED_RUNTIME_MACROS = {
    "cisco_secure_firewall",
    "security_content_ctime",
    "cisco_secure_firewall___react_server_components_rce_attempt_filter",
}
SUPPORTED_RUNTIME_DETECTIONS = {
    "d36459b1-7901-401a-a67e-44426c15b168",
}
DENIED_SPL_COMMANDS = {
    "collect",
    "delete",
    "dump",
    "fit",
    "into",
    "loadjob",
    "map",
    "outputcsv",
    "outputlookup",
    "runshellscript",
    "script",
    "sendalert",
    "sendemail",
    "tscollect",
}


def _catalog_path() -> Path:
    module = Path(__file__).resolve()
    candidates = (
        module.parents[2] / "catalog" / "phase13a_splunk_security_content.json",
        module.parent / "catalog_data" / "phase13a_splunk_security_content.json",
        module.parent.parent / "catalog_data" / "phase13a_splunk_security_content.json",
        Path("/opt/splunk/etc/apps/netspout/bin/catalog_data/phase13a_splunk_security_content.json"),
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Phase 13A security-content snapshot is unavailable")


def validate_index_name(value: str) -> str:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}", value):
        raise ValueError("Unsafe Splunk index name")
    return value


def validate_read_only_spl(query: str) -> None:
    if not query or len(query) > 20_000:
        raise ValueError("SPL is empty or exceeds the bounded execution policy")
    commands = {
        value.lower()
        for value in re.findall(r"(?im)(?:^|\|)\s*([A-Za-z][A-Za-z0-9_]*)", query)
    }
    denied = sorted(commands & DENIED_SPL_COMMANDS)
    if denied:
        raise ValueError(f"Write-capable or unsafe SPL command rejected: {', '.join(denied)}")
    if re.search(r"(?i)\b(?:rest|inputlookup|loadjob)\b", query):
        raise ValueError("SPL external/content access is outside the read-only policy")


class SecurityContentCatalog:
    """Read-only normalized upstream snapshot with conservative compatibility."""

    def __init__(
        self,
        path: Optional[Path] = None,
        source_catalog_path: Optional[Path] = None,
    ):
        self.path = path or _catalog_path()
        self.document = json.loads(self.path.read_text(encoding="utf-8"))
        if self.document.get("schema_version") != "1.0.0":
            raise ValueError("Unsupported security-content snapshot schema")
        if source_catalog_path is None:
            source_catalog_path = self.path.parent / "phase13_security_source_coverage.json"
        self.source_document = (
            json.loads(source_catalog_path.read_text(encoding="utf-8"))
            if source_catalog_path.is_file()
            else {"sources": []}
        )
        evidence_path = self.path.parent / "phase13a_validation_evidence.json"
        evidence_document = (
            json.loads(evidence_path.read_text(encoding="utf-8"))
            if evidence_path.is_file()
            else {"validations": []}
        )
        self._validation_by_detection = {
            item["detection_id"]: item
            for item in evidence_document.get("validations", [])
            if item.get("detection_id")
        }
        self._detections = {
            item["catalog_key"]: item for item in self.document["detections"]
        }
        self._detections_by_id: Dict[str, List[Dict[str, Any]]] = {}
        for item in self.document["detections"]:
            self._detections_by_id.setdefault(item["content_id"], []).append(item)
        self._datasets = {
            item["catalog_key"]: item for item in self.document["datasets"]
        }
        self._data_sources = {
            item.get("name"): item
            for item in self.document["data_sources"]
            if item.get("name")
        }
        self._dataset_files = {
            file_record["path"]: (dataset, file_record)
            for dataset in self.document["datasets"]
            for file_record in dataset.get("files", [])
        }
        self._mitre_techniques = {
            item["technique_id"]: item
            for item in self.document.get("mitre_techniques", [])
        }

    def summary(self) -> Dict[str, Any]:
        compatibility = [self.compatibility(item) for item in self.document["detections"]]
        counts: Dict[str, int] = {}
        for item in compatibility:
            counts[item["status"]] = counts.get(item["status"], 0) + 1
        resolved = sum(
            item.get("dependencies", {}).get("resolution") == "RESOLVED"
            for item in self.document["detections"]
        )
        return {
            **self.document["summary"],
            "upstreams": self.document["upstreams"],
            "dependencies_resolved": resolved,
            "live_validated_detections": len(self._validation_by_detection),
            "compatibility_counts": counts,
            "metadata_only": True,
        }

    def list_detections(
        self,
        query: Optional[str] = None,
        story: Optional[str] = None,
        technique: Optional[str] = None,
        data_source: Optional[str] = None,
        sourcetype: Optional[str] = None,
        detection_type: Optional[str] = None,
        product: Optional[str] = None,
        required_ta: Optional[str] = None,
        data_model: Optional[str] = None,
        validation_status: Optional[str] = None,
        compatibility: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> Dict[str, Any]:
        if limit < 1 or limit > 500 or offset < 0:
            raise ValueError("Invalid pagination")
        values = []
        needle = (query or "").casefold()
        for detection in self.document["detections"]:
            assessment = self.compatibility(detection)
            source_records = [
                self._data_sources.get(name)
                for name in detection.get("data_source_names", [])
            ]
            source_records = [item for item in source_records if item]
            searchable = " ".join(
                str(value)
                for value in (
                    detection.get("name"),
                    detection.get("description"),
                    detection.get("category"),
                    detection.get("security_domain"),
                    detection.get("author"),
                    detection.get("data_source_names"),
                    detection.get("mitre_attack_ids"),
                    detection.get("products"),
                    detection.get("dependencies"),
                )
            ).casefold()
            if needle and needle not in searchable:
                continue
            if story and story not in detection.get("analytic_stories", []):
                continue
            if technique and technique not in detection.get("mitre_attack_ids", []):
                continue
            if data_source and data_source not in detection.get("data_source_names", []):
                continue
            if sourcetype and not any(
                record.get("sourcetype") == sourcetype for record in source_records
            ):
                continue
            if detection_type and detection.get("detection_type") != detection_type:
                continue
            if product and product not in detection.get("products", []):
                continue
            if required_ta and required_ta not in detection.get("dependencies", {}).get(
                "technology_add_ons", []
            ):
                continue
            if data_model and data_model not in detection.get("dependencies", {}).get(
                "data_models", []
            ):
                continue
            if validation_status and detection.get("validation_status") != validation_status:
                continue
            if compatibility and assessment["status"] != compatibility:
                continue
            values.append(
                {
                    **{key: detection.get(key) for key in (
                        "catalog_key",
                        "content_id",
                        "name",
                        "description",
                        "category",
                        "security_domain",
                        "detection_type",
                        "status",
                        "version",
                        "analytic_stories",
                        "mitre_attack_ids",
                        "data_source_names",
                        "products",
                        "repository_commit",
                        "file_path",
                    )},
                    "compatibility": assessment,
                    "has_attack_data": bool(detection.get("attack_data")),
                }
            )
        return {
            "total": len(values),
            "offset": offset,
            "limit": limit,
            "items": values[offset : offset + limit],
        }

    def get_detection(self, identifier: str) -> Optional[Dict[str, Any]]:
        detection = self._detections.get(identifier)
        if detection is None:
            matches = self._detections_by_id.get(identifier, [])
            if len(matches) == 1:
                detection = matches[0]
        if detection is None:
            return None
        sources = [
            self._data_sources[name]
            for name in detection.get("data_source_names", [])
            if name in self._data_sources
        ]
        return {
            **detection,
            "resolved_data_sources": sources,
            "compatibility": self.compatibility(detection),
            "validation_evidence": self._validation_by_detection.get(
                detection.get("content_id")
            ),
            "production_detection_efficacy": "NOT_ESTABLISHED",
        }

    def list_stories(self, query: Optional[str] = None, limit: int = 200) -> List[Dict[str, Any]]:
        needle = (query or "").casefold()
        return [
            item
            for item in self.document["analytic_stories"]
            if not needle
            or needle in f"{item.get('name')} {item.get('description')}".casefold()
        ][: max(1, min(limit, 500))]

    def list_datasets(
        self, query: Optional[str] = None, technique: Optional[str] = None, limit: int = 200
    ) -> List[Dict[str, Any]]:
        needle = (query or "").casefold()
        values = []
        for item in self.document["datasets"]:
            if technique and technique not in item.get("mitre_techniques", []):
                continue
            if needle and needle not in (
                f"{item.get('name')} {item.get('description')} "
                f"{item.get('mitre_techniques')} {item.get('files')}"
            ).casefold():
                continue
            values.append(item)
        return values[: max(1, min(limit, 500))]

    def get_dataset_file(self, path: str) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
        return self._dataset_files.get("/" + path.lstrip("/"))

    def compatibility(self, detection: Dict[str, Any]) -> Dict[str, Any]:
        dependency = detection.get("dependencies", {})
        requirements = set(dependency.get("required_fields", []))
        required_sourcetypes = set(dependency.get("sourcetypes", []))
        matched_sources = []
        for source in self.source_document.get("sources", []):
            sourcetypes = set(source.get("splunk_sourcetypes", []))
            if required_sourcetypes & sourcetypes:
                matched_sources.append(source)

        missing_macros = sorted(
            set(dependency.get("macros", [])) - SUPPORTED_RUNTIME_MACROS
        )
        missing_lookups = list(dependency.get("lookups", []))
        reasons: List[str] = []
        status = "NOT_EVALUATED"
        if dependency.get("resolution") == "DEPENDENCY_UNRESOLVED":
            status = "RESEARCH_REQUIRED"
            reasons.extend(dependency.get("unresolved_reasons", []))
        elif dependency.get("data_models"):
            status = "MISSING_DATA_MODEL"
            reasons.append("Required accelerated/CIM data model is not established")
        elif missing_lookups:
            status = "MISSING_LOOKUP"
            reasons.append("Required lookup is not installed by NetSpout")
        elif missing_macros:
            status = "MISSING_MACRO"
            reasons.append("Required runtime macros are not installed by NetSpout")
        elif not matched_sources:
            if detection.get("attack_data"):
                status = "REQUIRES_TRANSFORMATION"
                reasons.append(
                    "Curated replay exists, but no matching validated NetSpout native source contract exists"
                )
            else:
                status = "MISSING_SOURCE"
                reasons.append("No matching NetSpout sourcetype contract")
        else:
            available_fields = set().union(
                *(set(source.get("required_fields", [])) for source in matched_sources)
            )
            missing_fields = sorted(requirements - available_fields)
            if missing_fields:
                status = "MISSING_REQUIRED_FIELDS"
                reasons.append("Source contract does not establish every upstream field")
            elif any(
                source.get("status") == "IMPLEMENTED_AND_VALIDATED"
                for source in matched_sources
            ):
                status = "STRUCTURALLY_COMPATIBLE"
            else:
                status = "PARTIALLY_COMPATIBLE"
        return {
            "status": status,
            "structural_compatibility": status == "STRUCTURALLY_COMPATIBLE",
            "runtime_compatibility": "NOT_TESTED",
            "splunk_compatibility": "NOT_TESTED",
            "detection_validation": self._validation_by_detection.get(
                detection.get("content_id"), {}
            ).get("status", detection.get("validation_status", "NOT_TESTED")),
            "production_detection_efficacy": "NOT_ESTABLISHED",
            "matched_netspout_sources": [
                source["coverage_id"] for source in matched_sources
            ],
            "missing_macros": missing_macros,
            "missing_lookups": missing_lookups,
            "reasons": reasons,
        }

    def mitre_coverage(self) -> List[Dict[str, Any]]:
        matrix: Dict[str, Dict[str, Any]] = {}
        for detection in self.document["detections"]:
            assessment = self.compatibility(detection)
            for technique in detection.get("mitre_attack_ids", []):
                row = matrix.setdefault(
                    technique,
                    {
                        "technique": technique,
                        "name": self._mitre_techniques.get(technique, {}).get("name"),
                        "tactics": self._mitre_techniques.get(technique, {}).get("tactics", []),
                        "is_subtechnique": self._mitre_techniques.get(technique, {}).get(
                            "is_subtechnique", "." in technique
                        ),
                        "detections": 0,
                        "telemetry_available": 0,
                        "test_data_available": 0,
                        "detection_executable": 0,
                        "detection_validated": 0,
                        "detection_ids": [],
                        "data_sources": set(),
                    },
                )
                row["detections"] += 1
                row["detection_ids"].append(detection["content_id"])
                row["data_sources"].update(detection.get("data_source_names", []))
                if assessment["status"] in {
                    "STRUCTURALLY_COMPATIBLE",
                    "PARTIALLY_COMPATIBLE",
                    "REQUIRES_TRANSFORMATION",
                }:
                    row["telemetry_available"] += 1
                if detection.get("attack_data"):
                    row["test_data_available"] += 1
                if not assessment["missing_macros"] and not assessment["missing_lookups"]:
                    row["detection_executable"] += 1
                if detection.get("content_id") in self._validation_by_detection:
                    row["detection_validated"] += 1
        return [
            {**row, "data_sources": sorted(row["data_sources"])}
            for _, row in sorted(matrix.items())
        ]


@dataclass
class ReplayLimits:
    max_bytes: int = MAX_DATASET_BYTES
    max_events: int = MAX_REPLAY_EVENTS
    timeout_seconds: int = 30


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class AttackDataReplayService:
    """Selective, non-executing retrieval and replay of one pinned dataset file."""

    def __init__(
        self,
        catalog: SecurityContentCatalog,
        dispatcher: Any,
        work_dir: Optional[str] = None,
        limits: Optional[ReplayLimits] = None,
    ):
        self.catalog = catalog
        root = Path(work_dir or os.environ.get("NETSPOUT_ATTACK_DATA_DIR") or tempfile.gettempdir())
        self.root = root / "netspout-attack-data"
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.root, stat.S_IRWXU)
        self.dispatcher = dispatcher
        self.limits = limits or ReplayLimits()
        self._runs: Dict[str, Dict[str, Any]] = {}
        self._cancellations: Dict[str, threading.Event] = {}
        self._lock = threading.Lock()

    def _validated_file(self, dataset_path: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        pure = PurePosixPath("/" + dataset_path.lstrip("/"))
        if ".." in pure.parts:
            raise ValueError("Dataset path traversal rejected")
        resolved = self.catalog.get_dataset_file(pure.as_posix())
        if resolved is None:
            raise ValueError("Dataset file is not in the pinned metadata snapshot")
        _, file_record = resolved
        suffix = Path(file_record["path"]).suffix.lower()
        if suffix not in SAFE_DATASET_EXTENSIONS:
            raise ValueError("Dataset format is not supported for replay")
        size = file_record.get("size_bytes")
        if size is None or int(size) > self.limits.max_bytes:
            raise ValueError("Dataset size is unknown or exceeds the configured limit")
        return resolved

    def retrieve(self, dataset_path: str) -> Dict[str, Any]:
        dataset, file_record = self._validated_file(dataset_path)
        url = file_record["download_url"]
        parsed = urlparse(url)
        expected_prefix = (
            f"/media/splunk/attack_data/"
            f"{self.catalog.document['upstreams']['attack_data']['commit']}/datasets/"
        )
        if (
            parsed.scheme != "https"
            or parsed.hostname != "media.githubusercontent.com"
            or not parsed.path.startswith(expected_prefix)
        ):
            raise ValueError("Dataset URL is outside the pinned allowlist")
        target = self.root / hashlib.sha256(file_record["path"].encode()).hexdigest()
        opener = urllib.request.build_opener(
            urllib.request.HTTPSHandler(), _NoRedirect()
        )
        request = urllib.request.Request(
            url,
            headers={"Accept": "application/octet-stream", "User-Agent": "NetSpout/13A"},
        )
        digest = hashlib.sha256()
        total = 0
        temporary = target.with_suffix(".tmp")
        try:
            with opener.open(request, timeout=self.limits.timeout_seconds) as response:
                content_type = (response.headers.get("Content-Type") or "").lower()
                if "text/html" in content_type:
                    raise ValueError("Unexpected dataset content type")
                with temporary.open("wb") as output:
                    while True:
                        chunk = response.read(64 * 1024)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > self.limits.max_bytes:
                            raise ValueError("Dataset exceeded the configured size limit")
                        digest.update(chunk)
                        output.write(chunk)
            expected = file_record.get("sha256")
            actual = digest.hexdigest()
            if expected and actual != expected:
                raise ValueError("Dataset integrity check failed")
            os.chmod(temporary, stat.S_IRUSR | stat.S_IWUSR)
            os.replace(temporary, target)
        finally:
            if temporary.exists():
                temporary.unlink()
        return {
            "dataset_id": dataset["dataset_id"],
            "dataset_path": file_record["path"],
            "local_id": target.name,
            "size_bytes": total,
            "sha256": digest.hexdigest(),
            "source": file_record.get("source"),
            "sourcetype": file_record.get("sourcetype"),
            "repository_commit": dataset["repository_commit"],
            "provenance": "SPLUNK_ATTACK_DATA_REPLAY",
        }

    def preview(self, local_id: str, limit: int = 10) -> Dict[str, Any]:
        if not re.fullmatch(r"[a-f0-9]{64}", local_id):
            raise ValueError("Invalid local dataset identifier")
        path = self.root / local_id
        if not path.is_file():
            raise FileNotFoundError("Dataset has not been retrieved")
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        return {"events": lines[: max(1, min(limit, 50))], "total_lines": len(lines)}

    def cancel(self, run_id: str) -> Dict[str, Any]:
        event = self._cancellations.get(run_id)
        if event is None:
            raise KeyError("Replay run not found")
        event.set()
        return self.get_run(run_id)

    def get_run(self, run_id: str) -> Dict[str, Any]:
        with self._lock:
            if run_id not in self._runs:
                raise KeyError("Replay run not found")
            return dict(self._runs[run_id])

    def replay(
        self,
        *,
        local_id: str,
        dataset_path: str,
        index: str,
        hec_url: str,
        hec_token: str,
        timestamp_mode: str = "PRESERVE",
        allow_insecure_tls: bool = False,
        run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        validate_index_name(index)
        if timestamp_mode not in {"PRESERVE", "CURRENT"}:
            raise ValueError("Unsupported timestamp mode")
        dataset, file_record = self._validated_file(dataset_path)
        if not re.fullmatch(r"[a-f0-9]{64}", local_id):
            raise ValueError("Invalid local dataset identifier")
        expected_local_id = hashlib.sha256(file_record["path"].encode()).hexdigest()
        if local_id != expected_local_id:
            raise ValueError("Retrieved bytes do not match the selected dataset metadata")
        path = self.root / local_id
        if not path.is_file():
            raise FileNotFoundError("Dataset has not been retrieved")
        if path.stat().st_size > self.limits.max_bytes:
            raise ValueError("Dataset exceeds replay size limit")

        run_id = run_id or f"p13a-{uuid.uuid4()}"
        cancellation = threading.Event()
        with self._lock:
            self._cancellations[run_id] = cancellation
            self._runs[run_id] = {
                "run_id": run_id,
                "status": "RUNNING",
                "dataset_id": dataset["dataset_id"],
                "dataset_path": file_record["path"],
                "index": index,
                "source": file_record.get("source"),
                "sourcetype": file_record.get("sourcetype"),
                "timestamp_mode": timestamp_mode,
                "events_read": 0,
                "events_sent": 0,
                "errors": [],
                "provenance": "SPLUNK_ATTACK_DATA_REPLAY",
                "repository_commit": dataset["repository_commit"],
            }
        lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
        for line in lines[: self.limits.max_events]:
            if cancellation.is_set():
                with self._lock:
                    self._runs[run_id]["status"] = "CANCELLED"
                break
            if not line.strip():
                continue
            with self._lock:
                self._runs[run_id]["events_read"] += 1
            try:
                raw_event: Any = json.loads(line)
            except json.JSONDecodeError:
                raw_event = line
            payload: Dict[str, Any] = {
                "event": raw_event,
                "index": index,
                "source": file_record.get("source") or "netspout:attack-data",
                "sourcetype": file_record.get("sourcetype") or "_json",
                "fields": {
                    "netspout_run_id": run_id,
                    "netspout_evidence_path": "SPLUNK_ATTACK_DATA_REPLAY",
                    "netspout_upstream_commit": dataset["repository_commit"],
                },
            }
            if timestamp_mode == "CURRENT":
                payload["time"] = time.time()
            ok, detail = self.dispatcher.emit_hec(
                payload,
                hec_url,
                hec_token,
                ssl_verify=not allow_insecure_tls,
                allow_insecure_tls=allow_insecure_tls,
            )
            with self._lock:
                if ok:
                    self._runs[run_id]["events_sent"] += 1
                else:
                    self._runs[run_id]["errors"].append(detail)
        with self._lock:
            run = self._runs[run_id]
            if run["status"] == "RUNNING":
                run["status"] = "SENT" if not run["errors"] else "FAILED"
            return dict(run)

    def cleanup(self, local_id: str) -> None:
        if not re.fullmatch(r"[a-f0-9]{64}", local_id):
            raise ValueError("Invalid local dataset identifier")
        path = self.root / local_id
        if path.exists():
            path.unlink()


class DetectionEvidenceStore:
    def __init__(self, root: Optional[str] = None):
        base = Path(root or os.environ.get("NETSPOUT_CONFIG_DIR") or tempfile.gettempdir())
        self.root = base / "security-content-evidence"
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)

    def save(self, evidence: Dict[str, Any]) -> Dict[str, Any]:
        run_id = str(evidence["run_id"])
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", run_id):
            raise ValueError("Invalid evidence run ID")
        temporary = self.root / f"{run_id}.tmp"
        destination = self.root / f"{run_id}.json"
        temporary.write_text(
            json.dumps(evidence, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        os.chmod(temporary, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(temporary, destination)
        return evidence

    def list(self) -> List[Dict[str, Any]]:
        return [
            json.loads(path.read_text(encoding="utf-8"))
            for path in sorted(self.root.glob("*.json"))
        ]


class DetectionValidationOrchestrator:
    """Executes reviewed, read-only, run-scoped SPL through the shared search client."""

    def __init__(
        self,
        catalog: SecurityContentCatalog,
        search_executor: Callable[[str], Tuple[List[Dict[str, Any]], Optional[str]]],
        evidence_store: Optional[DetectionEvidenceStore] = None,
    ):
        self.catalog = catalog
        self.search_executor = search_executor
        self.evidence_store = evidence_store or DetectionEvidenceStore()

    def prepare_query(
        self, detection: Dict[str, Any], run_id: str, index: str
    ) -> Tuple[str, List[str]]:
        validate_index_name(index)
        if detection.get("content_id") not in SUPPORTED_RUNTIME_DETECTIONS:
            raise ValueError("Detection SPL has not been approved for bounded runtime execution")
        if not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", run_id):
            raise ValueError("Invalid run identifier")
        query = str(detection.get("spl") or "")
        macros = set(detection.get("dependencies", {}).get("macros", []))
        missing = sorted(macros - SUPPORTED_RUNTIME_MACROS)
        if missing:
            raise ValueError(f"Unresolved macros: {', '.join(missing)}")
        adaptations = []
        if "cisco_secure_firewall" in macros:
            scope = (
                f'search index="{index}" sourcetype="cisco:sfw:estreamer" '
                f'netspout_run_id="{run_id}" earliest=-15m latest=now '
                "| spath "
                "| eval signature_id=coalesce(signature_id,SignatureID), "
                "signature=coalesce(signature,IntrusionRuleMessage), "
                "src=coalesce(src,InitiatorIP), dest=coalesce(dest,ResponderIP), "
                "dest_port=coalesce(dest_port,ResponderPort), "
                "rule=coalesce(rule,FirewallRule), "
                "transport=coalesce(transport,Protocol), app=coalesce(app,Application) "
                "| search"
            )
            query = query.replace("`cisco_secure_firewall`", scope)
            adaptations.append("Expanded cisco_secure_firewall with run/index scope and JSON field aliases")
        query = re.sub(
            r"(?m)^\s*\|\s*`security_content_ctime\([^)]+\)`\s*$",
            "",
            query,
        )
        if "security_content_ctime" in macros:
            adaptations.append(
                "Removed display-only security_content_ctime formatting for portable execution"
            )
        query = re.sub(
            r"(?m)^\s*\|\s*"
            r"`cisco_secure_firewall___react_server_components_rce_attempt_filter`\s*$",
            "",
            query,
        )
        if "cisco_secure_firewall___react_server_components_rce_attempt_filter" in macros:
            adaptations.append("Expanded empty upstream filter macro")
        validate_read_only_spl(query)
        if run_id not in query or "earliest=" not in query.lower() or "latest=" not in query.lower():
            raise ValueError("Prepared SPL is not run and time scoped")
        return query, adaptations

    def validate(
        self,
        *,
        detection_id: str,
        run_id: str,
        index: str,
        expected_min_matches: int,
        control: str,
        dataset_or_scenario_id: str,
        indexed_event_count: int,
    ) -> Dict[str, Any]:
        if control not in {"POSITIVE", "NEGATIVE"}:
            raise ValueError("Control must be POSITIVE or NEGATIVE")
        detection = self.catalog.get_detection(detection_id)
        if detection is None:
            raise KeyError("Detection not found")
        try:
            query, adaptations = self.prepare_query(detection, run_id, index)
        except ValueError as exc:
            status = "DEPENDENCY_BLOCKED"
            rows: List[Dict[str, Any]] = []
            error = str(exc)
            adaptations = []
            query = ""
        else:
            rows, error = self.search_executor(query)
            if error:
                status = "SPL_EXECUTION_FAILED"
            elif rows:
                status = "EXECUTED_MATCHED"
            else:
                status = "EXECUTED_NO_MATCH"
        matched = len(rows)
        expected = (
            matched >= expected_min_matches
            if control == "POSITIVE"
            else matched == expected_min_matches
        )
        if status not in {"DEPENDENCY_BLOCKED", "SPL_EXECUTION_FAILED"}:
            if expected:
                status = (
                    "POSITIVE_CASE_VALIDATED"
                    if control == "POSITIVE"
                    else "NEGATIVE_CASE_VALIDATED"
                )
            else:
                status = "VALIDATION_FAILED"
        evidence = {
            "schema_version": "1.0.0",
            "run_id": run_id,
            "detection_id": detection["content_id"],
            "detection_catalog_key": detection["catalog_key"],
            "upstream_commit": detection["repository_commit"],
            "spl_hash": detection["spl_hash"],
            "executed_spl_hash": hashlib.sha256(query.encode()).hexdigest() if query else None,
            "dataset_or_scenario_id": dataset_or_scenario_id,
            "splunk_destination": "CONFIGURED_AUTHORIZED_DESTINATION",
            "search_job_id": None,
            "time_range": "-15m to now",
            "indexed_event_count": indexed_event_count,
            "matched_event_count": matched,
            "expected_result": {
                "control": control,
                "minimum_matches": expected_min_matches,
            },
            "actual_result": status,
            "negative_control": control == "NEGATIVE",
            "required_field_evidence": sorted(
                detection.get("dependencies", {}).get("required_fields", [])
            ),
            "adaptations": adaptations,
            "limitations": [
                "Synthetic or replay validation does not establish production detection efficacy.",
                "Search job ID is unavailable from the shared streaming export client.",
            ],
            "error": error,
            "status": status,
            "recorded_at": time.time(),
        }
        self.evidence_store.save(evidence)
        return evidence
