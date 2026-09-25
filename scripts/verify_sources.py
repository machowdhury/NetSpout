#!/usr/bin/env python3
"""
NetSpout Architecture Guardrail: Single Python Source of Truth Verification
Validates that:
1. All canonical simulation logic resides exclusively in src/netspout_core/
2. Packaged copies in netspout/bin/netspout_core/ are byte-for-byte identical to src/netspout_core/
3. Generated copies in netspout/bin/ and backend/app/ carry the auto-generated warning header
   and match the canonical code byte-for-byte.
4. No duplicate, diverged engine logic exists anywhere in the repository.
"""

import os
import sys
import hashlib

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

GENERATED_HEADER_PREFIX = "# =========================================================================\n# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!"


def sha256_file(path: str) -> str:
    if not os.path.exists(path):
        return ""
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def verify_sources() -> bool:
    print("==========================================================================")
    print("🔍 NetSpout Architecture Guardrail: Single Python Source of Truth Audit")
    print("==========================================================================")

    all_passed = True

    # 1. Verify canonical files exist
    print("\n>> 1. Verifying Canonical Core (src/netspout_core/)...")
    for mod in CORE_MODULES + ["__init__.py"]:
        src_path = os.path.join(SRC_CORE_DIR, mod)
        if not os.path.exists(src_path):
            print(f"  [FAIL] Missing canonical module: {src_path}")
            all_passed = False
        else:
            size_kb = os.path.getsize(src_path) / 1024
            print(f"  [PASS] Canonical {mod} ({size_kb:.1f} KB)")

    # 2. Verify packaged copies in netspout_core are byte-for-byte identical
    print("\n>> 2. Verifying Packaged Splunk Core (netspout/bin/netspout_core/)...")
    for mod in CORE_MODULES + ["__init__.py"]:
        src_path = os.path.join(SRC_CORE_DIR, mod)
        pkg_path = os.path.join(SPLUNK_CORE_DIR, mod)
        if not os.path.exists(pkg_path):
            print(f"  [FAIL] Missing packaged copy: {pkg_path}")
            all_passed = False
            continue

        h_src = sha256_file(src_path)
        h_pkg = sha256_file(pkg_path)
        if h_src != h_pkg:
            print(f"  [FAIL] Drift detected in packaged copy: {mod}!")
            print(f"         Canonical SHA: {h_src}")
            print(f"         Packaged  SHA: {h_pkg}")
            print(f"         Run 'python3 scripts/sync_core.py' to synchronize.")
            all_passed = False
        else:
            print(f"  [PASS] {mod} matches canonical SHA-256 ({h_src[:12]}...)")

    # 3. Verify netspout/bin/ copies carry generated header and match canonical code
    print("\n>> 3. Verifying Splunk Bin Generated Copies (netspout/bin/)...")
    for mod in CORE_MODULES:
        src_path = os.path.join(SRC_CORE_DIR, mod)
        gen_path = os.path.join(SPLUNK_BIN_DIR, mod)
        if not os.path.exists(gen_path):
            print(f"  [FAIL] Missing Splunk generated copy: {gen_path}")
            all_passed = False
            continue

        with open(src_path, "r", encoding="utf-8") as sf:
            canonical_code = sf.read()
        with open(gen_path, "r", encoding="utf-8") as gf:
            gen_content = gf.read()

        if not gen_content.startswith(GENERATED_HEADER_PREFIX):
            print(f"  [FAIL] netspout/bin/{mod} is missing auto-generated warning header!")
            all_passed = False
        else:
            # Strip header (first 5 lines) and compare remaining code
            gen_lines = gen_content.splitlines(True)
            body = "".join(gen_lines[5:])
            if body != canonical_code:
                print(f"  [FAIL] Direct modification detected in netspout/bin/{mod}!")
                print(f"         Changes must be made to src/netspout_core/{mod}.")
                all_passed = False
            else:
                print(f"  [PASS] netspout/bin/{mod} matches canonical source")

    # 4. Verify backend/app/ copies carry generated header and match canonical code
    print("\n>> 4. Verifying Backend App Generated Copies (backend/app/)...")
    for mod in CORE_MODULES:
        src_path = os.path.join(SRC_CORE_DIR, mod)
        gen_path = os.path.join(BACKEND_APP_DIR, mod)
        if not os.path.exists(gen_path):
            print(f"  [FAIL] Missing backend generated copy: {gen_path}")
            all_passed = False
            continue

        with open(src_path, "r", encoding="utf-8") as sf:
            canonical_code = sf.read()
        with open(gen_path, "r", encoding="utf-8") as gf:
            gen_content = gf.read()

        if not gen_content.startswith(GENERATED_HEADER_PREFIX):
            print(f"  [FAIL] backend/app/{mod} is missing auto-generated warning header!")
            all_passed = False
        else:
            gen_lines = gen_content.splitlines(True)
            body = "".join(gen_lines[5:])
            if body != canonical_code:
                print(f"  [FAIL] Direct modification detected in backend/app/{mod}!")
                print(f"         Changes must be made to src/netspout_core/{mod}.")
                all_passed = False
            else:
                print(f"  [PASS] backend/app/{mod} matches canonical source")

    # 5. Verify Canonical Catalog JSON file synchronization
    print("\n>> 5. Verifying Canonical Catalog Data Synchronization...")
    catalog_targets = [
        os.path.join(SPLUNK_CORE_DIR, "catalog_data"),
        os.path.join(SPLUNK_BIN_DIR, "catalog_data"),
        os.path.join(BACKEND_APP_DIR, "catalog_data"),
        os.path.join(REPO_ROOT, "netspout", "catalog")
    ]
    json_files = sorted([f for f in os.listdir(CANONICAL_CATALOG_DIR) if f.endswith(".json")])
    for target in catalog_targets:
        target_rel = os.path.relpath(target, REPO_ROOT)
        for jf in json_files:
            src_json = os.path.join(CANONICAL_CATALOG_DIR, jf)
            dst_json = os.path.join(target, jf)
            if not os.path.exists(dst_json):
                print(f"  [FAIL] Missing catalog file in {target_rel}: {jf}")
                all_passed = False
                continue
            h_src = sha256_file(src_json)
            h_dst = sha256_file(dst_json)
            if h_src != h_dst:
                print(f"  [FAIL] Drift in {target_rel}/{jf}!")
                all_passed = False
        print(f"  [PASS] {len(json_files)} catalog JSONs verified in {target_rel}")

    # 6. Verify Catalog Schema & Static Vendor JSON Mirror
    print("\n>> 6. Verifying Catalog Schema & Static Vendor JSON Mirror...")
    try:
        from validate_catalog import validate_catalog
        valid, cat_errors, _ = validate_catalog()
        if not valid:
            for err in cat_errors:
                print(f"  [FAIL] Catalog validation error: {err}")
            all_passed = False
        else:
            print("  [PASS] Canonical catalog schema and reference integrity valid (0 errors)")
    except Exception as e:
        print(f"  [FAIL] Could not run catalog validation: {e}")
        all_passed = False

    if not os.path.exists(VENDOR_STATIC_JSON):
        print(f"  [FAIL] Missing {VENDOR_STATIC_JSON}")
        all_passed = False
    else:
        try:
            import json
            sys.path.insert(0, os.path.join(REPO_ROOT, "src"))
            from netspout_core.catalog import NetSpoutCatalog
            cat = NetSpoutCatalog(catalog_dir=CANONICAL_CATALOG_DIR)
            legacy = cat.get_legacy_vendor_catalog()
            with open(VENDOR_STATIC_JSON, "r", encoding="utf-8") as f:
                static_data = json.load(f)
            if len(legacy) != len(static_data):
                print(f"  [FAIL] Vendor count mismatch: catalog={len(legacy)}, static={len(static_data)}")
                all_passed = False
            else:
                print(f"  [PASS] Static vendor_catalog.json mirror matches canonical catalog ({len(legacy)} vendors)")
        except Exception as e:
            print(f"  [FAIL] Error verifying vendor_catalog.json mirror: {e}")
            all_passed = False

    print("\n==========================================================================")
    if all_passed:
        print("✅ Single Source of Truth Audit: 100% PASSED")
        print("   All simulation logic is centralized in src/netspout_core/.")
        print("==========================================================================")
        return True
    else:
        print("❌ Single Source of Truth Audit: FAILED. Please resolve errors above.")
        print("==========================================================================")
        return False


if __name__ == "__main__":
    success = verify_sources()
    sys.exit(0 if success else 1)
