"""
NetSpout Native Splunk REST Handler
Registered under /services/netspout
Handles:
  - KV Store topology persistence
  - Dynamic Fault Injection & Cascades
  - OpenConfig YANG & MDT Telemetry (RFC 7951 JSON-IETF)
  - SC4SNMP 300+ MIB Catalog & Trap Dispatcher
  - Universal Multi-Pipeline Testing (Splunk HEC, OTel, Telegraf, Syslog)
"""

import os
import sys
import json
import time
import urllib.request
import urllib.error

# Add current directory to path for local module imports
BIN_DIR = os.path.dirname(os.path.abspath(__file__))
if BIN_DIR not in sys.path:
    sys.path.insert(0, BIN_DIR)

try:
    from splunk.persistconn.application import PersistentServerConnectionApplication
except ImportError:
    class PersistentServerConnectionApplication:
        pass

from models import (
    TopologyState, FaultScenarioType, FaultInjectionRequest, FaultRecoveryRequest,
    SNMPTrapTriggerRequest, SNMPPollRequest, PipelineTestRequest, TelemetryTransportConfig
)
from fault_injection_engine import fault_engine
from gnmi_engine import yang_store, gnmi_server
from snmp_engine import snmp_engine
from telemetry_dispatcher import dispatcher
from graph_engine import TopologyGraph

class NetSpoutRestHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line=None, command_arg=None):
        super(NetSpoutRestHandler, self).__init__()

    def handle(self, in_string):
        try:
            request = json.loads(in_string)
            method = request.get("method", "GET").upper()
            path = request.get("path", "")
            session_key = request.get("session", {}).get("authtoken", "")
            query = request.get("query", {})
            payload_str = request.get("payload", "{}")
            payload = json.loads(payload_str) if payload_str else {}

            subpath = path.strip("/").split("/")[-1] if "/" in path else path

            # 1. Topology Persistence (KV Store)
            if "topology" in path:
                if method == "GET":
                    return self._handle_get_topology(session_key)
                elif method == "POST":
                    return self._handle_post_topology(payload, session_key)

            # 2. Fault Injection & Recovery
            elif "faults/inject" in path or subpath == "inject":
                return self._handle_fault_inject(payload)

            elif "faults/recover" in path or subpath == "recover":
                return self._handle_fault_recover(payload)

            elif "faults/history" in path or subpath == "history":
                return self._handle_fault_history()

            # 3. OpenConfig & gNMI Telemetry
            elif "gnmi/sample" in path or subpath == "sample":
                return self._handle_gnmi_sample(payload)

            elif "openconfig/tree" in path or subpath == "tree":
                node_id = query.get("node_id", payload.get("node_id", "node-core-1"))
                return self._handle_openconfig_tree(node_id)

            # 4. SC4SNMP MIBs & Traps
            elif "snmp/mibs" in path or subpath == "mibs":
                vendor = query.get("vendor")
                module = query.get("module")
                search = query.get("search")
                return self._handle_snmp_mibs(vendor, module, search)

            elif "snmp/trap" in path or subpath == "trap":
                return self._handle_snmp_trap(payload)

            elif "snmp/poll" in path or subpath == "poll":
                return self._handle_snmp_poll(payload)

            # 5. Multi-Pipeline Validation
            elif "pipelines/test" in path or subpath == "test":
                return self._handle_pipeline_test(payload)

            elif "pipelines/config" in path or subpath == "config":
                return self._handle_pipeline_config(method, payload)

            # 6. Splunkbase Vendor Directory & Official Documentation Audit
            elif "vendor_catalog" in path or subpath == "vendors":
                from vendor_catalog import list_all_vendors, get_vendor_by_id
                vendor_id = query.get("id")
                if vendor_id:
                    v = get_vendor_by_id(vendor_id)
                    return self._response(200, {"vendor": v} if v else {"error": "Vendor not found"})
                return self._response(200, {"vendors": list_all_vendors(), "count": len(list_all_vendors())})

            # 7. Interactive SPL Query Playground
            elif "spl_query" in path or subpath == "spl_query" or subpath == "query":
                from spl_engine import spl_engine
                q_str = payload.get("query", query.get("q", "*"))
                events_in = payload.get("events", [])
                res = spl_engine.execute(q_str, events_in)
                return self._response(200, res)

            # 8. NOC & SOC Telemetry Metrics & Frequency Blueprints
            elif "metrics" in path or subpath == "metrics":
                from noc_soc_metrics import metric_engine
                if "blueprints" in path or subpath == "blueprints":
                    return self._response(200, metric_engine.get_frequency_blueprints())
                is_deg = query.get("is_degraded", "false").lower() == "true"
                is_atk = query.get("is_under_attack", "false").lower() == "true"
                return self._response(200, {
                    "noc": metric_engine.generate_noc_metrics(is_degraded=is_deg),
                    "soc": metric_engine.generate_soc_metrics(is_under_attack=is_atk)
                })

            # 9. Use Case Repository & Test Harness
            elif "use_cases" in path or subpath == "use_cases":
                from use_case_repo import use_case_harness
                uc_id = query.get("id", payload.get("use_case_id"))
                if method == "POST" or "test" in path:
                    target_id = uc_id or payload.get("id", "uc-noc-01-bgp-flap")
                    test_res = use_case_harness.run_use_case_test(target_id, events=payload.get("events", []))
                    return self._response(200, test_res)
                return self._response(200, {"use_cases": use_case_harness.list_use_cases(), "count": len(use_case_harness.list_use_cases())})

            # Default /status
            return self._response(200, {
                "status": "online",
                "app": "netspout",
                "version": "2.0.0",
                "active_faults": len(fault_engine.active_faults),
                "mibs_catalog_count": len(snmp_engine.list_mibs()),
                "pipeline_stats": dispatcher.stats,
                "timestamp": time.time()
            })

        except Exception as e:
            return self._response(500, {"error": str(e)})

    def _response(self, status_code, payload_dict):
        return {
            "status": status_code,
            "headers": {"Content-Type": "application/json"},
            "payload": json.dumps(payload_dict)
        }

    def _handle_get_topology(self, session_key):
        url = "http://127.0.0.1:8089/servicesNS/nobody/netspout/storage/collections/data/netspout_topologies"
        headers = {"Authorization": f"Splunk {session_key}", "Content-Type": "application/json"}
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                items = json.loads(response.read().decode())
                if items and len(items) > 0:
                    latest = items[-1]
                    top_data = json.loads(latest.get("topology_json", "{}"))
                    return self._response(200, top_data)
        except Exception:
            pass
        return self._response(200, {"nodes": [], "edges": []})

    def _handle_post_topology(self, payload, session_key):
        url = "http://127.0.0.1:8089/servicesNS/nobody/netspout/storage/collections/data/netspout_topologies"
        headers = {"Authorization": f"Splunk {session_key}", "Content-Type": "application/json"}
        record = {
            "name": payload.get("name", "Active Topology"),
            "description": "User modified topology via NetSpout Canvas",
            "ecosystem": payload.get("ecosystem", "mixed_vendor"),
            "updated_at": int(time.time()),
            "topology_json": json.dumps(payload)
        }
        req = urllib.request.Request(url, data=json.dumps(record).encode(), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                result = json.loads(response.read().decode())
                return self._response(200, {"status": "saved_to_kv_store", "key": result.get("_key")})
        except Exception as e:
            return self._response(200, {"status": "in_memory_only", "warning": str(e)})

    def _handle_fault_inject(self, payload):
        req = FaultInjectionRequest(**payload)
        top = TopologyState(**payload.get("topology", {})) if "topology" in payload else TopologyState()
        record, logs, metrics, traps = fault_engine.inject_fault(top, req)
        return self._response(200, {
            "status": "success",
            "record": record.model_dump(),
            "cascades_count": len(logs) + len(metrics) + len(traps),
            "traps_emitted": len(traps)
        })

    def _handle_fault_recover(self, payload):
        req = FaultRecoveryRequest(**payload)
        top = TopologyState(**payload.get("topology", {})) if "topology" in payload else TopologyState()
        result = fault_engine.recover_fault(top, req)
        return self._response(200, result)

    def _handle_fault_history(self):
        return self._response(200, {
            "active_faults": [f.model_dump() for f in fault_engine.active_faults.values()],
            "fault_history": [f.model_dump() for f in fault_engine.fault_history],
            "total_active": len(fault_engine.active_faults)
        })

    def _handle_gnmi_sample(self, payload):
        from models import Node, NodeType
        node_id = payload.get("node_id", "router-core")
        node = Node(id=node_id, name=node_id, type=NodeType.ROUTER, x=0, y=0, vendor=payload.get("vendor", "cisco"))
        metrics = gnmi_server.generate_sample_telemetry(node)
        transport = TelemetryTransportConfig(**payload.get("transport", {})) if "transport" in payload else None
        if transport:
            for m in metrics:
                dispatcher.dispatch_openconfig(m, transport)
        return self._response(200, {
            "status": "success",
            "node_id": node_id,
            "metrics_count": len(metrics),
            "metrics": metrics
        })

    def _handle_openconfig_tree(self, node_id):
        from models import Node, NodeType
        node = Node(id=node_id, name=node_id, type=NodeType.ROUTER, x=0, y=0)
        tree = yang_store.get_or_create_tree(node)
        return self._response(200, {"node_id": node_id, "tree": tree})

    def _handle_snmp_mibs(self, vendor, module, search):
        mibs = snmp_engine.list_mibs(vendor=vendor, module=module, search=search)
        return self._response(200, {
            "status": "success",
            "total_count": len(mibs),
            "mibs": [m.model_dump() for m in mibs]
        })

    def _handle_snmp_trap(self, payload):
        from models import Node, NodeType
        trap_name = payload.get("trap_name", "linkDown")
        host = payload.get("host", "core-router-01")
        node = Node(id=host, name=host, type=NodeType.ROUTER, x=0, y=0, vendor=payload.get("vendor", "cisco"))
        trap = snmp_engine.generate_trap(trap_name, node, payload.get("varbind_overrides"))
        transport = TelemetryTransportConfig(**payload.get("transport", {})) if "transport" in payload else None
        res = dispatcher.dispatch_snmp_trap(trap, transport)
        return self._response(200, {
            "status": "success",
            "trap": trap.model_dump(),
            "dispatch_results": res
        })

    def _handle_snmp_poll(self, payload):
        from models import Node, NodeType
        module = payload.get("mib_module", "IF-MIB")
        host = payload.get("host", "core-switch-01")
        node = Node(id=host, name=host, type=NodeType.SWITCH, x=0, y=0, vendor=payload.get("vendor", "cisco"))
        metrics = snmp_engine.simulate_snmp_poll(node, module=module)
        transport = TelemetryTransportConfig(**payload.get("transport", {})) if "transport" in payload else None
        if transport:
            for m in metrics:
                dispatcher.dispatch_snmp_metric(m, transport)
        return self._response(200, {
            "status": "success",
            "polled_module": module,
            "metrics_count": len(metrics),
            "metrics": metrics[:10]
        })

    def _handle_pipeline_test(self, payload):
        pipeline = payload.get("pipeline", "hec")
        cfg = TelemetryTransportConfig(**payload.get("config", {}))
        ok, msg = dispatcher.test_pipeline(pipeline, cfg)
        return self._response(200, {
            "pipeline": pipeline,
            "success": ok,
            "message": msg
        })

    def _handle_pipeline_config(self, method, payload):
        return self._response(200, {
            "status": "success",
            "stats": dispatcher.stats
        })
