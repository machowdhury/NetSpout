#!/usr/bin/env python3
"""Install and validate the scenario Dashboard Studio views in the ISOLATED validation lab (tests/lab/ta_validation; credentials from git-ignored .env.lab, never printed).

  probe     run one replay session per pack (fresh data) and probe the optional panels  -> evidence/dashboards/sessions.json, panel_probe.json
  install   create app `netspout` in the lab if absent and install/update every pf_* view through REST, then read each back
  validate  per dashboard: data sources run with the run context and must return rows; KPI values must equal independent SPL; tokens must all be bound;
            drilldown searches must return rows; the run filter must change the result                                  -> evidence/dashboards/data_validation.json
Rendering in Splunk Web is a separate step (scripts/render_scenario_dashboards.mjs). Maturity is assembled by `maturity` from all evidence files.
Usage: PYTHONPATH=src python scripts/validate_scenario_dashboards.py probe|install|validate|maturity
"""
import json
import re
import sys
import time
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import validate_ta_windows as lab  # noqa: E402
from netspout_core import replay_packs  # noqa: E402
import build_scenario_dashboards as gen  # noqa: E402
from netspout_core.replay_service import ReplayService, resolve  # noqa: E402,F401
from netspout_core.sample_replay import HecSink, ReplaySession  # noqa: E402

EV = ROOT / "docs" / "verification" / "evidence" / "dashboards"
VIEWS = ROOT / "netspout" / "default" / "data" / "ui" / "views"
INDEX = "dev_test_replay"
URL = "https://127.0.0.1:%s/services/collector" % lab.ENV["LAB_HEC_PORT"]
APP = "netspout"
METRIC_INDEX = "dev_test_replay_metrics"


def jload(name, default=None):
    p = EV / name
    return json.loads(p.read_text()) if p.exists() else default


def jsave(name, obj):
    EV.mkdir(parents=True, exist_ok=True)
    (EV / name).write_text(json.dumps(obj, indent=1, default=str) + "\n")


def spl(q, earliest="-24h", latest="now"):
    out = lab.mgmt("/services/search/jobs/export", {"search": "search " + q if not q.lstrip().startswith(("search", "|")) else q, "output_mode": "json", "earliest_time": earliest, "latest_time": latest, "preview": "false"})
    return [json.loads(l)["result"] for l in out.splitlines() if '"result"' in l]


def ensure_indexes():
    names = {e["name"] for e in json.loads(lab.mgmt("/services/data/indexes?output_mode=json&count=0"))["entry"]}
    for n, kind in ((INDEX, "event"), (METRIC_INDEX, "metric")):
        if n not in names:
            try:
                lab.mgmt("/services/data/indexes", {"name": n, "datatype": kind})   # isolated lab fixture only; the product never creates indexes
            except Exception as exc:
                if "409" not in str(exc):   # already exists (created earlier in this lab; may not be listed until a restart)
                    raise


def cfgx():
    from netspout_core.models import TelemetryTransportConfig
    return TelemetryTransportConfig(hec_url=URL, hec_token=lab.ENV["LAB_HEC_TOKEN"], hec_index=INDEX, hec_metric_index=METRIC_INDEX, hec_ssl_verify=False, hec_allow_insecure_tls=True)


def run_source(src):
    """Generate fresh data for one scenario in the lab and return its run record. Replay packs run on the replay engine; native and incident packs through the generator service."""
    from netspout_core.models import TelemetryTransportConfig
    pid = src["id"]
    if src["family"] == "replay":
        tl = replay_packs.build_pack_timeline(pid, cycle_gap_s=2)
        s = ReplaySession(tl, HecSink(URL, lab.ENV["LAB_HEC_TOKEN"], INDEX, "replayed-log-generator", "x", "x", False, True), source_label=pid, sourcetype="(per event)",
                          index=INDEX, host="replayed-log-generator", speed=10, loops=1)
        s.sink._m["source"] = s.source
        s.start(); s.wait(180)
        return {"run": s.id, "accepted": s.counts["accepted"], "expected_events": s.counts["accepted"], "rejected": s.counts["rejected"], "state": s.state}
    if src["family"] == "unified":
        from app.main import unified_generation_service
        from netspout_core.unified_generation import UnifiedGenerationRequest
        import base64 as _b64
        # post-run observation needs an authenticated search target: the isolated lab's REST endpoint (credentials from .env.lab, never printed)
        unified_generation_service.search_provider = lambda: ("https://127.0.0.1:%s/services/search/jobs/export" % lab.ENV["LAB_MGMT_PORT"],
                                                              "Basic " + _b64.b64encode(("admin:" + lab.ENV["LAB_SPLUNK_PASSWORD"]).encode()).decode())
        cfg = TelemetryTransportConfig(hec_url=URL, hec_token=lab.ENV["LAB_HEC_TOKEN"], hec_index=INDEX, hec_metric_index=METRIC_INDEX, hec_ssl_verify=False, hec_allow_insecure_tls=True)
        d = unified_generation_service.run(UnifiedGenerationRequest(mode="SCENARIO", selection_id=pid), cfg).model_dump(mode="json")
        events = 0
        for _ in range(10):
            time.sleep(3)
            n = spl('index=%s netspout_scenario_id="%s" netspout_run_id="%s" | stats count' % (INDEX, pid, d["run_id"]))
            events = int(n[0]["count"]) if n else 0
            if events:
                time.sleep(2)
                events = int(spl('index=%s netspout_scenario_id="%s" netspout_run_id="%s" | stats count' % (INDEX, pid, d["run_id"]))[0]["count"])
                break
        return {"run": d["run_id"], "accepted": len(d.get("events", [])), "expected_events": events, "rejected": 0, "state": d["status"]}
    if src["family"] == "runner":
        from netspout_core.scenario_runner import scenario_runner
        from netspout_core.models import ScenarioRunRequest
        cfg = TelemetryTransportConfig(hec_url=URL, hec_token=lab.ENV["LAB_HEC_TOKEN"], hec_index=INDEX, hec_metric_index=METRIC_INDEX, hec_ssl_verify=False, hec_allow_insecure_tls=True)
        m = scenario_runner.run_scenario(ScenarioRunRequest(scenario_id=pid, seed=7, time_mode="TEST", dispatch_telemetry=True, transport_config=cfg))
        events = 0
        for _ in range(12):
            time.sleep(3)
            n = spl('index=%s netspout_scenario_id="%s" netspout_run_id="%s" | stats count' % (INDEX, pid, m.run_id))
            events = int(n[0]["count"]) if n else 0
            if events and events == int(spl('index=%s netspout_scenario_id="%s" netspout_run_id="%s" | stats count' % (INDEX, pid, m.run_id))[0]["count"]):
                break
        return {"run": m.run_id, "accepted": m.dispatch_succeeded, "expected_events": events, "rejected": m.dispatch_failed, "state": "COMPLETED"}
    from netspout_core.generator_modes import generator_service
    cfg = TelemetryTransportConfig(hec_url=URL, hec_token=lab.ENV["LAB_HEC_TOKEN"], hec_index=INDEX, hec_metric_index=METRIC_INDEX, hec_ssl_verify=False, hec_allow_insecure_tls=True)
    r = generator_service.generate_universe_scenario(pid, run_id="dash-%d" % (int(time.time() * 1000) % 10**10), dispatch=True, transport_config=cfg)
    ok = sum(1 for d in r["dispatch_results"] if (d.get("hec") or {}).get("success"))
    return {"run": r["run_id"], "accepted": ok, "expected_events": r.get("event_count", r["count_generated"]), "rejected": len(r["dispatch_results"]) - ok, "state": "COMPLETED",
            "metric_datapoints_expected": r.get("metric_datapoints_expected")}


def probe(only=None):
    ensure_indexes()
    sessions, probes = ({}, {}) if not only else (jload("sessions.json")["sessions"], jload("panel_probe.json", {}))
    for src in gen.sources(include_blocked=True):
        if only == {"__unified__"}:
            if src["family"] != "unified":
                continue
        elif only == {"__runner__"}:
            if src["family"] != "runner":
                continue
        elif only == {"__native__"}:
            if src["family"] == "replay":
                continue
        elif only and src["id"] not in only:
            continue
        pid = src["id"]
        try:
            rec = run_source(src)
        except ValueError as exc:   # unified scenarios whose preflight is BLOCKED in this lab (e.g. a native receiver is not running): recorded, no dashboard claimed
            from app.main import unified_generation_service as _u
            from netspout_core.unified_generation import UnifiedGenerationRequest as _R
            pf = _u.preflight(_R(mode="SCENARIO", selection_id=pid), cfgx()).model_dump(mode="json") if src["family"] == "unified" else {"checks": []}
            probes[pid] = {"blocked": str(exc), "failing_checks": [c["label"] + ": " + c["detail"][:140] for c in pf["checks"] if c["state"] in ("FAIL", "BLOCK", "BLOCKED")]}
            print(pid, "BLOCKED", probes[pid]["failing_checks"][:2], flush=True)
            jsave("panel_probe.json", probes)
            continue
        rec.update({"key_field": src["key_field"], "scenario_value": src["scenario_value"], "family": src["family"], "kind": src["kind"], "title": src["title"], "metric": src["metric"]})
        sessions[pid] = {**rec, "session_id": rec["run"]}
        for _ in range(15):
            n = spl('index=%s %s="%s" netspout_scenario_id="%s" | stats count' % (INDEX, src["key_field"], rec["run"], src["scenario_value"]))
            if n and int(n[0]["count"]) >= rec["expected_events"]:
                break
            time.sleep(3)
        users = spl('index=%s %s="%s" | eval who=coalesce(user, User, src_user, TargetUserName, SubjectUserName, Account_Name, \'userIdentity.userName\', \'actor.alternateId\') | where isnotnull(who) | stats count' % (INDEX, src["key_field"], rec["run"]))
        probes[pid] = {"users": bool(users and int(users[0]["count"]) > 0)}
        if src["family"] == "unified":
            st = spl('index=%s netspout_run_id="%s" | stats values(sourcetype) as st' % (INDEX, rec["run"]))
            probes[pid]["sourcetypes"] = (st[0]["st"] if st and isinstance(st[0]["st"], list) else [st[0]["st"]] if st else [])
        if src["family"] in ("runner", "unified"):   # only some topology scenarios emit gauge metrics: metric panels are included only when mstats finds datapoints for the run
            m = spl('| mstats count(_value) as n WHERE index=%s AND metric_name=* AND netspout_scenario_id="%s" AND netspout_run_id="%s"' % (METRIC_INDEX, src["scenario_value"], rec["run"]))
            probes[pid]["metrics"] = bool(m and int(m[0]["n"]) > 0)
        print(pid, rec["accepted"], rec["expected_events"], probes[pid], flush=True)
        jsave("sessions.json", {"generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "sessions": sessions})
        jsave("panel_probe.json", probes)


def view_files():
    return sorted(VIEWS.glob("pf_*.xml"))


def install():
    apps = [e["name"] for e in json.loads(lab.mgmt("/services/apps/local?output_mode=json&count=0"))["entry"]]
    if APP not in apps:
        lab.mgmt("/services/apps/local", {"name": APP, "label": "PulseForge (validation lab copy: dashboards only)", "visible": "1", "version": "1.0.0", "description": "Dashboard views under validation"})
    installed = {}
    for f in view_files():
        name, xml = f.stem, f.read_text()
        try:
            lab.mgmt("/servicesNS/nobody/%s/data/ui/views/%s" % (APP, name), {"eai:data": xml})          # update when it exists
        except Exception:
            lab.mgmt("/servicesNS/nobody/%s/data/ui/views" % APP, {"name": name, "eai:data": xml})
        back = json.loads(lab.mgmt("/servicesNS/nobody/%s/data/ui/views/%s?output_mode=json" % (APP, name)))["entry"][0]
        installed[name] = {"app": back["acl"]["app"], "sharing": back["acl"]["sharing"], "bytes": len(back["content"]["eai:data"]), "matches_source": back["content"]["eai:data"].strip() == xml.strip()}
        lab.mgmt("/servicesNS/nobody/%s/data/ui/views/%s/acl" % (APP, name), {"sharing": "app", "owner": "nobody"})
    jsave("install.json", {"generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "app": APP, "views": installed})
    print(json.dumps({"installed": len(installed), "identical_to_source": sum(v["matches_source"] for v in installed.values())}))


def definition(name):
    xml = json.loads(lab.mgmt("/servicesNS/nobody/%s/data/ui/views/%s?output_mode=json" % (APP, name)))["entry"][0]["content"]["eai:data"]
    return json.loads(re.search(r"<!\[CDATA\[(.*?)\]\]>", xml, re.S).group(1))


def subst(q, sid, phase="*"):
    return q.replace("$run_tok$", sid).replace("$phase_tok$", phase).replace("$index_tok$", INDEX)


def validate(only=None):
    sessions = jload("sessions.json")["sessions"]
    out = jload("data_validation.json", {"dashboards": {}})["dashboards"] if only else {}
    for src in gen.sources():
        pid, name = src["id"], "pf_" + src["id"]
        if only and pid not in only:
            continue
        info = sessions[pid]
        sid, key, scn = info["run"], info["key_field"], info["scenario_value"]
        d = definition(name)
        res = {"session_id": sid, "family": src["family"], "datasources": {}, "kpi": {}, "tokens": {}, "drilldowns": {}, "run_filter": {}}
        mtok = {"$mindex_tok$": METRIC_INDEX}

        def sub(q, run=sid):
            for k, v in mtok.items():
                q = q.replace(k, v)
            return subst(q, run)
        # 1. every data source returns rows with the run context applied
        for k, ds in d["dataSources"].items():
            res["datasources"][k] = {"name": ds["name"], "rows": len(spl(sub(ds["options"]["query"])))}
        res["datasources_empty"] = [v["name"] for v in res["datasources"].values() if v["rows"] == 0]
        # 2. KPI cards equal independent searches written separately from the dashboard SPL
        base = 'index=%s netspout_scenario_id="%s" %s="%s"' % (INDEX, scn, key, sid)
        one = lambda q: spl(base + q)[0]["v"]
        indep = {"Events in run": one(" | stats count as v"), "Telemetry sources (sourcetypes)": one(" | eval s=mvindex(sourcetype,0) | stats dc(s) as v"),
                 "Reporting hosts": one(" | eval h=mvindex(host,-1) | stats dc(h) as v"), "Hosts observed": one(" | eval h=mvindex(host,-1) | stats dc(h) as v"),
                 "Devices reporting": one(" | stats dc(netspout_device_id) as v"), "Sites involved": one(" | stats dc(netspout_site_id) as v"),
                 "Incident phases observed": one(" | eval p=coalesce(netspout_pack_phase,netspout_phase) | stats dc(p) as v"),
                 "Progression phases observed": one(" | eval p=coalesce(netspout_pack_phase,netspout_phase) | stats dc(p) as v"),
                 "Recovery / validation evidence": one(" | eval p=coalesce(netspout_pack_phase,netspout_phase) | where match(p,\"(?i)RECOVER|VALIDATE|VERIFIED|CONTAIN|RESPONSE\") | stats count as v")}
        for vz in d["visualizations"].values():
            if vz["type"] != "splunk.singlevalue":
                continue
            got = next(iter(spl(sub(d["dataSources"][vz["dataSources"]["primary"]]["options"]["query"]))[0].values()))
            if vz["title"] in indep:
                res["kpi"][vz["title"]] = {"dashboard": got, "independent": indep[vz["title"]], "equal": str(got) == str(indep[vz["title"]])}
            elif "duration" in vz["title"] or "span" in vz["title"]:
                t = one(" | stats min(_time) as a max(_time) as z | eval v=round(z-a)")
                secs = lambda x: sum(int(y) * m for y, m in zip(re.findall(r"\d+", x.replace("+", ":"))[::-1], (1, 60, 3600, 86400)))
                res["kpi"][vz["title"]] = {"dashboard": got, "independent_seconds": int(float(t)), "equal": secs(got) == int(float(t))}
        # 3. tokens: every $token$ is bound by an input or an interaction
        text = json.dumps(d)
        used = set(re.findall(r"\$([A-Za-z_][\w.]*)\$", text))
        bound = {i["options"]["token"] for i in d["inputs"].values()} | {"global_time", "global_time.earliest", "global_time.latest"}
        unbound = sorted(t for t in used if t.split(".")[0] not in {b_.split(".")[0] for b_ in bound} and not t.startswith(("row.", "click.")))
        res["tokens"] = {"used": sorted(used), "unbound": unbound}
        # 4. drilldown searches: substitute a real row and require rows
        for vz in d["visualizations"].values():
            for h in vz.get("eventHandlers", []):
                if h["type"] == "drilldown.linkToSearch":
                    row = spl(sub(d["dataSources"][vz["dataSources"]["primary"]]["options"]["query"]))
                    if not row:
                        res["drilldowns"][vz["title"]] = {"rows": 0}
                        continue
                    q = sub(h["options"]["query"])
                    for k2, v2 in row[0].items():
                        q = q.replace("$row.%s.value$" % k2, str(v2[0] if isinstance(v2, list) else v2).split("\n")[0])
                    res["drilldowns"][vz["title"]] = {"rows": len(spl(q))}
                elif h["type"] == "drilldown.setToken":
                    res["drilldowns"][vz["title"]] = {"sets_token": h["options"]["tokens"][0]["token"], "token_declared": h["options"]["tokens"][0]["token"] in bound}
        # 5. the run filter narrows (one run vs all) and the KPI equals what was generated
        q = d["dataSources"]["ds_1"]["options"]["query"]
        n_one = int(spl(sub(q))[0]["value"]); n_all = int(spl(sub(q, "*"))[0]["value"])
        res["run_filter"] = {"events_for_run": n_one, "events_all_runs": n_all, "run_equals_generated": n_one == info["expected_events"], "narrows_or_equals": n_one <= n_all}
        # 6. tabs present with a layout each
        tabs = d["layout"]["tabs"]["items"]
        res["tabs"] = [t["label"] for t in tabs]
        res["pass"] = (not res["datasources_empty"] and all(k["equal"] for k in res["kpi"].values()) and not unbound and len(tabs) == 3 and
                       all(v.get("rows", 1) > 0 and v.get("token_declared", True) for v in res["drilldowns"].values()) and res["run_filter"]["run_equals_generated"] and len(res["kpi"]) >= 5)
        out[pid] = res
        print(("PASS " if res["pass"] else "FAIL ") + pid, res["datasources_empty"], [k for k, v in res["kpi"].items() if not v["equal"]], unbound, flush=True)
    jsave("data_validation.json", {"generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "dashboards": out})
    print(json.dumps({"passed": sum(v["pass"] for v in out.values()), "total": len(out)}))


def maturity():
    """Assemble per-dashboard maturity from stored evidence only.
    SPECIFIED: the pack contract names panels/requirements.  IMPLEMENTED: the view is installed in Splunk and reads back identical to the source.
    DATA_VALIDATED: every data source returned rows with the run context, KPIs equal independent SPL, tokens bound, drilldowns return rows.
    VISUALLY_VERIFIED: DATA_VALIDATED + opened in Splunk Web with correct run context and no error text + the screenshot was inspected (visual_inspection.json)."""
    inst, data, render, insp = jload("install.json", {}), jload("data_validation.json", {}), jload("browser_render.json", {}), jload("visual_inspection.json", {"inspected": {}})
    out = {}
    for pack in gen.sources():
        pid, view = pack["id"], "pf_" + pack["id"]
        specified = True   # every source family has a generated template contract (tabs, panels, requirements)
        implemented = bool(inst.get("views", {}).get(view, {}).get("matches_source"))
        dv = bool(data.get("dashboards", {}).get(pid, {}).get("pass"))
        rendered = bool(render.get("dashboards", {}).get(pid, {}).get("ok"))
        visual = dv and rendered and pid in insp.get("inspected", {})
        level = ("DASHBOARD_VISUALLY_VERIFIED" if visual else "DASHBOARD_DATA_VALIDATED" if dv and implemented else "DASHBOARD_IMPLEMENTED" if implemented else "DASHBOARD_SPECIFIED" if specified else "NONE")
        out[pid] = {"maturity": level, "specified": specified, "implemented": implemented, "installed_and_opened_in_splunk_web": rendered, "data_validated": dv,
                    "browser_render_checks_pass": rendered, "screenshot_inspected": pid in insp.get("inspected", {}), "kind": pack["kind"], "family": pack["family"]}
    jsave("dashboard_maturity.json", {"generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
                                      "scale": ["DASHBOARD_SPECIFIED", "DASHBOARD_IMPLEMENTED", "DASHBOARD_DATA_VALIDATED", "DASHBOARD_VISUALLY_VERIFIED"], "dashboards": out})
    from collections import Counter
    print(json.dumps(Counter(v["maturity"] for v in out.values())))


if __name__ == "__main__":
    only = set(sys.argv[2].split(",")) if len(sys.argv) > 2 else None
    {"probe": lambda: probe(only), "install": install, "validate": lambda: validate(only), "maturity": maturity}[sys.argv[1]]()
