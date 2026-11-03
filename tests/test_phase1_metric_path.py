"""cisco:ios:mdt:metric through Generate Data: must reach Splunk as HEC *metrics* (event "metric", metric_name:<name> numeric fields, metric index),
never as a log event. Splunk-side proof (mstats) is a separate lab step; this checks the payload Splunk's HEC metric format requires."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]

from netspout_core import generator_modes, telemetry_dispatcher  # noqa: E402
from netspout_core.models import TelemetryTransportConfig  # noqa: E402

SVC = generator_modes.TelemetryGeneratorService


def test_generate_data_metric_entries_carry_numeric_measurements():
    entries, prov = SVC().prepare_sourcetype_entries("cisco_ios", "cisco:ios:mdt:metric", 6)
    assert prov["mode"] == "native"
    for e in entries:
        fields = telemetry_dispatcher.TelemetryDispatcher.extract_metric_fields(e)
        names = [k for k in fields if k.startswith("metric_name:")]
        assert {"metric_name:in_octets", "metric_name:cpu_utilization"} <= set(names), names
        assert all(isinstance(fields[k], float) for k in names)


def test_hec_payload_is_metric_encoded_and_routed_to_metric_index(monkeypatch):
    sent = []
    monkeypatch.setattr(telemetry_dispatcher.dispatcher, "emit_hec", lambda ev, *a, **k: (sent.append(ev), telemetry_dispatcher.HecOutcome(True, "ok", telemetry_dispatcher.HEC_ACCEPTED, 200, None))[1])
    cfg = TelemetryTransportConfig(hec_url="https://127.0.0.1:8088/services/collector", hec_token="t", hec_index="idx_network_ops", hec_metric_index="cisco_mdt_metrics")
    entries, _ = SVC().prepare_sourcetype_entries("cisco_ios", "cisco:ios:mdt:metric", 3)
    for e in entries:
        res = telemetry_dispatcher.dispatcher.dispatch_log(e, cfg)
        assert res["hec"]["success"]
    assert len(sent) == 3
    for ev in sent:
        assert ev["event"] == "metric" and ev["index"] == "cisco_mdt_metrics" and ev["sourcetype"] == "cisco:ios:mdt:metric"
        metrics = {k: v for k, v in ev["fields"].items() if k.startswith("metric_name:")}
        assert metrics and all(isinstance(v, float) for v in metrics.values())
        assert isinstance(ev["time"], float)
