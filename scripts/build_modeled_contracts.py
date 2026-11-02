#!/usr/bin/env python3
"""
Build declarative scenario contracts for the scenario definitions that carry a specification but no executable telemetry, and merge them into
catalog/scenario_contracts.json (hand-authored contracts are never touched; generated ones are replaced on every run).

Sources and what each contributes (nothing is invented beyond the stated assumptions, and every contract records them):
  catalog/cisco_100_scenarios.json   title, story, objective, business impact, technologies, failure vector, entities, relationships and the staged state timeline
                                     -> modeled state progression (netspout:scenario:state), dependency first, dependent second
  catalog/scenario_candidates.json   community monitoring use cases (title + data-source hint) -> a documented archetype interpretation (see ARCHETYPES)

All output of these contracts uses the labeled MODELED_NETSPOUT_SCHEMA (src/netspout_core/modeled_telemetry.py); it is never presented as vendor-native.

  PYTHONPATH=src:backend python scripts/build_modeled_contracts.py
"""
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "catalog" / "scenario_contracts.json"
SEVERITY = {"HEALTHY": "info", "IMPAIRED": "warning", "DEGRADED": "warning", "FAILED": "critical", "DOWN": "critical", "OUTAGE": "critical", "COMPROMISED": "critical",
            "INVESTIGATING": "warning", "RECOVERING": "notice", "FAILOVER": "notice", "MITIGATED": "notice"}
NODE_TYPE = {"Enterprise Networking": "SWITCH", "Service Provider": "ROUTER", "Data Center": "SWITCH", "Security": "FIREWALL", "Critical Infrastructure": "ROUTER"}
ROUNDS = {"BASELINE": 2, "INCIDENT": 3}


def ip_for(key):
    h = hashlib.sha256(key.encode()).digest()
    return "10.%d.%d.%d" % (20 + h[0] % 180, h[1] % 250, 1 + h[2] % 250)


def sev(state):
    return SEVERITY.get(state.upper(), "warning" if state.upper() not in ("HEALTHY", "NORMAL") else "info")


def modeled_stream(sid, node, scenario_id, component, stages, states, messages, entity, extra=None):
    """One stream: the entity's state in each phase, with the state it came from."""
    phase_params, prev = {}, "HEALTHY"
    for st in stages:
        cur = states[st]
        phase_params[st] = {"state": cur, "previous_state": prev, "severity": sev(cur), "message": messages[st]}
        prev = cur
    first = stages[0]
    params = {"scenario_id": scenario_id, "entity": entity, "component": component, **phase_params[first]}
    if extra:
        params.update(extra)
    return {"id": sid, "sourcetype": "netspout:scenario:state", "formatter": "format_modeled_state_event", "node": node, "params": params, "phase_params": phase_params, "per_round": 1}


def c100(r):
    cid = r["scenario_id"]
    ents = r["entities"]
    ntype = NODE_TYPE.get(r["domain"], "ROUTER")
    nodes = [{"id": "n%d" % i, "name": e, "type": ntype, "ip": ip_for(cid + e), "vendor": "cisco"} for i, e in enumerate(ents)]
    stages = [t["stage"] for t in r["timeline"]]
    var = next(iter(r["enterprise_state"]))
    cur, states = r["enterprise_state"][var], {}
    for t in r["timeline"]:
        cur = t["state_changes"].get(var, cur)
        states[t["stage"]] = cur
    obs = {t["stage"]: t["expected_observation"] for t in r["timeline"]}
    dep = next((rel for rel in r["relationships"] if "depends on" in rel), None)
    dependency, dependent = (nodes[1], nodes[0]) if dep and len(nodes) >= 2 else (nodes[-1], nodes[0])
    msgs_dep = {s: (obs[s] + (" Failure vector: " + r["failure_or_attack_vector"] + "." if s not in ("BASELINE", "RECOVERY") else "")) for s in stages}
    msgs_dnt = {s: (obs[s] + (" Dependency %s is %s." % (dependency["name"], states[s].lower()))) for s in stages}
    streams = [modeled_stream("dependency", dependency["id"], cid, var, stages, states, msgs_dep, dependency["name"])]
    if dependent is not dependency:
        streams.append(modeled_stream("dependent", dependent["id"], cid, var, stages, states, msgs_dnt, dependent["name"]))
    corr = [{"entity": dependency["name"], "tokens": [dependency["name"]], "streams": [s["id"] for s in streams]}] if len(streams) > 1 else []
    c = {"id": cid, "title": r["title"], "category": r["category"], "vendors": ["cisco"], "technologies": r["technologies"], "generator_family": "modeled_state_progression",
         "kind": "security" if r["domain"] == "Security" else "operational", "source": "generated:cisco_100_scenarios.json",
         "description": "%s. Business impact: %s %s %s" % (r["failure_or_attack_vector"].rstrip("."), r["business_impact"].rstrip(".") + ".", r["story"], r["technical_objective"]),
         "assumptions": ["Telemetry is MODELED (sourcetype netspout:scenario:state): the catalog entry specifies a state progression and expected observations but defines no vendor log format, so none is invented.",
                         "Entities are the catalog's fictional names; their addresses are deterministic private addresses.",
                         "Technologies named by the catalog (%s) label the scenario; no device-native log of those products is emitted." % ", ".join(r["technologies"]),
                         ("Ordering follows the catalog relationship '%s': the dependency changes state first, then the dependent." % dep) if dep else "No dependency relationship is stated; the first entity is treated as the dependent."],
         "nodes": nodes, "phases": [{"id": s, "label": obs[s], "rounds": ROUNDS.get(s, 2)} for s in stages], "streams": streams, "correlation": corr}
    if not corr:
        c["correlation_limit"] = "Only one entity is modeled, so there is nothing to correlate across streams."
    return c


# ------------------------------------------------------------------------------------------------------ community use cases (title + data-source hint only)
# First matching archetype wins. Metric names, units and values are MODELED to show a deviation and its recovery; they are not measurements of any product.
ARCHETYPES = [
    ("temperature_excursion", r"temperature|cold storage|cold chain|refrigerator|hvac|greenhouse|humidity|environmental safety", "temperature_c", "degC", [4.0, 4.2, 3.9], [8.6, 10.1, 11.4], "NORMAL", "EXCURSION"),
    ("process_variable", r"process (variable|parameter)|dissolved gas|spc chart|quality spc|yield|oee|pressure and flow|pipeline pressure|spectrum|setpoint", "process_variable_zscore", "sigma", [0.2, 0.3, 0.1], [3.9, 4.8, 5.4], "NORMAL", "OUT_OF_BOUNDS"),
    ("fraud_anomaly", r"fraud|anomal|unusual|leakage|overpayment|expenditure|settlement|ring detection|geo-velocity|unauthorized", "anomaly_score", "score", [0.08, 0.12, 0.1], [0.81, 0.93, 0.97], "NORMAL", "ANOMALOUS"),
    ("compliance_audit", r"gdpr|mifid|ferpa|cmmc|soc 2|consent|retention|legal hold|audit|traceab|integrity|conflicts of interest|compliance|cardholder|cryptographic|baseline configuration|incident response lifecycle|title ix|voting|pci", "policy_violations", "count", [0, 0, 1], [6, 9, 12], "COMPLIANT", "VIOLATION"),
    ("latency_sla", r"response time|latency|wait time|answer time|dispatch|sla\b|cycle time|turnaround|processing time|fulfillment|completion rate|queue length|timeliness|backlog|scheduling gap|lag", "response_time_ms", "ms", [120, 135, 110], [940, 1320, 1780], "WITHIN_SLA", "SLA_BREACH"),
    ("error_rate", r"error rate|error|failure|fault|jam|misroute|trip|flooding|overflow|rate-limit|breach|call failure|trouble code", "error_rate_pct", "%", [0.4, 0.5, 0.3], [11.0, 14.5, 19.2], "NORMAL", "ELEVATED_ERRORS"),
    ("capacity_utilization", r"throughput|utilization|capacity|surge|passenger flow|volume|usage|egress|hit rate|hit ratio|cache|quota|burn|speed|patterns", "utilization_pct", "%", [38, 41, 44], [91, 96, 99], "NORMAL", "SATURATED"),
    ("availability_health", r"uptime|availability|health|status|connectivity|communication|sensor|visibility|battery|reachability|integration|lighting|display|monitoring", "availability_pct", "%", [99.95, 99.9, 99.97], [92.0, 87.5, 81.0], "AVAILABLE", "DEGRADED_AVAILABILITY"),
]
DEFAULT_ARCH = ("service_health", "", "service_health_score", "score", [0.98, 0.97, 0.99], [0.62, 0.48, 0.35], "NORMAL", "DEGRADED")
UC_PHASES = [("BASELINE", "Normal operation", 3), ("DEVIATION", "The indicator departs from its normal range", 3), ("ESCALATION", "The deviation grows", 2),
             ("RESPONSE", "Operators act on the alert", 2), ("RECOVERY", "The indicator returns to normal", 3)]


def pick_archetype(title):
    for a in ARCHETYPES:
        m = re.search(a[1], title.lower())
        if m:
            return a, m.group(0)
    return DEFAULT_ARCH, None


def slug(title):
    return "-".join(re.findall(r"[a-z0-9]+", re.sub(r"\(.*?\)", "", title.lower()))[:3]) or "entity"


def uc(row):
    cid, title = row["candidate_id"], row["title"]
    (arch, _, metric, unit, base, bad, ok_state, bad_state), kw = pick_archetype(title)
    sl = slug(title)
    t_low = title.lower()
    etype = "IOT_SENSOR" if re.search(r"sensor|hvac|plc|rtu|refrigerator|elevator|lighting|scada|battery|gps|vehicle|meter|valve", t_low) else \
        "DATABASE" if re.search(r"audit|record|ledger|consent|trail", t_low) else "WEB_SERVER"
    nodes = [{"id": "subject", "name": sl + "-01", "type": etype, "ip": ip_for(cid + "subject"), "vendor": "generic"},
             {"id": "monitor", "name": sl + "-monitor", "type": "SWITCH", "ip": ip_for(cid + "monitor"), "vendor": "generic"}]
    values = {"BASELINE": base, "DEVIATION": bad[:2], "ESCALATION": bad[1:], "RESPONSE": [bad[0], base[0] * 2 + bad[0] / 4 if base[0] else bad[0] / 2], "RECOVERY": base}
    states = {"BASELINE": ok_state, "DEVIATION": bad_state, "ESCALATION": bad_state, "RESPONSE": "MITIGATING", "RECOVERY": "RECOVERED"}
    sevs = {"BASELINE": "info", "DEVIATION": "warning", "ESCALATION": "error", "RESPONSE": "notice", "RECOVERY": "info"}
    msg = {"BASELINE": "%s is within its normal range." % title, "DEVIATION": "%s: indicator %s is outside its normal range." % (title, metric),
           "ESCALATION": "%s: deviation of %s is growing." % (title, metric), "RESPONSE": "%s: operators are acting; %s is coming back." % (title, metric), "RECOVERY": "%s has returned to normal." % title}
    prev, pp = ok_state, {}
    for ph, _, _ in UC_PHASES:
        pp[ph] = {"state": states[ph], "previous_state": prev, "severity": sevs[ph], "message": msg[ph], "metric_value": values[ph]}
        prev = states[ph]
    measure = {"id": "measure", "sourcetype": "netspout:scenario:state", "formatter": "format_modeled_state_event", "node": "subject", "per_round": 1,
               "params": {"scenario_id": cid, "entity": nodes[0]["name"], "component": arch, "metric_name": metric, "unit": unit, **pp["BASELINE"]}, "phase_params": pp}
    alert_pp = {ph: {"state": "ALERT_FIRING", "previous_state": "OK", "severity": "error", "message": "Monitoring rule for '%s' fired on %s (%s breached)." % (title, nodes[0]["name"], metric)}
                for ph in ("DEVIATION", "ESCALATION")}
    alert_pp["RESPONSE"] = {"state": "ALERT_ACKNOWLEDGED", "previous_state": "ALERT_FIRING", "severity": "notice", "message": "Alert for '%s' on %s acknowledged by an operator." % (title, nodes[0]["name"])}
    alert_pp["RECOVERY"] = {"state": "ALERT_CLEARED", "previous_state": "ALERT_ACKNOWLEDGED", "severity": "info", "message": "Alert for '%s' on %s cleared." % (title, nodes[0]["name"])}
    alert = {"id": "alert", "sourcetype": "netspout:scenario:state", "formatter": "format_modeled_state_event", "node": "monitor", "per_round": 1, "phases": list(alert_pp),
             "params": {"scenario_id": cid, "entity": nodes[0]["name"], "component": "monitoring_rule", **alert_pp["DEVIATION"]}, "phase_params": alert_pp}
    hint = (row.get("dependencies", {}).get("upstream_data_sources_hint") or "").strip()
    return {"id": cid, "title": title, "category": "COMPLIANCE" if arch == "compliance_audit" else "OPERATIONS", "vendors": [], "generator_family": "modeled_use_case_archetype",
            "kind": "operational", "source": "generated:scenario_candidates.json",
            "description": "%s A monitoring use case: the indicator %s%s shows a deviation, the monitoring rule fires, operators respond and the indicator recovers. Source hint (%s): %s" % (
                title + ".", metric, " (%s)" % unit if unit else "", row.get("source_ref", cid), (hint[:230] + "...") if len(hint) > 230 else hint or "none given."),
            "assumptions": ["Telemetry is MODELED (sourcetype netspout:scenario:state): the community use case documents what to monitor on real data, not an event format, so no product log syntax is invented.",
                            "Interpretation: archetype '%s'%s. Metric %s, its unit and its values are modeled to show a deviation and recovery; they are not measurements of any product." % (arch, " (matched '%s' in the title)" % kw if kw else " (default: no specific archetype matched the title)", metric),
                            "Products and indexes named in the source hint are not emitted; the entity and the monitoring node are fictional."],
            "nodes": nodes, "phases": [{"id": i, "label": l, "rounds": r} for i, l, r in UC_PHASES], "streams": [measure, alert],
            "correlation": [{"entity": nodes[0]["name"], "tokens": [nodes[0]["name"]], "streams": ["measure", "alert"]}]}


def main():
    existing = json.loads(OUT.read_text())
    kept = [c for c in existing["contracts"] if not str(c.get("source", "")).startswith("generated:")]
    runnable_ids = {c["id"] for c in kept}
    cand = {c["candidate_id"] for c in json.loads((ROOT / "catalog" / "scenario_candidates.json").read_text())["candidates"]}
    gen = []
    for r in json.loads((ROOT / "catalog" / "cisco_100_scenarios.json").read_text())["scenarios"]:
        if r["scenario_id"] in cand and r["scenario_id"] not in runnable_ids:
            gen.append(c100(r))
    for row in json.loads((ROOT / "catalog" / "scenario_candidates.json").read_text())["candidates"]:
        if not row["candidate_id"].startswith("C100-") and row["candidate_id"] not in runnable_ids:
            gen.append(uc(row))
    existing["contracts"] = kept + gen
    OUT.write_text(json.dumps(existing, indent=1) + "\n")
    print(json.dumps({"authored": len(kept), "generated": len(gen), "total": len(existing["contracts"])}))


if __name__ == "__main__":
    main()
