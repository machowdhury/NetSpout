#!/usr/bin/env python3
"""Validate the ten NetFlow Dashboard Studio views against real indexed flow data in the isolated lab (never the demo lab or any cloud).
For each view: every data source (and the run selector) is executed with the dashboard's own token defaults and the latest indexed run of that scenario; a data source must
return rows without an error. Each table/chart drilldown is executed with values taken from that panel's first row. Writes evidence (no secrets):
  docs/verification/evidence/netflow/dashboard_validation.json
Usage: PYTHONPATH=src python scripts/validate_netflow_dashboards.py [scenario-id ...]     Credentials: git-ignored tests/lab/ta_validation/.env.lab
"""
import base64
import json
import re
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from netspout_core import netflow_solution as nf  # noqa: E402

ENV = dict(l.split("=", 1) for l in (ROOT / "tests/lab/ta_validation/.env.lab").read_text().split("\n") if "=" in l)
CTX = ssl._create_unverified_context()   # isolated lab, self-signed
OUT = ROOT / "docs/verification/evidence/netflow/dashboard_validation.json"
INDEX = "dev_test_replay"


def spl(q, earliest="-24h", latest="now"):
    q = q if q.lstrip().startswith(("search", "|")) else "search " + q
    data = urllib.parse.urlencode({"search": q, "output_mode": "json", "earliest_time": earliest, "latest_time": latest, "count": 0, "exec_mode": "oneshot"}).encode()
    r = urllib.request.Request("https://127.0.0.1:%s/services/search/jobs" % ENV.get("LAB_MGMT_PORT", "19191"), data=data)
    r.add_header("Authorization", "Basic " + base64.b64encode(("admin:" + ENV["LAB_SPLUNK_PASSWORD"]).encode()).decode())
    try:
        return json.loads(urllib.request.urlopen(r, context=CTX, timeout=300).read()).get("results", []), None
    except urllib.error.HTTPError as e:
        return [], re.sub(r"\s+", " ", e.read().decode()[:300])


def view_spec(sid):
    return json.loads(re.search(r"CDATA\[(.*)\]\]>", (ROOT / "netspout/default/data/ui/views" / ("pf_%s.xml" % sid)).read_text(), re.S).group(1))


def tokens(spec, run_id):
    t = {"run_tok": run_id, "index_tok": INDEX, "st_tok": nf.DEFAULT_SOURCETYPE}
    for inp in spec["inputs"].values():
        o = inp["options"]
        if o["token"] not in t and o["token"] != "global_time":
            t[o["token"]] = o["defaultValue"]
    return t


def sub(q, t, row=None):
    for k, v in t.items():
        q = q.replace("$%s$" % k, str(v))
    if row is not None:
        first = next(iter(row.values()), "")
        q = re.sub(r"\$row\.([A-Za-z0-9_.]+)\.value\$", lambda m: str(row.get(m.group(1), "")), q)
        q = q.replace("$click.value$", str(first))
    q = q.replace("$global_time.earliest$", "-24h").replace("$global_time.latest$", "now")
    return q


def validate(sid):
    spec = view_spec(sid)
    rows, err = spl('index=%s sourcetype="%s" netspout_scenario_id="%s" | stats latest(_time) as t by netspout_run_id | sort - t | head 1' % (INDEX, nf.DEFAULT_SOURCETYPE, sid))
    res = {"scenario_id": sid, "run_id": rows[0]["netspout_run_id"] if rows else None, "panels": {}, "drilldowns": {}, "runs_dropdown_rows": None}
    if not rows:
        res["pass"] = False
        res["error"] = "no indexed run of this scenario in " + INDEX
        return res
    t = tokens(spec, res["run_id"])
    r0, e0 = spl(sub(spec["dataSources"]["ds_runs"]["options"]["query"], t))
    res["runs_dropdown_rows"] = len(r0) if not e0 else e0
    for vk, viz in spec["visualizations"].items():
        ds_key = (viz.get("dataSources") or {}).get("primary")
        if not ds_key:
            continue
        q = spec["dataSources"][ds_key]["options"]["query"]
        left = re.findall(r"\$[A-Za-z_]+\$", sub(q, t))
        data, err = spl(sub(q, t))
        title = viz.get("title") or vk
        res["panels"][title] = {"type": viz["type"], "rows": len(data), "error": err, "unresolved_tokens": left, "sample": data[0] if data else None}
        for h in viz.get("eventHandlers") or []:
            if h["type"] == "drilldown.linkToSearch" and data:
                dq = sub(h["options"]["query"], t, row=data[0])
                dd, derr = spl(dq)
                res["drilldowns"][title] = {"rows": len(dd), "error": derr, "from_row": {k: v for k, v in list(data[0].items())[:3]}}
    empties = [k for k, v in res["panels"].items() if v["rows"] == 0 or v["error"] or v["unresolved_tokens"]]
    bad_dd = [k for k, v in res["drilldowns"].items() if v["rows"] == 0 or v["error"]]
    # Panels whose emptiness is correct: Peak utilization is empty until a capacity is entered
    allowed = {"Peak utilization (needs capacity)"}
    res["empty_panels"] = [e for e in empties if e not in allowed]
    res["bad_drilldowns"] = bad_dd
    res["pass"] = not res["empty_panels"] and not bad_dd and isinstance(res["runs_dropdown_rows"], int) and res["runs_dropdown_rows"] > 0
    return res


def installed_matches_source(sid):
    """The view installed in the lab app reads back identical to the repository source."""
    r = urllib.request.Request("https://127.0.0.1:%s/servicesNS/nobody/netspout/data/ui/views/pf_%s?output_mode=json" % (ENV.get("LAB_MGMT_PORT", "19191"), sid))
    r.add_header("Authorization", "Basic " + base64.b64encode(("admin:" + ENV["LAB_SPLUNK_PASSWORD"]).encode()).decode())
    try:
        got = json.loads(urllib.request.urlopen(r, context=CTX, timeout=60).read())["entry"][0]["content"]["eai:data"]
    except Exception:
        return False
    src = (ROOT / "netspout/default/data/ui/views" / ("pf_%s.xml" % sid)).read_text()
    return re.sub(r"\s+", "", got) == re.sub(r"\s+", "", src)


def maturity():
    """Same scale as the template dashboards: IMPLEMENTED (installed, reads back identical) < DATA_VALIDATED (every data source returned rows, drilldowns return rows)
    < VISUALLY_VERIFIED (data validated + opened in Splunk Web without errors + the screenshot was inspected, listed in visual_inspection.json)."""
    ev = ROOT / "docs/verification/evidence/netflow"
    val = json.loads((ev / "dashboard_validation.json").read_text())["dashboards"]
    ren = json.loads((ev / "browser_render.json").read_text())["dashboards"] if (ev / "browser_render.json").exists() else {}
    insp = json.loads((ev / "visual_inspection.json").read_text())["inspected"] if (ev / "visual_inspection.json").exists() else {}
    out = {}
    for sid in nf.IDS:
        impl, dv = installed_matches_source(sid), bool(val.get(sid, {}).get("pass"))
        rendered, seen = bool(ren.get(sid, {}).get("ok")), sid in insp
        level = "DASHBOARD_VISUALLY_VERIFIED" if (dv and rendered and seen and impl) else "DASHBOARD_DATA_VALIDATED" if dv and impl else "DASHBOARD_IMPLEMENTED" if impl else "DASHBOARD_SPECIFIED"
        out[sid] = {"maturity": level, "implemented": impl, "data_validated": dv, "browser_render_checks_pass": rendered, "screenshot_inspected": seen, "run_id": val.get(sid, {}).get("run_id")}
    (ev / "dashboard_maturity.json").write_text(json.dumps({"generated_utc": datetime.now(timezone.utc).isoformat(timespec="minutes"),
                                                            "scale": ["DASHBOARD_SPECIFIED", "DASHBOARD_IMPLEMENTED", "DASHBOARD_DATA_VALIDATED", "DASHBOARD_VISUALLY_VERIFIED"], "dashboards": out}, indent=1) + "\n")
    from collections import Counter
    print(json.dumps(Counter(v["maturity"] for v in out.values())))


def main():
    if sys.argv[1:2] == ["maturity"]:
        return maturity()
    ids = sys.argv[1:] or nf.IDS
    prev = json.loads(OUT.read_text())["dashboards"] if OUT.exists() else {}
    for sid in ids:
        r = validate(sid)
        prev[sid] = r
        print(("PASS " if r["pass"] else "FAIL ") + sid, "empty:", r.get("empty_panels"), "bad drilldowns:", r.get("bad_drilldowns"), r.get("error") or "", flush=True)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"generated_utc": datetime.now(timezone.utc).isoformat(timespec="minutes"), "index": INDEX, "dashboards": prev}, indent=1) + "\n")


if __name__ == "__main__":
    main()
