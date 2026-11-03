#!/usr/bin/env python3
"""
Live validation of Dashboard Studio views against a REAL Splunk (an isolated lab instance you started yourself; never the demo).

Levels, recorded separately and never merged:
  parser   every search of every contract view is sent to Splunk's own SPL parser (GET /services/search/parser); Splunk's error list is the result
  results  for a given run id, every search of a view is executed over the run's indexed events and its row count recorded; a panel is "meaningful" only if it returns rows
Rendering in a browser is a separate step (scripts/render_contract_dashboards.py).

Credentials come from a private env file (SPLUNK_PASSWORD=...), never from arguments or output.

  python scripts/validate_contract_dashboards_live.py parser  ENVFILE [--port 28089]
  python scripts/validate_contract_dashboards_live.py results ENVFILE RUN_MAP.json [--port 28089]    # RUN_MAP: {"scenario id": "run id", ...}
"""
import base64
import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VIEWS = ROOT / "netspout" / "default" / "data" / "ui" / "views"
EVID = ROOT / "docs" / "verification" / "evidence" / "dashboards"
CTX = ssl._create_unverified_context()   # the lab instance uses its own self-signed certificate on loopback


class Splunk:
    def __init__(self, env, port):
        e = dict(l.strip().split("=", 1) for l in open(env) if "=" in l)
        self.base = "https://127.0.0.1:%d" % port
        self.auth = "Basic " + base64.b64encode(("admin:" + e["SPLUNK_PASSWORD"]).encode()).decode()

    def call(self, path, data=None):
        req = urllib.request.Request(self.base + path, data=urllib.parse.urlencode(data).encode() if data is not None else None, headers={"Authorization": self.auth})
        try:
            with urllib.request.urlopen(req, context=CTX, timeout=120) as r:
                return r.status, json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            try:
                return e.code, json.loads(e.read().decode() or "{}")
            except ValueError:
                return e.code, {}


def definition(path):
    return json.loads(re.search(r"<definition><!\[CDATA\[(.*?)\]\]></definition>", path.read_text(), re.S).group(1))


def substitute(q, run_id="validate", index="dev_test_replay"):
    q = q.replace("$index_tok$", index).replace("$mindex_tok$", index + "_metrics").replace("$run_tok$", run_id).replace("$phase_tok$", "*")
    return re.sub(r"\$[A-Za-z_][\w.]*\$", "*", q)   # any other token (a click filter) is exercised as a wildcard


def searches(view):
    d = definition(VIEWS / ("pf_%s.xml" % view))
    return {k: x["options"]["query"] for k, x in d["dataSources"].items() if x.get("type", "").endswith("ds.search")}


def contract_ids():
    sys.path[:0] = [str(ROOT / "src")]
    from netspout_core import scenario_contracts
    return scenario_contracts.ids()


def parser(sp):
    rows = []
    for cid in contract_ids():
        errs = []
        for k, q in searches(cid).items():
            full = q.strip() if q.strip().startswith(("|", "search")) else "search " + q.strip()
            st, body = sp.call("/services/search/parser", {"q": substitute(full), "parse_only": "true", "output_mode": "json"})
            msgs = [m.get("text", "") for m in body.get("messages", []) if m.get("type") in ("FATAL", "ERROR")]
            if st != 200 or msgs or not body.get("commands"):
                errs.append({"datasource": k, "http": st, "messages": msgs[:2]})
        rows.append({"scenario_id": cid, "searches": len(searches(cid)), "parser_errors": errs})
    out = {"validator": "Splunk /services/search/parser", "dashboards": len(rows), "parser_clean": sum(1 for r in rows if not r["parser_errors"]), "failed": [r for r in rows if r["parser_errors"]], "rows": rows,
           "not_checked_here": ["results from indexed data", "browser rendering"]}
    (EVID / "contract_dashboard_parser_validation.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("dashboards", "parser_clean")}), "failed:", [(r["scenario_id"], r["parser_errors"][0]) for r in out["failed"]][:5])


def run_search(sp, q, run_id):
    full = substitute(q, run_id)
    full = full if full.strip().startswith(("|", "search")) else "search " + full
    st, body = sp.call("/services/search/jobs", {"search": full, "exec_mode": "oneshot", "output_mode": "json", "count": "0", "earliest_time": "-24h", "latest_time": "+1h"})
    return st, body.get("results", []), [m.get("text") for m in body.get("messages", []) if m.get("type") in ("FATAL", "ERROR")]


def scenario_contracts_get(cid):
    sys.path[:0] = [str(ROOT / "src")]
    from netspout_core import scenario_contracts
    return scenario_contracts.get(cid)


def _only_metric_phase(c):
    """A phase whose every active stream is a metric stream has no events in the event index (so the event-index phase report cannot cover it)."""
    from netspout_core.telemetry_dispatcher import is_metric_sourcetype
    ph = []
    for p in c["phases"]:
        active = [x for x in c["streams"] if not x.get("phases") or p["id"] in x["phases"]]
        ph.append(bool(active) and all(is_metric_sourcetype(x["sourcetype"]) for x in active))
    return any(ph)


def _rows(sp, query, run_id):
    return run_search(sp, query, run_id)[1]


def results(sp, run_map):
    rows = []
    for cid, run_id in run_map.items():
        per = {}
        for k, q in searches(cid).items():
            st, res, errs = run_search(sp, q, run_id)
            per[k] = {"http": st, "rows": len(res), "errors": errs[:1]}
        meaningful = sum(1 for v in per.values() if v["rows"] > 0 and not v["errors"])
        # the contract-specific panels must tell the phase story: several statuses across phases, and every phase reported
        d = definition(VIEWS / ("pf_%s.xml" % cid))
        q = {v["title"]: d["dataSources"][v["dataSources"]["primary"]]["options"]["query"] for v in d["visualizations"].values() if v.get("title") and "primary" in v.get("dataSources", {})}
        story = {}
        for title, query in q.items():
            if title.startswith("Status by phase"):
                _, res, _ = run_search(sp, query, run_id)
                story["status_by_phase"] = {"phases": len(res), "status_columns": sorted(k for k in (res[0] if res else {}) if k not in ("step",) and not k.startswith("_"))}
            if title.startswith("What each phase reported"):
                _, res, _ = run_search(sp, query, run_id)
                story["phase_report"] = {"rows": len(res), "phases_covered": len({r.get("pf_phase") for r in res})}
        # "meaningful" is a defined test, not "returned a row": every search returns rows; the phase story shows every event phase (and, unless the scenario is steady-state,
        # at least two statuses); metric panels return data from the metric index; a modeled measure is charted with data
        problems = []
        if meaningful != len(per) or any(v["errors"] or v["http"] != 200 for v in per.values()):
            problems.append("some searches returned no rows or failed")
        c = scenario_contracts_get(cid)
        event_phases = len({p for p in story.get("phase_report", {}).get("phases_covered_set", [])}) if False else None
        if "phase_report" in story and story["phase_report"]["phases_covered"] < len(c["phases"]) - (1 if _only_metric_phase(c) else 0):
            problems.append("phase report covers %d of %d phases" % (story["phase_report"]["phases_covered"], len(c["phases"])))
        if "status_by_phase" in story and len(story["status_by_phase"]["status_columns"]) < 2:
            problems.append("status by phase shows fewer than two statuses")
        for title, query in q.items():
            if "mstats" in query and not _rows(sp, query, run_id):
                problems.append("metric panel %r returned no metric data" % title)
            if title.startswith("Measured indicator") and not _rows(sp, query, run_id):
                problems.append("measured indicator panel returned no data")
        rows.append({"scenario_id": cid, "run_id": run_id, "searches": len(per), "searches_with_rows": meaningful, "meaningful": not problems, "meaningful_problems": problems, "searches_empty": [k for k, v in per.items() if v["rows"] == 0 and not v["errors"]],
                     "searches_failed": [k for k, v in per.items() if v["errors"] or v["http"] != 200], "phase_story": story, "detail": per})
    f = EVID / "contract_dashboard_results_validation.json"
    merged = {r["scenario_id"]: r for r in (json.loads(f.read_text())["rows"] if f.exists() else [])}
    merged.update({r["scenario_id"]: r for r in rows})   # a partial rerun updates its own rows and keeps the rest
    out = {"validator": "searches executed in Splunk over the run's indexed events", "dashboards": len(merged), "rows": [merged[k] for k in sorted(merged)]}
    f.write_text(json.dumps(out, indent=1) + "\n")
    for r in rows:
        print("%-28s searches=%2d with_rows=%2d empty=%s failed=%s" % (r["scenario_id"], r["searches"], r["searches_with_rows"], r["searches_empty"][:4], r["searches_failed"][:2]))


if __name__ == "__main__":
    mode, env = sys.argv[1], sys.argv[2]
    port = int(sys.argv[sys.argv.index("--port") + 1]) if "--port" in sys.argv else 28089
    sp = Splunk(env, port)
    parser(sp) if mode == "parser" else results(sp, json.loads(Path(sys.argv[3]).read_text()))
