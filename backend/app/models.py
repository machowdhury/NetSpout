"""
Pydantic Models and Data Schemas for Network Topology Simulator (NetSpout)
Includes full support for:
  - OpenConfig YANG & Model-Driven Telemetry (MDT)
  - SC4SNMP 300+ MIB library, traps & metrics
  - Multi-Pipeline Telemetry (Splunk HEC, OTel Collector, Telegraf, RFC5424 Syslog)
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
    STORAGE_SAN = "storage_san"
    STORAGE_NAS = "storage_nas"
    VPN_GATEWAY = "vpn_gateway"
    CLOUD_TRANSIT = "cloud_transit"
    IOT_SENSOR = "iot_sensor"
    WLC_CONTROLLER = "wlc_controller"


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
    # Mode C: OpenConfig & Telemetry
    OPENCONFIG_MDT_STREAMING = "openconfig_mdt_streaming"
    # 11 Network Architectures (PAN to GAN)
    ARCH_PAN_IOT_MESH = "arch_pan_iot_mesh"
    ARCH_LAN_CAMPUS_ACCESS = "arch_lan_campus_access"
    ARCH_WLAN_MERAKI_CATALYST = "arch_wlan_meraki_catalyst"
    ARCH_CAN_MULTI_BUILDING = "arch_can_multi_building"
    ARCH_MAN_CARRIER_RING = "arch_man_carrier_ring"
    ARCH_WAN_GLOBAL_BACKBONE = "arch_wan_global_backbone"
    ARCH_SAN_FIBRE_CHANNEL = "arch_san_fibre_channel"
    ARCH_NAS_STORAGE_CLUSTER = "arch_nas_storage_cluster"
    ARCH_VPN_REMOTE_WORKFORCE = "arch_vpn_remote_workforce"
    ARCH_EPN_ISOLATED_INTRANET = "arch_epn_isolated_intranet"
    ARCH_GAN_SUBSEA_CLOUD = "arch_gan_subsea_cloud"
    # Specialized Unified Scenarios
    PURE_CISCO_ENTERPRISE = "pure_cisco_enterprise"
    MIXED_VENDOR_ENTERPRISE = "mixed_vendor_enterprise"
    SERVICE_PROVIDER_CISCO = "service_provider_cisco"
    SERVICE_PROVIDER_MIXED = "service_provider_mixed"
    SDWAN_CONNECTED_CORE = "sdwan_connected_core"
    WIRELESS_CONNECTED_CORE_CISCO = "wireless_connected_core_cisco"
    WIRELESS_CONNECTED_CORE_MIXED = "wireless_connected_core_mixed"


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
    zone_type: SecurityZoneType
    color: str = "#06b6d4"
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
    # 1. Performance & Traffic
    bandwidth_utilization_pct: float = 0.0
    throughput_bps: float = 0.0
    latency_ms: float = 0.0
    jitter_ms: float = 0.0
    packet_loss_pct: float = 0.0
    error_rate_pct: float = 0.0
    # 2. Device & Infrastructure Health
    uptime_seconds: int = 86400
    cpu_utilization_pct: float = 18.5
    memory_utilization_pct: float = 34.0
    temperature_celsius: float = 41.2
    psu_status: str = "ok"
    psu_wattage: float = 350.0
    ups_battery_runtime_min: int = 120
    ups_input_voltage: float = 120.0
    # 3. Configuration & Protocols
    routing_table_version: int = 1
    bgp_prefix_count: int = 0
    route_flaps: int = 0
    config_drift_checksum: str = "a1b2c3d4"
    ipam_dhcp_exhaustion_pct: float = 0.0
    # 4. Security & Compliance
    traffic_spike_score: float = 0.0
    unauthorized_access_attempts: int = 0
    firewall_drop_count: int = 0
    threat_severity_level: str = "low"
    interfaces: List[NetworkInterface] = Field(default_factory=list)


# =========================================================================
# Multi-Pipeline Telemetry Transport Configuration
# =========================================================================
class TelemetryTransportConfig(BaseModel):
    # 1. Splunk HEC Pipeline
    hec_enabled: bool = True
    hec_url: str = "https://127.0.0.1:8888/services/collector"
    hec_token: str = "00000000-0000-0000-0000-000000000000"
    hec_index: str = "idx_network_ops"
    hec_metric_index: str = "cisco_mdt_metrics"
    
    # 2. OpenTelemetry (OTel) Collector Pipeline (OTLP HTTP)
    otel_enabled: bool = False
    otel_endpoint: str = "http://127.0.0.1:4318"
    otel_metrics_path: str = "/v1/metrics"
    otel_logs_path: str = "/v1/logs"
    otel_headers: Dict[str, str] = Field(default_factory=dict)
    otel_service_name: str = "netspout-telemetry-engine"

    # 3. Telegraf Pipeline (HTTP / Influx Line Protocol or JSON)
    telegraf_enabled: bool = False
    telegraf_endpoint: str = "http://127.0.0.1:8080/telegraf"
    telegraf_format: str = "influx"  # influx, json

    # 4. Direct Syslog Pipeline (RFC 5424 / RFC 3164)
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
    status: str = "active"  # active, degraded, breached, blocked, stopped, paused
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


# =========================================================================
# SNMP & SC4SNMP Schemas
# =========================================================================
class SNMPProtocolVersion(str, Enum):
    V2C = "v2c"
    V3 = "v3"


class SNMPSecurityLevel(str, Enum):
    NO_AUTH_NO_PRIV = "noAuthNoPriv"
    AUTH_NO_PRIV = "authNoPriv"
    AUTH_PRIV = "authPriv"


class SNMPMibDefinition(BaseModel):
    name: str
    oid: str
    mib_module: str
    data_type: str  # Counter32, Counter64, Gauge32, Integer32, OctetString, IpAddress, TimeTicks
    description: str
    is_table: bool = False
    vendor: str = "RFC"  # RFC, Cisco, Juniper, Arista


class SNMPPollingMetric(BaseModel):
    timestamp: float
    host: str
    oid: str
    mib_module: str
    metric_name: str
    value: float
    dimensions: Dict[str, Any] = Field(default_factory=dict)
    community: str = "public"
    sourcetype: str = "sc4snmp:metric"
    index: str = "cisco_mdt_metrics"


class SNMPTrapEvent(BaseModel):
    timestamp: float
    host: str
    trap_oid: str
    trap_name: str
    enterprise: str
    generic_trap: Optional[int] = 6
    specific_trap: Optional[int] = 1
    varbinds: Dict[str, Any] = Field(default_factory=dict)
    severity: str = "warning"  # informational, warning, minor, major, critical
    sourcetype: str = "sc4snmp:event"
    index: str = "idx_network_ops"


class SNMPTrapTriggerRequest(BaseModel):
    trap_name: str
    host: str
    target_node_id: Optional[str] = None
    severity: str = "warning"
    varbind_overrides: Dict[str, Any] = Field(default_factory=dict)
    destinations: Optional[TelemetryTransportConfig] = None


class SNMPPollRequest(BaseModel):
    host: str
    mib_module: Optional[str] = "IF-MIB"
    target_node_id: Optional[str] = None
    destinations: Optional[TelemetryTransportConfig] = None


# =========================================================================
# OpenConfig YANG & Export Configuration
# =========================================================================
class OpenConfigSubscriptionMode(str, Enum):
    SAMPLE = "SAMPLE"
    ON_CHANGE = "ON_CHANGE"


class OpenConfigExportConfig(BaseModel):
    rfc7951_json_ietf: bool = True
    gnmi_encoding: str = "json_ietf"  # json_ietf, proto, kv
    export_pipelines: List[str] = Field(default_factory=lambda: ["hec"])


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


class FaultScenarioType(str, Enum):
    LINK_CUT = "link_cut"
    HARDWARE_EXHAUSTION = "hardware_exhaustion"
    BGP_ROUTE_FLAP = "bgp_route_flap"
    DDOS_SYN_FLOOD = "ddos_syn_flood"
    LATERAL_MOVEMENT = "lateral_movement"
    OPTICAL_BER_DEGRADATION = "optical_ber_degradation"
    SNMP_TRAP_BURST = "snmp_trap_burst"


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


class SimulationRequest(BaseModel):
    scenario: ScenarioType
    ecosystem_mode: Optional[EcosystemMode] = EcosystemMode.MIXED_VENDOR
    running: bool = True
    speed_ms: int = 500


class SyslogTestRequest(BaseModel):
    host: str = "127.0.0.1"
    port: int = 514
    protocol: str = "udp"
    message: Optional[str] = "RFC5424 Test Event from Network Telemetry Simulator"
    format: str = "rfc5424"


class PipelineTestRequest(BaseModel):
    pipeline: str  # "hec", "otel", "telegraf", "syslog"
    config: TelemetryTransportConfig
