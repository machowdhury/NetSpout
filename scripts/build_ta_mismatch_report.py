#!/usr/bin/env python3
"""Prioritized mismatch report between NetSpout's catalog and the downloaded add-on packages. Counts and lists are computed from
docs/contracts/ta_backed_registry.json, docs/verification/evidence/ta_inventory/packages.json and the catalog; the narrative is fixed text.
Writes docs/contracts/ta_mismatch_report.json and docs/contracts/ta_mismatch_report.md.   python scripts/build_ta_mismatch_report.py"""
import collections
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
from build_ta_registry import PKG_VENDORS  # noqa: E402
from netspout_core.telemetry_dispatcher import NETSPOUT_NAMESPACED_FIELDS, TA_PARSED_SOURCETYPES  # noqa: E402

PROTOCOL = {  # evidence: inventory modular_input_schemes / README / inputs.conf; not an assertion about NetSpout's capability
    "Splunk_TA_Cisco_Intersight": ("REST API modular inputs (audit_alarms, inventory, metrics, custom_input)", "NetSpout has no REST-API collector emulation; it can only POST JSON to HEC. Whether the JSON equals the Intersight API response is unverified."),
    "Splunk_TA_cisco_meraki": ("REST API modular inputs (cisco_meraki_*)", "same: HEC delivery of Meraki API-shaped JSON; equivalence to the TA's modular-input output is unverified."),
    "ta_cisco_thousandeyes": ("ThousandEyes streams delivered to a HEC target (test_metrics_stream, alerts_stream, event, activity_logs_stream) plus API inputs", "NetSpout does not emulate the ThousandEyes stream (OpenTelemetry/webhook payloads); its metric label conflicts with the add-on's event definition."),
    "TA_cisco_catalyst": ("syslog plus REST modular inputs (Catalyst Center, Cyber Vision, SD-WAN, ISE)", "syslog sourcetypes are testable (cisco:ios verified); modular-input sourcetypes are not."),
    "TA-cisco-cloud-security-addon": ("modular inputs (S3, API)", "not emulated."), "CiscoSecurityCloud": ("modular inputs (Duo, Secure Endpoint, Firepower, AI Defense, ...)", "not emulated except where the sourcetype is a plain syslog stream (cisco:asa)."),
    "splunk_app_stream_ipfix_cisco_hsl": ("Splunk App for Stream IPFIX template (cisco.hsl.json/xml, ipfixmap.conf); no props/inputs/sourcetypes", "needs an IPFIX collector (Stream forwarder). It is not a Technology Add-on: NetSpout's flow engine and the add-on were not tested together."),
    "aristanetworks": ("syslog (arista_switch_log), sFlow collector (arista_switch_sflow) and interface counters (arista_switch_ifcounter) via saved searches/scripts", "NetSpout's arista:* sourcetypes use different names; sFlow is a UDP protocol NetSpout does not send into this add-on."),
    "Splunk_TA_paloalto_networks": ("syslog CSV (pan:log routed to pan:*) plus modular inputs (Cortex XDR, data security, IoT)", "syslog log types are testable (pan:traffic verified); modular inputs are not."),
}


def main():
    reg = json.loads((ROOT / "docs/contracts/ta_backed_registry.json").read_text())
    cov = {r["sourcetype"]: r for r in json.loads((ROOT / "docs/reference/sourcetype_coverage.json").read_text())["rows"]}
    inv = json.loads((ROOT / "docs/verification/evidence/ta_inventory/packages.json").read_text())
    rows = reg["rows"]
    ta_names = {r["canonical_sourcetype"] for r in rows}
    mism = []

    def add(priority, kind, subject, detail, evidence):
        mism.append({"priority": priority, "kind": kind, "subject": subject, "detail": detail, "evidence": evidence})

    for r in rows:
        for c in r["conflict_types"]:
            kind = c.split(":")[0]
            pr = {"routing": "P1", "payload-format": "P1", "naming": "P2", "advertised-without-generator": "P2"}.get(kind, "P3")
            add(pr, kind, "%s (%s)" % (r["canonical_sourcetype"], r["package_id"]), c, r["evidence"][:1])
    # catalog sourcetypes of the add-ons' vendors whose name no package defines
    for pid, vendors in PKG_VENDORS.items():
        for st, c in cov.items():
            if c["vendor_id"] in vendors and st not in ta_names and c["generator_tier"] != "NONE" and c["data_kind"] == "event":
                add("P2", "naming", "%s (catalog)" % st, "catalog sourcetype of vendor %s is not defined by %s; NetSpout would emit a name the add-on does not parse" % (c["vendor_id"], pid), ["docs/reference/sourcetype_coverage.json"])
    seen, uniq = set(), []
    for m in mism:
        k = (m["kind"], m["subject"].split(" (")[0], m["detail"][:60])
        if k not in seen:
            seen.add(k); uniq.append(m)
    mism = sorted(uniq, key=lambda m: (m["priority"], m["kind"], m["subject"]))
    exact_unverified = sorted({r["canonical_sourcetype"] for r in rows if r["netspout"] and r["netspout"]["match"] == "EXACT" and "GENERATOR_AVAILABLE" in r["statuses"] and r["canonical_sourcetype"] not in TA_PARSED_SOURCETYPES})
    protocols = []
    for p in inv["packages"]:
        for a in p["apps"]:
            if a["id"] in PROTOCOL:
                protocols.append({"package": p["package"], "package_id": a["id"], "expected_ingestion": PROTOCOL[a["id"]][0], "netspout_gap": PROTOCOL[a["id"]][1]})
    out = {"summary": {"mismatches": len(mism), "by_priority": dict(collections.Counter(m["priority"] for m in mism)), "by_kind": dict(collections.Counter(m["kind"] for m in mism)),
                       "exact_name_matches_with_generator_not_yet_live_verified": len(exact_unverified), "live_verified_sourcetypes": sorted(TA_PARSED_SOURCETYPES),
                       "namespaced_netspout_fields": list(NETSPOUT_NAMESPACED_FIELDS)},
           "systemic": {"field_shadowing": {"description": "For every sourcetype outside TA_PARSED_SOURCETYPES the dispatcher still sends the bare NetSpout fields next to the netspout_* copies. Shadowing is add-on specific (ASA, FortiGate and Palo Alto were proven; IOS showed NetSpout values in CIM fields), so each of these needs its own live check before the bare names are removed.",
                                            "sourcetypes": exact_unverified}},
           "protocol_gaps": protocols, "mismatches": mism}
    (ROOT / "docs/contracts/ta_mismatch_report.json").write_text(json.dumps(out, indent=1) + "\n")
    L = ["# NetSpout catalog versus the downloaded add-ons: prioritized mismatches", "",
         "Generated by `scripts/build_ta_mismatch_report.py` from the registry (`ta_backed_registry.json`), the package inventory and the catalog. Nothing here renames anything.", "",
         "Summary: %d mismatches (%s); %d exact-name matches with a generator are not yet live-verified; live-verified: %s." % (len(mism), ", ".join("%s %d" % kv for kv in sorted(out["summary"]["by_priority"].items())), len(exact_unverified), ", ".join(sorted(TA_PARSED_SOURCETYPES))), "",
         "## Priorities", "- **P1** wrong payload or wrong index type: events would be mis-parsed or land in the wrong place.",
         "- **P2** wrong name or advertised without a generator: the add-on does not claim the events, or nothing can be generated.", "- **P3** other.", ""]
    for pr in ("P1", "P2", "P3"):
        items = [m for m in mism if m["priority"] == pr]
        if items:
            L += ["## %s (%d)" % (pr, len(items)), "", "| kind | subject | detail |", "|---|---|---|"] + ["| %s | %s | %s |" % (m["kind"], m["subject"], m["detail"].replace("|", "/")[:170]) for m in items[:60]] + ([""] + ["(%d more in the JSON)" % (len(items) - 60)] if len(items) > 60 else []) + [""]
    L += ["## Ingestion protocol gaps (packages that are not plain syslog/HEC sourcetypes)", "", "| package | expected ingestion | NetSpout gap |", "|---|---|---|"] + ["| %s | %s | %s |" % (p["package_id"], p["expected_ingestion"], p["netspout_gap"]) for p in protocols] + [""]
    L += ["## Migration approach (no mass rename)",
          "1. Keep scenario references stable: scenarios and contracts reference catalog `id`s and sourcetype names today. Add an `emitted_sourcetype` (the add-on's name) to each catalog entry next to `splunk_sourcetype`; the resolver maps old to new and `catalog/aliases.json` keeps the old name as a deprecated alias.",
          "2. Gate every entry on evidence: an entry may switch `emitted_sourcetype` only after `scripts/ta_compat.py` passes live for it (the registry then shows SPLUNK_VERIFIED). Entries that fail stay on their current name with status CONFLICT.",
          "3. Make searches tolerant during the transition: dashboards and searches use `sourcetype IN (<old>, <new>)` and the `netspout_*` fields (already the case for the phase-story panels).",
          "4. Field ownership per entry: when an entry becomes verified it joins `TA_PARSED_SOURCETYPES`, so the bare NetSpout fields stop shadowing the add-on.",
          "5. Never relabel a sample: a sample file whose claimed sourcetype differs from the entry is refused (Phase 2) until it is verified against the add-on.", "",
          "## Remediation order",
          "1. Verify the exact-name matches that already have generators (listed in the JSON under `systemic.field_shadowing.sourcetypes`), highest-use first, using one spec per entry.",
          "2. Fix P1 payload conflicts by regenerating the sample or formatter from the add-on's expected format (sdwan system logs, stream:netflow, intersight compute).",
          "3. Correct the metric/event labelling of `cisco:thousandeyes:metric` and `cisco:intersight:metrics` (the add-ons define event sourcetypes).",
          "4. Replace invented names (`fortinet:fortigate:*`, `juniper:junos:*`, `arista:*`) by the add-on's names where the formats match; otherwise mark them as NetSpout-defined.",
          "5. Decide per protocol-gap package whether NetSpout will emulate the input (REST, stream, IPFIX, sFlow) or label the integration unsupported."]
    (ROOT / "docs/contracts/ta_mismatch_report.md").write_text("\n".join(L) + "\n")
    print(json.dumps(out["summary"], indent=1))


if __name__ == "__main__":
    main()
