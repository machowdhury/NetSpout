#!/usr/bin/env python3
"""Build a pinned, metadata-only Splunk Security Content/Attack Data snapshot."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "catalog" / "phase13a_splunk_security_content.json"
MAX_METADATA_BYTES = 2 * 1024 * 1024


def git_value(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True
    ).strip()


def content_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    size = path.stat().st_size
    if size > MAX_METADATA_BYTES:
        raise ValueError(f"metadata exceeds {MAX_METADATA_BYTES} bytes")
    value = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("top-level YAML value must be an object")
    return value


def normalize_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


def discover_yaml(
    repo: Path, directory: str
) -> tuple[list[tuple[Path, dict[str, Any]]], list[dict[str, str]]]:
    records: list[tuple[Path, dict[str, Any]]] = []
    failures: list[dict[str, str]] = []
    for path in sorted((repo / directory).rglob("*.yml")):
        try:
            records.append((path, load_yaml(path)))
        except Exception as exc:
            failures.append(
                {
                    "path": path.relative_to(repo).as_posix(),
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    return records, failures


def extract_dependencies(search: str, data_sources: list[dict[str, Any]]) -> dict[str, Any]:
    import re

    macros = sorted(set(re.findall(r"`([A-Za-z0-9_.-]+)(?:\([^`]*)?\s*`", search)))
    data_models = sorted(
        set(
            re.findall(
                r"(?i)(?:datamodel\s*=\s*|from\s+datamodel\s+)([A-Za-z0-9_.-]+)",
                search,
            )
        )
    )
    lookups = sorted(
        set(
            re.findall(
                r"(?im)^\s*\|\s*(?:inputlookup|lookup)\s+([A-Za-z0-9_.-]+)",
                search,
            )
        )
    )
    commands = sorted(
        set(re.findall(r"(?m)^\s*\|\s*([A-Za-z][A-Za-z0-9_]*)", search))
    )
    sourcetypes = sorted(
        {
            str(source.get("sourcetype"))
            for source in data_sources
            if source.get("sourcetype")
        }
    )
    required_fields = sorted(
        {
            str(field)
            for source in data_sources
            for field in normalize_list(source.get("output_fields") or source.get("fields"))
            if field
        }
    )
    required_tas = sorted(
        {
            str(ta.get("name"))
            for source in data_sources
            for ta in normalize_list(source.get("supported_TA"))
            if isinstance(ta, dict) and ta.get("name")
        }
    )
    unresolved = []
    if not data_sources:
        unresolved.append("No authoritative data-source object resolved")
    if search and not (sourcetypes or data_models or macros):
        unresolved.append("SPL requirements cannot be resolved conservatively")
    return {
        "indexes": sorted(set(re.findall(r"(?i)\bindex\s*=\s*[\"']?([A-Za-z0-9_-]+)", search))),
        "sourcetypes": sourcetypes,
        "required_fields": required_fields,
        "data_models": data_models,
        "macros": macros,
        "lookups": lookups,
        "kv_store": [],
        "supporting_apps": [],
        "technology_add_ons": required_tas,
        "risk_based_alerting": "risk" in search.lower(),
        "required_enrichment": lookups,
        "search_commands": commands,
        "time_window": "DEFINED_AT_EXECUTION",
        "resolution": "DEPENDENCY_UNRESOLVED" if unresolved else "RESOLVED",
        "unresolved_reasons": unresolved,
        "parser_scope": "Conservative lexical parsing plus authoritative data-source relationships; not full SPL semantics.",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--security-content", type=Path, required=True)
    parser.add_argument("--attack-data", type=Path, required=True)
    parser.add_argument("--attack-stix", type=Path, required=True)
    parser.add_argument("--contentctl", type=Path, required=True)
    parser.add_argument("--attack-range", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()

    security_repo = args.security_content.resolve()
    attack_repo = args.attack_data.resolve()
    attack_stix_repo = args.attack_stix.resolve()
    contentctl_repo = args.contentctl.resolve()
    attack_range_repo = args.attack_range.resolve()
    security_sha = git_value(security_repo, "rev-parse", "HEAD")
    attack_sha = git_value(attack_repo, "rev-parse", "HEAD")
    attack_stix_sha = git_value(attack_stix_repo, "rev-parse", "HEAD")
    contentctl_sha = git_value(contentctl_repo, "rev-parse", "HEAD")
    attack_range_sha = git_value(attack_range_repo, "rev-parse", "HEAD")
    security_branch = git_value(security_repo, "branch", "--show-current")
    attack_branch = git_value(attack_repo, "branch", "--show-current")
    attack_stix_branch = git_value(attack_stix_repo, "branch", "--show-current")
    contentctl_branch = git_value(contentctl_repo, "branch", "--show-current")
    attack_range_branch = git_value(attack_range_repo, "branch", "--show-current")

    attack_bundle = json.loads(
        (attack_stix_repo / "enterprise-attack" / "enterprise-attack.json").read_text(
            encoding="utf-8"
        )
    )
    mitre_techniques = []
    for item in attack_bundle.get("objects", []):
        if item.get("type") != "attack-pattern":
            continue
        external = next(
            (
                reference
                for reference in item.get("external_references", [])
                if reference.get("source_name") == "mitre-attack"
                and str(reference.get("external_id", "")).startswith("T")
            ),
            None,
        )
        if not external:
            continue
        mitre_techniques.append(
            {
                "technique_id": external["external_id"],
                "name": item.get("name"),
                "description": item.get("description"),
                "url": external.get("url"),
                "tactics": sorted(
                    {
                        phase.get("phase_name")
                        for phase in item.get("kill_chain_phases", [])
                        if phase.get("phase_name")
                    }
                ),
                "is_subtechnique": bool(item.get("x_mitre_is_subtechnique")),
                "revoked": bool(item.get("revoked")),
                "deprecated": bool(item.get("x_mitre_deprecated")),
                "modified": item.get("modified"),
            }
        )
    mitre_techniques.sort(key=lambda item: item["technique_id"])

    categories: dict[str, list[tuple[Path, dict[str, Any]]]] = {}
    parse_failures: list[dict[str, str]] = []
    for category in ("detections", "stories", "data_sources", "macros", "lookups", "baselines"):
        records, failures = discover_yaml(security_repo, category)
        categories[category] = records
        parse_failures.extend(
            {"repository": "splunk/security_content", **item} for item in failures
        )
    dataset_records, dataset_failures = discover_yaml(attack_repo, "datasets")
    parse_failures.extend(
        {"repository": "splunk/attack_data", **item} for item in dataset_failures
    )

    duplicate_ids: list[dict[str, str]] = []
    seen: dict[tuple[str, str], str] = {}

    def identify(repository: str, category: str, path: Path, item: dict[str, Any]) -> str:
        content_id = str(item.get("id") or "").strip()
        if not content_id:
            content_id = f"path:{path.as_posix()}"
        key = (category, content_id)
        relative = path.as_posix()
        if key in seen:
            duplicate_ids.append(
                {
                    "repository": repository,
                    "category": category,
                    "content_id": content_id,
                    "first_path": seen[key],
                    "duplicate_path": relative,
                }
            )
        else:
            seen[key] = relative
        return content_id

    data_sources: list[dict[str, Any]] = []
    data_source_by_name: dict[str, dict[str, Any]] = {}
    for path, item in categories["data_sources"]:
        relative = path.relative_to(security_repo)
        normalized = {
            "content_id": identify(
                "splunk/security_content", "data_source", relative, item
            ),
            "name": item.get("name"),
            "description": item.get("description"),
            "source": item.get("source"),
            "sourcetype": item.get("sourcetype"),
            "fields": normalize_list(item.get("fields")),
            "output_fields": normalize_list(item.get("output_fields")),
            "supported_TA": normalize_list(item.get("supported_TA")),
            "field_mappings": normalize_list(item.get("field_mappings")),
            "file_path": relative.as_posix(),
            "content_hash": content_hash(path),
        }
        data_sources.append(normalized)
        if normalized["name"]:
            data_source_by_name[str(normalized["name"])] = normalized

    detections: list[dict[str, Any]] = []
    associated_dataset_urls: dict[str, list[str]] = {}
    for path, item in categories["detections"]:
        relative = path.relative_to(security_repo)
        source_names = [str(value) for value in normalize_list(item.get("data_source"))]
        resolved_sources = [
            data_source_by_name[name] for name in source_names if name in data_source_by_name
        ]
        attack_data = []
        for test in normalize_list(item.get("tests")):
            if not isinstance(test, dict):
                continue
            for evidence in normalize_list(test.get("attack_data")):
                if isinstance(evidence, dict) and evidence.get("data"):
                    attack_data.append(
                        {
                            "url": str(evidence["data"]),
                            "source": evidence.get("source"),
                            "sourcetype": evidence.get("sourcetype"),
                            "test_type": test.get("test_type"),
                            "test_name": test.get("name"),
                        }
                    )
        detection_id = identify(
            "splunk/security_content", "detection", relative, item
        )
        associated_dataset_urls[detection_id] = [
            record["url"] for record in attack_data
        ]
        search = str(item.get("search") or "")
        detections.append(
            {
                "catalog_key": f"detection:{detection_id}:{relative.as_posix()}",
                "content_id": detection_id,
                "name": item.get("name"),
                "description": item.get("description"),
                "category": item.get("category"),
                "security_domain": item.get("security_domain"),
                "detection_type": item.get("type"),
                "status": item.get("status"),
                "version": item.get("version"),
                "author": item.get("author"),
                "creation_date": str(item.get("creation_date") or ""),
                "modification_date": str(item.get("modification_date") or ""),
                "analytic_stories": normalize_list(item.get("analytic_story")),
                "mitre_attack_ids": normalize_list(item.get("mitre_attack_id")),
                "data_source_names": source_names,
                "products": normalize_list(item.get("product")),
                "how_to_implement": item.get("how_to_implement"),
                "known_false_positives": item.get("known_false_positives"),
                "spl": search,
                "spl_hash": hashlib.sha256(search.encode()).hexdigest(),
                "dependencies": extract_dependencies(search, resolved_sources),
                "attack_data": attack_data,
                "file_path": relative.as_posix(),
                "repository": "https://github.com/splunk/security_content",
                "repository_commit": security_sha,
                "license": "Apache-2.0 (repository); embedded assets require individual review",
                "content_hash": content_hash(path),
                "validation_status": "NOT_TESTED",
            }
        )

    stories = []
    for path, item in categories["stories"]:
        relative = path.relative_to(security_repo)
        stories.append(
            {
                "content_id": identify(
                    "splunk/security_content", "analytic_story", relative, item
                ),
                "name": item.get("name"),
                "description": item.get("description"),
                "narrative": item.get("narrative"),
                "detections": normalize_list(item.get("detections")),
                "investigations": normalize_list(item.get("investigations")),
                "file_path": relative.as_posix(),
                "content_hash": content_hash(path),
            }
        )

    simple_categories: dict[str, list[dict[str, Any]]] = {}
    for category in ("macros", "lookups", "baselines"):
        values = []
        for path, item in categories[category]:
            relative = path.relative_to(security_repo)
            values.append(
                {
                    "content_id": identify(
                        "splunk/security_content", category[:-1], relative, item
                    ),
                    "name": item.get("name"),
                    "description": item.get("description"),
                    "definition": item.get("definition"),
                    "file_path": relative.as_posix(),
                    "content_hash": content_hash(path),
                }
            )
        simple_categories[category] = values

    datasets = []
    dataset_paths: dict[str, dict[str, Any]] = {}
    for path, item in dataset_records:
        if path.name == "TEMPLATE.yml":
            continue
        relative = path.relative_to(attack_repo)
        dataset_id = identify(
            "splunk/attack_data", "dataset_manifest", relative, item
        )
        files = []
        for record in normalize_list(item.get("datasets")):
            if not isinstance(record, dict) or not record.get("path"):
                continue
            dataset_path = "/" + str(record["path"]).lstrip("/")
            file_path = attack_repo / dataset_path.lstrip("/")
            size = None
            lfs_oid = None
            if file_path.is_file():
                pointer = file_path.read_text(encoding="utf-8", errors="ignore")
                if pointer.startswith("version https://git-lfs.github.com/spec/v1"):
                    for line in pointer.splitlines():
                        if line.startswith("oid sha256:"):
                            lfs_oid = line.partition(":")[2]
                        elif line.startswith("size "):
                            size = int(line.partition(" ")[2])
                else:
                    size = file_path.stat().st_size
            normalized_file = {
                "name": record.get("name"),
                "path": dataset_path,
                "format": Path(dataset_path).suffix.lower().lstrip(".") or "unknown",
                "source": record.get("source"),
                "sourcetype": record.get("sourcetype"),
                "size_bytes": size,
                "sha256": lfs_oid,
                "download_url": (
                    "https://media.githubusercontent.com/media/splunk/attack_data/"
                    f"{attack_sha}{dataset_path}"
                ),
            }
            files.append(normalized_file)
            dataset_paths[dataset_path] = normalized_file
        datasets.append(
            {
                "catalog_key": f"dataset:{dataset_id}:{relative.as_posix()}",
                "dataset_id": dataset_id,
                "name": item.get("directory") or path.parent.name,
                "description": item.get("description"),
                "author": item.get("author"),
                "date": str(item.get("date") or ""),
                "environment": item.get("environment"),
                "mitre_techniques": normalize_list(item.get("mitre_technique")),
                "files": files,
                "file_path": relative.as_posix(),
                "repository": "https://github.com/splunk/attack_data",
                "repository_commit": attack_sha,
                "license": "Apache-2.0 (repository); each embedded asset requires review",
                "content_hash": content_hash(path),
                "redistribution_decision": "REFERENCE_ONLY_PENDING_HUMAN_REVIEW",
            }
        )

    document = {
        "schema_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "sync_policy": {
            "mode": "METADATA_ONLY",
            "automatic_sync": False,
            "bulk_lfs_download": False,
            "dataset_retrieval": "EXPLICIT_SELECTION_ONLY",
        },
        "upstreams": {
            "security_content": {
                "repository": "https://github.com/splunk/security_content",
                "branch": security_branch,
                "commit": security_sha,
                "license": "Apache-2.0",
            },
            "attack_data": {
                "repository": "https://github.com/splunk/attack_data",
                "branch": attack_branch,
                "commit": attack_sha,
                "license": "Apache-2.0",
            },
            "mitre_attack": {
                "repository": "https://github.com/mitre-attack/attack-stix-data",
                "branch": attack_stix_branch,
                "commit": attack_stix_sha,
                "license": "MITRE ATT&CK Terms of Use",
                "copyright": (
                    "© 2026 The MITRE Corporation. This work is reproduced and "
                    "distributed with the permission of The MITRE Corporation."
                ),
            },
            "contentctl": {
                "repository": "https://github.com/splunk/contentctl",
                "branch": contentctl_branch,
                "commit": contentctl_sha,
                "usage": "SCHEMA_AND_TOOLING_REFERENCE",
            },
            "attack_range": {
                "repository": "https://github.com/splunk/attack_range",
                "branch": attack_range_branch,
                "commit": attack_range_sha,
                "usage": "ARCHITECTURE_REFERENCE_ONLY",
            },
        },
        "summary": {
            "security_content_items": (
                len(detections)
                + len(stories)
                + len(data_sources)
                + sum(len(value) for value in simple_categories.values())
            ),
            "detections": len(detections),
            "analytic_stories": len(stories),
            "data_sources": len(data_sources),
            "macros": len(simple_categories["macros"]),
            "lookups": len(simple_categories["lookups"]),
            "baselines": len(simple_categories["baselines"]),
            "attack_dataset_manifests": len(datasets),
            "attack_dataset_files": sum(len(item["files"]) for item in datasets),
            "parse_failures": len(parse_failures),
            "duplicate_ids": len(duplicate_ids),
            "mitre_enterprise_techniques": len(mitre_techniques),
        },
        "detections": detections,
        "analytic_stories": stories,
        "data_sources": data_sources,
        "datasets": datasets,
        "mitre_techniques": mitre_techniques,
        **simple_categories,
        "parse_failures": parse_failures,
        "duplicate_ids": duplicate_ids,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, separators=(",", ":"), sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(document["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
