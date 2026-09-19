"""
Pydantic Models and Data Schemas for Network Topology Simulator
"""

from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class EcosystemMode(str, Enum):
    PURE_CISCO = "pure_cisco"
    MIXED_VENDOR = "mixed_vendor"


class NodeType(str, Enum):
    FIREWALL = "firewall"
    ROUTER = "router"
    SWITCH = "switch"
    LOAD_BALANCER = "load_balancer"
    SUBNET = "subnet"
    WEB_SERVER = "web_server"
    DATABASE = "database"
    CLIENT_EXTERNAL = "client_external"
    WIRELESS_AP = "wireless_ap"
    SASE_PROXY = "sase_proxy"
    OPTICAL_CORE = "optical_core"


class ScenarioType(str, Enum):
    # Baseline Scenarios
    NORMAL_TRAFFIC = "normal_traffic"
    DDOS_ATTACK = "ddos_attack"
    SQL_INJECTION = "sql_injection"
    LATERAL_MOVEMENT = "lateral_movement"
    # Mode A: Pure Cisco Architecture
    CISCO_CAMPUS_ROGUE = "cisco_campus_rogue"
    CISCO_SDWAN_BROWNOUT = "cisco_sdwan_brownout"
    CISCO_ACI_MICROBURST = "cisco_aci_microburst"
    # Mode B: Mixed-Vendor Enterprise Infrastructure
    MIXED_EDGE_BREACH = "mixed_edge_breach"
    MIXED_SASE_DEGRADATION = "mixed_sase_degradation"
    MIXED_BACKBONE_OPTICAL = "mixed_backbone_optical"


class SecurityZoneType(str, Enum):
    DMZ = "dmz"
    INTERNAL_TRUST = "internal_trust"
    CORE_BACKBONE = "core_backbone"
    EDGE_UNTRUST = "edge_untrust"
    DC_FABRIC = "dc_fabric"
    CLOUD_SASE = "cloud_sase"


class ZoneAnnotation(BaseModel):
    id: str
    name: str
    zone_type: SecurityZoneType = SecurityZoneType.INTERNAL_TRUST
    color: str = "#0284c7"
    opacity: float = 0.15
    x: float
    y: float
    width: float
    height: float
    description: Optional[str] = None


class NodePowerState(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    PAUSED = "paused"
    WIPED = "wiped"


class NetworkInterface(BaseModel):
    name: str = "GigabitEthernet0/0/1"
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    speed_mbps: int = 1000
    duplex: str = "full"
    mtu: int = 1500
    oper_status: str = "up"
    admin_status: str = "up"
    vlan_id: Optional[int] = 1
    in_octets: int = 0
    out_octets: int = 0
    in_errors: int = 0
    out_errors: int = 0


class NodeHardware(BaseModel):
    vcpu_count: int = 2
    ram_mb: int = 4096
    boot_time_sec: int = 5
    cpu_utilization_pct: float = 18.5
    memory_utilization_pct: float = 34.0
    temperature_celsius: float = 41.2
    interfaces: List[NetworkInterface] = Field(default_factory=list)


class TelemetryTransportConfig(BaseModel):
    hec_enabled: bool = True
    hec_url: str = "https://127.0.0.1:8888/services/collector"
    hec_token: str = "00000000-0000-0000-0000-000000000000"
    hec_index: str = "idx_network_ops"
    
    syslog_enabled: bool = False
    syslog_host: str = "127.0.0.1"
    syslog_port: int = 514
    syslog_protocol: str = "udp"  # udp or tcp
    syslog_facility: int = 16     # local0
    syslog_format: str = "rfc5424" # rfc5424 or rfc3164


class Node(BaseModel):
    id: str
    name: str
    type: NodeType
    x: float
    y: float
    ip_address: str = "10.0.1.1"
    status: str = "active"  # active, degraded, breached, blocked
    power_state: NodePowerState = NodePowerState.RUNNING
    vendor: str = "generic"  # cisco_catalyst, cisco_nexus, palo_alto, arista, juniper, nokia, zscaler, etc.
    sourcetype: Optional[str] = None
    interface: Optional[str] = "GigabitEthernet1/0/1"
    role: Optional[str] = None
    subnet: Optional[str] = "10.0.1.0/24"
    zone_id: Optional[str] = None
    hardware: Optional[NodeHardware] = Field(default_factory=NodeHardware)
    transport_config: Optional[TelemetryTransportConfig] = None
    config: Dict[str, Any] = Field(default_factory=dict)


class Edge(BaseModel):
    id: str
    source: str
    target: str
    source_port: str = "port-1"
    target_port: str = "port-1"
    status: str = "up"  # up, down, congested, breached
    link_type: str = "ethernet"  # ethernet, serial, fiber, trunk
    bandwidth_mbps: int = 1000
    latency_ms: float = 1.0


class TopologyState(BaseModel):
    nodes: List[Node] = Field(default_factory=list)
    edges: List[Edge] = Field(default_factory=list)
    zones: List[ZoneAnnotation] = Field(default_factory=list)
    global_transport: Optional[TelemetryTransportConfig] = Field(default_factory=TelemetryTransportConfig)


class SyslogTestRequest(BaseModel):
    host: str = "127.0.0.1"
    port: int = 514
    protocol: str = "udp"
    message: Optional[str] = "RFC5424 Test Event from Network Telemetry Simulator"
    format: str = "rfc5424"



class SimulationRequest(BaseModel):
    scenario: ScenarioType
    ecosystem_mode: Optional[EcosystemMode] = EcosystemMode.MIXED_VENDOR
    running: bool = True
    speed_ms: int = 500


class LogEntry(BaseModel):
    timestamp: str
    device_id: str
    src_ip: str
    dest_ip: str
    protocol: str
    duration: str
    action: str  # blocked, allowed, alerted, dropped
    signature: str
    status: str  # normal, blocked, breached, degraded
    raw_log: str
    node_type: str
    node_id: str
    vendor: str = "generic"
    sourcetype: Optional[str] = None


class BGPSessionState(str, Enum):
    IDLE = "IDLE"
    CONNECT = "CONNECT"
    ACTIVE = "ACTIVE"
    OPENSENT = "OPENSENT"
    OPENCONFIRM = "OPENCONFIRM"
    ESTABLISHED = "ESTABLISHED"


class OSPFNeighborState(str, Enum):
    DOWN = "DOWN"
    INIT = "INIT"
    TWO_WAY = "2WAY"
    EXSTART = "EXSTART"
    EXCHANGE = "EXCHANGE"
    LOADING = "LOADING"
    FULL = "FULL"


class InterfaceOperStatus(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    TESTING = "TESTING"
    DORMANT = "DORMANT"


class OpenConfigSubscriptionMode(str, Enum):
    SAMPLE = "SAMPLE"
    ON_CHANGE = "ON_CHANGE"


class FaultScenarioType(str, Enum):
    LINK_CUT = "link_cut"
    HARDWARE_EXHAUSTION = "hardware_exhaustion"
    BGP_ROUTE_FLAP = "bgp_route_flap"
    DDOS_SYN_FLOOD = "ddos_syn_flood"
    LATERAL_MOVEMENT = "lateral_movement"
    OPTICAL_BER_DEGRADATION = "optical_ber_degradation"


class FaultInjectionRequest(BaseModel):
    scenario_type: FaultScenarioType
    target_edge_id: Optional[str] = None
    target_node_id: Optional[str] = None
    severity: str = "critical"
    duration_sec: int = 30
    cascade_enabled: bool = True
    parameters: Dict[str, Any] = Field(default_factory=dict)


class FaultRecoveryRequest(BaseModel):
    fault_id: Optional[str] = None
    target_edge_id: Optional[str] = None
    target_node_id: Optional[str] = None


class FaultEventRecord(BaseModel):
    id: str
    scenario_type: FaultScenarioType
    timestamp: float
    target_id: str
    description: str
    cascades_count: int = 0
    status: str = "active"  # active, recovered
    affected_nodes: List[str] = Field(default_factory=list)
    affected_edges: List[str] = Field(default_factory=list)

