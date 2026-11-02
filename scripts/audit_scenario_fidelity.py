#!/usr/bin/env python3
"""
Vendor-fidelity audit of every declarative scenario contract that is not purely vendor-native. Everything is derived from the contracts and the catalogs; nothing is hand-set.

Per scenario: intended vendor/product (from the definition), the sourcetypes it actually emits, and for each stream whether it is vendor-native (an engine formatter that
writes the vendor's own log), a grounded sample (a verbatim recorded vendor event), or modeled (the labeled NetSpout schema). From that: whether an administrator of the named
product would recognize the output, which sourcetype in the catalog still has no generator and so limits fidelity, and whether a stronger existing generator is available.

  PYTHONPATH=src:backend python scripts/audit_scenario_fidelity.py
Writes docs/reference/scenario_fidelity_audit.json and SCENARIO_FIDELITY_AUDIT.md.
"""
import collections
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]
from netspout_core import scenario_contracts  # noqa: E402

REF = ROOT / "docs" / "reference"
# technology named by a definition -> catalog sourcetypes that would carry its real logs, in order of preference
TECH_SOURCETYPES = {
    "Cisco ISE": ["cisco:ise:syslog"], "Cisco Duo": ["cisco:duo:remote:vpn", "cisco:duo:authentication"], "IOS XR": ["cisco:ios:syslog", "cisco:ios:mdt:metric"],
    "IOS XE": ["cisco:ios:syslog"], "Cisco SD-WAN": ["cisco:sdwan:linkhealth", "cisco:sdwan:BGP-5-ADJCHANGE"], "Cisco Nexus": ["cisco:dc:nexus9k:syslog"], "NX-OS": ["cisco:nxos:syslog"],
    "Cisco ACI": ["cisco:dc:aci:health", "cisco:dc:aci:class"], "Cisco Secure Firewall": ["cisco:ftd:syslog", "cisco:asa"], "Cisco Umbrella": ["cisco:cloud_security:dns"],
    "Cisco Meraki": ["cisco:meraki:syslog", "meraki:accesspoints"], "Cisco Catalyst Center": ["cisco:dnac:networkhealth"], "Cisco Intersight": ["cisco:intersight:alarms"],
    "Cisco Secure Endpoint": ["cisco:se"], "ThousandEyes": ["cisco:thousandeyes:metric"], "Catalyst Switching": ["cisco:ios:syslog"],
}


def stream_kind(s):
    return "modeled" if s["formatter"] == "format_modeled_state_event" else "grounded_sample" if s["formatter"] == "grounded_sample" else "vendor_native"


def main():
    contracts = scenario_contracts.contracts()
    tiers = {r["sourcetype"]: r["generator_tier"] for r in json.loads((REF / "sourcetype_coverage.json").read_text())["rows"]}
    c100 = {r["scenario_id"]: r for r in json.loads((ROOT / "catalog" / "cisco_100_scenarios.json").read_text())["scenarios"]}
    declared = {r["id"]: r.get("sourcetypes", []) for r in json.loads((ROOT / "catalog" / "scenarios.json").read_text())}   # sourcetypes the original definition named
    rows = []
    for cid, c in sorted(contracts.items()):
        fid = scenario_contracts.fidelity(c)
        if fid == "VENDOR_NATIVE":
            continue
        kinds = collections.Counter(stream_kind(s) for s in c["streams"])
        techs = (c100.get(cid) or {}).get("technologies") or c.get("vendors") or []
        wanted = [st for t in techs for st in TECH_SOURCETYPES.get(t, [])]
        emitted = scenario_contracts.sourcetypes(c)
        stronger = [st for st in dict.fromkeys(wanted) if st not in emitted and tiers.get(st) in ("NATIVE_ENGINE", "SAMPLE_REPLAY")]
        still_missing = [st for st in dict.fromkeys(wanted + declared.get(cid, [])) if st not in emitted and tiers.get(st, "NONE") == "NONE"]
        no_generator_tech = [t for t in techs if t not in TECH_SOURCETYPES and cid in c100]
        recognizable = "yes" if kinds["modeled"] == 0 else ("partly: native or recorded vendor events plus a modeled context stream" if kinds["vendor_native"] + kinds["grounded_sample"] else "no: modeled state events only")
        rows.append({"scenario_id": cid, "title": c["title"], "intended_vendor_or_technology": techs, "emitted_sourcetypes": emitted, "fidelity": fid, "streams": dict(kinds),
                     "recognizable_to_product_admins": recognizable, "stronger_existing_generator_available": stronger, "missing_generator_sourcetypes": still_missing, "technologies_with_no_generator_mapping": no_generator_tech,
                     "upgraded": c.get("generator_family") == "modeled_state_progression_with_native_streams" or "native" in c.get("generator_family", "") and kinds["modeled"] > 0})
    summary = {"scenarios_audited": len(rows), "by_fidelity": dict(collections.Counter(r["fidelity"] for r in rows)),
               "mixed_with_native_or_sample_streams": sum(1 for r in rows if r["streams"].get("vendor_native") or r["streams"].get("grounded_sample")),
               "modeled_only": sum(1 for r in rows if not (r["streams"].get("vendor_native") or r["streams"].get("grounded_sample"))),
               "modeled_only_with_stronger_generator_available": sum(1 for r in rows if not (r["streams"].get("vendor_native") or r["streams"].get("grounded_sample")) and r["stronger_existing_generator_available"]),
               "missing_generators_by_sourcetype": dict(collections.Counter(st for r in rows for st in r["missing_generator_sourcetypes"]).most_common()),
               "technologies_with_no_generator_mapping": dict(collections.Counter(t for r in rows for t in r["technologies_with_no_generator_mapping"]).most_common())}
    (REF / "scenario_fidelity_audit.json").write_text(json.dumps({"summary": summary, "rows": rows}, indent=1) + "\n")
    L = ["# Scenario fidelity audit", "", "Generated by `scripts/audit_scenario_fidelity.py` from the scenario contracts and catalogs; do not edit by hand. It covers every declarative contract that is not purely vendor-native.", "",
         "| | Count |", "|---|---|", "| Scenarios audited (mixed or modeled) | %d |" % summary["scenarios_audited"],
         "| Mixed: native or recorded vendor events plus modeled context | %d |" % summary["mixed_with_native_or_sample_streams"],
         "| Modeled only (labeled NetSpout schema, not product logs) | %d |" % summary["modeled_only"],
         "| Modeled only, but a stronger existing generator is available for the named product | %d |" % summary["modeled_only_with_stronger_generator_available"], "",
         "**Fidelity means:** *vendor-native* is a formatter that writes the product's own log; *grounded sample* is a verbatim recorded vendor event; *modeled* is the labeled `netspout:scenario:state` schema, which an administrator of the named product would **not** recognize as that product's log. "
         "Modeled state events carry scenario context (entity, state, dependency order); they are not product telemetry.", "",
         "Catalog sourcetypes named by these definitions that still have **no generator**: " + (", ".join("`%s` (%d)" % kv for kv in summary["missing_generators_by_sourcetype"].items()) or "none") + ".", "",
         "Technologies named by Cisco-100 definitions for which no catalog generator is mapped: " + (", ".join("%s (%d)" % kv for kv in summary["technologies_with_no_generator_mapping"].items()) or "none") + ".", "",
         "| ID | Name | Intended product | Emitted sourcetypes | Fidelity | Recognizable to product admins | Stronger existing generator |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append("| `%s` | %s | %s | %s | %s | %s | %s |" % (r["scenario_id"], r["title"][:60].replace("|", "/"), ", ".join(r["intended_vendor_or_technology"])[:60] or "none named", ", ".join("`%s`" % s for s in r["emitted_sourcetypes"])[:110],
                                                           r["fidelity"], r["recognizable_to_product_admins"], ", ".join("`%s`" % s for s in r["stronger_existing_generator_available"][:3]) or "—"))
    (REF / "SCENARIO_FIDELITY_AUDIT.md").write_text("\n".join(L) + "\n")
    print(json.dumps(summary, indent=1)[:900])


if __name__ == "__main__":
    main()
