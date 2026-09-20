"""
Dynamic Failure & Fault Injection Engine (NetSpout)
Orchestrates multi-stage physical, protocol, and security failure cascades.
Synchronously emits cross-protocol telemetry:
  - Multi-Vendor RFC 5424 / Vendor-Specific Syslog (Palo Alto, Fortinet, Juniper, Arista, Dell, Cisco)
  - SC4SNMP Standard & Enterprise Traps (linkDown, linkUp, bgpBackwardTransition, ciscoCpuThresholdExceeded, etc.)
  - OpenConfig YANG ON_CHANGE Model-Driven Telemetry (MDT)
Dispatches to all active pipelines: Splunk HEC, OTel Collector, Telegraf, and Syslog.

Author: Mahamudul Chowdhury (mchowdhury@splunk.com)
"""

import time
import uuid
import random
from datetime import datetime
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


def get_vendor_slug(node: Node) -> str:
    """Classifies node vendor into canonical vendor slug."""
    vendor = (getattr(node, "vendor", "") or "").lower()
    name = (getattr(node, "name", "") or "").lower()
    if "palo" in vendor or "pan" in vendor or "pan" in name:
        return "palo_alto"
    if "fortinet" in vendor or "fortigate" in vendor or "fgt" in name:
        return "fortinet"
    if "juniper" in vendor or "junos" in vendor or "jnx" in name:
        return "juniper_junos"
    if "arista" in vendor or "eos" in vendor or "eos" in name:
        return "arista_eos"
    if "dell" in vendor or "os10" in vendor:
        return "dell_os10"
    if "checkpoint" in vendor or "chkp" in name:
        return "checkpoint"
    if "f5" in vendor or "bigip" in name:
        return "f5_bigip"
    if "nokia" in vendor or "sros" in vendor or "7750" in name:
        return "nokia_sr"
    if "asa" in vendor or "ftd" in vendor or "asa" in name or "firewall" in name:
        return "cisco_asa"
    if "meraki" in vendor or "mr" in name or "ms" in name:
        return "cisco_meraki"
    if "ise" in vendor or "ise" in name:
        return "cisco_ise"
    if "duo" in vendor or "duo" in name:
        return "cisco_duo"
    return "cisco_ios"


def format_vendor_carrier_log(node: Node, port: str, is_up: bool, now_iso: str, now_syslog: str) -> LogEntry:
    """Emits official vendor-specific interface carrier state change log."""
    v_slug = get_vendor_slug(node)
    now_dt = datetime.utcnow()
    datetime_slash = now_dt.strftime("%Y/%m/%d %H:%M:%S")
    date_str = now_dt.strftime("%Y-%m-%d")
    time_str = now_dt.strftime("%H:%M:%S")

    action = "allowed" if is_up else "alerted"
    status = "normal" if is_up else "degraded"
    sig = "Physical Layer Link Restored (UP)" if is_up else "Physical Layer Carrier Loss (LOS)"

    if v_slug == "palo_alto":
        sourcetype = "pan:system"
        state_str = "up" if is_up else "down"
        sev = "informational" if is_up else "high"
        seq = 12346 if is_up else 12345
        raw = f"1,{datetime_slash},001801000000,SYSTEM,link,0,{datetime_slash},,link-change,,0,0,general,{sev},\"Interface {port} changed state to {state_str}\",{seq},0x0,0,0,0,0,,{node.name}"
    elif v_slug == "fortinet":
        sourcetype = "fortinet:fortigate:event"
        state_str = "up" if is_up else "down"
        lvl = "notice" if is_up else "warning"
        lid = "0100022002" if is_up else "0100022001"
        raw = f"date={date_str} time={time_str} devname=\"{node.name}\" devid=\"FG200ETK18001048\" logid=\"{lid}\" type=\"event\" subtype=\"system\" level=\"{lvl}\" vd=\"root\" logdesc=\"Link monitor status\" msg=\"Interface {port} link is {state_str}\" action=\"link-{state_str}\""
    elif v_slug == "juniper_junos":
        sourcetype = "juniper:junos:syslog"
        trap_name = "SNMP_TRAP_LINK_UP" if is_up else "SNMP_TRAP_LINK_DOWN"
        oper_code = "up(1)" if is_up else "down(2)"
        pri = "189" if is_up else "187"
        raw = f"<{pri}>{now_syslog} {node.name} mib2d[1042]: {trap_name}: ifIndex 501, ifAdminStatus up(1), ifOperStatus {oper_code}, ifName {port}"
    elif v_slug == "arista_eos":
        sourcetype = "arista:eos:syslog"
        pri = "189" if is_up else "187"
        state_str = "up" if is_up else "down"
        raw = f"<{pri}>{now_syslog} {node.name} Ebra: %LINEPROTO-5-UPDOWN: Line protocol on Interface {port}, changed state to {state_str}"
    elif v_slug == "dell_os10":
        sourcetype = "dell:os10:syslog"
        pri = "189" if is_up else "187"
        state_str = "Up" if is_up else "Down"
        ifm_tag = "IF_UP" if is_up else "IF_DOWN"
        raw = f"%Dell <{pri}>{now_syslog} {node.name} dn_ifm[819]: %IFM-3-{ifm_tag}: Interface {port} is {state_str}"
    elif v_slug == "cisco_asa":
        sourcetype = "cisco:asa"
        pri = "166" if is_up else "163"
        state_str = "UP" if is_up else "DOWN, carrier lost"
        code = "105009" if is_up else "105010"
        raw = f"<{pri}>{now_syslog} {node.name} %ASA-3-{code}: (Ha-link) Interface {port} is {state_str}"
    else:
        sourcetype = "cisco:ios:syslog"
        pri = "189" if is_up else "187"
        state_str = "up" if is_up else "down"
        raw = f"<{pri}>{now_syslog} {node.name} %LINK-3-UPDOWN: Interface {port}, changed state to {state_str}"

    return LogEntry(
        timestamp=now_iso,
        device_id=node.name,
        src_ip=node.ip_address,
        dest_ip="255.255.255.255",
        protocol="ETHERNET",
        duration="0ms",
        action=action,
        signature=sig,
        status=status,
        raw_log=raw,
        node_type=node.type.value if hasattr(node.type, "value") else str(node.type),
        node_id=node.id,
        vendor=v_slug,
        sourcetype=sourcetype
    )


def format_vendor_bgp_log(node: Node, peer_ip: str, is_flap: bool, now_iso: str, now_syslog: str) -> LogEntry:
    """Emits official vendor BGP adjacency change or flap dampening log."""
    v_slug = get_vendor_slug(node)

    if v_slug == "juniper_junos":
        sourcetype = "juniper:junos:syslog"
        if is_flap:
            raw = f"<188>{now_syslog} {node.name} rpd[2104]: %DAEMON-4-BGP_FLAP_DAMPING: Flap damping route 203.0.113.0/24 in inet.0, penalty 2500 exceeds suppress limit 2000"
            sig = "BGP Route Dampening Active (Penalty > 2000)"
        else:
            raw = f"<187>{now_syslog} {node.name} rpd[2104]: %DAEMON-3-BGP_PREFIX_THRESH_EXCEEDED: neighbor {peer_ip} (External AS 65000): Hold timer expired. State changed from Established to Idle"
            sig = "BGP Neighbor Adjacency Lost"
    elif v_slug == "arista_eos":
        sourcetype = "arista:eos:syslog"
        if is_flap:
            raw = f"<188>{now_syslog} {node.name} Bgp: %BGP-4-ROUTE_DAMPED: Route 203.0.113.0/24 in VRF default damped (penalty 2480, suppress threshold 2000)"
            sig = "BGP Route Dampening Active (Penalty > 2000)"
        else:
            raw = f"<189>{now_syslog} {node.name} Bgp: %BGP-5-ADJCHANGE: peer {peer_ip} (VRF default) changed state from Established to Idle (Peer closed session)"
            sig = "BGP Neighbor Adjacency Lost"
    else:
        sourcetype = "cisco:ios:syslog"
        if is_flap:
            raw = f"<188>{now_syslog} {node.name} %BGP-4-DAMP_PENALTY: Route 203.0.113.0/24 flapped 12 times; dampening penalty 2450 exceeds suppress limit (2000)"
            sig = "BGP Route Dampening Active (Penalty > 2000)"
        else:
            raw = f"<189>{now_syslog} {node.name} %BGP-5-ADJCHANGE: neighbor {peer_ip} Down (Interface flap / HoldTimer Expired)"
            sig = "BGP Neighbor Adjacency Lost"

    return LogEntry(
        timestamp=now_iso,
        device_id=node.name,
        src_ip=node.ip_address,
        dest_ip=peer_ip,
        protocol="BGP",
        duration="1ms",
        action="dropped" if not is_flap else "alerted",
        signature=sig,
        status="degraded",
        raw_log=raw,
        node_type=node.type.value if hasattr(node.type, "value") else str(node.type),
        node_id=node.id,
        vendor=v_slug,
        sourcetype=sourcetype
    )


def format_vendor_cpu_log(node: Node, cpu_pct: float, mem_pct: float, now_iso: str, now_syslog: str) -> LogEntry:
    """Emits official vendor CPU/RAM exhaustion threshold alarm."""
    v_slug = get_vendor_slug(node)
    now_dt = datetime.utcnow()
    datetime_slash = now_dt.strftime("%Y/%m/%d %H:%M:%S")
    date_str = now_dt.strftime("%Y-%m-%d")
    time_str = now_dt.strftime("%H:%M:%S")

    if v_slug == "palo_alto":
        sourcetype = "pan:system"
        raw = f"1,{datetime_slash},001801000000,SYSTEM,general,0,{datetime_slash},,high-cpu,,0,0,general,critical,\"High CPU utilization detected on dataplane: {cpu_pct}%\",12347,0x0,0,0,0,0,,{node.name}"
    elif v_slug == "fortinet":
        sourcetype = "fortinet:fortigate:event"
        raw = f"date={date_str} time={time_str} devname=\"{node.name}\" devid=\"FG200ETK18001048\" logid=\"0100022922\" type=\"event\" subtype=\"system\" level=\"alert\" vd=\"root\" logdesc=\"CPU usage\" msg=\"System CPU usage reached {cpu_pct}%\" cpu={cpu_pct} mem={mem_pct}"
    elif v_slug == "juniper_junos":
        sourcetype = "juniper:junos:syslog"
        raw = f"<{186}>{now_syslog} {node.name} chassisd[1020]: %DAEMON-2-CHASSISD_HIGH_CPU: Host CPU utilization is high ({cpu_pct}%), system response may degrade"
    elif v_slug == "arista_eos":
        sourcetype = "arista:eos:syslog"
        raw = f"<{187}>{now_syslog} {node.name} ProcMgr: %PROCMGR-3-HIGH_CPU: System CPU usage is at {cpu_pct}% (threshold: 90%)"
    else:
        sourcetype = "cisco:ios:syslog"
        raw = f"<{186}>{now_syslog} {node.name} %SYS-2-CPU_RISING_THRESHOLD: CPU utilization {cpu_pct}% exceeds rising threshold (90%) for 60 seconds"

    return LogEntry(
        timestamp=now_iso,
        device_id=node.name,
        src_ip=node.ip_address,
        dest_ip="10.255.255.255",
        protocol="SNMP/PLATFORM",
        duration="0ms",
        action="alerted",
        signature="Control Plane CPU Exhaustion (>95%)",
        status="degraded",
        raw_log=raw,
        node_type=node.type.value if hasattr(node.type, "value") else str(node.type),
        node_id=node.id,
        vendor=v_slug,
        sourcetype=sourcetype
    )


def format_vendor_optical_log(node: Node, port: str, rx_power: float, now_iso: str, now_syslog: str) -> LogEntry:
    """Emits optical transceiver Bit Error Rate (BER) degradation log."""
    v_slug = get_vendor_slug(node)

    if v_slug == "juniper_junos":
        sourcetype = "juniper:junos:syslog"
        raw = f"<188>{now_syslog} {node.name} chassisd[1020]: %DAEMON-4-XCVR_OPTICAL_ALARM: SFP-10G-LR interface {port}: Rx power low alarm ({rx_power:.2f} dBm)"
    elif v_slug == "arista_eos":
        sourcetype = "arista:eos:syslog"
        raw = f"<188>{now_syslog} {node.name} Fru: %TRANSCEIVER-4-LOW_RX_POWER: Dom on {port}: Rx power ({rx_power:.2f} dBm) below low alarm limit (-18.0 dBm)"
    else:
        sourcetype = "cisco:ios:syslog"
        raw = f"<188>{now_syslog} {node.name} %TRANSCEIVER-4-LOW_RX_POWER: {port} transceiver Rx optical power ({rx_power:.2f} dBm) below low alarm threshold (-18.0 dBm)"

    return LogEntry(
        timestamp=now_iso,
        device_id=node.name,
        src_ip=node.ip_address,
        dest_ip="255.255.255.255",
        protocol="ETHERNET",
        duration="0ms",
        action="alerted",
        signature="Optical Signal Degradation (High BER / Low Rx Power)",
        status="degraded",
        raw_log=raw,
        node_type=node.type.value if hasattr(node.type, "value") else str(node.type),
        node_id=node.id,
        vendor=v_slug,
        sourcetype=sourcetype
    )


def format_vendor_ddos_log(node: Node, dest_ip: str, now_iso: str, now_syslog: str) -> LogEntry:
    """Emits volumetric TCP SYN flood protection alarm."""
    v_slug = get_vendor_slug(node)
    now_dt = datetime.utcnow()
    datetime_slash = now_dt.strftime("%Y/%m/%d %H:%M:%S")
    date_str = now_dt.strftime("%Y-%m-%d")
    time_str = now_dt.strftime("%H:%M:%S")

    if v_slug == "palo_alto":
        sourcetype = "pan:threat"
        raw = f"1,{datetime_slash},001801000000,THREAT,flood,9903,198.51.100.55,{dest_ip},0.0.0.0,0.0.0.0,Perimeter-SYN-Flood-Protection,untrust,trust,ethernet1/1,ethernet1/2,default,49182,80,0,0,0x0,tcp,drop,0,0,0,0,0,,TCP SYN Flood Attack Detected,web-browsing,critical,client-to-server,91024,0x0,United States,United States,0,,0,,,0,,,,0,0,{node.name},from-policy"
    elif v_slug == "fortinet":
        sourcetype = "fortinet:fortigate:utm"
        raw = f"date={date_str} time={time_str} devname=\"{node.name}\" devid=\"FG200ETK18001048\" logid=\"0419016385\" type=\"utm\" subtype=\"ips\" level=\"critical\" vd=\"root\" srcip=198.51.100.55 srcport=49182 dstip={dest_ip} dstport=80 proto=6 action=\"dropped\" attack=\"TCP.SYN.Flood\" attackid=100001 severity=\"critical\" msg=\"DoS attack detected: TCP SYN Flood\""
    elif v_slug == "cisco_asa":
        sourcetype = "cisco:asa"
        raw = f"<164>{now_syslog} {node.name} %ASA-4-405001: Received SYN flood attack from 198.51.100.0/24 to {dest_ip}/80. Threshold: 50000 pkts/sec reached"
    else:
        sourcetype = "cisco:ios:syslog"
        raw = f"<188>{now_syslog} {node.name} %TCP-4-SYNFLOOD: SYN flood detected on GigabitEthernet0/0/0, rate exceeded 50000 pps"

    return LogEntry(
        timestamp=now_iso,
        device_id=node.name,
        src_ip="198.51.100.55",
        dest_ip=dest_ip,
        protocol="TCP",
        duration="0ms",
        action="dropped",
        signature="Volumetric TCP SYN Flood Attack",
        status="degraded",
        raw_log=raw,
        node_type=node.type.value if hasattr(node.type, "value") else str(node.type),
        node_id=node.id,
        vendor=v_slug,
        sourcetype=sourcetype
    )


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

            # Cascade 1: Multi-Vendor Carrier Loss Syslogs
            if node_a:
                logs.append(format_vendor_carrier_log(node_a, target_edge.source_port, False, now_iso, now_syslog))
            if node_b:
                logs.append(format_vendor_carrier_log(node_b, target_edge.target_port, False, now_iso, now_syslog))

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

            # Cascade 4: Multi-Vendor Routing Flap (BGP Hold Timer Expired)
            if node_a and node_b:
                logs.append(format_vendor_bgp_log(node_a, node_b.ip_address, is_flap=False, now_iso=now_iso, now_syslog=now_syslog))
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

            logs.append(format_vendor_cpu_log(target_node, cpu_pct=98.4, mem_pct=95.2, now_iso=now_iso, now_syslog=now_syslog))

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
            router = next((n for n in topology.nodes if n.type == NodeType.ROUTER or "cisco" in n.vendor or "arista" in n.vendor or "juniper" in n.vendor), topology.nodes[0] if topology.nodes else None)
            if not router:
                raise ValueError("No router available for BGP flap")

            affected_nodes.append(router.id)
            peer_ip = "198.51.100.2"
            desc = f"Simulated BGP prefix flap storm with ISP Tier-1 Peer ({peer_ip})"

            logs.append(format_vendor_bgp_log(router, peer_ip, is_flap=True, now_iso=now_iso, now_syslog=now_syslog))

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
        # 4. OPTICAL BIT ERROR RATE (BER) DEGRADATION
        # =========================================================================
        elif request.scenario_type == FaultScenarioType.OPTICAL_BER_DEGRADATION:
            target_edge = None
            if request.target_edge_id:
                target_edge = next((e for e in topology.edges if e.id == request.target_edge_id), None)
            if not target_edge and topology.edges:
                target_edge = topology.edges[0]

            if not target_edge:
                raise ValueError("No edge available for optical degradation")

            affected_edges.append(target_edge.id)
            affected_nodes.extend([target_edge.source, target_edge.target])
            desc = f"Simulated fiber dirty connector / high Bit Error Rate (BER) degradation between {target_edge.source} and {target_edge.target}"

            node_a = graph.nodes_by_id.get(target_edge.source)
            if node_a:
                logs.append(format_vendor_optical_log(node_a, target_edge.source_port, -24.5, now_iso, now_syslog))
                traps.append(snmp_engine.generate_trap("ciscoEnvMonTemperatureNotification", node_a))
                metrics.append(gnmi_server.emit_on_change_event(
                    node=node_a,
                    path=f"/interfaces/interface[name={target_edge.source_port}]/transceiver/state/input-power",
                    changed_field="input-power",
                    old_value="-10.2",
                    new_value="-24.5",
                    numeric_metric_name="transceiver.rx.power_dbm",
                    numeric_val=-24.5
                ))

        # =========================================================================
        # 5. VOLUMETRIC DDOS SYN FLOOD
        # =========================================================================
        elif request.scenario_type == FaultScenarioType.DDOS_SYN_FLOOD:
            target_node = None
            if request.target_node_id:
                target_node = graph.nodes_by_id.get(request.target_node_id)
            if not target_node and topology.nodes:
                target_node = next((n for n in topology.nodes if n.type in (NodeType.FIREWALL, NodeType.ROUTER, NodeType.LOAD_BALANCER)), topology.nodes[0])

            if not target_node:
                raise ValueError("No edge/firewall node available for DDoS attack")

            affected_nodes.append(target_node.id)
            desc = f"Simulated 50 Gbps volumetric TCP SYN flood against {target_node.name}"

            logs.append(format_vendor_ddos_log(target_node, target_node.ip_address, now_iso, now_syslog))
            traps.append(snmp_engine.generate_trap("aristaQueueDropExceeded", target_node))

            metrics.append({
                "time": time.time(),
                "event": "metric",
                "source": "cisco:ios:mdt",
                "sourcetype": "cisco:ios:mdt:metric",
                "host": f"{target_node.name}.corp.internal",
                "index": "cisco_mdt_metrics",
                "fields": {
                    "metric_name:interface.drops": 142000.0,
                    "_value": 142000.0,
                    "component": "SYN-Protection-Engine",
                    "device": target_node.name,
                    "subscription_mode": "ON_CHANGE"
                }
            })

        # =========================================================================
        # 6. LATERAL MOVEMENT & CREDENTIAL STUFFING
        # =========================================================================
        elif request.scenario_type == FaultScenarioType.LATERAL_MOVEMENT:
            target_node = topology.nodes[0] if topology.nodes else None
            if not target_node:
                raise ValueError("No node available for lateral movement scenario")

            affected_nodes.append(target_node.id)
            desc = f"Simulated lateral movement and unauthorized privilege escalation pivot from {target_node.name}"

            now_dt = datetime.utcnow()
            now_iso_sec = now_dt.strftime("%Y-%m-%d %H:%M:%S")

            # Cisco ISE Auth failure
            logs.append(LogEntry(
                timestamp=now_iso,
                device_id="ise-appliance-01",
                src_ip="192.168.10.45",
                dest_ip="10.20.0.50",
                protocol="RADIUS/TACACS+",
                duration="15ms",
                action="blocked",
                signature="Unauthorized Lateral Credential Stuffing",
                status="degraded",
                raw_log=f"<181>{now_syslog} ise-appliance-01 CISE_Failed_Attempts 0000021482 1 0 {now_iso_sec}.012 +00:00 0001234567 5400 NOTICE Failed-Attempt: User authentication failed, User-Name=svc-backup, NAS-IP-Address=192.168.10.45, FailureReason=22056 Subject not found in identity source",
                node_type="server",
                node_id=target_node.id,
                vendor="cisco_ise",
                sourcetype="cisco:ise:syslog"
            ))

            # Cisco Duo Lockout
            logs.append(LogEntry(
                timestamp=now_iso,
                device_id="duo-cloud-proxy",
                src_ip="192.168.10.45",
                dest_ip="10.20.0.50",
                protocol="HTTPS",
                duration="8ms",
                action="blocked",
                signature="Duo MFA Account Lockout (5 Failed Push Challenges)",
                status="degraded",
                raw_log=f"""{{"timestamp": {int(time.time())}, "username": "admin_backup", "eventtype": "authentication", "result": "FAILURE", "reason": "Locked out after 5 consecutive failed MFA attempts", "ip": "192.168.10.45", "factor": "duo_push"}}""",
                node_type="server",
                node_id=target_node.id,
                vendor="cisco_duo",
                sourcetype="cisco:duo:auth"
            ))

            # Palo Alto Threat detection
            datetime_slash = now_dt.strftime("%Y/%m/%d %H:%M:%S")
            logs.append(LogEntry(
                timestamp=now_iso,
                device_id=target_node.name,
                src_ip="192.168.10.45",
                dest_ip="10.20.0.50",
                protocol="TCP",
                duration="5ms",
                action="dropped",
                signature="Microsoft Windows SMB Lateral Remote Execution Attempt",
                status="degraded",
                raw_log=f"1,{datetime_slash},001801000000,THREAT,vulnerability,9904,192.168.10.45,10.20.0.50,0.0.0.0,0.0.0.0,Internal-ZeroTrust-Block,trust,trust,ethernet1/2,ethernet1/3,default,52104,445,0,0,0x0,tcp,reset-both,0,0,0,0,0,,(30845) Microsoft Windows SMB Lateral Remote Execution Attempt,ms-ds-smb,high,client-to-server,94821,0x0,Internal,Internal,0,,0,,,0,,,,0,0,{target_node.name},from-policy",
                node_type=target_node.type.value if hasattr(target_node.type, "value") else str(target_node.type),
                node_id=target_node.id,
                vendor="palo_alto",
                sourcetype="pan:threat"
            ))

        # =========================================================================
        # 7. SNMP TRAP BURST
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
                    node_type=target_node.type.value if hasattr(target_node.type, "value") else str(target_node.type),
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
        Restores state of affected nodes and edges, emitting multi-vendor recovery events.
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
                node_a = graph.nodes_by_id.get(edge.source)
                node_b = graph.nodes_by_id.get(edge.target)

                if node_a:
                    recovery_log_a = format_vendor_carrier_log(node_a, edge.source_port, True, now_iso, now_syslog)
                    dispatcher.dispatch_log(recovery_log_a, transport)
                    up_trap_a = snmp_engine.generate_trap("linkUp", node_a, {"ifDescr": edge.source_port, "ifOperStatus": 1})
                    dispatcher.dispatch_snmp_trap(up_trap_a, transport)

                if node_b:
                    recovery_log_b = format_vendor_carrier_log(node_b, edge.target_port, True, now_iso, now_syslog)
                    dispatcher.dispatch_log(recovery_log_b, transport)
                    up_trap_b = snmp_engine.generate_trap("linkUp", node_b, {"ifDescr": edge.target_port, "ifOperStatus": 1})
                    dispatcher.dispatch_snmp_trap(up_trap_b, transport)

        return {
            "success": True,
            "recovered_edges": recovered_edges,
            "recovered_nodes": recovered_nodes,
            "active_faults_remaining": len(self.active_faults)
        }


# Global singleton fault injection engine
fault_engine = FaultInjectionEngine()
