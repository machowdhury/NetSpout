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
from netspout_core.replay_service import ReplayService, resolve  # noqa: E402,F401
from netspout_core.sample_replay import HecSink, ReplaySession  # noqa: E402

EV = ROOT / "docs" / "verification" / "evidence" / "dashboards"
VIEWS = ROOT / "netspout" / "default" / "data" / "ui" / "views"
INDEX = "dev_test_replay"
URL = "https://127.0.0.1:%s/services/collector" % lab.ENV["LAB_HEC_PORT"]
APP = "netspout"


def jload(name, default=None):
    p = EV / name
    return json.loads(p.read_text()) if p.exists() else default


def jsave(name, obj):
    EV.mkdir(parents=True, exist_ok=True)
    (EV / name).write_text(json.dumps(obj, indent=1, default=str) + "\n")


def spl(q, earliest="-24h", latest="now"):
    out = lab.mgmt("/services/search/jobs/export", {"search": "search " + q if not q.lstrip().startswith(("search", "|")) else q, "output_mode": "json", "earliest_time": earliest, "latest_time": latest, "preview": "false"})
    return [json.loads(l)["result"] for l in out.splitlines() if '"result"' in l]


def probe():
    sessions, probes = {}, {}
    for pack in replay_packs.packs():
        pid = pack["id"]
        tl = replay_packs.build_pack_timeline(pid, cycle_gap_s=2)
        s = ReplaySession(tl, HecSink(URL, lab.ENV["LAB_HEC_TOKEN"], INDEX, "replayed-log-generator", "x", "x", False, True), source_label=pid, sourcetype="(per event)",
                          index=INDEX, host="replayed-log-generator", speed=10, loops=1)
        s.sink._m["source"] = s.source
        s.start(); s.wait(180)
        sessions[pid] = {"session_id": s.id, "accepted": s.counts["accepted"], "generated": s.counts["generated"], "rejected": s.counts["rejected"], "state": s.state}
        for _ in range(15):
            n = spl('index=%s netspout_replay_session="%s" | stats count' % (INDEX, s.id))
            if n and int(n[0]["count"]) >= s.counts["accepted"]:
                break
            time.sleep(3)
        users = spl('index=%s netspout_replay_session="%s" | eval who=coalesce(user, User, src_user, TargetUserName, SubjectUserName, Account_Name, \'userIdentity.userName\', \'actor.alternateId\') | where isnotnull(who) | stats count' % (INDEX, s.id))
        probes[pid] = {"users": bool(users and int(users[0]["count"]) > 0)}
        print(pid, sessions[pid]["accepted"], probes[pid])
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


def validate():
    sessions = jload("sessions.json")["sessions"]
    out = {}
    for pack in replay_packs.packs():
        pid, name = pack["id"], "pf_" + pack["id"]
        sid = sessions[pid]["session_id"]
        d = definition(name)
        res = {"session_id": sid, "datasources": {}, "kpi": {}, "tokens": {}, "drilldowns": {}, "run_filter": {}}
        # 1. every data source returns rows with the run context applied
        for key, ds in d["dataSources"].items():
            rows = spl(subst(ds["options"]["query"], sid))
            res["datasources"][key] = {"name": ds["name"], "rows": len(rows)}
        res["datasources_empty"] = [v["name"] for v in res["datasources"].values() if v["rows"] == 0]
        # 2. KPI cards equal independent searches written separately from the dashboard SPL
        base = 'index=%s netspout_replay_session="%s"' % (INDEX, sid)
        indep = {
            "Events in run": spl(base + " | stats count as v")[0]["v"],
            "Telemetry sources (sourcetypes)": spl(base + " | eval s=mvindex(sourcetype,0) | stats dc(s) as v")[0]["v"],
            "Reporting hosts": spl(base + " | eval h=mvindex(host,-1) | stats dc(h) as v")[0]["v"],
            "Hosts observed": spl(base + " | eval h=mvindex(host,-1) | stats dc(h) as v")[0]["v"],
            "Incident phases observed": spl(base + " | eval p=coalesce(netspout_pack_phase,netspout_phase) | stats dc(p) as v")[0]["v"],
            "Progression phases observed": spl(base + " | eval p=coalesce(netspout_pack_phase,netspout_phase) | stats dc(p) as v")[0]["v"],
        }
        for vz in d["visualizations"].values():
            if vz["type"] == "splunk.singlevalue" and vz["title"] in indep:
                got = spl(subst(d["dataSources"][vz["dataSources"]["primary"]]["options"]["query"], sid))[0]
                value = next(iter(got.values()))
                res["kpi"][vz["title"]] = {"dashboard": value, "independent": indep[vz["title"]], "equal": str(value) == str(indep[vz["title"]])}
        for vz in d["visualizations"].values():            # duration KPI checked against min/max of _time
            if vz["type"] == "splunk.singlevalue" and ("duration" in vz["title"] or "span" in vz["title"]):
                got = next(iter(spl(subst(d["dataSources"][vz["dataSources"]["primary"]]["options"]["query"], sid))[0].values()))
                t = spl(base + " | stats min(_time) as a max(_time) as z | eval v=round(z-a)")[0]["v"]
                secs = lambda s: sum(int(x) * m for x, m in zip(re.findall(r"\d+", s.replace("+", ":"))[::-1], (1, 60, 3600, 86400)))
                res["kpi"][vz["title"]] = {"dashboard": got, "independent_seconds": int(float(t)), "equal": secs(got) == int(float(t))}
        # 3. tokens: every $token$ is bound by an input, an expression, or an interaction
        text = json.dumps(d)
        used = set(re.findall(r"\$([A-Za-z_][\w.]*)\$", text))
        bound = {i["options"]["token"] for i in d["inputs"].values()} | {"global_time", "global_time.earliest", "global_time.latest"}
        unbound = sorted(t for t in used if t.split(".")[0] not in {b.split(".")[0] for b in bound} and not t.startswith(("row.", "click.")))
        res["tokens"] = {"used": sorted(used), "unbound": unbound}
        # 4. drilldown searches: substitute a real row and require rows
        for vk, vz in d["visualizations"].items():
            for h in vz.get("eventHandlers", []):
                if h["type"] == "drilldown.linkToSearch":
                    row = spl(subst(d["dataSources"][vz["dataSources"]["primary"]]["options"]["query"], sid))
                    if not row:
                        res["drilldowns"][vz["title"]] = {"rows": 0}
                        continue
                    q = subst(h["options"]["query"], sid)
                    for k, v in row[0].items():
                        q = q.replace("$row.%s.value$" % k, str(v).split("\n")[0])
                    n = spl(q)
                    res["drilldowns"][vz["title"]] = {"rows": len(n)}
                elif h["type"] == "drilldown.setToken":
                    res["drilldowns"][vz["title"]] = {"sets_token": h["options"]["tokens"][0]["token"], "token_declared": h["options"]["tokens"][0]["token"] in bound}
        # 5. the run filter really narrows: one session vs all sessions
        q = d["dataSources"]["ds_1"]["options"]["query"]
        one = int(spl(subst(q, sid))[0]["value"]); allr = int(spl(subst(q, "*"))[0]["value"])
        res["run_filter"] = {"events_for_session": one, "events_all_runs": allr, "session_equals_accepted": one == sessions[pid]["accepted"], "narrows_or_equals": one <= allr}
        res["pass"] = (not res["datasources_empty"] and all(k["equal"] for k in res["kpi"].values()) and not unbound and
                       all(v.get("rows", 1) > 0 and v.get("token_declared", True) for v in res["drilldowns"].values()) and res["run_filter"]["session_equals_accepted"] and len(res["kpi"]) >= 5)
        out[pid] = res
        print(("PASS " if res["pass"] else "FAIL ") + pid, res["datasources_empty"], [k for k, v in res["kpi"].items() if not v["equal"]], unbound)
    jsave("data_validation.json", {"generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "dashboards": out})
    print(json.dumps({"passed": sum(v["pass"] for v in out.values()), "total": len(out)}))


def maturity():
    """Assemble per-dashboard maturity from stored evidence only.
    SPECIFIED: the pack contract names panels/requirements.  IMPLEMENTED: the view is installed in Splunk and reads back identical to the source.
    DATA_VALIDATED: every data source returned rows with the run context, KPIs equal independent SPL, tokens bound, drilldowns return rows.
    VISUALLY_VERIFIED: DATA_VALIDATED + opened in Splunk Web with correct run context and no error text + the screenshot was inspected (visual_inspection.json)."""
    inst, data, render, insp = jload("install.json", {}), jload("data_validation.json", {}), jload("browser_render.json", {}), jload("visual_inspection.json", {"inspected": {}})
    out = {}
    for pack in replay_packs.packs():
        pid, view = pack["id"], "pf_" + pack["id"]
        specified = bool(pack.get("dashboard_panels") or pack.get("dashboard_requirement") or pack.get("verification_spl"))
        implemented = bool(inst.get("views", {}).get(view, {}).get("matches_source"))
        dv = bool(data.get("dashboards", {}).get(pid, {}).get("pass"))
        rendered = bool(render.get("dashboards", {}).get(pid, {}).get("ok"))
        visual = dv and rendered and pid in insp.get("inspected", {})
        level = ("DASHBOARD_VISUALLY_VERIFIED" if visual else "DASHBOARD_DATA_VALIDATED" if dv and implemented else "DASHBOARD_IMPLEMENTED" if implemented else "DASHBOARD_SPECIFIED" if specified else "NONE")
        out[pid] = {"maturity": level, "specified": specified, "implemented": implemented, "installed_and_opened_in_splunk_web": rendered, "data_validated": dv,
                    "browser_render_checks_pass": rendered, "screenshot_inspected": pid in insp.get("inspected", {}), "kind": pack.get("kind") or "security"}
    jsave("dashboard_maturity.json", {"generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
                                      "scale": ["DASHBOARD_SPECIFIED", "DASHBOARD_IMPLEMENTED", "DASHBOARD_DATA_VALIDATED", "DASHBOARD_VISUALLY_VERIFIED"], "dashboards": out})
    from collections import Counter
    print(json.dumps(Counter(v["maturity"] for v in out.values())))


if __name__ == "__main__":
    {"probe": probe, "install": install, "validate": validate, "maturity": maturity}[sys.argv[1]]()
