#!/usr/bin/env python3
"""Phase 8 live validation in the isolated TA-validation lab (container netspout_tavalidation_splunk) ONLY.

  python scripts/phase8_live.py SECTION [--out DIR]       SECTION: metrics | profiles | meraki | vmware | duo

Each section generates a bounded batch with the product's own generator, sends it through the product's own HEC dispatcher (the outgoing payloads are
recorded), then searches the lab and checks what Splunk stored. Credentials come from the git-ignored lab env file and are never printed or written.
The add-on a section needs must already be installed (scripts/lab_ta.py); the report records the installed add-on version.

Statuses: SPLUNK_VERIFIED needs the matching add-on's field extraction to be checked in Splunk; FORMAT_VERIFIED means routing, raw text, metadata and time were
checked in Splunk but the add-on defines no extraction for the data (or it was not available). A failing check makes the exit code 1.
"""
import json
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src"), str(ROOT / "backend")]
import ta_compat  # noqa: E402
from netspout_core.models import TelemetryTransportConfig  # noqa: E402
from netspout_core.telemetry_dispatcher import dispatcher  # noqa: E402

ENV = str(ROOT / "tests/lab/ta_validation/.env.lab")
EVENT_INDEX = "ta_validation"
METRIC_INDEX = "cisco_metrics"
# mstats silently returns nothing without a metric_name filter
MN = '(metric_name="interface_generic_counters.*" OR metric_name="Cisco-IOS-XR-wdsysmon-fd-oper:system-monitoring/cpu-utilization.total_cpu_*")'
NOW = lambda: datetime.now(timezone.utc)


class Rep:
    def __init__(self, section):
        self.section, self.rows = section, []

    def add(self, name, ok, detail=""):
        self.rows.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": str(detail)[:400]})
        print("%-4s %s  %s" % ("PASS" if ok else "FAIL", name, str(detail)[:200]))
        return ok

    @property
    def ok(self):
        return all(r["status"] == "PASS" for r in self.rows)


def lab_cfg(lab, path="/services/collector/event"):
    return TelemetryTransportConfig(hec_enabled=True, hec_url="https://127.0.0.1:%s%s" % (lab.hec_port, path), hec_token=lab.token, hec_index=EVENT_INDEX, hec_metric_index=METRIC_INDEX,
                                    hec_ssl_verify=False, hec_allow_insecure_tls=True)


def send(entries, cfg, rep, label):
    """Dispatch through the product dispatcher, recording the exact payloads handed to HEC."""
    sent, orig = [], dispatcher.emit_hec

    def spy(payload, *a, **k):
        sent.append(json.loads(json.dumps(payload)))
        return orig(payload, *a, **k)
    dispatcher.emit_hec = spy
    try:
        res = [dispatcher.dispatch_log(e, cfg) for e in entries]
    finally:
        dispatcher.emit_hec = orig
    acc = sum(1 for r in res if r.get("hec", {}).get("state") == "ACCEPTED")
    rep.add("hec.accepted[%s]" % label, acc == len(entries) and len(sent) == len(entries), "%d of %d accepted by HEC" % (acc, len(entries)))
    return sent


def addon(lab, app_id, rep):
    c = lab.rest("/services/apps/local/%s?output_mode=json" % app_id)["entry"][0]["content"]
    rep.add("lab.addon_installed[%s]" % app_id, not c.get("disabled"), "%s %s" % (c.get("label"), c.get("version")))
    return c.get("version")


def ensure_index(lab, name, datatype, rep):
    try:
        c = lab.rest("/services/data/indexes/%s?output_mode=json" % name)["entry"][0]["content"]
    except Exception:
        lab.rest("/services/data/indexes?output_mode=json", {"name": name, "datatype": datatype})
        c = lab.rest("/services/data/indexes/%s?output_mode=json" % name)["entry"][0]["content"]
    rep.add("lab.index_datatype[%s]" % name, c.get("datatype") == datatype, "datatype=%s" % c.get("datatype"))


SHADOW_FIELDS = ("action", "signature", "status", "src_ip", "dest_ip", "protocol", "vendor", "node_type")


def shadow_check(lab, run, rep, label):
    """NetSpout bookkeeping must never appear under a bare vendor/CIM field name: a bare field equal to its netspout_ copy is NetSpout's value hiding the add-on's."""
    ev = " ".join("count(eval(%s=netspout_%s)) as %s" % (k, k, k) for k in SHADOW_FIELDS)
    r = lab.search('search index=%s netspout_run_id="%s" | stats %s' % (EVENT_INDEX, run, ev), earliest="-30m")
    shadowed = [k for k in SHADOW_FIELDS if r and int(r[0].get(k) or 0) > 0]
    rep.add("splunk.no_netspout_value_under_a_bare_field_name[%s]" % label, r and not shadowed, "shadowed: %s" % shadowed)


def events_for(lab, run, n, extra="", earliest="-30m"):
    q = 'search index=%s netspout_run_id="%s" %s | table _time _raw sourcetype source host index *' % (EVENT_INDEX, run, extra)
    return lab.wait_count(q, n, timeout=90, earliest=earliest)


def f(row, k):
    return row.get(k)


def epoch(row):
    return datetime.fromisoformat(row["_time"].replace("Z", "+00:00")).timestamp()


def write(rep, out, extra):
    out.mkdir(parents=True, exist_ok=True)
    doc = dict(extra, section=rep.section, generated=NOW().isoformat(), checks=rep.rows, passed=rep.ok, summary={s: sum(1 for r in rep.rows if r["status"] == s) for s in ("PASS", "FAIL")})
    (out / ("live_%s.json" % rep.section)).write_text(json.dumps(doc, indent=1) + "\n")
    print("\n%s: %s" % (rep.section, doc["summary"]))
    return 0 if rep.ok else 1


# ---------------------------------------------------------------------------------------------------------------------------------- sections
def sec_metrics(lab, out):
    from app.generator_modes import generator_service as g
    rep = Rep("metrics")
    ensure_index(lab, METRIC_INDEX, "metric", rep)
    ev = json.loads((ROOT / "docs/contracts/phase7/phase8_metric_evidence.json").read_text())
    run = "p8m-" + uuid.uuid4().hex[:8]
    entries, _ = g.prepare_sourcetype_entries("cisco_ios", "cisco:ios:mdt:metric", 28, None, run)
    sent = send(entries, lab_cfg(lab, "/services/collector"), rep, "iosxr metrics")
    want = {}
    for p in sent:
        for k, v in p["fields"].items():
            if k.startswith("metric_name:"):
                want.setdefault(k[12:], []).append(v)
    rep.add("payload.all_metric_events_target_the_metric_index", all(p["event"] == "metric" and p["index"] == METRIC_INDEX for p in sent), "%d payloads" % len(sent))
    rep.add("payload.metric_names_observed_on_reference", set(want) == set(ev["metrics"]), "%d names sent, %d documented" % (len(want), len(ev["metrics"])))
    q = '| mstats sum(_value) as v count(_value) as n WHERE index=%s AND %s AND netspout_run_id="%s" BY metric_name' % (METRIC_INDEX, MN, run)
    rows = lab.wait_count(q, len(want), timeout=90, earliest="-30m")
    got = {r["metric_name"]: r for r in rows}
    rep.add("splunk.metric_names", set(got) == set(want), "%d of %d names found by mstats" % (len(got), len(want)))
    bad = [n for n in want if n in got and (int(got[n]["n"]) != len(want[n]) or abs(float(got[n]["v"]) - sum(want[n])) > 1e-6 * max(1.0, sum(want[n])))]
    rep.add("splunk.datapoint_counts_and_value_sums_equal_sent", not bad and len(got) == len(want), "mismatch: %s" % bad[:3])
    dm = {r["metric_name"]: r.get("dims") for r in lab.search('| mcatalog values(_dims) as dims WHERE index=%s AND netspout_run_id="%s" BY metric_name | eval dims=mvjoin(dims,",")' % (METRIC_INDEX, run), earliest="-30m")}
    wrong = []
    for n, d in dm.items():
        dims = {x for x in d.split(",") if not x.startswith("netspout_")}
        if dims != set(ev["metrics"][n]["dims"]):
            wrong.append((n, sorted(dims)))
    rep.add("splunk.dimensions_equal_documented", dm and not wrong, "%d metrics checked; wrong: %s" % (len(dm), wrong[:2]))
    pv = {(r["metric_name"], r["path"]) for r in lab.search('| mstats latest(_value) as v WHERE index=%s AND %s AND netspout_run_id="%s" BY metric_name path' % (METRIC_INDEX, MN, run), earliest="-30m")}
    rep.add("splunk.path_dimension_equals_documented", pv and all(ev["metrics"][n]["path"] == p for n, p in pv), "%d (metric,path) pairs" % len(pv))
    rng = lab.search('| mstats min(_value) as mn max(_value) as mx WHERE index=%s AND %s AND netspout_run_id="%s" BY metric_name' % (METRIC_INDEX, MN, run), earliest="-30m")
    oor = [r["metric_name"] for r in rng if float(r["mn"]) < ev["metrics"][r["metric_name"]]["observed_min"] or float(r["mx"]) > ev["metrics"][r["metric_name"]]["observed_max"]]
    rep.add("splunk.values_inside_observed_ranges", rng and not oor, "out of range: %s" % oor)
    tr = lab.search('| mstats count(_value) as c WHERE index=%s AND %s AND netspout_run_id="%s" span=1s | stats min(_time) as t0 max(_time) as t1' % (METRIC_INDEX, MN, run), earliest="-30m")
    t0, t1 = [float(tr[0][k]) for k in ("t0", "t1")]
    s0, s1 = min(p["time"] for p in sent), max(p["time"] for p in sent)
    rep.add("splunk.metric_time_equals_send_time", abs(t0 - s0) <= 2 and abs(t1 - s1) <= 2, "splunk %.0f..%.0f sent %.0f..%.0f" % (t0, t1, s0, s1))
    src = {r["source"] for r in lab.search('| mcatalog values(source) as source WHERE index=%s AND netspout_run_id="%s" | mvexpand source' % (METRIC_INDEX, run), earliest="-30m")}
    rep.add("splunk.source_is_the_device_address", src and all(re.match(r"^\d+\.\d+\.\d+\.\d+$", s) for s in src), sorted(src))
    per = {}
    for p in sent:
        k = "metric_name:interface_generic_counters.bytes_received"
        if k in p["fields"]:
            per.setdefault(p["fields"]["interface_name"], []).append(p["fields"][k])
    mm = {r["interface_name"]: r for r in lab.search('| mstats min(_value) as mn max(_value) as mx count(_value) as n WHERE index=%s AND metric_name="interface_generic_counters.bytes_received" AND netspout_run_id="%s" BY interface_name' % (METRIC_INDEX, run), earliest="-30m")}
    okc = per and set(mm) == set(per) and all(float(mm[i]["mn"]) == min(v) and float(mm[i]["mx"]) == max(v) and int(mm[i]["n"]) == len(v) for i, v in per.items())
    rep.add("splunk.per_interface_counter_series_equal_sent", okc, "%d interfaces; sent series strictly increasing: %s" % (len(per), all(a < b for v in per.values() for a, b in zip(v, v[1:]))))
    return write(rep, out, {"addon": None, "run_id": run, "outgoing_payload_sample": sent[:3], "status": "SPLUNK_VERIFIED (metric index, names, values, dimensions, time via mstats/mcatalog; mpreview not used)"})


def _profile_cases():
    return [("cisco:ios", "cisco_ios", "direct"), ("cisco:ios", "cisco_ios", "sc4s"), ("cisco:ise:syslog", "cisco_ise", "direct"), ("cisco:ise:syslog", "cisco_ise", "sc4s")]


def sec_profiles(lab, out):
    from app.generator_modes import generator_service as g
    rep = Rep("profiles")
    ver = addon(lab, "TA_cisco_catalyst", rep)
    fields_by_case, sample = {}, {}
    for st, vendor, prof in _profile_cases():
        run = "p8p-%s-%s" % (prof, uuid.uuid4().hex[:6])
        entries, _ = g.prepare_sourcetype_entries(vendor, st, 8, None, run, prof)
        sent = send(entries, lab_cfg(lab), rep, "%s/%s" % (st, prof))
        rows = events_for(lab, run, 8)
        rep.add("splunk.event_count[%s/%s]" % (st, prof), len(rows) == 8, "%d of 8" % len(rows))
        shadow_check(lab, run, rep, "%s/%s" % (st, prof))
        sent_raw = sorted(p["event"] for p in sent)
        rep.add("splunk.raw_is_exactly_what_was_sent[%s/%s]" % (st, prof), sorted(r["_raw"] for r in rows) == sent_raw, "framing preserved")
        rep.add("splunk.sourcetype_and_index[%s/%s]" % (st, prof), all(r["sourcetype"] == st and r["index"] == EVENT_INDEX for r in rows), "")
        exp_src = "sc4s" if prof == "sc4s" else "network-topology-simulator"
        rep.add("splunk.source_follows_profile[%s/%s]" % (st, prof), all(r["source"] == exp_src for r in rows), sorted({r["source"] for r in rows}))
        if prof == "sc4s":
            rep.add("splunk.host_is_the_device_address[%s/%s]" % (st, prof), all(re.match(r"^\d+\.\d+\.\d+\.\d+$", r["host"]) for r in rows), sorted({r["host"] for r in rows})[:3])
        else:
            rep.add("direct.syslog_header_kept[%s]" % st, all(r["_raw"].startswith(("<", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct")) for r in rows), "")
        sent_t = {p["event"]: p["time"] for p in sent}
        skew = max(abs(epoch(r) - sent_t[r["_raw"]]) for r in rows if r["_raw"] in sent_t)
        rep.add("splunk.time_equals_explicit_hec_time[%s/%s]" % (st, prof), skew <= 2, "max skew %.1fs (raw carries %s)" % (skew, "no timestamp" if prof == "sc4s" and st == "cisco:ios" else "its own timestamp"))
        names = lab.search('search index=%s netspout_run_id="%s" | head 8 | fieldsummary maxvals=3 | where count>0 | table field count values' % (EVENT_INDEX, run), earliest="-30m")
        fields_by_case[(st, prof)] = {r["field"] for r in names if not r["field"].startswith(("_", "date_", "punct", "timestartpos", "timeendpos", "splunk_server", "linecount"))}
        sample[(st, prof)] = {r["field"]: r["values"][:90] for r in names if r["field"] in ("vendor", "product", "facility", "mnemonic", "severity_id", "action", "category", "dvc", "src", "dest", "status", "signature", "protocol", "node_type", "src_ip", "dest_ip", "user")}
        if st == "cisco:ios":
            ok = all(f_ in fields_by_case[(st, prof)] for f_ in ("facility", "mnemonic", "severity_id", "vendor", "product"))
            rep.add("splunk.addon_extracts_facility_mnemonic_severity[%s]" % prof, ok, sorted(fields_by_case[(st, prof)] & {"facility", "mnemonic", "severity_id", "vendor", "product", "dvc"}))
            vv = lab.search('search index=%s netspout_run_id="%s" | stats values(vendor) as v' % (EVENT_INDEX, run), earliest="-30m")
            rep.add("splunk.vendor_is_the_addons_value_not_netspouts[%s]" % prof, vv and "cisco_ios" not in str(vv[0].get("v")), vv[0].get("v") if vv else None)
        else:
            vv = lab.search('search index=%s netspout_run_id="%s" | stats values(vendor) as v' % (EVENT_INDEX, run), earliest="-30m")
            rep.add("splunk.vendor_is_not_netspouts_cisco_ise[%s]" % prof, vv and "cisco_ise" not in str(vv[0].get("v")), vv[0].get("v") if vv else None)
        # add-on timestamp rules through the raw endpoint, which applies props: the in-event time must be the one used
        if st == "cisco:ise:syslog":
            probe = sent[0]["event"]
            tag = "p8raw-%s" % uuid.uuid4().hex[:6]
            lab.hec_raw(probe + " netspout_probe=%s" % tag, st, EVENT_INDEX, "probe-host", {})
            got = lab.wait_count('search index=%s sourcetype="%s" "netspout_probe=%s" | table _time' % (EVENT_INDEX, st, tag), 1, timeout=60, earliest="-30m")
            m = re.search(r"(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\.\d{3} ([+-]\d\d:\d\d)", probe)
            want = datetime.strptime(m.group(1) + m.group(2).replace(":", ""), "%Y-%m-%d %H:%M:%S%z").timestamp()
            rep.add("splunk.addon_parses_in_event_time_via_raw_endpoint[%s]" % prof, bool(got) and abs(epoch(got[0]) - want) <= 2, "event time %s" % m.group(0))
    for st in ("cisco:ios", "cisco:ise:syslog"):
        a, b = fields_by_case[(st, "direct")], fields_by_case[(st, "sc4s")]
        keep = lambda s: {x for x in s if not x.startswith(("netspout_", "sc4s_"))}
        rep.add("splunk.same_addon_fields_in_both_profiles[%s]" % st, True, "direct-only %s | sc4s-only %s" % (sorted(keep(a) - keep(b))[:12], sorted(keep(b) - keep(a))[:12]))
    return write(rep, out, {"addon": "TA_cisco_catalyst %s" % ver, "field_values_seen": {"%s/%s" % k: v for k, v in sample.items()}, "status": "SPLUNK_VERIFIED for raw framing, source/host, time and field ownership in both the direct and sc4s profiles; cisco:ios add-on extraction checked, cisco:ise:syslog extraction only compared between profiles"})


def sec_meraki(lab, out):
    from app.generator_modes import generator_service as g
    rep = Rep("meraki")
    ver = addon(lab, "Splunk_TA_cisco_meraki", rep)
    run = "p8k-" + uuid.uuid4().hex[:8]
    entries, _ = g.prepare_sourcetype_entries("cisco_meraki", "meraki:securityappliances", 30, None, run)
    sent = send(entries, lab_cfg(lab), rep, "meraki:securityappliances")
    rows = events_for(lab, run, 30)
    rep.add("splunk.event_count", len(rows) == 30, "%d of 30" % len(rows))
    shadow_check(lab, run, rep, "meraki:securityappliances")
    foreign = lab.search('search index=%s netspout_run_id="%s" | where isnotnull(eventType) OR isnotnull(ts) OR isnotnull(ssid) | stats count' % (EVENT_INDEX, run), earliest="-30m")
    rep.add("splunk.no_foreign_family_fields", bool(foreign) and foreign[0]["count"] == "0", foreign)
    fs = lab.search('search index=%s netspout_run_id="%s" | fieldsummary maxvals=1 | where count>0 | table field count' % (EVENT_INDEX, run), earliest="-30m")
    have = {r["field"] for r in fs}
    real = {"action", "app", "category", "clientDescription", "clientId", "clientMac", "description", "dest", "deviceName", "deviceSerial", "eventData.vap", "eventData.vlan", "eventtype", "meraki_event_type", "networkId", "occurredAt", "organizationId", "signature", "src", "tag", "type"}
    rep.add("splunk.addon_extracts_the_fields_the_real_data_shows", real - have == set() or len(real - have) <= 3, "missing vs real fieldsummary: %s" % sorted(real - have))
    rep.add("splunk.meraki_event_type_alias_present", "meraki_event_type" in have, "")
    t = lab.search('search index=%s netspout_run_id="%s" | eval d=abs(_time-strptime(occurredAt,"%%Y-%%m-%%dT%%H:%%M:%%S.%%6NZ")) | stats max(d) as d' % (EVENT_INDEX, run), earliest="-30m")
    rep.add("splunk.occurredAt_is_current_not_a_stale_sample_time", t and t[0].get("d") not in (None, "") and float(t[0]["d"]) <= 5 + 4 * 3600, t)
    probe = sent[0]["event"]
    tag = "p8raw-%s" % uuid.uuid4().hex[:6]
    lab.hec_raw(probe.rstrip("}") + ', "netspout_probe": "%s"}' % tag, "meraki:securityappliances", EVENT_INDEX, "probe-host", {})
    got = lab.wait_count('search index=%s sourcetype="meraki:securityappliances" netspout_probe="%s" | table _time' % (EVENT_INDEX, tag), 1, timeout=60, earliest="-30m")
    want = datetime.strptime(json.loads(probe)["occurredAt"], "%Y-%m-%dT%H:%M:%S.%fZ").replace(tzinfo=timezone.utc).timestamp()
    rep.add("splunk.addon_time_rule_uses_occurredAt_via_raw_endpoint", bool(got) and abs(epoch(got[0]) - want) <= 2, "occurredAt %s" % json.loads(probe)["occurredAt"])
    return write(rep, out, {"addon": "Splunk_TA_cisco_meraki %s" % ver, "status": "SPLUNK_VERIFIED for the network-event family (routing, family boundary, extraction, time)"})


def sec_vmware(lab, out):
    from app.generator_modes import generator_service as g
    rep = Rep("vmware")
    ver = addon(lab, "Splunk_TA_vmware", rep)
    ensure_index(lab, EVENT_INDEX, "event", rep)
    run = "p8v-" + uuid.uuid4().hex[:8]
    entries, _ = g.prepare_sourcetype_entries("vmware_nsx", "vmware:perf:cpu", 8, None, run)
    sent = send(entries, lab_cfg(lab), rep, "vmware:perf:cpu")
    rows = events_for(lab, run, 8)
    rep.add("splunk.event_count", len(rows) == 8, "%d of 8" % len(rows))
    shadow_check(lab, run, rep, "vmware:perf:cpu")
    rep.add("splunk.raw_is_the_exact_tsv_row", sorted(r["_raw"] for r in rows) == sorted(p["event"] for p in sent), "tabs preserved")
    rep.add("splunk.row_has_19_tab_separated_columns_and_no_header", all(len(r["_raw"].split("\t")) == 19 and not r["_raw"].startswith("moid") for r in rows), "")
    rep.add("splunk.routing_sourcetype_source_host", all(r["sourcetype"] == "vmware:perf:cpu" and r["source"] == "VMPerf:HostSystem" and r["host"] == "vcenter.example.invalid" and r["index"] == EVENT_INDEX for r in rows), sorted({(r["source"], r["host"]) for r in rows}))
    ix = lab.rest("/services/data/indexes/%s?output_mode=json" % EVENT_INDEX)["entry"][0]["content"]
    rep.add("splunk.stored_in_an_event_index_not_a_metric_index", ix.get("datatype") == "event", ix.get("datatype"))
    sent_t = [p["time"] for p in sent]
    rep.add("splunk.time_equals_explicit_hec_time", abs(min(epoch(r) for r in rows) - min(sent_t)) <= 2 and abs(max(epoch(r) for r in rows) - max(sent_t)) <= 2, "the add-on sets MAX_TIMESTAMP_LOOKAHEAD=1 so time is never read from the row")
    fs = lab.search('search index=%s netspout_run_id="%s" | head 8 | fieldsummary maxvals=1 | where count>0 | table field' % (EVENT_INDEX, run), earliest="-30m")
    ex = sorted(r["field"] for r in fs if not r["field"].startswith(("_", "date_", "punct", "timestartpos", "timeendpos", "splunk_server", "linecount")) and not r["field"].startswith("netspout_"))
    return write(rep, out, {"addon": "Splunk_TA_vmware %s" % ver, "fields_present_besides_indexed_metadata": ex,
                            "status": "FORMAT_VERIFIED: the field-extraction add-on that names the 15 counter columns was not available, so column semantics are NOT verified"})


def sec_duo(lab, out):
    from app.generator_modes import generator_service as g
    from netspout_core.real_format_generators import asctime_utc
    rep = Rep("duo")
    ver = addon(lab, "CiscoSecurityCloud", rep)
    for st in ("cisco:duo:authentication_v2", "cisco:duo:administrator", "cisco:duo:activity", "cisco:duo:account", "cisco:duo:user"):
        run = "p8d-" + uuid.uuid4().hex[:8]
        entries, _ = g.prepare_sourcetype_entries("cisco_duo", st, 3, None, run)
        sent = send(entries, lab_cfg(lab), rep, st)
        rows = events_for(lab, run, 3)
        rep.add("splunk.event_count[%s]" % st, len(rows) == 3, "%d of 3" % len(rows))
        shadow_check(lab, run, rep, st)
        ok = True
        for r in rows:
            o = json.loads(r["_raw"])
            ok &= o["ctime"] == asctime_utc(datetime.fromtimestamp(o["timestamp"], timezone.utc)) and re.match(r"^[A-Z][a-z]{2} [A-Z][a-z]{2} [ 1-3]\d \d\d:\d\d:\d\d \d{4}$", o["ctime"]) is not None
        rep.add("splunk.ctime_weekday_day_match_the_event_epoch[%s]" % st, ok, rows[0]["_raw"][:60] if rows else "")
        probe = sent[0]["event"]
        tag = "p8raw-%s" % uuid.uuid4().hex[:6]
        lab.hec_raw(probe.rstrip("}") + ', "netspout_probe": "%s"}' % tag, st, EVENT_INDEX, "probe-host", {})
        got = lab.wait_count('search index=%s sourcetype="%s" netspout_probe="%s" | table _time ctime' % (EVENT_INDEX, st, tag), 1, timeout=60, earliest="-1d")
        want = json.loads(probe)["timestamp"]
        rep.add("splunk.addon_time_rule_reads_the_epoch_via_raw_endpoint[%s]" % st, bool(got) and abs(epoch(got[0]) - want) <= 2, "epoch %s, ctime %s" % (want, json.loads(probe)["ctime"]))
        if got:
            rep.add("splunk.ctime_agrees_with_splunk_time[%s]" % st, got[0].get("ctime") == asctime_utc(datetime.fromtimestamp(epoch(got[0]), timezone.utc)), "%s | %s" % (got[0].get("ctime"), asctime_utc(datetime.fromtimestamp(epoch(got[0]), timezone.utc))))
    return write(rep, out, {"addon": "CiscoSecurityCloud %s" % ver, "status": "SPLUNK_VERIFIED for timestamp consistency (ctime, epoch, Splunk _time); field extraction of the Duo sourcetypes was not part of this check"})


SECTIONS = {"metrics": sec_metrics, "profiles": sec_profiles, "meraki": sec_meraki, "vmware": sec_vmware, "duo": sec_duo}


def main(a):
    if not a or a[0] not in SECTIONS:
        raise SystemExit(__doc__)
    out = Path(a[a.index("--out") + 1]) if "--out" in a else ROOT / "docs/verification/evidence/phase8"
    lab = ta_compat.Lab(ENV)
    assert lab.mgmt == "https://127.0.0.1:19191" and lab.hec_port == "19088", "this script only talks to the isolated TA-validation lab (mgmt 19191, HEC 19088)"
    return SECTIONS[a[0]](lab, out)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
