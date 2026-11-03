#!/usr/bin/env python3
"""Splunk Technology Add-on compatibility check. The add-on package is the source of truth.

  python scripts/ta_compat.py SPEC.json --offline [--packs DIR]
  python scripts/ta_compat.py SPEC.json --live ENVFILE [--packs DIR] [--out evidence.json]     (isolated lab only)

OFFLINE (reads the .spl, needs no Splunk): the sourcetype stanza exists in props.conf; every REPORT transform it names exists; the
force-sourcetype transform matches the representative events and not the negative ones; the leading timestamp parses with the add-on's
TIME_PREFIX/TIME_FORMAT; each event's expected message id is covered by the add-on's event type; expected actions agree with the add-on's lookup.
LIVE (isolated lab, ENVFILE keys LAB_SPLUNK_PASSWORD LAB_HEC_TOKEN LAB_MGMT_PORT LAB_HEC_PORT, never printed): events are sent through the product's own HEC
dispatcher (so product metadata is part of the test), then Splunk is searched: HEC acceptance, event count, sourcetype, index type (event/metric), each
expected field, event type and tags, negative payloads, and timestamp parsing through the HEC raw endpoint (which applies the add-on's props).
Exit 0 only if every check passes. Missing checks are reported as NOT_RUN, never as passed.
"""
import base64
import glob
import io
import json
import os
import re
import ssl
import sys
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]


# ----------------------------------------------------------------- TA package
def parse_conf(text):
    """Splunk .conf -> {stanza: {key: value}} (continuation lines joined; later duplicate keys win)."""
    out, cur, pend = {}, None, ""
    for line in text.splitlines():
        if pend:
            line, pend = pend + line.lstrip(), ""
        if line.endswith("\\"):
            pend = line[:-1]
            continue
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("[") and s.endswith("]"):
            cur = out.setdefault(s[1:-1], {})
        elif "=" in s and cur is not None:
            k, v = s.split("=", 1)
            cur[k.strip()] = v.strip()
    return out


class TA:
    def __init__(self, package):
        self.package = package
        self.files = {}
        with tarfile.open(package) as tf:
            for m in tf.getmembers():
                if m.isfile():
                    self.files[m.name] = tf.extractfile(m).read()
        self.root = next(n.split("/")[0] for n in self.files)
        g = lambda p: self.files.get("%s/%s" % (self.root, p), b"").decode("utf-8", "replace")
        self.app = parse_conf(g("default/app.conf"))
        self.props, self.transforms = parse_conf(g("default/props.conf")), parse_conf(g("default/transforms.conf"))
        self.eventtypes, self.tags = parse_conf(g("default/eventtypes.conf")), parse_conf(g("default/tags.conf"))
        self.lookups = {n.rsplit("/", 1)[1]: self.files[n].decode("utf-8", "replace") for n in self.files if "/lookups/" in n and n.endswith(".csv")}

    @property
    def version(self):
        return self.app.get("launcher", {}).get("version") or self.app.get("id", {}).get("version")


def _rx(pattern):
    return re.compile(re.sub(r"\(\?<([A-Za-z_]\w*)>", r"(?P<\1>", pattern))   # Splunk (?<name>) -> Python (?P<name>)


def _go(spec, **kw):
    ts = datetime.now(timezone.utc).strftime("%b %d %H:%M:%S")
    return spec.replace("{TS}", kw.get("ts", ts)).replace("{HOST}", kw.get("host", "fw-ta-compat"))


def _strptime_prefix(raw, props):
    """Parse the leading timestamp the way props.conf says (TIME_PREFIX, TIME_FORMAT, MAX_TIMESTAMP_LOOKAHEAD)."""
    prefix, fmt, look = props.get("TIME_PREFIX", ""), props.get("TIME_FORMAT"), int(props.get("MAX_TIMESTAMP_LOOKAHEAD", 128))
    m = re.match(prefix, raw) if prefix else None
    start = m.end() if m else 0
    window = raw[start:start + look]
    yearless = not re.search(r"%[YyCGg]", fmt)               # Splunk assumes the current year; a leap year keeps Feb 29 parseable
    for ln in range(len(window), 0, -1):                       # longest prefix of the window that parses
        try:
            return datetime.strptime(("2000 " if yearless else "") + window[:ln], ("%Y " if yearless else "") + fmt)
        except ValueError:
            continue
    return None


# --------------------------------------------------------------------- checks
class Report:
    def __init__(self):
        self.rows = []

    def add(self, name, ok, detail="", status=None):
        self.rows.append({"check": name, "status": status or ("PASS" if ok else "FAIL"), "detail": detail})

    def ok(self):
        return all(r["status"] == "PASS" for r in self.rows)


def offline(spec, ta, rep):
    st = spec["sourcetype"]
    rep.add("ta.version", ta.version == spec["ta"]["expected_version"], "installed package %s, expected %s" % (ta.version, spec["ta"]["expected_version"]))
    props = ta.props.get(st)
    rep.add("props.sourcetype_stanza", props is not None, "[%s] in props.conf" % st)
    if props is None:
        return
    names = [n.strip() for n in props.get("REPORT-cisco_asa_field_extractions", "").split(",") if n.strip()] if "REPORT-cisco_asa_field_extractions" in props else \
            [n.strip() for k, v in props.items() if k.startswith("REPORT-") for n in v.split(",") if n.strip()]
    missing = [n for n in names if n not in ta.transforms]
    rep.add("props.report_transforms_exist", bool(names) and not missing, "%d REPORT transforms, missing: %s" % (len(names), missing[:5]))
    force = [t for t in ta.transforms.values() if t.get("DEST_KEY") == "MetaData:Sourcetype" and t.get("FORMAT") == "sourcetype::" + st]
    rep.add("transforms.force_sourcetype_defined", len(force) == 1, "%d transform(s) set sourcetype::%s" % (len(force), st))
    frx = _rx(force[0]["REGEX"]) if force else None
    for ev in spec["events"]:
        raw = _go(ev["raw"])
        rep.add("force_sourcetype.matches[%s]" % ev["id"], bool(frx and frx.search(raw)), "regex %s" % (force[0]["REGEX"] if force else "-"))
        t = _strptime_prefix(raw, props)
        rep.add("timestamp.format_parses[%s]" % ev["id"], t is not None, "TIME_PREFIX=%r TIME_FORMAT=%r" % (props.get("TIME_PREFIX"), props.get("TIME_FORMAT")))
        mid = ev["expect"].get("message_id")
        et = ta.eventtypes.get(ev.get("eventtype", ""), {}).get("search", "") if ev.get("eventtype") else None
        if ev.get("eventtype"):
            rep.add("eventtype.covers_message_id[%s]" % ev["id"], et is not None and ('"%s"' % mid) in et, ev["eventtype"])
            for tag in ev.get("tags", []):
                rep.add("tags.defined[%s:%s]" % (ev["id"], tag), ta.tags.get("eventtype=" + ev["eventtype"], {}).get(tag) == "enabled")
        if "vendor_action" in ev["expect"] and "action" in ev["expect"]:
            rows = [r.split(",") for r in next(iter(ta.lookups.values()), "").splitlines()] if not any("action_lookup" in k for k in ta.lookups) else \
                   [r.split(",") for k, v in ta.lookups.items() if "action_lookup" in k for r in v.splitlines()]
            act = {r[0]: r[2] for r in rows if len(r) >= 3 and r[1] == ""}
            rep.add("lookup.action[%s]" % ev["id"], act.get(ev["expect"]["vendor_action"]) == ev["expect"]["action"], "TA lookup: %s -> %s" % (ev["expect"]["vendor_action"], act.get(ev["expect"]["vendor_action"])))
    for ng in spec.get("negative", []):
        if ng.get("expect_no_force_match") and frx:
            rep.add("force_sourcetype.rejects[%s]" % ng["id"], not frx.search(_go(ng["raw"])), "negative payload must not be claimed by the add-on")


# ------------------------------------------------------------------------ live
class Lab:
    def __init__(self, envfile):
        e = dict(l.strip().split("=", 1) for l in open(envfile) if "=" in l)
        self.ctx = ssl._create_unverified_context()      # isolated lab on loopback, self-signed certificate
        self.mgmt, self.hec_port, self.token = "https://127.0.0.1:%s" % e["LAB_MGMT_PORT"], e["LAB_HEC_PORT"], e["LAB_HEC_TOKEN"]
        self.auth = "Basic " + base64.b64encode(("admin:" + e["LAB_SPLUNK_PASSWORD"]).encode()).decode()

    def rest(self, path, data=None):
        r = urllib.request.Request(self.mgmt + path, data=urllib.parse.urlencode(data).encode() if data else None, headers={"Authorization": self.auth})
        return json.loads(urllib.request.urlopen(r, context=self.ctx, timeout=120).read())

    def search(self, q, earliest="-3h", latest="+1h"):
        d = {"search": q if q.strip().startswith(("|", "search")) else "search " + q, "exec_mode": "oneshot", "output_mode": "json", "count": "0", "earliest_time": earliest, "latest_time": latest}
        return self.rest("/services/search/jobs", d).get("results", [])

    def wait_count(self, q, n, timeout=60, earliest="-3h"):
        end = time.time() + timeout
        rows = []
        while time.time() < end:
            rows = self.search(q, earliest=earliest)
            if len(rows) >= n:
                break
            time.sleep(3)
        return rows

    def hec_raw(self, raw, sourcetype, index, host, fields):
        qs = urllib.parse.urlencode({"sourcetype": sourcetype, "index": index, "host": host})
        r = urllib.request.Request("https://127.0.0.1:%s/services/collector/raw?%s" % (self.hec_port, qs), data=raw.encode(), headers={"Authorization": "Splunk " + self.token})
        return json.loads(urllib.request.urlopen(r, context=self.ctx, timeout=30).read()).get("code") == 0


def live(spec, ta, lab, rep):
    from netspout_core.models import LogEntry, TelemetryTransportConfig
    from netspout_core.telemetry_dispatcher import dispatcher
    st, index = spec["sourcetype"], spec["index"]
    run = "tacompat-" + uuid.uuid4().hex[:10]
    cfg = TelemetryTransportConfig(hec_url="https://127.0.0.1:%s/services/collector/event" % lab.hec_port, hec_token=lab.token, hec_index=index, hec_ssl_verify=False, hec_allow_insecure_tls=True)
    # installed version
    app = lab.rest("/services/apps/local/%s?output_mode=json" % spec["ta"]["id"])["entry"][0]["content"]
    rep.add("lab.installed_version", app.get("version") == ta.version and not app.get("disabled"), "lab has %s %s, package %s" % (app.get("label"), app.get("version"), ta.version))
    idx = lab.rest("/services/data/indexes/%s?output_mode=json" % index)["entry"][0]["content"]
    rep.add("routing.index_datatype", idx.get("datatype") == spec["kind"], "index %s datatype=%s, expected %s" % (index, idx.get("datatype"), spec["kind"]))
    sent = []
    for case in spec["events"] + spec.get("negative", []):
        raw = _go(case["raw"])
        le = LogEntry(timestamp=datetime.now(timezone.utc).isoformat(), device_id="fw-ta-compat", src_ip="192.0.2.1", dest_ip="192.0.2.2", protocol="TCP", duration="0ms", action="streamed", signature="TA_COMPAT",
                      status="normal", raw_log=raw, node_type="firewall", node_id="fw", vendor=spec.get("vendor", "v"), sourcetype=st, netspout_run_id=run, netspout_event_id="%s-%s" % (run, case["id"]))
        res = dispatcher.dispatch_log(le, cfg)
        sent.append((case, bool(res["hec"] and res["hec"]["success"])))
    rep.add("hec.accepted", all(ok for _, ok in sent), "%d/%d accepted" % (sum(ok for _, ok in sent), len(sent)))
    rows = lab.wait_count("index=%s netspout_run_id=%s | fields *" % (index, run), len(sent))
    rep.add("index.event_count", len(rows) == len(sent), "indexed %d of %d" % (len(rows), len(sent)))
    rep.add("index.sourcetype", {r.get("sourcetype") for r in rows} == {st}, "sourcetypes seen: %s" % sorted({r.get("sourcetype") for r in rows}))
    by = {r.get("netspout_event_id"): r for r in rows}
    for case, _ in sent:
        r = by.get("%s-%s" % (run, case["id"]))
        if r is None:
            rep.add("event.indexed[%s]" % case["id"], False, "not found")
            continue
        for f, want in case.get("expect", {}).items():
            got = r.get(f)
            rep.add("field[%s.%s]" % (case["id"], f), got == want, "expected %r, Splunk returned %r" % (want, got))
        for f in case.get("expect_absent", []):
            rep.add("absent[%s.%s]" % (case["id"], f), r.get(f) in (None, ""), "Splunk returned %r" % r.get(f))
        if case.get("eventtype"):
            ets = r.get("eventtype"); ets = ets if isinstance(ets, list) else [ets]
            rep.add("eventtype[%s]" % case["id"], case["eventtype"] in ets, "Splunk returned %s" % ets)
            tg = r.get("tag"); tg = tg if isinstance(tg, list) else [tg]
            rep.add("tags[%s]" % case["id"], set(case.get("tags", [])) <= set(tg), "Splunk returned %s" % tg)
    # searchability by an independent search
    n = lab.search("index=%s sourcetype=%s netspout_run_id=%s message_id=* | stats count" % (index, st, run))
    marker = _rx(ta.transforms[spec["id_transform"]]["REGEX"])          # the add-on's own definition of which payloads carry a message id
    want = sum(1 for c, _ in sent if marker.search(_go(c["raw"])))
    rep.add("search.by_run_and_message_id", bool(n) and int(n[0]["count"]) == want, "Splunk: %s events with message_id; add-on regex %s matches %d" % (n[0]["count"] if n else None, spec["id_transform"], want))
    # timestamp parsing by the add-on (HEC raw endpoint applies props.conf)
    if spec.get("timestamp", {}).get("raw_endpoint_check"):
        tsrun = "ts-" + uuid.uuid4().hex[:8]
        probe = spec["events"][0]
        past = datetime.fromtimestamp(time.time() - 3 * 3600, tz=timezone.utc)      # three hours ago: parsed time must follow the text, not the arrival time
        raw = _go(probe["raw"], ts=past.strftime("%b %d %H:%M:%S"), host=tsrun)
        ok = lab.hec_raw(raw, st, index, tsrun, {})
        got = lab.wait_count("index=%s host=%s | fields _time" % (index, tsrun), 1, earliest="-6h")
        if ok and got:
            t = datetime.fromisoformat(got[0]["_time"])
            skew = abs((t - past.replace(microsecond=0)).total_seconds())
            rep.add("timestamp.parsed_from_event_text", skew <= spec["timestamp"].get("max_skew_seconds", 5), "_time %s vs text %s (skew %ds)" % (got[0]["_time"], past.strftime("%H:%M:%S"), skew))
        else:
            rep.add("timestamp.parsed_from_event_text", False, "raw endpoint accepted=%s found=%s" % (ok, bool(got)))
    return run


def main(argv):
    spec_path = argv[0]
    spec = json.load(open(spec_path))
    packs = Path(argv[argv.index("--packs") + 1]).expanduser() if "--packs" in argv else Path("~/netspout/private-packs").expanduser()
    pkg = sorted(glob.glob(str(packs / spec["ta"]["package_glob"])))
    if not pkg:
        print("NOT_RUN: add-on package %s not found in %s" % (spec["ta"]["package_glob"], packs))
        return 2
    ta, rep = TA(pkg[-1]), Report()
    offline(spec, ta, rep)
    run = None
    if "--live" in argv:
        run = live(spec, ta, Lab(argv[argv.index("--live") + 1]), rep)
    else:
        rep.add("live", False, "not requested", status="NOT_RUN")
    out = {"spec": os.path.basename(spec_path), "ta": {"id": spec["ta"]["id"], "package": os.path.basename(pkg[-1]), "version": ta.version}, "run_id": run,
           "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"), "checks": rep.rows,
           "summary": {s: sum(1 for r in rep.rows if r["status"] == s) for s in ("PASS", "FAIL", "NOT_RUN")}}
    if "--out" in argv:
        Path(argv[argv.index("--out") + 1]).write_text(json.dumps(out, indent=1) + "\n")
    for r in rep.rows:
        print("%-5s %-52s %s" % (r["status"], r["check"], r["detail"][:110]))
    print(json.dumps(out["summary"]))
    return 0 if rep.ok() else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
