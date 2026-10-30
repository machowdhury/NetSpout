#!/usr/bin/env python3
"""Generate Dashboard Studio (v2) views for the replay-pack scenarios from two reusable templates (operational, security).

Every number on a dashboard comes from an SPL data source over the scenario's own indexed events: no hardcoded counts, no placeholder charts.
Static text is limited to contract text (title, objective, provenance, detection prerequisites) and links. Data sources use only fields that exist on
every event of these packs (`netspout_scenario_id`, `netspout_replay_session`, `netspout_phase`, `netspout_pack_phase`, `netspout_source_pack`, `host`,
`sourcetype`, `_raw`); `pf_phase` = coalesce(netspout_pack_phase, netspout_phase). Windows add-on rewriting of source/sourcetype is not relied on.
Optional panels (users, endpoints) are included only if the live probe (`validate_scenario_dashboards.py probe`) found rows for that pack.
Run: PYTHONPATH=src python scripts/build_scenario_dashboards.py   (reads docs/verification/evidence/dashboards/panel_probe.json when present)
"""
import collections
import glob
import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from netspout_core import replay_packs  # noqa: E402

VIEWS = ROOT / "netspout" / "default" / "data" / "ui" / "views"
PROBE = ROOT / "docs" / "verification" / "evidence" / "dashboards" / "panel_probe.json"
C = {"bg": "#0e1822", "card": "#16232f", "accent": "#19b5c4", "teal": "#087f8c", "amber": "#f2a93b", "red": "#f0615a", "green": "#3fb97f", "blue": "#5aa0e8",
     "purple": "#9b7ddc", "text": "#e8eef3", "muted": "#9fb0bd"}
SERIES = [C["accent"], C["amber"], C["blue"], C["purple"], C["green"], C["red"], "#c7d36f", "#e58fb6"]
BASE = 'index=$index_tok$ netspout_scenario_id="%s" netspout_replay_session="$run_tok$"'
# pf_host/pf_st: replayed JSON often carries its own host/sourcetype keys, which Splunk extracts as extra values; the event's own host is the last host value, the metadata sourcetype the first
PHASE = '| eval pf_phase=coalesce(netspout_pack_phase, netspout_phase), pf_host=mvindex(host,-1), pf_st=mvindex(sourcetype,0) | search pf_phase="$phase_tok$"'
CLASS = ('| eval pf_class=case(match(pf_phase,"(?i)^BASELINE"),"1 Before incident", match(pf_phase,"(?i)RECOVER|VALIDATE|CONTAIN|RESPONSE"),'
         '"3 Recovery / validation", true(),"2 During incident")')
DRILL = '| head 1000'
# seconds since the first event of the (filtered) run, in at most 60 buckets: the x axis spans the run, not the whole time range
SECS = ('| eventstats min(_time) as pf_t0 max(_time) as pf_t1 | eval pf_w=max(1, ceil((pf_t1-pf_t0)/60)), pf_sec=floor((_time-pf_t0)/pf_w)*pf_w')


def search_drill(query, newtab=True):
    return {"type": "drilldown.linkToSearch", "options": {"query": query, "earliest": "$global_time.earliest$", "latest": "$global_time.latest$", "type": "custom", "newTab": newtab}}


def analytics_for(pack):
    """Original Splunk Security Content detections whose published TEST DATA is a dataset this pack replays (exact path match). Never inferred by name."""
    paths = collections.defaultdict(set)
    for f in glob.glob(str(ROOT / "catalog/raw_reference/selected_pinned_datasets*.json")):
        for r in json.load(open(f)):
            paths[r["sourcetype"]].add(r["path"])
    for r in json.load(open(ROOT / "catalog/raw_reference/provenance.json"))["references"]:
        p, st = r.get("upstream_path") or r.get("upstream_dataset_path"), r.get("sourcetype")
        if p and st:
            paths[st].add(p)
    idx = collections.defaultdict(dict)
    for det in json.load(open(ROOT / "catalog/phase13a_splunk_security_content.json"))["detections"]:
        for a in det.get("attack_data") or []:
            u = a.get("url", "")
            if "/datasets/" in u:
                idx["/datasets/" + u.split("/datasets/", 1)[1]][det["content_id"]] = det
    hits = {}
    for st in pack.get("required_sourcetypes", []) or []:
        for path in paths.get("XmlWinEventLog" if st.startswith("XmlWinEventLog:") else st, []):
            hits.update(idx.get(path, {}))
    return sorted(hits.values(), key=lambda d: d["name"])


class Dash:
    def __init__(self, pack, kind, title):
        self.pack, self.kind, self.title, self.id = pack, kind, title, pack["id"]
        self.ds, self.viz, self.layout, self.n = {}, {}, [], 0
        self.base = BASE % self.id

    def add_ds(self, name, query):
        k = "ds_%d" % (len(self.ds) + 1)
        self.ds[k] = {"type": "ds.search", "name": name, "options": {"query": query}}
        return k

    def add(self, vtype, title, x, y, w, h, query=None, options=None, description=None, handlers=None, viz_extra=None, markdown=None):
        self.n += 1
        key = "viz_%d" % self.n
        v = {"type": vtype, "options": options or {}}
        if title:
            v["title"] = title
        if description:
            v["description"] = description
        if query:
            v["dataSources"] = {"primary": self.add_ds(title or key, query)}
            v["showProgressBar"] = True
        if handlers:
            v["eventHandlers"] = handlers
        if viz_extra:
            v.update(viz_extra)
        self.viz[key] = v
        self.layout.append({"item": key, "type": "block", "position": {"x": x, "y": y, "w": w, "h": h}})
        return key

    def kpi(self, i, label, query, color, x0=20, y=130, w=230, fmt=None):
        opts = {"majorColor": color, "majorFontSize": 44, "trendDisplay": "off", "sparklineDisplay": "off", "backgroundColor": C["card"], "numberPrecision": 0}
        if fmt:
            opts.update(fmt)
        self.add("splunk.singlevalue", None, x0 + i * 240, y, w, 120, query=query, options=opts)
        self.viz["viz_%d" % self.n]["title"] = label

    def banner(self, kind_label):
        p = self.pack
        ind = p["industries"][0].replace("-", " ").title()
        md = ("### **PulseForge** · %s\n**%s · %s**  ·  `%s`\n\n%s\n\n_Live searches over the replayed run: authentic recorded/native telemetry run on the PulseForge replay engine; industry framing is editorial._"
              % (kind_label, ind, p.get("subindustry") or "Recorded-telemetry replay", p["id"], p["objective"]))
        self.add("splunk.markdown", None, 20, 0, 1420, 112, options={"markdown": md, "fontColor": C["text"], "backgroundColor": C["bg"], "fontSize": "default"})

    def definition(self, probe_ok):
        p = self.pack
        phases = [ph["id"] for ph in p["phases"]]
        inputs = {
            "input_global_time": {"type": "input.timerange", "title": "Time range", "options": {"token": "global_time", "defaultValue": "-24h@h,now"}},
            "input_run": {"type": "input.dropdown", "title": "Scenario run (replay session)", "options": {"token": "run_tok", "defaultValue": "*", "items": [{"label": "All runs", "value": "*"}],
                                                                                               "createSearchJobOnChange": False, "clearDefaultOnSelection": False},
                          "dataSources": {"primary": "ds_runs"}, "context": {}},
            "input_phase": {"type": "input.dropdown", "title": "Incident phase", "options": {"token": "phase_tok", "defaultValue": "*", "items": [{"label": "All phases", "value": "*"}],
                                                                                           "createSearchJobOnChange": False, "clearDefaultOnSelection": False},
                            "dataSources": {"primary": "ds_phase_list"}, "context": {}},
            "input_index": {"type": "input.text", "title": "Index", "options": {"token": "index_tok", "defaultValue": "dev_test_replay"}},
        }
        ds = dict(self.ds)
        ds["ds_runs"] = {"type": "ds.search", "name": "Run list", "options": {"query": "index=$index_tok$ netspout_scenario_id=\"%s\" | stats latest(_time) as t count by netspout_replay_session | sort - t | "
                                                                                       "eval label=netspout_replay_session.\" · \".strftime(t,\"%%m-%%d %%H:%%M\").\" · \".count.\" events\" | table label netspout_replay_session" % self.id}}
        ds["ds_phase_list"] = {"type": "ds.search", "name": "Phase list", "options": {"query": self.base + " | eval pf_phase=coalesce(netspout_pack_phase, netspout_phase) | stats count by pf_phase | sort pf_phase | eval label=pf_phase | table label pf_phase"}}
        defaults = {"dataSources": {"ds.search": {"options": {"queryParameters": {"earliest": "$global_time.earliest$", "latest": "$global_time.latest$"}}}}}
        height = max(it["position"]["y"] + it["position"]["h"] for it in self.layout) + 20
        return {"title": "PulseForge · " + p["title"], "description": p["objective"], "inputs": inputs, "defaults": defaults, "visualizations": self.viz, "dataSources": ds,
                "layout": {"globalInputs": list(inputs), "layoutDefinitions": {"layout_1": {"type": "absolute", "options": {"width": 1460, "height": height, "display": "auto-scale",
                                                                                                                        "backgroundColor": C["bg"]},
                                                                                           "structure": self.layout}},
                           "tabs": {"items": [{"label": "Scenario", "layoutId": "layout_1"}]}},
                "expressions": {}, "applicationProperties": {"hideEdit": False, "hideExport": False}}


def common_charts(d, y):
    b = d.base
    d.add("splunk.column", "Incident timeline · events by phase", 20, y, 930, 300,
          query=b + PHASE + SECS + " | stats count by pf_sec, pf_phase | xyseries pf_sec pf_phase count | sort pf_sec | fillnull value=0",
          options={"stackMode": "stacked", "seriesColors": SERIES, "legendDisplay": "bottom", "yAxisTitleText": "Events", "xAxisTitleText": "Seconds since the first event of the run",
                   "backgroundColor": C["card"]},
          description="Event volume over the run's own clock, split by incident phase.")
    d.add("splunk.bar", "Events by phase (click to filter the page)", 970, y, 470, 300,
          query=b + PHASE + " | stats count by pf_phase | sort - count",
          options={"seriesColors": [C["accent"]], "backgroundColor": C["card"], "xAxisTitleText": "Events", "legendDisplay": "off"},
          handlers=[{"type": "drilldown.setToken", "options": {"tokens": [{"token": "phase_tok", "key": "name"}]}}],
          description="Click a column to set the Incident phase filter; choose All phases to reset.")


def build_operational(pack, probe):
    d = Dash(pack, "operational", pack["title"])
    b = d.base
    d.banner("Operational scenario")
    d.kpi(0, "Events in run", b + PHASE + " | stats count as value", C["accent"])
    d.kpi(1, "Telemetry sources (sourcetypes)", b + PHASE + " | stats dc(pf_st) as value", C["blue"])
    d.kpi(2, "Reporting hosts", b + PHASE + " | stats dc(pf_host) as value", C["purple"])
    d.kpi(3, "Incident duration", b + PHASE + " | stats min(_time) as a max(_time) as z | eval value=tostring(round(z-a),\"duration\") | table value", C["amber"])
    d.kpi(4, "Incident phases observed", b + PHASE + " | stats dc(pf_phase) as value", C["green"])
    d.kpi(5, "Recovery / validation evidence", b + PHASE + CLASS + " | stats count(eval(pf_class=\"3 Recovery / validation\")) as value", C["green"])
    common_charts(d, 270)
    d.add("splunk.line", "Telemetry volume trend by source", 20, 590, 710, 290, query=b + PHASE + SECS + " | stats count by pf_sec, pf_st | xyseries pf_sec pf_st count | sort pf_sec | fillnull value=0",
          options={"seriesColors": SERIES, "legendDisplay": "bottom", "backgroundColor": C["card"], "yAxisTitleText": "Events", "xAxisTitleText": "Seconds since the first event of the run"},
          description="Event throughput per source over the run: a drop in a source after the incident phase is the health signal available from this telemetry.")
    d.add("splunk.column", "Before / during / after by source", 750, 590, 690, 290, query=b + PHASE + CLASS + " | chart count over pf_st by pf_class | addtotals fieldname=_total | sort - _total | head 8 | fields - _total | rename pf_st as sourcetype",
          options={"stackMode": "stacked", "seriesColors": [C["blue"], C["amber"], C["green"]], "legendDisplay": "bottom", "backgroundColor": C["card"], "xAxisLabelRotation": -30, "yAxisTitleText": "Events"},
          description="Events per source before the incident, during it and during recovery/validation (phase names from the constituent packs).")
    d.add("splunk.table", "Affected assets and services (click a row to search its events)", 20, 900, 710, 320,
          query=b + PHASE + " | stats count as events, dc(pf_phase) as phases, values(pf_st) as services, min(_time) as first, max(_time) as last by pf_host | eval first=strftime(first,\"%H:%M:%S\"), last=strftime(last,\"%H:%M:%S\") | sort - events | head 25 | rename pf_host as host",
          options={"count": 8, "backgroundColor": C["card"]},
          handlers=[search_drill(b + ' | eval pf_host=mvindex(host,-1), pf_st=mvindex(sourcetype,0) | search pf_host="$row.host.value$" | sort 0 _time' + DRILL)])
    d.add("splunk.table", "Incident sequence: root cause to recovery", 750, 900, 690, 320,
          query=b + PHASE + " | stats min(_time) as t0 max(_time) as t1 count as events by netspout_source_pack pf_phase | sort t0 | eval start=strftime(t0,\"%H:%M:%S\"), seconds=round(t1-t0) | fields start pf_phase events seconds netspout_source_pack | rename netspout_source_pack as pack",
          options={"count": 8, "backgroundColor": C["card"]},
          handlers=[search_drill(b + ' | eval pf_phase=coalesce(netspout_pack_phase, netspout_phase) | search pf_phase="$row.pf_phase.value$" | sort 0 _time' + DRILL)])
    d.add("splunk.table", "Impact events (everything after the baseline; click a row for the raw event search)", 20, 1240, 1420, 340,
          query=b + PHASE + CLASS + " | search pf_class!=\"1 Before incident\" | sort 0 _time | eval time=strftime(_time,\"%H:%M:%S\"), message=substr(_raw,1,200) | table time pf_phase pf_host pf_st message | rename pf_host as host, pf_st as sourcetype | head 200",
          options={"count": 8, "backgroundColor": C["card"]},
          handlers=[search_drill(b + ' | eval pf_host=mvindex(host,-1), pf_st=mvindex(sourcetype,0) | search pf_host="$row.host.value$" pf_st="$row.sourcetype.value$" | sort 0 _time' + DRILL)])
    return d


def build_security(pack, probe):
    d = Dash(pack, "security", pack["title"])
    b = d.base
    d.banner("Security investigation")
    d.kpi(0, "Events in run", b + PHASE + " | stats count as value", C["accent"])
    d.kpi(1, "Telemetry sources (sourcetypes)", b + PHASE + " | stats dc(pf_st) as value", C["blue"])
    d.kpi(2, "Hosts observed", b + PHASE + " | stats dc(pf_host) as value", C["purple"])
    d.kpi(3, "Attack progression span", b + PHASE + " | stats min(_time) as a max(_time) as z | eval value=tostring(round(z-a),\"duration\") | table value", C["amber"])
    d.kpi(4, "Progression phases observed", b + PHASE + " | stats dc(pf_phase) as value", C["green"])
    d.kpi(5, "Contributing packs", b + PHASE + " | eval pk=coalesce(netspout_source_pack, netspout_phase) | stats dc(pk) as value", C["red"])
    common_charts(d, 270)
    links = analytics_for(pack)
    if links:
        rows = "\n".join("- [%s](https://research.splunk.com/%s/%s/) · %s · upstream validation: %s" % (x["name"], x["category"], x["content_id"], x.get("detection_type", ""), x.get("validation_status", "")) for x in links[:12])
        more = "\n\n_%d detections are linked in total; the first 12 are shown._" % len(links) if len(links) > 12 else ""
        md = ("### Original analytics (Splunk Security Content)\nDetections whose published test data is a dataset replayed by this scenario:\n\n%s%s" % (rows, more))
    else:
        md = ("### Original analytics (Splunk Security Content)\nNo detection in the pinned Security Content catalog lists a dataset replayed by this scenario as its test data, so no original analytic is linked. "
              "Nothing is inferred from names or techniques.")
    det = ("### Detection status: **NOT VERIFIED**\n%s\n\n**Severity:** not asserted. PulseForge does not assign a severity to replayed telemetry; no detection has fired in this lab.\n\n"
           "**Constituent contracts:** %s" % (pack["detection_prerequisites"], "; ".join(ph["source"].get("pack") or ph["source"].get("source_id") for ph in pack["phases"])))
    d.add("splunk.markdown", None, 20, 590, 700, 330, options={"markdown": det, "fontColor": C["text"], "backgroundColor": C["card"]})
    d.add("splunk.markdown", None, 740, 590, 700, 330, options={"markdown": md, "fontColor": C["text"], "backgroundColor": C["card"]})
    y = 940
    d.add("splunk.table", "Affected hosts and assets (click a row to search its events)", 20, y, 700, 320,
          query=b + PHASE + " | stats count as events, dc(pf_phase) as phases, values(pf_st) as sources, min(_time) as first by pf_host | eval first=strftime(first,\"%H:%M:%S\") | sort - events | head 25 | rename pf_host as host",
          options={"count": 8, "backgroundColor": C["card"]}, handlers=[search_drill(b + ' | eval pf_host=mvindex(host,-1), pf_st=mvindex(sourcetype,0) | search pf_host="$row.host.value$" | sort 0 _time' + DRILL)])
    d.add("splunk.table", "Attack progression by phase (click a row to search it)", 740, y, 700, 320,
          query=b + PHASE + " | stats min(_time) as t0 max(_time) as t1 count as events by pf_phase | sort t0 | eval start=strftime(t0,\"%H:%M:%S\"), seconds=round(t1-t0) | fields start pf_phase events seconds",
          options={"count": 8, "backgroundColor": C["card"]},
          handlers=[search_drill(b + ' | eval pf_phase=coalesce(netspout_pack_phase, netspout_phase) | search pf_phase="$row.pf_phase.value$" | sort 0 _time' + DRILL)])
    y += 340
    if probe.get("users"):
        d.add("splunk.table", "Users and accounts seen in the events", 20, y, 700, 300,
              query=b + PHASE + " | eval who=coalesce(user, User, src_user, TargetUserName, SubjectUserName, Account_Name, 'userIdentity.userName', 'actor.alternateId') | stats count as events, dc(pf_host) as hosts by who | where isnotnull(who) | sort - events | head 25",
              options={"count": 8, "backgroundColor": C["card"]})
        wide = False
    else:
        wide = True
    d.add("splunk.table", "Investigation evidence: security-relevant events (click a row for the raw search)", 20 if wide else 740, y, 1420 if wide else 700, 340 if wide else 300,
          query=b + PHASE + " | sort 0 _time | eval time=strftime(_time,\"%H:%M:%S\"), message=substr(_raw,1,200) | table time pf_phase pf_host pf_st message | rename pf_host as host, pf_st as sourcetype | head 200",
          options={"count": 8, "backgroundColor": C["card"]},
          handlers=[search_drill(b + ' | eval pf_host=mvindex(host,-1), pf_st=mvindex(sourcetype,0) | search pf_host="$row.host.value$" pf_st="$row.sourcetype.value$" | sort 0 _time' + DRILL)])
    return d


def render(d, probe):
    spec = d.definition(probe)
    xml = ('<dashboard version="2" theme="dark">\n  <label>%s</label>\n  <description>%s</description>\n  <definition><![CDATA[\n%s\n]]></definition>\n</dashboard>\n'
           % (escape("PulseForge · " + d.pack["title"]), escape(d.pack["objective"]), json.dumps(spec, indent=2, ensure_ascii=False)))
    assert "]]>" not in json.dumps(spec)
    return xml, spec


def view_name(pid):
    return "pf_" + pid


def main():
    probe_all = json.loads(PROBE.read_text()) if PROBE.exists() else {}
    built = []
    for pack in replay_packs.packs():
        kind = pack.get("kind") or ("security" if pack["category"] in ("SOC", "AI_SECURITY") else "operational")
        probe = probe_all.get(pack["id"], {})
        d = (build_operational if kind == "operational" else build_security)(pack, probe)
        xml, spec = render(d, probe)
        (VIEWS / (view_name(pack["id"]) + ".xml")).write_text(xml, encoding="utf-8")
        built.append((pack["id"], kind, len(spec["visualizations"]), len(spec["dataSources"])))
    print(json.dumps({"dashboards": len(built), "operational": sum(b[1] == "operational" for b in built), "security": sum(b[1] == "security" for b in built)}))


if __name__ == "__main__":
    main()
