#!/usr/bin/env python3
"""Phase 17 acceptance driver for the single-package Enterprise app, run against a disposable Splunk (never a protected or remote one).

Prerequisite: ONLY netspout.spl is installed in the Splunk under test (no external engine anywhere), Splunk restarted once, and the Connection Center saved.
Everything goes through Splunk's own REST surface (/services/netspout_gateway), as the browser does, with Splunk users. Each result is verified by an
independent Splunk search, not only by the engine's own counters.

  P17_MGMT=https://127.0.0.1:18089 P17_PASSWORD_FILE=<0600 file> python scripts/phase17_acceptance.py <section> [...]
sections: events metrics scenario stream authz idle
Evidence (no secrets) is written to docs/verification/evidence/phase17/<section>.json
"""
import base64
import json
import os
import re
import secrets
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

MGMT = os.environ.get("P17_MGMT", "https://127.0.0.1:18089")
PW = Path(os.environ["P17_PASSWORD_FILE"]).read_text().strip()
EV = Path(__file__).resolve().parents[1] / "docs" / "verification" / "evidence" / "phase17"
CTX = ssl.create_default_context()
CTX.check_hostname, CTX.verify_mode = False, ssl.CERT_NONE
IDX, MIDX = "dev_test_replay", "dev_test_replay_metrics"
EVENT_CASES = [("cisco:asa", "cisco_asa"), ("cisco:ios", "cisco_ios"), ("fortigate_traffic", "fortinet"),
               ("pan:traffic", "palo_alto"), ("pan:threat", "palo_alto"), ("pan:system", "palo_alto")]
METRIC_CASE = ("cisco:ios:mdt:metric", "cisco_ios")


def http(method, path, body=None, form=None, user="admin", password=None, timeout=120):
    data, headers = None, {}
    if user:
        headers["Authorization"] = "Basic " + base64.b64encode(("%s:%s" % (user, password or PW)).encode()).decode()
    if body is not None:
        data, headers["Content-Type"] = json.dumps(body).encode(), "application/json"
    if form is not None:
        data, headers["Content-Type"] = urllib.parse.urlencode(form).encode(), "application/x-www-form-urlencoded"
    req = urllib.request.Request(MGMT + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw.strip().startswith(("{", "[")) else raw)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except ValueError:
            return e.code, raw


def gw(method, path, body=None, **kw):
    return http(method, "/services/netspout_gateway" + path, body=body, **kw)


def search(spl, earliest="-24h", user="admin", password=None):
    data = urllib.parse.urlencode({"search": spl if spl.lstrip().startswith(("|", "search")) else "search " + spl, "output_mode": "json", "earliest_time": earliest}).encode()
    req = urllib.request.Request(MGMT + "/services/search/jobs/export", data=data, headers={"Authorization": "Basic " + base64.b64encode(("%s:%s" % (user, password or PW)).encode()).decode()})
    rows = []
    with urllib.request.urlopen(req, timeout=300, context=CTX) as r:
        for line in r.read().decode().splitlines():
            if line.strip():
                d = json.loads(line)
                if d.get("result"):
                    rows.append(d["result"])
    return rows


def count(spl, earliest="-24h"):
    rows = search(spl + " | stats count", earliest)
    return int(rows[0]["count"]) if rows else 0


def follow(rid, timeout=120):
    end = time.time() + timeout
    while time.time() < end:
        _, s = gw("GET", "/api/runs/" + rid)
        if s.get("state") in ("COMPLETED", "FAILED", "STOPPED", "INTERRUPTED", "PARTIAL"):
            return s
        time.sleep(1)
    return s


def verify(rid, wait=90):
    last = None
    for _ in range(wait // 5):
        _, last = gw("POST", "/api/runs/%s/verify" % rid, {})
        if last.get("status") == "VERIFIED":
            break
        time.sleep(5)
    return last


def start(body):
    return gw("POST", "/api/runs", dict({"index": IDX, "confirm_destination": True}, **body))


def save(section, data):
    EV.mkdir(parents=True, exist_ok=True)
    (EV / (section + ".json")).write_text(json.dumps(data, indent=1, default=str))
    bad = [r for r in data["results"] if not r.get("ok")]
    print("%s: %d/%d ok%s" % (section, len(data["results"]) - len(bad), len(data["results"]), "" if not bad else "  FAILED: " + ", ".join(r["name"] for r in bad)))
    return not bad


def events():
    out = []
    for st, vendor in EVENT_CASES:
        before = count('index=%s sourcetype="%s"' % (IDX, st))
        code, s = start({"kind": "sourcetype", "target": st, "vendor_id": vendor, "mode": "finite", "count": 25, "eps": 50})
        r = {"name": st, "http": code}
        if code == 200:
            fin = follow(s["run_id"])
            v = verify(s["run_id"])
            time.sleep(3)
            after = count('index=%s sourcetype="%s"' % (IDX, st))
            c = fin["counters"]
            r.update(run_id=s["run_id"], state=fin["state"], counters=c, engine_verification=v.get("status"), independent_search_delta=after - before,
                     ok=fin["state"] == "COMPLETED" and v.get("status") == "VERIFIED" and c["accepted"] == 25 and after - before == 25)
        else:
            r.update(detail=s, ok=False)
        out.append(r)
    return save("events", {"results": out})


def metrics():
    st, vendor = METRIC_CASE
    before = int((search("| mstats count(_value) as n WHERE index=%s metric_name=*" % MIDX) or [{"n": 0}])[0]["n"])
    code, s = start({"kind": "sourcetype", "target": st, "vendor_id": vendor, "mode": "finite", "count": 20, "eps": 50, "metric_index": MIDX})
    r = {"name": st, "http": code}
    if code == 200:
        fin = follow(s["run_id"])
        v = verify(s["run_id"])
        time.sleep(5)
        after = int((search("| mstats count(_value) as n WHERE index=%s metric_name=*" % MIDX) or [{"n": 0}])[0]["n"])
        names = search("| mstats count(_value) as n WHERE index=%s metric_name=* BY metric_name | head 5" % MIDX)
        as_events = count('index=%s sourcetype="%s"' % (MIDX, st))
        r.update(run_id=s["run_id"], state=fin["state"], counters=fin["counters"], engine_verification=v.get("status"), mstats_datapoints_before=before, mstats_datapoints_after=after, sample_metric_names=[n["metric_name"] for n in names],
                 ok=fin["state"] == "COMPLETED" and after > before)
    else:
        r.update(detail=s, ok=False)
    return save("metrics", {"results": [r]})


def scenario():
    target = "paloalto_threat_investigation"
    code, s = start({"kind": "scenario", "target": target})
    r = {"name": "run", "http": code}
    results = [r]
    if code != 200:
        r.update(detail=s, ok=False)
        return save("scenario", {"results": results})
    fin = follow(s["run_id"], 300)
    v = verify(s["run_id"])
    time.sleep(4)
    rid = s["run_id"]
    by_st = search('index=%s netspout_run_id="%s" | stats count by sourcetype' % (IDX, rid))
    r.update(run_id=rid, state=fin["state"], counters=fin["counters"], engine_verification=v.get("status"), independent_by_sourcetype=by_st,
             ok=fin["state"] == "COMPLETED" and v.get("status") == "VERIFIED" and {x["sourcetype"] for x in by_st} >= {"pan:traffic", "pan:threat", "pan:system"})
    _, view = http("GET", "/servicesNS/nobody/netspout/data/ui/views/pf_paloalto_threat_investigation?output_mode=json")
    xml = view["entry"][0]["content"]["eai:data"]
    definition = json.loads(re.search(r"<definition><!\[CDATA\[(.*?)\]\]>", xml, re.S).group(1))
    panels = {}
    for name, ds in definition["dataSources"].items():
        if not name.startswith("ds_") or name in ("ds_runs", "ds_phase_list"):
            continue
        q = ds["options"]["query"].replace("$index_tok$", IDX).replace("$run_tok$", rid).replace("$phase_tok$", "*").replace("$global_time.earliest$", "-24h").replace("$global_time.latest$", "now")
        try:
            panels[name] = len(search(q))
        except urllib.error.HTTPError as e:
            panels[name] = "HTTP %s" % e.code
    nonempty = sum(1 for n in panels.values() if isinstance(n, int) and n > 0)
    results.append({"name": "dashboard_panels_return_rows_for_this_run", "view": "pf_paloalto_threat_investigation", "rows_per_panel": panels, "ok": nonempty >= len(panels) - 3 and nonempty > 0,
                    "note": "panels that legitimately return no rows for a phase are tolerated up to 3"})
    return save("scenario", {"results": results})


def stream():
    out = []
    st, vendor = "pan:traffic", "palo_alto"
    code, s = start({"kind": "sourcetype", "target": st, "vendor_id": vendor, "mode": "continuous", "eps": 8})
    r = {"name": "continuous_start_stop", "http": code}
    out.append(r)
    if code == 200:
        rid = s["run_id"]
        r["limits_at_start"] = s.get("limits") or gw("GET", "/api/runs/" + rid)[1].get("limits")
        series = []
        for _ in range(4):
            time.sleep(2.5)
            series.append(gw("GET", "/api/runs/" + rid)[1]["counters"]["attempts"])
        gw("POST", "/api/runs/%s/stop" % rid, {})
        fin = follow(rid, 60)
        n1 = fin["counters"]["attempts"]
        time.sleep(4)
        n2 = gw("GET", "/api/runs/" + rid)[1]["counters"]["attempts"]
        active = [x for x in gw("GET", "/api/runs")[1]["runs"] if x.get("state") in ("RUNNING", "PAUSED", "STOPPING")]
        v = verify(rid)
        r.update(run_id=rid, attempts_over_time=series, final_state=fin["state"], no_growth_after_stop=n1 == n2, active_runs_after=len(active), engine_verification=v.get("status"),
                 independent_indexed=count('index=%s netspout_run_id="%s"' % (IDX, rid)),
                 ok=all(b > a for a, b in zip(series, series[1:])) and fin["state"] == "STOPPED" and n1 == n2 and not active and v.get("status") == "VERIFIED")
    else:
        r.update(detail=s, ok=False)
    code, s = start({"kind": "sourcetype", "target": st, "vendor_id": vendor, "mode": "duration", "duration_s": 6, "eps": 10})
    r2 = {"name": "duration_bounded", "http": code}
    out.append(r2)
    if code == 200:
        t0 = time.time()
        fin = follow(s["run_id"], 60)
        r2.update(run_id=s["run_id"], final_state=fin["state"], wall_s=round(time.time() - t0, 1), limits=fin.get("limits"), ok=fin["state"] == "COMPLETED" and fin["counters"]["attempts"] > 0 and time.time() - t0 < 30)
    else:
        r2.update(detail=s, ok=False)
    code, s = start({"kind": "sourcetype", "target": st, "vendor_id": vendor, "mode": "continuous"})   # open-ended request: the install cap applies
    r3 = {"name": "open_ended_gets_the_install_duration_cap", "http": code}
    out.append(r3)
    if code == 200:
        lim = gw("GET", "/api/runs/" + s["run_id"])[1].get("limits")
        gw("POST", "/api/runs/%s/stop" % s["run_id"], {})
        follow(s["run_id"], 60)
        r3.update(limits=lim, ok=bool(lim and lim.get("duration_s") and lim["duration_s"] <= 3600))
    else:
        r3.update(detail=s, ok=False)
    for name, body in (("eps_over_cap_refused", {"mode": "continuous", "eps": 5000}), ("duration_over_cap_refused", {"mode": "duration", "duration_s": 7200, "eps": 5})):
        code, s = start(dict({"kind": "sourcetype", "target": st, "vendor_id": vendor}, **body))
        out.append({"name": name, "http": code, "detail": s, "ok": code in (400, 422)})
    code, s = gw("POST", "/api/runs", {"kind": "sourcetype", "target": st, "vendor_id": vendor, "index": IDX, "mode": "finite", "count": 5})
    out.append({"name": "no_confirmation_no_generation", "http": code, "detail": s, "ok": code == 403})
    return save("stream", {"results": out})


def authz():
    out = []
    pw = secrets.token_urlsafe(14) + "Aa1"
    http("POST", "/services/authorization/roles", form={"name": "p17_nocap", "imported_roles": "", "output_mode": "json"})
    for user, role in (("p17_viewer", "user"), ("p17_nocap", "p17_nocap"), ("p17_power", "power")):
        http("DELETE", "/services/authentication/users/" + user)
        http("POST", "/services/authentication/users", form={"name": user, "password": pw, "roles": role, "output_mode": "json"})
    body = {"kind": "sourcetype", "target": "pan:system", "vendor_id": "palo_alto", "index": IDX, "confirm_destination": True, "mode": "finite", "count": 3}

    def status(method, path, user=None, password=None, payload=None):
        return gw(method, path, payload, user=user, password=password)[0]
    out.append({"name": "unauthenticated_get_refused", "http": status("GET", "/api/runs", user=None), "ok": status("GET", "/api/runs", user=None) in (401, 403)})
    out.append({"name": "unauthenticated_post_refused", "http": status("POST", "/api/runs", user=None, payload=body), "ok": status("POST", "/api/runs", user=None, payload=body) in (401, 403)})
    out.append({"name": "no_capability_get_403", "http": status("GET", "/api/runs", "p17_nocap", pw), "ok": status("GET", "/api/runs", "p17_nocap", pw) == 403})
    out.append({"name": "viewer_can_read", "http": status("GET", "/api/runs", "p17_viewer", pw), "ok": status("GET", "/api/runs", "p17_viewer", pw) == 200})
    out.append({"name": "viewer_cannot_run", "http": status("POST", "/api/runs", "p17_viewer", pw, body), "ok": status("POST", "/api/runs", "p17_viewer", pw, body) == 403})
    out.append({"name": "viewer_cannot_save_setup", "http": status("POST", "/api/setup", "p17_viewer", pw, {}), "ok": status("POST", "/api/setup", "p17_viewer", pw, {}) == 403})
    out.append({"name": "admin_can_run", "http": status("POST", "/api/runs", "admin", None, body), "ok": status("POST", "/api/runs", "admin", None, body) == 200})
    code, setup = gw("GET", "/api/setup")
    text = json.dumps(setup)
    out.append({"name": "setup_response_never_contains_secrets", "ok": PW not in text and "hec_token\":" not in text.replace("hec_token_configured", "")})
    code, health = gw("GET", "/api/health", user=None)
    out.append({"name": "engine_has_no_direct_route", "ok": code in (401, 403)})
    # power role: may run (netspout_admin) but cannot write storage/passwords unless it also has edit_storage_passwords
    code, s = gw("POST", "/api/setup", {"deployment_mode": "SPLUNK_ENTERPRISE", "splunk_deployment_type": "enterprise", "hec_url": "https://127.0.0.1:8088/services/collector/event", "search_url": "https://127.0.0.1:8089/services/search/jobs/export",
                                         "auth_method": "HEC_TOKEN_AND_BASIC_SEARCH", "search_username": "x", "hec_token": "should-not-be-saved", "search_secret": "should-not-be-saved", "indexes": [IDX]}, user="p17_power", password=pw)
    out.append({"name": "power_role_cannot_store_credentials_and_nothing_is_saved", "http": code, "detail": s, "ok": code == 403})
    return save("authz", {"results": out})


def idle(minutes=3):
    """Zero synthetic telemetry while the app is installed and nothing was requested: count events INDEXED during the window (_index_earliest/_index_latest) in every
    non-internal index. This is exact; comparing `eventcount` before and after is not (hot-bucket counts update lazily, which showed up as a false +98)."""
    now = lambda: int(float(search("| makeresults | eval t=now() | table t", "-1m")[0]["t"]))
    time.sleep(45)   # grace: events accepted just before this call can still be indexed; the window starts after it
    t0 = now()
    time.sleep(minutes * 60)
    t1 = now()
    indexed = search("index=* _index_earliest=%d _index_latest=%d earliest=0 | stats count by index, sourcetype, source" % (t0, t1), "0")
    nothing_during_window = not indexed
    return save("idle_%dmin_%s" % (minutes, os.environ.get("P17_LABEL", "run")), {"results": [{"name": "no_events_indexed_in_any_index", "window_start": t0, "window_end": t1, "window_min": minutes,
                "events_indexed_in_window_by_index_sourcetype_source": indexed, "ok": nothing_during_window}]})


if __name__ == "__main__":
    ok = True
    for sec in sys.argv[1:] or ["events", "metrics", "scenario", "stream", "authz"]:
        name, _, arg = sec.partition(":")
        ok = (globals()[name](int(arg)) if arg else globals()[name]()) and ok
    sys.exit(0 if ok else 1)
