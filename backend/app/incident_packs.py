# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/incident_packs.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""Adapter for the finite, seeded NetSpout incident packs (27 network + 10 telecom) so the backend scenario-pack path can run them.

The generators live in the Splunk app (network_incidents.py / telecom_incidents.py, used unchanged by the app's runner). They emit
NetSpout-defined, MODELED telemetry (netspout:network:* / netspout:telecom:*): synthetic vendor-style messages, not device firmware
emulation and not vendor-native formats. Each run is 30 log records plus 10 gauge records (3 to 5 metrics per record, depending on the incident); a supplied seed, start
and run id reproduce the exact events.
"""
import sys
import time
from pathlib import Path


def _load():
    try:
        import network_incidents, telecom_incidents  # noqa: F401 (Splunk app bin directory is already on sys.path)
    except ImportError:
        for parent in Path(__file__).resolve().parents:
            for candidate in (parent / "netspout" / "bin", parent):
                if (candidate / "network_incidents.py").is_file():
                    sys.path.insert(0, str(candidate))
                    break
            else:
                continue
            break
        import network_incidents, telecom_incidents  # noqa: F401
    return network_incidents, telecom_incidents


def catalog():
    """Stable entries: network slugs become `network_<slug>`; telecom slugs already start with `telco_`."""
    net, tel = _load()
    rows = [{"scenario_id": "network_" + slug, "slug": slug, "family": "network", "title": row[1]} for slug, row in net.CATALOG.items()]
    rows += [{"scenario_id": slug, "slug": slug, "family": "telecom", "title": row[0]} for slug, row in tel.CATALOG.items()]
    return rows


def incident_ids():
    return [r["scenario_id"] for r in catalog()]


def generate_pack(scenario_id, run_id, seed=42, eps=10, now=None):
    net, _ = _load()
    entry = next((r for r in catalog() if r["scenario_id"] == scenario_id), None)
    if entry is None:
        raise ValueError("Unsupported incident pack: " + str(scenario_id))
    # 40 paced records; start far enough back that every record time is already in the past when it is sent
    start = (now or time.time()) - 40.0 / eps - 1.0
    events = net.generate(entry["slug"], seed, start, run_id, eps)
    if len(events) != 40 or sum("metrics" in e for e in events) != 10:
        raise RuntimeError("Incident pack did not produce the documented 30 log + 10 gauge records")
    return events


def hec_payloads(events, event_index, metric_index):
    """Exactly the app runner's HEC conversion: gauges go to the metric index with metric_name:* fields."""
    out = []
    for e in events:
        fields = dict(e["fields"])
        if "metrics" in e:
            fields.update({"metric_name:" + k: v for k, v in e["metrics"].items()})
        out.append(dict(time=e["time"], host=e["host"], source=e["source"], sourcetype=e["sourcetype"],
                        index=metric_index if "metrics" in e else event_index,
                        event="metric" if "metrics" in e else e["raw"], fields=fields))
    return out


def summarize(events):
    logs = [e for e in events if "metrics" not in e]
    gauges = [e for e in events if "metrics" in e]
    return {"records": len(events), "log_events": len(logs), "metric_events": len(gauges),
            "metric_datapoints": sum(len(e["metrics"]) for e in gauges),
            "phases": sorted({e["fields"]["netspout_phase"] for e in events})}
