"""
OpenConfig YANG Data Modeling & gNMI Model-Driven Telemetry (MDT) Engine
Implements RFC 7951 JSON-IETF & OpenConfig Schema Trees:
  - openconfig-interfaces: /interfaces/interface[name=...]/state
  - openconfig-network-instance: /network-instances/network-instance[name=...]/protocols/protocol/bgp
  - openconfig-rib-bgp: /network-instances/network-instance/ribs/rib/routes/route/state
  - openconfig-platform: /components/component[name=...]/state
  - openconfig-system: /system/state
Supports:
  - Multi-vendor dialects: Cisco IOS-XE/XR, Juniper Junos, Arista EOS
  - SAMPLE (periodic stream) and ON_CHANGE (event-driven trigger) subscriptions
  - Universal Multi-Pipeline payloads: Splunk HEC (cisco_mdt_metrics), OTel OTLP, Telegraf Influx, RFC 5424 Syslog
"""

import time
import json
import random
from typing import Dict, List, Any, Optional, Tuple

try:
    from app.models import (
        Node, Edge, TopologyState, OpenConfigSubscriptionMode, LogEntry
    )
except ImportError:
    from models import (
        Node, Edge, TopologyState, OpenConfigSubscriptionMode, LogEntry
    )


class OpenConfigYANGStore:
    """
    Maintains hierarchical OpenConfig YANG state tree for all active network nodes.
    Formats outputs with RFC 7951 JSON-IETF compliance.
    """
    def __init__(self):
        # node_id -> schema tree dict
        self._trees: Dict[str, Dict[str, Any]] = {}
        self._last_update: Dict[str, float] = {}

    def get_or_create_tree(self, node: Node) -> Dict[str, Any]:
        nid = node.id
        now_ts = int(time.time() * 1000)
        
        if nid not in self._trees:
            hw = node.hardware
            cpu_pct = hw.cpu_utilization_pct if hw else 18.5
            mem_pct = hw.memory_utilization_pct if hw else 34.0
            temp_c = hw.temperature_celsius if hw else 41.2
            vendor = (node.vendor or "cisco").lower()

            interfaces_list = []
            if hw and hw.interfaces:
                for intf in hw.interfaces:
                    interfaces_list.append({
                        "name": intf.name,
                        "config": {
                            "name": intf.name,
                            "type": "iana-if-type:ethernetCsmacd",
                            "enabled": (intf.admin_status.lower() == "up")
                        },
                        "state": {
                            "name": intf.name,
                            "type": "iana-if-type:ethernetCsmacd",
                            "admin-status": intf.admin_status.upper(),
                            "oper-status": intf.oper_status.upper(),
                            "mtu": intf.mtu,
                            "high-speed": intf.speed_mbps,
                            "counters": {
                                "in-octets": intf.in_octets or random.randint(15000000, 95000000),
                                "out-octets": intf.out_octets or random.randint(12000000, 88000000),
                                "in-unicast-pkts": random.randint(45000, 150000),
                                "out-unicast-pkts": random.randint(40000, 140000),
                                "in-errors": intf.in_errors,
                                "out-errors": intf.out_errors,
                                "in-discards": 0,
                                "out-discards": 0,
                                "carrier-transitions": 0
                            }
                        }
                    })
            else:
                default_if = node.interface or "GigabitEthernet0/0/1"
                interfaces_list.append({
                    "name": default_if,
                    "config": {
                        "name": default_if,
                        "type": "iana-if-type:ethernetCsmacd",
                        "enabled": True
                    },
                    "state": {
                        "name": default_if,
                        "type": "iana-if-type:ethernetCsmacd",
                        "admin-status": "UP",
                        "oper-status": "UP" if node.status != "degraded" else "DOWN",
                        "mtu": 1500,
                        "high-speed": 1000,
                        "counters": {
                            "in-octets": random.randint(15000000, 95000000),
                            "out-octets": random.randint(12000000, 88000000),
                            "in-unicast-pkts": random.randint(45000, 150000),
                            "out-unicast-pkts": random.randint(40000, 140000),
                            "in-errors": 0,
                            "out-errors": 0,
                            "in-discards": 0,
                            "out-discards": 0,
                            "carrier-transitions": 0
                        }
                    }
                })

            bgp_neighbors = []
            if any(v in vendor for v in ["cisco", "juniper", "arista", "nokia", "router", "core"]):
                bgp_neighbors.append({
                    "neighbor-address": "10.255.0.2",
                    "config": {
                        "neighbor-address": "10.255.0.2",
                        "peer-as": 65001,
                        "peer-group": "IBGP-CORE"
                    },
                    "state": {
                        "neighbor-address": "10.255.0.2",
                        "peer-as": 65001,
                        "session-state": "ESTABLISHED",
                        "prefixes": {
                            "received": 1420,
                            "installed": 1420,
                            "advertised": 850
                        },
                        "queues": {
                            "input-messages": 0,
                            "output-messages": 0
                        }
                    }
                })

            # Base RFC 7951 JSON-IETF Tree
            self._trees[nid] = {
                "openconfig-system:system": {
                    "config": {
                        "hostname": node.name or node.id,
                        "domain-name": "corp.internal"
                    },
                    "state": {
                        "hostname": node.name or node.id,
                        "domain-name": "corp.internal",
                        "boot-time": str(now_ts - 86400000),
                        "current-datetime": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                    }
                },
                "openconfig-platform:components": {
                    "component": [
                        {
                            "name": "Chassis-Main",
                            "state": {
                                "name": "Chassis-Main",
                                "type": "openconfig-platform-types:CHASSIS",
                                "temperature-celsius": temp_c
                            }
                        },
                        {
                            "name": "Routing-Processor-0",
                            "state": {
                                "name": "Routing-Processor-0",
                                "type": "openconfig-platform-types:CPU",
                                "cpu-utilization": cpu_pct,
                                "memory-utilization": mem_pct
                            }
                        }
                    ]
                },
                "openconfig-interfaces:interfaces": {
                    "interface": interfaces_list
                },
                "openconfig-network-instance:network-instances": {
                    "network-instance": [
                        {
                            "name": "default",
                            "protocols": {
                                "protocol": [
                                    {
                                        "identifier": "openconfig-policy-types:BGP",
                                        "name": "BGP",
                                        "openconfig-bgp:bgp": {
                                            "neighbors": {
                                                "neighbor": bgp_neighbors
                                            }
                                        }
                                    }
                                ]
                            },
                            "openconfig-rib-bgp:ribs": {
                                "rib": [
                                    {
                                        "name": "openconfig-rib-bgp:IPV4-UNICAST",
                                        "routes": {
                                            "route": [
                                                {
                                                    "prefix": "10.0.0.0/16",
                                                    "state": {
                                                        "prefix": "10.0.0.0/16",
                                                        "valid-route": True,
                                                        "best-path": True,
                                                        "next-hop": "10.255.0.2"
                                                    }
                                                }
                                            ]
                                        }
                                    }
                                ]
                            }
                        }
                    ]
                }
            }
            self._last_update[nid] = time.time()

        return self._trees[nid]

    def update_interface_oper_status(self, node_id: str, if_name: str, oper_status: str) -> Optional[Dict[str, Any]]:
        if node_id not in self._trees:
            return None
        tree = self._trees[node_id]
        interfaces = tree.get("openconfig-interfaces:interfaces", {}).get("interface", [])
        for intf in interfaces:
            if intf["name"] == if_name or if_name == "*":
                old_status = intf["state"]["oper-status"]
                intf["state"]["oper-status"] = oper_status.upper()
                if old_status != oper_status.upper():
                    intf["state"]["counters"]["carrier-transitions"] += 1
                return intf["state"]
        return None

    def update_bgp_session_state(self, node_id: str, peer_addr: str, new_state: str) -> Optional[Dict[str, Any]]:
        if node_id not in self._trees:
            return None
        tree = self._trees[node_id]
        net_insts = tree.get("openconfig-network-instance:network-instances", {}).get("network-instance", [])
        for ni in net_insts:
            protos = ni.get("protocols", {}).get("protocol", [])
            for p in protos:
                bgp = p.get("openconfig-bgp:bgp", {})
                neighbors = bgp.get("neighbors", {}).get("neighbor", [])
                for nbr in neighbors:
                    if nbr["neighbor-address"] == peer_addr or peer_addr == "*":
                        nbr["state"]["session-state"] = new_state.upper()
                        if new_state.upper() == "IDLE":
                            nbr["state"]["prefixes"]["installed"] = 0
                        elif new_state.upper() == "ESTABLISHED":
                            nbr["state"]["prefixes"]["installed"] = nbr["state"]["prefixes"]["received"]
                        return nbr["state"]
        return None

    def update_platform_utilization(self, node_id: str, cpu_pct: float, mem_pct: float):
        if node_id not in self._trees:
            return
        comps = self._trees[node_id].get("openconfig-platform:components", {}).get("component", [])
        for c in comps:
            if "Routing-Processor" in c["name"]:
                c["state"]["cpu-utilization"] = round(cpu_pct, 1)
                c["state"]["memory-utilization"] = round(mem_pct, 1)

    def to_rfc7951_json(self, node_id: str) -> str:
        """
        Serialize node's YANG tree as strict RFC 7951 JSON-IETF string.
        """
        if node_id in self._trees:
            return json.dumps(self._trees[node_id], indent=2)
        return "{}"


class MockGNMIServer:
    """
    Carrier-grade gNMI/gRPC Streaming Telemetry Service.
    Supports SAMPLE mode (cadence-based push) and ON_CHANGE mode (event-driven push).
    Formats Splunk HEC metric payloads, OTel OTLP, Telegraf Influx, and RFC 5424 Syslog.
    """
    def __init__(self, yang_store: OpenConfigYANGStore):
        self.yang_store = yang_store
        self.active_subscriptions: List[Dict[str, Any]] = [
            {"path": "openconfig-interfaces:interfaces/interface/state/counters", "mode": OpenConfigSubscriptionMode.SAMPLE, "interval_sec": 10},
            {"path": "openconfig-platform:components/component/state", "mode": OpenConfigSubscriptionMode.SAMPLE, "interval_sec": 5},
            {"path": "openconfig-network-instance:network-instances/network-instance/protocols/protocol/bgp/neighbors/neighbor/state", "mode": OpenConfigSubscriptionMode.ON_CHANGE},
            {"path": "openconfig-interfaces:interfaces/interface/state/oper-status", "mode": OpenConfigSubscriptionMode.ON_CHANGE}
        ]

    def generate_sample_telemetry(self, node: Node) -> List[Dict[str, Any]]:
        """
        Generates periodic SAMPLE notifications formatted for Splunk HEC cisco_mdt_metrics.
        """
        tree = self.yang_store.get_or_create_tree(node)
        now = time.time()
        dev_name = node.name or node.id
        results = []

        # 1. Interface counters
        interfaces = tree.get("openconfig-interfaces:interfaces", {}).get("interface", [])
        for intf in interfaces:
            istate = intf.get("state", {})
            counters = istate.get("counters", {})
            counters["in-octets"] += random.randint(15000, 95000)
            counters["out-octets"] += random.randint(12000, 85000)
            counters["in-unicast-pkts"] += random.randint(20, 120)
            counters["out-unicast-pkts"] += random.randint(18, 110)
            
            payload = {
                "time": now,
                "event": "metric",
                "source": "cisco:ios:mdt",
                "sourcetype": "cisco:ios:mdt:metric",
                "host": f"{dev_name}.corp.internal",
                "index": "cisco_mdt_metrics",
                "fields": {
                    "metric_name:interface.octets.in": float(counters["in-octets"]),
                    "metric_name:interface.octets.out": float(counters["out-octets"]),
                    "metric_name:interface.packets.in": float(counters["in-unicast-pkts"]),
                    "metric_name:interface.packets.out": float(counters["out-unicast-pkts"]),
                    "metric_name:interface.errors.in": float(counters["in-errors"]),
                    "metric_name:interface.errors.out": float(counters["out-errors"]),
                    "metric_name:carrier.transitions": float(counters["carrier-transitions"]),
                    "_value": float(counters["in-octets"]),
                    "interface": intf["name"],
                    "oper_status": istate.get("oper-status", "UP"),
                    "subscription_mode": "SAMPLE",
                    "openconfig_path": f"/interfaces/interface[name={intf['name']}]/state/counters",
                    "device": dev_name,
                    "vendor": node.vendor or "cisco"
                }
            }
            results.append(payload)

        # 2. Platform CPU / Memory gauges
        components = tree.get("openconfig-platform:components", {}).get("component", [])
        for comp in components:
            cstate = comp.get("state", {})
            if "cpu-utilization" in cstate:
                cpu = cstate["cpu-utilization"]
                mem = cstate["memory-utilization"]
                payload = {
                    "time": now,
                    "event": "metric",
                    "source": "cisco:ios:mdt",
                    "sourcetype": "cisco:ios:mdt:metric",
                    "host": f"{dev_name}.corp.internal",
                    "index": "cisco_mdt_metrics",
                    "fields": {
                        "metric_name:cpu.utilization": float(cpu),
                        "metric_name:memory.utilization": float(mem),
                        "_value": float(cpu),
                        "component": comp["name"],
                        "subscription_mode": "SAMPLE",
                        "openconfig_path": f"/components/component[name={comp['name']}]/state",
                        "device": dev_name,
                        "vendor": node.vendor or "cisco"
                    }
                }
                results.append(payload)

        return results

    def emit_on_change_event(
        self,
        node: Node,
        path: str,
        changed_field: str,
        old_value: Any,
        new_value: Any,
        numeric_metric_name: Optional[str] = None,
        numeric_val: float = 1.0
    ) -> Dict[str, Any]:
        """
        Generates an ON_CHANGE reactive gNMI notification triggered by a state change.
        """
        dev_name = node.name or node.id
        now = time.time()
        metric_key = numeric_metric_name or f"gnmi.on_change.{changed_field.replace('-', '_')}"

        payload = {
            "time": now,
            "event": "metric",
            "source": "cisco:ios:mdt",
            "sourcetype": "cisco:ios:mdt:metric",
            "host": f"{dev_name}.corp.internal",
            "index": "cisco_mdt_metrics",
            "fields": {
                f"metric_name:{metric_key}": float(numeric_val),
                "_value": float(numeric_val),
                "openconfig_path": path,
                "changed_field": changed_field,
                "old_val": str(old_value),
                "new_val": str(new_value),
                "subscription_mode": "ON_CHANGE",
                "device": dev_name,
                "vendor": node.vendor or "cisco"
            }
        }
        return payload

    def to_otel_metric_payload(self, metric_event: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format OpenConfig MDT event as OpenTelemetry OTLP JSON /v1/metrics payload.
        """
        fields = metric_event.get("fields", {})
        host = metric_event.get("host", "unknown-router")
        now_nano = int(metric_event.get("time", time.time()) * 1e9)

        data_points = []
        for k, v in fields.items():
            if k.startswith("metric_name:") and isinstance(v, (int, float)):
                m_name = k.replace("metric_name:", "")
                data_points.append({
                    "name": m_name,
                    "gauge": {
                        "dataPoints": [{
                            "asDouble": float(v),
                            "timeUnixNano": str(now_nano),
                            "attributes": [
                                {"key": "host.name", "value": {"stringValue": host}},
                                {"key": "service.name", "value": {"stringValue": "openconfig-mdt"}},
                                {"key": "openconfig.path", "value": {"stringValue": fields.get("openconfig_path", "")}}
                            ]
                        }]
                    }
                })

        return {
            "resourceMetrics": [{
                "resource": {
                    "attributes": [
                        {"key": "host.name", "value": {"stringValue": host}},
                        {"key": "service.name", "value": {"stringValue": "openconfig-mdt"}}
                    ]
                },
                "scopeMetrics": [{
                    "scope": {"name": "netspout.openconfig", "version": "2.0.0"},
                    "metrics": data_points
                }]
            }]
        }

    def to_telegraf_influx_line(self, metric_event: Dict[str, Any]) -> str:
        """
        Format OpenConfig MDT event as Influx Line Protocol for Telegraf.
        """
        fields = metric_event.get("fields", {})
        host = metric_event.get("host", "unknown-router")
        timestamp_nano = int(metric_event.get("time", time.time()) * 1e9)

        tags = [f"host={host}", "source=openconfig_mdt"]
        if "device" in fields:
            tags.append(f"device={fields['device']}")
        if "vendor" in fields:
            tags.append(f"vendor={fields['vendor']}")
        if "interface" in fields:
            tags.append(f"interface={fields['interface']}")
        if "component" in fields:
            tags.append(f"component={fields['component']}")

        field_assignments = []
        for k, v in fields.items():
            if k.startswith("metric_name:") and isinstance(v, (int, float)):
                clean_k = k.replace("metric_name:", "").replace(".", "_")
                field_assignments.append(f"{clean_k}={float(v)}")

        if not field_assignments:
            field_assignments.append("value=1.0")

        return f"openconfig_telemetry,{','.join(tags)} {','.join(field_assignments)} {timestamp_nano}"

    def to_rfc5424_syslog_mdt(self, metric_event: Dict[str, Any]) -> str:
        """
        Format OpenConfig notification as RFC 5424 structured syslog message.
        """
        fields = metric_event.get("fields", {})
        host = metric_event.get("host", "unknown-router").split(".")[0]
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(metric_event.get("time", time.time())))
        
        path = fields.get("openconfig_path", "/openconfig/telemetry")
        sd = f'[openconfig@41888 xpath="{path}" mode="{fields.get("subscription_mode", "SAMPLE")}"]'
        
        metric_summary = ", ".join(
            f"{k.replace('metric_name:', '')}={v}"
            for k, v in fields.items() if k.startswith("metric_name:")
        )
        msg = f"gNMI MDT Notification: {metric_summary}"
        return f"<134>1 {now_iso} {host} gnmi-telemetry - - {sd} {msg}"


# Global singleton YANG store & gNMI Server
yang_store = OpenConfigYANGStore()
gnmi_server = MockGNMIServer(yang_store)
