import type { TopologyState, ScenarioDefinition } from '../types/topology';

export const SCENARIOS: ScenarioDefinition[] = [
  {
    id: 'openconfig_mdt_streaming',
    name: 'Mode C: OpenConfig MDT Streaming & Telemetry Assurance',
    code: 'OC-001',
    ecosystem: 'both',
    description: 'Routers and switches stream real-time OpenConfig YANG metrics (interface counters, CPU/RAM, BGP peering) directly to cisco_mdt_metrics.',
    attackVector: 'Core Carrier Link Flap & Optical BER Degradation',
    defenseMechanism: 'Model-Driven Telemetry (MDT) detects carrier transitions and spikes within sub-second intervals for automated traffic re-routing.',
    sourcetypes: ['cisco:ios:mdt:metric', 'arista:telemetry:json', 'openconfig:gnmi:telemetry', 'cisco:ios:syslog']
  },

  // ==========================================
  // BASELINE SCENARIOS
  // ==========================================
  {
    id: 'normal_traffic',
    name: 'Normal Operations (HTTP Round-Robin)',
    code: 'BASE-01',
    ecosystem: 'both',
    description: 'Legitimate external clients make distributed HTTP requests passing through Firewall and Load Balancer to Web tier.',
    attackVector: 'None (Standard Production Traffic)',
    defenseMechanism: 'In-line stateful inspection allows HTTP traffic to flow evenly across Web nodes.',
    sourcetypes: ['cisco:asa', 'pan:traffic', 'f5:bigip:ltm', 'nginx:plus:kv', 'postgresql:audit']
  },
  {
    id: 'ddos_attack',
    name: 'Distributed Denial of Service (DDoS SYN Flood)',
    code: 'BASE-02',
    ecosystem: 'both',
    description: 'Malicious botnet IPs launch high-rate TCP SYN floods targeting internal infrastructure.',
    attackVector: 'Volumetric TCP SYN Flood targeting Port 80/443',
    defenseMechanism: 'Firewall intercepts with action=blocked. If Firewall is bypassed with a wire or deleted, logs switch to action=allowed status=breached!',
    sourcetypes: ['cisco:asa', 'pan:traffic', 'nginx:plus:kv']
  },
  {
    id: 'sql_injection',
    name: 'SQL Injection / Application Breach',
    code: 'BASE-03',
    ecosystem: 'both',
    description: 'Adversary injects malicious SQL exploitation payload through HTTP query parameters targeting Database backend.',
    attackVector: 'OWASP SQLi Vector (1\' OR \'1\'=\'1 -- UNION SELECT)',
    defenseMechanism: 'Perimeter WAF/Firewall drops attack. If bypassed, payload passes Web Server and triggers critical alert at Database layer!',
    sourcetypes: ['cisco:asa', 'nginx:plus:kv', 'postgresql:audit']
  },
  {
    id: 'lateral_movement',
    name: 'Ransomware / Lateral Spread (Port 445)',
    code: 'BASE-04',
    ecosystem: 'both',
    description: 'Malware attempts lateral propagation between internal servers across subnet boundaries using SMB Port 445.',
    attackVector: 'Lateral PsExec / Mimikatz SMB credential spread',
    defenseMechanism: 'Internal segmentation firewall blocks lateral spread. On flat unsegmented topology, malware breaches multiple interior nodes.',
    sourcetypes: ['cisco:ios:syslog', 'cisco:asa', 'postgresql:audit']
  },

  // ==========================================
  // MODE A: PURE CISCO ARCHITECTURE
  // ==========================================
  {
    id: 'cisco_campus_rogue',
    name: 'Mode A1: Campus Core L2/3 Disturbance & Rogue AP',
    code: 'CISCO-A1',
    ecosystem: 'pure_cisco',
    description: 'Unsanctioned Rogue AP connects to campus switch; Cisco ISE applies 802.1X quarantine while Catalyst core detects MAC flapping.',
    attackVector: 'Evil Twin / Rogue AP SSID injection causing L2 broadcast loop & MAC flapping',
    defenseMechanism: 'Catalyst Rogue Detection triggers ISE quarantine profile; switch isolates flapping access port.',
    sourcetypes: ['cisco:catalyst:security:events', 'cisco:catalyst:rogue:threat_details', 'cisco:ise:syslog', 'cisco:ios:syslog']
  },
  {
    id: 'cisco_sdwan_brownout',
    name: 'Mode A2: Enterprise WAN Circuit Brownout & App Route Failover',
    code: 'CISCO-A2',
    ecosystem: 'pure_cisco',
    description: 'MPLS transport experiences high latency and packet loss; Cisco SD-WAN vEdge triggers SLA violation and BGP failover to secondary LTE/Broadband.',
    attackVector: 'Underlay Carrier Brownout (185ms Latency, 12% Packet Loss)',
    defenseMechanism: 'SD-WAN BFD triggers dynamic SLA policy redirect; ThousandEyes synthetic probe validates application continuity.',
    sourcetypes: ['cisco:sdwan:linkhealth', 'cisco:sdwan:BGP-5-ADJCHANGE', 'cisco:thousandeyes:path-vis', 'cisco:thousandeyes:metric']
  },
  {
    id: 'cisco_aci_microburst',
    name: 'Mode A3: Data Center Fabric ACI Ingress Microburst Traffic',
    code: 'CISCO-A3',
    ecosystem: 'pure_cisco',
    description: 'Microburst traffic pattern saturates Nexus 9K leaf switch ingress ASIC buffers; ACI fabric health score drops and MDT telemetry flags queue incast.',
    attackVector: 'High-bandwidth Incast Traffic Burst saturating Switch ASIC Buffers',
    defenseMechanism: 'Nexus 9K buffer manager drops packets to protect spine; Cisco ACI health scoring reflects leaf congestion.',
    sourcetypes: ['cisco:dc:nexus9k:syslog', 'cisco:dc:aci:health', 'cisco:ios:mdt']
  },

  // ==========================================
  // MODE B: MIXED-VENDOR ENTERPRISE INFRASTRUCTURE
  // ==========================================
  {
    id: 'mixed_edge_breach',
    name: 'Mode B1: Distributed Edge Breach & Internal Probing',
    code: 'MIXED-B1',
    ecosystem: 'mixed_vendor',
    description: 'Attacker probes wireless network via Meraki AP through Catalyst Core toward internal servers; Palo Alto NGFW inspects traffic.',
    attackVector: 'Wireless Air Marshal Probe & Lateral Internal Port Scanning',
    defenseMechanism: 'Palo Alto NGFW drops threat inline (action=blocked). If NGFW is bypassed via direct wire or removed, breach penetrates internal servers (action=allowed status=breached)!',
    sourcetypes: ['meraki:assurancealerts', 'cisco:catalyst:security:events', 'pan:threat']
  },
  {
    id: 'mixed_sase_degradation',
    name: 'Mode B2: SASE Cloud Ingress App Degradation & Synthetic Validation',
    code: 'MIXED-B2',
    ecosystem: 'mixed_vendor',
    description: 'Zscaler/Cloudflare edge proxy experiences SSL inspection latency surge; Palo Alto SD-WAN queues sessions and ThousandEyes detects SaaS TTFB slowdown.',
    attackVector: 'Cloud SASE Proxy TLS Handshake Schedular Bottleneck',
    defenseMechanism: 'Palo Alto Prisma SD-WAN prioritizes critical ERP traffic; ThousandEyes synthetics detect and isolate edge cloud hop delay.',
    sourcetypes: ['zscaler:zia', 'pan:threat', 'cisco:thousandeyes:metric']
  },
  {
    id: 'mixed_backbone_optical',
    name: 'Mode B3: Multicast/MPLS Backbone Optical Carrier Shift',
    code: 'MIXED-B3',
    ecosystem: 'mixed_vendor',
    description: 'DWDM Loss-of-Signal alarm on Nokia SR-OS core triggers Juniper Junos RSVP-TE Fast Reroute (FRR) switchover; Arista IPFIX telemetry tracks rerouted flow.',
    attackVector: 'Physical Layer Fiber Cut / DWDM 100G Lambda Optical Loss of Signal',
    defenseMechanism: 'Nokia/Juniper MPLS Fast Reroute switches to sub-50ms facility bypass tunnel; Arista telemetry confirms alternate egress routing.',
    sourcetypes: ['nokia:sros:syslog', 'juniper:junos', 'arista:flow:ipfix', 'arista:telemetry:json']
  }
];

export const PRESET_SECURE: TopologyState = {
  zones: [
    { id: 'zone-sec-1', name: 'External Untrusted Zone', zone_type: 'edge_untrust', color: '#f43f5e', opacity: 0.12, x: 30, y: 160, width: 200, height: 230, description: 'External inbound client transit' },
    { id: 'zone-sec-2', name: 'DMZ Perimeter Inspection', zone_type: 'dmz', color: '#f59e0b', opacity: 0.12, x: 240, y: 160, width: 400, height: 230, description: 'Stateful firewall and load balancer tier' },
    { id: 'zone-sec-3', name: 'Internal Trust Tier', zone_type: 'internal_trust', color: '#10b981', opacity: 0.12, x: 660, y: 90, width: 440, height: 330, description: 'Segmented application and database cluster' }
  ],
  nodes: [
    { id: 'node-client', name: 'External Client', type: 'client_external', x: 60, y: 240, ip_address: '198.51.100.42', status: 'active', power_state: 'running', vendor: 'generic', hardware: { vcpu_count: 1, ram_mb: 2048, boot_time_sec: 2, cpu_utilization_pct: 12.0, memory_utilization_pct: 25.0, temperature_celsius: 38.0 } },
    { id: 'node-fw', name: 'Perimeter Firewall', type: 'firewall', x: 260, y: 240, ip_address: '198.51.100.1', status: 'active', power_state: 'running', vendor: 'cisco_asa', hardware: { vcpu_count: 4, ram_mb: 8192, boot_time_sec: 6, cpu_utilization_pct: 28.5, memory_utilization_pct: 44.0, temperature_celsius: 46.0 } },
    { id: 'node-lb', name: 'Core Load Balancer', type: 'load_balancer', x: 470, y: 240, ip_address: '10.0.1.5', status: 'active', power_state: 'running', vendor: 'f5', hardware: { vcpu_count: 4, ram_mb: 8192, boot_time_sec: 5, cpu_utilization_pct: 19.0, memory_utilization_pct: 35.0, temperature_celsius: 42.0 } },
    { id: 'node-web1', name: 'Web Server 01', type: 'web_server', x: 690, y: 150, ip_address: '10.0.1.10', status: 'active', power_state: 'running', vendor: 'nginx', hardware: { vcpu_count: 2, ram_mb: 4096, boot_time_sec: 3, cpu_utilization_pct: 22.0, memory_utilization_pct: 38.0, temperature_celsius: 40.0 } },
    { id: 'node-web2', name: 'Web Server 02', type: 'web_server', x: 690, y: 330, ip_address: '10.0.1.11', status: 'active', power_state: 'running', vendor: 'nginx', hardware: { vcpu_count: 2, ram_mb: 4096, boot_time_sec: 3, cpu_utilization_pct: 21.0, memory_utilization_pct: 37.0, temperature_celsius: 39.5 } },
    { id: 'node-db', name: 'Production Database', type: 'database', x: 920, y: 240, ip_address: '10.0.2.50', status: 'active', power_state: 'running', vendor: 'postgresql', hardware: { vcpu_count: 8, ram_mb: 16384, boot_time_sec: 8, cpu_utilization_pct: 35.0, memory_utilization_pct: 58.0, temperature_celsius: 48.0 } }
  ],
  edges: [
    { id: 'edge-1', source: 'node-client', target: 'node-fw', source_port: 'wan', target_port: 'outside' },
    { id: 'edge-2', source: 'node-fw', target: 'node-lb', source_port: 'inside', target_port: 'vip' },
    { id: 'edge-3', source: 'node-lb', target: 'node-web1', source_port: 'pool-1', target_port: 'eth0' },
    { id: 'edge-4', source: 'node-lb', target: 'node-web2', source_port: 'pool-2', target_port: 'eth0' },
    { id: 'edge-5', source: 'node-web1', target: 'node-db', source_port: 'db-link', target_port: 'pg-port' },
    { id: 'edge-6', source: 'node-web2', target: 'node-db', source_port: 'db-link', target_port: 'pg-port' }
  ]
};

export const PRESET_BYPASSED: TopologyState = {
  zones: [
    { id: 'zone-byp-1', name: 'External Untrusted Zone', zone_type: 'edge_untrust', color: '#f43f5e', opacity: 0.12, x: 30, y: 160, width: 200, height: 230, description: 'Direct uninspected packet injection' },
    { id: 'zone-byp-2', name: 'Bypassed DMZ (Inactive Inspection)', zone_type: 'dmz', color: '#f59e0b', opacity: 0.12, x: 240, y: 60, width: 400, height: 330, description: 'Firewall bypassed by anomalous direct link' },
    { id: 'zone-byp-3', name: 'Compromised Internal Tier', zone_type: 'internal_trust', color: '#10b981', opacity: 0.12, x: 660, y: 90, width: 440, height: 330, description: 'Exposed internal assets receiving unfiltered attacks' }
  ],
  nodes: [
    { id: 'node-client', name: 'External Client', type: 'client_external', x: 60, y: 240, ip_address: '198.51.100.42', status: 'active', power_state: 'running', vendor: 'generic' },
    { id: 'node-fw', name: 'Perimeter Firewall (Bypassed)', type: 'firewall', x: 260, y: 100, ip_address: '198.51.100.1', status: 'degraded', power_state: 'running', vendor: 'cisco_asa' },
    { id: 'node-lb', name: 'Core Load Balancer', type: 'load_balancer', x: 470, y: 240, ip_address: '10.0.1.5', status: 'active', power_state: 'running', vendor: 'f5' },
    { id: 'node-web1', name: 'Vulnerable Web Server 01', type: 'web_server', x: 690, y: 150, ip_address: '10.0.1.10', status: 'breached', power_state: 'running', vendor: 'nginx' },
    { id: 'node-web2', name: 'Web Server 02', type: 'web_server', x: 690, y: 330, ip_address: '10.0.1.11', status: 'active', power_state: 'running', vendor: 'nginx' },
    { id: 'node-db', name: 'Production Database', type: 'database', x: 920, y: 240, ip_address: '10.0.2.50', status: 'active', power_state: 'running', vendor: 'postgresql' }
  ],
  edges: [
    { id: 'edge-bypass', source: 'node-client', target: 'node-web1', source_port: 'direct', target_port: 'eth0', status: 'breached' },
    { id: 'edge-2', source: 'node-fw', target: 'node-lb', source_port: 'inside', target_port: 'vip' },
    { id: 'edge-3', source: 'node-lb', target: 'node-web1', source_port: 'pool-1', target_port: 'eth0' },
    { id: 'edge-4', source: 'node-lb', target: 'node-web2', source_port: 'pool-2', target_port: 'eth0' },
    { id: 'edge-5', source: 'node-web1', target: 'node-db', source_port: 'db-link', target_port: 'pg-port', status: 'breached' }
  ]
};

export const PRESET_LATERAL: TopologyState = {
  zones: [
    { id: 'zone-lat-1', name: 'External Adversary Node', zone_type: 'edge_untrust', color: '#f43f5e', opacity: 0.12, x: 30, y: 140, width: 210, height: 230, description: 'Initial foothold vector' },
    { id: 'zone-lat-2', name: 'Unsegmented Internal VLAN', zone_type: 'internal_trust', color: '#10b981', opacity: 0.12, x: 270, y: 80, width: 730, height: 300, description: 'Flat subnet allowing unrestricted SMB port 445 lateral spread' }
  ],
  nodes: [
    { id: 'node-client', name: 'Initial Attacker', type: 'client_external', x: 60, y: 220, ip_address: '203.0.113.99', status: 'active', power_state: 'running', vendor: 'generic' },
    { id: 'node-web1', name: 'Compromised Host 01', type: 'web_server', x: 300, y: 150, ip_address: '10.0.1.10', status: 'breached', power_state: 'running', vendor: 'nginx' },
    { id: 'node-web2', name: 'Lateral Target 02', type: 'web_server', x: 560, y: 150, ip_address: '10.0.1.11', status: 'breached', power_state: 'running', vendor: 'nginx' },
    { id: 'node-db', name: 'Crown Jewel Database', type: 'database', x: 820, y: 220, ip_address: '10.0.1.50', status: 'breached', power_state: 'running', vendor: 'postgresql' }
  ],
  edges: [
    { id: 'e-1', source: 'node-client', target: 'node-web1', status: 'breached' },
    { id: 'e-2', source: 'node-web1', target: 'node-web2', status: 'breached' },
    { id: 'e-3', source: 'node-web2', target: 'node-db', status: 'breached' }
  ]
};

export const PRESET_CISCO_CAMPUS: TopologyState = {
  zones: [
    { id: 'zone-camp-1', name: 'Campus Access / RF Boundary', zone_type: 'edge_untrust', color: '#f43f5e', opacity: 0.12, x: 40, y: 140, width: 210, height: 230, description: 'Wireless access perimeter & rogue AP ingress' },
    { id: 'zone-camp-2', name: 'Campus Access & Policy (Cisco ISE)', zone_type: 'dmz', color: '#0ea5e9', opacity: 0.12, x: 260, y: 60, width: 450, height: 350, description: '802.1X quarantine and Layer 2 access switching' },
    { id: 'zone-camp-3', name: 'Campus Core Backbone', zone_type: 'core_backbone', color: '#8b5cf6', opacity: 0.12, x: 740, y: 140, width: 230, height: 230, description: 'High-speed Catalyst 9600 enterprise aggregation' }
  ],
  nodes: [
    { id: 'node-rogue-ap', name: 'Rogue AP (Air Marshal Alert)', type: 'wireless_ap', x: 70, y: 220, ip_address: '10.10.20.99', status: 'breached', power_state: 'running', vendor: 'cisco_catalyst', sourcetype: 'cisco:catalyst:rogue:threat_details' },
    { id: 'node-cat9300', name: 'Catalyst-9300-Access', type: 'switch', x: 290, y: 220, ip_address: '10.10.20.1', status: 'active', power_state: 'running', vendor: 'cisco_catalyst', sourcetype: 'cisco:ios:syslog' },
    { id: 'node-cat9800', name: 'Catalyst-9800-WLC', type: 'switch', x: 530, y: 130, ip_address: '10.10.1.10', status: 'active', power_state: 'running', vendor: 'cisco_catalyst', sourcetype: 'cisco:catalyst:security:events' },
    { id: 'node-ise', name: 'Cisco-ISE-PSN01', type: 'firewall', x: 530, y: 310, ip_address: '10.10.1.25', status: 'active', power_state: 'running', vendor: 'cisco_ise', sourcetype: 'cisco:ise:syslog' },
    { id: 'node-campus-core', name: 'Catalyst-9600-Core', type: 'router', x: 780, y: 220, ip_address: '10.10.0.1', status: 'active', power_state: 'running', vendor: 'cisco_catalyst', sourcetype: 'cisco:ios:syslog' }
  ],
  edges: [
    { id: 'e-c1', source: 'node-rogue-ap', target: 'node-cat9300', source_port: 'radio0', target_port: 'Gi1/0/12', status: 'breached' },
    { id: 'e-c2', source: 'node-cat9300', target: 'node-cat9800', source_port: 'Te1/1/1', target_port: 'TenGig0/0/1' },
    { id: 'e-c3', source: 'node-cat9300', target: 'node-ise', source_port: 'Te1/1/2', target_port: 'eth0' },
    { id: 'e-c4', source: 'node-cat9800', target: 'node-campus-core', source_port: 'uplink', target_port: 'FortyGig1/0/1' },
    { id: 'e-c5', source: 'node-ise', target: 'node-campus-core', source_port: 'uplink', target_port: 'FortyGig1/0/2' }
  ]
};

export const PRESET_CISCO_SDWAN: TopologyState = {
  zones: [
    { id: 'zone-sdwan-1', name: 'Branch Office Site', zone_type: 'internal_trust', color: '#10b981', opacity: 0.12, x: 40, y: 140, width: 420, height: 230, description: 'Enterprise branch LAN and ThousandEyes probe' },
    { id: 'zone-sdwan-2', name: 'SD-WAN Underlay Carrier Grid', zone_type: 'edge_untrust', color: '#f59e0b', opacity: 0.12, x: 490, y: 60, width: 230, height: 350, description: 'MPLS primary and broadband failover transports' },
    { id: 'zone-sdwan-3', name: 'Data Center Headend', zone_type: 'dc_fabric', color: '#06b6d4', opacity: 0.12, x: 740, y: 140, width: 230, height: 230, description: 'vEdge hub aggregation and corporate core' }
  ],
  nodes: [
    { id: 'node-te-agent', name: 'ThousandEyes-Agent', type: 'client_external', x: 70, y: 220, ip_address: '172.16.1.50', status: 'active', power_state: 'running', vendor: 'cisco_thousandeyes', sourcetype: 'cisco:thousandeyes:metric' },
    { id: 'node-c8000', name: 'Catalyst-8300-Branch', type: 'router', x: 280, y: 220, ip_address: '172.16.1.1', status: 'active', power_state: 'running', vendor: 'cisco_sdwan', sourcetype: 'cisco:sdwan:linkhealth' },
    { id: 'node-mpls-circuit', name: 'MPLS Primary (Brownout Loss)', type: 'router', x: 530, y: 130, ip_address: '198.51.100.1', status: 'degraded', power_state: 'running', vendor: 'cisco_sdwan', sourcetype: 'cisco:sdwan:BGP-5-ADJCHANGE' },
    { id: 'node-lte-circuit', name: 'LTE / Biz-Internet (Failover)', type: 'router', x: 530, y: 310, ip_address: '203.0.113.1', status: 'active', power_state: 'running', vendor: 'cisco_sdwan', sourcetype: 'cisco:sdwan:linkhealth' },
    { id: 'node-dc-vedge', name: 'DC-vEdge-5000-Hub', type: 'router', x: 780, y: 220, ip_address: '10.254.1.1', status: 'active', power_state: 'running', vendor: 'cisco_sdwan', sourcetype: 'cisco:sdwan:linkhealth' }
  ],
  edges: [
    { id: 'e-sd1', source: 'node-te-agent', target: 'node-c8000', source_port: 'eth0', target_port: 'Gig0/0/0' },
    { id: 'e-sd2', source: 'node-c8000', target: 'node-mpls-circuit', source_port: 'Gig0/0/1', target_port: 'wan-mpls', status: 'congested' },
    { id: 'e-sd3', source: 'node-c8000', target: 'node-lte-circuit', source_port: 'Gig0/0/2', target_port: 'wan-lte' },
    { id: 'e-sd4', source: 'node-mpls-circuit', target: 'node-dc-vedge', source_port: 'wan', target_port: 'Gig1/0/1', status: 'congested' },
    { id: 'e-sd5', source: 'node-lte-circuit', target: 'node-dc-vedge', source_port: 'wan', target_port: 'Gig1/0/2' }
  ]
};

export const PRESET_CISCO_ACI: TopologyState = {
  zones: [
    { id: 'zone-aci-1', name: 'Compute Ingress Edge', zone_type: 'edge_untrust', color: '#f59e0b', opacity: 0.12, x: 40, y: 140, width: 200, height: 230, description: 'Microburst workload generator edge' },
    { id: 'zone-aci-2', name: 'ACI DC Spine-Leaf Fabric', zone_type: 'dc_fabric', color: '#06b6d4', opacity: 0.12, x: 260, y: 60, width: 700, height: 350, description: 'Nexus 9K spine-leaf Clos network topology' }
  ],
  nodes: [
    { id: 'node-incast-clients', name: 'Incast Compute Burst', type: 'client_external', x: 70, y: 220, ip_address: '10.255.10.5', status: 'active', power_state: 'running', vendor: 'generic' },
    { id: 'node-leaf-nexus', name: 'Nexus-9336-Leaf01', type: 'switch', x: 290, y: 220, ip_address: '10.255.0.11', status: 'degraded', power_state: 'running', vendor: 'cisco_nexus', sourcetype: 'cisco:dc:nexus9k:syslog' },
    { id: 'node-spine1', name: 'Nexus-9508-Spine01', type: 'switch', x: 530, y: 130, ip_address: '10.255.0.1', status: 'active', power_state: 'running', vendor: 'cisco_nexus', sourcetype: 'cisco:dc:aci:health' },
    { id: 'node-spine2', name: 'Nexus-9508-Spine02', type: 'switch', x: 530, y: 310, ip_address: '10.255.0.2', status: 'active', power_state: 'running', vendor: 'cisco_nexus', sourcetype: 'cisco:dc:aci:health' },
    { id: 'node-leaf-dst', name: 'Nexus-9336-Leaf02', type: 'switch', x: 780, y: 220, ip_address: '10.255.0.12', status: 'active', power_state: 'running', vendor: 'cisco_nexus', sourcetype: 'cisco:ios:mdt' }
  ],
  edges: [
    { id: 'e-aci1', source: 'node-incast-clients', target: 'node-leaf-nexus', source_port: '100G', target_port: 'Eth1/24', status: 'congested' },
    { id: 'e-aci2', source: 'node-leaf-nexus', target: 'node-spine1', source_port: 'Eth1/49', target_port: 'Eth1/1' },
    { id: 'e-aci3', source: 'node-leaf-nexus', target: 'node-spine2', source_port: 'Eth1/50', target_port: 'Eth1/1' },
    { id: 'e-aci4', source: 'node-spine1', target: 'node-leaf-dst', source_port: 'Eth1/2', target_port: 'Eth1/49' },
    { id: 'e-aci5', source: 'node-spine2', target: 'node-leaf-dst', source_port: 'Eth1/2', target_port: 'Eth1/50' }
  ]
};

export const PRESET_MIXED_EDGE: TopologyState = {
  zones: [
    { id: 'zone-mix-1', name: 'Edge Untrusted (Meraki RF)', zone_type: 'edge_untrust', color: '#f43f5e', opacity: 0.12, x: 40, y: 140, width: 210, height: 230, description: 'Air Marshal RF scan boundary' },
    { id: 'zone-mix-2', name: 'Perimeter Inspection (Palo Alto NGFW)', zone_type: 'dmz', color: '#f59e0b', opacity: 0.12, x: 260, y: 140, width: 450, height: 230, description: 'Catalyst L2/L3 transit and PA-440 App-ID inspection' },
    { id: 'zone-mix-3', name: 'Internal Trust Tier', zone_type: 'internal_trust', color: '#10b981', opacity: 0.12, x: 740, y: 140, width: 230, height: 230, description: 'Protected backend web application' }
  ],
  nodes: [
    { id: 'node-meraki-ap', name: 'Meraki-MR56-AP', type: 'wireless_ap', x: 70, y: 220, ip_address: '10.128.0.55', status: 'active', power_state: 'running', vendor: 'meraki', sourcetype: 'meraki:assurancealerts', hardware: { vcpu_count: 2, ram_mb: 2048, boot_time_sec: 4, cpu_utilization_pct: 18.0, memory_utilization_pct: 32.0, temperature_celsius: 41.0 } },
    { id: 'node-cat-switch', name: 'Catalyst-9300-Core', type: 'switch', x: 290, y: 220, ip_address: '10.128.0.1', status: 'active', power_state: 'running', vendor: 'cisco_catalyst', sourcetype: 'cisco:catalyst:security:events', hardware: { vcpu_count: 4, ram_mb: 8192, boot_time_sec: 5, cpu_utilization_pct: 22.0, memory_utilization_pct: 38.0, temperature_celsius: 43.0 } },
    { id: 'node-pan-fw', name: 'PaloAlto-PA440-NGFW', type: 'firewall', x: 530, y: 220, ip_address: '10.128.1.1', status: 'active', power_state: 'running', vendor: 'palo_alto', sourcetype: 'pan:threat', hardware: { vcpu_count: 4, ram_mb: 8192, boot_time_sec: 6, cpu_utilization_pct: 31.0, memory_utilization_pct: 49.0, temperature_celsius: 45.0 } },
    { id: 'node-internal-srv', name: 'Internal App Server', type: 'web_server', x: 780, y: 220, ip_address: '10.128.2.10', status: 'active', power_state: 'running', vendor: 'nginx', hardware: { vcpu_count: 2, ram_mb: 4096, boot_time_sec: 3, cpu_utilization_pct: 15.0, memory_utilization_pct: 30.0, temperature_celsius: 39.0 } }
  ],
  edges: [
    { id: 'e-b1', source: 'node-meraki-ap', target: 'node-cat-switch', source_port: 'eth0', target_port: 'Gi1/0/1' },
    { id: 'e-b2', source: 'node-cat-switch', target: 'node-pan-fw', source_port: 'Gi1/0/24', target_port: 'ethernet1/1' },
    { id: 'e-b3', source: 'node-pan-fw', target: 'node-internal-srv', source_port: 'ethernet1/2', target_port: 'eth0' }
  ]
};

export const PRESET_MIXED_SASE: TopologyState = {
  zones: [
    { id: 'zone-sase-1', name: 'Cloud SASE Edge (Zscaler ZIA)', zone_type: 'cloud_sase', color: '#38bdf8', opacity: 0.12, x: 40, y: 140, width: 210, height: 230, description: 'Cloud-native SWG and SSL inspection proxy' },
    { id: 'zone-sase-2', name: 'Prisma SD-WAN & DC Interconnect', zone_type: 'dmz', color: '#f59e0b', opacity: 0.12, x: 260, y: 140, width: 450, height: 230, description: 'Enterprise SD-WAN VPN and Nexus DC aggregation' },
    { id: 'zone-sase-3', name: 'Enterprise SaaS ERP Cloud', zone_type: 'internal_trust', color: '#10b981', opacity: 0.12, x: 740, y: 140, width: 230, height: 230, description: 'SaaS multi-tenant business applications' }
  ],
  nodes: [
    { id: 'node-zscaler', name: 'Zscaler-ZIA-CloudEdge', type: 'sase_proxy', x: 70, y: 220, ip_address: '165.225.10.1', status: 'degraded', power_state: 'running', vendor: 'zscaler', sourcetype: 'zscaler:zia' },
    { id: 'node-pan-sdwan', name: 'PaloAlto-Prisma-SDWAN', type: 'firewall', x: 290, y: 220, ip_address: '10.20.1.1', status: 'active', power_state: 'running', vendor: 'palo_alto', sourcetype: 'pan:threat' },
    { id: 'node-nexus-core', name: 'Cisco-Nexus-DC-Core', type: 'switch', x: 530, y: 220, ip_address: '10.20.1.254', status: 'active', power_state: 'running', vendor: 'cisco_nexus', sourcetype: 'cisco:dc:nexus9k:syslog' },
    { id: 'node-saas-erp', name: 'SaaS ERP Target', type: 'web_server', x: 780, y: 220, ip_address: '104.16.132.229', status: 'active', power_state: 'running', vendor: 'nginx' }
  ],
  edges: [
    { id: 'e-sase1', source: 'node-zscaler', target: 'node-pan-sdwan', source_port: 'gre-tunnel', target_port: 'tunnel.1', status: 'congested' },
    { id: 'e-sase2', source: 'node-pan-sdwan', target: 'node-nexus-core', source_port: 'ethernet1/1', target_port: 'Eth1/1' },
    { id: 'e-sase3', source: 'node-nexus-core', target: 'node-saas-erp', source_port: 'Eth1/2', target_port: 'eth0' }
  ]
};

export const PRESET_MIXED_OPTICAL: TopologyState = {
  zones: [
    { id: 'zone-opt-1', name: 'Carrier DWDM Optical Transport', zone_type: 'core_backbone', color: '#8b5cf6', opacity: 0.12, x: 40, y: 140, width: 270, height: 230, description: 'Nokia 7750 SR DWDM Loss of Signal alarm domain' },
    { id: 'zone-opt-2', name: 'MPLS RSVP-TE Backbone', zone_type: 'core_backbone', color: '#0ea5e9', opacity: 0.12, x: 340, y: 140, width: 290, height: 230, description: 'Juniper MX960 Fast Reroute sub-50ms failover' },
    { id: 'zone-opt-3', name: 'Cloud Leaf Fabric (Arista EOS)', zone_type: 'dc_fabric', color: '#10b981', opacity: 0.12, x: 660, y: 140, width: 260, height: 230, description: 'Arista IPFIX and flow telemetry validation tier' }
  ],
  nodes: [
    { id: 'node-nokia-core', name: 'Nokia-7750-SR12-Transport', type: 'optical_core', x: 70, y: 220, ip_address: '10.200.0.1', status: 'degraded', power_state: 'running', vendor: 'nokia_sros', sourcetype: 'nokia:sros:syslog' },
    { id: 'node-juniper-pe', name: 'Juniper-MX960-PE01', type: 'router', x: 380, y: 220, ip_address: '10.200.0.2', status: 'active', power_state: 'running', vendor: 'juniper_junos', sourcetype: 'juniper:junos' },
    { id: 'node-arista-leaf', name: 'Arista-7280R-Leaf01', type: 'switch', x: 700, y: 220, ip_address: '10.200.0.3', status: 'active', power_state: 'running', vendor: 'arista_eos', sourcetype: 'arista:flow:ipfix' }
  ],
  edges: [
    { id: 'e-opt1', source: 'node-nokia-core', target: 'node-juniper-pe', source_port: '1/1/c1', target_port: 'ge-0/0/0', status: 'congested' },
    { id: 'e-opt2', source: 'node-juniper-pe', target: 'node-arista-leaf', source_port: 'ge-0/0/1', target_port: 'Ethernet49/1' }
  ]
};


export const PRESET_OPENCONFIG_CORE: TopologyState = {
  zones: [
    { id: 'zone-oc-1', name: 'Carrier Core MDT Fabric (OpenConfig)', zone_type: 'core_backbone', color: '#8b5cf6', opacity: 0.12, x: 40, y: 140, width: 420, height: 250, description: 'OpenConfig YANG streaming routers emitting gNMI telemetry' },
    { id: 'zone-oc-2', name: 'Leaf / Spine Telemetry Tier', zone_type: 'dc_fabric', color: '#06b6d4', opacity: 0.12, x: 490, y: 140, width: 490, height: 250, description: 'Arista and Catalyst Spine/Leaf telemetry aggregation' }
  ],
  nodes: [
    { id: 'node-cisco8k', name: 'Cisco-8000-Core01', type: 'router', x: 70, y: 220, ip_address: '10.100.1.1', status: 'active', power_state: 'running', vendor: 'cisco_ios', sourcetype: 'cisco:ios:mdt:metric', hardware: { vcpu_count: 8, ram_mb: 16384, boot_time_sec: 5, cpu_utilization_pct: 24.5, memory_utilization_pct: 38.0, temperature_celsius: 42.0 } },
    { id: 'node-juniper-ptx', name: 'Juniper-PTX10K-PE01', type: 'router', x: 260, y: 220, ip_address: '10.100.1.2', status: 'active', power_state: 'running', vendor: 'juniper_junos', sourcetype: 'cisco:ios:mdt:metric', hardware: { vcpu_count: 8, ram_mb: 16384, boot_time_sec: 5, cpu_utilization_pct: 21.0, memory_utilization_pct: 35.0, temperature_celsius: 40.0 } },
    { id: 'node-arista-spine', name: 'Arista-7280R-Spine', type: 'switch', x: 520, y: 220, ip_address: '10.100.2.1', status: 'active', power_state: 'running', vendor: 'arista_eos', sourcetype: 'arista:telemetry:json', hardware: { vcpu_count: 4, ram_mb: 8192, boot_time_sec: 4, cpu_utilization_pct: 19.5, memory_utilization_pct: 32.0, temperature_celsius: 39.0 } },
    { id: 'node-cat-leaf', name: 'Catalyst-9600-Leaf', type: 'switch', x: 750, y: 220, ip_address: '10.100.2.2', status: 'active', power_state: 'running', vendor: 'cisco_catalyst', sourcetype: 'cisco:ios:mdt:metric', hardware: { vcpu_count: 4, ram_mb: 8192, boot_time_sec: 4, cpu_utilization_pct: 18.0, memory_utilization_pct: 29.0, temperature_celsius: 38.0 } }
  ],
  edges: [
    { id: 'e-oc1', source: 'node-cisco8k', target: 'node-juniper-ptx', source_port: 'HundredGigE0/0/0/0', target_port: 'et-0/0/0', status: 'up' },
    { id: 'e-oc2', source: 'node-juniper-ptx', target: 'node-arista-spine', source_port: 'et-0/0/1', target_port: 'Ethernet1/1', status: 'up' },
    { id: 'e-oc3', source: 'node-arista-spine', target: 'node-cat-leaf', source_port: 'Ethernet2/1', target_port: 'FortyGigE1/0/1', status: 'up' }
  ]
};
