#!/usr/bin/env python3
"""
NetSpout Canonical Core Synchronization Tool
Authoritative Source: src/netspout_core/

Replicates canonical modules into:
1. netspout/bin/netspout_core/ (packaged copy for Splunk runtime, exact SHA256)
2. netspout/bin/*.py (packaged copies for Splunk runtime with auto-generated header)
3. backend/app/*.py (runtime copies for FastAPI backend with auto-generated header)

Enforces:
- Single Source of Truth under src/netspout_core/
- Deterministic, verifiable generation across all deployment targets
"""

import os
import sys
import shutil

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_CORE_DIR = os.path.join(REPO_ROOT, "src", "netspout_core")
SPLUNK_BIN_DIR = os.path.join(REPO_ROOT, "netspout", "bin")
SPLUNK_CORE_DIR = os.path.join(SPLUNK_BIN_DIR, "netspout_core")
BACKEND_APP_DIR = os.path.join(REPO_ROOT, "backend", "app")

CORE_MODULES = [
    "models.py",
    "graph_engine.py",
    "log_engine.py",
    "scenario_runner.py",
    "snmp_engine.py",
    "gnmi_engine.py",
    "fault_injection_engine.py",
    "telemetry_dispatcher.py",
    "cisco_sample_provider.py",
    "spl_engine.py",
    "use_case_repo.py",
    "noc_soc_metrics.py",
    "catalog.py",
    "vendor_catalog.py"
]

CANONICAL_CATALOG_DIR = os.path.join(REPO_ROOT, "catalog")
VENDOR_STATIC_JSON = os.path.join(REPO_ROOT, "netspout", "appserver", "static", "vendor_catalog.json")

GENERATED_HEADER = """# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/{mod}
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""


def sync_core():
    print(f"⚡ NetSpout: Synchronizing Canonical Core from {SRC_CORE_DIR}...")
    os.makedirs(SPLUNK_CORE_DIR, exist_ok=True)

    # 1. Sync __init__.py into SPLUNK_CORE_DIR
    src_init = os.path.join(SRC_CORE_DIR, "__init__.py")
    dst_init = os.path.join(SPLUNK_CORE_DIR, "__init__.py")
    shutil.copy2(src_init, dst_init)

    # 2. Sync exact canonical modules into netspout/bin/netspout_core/
    for mod in CORE_MODULES:
        src_path = os.path.join(SRC_CORE_DIR, mod)
        if not os.path.exists(src_path):
            print(f"❌ Error: Missing canonical module {src_path}")
            sys.exit(1)
        dst_path = os.path.join(SPLUNK_CORE_DIR, mod)
        shutil.copy2(src_path, dst_path)
        print(f"  [CORE_COPY] {mod} -> netspout/bin/netspout_core/{mod}")

    # 3. Generate packaged copies in netspout/bin/ with auto-generated header
    for mod in CORE_MODULES:
        src_path = os.path.join(SRC_CORE_DIR, mod)
        dst_path = os.path.join(SPLUNK_BIN_DIR, mod)
        with open(src_path, "r", encoding="utf-8") as f:
            code = f.read()
        header = GENERATED_HEADER.format(mod=mod)
        with open(dst_path, "w", encoding="utf-8") as f:
            f.write(header + code)
        print(f"  [SPLUNK_COPY] netspout/bin/{mod}")

    # 4. Generate runtime copies in backend/app/ with auto-generated header
    for mod in CORE_MODULES:
        src_path = os.path.join(SRC_CORE_DIR, mod)
        dst_path = os.path.join(BACKEND_APP_DIR, mod)
        with open(src_path, "r", encoding="utf-8") as f:
            code = f.read()
        header = GENERATED_HEADER.format(mod=mod)
        with open(dst_path, "w", encoding="utf-8") as f:
            f.write(header + code)
        print(f"  [BACKEND_COPY] backend/app/{mod}")

    # 5. Sync Canonical Catalog JSON files
    catalog_targets = [
        os.path.join(SPLUNK_CORE_DIR, "catalog_data"),
        os.path.join(SPLUNK_BIN_DIR, "catalog_data"),
        os.path.join(BACKEND_APP_DIR, "catalog_data"),
        os.path.join(REPO_ROOT, "netspout", "catalog")
    ]
    if os.path.isdir(CANONICAL_CATALOG_DIR):
        json_files = [f for f in os.listdir(CANONICAL_CATALOG_DIR) if f.endswith(".json")]
        for target in catalog_targets:
            os.makedirs(target, exist_ok=True)
            for jf in json_files:
                src_json = os.path.join(CANONICAL_CATALOG_DIR, jf)
                dst_json = os.path.join(target, jf)
                shutil.copy2(src_json, dst_json)
            print(f"  [CATALOG_SYNC] {len(json_files)} catalog JSONs -> {os.path.relpath(target, REPO_ROOT)}")

    # 6. Generate netspout/appserver/static/vendor_catalog.json from Canonical Catalog
    try:
        sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
        from netspout_core.catalog import NetSpoutCatalog
        cat = NetSpoutCatalog(catalog_dir=CANONICAL_CATALOG_DIR)
        legacy_vendors = cat.get_legacy_vendor_catalog()
        os.makedirs(os.path.dirname(VENDOR_STATIC_JSON), exist_ok=True)
        import json
        with open(VENDOR_STATIC_JSON, "w", encoding="utf-8") as f:
            json.dump(legacy_vendors, f, indent=2)
            f.write("\n")
        print(f"  [VENDOR_JSON] Generated {VENDOR_STATIC_JSON} ({len(legacy_vendors)} vendors)")
    except Exception as e:
        print(f"  ⚠️ Warning: Could not re-generate vendor_catalog.json: {e}")

    print("✅ Canonical Core synchronization complete.")


if __name__ == "__main__":
    sync_core()
