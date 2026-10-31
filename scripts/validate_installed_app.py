#!/usr/bin/env python3
"""End-to-end check of the INSTALLED PulseForge app in the isolated Docker lab (never the demo lab).

Path under test: Splunk REST (authenticated as a Splunk user) -> installed app gateway handler -> PulseForge engine -> lab HEC; verification by
independent Splunk searches. Credentials come from the git-ignored tests/lab/ta_validation/.env.lab and are never printed or written to evidence.
Prerequisites (documented in docs/guides/INSTALLATION.md): netspout.spl installed in the lab, engine running with NETSPOUT_CONFIG_DIR isolated, gateway pointed at it
through NETSPOUT_BACKEND_URL, Connection Center saved against the lab.  Usage: python scripts/validate_installed_app.py
"""
import base64
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))
import validate_ta_windows as lab  # noqa: E402

BASE = "https://127.0.0.1:%s" % lab.ENV["LAB_MGMT_PORT"]
SECRETS = [lab.ENV["LAB_HEC_TOKEN"], lab.ENV["LAB_SPLUNK_PASSWORD"]]
results, leaks = {}, []


def basic(user, pw):
    return "Basic " + base64.b64encode(("%s:%s" % (user, pw)).encode()).decode()


ADMIN = basic("admin", lab.ENV["LAB_SPLUNK_PASSWORD"])


def call(path, auth=ADMIN, method="GET", body=None):
    req = urllib.request.Request(BASE + path, method=method, data=None if body is None else json.dumps(body).encode(), headers={"Authorization": auth, "Content-Type": "application/json"})
    try:
        raw = urllib.request.urlopen(req, context=lab.CTX, timeout=120).read()
        code = 200
    except urllib.error.HTTPError as e:
        raw, code = e.read(), e.code
    text = raw.decode("utf-8", "replace")
    if any(s in text for s in SECRETS):
        leaks.append(path)
    try:
        return code, json.loads(text)
    except ValueError:
        return code, text


def gw(path, **kw):
    return call("/services/netspout_gateway" + path + ("?output_mode=json" if "?" not in path and False else ""), **kw)


def check(name, ok, **detail):
    results[name] = {"pass": bool(ok), **detail}
    print(("PASS " if ok else "FAIL ") + name)


def spl(q, earliest="-2h"):
    out = lab.mgmt("/services/search/jobs/export", {"search": q if q.lstrip().startswith("|") else "search " + q, "output_mode": "json", "earliest_time": earliest, "preview": "false"})
    return [json.loads(l)["result"] for l in out.splitlines() if '"result"' in l]


def main():
    indexes_before = sorted(e["name"] for e in json.loads(lab.mgmt("/services/data/indexes?output_mode=json&count=0"))["entry"])
    # 1 installation and navigation
    app = json.loads(lab.mgmt("/services/apps/local/netspout?output_mode=json"))["entry"][0]["content"]
    views = json.loads(lab.mgmt("/servicesNS/nobody/netspout/data/ui/views?output_mode=json&count=0&search=name%3Dpf_*"))["entry"]
    nav = json.loads(lab.mgmt("/servicesNS/nobody/netspout/data/ui/nav/default?output_mode=json"))["entry"][0]["content"]["eai:data"]
    check("01_app_installed_and_enabled", app["version"] == "2.0.0" and not app["disabled"] and app["visible"], version=app["version"])
    check("02_dashboard_views_and_navigation_installed", len(views) == len(list((ROOT / "netspout/default/data/ui/views").glob("pf_*.xml"))) and nav.count('name="pf_') == len(views) and "use_case_explorer" in nav, pf_views=len(views))
    # 2 gateway to engine, connection center, no secret leakage
    code, summ = gw("/api/explorer/summary")
    check("03_gateway_reaches_engine_and_explorer_lists_scenarios", code == 200 and summ["operational"]["total"] > 300, operational_total=summ["operational"]["total"] if code == 200 else None)
    code, setup = gw("/api/setup")
    check("04_connection_center_configured_and_secret_free", code == 200 and setup.get("configured") and setup["secret_state"]["hec_token_configured"] and "hec_token\"" not in json.dumps(setup), indexes=setup.get("indexes"))
    # 3 RBAC: a Splunk user without a write role may read but not run anything
    pw = "Ns%s!Rbac" % int(time.time())
    try:
        lab.mgmt("/services/authentication/users", {"name": "pf_readonly_tmp", "password": pw, "roles": "user"})
        ro = basic("pf_readonly_tmp", pw)
        rcode, _ = gw("/api/explorer/summary", auth=ro)
        wcode, wbody = gw("/api/replay/sessions", auth=ro, method="POST", body={"pack_id": "rp_cloud_control_plane_activity", "speed": 100, "loops": 1})
        check("05_rbac_read_only_splunk_user_can_read_but_not_start_runs", rcode == 200 and wcode == 403, read=rcode, write=wcode)
    finally:
        try:
            req = urllib.request.Request(BASE + "/services/authentication/users/pf_readonly_tmp", method="DELETE", headers={"Authorization": ADMIN})
            urllib.request.urlopen(req, context=lab.CTX, timeout=30)
        except Exception:
            pass
    # 4 index allowlist through the installed path
    code, body = gw("/api/replay/sessions", method="POST", body={"pack_id": "rp_cloud_control_plane_activity", "index": "not_authorized_index", "speed": 100, "loops": 1})
    check("06_unauthorized_index_refused_through_the_gateway", code == 403, status=code)
    # 5 replay from the packaged recordings, verified independently
    code, sess = gw("/api/replay/sessions", method="POST", body={"pack_id": "rp_cloud_control_plane_activity", "speed": 100, "loops": 1})
    sid = sess.get("session_id") if code == 200 else None
    state = None
    for _ in range(30):
        time.sleep(2)
        _, st = gw("/api/replay/sessions/%s" % sid)
        state = st.get("state") if isinstance(st, dict) else None
        if state in ("COMPLETED", "FAILED", "STOPPED"):
            break
    counts = st["counts"] if isinstance(st, dict) else {}
    indexed = 0
    for _ in range(15):
        r = spl('index=dev_test_replay netspout_replay_session="%s" | stats count' % sid)
        indexed = int(r[0]["count"]) if r else 0
        if indexed >= counts.get("accepted", 1):
            break
        time.sleep(3)
    _, ver = gw("/api/replay/sessions/%s/verify" % sid, method="POST")
    check("07_replay_session_completes_and_splunk_holds_what_was_accepted", state == "COMPLETED" and counts.get("accepted") == 12 == indexed and not counts.get("rejected"), counts=counts, independent_indexed=indexed)
    check("08_engine_verify_endpoint_agrees_with_independent_search", isinstance(ver, dict) and ver.get("verified") and ver.get("complete") and ver.get("indexed") == indexed, verify=ver if isinstance(ver, dict) else None)
    # 6 native generation (authentic pack) and an incident pack with metrics
    code, nat = gw("/api/generate/scenario-pack", method="POST", body={"scenario_id": "ub5_cisco_change_induced_outage", "dispatch": True, "index": "dev_test_replay"})
    n_ind = 0
    for _ in range(15):
        r = spl('index=dev_test_replay netspout_run_id="%s" | stats count' % nat.get("run_id"))
        n_ind = int(r[0]["count"]) if r else 0
        if n_ind >= nat.get("count_generated", 1):
            break
        time.sleep(3)
    ok = sum(1 for d in nat.get("dispatch_results", []) if (d.get("hec") or {}).get("success"))
    check("09_native_pack_generated_dispatched_and_indexed", code == 200 and ok == nat["count_generated"] == n_ind, generated=nat.get("count_generated"), accepted=ok, indexed=n_ind)
    code, inc = gw("/api/generate/scenario-pack", method="POST", body={"scenario_id": "network_01_campus_link", "dispatch": True, "index": "dev_test_replay"})
    ev = mt = 0
    for _ in range(15):
        a = spl('index=dev_test_replay netspout_run_id="%s" | stats count' % inc.get("run_id"))
        m = spl('| mstats count(_value) as n WHERE index=dev_test_replay_metrics AND metric_name=* AND netspout_run_id="%s"' % inc.get("run_id"))
        ev, mt = (int(a[0]["count"]) if a else 0), (int(m[0]["n"]) if m else 0)
        if ev >= inc.get("event_count", 1) and mt >= inc.get("metric_datapoints_expected", 1):
            break
        time.sleep(3)
    check("10_incident_pack_events_and_mstats_datapoints_indexed", code == 200 and ev == inc["event_count"] and mt == inc["metric_datapoints_expected"], events=ev, datapoints=mt)
    # 7 index hygiene and secrets
    indexes_after = sorted(e["name"] for e in json.loads(lab.mgmt("/services/data/indexes?output_mode=json&count=0"))["entry"])
    check("11_no_index_was_created_by_the_product", indexes_before == indexes_after)
    check("12_no_secret_appeared_in_any_gateway_response", not leaks, leaking_paths=leaks)
    doc = {"generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "lab": "tests/lab/ta_validation (isolated Docker Splunk Enterprise 10.2.7)", "app": "netspout.spl installed from the built package",
           "engine": "PulseForge engine on the host, reached through the installed gateway (NETSPOUT_BACKEND_URL)", "passed": sum(v["pass"] for v in results.values()), "failed": [k for k, v in results.items() if not v["pass"]],
           "runs": {"replay_session": sid, "native_run": nat.get("run_id"), "incident_run": inc.get("run_id")}, "checks": results}
    out = ROOT / "docs/verification/evidence/installed_app/e2e.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1, default=str) + "\n")
    print(json.dumps({"passed": doc["passed"], "failed": doc["failed"]}))
    return 1 if doc["failed"] else 0


if __name__ == "__main__":
    sys.exit(main())
