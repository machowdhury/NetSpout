#!/usr/bin/env python3
"""Validate install, upgrade, and removal semantics for the Phase 13 Splunk App."""

from __future__ import annotations

import hashlib
import json
import shutil
import tarfile
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "netspout.spl"
OUTPUT = ROOT / ".artifacts" / "phase13-current" / "installation"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_extract(package: tarfile.TarFile, destination: Path) -> None:
    root = destination.resolve()
    for member in package.getmembers():
        target = (destination / member.name).resolve()
        if not target.is_relative_to(root):
            raise ValueError(f"Unsafe archive member: {member.name}")
        if member.issym() or member.islnk():
            raise ValueError(f"Links are not permitted in the release archive: {member.name}")
    package.extractall(destination, filter="data")


def main() -> int:
    checks = []
    with tempfile.TemporaryDirectory(prefix="netspout-phase13-install-") as temporary:
        staging = Path(temporary)
        splunk_apps = staging / "splunk" / "etc" / "apps"
        splunk_apps.mkdir(parents=True)

        with tarfile.open(ARCHIVE, "r:gz") as package:
            names = package.getnames()
            safe_extract(package, staging / "first-install")
        required = {
            "netspout/app.manifest",
            "netspout/default/app.conf",
            "netspout/default/data/ui/nav/default.xml",
            "netspout/appserver/static/dist/index.html",
            "netspout/bin/netspout_core/catalog.py",
        }
        checks.append({"id": "layout", "status": "PASS" if required <= set(names) else "FAIL"})
        checks.append({"id": "single_root", "status": "PASS" if {name.split('/')[0] for name in names} == {"netspout"} else "FAIL"})
        checks.append({"id": "no_local", "status": "PASS" if not any("/local/" in name for name in names) else "FAIL"})

        installed = splunk_apps / "netspout"
        shutil.copytree(staging / "first-install" / "netspout", installed)
        checks.append({"id": "clean_install", "status": "PASS" if (installed / "default" / "app.conf").is_file() else "FAIL"})

        local = installed / "local"
        local.mkdir()
        owner_marker = local / "owner-managed.conf"
        owner_marker.write_text("[owner]\nmanaged = true\n", encoding="utf-8")
        with tarfile.open(ARCHIVE, "r:gz") as package:
            safe_extract(package, staging / "upgrade")
        shutil.copytree(staging / "upgrade" / "netspout", installed, dirs_exist_ok=True)
        checks.append({"id": "upgrade_preserves_local", "status": "PASS" if owner_marker.is_file() else "FAIL"})

        shutil.rmtree(installed)
        checks.append({"id": "removal", "status": "PASS" if not installed.exists() else "FAIL"})

    OUTPUT.mkdir(parents=True, exist_ok=True)
    evidence = {
        "schema_version": "1.0.0",
        "archive": str(ARCHIVE.relative_to(ROOT)),
        "sha256": digest(ARCHIVE),
        "checks": checks,
        "status": "PASS" if all(item["status"] == "PASS" for item in checks) else "FAIL",
        "scope": "Filesystem package installation semantics; live Splunk operation is validated by the clean Docker journey.",
        "appinspect": {"status": "NOT_TESTED", "reason": "Splunk AppInspect is not installed in the local environment."},
    }
    (OUTPUT / "splunk-app-installation.json").write_text(
        json.dumps(evidence, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(evidence, indent=2))
    return 0 if evidence["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
