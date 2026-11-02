#!/usr/bin/env python3
"""NetFlow v9 and IPFIX end to end with an INDEPENDENT collector: PulseForge encoders -> UDP -> GoFlow2 (netsampler/goflow2 v2.2.5, pinned image already present locally,
run as a throw-away container on loopback ports) -> decoded JSON compared with the records sent -> repository flow forwarder -> isolated lab HEC -> independent Splunk search.
Nothing is sent as HEC JSON by the exporter side. Credentials from the git-ignored lab env file, never printed.  Usage: PYTHONPATH=src:backend python scripts/validate_flow_e2e.py
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
import validate_ta_windows as lab  # noqa: E402
from netspout_core.models import FlowRecord  # noqa: E402
from netspout_core.exporter_session import ExporterSession  # noqa: E402
from netspout_core.netflow_v9_encoder import NetFlowV9Encoder  # noqa: E402
from netspout_core.ipfix_encoder import IPFIXEncoder  # noqa: E402

IMAGE = "netsampler/goflow2:v2.2.5"
NAME = "pf_goflow2_validation"
V9_PORT, IPFIX_PORT = 12055, 14739
INDEX = "dev_test_replay"
results = {}


def check(name, ok, **detail):
    results[name] = {"pass": bool(ok), **detail}
    print(("PASS " if ok else "FAIL ") + name)


def main():
    work = Path(tempfile.mkdtemp(prefix="pf_flows_"))
    os.chmod(work, 0o777)
    flows = work / "flows.json"
    flows.write_text("")
    os.chmod(flows, 0o666)
    subprocess.run(["docker", "rm", "-f", NAME], capture_output=True)
    run = subprocess.run(["docker", "run", "-d", "--rm", "--name", NAME, "--user", "100:65533", "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
                          "-p", "127.0.0.1:%d:2055/udp" % V9_PORT, "-p", "127.0.0.1:%d:4739/udp" % IPFIX_PORT, "-v", "%s:/flows" % work, IMAGE,
                          "-listen", "netflow://:2055,netflow://:4739", "-format", "json", "-transport", "file", "-transport.file", "/flows/flows.json"], capture_output=True, text=True)
    if run.returncode:
        print("could not start collector:", run.stderr[:200])
        return 2
    try:
        time.sleep(3)
        marker = 40000 + int(time.time()) % 20000                      # unique source port identifies this run's records
        sent = []
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s9, si = ExporterSession(node_id="r1", source_id=101), ExporterSession(node_id="r1", observation_domain_id=101)
        for i in range(3):
            rec9 = FlowRecord(src_ip="10.0.1.%d" % (10 + i), dest_ip="10.0.2.20", bgp_next_hop="10.0.1.1", input_snmp=3, output_snmp=5, packets_count=1024 + i, bytes_count=524288 + i,
                              start_time_ms=120000, end_time_ms=125000, src_port=marker + i, dest_port=443, tcp_flags=0x18, protocol=6, tos_dscp=0, src_as=65535, dest_as=61440)
            sock.sendto(NetFlowV9Encoder.build_packet(session=s9, data_records=[rec9], include_template=(i == 0), sim_time_sec=int(time.time()), sys_uptime_ms=125000), ("127.0.0.1", V9_PORT))
            sent.append(("NETFLOW_V9", rec9))
            reci = FlowRecord(src_ip="10.0.3.%d" % (10 + i), dest_ip="10.0.4.20", src_port=marker + 10 + i, dest_port=8443, protocol=6, tos_dscp=0, tcp_flags=0x0018, input_snmp=3, output_snmp=5,
                              packets_count=2048 + i, bytes_count=1048576 + i, start_time_ms=int(time.time() * 1000) - 5000, end_time_ms=int(time.time() * 1000), src_as=65535, dest_as=61440)
            sock.sendto(IPFIXEncoder.build_packet(session=si, data_records=[reci], include_template=(i == 0), sim_time_sec=int(time.time())), ("127.0.0.1", IPFIX_PORT))
            sent.append(("IPFIX", reci))
            time.sleep(0.2)
        decoded = []
        for _ in range(20):
            time.sleep(1)
            decoded = [json.loads(l) for l in flows.read_text().splitlines() if l.strip()]
            mine = [d for d in decoded if marker <= int(d.get("src_port", 0)) < marker + 20]
            if len(mine) >= len(sent):
                break
        mine = {int(d["src_port"]): d for d in decoded if marker <= int(d.get("src_port", 0)) < marker + 20}
        check("01_collector_decoded_every_datagram", len(mine) == len(sent), sent=len(sent), decoded=len(mine))
        mism = []
        for proto, r in sent:
            d = mine.get(r.src_port)
            if not d:
                mism.append((r.src_port, "missing"))
                continue
            want = {"type": proto, "src_addr": r.src_ip, "dst_addr": r.dest_ip, "src_port": r.src_port, "dst_port": r.dest_port, "proto": {6: "TCP"}[r.protocol], "bytes": r.bytes_count, "packets": r.packets_count,
                    "etype": "IPv4", "in_if": r.input_snmp, "out_if": r.output_snmp}
            got = {k: (d.get(k) if k != "type" else d.get("type")) for k in want}
            bad = {k: (want[k], got[k]) for k in want if str(want[k]) != str(got[k])}
            if bad:
                mism.append((r.src_port, bad))
        check("02_decoded_fields_equal_the_records_sent_v9_and_ipfix", not mism, mismatches=mism[:3], fields=["type", "src_addr", "dst_addr", "src_port", "dst_port", "proto", "bytes", "packets", "etype", "in_if", "out_if"])
        check("03_template_then_data_semantics_both_protocols", {d["type"] for d in mine.values()} == {"NETFLOW_V9", "IPFIX"}, types=sorted({d["type"] for d in mine.values()}))
        # forward through the repository forwarder to the isolated lab and verify independently
        os.environ.update({"SPLUNK_HEC_URL": "https://127.0.0.1:%s/services/collector/event" % lab.ENV["LAB_HEC_PORT"], "SPLUNK_HEC_TOKEN": lab.ENV["LAB_HEC_TOKEN"], "SPLUNK_HEC_ALLOW_INSECURE_TLS": "true",
                           "SPLUNK_INDEX": INDEX, "SPLUNK_SOURCETYPE": "netflow:collector", "FLOW_FILE": str(flows)})
        sys.path.insert(0, str(ROOT / "deploy" / "collector"))
        import forwarder  # noqa: E402
        ok = sum(1 for d in mine.values() if forwarder.forward_to_splunk(d))
        check("04_forwarder_delivered_every_decoded_flow_to_hec", ok == len(mine), delivered=ok)
        rows = []
        for _ in range(15):
            out = lab.mgmt("/services/search/jobs/export", {"search": 'search index=%s sourcetype="netflow:collector" earliest=-15m | search src_port>=%d src_port<%d | stats count by type' % (INDEX, marker, marker + 20), "output_mode": "json", "preview": "false"})
            rows = [json.loads(l)["result"] for l in out.splitlines() if '"result"' in l]
            if sum(int(r["count"]) for r in rows) >= len(mine):
                break
            time.sleep(3)
        got = {r["type"]: int(r["count"]) for r in rows}
        check("05_splunk_holds_the_decoded_flows_per_protocol", got == {"NETFLOW_V9": 3, "IPFIX": 3}, indexed=got)
    finally:
        subprocess.run(["docker", "rm", "-f", NAME], capture_output=True)
    doc = {"generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "collector": IMAGE + " (independent, third-party decoder)", "exporter": "PulseForge NetFlow v9 and IPFIX encoders over UDP",
           "lab": "isolated Docker Splunk Enterprise 10.2.7", "passed": sum(v["pass"] for v in results.values()), "failed": [k for k, v in results.items() if not v["pass"]], "checks": results,
           "not_claimed": ["sFlow", "J-Flow beyond NetFlow v9 compatibility", "IPv6 flows", "Cisco Flexible NetFlow templates beyond the encoder's standard fields", "Splunk Stream or other vendor flow add-ons"]}
    out = ROOT / "docs/verification/evidence/flow/flow_e2e.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1, default=str) + "\n")
    print(json.dumps({"passed": doc["passed"], "failed": doc["failed"]}))
    return 1 if doc["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
