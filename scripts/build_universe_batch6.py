#!/usr/bin/env python3
"""Build catalog/universe_batch6.json: captured Cisco Catalyst Center / SD-WAN / ACI / Nexus payloads (10 sourcetypes).

Every family is a record captured in the vendored Network Assurance replay samples
(netspout/appserver/static/samples/<sample>, described there as "Real Network Assurance replay"). The captured text is kept
verbatim; only declared time fields are resolved at render time (the sample's own $GOTS$ / $EPOCH_MS$ / $TS$ tokens, plus the
in-body UTD timestamp and the MX flow epoch, which are detected here and declared as tokens so no stale capture time remains).

Deliberately NOT promoted (captured text is an empty-poller status string or a bare value, not a vendor record):
cisco:catalyst:{rogue:allowed, rogue:counts, rogue:verbose:legacy, rogue:wired, security:awips_signatures, security:profile,
security:rules, threat:list, threat:signatures, script:heartbeat}.

Run: python scripts/build_universe_batch6.py   (idempotent; then scripts/sync_core.py)
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "netspout" / "appserver" / "static" / "samples"
PROMOTED = [
    "cisco:dc:aci:class", "cisco:dc:nexus9k", "cisco:catalyst:rogue:verbose", "cisco:catalyst:security:profile_signatures",
    "cisco:catalyst:threat:summary", "cisco:catalyst:threat:summary:legacy", "cisco:sdwan:ssetunnels", "cisco:sdwan:sytem:logs",
    "cisco:sdwan:utd:logs", "cisco:sdwan:utdhealth",
]
UTD_TS = re.compile(r"\d{4}/\d\d/\d\d-\d\d:\d\d:\d\d\.\d{6} UTC")
MX_EPOCH = re.compile(r"(?<= )1\d{9}\.\d{9}(?= )")
SCENARIOS = {
    "ub6_sdwan_utd_threat_pipeline": [
        ("BASELINE", "cisco:sdwan:utdhealth", "captured_1"),
        ("BASELINE", "cisco:sdwan:ssetunnels", "captured_1"),
        ("DETECT", "cisco:sdwan:utd:logs", "captured_1"),
        ("DETECT", "cisco:sdwan:utd:logs", "captured_2"),
        ("VALIDATE", "cisco:sdwan:utdhealth", "captured_2"),
        ("VALIDATE", "cisco:sdwan:ssetunnels", "captured_2"),
    ],
    "ub6_catalyst_wireless_rogue_threat": [
        ("BASELINE", "cisco:catalyst:security:profile_signatures", "captured_1"),
        ("BASELINE", "cisco:catalyst:threat:summary:legacy", "captured_1"),
        ("DETECT", "cisco:catalyst:rogue:verbose", "captured_1"),
        ("DETECT", "cisco:catalyst:rogue:verbose", "captured_2"),
        ("DETECT", "cisco:catalyst:threat:summary", "captured_1"),
        ("VALIDATE", "cisco:catalyst:threat:summary", "captured_2"),
    ],
}


def captured(sample_dir):
    text = next(sample_dir.glob("*.yml")).read_text()
    out = []
    for number, line in enumerate(text.splitlines(), 1):
        m = re.search(r"_raw: '(.*)'\s*$", line)
        if m:
            out.append((number, m.group(1).replace("''", "'")))
    return out


def main():
    catalog = {r["splunk_sourcetype"]: r for r in json.loads((ROOT / "catalog" / "sourcetypes.json").read_text())}
    sources = []
    for st in PROMOTED:
        row = catalog[st]
        sample = row["sample_file"].rsplit(".", 1)[0]
        families = []
        for i, (number, raw) in enumerate(captured(SAMPLES / sample), 1):
            template = UTD_TS.sub("$UTD_TS$", raw)
            template = MX_EPOCH.sub("$EPOCH_NS$", template)
            tokens = sorted(set(re.findall(r"\$[A-Z_]+\$", template)))
            assert set(tokens) <= {"$GOTS$", "$EPOCH_MS$", "$TS$", "$UTD_TS$", "$EPOCH_NS$"}, (st, tokens)
            families.append({"id": f"captured_{i}", "template": template, "tokens": tokens, "sample": sample, "sample_line": number,
                             "captured_sha256": hashlib.sha256(raw.encode()).hexdigest()})
        assert families, st
        sources.append({"batch_source_id": st, "vendor": row["vendor_id"], "product": row["display_name"], "splunk_sourcetype": st,
                        "generator": "format_universe_batch6_log", "event_families": [f["id"] for f in families], "families": families})
    known = {s["batch_source_id"]: {f["id"] for f in s["families"]} for s in sources}
    for sid, steps in SCENARIOS.items():
        for _, st, fid in steps:
            assert fid in known[st], (sid, st, fid)
    reg = {
        "schema_version": "1.0", "registry_version": "universe-batch6-2026-10-30",
        "purpose": "Captured Cisco Catalyst Center, SD-WAN, ACI and Nexus records rendered natively with declared time fields; two correlated scenarios.",
        "baseline_counts": {"native_generators": 148, "sourcetypes": 348},
        "engine_module": "src/netspout_core/universe_batch6_engine.py",
        "provenance": "Captured records in netspout/appserver/static/samples/* (Network Assurance replay). Provenance basis is the repository capture, not vendor documentation. Splunk TA parsing is NOT verified.",
        "sources": sources,
        "scenarios": {sid: [{"phase": p, "sourcetype": st, "family": f} for p, st, f in steps] for sid, steps in SCENARIOS.items()},
        "counts_summary": {"new_native_sourcetypes": len(sources), "families": sum(len(s["families"]) for s in sources), "scenario_packs": len(SCENARIOS)},
    }
    (ROOT / "catalog" / "universe_batch6.json").write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(reg["counts_summary"]))


if __name__ == "__main__":
    main()
