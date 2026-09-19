"""
NetSpout Native Splunk REST Handler
Registered under /services/netspout
Handles KV Store topology persistence, fault injection orchestration,
and OpenConfig MDT / gNMI telemetry requests directly within Splunk Enterprise.
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
    TopologyState, FaultScenarioType, FaultInjectionRequest, FaultRecoveryRequest
)
from fault_injection_engine import fault_engine
from gnmi_engine import yang_store, gnmi_server
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

            # Route requests
            # e.g., /services/netspout/topology, /services/netspout/faults/inject, etc.
            subpath = path.strip("/").split("/")[-1] if "/" in path else path

            if "topology" in path:
                if method == "GET":
                    return self._handle_get_topology(session_key)
                elif method == "POST":
                    return self._handle_post_topology(payload, session_key)

            elif "faults/inject" in path or subpath == "inject":
                return self._handle_fault_inject(payload)

            elif "faults/recover" in path or subpath == "recover":
                return self._handle_fault_recover(payload)

            elif "faults/history" in path or subpath == "history":
                return self._handle_fault_history()

            elif "gnmi/sample" in path or subpath == "sample":
                return self._handle_gnmi_sample(payload)

            elif "openconfig/tree" in path or subpath == "tree":
                node_id = query.get("node_id", payload.get("node_id", "node-core-1"))
                return self._handle_openconfig_tree(node_id)

            # Default /status
            return self._response(200, {
                "status": "online",
                "app": "netspout",
                "version": "2.0.0",
                "active_faults": len(fault_engine.active_faults),
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
        # Retrieve from KV store
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

        # Fallback to default in-memory active topology
        return self._response(200, {"nodes": [], "edges": []})

    def _handle_post_topology(self, payload, session_key):
        # Save to Splunk KV store
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
        record = fault_engine.inject_fault(req)
        return self._response(200, record.model_dump())

    def _handle_fault_recover(self, payload):
        req = FaultRecoveryRequest(**payload)
        result = fault_engine.recover_fault(req)
        return self._response(200, result)

    def _handle_fault_history(self):
        return self._response(200, {
            "active_faults": [f.model_dump() for f in fault_engine.active_faults.values()],
            "fault_history": [f.model_dump() for f in fault_engine.fault_history],
            "total_active": len(fault_engine.active_faults)
        })

    def _handle_gnmi_sample(self, payload):
        node_id = payload.get("node_id")
        count = int(payload.get("count", 1))
        emitted = gnmi_server.push_sample_metrics(node_id=node_id, sample_count=count)
        return self._response(200, {
            "status": "success",
            "sampled_nodes": len(gnmi_server.yang_store.nodes),
            "total_metrics_emitted": len(emitted),
            "target_index": "cisco_mdt_metrics",
            "metrics": emitted
        })

    def _handle_openconfig_tree(self, node_id):
        tree = yang_store.get_or_create_node(node_id)
        return self._response(200, {"node_id": node_id, "tree": tree})
