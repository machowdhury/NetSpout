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


def ta_defined_fields(ta, st):
    """Field names the add-on defines for a sourcetype (EVAL, FIELDALIAS, LOOKUP outputs, REPORT/EXTRACT groups and FIELDS). kv: DELIMS without FIELDS (keys come from the event)."""
    names, kv = set(), False
    p = ta.props.get(st, {})
    for k, v in p.items():
        if k.startswith("EVAL-"):
            names.add(k[5:])
        elif k.startswith("FIELDALIAS-"):
            names |= set(re.findall(r"\bas\s+([A-Za-z_]\w*)", v, re.I))
        elif k.startswith("LOOKUP-"):
            tail = re.split(r"\bOUTPUT(?:NEW)?\b", v, maxsplit=1)
            if len(tail) == 2:
                names |= set(re.findall(r"([A-Za-z_]\w*)", re.sub(r"\w+\s+as\s+", "", tail[1], flags=re.I)))
        elif k.startswith("EXTRACT-"):
            names |= set(re.findall(r"\(\?P?<([A-Za-z_]\w*)>", v))
        elif k.startswith("REPORT-"):
            for n in (x.strip() for x in v.split(",") if x.strip()):
                t = ta.transforms.get(n, {})
                names |= set(re.findall(r"\(\?P?<([A-Za-z_]\w*)>", t.get("REGEX", "")))
                names |= set(re.findall(r"([A-Za-z_]\w*)::", t.get("FORMAT", "")))
                names |= {f.strip().strip('"') for f in t.get("FIELDS", "").split(",") if f.strip()}
                kv = kv or (bool(t.get("DELIMS")) and not t.get("FIELDS"))
    return names, kv


def _rx(pattern):
    return re.compile(re.sub(r"\(\?<([A-Za-z_]\w*)>", r"(?P<\1>", pattern))   # Splunk (?<name>) -> Python (?P<name>)


def _go(spec, when=None, host="fw-ta-compat", **kw):
    """Render placeholders: {TS} BSD syslog time, {DATE} {TIME} ISO parts, {TS_SLASH} 'YYYY/MM/DD HH:MM:SS', {TS_DEV} 'YYYY Mon DD HH:MM:SS UTC' (device time), {HOST}."""
    t = when or datetime.now(timezone.utc)
    if "ts" in kw:                                         # legacy callers pass a pre-rendered syslog time
        return spec.replace("{TS}", kw["ts"]).replace("{HOST}", host)
    return (spec.replace("{TS}", t.strftime("%b %d %H:%M:%S")).replace("{DATE}", t.strftime("%Y-%m-%d")).replace("{TIME}", t.strftime("%H:%M:%S"))
            .replace("{TS_SLASH}", t.strftime("%Y/%m/%d %H:%M:%S")).replace("{TS_DEV}", t.strftime("%Y %b %d %H:%M:%S UTC")).replace("{HOST}", host))


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


def _lookup(ta, file_contains, key, value, inp):
    """Value of column `value` for the first row whose column `key` equals `inp`, in the add-on's own lookup CSV."""
    import csv
    for name, text in ta.lookups.items():
        if file_contains in name:
            for row in csv.DictReader(io.StringIO(text), skipinitialspace=True):
                row = {(k or "").strip(): (v or "").strip() for k, v in row.items()}
                if row.get(key) == inp and row.get(value, "") != "":
                    return row[value]
    return None


def _force_matches_name(fmt, st):
    pat = re.escape(fmt[len("sourcetype::"):]).replace(r"\$1", "(.+)").replace("$1", "(.+)")
    return re.fullmatch(pat, st) is not None


def _forced(frx, raw):
    """The sourcetype the add-on's routing transforms would assign to raw, or None (the first matching transform wins, $1 is the first capture group)."""
    for rx, fmt in frx:
        m = rx.search(raw)
        if m:
            return fmt.replace("$1", m.group(1) if m.groups() else "")
    return None


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
    force = [t for t in ta.transforms.values() if t.get("DEST_KEY") == "MetaData:Sourcetype" and str(t.get("FORMAT", "")).startswith("sourcetype::") and _force_matches_name(t["FORMAT"], st)]
    explicit = spec.get("routing") == "explicit_input"           # the add-on has no routing transform for this sourcetype: the input (or HEC token) must set it
    if explicit:
        rep.add("transforms.force_sourcetype_defined", False, "the add-on has no transform that assigns [%s]; the sourcetype must be set by the input (HEC sourcetype). Routing is not verified." % st, status="NOT_RUN")
        force = []
    else:
        rep.add("transforms.force_sourcetype_defined", len(force) >= 1, "%d transform(s) can set sourcetype::%s" % (len(force), st))
    frx = [(_rx(t["REGEX"]), t["FORMAT"][len("sourcetype::"):]) for t in force]
    for ev in spec["events"]:
        raw = _go(ev["raw"])
        if not explicit:
            rep.add("force_sourcetype.assigns_expected[%s]" % ev["id"], _forced(frx, raw) == st, "add-on routing assigns %r, expected %r" % (_forced(frx, raw), st))
        if props.get("TIME_FORMAT"):
            t = _strptime_prefix(raw, props)
            rep.add("timestamp.format_parses[%s]" % ev["id"], t is not None, "TIME_PREFIX=%r TIME_FORMAT=%r" % (props.get("TIME_PREFIX"), props.get("TIME_FORMAT")))
        else:
            rep.add("timestamp.format_parses[%s]" % ev["id"], False, "the add-on sets no TIME_FORMAT for [%s] (Splunk auto-detects); verified live only" % st, status="NOT_RUN")
        known, kvmode = ta_defined_fields(ta, st)
        for f in ev.get("expect", {}):
            ok = f in known or (kvmode and re.search(r"\b%s=" % re.escape(f), raw) is not None)
            rep.add("ta_defines_field[%s.%s]" % (ev["id"], f), ok, "field %s is defined by the add-on for [%s]" % (f, st))
        mid = ev["expect"].get("message_id")
        et = ta.eventtypes.get(ev.get("eventtype", ""), {}).get("search", "") if ev.get("eventtype") else None
        if ev.get("eventtype"):
            rep.add("eventtype.defined_and_covers[%s]" % ev["id"], et is not None and (mid is None or ('"%s"' % mid) in et), "%s%s" % (ev["eventtype"], " covers message id %s" % mid if mid else " (defined; no message id to cover)"))
            for tag in ev.get("tags", []):
                rep.add("tags.defined[%s:%s]" % (ev["id"], tag), ta.tags.get("eventtype=" + ev["eventtype"], {}).get(tag) == "enabled")
        lk = ev.get("lookup")
        if lk:
            got = _lookup(ta, lk["file_contains"], lk["key"], lk["value"], lk["input"])
            rep.add("lookup[%s]" % ev["id"], got == lk["expect"], "add-on lookup %s: %s=%s -> %s=%r (expected %r)" % (lk["file_contains"], lk["key"], lk["input"], lk["value"], got, lk["expect"]))
    for ng in spec.get("negative", []):
        if ng.get("expect_no_force_match") and force:
            rep.add("force_sourcetype.rejects[%s]" % ng["id"], _forced(frx, _go(ng["raw"])) != st, "negative payload must not be routed to %s (add-on assigns %r)" % (st, _forced(frx, _go(ng["raw"]))))


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
        sentinels = {"action": "streamed", "signature": "TA_COMPAT", "src_ip": "192.0.2.1", "dest_ip": "192.0.2.2", "protocol": "TCP"}
        shadowed = {k: r.get(k) for k, v in sentinels.items() if r.get(k) == v or (isinstance(r.get(k), list) and v in r.get(k))}
        rep.add("ownership.no_netspout_values_in_vendor_fields[%s]" % case["id"], not shadowed, "NetSpout test values found in vendor/CIM fields: %s" % (shadowed or "none"))
        for f in case.get("expect_absent", []):
            rep.add("absent[%s.%s]" % (case["id"], f), r.get(f) in (None, ""), "Splunk returned %r" % r.get(f))
        if case.get("eventtype"):
            ets = r.get("eventtype"); ets = ets if isinstance(ets, list) else [ets]
            rep.add("eventtype[%s]" % case["id"], case["eventtype"] in ets, "Splunk returned %s" % ets)
            tg = r.get("tag"); tg = tg if isinstance(tg, list) else [tg]
            rep.add("tags[%s]" % case["id"], set(case.get("tags", [])) <= set(tg), "Splunk returned %s" % tg)
    # searchability by an independent search
    n = lab.search("index=%s sourcetype=%s netspout_run_id=%s message_id=* | stats count" % (index, st, run))
    if spec.get("id_transform"):
        marker = _rx(ta.transforms[spec["id_transform"]]["REGEX"])          # the add-on's own definition of which payloads carry a message id
        want = sum(1 for c, _ in sent if marker.search(_go(c["raw"])))
        rep.add("search.by_run_and_message_id", bool(n) and int(n[0]["count"]) == want, "Splunk: %s events with message_id; add-on regex %s matches %d" % (n[0]["count"] if n else None, spec["id_transform"], want))
    else:
        rep.add("search.by_run", len(lab.search("index=%s sourcetype=%s netspout_run_id=%s | stats count by host" % (index, st, run))) >= 1, "events searchable by run id and sourcetype")
    # timestamp parsing by the add-on (HEC raw endpoint applies props.conf)
    if spec.get("timestamp", {}).get("raw_endpoint_check"):
        tsrun = "ts-" + uuid.uuid4().hex[:8]
        probe = spec["events"][0]
        past = datetime.fromtimestamp(time.time() - 3 * 3600, tz=timezone.utc)      # three hours ago: parsed time must follow the text, not the arrival time
        raw = _go(probe["raw"], when=past, host=tsrun)
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
