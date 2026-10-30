#!/usr/bin/env python3
"""Vendor-TA parsing validation for NetSpout's native Windows/Sysmon generators, against the ISOLATED validation lab only.

Lab: tests/lab/ta_validation (container netspout_tavalidation_splunk, ports 19000/19191/19088). Never point this at the demo lab:
it assumes Splunk_TA_windows and Splunk_TA_microsoft_sysmon are installed. Credentials come from the git-ignored .env.lab and are never printed.

For every distinct (sourcetype, EventID) emitted by the native scenario packs, the same raw event is sent two ways:
  A "as NetSpout dispatches": HEC /event, sourcetype=<catalog name>, source=network-topology-simulator, time=send time
  B "forwarder-canonical":    HEC /raw,   sourcetype=XmlWinEventLog, source=<channel>, Splunk parses _time with the TA's props
Fixture transform (declared, applied to both variants): the event's own timestamp (SystemTime / Sysmon UtcTime) is moved 48 h into the
past so a correctly parsed _time cannot be confused with ingest time. No other byte of the event is changed.

Measured per event: indexed, _time source, extraction of the fields the event itself carries (EventCode, Computer and each
<Data Name=...>), TA-assigned tags/eventtypes, and the metadata predicate  sourcetype=XmlWinEventLog source="<channel>"  that Splunk
detection macros are commonly written against. CIM data models are NOT validated (Splunk_SA_CIM is not installed).
Usage: python scripts/validate_ta_windows.py [--out docs/verification/evidence/ta_validation/windows_sysmon.json]
"""
import argparse
import json
import re
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
ENV = dict(l.strip().split("=", 1) for l in (ROOT / "tests/lab/ta_validation/.env.lab").read_text().splitlines() if "=" in l)

import base64
import ssl
import urllib.parse
import urllib.request

CTX = ssl._create_unverified_context()  # isolated loopback lab, self-signed certificate
INDEX = "ta_validation"
PACKS = ["wave2_ws_credential_compromise_chain", "wave3_vsphere_hostpath_triage"]
SYSTEM_FIELDS = {"EventCode": r"<EventID[^>]*>(\d+)</EventID>", "Computer": r"<Computer>([^<]+)</Computer>"}


def mgmt(path, data=None):
    req = urllib.request.Request("https://127.0.0.1:%s%s" % (ENV["LAB_MGMT_PORT"], path),
                                 data=urllib.parse.urlencode(data).encode() if data is not None else None)
    req.add_header("Authorization", "Basic " + base64.b64encode(("admin:" + ENV["LAB_SPLUNK_PASSWORD"]).encode()).decode())
    return urllib.request.urlopen(req, context=CTX, timeout=120).read().decode()


def search(spl, earliest="-3d"):
    out = mgmt("/services/search/jobs/export", {"search": spl, "output_mode": "json", "earliest_time": earliest, "preview": "false"})
    return [json.loads(l)["result"] for l in out.splitlines() if '"result"' in l]


def hec(path, body, params=None, as_json=True):
    q = ("?" + urllib.parse.urlencode(params)) if params else ""
    req = urllib.request.Request("https://127.0.0.1:%s%s%s" % (ENV["LAB_HEC_PORT"], path, q),
                                 json.dumps(body).encode() if as_json else body.encode("utf-8"),
                                 {"Authorization": "Splunk " + ENV["LAB_HEC_TOKEN"], "Content-Type": "application/json" if as_json else "text/plain"})
    reply = json.loads(urllib.request.urlopen(req, context=CTX, timeout=60).read())
    if reply.get("code") != 0:
        raise RuntimeError("HEC rejected event")


def collect_events():
    from netspout_core.authentic_scenario_packs import run_scenario_pack
    picked = {}
    for sid in PACKS:
        for e in run_scenario_pack(sid, "ta-validation"):
            if e.sourcetype.startswith("XmlWinEventLog:"):
                m = re.search(r"<EventID[^>]*>(\d+)</EventID>", e.raw_log)
                picked.setdefault((e.sourcetype, m[1]), e)
    return [picked[k] for k in sorted(picked)]


def shift_time(raw, when):
    """Move the event's own timestamp; returns (raw, event_time). Handles Windows SystemTime and Sysmon UtcTime."""
    system = re.search(r"SystemTime=(['\"])([^'\"]+)\1", raw)
    stamp = when.strftime("%Y-%m-%dT%H:%M:%S.") + "%07dZ" % (when.microsecond * 10)
    raw = re.sub(r"(SystemTime=(['\"]))[^'\"]+(\2)", lambda m: m.group(1) + stamp + m.group(3), raw, count=1) if system else raw
    raw = re.sub(r"(<Data Name=(['\"])UtcTime\2>)[^<]+(</Data>)", lambda m: m.group(1) + when.strftime("%Y-%m-%d %H:%M:%S.") + "%03d" % (when.microsecond // 1000) + m.group(3), raw)
    return raw


def expected_fields(raw):
    fields = {name: re.search(rx, raw)[1] for name, rx in SYSTEM_FIELDS.items() if re.search(rx, raw)}
    for name, value in re.findall(r"<Data Name=['\"]([^'\"]+)['\"]>([^<]*)</Data>", raw):
        if value.strip() not in ("", "-"):
            fields[name] = value
    return fields


def main(out):
    run = uuid.uuid4().hex[:8]
    when = datetime.now(timezone.utc).replace(microsecond=123000) - timedelta(hours=48)
    events = collect_events()
    plan = []
    for i, e in enumerate(events):
        raw = shift_time(e.raw_log, when)
        eid = re.search(r"<EventID[^>]*>(\d+)</EventID>", raw)[1]
        for variant in ("A", "B"):
            host = "tav-%s-%s-%02d" % (run, variant, i)
            plan.append({"variant": variant, "host": host, "sourcetype": e.sourcetype, "event_id": eid, "raw": raw, "expected": expected_fields(raw)})
            if variant == "A":
                hec("/services/collector/event", {"event": raw, "sourcetype": e.sourcetype, "source": "network-topology-simulator", "host": host, "index": INDEX, "time": time.time()})
            else:
                hec("/services/collector/raw", raw, {"sourcetype": "XmlWinEventLog", "source": e.sourcetype, "host": host, "index": INDEX, "channel": str(uuid.uuid4())}, as_json=False)
    control = []  # authentic pinned Sysmon bytes, timestamp moved, labeled with a channel that has NO TA timestamp rule
    ref = (ROOT / "catalog/raw_reference/XmlWinEventLog.head.bin").read_bytes().decode("utf-8", "replace")
    for i, raw in enumerate(re.findall(r"<Event[ >].*?</Event>", ref, re.S)[:3]):
        host = "tav-%s-C-%02d" % (run, i)
        raw = shift_time(raw, when)
        hec("/services/collector/raw", raw, {"sourcetype": "XmlWinEventLog", "source": "XmlWinEventLog:Application", "host": host, "index": INDEX, "channel": str(uuid.uuid4())}, as_json=False)
        control.append(host)
    rows = []
    for _ in range(20):
        rows = search('search index=%s host="tav-%s-*" | eval epoch=_time | table host epoch _indextime sourcetype source tag eventtype *' % (INDEX, run))
        if len(rows) >= len(plan) + len(control):
            break
        time.sleep(3)
    by_host = {r["host"]: r for r in rows}
    event_epoch = when.timestamp()
    results = []
    for p in plan:
        r = by_host.get(p["host"])
        row = {"variant": p["variant"], "sourcetype_emitted": p["sourcetype"], "event_id": p["event_id"], "indexed": r is not None}
        if r:
            observed = {k for k, v in r.items() if v not in (None, "", "-") and not k.startswith("_")}
            norm = lambda f: re.sub(r"[^A-Za-z0-9]+", "_", f)  # the Windows TA normalizes names such as "Action ID" to Action_ID
            hit = sorted(f for f in p["expected"] if f in observed or norm(f) in observed)
            missing = sorted(f for f in p["expected"] if f not in observed and norm(f) not in observed)
            t = float(r["epoch"])
            row.update({
                "expected_fields": len(p["expected"]), "extracted": len(hit), "extraction_ratio": round(len(hit) / max(1, len(p["expected"])), 3), "missing_fields": missing,
                "time_delta_from_event_s": round(t - event_epoch, 3),
                "time_source": "event_timestamp" if abs(t - event_epoch) < 2 else "ingest_time" if abs(t - time.time()) < 600 else "other",
                "indexed_sourcetype": r.get("sourcetype"), "source": r.get("source"), "tags": r.get("tag"), "eventtypes": r.get("eventtype"),
            })
        results.append(row)
    # metadata predicate parity (what detection macros are typically written against), counted per variant
    predicate = {}
    for variant in ("A", "B"):
        n = search('search index=%s host="tav-%s-%s-*" sourcetype=XmlWinEventLog source="XmlWinEventLog:*" | stats count' % (INDEX, run, variant))
        predicate[variant] = int(n[0]["count"]) if n else 0
    control_rows = [by_host[h] for h in control if h in by_host]
    control_result = {"events": len(control), "indexed": len(control_rows),
                      "event_timestamp_parsed": sum(abs(float(r["epoch"]) - event_epoch) < 2 for r in control_rows),
                      "note": "authentic pinned Sysmon bytes labeled source=XmlWinEventLog:Application (no TA timestamp rule); parsing from the event body would show here only if Splunk found it by default"}
    time_rules = {}
    for stanza in ("source::XmlWinEventLog:Security", "source::XmlWinEventLog:System", "source::XmlWinEventLog:Microsoft-Windows-PowerShell/Operational",
                   "source::XmlWinEventLog:Microsoft-Windows-Windows Defender/Operational", "source::XmlWinEventLog:Microsoft-Windows-Sysmon/Operational", "XmlWinEventLog"):
        try:
            entry = json.loads(mgmt("/servicesNS/-/-/configs/conf-props/%s?output_mode=json" % urllib.parse.quote(stanza, safe="")))["entry"][0]
            time_rules[stanza] = {"app": entry["acl"]["app"], **{k: entry["content"].get(k) for k in ("TIME_PREFIX", "TIME_FORMAT", "MAX_TIMESTAMP_LOOKAHEAD", "DATETIME_CONFIG")}}
        except Exception:
            time_rules[stanza] = None
    summary = {}
    for variant in ("A", "B"):
        rs = [r for r in results if r["variant"] == variant]
        ok = [r for r in rs if r["indexed"]]
        summary[variant] = {"events": len(rs), "indexed": len(ok),
                            "mean_extraction_ratio": round(sum(r["extraction_ratio"] for r in ok) / max(1, len(ok)), 3),
                            "event_timestamp_parsed": sum(r["time_source"] == "event_timestamp" for r in ok),
                            "with_tags": sum(bool(r.get("tags")) for r in ok), "with_eventtypes": sum(bool(r.get("eventtypes")) for r in ok),
                            "source_predicate_matches": predicate[variant]}
    info = json.loads(mgmt("/services/server/info?output_mode=json"))["entry"][0]["content"]
    apps = {e["name"]: e["content"]["version"] for e in json.loads(mgmt("/services/apps/local?output_mode=json&count=0"))["entry"] if e["name"].startswith("Splunk_")}
    doc = {"run": run, "splunk_version": info["version"], "splunk_build": info["build"], "installed_vendor_apps": apps,
           "cim_installed": "Splunk_SA_CIM" in apps, "fixture_time_shift_hours": 48, "summary": summary,
           "authentic_control": control_result, "ta_timestamp_rules": time_rules, "events": results}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(doc, indent=1) + "\n")
    print(json.dumps({"splunk": info["version"], "apps": apps, "summary": summary}, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(ROOT / "docs/verification/evidence/ta_validation/windows_sysmon.json"))
    main(ap.parse_args().out)
