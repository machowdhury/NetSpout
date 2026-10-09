#!/usr/bin/env python3
"""Generate local Phase 13 release-candidate supply-chain and audit evidence."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from artifact_isolation import protected_roots, snapshot_files


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / ".artifacts" / "phase13-current" / "release"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write(name: str, value: Any) -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / name).write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def python_components() -> list[dict[str, str]]:
    components = []
    for line in (ROOT / "backend" / "requirements.txt").read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        name, version = line.split("==", 1)
        components.append({"type": "library", "name": name, "version": version, "ecosystem": "PyPI"})
    return components


def npm_components() -> list[dict[str, str]]:
    lock = json.loads((ROOT / "frontend" / "package-lock.json").read_text(encoding="utf-8"))
    components = []
    for package_path, metadata in lock.get("packages", {}).items():
        if not package_path.startswith("node_modules/") or not metadata.get("version"):
            continue
        components.append(
            {
                "type": "library",
                "name": package_path.removeprefix("node_modules/"),
                "version": metadata["version"],
                "ecosystem": "npm",
                "license": metadata.get("license", "NOT_DECLARED"),
            }
        )
    return components


def image_inventory() -> list[dict[str, str]]:
    files = [
        ROOT / "Dockerfile.standalone",
        ROOT / "docker-compose.yml",
        ROOT / "docker-compose.standalone.yml",
        ROOT / "deploy" / "collector" / "Dockerfile.forwarder",
        ROOT / "deploy" / "collector" / "docker-compose.collector.yml",
    ]
    pattern = re.compile(
        r"^(?:FROM(?:\s+--platform=\S+)?|\s*image:)\s+([^\s]+)",
        re.IGNORECASE | re.MULTILINE,
    )
    images: dict[str, dict[str, str]] = {}
    for path in files:
        for match in pattern.finditer(path.read_text(encoding="utf-8")):
            ref = match.group(1)
            if ref.startswith(("$", "scratch")):
                continue
            images[ref] = {
                "reference": ref,
                "source_file": str(path.relative_to(ROOT)),
                "digest_pinned": "@sha256:" in ref,
            }
    return sorted(images.values(), key=lambda item: item["reference"])


def operational_secret_scan() -> dict[str, Any]:
    tracked = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    active_roots = (
        "backend/",
        "src/",
        "scripts/",
        "deploy/",
        "docker/",
        "frontend/src/",
        "netspout/bin/",
        "netspout/default/",
        "netspout/appserver/static/",
        "entrypoint-standalone.sh",
        "docker-compose",
        "Dockerfile",
        "otel-collector",
    )
    patterns = {
        "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        "provider_token": re.compile(r"(?:AKIA|ASIA|gh[pousr]_|sk_live_|AIza)[A-Za-z0-9_-]{12,}"),
        "legacy_lab_secret": re.compile(
            r"SplunkPassword123!|(?:token|password)[^\n]{0,80}00000000-0000-0000-0000-000000000000",
            re.IGNORECASE,
        ),
    }
    findings = []
    for relative in tracked:
        if relative == "scripts/run_phase13_release_audit.py":
            continue
        if not relative.startswith(active_roots):
            continue
        path = ROOT / relative
        if not path.is_file() or path.stat().st_size > 3_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for pattern_id, pattern in patterns.items():
            if pattern.search(text):
                findings.append({"path": relative, "pattern": pattern_id})
    return {"status": "PASS" if not findings else "FAIL", "findings": findings}


def privacy_provenance_scan() -> dict[str, Any]:
    files = subprocess.check_output(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    emails = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
    ipv4s = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    uuids = re.compile(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
        re.IGNORECASE,
    )
    candidate_paths: dict[str, set[str]] = {
        "email": set(),
        "public_ip": set(),
        "uuid": set(),
    }
    opaque_binary_paths = []
    for relative in files:
        path = ROOT / relative
        if not path.is_file() or path.stat().st_size > 3_000_000:
            continue
        if path.suffix.lower() in {".pcap", ".pcapng", ".cap", ".der", ".bin"}:
            opaque_binary_paths.append(relative)
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if emails.search(text):
            candidate_paths["email"].add(relative)
        if uuids.search(text):
            candidate_paths["uuid"].add(relative)
        for value in ipv4s.findall(text):
            try:
                address = ipaddress.ip_address(value)
            except ValueError:
                continue
            if not (
                address.is_private
                or address.is_loopback
                or address.is_link_local
                or address.is_multicast
                or address.is_unspecified
                or address in ipaddress.ip_network("192.0.2.0/24")
                or address in ipaddress.ip_network("198.51.100.0/24")
                or address in ipaddress.ip_network("203.0.113.0/24")
            ):
                candidate_paths["public_ip"].add(relative)
    normalized = {
        kind: sorted(paths) for kind, paths in candidate_paths.items()
    }
    return {
        "status": "REQUIRES_HUMAN_REVIEW",
        "candidate_path_counts": {
            kind: len(paths) for kind, paths in normalized.items()
        },
        "candidate_paths": normalized,
        "opaque_binary_paths": sorted(opaque_binary_paths),
        "git_history_review": "PARTIAL_AUTOMATED_SECRET_PATTERNS_ONLY",
        "limitations": [
            "Pattern matches are review candidates, not proof of personal or customer data.",
            "Automated scanning cannot establish ownership or redistribution rights.",
            "Unknown opaque binary formats must remain blocked until manually reviewed.",
        ],
    }


def main() -> int:
    before = snapshot_files(protected_roots(ROOT))
    package = ROOT / "netspout.spl"
    if not package.is_file():
        raise SystemExit("Build netspout.spl before running the release audit")

    components = python_components() + npm_components()
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": "urn:uuid:netspout-phase13-local",
        "version": 1,
        "metadata": {"component": {"type": "application", "name": "NetSpout", "version": "1.0.0-rc"}},
        "components": components,
        "limitations": ["Locally generated dependency inventory; no signature or external attestation."],
    }
    write("netspout-phase13-sbom.cdx.json", sbom)
    write("container-images.json", {"images": image_inventory()})
    write(
        "artifact-checksums.json",
        {
            "artifacts": [
                {
                    "path": "netspout.spl",
                    "sha256": sha256(package),
                    "size_bytes": package.stat().st_size,
                }
            ]
        },
    )
    write("security-scan.json", operational_secret_scan())
    write("privacy-provenance-audit.json", privacy_provenance_scan())
    after = snapshot_files(protected_roots(ROOT))
    mutations = {
        path: {"before": before.get(path), "after": after.get(path)}
        for path in sorted(set(before) | set(after))
        if before.get(path) != after.get(path)
    }
    write(
        "protected-artifacts.json",
        {
            "before": len(before),
            "after": len(after),
            "mutations_during_audit": mutations,
        },
    )
    write(
        "release-audit-summary.json",
        {
            "sbom_components": len(components),
            "security_scan": operational_secret_scan(),
            "protected_artifact_count": len(after),
            "protected_mutations_during_audit": len(mutations),
            "human_approval_required": [
                "Employer and contributor intellectual-property approval",
                "Third-party sample redistribution and legal review",
                "Splunk AppInspect/Splunkbase or Splunk Cloud vetting",
                "Owner authorization to publish V1.0",
            ],
        },
    )
    print(f"Phase 13 release audit evidence: {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
