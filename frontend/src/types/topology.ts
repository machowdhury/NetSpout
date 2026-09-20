export type EcosystemMode = 'pure_cisco' | 'mixed_vendor';

export type NodeType =
  | 'firewall'
  | 'router'
  | 'switch'
  | 'load_balancer'
  | 'subnet'
  | 'web_server'
  | 'database'
  | 'client_external'
  | 'wireless_ap'
  | 'sase_proxy'
  | 'optical_core'
  | 'storage_san'
  | 'storage_nas'
  | 'vpn_gateway'
  | 'cloud_transit'
  | 'iot_sensor'
  | 'wlc_controller';

export type ScenarioType =
  | 'normal_traffic'
  | 'ddos_attack'
  | 'sql_injection'
  | 'lateral_movement'
  | 'cisco_campus_rogue'
  | 'cisco_sdwan_brownout'
  | 'cisco_aci_microburst'
  | 'mixed_edge_breach'
  | 'mixed_sase_degradation'
  | 'mixed_backbone_optical'
  | 'openconfig_mdt_streaming'
  | 'arch_pan_iot_mesh'
  | 'arch_lan_campus_access'
  | 'arch_wlan_meraki_catalyst'
  | 'arch_can_multi_building'
  | 'arch_man_carrier_ring'
  | 'arch_wan_global_backbone'
  | 'arch_san_fibre_channel'
  | 'arch_nas_storage_cluster'
  | 'arch_vpn_remote_workforce'
  | 'arch_epn_isolated_intranet'
  | 'arch_gan_subsea_cloud'
  | 'pure_cisco_enterprise'
  | 'mixed_vendor_enterprise'
  | 'service_provider_cisco'
  | 'service_provider_mixed'
  | 'sdwan_connected_core'
  | 'wireless_connected_core_cisco'
  | 'wireless_connected_core_mixed';

export type SecurityZoneType =
  | 'dmz'
  | 'internal_trust'
  | 'core_backbone'
  | 'edge_untrust'
  | 'dc_fabric'
  | 'cloud_sase';

export interface ZoneAnnotation {
  id: string;
  name: string;
  zone_type: SecurityZoneType;
  color: string;
  opacity: number;
  x: number;
  y: number;
  width: number;
  height: number;
  description?: string;
}

export type NodePowerState = 'stopped' | 'starting' | 'running' | 'paused' | 'wiped';

export interface NetworkInterface {
  name: string;
  ip_address?: string;
  mac_address?: string;
  speed_mbps: number;
  duplex: string;
  mtu: number;
  oper_status: 'up' | 'down' | 'testing';
  admin_status: 'up' | 'down';
  vlan_id?: number;
  in_octets: number;
  out_octets: number;
  in_errors: number;
  out_errors: number;
}

export interface NodeHardware {
  vcpu_count: number;
  ram_mb: number;
  boot_time_sec: number;
  cpu_utilization_pct: number;
  memory_utilization_pct: number;
  temperature_celsius: number;
  interfaces?: NetworkInterface[];
  // 4 KPI Dimensions
  bandwidth_utilization_pct?: number;
  throughput_bps?: number;
  latency_ms?: number;
  jitter_ms?: number;
  packet_loss_pct?: number;
  error_rate?: number;
  uptime_seconds?: number;
  thermal_status?: string;
  psu_status?: string;
  ups_runtime_min?: number;
  routing_table_version?: number;
  bgp_prefix_count?: number;
  route_flaps?: number;
  config_checksum?: string;
  ipam_utilization_pct?: number;
  traffic_anomaly_score?: number;
  unauthorized_access_count?: number;
  firewall_drops?: number;
}

export interface TelemetryTransportConfig {
  hec_enabled: boolean;
  hec_url: string;
  hec_token: string;
  hec_index: string;
  hec_metric_index?: string;
  
  otel_enabled?: boolean;
  otel_endpoint?: string;
  otel_metrics_path?: string;
  otel_logs_path?: string;
  otel_service_name?: string;

  telegraf_enabled?: boolean;
  telegraf_endpoint?: string;
  telegraf_format?: 'influx' | 'json';

  syslog_enabled: boolean;
  syslog_host: string;
  syslog_port: number;
  syslog_protocol: 'udp' | 'tcp';
  syslog_facility: number;
  syslog_format: 'rfc5424' | 'rfc3164';
}

export interface Node {
  id: string;
  name: string;
  type: NodeType;
  x: number;
  y: number;
  ip_address: string;
  status: 'active' | 'degraded' | 'breached' | 'blocked' | 'stopped' | 'paused';
  power_state?: NodePowerState;
  vendor: string;
  sourcetype?: string;
  interface?: string;
  role?: string;
  subnet?: string;
  zone_id?: string;
  hardware?: NodeHardware;
  transport_config?: TelemetryTransportConfig;
  config?: Record<string, any>;
}

export interface Edge {
  id: string;
  source: string;
  target: string;
  source_port?: string;
  target_port?: string;
  status?: 'up' | 'down' | 'congested' | 'breached';
  link_type?: 'ethernet' | 'serial' | 'fiber' | 'trunk';
  bandwidth_mbps?: number;
  latency_ms?: number;
}

export interface TopologyState {
  nodes: Node[];
  edges: Edge[];
  zones?: ZoneAnnotation[];
  global_transport?: TelemetryTransportConfig;
}

export interface LogEntry {
  timestamp: string;
  device_id: string;
  src_ip: string;
  dest_ip: string;
  protocol: string;
  duration: string;
  action: 'blocked' | 'allowed' | 'alerted' | 'dropped';
  signature: string;
  status: 'normal' | 'blocked' | 'breached' | 'degraded';
  raw_log: string;
  node_type: string;
  node_id: string;
  vendor?: string;
  sourcetype?: string;
}

export interface ScenarioDefinition {
  id: ScenarioType;
  name: string;
  code: string;
  ecosystem: EcosystemMode | 'both';
  description: string;
  attackVector: string;
  defenseMechanism: string;
  sourcetypes: string[];
}

export type FaultScenarioType =
  | 'link_cut'
  | 'hardware_exhaustion'
  | 'bgp_route_flap'
  | 'ddos_syn_flood'
  | 'lateral_movement'
  | 'optical_ber_degradation'
  | 'snmp_trap_burst';

export interface FaultInjectionRequest {
  scenario_type: FaultScenarioType;
  target_edge_id?: string;
  target_node_id?: string;
  severity?: string;
  duration_sec?: number;
  cascade_enabled?: boolean;
}

export interface FaultEventRecord {
  id: string;
  scenario_type: FaultScenarioType;
  timestamp: number;
  target_id: string;
  description: string;
  cascades_count: number;
  status: 'active' | 'recovered';
  affected_nodes: string[];
  affected_edges: string[];
}

// =========================================================================
// SNMP & SC4SNMP Types
// =========================================================================
export interface SNMPMibDefinition {
  name: string;
  oid: string;
  mib_module: string;
  data_type: string;
  description: string;
  is_table: boolean;
  vendor: string;
}

export interface SNMPTrapEvent {
  timestamp: number;
  host: string;
  trap_oid: string;
  trap_name: string;
  enterprise: string;
  generic_trap?: number;
  specific_trap?: number;
  varbinds: Record<string, any>;
  severity: string;
  sourcetype: string;
  index: string;
}

export interface PipelineStats {
  hec_dispatched: number;
  otel_dispatched: number;
  telegraf_dispatched: number;
  syslog_dispatched: number;
  hec_errors: number;
  otel_errors: number;
  telegraf_errors: number;
  syslog_errors: number;
  last_error: string | null;
  last_active: number | null;
}
