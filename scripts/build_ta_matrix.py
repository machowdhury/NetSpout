#!/usr/bin/env python3
"""Build docs/verification/pulseforge_ta_validation_matrix.{md,csv}: executed TA validation results plus the 20-generator backlog.

Executed rows come from docs/verification/evidence/ta_validation/windows_sysmon.json (written by scripts/validate_ta_windows.py).
Backlog rows are a curated selection (rationale per row) joined with the current evidence flags in pulseforge_sourcetype_coverage.csv.
Splunkbase IDs are cited ONLY where the repository verifies them (catalog/telemetry_catalog.json integration profiles or an installed
package); otherwise the row says "id not verified in repo". Nothing here asserts that an uninstalled TA parses anything.
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
V = ROOT / "docs" / "verification"
COVERAGE = {r["sourcetype"]: r for r in csv.DictReader(open(V / "pulseforge_sourcetype_coverage.csv"))}
EVIDENCE = json.loads((V / "evidence" / "ta_validation" / "windows_sysmon.json").read_text())
PACKS = {  # package availability, from what exists on disk / in repo evidence
    "win": "Splunk Add-on for Microsoft Windows 10.0.1 (package on disk: ~/Downloads/splunk-add-on-for-microsoft-windows_1001.spl)",
    "sysmon": "Splunk Add-on for Sysmon 5.0.1 (package on disk: ~/Downloads/splunk-add-on-for-sysmon_501.spl)",
    "7538": "Cisco Enterprise Networking Add-on for Splunk, Splunkbase 7538 (SUPPORTED in telemetry_catalog); package not on disk",
    "7404": "Cisco Security Cloud Add-on for Splunk, Splunkbase 7404 (RESEARCH_REQUIRED in telemetry_catalog); package not on disk",
    "7569": "Cisco Secure Access Add-on for Splunk, Splunkbase 7569 (RESEARCH_REQUIRED in telemetry_catalog); package not on disk",
    "5580": "Cisco Meraki Add-on for Splunk, Splunkbase 5580 (RESEARCH_REQUIRED in telemetry_catalog); package not on disk",
    "1915": "Splunk Add-on for Cisco Identity Services 5.0.0, Splunkbase 1915 (validated once; package lived on an unmounted volume)",
    "7523": "Splunk Add-on for Palo Alto Networks, Splunkbase 7523 (RESEARCH_REQUIRED in telemetry_catalog); package not on disk",
    "unix": "Splunk Add-on for Unix and Linux (Splunkbase id not verified in repo); package not on disk",
    "sysmon_linux": "Splunk Add-on for Sysmon on Linux (id not verified in repo); package not on disk",
    "ios": "Cisco IOS parsing add-on: catalog lists 1467 (DEPRECATED) and 7538; the correct current package must be confirmed before download",
    "duo": "Duo / Cisco Security Cloud add-on (id not verified in repo); package not on disk",
    "aci": "Cisco ACI add-on (id not verified in repo); package not on disk",
}
# (rank, sourcetype, pack key, domain, rationale)
BACKLOG = [
    (1, "cisco:asa", "7404", "Cisco security", "Most-deployed Cisco firewall syslog; used by ASA scenarios; not byte-verified yet"),
    (2, "cisco:sfw:estreamer", "7404", "Cisco security", "Secure Firewall events; byte-verified and indexed; React2Shell-family detections depend on it"),
    (3, "cisco:ios", "ios", "Cisco networking", "Core IOS/IOS-XE syslog; byte-verified; basis for NOC change/fault scenarios"),
    (4, "cisco:ise:syslog", "1915", "Cisco security", "ISE is the only partial TA validation; extend it beyond the message classes already exercised"),
    (5, "cisco:sdwan:syslog", "7538", "Cisco networking", "SD-WAN edge syslog; byte-verified; used by cisco_sdwan_brownout (golden path)"),
    (6, "cisco:sdwan:OSPF-5-ADJCHG", "7538", "Cisco networking", "Representative of the 31 Batch-5 IOS-XE mnemonic sourcetypes (change/fault timelines)"),
    (7, "cisco:sdwan:utd:logs", "7538", "Cisco security", "UTD/Snort threat logs from Batch 6; correlated with UTD health"),
    (8, "cisco:duo:administrator", "duo", "Cisco security", "Identity/admin audit; byte-verified; used in authentication scenarios"),
    (9, "cisco:meraki:syslog", "5580", "Cisco networking", "Meraki MX/MR syslog; byte-verified"),
    (10, "cisco:cloud_security:dns", "7569", "DNS / Cisco security", "Only catalog DNS telemetry with a native generator; CIM Network_Resolution candidate"),
    (11, "cisco:cloud_security:firewall", "7569", "Cisco security", "Secure Access firewall events; byte-verified"),
    (12, "cisco:dc:aci:class", "aci", "Cisco networking", "ACI APIC class data from Batch 6; tab-separated native format"),
    (13, "cisco:catalyst:threat:summary", "7538", "Cisco networking", "Catalyst Center wireless threat summary from Batch 6"),
    (14, "pan:traffic", "7523", "Palo Alto", "Palo Alto traffic; 54 documented fields; indexed; not byte-verified"),
    (15, "pan:threat", "7523", "Palo Alto", "Palo Alto threat; 45 documented fields; used by paloalto_threat_investigation"),
    (16, "pan:system", "7523", "Palo Alto", "Palo Alto system log; counted native after the scanner fix; not byte-verified"),
    (17, "auditd", "unix", "Linux", "Linux audit records; byte-verified; used by wave2_linux_auth_anomaly"),
    (18, "linux_secure", "unix", "Linux", "Linux auth log; byte-verified; used by wave3_vsphere_hostpath_triage"),
    (19, "linux_messages_syslog", "unix", "Linux", "Linux syslog; byte-verified"),
    (20, "sysmon:linux", "sysmon_linux", "Linux / endpoint", "Sysmon for Linux events; byte-verified"),
]
TESTS = [
    ("T1", "Install verified", "TA app visible with expected version and its props.conf stanzas visible through /configs/conf-props (not just files copied)"),
    ("T2", "Metadata convention", "Same raw sent (A) as NetSpout dispatches and (B) as a forwarder would; both must reach the TA's parsing"),
    ("T3", "Timestamp", "Event timestamp moved 48 h into the past; _time must equal it where the TA defines a timestamp rule; an authentic control shows what is TA behavior"),
    ("T4", "Field extraction", "Every field the event itself carries (EventCode, Computer, each Data Name) must appear as an extracted field (space/underscore-normalized)"),
    ("T5", "TA tags/eventtypes", "Tags the TA assigns are recorded (CIM-relevant: authentication, process, dns, ...)"),
    ("T6", "CIM data model", "Requires Splunk_SA_CIM installed; datamodel search must return the events. NOT RUN while CIM is absent"),
    ("T7", "Detection outcome", "A relevant detection's SPL (with its macros) must match naturally generated events. NOT RUN while ESCU macros are absent"),
    ("T8", "Authentic control", "Pinned authentic bytes through the same path to separate generator fidelity from TA behavior"),
]


def executed_rows():
    by = defaultdict(list)
    for r in EVIDENCE["events"]:
        if r["variant"] == "B":
            by[r["sourcetype_emitted"]].append(r)
    rows = []
    for st, rs in sorted(by.items()):
        n = len(rs)
        mean = sum(r["extraction_ratio"] for r in rs) / n
        parsed = sum(r["time_source"] == "event_timestamp" for r in rs)
        tags = sorted({t for r in rs for t in (r["tags"] if isinstance(r["tags"], list) else [r["tags"]] if r["tags"] else [])} - {"track_event_signatures"})
        pack = "sysmon" if "Sysmon" in st else "win"
        verdict = ("TA_PARSES_EMITTED_FIELDS" if n >= 3 else "TA_PARSES_EMITTED_FIELDS_LIMITED_SAMPLE") if mean >= 0.99 else "TA_PARSES_EMITTED_FIELDS_PARTIALLY"
        eids = ", ".join(sorted({r["event_id"] for r in rs}))
        notes = []
        if parsed == n:
            notes.append("timestamp parsed from event body (TA rule)")
        else:
            notes.append("timestamp NOT parsed from event body: the TA props define no timestamp rule for this channel (props dump in the evidence JSON)")
        miss = sorted({m for r in rs for m in r["missing_fields"]})
        if miss:
            notes.append("fields not extracted: " + ", ".join(miss))
        rows.append({"sourcetype": st, "ta": PACKS[pack], "events": n, "event_ids": eids, "extraction_mean": round(mean, 3), "timestamp_parsed": f"{parsed}/{n}",
                     "tags": ", ".join(tags) or "none", "verdict": verdict, "cim_data_model": "NOT_RUN (Splunk_SA_CIM absent)", "detection": "NOT_RUN (ESCU macros absent)", "notes": "; ".join(notes)})
    return rows


def main():
    ex = executed_rows()
    back = []
    for rank, st, pack, domain, why in BACKLOG:
        c = COVERAGE[st]
        back.append({"rank": rank, "sourcetype": st, "domain": domain, "generator": c["generator"], "byte_verified": c["format_verified"],
                     "indexed": c["indexed_evidence"], "ta_package": PACKS[pack], "status": "BLOCKED_PACKAGE", "why": why})
    with open(V / "pulseforge_ta_validation_matrix.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["section", "rank", "sourcetype", "domain", "generator", "byte_verified", "indexed", "ta_package", "status", "extraction_mean", "timestamp_parsed", "tags", "notes"])
        for r in ex:
            w.writerow(["EXECUTED", "", r["sourcetype"], "Windows", "NATIVE_ENGINE", "YES", "YES", r["ta"], r["verdict"], r["extraction_mean"], r["timestamp_parsed"], r["tags"], r["notes"]])
        for b in back:
            w.writerow(["BACKLOG", b["rank"], b["sourcetype"], b["domain"], b["generator"], b["byte_verified"], b["indexed"], b["ta_package"], b["status"], "", "", "", b["why"]])
    s = EVIDENCE["summary"]
    L = ["# PulseForge Vendor TA Validation Matrix", "",
         "Generated by `scripts/build_ta_matrix.py` from `docs/verification/evidence/ta_validation/windows_sysmon.json`. "
         "Splunk Enterprise %s (build %s) in the isolated container `netspout_tavalidation_splunk` (never the demo lab)." % (EVIDENCE["splunk_version"], EVIDENCE["splunk_build"]), "",
         "**Scope of what was actually run:** Splunk Add-on for Microsoft Windows 10.0.1 and Splunk Add-on for Sysmon 5.0.1 against %d native Windows/Sysmon events "
         "(distinct sourcetype x EventID) sent two ways. **No other vendor TA has been run**: the packages are not available (see Missing inputs). "
         "CIM (`Splunk_SA_CIM`) and ESCU are not installed, so CIM data models and detection outcomes are NOT validated." % s["A"]["events"], "",
         "## 1. Executed: Windows / Sysmon", "",
         "| Sourcetype | Events (EventIDs) | Field extraction (mean) | Timestamp from event | TA tags (CIM-relevant) | Verdict |", "|---|---|---|---|---|---|"]
    for r in ex:
        L.append(f"| `{r['sourcetype']}` | {r['events']} ({r['event_ids']}) | {r['extraction_mean']} | {r['timestamp_parsed']} | {r['tags']} | {r['verdict']} |")
    L += ["", "**How to read the verdicts.** Field extraction is measured against the fields *the event itself carries* (EventCode, Computer, every `<Data Name=...>`). "
          "It shows the vendor TA correctly parses what the generator emits; it does **not** show the generator emits every field a real source would. "
          "Verdict names say what was shown: `TA_PARSES_EMITTED_FIELDS` = the TA extracted every field the generated event carries (a self-consistency check, not a vendor-schema completeness check). `LIMITED_SAMPLE` means fewer than 3 events (one EventID) were tested, which is too thin to call the sourcetype validated. "
          "Timestamps were tested with a 48 h shifted event time (declared fixture transform); tags are what the TA assigned, not a CIM data model result.", "", "Notes per row:", ""] + [f"* `{r['sourcetype']}`: {r['notes']}" for r in ex]
    L += ["", "### Findings from the run", "",
          f"* **Metadata convention works with the Windows TA.** Events sent as NetSpout dispatches them (variant A: sourcetype `XmlWinEventLog:<channel>`, source `network-topology-simulator`) extracted exactly like the forwarder-canonical form (variant B): mean extraction A={s['A']['mean_extraction_ratio']}, B={s['B']['mean_extraction_ratio']}; the source predicate `source=\"XmlWinEventLog:*\"` matched {s['A']['source_predicate_matches']}/{s['A']['events']} for A because the TA's index-time fixup rewrites source and sourcetype.",
          f"* **Timestamps.** NetSpout's dispatcher sets HEC `time` to the send time, so variant A shows 0/{s['A']['events']} event-time parses by construction of that path (a property of how NetSpout sends, not a TA result). With a forwarder-style path (B) only the Sysmon channel parses the event time ({s['B']['event_timestamp_parsed']}/{s['B']['events']}); the Windows TA defines no timestamp rule for the other channels, and the TA props dump shows no timestamp rule for them. One authentic-bytes control (pinned Sysmon events relabeled to a channel with no rule, {EVIDENCE['authentic_control']['event_timestamp_parsed']}/{EVIDENCE['authentic_control']['events']} parsed) is consistent with that; it only supports the timestamp conclusion, and it says nothing about field extraction or tags.",
          f"* **Tags.** Every event received TA tags/eventtypes ({s['B']['with_tags']}/{s['B']['events']}); examples: 4624/4625 `authentication`, Sysmon 1/7/10 `process`+`report`, Sysmon 22 `dns`+`resolution`.",
          "* **Not validated:** CIM data models (needs Splunk_SA_CIM), detection outcomes (needs ESCU content/macros), ES notable behavior, TA behavior on a real Windows forwarder.", "",
          "## 2. Prioritized 20-generator backlog (native generators not yet TA-validated)", "",
          "Ranking rule: priority domains first (Cisco networking/security, Palo Alto, Linux, DNS; Windows was just validated above), then byte-verified generators already used by "
          "runnable scenarios, so a TA result immediately strengthens a demonstrable workflow. All rows are BLOCKED_PACKAGE until the package is supplied.", "",
          "| # | Sourcetype | Domain | Generator | Byte-verified | Indexed | Required TA package | Status |", "|---|---|---|---|---|---|---|---|"]
    for b in back:
        L.append(f"| {b['rank']} | `{b['sourcetype']}` | {b['domain']} | {b['generator']} | {b['byte_verified']} | {b['indexed']} | {b['ta_package']} | {b['status']} |")
    L += ["", "Rationale per row:", ""] + [f"{b['rank']}. `{b['sourcetype']}`: {b['why']}" for b in back]
    L += ["", "## 3. Test definitions (apply to every row)", "", "| ID | Test | Pass criterion |", "|---|---|---|"] + [f"| {a} | {b} | {c} |" for a, b, c in TESTS]
    L += ["", "## 4. Missing inputs (exact)", "",
          "* Authenticated Splunkbase downloads (user action; this repo never downloads TAs): packages listed in the backlog table. For ISE, re-fetch 1915 5.0.0 (sha256 `7c5c1489d11744cfe6270f4f28f109e46b94f65a77f1624bcbb13d0ceb629b80`) because the prior copy was on an unmounted volume.",
          "* Splunk Common Information Model (`Splunk_SA_CIM`) for T6.",
          "* Splunk ES Content Update (ESCU, `DA-ESS-ContentUpdate`) for T7: the repo does not contain ESCU macro definitions, and none were written here.",
          "* Confirm Splunkbase IDs before download: `catalog/vendors.json` IDs disagree with `telemetry_catalog.json` and with the ISE-verified ID (for example ISE 2736 vs 1915; ASA 6259 vs 7404), and `required_ta` is wrong for ~100 Cisco rows (shows Unix and Linux).", "",
          "## 5. Reproduce", "", "```", "tests/lab/ta_validation/lab.sh up                                  # isolated lab, ports 19000/19191/19088, credentials in git-ignored .env.lab",
          "# install the two packages (REST apps/local, filename=true), create index ta_validation, restart",
          "PYTHONPATH=src:backend python scripts/validate_ta_windows.py        # writes docs/verification/evidence/ta_validation/windows_sysmon.json",
          "python scripts/build_ta_matrix.py                                   # regenerates this matrix", "```"]
    (V / "pulseforge_ta_validation_matrix.md").write_text("\n".join(L) + "\n")
    print(json.dumps({"executed": len(ex), "backlog": len(back)}))


if __name__ == "__main__":
    main()
