#!/usr/bin/env python3
"""Build catalog/universe_batch7.json (+ the catalog row): authentic NGINX Plus key=value access records, sourcetype nginx:plus:access.

Evidence: splunk/attack_data datasets under datasets/attack_techniques/T1190/confluence/ labelled `sourcetype: nginx:plus:access`, byte-compared with the
repository's pinned commit (4389fa7a...) on 2026-10-30; the sourcetype is declared by the Splunk Add-on for NGINX (Splunkbase 3258) per the pinned
Splunkbase snapshot. Records are kept verbatim; the only declared token is the record's own time_local value. The fields site/server/dest_ip/src/src_ip
are NOT varied: captured values stay consistent inside each record.
Note: the existing `nginx:plus:kv` generator emits a combined-log line plus a synthetic KV trail and does NOT match these authentic records.
Run: python scripts/build_universe_batch7.py   (idempotent; then scripts/sync_core.py)
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATASETS = Path.home() / "Downloads" / "attack_data" / "datasets" / "attack_techniques" / "T1190" / "confluence"
FILES = ["nginx_plus_kv_confluence.log", "nginx_kv_confluence_CVE-2024-21683.log", "nginx_shellservlet.log"]
PIN = "4389fa7a4e74a7c083c0fbe448fa2c7c32378981"
TIME_LOCAL = re.compile(r'(?<=time_local=")\d\d/[A-Z][a-z]{2}/\d{4}:\d\d:\d\d:\d\d \+0000(?=")')
PER_FILE = 2


def main():
    families = []
    for name in FILES:
        data = (DATASETS / name).read_bytes()
        picked = 0
        for number, line in enumerate(data.decode("utf-8").splitlines(), 1):
            if picked == PER_FILE:
                break
            if not line.startswith('site="') or len(TIME_LOCAL.findall(line)) != 1:
                continue
            families.append({"id": f"captured_{len(families) + 1}", "template": TIME_LOCAL.sub("$NGINX_TS$", line), "tokens": ["$NGINX_TS$"],
                             "dataset": name, "dataset_sha256": hashlib.sha256(data).hexdigest(), "dataset_line": number,
                             "captured_sha256": hashlib.sha256(line.encode()).hexdigest()})
            picked += 1
        assert picked >= 1, name
    st = "nginx:plus:access"
    reg = {"schema_version": "1.0", "registry_version": "universe-batch7-2026-10-30",
           "purpose": "Authentic NGINX Plus key=value access records (splunk/attack_data), rendered natively with the record's own time_local re-stamped.",
           "engine_module": "src/netspout_core/universe_batch7_engine.py",
           "provenance": {"corpus": "splunk/attack_data", "pinned_commit": PIN, "path": "datasets/attack_techniques/T1190/confluence/",
                          "declared_by": "Splunk Add-on for NGINX (Splunkbase 3258), pinned Splunkbase snapshot 2026-10-26",
                          "ta_parsing": "NOT verified: the add-on package is not installed in any lab"},
           "sources": [{"batch_source_id": st, "vendor": "nginx_f5", "product": "NGINX Plus access (key=value)", "splunk_sourcetype": st,
                        "generator": "format_universe_batch7_log", "event_families": [f["id"] for f in families], "families": families}],
           "counts_summary": {"new_native_sourcetypes": 1, "families": len(families), "scenario_packs": 0}}
    (ROOT / "catalog" / "universe_batch7.json").write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    path = ROOT / "catalog" / "sourcetypes.json"
    rows = json.loads(path.read_text())
    if not any(r["splunk_sourcetype"] == st for r in rows):
        rows.append({"id": "nginx-plus-access", "splunk_sourcetype": st, "display_name": "NGINX Plus access (key=value)", "vendor_id": "nginx_f5",
                     "category": "Web Infrastructure", "data_kind": "event", "default_index": "idx_network_ops", "recommended_index": "netops_logs",
                     "generation_mode": "STATEFUL", "protocol": "hec", "sample_file": None, "required_ta": "Splunk Add-on for NGINX",
                     "aliases": [st], "deprecated_aliases": [], "is_benchmark_197": False, "status": "active",
                     "required_ta_review": {"status": "VERIFIED_DECLARED_BY_SPLUNKBASE", "splunkbase_ids": [3258],
                                            "basis": "Splunkbase release metadata declares this exact sourcetype. Declaration only: package not installed, parsing not validated."}})
        path.write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(reg["counts_summary"]))


if __name__ == "__main__":
    main()
