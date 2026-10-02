# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/models.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""
Pydantic Models and Data Schemas for Network Topology Simulator (NetSpout)
Includes full support for:
  - OpenConfig YANG & Model-Driven Telemetry (MDT)
  - SC4SNMP 300+ MIB library, traps & metrics
  - Multi-Pipeline Telemetry (Splunk HEC, OTel Collector, Telegraf, RFC5424 Syslog)
"""

from enum import Enum
import time
from typing import List, Dict, Optional, Any, Union

try:
    from pydantic import BaseModel, Field
except ImportError:
    class _FieldDefault:
        def __init__(self, default=None, default_factory=None):
            self.default = default
            self.default_factory = default_factory
        def get_value(self):
            if self.default_factory is not None:
                return self.default_factory()
            return self.default

    def Field(default=None, *, default_factory=None, **kwargs):
        return _FieldDefault(default=default, default_factory=default_factory)

    class BaseModel:
        def __init__(self, **kwargs):
            for cls in reversed(self.__class__.__mro__):
                for k, v in getattr(cls, "__dict__", {}).items():
                    if k.startswith("_"):
                        continue
                    if isinstance(v, _FieldDefault):
                        setattr(self, k, v.get_value())
                    elif not callable(v):
                        setattr(self, k, v)
            for k, v in kwargs.items():
                setattr(self, k, v)

        def dict(self, *args, **kwargs):
            return {k: (v.dict() if hasattr(v, "dict") else v) for k, v in self.__dict__.items() if not k.startswith("_")}

        def model_dump(self, *args, **kwargs):
            return self.dict(*args, **kwargs)


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
    id: str = "zone-default"
    name: str = "Default Zone"
    zone_type: SecurityZoneType = SecurityZoneType.INTERNAL_TRUST
    color: str = "#0284c7"
    opacity: float = 0.15
    x: float = 0.0
    y: float = 0.0
    width: float = 200.0
    height: float = 200.0
    description: Optional[str] = None

    def __init__(self, **kwargs):
        if "zone_id" in kwargs and "id" not in kwargs:
            kwargs["id"] = kwargs.pop("zone_id")
        super().__init__(**kwargs)



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
    hec_ssl_verify: bool = False
    hec_allow_insecure_tls: bool = True
    default_index: Optional[str] = None
    hec_endpoint: Optional[str] = None

    def __init__(self, **data):
        if "hec_endpoint" in data and ("hec_url" not in data or not data["hec_url"]):
            data["hec_url"] = data["hec_endpoint"]
        if "endpoint" in data and ("hec_url" not in data or not data["hec_url"]):
            data["hec_url"] = data["endpoint"]
        if "default_index" in data and ("hec_index" not in data or not data["hec_index"]):
            data["hec_index"] = data["default_index"]
        if "index" in data and ("hec_index" not in data or not data["hec_index"]):
            data["hec_index"] = data["index"]
        if "token" in data and ("hec_token" not in data or not data["hec_token"]):
            data["hec_token"] = data["token"]
        super().__init__(**data)
        if self.default_index and (not self.hec_index or self.hec_index == "idx_network_ops"):
            self.hec_index = self.default_index
        if self.hec_endpoint and (not self.hec_url or self.hec_url == "https://127.0.0.1:8888/services/collector"):
            self.hec_url = self.hec_endpoint
    
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

    # 5. Native Flow Telemetry Pipeline (RFC 3954 NetFlow v9 & RFC 7011 IPFIX)
    native_flow_enabled: bool = False
    native_flow_protocol: str = "IPFIX"  # NETFLOW_V9, IPFIX, BOTH
    native_flow_collector_host: str = "127.0.0.1"
    native_flow_netflow_port: int = 2055
    native_flow_ipfix_port: int = 4739
    native_flow_observation_domain_id: int = 1
    native_flow_rate_limit_pps: int = 100
    native_flow_packet_cap: int = 10000
    native_flow_template_refresh_policy: str = "EVERY_BURST"
    native_flow_allow_public: bool = False

    # 6. Native SNMPv2c Telemetry Pipeline (RFC 3416 / RFC 1905)
    native_snmp_enabled: bool = False
    native_snmp_pdu_mode: str = "TRAP"  # TRAP, INFORM, MIXED
    native_snmp_receiver_host: str = "127.0.0.1"
    native_snmp_receiver_port: int = 1162
    native_snmp_community: str = "netspout-lab"
    native_snmp_trap_rate_pps: int = 50
    native_snmp_inform_rate_pps: int = 25
    native_snmp_packet_cap: int = 1000
    native_snmp_inform_timeout_ms: int = 1500
    native_snmp_inform_max_retries: int = 2
    native_snmp_allow_public: bool = False


class Node(BaseModel):
    id: str
    name: str = ""
    type: NodeType = NodeType.SWITCH
    x: float = 0.0
    y: float = 0.0
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
    packet_loss_pct: float = 0.0
    jitter_ms: float = 0.0


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
    data_type: str  # Counter32, Counter64, Gauge32, Integer32, OctetString, IpAddress, TimeTicks, ObjectIdentifier
    description: str
    is_table: bool = False
    vendor: str = "RFC"  # RFC, Cisco, Juniper, Arista
    fidelity: str = "STANDARD_VERIFIED"


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
    netspout_run_id: Optional[str] = None
    netspout_scenario_id: Optional[str] = None
    netspout_phase: Optional[str] = None
    netspout_device_id: Optional[str] = None
    netspout_event_id: Optional[str] = None
    netspout_parent_event_id: Optional[str] = None
    netspout_ground_truth: Optional[str] = None


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


# =========================================================================
# Gate 4: Unified Scenario, Topology, & Use-Case Contract Models
# =========================================================================

class ScenarioPhase(str, Enum):
    INITIALIZE = "INITIALIZE"
    BASELINE = "BASELINE"
    DEGRADE = "DEGRADE"
    FAULT = "FAULT"
    PROPAGATE = "PROPAGATE"
    FAILOVER = "FAILOVER"
    RECOVER = "RECOVER"
    VALIDATE = "VALIDATE"
    COMPLETE = "COMPLETE"


class ValidationType(str, Enum):
    EVENT_EXISTS = "EVENT_EXISTS"
    FIELD_VALUE = "FIELD_VALUE"
    METRIC_EXISTS = "METRIC_EXISTS"
    METRIC_THRESHOLD = "METRIC_THRESHOLD"
    METRIC_PROGRESSION = "METRIC_PROGRESSION"
    STATE_TRANSITION = "STATE_TRANSITION"
    COUNT_THRESHOLD = "COUNT_THRESHOLD"
    SEQUENCE = "SEQUENCE"
    DESTINATION_CHECK = "DESTINATION_CHECK"
    CROSS_SOURCE_COHERENCE = "CROSS_SOURCE_COHERENCE"
    SPL_QUERY = "SPL_QUERY"


class ValidationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_RUN = "NOT_RUN"
    BLOCKED = "BLOCKED"


class ValidationRule(BaseModel):
    id: str
    name: str
    type: ValidationType = ValidationType.EVENT_EXISTS
    description: str = ""
    target_sourcetype: Optional[str] = None
    target_index: Optional[str] = None
    target_vendor: Optional[str] = None
    target_gnmi_path: Optional[str] = None
    target_phase: Optional[str] = None
    target_metric_name: Optional[str] = None
    target_field: Optional[str] = None
    expected_value: Optional[Any] = None
    expected_sequence: Optional[List[Any]] = None
    required_sources: Optional[List[str]] = None
    comparison: str = "=="  # "==", "!=", ">=", "<=", ">", "<", "in", "contains"
    min_count: Optional[int] = 1
    spl_query: Optional[str] = None


class ValidationResult(BaseModel):
    rule_id: str
    rule_name: str
    status: ValidationStatus = ValidationStatus.NOT_RUN
    message: str = ""
    observed_value: Optional[Any] = None
    expected_value: Optional[Any] = None
    evidence: Optional[Dict[str, Any]] = None


class UseCaseContract(BaseModel):
    objective: str  # WHAT ARE WE PROVING?
    required_telemetry: List[str] = Field(default_factory=list)  # WHAT DATA IS REQUIRED?
    expected_progression: List[str] = Field(default_factory=list)  # WHAT SHOULD HAPPEN?
    expected_observations: List[str] = Field(default_factory=list)  # WHAT SHOULD THE USER OBSERVE?
    validation_criteria: List[str] = Field(default_factory=list)  # HOW DO WE KNOW IT WORKED?
    telemetry_model: Optional[str] = None
    transport_protocol: Optional[str] = None
    splunk_storage: Optional[str] = None
    fidelity_badge: Optional[str] = None
    telemetry_notes: Optional[str] = None
    timing_claim: Optional[str] = None
    timing_value: Optional[float] = None
    timing_unit: Optional[str] = None
    timing_classification: Optional[str] = None
    timing_notes: Optional[str] = None


class ScenarioPhaseDefinition(BaseModel):
    phase: ScenarioPhase
    name: str = ""
    duration_ticks: int = 1
    description: str = ""
    fault_action: Optional[Dict[str, Any]] = None
    recovery_action: Optional[Dict[str, Any]] = None
    expected_observations: List[str] = Field(default_factory=list)


class ScenarioContract(BaseModel):
    id: str
    code: Optional[str] = None
    display_name: str = ""
    name: Optional[str] = None
    category: str = "NETWORK_OPERATIONS"
    difficulty: str = "INTERMEDIATE"  # BEGINNER, INTERMEDIATE, ADVANCED
    estimated_duration_sec: int = 30
    topology_id: str = "cisco_campus"
    ecosystem: str = "mixed_vendor"
    maturity: str = "CONTRACTED"  # CANDIDATE, CONTRACTED, IMPLEMENTED, FORMAT_VALIDATED, E2E_VALIDATED, GOLDEN_PATH_CERTIFIED
    description: str = ""
    attack_vector: Optional[str] = None
    defense_mechanism: Optional[str] = None
    vendor_scope: List[str] = Field(default_factory=list)
    telemetry_requirements: List[str] = Field(default_factory=list)
    sourcetypes: List[str] = Field(default_factory=list)
    generation_modes: List[str] = Field(default_factory=list)
    phases: List[ScenarioPhaseDefinition] = Field(default_factory=list)
    affected_entities: List[str] = Field(default_factory=list)
    fault_definition: Optional[Dict[str, Any]] = None
    recovery_definition: Optional[Dict[str, Any]] = None
    expected_observations: List[str] = Field(default_factory=list)
    validation_rules: List[ValidationRule] = Field(default_factory=list)
    use_case: Optional[UseCaseContract] = None
    telemetry_model: Optional[str] = "Standard Telemetry Payload"
    transport_protocol: Optional[str] = "Splunk HEC"
    splunk_storage: Optional[str] = "Splunk Event Index (idx_network_ops)"
    fidelity_badge: Optional[str] = "MODELED PAYLOAD"
    telemetry_notes: Optional[str] = None
    native_snmp_supported: bool = False
    native_snmp_capabilities: Optional[Dict[str, Any]] = None
    timing_claim: Optional[str] = None
    timing_value: Optional[float] = None
    timing_unit: Optional[str] = None
    timing_classification: str = "NOT_APPLICABLE"  # MEASURED, MODELED, DECLARED_ONLY, NOT_APPLICABLE
    timing_notes: Optional[str] = None


class GroundTruthRecord(BaseModel):
    run_id: str
    scenario_id: str
    phase: str
    timestamp: float
    intentional_fault: Optional[Dict[str, Any]] = None
    intentional_recovery: Optional[Dict[str, Any]] = None
    affected_nodes: List[str] = Field(default_factory=list)
    affected_edges: List[str] = Field(default_factory=list)
    expected_observations: List[str] = Field(default_factory=list)
    expected_secondary_effects: List[str] = Field(default_factory=list)


class TelemetryType(str, Enum):
    EVENT = "EVENT"
    METRIC = "METRIC"
    FLOW = "FLOW"
    TRACE = "TRACE"


class QueryMechanism(str, Enum):
    SPL_SEARCH = "SPL_SEARCH"
    MSTATS = "MSTATS"


class EvidenceRole(str, Enum):
    REQUIRED = "REQUIRED"
    SUPPORTING = "SUPPORTING"
    OPTIONAL = "OPTIONAL"


class EvidenceDestination(BaseModel):
    id: str
    name: str
    telemetry_type: TelemetryType = TelemetryType.EVENT
    target_index: str
    sourcetype: Optional[str] = None
    metric_names: List[str] = Field(default_factory=list)
    query_mechanism: QueryMechanism = QueryMechanism.SPL_SEARCH
    query_template: Optional[str] = None
    role: EvidenceRole = EvidenceRole.REQUIRED
    expected_count: int = 0


class EvidenceObservation(BaseModel):
    destination_id: str
    name: str
    telemetry_type: TelemetryType = TelemetryType.EVENT
    target_index: str
    query_mechanism: QueryMechanism = QueryMechanism.SPL_SEARCH
    query: str
    observed_count: int = 0
    expected_count: int = 0
    status: str = "PENDING"  # PASS | FAIL | PENDING | ERROR
    role: EvidenceRole = EvidenceRole.REQUIRED
    errors: List[str] = Field(default_factory=list)


class UnifiedRunEvidence(BaseModel):
    run_id: str
    scenario_id: str
    destinations: List[EvidenceObservation] = Field(default_factory=list)
    total_generated: int = 0
    total_dispatched: int = 0
    total_observed: int = 0
    event_observed_count: int = 0
    event_expected_count: int = 0
    metric_observed_count: int = 0
    metric_expected_count: int = 0
    observation_completeness_pct: float = 0.0
    observation_status: str = "PENDING"  # COMPLETE | PARTIAL | FAILED | PENDING
    contract_validation: str = "NOT_RUN"  # PASS | FAIL | BLOCKED | NOT_RUN
    required_evidence_satisfied: bool = False
    errors: List[str] = Field(default_factory=list)


class RunManifest(BaseModel):
    run_id: str
    scenario_id: str
    scenario_name: str = ""
    topology_id: str = ""
    scenario_maturity: str = "CONTRACTED"  # CANDIDATE, CONTRACTED, IMPLEMENTED, FORMAT_VALIDATED, E2E_VALIDATED, GOLDEN_PATH_CERTIFIED
    seed: Optional[int] = None
    time_mode: str = "TEST"  # REALTIME | ACCELERATED | TEST
    transport_mode: str = "DIRECT_TO_SPLUNK"  # DIRECT_TO_SPLUNK | NATIVE_TRANSPORT
    native_protocol: Optional[str] = None
    start_time: float = Field(default_factory=time.time)
    end_time: Optional[float] = None
    duration_sec: float = 0.0
    phases_executed: List[str] = Field(default_factory=list)
    affected_devices: List[str] = Field(default_factory=list)
    expected_sourcetypes: List[str] = Field(default_factory=list)
    actual_generated_counts: Dict[str, int] = Field(default_factory=dict)
    total_events_generated: int = 0
    ground_truth_records: List[GroundTruthRecord] = Field(default_factory=list)
    validation_results: List[ValidationResult] = Field(default_factory=list)
    overall_validation: str = "NOT_RUN"  # PASS | FAIL | BLOCKED | NOT_RUN
    dispatch_results: Dict[str, Any] = Field(default_factory=dict)
    dispatch_attempted: int = 0
    dispatch_succeeded: int = 0
    dispatch_failed: int = 0
    observed_count: int = 0
    observation_status: str = "NOT_CHECKED"  # NOT_CHECKED | PENDING | VERIFIED | FAILED
    destination_validation: str = "NOT_RUN"  # NOT_RUN | PASS | FAIL | BLOCKED
    splunk_search_query: Optional[str] = None
    splunk_metric_query: Optional[str] = None
    event_observed_count: int = 0
    metric_observed_count: int = 0
    observation_completeness_pct: float = 0.0
    evidence_summary: Optional[UnifiedRunEvidence] = None
    timing_claim: Optional[str] = None
    timing_value: Optional[float] = None
    timing_unit: Optional[str] = None
    timing_classification: str = "NOT_APPLICABLE"
    timing_notes: Optional[str] = None
    errors: List[str] = Field(default_factory=list)
    native_transport_result: Optional[Any] = None
    companion_manifest: Optional[Any] = None
    native_flow_records: List[Any] = Field(default_factory=list)
    native_snmp_result: Optional[Any] = None
    native_snmp_pdus: List[Any] = Field(default_factory=list)
    snmp_e2e_scorecard: Optional[Any] = None
    snmp_normalized_events: List[Any] = Field(default_factory=list)
    snmp_polling_evidence: Optional[Any] = None


class ScenarioRunRequest(BaseModel):
    scenario_id: str
    topology_id: Optional[str] = None
    seed: Optional[int] = None
    time_mode: str = "TEST"  # REALTIME | ACCELERATED | TEST
    duration_ticks: Optional[int] = None
    dispatch_telemetry: bool = False
    transport_config: Optional[TelemetryTransportConfig] = None
    transport_mode: str = "DIRECT_TO_SPLUNK"  # DIRECT_TO_SPLUNK | NATIVE_TRANSPORT
    native_protocol: Optional[str] = None     # IPFIX | NETFLOW_V9 | SNMPV2C_TRAP | SNMPV2C_INFORM | SNMPV2C
    native_destination_host: Optional[str] = None
    native_destination_port: Optional[int] = None
    native_rate_pps: int = 100
    native_snmp_pdu_mode: Optional[str] = None  # TRAP | INFORM | MIXED
    native_snmp_community: Optional[str] = None
    native_snmp_timeout_ms: int = 1500
    native_snmp_max_retries: int = 2
    native_snmp_e2e: bool = False
    native_snmp_agent_port: Optional[int] = None


class FlowRecord(BaseModel):
    """Canonical protocol-agnostic flow record representation."""
    src_ip: str
    dest_ip: str
    src_port: int
    dest_port: int
    protocol: int = 6                     # 6=TCP, 17=UDP, 1=ICMP, 58=ICMPv6
    tcp_flags: int = 0                    # Bitmask (SYN=2, ACK=16, FIN=1, RST=4)
    tos_dscp: int = 0                     # DiffServ / Type of Service
    src_as: int = 0                       # Autonomous System Number
    dest_as: int = 0                      # Autonomous System Number
    input_snmp: int = 1                   # Ingress interface ifIndex
    output_snmp: int = 2                  # Egress interface ifIndex
    bytes_count: int = 0                  # Octets transferred
    packets_count: int = 0                # Packets transferred
    start_time_ms: int = 0                # Flow start (relative sysUptime or absolute epoch)
    end_time_ms: int = 0                  # Flow end
    ip_version: int = 4                   # 4 or 6
    bgp_next_hop: Optional[str] = None    # Next hop IP address
    vlan_id: Optional[int] = None         # 802.1Q tag
    flow_direction: int = 0               # 0=Ingress, 1=Egress
    netspout_run_id: Optional[str] = None
    netspout_scenario_id: Optional[str] = None
    netspout_phase: Optional[str] = None
    anomaly_type: Optional[str] = "normal"

    @property
    def dst_ip(self) -> str:
        return self.dest_ip

    @property
    def dst_port(self) -> int:
        return self.dest_port

    @property
    def byte_count(self) -> int:
        return self.bytes_count

    @property
    def packet_count(self) -> int:
        return self.packets_count


class TransportErrorType(str, Enum):
    DESTINATION_INVALID = "DESTINATION_INVALID"
    DESTINATION_BLOCKED = "DESTINATION_BLOCKED"
    SOCKET_CREATE_FAILED = "SOCKET_CREATE_FAILED"
    ENCODING_FAILED = "ENCODING_FAILED"
    PACKET_TOO_LARGE = "PACKET_TOO_LARGE"
    SEND_FAILED = "SEND_FAILED"
    PARTIAL_EXPORT = "PARTIAL_EXPORT"
    TEMPLATE_FAILED = "TEMPLATE_FAILED"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    CIRCUIT_BREAKER_TRIGGERED = "CIRCUIT_BREAKER_TRIGGERED"
    COLLECTOR_TIMEOUT = "COLLECTOR_TIMEOUT"


class TransportResult(BaseModel):
    transport_type: str = "UNKNOWN"       # e.g. "IPFIX_UDP", "NETFLOW_V9_UDP", "HEC"
    destination_host: str = ""
    destination_port: int = 0
    records_received: int = 0             # Count of records passed into encoder
    records_encoded: int = 0              # Count of records packed into flow sets
    datagrams_attempted: int = 0          # Number of UDP packets passed to sendto()
    datagrams_sent: int = 0               # Number of UDP packets successfully sent by OS
    bytes_sent: int = 0                   # Total wire bytes transmitted
    templates_sent: int = 0               # Number of template sets emitted
    sequence_start: int = 0               # Initial sequence number
    sequence_end: int = 0                 # Final sequence number
    encoding_failures: int = 0
    send_failures: int = 0
    elapsed_ms: float = 0.0
    errors: List[str] = Field(default_factory=list)
    error_types: List[str] = Field(default_factory=list)


class NativeFlowProtocol(str, Enum):
    NETFLOW_V9 = "NETFLOW_V9"
    IPFIX = "IPFIX"
    BOTH = "BOTH"


class TemplateRefreshPolicy(str, Enum):
    EVERY_BURST = "EVERY_BURST"
    PERIODIC = "PERIODIC"
    ADAPTIVE = "ADAPTIVE"


class CollectorHealthState(str, Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    UNREACHABLE = "UNREACHABLE"
    RECEIVING = "RECEIVING"
    FORWARDER_BLOCKED = "FORWARDER_BLOCKED"
    SPLUNK_UNAVAILABLE = "SPLUNK_UNAVAILABLE"


class NativeFlowConfig(BaseModel):
    protocol: NativeFlowProtocol = NativeFlowProtocol.IPFIX
    collector_host: str = "127.0.0.1"
    netflow_port: int = 2055
    ipfix_port: int = 4739
    observation_domain_id: int = 1
    exporter_identity: str = "10.0.0.1"
    template_id: int = 256
    template_refresh_policy: TemplateRefreshPolicy = TemplateRefreshPolicy.EVERY_BURST
    rate_limit_pps: int = 100
    packet_cap: int = 10000
    collector_enabled: bool = True
    splunk_index: str = "idx_network_ops"
    splunk_sourcetype: str = "netflow:collector"
    allow_public_export: bool = False
    goflow_metrics_port: int = 8080
    forwarder_status_port: int = 8082


class CollectorDetailedHealth(BaseModel):
    state: CollectorHealthState = CollectorHealthState.STOPPED
    collector_process: bool = False
    udp_listeners_active: bool = False
    netflow_port: int = 2055
    ipfix_port: int = 4739
    packets_received_total: int = 0
    records_decoded_total: int = 0
    decode_errors_total: int = 0
    forwarder_healthy: bool = False
    hec_connectivity: bool = False
    hec_failures_total: int = 0
    flows_forwarded_total: int = 0
    splunk_observation_verified: bool = False
    last_packet_timestamp: Optional[float] = None
    last_splunk_observation_timestamp: Optional[float] = None
    details: Dict[str, Any] = Field(default_factory=dict)


class CompanionControlManifest(BaseModel):
    run_id: str
    scenario_id: str
    protocol: str                         # "IPFIX", "NETFLOW_V9", "SNMPV2C_TRAP", "SNMPV2C_INFORM", "SNMPV2C"
    destination_host: str
    destination_port: int
    observation_domain_id: int = 1        # Or source_id
    exporter_ip: str
    template_ids: List[int] = Field(default_factory=list)
    records_generated: int = 0
    records_encoded: int = 0
    datagrams_sent: int = 0
    bytes_sent: int = 0
    start_time_epoch_ms: int = 0
    end_time_epoch_ms: int = 0
    fidelity_badge: str = "NATIVE TRANSPORT"
    splunk_suggested_spl: str = ""
    splunk_raw_events_spl: str = ""
    splunk_stats_spl: str = ""
    pipeline_stage: str = "UNKNOWN"
    troubleshooting_notes: List[str] = Field(default_factory=list)
    # Gate 12B Native SNMPv2c correlation fields
    pdu_mode: Optional[str] = None
    request_ids: List[int] = Field(default_factory=list)
    acknowledged_request_ids: List[int] = Field(default_factory=list)
    trap_oids: List[str] = Field(default_factory=list)
    informs_acknowledged: int = 0
    inform_retries: int = 0
    inform_timeouts: int = 0
    receiver_observed_count: int = 0
    # Gate 12C Native SNMPv2c Polling Agent evidence fields
    snmp_agent_bind_host: Optional[str] = None
    snmp_agent_port: Optional[int] = None
    exposed_oid_count: int = 0
    mib_families: List[str] = Field(default_factory=list)
    snmp_requests_received: int = 0
    snmp_get_requests: int = 0
    snmp_getnext_requests: int = 0
    snmp_getbulk_requests: int = 0
    snmp_responses_sent: int = 0
    snmp_malformed_requests: int = 0
    snmp_set_rejected: int = 0
    simulated_device_ids: List[str] = Field(default_factory=list)


# =========================================================================
# Gate 12B / 12C: Native SNMPv2c Protocol, Transport & Polling Models
# =========================================================================

SYSUPTIME_OID = "1.3.6.1.2.1.1.3.0"
SNMP_TRAP_OID = "1.3.6.1.6.3.1.1.4.1.0"


class SnmpVersion(int, Enum):
    V1 = 0
    V2C = 1
    V3 = 3


class SnmpPduType(int, Enum):
    GET_REQUEST = 0xA0
    GET_NEXT_REQUEST = 0xA1
    RESPONSE = 0xA2
    SET_REQUEST = 0xA3
    GET_BULK_REQUEST = 0xA5
    INFORM_REQUEST = 0xA6
    SNMPV2_TRAP = 0xA7


class SnmpAsn1Type(int, Enum):
    INTEGER = 0x02
    OCTET_STRING = 0x04
    NULL = 0x05
    OBJECT_IDENTIFIER = 0x06
    SEQUENCE = 0x30
    IP_ADDRESS = 0x40
    COUNTER32 = 0x41
    GAUGE32 = 0x42
    TIME_TICKS = 0x43
    OPAQUE = 0x44
    COUNTER64 = 0x46
    NO_SUCH_OBJECT = 0x80
    NO_SUCH_INSTANCE = 0x81
    END_OF_MIB_VIEW = 0x82


class OidFidelityClass(str, Enum):
    STANDARD_VERIFIED = "STANDARD_VERIFIED"
    VENDOR_VERIFIED = "VENDOR_VERIFIED"
    MODELED = "MODELED"
    SYNTHETIC = "SYNTHETIC"


class SnmpEvidenceStage(str, Enum):
    GENERATED = "GENERATED"
    ENCODED = "ENCODED"
    SENT = "SENT"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RECEIVER_OBSERVED = "RECEIVER_OBSERVED"
    REQUEST_RECEIVED = "REQUEST_RECEIVED"
    REQUEST_DECODED = "REQUEST_DECODED"
    RESPONSE_GENERATED = "RESPONSE_GENERATED"
    RESPONSE_ENCODED = "RESPONSE_ENCODED"
    RESPONSE_SENT = "RESPONSE_SENT"
    MANAGER_OBSERVED = "MANAGER_OBSERVED"
    SPLUNK_DISPATCHED = "SPLUNK_DISPATCHED"
    SPLUNK_OBSERVED = "SPLUNK_OBSERVED"
    VALIDATED = "VALIDATED"


ASN1_TYPE_NAME_TO_TAG: Dict[str, int] = {
    "INTEGER": 0x02,
    "INTEGER32": 0x02,
    "INT": 0x02,
    "OCTETSTRING": 0x04,
    "OCTET_STRING": 0x04,
    "OCTET STRING": 0x04,
    "STRING": 0x04,
    "NULL": 0x05,
    "OBJECTIDENTIFIER": 0x06,
    "OBJECT_IDENTIFIER": 0x06,
    "OBJECT IDENTIFIER": 0x06,
    "OID": 0x06,
    "SEQUENCE": 0x30,
    "IPADDRESS": 0x40,
    "IP_ADDRESS": 0x40,
    "COUNTER32": 0x41,
    "COUNTER": 0x41,
    "GAUGE32": 0x42,
    "GAUGE": 0x42,
    "UNSIGNED32": 0x42,
    "TIMETICKS": 0x43,
    "TIME_TICKS": 0x43,
    "OPAQUE": 0x44,
    "COUNTER64": 0x46,
    "NOSUCHOBJECT": 0x80,
    "NO_SUCH_OBJECT": 0x80,
    "NOSUCHINSTANCE": 0x81,
    "NO_SUCH_INSTANCE": 0x81,
    "ENDOFMIBVIEW": 0x82,
    "END_OF_MIB_VIEW": 0x82,
}

ASN1_TAG_TO_CANONICAL_NAME: Dict[int, str] = {
    0x02: "Integer32",
    0x04: "OctetString",
    0x05: "Null",
    0x06: "ObjectIdentifier",
    0x30: "Sequence",
    0x40: "IpAddress",
    0x41: "Counter32",
    0x42: "Gauge32",
    0x43: "TimeTicks",
    0x44: "Opaque",
    0x46: "Counter64",
    0x80: "noSuchObject",
    0x81: "noSuchInstance",
    0x82: "endOfMibView",
}


def resolve_asn1_tag(asn1_type: Union[int, str, SnmpAsn1Type]) -> int:
    if isinstance(asn1_type, SnmpAsn1Type):
        return int(asn1_type.value)
    if isinstance(asn1_type, int):
        if asn1_type in ASN1_TAG_TO_CANONICAL_NAME:
            return asn1_type
        raise ValueError(f"Unsupported ASN.1 tag integer: 0x{asn1_type:02x}")
    if isinstance(asn1_type, str):
        key = asn1_type.strip().upper()
        if key in ASN1_TYPE_NAME_TO_TAG:
            return ASN1_TYPE_NAME_TO_TAG[key]
    raise ValueError(f"Unsupported ASN.1 type specification: {asn1_type!r}")


class SnmpVarBind(BaseModel):
    oid: str
    asn1_type: str = "OctetString"
    value: Any = None
    mib_module: Optional[str] = None
    object_name: Optional[str] = None
    fidelity: str = OidFidelityClass.STANDARD_VERIFIED.value

    def __init__(self, **data):
        if "syntax" in data and "asn1_type" not in data:
            data["asn1_type"] = data.pop("syntax")
        if "tag" in data and "asn1_type" not in data:
            tag_val = data.pop("tag")
            data["asn1_type"] = ASN1_TAG_TO_CANONICAL_NAME.get(int(tag_val), str(tag_val))
        elif "asn1_type" in data and isinstance(data["asn1_type"], (int, SnmpAsn1Type)):
            tag_val = int(data["asn1_type"].value if isinstance(data["asn1_type"], SnmpAsn1Type) else data["asn1_type"])
            data["asn1_type"] = ASN1_TAG_TO_CANONICAL_NAME.get(tag_val, str(tag_val))
        super().__init__(**data)

    @property
    def tag(self) -> int:
        return resolve_asn1_tag(self.asn1_type)


def validate_notification_varbind_order(varbinds: List[SnmpVarBind]) -> None:
    """
    Enforces RFC 3416 Section 4.2.6 mandatory notification varbind ordering:
      VarBind[0] MUST be sysUpTime.0 (1.3.6.1.2.1.1.3.0, TimeTicks / 0x43)
      VarBind[1] MUST be snmpTrapOID.0 (1.3.6.1.6.3.1.1.4.1.0, ObjectIdentifier / 0x06)
    """
    if len(varbinds) < 2:
        raise ValueError(
            f"SNMPv2c notification PDU requires at least 2 varbinds (sysUpTime.0 and snmpTrapOID.0), got {len(varbinds)}"
        )
    vb0 = varbinds[0]
    vb1 = varbinds[1]
    if vb0.oid != SYSUPTIME_OID:
        raise ValueError(
            f"VarBind[0] must be sysUpTime.0 ({SYSUPTIME_OID}), got {vb0.oid!r}"
        )
    if resolve_asn1_tag(vb0.asn1_type) != SnmpAsn1Type.TIME_TICKS.value:
        raise ValueError(
            f"VarBind[0] (sysUpTime.0) must have ASN.1 type TimeTicks (0x43), got {vb0.asn1_type!r}"
        )
    if vb1.oid != SNMP_TRAP_OID:
        raise ValueError(
            f"VarBind[1] must be snmpTrapOID.0 ({SNMP_TRAP_OID}), got {vb1.oid!r}"
        )
    if resolve_asn1_tag(vb1.asn1_type) != SnmpAsn1Type.OBJECT_IDENTIFIER.value:
        raise ValueError(
            f"VarBind[1] (snmpTrapOID.0) must have ASN.1 type ObjectIdentifier (0x06), got {vb1.asn1_type!r}"
        )


class SnmpMessage(BaseModel):
    version: int = SnmpVersion.V2C.value
    community: str = "netspout-lab"
    pdu_type: int = SnmpPduType.SNMPV2_TRAP.value
    request_id: int = 1
    error_status: int = 0
    error_index: int = 0
    varbinds: List[SnmpVarBind] = Field(default_factory=list)
    source_device_id: Optional[str] = None
    source_ip: Optional[str] = None
    scenario_id: Optional[str] = None
    phase: Optional[str] = None
    non_repeaters: Optional[int] = None
    max_repetitions: Optional[int] = None

    def __init__(self, **data):
        if "pdu_type" in data and isinstance(data["pdu_type"], SnmpPduType):
            data["pdu_type"] = int(data["pdu_type"].value)
        if "version" in data and isinstance(data["version"], SnmpVersion):
            data["version"] = int(data["version"].value)
        if "varbinds" in data and isinstance(data["varbinds"], list):
            converted = []
            for vb in data["varbinds"]:
                if isinstance(vb, dict):
                    converted.append(SnmpVarBind(**vb))
                else:
                    converted.append(vb)
            data["varbinds"] = converted
        super().__init__(**data)


class SnmpTrap(SnmpMessage):
    pdu_type: int = SnmpPduType.SNMPV2_TRAP.value

    def __init__(self, **data):
        data["pdu_type"] = int(SnmpPduType.SNMPV2_TRAP.value)
        sys_uptime = data.pop("sys_uptime", None)
        trap_oid = data.pop("trap_oid", None)
        vbs = list(data.get("varbinds", []))
        converted_vbs = [SnmpVarBind(**vb) if isinstance(vb, dict) else vb for vb in vbs]
        if sys_uptime is not None and trap_oid is not None:
            if not converted_vbs or converted_vbs[0].oid != SYSUPTIME_OID:
                converted_vbs = [
                    SnmpVarBind(
                        oid=SYSUPTIME_OID,
                        asn1_type="TimeTicks",
                        value=int(sys_uptime),
                        mib_module="SNMPv2-MIB",
                        object_name="sysUpTime.0",
                        fidelity=OidFidelityClass.STANDARD_VERIFIED.value
                    ),
                    SnmpVarBind(
                        oid=SNMP_TRAP_OID,
                        asn1_type="ObjectIdentifier",
                        value=str(trap_oid),
                        mib_module="SNMPv2-MIB",
                        object_name="snmpTrapOID.0",
                        fidelity=OidFidelityClass.STANDARD_VERIFIED.value
                    )
                ] + converted_vbs
        data["varbinds"] = converted_vbs
        super().__init__(**data)
        validate_notification_varbind_order(self.varbinds)

    @property
    def sys_uptime(self) -> int:
        return int(self.varbinds[0].value)

    @property
    def trap_oid(self) -> str:
        return str(self.varbinds[1].value)


class SnmpInform(SnmpMessage):
    pdu_type: int = SnmpPduType.INFORM_REQUEST.value

    def __init__(self, **data):
        data["pdu_type"] = int(SnmpPduType.INFORM_REQUEST.value)
        sys_uptime = data.pop("sys_uptime", None)
        trap_oid = data.pop("trap_oid", None)
        vbs = list(data.get("varbinds", []))
        converted_vbs = [SnmpVarBind(**vb) if isinstance(vb, dict) else vb for vb in vbs]
        if sys_uptime is not None and trap_oid is not None:
            if not converted_vbs or converted_vbs[0].oid != SYSUPTIME_OID:
                converted_vbs = [
                    SnmpVarBind(
                        oid=SYSUPTIME_OID,
                        asn1_type="TimeTicks",
                        value=int(sys_uptime),
                        mib_module="SNMPv2-MIB",
                        object_name="sysUpTime.0",
                        fidelity=OidFidelityClass.STANDARD_VERIFIED.value
                    ),
                    SnmpVarBind(
                        oid=SNMP_TRAP_OID,
                        asn1_type="ObjectIdentifier",
                        value=str(trap_oid),
                        mib_module="SNMPv2-MIB",
                        object_name="snmpTrapOID.0",
                        fidelity=OidFidelityClass.STANDARD_VERIFIED.value
                    )
                ] + converted_vbs
        data["varbinds"] = converted_vbs
        super().__init__(**data)
        validate_notification_varbind_order(self.varbinds)

    @property
    def sys_uptime(self) -> int:
        return int(self.varbinds[0].value)

    @property
    def trap_oid(self) -> str:
        return str(self.varbinds[1].value)


class SnmpResponse(SnmpMessage):
    pdu_type: int = SnmpPduType.RESPONSE.value

    def __init__(self, **data):
        data["pdu_type"] = int(SnmpPduType.RESPONSE.value)
        super().__init__(**data)

    @classmethod
    def from_inform(cls, inform: SnmpMessage, error_status: int = 0, error_index: int = 0) -> "SnmpResponse":
        """
        Constructs an RFC 3416 Section 4.2.7 Response-PDU (0xA2) acknowledging an InformRequest-PDU (0xA6)
        with identical version, community, request-id, error-status=0, error-index=0, and varbinds.
        """
        return cls(
            version=inform.version,
            community=inform.community,
            request_id=inform.request_id,
            error_status=error_status,
            error_index=error_index,
            varbinds=list(inform.varbinds),
            source_device_id=inform.source_device_id,
            source_ip=inform.source_ip,
            scenario_id=inform.scenario_id,
            phase=inform.phase
        )


class SnmpTransportResult(BaseModel):
    transport_type: str = "SNMPV2C_UDP"
    pdu_mode: str = "TRAP"                # "TRAP", "INFORM", "MIXED"
    destination_host: str = "127.0.0.1"
    destination_port: int = 1162
    pdus_generated: int = 0
    pdus_encoded: int = 0
    datagrams_attempted: int = 0
    datagrams_sent: int = 0
    bytes_sent: int = 0
    informs_sent: int = 0
    informs_acknowledged: int = 0
    inform_retries: int = 0
    inform_timeouts: int = 0
    late_or_mismatched_acks: int = 0
    request_ids: List[int] = Field(default_factory=list)
    acknowledged_request_ids: List[int] = Field(default_factory=list)
    receiver_observed_count: int = 0
    receiver_observed_request_ids: List[int] = Field(default_factory=list)
    evidence_stage: str = SnmpEvidenceStage.GENERATED.value
    stage_history: List[str] = Field(default_factory=list)
    rtt_ms_samples: List[float] = Field(default_factory=list)
    packet_cap_exceeded: bool = False
    encoding_failures: int = 0
    send_failures: int = 0
    elapsed_ms: float = 0.0
    errors: List[str] = Field(default_factory=list)
    error_types: List[str] = Field(default_factory=list)


class SnmpOidEntry(BaseModel):
    oid: str
    symbolic_name: Optional[str] = None
    asn1_type: str = "OctetString"
    value: Any = None
    fidelity: str = OidFidelityClass.STANDARD_VERIFIED.value
    source_mib: str = "SNMPv2-MIB"
    writable: bool = False
    base_oid: Optional[str] = None
    scenario_id: Optional[str] = None
    device_id: Optional[str] = None
    phase: Optional[str] = None

    def to_varbind(self) -> SnmpVarBind:
        return SnmpVarBind(
            oid=self.oid,
            asn1_type=self.asn1_type,
            value=self.value,
            mib_module=self.source_mib,
            object_name=self.symbolic_name,
            fidelity=self.fidelity,
        )


class SnmpPollingEvidence(BaseModel):
    bind_host: str = "127.0.0.1"
    bind_port: int = 1161
    scenario_id: str = "service_provider_cisco"
    phase: str = "BASELINE"
    seed: int = 42
    simulated_device_ids: List[str] = Field(default_factory=list)
    exposed_oid_count: int = 0
    mib_families: List[str] = Field(default_factory=list)
    requests_received: int = 0
    requests_decoded: int = 0
    get_requests: int = 0
    getnext_requests: int = 0
    getbulk_requests: int = 0
    set_requests_rejected: int = 0
    unsupported_pdu_rejected: int = 0
    malformed_requests: int = 0
    bad_community_requests: int = 0
    bad_version_requests: int = 0
    rate_limited_requests: int = 0
    responses_generated: int = 0
    responses_encoded: int = 0
    responses_sent: int = 0
    manager_observed_responses: int = 0
    evidence_stage: str = "IDLE"
    stage_history: List[str] = Field(default_factory=list)


class NormalizedSnmpEvent(BaseModel):
    """
    Canonical Gate 12D normalized SNMP collector/poller event for Splunk indexing.
    Correlation metadata (`netspout_run_id`, `netspout_scenario_id`, `netspout_phase`,
    `netspout_device_id`, `netspout_event_id`) is attached out-of-band in the collector
    normalization tier so the native SNMPv2c wire payload remains 100% standards-pure.
    """
    timestamp: float = Field(default_factory=time.time)
    sourcetype: str = "netspout:snmp:trap"  # "netspout:snmp:trap" | "netspout:snmp:poll"
    index: str = "idx_network_ops"
    source: str = "snmptrapd:udp:1162"
    host: str = "cisco-asr9k-pe1"
    netspout_run_id: str = ""
    netspout_scenario_id: str = "service_provider_cisco"
    netspout_phase: str = "BASELINE"
    netspout_device_id: str = "cisco-asr9k-pe1"
    netspout_event_id: str = ""
    snmp_version: str = "2c"
    snmp_pdu_type: str = "SNMPv2-Trap"      # "SNMPv2-Trap", "InformRequest", "GetRequest", "GetNextRequest", "GetBulkRequest"
    snmp_request_id: Optional[int] = None
    snmp_trap_oid: Optional[str] = None
    snmp_trap_name: Optional[str] = None
    snmp_oid: str = ""
    snmp_oid_name: str = ""
    snmp_value: str = ""
    snmp_numeric_value: Optional[float] = None
    snmp_value_type: str = "OctetString"
    snmp_source: str = "127.0.0.1"
    snmp_collector: str = "snmptrapd"       # "snmptrapd" | "net-snmp-cli"
    snmp_transport: str = "SNMPV2C_UDP"
    origin_evidence_stage: str = SnmpEvidenceStage.RECEIVER_OBSERVED.value
    current_evidence_stage: str = SnmpEvidenceStage.RECEIVER_OBSERVED.value
    evidence_stage: str = SnmpEvidenceStage.RECEIVER_OBSERVED.value
    sys_uptime: Optional[int] = None
    varbinds: Dict[str, Any] = Field(default_factory=dict)
    raw_collector_line: Optional[str] = None
    telemetry_semantics: str = "NATIVE TRANSPORT / MODELED DEVICE STATE"

    def to_event_dict(self) -> Dict[str, Any]:
        return {
            "netspout_run_id": self.netspout_run_id,
            "netspout_scenario_id": self.netspout_scenario_id,
            "netspout_phase": self.netspout_phase,
            "netspout_device_id": self.netspout_device_id,
            "netspout_event_id": self.netspout_event_id,
            "snmp_version": self.snmp_version,
            "snmp_pdu_type": self.snmp_pdu_type,
            "snmp_request_id": self.snmp_request_id,
            "snmp_trap_oid": self.snmp_trap_oid,
            "snmp_trap_name": self.snmp_trap_name,
            "snmp_oid": self.snmp_oid,
            "snmp_oid_name": self.snmp_oid_name,
            "snmp_value": self.snmp_value,
            "snmp_numeric_value": self.snmp_numeric_value,
            "snmp_value_type": self.snmp_value_type,
            "snmp_source": self.snmp_source,
            "snmp_collector": self.snmp_collector,
            "snmp_transport": self.snmp_transport,
            "origin_evidence_stage": self.origin_evidence_stage,
            "current_evidence_stage": self.current_evidence_stage,
            "evidence_stage": self.evidence_stage,
            "sys_uptime": self.sys_uptime,
            "varbinds": dict(self.varbinds),
            "raw_collector_line": self.raw_collector_line,
            "telemetry_semantics": self.telemetry_semantics,
        }

    def to_hec_payload(self) -> Dict[str, Any]:
        ev_dict = self.to_event_dict()
        # Preserve original collector observation state in origin_evidence_stage without
        # claiming that HEC dispatch equals SPLUNK_OBSERVED (SPLUNK_OBSERVED is established
        # strictly by fresh Splunk search verification).
        ev_dict["origin_evidence_stage"] = self.origin_evidence_stage
        ev_dict["hec_dispatch_stage"] = SnmpEvidenceStage.SPLUNK_DISPATCHED.value
        return {
            "time": self.timestamp,
            "host": self.host,
            "source": self.source,
            "sourcetype": self.sourcetype,
            "index": self.index,
            "event": ev_dict,
        }

    def to_log_entry(self) -> LogEntry:
        iso_ts = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(self.timestamp))
        status_val = "normal"
        action_val = "allowed"
        if self.netspout_phase in ("DEGRADE", "FAULT", "FAILOVER", "PROPAGATE"):
            status_val = "degraded" if self.netspout_phase in ("DEGRADE", "FAULT") else "mitigated"
            action_val = "alerted"
        elif self.netspout_phase in ("RECOVERY", "RECOVER", "VALIDATE"):
            status_val = "restored"
            action_val = "allowed"
        sig = self.snmp_trap_name or f"SNMP Poll {self.snmp_oid_name}={self.snmp_value}"
        kv_pairs = [
            f'netspout_run_id="{self.netspout_run_id}"',
            f'netspout_scenario_id="{self.netspout_scenario_id}"',
            f'netspout_phase="{self.netspout_phase}"',
            f'netspout_device_id="{self.netspout_device_id}"',
            f'netspout_event_id="{self.netspout_event_id}"',
            f'snmp_version="{self.snmp_version}"',
            f'snmp_pdu_type="{self.snmp_pdu_type}"',
            f'snmp_request_id="{self.snmp_request_id if self.snmp_request_id is not None else ""}"',
            f'snmp_trap_oid="{self.snmp_trap_oid or ""}"',
            f'snmp_trap_name="{self.snmp_trap_name or ""}"',
            f'snmp_oid="{self.snmp_oid}"',
            f'snmp_oid_name="{self.snmp_oid_name}"',
            f'snmp_value="{self.snmp_value}"',
            f'snmp_value_type="{self.snmp_value_type}"',
            f'snmp_source="{self.snmp_source}"',
            f'snmp_collector="{self.snmp_collector}"',
            f'snmp_transport="{self.snmp_transport}"',
            f'origin_evidence_stage="{self.origin_evidence_stage}"',
            f'current_evidence_stage="{self.current_evidence_stage}"',
            f'evidence_stage="{self.evidence_stage}"',
        ]
        return LogEntry(
            timestamp=iso_ts,
            device_id=self.netspout_device_id,
            src_ip=self.snmp_source,
            dest_ip="127.0.0.1",
            protocol="UDP",
            duration="1ms",
            action=action_val,
            signature=sig,
            status=status_val,
            raw_log=" ".join(kv_pairs),
            node_type="router",
            node_id=self.netspout_device_id,
            vendor="cisco_ios",
            sourcetype=self.sourcetype,
            netspout_run_id=self.netspout_run_id,
            netspout_scenario_id=self.netspout_scenario_id,
            netspout_phase=self.netspout_phase,
            netspout_device_id=self.netspout_device_id,
            netspout_event_id=self.netspout_event_id,
            netspout_ground_truth="true",
        )


class SnmpE2ERunScorecard(BaseModel):
    """
    Machine-readable Gate 12D/12F End-to-End Scorecard preserving strict separation across:
    GENERATED -> ENCODED -> SENT -> ACKNOWLEDGED -> RECEIVER_OBSERVED -> SPLUNK_DISPATCHED -> SPLUNK_OBSERVED -> VALIDATED
    """
    run_id: str
    scenario_id: str = "service_provider_cisco"
    device_id: str = "cisco-asr9k-pe1"
    seed: int = 42
    external_trap_receiver: str = "/usr/sbin/snmptrapd"
    external_poller: str = "net-snmp-cli (/usr/bin/snmpget, /usr/bin/snmpgetnext, /usr/bin/snmpwalk, /usr/bin/snmpbulkwalk)"
    target_index: str = "idx_network_ops"
    sourcetypes: List[str] = Field(default_factory=lambda: ["netspout:snmp:trap", "netspout:snmp:poll"])
    telemetry_semantics: str = "NATIVE TRANSPORT / MODELED DEVICE STATE"
    # Stage 1-3: Generation, Encoding, Transmission
    generated_notifications: int = 0
    encoded_notifications: int = 0
    sent_notifications: int = 0
    traps_generated: int = 0
    traps_sent: int = 0
    informs_generated: int = 0
    informs_sent: int = 0
    # Stage 4: Acknowledgement
    informs_acknowledged: int = 0
    # Stage 5: External Receiver / Poller Observation
    traps_receiver_observed: int = 0
    informs_receiver_observed: int = 0
    receiver_observed_notifications: int = 0
    polling_requests: int = 0
    polling_responses: int = 0
    get_requests: int = 0
    getnext_requests: int = 0
    getbulk_requests: int = 0
    walk_oids_observed: int = 0
    # Normalization
    normalized_records: int = 0
    normalized_trap_records: int = 0
    normalized_poll_records: int = 0
    duplicate_records_suppressed: int = 0
    malformed_records_dropped: int = 0
    # Stage 6: Splunk HEC Dispatch
    splunk_dispatched_records: int = 0
    splunk_dispatch_failures: int = 0
    # Stage 7: Fresh Splunk Search Observation
    splunk_observed_records: int = 0
    splunk_observed_trap_records: int = 0
    splunk_observed_poll_records: int = 0
    observation_completeness_pct: float = 0.0
    # Explicit UI/API boundary distinction
    snmp_receiver_observed_status: str = "NO"
    splunk_dispatched_status: str = "NO"
    splunk_observed_status: str = "NO"
    # Stage 8: Validation & Coherence
    phases_verified: List[str] = Field(default_factory=list)
    trap_poll_coherence: bool = False
    coherence_details: Dict[str, Any] = Field(default_factory=dict)
    validation_result: str = "NOT_RUN"
    validation_checks: List[Dict[str, Any]] = Field(default_factory=list)
    origin_evidence_stage: str = SnmpEvidenceStage.RECEIVER_OBSERVED.value
    current_evidence_stage: str = SnmpEvidenceStage.GENERATED.value
    evidence_stage: str = SnmpEvidenceStage.GENERATED.value
    stage_history: List[str] = Field(default_factory=list)
    stage_classification: Dict[str, str] = Field(default_factory=dict)
    investigation_queries: Dict[str, str] = Field(default_factory=dict)
    errors: List[str] = Field(default_factory=list)


def resolve_native_flow_config(
    explicit_config: Optional[Union[Dict[str, Any], NativeFlowConfig]] = None,
    env: Optional[Dict[str, str]] = None
) -> NativeFlowConfig:
    """
    Resolves NativeFlowConfig applying strict configuration precedence:
    Explicit Run Configuration > Environment Configuration > NetSpout Defaults.
    Never commits secrets or alters unconfigured fields.
    """
    if env is None:
        import os
        env = os.environ

    # Start with defaults
    cfg_data: Dict[str, Any] = {
        "protocol": "IPFIX",
        "collector_host": "127.0.0.1",
        "netflow_port": 2055,
        "ipfix_port": 4739,
        "observation_domain_id": 1,
        "exporter_identity": "10.0.0.1",
        "template_id": 256,
        "template_refresh_policy": "EVERY_BURST",
        "rate_limit_pps": 100,
        "packet_cap": 10000,
        "collector_enabled": True,
        "splunk_index": "idx_network_ops",
        "splunk_sourcetype": "netflow:collector",
        "allow_public_export": False,
        "goflow_metrics_port": 8080,
        "forwarder_status_port": 8082
    }

    # Environment variables overlay (NETSPOUT_*)
    env_mappings = {
        "NETSPOUT_FLOW_PROTOCOL": ("protocol", str),
        "NETSPOUT_COLLECTOR_HOST": ("collector_host", str),
        "NETSPOUT_NETFLOW_PORT": ("netflow_port", int),
        "NETSPOUT_IPFIX_PORT": ("ipfix_port", int),
        "NETSPOUT_OBSERVATION_DOMAIN_ID": ("observation_domain_id", int),
        "NETSPOUT_EXPORTER_IP": ("exporter_identity", str),
        "NETSPOUT_TEMPLATE_ID": ("template_id", int),
        "NETSPOUT_TEMPLATE_REFRESH_POLICY": ("template_refresh_policy", str),
        "NETSPOUT_RATE_LIMIT_PPS": ("rate_limit_pps", int),
        "NETSPOUT_PACKET_CAP": ("packet_cap", int),
        "NETSPOUT_COLLECTOR_ENABLED": ("collector_enabled", lambda v: v.lower() in ("1", "true", "yes")),
        "NETSPOUT_SPLUNK_INDEX": ("splunk_index", str),
        "NETSPOUT_SPLUNK_SOURCETYPE": ("splunk_sourcetype", str),
        "NETSPOUT_ALLOW_PUBLIC_EXPORT": ("allow_public_export", lambda v: v.lower() in ("1", "true", "yes")),
        "NETSPOUT_GOFLOW_METRICS_PORT": ("goflow_metrics_port", int),
        "NETSPOUT_FORWARDER_STATUS_PORT": ("forwarder_status_port", int),
    }

    for env_key, (cfg_key, parser) in env_mappings.items():
        if env_key in env:
            try:
                cfg_data[cfg_key] = parser(env[env_key])
            except Exception:
                pass

    # Explicit configuration overlay (takes highest precedence)
    if explicit_config:
        explicit_dict = explicit_config.dict() if hasattr(explicit_config, "dict") else dict(explicit_config)
        for k, v in explicit_dict.items():
            if v is not None:
                cfg_data[k] = v

    return NativeFlowConfig(**cfg_data)





