#!/usr/bin/env python3
"""Round-trip check of the NetFlow/IPFIX wire path for every NetFlow solution scenario (isolated lab only).
generated FlowRecords -> real IPFIX over UDP (existing encoder/transport) -> GoFlow2 -> flows.json -> record_from_goflow -> normalize
must equal normalize(source record), field by field, for exporter-independent fields. Exporter identity is compared through the observation domain id (300 + sorted exporter index).
Needs the lab collector stack (deploy/collector, project pf-lab-flow) and docker for reading the collector's named volume.
ok = every record the collector decoded equals the source record on all compared fields (UDP can lose datagrams; completeness_pct reports how many arrived, it is not hidden).
Evidence: docs/verification/evidence/netflow/wire_roundtrip.json. Usage: PYTHONPATH=src python scripts/validate_netflow_wire.py"""
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from netspout_core import netflow_solution as nf, netflow_wire

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/verification/evidence/netflow/wire_roundtrip.json"
FIELDS = ["flowStartMilliseconds", "flowEndMilliseconds", "duration_ms", "src_ip", "src_port", "dest_ip", "dest_port", "protocol", "tcp_flags", "bytes", "packets", "tos", "dscp", "snmp_in", "snmp_out", "src_as", "dest_as", "app"]


def lines():
    """Decoded rows in order. A row is parsed with raw_decode so two objects written back to back without a newline still count as two rows."""
    text = subprocess.run(["docker", "run", "--rm", "-v", "netspout_flow_data:/flows", "busybox", "sh", "-c", "cat /flows/flows.json"], capture_output=True, text=True, check=True).stdout
    dec, i, rows = json.JSONDecoder(), 0, []
    while i < len(text):
        while i < len(text) and text[i] in "\n\r ":
            i += 1
        if i >= len(text):
            break
        try:
            obj, i = dec.raw_decode(text, i)
        except ValueError:
            break   # a half-written trailing row; it is picked up on the next read
        rows.append(obj)
    return rows


def one(sid):
    rows = nf.generate(sid, "wire-check", seed=42)
    n0 = len(lines())
    res = netflow_wire.export(rows, {"NETSPOUT_COLLECTOR_HOST": "127.0.0.1"})
    for _ in range(30):
        new = lines()[n0:]
        if len(new) >= len(rows):
            break
        time.sleep(0.5)
    decoded = new
    doms = {ip: 300 + i for i, ip in enumerate(sorted({r["exporter_ip"] for r in rows}))}
    src = {}
    for r in rows:
        ev = nf.normalize(r["record"], r["exporter_ip"])
        src.setdefault((ev["src_ip"], ev["src_port"], ev["dest_ip"], ev["dest_port"], ev["flowStartMilliseconds"], ev["exporter_ip"]), []).append(ev)
    matched, mism, unmatched = 0, {}, 0
    rev = {v: k for k, v in doms.items()}
    for d in decoded:
        exp = rev.get(d.get("observation_domain_id"))
        got = nf.normalize_goflow(d, exporter_ip=exp)
        cand = src.get((got["src_ip"], got["src_port"], got["dest_ip"], got["dest_port"], got["flowStartMilliseconds"], exp))
        if not cand:
            unmatched += 1
            continue
        want = cand.pop()
        bad = [f for f in FIELDS if want[f] != got[f]]
        for f in bad:
            mism[f] = mism.get(f, 0) + 1
        matched += not bad
    return {"scenario_id": sid, "generated": len(rows), "udp_exported": res["udp_exported"], "datagrams": res["datagrams"], "collector_decoded_counter": res["collector_decoded"], "wire_state": res["state"],
            "rows_in_collector_file": len(decoded), "fully_equal": matched, "unmatched_rows": unmatched, "field_mismatches": mism,
            "completeness_pct": round(100.0 * len(decoded) / len(rows), 1), "ok": bool(decoded) and len(decoded) == matched and not unmatched}


def main():
    import sys
    prev = {r["scenario_id"]: r for r in json.loads(OUT.read_text())["scenarios"]} if OUT.exists() and sys.argv[1:] else {}
    prev.update({r["scenario_id"]: r for r in (one(s) for s in (sys.argv[1:] or nf.IDS))})
    out = [prev[s] for s in nf.IDS if s in prev]
    for r in out:
        print(("PASS " if r["ok"] else "FAIL ") + r["scenario_id"], r["generated"], r["udp_exported"], r["collector_decoded_counter"], r["fully_equal"], r["field_mismatches"], str(r["completeness_pct"]) + "% of exported records reached the collector file", flush=True)
    OUT.write_text(json.dumps({"generated_utc": datetime.now(timezone.utc).isoformat(timespec="minutes"), "collector": "netsampler/goflow2:v2.2.5 (lab)", "protocol": "IPFIX over UDP",
                               "compared_fields": FIELDS, "scenarios": out}, indent=1) + "\n")


if __name__ == "__main__":
    main()
