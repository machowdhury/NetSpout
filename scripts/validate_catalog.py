#!/usr/bin/env python3
"""
NetSpout Canonical Catalog Validator
Validates schema correctness, reference integrity, uniqueness, and alias resolution.
Fails with non-zero exit code on validation errors.
"""

import os
import sys
import json
from typing import Dict, List, Set, Tuple, Any

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
CATALOG_DIR = os.path.join(REPO_ROOT, "catalog")


def validate_catalog() -> Tuple[bool, List[str], Dict[str, Any]]:
    errors = []
    warnings = []
    orphans = {
        "orphan_sourcetypes": [],
        "orphan_samples": [],
        "orphan_scenarios": [],
        "orphan_vendors": [],
        "orphan_topologies": []
    }

    # 1. Load all catalog files
    required_files = [
        "vendors.json",
        "sourcetypes.json",
        "scenarios.json",
        "device_types.json",
        "topologies.json",
        "samples.json",
        "telemetry_protocols.json",
        "aliases.json"
    ]
    catalog_data = {}
    for rf in required_files:
        p = os.path.join(CATALOG_DIR, rf)
        if not os.path.exists(p):
            errors.append(f"Missing required catalog file: {p}")
            continue
        try:
            with open(p, "r", encoding="utf-8") as f:
                catalog_data[rf] = json.load(f)
        except Exception as e:
            errors.append(f"JSON syntax error in {p}: {e}")

    if errors:
        return False, errors, orphans

    vendors = catalog_data["vendors.json"]
    sourcetypes = catalog_data["sourcetypes.json"]
    scenarios = catalog_data["scenarios.json"]
    device_types = catalog_data["device_types.json"]
    topologies = catalog_data["topologies.json"]
    samples = catalog_data["samples.json"]
    protocols = catalog_data["telemetry_protocols.json"]
    aliases = catalog_data["aliases.json"]

    # 2. Check Uniqueness of IDs
    def check_unique_ids(items, id_field, domain_name):
        seen = {}
        for item in items:
            iid = item.get(id_field)
            if not iid:
                errors.append(f"[{domain_name}] Missing '{id_field}' in entry: {item}")
                continue
            if iid in seen:
                errors.append(f"[{domain_name}] Duplicate '{id_field}': '{iid}'")
            seen[iid] = item
        return seen

    vendor_map = check_unique_ids(vendors, "id", "Vendors")
    sourcetype_map = check_unique_ids(sourcetypes, "splunk_sourcetype", "Sourcetypes")
    sourcetype_id_map = check_unique_ids(sourcetypes, "id", "Sourcetypes (ID)")
    scenario_map = check_unique_ids(scenarios, "id", "Scenarios")
    device_type_map = check_unique_ids(device_types, "id", "DeviceTypes")
    topology_map = check_unique_ids(topologies, "id", "Topologies")
    sample_map = check_unique_ids(samples, "id", "Samples")
    protocol_map = check_unique_ids(protocols, "id", "Protocols")

    # 3. Validate Vendor References in Sourcetypes
    vendor_slug_map = {v.get("slug"): v["id"] for v in vendors if v.get("slug")}
    for st in sourcetypes:
        vid = st.get("vendor_id")
        if not vid or (vid not in vendor_map and vid not in vendor_slug_map):
            errors.append(f"[Sourcetypes] Sourcetype '{st['splunk_sourcetype']}' references unknown vendor_id '{vid}'")

    # 4. Validate Scenario References
    for sc in scenarios:
        sid = sc["id"]
        # Topology reference
        top_id = sc.get("default_topology_id")
        if top_id and top_id not in topology_map:
            # Check if top_id is in aliases
            if top_id in aliases and aliases[top_id].get("canonical_id") in topology_map:
                pass
            else:
                errors.append(f"[Scenarios] Scenario '{sid}' references unknown default_topology_id '{top_id}'")

        # Sourcetype references
        for st_ref in sc.get("sourcetypes", []):
            if st_ref not in sourcetype_map:
                if st_ref in aliases:
                    target_st = aliases[st_ref].get("canonical_sourcetype")
                    if target_st not in sourcetype_map:
                        errors.append(f"[Scenarios] Scenario '{sid}' references alias '{st_ref}' whose target '{target_st}' is unknown")
                else:
                    errors.append(f"[Scenarios] Scenario '{sid}' references unknown sourcetype '{st_ref}'")

    # 5. Validate Sample References
    for s in samples:
        sid = s["id"]
        st_ref = s.get("sourcetype")
        if st_ref and st_ref not in sourcetype_map:
            if st_ref in aliases:
                target_st = aliases[st_ref].get("canonical_sourcetype")
                if target_st not in sourcetype_map:
                    errors.append(f"[Samples] Sample '{sid}' references alias '{st_ref}' whose target '{target_st}' is unknown")
            else:
                errors.append(f"[Samples] Sample '{sid}' references unknown sourcetype '{st_ref}'")

    # 6. Validate Aliases
    for alias_key, alias_info in aliases.items():
        can_st = alias_info.get("canonical_sourcetype")
        can_id = alias_info.get("canonical_id")
        if can_st and can_st not in sourcetype_map:
            errors.append(f"[Aliases] Alias '{alias_key}' points to non-existent canonical_sourcetype '{can_st}'")
        if can_id:
            # Check if canonical_id is valid in vendors, topologies, or sourcetypes
            valid = (can_id in vendor_map or can_id in topology_map or can_id in sourcetype_id_map or can_id in scenario_map)
            if not valid:
                errors.append(f"[Aliases] Alias '{alias_key}' points to non-existent canonical_id '{can_id}'")

    # 7. Orphan Detection (Step 16)
    # Orphan sourcetypes: sourcetypes with no scenario referencing them and no sample
    sampled_sts = {s.get("sourcetype") for s in samples if s.get("sourcetype")}
    scenario_sts = set()
    for sc in scenarios:
        for st in sc.get("sourcetypes", []):
            scenario_sts.add(st)

    for st in sourcetypes:
        name = st["splunk_sourcetype"]
        if name not in sampled_sts and name not in scenario_sts and not st.get("is_benchmark_197"):
            orphans["orphan_sourcetypes"].append(name)

    # Orphan vendors: vendors with no sourcetypes
    st_vendors = {st["vendor_id"] for st in sourcetypes}
    for v in vendors:
        vid = v["id"]
        slug = v.get("slug")
        if vid not in st_vendors and slug not in st_vendors:
            orphans["orphan_vendors"].append(vid)

    # Orphan topologies: topologies with no associated scenarios
    for top in topologies:
        if not top.get("associated_scenarios"):
            orphans["orphan_topologies"].append(top["id"])

    # 8. Check Disk Samples match samples.json
    samples_dir = os.path.join(REPO_ROOT, "netspout/appserver/static/samples")
    if os.path.isdir(samples_dir):
        disk_sample_files = set()
        for root, dirs, files in os.walk(samples_dir):
            for fn in files:
                if fn.endswith(".yml") or fn.endswith(".yaml") or fn.endswith(".sample"):
                    disk_sample_files.add(fn)
        sample_json_files = {s["sample_file"] for s in samples if s.get("sample_file")}
        missing_on_disk = sample_json_files - disk_sample_files
        if missing_on_disk:
            errors.append(f"[Samples] {len(missing_on_disk)} sample files in catalog missing from disk: {sorted(list(missing_on_disk))[:5]}")

    is_valid = len(errors) == 0
    return is_valid, errors, orphans


def main():
    print("==========================================================================")
    print("🔍 NetSpout Architecture Guardrail: Canonical Catalog Validation")
    print("==========================================================================")
    is_valid, errors, orphans = validate_catalog()

    if errors:
        print(f"\n❌ VALIDATION FAILED with {len(errors)} errors:")
        for err in errors:
            print(f"  [ERROR] {err}")
    else:
        print("\n✅ Canonical Catalog Schema & Reference Integrity: 100% VALID")

    print("\n>> Orphan Analysis Summary:")
    print(f"  - Orphan Sourcetypes (unreferenced): {len(orphans['orphan_sourcetypes'])}")
    print(f"  - Orphan Vendors (no sourcetypes):   {len(orphans['orphan_vendors'])}")
    print(f"  - Orphan Topologies (no scenarios):  {len(orphans['orphan_topologies'])}")

    if not is_valid:
        sys.exit(1)
    print("==========================================================================")
    sys.exit(0)


if __name__ == "__main__":
    main()
