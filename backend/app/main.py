"""
FastAPI Server & WebSocket Gateway
Provides REST APIs for topology management, scenario control, log export,
and real-time WebSocket streaming at 500ms intervals.
"""

import asyncio
import json
from pathlib import Path
import re
import time
import csv
import io
import os
import urllib.error
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Dict, Set, Optional, Any, Union
from pydantic import BaseModel
from fastapi import APIRouter, FastAPI, WebSocket, WebSocketDisconnect, Query, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles
from starlette.responses import FileResponse
from app.models import (
    SNMPTrapTriggerRequest, SNMPPollRequest, PipelineTestRequest,
    TopologyState, Node, Edge, NodeType, ScenarioType,
    LogEntry, SimulationRequest, EcosystemMode,
    ZoneAnnotation, NodePowerState, NodeHardware,
    TelemetryTransportConfig, SyslogTestRequest,
    FaultScenarioType, FaultInjectionRequest, FaultRecoveryRequest, FaultEventRecord,
    ScenarioRunRequest, RunManifest, ScenarioContract, ValidationRule, ValidationResult,
    ValidationStatus
)
from app.transport_credential_updates import (
    CredentialUpdateError, update_shared_transport,
)
from app.telemetry_config_api import (
    TelemetryConfigRoute, TelemetryConfigUpdate, CONFIG_UPDATE_RESPONSES,
    invalid_update_error,
)
from app.telemetry_dispatcher import dispatcher
from app.scenario_runner import ScenarioRunner, SUPPORTED_SCENARIO_IDS
from app.authentic_scenario_packs import SCENARIO_PACK_IDS
from netspout_core.incident_packs import catalog as incident_catalog
from app.run_progress import RunProgressTracker, RunProgressState
from app.unified_generation import (
    GenerationMode,
    UnifiedGenerationRequest,
    UnifiedGenerationService,
)
from app.scenario_studio import (
    CustomSourceDraft,
    SampleAnalysisRequest,
    ScenarioStudioService,
    StudioDraftRequest,
    StudioRunRequest,
    StudioScenarioPack,
)
from app.industry_packs import IndustrySelection
from app.vendor_coverage import VendorCoverageService
from app.cisco_scenario_factory import CiscoScenarioFactoryService, ScenarioMaturity
from app.graph_engine import TopologyGraph
from app.gnmi_engine import yang_store, gnmi_server
from app.snmp_engine import snmp_engine
from app.fault_injection_engine import fault_engine

# Import destination management
from app.destination_manager import destination_manager
from app.destination_api import router as destination_router

from app.release_candidate import (
    ReleaseCandidateConfiguration,
    SecuritySourceCatalog,
)
from app.use_case_explorer import UseCaseExplorer, load_candidates, load_curated_stories, load_taxonomy
from app.security_content_lab import (
    SUPPORTED_RUNTIME_DETECTIONS,
    validate_index_name,
    AttackDataReplayService,
    DetectionEvidenceStore,
    DetectionValidationOrchestrator,
    SecurityContentCatalog,
)

# Enhanced scenario run model
class EnhancedScenarioRunRequest(BaseModel):
    """Enhanced scenario run request with destination configuration."""
    scenario_id: str
    destination_id: Optional[str] = None
    start_immediately: bool = True
    seed: Optional[int] = None
    duration_minutes: Optional[int] = None

@asynccontextmanager
async def lifespan(_: FastAPI):
    global simulation_task
    simulation_task = asyncio.create_task(run_simulation_loop())
    try:
        yield
    finally:
        if simulation_task:
            simulation_task.cancel()


app = FastAPI(
    title="NetSpout Telemetry & Simulation API",
    version="2.0.0",
    lifespan=lifespan,
)

# Enable CORS for frontend development server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[],
    allow_origin_regex=r"https?://(?:localhost|127\.0\.0\.1|\[::1\])(?::\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include destination router
app.include_router(destination_router)

# Global Simulation State
scenario_runner = ScenarioRunner()

# Initialize progress tracker first
progress_tracker = None

# Define broadcast function before use
async def broadcast_progress_event(event):
    """Broadcast progress events to WebSocket clients."""
    from app.run_progress import RunProgressEvent
    event_dict = event.to_dict()
    await manager.broadcast({
        "type": "run_progress",
        **event_dict
    })

# Progress-aware scenario runner
try:
    from app.progress_scenario_runner_v2 import ProgressScenarioRunner
    from app.run_progress import RunProgressTracker
    
    # Create progress tracker
    progress_tracker = RunProgressTracker(broadcast_callback=broadcast_progress_event)
    progress_scenario_runner = ProgressScenarioRunner(scenario_runner, progress_tracker)
except ImportError as e:
    print(f"Note: ProgressScenarioRunner not available: {e}")
    # Fallback if module not available
    progress_scenario_runner = None
    progress_tracker = None
unified_generation_service = UnifiedGenerationService(dispatcher=dispatcher)
scenario_studio_service = ScenarioStudioService(
    catalog=unified_generation_service.catalog,
    generation_service=unified_generation_service,
)
industry_pack_service = unified_generation_service.catalog.get_industry_pack_service()
dashboard_recipe_service = (
    unified_generation_service.catalog.get_dashboard_recipe_service()
)
_coverage_catalog = unified_generation_service.catalog.get_telemetry_catalog()
vendor_coverage_service = VendorCoverageService(
    registry=unified_generation_service.registry,
    source_ids={item["source_id"] for item in _coverage_catalog["sources"]},
    integration_ids={
        item["integration_id"] for item in _coverage_catalog["integrations"]
    },
)
cisco_scenario_factory_service = CiscoScenarioFactoryService()
security_source_catalog = SecuritySourceCatalog()
release_candidate_configuration = ReleaseCandidateConfiguration()
security_content_catalog = SecurityContentCatalog()
attack_data_replay_service = AttackDataReplayService(
    security_content_catalog,
    dispatcher,
)
detection_evidence_store = DetectionEvidenceStore()
detection_validation_orchestrator = DetectionValidationOrchestrator(
    security_content_catalog,
    lambda query: release_candidate_configuration.execute_read_only_search(query),
    detection_evidence_store,
)
def _connection_center_search_target():
    """(search_url, Authorization header) from Connection Center, or None so callers fall back to env vars."""
    config = release_candidate_configuration.load()
    if not config.get("configured") or not release_candidate_configuration.secrets.search_secret:
        return None
    return config["search_url"], release_candidate_configuration._search_authorization(config)


unified_generation_service.search_provider = _connection_center_search_target
scenario_runner.search_provider = _connection_center_search_target
active_scenario: ScenarioType = ScenarioType.NORMAL_TRAFFIC
active_ecosystem_mode: EcosystemMode = EcosystemMode.MIXED_VENDOR
simulation_running: bool = False
simulation_interval_ms: int = 500
accumulated_logs: List[LogEntry] = []
MAX_LOG_HISTORY: int = 2000

# =========================================================================
# LIVE SIMULATION GUARD (D3)
# =========================================================================
# Only these 10 scenarios have dedicated telemetry in scenario_runner.execute_step
LIVE_SIMULATION_SCENARIOS = {
    ScenarioType.NORMAL_TRAFFIC,
    ScenarioType.DDOS_ATTACK,
    ScenarioType.SQL_INJECTION,
    ScenarioType.LATERAL_MOVEMENT,
    ScenarioType.CISCO_CAMPUS_ROGUE,
    ScenarioType.CISCO_SDWAN_BROWNOUT,
    ScenarioType.CISCO_ACI_MICROBURST,
    ScenarioType.MIXED_EDGE_BREACH,
    ScenarioType.MIXED_SASE_DEGRADATION,
    ScenarioType.MIXED_BACKBONE_OPTICAL,
}


def _live_simulation_refusal_detail(scenario_id: str) -> str:
    if scenario_id in SUPPORTED_SCENARIO_IDS:
        return (
            f"Scenario '{scenario_id}' is not supported by the live-simulation workflow. "
            "Only scenarios with dedicated telemetry can be used. "
            f"Use POST /api/scenarios/{scenario_id}/run for native engine scenarios."
        )
    return (
        f"Scenario '{scenario_id}' is not available in this release (live-simulation)."
    )

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
            if simulation_running and active_scenario in LIVE_SIMULATION_SCENARIOS:
                logs = scenario_runner.execute_step(current_topology, active_scenario)
                transport = getattr(current_topology, "global_transport", None)
                for entry in logs:
                    accumulated_logs.append(entry)
                    if len(accumulated_logs) > MAX_LOG_HISTORY:
                        accumulated_logs.pop(0)
                    await manager.broadcast_log(entry.dict())
                    if transport and getattr(transport, "hec_enabled", False):
                        try:
                            dispatcher.dispatch_log(entry, transport)
                        except Exception:
                            pass
            await asyncio.sleep(simulation_interval_ms / 1000.0)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"Simulation loop error: {e}")
            await asyncio.sleep(1.0)

# REST API Endpoints
@app.get("/api/health")
async def health_check():
    """Enhanced health check with destination status."""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "simulation_running": simulation_running,
        "active_scenario": active_scenario.value if active_scenario else None,
        "destination_count": len(destination_manager.destinations),
        "active_destination": destination_manager.active_destination_id,
        "destinations": [
            {
                "id": dest_id,
                "name": dest.name,
                "deployment_type": dest.deployment_type,
                "validation_status": dest.validation_status,
                "is_active": dest_id == destination_manager.active_destination_id
            }
            for dest_id, dest in destination_manager.destinations.items()
        ]
    }

@app.get("/api/destinations/active/transport-config")
async def get_active_transport_config():
    """Get transport config for active destination."""
    transport = destination_manager.get_active_transport_config()
    if not transport:
        raise HTTPException(status_code=404, detail="No active destination configured")

    return transport

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
    # The backend owns the destination and its credentials (Connection Center / /api/telemetry/config). A topology
    # sync from the UI carries an empty transport and must not wipe them.
    previous = getattr(current_topology, "global_transport", None)
    current_topology = topology
    if previous is not None:
        current_topology.global_transport = previous
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
    if req.scenario not in LIVE_SIMULATION_SCENARIOS:
        raise HTTPException(
            status_code=400,
            detail=_live_simulation_refusal_detail(req.scenario.value)
        )
    simulation_running = req.running
    active_scenario = req.scenario
    if req.speed_ms:
        simulation_interval_ms = max(50, min(req.speed_ms, 5000))
    if req.ecosystem_mode:
        active_ecosystem_mode = req.ecosystem_mode
    await manager.broadcast({
        "type": "simulation_state",
        "running": simulation_running,
        "scenario": active_scenario,
        "speed_ms": simulation_interval_ms
    })
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
        {"id": "cisco_campus", "name": "Cisco Campus Core Rogue AP & ISE Quarantine", "mode": "pure_cisco"},
        {"id": "cisco_sdwan", "name": "Cisco SD-WAN WAN Circuit Brownout & BGP Failover", "mode": "pure_cisco"},
        {"id": "cisco_aci", "name": "Cisco Data Center ACI Ingress Microburst", "mode": "pure_cisco"},
        {"id": "mixed_edge", "name": "Mixed-Vendor Edge Breach (Meraki -> Catalyst -> Palo Alto)", "mode": "mixed_vendor"},
        {"id": "mixed_sase", "name": "SASE Cloud Ingress Degradation (Zscaler -> Palo Alto -> Nexus)", "mode": "mixed_vendor"},
        {"id": "mixed_optical", "name": "Multicast/MPLS Backbone Optical Shift (Nokia -> Juniper -> Arista)", "mode": "mixed_vendor"}
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


telemetry_config_router = APIRouter(route_class=TelemetryConfigRoute)


@telemetry_config_router.post("/api/telemetry/config", responses=CONFIG_UPDATE_RESPONSES)
async def set_telemetry_config(config: TelemetryConfigUpdate):
    global current_topology
    try:
        payload = (config.model_dump(exclude_unset=True) if hasattr(config, "model_dump")
                   else config.dict(exclude_unset=True))
        candidate = update_shared_transport(
            current_topology.global_transport, payload, TelemetryTransportConfig
        )
    except CredentialUpdateError:
        raise invalid_update_error() from None
    current_topology.global_transport = candidate
    return {
        "status": "success",
        "message": "Telemetry transport updated",
        "global_transport": current_topology.global_transport
    }


app.include_router(telemetry_config_router)

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


class ConnectionTestPayload(BaseModel):
    endpoint: Optional[str] = None
    hec_url: Optional[str] = None
    token: Optional[str] = None
    hec_token: Optional[str] = None
    index: Optional[str] = None
    hec_index: Optional[str] = None
    pipeline: str = "hec"
    allow_insecure_tls: bool = False
    ssl_verify: bool = True
    config: Optional[TelemetryTransportConfig] = None


class SetupConfigurationPayload(BaseModel):
    deployment_mode: str
    splunk_deployment_type: str
    hec_url: str
    search_url: str
    auth_method: str
    search_username: Optional[str] = None
    hec_token: Optional[str] = None
    search_secret: Optional[str] = None
    indexes: List[str]
    collectors: List[str] = []
    guided_sample: bool = True
    allow_insecure_tls: bool = False


class AttackDataRetrievePayload(BaseModel):
    dataset_path: str


class AttackDataReplayPayload(BaseModel):
    local_id: str
    dataset_path: str
    index: str
    timestamp_mode: str = "PRESERVE"


class DetectionValidationPayload(BaseModel):
    detection_id: str
    run_id: str
    index: str
    expected_min_matches: int = 1
    control: str = "POSITIVE"
    dataset_or_scenario_id: str
    indexed_event_count: int


@app.post("/api/telemetry/test-connection")
@app.post("/api/telemetry/test-hec")
@app.post("/api/telemetry/test-pipeline")
async def test_connection_endpoint(req: Union[ConnectionTestPayload, PipelineTestRequest, Dict[str, Any]]):
    global current_topology
    if isinstance(req, PipelineTestRequest):
        pipeline = req.pipeline
        transport = req.config
    elif isinstance(req, ConnectionTestPayload):
        pipeline = req.pipeline
        if req.config:
            transport = req.config
        else:
            def_url = current_topology.global_transport.hec_url if current_topology and current_topology.global_transport else "https://localhost:8888/services/collector"
            def_tok = current_topology.global_transport.hec_token if current_topology and current_topology.global_transport else ""
            def_idx = current_topology.global_transport.hec_index if current_topology and current_topology.global_transport else "idx_network_ops"
            transport = TelemetryTransportConfig(
                hec_url=req.endpoint or req.hec_url or def_url,
                hec_token=req.token or req.hec_token or def_tok,
                hec_index=req.index or req.hec_index or def_idx,
                hec_ssl_verify=req.ssl_verify,
                hec_allow_insecure_tls=req.allow_insecure_tls
            )
    else:
        d = dict(req) if isinstance(req, dict) else {}
        pipeline = d.get("pipeline", "hec")
        transport = TelemetryTransportConfig(
            hec_url=d.get("endpoint") or d.get("hec_url") or "https://localhost:8888/services/collector",
            hec_token=d.get("token") or d.get("hec_token") or "",
            hec_index=d.get("index") or d.get("hec_index") or "idx_network_ops",
            hec_ssl_verify=d.get("ssl_verify", True),
            hec_allow_insecure_tls=d.get("allow_insecure_tls", False)
        )

    if current_topology:
        current_topology.global_transport = transport

    result = dispatcher.test_connection(transport, pipeline=pipeline)
    return {
        "status": result.get("status", result["state"]),
        "state": result["state"],
        "stage": result["stage"],
        "reachable": result["reachable"],
        "authenticated": result["authenticated"],
        "event_accepted": result["event_accepted"],
        "target_index": result["target_index"],
        "message": result["message"],
        "success": result["state"] in ("VERIFIED", "REACHABLE"),
        "latency_ms": 4
    }


@app.get("/api/scenarios/runs/{run_id}/observation")
async def get_run_observation(run_id: str):
    global current_topology
    transport = current_topology.global_transport if current_topology and getattr(current_topology, "global_transport", None) else TelemetryTransportConfig()
    status, count = scenario_runner.check_destination_observation(run_id, transport)
    manifest = scenario_runner.get_run(run_id)
    evidence = scenario_runner.get_run_evidence(run_id, transport) if hasattr(scenario_runner, "get_run_evidence") else None
    if manifest:
        manifest.observed_count = count
        manifest.observation_status = status
        if evidence:
            manifest.evidence_summary = evidence
            manifest.event_observed_count = evidence.event_observed_count
            manifest.metric_observed_count = evidence.metric_observed_count
            manifest.observation_completeness_pct = evidence.observation_completeness_pct
        # PASS only when the REQUIRED destinations were observed (a supporting-only hit is not enough).
        if (evidence.required_evidence_satisfied if evidence else count > 0):
            manifest.destination_validation = "PASS"
            if manifest.overall_validation in ("BLOCKED", "FAIL"):
                all_pass = all(r.status == ValidationStatus.PASS for r in manifest.validation_results)
                manifest.overall_validation = "PASS" if all_pass else "FAIL"
    return {
        "run_id": run_id,
        "observed_count": count,
        "observation_status": status,
        "schema_version": evidence.schema_version if evidence else None,
        "observed_at": evidence.observed_at if evidence else None,
        "required_evidence_satisfied": evidence.required_evidence_satisfied if evidence else False,
        "destination_validation": manifest.destination_validation if manifest else ("PASS" if (evidence.required_evidence_satisfied if evidence else count > 0) else "FAIL"),
        "event_observed_count": evidence.event_observed_count if evidence else count,
        "metric_observed_count": evidence.metric_observed_count if evidence else 0,
        "observation_completeness_pct": evidence.observation_completeness_pct if evidence else 0.0,
        "destinations": [d.dict() for d in evidence.destinations] if evidence else [],
        "evidence_summary": evidence.dict() if evidence else None
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


# =========================================================================
# Gate 4: Scenario Contract & Lifecycle API Endpoints
# =========================================================================

@app.get("/api/scenarios")
def list_catalog_scenarios(category: Optional[str] = None, ecosystem: Optional[str] = None):
    from app.catalog import catalog
    scenarios = catalog.list_scenarios(category=category, ecosystem=ecosystem)
    return {"scenarios": scenarios, "count": len(scenarios)}


@app.get("/api/use-cases")
def list_catalog_use_cases(category: Optional[str] = None):
    from app.catalog import catalog
    from app.use_case_repo import USE_CASES as PRE_BUILT_USE_CASES
    
    use_cases = []
    # 1. Add 29 scenario-bound use cases
    for s in catalog.list_scenarios():
        sc_id = s.get("id")
        sc_name = s.get("name")
        sc_cat = s.get("category", "NETWORK_OPERATIONS")
        sc_desc = s.get("description", "")
        sc_diff = s.get("difficulty", "INTERMEDIATE")
        sc_duration = s.get("estimated_duration_sec", 30)
        sc_vendors = s.get("vendor_scope", [])
        sc_sourcetypes = s.get("sourcetypes", [])
        uc_data = s.get("use_case", {})
        
        uc_entry = {
            "id": f"uc-{sc_id}",
            "scenario_id": sc_id,
            "name": sc_name,
            "category": sc_cat,
            "domain": sc_cat.replace("_", " ").title(),
            "difficulty": sc_diff,
            "estimated_runtime_sec": sc_duration,
            "vendors": sc_vendors,
            "sourcetypes": sc_sourcetypes,
            "description": sc_desc,
            "objective": uc_data.get("objective", sc_desc) if uc_data else sc_desc,
            "expected_observations": uc_data.get("expected_observations", s.get("expected_observations", [])) if uc_data else s.get("expected_observations", []),
            "validation_rules": s.get("validation_rules", []),
            "default_topology_id": s.get("default_topology_id") or s.get("topology_id", "default_secure"),
            "phases": s.get("phases", []),
            "source": "SCENARIO_BOUND",
            "maturity": s.get("maturity", "CONTRACTED"),
            "telemetry_model": s.get("telemetry_model") or "Standard Telemetry Payload",
            "transport_protocol": s.get("transport_protocol") or "Splunk HEC",
            "splunk_storage": s.get("splunk_storage") or "Splunk Event Index",
            "fidelity_badge": s.get("fidelity_badge") or "MODELED PAYLOAD",
            "telemetry_notes": s.get("telemetry_notes"),
            "native_snmp_supported": bool(s.get("native_snmp_supported", False)),
            "native_snmp_capabilities": s.get("native_snmp_capabilities"),
            "telemetry_requirements": s.get("telemetry_requirements", []),
            "affected_entities": s.get("affected_entities", []),
            "timing_claim": s.get("timing_claim"),
            "timing_value": s.get("timing_value"),
            "timing_unit": s.get("timing_unit"),
            "timing_classification": s.get("timing_classification", "NOT_APPLICABLE"),
            "timing_notes": s.get("timing_notes")
        }
        use_cases.append(uc_entry)
        
    # 2. Add 10 pre-built NOC/SOC production use cases
    for pb in PRE_BUILT_USE_CASES:
        uc_entry = {
            "id": pb.get("id"),
            "scenario_id": pb.get("fault_scenario"),
            "name": pb.get("name"),
            "category": "SECURITY" if "SOC" in pb.get("domain", "") or (pb.get("severity") in ("critical", "high") and "Security" in pb.get("domain", "")) else "NETWORK_OPERATIONS",
            "domain": pb.get("domain", "NOC Operations"),
            "difficulty": "ADVANCED" if pb.get("severity") == "critical" else "INTERMEDIATE",
            "estimated_runtime_sec": 30,
            "vendors": pb.get("vendors", []),
            "sourcetypes": pb.get("target_sourcetypes", []),
            "description": pb.get("description", ""),
            "objective": f"Demonstrate operational response to {pb.get('name')}.",
            "expected_observations": [pb.get("expected_cim_model", "")] if pb.get("expected_cim_model") else [],
            "validation_rules": [
                {
                    "id": f"{pb.get('id')}-rule-01",
                    "name": "Target Sourcetype Emitted",
                    "type": "COUNT_THRESHOLD",
                    "target_sourcetype": pb.get("target_sourcetypes", ["cisco:ios:syslog"])[0],
                    "min_count": pb.get("assertions", {}).get("min_events", 1),
                    "description": pb.get("verification_spl", "")
                }
            ],
            "default_topology_id": "default_secure",
            "phases": [],
            "source": "PRE_BUILT_REPO",
            "telemetry_model": pb.get("telemetry_model", "Standard Telemetry Payload"),
            "transport_protocol": "Splunk HEC",
            "splunk_storage": "Splunk Event Index",
            "fidelity_badge": "MODELED PAYLOAD",
            "telemetry_notes": None,
            "native_snmp_supported": False,
            "native_snmp_capabilities": None,
            "telemetry_requirements": [],
            "affected_entities": []
        }
        use_cases.append(uc_entry)
        
    if category:
        use_cases = [u for u in use_cases if u.get("category", "").upper() == category.upper()]
        
    return {"use_cases": use_cases, "count": len(use_cases)}



@app.get("/api/scenarios/run/active")
def get_active_scenario_run():
    active = scenario_runner.get_active_run()
    if not active:
        return {"active": False, "manifest": None}
    return {"active": True, "manifest": active.dict() if hasattr(active, "dict") else active}


@app.post("/api/scenarios/run/stop")
def stop_active_scenario_run(run_id: Optional[str] = None):
    if not run_id:
        active = scenario_runner.get_active_run()
        run_id = active.run_id if active else None
    if not run_id:
        return {"status": "no_active_run", "stopped": False}
    stopped = scenario_runner.stop_run(run_id)
    return {"status": "stopped" if stopped else "not_found", "run_id": run_id, "stopped": stopped}


@app.get("/api/scenarios/runs/{run_id}")
def get_scenario_run_manifest(run_id: str):
    manifest = scenario_runner.get_run(run_id)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    return manifest.dict() if hasattr(manifest, "dict") else manifest


@app.get("/api/scenarios/runs/{run_id}/logs")
def get_scenario_run_logs(run_id: str, limit: int = 100):
    manifest = scenario_runner.get_run(run_id)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    logs = scenario_runner.get_run_logs(run_id)
    if limit and limit > 0:
        logs = logs[:limit]
    return {
        "run_id": run_id,
        "count": len(logs),
        "logs": [l.dict() if hasattr(l, "dict") else l for l in logs]
    }



@app.post("/api/scenarios/runs/{run_id}/validate")
def validate_scenario_run(run_id: str):
    manifest = scenario_runner.get_run(run_id)
    if not manifest:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")
    results = scenario_runner.validate_manifest(run_id)
    return {
        "run_id": run_id,
        "overall_validation": manifest.overall_validation,
        "results": [r.dict() if hasattr(r, "dict") else r for r in results]
    }


@app.get("/api/scenarios/{scenario_id}")
def get_catalog_scenario(scenario_id: str):
    from app.catalog import catalog
    sc = catalog.get_scenario(scenario_id)
    if not sc:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")
    contract = catalog.get_scenario_contract(scenario_id)
    return contract.dict() if hasattr(contract, "dict") else contract


@app.post("/api/scenarios/{scenario_id}/run")
def run_scenario_contract(
    scenario_id: str,
    payload: Optional[Dict[str, Any]] = None,
    seed: Optional[int] = None,
    time_mode: str = "TEST",
    topology_id: Optional[str] = None
):
    global current_topology
    dispatch_telemetry = True
    transport_config = current_topology.global_transport if current_topology and current_topology.global_transport else TelemetryTransportConfig()
    transport_mode = "DIRECT_TO_SPLUNK"
    native_protocol: Optional[str] = None
    native_destination_host: Optional[str] = None
    native_destination_port: Optional[int] = None
    native_rate_pps: Optional[int] = 100
    native_snmp_pdu_mode: Optional[str] = None
    native_snmp_community: Optional[str] = "netspout-lab"
    native_snmp_timeout_ms: Optional[int] = 1500
    native_snmp_max_retries: Optional[int] = 2
    native_snmp_e2e: bool = False
    native_gnmi_e2e: bool = False
    native_gnmi_target_device: Optional[str] = None

    if payload:
        seed = payload.get("seed", seed)
        time_mode = payload.get("time_mode", payload.get("mode", time_mode))
        topology_id = payload.get("topology_id", topology_id)
        if "dispatch_telemetry" in payload:
            dispatch_telemetry = bool(payload["dispatch_telemetry"])
        if "transport_config" in payload and payload["transport_config"]:
            transport_config = _authorize_caller_transport(payload["transport_config"])
            if current_topology and not release_candidate_configuration.load().get("configured"):
                current_topology.global_transport = transport_config  # legacy lab behavior only; never replaces a saved Connection Center destination
        if "transport_mode" in payload and payload["transport_mode"] is not None:
            transport_mode = str(payload["transport_mode"])
        if "native_protocol" in payload:
            native_protocol = payload["native_protocol"]
        if "native_destination_host" in payload:
            native_destination_host = payload["native_destination_host"]
        if "native_destination_port" in payload and payload["native_destination_port"] is not None:
            try:
                native_destination_port = int(payload["native_destination_port"])
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid native_destination_port: {payload['native_destination_port']}",
                )
        if "native_rate_pps" in payload and payload["native_rate_pps"] is not None:
            native_rate_pps = int(payload["native_rate_pps"])
        if "native_snmp_pdu_mode" in payload:
            native_snmp_pdu_mode = payload["native_snmp_pdu_mode"]
        if "native_snmp_community" in payload:
            native_snmp_community = payload["native_snmp_community"]
        if "native_snmp_timeout_ms" in payload and payload["native_snmp_timeout_ms"] is not None:
            native_snmp_timeout_ms = int(payload["native_snmp_timeout_ms"])
        if "native_snmp_max_retries" in payload and payload["native_snmp_max_retries"] is not None:
            native_snmp_max_retries = int(payload["native_snmp_max_retries"])
        if "native_snmp_e2e" in payload:
            native_snmp_e2e = bool(payload["native_snmp_e2e"])
        if "native_gnmi_e2e" in payload:
            native_gnmi_e2e = bool(payload["native_gnmi_e2e"])
        if "native_gnmi_target_device" in payload:
            native_gnmi_target_device = payload["native_gnmi_target_device"]

    req = ScenarioRunRequest(
        scenario_id=scenario_id,
        seed=seed,
        time_mode=time_mode,
        topology_id=topology_id,
        dispatch_telemetry=dispatch_telemetry,
        transport_config=transport_config,
        transport_mode=transport_mode,
        native_protocol=native_protocol,
        native_destination_host=native_destination_host,
        native_destination_port=native_destination_port,
        native_rate_pps=native_rate_pps,
        native_snmp_pdu_mode=native_snmp_pdu_mode,
        native_snmp_community=native_snmp_community,
        native_snmp_timeout_ms=native_snmp_timeout_ms,
        native_snmp_max_retries=native_snmp_max_retries,
        native_snmp_e2e=native_snmp_e2e,
        native_gnmi_e2e=native_gnmi_e2e,
        native_gnmi_target_device=native_gnmi_target_device,
    )
    try:
        manifest = scenario_runner.run_scenario(req)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return manifest.dict() if hasattr(manifest, "dict") else manifest


@app.post("/api/scenarios/run-with-destination")
def run_scenario_with_destination(req: EnhancedScenarioRunRequest):
    dest_id = req.destination_id or destination_manager.active_destination_id
    dest = destination_manager.destinations.get(dest_id)
    if not dest:
        raise HTTPException(404, "Destination not found")
    transport = dest.to_transport_config()
    if not dest.enabled or not transport.hec_token:
        raise HTTPException(400, "Destination disabled or HEC credential unavailable")
    try:
        manifest = scenario_runner.run_scenario(ScenarioRunRequest(
            scenario_id=req.scenario_id, seed=req.seed, time_mode="TEST",
            dispatch_telemetry=True, transport_config=transport,
        ))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    from app.live_dashboard import observe_run
    observe_run(manifest, dest)
    destination_manager.record_event_sent(dest_id, manifest.dispatch_succeeded)
    return manifest.model_dump(mode="json")

@app.post("/api/scenarios/run-with-progress")
async def run_scenario_with_progress(req: EnhancedScenarioRunRequest):
    """Run scenario with real-time progress tracking."""
    dest_id = req.destination_id or destination_manager.active_destination_id
    dest = destination_manager.destinations.get(dest_id)
    if not dest:
        raise HTTPException(404, "Destination not found")
    transport = dest.to_transport_config()
    if not dest.enabled or not transport.hec_token:
        raise HTTPException(400, "Destination disabled or HEC credential unavailable")
    
    try:
        if progress_scenario_runner:
            # Use progress-aware runner
            manifest = await progress_scenario_runner.run_scenario_with_progress(
                ScenarioRunRequest(
                    scenario_id=req.scenario_id, 
                    seed=req.seed, 
                    time_mode="TEST",
                    dispatch_telemetry=True, 
                    transport_config=transport,
                ),
                destination_info={
                    "name": dest.name,
                    "type": dest.type,
                    "url": dest.url
                }
            )
        else:
            # Fallback to regular runner
            manifest = scenario_runner.run_scenario(ScenarioRunRequest(
                scenario_id=req.scenario_id, seed=req.seed, time_mode="TEST",
                dispatch_telemetry=True, transport_config=transport,
            ))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    
    from app.live_dashboard import observe_run
    observe_run(manifest, dest)
    destination_manager.record_event_sent(dest_id, manifest.dispatch_succeeded)
    
    # Return manifest with progress info
    result = manifest.model_dump(mode="json")
    result["progress_tracked"] = progress_scenario_runner is not None
    return result


@app.get("/api/acceptance/scenarios")
def acceptance_scenarios():
    return [{"id": item, "title": item.replace("_", " ")} for item in sorted(SUPPORTED_SCENARIO_IDS)]


@app.post("/api/acceptance/preview/{scenario_id}")
def acceptance_preview(scenario_id: str):
    try:
        runner = ScenarioRunner()
        manifest = runner.run_scenario(ScenarioRunRequest(scenario_id=scenario_id, seed=42, dispatch_telemetry=False))
        return {"manifest": manifest.model_dump(mode="json"), "events": [entry.model_dump(mode="json") for entry in runner.get_run_logs(manifest.run_id)[:5]]}
    except ValueError as exc:
        raise HTTPException(400, str(exc))


# =========================================================================
# Native SNMP Subsystem Endpoints (Gate 12F Productization)
# =========================================================================
@app.get("/api/native-snmp/preflight")
def get_native_snmp_preflight(index: str = "idx_network_ops"):
    from app.snmp_splunk_e2e import run_snmp_preflight_check
    return run_snmp_preflight_check(index=index)


@app.post("/api/native-snmp/preflight")
def post_native_snmp_preflight(payload: Optional[Dict[str, Any]] = None):
    from app.snmp_splunk_e2e import run_snmp_preflight_check
    idx = (payload or {}).get("index", "idx_network_ops") or "idx_network_ops"
    return run_snmp_preflight_check(index=idx)


# =========================================================================
# Native gNMI Subsystem Endpoints (Gate 13E Productization)
# =========================================================================
@app.get("/api/native-gnmi/preflight")
def get_native_gnmi_preflight(
    event_index: str = "idx_network_ops",
    metric_index: str = "cisco_mdt_metrics",
):
    from app.gnmi.splunk_e2e import run_gnmi_preflight_check
    return run_gnmi_preflight_check(event_index=event_index, metric_index=metric_index)


@app.post("/api/native-gnmi/preflight")
def post_native_gnmi_preflight(payload: Optional[Dict[str, Any]] = None):
    from app.gnmi.splunk_e2e import run_gnmi_preflight_check
    ev_idx = (payload or {}).get("event_index", "idx_network_ops") or "idx_network_ops"
    met_idx = (payload or {}).get("metric_index", "cisco_mdt_metrics") or "cisco_mdt_metrics"
    return run_gnmi_preflight_check(event_index=ev_idx, metric_index=met_idx)


# =========================================================================
# Native Flow Subsystem Endpoints (Gate 11D Productization)
# =========================================================================
@app.get("/api/native-flow/health")
def get_native_flow_health():
    from app.collector_evidence import CollectorEvidenceAdapter
    adapter = CollectorEvidenceAdapter()
    detailed = adapter.get_detailed_health()
    return detailed.dict() if hasattr(detailed, "dict") else detailed


@app.get("/api/native-flow/config")
def get_native_flow_config():
    from app.models import resolve_native_flow_config
    cfg = resolve_native_flow_config()
    return cfg.dict() if hasattr(cfg, "dict") else cfg


@app.post("/api/native-flow/preflight")
def post_native_flow_preflight(payload: Optional[Dict[str, Any]] = None):
    from app.collector_evidence import CollectorEvidenceAdapter
    from app.models import resolve_native_flow_config
    cfg = resolve_native_flow_config(explicit_config=payload)
    adapter = CollectorEvidenceAdapter()
    return adapter.run_preflight_check(config=cfg)


@app.get("/api/native-flow/diagnostics")
def get_native_flow_diagnostics():
    from app.collector_evidence import CollectorEvidenceAdapter
    adapter = CollectorEvidenceAdapter()
    health = adapter.get_detailed_health()
    prom = adapter.get_prometheus_metrics()
    return {
        "status": health.state,
        "health": health.dict() if hasattr(health, "dict") else health,
        "prometheus_metrics": prom,
        "recent_flows_count": len(adapter.get_recent_flows())
    }
# =========================================================================
# Deployment Profile (Demo vs Secure / External)
# =========================================================================
@app.get("/api/profile")
def get_deployment_profile_info():
    from app.models import get_deployment_profile, DeploymentProfile
    profile = get_deployment_profile()
    return {
        "profile": profile.value,
        "label": "DEMO / LOCAL LAB" if profile == DeploymentProfile.DEMO else "SECURE / EXTERNAL",
        "description": (
            "Isolated demonstration environment with pre-configured disposable test credentials."
            if profile == DeploymentProfile.DEMO
            else "Hardened profile with user-managed secrets and strict credentials enforcement."
        ),
    }


@app.get("/health")
def get_service_health():
    return {"status": "ok", "service": "netspout-simulation-engine"}


# =========================================================================
# Self-Contained Telemetry Pipelines Health & Lifecycle (Gate 14+)
# =========================================================================
@app.get("/api/health/pipelines")
def get_pipelines_health():
    return {
        "components": unified_generation_service.runtime_health(
            _unified_transport_config()
        )
    }


# =========================================================================
# Unified Generation Experience (Modes A, B, C, and D)
# =========================================================================
def _unified_transport_config() -> TelemetryTransportConfig:
    if current_topology and getattr(current_topology, "global_transport", None):
        return current_topology.global_transport
    return TelemetryTransportConfig()


@app.get("/api/generation/capabilities")
def get_unified_generation_capabilities():
    return unified_generation_service.capabilities(_unified_transport_config())


@app.post("/api/generation/preview")
def preview_unified_generation(payload: UnifiedGenerationRequest):
    try:
        return unified_generation_service.preview(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/api/generation/preflight")
def preflight_unified_generation(payload: UnifiedGenerationRequest):
    try:
        return unified_generation_service.preflight(
            payload, _unified_transport_config()
        ).model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.post("/api/generation/runs")
def run_unified_generation(payload: UnifiedGenerationRequest):
    try:
        return unified_generation_service.run(
            payload, _unified_transport_config()
        ).model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.get("/api/generation/runs/{run_id}")
def get_unified_generation_run(run_id: str):
    run = unified_generation_service.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Generation run not found")
    return run.model_dump(mode="json")


@app.post("/api/generation/runs/{run_id}/observe")
def observe_unified_generation_run(run_id: str):
    try:
        return unified_generation_service.observe(
            run_id, _unified_transport_config()
        ).model_dump(mode="json")
    except KeyError:
        raise HTTPException(status_code=404, detail="Generation run not found")


@app.post("/api/generation/runs/{run_id}/investigate/{recipe_id}")
def investigate_unified_generation_run(run_id: str, recipe_id: str):
    try:
        return unified_generation_service.run_investigation(
            run_id, recipe_id, _unified_transport_config()
        )
    except KeyError:
        raise HTTPException(status_code=404, detail="Generation run not found")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


# =========================================================================
# Scenario-Aware Dashboard Studio & Recipe Engine (Phase 11)
# =========================================================================
class DashboardLiveValidationRequest(BaseModel):
    run_id: str
    index: str = "idx_network_ops"


class DashboardVisualValidationRequest(BaseModel):
    run_id: str
    evidence_ref: str
    export_validated: bool
    browser_rendered: bool
    scenario_run_binding: bool
    source_coverage_validated: bool
    visualization_compatible: bool
    drilldowns_tested: bool
    inspector_tested: bool
    responsive_tested: bool


@app.get("/api/dashboards")
def get_dashboard_catalog():
    return dashboard_recipe_service.catalog_summary()


@app.get("/api/dashboards/{dashboard_id}")
def get_dashboard_pack(
    dashboard_id: str,
    run_id: Optional[str] = Query(default=None),
    index: str = Query(default="idx_network_ops"),
):
    try:
        return dashboard_recipe_service.generate(
            dashboard_id, run_id=run_id, index=index
        ).model_dump(mode="json")
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))


DASHBOARD_PANEL_RETRIES = 8
DASHBOARD_PANEL_RETRY_DELAY_S = 4.0


@app.post("/api/dashboards/{dashboard_id}/validate")
def validate_dashboard_pack(
    dashboard_id: str, payload: DashboardLiveValidationRequest
):
    run = unified_generation_service.get_run(payload.run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Generation run not found")
    try:
        pack = dashboard_recipe_service.generate(
            dashboard_id, run_id=payload.run_id, index=payload.index
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))
    if pack.runtime_scenario_id != (run.scenario_id or run.selection_id):
        raise HTTPException(
            status_code=409,
            detail="run does not belong to the selected dashboard scenario",
        )
    panel_results: Dict[str, List[Dict[str, Any]]] = {}
    failures = []
    for panel in pack.panels:
        if not panel.executable or not panel.query:
            continue
        # Observed events can lag behind search by a few seconds; retry an empty or short-shaped panel before
        # concluding it has no data. The verdict still rests only on rows Splunk actually returned.
        for attempt in range(DASHBOARD_PANEL_RETRIES):
            rows, error = unified_generation_service.execute_bounded_spl(
                panel.query, _unified_transport_config()
            )
            shaped = bool(rows) and set(panel.expected_shape) <= {f for r in rows for f in r}
            if error or shaped or attempt == DASHBOARD_PANEL_RETRIES - 1:
                break
            time.sleep(DASHBOARD_PANEL_RETRY_DELAY_S)
        if error:
            failures.append("{}: {}".format(panel.panel_id, error))
        else:
            panel_results[panel.panel_id] = rows
    evidence = dashboard_recipe_service.validate(
        pack,
        panel_results,
        evidence_refs=["run:{}".format(payload.run_id)],
        execution_failures=failures,
        source_coverage_validated=bool(
            [channel for channel in run.channel_results if channel.required]
        )
        and all(
            any(
                item.stage == "SPLUNK_OBSERVED"
                and getattr(item.state, "value", item.state) == "PROVEN"
                for item in channel.evidence
            )
            for channel in run.channel_results
            if channel.required
        ),
        source_observations={
            channel.source_id: any(
                item.stage == "SPLUNK_OBSERVED"
                and getattr(item.state, "value", item.state) == "PROVEN"
                for item in channel.evidence
            )
            for channel in run.channel_results
            if channel.required
        },
    )
    return evidence.model_dump(mode="json")


@app.post("/api/dashboards/{dashboard_id}/validate-visual")
def validate_dashboard_visuals(
    dashboard_id: str, payload: DashboardVisualValidationRequest
):
    try:
        evidence = dashboard_recipe_service.mark_visual_validation(
            dashboard_id=dashboard_id,
            run_id=payload.run_id,
            evidence_ref=payload.evidence_ref,
            export_validated=payload.export_validated,
            validation_checks={
                "browser_rendered": payload.browser_rendered,
                "scenario_run_binding": payload.scenario_run_binding,
                "source_coverage_validated": payload.source_coverage_validated,
                "visualization_compatible": payload.visualization_compatible,
                "drilldowns_tested": payload.drilldowns_tested,
                "inspector_tested": payload.inspector_tested,
                "responsive_tested": payload.responsive_tested,
            },
        )
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))
    return evidence.model_dump(mode="json")


@app.get("/api/dashboards/{dashboard_id}/export")
def export_dashboard_pack(
    dashboard_id: str,
    run_id: Optional[str] = Query(default=None),
    index: str = Query(default="idx_network_ops"),
):
    try:
        pack = dashboard_recipe_service.generate(
            dashboard_id, run_id=run_id, index=index
        )
        return dashboard_recipe_service.export_dashboard_studio(pack)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))


# =========================================================================
# Industry Studio & Cross-Domain Composition (Phase 10)
# =========================================================================
@app.get("/api/industries")
def get_industry_catalog():
    return industry_pack_service.catalog()


@app.get("/api/industries/{industry_id}")
def get_industry_pack(industry_id: str):
    industry = industry_pack_service.get(industry_id)
    if industry is None:
        raise HTTPException(status_code=404, detail="Industry Pack not found")
    return industry_pack_service.describe(industry)


@app.post("/api/industries/compose")
def compose_industry_scenario(payload: IndustrySelection):
    try:
        return industry_pack_service.compose(payload)
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))


@app.post("/api/industries/{industry_id}/studio-draft")
def clone_industry_scenario_to_studio(
    industry_id: str, payload: IndustrySelection
):
    if payload.industry_id != industry_id:
        raise HTTPException(status_code=409, detail="industry selection mismatch")
    try:
        composition = industry_pack_service.compose(payload)
        industry = industry_pack_service.get(industry_id)
        draft = scenario_studio_service.clone_scenario(composition["scenario_id"])
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))
    environment = next(
        item
        for item in industry.environments
        if item.environment_id == payload.environment_id
    )
    draft.industry_id = industry_id
    draft.industry_environment_id = environment.environment_id
    declared_assumptions = [
        assumption
        for impact in industry.business_impacts
        for assumption in impact.assumptions
    ]
    configured_assumptions = payload.modeled_parameters.get(
        "impact_assumptions", []
    )
    draft.business_impact_assumptions = list(
        dict.fromkeys(declared_assumptions + configured_assumptions)
    )
    draft.title = "{} — {} Private Clone".format(
        industry.name, environment.name
    )
    for entity in draft.entities:
        entity.attributes["industry_id"] = industry_id
        entity.attributes["industry_environment_id"] = environment.environment_id
    return draft.model_dump(mode="json")


# =========================================================================
# Scenario Studio & Private Custom Source Packs (Phase 6)
# =========================================================================
@app.get("/api/studio")
def get_scenario_studio_home():
    return scenario_studio_service.home()


@app.post("/api/studio/samples/analyze")
def analyze_studio_sample(payload: SampleAnalysisRequest):
    return scenario_studio_service.analyze_sample(payload).model_dump(mode="json")


@app.post("/api/studio/custom-sources/validate")
def validate_studio_custom_source(payload: CustomSourceDraft):
    return scenario_studio_service.validate_custom_source(payload)


@app.post("/api/studio/drafts")
def create_studio_draft(payload: StudioDraftRequest):
    try:
        return scenario_studio_service.create_draft(payload).model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.get("/api/studio/packs")
def list_studio_packs():
    return [
        scenario_studio_service.summarize(item)
        for item in scenario_studio_service.list_packs()
    ]


@app.get("/api/studio/packs/{pack_id}")
def get_studio_pack(pack_id: str):
    pack = scenario_studio_service.get_pack(pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Private Studio pack not found")
    return pack.model_dump(mode="json")


@app.post("/api/studio/packs/validate")
def validate_studio_pack(payload: StudioScenarioPack):
    return scenario_studio_service.validate_pack(payload).model_dump(mode="json")


@app.post("/api/studio/packs")
def save_studio_pack(payload: StudioScenarioPack):
    try:
        return scenario_studio_service.save_pack(payload).model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@app.delete("/api/studio/packs/{pack_id}")
def delete_studio_pack(pack_id: str):
    if not scenario_studio_service.delete_pack(pack_id):
        raise HTTPException(status_code=404, detail="Private Studio pack not found")
    return {"deleted": True, "pack_id": pack_id}


@app.get("/api/studio/packs/{pack_id}/export-gate")
def get_studio_export_gate(pack_id: str, public: bool = False):
    try:
        return scenario_studio_service.export_gate(pack_id, public=public)
    except KeyError:
        raise HTTPException(status_code=404, detail="Private Studio pack not found")


@app.post("/api/studio/packs/{pack_id}/run")
def run_studio_pack(pack_id: str, payload: StudioRunRequest):
    pack = scenario_studio_service.get_pack(pack_id)
    if not pack:
        raise HTTPException(status_code=404, detail="Private Studio pack not found")
    if pack.definition_only:
        raise HTTPException(
            status_code=409,
            detail=(
                "Studio definition draft is non-executable: "
                + "; ".join(pack.execution_blockers)
            ),
        )
    report = scenario_studio_service.validate_pack(pack)
    if not report.valid:
        raise HTTPException(
            status_code=409,
            detail="Studio pack validation is BLOCKED: {}".format(
                "; ".join(report.errors)
            ),
        )
    for parameter in pack.parameters:
        value = payload.parameters.get(parameter.parameter_id, parameter.default)
        error = parameter.validate_value(value)
        if error:
            raise HTTPException(
                status_code=409,
                detail="{} {}".format(parameter.parameter_id, error),
            )
    _, composition = scenario_studio_service.compile_pack(pack)
    binding = composition.source_bindings[0]
    scenario_parameters = dict(payload.parameters)
    scenario_parameters.update(
        {
            "seed": payload.seed,
            "entity_id": pack.entities[0].entity_id,
            "studio_shared_state": True,
            **(
                {"reference_scenario_id": pack.cloned_from_scenario_id}
                if pack.cloned_from_scenario_id
                else {}
            ),
            **(
                {
                    "security_profile_scenario_id": pack.cloned_from_scenario_id,
                }
                if pack.cloned_from_scenario_id
                and pack.cloned_from_scenario_id.startswith("SEC-P9-")
                else {}
            ),
        }
    )
    try:
        run = unified_generation_service.run(
            UnifiedGenerationRequest(
                mode=GenerationMode.SCENARIO,
                selection_id=pack.scenario_id,
                transport_id=(
                    binding.destination_transport_id or binding.transport_id
                ),
                destination_id=binding.destination_id,
                count=1,
                rate_eps=10,
                scenario_parameters=scenario_parameters,
            ),
            _unified_transport_config(),
        )
        return run.model_dump(mode="json")
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc))


# =========================================================================
# Legacy Generation Modes (compatibility surface)
# =========================================================================
def _authorize_caller_transport(raw: Dict[str, Any]) -> TelemetryTransportConfig:
    """A caller-supplied transport_config is untrusted input (it carries a destination URL, a token and index names).

    Connection Center not configured: lab/legacy behavior is kept, but index names must be safe.
    Connection Center configured: the config must point at the configured destination (same host:port) and BOTH the event and
    metric index it would use (explicit or defaulted) must be on the allowlist; otherwise 403 before anything is sent.
    """
    from urllib.parse import urlparse
    try:
        cfg = TelemetryTransportConfig(**raw)
    except Exception as exc:
        raise HTTPException(status_code=422, detail="Invalid transport_config") from exc
    indexes = [i for i in (cfg.hec_index, cfg.hec_metric_index) if i]
    for name in indexes:
        try:
            validate_index_name(name)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    config = release_candidate_configuration.load()
    if not config.get("configured"):
        return cfg
    if urlparse(cfg.hec_url or "").netloc.lower() != urlparse(config.get("hec_url") or "").netloc.lower():
        raise HTTPException(status_code=403, detail="transport_config destination differs from the Connection Center destination")
    for name in indexes:
        if name not in config.get("indexes", []):
            raise HTTPException(status_code=403, detail="Index is not authorized by Connection Center")
    return cfg


def _generator_transport(index=None, explicit=None, needs_metric_index=False):
    """Transport for the generator-mode routes: an explicit request config wins; otherwise the Connection Center
    destination (global transport) with the requested index; None keeps the pre-existing defaults when none is saved."""
    if explicit:
        return _authorize_caller_transport(explicit)
    config = release_candidate_configuration.load()
    if not config.get("configured"):
        return None  # nothing configured: callers keep failing closed (the default transport is not a destination)
    gt = getattr(current_topology, "global_transport", None) if current_topology else None
    if gt is not None and getattr(gt, "hec_url", None):
        effective = index or getattr(gt, "hec_index", None)  # an omitted index falls back to the destination's own index, which must also be allowed
        if effective and effective not in config.get("indexes", []):
            raise HTTPException(status_code=403, detail="Index is not authorized by Connection Center")
        metric_index = getattr(gt, "hec_metric_index", None)
        if needs_metric_index and metric_index and metric_index not in config.get("indexes", []):
            raise HTTPException(status_code=403, detail="Metric index is not authorized by Connection Center")
        return gt.model_copy(update={"hec_index": index} if index else {})
    return None


@app.post("/api/generate/single-event")
def post_generate_single_event(payload: Dict[str, Any]):
    from app.generator_modes import generator_service
    vendor_id = payload.get("vendor_id", "cisco_ios")
    sourcetype = payload.get("sourcetype", "cisco:ios:syslog")
    event_name = payload.get("event_name")
    dispatch = bool(payload.get("dispatch", False))
    index = payload.get("index", "idx_network_ops")
    try:
        return generator_service.generate_single_event(
            vendor_id=vendor_id,
            sourcetype=sourcetype,
            event_name=event_name,
            dispatch=dispatch,
            transport_config=_generator_transport(index) if dispatch else None,
            index=index
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/generate/sourcetype")
def post_generate_sourcetype_batch(payload: Dict[str, Any]):
    from app.generator_modes import generator_service
    vendor_id = payload.get("vendor_id", "cisco_ios")
    sourcetype = payload.get("sourcetype", "cisco:ios:syslog")
    count = int(payload.get("count", 10))
    rate_eps = int(payload.get("rate_eps", 10))
    dispatch = bool(payload.get("dispatch", False))
    index = payload.get("index", "idx_network_ops")
    try:
        return generator_service.generate_sourcetype_batch(
            vendor_id=vendor_id,
            sourcetype=sourcetype,
            count=count,
            rate_eps=rate_eps,
            event_families=payload.get("event_families"),
            dispatch=dispatch,
            transport_config=_generator_transport(index) if dispatch else None,
            index=index
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/generate/data-source")
def post_generate_data_source(payload: Dict[str, Any]):
    from app.generator_modes import generator_service
    vendor_id = payload.get("vendor_id", "cisco_ios")
    product = payload.get("product", "IOS XR")
    transport = payload.get("transport", "syslog")
    count = int(payload.get("count", 25))
    rate_eps = int(payload.get("rate_eps", 10))
    dispatch = bool(payload.get("dispatch", False))
    index = payload.get("index", "idx_network_ops")
    try:
        return generator_service.generate_data_source(
            vendor_id=vendor_id,
            product=product,
            transport=transport,
            count=count,
            rate_eps=rate_eps,
            dispatch=dispatch,
            index=index
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/generate/scenario-pack")
def post_generate_universe_scenario_pack(payload: Dict[str, Any]):
    """Bounded authentic observation packs; separate from graph scenario contracts."""
    scenario_id = payload.get('scenario_id')
    from netspout_core.authentic_scenario_packs import SCENARIO_PACK_IDS as _PACKS
    from netspout_core.incident_packs import incident_ids
    incident = incident_ids()
    if scenario_id in list(_PACKS) + incident:
        from app.generator_modes import generator_service
        try:
            config = payload.get('transport_config')
            return generator_service.generate_universe_scenario(
                scenario_id, run_id=payload.get('run_id'), dispatch=bool(payload.get('dispatch', False)),
                transport_config=_generator_transport(payload.get('index'), config, needs_metric_index=scenario_id in incident) if payload.get('dispatch') else None)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    raise HTTPException(status_code=400, detail=f"Scenario pack '{scenario_id}' is not available")


# =========================================================================
# Continuous sample replay (Connection Center destination only; no caller transport_config)
# =========================================================================
from netspout_core.replay_service import ReplayService, preview as replay_preview, sources as replay_sources
from netspout_core.sample_replay import DEFAULT_HOST as REPLAY_HOST, DEFAULT_INDEX as REPLAY_INDEX, HecSink, ReplayError

replay_service = ReplayService(Path(os.environ["NETSPOUT_REPLAY_STATE"]) if os.environ.get("NETSPOUT_REPLAY_STATE") else None)


def _replay_destination(payload: Dict[str, Any]):
    """The authorized destination for replay: the saved Connection Center destination, an allowlisted index (default dev_test_replay).
    A caller-supplied transport_config is refused outright. Outside DOCKER_LAB the index must be a dev_ index and the caller must confirm."""
    if payload.get("transport_config"):
        raise HTTPException(status_code=422, detail="Replay uses the Connection Center destination; transport_config is not accepted")
    config = release_candidate_configuration.load()
    if not config.get("configured"):
        raise HTTPException(status_code=409, detail="Connection Center destination is not configured")
    gt = getattr(current_topology, "global_transport", None) if current_topology else None
    if gt is None or not getattr(gt, "hec_url", None) or not getattr(gt, "hec_token", None):
        raise HTTPException(status_code=409, detail="Connection Center HEC destination is not active")
    index = payload.get("index") or REPLAY_INDEX
    try:
        validate_index_name(index)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if index not in config.get("indexes", []):
        raise HTTPException(status_code=403, detail="Index is not authorized by Connection Center")
    if config.get("deployment_mode") != "DOCKER_LAB" and not (index.startswith("dev_") and payload.get("confirm_destination") is True):
        raise HTTPException(status_code=403, detail="Replay outside a lab destination requires a dev_ index and confirm_destination=true")
    return gt, index, payload.get("host") or REPLAY_HOST


@app.get("/api/replay/sources")
def replay_list_sources():
    return {"sources": [{k: v for k, v in s.items() if k != "file"} for s in replay_sources()],
            "defaults": {"index": REPLAY_INDEX, "host": REPLAY_HOST}}


@app.get("/api/replay/packs")
def replay_list_packs():
    from netspout_core import replay_packs
    return {"packs": [{**{k: v for k, v in p.items() if k != "phases"}, "correlation_level": replay_packs.correlation_level(p),
                       "phases": [{"id": ph["id"], "kind": ph["source"]["kind"], "source": ph["source"].get("source_id") or ph["source"].get("pack"),
                                   "offset_s": ph["offset_s"]} for ph in p["phases"]]} for p in replay_packs.packs()],
            "defaults": {"index": REPLAY_INDEX, "host": REPLAY_HOST}}


@app.post("/api/replay/preview")
def replay_post_preview(payload: Dict[str, Any]):
    try:
        return replay_preview(payload)
    except ReplayError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.post("/api/replay/sessions")
def replay_start(payload: Dict[str, Any]):
    gt, index, host = _replay_destination(payload)
    def sink(source, sourcetype, idx, hst):
        return HecSink(gt.hec_url, gt.hec_token, idx, hst, source, sourcetype, getattr(gt, "hec_ssl_verify", True), getattr(gt, "hec_allow_insecure_tls", False))
    try:
        return replay_service.create(payload, sink, index=index, host=host).status()
    except ReplayError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/replay/sessions")
def replay_list_sessions():
    return {"sessions": replay_service.list()}


@app.get("/api/replay/sessions/{session_id}")
def replay_get_session(session_id: str):
    try:
        return replay_service.status(session_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown replay session")


@app.post("/api/replay/sessions/{session_id}/verify")
def replay_verify(session_id: str):
    try:
        return replay_service.verify(session_id, lambda q: release_candidate_configuration.execute_read_only_search(q))
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown replay session")


@app.post("/api/replay/sessions/{session_id}/{action}")
def replay_control(session_id: str, action: str):
    if action not in ("pause", "resume", "stop"):
        raise HTTPException(status_code=404, detail="Unknown action")
    try:
        return replay_service.control(session_id, action)
    except KeyError:
        raise HTTPException(status_code=404, detail="Unknown replay session")
    except ReplayError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@app.post("/api/generate/scenario")
def post_generate_scenario_canonical(payload: Dict[str, Any]):
    """Canonical alias for scenario execution matching Section 17 API requirements."""
    scenario_id = payload.get("scenario_id") or payload.get("scenario", "cisco_sdwan_brownout")
    return run_scenario_contract(scenario_id=scenario_id, payload=payload)


@app.get("/api/catalog/vendors")
def get_catalog_vendors_canonical():
    """Canonical vendor list matching Section 17 API requirements."""
    from app.catalog import catalog
    return catalog.list_vendors()


@app.get("/api/catalog/sourcetypes")
def get_catalog_sourcetypes_canonical():
    """Canonical sourcetype list matching Section 17 API requirements."""
    from app.catalog import catalog
    return catalog.list_sourcetypes(include_deprecated=True)


@app.get("/api/catalog/scenarios")
def get_catalog_scenarios_canonical():
    """Canonical scenario list matching Section 17 API requirements."""
    from app.catalog import catalog
    return catalog.list_scenarios()


@app.post("/api/splunk/test")
async def post_splunk_test_canonical(req: Union[ConnectionTestPayload, PipelineTestRequest, Dict[str, Any]]):
    """Canonical Splunk connection test endpoint matching Section 17 API requirements."""
    return await test_connection_endpoint(req)


@app.get("/api/catalog/domains")
def get_catalog_domains():
    import json
    domains_path = os.path.join(os.path.dirname(__file__), "catalog_data", "network_coverage.json")
    if os.path.exists(domains_path):
        with open(domains_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


@app.get("/api/catalog/provenance")
def get_catalog_provenance():
    """Legacy provenance list retained for compatibility."""
    import json
    prov_path = os.path.join(os.path.dirname(__file__), "catalog_data", "telemetry_sources.json")
    if os.path.exists(prov_path):
        with open(prov_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


@app.get("/api/catalog/telemetry")
def get_telemetry_catalog():
    """Strict Native/Splunk/NetSpout telemetry contract catalog."""
    from app.catalog import catalog
    return catalog.get_telemetry_catalog()


@app.get("/api/catalog/summary")
def get_telemetry_catalog_summary():
    from app.catalog import catalog
    return catalog.get_telemetry_catalog_summary()


@app.get("/api/security-sources")
def get_security_source_coverage():
    return {
        "summary": security_source_catalog.summary(),
        "sources": security_source_catalog.list_sources(),
    }


@app.get("/api/security-sources/{coverage_id}")
def get_security_source_coverage_detail(coverage_id: str):
    source = security_source_catalog.get_source(coverage_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Security source not found")
    return source


@app.get("/api/security-content/summary")
def get_security_content_summary():
    return security_content_catalog.summary()


@app.get("/api/security-content/detections")
def list_security_content_detections(
    q: Optional[str] = None,
    story: Optional[str] = None,
    technique: Optional[str] = None,
    data_source: Optional[str] = None,
    sourcetype: Optional[str] = None,
    detection_type: Optional[str] = None,
    product: Optional[str] = None,
    required_ta: Optional[str] = None,
    data_model: Optional[str] = None,
    validation_status: Optional[str] = None,
    compatibility: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    try:
        return security_content_catalog.list_detections(
            query=q,
            story=story,
            technique=technique,
            data_source=data_source,
            sourcetype=sourcetype,
            detection_type=detection_type,
            product=product,
            required_ta=required_ta,
            data_model=data_model,
            validation_status=validation_status,
            compatibility=compatibility,
            limit=limit,
            offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/security-content/detections/{detection_id:path}")
def get_security_content_detection(detection_id: str):
    detection = security_content_catalog.get_detection(detection_id)
    if detection is None:
        raise HTTPException(status_code=404, detail="Detection not found")
    return detection


@app.get("/api/security-content/stories")
def list_security_content_stories(
    q: Optional[str] = None,
    limit: int = Query(default=200, ge=1, le=500),
):
    return security_content_catalog.list_stories(query=q, limit=limit)


@app.get("/api/security-content/datasets")
def list_attack_datasets(
    q: Optional[str] = None,
    technique: Optional[str] = None,
    limit: int = Query(default=200, ge=1, le=500),
):
    return security_content_catalog.list_datasets(
        query=q, technique=technique, limit=limit
    )


@app.get("/api/security-content/mitre")
def get_security_content_mitre_coverage():
    return security_content_catalog.mitre_coverage()


@app.post("/api/security-content/datasets/retrieve")
def retrieve_attack_dataset(payload: AttackDataRetrievePayload):
    try:
        return attack_data_replay_service.retrieve(payload.dataset_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (ValueError, urllib.error.URLError, TimeoutError, OSError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/security-content/datasets/preview/{local_id}")
def preview_attack_dataset(
    local_id: str,
    limit: int = Query(default=10, ge=1, le=50),
):
    try:
        return attack_data_replay_service.preview(local_id, limit=limit)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _authorized_replay_configuration(index: str) -> Dict[str, Any]:
    config = release_candidate_configuration.load()
    if not config.get("configured"):
        raise HTTPException(status_code=409, detail="Complete Connection Center setup first")
    if index not in config.get("indexes", []):
        raise HTTPException(status_code=403, detail="Index is not authorized by Connection Center")
    token = release_candidate_configuration.secrets.hec_token
    if not token:
        raise HTTPException(status_code=409, detail="HEC credential is unavailable")
    hec_url = config["hec_url"].rstrip("/")
    if not hec_url.endswith("/event"):
        hec_url += "/event"
    return {
        "hec_url": hec_url,
        "hec_token": token,
        "allow_insecure_tls": bool(config.get("allow_insecure_tls")),
    }


@app.post("/api/security-content/replays")
def replay_attack_dataset(payload: AttackDataReplayPayload):
    destination = _authorized_replay_configuration(payload.index)
    try:
        return attack_data_replay_service.replay(
            local_id=payload.local_id,
            dataset_path=payload.dataset_path,
            index=payload.index,
            timestamp_mode=payload.timestamp_mode,
            **destination,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/security-content/replays/{run_id}")
def get_attack_data_replay(run_id: str):
    try:
        return attack_data_replay_service.get_run(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/security-content/replays/{run_id}/cancel")
def cancel_attack_data_replay(run_id: str):
    try:
        return attack_data_replay_service.cancel(run_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/security-content/validations")
def validate_security_content_detection(payload: DetectionValidationPayload):
    config = release_candidate_configuration.load()
    if not config.get("configured"):
        raise HTTPException(status_code=409, detail="Complete Connection Center setup first")
    if payload.index not in config.get("indexes", []):
        raise HTTPException(status_code=403, detail="Index is not authorized by Connection Center")
    if payload.expected_min_matches < 0 or payload.expected_min_matches > 100:
        raise HTTPException(status_code=422, detail="Expected match bound is outside policy")
    try:
        return detection_validation_orchestrator.validate(**payload.model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@app.get("/api/security-content/validations")
def list_security_content_validations():
    return detection_evidence_store.list()


# =========================================================================
# Use Case Explorer (Phase 4E): search + workflow descriptors over existing engines
# =========================================================================
_explorer_operational_cache: Dict[str, Any] = {}


def _verified_scenario_ids():
    """(live-verified scenario ids, dashboard-verified scenario ids) from COMMITTED evidence only; empty if the evidence files are not present."""
    import glob as _glob
    here = Path(__file__).resolve().parent
    root = here.parents[1]
    verified, dashboards = set(), set()
    files = _glob.glob(str(here / "catalog_data" / "*live_raw_equality_results.json")) + _glob.glob(str(root / "docs/verification/evidence/incident_packs/live_results.json"))
    for f in files:
        try:
            doc = json.loads(Path(f).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        for run in doc.get("scenario_runs", []):
            if run.get("verdict") == "PASS":
                verified.add(run["scenario_id"])
    try:  # replay packs whose every event, phase order and run tag were read back from Splunk in the isolated lab
        verified |= set(json.loads((root / "docs/verification/evidence/replay/replay_live.json").read_text(encoding="utf-8")).get("packs_indexed_verified", []))
    except (OSError, ValueError):
        pass
    try:
        visual = json.loads((root / "docs/verification/evidence/phase4f/visual-validation.json").read_text(encoding="utf-8"))
        if visual.get("verdict", {}).get("maturity") == "DASHBOARD_READY":
            dashboards.add("SEC-P9-B-DNS-ANOMALY")
            verified.add("SEC-P9-B-DNS-ANOMALY")
    except (OSError, ValueError):
        pass
    return verified, dashboards


def _replay_panels_populated():
    try:
        root = Path(__file__).resolve().parents[2]
        return set(json.loads((root / "docs/verification/evidence/replay/replay_live.json").read_text(encoding="utf-8")).get("packs_panels_populated", []))
    except (OSError, ValueError):
        return set()


def _replay_dashboards():
    """scenario id -> installed Dashboard Studio view and the maturity recorded by stored evidence (replay, authentic native and incident packs; never inferred)."""
    try:
        root = Path(__file__).resolve().parents[2]
        doc = json.loads((root / "docs/verification/evidence/dashboards/dashboard_maturity.json").read_text(encoding="utf-8"))
        return {pid: {"view": "pf_" + pid, "maturity": v["maturity"]} for pid, v in doc["dashboards"].items()}
    except (OSError, ValueError, KeyError):
        return {}


def _explorer() -> UseCaseExplorer:
    from app.catalog import catalog
    if "inputs" not in _explorer_operational_cache:
        capabilities = unified_generation_service.capabilities(_unified_transport_config())
        _explorer_operational_cache["inputs"] = {
            "generation_scenarios": capabilities["scenarios"],
            "generation_sources": capabilities["sources"],
            "dashboards": dashboard_recipe_service.catalog_summary()["dashboards"],
            "catalog_scenarios": catalog.list_scenarios(),
        }
    return UseCaseExplorer(
        taxonomy=load_taxonomy(),
        security_catalog=security_content_catalog,
        validations=detection_evidence_store.list,
        runtime_approved_detections=SUPPORTED_RUNTIME_DETECTIONS,
        pack_scenario_ids=SCENARIO_PACK_IDS,
        runner_scenario_ids=SUPPORTED_SCENARIO_IDS,
        incident_packs=incident_catalog(),
        replay_packs=__import__('netspout_core.replay_packs', fromlist=['packs']).packs(),
        replay_panels_populated=_replay_panels_populated(),
        replay_dashboards=_replay_dashboards(),
        candidates=load_candidates(),
        curated_stories=load_curated_stories(),
        verified_scenarios=_verified_scenario_ids()[0],
        dashboard_verified=_verified_scenario_ids()[1],
        **_explorer_operational_cache["inputs"],
    )


@app.get("/api/explorer/summary")
def explorer_summary():
    explorer = _explorer()
    return {**explorer.facets(), "industries": explorer.industries()}


@app.get("/api/explorer/entries")
def explorer_search(
    q: str = Query(default="", max_length=200),
    kind: Optional[str] = Query(default=None, pattern="^(operational|security)$"),
    industry: Optional[str] = None,
    tier: Optional[str] = None,
    vendor: Optional[str] = None,
    readiness: Optional[str] = None,
    demo_ready: Optional[bool] = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    return _explorer().search(q=q, kind=kind, industry=industry, tier=tier, vendor=vendor,
                              readiness=readiness, demo_ready=demo_ready, limit=limit, offset=offset)


@app.get("/api/explorer/entries/{entry_id}")
def explorer_entry(entry_id: str):
    entry = _explorer().get(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Explorer entry not found")
    return entry


@app.get("/api/explorer/entries/{entry_id}/prerequisites")
def explorer_prerequisites(entry_id: str, index: Optional[str] = None):
    if index is not None:
        try:
            validate_index_name(index)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
    try:
        return _explorer().prerequisites(entry_id, release_candidate_configuration.load(), index=index)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


class ExplorerEnablePayload(BaseModel):
    index: str


class ExplorerObservePayload(BaseModel):
    index: str
    run_id: str
    metric_index: Optional[str] = None


@app.post("/api/explorer/detections/{detection_id}/enable")
def explorer_enable_detection(detection_id: str, payload: ExplorerEnablePayload):
    config = release_candidate_configuration.load()
    if not config.get("configured"):
        raise HTTPException(status_code=409, detail="Complete Connection Center setup first")
    if payload.index not in config.get("indexes", []):
        raise HTTPException(status_code=403, detail="Index is not authorized by Connection Center")
    try:
        prepared = detection_validation_orchestrator.prepare_enable(detection_id, payload.index)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    result = release_candidate_configuration.upsert_saved_search(prepared["saved_search_name"], prepared["spl"])
    return {
        **result, "detection_id": prepared["detection_id"], "spl_hash": prepared["spl_hash"],
        "upstream_commit": prepared["upstream_commit"], "adaptations": prepared["adaptations"],
        "limitations": ["Enabled means the scheduled saved search exists in Splunk; it does not show that it has fired."],
    }


@app.post("/api/explorer/observe")
@app.post("/api/explorer/security/observe")
def explorer_observe_replay(payload: ExplorerObservePayload):
    """Count run-scoped events actually present in Splunk, so validation never relies on 'events sent'."""
    config = release_candidate_configuration.load()
    if not config.get("configured"):
        raise HTTPException(status_code=409, detail="Complete Connection Center setup first")
    if payload.index not in config.get("indexes", []):
        raise HTTPException(status_code=403, detail="Index is not authorized by Connection Center")
    try:
        validate_index_name(payload.index)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,128}", payload.run_id):
        raise HTTPException(status_code=422, detail="Invalid run identifier")
    rows, error = release_candidate_configuration.execute_read_only_search(
        f'search index="{payload.index}" netspout_run_id="{payload.run_id}" earliest=-24h latest=now | stats count'
    )
    if error:
        return {"status": "ERROR", "indexed_event_count": None, "error": error}
    count = int(rows[0].get("count", 0)) if rows else 0
    reply = {"status": "OBSERVED" if count > 0 else "NOT_OBSERVED", "indexed_event_count": count, "error": None}
    if payload.metric_index:
        if payload.metric_index not in config.get("indexes", []):
            raise HTTPException(status_code=403, detail="Metric index is not authorized by Connection Center")
        try:
            validate_index_name(payload.metric_index)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        mrows, merror = release_candidate_configuration.execute_read_only_search(
            f'| mstats count(_value) as datapoints WHERE index="{payload.metric_index}" AND metric_name=* AND netspout_run_id="{payload.run_id}" earliest=-24h latest=now')
        reply["indexed_metric_datapoints"] = None if merror else (int(mrows[0].get("datapoints", 0)) if mrows else 0)
        reply["metric_error"] = merror
    return reply


@app.get("/api/setup")
def get_release_candidate_setup():
    return release_candidate_configuration.load()


@app.post("/api/setup")
def save_release_candidate_setup(payload: SetupConfigurationPayload):
    try:
        saved = release_candidate_configuration.save(payload.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    global current_topology
    current_topology.global_transport.hec_enabled = True
    current_topology.global_transport.hec_url = saved["hec_url"]
    current_topology.global_transport.hec_token = (
        release_candidate_configuration.secrets.hec_token or ""
    )
    # Indexes are stored sorted; use the dispatcher's own rule (a "metric" name means a metric store) so the
    # alphabetically-first index is not wrongly chosen as the event index.
    event_indexes = [i for i in saved["indexes"] if "metric" not in i.lower()]
    metric_indexes = [i for i in saved["indexes"] if "metric" in i.lower()]
    current_topology.global_transport.hec_index = (event_indexes or saved["indexes"])[0]
    if metric_indexes:
        current_topology.global_transport.hec_metric_index = metric_indexes[0]
    current_topology.global_transport.hec_ssl_verify = not saved["allow_insecure_tls"]
    current_topology.global_transport.hec_allow_insecure_tls = saved["allow_insecure_tls"]
    return saved


@app.post("/api/setup/validate")
def validate_release_candidate_setup():
    return release_candidate_configuration.validate_connection()


@app.delete("/api/setup")
def reset_release_candidate_setup():
    return release_candidate_configuration.reset()


@app.get("/api/catalog/sources")
def get_telemetry_sources(
    domain: Optional[str] = None,
    verification_state: Optional[str] = None,
):
    from app.catalog import catalog
    return catalog.list_telemetry_sources(
        domain=domain, verification_state=verification_state
    )


@app.get("/api/catalog/sources/{source_id}")
def get_telemetry_source(source_id: str):
    from app.catalog import catalog
    source = catalog.get_telemetry_source(source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Telemetry source not found")
    return source


@app.get("/api/catalog/integrations")
def get_splunk_integrations():
    from app.catalog import catalog
    return catalog.list_splunk_integrations()


@app.get("/api/catalog/integrations/{integration_id}")
def get_splunk_integration(integration_id: str):
    from app.catalog import catalog
    integration = catalog.get_splunk_integration(integration_id)
    if integration is None:
        raise HTTPException(status_code=404, detail="Splunk integration not found")
    return integration


@app.get("/api/catalog/evidence")
def get_catalog_evidence():
    from app.catalog import catalog
    return catalog.list_catalog_evidence()


@app.get("/api/coverage/cisco")
def get_cisco_coverage():
    """Evidence-backed Cisco coverage projection over catalog and Pack state."""
    return vendor_coverage_service.view()


@app.get("/api/coverage/cisco/products/{product_id}")
def get_cisco_coverage_product(product_id: str):
    product = vendor_coverage_service.product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Coverage product not found")
    return product


@app.get("/api/cisco100")
def get_cisco_100(
    domain: Optional[str] = None,
    product: Optional[str] = None,
    technology: Optional[str] = None,
    telemetry_source: Optional[str] = None,
    protocol: Optional[str] = None,
    integration: Optional[str] = None,
    maturity: Optional[str] = None,
    category: Optional[str] = None,
    difficulty: Optional[str] = None,
):
    """Filter the evidence-gated Cisco 100 definition catalog."""
    return cisco_scenario_factory_service.view(
        domain=domain,
        product=product,
        technology=technology,
        telemetry_source=telemetry_source,
        protocol=protocol,
        integration=integration,
        maturity=maturity,
        category=category,
        difficulty=difficulty,
    )


@app.get("/api/cisco100/matrix")
def get_cisco_100_matrix():
    return {"rows": cisco_scenario_factory_service.coverage_matrix()}


@app.get("/api/cisco100/dependencies/{dependency_id}")
def get_cisco_100_dependency_impact(dependency_id: str):
    return cisco_scenario_factory_service.affected_scenarios(dependency_id)


@app.get("/api/cisco100/scenarios/{scenario_id}")
def get_cisco_100_scenario(scenario_id: str):
    result = cisco_scenario_factory_service.scenario(scenario_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Cisco 100 scenario not found")
    return result


@app.post("/api/cisco100/scenarios/{scenario_id}/promotions/{target}")
def validate_cisco_100_promotion(scenario_id: str, target: ScenarioMaturity):
    try:
        return cisco_scenario_factory_service.validate_promotion(scenario_id, target)
    except KeyError:
        raise HTTPException(status_code=404, detail="Cisco 100 scenario not found")
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))


@app.post("/api/cisco100/scenarios/{scenario_id}/execute")
def execute_cisco_100_scenario(scenario_id: str):
    try:
        return cisco_scenario_factory_service.execution_decision(scenario_id)
    except KeyError:
        raise HTTPException(status_code=404, detail="Cisco 100 scenario not found")
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error))


@app.post("/api/cisco100/scenarios/{scenario_id}/studio-draft")
def clone_cisco_100_definition_to_studio(scenario_id: str):
    result = cisco_scenario_factory_service.scenario(scenario_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Cisco 100 scenario not found")
    definition = result["scenario"]
    runtime_scenario_id = definition.get("runtime_scenario_id")
    if definition.get("execution_enabled") and runtime_scenario_id:
        try:
            draft = scenario_studio_service.clone_scenario(runtime_scenario_id)
        except ValueError as error:
            raise HTTPException(status_code=409, detail=str(error))
        draft.cloned_from_scenario_id = scenario_id
        draft.title = "{} — Private Clone".format(definition["title"])
        return draft.model_dump(mode="json")
    return scenario_studio_service.clone_definition(definition).model_dump(mode="json")


@app.get("/api/catalog/source-manifests")
def get_source_manifests(scenario_id: Optional[str] = None):
    from app.catalog import catalog
    return catalog.list_source_manifests(scenario_id=scenario_id)


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
        await websocket.send_json({
            "type": "simulation_state",
            "running": simulation_running,
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
                    await manager.broadcast({"type": "simulation_state", "running": simulation_running})
                elif action == "set_running":
                    simulation_running = bool(data.get("running", True))
                    await manager.broadcast({"type": "simulation_state", "running": simulation_running})
                elif action == "set_scenario":
                    requested_scenario = ScenarioType(data.get("scenario", "normal_traffic"))
                    if requested_scenario not in LIVE_SIMULATION_SCENARIOS:
                        await websocket.send_json({
                            "type": "scenario_error",
                            "scenario": requested_scenario.value,
                            "detail": _live_simulation_refusal_detail(requested_scenario.value)
                        })
                    else:
                        active_scenario = requested_scenario
                        await manager.broadcast({"type": "scenario_state", "scenario": active_scenario})
                elif action == "update_topology":
                    current_topology = TopologyState(**data.get("topology", {}))
            except Exception as e:
                print(f"WS message error: {e}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        manager.disconnect(websocket)


@app.websocket("/ws/run-progress")
async def websocket_run_progress_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time run progress updates."""
    await manager.connect(websocket)
    try:
        # Send initial handshake
        await websocket.send_json({
            "type": "connection_established",
            "message": "Connected to Run Progress Feed",
            "active_runs": len(progress_tracker.get_all_active_runs())
        })
        
        # Send current active runs
        active_runs = progress_tracker.get_all_active_runs()
        for run_id, progress in active_runs.items():
            await websocket.send_json({
                "type": "run_progress",
                "run_id": progress.run_id,
                "state": progress.state,
                "timestamp": progress.timestamp.isoformat(),
                "message": progress.message,
                "details": progress.details,
                "current_phase": progress.current_phase,
                "phases_total": progress.phases_total,
                "phases_completed": progress.phases_completed,
                "generated_count": progress.generated_count,
                "accepted_count": progress.accepted_count,
                "rejected_count": progress.rejected_count,
                "indexed_count": progress.indexed_count,
                "verified_count": progress.verified_count
            })
        
        # Keep connection alive, listening for client messages
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                action = message.get("action")
                
                if action == "get_run_progress":
                    run_id = message.get("run_id")
                    if run_id:
                        progress = progress_tracker.get_run_progress(run_id)
                        if progress:
                            await websocket.send_json({
                                "type": "run_progress",
                                "run_id": progress.run_id,
                                "state": progress.state,
                                "timestamp": progress.timestamp.isoformat(),
                                "message": progress.message,
                                "details": progress.details
                            })
                        else:
                            await websocket.send_json({
                                "type": "error",
                                "message": f"Run {run_id} not found"
                            })
                
                elif action == "cancel_run":
                    run_id = message.get("run_id")
                    reason = message.get("reason", "User requested cancellation")
                    if run_id:
                        cancelled = progress_tracker.cancel_run(run_id, reason)
                        if cancelled:
                            await websocket.send_json({
                                "type": "run_cancelled",
                                "run_id": run_id,
                                "reason": reason
                            })
                        else:
                            await websocket.send_json({
                                "type": "error",
                                "message": f"Run {run_id} not found or already completed"
                            })
                
                elif action == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.now().isoformat()})
                    
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
            except Exception as e:
                await websocket.send_json({"type": "error", "message": str(e)})
                
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


from app.live_dashboard import register_live_dashboard
register_live_dashboard(app, scenario_runner, destination_manager)
