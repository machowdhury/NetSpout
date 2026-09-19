"""
Dynamic Failure & Fault Injection Engine
Orchestrates multi-stage network anomalies and generates chronologically ordered,
multi-device log cascades across Splunk HEC (events & metrics) and Syslog (UDP/TCP 514).
"""

import time
import uuid
import random
from typing import Dict, List, Any, Optional, Tuple
from app.models import (
    TopologyState, Node, Edge, NodeType, LogEntry,
    FaultScenarioType, FaultInjectionRequest, FaultEventRecord, FaultRecoveryRequest
)
from app.graph_engine import TopologyGraph
from app.log_engine import SplunkLogEngine
from app.gnmi_engine import yang_store, gnmi_server
from app.telemetry_dispatcher import dispatcher


class FaultInjectionEngine:
    """
    Orchestrates physical, protocol, and security failure injections.
    Produces authentic multi-device cascading timelines to test SIEM correlation rules.
    """
    def __init__(self):
        self.active_faults: Dict[str, FaultEventRecord] = {}
        self.fault_history: List[FaultEventRecord] = []

    def inject_fault(
        self,
        topology: TopologyState,
        request: FaultInjectionRequest
    ) -> Tuple[FaultEventRecord, List[LogEntry], List[Dict[str, Any]]]:
        """
        Executes fault injection and returns:
          1. FaultEventRecord tracking the failure
          2. Chronologically ordered LogEntry cascade
          3. gNMI metric payloads for cisco_mdt_metrics
        """
        fault_id = f"flt-{uuid.uuid4().hex[:8]}"
        graph = TopologyGraph(topology)
        logs: List[LogEntry] = []
        metrics: List[Dict[str, Any]] = []
        affected_nodes: List[str] = []
        affected_edges: List[str] = []
        desc = ""

        # =========================================================================
        # 1. PHYSICAL LINK SEVER (LINK_CUT)
        # =========================================================================
        if request.scenario_type == FaultScenarioType.LINK_CUT:
            target_edge = None
            if request.target_edge_id:
                target_edge = next((e for e in topology.edges if e.id == request.target_edge_id), None)
            if not target_edge and topology.edges:
                target_edge = topology.edges[0]

            if not target_edge:
                raise ValueError("No edge available to cut")

            affected_edges.append(target_edge.id)
            affected_nodes.extend([target_edge.source, target_edge.target])
            desc = f"Severed physical fiber link between {target_edge.source} and {target_edge.target}"

            # Step 1: Propagate failure across graph and OpenConfig state
            graph.propagate_link_failure(target_edge.id)

            node_a = graph.nodes_by_id.get(target_edge.source)
            node_b = graph.nodes_by_id.get(target_edge.target)

            now_iso = SplunkLogEngine.current_timestamp_iso()
            now_syslog = SplunkLogEngine.current_timestamp_syslog()

            # Cascade Event 1: Port A Carrier Loss Syslog
            logs.append(LogEntry(
                timestamp=now_iso,
                device_id=node_a.name if node_a else target_edge.source,
                src_ip=node_a.ip_address if node_a else "10.0.1.1",
                dest_ip="255.255.255.255",
                protocol="ETHERNET",
                duration="0ms",
                action="alerted",
                signature="Physical Layer Carrier Loss (LOS)",
                status="degraded",
                raw_log=f"<187>{now_syslog} {node_a.name if node_a else target_edge.source} %LINK-3-UPDOWN: Interface {target_edge.source_port}, changed state to down",
                node_type=node_a.type.value if node_a else "switch",
                node_id=target_edge.source,
                vendor=node_a.vendor if node_a else "cisco",
                sourcetype="cisco:ios:syslog"
            ))

            # Cascade Event 2: Port B Carrier Loss Syslog
            logs.append(LogEntry(
                timestamp=now_iso,
                device_id=node_b.name if node_b else target_edge.target,
                src_ip=node_b.ip_address if node_b else "10.0.1.2",
                dest_ip="255.255.255.255",
                protocol="ETHERNET",
                duration="0ms",
                action="alerted",
                signature="Physical Layer Carrier Loss (LOS)",
                status="degraded",
                raw_log=f"<187>{now_syslog} {node_b.name if node_b else target_edge.target} %LINK-3-UPDOWN: Interface {target_edge.target_port}, changed state to down",
                node_type=node_b.type.value if node_b else "switch",
                node_id=target_edge.target,
                vendor=node_b.vendor if node_b else "cisco",
                sourcetype="cisco:ios:syslog"
            ))

            # Cascade Event 3: SNMP linkDown Traps
            if node_a:
                logs.append(SplunkLogEngine.format_snmp_trap(node_a, trap_type="linkDown", interface_name=target_edge.source_port, action="alerted", status="degraded"))
            if node_b:
                logs.append(SplunkLogEngine.format_snmp_trap(node_b, trap_type="linkDown", interface_name=target_edge.target_port, action="alerted", status="degraded"))

            # Cascade Event 4: gNMI ON_CHANGE Notifications to cisco_mdt_metrics
            if node_a:
                metrics.append(gnmi_server.emit_on_change_event(
                    node=node_a,
                    path=f"/interfaces/interface[name={target_edge.source_port}]/state/oper-status",
                    changed_field="oper-status",
                    old_value="UP",
                    new_value="DOWN",
                    numeric_metric_name="interface.carrier.transitions",
                    numeric_val=1.0
                ))
            if node_b:
                metrics.append(gnmi_server.emit_on_change_event(
                    node=node_b,
                    path=f"/interfaces/interface[name={target_edge.target_port}]/state/oper-status",
                    changed_field="oper-status",
                    old_value="UP",
                    new_value="DOWN",
                    numeric_metric_name="interface.carrier.transitions",
                    numeric_val=1.0
                ))

            # Cascade Event 5: Routing Protocol Flap (BGP Hold Timer Expired)
            if node_a and node_b:
                logs.append(LogEntry(
                    timestamp=now_iso,
                    device_id=node_a.name,
                    src_ip=node_a.ip_address,
                    dest_ip=node_b.ip_address,
                    protocol="BGP",
                    duration="1ms",
                    action="dropped",
                    signature="BGP Neighbor Adjacency Lost",
                    status="degraded",
                    raw_log=f"<189>{now_syslog} {node_a.name} %BGP-5-ADJCHANGE: neighbor {node_b.ip_address} Down (Interface flap / HoldTimer Expired)",
                    node_type=node_a.type.value,
                    node_id=node_a.id,
                    vendor=node_a.vendor,
                    sourcetype="cisco:ios:syslog"
                ))
                metrics.append(gnmi_server.emit_on_change_event(
                    node=node_a,
                    path=f"/bgp/neighbors/neighbor[neighbor-address={node_b.ip_address}]/state/session-state",
                    changed_field="session-state",
                    old_value="ESTABLISHED",
                    new_value="IDLE",
                    numeric_metric_name="bgp.prefixes.received",
                    numeric_val=0.0
                ))

        # =========================================================================
        # 2. HARDWARE / RESOURCE EXHAUSTION
        # =========================================================================
        elif request.scenario_type == FaultScenarioType.HARDWARE_EXHAUSTION:
            target_node = None
            if request.target_node_id:
                target_node = graph.nodes_by_id.get(request.target_node_id)
            if not target_node and topology.nodes:
                target_node = next((n for n in topology.nodes if n.type in (NodeType.ROUTER, NodeType.FIREWALL, NodeType.SWITCH)), topology.nodes[0])

            if not target_node:
                raise ValueError("No node available for hardware exhaustion")

            affected_nodes.append(target_node.id)
            desc = f"Triggered CPU/Memory saturation on {target_node.name} (98.4% CPU, 95.2% RAM)"
            graph.propagate_node_exhaustion(target_node.id, cpu_pct=98.4, mem_pct=95.2)

            now_iso = SplunkLogEngine.current_timestamp_iso()
            now_syslog = SplunkLogEngine.current_timestamp_syslog()

            logs.append(LogEntry(
                timestamp=now_iso,
                device_id=target_node.name,
                src_ip=target_node.ip_address,
                dest_ip="10.255.255.255",
                protocol="SNMP/PLATFORM",
                duration="0ms",
                action="alerted",
                signature="Control Plane CPU Exhaustion (>95%)",
                status="degraded",
                raw_log=f"<186>{now_syslog} {target_node.name} %SYS-2-CPU_RISING_THRESHOLD: CPU utilization 98.4% exceeds rising threshold (90%) for 60 seconds",
                node_type=target_node.type.value,
                node_id=target_node.id,
                vendor=target_node.vendor,
                sourcetype="cisco:ios:syslog"
            ))

            # Emit gNMI platform metric spike
            metrics.append({
                "time": time.time(),
                "event": "metric",
                "source": "cisco:ios:mdt",
                "sourcetype": "cisco:ios:mdt:metric",
                "host": f"{target_node.name}.corp.internal",
                "index": "cisco_mdt_metrics",
                "fields": {
                    "metric_name:cpu.utilization": 98.4,
                    "metric_name:memory.utilization": 95.2,
                    "metric_name:buffer_utilization_pct": 96.5,
                    "metric_name:queue_depth_bytes": 48200000.0,
                    "_value": 98.4,
                    "device": target_node.name,
                    "subscription_mode": "ON_CHANGE",
                    "openconfig_path": "/components/component[CPU]/state"
                }
            })

        # =========================================================================
        # 3. BGP ROUTE FLAPPING / LEAK
        # =========================================================================
        elif request.scenario_type == FaultScenarioType.BGP_ROUTE_FLAP:
            router = next((n for n in topology.nodes if n.type in (NodeType.ROUTER, NodeType.SWITCH)), topology.nodes[0] if topology.nodes else None)
            if not router:
                raise ValueError("No router available for BGP flap")

            affected_nodes.append(router.id)
            desc = f"BGP Route Flapping & Prefix Leak on {router.name}"
            now_iso = SplunkLogEngine.current_timestamp_iso()
            now_syslog = SplunkLogEngine.current_timestamp_syslog()

            # Multiple oscillating flap events
            for i, st in enumerate(["IDLE", "ACTIVE", "OPENSENT", "ESTABLISHED", "IDLE"]):
                logs.append(LogEntry(
                    timestamp=now_iso,
                    device_id=router.name,
                    src_ip=router.ip_address,
                    dest_ip="198.51.100.1",
                    protocol="BGP",
                    duration="1ms",
                    action="alerted" if st != "IDLE" else "dropped",
                    signature=f"BGP State Machine Transition: {st}",
                    status="degraded" if st == "IDLE" else "normal",
                    raw_log=f"<189>{now_syslog} {router.name} rpd[2480]: %ROUTING-5-BGP_STATE_CHANGE: Peer 198.51.100.1 (AS 65001) state transitioned to {st} (flap #{i+1})",
                    node_type=router.type.value,
                    node_id=router.id,
                    vendor=router.vendor,
                    sourcetype="juniper:junos" if "juniper" in router.vendor else "cisco:ios:syslog"
                ))

            metrics.append({
                "time": time.time(),
                "event": "metric",
                "source": "cisco:ios:mdt",
                "sourcetype": "cisco:ios:mdt:metric",
                "host": f"{router.name}.corp.internal",
                "index": "cisco_mdt_metrics",
                "fields": {
                    "metric_name:bgp.prefixes.received": 42.0,
                    "metric_name:bgp.prefixes.advertised": 18.0,
                    "_value": 42.0,
                    "device": router.name,
                    "subscription_mode": "ON_CHANGE"
                }
            })

        # =========================================================================
        # 4. DDOS SYN FLOOD & PERIMETER PRESSURE
        # =========================================================================
        elif request.scenario_type == FaultScenarioType.DDOS_SYN_FLOOD:
            target_host = next((n for n in topology.nodes if n.type in (NodeType.WEB_SERVER, NodeType.FIREWALL)), topology.nodes[0] if topology.nodes else None)
            fw_node = next((n for n in topology.nodes if n.type == NodeType.FIREWALL), None)
            if not target_host:
                raise ValueError("No target host for DDoS")

            affected_nodes.append(target_host.id)
            if fw_node:
                affected_nodes.append(fw_node.id)
            desc = f"High-PPS Distributed SYN Flood directed at {target_host.name} ({target_host.ip_address})"

            now_iso = SplunkLogEngine.current_timestamp_iso()
            target_ip = target_host.ip_address

            # Radware Scrubbing alert
            logs.append(LogEntry(
                timestamp=now_iso,
                device_id="radware-defensepro01",
                src_ip="203.0.113.50",
                dest_ip=target_ip,
                protocol="TCP/SYN",
                duration="0ms",
                action="blocked",
                signature="Volumetric SYN Flood Detection (>120,000 PPS)",
                status="blocked",
                raw_log=json.dumps({"timestamp": int(time.time()*1000), "attack_type": "SYN Flood", "target_ip": target_ip, "pps_rate": 145000, "bandwidth_mbps": 2410, "mitigation": "active_scrubbing"}),
                node_type="security_appliance",
                node_id="radware-dp",
                vendor="radware",
                sourcetype="radware:ddos"
            ))

            # Firewall Rate-Limit Drop
            if fw_node:
                logs.append(LogEntry(
                    timestamp=now_iso,
                    device_id=fw_node.name,
                    src_ip="198.51.100.22",
                    dest_ip=target_ip,
                    protocol="TCP",
                    duration="1ms",
                    action="blocked",
                    signature="Perimeter Firewall SYN Flood Protection Drop",
                    status="blocked",
                    raw_log=f"1,{now_iso},001801000001,THREAT,flood,2304,{now_iso},198.51.100.22,{target_ip},0.0.0.0,0.0.0.0,SYN-Flood-Drop,,,tcp,vsys1,untrust,trust,ethernet1/1,ethernet1/2,LogForwarding,2026/09/19 12:00:00,10482,1,45210,80,0,0,0x0,tcp,drop,0,0,0,1,2026/09/19 12:00:00,0,any,0,294829,0x0,198.51.100.0-198.51.100.255,US,0,1,0",
                    node_type="firewall",
                    node_id=fw_node.id,
                    vendor=fw_node.vendor,
                    sourcetype="pan:threat"
                ))

        # =========================================================================
        # 5. LATERAL MOVEMENT & CREDENTIAL STUFFING
        # =========================================================================
        elif request.scenario_type == FaultScenarioType.LATERAL_MOVEMENT:
            infected = next((n for n in topology.nodes if n.type == NodeType.WEB_SERVER), topology.nodes[0] if topology.nodes else None)
            target = next((n for n in topology.nodes if n.type == NodeType.DATABASE), None)
            if not infected:
                raise ValueError("No infected node available")

            affected_nodes.append(infected.id)
            if target:
                affected_nodes.append(target.id)
            target_ip = target.ip_address if target else "10.0.2.50"
            desc = f"Internal Kerberos Brute-Force & Lateral Movement from {infected.name} to {target.name if target else Database}"

            now_iso = SplunkLogEngine.current_timestamp_iso()
            now_syslog = SplunkLogEngine.current_timestamp_syslog()

            # Failed logon attempts
            logs.append(LogEntry(
                timestamp=now_iso,
                device_id=infected.name,
                src_ip=infected.ip_address,
                dest_ip=target_ip,
                protocol="SMB/RPC",
                duration="5ms",
                action="alerted",
                signature="Repeated Kerberos Pre-Authentication Failure (EventCode 4771)",
                status="breached",
                raw_log=f"<134>{now_syslog} {infected.name} Security-Auditing: EventCode=4771 Account_Name=svc_dbadmin Failure_Code=0x18 Client_Address={infected.ip_address}",
                node_type=infected.type.value,
                node_id=infected.id,
                vendor="microsoft_windows",
                sourcetype="wineventlog:security"
            ))

        # =========================================================================
        # 6. OPTICAL BIT ERROR RATE DEGRADATION
        # =========================================================================
        elif request.scenario_type == FaultScenarioType.OPTICAL_BER_DEGRADATION:
            optical_node = next((n for n in topology.nodes if n.type == NodeType.OPTICAL_CORE or "nokia" in n.vendor or "arista" in n.vendor), topology.nodes[0] if topology.nodes else None)
            if not optical_node:
                raise ValueError("No optical node available")

            affected_nodes.append(optical_node.id)
            desc = f"Pre-FEC Bit Error Rate Degradation on {optical_node.name} Transceiver"
            now_iso = SplunkLogEngine.current_timestamp_iso()
            now_syslog = SplunkLogEngine.current_timestamp_syslog()

            logs.append(LogEntry(
                timestamp=now_iso,
                device_id=optical_node.name,
                src_ip=optical_node.ip_address,
                dest_ip="10.254.0.1",
                protocol="DWDM",
                duration="0ms",
                action="alerted",
                signature="Pre-FEC Bit Error Rate Degradation Alarm",
                status="degraded",
                raw_log=f"<164>{now_syslog} {optical_node.name} Major: OPTICAL #4012 Port 1/1/c1: Pre-FEC BER 1.45e-3 exceeded warning threshold 1.00e-4",
                node_type=optical_node.type.value,
                node_id=optical_node.id,
                vendor=optical_node.vendor,
                sourcetype="nokia:sros:syslog"
            ))

            metrics.append({
                "time": time.time(),
                "event": "metric",
                "source": "cisco:ios:mdt",
                "sourcetype": "cisco:ios:mdt:metric",
                "host": f"{optical_node.name}.corp.internal",
                "index": "cisco_mdt_metrics",
                "fields": {
                    "metric_name:optical.pre_fec_ber": 0.00145,
                    "metric_name:optical.rx_power_dbm": -18.5,
                    "_value": 0.00145,
                    "device": optical_node.name,
                    "interface": "1/1/c1",
                    "subscription_mode": "ON_CHANGE"
                }
            })

        # Record the active fault
        record = FaultEventRecord(
            id=fault_id,
            scenario_type=request.scenario_type,
            timestamp=time.time(),
            target_id=request.target_edge_id or request.target_node_id or "auto",
            description=desc,
            cascades_count=len(logs) + len(metrics),
            status="active",
            affected_nodes=affected_nodes,
            affected_edges=affected_edges
        )
        self.active_faults[fault_id] = record
        self.fault_history.append(record)

        # Dispatch logs and metrics to configured transport (HEC & Syslog)
        transport = topology.global_transport
        for log in logs:
            dispatcher.dispatch_log(log, transport)

        if transport and transport.hec_enabled and transport.hec_url and transport.hec_token:
            for metric in metrics:
                dispatcher.emit_hec(metric, transport.hec_url, transport.hec_token)

        return record, logs, metrics

    def recover_fault(self, topology: TopologyState, request: FaultRecoveryRequest) -> Dict[str, Any]:
        """
        Restores state of affected nodes and edges, emitting recovery events.
        """
        graph = TopologyGraph(topology)
        recovered_edges = []
        recovered_nodes = []

        if request.fault_id and request.fault_id in self.active_faults:
            record = self.active_faults[request.fault_id]
            for edge_id in record.affected_edges:
                graph.restore_link(edge_id)
                recovered_edges.append(edge_id)
            for node_id in record.affected_nodes:
                graph.restore_node(node_id)
                recovered_nodes.append(node_id)
            record.status = "recovered"
            del self.active_faults[request.fault_id]
        else:
            if request.target_edge_id:
                graph.restore_link(request.target_edge_id)
                recovered_edges.append(request.target_edge_id)
            if request.target_node_id:
                graph.restore_node(request.target_node_id)
                recovered_nodes.append(request.target_node_id)

        # Emit recovery notifications
        now_iso = SplunkLogEngine.current_timestamp_iso()
        now_syslog = SplunkLogEngine.current_timestamp_syslog()
        for edge_id in recovered_edges:
            edge = next((e for e in topology.edges if e.id == edge_id), None)
            if edge:
                recovery_log = LogEntry(
                    timestamp=now_iso,
                    device_id=edge.source,
                    src_ip="10.0.1.1",
                    dest_ip="255.255.255.255",
                    protocol="ETHERNET",
                    duration="0ms",
                    action="allowed",
                    signature="Physical Layer Link Restored (UP)",
                    status="normal",
                    raw_log=f"<189>{now_syslog} {edge.source} %LINK-3-UPDOWN: Interface {edge.source_port}, changed state to up",
                    node_type="switch",
                    node_id=edge.source,
                    vendor="cisco",
                    sourcetype="cisco:ios:syslog"
                )
                dispatcher.dispatch_log(recovery_log, topology.global_transport)

        return {
            "success": True,
            "recovered_edges": recovered_edges,
            "recovered_nodes": recovered_nodes,
            "active_faults_remaining": len(self.active_faults)
        }


# Global singleton fault injection engine
fault_engine = FaultInjectionEngine()
