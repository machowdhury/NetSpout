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
  | 'optical_core';

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
  | 'openconfig_mdt_streaming';

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
}

export interface TelemetryTransportConfig {
  hec_enabled: boolean;
  hec_url: string;
  hec_token: string;
  hec_index: string;
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
  | 'optical_ber_degradation';

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


