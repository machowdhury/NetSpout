"""WIRE stage for the NetFlow solution scenarios: the same FlowRecords go out as real IPFIX over UDP to the existing GoFlow2 collector.
Reuses NativeFlowTransport + ExporterSession + CollectorEvidenceAdapter (nothing is re-encoded here). No correlation is registered with the forwarder, so the forwarder's
own HEC events carry no run id and can never be mistaken for, or double-counted with, the normalized events the run monitor delivers.
Stages are reported separately: generated -> UDP exported -> collector decoded. 'Decoded' is a collector metric delta, not proof of indexing."""
import os
import time
from typing import Any, Dict, List

from netspout_core.collector_evidence import CollectorEvidenceAdapter
from netspout_core.exporter_session import ExporterSession
from netspout_core.transport_native_flow import NativeFlowTransport


def export(rows: List[Dict[str, Any]], environment: Dict[str, str] = None, settle_s: float = 6.0) -> Dict[str, Any]:
    env = environment if environment is not None else os.environ
    host = env.get("NETSPOUT_COLLECTOR_HOST", "127.0.0.1")
    adapter = CollectorEvidenceAdapter(env.get("NETSPOUT_GOFLOW_METRICS_URL", "http://%s:8080/metrics" % host), env.get("NETSPOUT_FLOW_FORWARDER_STATUS_URL", "http://%s:8082" % host))
    out: Dict[str, Any] = {"protocol": "IPFIX", "collector": "%s:%s" % (host, env.get("NETSPOUT_IPFIX_PORT", "4739")), "generated": len(rows), "udp_exported": 0, "datagrams": 0,
                           "collector_decoded": None, "state": "SKIPPED", "note": ""}
    before = adapter.get_prometheus_metrics()
    if not before.get("raw_metric_count"):
        out.update(state="COLLECTOR_UNREACHABLE", note="GoFlow2 metrics endpoint did not answer; no UDP was sent. The normalized HEC delivery is unaffected.")
        return out
    try:
        transport = NativeFlowTransport(destination_host=host, destination_port=int(env.get("NETSPOUT_IPFIX_PORT", "4739")), protocol="IPFIX", rate_pps=50,
                                        max_packets_per_run=5000, allow_privileged_ports=False, template_refresh_policy="EVERY_BURST", test_mode=False)
    except Exception as exc:  # destination safety checks reject non-lab targets
        out.update(state="BLOCKED", note="UDP export refused: %s" % exc)
        return out
    by_exp: Dict[str, List] = {}
    for r in rows:
        by_exp.setdefault(r["exporter_ip"], []).append(r["record"])
    for i, (ip, recs) in enumerate(sorted(by_exp.items())):
        session = ExporterSession(node_id="netspout-nf-%s" % ip, exporter_ip=ip, observation_domain_id=300 + i, base_time_epoch_ms=min(x.start_time_ms for x in recs), template_refresh_policy="EVERY_BURST")
        sent = transport.send_batch(recs, session, force_template=True)
        out["udp_exported"] += int(getattr(sent, "records_encoded", 0) if getattr(sent, "datagrams_sent", 0) else 0)
        out["datagrams"] += int(getattr(sent, "datagrams_sent", 0))
    deadline = time.time() + settle_s
    while True:   # the collector decodes asynchronously: wait until its counter catches up with what was sent, or give up at the deadline
        after = adapter.get_prometheus_metrics()
        out["collector_decoded"] = max(0, int(after.get("records_total", 0)) - int(before.get("records_total", 0)))
        if out["collector_decoded"] >= out["udp_exported"] or time.time() >= deadline:
            break
        time.sleep(0.4)
    out["state"] = "COLLECTOR_DECODED" if out["collector_decoded"] >= out["udp_exported"] > 0 else ("PARTIAL" if out["collector_decoded"] else "UDP_SENT_NOT_CONFIRMED")
    out["note"] = ("collector_decoded is the GoFlow2 data-record counter delta during this export and could include other senders. It is not HEC acceptance and not indexing.")
    return out
