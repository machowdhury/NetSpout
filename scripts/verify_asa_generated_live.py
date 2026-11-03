#!/usr/bin/env python3
"""Deliver bounded cisco:asa telemetry from (1) the repaired YAML replay engine and (2) the native generator through the product's HEC dispatcher into the
isolated TA lab, then compare what the installed Splunk Add-on for Cisco ASA extracted with the values written in the raw ASA text (Cisco message formats,
tests/fixtures/cisco_asa/message_formats.json). Lab credentials come from the git-ignored env file; nothing secret is printed or written.

  python scripts/verify_asa_generated_live.py tests/lab/ta_validation/.env.lab OUT.json
"""
import json
import random
import re
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src"), str(ROOT / "scripts")]
import ta_compat  # noqa: E402
from netspout_core.asa_generator import generate_asa_entries  # noqa: E402
from netspout_core.models import LogEntry, TelemetryTransportConfig  # noqa: E402
from netspout_core.telemetry_dispatcher import dispatcher  # noqa: E402
from netspout_core.yaml_sample_replay import load_sample_set  # noqa: E402

FIX = json.loads((ROOT / "tests/fixtures/cisco_asa/message_formats.json").read_text())
HEADER = re.compile(FIX["header"])
# message text -> expected Splunk fields (group order follows the Cisco templates in the fixture)
MAP = {"302013": ["direction", "session_id", "src_interface", "src_ip", "src_port", None, None, "dest_interface", "dest_ip", "dest_port"],
       "302015": ["direction", "session_id", "src_interface", "src_ip", "src_port", None, None, "dest_interface", "dest_ip", "dest_port"],
       "302014": ["session_id", "src_interface", "src_ip", "src_port", "dest_interface", "dest_ip", "dest_port", "duration_text", "bytes"],
       "302016": ["session_id", "src_interface", "src_ip", "src_port", "dest_interface", "dest_ip", "dest_port", "duration_text", "bytes"],
       "106023": ["transport", "src_interface", "src_ip", "src_port", "dest_interface", "dest_ip", "dest_port"]}


def expected(raw):
    code = re.search(r"%ASA-\d-(\d{6})", raw).group(1)
    rx = re.compile(FIX["formats"][code]) if code in FIX["formats"] else None
    m = rx.search(raw) if rx else None
    exp = {"message_id": code, "log_level": re.search(r"%ASA-(\d)-", raw).group(1)}
    if m and code in MAP:
        for name, val in zip(MAP[code], m.groups()):
            if name == "duration_text":
                h, mi, s = (int(x) for x in val.split(":")); exp["duration"] = str(h * 3600 + mi * 60 + s)
            elif name:
                exp[name] = val.lower() if name == "transport" else val
        if code in ("302013", "302014", "302015", "302016"):
            exp["transport"] = "tcp" if code in ("302013", "302014") else "udp"
    return exp


def run(label, raws, lab, index):
    run_id = "p3-%s-%s" % (label, uuid.uuid4().hex[:8])
    cfg = TelemetryTransportConfig(hec_url="https://127.0.0.1:%s/services/collector/event" % lab.hec_port, hec_token=lab.token, hec_index=index, hec_ssl_verify=False, hec_allow_insecure_tls=True)
    acc = 0
    for i, raw in enumerate(raws):
        le = LogEntry(timestamp=datetime.now(timezone.utc).isoformat(), device_id=raw.split()[3], src_ip="192.0.2.1", dest_ip="192.0.2.2", protocol="TCP", duration="0ms", action="streamed", signature="ASA_PHASE3",
                      status="normal", raw_log=raw, node_type="firewall", node_id="fw", vendor="cisco_asa", sourcetype="cisco:asa", netspout_run_id=run_id, netspout_event_id="%s-%03d" % (run_id, i))
        acc += bool(dispatcher.dispatch_log(le, cfg)["hec"]["success"])
    rows = lab.wait_count("index=%s netspout_run_id=%s | fields *" % (index, run_id), len(raws))
    by = {r["netspout_event_id"]: r for r in rows}
    mism, fields_checked, ok_events = [], 0, 0
    for i, raw in enumerate(raws):
        r = by.get("%s-%03d" % (run_id, i))
        if not r:
            mism.append({"event": i, "problem": "not indexed"}); continue
        bad = []
        for f, want in expected(raw).items():
            fields_checked += 1
            if r.get(f) != want:
                bad.append({"field": f, "expected": want, "splunk": r.get(f)})
        if r.get("sourcetype") != "cisco:asa":
            bad.append({"field": "sourcetype", "splunk": r.get("sourcetype")})
        (mism.append({"event": i, "raw": raw[:100], "mismatches": bad}) if bad else None)
        ok_events += not bad
    ids = {}
    for r in rows:
        ids[r.get("message_id")] = ids.get(r.get("message_id"), 0) + 1
    ets = {}
    for r in rows:
        for e in (r.get("eventtype") if isinstance(r.get("eventtype"), list) else [r.get("eventtype")]):
            ets[e] = ets.get(e, 0) + 1
    return {"label": label, "run_id": run_id, "generated": len(raws), "hec_accepted": acc, "indexed": len(rows), "events_fully_matching": ok_events, "fields_compared": fields_checked,
            "message_ids": dict(sorted(ids.items(), key=lambda kv: str(kv[0]))), "eventtypes": dict(sorted(ets.items(), key=lambda kv: str(kv[0]))), "mismatches": mism,
            "examples": [{"raw": r["_raw"], "_time": r["_time"], **{k: r.get(k) for k in ("sourcetype", "host", "message_id", "action", "vendor_action", "src_ip", "dest_ip", "src_port", "dest_port", "transport", "eventtype")}} for r in rows[:3]]}


def main(env, out):
    lab = ta_compat.Lab(env)
    sample = load_sample_set(str(ROOT / "netspout/appserver/static/samples/cisco-asa/cisco-asa.yml")).restrict_to("cisco:asa")
    rng, replay = random.Random(21), []
    for _ in range(3):
        replay += sample.render_all(rng, datetime.now(timezone.utc))
    native = [e.raw_log for e in generate_asa_entries(30, seed=4)]
    for raws in (replay, native):
        assert all(HEADER.match(x) and "$" not in x and "sourcetype:" not in x for x in raws)   # only raw ASA syslog, no YAML metadata, no placeholders
    result = {"replay": run("replay", replay, lab, "ta_validation"), "native": run("native", native, lab, "ta_validation")}
    Path(out).write_text(json.dumps(result, indent=1) + "\n")
    for k, v in result.items():
        print(k, {x: v[x] for x in ("generated", "hec_accepted", "indexed", "events_fully_matching", "fields_compared")}, "mismatched events:", len(v["mismatches"]))
    return 0 if all(not v["mismatches"] and v["indexed"] == v["generated"] == v["hec_accepted"] for v in result.values()) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1], sys.argv[2]))
