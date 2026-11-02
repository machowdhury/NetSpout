#!/usr/bin/env python3
"""Build catalog/replay_sources.json: authentic recorded samples already vendored in catalog/raw_reference, each with a verified timestamp rule.

Every entry is parsed end to end here (build_timeline) so a rule that does not fit the recorded bytes fails the build instead of the demo.
Provenance (pinned splunk/attack_data commit, declared size, sha256) comes from catalog/raw_reference/provenance.json by file hash.
Not included: Ollama server log (mixed slog, GIN and llama.cpp lines have no single timestamp rule). Excerpts fetched with a byte-range may end mid-record: those carry `drop_last_record` and the final (possibly partial) record is not replayed.
Run: python scripts/build_replay_sources.py   (idempotent; then scripts/sync_core.py)
"""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from netspout_core.sample_replay import TimestampRule as R, build_timeline  # noqa: E402

RAW = ROOT / "catalog" / "raw_reference"
ISO = lambda path: R("json_path", path, "iso8601")
SOURCES = [  # id, file, format, rule, title
    ("linux_syslog_messages", "linux_messages_syslog.head.bin", "syslog", R("regex", r"^([A-Z][a-z]{2} +\d{1,2} \d\d:\d\d:\d\d)", "syslog3164"), "Linux /var/log/messages"),
    ("auditd", "auditd.head.bin", "text", R("regex", r"audit\((\d\d/\d\d/\d{4} \d\d:\d\d:\d\d\.\d+):", "%m/%d/%Y %H:%M:%S.%f"), "Linux auditd (credential file access)"),
    ("nginx_access_combined", "universe_batch2/nginx.bin", "apache", R("regex", r"\[([^\]]+)\]", "%d/%b/%Y:%H:%M:%S %z"), "NGINX combined access log"),
    ("suricata_eve", "suricata.head.bin", "jsonl", ISO("timestamp"), "Suricata EVE JSON"),
    ("aws_cloudtrail", "aws_cloudtrail.head.bin", "jsonl", ISO("eventTime"), "AWS CloudTrail"),
    ("crowdstrike_sensor", "crowdstrike_events_sensor.head.bin", "jsonl", R("json_path", "timestamp", "epoch_ms"), "CrowdStrike Falcon sensor events"),
    ("crushftp_sessions", "crushftp_sessionlogs.head.bin", "text", R("regex", r"\|(\d\d/\d\d/\d{4} \d\d:\d\d:\d\d\.\d+)\|", "%m/%d/%Y %H:%M:%S.%f"), "CrushFTP session log"),
    ("mcp_jsonrpc", "mcp_jsonrpc.head.bin", "jsonl", ISO("timestamp"), "MCP JSON-RPC server log"),
    ("windows_sysmon_xml", "XmlWinEventLog.head.bin", "windows_xml", R("regex", r"SystemTime='([^']+)'", "iso8601"), "Windows Sysmon XML events"),
    ("sysmon_linux_xml", "sysmon_linux.head.bin", "windows_xml", R("regex", r'SystemTime="([^"]+)"', "iso8601"), "Sysmon for Linux XML events"),
]


SOURCETYPE_OVERRIDE = {"nginx_access_combined": "nginx:access"}  # not in provenance.json; the catalog sourcetype for this vendored sample


def main():
    prov = {r.get("fetched_sha256"): r for r in json.loads((RAW / "provenance.json").read_text())["references"]}
    out = []
    for sid, rel, fmt, rule, title in SOURCES:
        data = (RAW / rel).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        ref = prov.get(digest)
        truncated = bool(ref and int(ref.get("upstream_declared_size_bytes") or 0) > len(data)) or (ref is None and len(data) >= 131072)
        text = data.decode("utf-8")
        if truncated and fmt not in ("windows_xml",):
            text = text[:text.rstrip("\n").rfind("\n")]  # drop the possibly partial final line
        tl = build_timeline(text, fmt, rule)
        out.append({"id": sid, "title": title, "file": "catalog/raw_reference/" + rel, "sha256": digest, "format": fmt,
                    "sourcetype": SOURCETYPE_OVERRIDE.get(sid) or (ref or {}).get("sourcetype"), "drop_last_record": truncated and fmt not in ("windows_xml",),
                    "timestamp_rule": rule.__dict__, "records": len(tl.items), "span_s": round(tl.span_s, 3), "out_of_order_clamped": tl.out_of_order,
                    "provenance": ({"pinned_commit": (ref.get("download_url") or "/attack_data//").split("/attack_data/")[1].split("/")[0] or None,
                                   "upstream_path": ref.get("upstream_path") or ref.get("upstream_dataset_path"), "declared_size_bytes": ref.get("upstream_declared_size_bytes"),
                                   "excerpt_only": truncated} if ref else {"note": "vendored repository sample; see catalog/raw_reference/universe_batch*/references.json"})})
    doc = {"schema_version": "1.0", "note": "Authentic recorded samples; replay changes only the selected timestamp bytes. Sourcetype null = not recorded in provenance.json (caller must choose).",
           "sources": out}
    (ROOT / "catalog" / "replay_sources.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps([(s["id"], s["records"], s["sourcetype"], s["drop_last_record"]) for s in out]))


if __name__ == "__main__":
    main()
