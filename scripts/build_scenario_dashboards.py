#!/usr/bin/env python3
"""Generate Dashboard Studio (v2) views for every runnable scenario family that emits indexed telemetry, from reusable templates.

Sources (one view each, `pf_<scenario id>`):
  replay packs (33)            key field netspout_replay_session
  authentic native packs (26)  key field netspout_run_id, scenario field = pack id
  incident packs (37)          key field netspout_run_id, scenario field = incident slug, plus mstats panels on the metric index
Templates: operational (tabs NOC / Engineer / Evidence) and security (tabs Overview / Investigation / Evidence).

Every number comes from an SPL/mstats data source over the scenario's own indexed events: no hardcoded counts, no placeholder charts. Static text is limited to
contract text (title, objective, provenance, detection prerequisites) and links. Optional panels (users) are included only if the live probe found rows.
Fields used exist on every event of the family; `pf_phase` = coalesce(netspout_pack_phase, netspout_phase). Severity/sites appear ONLY for incident packs, which
carry real `severity` and `netspout_site_id` fields; nothing is asserted where the telemetry has no such field.
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
from netspout_core import replay_packs, incident_packs  # noqa: E402
from netspout_core.authentic_scenario_packs import SCENARIO_PACK_IDS, run_scenario_pack  # noqa: E402

VIEWS = ROOT / "netspout" / "default" / "data" / "ui" / "views"
PROBE = ROOT / "docs" / "verification" / "evidence" / "dashboards" / "panel_probe.json"
# Palette follows the Figma V2 tokens (design/): dark #17191b canvas, terracotta accent #a45132 (lightened for charts on dark), muted status colours.
# IBM Plex Mono cannot be loaded by Dashboard Studio (no custom web fonts): identifiers use markdown code formatting instead. Documented gap.
C = {"bg": "#17191b", "card": "#22262a", "accent": "#d4764f", "brand": "#a45132", "amber": "#c9a24a", "red": "#c9786f", "green": "#6fa387", "blue": "#6f9db5",
     "purple": "#a79fc4", "text": "#ececea", "muted": "#9aa1a6"}
SERIES = [C["accent"], C["blue"], C["amber"], C["green"], C["purple"], C["red"], "#8fb0a8", "#b8b09a"]
BASE = 'index=$index_tok$ netspout_scenario_id="%s" %s="$run_tok$"'
# pf_host/pf_st: replayed JSON often carries its own host/sourcetype keys, which Splunk extracts as extra values; the event's own host is the last host value, the metadata sourcetype the first
PHASE = ('| eval pf_phase=coalesce(netspout_pack_phase, netspout_phase), pf_host=mvindex(host,-1), pf_st=mvindex(sourcetype,0) | search pf_phase="$phase_tok$"')
EVAL = ' | eval pf_host=mvindex(host,-1), pf_st=mvindex(sourcetype,0) | search '
CLASS = ('| eval pf_class=case(match(pf_phase,"(?i)^BASELINE"),"1 Before incident", match(pf_phase,"(?i)RECOVER|VALIDATE|VERIFIED|CONTAIN|RESPONSE"),'
         '"3 Recovery / validation", true(),"2 During incident")')
DRILL = '| head 1000'
SECS = ('| eventstats min(_time) as pf_t0 max(_time) as pf_t1 | eval pf_w=max(1, ceil((pf_t1-pf_t0)/60)), pf_sec=floor((_time-pf_t0)/pf_w)*pf_w')
SEC_PREREQ = ("No vendor add-on, CIM or Enterprise Security content is installed in any lab, so no detection is claimed. Detection work needs the add-ons for the constituent "
              "sourcetypes plus reviewed SPL; the constituent contracts list their own expectations.")


def search_drill(query, newtab=True):
    return {"type": "drilldown.linkToSearch", "options": {"query": query, "earliest": "$global_time.earliest$", "latest": "$global_time.latest$", "type": "custom", "newTab": newtab}}


def analytics_for(sourcetypes):
    """Original Splunk Security Content detections whose published TEST DATA is a dataset this scenario replays (exact path match). Never inferred by name."""
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
    for st in sourcetypes:
        for path in paths.get("XmlWinEventLog" if st.startswith("XmlWinEventLog:") else st, []):
            hits.update(idx.get(path, {}))
    return sorted(hits.values(), key=lambda d: d["name"])


# ------------------------------------------------------------------------------------------------------------------ scenario sources
def _has_metric_stream(sourcetypes):
    """Contracts that emit a metric sourcetype land gauge datapoints in the metric index (dimensions: netspout_scenario_id, netspout_run_id, netspout_phase), so the mstats panels apply."""
    from netspout_core.telemetry_dispatcher import is_metric_sourcetype
    return any(is_metric_sourcetype(st) for st in sourcetypes)


def sources(include_blocked=False):
    """-> list of dicts: id, title, kind, family, key_field, scenario_value, industries, subindustry, objective, phases, required_sourcetypes, detection_prerequisites, provenance, metric."""
    tax = json.load(open(ROOT / "catalog/explorer_taxonomy.json"))
    ind_map = collections.defaultdict(list)
    for m in tax["scenario_industries"]:
        ind_map[m["scenario_id"]] += m["industries"]
    out = []
    reg = {x["id"]: x for x in json.load(open(ROOT / "catalog/replay_sources.json"))["sources"]}

    def pack_sourcetypes(p):
        sts = set(p.get("required_sourcetypes") or [])
        for ph in p["phases"]:
            src = ph["source"]
            if src["kind"] == "replay" and reg[src["source_id"]].get("sourcetype"):
                sts.add(reg[src["source_id"]]["sourcetype"])
            elif src["kind"] == "native":
                sts |= {e.sourcetype for e in run_scenario_pack(src["pack"], "probe")}
        return sorted(sts)

    for p in replay_packs.packs():
        out.append({**p, "required_sourcetypes": pack_sourcetypes(p), "family": "replay", "key_field": "netspout_replay_session", "scenario_value": p["id"], "kind": p.get("kind") or ("security" if p["category"] in ("SOC", "AI_SECURITY") else "operational"),
                    "metric": False, "provenance": p.get("provenance") or "Recorded or native telemetry replayed by the PulseForge replay engine."})
    cat = {s["id"]: s for s in json.load(open(ROOT / "catalog/scenarios.json"))}
    for pid in SCENARIO_PACK_IDS:
        s = cat[pid]
        sts = sorted({e.sourcetype for e in run_scenario_pack(pid, "probe")})
        sec = s.get("category") == "SECURITY"
        out.append({"id": pid, "title": s.get("display_name") or pid, "kind": "security" if sec else "operational", "family": "native_pack",
                    "key_field": "netspout_run_id", "scenario_value": pid, "industries": ind_map.get(pid, []), "subindustry": None, "objective": s.get("description", ""),
                    "phases": [{"id": "PACK", "source": {"kind": "native", "pack": pid}}], "required_sourcetypes": sts, "metric": False,
                    "detection_prerequisites": SEC_PREREQ if sec else "Operational scenario: no detection claimed.",
                    "provenance": "Authentic vendor-format native pack (see its contract); correlated inside the pack.", "category": s.get("category")})
    for row in incident_packs.catalog():
        out.append({"id": row["scenario_id"], "title": row["title"], "kind": "operational", "family": "incident_pack", "key_field": "netspout_run_id", "scenario_value": row["slug"],
                    "industries": ind_map.get(row["scenario_id"], []), "subindustry": row["family"].title() + " incident", "metric": True,
                    "objective": "Finite %s incident: baseline, degradation, failure, intervention and recovery with logs and gauge metrics." % row["family"],
                    "phases": [{"id": "INCIDENT", "source": {"kind": "native", "pack": row["scenario_id"]}}],
                    "required_sourcetypes": ["netspout:network:syslog", "netspout:network:metric"] if row["family"] == "network" else ["netspout:telecom:log", "netspout:telecom:metric"],
                    "detection_prerequisites": "Operational scenario: no detection claimed.",
                    "provenance": "MODELED NetSpout-defined telemetry (not vendor-native formats, not device firmware emulation); seeded and reproducible."})
    try:   # ScenarioRunner topology scenarios (needs the backend dependencies; run this script with the project virtualenv)
        from netspout_core.scenario_runner import SUPPORTED_SCENARIO_IDS
    except Exception:
        SUPPORTED_SCENARIO_IDS = frozenset()
    for sid in sorted(set(SUPPORTED_SCENARIO_IDS) - set(SCENARIO_PACK_IDS)):
        s = cat.get(sid)
        if not s:
            continue
        sec = s.get("category") == "SECURITY"
        probe = json.loads(PROBE.read_text()).get(sid, {}) if PROBE.exists() else {}
        out.append({"id": sid, "title": s.get("display_name") or sid, "kind": "security" if sec else "operational", "family": "runner", "key_field": "netspout_run_id",
                    "scenario_value": sid, "industries": ind_map.get(sid, []), "subindustry": None, "objective": s.get("description", ""),
                    "phases": [{"id": "RUNNER", "source": {"kind": "native", "pack": sid}}], "required_sourcetypes": sorted(s.get("sourcetypes", [])), "metric": (not sec) and bool(probe.get("metrics")),
                    "detection_prerequisites": SEC_PREREQ if sec else "Operational scenario: no detection claimed.",
                    "provenance": "ScenarioRunner topology simulation: vendor-format events and gauge metrics produced by the scenario's own contract; correlated by the runner.", "category": s.get("category")})
    try:   # unified-generation scenarios (service lives in the backend app; run this script with the project virtualenv)
        from app.main import unified_generation_service, _unified_transport_config
        uni = unified_generation_service.capabilities(_unified_transport_config())["scenarios"]
    except Exception:
        uni = []
    for u in uni:
        if not u.get("runnable"):
            continue
        sid = u["scenario_id"]
        sec = u.get("domain") in ("Security & SecOps", "Agentic AI Security", "Software Supply Chain Security", "Cross-Domain Incident") or u.get("category") == "FIREWALL_ACTIVITY"
        probe = json.loads(PROBE.read_text()).get(sid, {}) if PROBE.exists() else {}
        if probe.get("blocked") and not include_blocked:
            continue   # preflight blocked in the validation lab: no dashboard is claimed for a scenario that could not be run and indexed
        out.append({"id": sid, "title": u["title"], "kind": "security" if sec else "operational", "family": "unified", "key_field": "netspout_run_id", "scenario_value": sid,
                    "industries": ind_map.get(sid, []), "subindustry": None, "objective": u.get("description", ""), "phases": [{"id": "UNIFIED", "source": {"kind": "native", "pack": sid}}],
                    "required_sourcetypes": sorted(probe.get("sourcetypes", [])), "metric": (not sec) and bool(probe.get("metrics")),
                    "detection_prerequisites": SEC_PREREQ if sec else "Operational scenario: no detection claimed.",
                    "provenance": "Unified-generation scenario (%s); modeled and documented payloads as declared by its source contracts." % u.get("category", "").replace("_", " ").title().lower(),
                    "category": u.get("category")})
    from netspout_core import scenario_contracts   # declarative contracts: events are indexed with netspout_run_id / netspout_scenario_id / netspout_phase
    for row in scenario_contracts.catalog():
        sid, sec = row["scenario_id"], row["kind"] == "security"
        out.append({"id": sid, "title": row["title"], "kind": "security" if sec else "operational", "family": "contract", "key_field": "netspout_run_id", "scenario_value": sid,
                    "industries": ind_map.get(sid, []), "subindustry": None, "objective": row["description"], "phases": [{"id": p, "source": {"kind": "native", "pack": sid}} for p in row["phases"]],
                    "required_sourcetypes": row["sourcetypes"], "metric": _has_metric_stream(row["sourcetypes"]), "detection_prerequisites": SEC_PREREQ if sec else "Operational scenario: no detection claimed.",
                    "provenance": "Declarative scenario contract (%s): existing vendor formatters called with a shared topology and ordered phases. Events carry fixed vendor text plus the indexed fields action, status and signature that show each phase." % row["generator_family"],
                    "category": row["category"]})
    return out


class Dash:
    TABS = {"operational": [("noc", "NOC"), ("engineer", "Engineer"), ("evidence", "Evidence")], "security": [("overview", "Overview"), ("investigation", "Investigation"), ("evidence", "Evidence")]}

    def __init__(self, src):
        self.src, self.id, self.kind = src, src["id"], src["kind"]
        self.tabs = {k: [] for k, _ in self.TABS[self.kind]}
        self.ds, self.viz, self.n = {}, {}, 0
        self.base = BASE % (src["scenario_value"], src["key_field"])

    def add_ds(self, name, query):
        k = "ds_%d" % (len(self.ds) + 1)
        self.ds[k] = {"type": "ds.search", "name": name, "options": {"query": query}}
        return k

    def add(self, tab, vtype, title, x, y, w, h, query=None, options=None, description=None, handlers=None):
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
        self.viz[key] = v
        self.tabs[tab].append({"item": key, "type": "block", "position": {"x": x, "y": y, "w": w, "h": h}})
        return key

    def banner(self):
        s = self.src
        first = s["industries"][0] if s["industries"] else None
        ind = "Industry not mapped" if first is None else (first if isinstance(first, str) else first["id"]).replace("-", " ").title()
        label = "Operational scenario" if self.kind == "operational" else "Security investigation"
        md_ = ("### **PulseForge** · %s\n**%s · %s**  ·  `%s`\n\n%s\n\n_Live searches over the run; %s_"
               % (label, ind, s.get("subindustry") or "scenario telemetry", s["id"], s["objective"],
                  "telemetry is MODELED by NetSpout, not vendor-native." if s["family"] == "incident_pack" else "authentic recorded/native telemetry; industry framing is editorial."))
        self.n += 1
        key = "viz_%d" % self.n
        self.viz[key] = {"type": "splunk.markdown", "options": {"markdown": md_, "fontColor": C["text"], "backgroundColor": C["bg"], "fontSize": "default"}}
        for tab in self.tabs:
            self.tabs[tab].append({"item": key, "type": "block", "position": {"x": 20, "y": 0, "w": 1420, "h": 112}})

    def kpi(self, tab, i, label, query, color):
        self.add(tab, "splunk.singlevalue", label, 20 + i * 240, 130, 230, 120, query=query,
                 options={"majorColor": color, "majorFontSize": 44, "trendDisplay": "off", "sparklineDisplay": "off", "backgroundColor": C["card"], "numberPrecision": 0})

    def definition(self):
        s = self.src
        key = s["key_field"]
        inputs = {
            "input_global_time": {"type": "input.timerange", "title": "Time range", "options": {"token": "global_time", "defaultValue": "-24h@h,now"}},
            "input_run": {"type": "input.dropdown", "title": "Scenario run" + (" (replay session)" if key == "netspout_replay_session" else ""),
                          "options": {"token": "run_tok", "defaultValue": "*", "items": [{"label": "All runs", "value": "*"}], "createSearchJobOnChange": False, "clearDefaultOnSelection": False},
                          "dataSources": {"primary": "ds_runs"}, "context": {}},
            "input_phase": {"type": "input.dropdown", "title": "Incident phase", "options": {"token": "phase_tok", "defaultValue": "*", "items": [{"label": "All phases", "value": "*"}],
                                                                                           "createSearchJobOnChange": False, "clearDefaultOnSelection": False},
                            "dataSources": {"primary": "ds_phase_list"}, "context": {}},
            "input_index": {"type": "input.text", "title": "Index", "options": {"token": "index_tok", "defaultValue": "dev_test_replay"}},
        }
        if s["metric"]:
            inputs["input_mindex"] = {"type": "input.text", "title": "Metric index", "options": {"token": "mindex_tok", "defaultValue": "dev_test_replay_metrics"}}
        ds = dict(self.ds)
        ds["ds_runs"] = {"type": "ds.search", "name": "Run list", "options": {"query": "index=$index_tok$ netspout_scenario_id=\"%s\" | stats latest(_time) as t count by %s | sort - t | "
                                                                                       "eval label=%s.\" · \".strftime(t,\"%%m-%%d %%H:%%M\").\" · \".count.\" events\" | table label %s" % (s["scenario_value"], key, key, key)}}
        ds["ds_phase_list"] = {"type": "ds.search", "name": "Phase list", "options": {"query": self.base + " | eval pf_phase=coalesce(netspout_pack_phase, netspout_phase) | stats count by pf_phase | sort pf_phase | eval label=pf_phase | table label pf_phase"}}
        defaults = {"dataSources": {"ds.search": {"options": {"queryParameters": {"earliest": "$global_time.earliest$", "latest": "$global_time.latest$"}}}}}
        layouts, items = {}, []
        labels = dict(self.TABS[self.kind], impact="Metric impact")
        for tab in self.tabs:
            label = labels[tab]
            lid = "layout_" + tab
            height = max(it["position"]["y"] + it["position"]["h"] for it in self.tabs[tab]) + 20
            layouts[lid] = {"type": "absolute", "options": {"width": 1460, "height": height, "display": "auto-scale", "backgroundColor": C["bg"]}, "structure": self.tabs[tab]}
            items.append({"label": label, "layoutId": lid})
        return {"title": "PulseForge · " + s["title"], "description": s["objective"], "inputs": inputs, "defaults": defaults, "visualizations": self.viz, "dataSources": ds,
                "layout": {"globalInputs": list(inputs), "layoutDefinitions": layouts, "tabs": {"items": items}}, "expressions": {}, "applicationProperties": {"hideEdit": False, "hideExport": False}}


def charts(d, tab, y):
    b = d.base
    d.add(tab, "splunk.column", "Incident timeline · events by phase", 20, y, 930, 300,
          query=b + PHASE + SECS + " | stats count by pf_sec, pf_phase | xyseries pf_sec pf_phase count | sort pf_sec | fillnull value=0",
          options={"stackMode": "stacked", "seriesColors": SERIES, "legendDisplay": "bottom", "yAxisTitleText": "Events", "xAxisTitleText": "Seconds since the first event of the run", "backgroundColor": C["card"]},
          description="Event volume over the run's own clock, split by incident phase.")
    d.add(tab, "splunk.bar", "Events by phase (click to filter the page)", 970, y, 470, 300, query=b + PHASE + " | stats count by pf_phase | sort - count",
          options={"seriesColors": [C["accent"]], "backgroundColor": C["card"], "xAxisTitleText": "Events", "legendDisplay": "off"},
          handlers=[{"type": "drilldown.setToken", "options": {"tokens": [{"token": "phase_tok", "key": "name"}]}}],
          description="Click a bar to set the Incident phase filter; choose All phases to reset.")


def asset_tables(d, tab, y, security):
    b = d.base
    d.add(tab, "splunk.table", ("Affected hosts and assets" if security else "Affected assets and services") + " (click a row to search its events)", 20, y, 710, 320,
          query=b + PHASE + " | stats count as events, dc(pf_phase) as phases, values(pf_st) as %s, min(_time) as first by pf_host | eval first=strftime(first,\"%%H:%%M:%%S\") | sort - events | head 25 | rename pf_host as host" % ("sources" if security else "services"),
          options={"count": 8, "backgroundColor": C["card"]}, handlers=[search_drill(b + EVAL + 'pf_host="$row.host.value$" | sort 0 _time' + DRILL)])
    d.add(tab, "splunk.table", "Attack progression by phase (click a row to search it)" if security else "Incident sequence: root cause to recovery", 750, y, 690, 320,
          query=b + PHASE + " | stats min(_time) as t0 max(_time) as t1 count as events by pf_phase | sort t0 | eval start=strftime(t0,\"%H:%M:%S\"), seconds=round(t1-t0) | fields start pf_phase events seconds",
          options={"count": 8, "backgroundColor": C["card"]},
          handlers=[search_drill(b + ' | eval pf_phase=coalesce(netspout_pack_phase, netspout_phase) | search pf_phase="$row.pf_phase.value$" | sort 0 _time' + DRILL)])


def event_table(d, tab, title, y, h, after_baseline):
    b = d.base
    q = b + PHASE + (CLASS + ' | search pf_class!="1 Before incident"' if after_baseline else "") + " | sort 0 _time | eval time=strftime(_time,\"%H:%M:%S\"), message=substr(_raw,1,200) | table time pf_phase pf_host pf_st message | rename pf_host as host, pf_st as sourcetype | head 200"
    d.add(tab, "splunk.table", title, 20, y, 1420, h, query=q, options={"count": 8, "backgroundColor": C["card"]},
          handlers=[search_drill(b + EVAL + 'pf_host="$row.host.value$" pf_st="$row.sourcetype.value$" | sort 0 _time' + DRILL)])


def md(d, tab, text, x, y, w, h):
    d.add(tab, "splunk.markdown", None, x, y, w, h, options={"markdown": text, "fontColor": C["text"], "backgroundColor": C["card"]})


def provenance_md(s):
    return ("### Provenance and contract\n**Scenario:** `%s`  \n**Execution:** %s  \n**Telemetry:** %s  \n**Sourcetypes:** %s\n\n%s" %
            (s["id"], s["family"].replace("_", " "), s["provenance"], ", ".join("`%s`" % x for x in s["required_sourcetypes"]) or "see contract",
             "**Correlation:** " + s["correlation_note"] if s.get("correlation_note") else "**Correlation:** only what the source telemetry itself carries; nothing is added by PulseForge."))


def impact_tab(d):
    """Incident packs are small and uniform (30 log events, 3 devices, one site, a few seconds), so device/role/severity charts say nothing here. What the packs do carry is
    gauge metrics per phase and an ordered story of events. This tab answers 'what degraded, by how much against its own baseline, and did it come back':
    a scorecard per metric, all metrics indexed to their baseline on one axis, and the first event of each phase as the narrative."""
    b = d.base
    d.banner()
    mb = 'index=$mindex_tok$ AND metric_name=* AND netspout_scenario_id="%s" AND netspout_run_id="$run_tok$"' % d.src["scenario_value"]
    per = "| mstats avg(_value) as v WHERE " + mb + " BY metric_name, netspout_phase span=1s | eval pf_phase=netspout_phase "
    base = '| eventstats avg(eval(if(match(pf_phase,"(?i)^BASELINE"),v,null()))) as base by metric_name'
    d.add("impact", "splunk.table", "Metric scorecard: baseline, worst point, last value (click a row to search the metric's events)", 20, 130, 1420, 300,
          query=per + base + ' | eval dev=abs(v-base) | eventstats max(dev) as maxdev by metric_name | eval worst_pt=if(dev=maxdev,v,null()) | sort 0 _time'
                ' | stats first(base) as baseline, first(worst_pt) as worst, last(v) as last by metric_name'
                ' | eval change_pct=round(100*(worst-baseline)/baseline,1), back_within_10pct=if(abs(last-baseline)<=0.1*abs(baseline),"yes","no")'
                ' | eval baseline=round(baseline,2), worst=round(worst,2), last=round(last,2)',
          options={"count": 8, "backgroundColor": C["card"]},
          description="Baseline = the metric's average in the BASELINE phase. Worst = the point furthest from baseline. back_within_10pct compares the last value with the baseline; it is a plain arithmetic check, not a recovery verdict.")
    d.add("impact", "splunk.line", "Metric shapes: each metric scaled to its own range in this run (0 = lowest, 100 = highest)", 20, 450, 930, 320,
          query=per + " | eventstats min(v) as lo max(v) as hi by metric_name | eval idx=if(hi>lo, round(100*(v-lo)/(hi-lo),1), null()) | xyseries _time metric_name idx",
          options={"seriesColors": SERIES, "legendDisplay": "bottom", "backgroundColor": C["card"], "yAxisTitleText": "% of the metric's own range"},
          description="Metrics have different units, so each is scaled to its own minimum and maximum in the run. This shows when each one moved and in what order; the scorecard above has the real values.")
    d.add("impact", "splunk.table", "What happened, phase by phase (first event of each phase)", 970, 450, 470, 320,
          query=b + PHASE + " | sort 0 _time | stats first(_time) as t0 first(_raw) as first_event count as events by pf_phase | sort t0 | eval start=strftime(t0,\"%H:%M:%S\"), first_event=substr(first_event,1,180) | fields start pf_phase events first_event",
          options={"count": 6, "backgroundColor": C["card"]},
          handlers=[search_drill(b + ' | eval pf_phase=coalesce(netspout_pack_phase, netspout_phase) | search pf_phase="$row.pf_phase.value$" | sort 0 _time' + DRILL)])


def _status_varies(cid):
    from netspout_core import scenario_contracts
    return len({e.status for e in scenario_contracts.generate(cid, "dashboard-build")}) > 1


def _has_modeled_measure(cid):
    from netspout_core import scenario_contracts
    return any("metric_name" in json.dumps(st) for st in scenario_contracts.get(cid)["streams"] if st["formatter"] == "format_modeled_state_event")


def contract_panels(d, tab, y):
    """Panels for declarative-contract scenarios: the phase story lives in the indexed status / action / signature fields (raw vendor text is fixed), shown in the contract's own phase order."""
    s, b = d.src, d.base
    order = "case(" + ",".join('pf_phase="%s",%d' % (p["id"], i + 1) for i, p in enumerate(s["phases"])) + ",true(),99)"
    if _status_varies(s["id"]):
        d.add(tab, "splunk.column", "Status by phase (how the story progresses)", 20, y, 700, 300,
              query=b + PHASE + " | eval pf_ord=" + order + " | eval step=printf(\"%d %s\", pf_ord, pf_phase) | eval pf_status=coalesce(netspout_status, status) | chart count over step by pf_status",
              options={"stackMode": "stacked", "seriesColors": SERIES, "legendDisplay": "bottom", "backgroundColor": C["card"], "xAxisLabelRotation": -30, "yAxisTitleText": "Events"},
              description="Each phase of the scenario contract with the status values its events carry (for example normal, degraded, blocked, mitigated, restored).")
    else:   # a steady-state scenario: every event is normal by design, so a status chart would show one colour; show the load per phase and source instead
        d.add(tab, "splunk.column", "Events by phase and source (steady-state scenario)", 20, y, 700, 300,
              query=b + PHASE + " | eval pf_ord=" + order + " | eval step=printf(\"%d %s\", pf_ord, pf_phase) | chart count over step by pf_st",
              options={"stackMode": "stacked", "seriesColors": SERIES, "legendDisplay": "bottom", "backgroundColor": C["card"], "xAxisLabelRotation": -30, "yAxisTitleText": "Events"},
              description="This scenario has no fault: every event is normal. The chart shows how much each source reports in each load phase.")
    d.add(tab, "splunk.table", "What each phase reported (action and signature by device)", 740, y, 700, 300,
          query=b + PHASE + " | eval pf_ord=" + order + " | eval pf_action=coalesce(netspout_action, action), pf_signature=coalesce(netspout_signature, signature) | stats count as events by pf_ord, pf_phase, pf_host, pf_action, pf_signature | rename pf_action as action, pf_signature as signature | sort pf_ord, - events | fields - pf_ord | head 40",
          options={"count": 8, "backgroundColor": C["card"]}, handlers=[search_drill(b + ' netspout_phase="$row.pf_phase.value$" | sort 0 _time' + DRILL)],
          description="The signature text each device reported in each phase; click a row to open the events of that phase.")
    if _has_modeled_measure(s["id"]):
        d.add(tab, "splunk.line", "Measured indicator by phase (modeled values)", 20, y + 320, 1420, 300,
              query=b + PHASE + ' | search sourcetype="netspout:scenario:state" | spath input=_raw | where isnotnull(metric_value) | eval pf_ord=' + order + ' | eval step=printf("%d %s", pf_ord, pf_phase) | chart avg(metric_value) as value over step by metric_name',
              options={"seriesColors": SERIES, "legendDisplay": "bottom", "backgroundColor": C["card"], "xAxisLabelRotation": -30, "yAxisTitleText": "Value"},
              description="The indicator this scenario models, averaged in each phase. The values are modeled (netspout:scenario:state), not measurements of any product.")
        return y + 640
    return y + 320


def build_operational(s, probe):
    d = Dash(s)
    b = d.base
    incident = s["family"] == "incident_pack"
    if incident:
        d.tabs["impact"] = []
        impact_tab(d)
    else:
        d.banner()
    K = [("Events in run", b + PHASE + " | stats count as value", C["accent"]), ("Telemetry sources (sourcetypes)", b + PHASE + " | stats dc(pf_st) as value", C["blue"]),
         (("Devices reporting" if incident else "Reporting hosts"), b + PHASE + (" | stats dc(netspout_device_id) as value" if incident else " | stats dc(pf_host) as value"), C["purple"]),
         ("Incident duration", b + PHASE + " | stats min(_time) as a max(_time) as z | eval value=tostring(round(z-a),\"duration\") | table value", C["amber"]),
         (("Sites involved" if incident else "Incident phases observed"), b + PHASE + (" | stats dc(netspout_site_id) as value" if incident else " | stats dc(pf_phase) as value"), C["green"]),
         ("Recovery / validation evidence", b + PHASE + CLASS + " | stats count(eval(pf_class=\"3 Recovery / validation\")) as value", C["green"])]
    for i, (label, q, col) in enumerate(K):
        d.kpi("noc", i, label, q, col)
    charts(d, "noc", 270)
    asset_tables(d, "noc", 590, False)
    d.add("engineer", "splunk.line", "Telemetry volume trend by source", 20, 130, 710, 300, query=b + PHASE + SECS + " | stats count by pf_sec, pf_st | xyseries pf_sec pf_st count | sort pf_sec | fillnull value=0",
          options={"seriesColors": SERIES, "legendDisplay": "bottom", "backgroundColor": C["card"], "yAxisTitleText": "Events", "xAxisTitleText": "Seconds since the first event of the run"},
          description="Event throughput per source over the run: a drop after the incident phase is the health signal available from this telemetry.")
    if s["family"] == "contract" and not _status_varies(s["id"]):   # a steady-state scenario has no incident: do not label its events "During incident"
        d.add("engineer", "splunk.column", "Events by source (steady-state scenario: no incident)", 750, 130, 690, 300, query=b + PHASE + " | chart count over pf_st | rename pf_st as sourcetype",
              options={"seriesColors": SERIES, "legendDisplay": "off", "backgroundColor": C["card"], "xAxisLabelRotation": -30, "yAxisTitleText": "Events"},
              description="Every event in this scenario is normal; the chart shows how much each source reports.")
    else:
        d.add("engineer", "splunk.column", "Before / during / after by source", 750, 130, 690, 300,
              query=b + PHASE + CLASS + " | chart count over pf_st by pf_class | addtotals fieldname=_total | sort - _total | head 8 | fields - _total | rename pf_st as sourcetype",
              options={"stackMode": "stacked", "seriesColors": [C["blue"], C["amber"], C["green"]], "legendDisplay": "bottom", "backgroundColor": C["card"], "xAxisLabelRotation": -30, "yAxisTitleText": "Events"},
              description="Events per source before the incident, during it and during recovery/validation (phase names from the scenario).")
    y = 450
    if s["family"] == "contract":
        y = contract_panels(d, "engineer", y)
    if s["metric"]:
        mb = 'index=$mindex_tok$ AND metric_name=* AND netspout_scenario_id="%s" AND netspout_run_id="$run_tok$"' % s["scenario_value"]
        d.add("engineer", "splunk.line", "Health and performance metrics over the run (mstats)", 20, y, 710, 300,
              query="| mstats avg(_value) as value WHERE " + mb + " BY metric_name span=1s | xyseries _time metric_name value | fillnull value=0",
              options={"seriesColors": SERIES, "legendDisplay": "bottom", "backgroundColor": C["card"], "yAxisTitleText": "Value"}, description="Gauge metrics recorded by the incident: loss, latency, error rate, availability.")
        d.add("engineer", "splunk.column", "Metrics before / during / after (average)", 750, y, 690, 300,
              query="| mstats avg(_value) as v WHERE " + mb + " BY metric_name, netspout_phase | eval pf_phase=netspout_phase " + CLASS + " | stats avg(v) as v by metric_name, pf_class | xyseries metric_name pf_class v",
              options={"seriesColors": [C["blue"], C["amber"], C["green"]], "legendDisplay": "bottom", "backgroundColor": C["card"], "xAxisLabelRotation": -30},
              description="Average of each gauge in the baseline, the incident and recovery phases: the before/after comparison.")
        y += 320
    if incident:
        d.add("engineer", "splunk.table", "Affected sites, devices and roles (click a row to search it)", 20, y, 1420, 300,
              query=b + PHASE + " | stats count as events, min(severity) as most_severe_level, dc(netspout_phase) as phases by netspout_site_id, netspout_device_id, device_role | sort - events | head 25",
              options={"count": 8, "backgroundColor": C["card"]}, handlers=[search_drill(b + ' netspout_device_id="$row.netspout_device_id.value$" | sort 0 _time' + DRILL)],
              description="most_severe_level is the syslog severity carried by the events (0 = emergency, 7 = debug); lower is worse.")
        y += 320
    event_table(d, "engineer", "Impact events (everything after the baseline; click a row for the raw event search)", y, 340, True)
    verify = ('Verification search:\n\n    index=YOUR_INDEX netspout_scenario_id="%s" %s=RUN_ID\n    | stats count by netspout_phase, sourcetype' % (s["scenario_value"], s["key_field"]))
    md(d, "evidence", provenance_md(s), 20, 130, 700, 300)
    md(d, "evidence", "### Detection and verification status\n**Detection:** not applicable to this operational scenario; none is claimed.\n\n%s\n\nMaturity is recorded in the PulseForge evidence store, not on this page." % verify, 740, 130, 700, 300)
    event_table(d, "evidence", "Raw event evidence for the run (click a row for the search)", 450, 420, False)
    return d


def build_security(s, probe):
    d = Dash(s)
    b = d.base
    d.banner()
    K = [("Events in run", b + PHASE + " | stats count as value", C["accent"]), ("Telemetry sources (sourcetypes)", b + PHASE + " | stats dc(pf_st) as value", C["blue"]),
         ("Hosts observed", b + PHASE + " | stats dc(pf_host) as value", C["purple"]),
         ("Attack progression span", b + PHASE + " | stats min(_time) as a max(_time) as z | eval value=tostring(round(z-a),\"duration\") | table value", C["amber"]),
         ("Progression phases observed", b + PHASE + " | stats dc(pf_phase) as value", C["green"]),
         ("Contributing packs", b + PHASE + " | eval pk=coalesce(netspout_source_pack, netspout_scenario_id) | stats dc(pk) as value", C["red"])]
    for i, (label, q, col) in enumerate(K):
        d.kpi("overview", i, label, q, col)
    charts(d, "overview", 270)
    links = analytics_for(s["required_sourcetypes"])
    if links:
        rows = "\n".join("- [%s](https://research.splunk.com/%s/%s/) · %s · upstream validation: %s" % (x["name"], x["category"], x["content_id"], x.get("detection_type", ""), x.get("validation_status", "")) for x in links[:12])
        more = "\n\n_%d detections are linked in total; the first 12 are shown._" % len(links) if len(links) > 12 else ""
        amd = "### Original analytics (Splunk Security Content)\nDetections whose published test data is a dataset replayed by this scenario:\n\n%s%s" % (rows, more)
    else:
        amd = ("### Original analytics (Splunk Security Content)\nNo detection in the pinned Security Content catalog lists a dataset replayed by this scenario as its test data, so no original analytic is linked. "
               "Nothing is inferred from names or techniques.")
    det = ("### Detection status: **NOT VERIFIED**\n%s\n\n**Severity:** not asserted. PulseForge does not assign a severity to replayed telemetry; no detection has fired in this lab." % s["detection_prerequisites"])
    md(d, "overview", det, 20, 590, 700, 300)
    md(d, "overview", amd, 740, 590, 700, 300)
    asset_tables(d, "investigation", 130, True)
    y = 470
    if s["family"] == "contract":
        y = contract_panels(d, "investigation", y)
    if probe.get("users"):
        d.add("investigation", "splunk.table", "Users and accounts seen in the events", 20, y, 700, 300,
              query=b + PHASE + " | eval who=coalesce(user, User, src_user, TargetUserName, SubjectUserName, Account_Name, 'userIdentity.userName', 'actor.alternateId') | stats count as events, dc(pf_host) as hosts by who | where isnotnull(who) | sort - events | head 25",
              options={"count": 8, "backgroundColor": C["card"]})
        d.add("investigation", "splunk.line", "Telemetry volume trend by source", 740, y, 700, 300, query=b + PHASE + SECS + " | stats count by pf_sec, pf_st | xyseries pf_sec pf_st count | sort pf_sec | fillnull value=0",
              options={"seriesColors": SERIES, "legendDisplay": "bottom", "backgroundColor": C["card"], "yAxisTitleText": "Events", "xAxisTitleText": "Seconds since the first event of the run"})
        y += 320
    event_table(d, "investigation", "Investigation evidence: security-relevant events (click a row for the raw search)", y, 340, False)
    md(d, "evidence", provenance_md(s), 20, 130, 700, 300)
    md(d, "evidence", amd, 740, 130, 700, 300)
    event_table(d, "evidence", "Raw event evidence for the run (click a row for the search)", 450, 420, False)
    return d


def render(d):
    spec = d.definition()
    xml = ('<dashboard version="2" theme="dark">\n  <label>%s</label>\n  <description>%s</description>\n  <definition><![CDATA[\n%s\n]]></definition>\n</dashboard>\n'
           % (escape("PulseForge · " + d.src["title"]), escape(d.src["objective"]), json.dumps(spec, indent=2, ensure_ascii=False)))
    assert "]]>" not in json.dumps(spec)
    return xml, spec


def view_name(pid):
    return "pf_" + pid


def write_nav(built):
    """Explicit nav entries (no pattern matching): two collections, operational and security, labelled with the scenario titles."""
    import re
    nav = ROOT / "netspout" / "default" / "data" / "ui" / "nav" / "default.xml"
    text = nav.read_text(encoding="utf-8")
    def coll(label, rows):
        body = "\n".join('      <view name="%s" label="%s"/>' % (pid, escape(title, {'"': "&quot;"})) for pid, title in sorted(rows, key=lambda r: r[1].lower()))
        return '    <collection label="%s">\n%s\n    </collection>' % (label, body)
    ops = [("pf_" + b[0], b[3]) for b in built if b[1] == "operational"]
    sec = [("pf_" + b[0], b[3]) for b in built if b[1] == "security"]
    block = ('  <collection label="Scenario Dashboards">\n' + coll("Operational", ops) + "\n" + coll("Security", sec) + "\n  </collection>")
    text = re.sub(r'  <collection label="Scenario Dashboards">.*?</collection>\s*</collection>|  <collection label="Scenario Dashboards">.*?</collection>', lambda m: block, text, count=1, flags=re.S)
    nav.write_text(text, encoding="utf-8")


def main():
    probe_all = json.loads(PROBE.read_text()) if PROBE.exists() else {}
    built = []
    for s in sources():
        probe = probe_all.get(s["id"], {})
        d = (build_operational if s["kind"] == "operational" else build_security)(s, probe)
        xml, spec = render(d)
        (VIEWS / (view_name(s["id"]) + ".xml")).write_text(xml, encoding="utf-8")
        built.append((s["id"], s["kind"], s["family"], s["title"]))
    write_nav(built)
    c = collections.Counter((b[2], b[1]) for b in built)
    print(json.dumps({"dashboards": len(built), "by_family_kind": {"%s/%s" % k: v for k, v in c.items()}}))


if __name__ == "__main__":
    main()
