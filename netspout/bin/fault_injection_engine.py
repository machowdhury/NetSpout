"""
Dynamic Failure & Fault Injection Engine (NetSpout)
Orchestrates multi-stage physical, protocol, and security failure cascades.
Synchronously emits cross-protocol telemetry:
  - RFC 5424 / Cisco Syslog
  - SC4SNMP Standard & Enterprise Traps (linkDown, linkUp, bgpBackwardTransition, ciscoCpuThresholdExceeded, etc.)
  - OpenConfig YANG ON_CHANGE Model-Driven Telemetry (MDT)
Dispatches to all active pipelines: Splunk HEC, OTel Collector, Telegraf, and Syslog.
"""

import time
import uuid
import random
from typing import Dict, List, Any, Optional, Tuple

try:
    from app.models import (
        TopologyState, Node, Edge, NodeType, LogEntry,
        FaultScenarioType, FaultInjectionRequest, FaultEventRecord, FaultRecoveryRequest,
        SNMPTrapEvent
    )
    from app.graph_engine import TopologyGraph
    from app.log_engine import SplunkLogEngine
    from app.gnmi_engine import yang_store, gnmi_server
    from app.snmp_engine import snmp_engine
    from app.telemetry_dispatcher import dispatcher
except ImportError:
    from models import (
        TopologyState, Node, Edge, NodeType, LogEntry,
        FaultScenarioType, FaultInjectionRequest, FaultEventRecord, FaultRecoveryRequest,
        SNMPTrapEvent
    )
    from graph_engine import TopologyGraph
    from log_engine import SplunkLogEngine
    from gnmi_engine import yang_store, gnmi_server
    from snmp_engine import snmp_engine
    from telemetry_dispatcher import dispatcher


class FaultInjectionEngine:
    """
    Orchestrates physical, protocol, and security failure injections.
    Produces authentic multi-device cascading timelines to test SIEM and NOC correlation.
    """
    def __init__(self):
        self.active_faults: Dict[str, FaultEventRecord] = {}
        self.fault_history: List[FaultEventRecord] = []

    def inject_fault(
        self,
        topology: TopologyState,
        request: FaultInjectionRequest
    ) -> Tuple[FaultEventRecord, List[LogEntry], List[Dict[str, Any]], List[SNMPTrapEvent]]:
        """
        Executes fault injection and returns:
          1. FaultEventRecord tracking the failure
          2. Chronologically ordered LogEntry cascade
          3. gNMI metric payloads for cisco_mdt_metrics
          4. SC4SNMP Trap Events
        """
        fault_id = f"flt-{uuid.uuid4().hex[:8]}"
        graph = TopologyGraph(topology)
        logs: List[LogEntry] = []
        metrics: List[Dict[str, Any]] = []
        traps: List[SNMPTrapEvent] = []
        affected_nodes: List[str] = []
        affected_edges: List[str] = []
        desc = ""

        now_iso = SplunkLogEngine.current_timestamp_iso()
        now_syslog = SplunkLogEngine.current_timestamp_syslog()

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

            # Cascade 1: Port A & B Carrier Loss Syslogs
            if node_a:
                logs.append(LogEntry(
                    timestamp=now_iso,
                    device_id=node_a.name,
                    src_ip=node_a.ip_address,
                    dest_ip="255.255.255.255",
                    protocol="ETHERNET",
                    duration="0ms",
                    action="alerted",
                    signature="Physical Layer Carrier Loss (LOS)",
                    status="degraded",
                    raw_log=f"<187>{now_syslog} {node_a.name} %LINK-3-UPDOWN: Interface {target_edge.source_port}, changed state to down",
                    node_type=node_a.type.value,
                    node_id=target_edge.source,
                    vendor=node_a.vendor,
                    sourcetype="cisco:ios:syslog"
                ))
            if node_b:
                logs.append(LogEntry(
                    timestamp=now_iso,
                    device_id=node_b.name,
                    src_ip=node_b.ip_address,
                    dest_ip="255.255.255.255",
                    protocol="ETHERNET",
                    duration="0ms",
                    action="alerted",
                    signature="Physical Layer Carrier Loss (LOS)",
                    status="degraded",
                    raw_log=f"<187>{now_syslog} {node_b.name} %LINK-3-UPDOWN: Interface {target_edge.target_port}, changed state to down",
                    node_type=node_b.type.value,
                    node_id=target_edge.target,
                    vendor=node_b.vendor,
                    sourcetype="cisco:ios:syslog"
                ))

            # Cascade 2: SC4SNMP linkDown Traps
            if node_a:
                trap_a = snmp_engine.generate_trap(
                    "linkDown", node_a,
                    {"ifDescr": target_edge.source_port, "ifOperStatus": 2}
                )
                traps.append(trap_a)
                logs.append(SplunkLogEngine.format_snmp_trap(node_a, trap_type="linkDown", interface_name=target_edge.source_port, action="alerted", status="degraded"))

            if node_b:
                trap_b = snmp_engine.generate_trap(
                    "linkDown", node_b,
                    {"ifDescr": target_edge.target_port, "ifOperStatus": 2}
                )
                traps.append(trap_b)
                logs.append(SplunkLogEngine.format_snmp_trap(node_b, trap_type="linkDown", interface_name=target_edge.target_port, action="alerted", status="degraded"))

            # Cascade 3: OpenConfig ON_CHANGE Notifications for oper-status
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

            # Cascade 4: Routing Protocol Flap (BGP Hold Timer Expired & backward transition trap)
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
                bgp_trap = snmp_engine.generate_trap(
                    "bgpBackwardTransition", node_a,
                    {"bgpPeerRemoteAddr": node_b.ip_address, "bgpPeerState": 1, "bgpPeerLastError": "0400"}
                )
                traps.append(bgp_trap)

                metrics.append(gnmi_server.emit_on_change_event(
                    node=node_a,
                    path=f"/network-instances/network-instance[name=default]/protocols/protocol/bgp/neighbors/neighbor[neighbor-address={node_b.ip_address}]/state/session-state",
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

            # SC4SNMP Traps
            traps.append(snmp_engine.generate_trap(
                "ciscoCpuThresholdExceeded", target_node,
                {"cpmCPUTotal5minRev": 98.4, "cpmCPUTotal5secRev": 99.2}
            ))
            traps.append(snmp_engine.generate_trap(
                "ciscoMemoryThresholdExceeded", target_node,
                {"ciscoMemoryPoolFree": 1048576, "ciscoMemoryPoolUsed": 3980000000}
            ))

            # OpenConfig MDT CPU/Memory updates
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
                    "_value": 98.4,
                    "component": "Routing-Processor-0",
                    "device": target_node.name,
                    "subscription_mode": "ON_CHANGE"
                }
            })

        # =========================================================================
        # 3. BGP ROUTE FLAPPING
        # =========================================================================
        elif request.scenario_type == FaultScenarioType.BGP_ROUTE_FLAP:
            router = next((n for n in topology.nodes if n.type == NodeType.ROUTER or "cisco" in n.vendor or "arista" in n.vendor), topology.nodes[0] if topology.nodes else None)
            if not router:
                raise ValueError("No router available for BGP flap")

            affected_nodes.append(router.id)
            peer_ip = "198.51.100.2"
            desc = f"Simulated BGP prefix flap storm with ISP Tier-1 Peer ({peer_ip})"

            logs.append(LogEntry(
                timestamp=now_iso,
                device_id=router.name,
                src_ip=router.ip_address,
                dest_ip=peer_ip,
                protocol="BGP",
                duration="0ms",
                action="alerted",
                signature="BGP Route Dampening Active (Penalty > 2000)",
                status="degraded",
                raw_log=f"<188>{now_syslog} {router.name} %BGP-4-DAMP_PENALTY: Route 203.0.113.0/24 flapped 12 times; dampening penalty 2450 exceeds suppress limit (2000)",
                node_type=router.type.value,
                node_id=router.id,
                vendor=router.vendor,
                sourcetype="cisco:ios:syslog"
            ))

            traps.append(snmp_engine.generate_trap(
                "bgpBackwardTransition", router,
                {"bgpPeerRemoteAddr": peer_ip, "bgpPeerState": 1, "bgpPeerLastError": "0602"}
            ))

            metrics.append(gnmi_server.emit_on_change_event(
                node=router,
                path="/network-instances/network-instance[name=default]/protocols/protocol/bgp/neighbors/neighbor/state/session-state",
                changed_field="session-state",
                old_value="ESTABLISHED",
                new_value="ACTIVE",
                numeric_metric_name="bgp.prefixes.suppressed",
                numeric_val=14.0
            ))

        # =========================================================================
        # 4. SNMP TRAP BURST
        # =========================================================================
        elif request.scenario_type == FaultScenarioType.SNMP_TRAP_BURST:
            target_node = topology.nodes[0] if topology.nodes else None
            if not target_node:
                raise ValueError("No node available for SNMP Trap burst")

            desc = f"Emitted multi-vendor SC4SNMP trap burst from {target_node.name}"
            traps.append(snmp_engine.generate_trap("linkDown", target_node))
            traps.append(snmp_engine.generate_trap("ciscoEnvMonTemperatureNotification", target_node))
            traps.append(snmp_engine.generate_trap("ospfNbrStateChange", target_node))
            traps.append(snmp_engine.generate_trap("aristaQueueDropExceeded", target_node))

            for t in traps:
                logs.append(LogEntry(
                    timestamp=now_iso,
                    device_id=target_node.name,
                    src_ip=target_node.ip_address,
                    dest_ip="10.255.255.255",
                    protocol="SNMP-TRAP",
                    duration="0ms",
                    action="alerted",
                    signature=f"SNMP Trap {t.trap_name}",
                    status="degraded",
                    raw_log=f"SNMP-COMMUNITY=public TRAP-TYPE={t.trap_name} OID={t.trap_oid} SEVERITY={t.severity.upper()}",
                    node_type=target_node.type.value,
                    node_id=target_node.id,
                    vendor=target_node.vendor,
                    sourcetype="sc4snmp:event"
                ))

        # Record active fault
        record = FaultEventRecord(
            id=fault_id,
            scenario_type=request.scenario_type,
            timestamp=time.time(),
            target_id=request.target_edge_id or request.target_node_id or "auto",
            description=desc,
            cascades_count=len(logs) + len(metrics) + len(traps),
            status="active",
            affected_nodes=affected_nodes,
            affected_edges=affected_edges
        )
        self.active_faults[fault_id] = record
        self.fault_history.append(record)

        # Broadcast across active pipelines!
        transport = topology.global_transport
        for log in logs:
            dispatcher.dispatch_log(log, transport)
        for metric in metrics:
            dispatcher.dispatch_openconfig(metric, transport)
        for trap in traps:
            dispatcher.dispatch_snmp_trap(trap, transport)

        return record, logs, metrics, traps

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

        now_iso = SplunkLogEngine.current_timestamp_iso()
        now_syslog = SplunkLogEngine.current_timestamp_syslog()
        transport = topology.global_transport

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
                dispatcher.dispatch_log(recovery_log, transport)

                node_a = graph.nodes_by_id.get(edge.source)
                if node_a:
                    up_trap = snmp_engine.generate_trap("linkUp", node_a, {"ifDescr": edge.source_port, "ifOperStatus": 1})
                    dispatcher.dispatch_snmp_trap(up_trap, transport)

        return {
            "success": True,
            "recovered_edges": recovered_edges,
            "recovered_nodes": recovered_nodes,
            "active_faults_remaining": len(self.active_faults)
        }


# Global singleton fault injection engine
fault_engine = FaultInjectionEngine()
