"""
FastAPI Server & WebSocket Gateway
Provides REST APIs for topology management, scenario control, log export,
and real-time WebSocket streaming at 500ms intervals.
"""

import asyncio
import json
import time
import csv
import io
import os
from typing import List, Dict, Set
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse
from app.models import (
    SNMPTrapTriggerRequest, SNMPPollRequest, PipelineTestRequest,
    TopologyState, Node, Edge, NodeType, ScenarioType,
    LogEntry, SimulationRequest, EcosystemMode,
    ZoneAnnotation, NodePowerState, NodeHardware,
    TelemetryTransportConfig, SyslogTestRequest,
    FaultScenarioType, FaultInjectionRequest, FaultRecoveryRequest, FaultEventRecord
)
from app.telemetry_dispatcher import dispatcher
from app.scenario_runner import ScenarioRunner
from app.graph_engine import TopologyGraph
from app.gnmi_engine import yang_store, gnmi_server
from app.snmp_engine import snmp_engine
from app.fault_injection_engine import fault_engine

app = FastAPI(title="NetSpout Telemetry & Simulation API", version="2.0.0")

# Enable CORS for frontend development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Simulation State
scenario_runner = ScenarioRunner()
active_scenario: ScenarioType = ScenarioType.NORMAL_TRAFFIC
active_ecosystem_mode: EcosystemMode = EcosystemMode.MIXED_VENDOR
simulation_running: bool = False
simulation_interval_ms: int = 500
accumulated_logs: List[LogEntry] = []
MAX_LOG_HISTORY: int = 2000

# =========================================================================
# TOPOLOGY PRESETS
# =========================================================================

# Baseline Secure Topology Preset
def get_default_secure_topology() -> TopologyState:
    return TopologyState(
        nodes=[
            Node(id="node-client", name="External Client", type=NodeType.CLIENT_EXTERNAL, x=60, y=220, ip_address="198.51.100.42", status="active", vendor="generic"),
            Node(id="node-fw", name="Perimeter Firewall", type=NodeType.FIREWALL, x=260, y=220, ip_address="198.51.100.1", status="active", vendor="cisco_asa"),
            Node(id="node-lb", name="Core Load Balancer", type=NodeType.LOAD_BALANCER, x=470, y=220, ip_address="10.0.1.5", status="active", vendor="f5"),
            Node(id="node-web1", name="Web Server 01", type=NodeType.WEB_SERVER, x=690, y=140, ip_address="10.0.1.10", status="active", vendor="nginx"),
            Node(id="node-web2", name="Web Server 02", type=NodeType.WEB_SERVER, x=690, y=300, ip_address="10.0.1.11", status="active", vendor="nginx"),
            Node(id="node-db", name="Production Database", type=NodeType.DATABASE, x=920, y=220, ip_address="10.0.2.50", status="active", vendor="postgresql")
        ],
        edges=[
            Edge(id="edge-1", source="node-client", target="node-fw", source_port="wan", target_port="outside"),
            Edge(id="edge-2", source="node-fw", target="node-lb", source_port="inside", target_port="vip"),
            Edge(id="edge-3", source="node-lb", target="node-web1", source_port="pool-1", target_port="eth0"),
            Edge(id="edge-4", source="node-lb", target="node-web2", source_port="pool-2", target_port="eth0"),
            Edge(id="edge-5", source="node-web1", target="node-db", source_port="db-link", target_port="pg-port"),
            Edge(id="edge-6", source="node-web2", target="node-db", source_port="db-link", target_port="pg-port")
        ]
    )

def get_bypassed_topology() -> TopologyState:
    top = get_default_secure_topology()
    top.edges.append(Edge(id="edge-bypass", source="node-client", target="node-web1", source_port="direct", target_port="mgmt"))
    return top

def get_lateral_topology() -> TopologyState:
    return TopologyState(
        nodes=[
            Node(id="node-client", name="External Attacker", type=NodeType.CLIENT_EXTERNAL, x=60, y=220, ip_address="203.0.113.99", status="active", vendor="generic"),
            Node(id="node-web1", name="Infected Server 01", type=NodeType.WEB_SERVER, x=300, y=150, ip_address="10.0.1.10", status="breached", vendor="nginx"),
            Node(id="node-web2", name="Internal Server 02", type=NodeType.WEB_SERVER, x=540, y=150, ip_address="10.0.1.11", status="active", vendor="nginx"),
            Node(id="node-db", name="Target Database", type=NodeType.DATABASE, x=780, y=220, ip_address="10.0.1.50", status="active", vendor="postgresql")
        ],
        edges=[
            Edge(id="e-1", source="node-client", target="node-web1"),
            Edge(id="e-2", source="node-web1", target="node-web2"),
            Edge(id="e-3", source="node-web2", target="node-db")
        ]
    )

# Mode A1 Preset: Cisco Campus Rogue AP
def get_cisco_campus_topology() -> TopologyState:
    return TopologyState(
        nodes=[
            Node(id="node-rogue-ap", name="Rogue AP (Air Marshal Alert)", type=NodeType.WIRELESS_AP, x=70, y=220, ip_address="10.10.20.99", status="breached", vendor="cisco_catalyst", sourcetype="cisco:catalyst:rogue:threat_details"),
            Node(id="node-cat9300", name="Catalyst-9300-Access", type=NodeType.SWITCH, x=290, y=220, ip_address="10.10.20.1", status="active", vendor="cisco_catalyst", sourcetype="cisco:ios:syslog"),
            Node(id="node-cat9800", name="Catalyst-9800-WLC", type=NodeType.SWITCH, x=530, y=130, ip_address="10.10.1.10", status="active", vendor="cisco_catalyst", sourcetype="cisco:catalyst:security:events"),
            Node(id="node-ise", name="Cisco-ISE-PSN01", type=NodeType.FIREWALL, x=530, y=310, ip_address="10.10.1.25", status="active", vendor="cisco_ise", sourcetype="cisco:ise:syslog"),
            Node(id="node-campus-core", name="Catalyst-9600-Core", type=NodeType.ROUTER, x=780, y=220, ip_address="10.10.0.1", status="active", vendor="cisco_catalyst", sourcetype="cisco:ios:syslog")
        ],
        edges=[
            Edge(id="e-c1", source="node-rogue-ap", target="node-cat9300", source_port="radio0", target_port="Gi1/0/12", status="breached"),
            Edge(id="e-c2", source="node-cat9300", target="node-cat9800", source_port="Te1/1/1", target_port="TenGig0/0/1"),
            Edge(id="e-c3", source="node-cat9300", target="node-ise", source_port="Te1/1/2", target_port="eth0"),
            Edge(id="e-c4", source="node-cat9800", target="node-campus-core", source_port="uplink", target_port="FortyGig1/0/1"),
            Edge(id="e-c5", source="node-ise", target="node-campus-core", source_port="uplink", target_port="FortyGig1/0/2")
        ]
    )

# Mode A2 Preset: Cisco SD-WAN Brownout & Failover
def get_cisco_sdwan_topology() -> TopologyState:
    return TopologyState(
        nodes=[
            Node(id="node-te-agent", name="ThousandEyes-Agent", type=NodeType.CLIENT_EXTERNAL, x=70, y=220, ip_address="172.16.1.50", status="active", vendor="cisco_thousandeyes", sourcetype="cisco:thousandeyes:metric"),
            Node(id="node-c8000", name="Catalyst-8300-Branch", type=NodeType.ROUTER, x=280, y=220, ip_address="172.16.1.1", status="active", vendor="cisco_sdwan", sourcetype="cisco:sdwan:linkhealth"),
            Node(id="node-mpls-circuit", name="MPLS Primary (Brownout Loss)", type=NodeType.ROUTER, x=530, y=130, ip_address="198.51.100.1", status="degraded", vendor="cisco_sdwan", sourcetype="cisco:sdwan:BGP-5-ADJCHANGE"),
            Node(id="node-lte-circuit", name="LTE / Biz-Internet (Failover)", type=NodeType.ROUTER, x=530, y=310, ip_address="203.0.113.1", status="active", vendor="cisco_sdwan", sourcetype="cisco:sdwan:linkhealth"),
            Node(id="node-dc-vedge", name="DC-vEdge-5000-Hub", type=NodeType.ROUTER, x=780, y=220, ip_address="10.254.1.1", status="active", vendor="cisco_sdwan", sourcetype="cisco:sdwan:linkhealth")
        ],
        edges=[
            Edge(id="e-sd1", source="node-te-agent", target="node-c8000", source_port="eth0", target_port="Gig0/0/0"),
            Edge(id="e-sd2", source="node-c8000", target="node-mpls-circuit", source_port="Gig0/0/1", target_port="wan-mpls", status="congested"),
            Edge(id="e-sd3", source="node-c8000", target="node-lte-circuit", source_port="Gig0/0/2", target_port="wan-lte"),
            Edge(id="e-sd4", source="node-mpls-circuit", target="node-dc-vedge", source_port="wan", target_port="Gig1/0/1", status="congested"),
            Edge(id="e-sd5", source="node-lte-circuit", target="node-dc-vedge", source_port="wan", target_port="Gig1/0/2")
        ]
    )

# Mode A3 Preset: Cisco ACI Microburst & Buffer Saturation
def get_cisco_aci_topology() -> TopologyState:
    return TopologyState(
        nodes=[
            Node(id="node-incast-clients", name="Incast Compute Burst", type=NodeType.CLIENT_EXTERNAL, x=70, y=220, ip_address="10.255.10.5", status="active", vendor="generic"),
            Node(id="node-leaf-nexus", name="Nexus-9336-Leaf01", type=NodeType.SWITCH, x=290, y=220, ip_address="10.255.0.11", status="degraded", vendor="cisco_nexus", sourcetype="cisco:dc:nexus9k:syslog"),
            Node(id="node-spine1", name="Nexus-9508-Spine01", type=NodeType.SWITCH, x=530, y=130, ip_address="10.255.0.1", status="active", vendor="cisco_nexus", sourcetype="cisco:dc:aci:health"),
            Node(id="node-spine2", name="Nexus-9508-Spine02", type=NodeType.SWITCH, x=530, y=310, ip_address="10.255.0.2", status="active", vendor="cisco_nexus", sourcetype="cisco:dc:aci:health"),
            Node(id="node-leaf-dst", name="Nexus-9336-Leaf02", type=NodeType.SWITCH, x=780, y=220, ip_address="10.255.0.12", status="active", vendor="cisco_nexus", sourcetype="cisco:ios:mdt")
        ],
        edges=[
            Edge(id="e-aci1", source="node-incast-clients", target="node-leaf-nexus", source_port="100G", target_port="Eth1/24", status="congested"),
            Edge(id="e-aci2", source="node-leaf-nexus", target="node-spine1", source_port="Eth1/49", target_port="Eth1/1"),
            Edge(id="e-aci3", source="node-leaf-nexus", target="node-spine2", source_port="Eth1/50", target_port="Eth1/1"),
            Edge(id="e-aci4", source="node-spine1", target="node-leaf-dst", source_port="Eth1/2", target_port="Eth1/49"),
            Edge(id="e-aci5", source="node-spine2", target="node-leaf-dst", source_port="Eth1/2", target_port="Eth1/50")
        ]
    )

# Mode B1 Preset: Mixed-Vendor Edge Breach & Internal Probing
def get_mixed_edge_topology() -> TopologyState:
    return TopologyState(
        nodes=[
            Node(id="node-meraki-ap", name="Meraki-MR56-AP", type=NodeType.WIRELESS_AP, x=70, y=220, ip_address="10.128.0.55", status="active", vendor="meraki", sourcetype="meraki:assurancealerts"),
            Node(id="node-cat-switch", name="Catalyst-9300-Core", type=NodeType.SWITCH, x=290, y=220, ip_address="10.128.0.1", status="active", vendor="cisco_catalyst", sourcetype="cisco:catalyst:security:events"),
            Node(id="node-pan-fw", name="PaloAlto-PA440-NGFW", type=NodeType.FIREWALL, x=530, y=220, ip_address="10.128.1.1", status="active", vendor="palo_alto", sourcetype="pan:threat"),
            Node(id="node-internal-srv", name="Internal App Server", type=NodeType.WEB_SERVER, x=780, y=220, ip_address="10.128.2.10", status="active", vendor="nginx")
        ],
        edges=[
            Edge(id="e-b1", source="node-meraki-ap", target="node-cat-switch", source_port="eth0", target_port="Gi1/0/1"),
            Edge(id="e-b2", source="node-cat-switch", target="node-pan-fw", source_port="Gi1/0/24", target_port="ethernet1/1"),
            Edge(id="e-b3", source="node-pan-fw", target="node-internal-srv", source_port="ethernet1/2", target_port="eth0")
        ]
    )

# Mode B2 Preset: Mixed-Vendor SASE Cloud Ingress App Degradation
def get_mixed_sase_topology() -> TopologyState:
    return TopologyState(
        nodes=[
            Node(id="node-zscaler", name="Zscaler-ZIA-CloudEdge", type=NodeType.SASE_PROXY, x=70, y=220, ip_address="165.225.10.1", status="degraded", vendor="zscaler", sourcetype="zscaler:zia"),
            Node(id="node-pan-sdwan", name="PaloAlto-Prisma-SDWAN", type=NodeType.FIREWALL, x=290, y=220, ip_address="10.20.1.1", status="active", vendor="palo_alto", sourcetype="pan:threat"),
            Node(id="node-nexus-core", name="Cisco-Nexus-DC-Core", type=NodeType.SWITCH, x=530, y=220, ip_address="10.20.1.254", status="active", vendor="cisco_nexus", sourcetype="cisco:dc:nexus9k:syslog"),
            Node(id="node-saas-erp", name="SaaS ERP Target", type=NodeType.WEB_SERVER, x=780, y=220, ip_address="104.16.132.229", status="active", vendor="nginx")
        ],
        edges=[
            Edge(id="e-sase1", source="node-zscaler", target="node-pan-sdwan", source_port="gre-tunnel", target_port="tunnel.1", status="congested"),
            Edge(id="e-sase2", source="node-pan-sdwan", target="node-nexus-core", source_port="ethernet1/1", target_port="Eth1/1"),
            Edge(id="e-sase3", source="node-nexus-core", target="node-saas-erp", source_port="Eth1/2", target_port="eth0")
        ]
    )

# Mode B3 Preset: Mixed-Vendor Optical Carrier Shift & FRR
def get_mixed_optical_topology() -> TopologyState:
    return TopologyState(
        nodes=[
            Node(id="node-nokia-core", name="Nokia-7750-SR12-Transport", type=NodeType.OPTICAL_CORE, x=70, y=220, ip_address="10.200.0.1", status="degraded", vendor="nokia_sros", sourcetype="nokia:sros:syslog"),
            Node(id="node-juniper-pe", name="Juniper-MX960-PE01", type=NodeType.ROUTER, x=380, y=220, ip_address="10.200.0.2", status="active", vendor="juniper_junos", sourcetype="juniper:junos"),
            Node(id="node-arista-leaf", name="Arista-7280R-Leaf01", type=NodeType.SWITCH, x=700, y=220, ip_address="10.200.0.3", status="active", vendor="arista_eos", sourcetype="arista:flow:ipfix")
        ],
        edges=[
            Edge(id="e-opt1", source="node-nokia-core", target="node-juniper-pe", source_port="1/1/c1", target_port="ge-0/0/0", status="congested"),
            Edge(id="e-opt2", source="node-juniper-pe", target="node-arista-leaf", source_port="ge-0/0/1", target_port="Ethernet49/1")
        ]
    )

current_topology: TopologyState = get_default_secure_topology()


class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast_log(self, log_dict: dict):
        if not self.active_connections:
            return
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_json(log_dict)
            except Exception:
                dead.append(connection)
        for d in dead:
            self.active_connections.discard(d)

    async def broadcast(self, payload: dict):
        await self.broadcast_log(payload)

manager = ConnectionManager()


# Background Simulation Task
simulation_task = None

async def run_simulation_loop():
    global accumulated_logs
    while True:
        try:
            if simulation_running:
                logs = scenario_runner.execute_step(current_topology, active_scenario)
                for entry in logs:
                    accumulated_logs.append(entry)
                    if len(accumulated_logs) > MAX_LOG_HISTORY:
                        accumulated_logs.pop(0)
                    await manager.broadcast_log(entry.dict())
            await asyncio.sleep(simulation_interval_ms / 1000.0)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Simulation loop error: {e}")
            await asyncio.sleep(1.0)

@app.on_event("startup")
async def startup_event():
    global simulation_task
    simulation_task = asyncio.create_task(run_simulation_loop())

@app.on_event("shutdown")
async def shutdown_event():
    global simulation_task
    if simulation_task:
        simulation_task.cancel()


# REST API Endpoints
@app.get("/api/status")
async def get_status():
    return {
        "status": "online",
        "simulation_running": simulation_running,
        "active_scenario": active_scenario,
        "active_ecosystem_mode": active_ecosystem_mode,
        "speed_ms": simulation_interval_ms,
        "node_count": len(current_topology.nodes),
        "edge_count": len(current_topology.edges),
        "connected_clients": len(manager.active_connections),
        "total_logs": len(accumulated_logs)
    }

@app.get("/api/topology", response_model=TopologyState)
async def get_topology():
    return current_topology

@app.post("/api/topology", response_model=TopologyState)
async def update_topology(topology: TopologyState):
    global current_topology
    current_topology = topology
    # Notify WebSocket clients of topology update
    await manager.broadcast_log({
        "type": "topology_updated",
        "node_count": len(topology.nodes),
        "edge_count": len(topology.edges)
    })
    return current_topology

@app.post("/api/scenarios/run")
async def control_simulation(req: SimulationRequest):
    global simulation_running, active_scenario, simulation_interval_ms, active_ecosystem_mode
    simulation_running = req.running
    active_scenario = req.scenario
    if req.speed_ms:
        simulation_interval_ms = max(50, min(req.speed_ms, 5000))
    if req.ecosystem_mode:
        active_ecosystem_mode = req.ecosystem_mode
    return {
        "status": "success",
        "running": simulation_running,
        "scenario": active_scenario,
        "speed_ms": simulation_interval_ms,
        "ecosystem_mode": active_ecosystem_mode
    }

@app.get("/api/presets")
async def list_presets():
    return [
        {"id": "secure", "name": "Standard Secure Perimeter (Firewall + LB + Web + DB)", "mode": "mixed_vendor"},
        {"id": "bypassed", "name": "Bypassed Firewall (Shadow IT / Direct Wire)", "mode": "mixed_vendor"},
        {"id": "lateral", "name": "Flat Unsegmented Subnet (Ransomware Lateral Spread)", "mode": "mixed_vendor"},
        {"id": "cisco_campus", "name": "Mode A1: Cisco Campus Core Rogue AP & ISE Quarantine", "mode": "pure_cisco"},
        {"id": "cisco_sdwan", "name": "Mode A2: Cisco SD-WAN WAN Circuit Brownout & BGP Failover", "mode": "pure_cisco"},
        {"id": "cisco_aci", "name": "Mode A3: Cisco Data Center ACI Ingress Microburst", "mode": "pure_cisco"},
        {"id": "mixed_edge", "name": "Mode B1: Mixed-Vendor Edge Breach (Meraki -> Catalyst -> Palo Alto)", "mode": "mixed_vendor"},
        {"id": "mixed_sase", "name": "Mode B2: SASE Cloud Ingress Degradation (Zscaler -> Palo Alto -> Nexus)", "mode": "mixed_vendor"},
        {"id": "mixed_optical", "name": "Mode B3: Multicast/MPLS Backbone Optical Shift (Nokia -> Juniper -> Arista)", "mode": "mixed_vendor"}
    ]

@app.post("/api/presets/{preset_id}")
async def load_preset(preset_id: str):
    global current_topology
    if preset_id == "secure":
        current_topology = get_default_secure_topology()
    elif preset_id == "bypassed":
        current_topology = get_bypassed_topology()
    elif preset_id == "lateral":
        current_topology = get_lateral_topology()
    elif preset_id in ("cisco_campus", "cisco_campus_rogue"):
        current_topology = get_cisco_campus_topology()
    elif preset_id in ("cisco_sdwan", "cisco_sdwan_brownout"):
        current_topology = get_cisco_sdwan_topology()
    elif preset_id in ("cisco_aci", "cisco_aci_microburst"):
        current_topology = get_cisco_aci_topology()
    elif preset_id in ("mixed_edge", "mixed_edge_breach"):
        current_topology = get_mixed_edge_topology()
    elif preset_id in ("mixed_sase", "mixed_sase_degradation"):
        current_topology = get_mixed_sase_topology()
    elif preset_id in ("mixed_optical", "mixed_backbone_optical"):
        current_topology = get_mixed_optical_topology()
    else:
        return {"status": "error", "message": f"Unknown preset: {preset_id}"}
    
    await manager.broadcast_log({
        "type": "preset_loaded",
        "preset_id": preset_id,
        "node_count": len(current_topology.nodes)
    })
    return {"status": "success", "preset": preset_id, "topology": current_topology}

@app.get("/api/export-logs")
async def export_logs(format: str = Query("raw", enum=["raw", "json", "csv"])):
    if format == "json":
        data = [entry.dict() for entry in accumulated_logs]
        return Response(
            content=json.dumps(data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=splunk_topology_simulator_logs.json"}
        )
    elif format == "csv":
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)
        writer.writerow([
            "_time", "device_id", "sourcetype", "vendor", "node_type",
            "src_ip", "dest_ip", "protocol", "duration", "action", "signature", "status", "_raw"
        ])
        for entry in accumulated_logs:
            writer.writerow([
                entry.timestamp, entry.device_id, entry.sourcetype or "",
                entry.vendor, entry.node_type, entry.src_ip, entry.dest_ip,
                entry.protocol, entry.duration, entry.action, entry.signature,
                entry.status, entry.raw_log
            ])
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=splunk_topology_simulator_logs.csv"}
        )
    else:
        raw_text = "\n".join([entry.raw_log for entry in accumulated_logs])
        return Response(
            content=raw_text,
            media_type="text/plain",
            headers={"Content-Disposition": "attachment; filename=splunk_topology_simulator_logs.log"}
        )

@app.delete("/api/logs")
async def clear_logs():
    global accumulated_logs
    accumulated_logs = []
    return {"status": "success", "message": "Log buffer cleared"}


# =========================================================================
# NODE LIFECYCLE & POWER CONTROLS
# =========================================================================

@app.post("/api/nodes/{node_id}/power")
async def set_node_power(node_id: str, payload: Dict[str, str]):
    global current_topology
    power_str = payload.get("power_state", "running").lower()
    target_node = next((n for n in current_topology.nodes if n.id == node_id), None)
    if not target_node:
        return {"status": "error", "message": f"Node {node_id} not found"}

    try:
        new_state = NodePowerState(power_str)
        target_node.power_state = new_state
        if new_state == NodePowerState.STOPPED:
            target_node.status = "stopped"
        elif new_state == NodePowerState.PAUSED:
            target_node.status = "paused"
        elif new_state == NodePowerState.RUNNING:
            target_node.status = "active"
        
        await manager.broadcast({
            "type": "node_power_changed",
            "node_id": node_id,
            "power_state": new_state.value
        })
        return {
            "status": "success",
            "node_id": node_id,
            "power_state": new_state.value
        }
    except ValueError:
        return {"status": "error", "message": f"Invalid power state: {power_str}"}


@app.post("/api/nodes/{node_id}/hardware")
async def update_node_hardware(node_id: str, hardware: NodeHardware):
    global current_topology
    target_node = next((n for n in current_topology.nodes if n.id == node_id), None)
    if not target_node:
        return {"status": "error", "message": f"Node {node_id} not found"}

    target_node.hardware = hardware
    return {
        "status": "success",
        "node_id": node_id,
        "hardware": hardware.dict()
    }


# =========================================================================
# SECURITY ZONES MANAGEMENT
# =========================================================================

@app.get("/api/zones")
async def get_security_zones():
    global current_topology
    return {"zones": current_topology.zones}


@app.post("/api/zones")
async def create_or_update_zone(zone: ZoneAnnotation):
    global current_topology
    existing = next((z for z in current_topology.zones if z.id == zone.id), None)
    if existing:
        current_topology.zones = [z if z.id != zone.id else zone for z in current_topology.zones]
    else:
        current_topology.zones.append(zone)

    await manager.broadcast({
        "type": "zones_updated",
        "zone_count": len(current_topology.zones)
    })
    return {"status": "success", "zone": zone}


@app.delete("/api/zones/{zone_id}")
async def delete_zone(zone_id: str):
    global current_topology
    current_topology.zones = [z for z in current_topology.zones if z.id != zone_id]
    await manager.broadcast({
        "type": "zones_updated",
        "zone_count": len(current_topology.zones)
    })
    return {"status": "success", "message": f"Zone {zone_id} deleted"}


# =========================================================================
# DUAL TRANSPORT & SYSLOG CONFIGURATION
# =========================================================================

@app.post("/api/telemetry/test-syslog")
async def test_syslog_destination(req: SyslogTestRequest):
    test_msg = req.message or "RFC5424 Diagnostic Health Test from Network Telemetry Simulator"
    success, msg = dispatcher.emit_syslog(
        raw_message=test_msg,
        host=req.host,
        port=req.port,
        protocol=req.protocol,
        facility=16, # local0
        severity=6,  # informational
        hostname="sim-edge-01",
        app_name="splunk-simulator",
        syslog_format=req.format
    )
    return {
        "status": "success" if success else "error",
        "message": msg,
        "host": req.host,
        "port": req.port,
        "protocol": req.protocol
    }


@app.get("/api/telemetry/config")
async def get_telemetry_config():
    global current_topology
    return {
        "global_transport": current_topology.global_transport,
        "stats": dispatcher.stats
    }


@app.post("/api/telemetry/config")
async def set_telemetry_config(config: TelemetryTransportConfig):
    global current_topology
    current_topology.global_transport = config
    return {
        "status": "success",
        "message": "Telemetry transport updated",
        "global_transport": current_topology.global_transport
    }


@app.post("/api/faults/inject")
async def inject_fault_endpoint(req: FaultInjectionRequest):
    global current_topology, accumulated_logs
    try:
        record, logs, metrics = fault_engine.inject_fault(current_topology, req)
        # Broadcast each cascading log to WebSocket clients
        for entry in logs:
            accumulated_logs.append(entry)
            if len(accumulated_logs) > 500:
                accumulated_logs.pop(0)
            await manager.broadcast_log(entry.dict())

        # Also broadcast fault notification
        await manager.broadcast_log({
            "type": "fault_injected",
            "fault_id": record.id,
            "scenario_type": record.scenario_type.value,
            "description": record.description,
            "cascades_count": record.cascades_count,
            "affected_nodes": record.affected_nodes,
            "affected_edges": record.affected_edges
        })

        return {
            "status": "success",
            "record": record,
            "cascading_logs_count": len(logs),
            "metrics_count": len(metrics),
            "logs": logs[:10],
            "metrics": metrics[:5]
        }
    except Exception as e:
        return Response(status_code=400, content=json.dumps({"status": "error", "message": str(e)}), media_type="application/json")


@app.post("/api/faults/recover")
async def recover_fault_endpoint(req: FaultRecoveryRequest):
    global current_topology
    res = fault_engine.recover_fault(current_topology, req)
    await manager.broadcast_log({
        "type": "fault_recovered",
        "recovered_edges": res["recovered_edges"],
        "recovered_nodes": res["recovered_nodes"]
    })
    return res


@app.get("/api/faults/history")
async def get_fault_history():
    return {
        "active_faults": list(fault_engine.active_faults.values()),
        "fault_history": fault_engine.fault_history[-50:],
        "total_active": len(fault_engine.active_faults)
    }


@app.get("/api/openconfig/tree/{node_id}")
async def get_openconfig_tree(node_id: str):
    node = next((n for n in current_topology.nodes if n.id == node_id), None)
    if not node:
        return Response(status_code=404, content=json.dumps({"status": "error", "message": f"Node {node_id} not found"}), media_type="application/json")
    tree = yang_store.get_or_create_tree(node)
    return {
        "status": "success",
        "node_id": node_id,
        "hostname": node.name or node.id,
        "vendor": node.vendor,
        "tree": tree
    }


@app.post("/api/gnmi/sample")
async def trigger_gnmi_sample(node_id: Optional[str] = Query(None)):
    global current_topology
    nodes_to_sample = [n for n in current_topology.nodes if (not node_id or n.id == node_id)]
    all_metrics = []
    transport = current_topology.global_transport
    for n in nodes_to_sample:
        metrics = gnmi_server.generate_sample_telemetry(n)
        for m in metrics:
            all_metrics.append(m)
            if transport and transport.hec_enabled and transport.hec_url and transport.hec_token:
                dispatcher.emit_hec(m, transport.hec_url, transport.hec_token)

    return {
        "status": "success",
        "sampled_nodes": len(nodes_to_sample),
        "total_metrics_emitted": len(all_metrics),
        "target_index": "cisco_mdt_metrics",
        "metrics": all_metrics[:10]
    }



# =========================================================================
# SC4SNMP 300+ MIB LIBRARY & TRAP DISPATCHER
# =========================================================================

@app.get("/api/snmp/mibs")
async def get_snmp_mibs(
    vendor: Optional[str] = Query(None),
    module: Optional[str] = Query(None),
    search: Optional[str] = Query(None)
):
    mibs = snmp_engine.list_mibs(vendor=vendor, module=module, search=search)
    return {
        "status": "success",
        "total_count": len(mibs),
        "mibs": [m.model_dump() for m in mibs]
    }


@app.post("/api/snmp/trap")
async def trigger_snmp_trap(req: SNMPTrapTriggerRequest):
    global current_topology
    node = next((n for n in current_topology.nodes if n.id == req.target_node_id or n.name == req.host), None)
    if not node:
        node = Node(id="sim-node", name=req.host, type=NodeType.ROUTER, x=0, y=0, vendor="cisco")
    
    trap = snmp_engine.generate_trap(req.trap_name, node, req.varbind_overrides)
    transport = req.destinations or current_topology.global_transport
    results = dispatcher.dispatch_snmp_trap(trap, transport)
    
    # Broadcast to WebSocket log feed
    await manager.broadcast_log({
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(trap.timestamp)),
        "device_id": trap.host,
        "src_ip": node.ip_address,
        "dest_ip": "10.255.255.255",
        "protocol": "SNMP-TRAP",
        "duration": "0ms",
        "action": "alerted",
        "signature": f"SNMP TRAP {trap.trap_name}",
        "status": "degraded",
        "raw_log": f"SNMP-COMMUNITY=public TRAP-TYPE={trap.trap_name} OID={trap.trap_oid} SEVERITY={trap.severity.upper()}",
        "node_type": node.type.value,
        "node_id": node.id,
        "vendor": node.vendor,
        "sourcetype": "sc4snmp:event"
    })
    
    return {
        "status": "success",
        "trap": trap.model_dump(),
        "dispatch_results": results
    }


@app.post("/api/snmp/poll")
async def trigger_snmp_poll(req: SNMPPollRequest):
    global current_topology
    node = next((n for n in current_topology.nodes if n.id == req.target_node_id or n.name == req.host), None)
    if not node:
        node = Node(id="sim-node", name=req.host, type=NodeType.SWITCH, x=0, y=0, vendor="cisco")

    module = req.mib_module or "IF-MIB"
    metrics = snmp_engine.simulate_snmp_poll(node, module=module)
    transport = req.destinations or current_topology.global_transport
    
    for m in metrics:
        dispatcher.dispatch_snmp_metric(m, transport)

    return {
        "status": "success",
        "polled_module": module,
        "metrics_count": len(metrics),
        "target_index": "cisco_mdt_metrics",
        "metrics": metrics[:10]
    }


@app.post("/api/telemetry/test-pipeline")
async def test_pipeline_endpoint(req: PipelineTestRequest):
    ok, msg = dispatcher.test_pipeline(req.pipeline, req.config)
    return {
        "pipeline": req.pipeline,
        "success": ok,
        "message": msg
    }


@app.get("/api/openconfig/export/{node_id}")
async def export_openconfig_rfc7951(node_id: str):
    node = next((n for n in current_topology.nodes if n.id == node_id), None)
    if not node:
        return Response(status_code=404, content=json.dumps({"error": "Node not found"}), media_type="application/json")
    tree = yang_store.get_or_create_tree(node)
    return Response(
        content=json.dumps(tree, indent=2),
        media_type="application/yang-data+json",
        headers={"Content-Disposition": f"attachment; filename=openconfig_{node_id}.json"}
    )


# Vendor Catalog Endpoint
@app.get("/api/vendors/catalog")
def get_vendor_catalog(id: Optional[str] = None):
    from app.vendor_catalog import list_all_vendors, get_vendor_by_id
    if id:
        v = get_vendor_by_id(id)
        if not v:
            raise HTTPException(status_code=404, detail="Vendor not found")
    return {"vendors": list_all_vendors(), "count": len(list_all_vendors())}


# SPL Query Playground Endpoint
@app.post("/api/spl/query")
def execute_spl_query(payload: Dict[str, Any]):
    from app.spl_engine import spl_engine
    query = payload.get("query", "*")
    input_events = payload.get("events")
    if not input_events:
        input_events = [e.dict() if hasattr(e, "dict") else e for e in list(accumulated_logs)]
    return spl_engine.execute(query, input_events)


# NOC & SOC Metrics Endpoints
@app.get("/api/metrics/noc_soc")
def get_noc_soc_metrics(is_degraded: bool = False, is_under_attack: bool = False):
    from app.noc_soc_metrics import metric_engine
    from datetime import datetime, timezone
    return {
        "noc": metric_engine.generate_noc_metrics(is_degraded=is_degraded),
        "soc": metric_engine.generate_soc_metrics(is_under_attack=is_under_attack),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/api/metrics/blueprints")
def get_metric_blueprints():
    from app.noc_soc_metrics import metric_engine
    return metric_engine.get_frequency_blueprints()


# Use Case Repository & Test Harness Endpoints
@app.get("/api/use_cases")
def list_use_cases():
    from app.use_case_repo import use_case_harness
    return {"use_cases": use_case_harness.list_use_cases(), "count": len(use_case_harness.list_use_cases())}


@app.post("/api/use_cases/{uc_id}/test")
def run_use_case_test(uc_id: str):
    from app.use_case_repo import use_case_harness
    raw_evs = [e.dict() if hasattr(e, "dict") else e for e in list(accumulated_logs)]
    res = use_case_harness.run_use_case_test(uc_id, topology=current_topology, events=raw_evs)
    return res


# WebSocket Endpoint
@app.websocket("/ws/logs")
async def websocket_logs_endpoint(websocket: WebSocket):
    global simulation_running, active_scenario, current_topology
    await manager.connect(websocket)
    try:
        # Send initial handshake
        await websocket.send_json({
            "type": "connection_established",
            "message": "Connected to Splunk Network Simulator Log Feed",
            "simulation_running": simulation_running,
            "scenario": active_scenario
        })
        while True:
            # Receive client interactions (e.g. topology mutations or play/pause)
            data_text = await websocket.receive_text()
            try:
                data = json.loads(data_text)
                action = data.get("action")
                if action == "toggle_play":
                    simulation_running = not simulation_running
                    await websocket.send_json({"type": "simulation_state", "running": simulation_running})
                elif action == "set_scenario":
                    active_scenario = ScenarioType(data.get("scenario", "normal_traffic"))
                    await websocket.send_json({"type": "scenario_state", "scenario": active_scenario})
                elif action == "update_topology":
                    current_topology = TopologyState(**data.get("topology", {}))
            except Exception as e:
                print(f"WS message error: {e}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)


# Static frontend mounting for self-contained operation
FRONTEND_DIST_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))

if os.path.exists(FRONTEND_DIST_DIR):
    assets_dir = os.path.join(FRONTEND_DIST_DIR, "assets")
    if os.path.exists(assets_dir):
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith("api/") or full_path.startswith("ws/"):
            return Response(status_code=404)
        file_path = os.path.join(FRONTEND_DIST_DIR, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(FRONTEND_DIST_DIR, "index.html"))

