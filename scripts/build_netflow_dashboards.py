#!/usr/bin/env python3
"""Generate the ten NetFlow/IPFIX Dashboard Studio (v2) views `pf_NF-*`. Each has its own investigation question, SPL and layout composition; they do not share a panel template.

Data: normalized flow events (source netspout:netflow:normalized, one HEC event per flow) written by the NetFlow solution scenarios. Every panel is SPL over those events,
bound to a run with netspout_run_id. Nothing is claimed that a flow record cannot show (no TTL, no latency, no DNS names, no allow/deny). `label_meta` (synthetic truth) is never used
as a detection input; it only appears in the evidence tables so a reader can compare an indicator with the scenario's own truth.
Run: PYTHONPATH=src python scripts/build_netflow_dashboards.py
"""
import json
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from netspout_core import netflow_solution as nf  # noqa: E402

VIEWS = ROOT / "netspout" / "default" / "data" / "ui" / "views"
C = {"bg": "#17191b", "card": "#22262a", "accent": "#d4764f", "brand": "#a45132", "amber": "#c9a24a", "red": "#c9786f", "green": "#6fa387", "blue": "#6f9db5", "purple": "#a79fc4",
     "text": "#ececea", "muted": "#9aa1a6"}
SERIES = [C["accent"], C["blue"], C["amber"], C["green"], C["purple"], C["red"], "#8fb0a8", "#b8b09a"]
BASE = 'index=$index_tok$ sourcetype=$st_tok$ source="netspout:netflow:normalized" netspout_scenario_id="%s" netspout_run_id="$run_tok$"'
# Bytes spread uniformly across each flow's [start,end] into 10 s buckets (flow records are exported at flow end, so end-time bucketing would put an elephant flow's whole volume in one bucket).
SPREAD = ('| eval s=flowStartMilliseconds/1000, e=max(flowEndMilliseconds/1000, flowStartMilliseconds/1000+0.001) | eval bucket=mvrange(floor(s/10)*10, floor(e/10)*10+10, 10) | mvexpand bucket '
          '| eval ov=max(0, min(e, bucket+10)-max(s, bucket)), share=bytes*ov/(e-s), _time=bucket')


def TC(span, agg, by=None, fill=True):
    """Time series over the data's own time span. `timechart` would zero-pad the whole selected range (24 h by default), burying a minutes-long run in empty buckets."""
    core = ("| bin _time span=%ds | " % span) + (("chart %s over _time by %s limit=6" % (agg, by)) if by else ("stats %s by _time" % agg))
    return core + (" | makecontinuous _time span=%ds | fillnull value=0" % span if fill else " | makecontinuous _time span=%ds" % span)


def drill(query):
    return [{"type": "drilldown.linkToSearch", "options": {"query": query, "earliest": "$global_time.earliest$", "latest": "$global_time.latest$", "type": "custom", "newTab": True}}]


class View:
    def __init__(self, code, title, question, limits, mitre=None, extra_inputs=None):
        self.meta = nf.get(code)
        self.sid = code
        self.title, self.question, self.limits, self.mitre = title, question, limits, mitre or []
        self.base = BASE % code
        self.ds, self.viz, self.items, self.n = {}, {}, [], 0
        self.dy = 20   # content starts below the taller banner
        self.extra = extra_inputs or {}

    def B(self, tail=""):
        return self.base + (" " + tail if tail else "")

    def _ds(self, name, q):
        k = "ds_%d" % (len(self.ds) + 1)
        self.ds[k] = {"type": "ds.search", "name": name, "options": {"query": q}}
        return k

    def add(self, vtype, title, x, y, w, h, q=None, options=None, desc=None, handlers=None):
        self.n += 1
        key = "viz_%d" % self.n
        v = {"type": vtype, "options": dict({"backgroundColor": C["card"]}, **(options or {}))}
        if title:
            v["title"] = title
        if desc:
            v["description"] = desc
        if q:
            v["dataSources"] = {"primary": self._ds(title or key, q)}
            v["showProgressBar"] = True
        if handlers:
            v["eventHandlers"] = handlers
        self.viz[key] = v
        self.items.append({"item": key, "type": "block", "position": {"x": x, "y": y + self.dy, "w": w, "h": h}})

    def md(self, text, x, y, w, h, bg=None):
        self.n += 1
        key = "viz_%d" % self.n
        self.viz[key] = {"type": "splunk.markdown", "options": {"markdown": text, "fontColor": C["text"], "backgroundColor": bg or C["bg"], "fontSize": "default"}}
        self.items.append({"item": key, "type": "block", "position": {"x": x, "y": y + (self.dy if y else 0), "w": w, "h": h}})

    def kpi(self, label, q, x, y, w=230, h=110, color=None, unit=None, prec=0):
        o = {"majorColor": color or C["accent"], "majorFontSize": 40, "trendDisplay": "off", "sparklineDisplay": "off", "numberPrecision": prec}
        if unit:
            o["unit"] = unit
        self.add("splunk.singlevalue", label, x, y, w, h, q=q if q.rstrip().endswith("fields v") else q + " | fields v", options=o)

    def banner(self, h=124):
        m = self.meta
        mitre = ("  ·  MITRE ATT&CK " + ", ".join(self.mitre)) if self.mitre else ""
        ext = ("  ·  extends `%s`" % m["extends"]) if m.get("extends") else ""
        self.md("### **PulseForge** · NetFlow/IPFIX · %s\n**%s**  ·  `%s`%s%s\n\n**Question:** %s\n\n**Limits:** %s"
                % (m["code"], self.title, self.sid, mitre, ext, self.question, self.limits), 20, 0, 1420, h)

    def prereq(self, y, text="", w=1420):
        self.md("**Data prerequisites.** Events: index `$index_tok$`, sourcetype `$st_tok$`, source `netspout:netflow:normalized`, scenario `%s`, filtered by run (`netspout_run_id`). "
                "Flows are synthetic (RFC 5737 documentation addresses); `label_meta` is scenario truth, not exporter data. Fields used: %s. **If every panel is empty:** no run of this scenario is indexed in the selected time range and index. Start it from the PulseForge Use Case Explorer "
                "(Run scenario with live delivery monitor) and wait for Dashboard READY. CIM names (`src`, `dest`, `transport`) come from the app's props.conf; no accelerated data model is assumed."
                % (self.sid, text), 20, y, w, 96, bg=C["card"])

    def definition(self):
        run_q = ('index=$index_tok$ netspout_scenario_id="%s" | stats latest(_time) as t count by netspout_run_id | sort - t '
                 '| eval label=netspout_run_id." · ".strftime(t,"%%m-%%d %%H:%%M")." · ".count." flows" | table label netspout_run_id' % self.sid)
        inputs = {
            "input_global_time": {"type": "input.timerange", "title": "Time range", "options": {"token": "global_time", "defaultValue": "-24h@h,now"}},
            "input_run": {"type": "input.dropdown", "title": "Scenario run", "options": {"token": "run_tok", "defaultValue": "*", "items": [{"label": "All runs", "value": "*"}],
                                                                                      "createSearchJobOnChange": False, "clearDefaultOnSelection": False},
                          "dataSources": {"primary": "ds_runs"}, "context": {}},
            "input_index": {"type": "input.text", "title": "Index", "options": {"token": "index_tok", "defaultValue": "dev_test_replay"}},
            "input_st": {"type": "input.text", "title": "Sourcetype", "options": {"token": "st_tok", "defaultValue": nf.DEFAULT_SOURCETYPE}},
        }
        for tok, (label, default) in self.extra.items():
            inputs["input_" + tok] = {"type": "input.text", "title": label, "options": {"token": tok, "defaultValue": default}}
        ds = dict(self.ds)
        ds["ds_runs"] = {"type": "ds.search", "name": "Run list", "options": {"query": run_q}}
        height = max(i["position"]["y"] + i["position"]["h"] for i in self.items) + 20
        layout = {"type": "absolute", "options": {"width": 1460, "height": height, "display": "auto-scale", "backgroundColor": C["bg"]}, "structure": self.items}
        return {"title": "PulseForge · " + self.title, "description": self.question, "inputs": inputs,
                "defaults": {"dataSources": {"ds.search": {"options": {"queryParameters": {"earliest": "$global_time.earliest$", "latest": "$global_time.latest$"}}}}},
                "visualizations": self.viz, "dataSources": ds, "layout": {"globalInputs": list(inputs), "layoutDefinitions": {"layout_1": layout}, "tabs": {"items": [{"label": self.title, "layoutId": "layout_1"}]}},
                "expressions": {}, "applicationProperties": {"hideEdit": False, "hideExport": False}}

    def xml(self):
        spec = self.definition()
        body = json.dumps(spec, indent=2, ensure_ascii=False)
        assert "]]>" not in body
        return ('<dashboard version="2" theme="dark">\n  <label>%s</label>\n  <description>%s</description>\n  <definition><![CDATA[\n%s\n]]></definition>\n</dashboard>\n'
                % (escape("PulseForge · " + self.title), escape(self.question), body)), spec


def opts(**kw):
    return dict({"seriesColors": SERIES, "legendDisplay": "bottom"}, **kw)


FLOW_TABLE = "| eval start=strftime(flowStartMilliseconds/1000,\"%H:%M:%S\") | foreach app tcp_flags_text [eval <<FIELD>>=if(isnull(<<FIELD>>) OR <<FIELD>>=\"null\",\"-\",<<FIELD>>)] | table start exporter_ip src src_port dest dest_port transport app tcp_flags_text dscp packets bytes duration_ms snmp_in snmp_out label_meta.is_malicious"


# ---------------------------------------------------------------------------------------------------------------------------------- NOC-01
def noc01():
    v = View("NF-NOC-01-ELEPHANT", "Bandwidth saturation and elephant flows", "Which few flows carry most of the bytes, who sends them, where do they go, and how long do they last?",
             "Utilization is calculated only when a link capacity is entered below; NetFlow carries no interface speed. Throughput assumes a constant rate within each flow.",
             extra_inputs={"eleph_mb": ("Elephant threshold (MB per flow)", "500"), "cap_mbps": ("Link capacity Mbps (0 = not set)", "0")})
    v.banner()
    b = v.B()
    v.kpi("Flow records", b + " | stats count as v", 20, 114)
    v.kpi("Volume (GB)", b + " | stats sum(bytes) as b | eval v=round(b/1e9,2)", 270, 114, prec=2)
    v.kpi("Elephant flows (≥ threshold)", b + " | where bytes>=$eleph_mb$*1000000 | stats count as v", 520, 114, color=C["red"])
    v.kpi("Top talker share of bytes", b + " | stats sum(bytes) as b by src | eventstats sum(b) as tot | eval v=round(100*b/tot,1) | sort - v | head 1 | fields v", 770, 114, unit="%", prec=1)
    v.kpi("Peak utilization (needs capacity)", b + " " + SPREAD + " | stats sum(share) as bytes_share by bucket | eval mbps=bytes_share*8/1e6/10 | stats max(mbps) as peak "
          "| eval v=if($cap_mbps$>0, round(100*peak/$cap_mbps$,1), null()) | fields v", 1020, 114, w=420, unit="%", prec=1)
    v.add("splunk.area", "Estimated throughput (Mbps, 10 s buckets)", 20, 240, 940, 300,
          q=b + " " + SPREAD + " | stats sum(share) as bytes_share by _time | makecontinuous _time span=10s | fillnull value=0 | eval Throughput_Mbps=round(bytes_share*8/1e6/10,1), Capacity_Mbps=if($cap_mbps$>0,$cap_mbps$,null()) | fields _time Throughput_Mbps Capacity_Mbps",
          options=opts(yAxisTitleText="Mbps"), desc="Flow bytes spread evenly across each flow's start-to-end time. The capacity line appears only if you set a capacity.")
    v.add("splunk.bar", "Top source talkers (GB)", 980, 240, 460, 300, q=b + " | stats sum(bytes) as bytes count as flows by src | sort - bytes | head 10 | eval GB=round(bytes/1e9,3) | fields src GB",
          options=opts(legendDisplay="off"), handlers=drill(v.B('src="$click.value$"') + " | sort - bytes | head 1000"))
    v.add("splunk.table", "Elephant flows (click a row to see its flow records)", 20, 560, 940, 300,
          q=b + " | where bytes>=$eleph_mb$*1000000 | eval dur_s=round(duration_ms/1000,1), MB=round(bytes/1e6,1), avg_Mbps=round(bytes*8/1e6/max(duration_ms/1000,0.001),1), app=coalesce(app,\"unclassified\") "
          "| sort - bytes | eval start=strftime(flowStartMilliseconds/1000,\"%H:%M:%S\") | table start src dest dest_port app dur_s MB avg_Mbps exporter_ip snmp_in snmp_out",
          options={"count": 8}, desc="app is a port-based label, not application identification.",
          handlers=drill(b + ' src="$row.src.value$" dest="$row.dest.value$" | sort - bytes | head 1000'))
    v.add("splunk.bar", "Volume by destination, split by application (GB, port-based app)", 980, 560, 460, 300,
          q=b + " | eval app=coalesce(app,\"unclassified\") | stats sum(bytes) as bytes by dest app | eval GB=round(bytes/1e9,3) | sort - bytes | head 12 | chart sum(GB) over dest by app", options=opts(stackMode="stacked", legendDisplay="bottom"))
    v.add("splunk.scatter", "Duration vs volume per flow (seconds vs MB)", 20, 880, 700, 280, q=b + " | eval duration_s=round(duration_ms/1000,1), MB=round(bytes/1e6,2) | table duration_s MB | head 2000",
          options=opts(legendDisplay="off", xAxisTitleText="flow duration (s)", yAxisTitleText="MB"), desc="Each dot is one flow record. Elephants sit top-right.")
    v.add("splunk.table", "Flow evidence (largest 100)", 740, 880, 700, 280, q=b + " | sort - bytes | head 100 " + FLOW_TABLE, options={"count": 6})
    v.prereq(1180, "src, dest, dest_port, app, bytes, packets, duration_ms, flowStartMilliseconds, flowEndMilliseconds, exporter_ip, snmp_in, snmp_out")
    return v


# ---------------------------------------------------------------------------------------------------------------------------------- NOC-02
def noc02():
    v = View("NF-NOC-02-DSCP", "QoS and DSCP marking validation", "Is voice and video marked with the DSCP the policy expects, and which endpoints are not?",
             "Voice/video class is a UDP port heuristic (RTP 16384-32767, video 5004) and the policy (voice EF=46, video AF41=34) is the lab default, not discovered from the network.",
             extra_inputs={"if_tok": ("Ingress interface (snmp_in, * = all)", "*"), "class_tok": ("Traffic class (voice, video or *)", "*")})
    v.banner()
    cls = ('| eval cls=case(transport="udp" AND dest_port=5004,"video", transport="udp" AND dest_port>=16384 AND dest_port<=32767,"voice") | where isnotnull(cls) '
           '| search cls="$class_tok$" | eval expected=case(cls="voice",46,cls="video",34), result=if(dscp=expected,"compliant","noncompliant")')
    b = v.B("snmp_in=$if_tok$")
    v.add("splunk.markergauge", "Policy compliance (% of voice/video flows)", 20, 114, 330, 250, q=b + " " + cls + " | stats count(eval(result=\"compliant\")) as c count as n | eval v=round(100*c/n,1) | fields v",
          options={"orientation": "horizontal", "gaugeRanges": [{"from": 0, "to": 80, "value": C["red"]}, {"from": 80, "to": 95, "value": C["amber"]}, {"from": 95, "to": 100, "value": C["green"]}], "majorValueDisplay": "number"})
    v.add("splunk.pie", "DSCP distribution (all flows)", 20, 380, 330, 330, q=v.B("snmp_in=$if_tok$") + " | stats count by dscp | eval dscp=\"DSCP \".dscp | sort - count", options=opts(legendDisplay="right"))
    v.add("splunk.column", "Marked as policy vs not marked as policy, over time", 370, 114, 1070, 300,
          q=b + " " + cls + " " + TC(15, "count", "result"), options=opts(stackMode="stacked", seriesColors=[C["green"], C["red"]], yAxisTitleText="flow records"))
    v.add("splunk.bar", "Result by class", 370, 430, 340, 280, q=b + " " + cls + " | stats count(eval(result=\"compliant\")) as compliant count(eval(result=\"noncompliant\")) as noncompliant by cls",
          options=opts(stackMode="stacked", seriesColors=[C["green"], C["red"]]))
    v.add("splunk.table", "Noncompliant endpoints (click a row for their flows)", 730, 430, 710, 280,
          q=b + " " + cls + " | stats count as flows count(eval(result=\"noncompliant\")) as noncompliant values(cls) as class values(dscp) as observed_dscp values(expected) as expected_dscp sum(bytes) as bytes values(snmp_in) as interfaces by src "
          "| where noncompliant>0 | eval pct_noncompliant=round(100*noncompliant/flows,1) | sort - noncompliant | table src class expected_dscp observed_dscp flows noncompliant pct_noncompliant bytes interfaces",
          options={"count": 7}, handlers=drill(b + ' src="$row.src.value$" | sort 0 _time | head 1000'))
    v.add("splunk.table", "Observed DSCP by class and interface (voice/video flows)", 20, 730, 690, 230,
          q=b + " " + cls + " | stats count as flows by cls dscp expected snmp_in | sort cls - flows | table cls expected dscp snmp_in flows", options={"count": 6})
    v.add("splunk.table", "Noncompliant flow evidence", 730, 730, 710, 230, q=b + " " + cls + " | where result=\"noncompliant\" | sort - _time | head 100 " + FLOW_TABLE, options={"count": 5})
    v.prereq(980, "dscp, tos, dest_port, transport, src, snmp_in")
    return v


# ---------------------------------------------------------------------------------------------------------------------------------- NOC-03
def noc03():
    v = View("NF-NOC-03-ROUTING-LOOP", "Routing-loop indicators (flow-only)", "Are the same source/destination pairs being observed repeatedly at several exporters and interfaces, in the pattern a forwarding loop would produce?",
             "INDICATOR ONLY. NetFlow has no TTL, so TTL depletion and loop drops are not shown. Confirmation needs ICMP time-exceeded messages or router counters, which are not in this data.",
             extra_inputs={"minobs": ("Min observations per pair", "10"), "maxpkts": ("Max avg packets per flow", "3")})
    v.banner()
    b = v.B()
    ind = ("| eventstats count as obs dc(exporter_ip) as exporters avg(packets) as avg_pkts by src dest dest_port | eval indicator=if(obs>=$minobs$ AND exporters>=2 AND avg_pkts<=$maxpkts$,1,0)")
    v.md("#### How to read this\nA pair is flagged when it is seen at **two or more exporters**, at least **N times**, with **small flows** (few packets each). That pattern is *consistent with* repeated traversal "
         "of a path, and also with asymmetric paths, load balancing or sampling. Treat the table as a worklist, not a verdict.", 20, 114, 460, 190, bg=C["card"])
    v.kpi("Flagged pairs", b + " " + ind + " | where indicator=1 | stats dc(src) as v by dest | stats sum(v) as v", 500, 114, w=220, h=190, color=C["red"])
    v.kpi("Indicator flows", b + " " + ind + " | stats sum(indicator) as v", 740, 114, w=220, h=190)
    v.kpi("Exporters involved", b + " " + ind + " | where indicator=1 | stats dc(exporter_ip) as v", 980, 114, w=220, h=190)
    v.kpi("Share of all flows", b + " " + ind + " | stats sum(indicator) as i count as n | eval v=round(100*i/n,1)", 1220, 114, w=220, h=190, unit="%", prec=1)
    v.add("splunk.table", "Flagged source/destination pairs (click a row for the supporting flows)", 20, 324, 1420, 250,
          q=b + " " + ind + " | where indicator=1 | stats count as observations dc(exporter_ip) as exporters values(exporter_ip) as exporter_list values(snmp_in) as ingress_if values(snmp_out) as egress_if avg(packets) as avg_pkts min(_time) as first_seen max(_time) as last_seen by src dest dest_port "
          "| eval avg_pkts=round(avg_pkts,1), first_seen=strftime(first_seen,\"%H:%M:%S\"), last_seen=strftime(last_seen,\"%H:%M:%S\") | sort - observations",
          options={"count": 6}, handlers=drill(b + ' src="$row.src.value$" dest="$row.dest.value$" | sort 0 _time | head 1000'))
    v.add("splunk.line", "Anomaly trend: indicator flows vs all flows", 20, 594, 900, 280, q=b + " " + ind + " " + TC(15, "count as all_flows sum(indicator) as indicator_flows") + "",
          options=opts(seriesColors=[C["muted"], C["red"]], yAxisTitleText="flow records"))
    v.add("splunk.bar", "Affected exporter / interface path (indicator flows)", 940, 594, 500, 280,
          q=b + " " + ind + " | where indicator=1 | eval path=exporter_ip.\"  if\".snmp_in.\"→\".snmp_out | stats count by path | sort - count", options=opts(legendDisplay="off"))
    v.add("splunk.table", "Supporting flow evidence (flagged pairs)", 20, 894, 1420, 260, q=b + " " + ind + " | where indicator=1 | sort - _time | head 200 " + FLOW_TABLE, options={"count": 6})
    v.prereq(1174, "src, dest, dest_port, exporter_ip, snmp_in, snmp_out, packets")
    return v


# ---------------------------------------------------------------------------------------------------------------------------------- NOC-04
def noc04():
    v = View("NF-NOC-04-ASYMMETRY", "Asymmetric-routing indicators", "For which endpoint pairs is the reverse direction seen at a different exporter, or not seen at all?",
             "A missing reverse flow is not proof of asymmetric routing: sampling, observation coverage and collection gaps look identical. Pairs are indicators, not findings.")
    v.banner()
    b = v.B()
    pair = ('| eval svc=min(src_port,dest_port) | eval client=if(dest_port=svc,src,dest), server=if(dest_port=svc,dest,src), dir=if(dest_port=svc,"forward","reverse") '
            '| stats sum(eval(if(dir="forward",bytes,0))) as fwd_bytes sum(eval(if(dir="reverse",bytes,0))) as rev_bytes count(eval(dir="forward")) as fwd_flows count(eval(dir="reverse")) as rev_flows '
            'values(eval(if(dir="forward",exporter_ip,null()))) as fwd_exp values(eval(if(dir="reverse",exporter_ip,null()))) as rev_exp by client server svc '
            '| eval fwd_exporters=mvjoin(fwd_exp,","), rev_exporters=mvjoin(rev_exp,",") | eval verdict=case(rev_flows=0,"reverse not observed", fwd_exporters=rev_exporters,"symmetric (same exporter)", true(),"reverse at different exporter")')
    v.add("splunk.pie", "Pair classification", 20, 114, 460, 300, q=b + " " + pair + " | stats count by verdict", options=opts(seriesColors=[C["green"], C["amber"], C["red"]], legendDisplay="right"))
    v.add("splunk.bar", "Forward vs reverse volume, top 12 pairs (MB)", 500, 114, 940, 300,
          q=b + " " + pair + " | sort - fwd_bytes | head 12 | eval pair=client.\" ⇄ \".server, forward_MB=round(fwd_bytes/1e6,2), reverse_MB=round(rev_bytes/1e6,2) | table pair forward_MB reverse_MB",
          options=opts(seriesColors=[C["accent"], C["blue"]], yAxisTitleText=""))
    v.kpi("Pairs analysed", b + " " + pair + " | stats count as v", 20, 434, w=220, h=120)
    v.kpi("Reverse at different exporter", b + " " + pair + " | stats count(eval(verdict=\"reverse at different exporter\")) as d count as n | eval v=round(100*d/n,1)", 260, 434, w=220, h=120, unit="%", prec=1, color=C["amber"])
    v.kpi("Reverse not observed", b + " " + pair + " | stats count(eval(verdict=\"reverse not observed\")) as d count as n | eval v=round(100*d/n,1)", 500, 434, w=220, h=120, unit="%", prec=1, color=C["red"])
    v.add("splunk.table", "Pairs with a non-symmetric result (click a row for the flows)", 740, 434, 700, 300,
          q=b + " " + pair + " | where verdict!=\"symmetric (same exporter)\" | eval fwd_MB=round(fwd_bytes/1e6,2), rev_MB=round(rev_bytes/1e6,2) | sort - fwd_bytes | table client server verdict fwd_exporters rev_exporters fwd_MB rev_MB fwd_flows rev_flows",
          options={"count": 7}, handlers=drill(b + ' (src="$row.client.value$" dest="$row.server.value$") OR (src="$row.server.value$" dest="$row.client.value$") | sort 0 _time | head 1000'))
    v.add("splunk.table", "Observation-point evidence: flows by exporter and direction", 20, 574, 700, 160,
          q=b + " | eval svc=min(src_port,dest_port), dir=if(dest_port=svc,\"forward\",\"reverse\") | chart count over exporter_ip by dir", options={"count": 6})
    v.add("splunk.table", "Flow evidence for non-symmetric pairs", 20, 754, 1420, 250,
          q=b + " | eval svc=min(src_port,dest_port), client=if(dest_port=svc,src,dest), dir=if(dest_port=svc,\"forward\",\"reverse\") | sort 0 client _time | head 300 " + FLOW_TABLE, options={"count": 6})
    v.prereq(1024, "src, dest, src_port, dest_port, exporter_ip, bytes, snmp_in, snmp_out")
    return v


# ---------------------------------------------------------------------------------------------------------------------------------- NOC-05
def noc05():
    v = View("NF-NOC-05-BASELINE-DRIFT", "Application baseline and flow-duration drift", "Did flow duration or volume to a destination drift away from its earlier baseline?",
             "Flow duration is not application latency. It also depends on session length and exporter timeouts. The baseline is simply the first part of the selected window.",
             extra_inputs={"base_pct": ("Baseline = first N % of window", "40"), "ratio_tok": ("Flag when observed/baseline ≥", "1.5"), "dest_tok": ("Destination (* = all)", "*")})
    v.banner()
    b = v.B("dest=$dest_tok$")
    per = "| eventstats min(_time) as t0 max(_time) as t1 | eval period=if(_time < t0+(t1-t0)*$base_pct$/100,\"baseline\",\"observed\")"
    cmp_ = (b + " " + per + " | stats avg(duration_ms) as dur avg(bytes) as byt count as flows by dest period | eval dur=round(dur,0), byt=round(byt,0) "
            "| stats values(eval(if(period=\"baseline\",dur,null()))) as baseline_ms values(eval(if(period=\"observed\",dur,null()))) as observed_ms values(eval(if(period=\"baseline\",byt,null()))) as baseline_bytes "
            "values(eval(if(period=\"observed\",byt,null()))) as observed_bytes sum(flows) as flows by dest | eval duration_ratio=round(observed_ms/baseline_ms,2), bytes_ratio=round(observed_bytes/baseline_bytes,2)")
    v.kpi("Largest duration ratio", cmp_ + " | stats max(duration_ratio) as v", 20, 114, w=300, h=120, prec=2, color=C["red"])
    v.kpi("Destinations flagged", cmp_ + " | where duration_ratio>=$ratio_tok$ | stats count as v", 340, 114, w=300, h=120)
    v.kpi("Flow records", b + " | stats count as v", 660, 114, w=300, h=120)
    v.add("splunk.table", "Baseline vs observed per destination", 980, 114, 460, 300, q=cmp_ + " | sort - duration_ratio | table dest baseline_ms observed_ms duration_ratio baseline_bytes observed_bytes bytes_ratio flows", options={"count": 6},
          handlers=drill(b + ' dest="$row.dest.value$" | sort 0 _time | head 1000'))
    v.add("splunk.line", "Average flow duration over time, by destination (ms)", 20, 254, 940, 270, q=b + " " + TC(20, "avg(duration_ms)", "dest", fill=False), options=opts(yAxisTitleText="ms"))
    v.add("splunk.column", "Baseline vs observed average duration (ms)", 20, 544, 460, 280, q=cmp_ + " | table dest baseline_ms observed_ms", options=opts(seriesColors=[C["blue"], C["accent"]]))
    v.add("splunk.line", "Total bytes over time, by destination", 500, 544, 460, 280, q=b + " " + TC(20, "sum(bytes)", "dest"), options=opts())
    v.add("splunk.bar", "Observed-period bytes by destination and port (port-based app label)", 980, 434, 460, 390,
          q=b + " " + per + " | where period=\"observed\" | eval svc=coalesce(app,\"unclassified\").\" :\".dest_port | stats sum(bytes) as bytes by dest svc | eval KB=round(bytes/1000,0) | chart sum(KB) over dest by svc", options=opts(stackMode="stacked", legendDisplay="bottom"))
    v.add("splunk.table", "Flow evidence (longest 100)", 20, 844, 1420, 250, q=b + " | sort - duration_ms | head 100 " + FLOW_TABLE, options={"count": 5})
    v.prereq(1114, "dest, dest_port, app, duration_ms, bytes")
    return v


# ---------------------------------------------------------------------------------------------------------------------------------- SEC-06
def sec06():
    v = View("NF-SEC-06-DDOS", "Volumetric DDoS indicators", "Where is the packet rate peaking, which protocols and TCP flags dominate, and which destination assets are targeted?",
             "Synthetic flood patterns. Production flow export is often sampled, and flow data cannot show whether availability was lost.", mitre=["T1498.001"])
    v.banner()
    b = v.B()
    v.add("splunk.area", "Packet rate (packets per second, 5 s buckets)", 20, 114, 1420, 300, q=b + " " + TC(5, "sum(packets) as packets") + " | eval pps=round(packets/5,1) | fields _time pps",
          options=opts(legendDisplay="off", yAxisTitleText="packets/s", seriesColors=[C["red"]]), desc="Packet counts per flow are attributed to the flow end time; peak is the highest 5 s bucket.")
    v.kpi("Peak packets/s", b + " | bin _time span=5s | stats sum(packets) as p by _time | eval r=p/5 | stats max(r) as v", 20, 434, w=230, h=110, color=C["red"])
    v.kpi("Flows", b + " | stats count as v", 270, 434, w=230, h=110)
    v.kpi("SYN-only flows", b + " | stats count(eval(tcp_flags=2)) as s count as n | eval v=round(100*s/n,1)", 520, 434, w=230, h=110, unit="%", prec=1)
    v.kpi("Distinct sources", b + " | stats dc(src) as v", 770, 434, w=230, h=110)
    v.kpi("Destinations receiving SYN-only flows", b + " | where tcp_flags=2 | stats dc(dest) as v", 1020, 434, w=420, h=110)
    v.add("splunk.column", "TCP flags over time", 20, 564, 480, 290, q=b + " | where transport=\"tcp\" " + TC(15, "count", "tcp_flags_text"), options=opts(stackMode="stacked"))
    v.add("splunk.pie", "Packets by protocol", 520, 564, 300, 290, q=b + " | stats sum(packets) as packets by transport", options=opts(legendDisplay="bottom"))
    v.add("splunk.bar", "Targeted assets (packets)", 840, 564, 600, 290, q=b + " | stats sum(packets) as packets dc(src) as sources by dest | sort - packets | head 8 | fields dest packets",
          options=opts(legendDisplay="off"), handlers=drill(b + ' dest="$click.value$" | sort - packets | head 1000'))
    v.add("splunk.line", "Attack progression: distinct sources per 15 s", 20, 874, 700, 260, q=b + " " + TC(15, "dc(src) as distinct_sources"), options=opts(legendDisplay="off", seriesColors=[C["amber"]]))
    v.add("splunk.table", "Top sources by packets (click for flow evidence)", 740, 874, 700, 260,
          q=b + " | stats sum(packets) as packets count as flows values(dest_port) as ports values(tcp_flags_text) as flags values(transport) as proto by src | sort - packets | head 50", options={"count": 6},
          handlers=drill(b + ' src="$row.src.value$" | sort 0 _time | head 1000'))
    v.prereq(1154, "packets, bytes, tcp_flags, tcp_flags_text, transport, src, dest, dest_port")
    return v


# ---------------------------------------------------------------------------------------------------------------------------------- SEC-07
def sec07():
    v = View("NF-SEC-07-PORTSCAN", "Network reconnaissance and port scanning", "Which hosts touch many ports or many destinations with tiny flows, and how does that footprint grow over time?",
             "Connection attempts do not prove access, and approved vulnerability scanners and monitors look the same in flow data.", mitre=["T1046"],
             extra_inputs={"min_hosts": ("Suspect if distinct destinations ≥", "20"), "min_ports": ("…or distinct ports ≥", "20")})
    v.banner()
    b = v.B()
    sus = "[ search " + b + " | stats dc(dest_port) as p dc(dest) as h by src | where p>=$min_ports$ OR h>=$min_hosts$ | fields src ]"
    prof = b + " | stats dc(dest_port) as unique_ports dc(dest) as unique_hosts count as flows avg(packets) as avg_pkts avg(bytes) as avg_bytes by src"
    v.add("splunk.scatter", "Footprint per source: distinct destinations (x) vs distinct ports (y); one dot per source", 20, 114, 820, 400,
          q=prof + " | table unique_hosts unique_ports", options=opts(legendDisplay="off", xAxisTitleText="distinct destination hosts", yAxisTitleText="distinct destination ports"))
    v.add("splunk.table", "Suspected scanning sources (click a row for the flows)", 860, 114, 580, 400,
          q=prof + " | where unique_ports>=$min_ports$ OR unique_hosts>=$min_hosts$ | eval avg_pkts=round(avg_pkts,1), avg_bytes=round(avg_bytes,0) | sort - unique_ports | table src unique_hosts unique_ports flows avg_pkts avg_bytes",
          options={"count": 8}, handlers=drill(b + ' src="$row.src.value$" | sort 0 _time | head 1000'))
    v.add("splunk.line", "Cumulative distinct destination hosts per suspected source", 20, 534, 700, 270,
          q=b + " " + sus + " | sort 0 _time | streamstats dc(dest) as hosts by src " + TC(10, "max(hosts)", "src", fill=False) + " | filldown", options=opts(yAxisTitleText="distinct hosts"))
    v.add("splunk.line", "Cumulative distinct ports per suspected source", 740, 534, 700, 270,
          q=b + " " + sus + " | sort 0 _time | streamstats dc(dest_port) as ports by src " + TC(10, "max(ports)", "src", fill=False) + " | filldown", options=opts(yAxisTitleText="distinct ports"))
    v.add("splunk.bar", "Most probed ports (suspected sources)", 20, 824, 480, 140, q=b + " " + sus + " | stats count by dest_port | sort - count | head 12 | eval dest_port=\"port \".dest_port", options=opts(legendDisplay="off"))
    v.kpi("Suspected sources", prof + " | where unique_ports>=$min_ports$ OR unique_hosts>=$min_hosts$ | stats count as v", 520, 824, w=240, h=130, color=C["red"])
    v.kpi("Avg packets per scan flow", b + " " + sus + " | stats avg(packets) as v", 780, 824, w=240, h=130, prec=1)
    v.kpi("Avg bytes per scan flow", b + " " + sus + " | stats avg(bytes) as v", 1040, 824, w=400, h=130)
    v.add("splunk.table", "Investigation table: flows from suspected sources", 520, 974, 920, 250, q=b + " " + sus + " | sort 0 _time | head 300 " + FLOW_TABLE, options={"count": 6})
    v.add("splunk.table", "Suspected-source SYN profile", 20, 974, 480, 250, q=b + " " + sus + " | stats count as flows count(eval(tcp_flags=2)) as syn_only count(eval(packets<=2)) as tiny by src | eval syn_only_pct=round(100*syn_only/flows,1)", options={"count": 5})
    v.prereq(1244, "src, dest, dest_port, packets, bytes, tcp_flags")
    return v


# ---------------------------------------------------------------------------------------------------------------------------------- SEC-08
def sec08():
    v = View("NF-SEC-08-EXFIL", "Outbound data-exfiltration indicators", "Which internal host sends unusual byte volume to external destinations, over which ports and when?",
             "Volume alone does not establish data theft: backups, updates and uploads look identical in flow records. Internal ranges are the lab documentation ranges, adjustable below.", mitre=["T1048"],
             extra_inputs={"int1_tok": ("Internal range 1", "192.0.2.0/24"), "int2_tok": ("Internal range 2", "198.51.100.0/24"), "min_mb": ("Evidence threshold (MB per flow)", "50")})
    v.banner()
    b = v.B()
    out = ('| where (cidrmatch("$int1_tok$",src) OR cidrmatch("$int2_tok$",src)) AND NOT (cidrmatch("$int1_tok$",dest) OR cidrmatch("$int2_tok$",dest))')
    v.add("splunk.sankey", "Outbound volume: internal source → external destination (MB)", 20, 114, 940, 320,
          q=b + " " + out + " | stats sum(bytes) as MB by src dest | eval MB=round(MB/1e6,1) | sort - MB | head 6 | table src dest MB", options={})
    v.kpi("Outbound volume (MB)", b + " " + out + " | stats sum(bytes) as b | eval v=round(b/1e6,1)", 980, 114, w=225, h=150, prec=1)
    v.kpi("External destinations", b + " " + out + " | stats dc(dest) as v", 1215, 114, w=225, h=150)
    v.kpi("Top source vs median source", b + " " + out + " | stats sum(bytes) as b by src | eventstats median(b) as med | eval v=round(b/med,1) | sort - b | head 1 | fields v", 980, 284, w=460, h=150, unit="× median", prec=1, color=C["red"])
    v.add("splunk.area", "Outbound transfer timeline (Mbps, bytes spread over each flow)", 20, 454, 940, 280,
          q=b + " " + out + " " + SPREAD + " | stats sum(share) as s by _time | makecontinuous _time span=10s | fillnull value=0 | eval Mbps=round(s*8/1e6/10,1) | fields _time Mbps", options=opts(legendDisplay="off", seriesColors=[C["red"]]))
    v.add("splunk.bar", "Top internal sources (MB out)", 980, 454, 460, 280, q=b + " " + out + " | stats sum(bytes) as bytes by src | sort - bytes | head 8 | eval MB=round(bytes/1e6,1) | fields src MB",
          options=opts(legendDisplay="off"), handlers=drill(b + ' src="$click.value$" | sort - bytes | head 1000'))
    v.add("splunk.table", "Destination and port analysis", 20, 754, 700, 270,
          q=b + " " + out + " | stats sum(bytes) as bytes count as flows dc(src) as sources min(_time) as first max(_time) as last by dest dest_port | eval MB=round(bytes/1e6,1), first=strftime(first,\"%H:%M:%S\"), last=strftime(last,\"%H:%M:%S\") | sort - bytes | table dest dest_port MB flows sources first last",
          options={"count": 6}, handlers=drill(b + ' dest="$row.dest.value$" dest_port=$row.dest_port.value$ | sort - bytes | head 1000'))
    v.add("splunk.pie", "Outbound bytes by port (port-based label)", 740, 754, 700, 270, q=b + " " + out + " | stats sum(bytes) as bytes by dest_port | eval dest_port=\"port \".dest_port | sort - bytes", options=opts(legendDisplay="right"))
    v.add("splunk.table", "Evidence: outbound flows above threshold", 20, 1044, 1420, 250, q=b + " " + out + " | where bytes>=$min_mb$*1000000 | sort - bytes " + FLOW_TABLE, options={"count": 6})
    v.prereq(1314, "src, dest, dest_port, bytes, flowStartMilliseconds, flowEndMilliseconds")
    return v


# ---------------------------------------------------------------------------------------------------------------------------------- SEC-09
def sec09():
    v = View("NF-SEC-09-BEACON", "Command-and-control beaconing indicators", "Which source/destination pairs reconnect on a regular interval, and how regular is it?",
             "Periodicity is a weak indicator by itself: agents, monitoring and update checks beacon too, and encrypted payloads are not visible. Intervals use actual flow start timestamps.", mitre=["T1071"],
             extra_inputs={"min_ev": ("Min intervals per pair", "5"), "cv_tok": ("High regularity if CV below", "0.25"), "bin_tok": ("Histogram bin (s)", "5")})
    v.banner()
    b = v.B()
    gap = "| sort 0 src dest flowStartMilliseconds | streamstats current=f last(flowStartMilliseconds) as prev by src dest | eval gap_s=round((flowStartMilliseconds-prev)/1000,1) | where isnotnull(gap_s)"
    rank = (b + " " + gap + " | stats count as intervals avg(gap_s) as mean_s stdev(gap_s) as sd_s min(gap_s) as min_s max(gap_s) as max_s sum(bytes) as bytes by src dest | where intervals>=$min_ev$ "
            "| eval cv=round(sd_s/mean_s,3), mean_s=round(mean_s,1), sd_s=round(sd_s,1) | eval regularity=if(cv<$cv_tok$,\"high\",if(cv<0.6,\"medium\",\"low\"))")
    v.add("splunk.column", "Inter-arrival interval distribution (seconds between consecutive flow starts per pair)", 20, 114, 940, 330,
          q=b + " " + gap + " | where gap_s<=600 | bin gap_s span=$bin_tok$ | stats count by gap_s | sort 0 gap_s", options=opts(legendDisplay="off", xAxisTitleText="interval (s)", yAxisTitleText="intervals"),
          desc="A tall narrow peak means many repeats at one interval.")
    v.kpi("Pairs analysed", rank + " | stats count as v", 980, 114, w=225, h=150)
    v.kpi("High-regularity pairs", rank + " | where cv<$cv_tok$ | stats count as v", 1215, 114, w=225, h=150, color=C["red"])
    v.kpi("Lowest CV", rank + " | stats min(cv) as v", 980, 284, w=460, h=160, prec=3)
    v.add("splunk.table", "Pairs ranked by regularity (lowest coefficient of variation first; click a row for the flows)", 20, 464, 1420, 260,
          q=rank + " | sort cv | table src dest intervals mean_s sd_s cv regularity min_s max_s bytes", options={"count": 6}, handlers=drill(b + ' src="$row.src.value$" dest="$row.dest.value$" | sort 0 _time | head 1000'))
    v.add("splunk.column", "Periodicity timeline: contacts per 5 s for the 3 most regular pairs", 20, 744, 940, 290,
          q=b + " [ search " + rank + " | sort cv | head 3 | fields src dest ] | eval pair=src.\" → \".dest " + TC(5, "count", "pair"), options=opts(stackMode="stacked"))
    v.add("splunk.bar", "Coefficient of variation, 10 most regular pairs", 980, 744, 460, 290, q=rank + " | sort cv | head 10 | eval pair=src.\" → \".dest | table pair cv", options=opts(legendDisplay="off"))
    v.add("splunk.table", "Flow evidence (regular pairs)", 20, 1054, 1420, 250, q=b + " [ search " + rank + " | where cv<$cv_tok$ | fields src dest ] | sort 0 src dest flowStartMilliseconds | head 300 " + FLOW_TABLE, options={"count": 6})
    v.prereq(1324, "src, dest, flowStartMilliseconds, bytes, packets")
    return v


# ---------------------------------------------------------------------------------------------------------------------------------- SEC-10
def sec10():
    v = View("NF-SEC-10-DNS-FLOW", "DNS-tunneling indicators (flow-only, limited evidence)", "Which clients send unusually many or unusually large DNS flows, and is request/response volume imbalanced?",
             "LIMITED EVIDENCE. Flow records contain no query names, label lengths or entropy, so encoded DNS labels cannot be detected here. Correlate with DNS logs (for example the SEC-P9 DNS wire events) to go further.",
             mitre=["T1071.004", "T1048.003"], extra_inputs={"z_tok": ("Outlier if z-score ≥", "3")})
    v.banner()
    b = v.B()
    dns = ('| where src_port=53 OR dest_port=53 | eval dir=if(dest_port=53,"query (client to resolver)","response (resolver to client)"), client=if(dest_port=53,src,dest), resolver=if(dest_port=53,dest,src)')
    cl = (b + " " + dns + " | stats sum(eval(if(dest_port=53,bytes,0))) as req_bytes sum(eval(if(src_port=53,bytes,0))) as resp_bytes count(eval(dest_port=53)) as query_flows dc(resolver) as resolvers by client "
          "| eval avg_req_bytes=round(req_bytes/query_flows,0), resp_req_ratio=round(resp_bytes/req_bytes,2) | eventstats avg(query_flows) as mq stdev(query_flows) as sq avg(avg_req_bytes) as ma stdev(avg_req_bytes) as sa "
          "| eval z_flows=round((query_flows-mq)/sq,1), z_size=round((avg_req_bytes-ma)/sa,1) | eval outlier=if(z_flows>=$z_tok$ OR z_size>=$z_tok$,\"outlier vs peers\",\"\")")
    v.add("splunk.area", "DNS bytes over time by direction", 20, 114, 700, 290, q=b + " " + dns + " " + TC(15, "sum(bytes)", "dir"), options=opts(stackMode="stacked", seriesColors=[C["accent"], C["blue"]]))
    v.kpi("DNS flow records", b + " " + dns + " | stats count as v", 740, 114, w=230, h=140)
    v.kpi("Clients", b + " " + dns + " | stats dc(client) as v", 980, 114, w=230, h=140)
    v.kpi("Outlier clients", cl + " | where outlier!=\"\" | stats count as v", 1220, 114, w=220, h=140, color=C["red"])
    v.kpi("Resolvers", b + " " + dns + " | stats dc(resolver) as v", 740, 274, w=230, h=130)
    v.kpi("Median response/request ratio", cl + " | stats median(resp_req_ratio) as v", 980, 274, w=460, h=130, prec=2)
    v.add("splunk.scatter", "Clients: average request size (x) vs query flows (y); one dot per client", 20, 424, 700, 360, q=cl + " | table avg_req_bytes query_flows",
          options=opts(legendDisplay="off", xAxisTitleText="average request bytes per flow", yAxisTitleText="query flows"))
    v.add("splunk.table", "Client behaviour (click a row for the DNS flows)", 740, 424, 700, 360,
          q=cl + " | sort - z_flows | table client query_flows avg_req_bytes resp_req_ratio z_flows z_size outlier", options={"count": 8}, handlers=drill(b + ' (src="$row.client.value$" OR dest="$row.client.value$") | sort 0 _time | head 1000'))
    v.add("splunk.table", "Resolver behaviour", 20, 804, 560, 230, q=b + " " + dns + " | stats dc(client) as clients count as flows sum(bytes) as bytes by resolver | sort - bytes", options={"count": 5})
    v.add("splunk.column", "Response/request byte ratio, top 10 clients by query flows", 600, 804, 840, 230, q=cl + " | sort - query_flows | head 10 | table client resp_req_ratio", options=opts(legendDisplay="off"))
    v.add("splunk.table", "Supporting DNS flow evidence (outlier clients)", 20, 1054, 1420, 250,
          q=b + " [ search " + cl + " | where outlier!=\"\" | eval src=client | fields src ] " + dns + " | sort 0 _time | head 300 " + FLOW_TABLE, options={"count": 6})
    v.prereq(1324, "src, dest, src_port, dest_port, bytes, packets; statistical outliers are peer-relative, not a threshold on query content")
    return v


BUILDERS = [noc01, noc02, noc03, noc04, noc05, sec06, sec07, sec08, sec09, sec10]


def write_nav(built):
    nav = ROOT / "netspout" / "default" / "data" / "ui" / "nav" / "default.xml"
    text = nav.read_text(encoding="utf-8")
    rows = "\n".join('    <view name="pf_%s" label="%s"/>' % (sid, escape(title, {'"': "&quot;"})) for sid, title in built)
    block = '  <collection label="NetFlow / IPFIX">\n%s\n  </collection>\n' % rows
    if 'label="NetFlow / IPFIX"' in text:
        text = re.sub(r'  <collection label="NetFlow / IPFIX">.*?</collection>\n', lambda m: block, text, count=1, flags=re.S)
    else:
        text = text.replace('  <collection label="Operations">', block + '  <collection label="Operations">', 1)
    nav.write_text(text, encoding="utf-8")


def main():
    built = []
    for fn in BUILDERS:
        v = fn()
        xml, spec = v.xml()
        (VIEWS / ("pf_%s.xml" % v.sid)).write_text(xml, encoding="utf-8")
        built.append((v.sid, v.title))
    write_nav(built)
    print(json.dumps({"dashboards": len(built), "ids": [b[0] for b in built]}))


if __name__ == "__main__":
    main()
