"""
OpenConfig YANG Data Modeling & Mock gNMI Telemetry Engine
Implements RFC/OpenConfig schema trees:
  - openconfig-interfaces: /interfaces/interface[name=...]/state
  - openconfig-bgp: /bgp/neighbors/neighbor[neighbor-address=...]/state
  - openconfig-platform: /components/component[name=...]/state
  - openconfig-system: /system/state
Supports SAMPLE (periodic stream) and ON_CHANGE (event-driven trigger) subscription modes.
Formats compliant Splunk HEC metric payloads for cisco_mdt_metrics.
"""

import time
import json
import random
from typing import Dict, List, Any, Optional, Tuple
from app.models import Node, Edge, TopologyState, OpenConfigSubscriptionMode, LogEntry


class OpenConfigYANGStore:
    """
    Maintains hierarchical OpenConfig YANG state tree for all active network nodes.
    """
    def __init__(self):
        # node_id -> schema tree dict
        self._trees: Dict[str, Dict[str, Any]] = {}
        self._last_update: Dict[str, float] = {}

    def get_or_create_tree(self, node: Node) -> Dict[str, Any]:
        nid = node.id
        now_ts = int(time.time() * 1000)
        
        if nid not in self._trees:
            # Construct standard baseline OpenConfig tree
            hw = node.hardware
            cpu_pct = hw.cpu_utilization_pct if hw else 18.5
            mem_pct = hw.memory_utilization_pct if hw else 34.0
            temp_c = hw.temperature_celsius if hw else 41.2

            interfaces_list = []
            if hw and hw.interfaces:
                for intf in hw.interfaces:
                    interfaces_list.append({
                        "name": intf.name,
                        "config": {"name": intf.name, "type": "iana-if-type:ethernetCsmacd", "enabled": True},
                        "state": {
                            "name": intf.name,
                            "type": "iana-if-type:ethernetCsmacd",
                            "admin-status": intf.admin_status.upper(),
                            "oper-status": intf.oper_status.upper(),
                            "mtu": intf.mtu,
                            "speed": f"SPEED_{intf.speed_mbps}MB",
                            "counters": {
                                "in-octets": intf.in_octets or random.randint(10000000, 99000000),
                                "out-octets": intf.out_octets or random.randint(8000000, 85000000),
                                "in-errors": intf.in_errors,
                                "out-errors": intf.out_errors,
                                "carrier-transitions": 0
                            }
                        }
                    })
            else:
                default_if = node.interface or "GigabitEthernet0/0/1"
                interfaces_list.append({
                    "name": default_if,
                    "config": {"name": default_if, "type": "iana-if-type:ethernetCsmacd", "enabled": True},
                    "state": {
                        "name": default_if,
                        "type": "iana-if-type:ethernetCsmacd",
                        "admin-status": "UP",
                        "oper-status": "UP" if node.status != "degraded" else "DOWN",
                        "mtu": 1500,
                        "speed": "SPEED_1000MB",
                        "counters": {
                            "in-octets": random.randint(12000000, 88000000),
                            "out-octets": random.randint(11000000, 75000000),
                            "in-errors": 0,
                            "out-errors": 0,
                            "carrier-transitions": 0
                        }
                    }
                })

            bgp_neighbors = []
            if "cisco" in node.vendor or "juniper" in node.vendor or "arista" in node.vendor or "nokia" in node.vendor:
                bgp_neighbors.append({
                    "neighbor-address": "10.255.0.2",
                    "config": {"neighbor-address": "10.255.0.2", "peer-as": 65001, "peer-group": "IBGP-CORE"},
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

            self._trees[nid] = {
                "openconfig-system:system": {
                    "config": {
                        "hostname": node.name or node.id,
                        "domain-name": "corp.internal"
                    },
                    "state": {
                        "hostname": node.name or node.id,
                        "domain-name": "corp.internal",
                        "boot-time": now_ts - 86400000,
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
                "openconfig-bgp:bgp": {
                    "neighbors": {
                        "neighbor": bgp_neighbors
                    }
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
        neighbors = tree.get("openconfig-bgp:bgp", {}).get("neighbors", {}).get("neighbor", [])
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


class MockGNMIServer:
    """
    Emulates a carrier-grade gNMI/gRPC Streaming Telemetry Service.
    Supports SAMPLE mode (cadence-based push) and ON_CHANGE mode (event-driven push).
    Generates Splunk HEC metric payloads directed to cisco_mdt_metrics.
    """
    def __init__(self, yang_store: OpenConfigYANGStore):
        self.yang_store = yang_store
        self.active_subscriptions: List[Dict[str, Any]] = [
            {"path": "openconfig-interfaces:interfaces/interface/state/counters", "mode": OpenConfigSubscriptionMode.SAMPLE, "interval_sec": 10},
            {"path": "openconfig-platform:components/component/state", "mode": OpenConfigSubscriptionMode.SAMPLE, "interval_sec": 5},
            {"path": "openconfig-bgp:bgp/neighbors/neighbor/state", "mode": OpenConfigSubscriptionMode.ON_CHANGE},
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
            # advance counters realistically
            counters["in-octets"] += random.randint(12000, 95000)
            counters["out-octets"] += random.randint(10000, 85000)
            
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
                    "metric_name:interface.errors.in": float(counters["in-errors"]),
                    "metric_name:interface.errors.out": float(counters["out-errors"]),
                    "metric_name:carrier.transitions": float(counters["carrier-transitions"]),
                    "_value": float(counters["in-octets"]),
                    "interface": intf["name"],
                    "oper_status": istate.get("oper-status", "UP"),
                    "subscription_mode": "SAMPLE",
                    "openconfig_path": f"/interfaces/interface[name={intf["name"]}]/state/counters",
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
                        "openconfig_path": f"/components/component[name={comp["name"]}]/state",
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
        metric_key = numeric_metric_name or f"gnmi.on_change.{changed_field.replace("-", "_")}"

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


# Global singleton YANG store & gNMI Server
yang_store = OpenConfigYANGStore()
gnmi_server = MockGNMIServer(yang_store)
