"""
Modeled scenario telemetry: a NetSpout-defined, clearly labeled schema for behavior that has no verifiable vendor-native log format here.

This is NOT vendor-authentic telemetry and is never presented as such. It exists so that a scenario whose specification is a state progression
(entities, stages, expected observations, a measured indicator) can be executed and investigated without inventing a vendor log syntax. The sourcetype
is `netspout:scenario:state`, every event carries `telemetry_model: MODELED_NETSPOUT_SCHEMA`, and a contract that uses it records that in its fidelity.

Event (JSON in _raw; the same facts are indexed fields on the HEC event: status=state, signature=message, action, src_ip, dest_ip):
  time, scenario_id, entity, component, state, previous_state, severity, message, telemetry_model
  and, only when the contract supplies a measurement: metric_name, metric_value, unit
"""
import json
from datetime import datetime, timezone
from typing import Optional

try:
    from netspout_core.models import LogEntry, Node
except ImportError:  # pragma: no cover
    try:
        from app.models import LogEntry, Node
    except ImportError:
        from models import LogEntry, Node

SOURCETYPE = "netspout:scenario:state"
HEALTHY = {"healthy", "normal", "restored", "ok", "compliant", "available", "nominal", "recovered", "complete", "stable"}
SEVERITIES = ("info", "notice", "warning", "error", "critical")


def format_modeled_state_event(device: Node, scenario_id: str, entity: str, component: str, state: str, previous_state: str, severity: str, message: str,
                               metric_name: Optional[str] = None, metric_value: Optional[float] = None, unit: Optional[str] = None) -> LogEntry:
    if severity not in SEVERITIES:
        raise ValueError("severity must be one of %s" % ", ".join(SEVERITIES))
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
    event = {"time": now, "scenario_id": scenario_id, "entity": entity, "component": component, "state": state, "previous_state": previous_state, "severity": severity,
             "message": message, "telemetry_model": "MODELED_NETSPOUT_SCHEMA"}
    if metric_name is not None and metric_value is not None:
        event.update(metric_name=metric_name, metric_value=metric_value, unit=unit or "")
    healthy = state.lower() in HEALTHY
    return LogEntry(timestamp=now, device_id=device.name, src_ip=device.ip_address, dest_ip=device.ip_address, protocol="n/a", duration="0ms",
                    action="allowed" if healthy else "alerted", signature=message[:160], status=state.lower(), raw_log=json.dumps(event, sort_keys=True),
                    node_type=device.type.value, node_id=device.id, vendor=device.vendor, sourcetype=SOURCETYPE)


FORMATTERS = {"format_modeled_state_event": format_modeled_state_event}
