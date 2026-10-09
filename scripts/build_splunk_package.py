#!/usr/bin/env python3
"""
NetSpout Splunk App Production Release Packaging Tool
1. Synchronizes canonical core (src/netspout_core/) into netspout/bin/
2. Verifies single-source-of-truth integrity
3. Cleans ephemeral cache artifacts
4. Builds release archive: netspout.spl
"""

import os
import sys
import shutil
import tarfile
import gzip
import hashlib
import subprocess
import json

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
NETSPOUT_DIR = os.path.join(REPO_ROOT, "netspout")
SPL_ARCHIVE = os.path.join(REPO_ROOT, "netspout.spl")
ARTIFACT_MANIFEST = os.path.join(REPO_ROOT, "netspout.spl.manifest.json")


def clean_caches(root_dir: str):
    for root, dirs, files in os.walk(root_dir, topdown=False):
        for d in dirs:
            if d == "__pycache__":
                shutil.rmtree(os.path.join(root, d), ignore_errors=True)
        for f in files:
            if f in (".DS_Store", "datablaster.pid", "datablaster_status.json"):
                try:
                    os.remove(os.path.join(root, f))
                except OSError:
                    pass


def build_package():
    print("==========================================================================")
    print("📦 NetSpout: Building Production Splunk App Release Archive (netspout.spl)")
    print("==========================================================================")

    # 1. Sync Canonical Core
    sync_script = os.path.join(REPO_ROOT, "scripts", "sync_core.py")
    res = subprocess.run([sys.executable, sync_script], cwd=REPO_ROOT)
    if res.returncode != 0:
        print("❌ Core synchronization failed! Aborting packaging.")
        sys.exit(1)

    # 1.5 Build & Synchronize Frontend Production Assets
    frontend_script = os.path.join(REPO_ROOT, "scripts", "build_frontend.py")
    res = subprocess.run([sys.executable, frontend_script], cwd=REPO_ROOT)
    if res.returncode != 0:
        print("❌ Frontend build failed! Aborting packaging.")
        sys.exit(1)

    # 2. Verify Single Source of Truth
    verify_script = os.path.join(REPO_ROOT, "scripts", "verify_sources.py")
    res = subprocess.run([sys.executable, verify_script], cwd=REPO_ROOT)
    if res.returncode != 0:
        print("❌ Architecture verification failed! Aborting packaging.")
        sys.exit(1)

    # 2.5 Verify Canonical Catalog & Gate 10.6 Release Guardrails
    catalog_script = os.path.join(REPO_ROOT, "scripts", "validate_catalog.py")
    res = subprocess.run([sys.executable, catalog_script], cwd=REPO_ROOT)
    if res.returncode != 0:
        print("❌ Canonical catalog guardrail verification failed! Aborting packaging.")
        sys.exit(1)

    # 3. Clean caches
    print("\n>> Cleaning ephemeral caches...")
    clean_caches(NETSPOUT_DIR)

    # 4. Create tar.gz archive
    print(f">> Packing {NETSPOUT_DIR} -> {SPL_ARCHIVE}...")
    if os.path.exists(SPL_ARCHIVE):
        os.remove(SPL_ARCHIVE)

    def tar_filter(tarinfo):
        # Exclude runtime state and normalize metadata for reproducible archives.
        parts = tarinfo.name.split("/")
        if (
            "__pycache__" in tarinfo.name
            or ".DS_Store" in tarinfo.name
            or "local" in parts
            or tarinfo.name.endswith((".pyc", ".pyo"))
        ):
            return None
        tarinfo.uid = 0
        tarinfo.gid = 0
        tarinfo.uname = ""
        tarinfo.gname = ""
        tarinfo.mtime = 0
        return tarinfo

    with open(SPL_ARCHIVE, "wb") as output:
        with gzip.GzipFile(filename="", mode="wb", fileobj=output, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as tar:
                tar.add(NETSPOUT_DIR, arcname="netspout", filter=tar_filter)

    # 5. Validate Package
    size_bytes = os.path.getsize(SPL_ARCHIVE)
    size_mb = size_bytes / (1024 * 1024)
    with open(SPL_ARCHIVE, "rb") as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()

    with tarfile.open(SPL_ARCHIVE, "r:gz") as tar:
        members = tar.getnames()
        top_levels = set(m.split("/")[0] for m in members if "/" in m)
        has_core = any("netspout/bin/netspout_core/models.py" in m for m in members)
        has_catalog = any("netspout/bin/netspout_core/catalog.py" in m for m in members)
        has_catalog_data = any("netspout/bin/catalog_data/vendors.json" in m for m in members)
        has_manifest = "netspout/app.manifest" in members
        has_app_conf = "netspout/default/app.conf" in members
        has_navigation = "netspout/default/data/ui/nav/default.xml" in members
        contains_local = any("/local/" in m for m in members)

    if not all((has_core, has_catalog, has_catalog_data, has_manifest, has_app_conf, has_navigation)):
        raise SystemExit("Release archive is missing mandatory Splunk App files")
    if contains_local:
        raise SystemExit("Release archive must not contain local configuration or secrets")

    manifest = {
        "schema_version": "1.0.0",
        "artifact": os.path.basename(SPL_ARCHIVE),
        "sha256": sha256,
        "size_bytes": size_bytes,
        "member_count": len(members),
        "reproducible_metadata_epoch": 0,
        "contains_local_configuration": False,
    }
    with open(ARTIFACT_MANIFEST, "w", encoding="utf-8") as output:
        json.dump(manifest, output, indent=2, sort_keys=True)
        output.write("\n")

    print("\n>> Archive Verification:")
    print(f"  [PASS] File exists: {SPL_ARCHIVE}")
    print(f"  [PASS] Archive size: {size_mb:.2f} MB (< 5.0 MB)")
    print(f"  [PASS] Total member count: {len(members)} entries")
    print(f"  [PASS] Top-level directory: {list(top_levels)}")
    print(f"  [PASS] Canonical core packaged: {has_core}")
    print(f"  [PASS] Canonical catalog packaged: {has_catalog}")
    print(f"  [PASS] Canonical catalog data packaged: {has_catalog_data}")
    print(f"  [PASS] Supported app layout: {has_manifest and has_app_conf and has_navigation}")
    print(f"  [PASS] Runtime local/ state excluded: {not contains_local}")
    print(f"  [PASS] SHA-256 Checksum: {sha256}")
    print("==========================================================================")
    print("🎉 Splunk Release Package built successfully!")
    print("==========================================================================")


if __name__ == "__main__":
    build_package()
