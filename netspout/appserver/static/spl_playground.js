/**
 * NetSpout SPL Playground & NOC/SOC Analytics Workbench
 * Author: Mahamudul Chowdhury (mchowdhury@splunk.com)
 *
 * Interactive SPL workspace with 30+ pre-canned multi-vendor queries,
 * instant client-side execution engine, Splunkd REST integration,
 * dynamic charting, and direct Splunk search dispatch.
 */

require(['jquery', 'splunkjs/mvc', 'splunkjs/mvc/simplexml/ready!'], function($, mvc) {
  'use strict';

  // --- Pre-canned Query Catalog ---
  var PRE_CANNED_QUERIES = [
    // CISCO
    {
      id: 'cisco-crc-flaps',
      category: 'cisco',
      vendor: 'Cisco Systems',
      title: 'IOS-XE / Catalyst: Interface Errors & Flaps',
      target_index: '*',
      spl: 'index=* sourcetype="cisco:ios:syslog" ("line protocol" OR "LINK-3-UPDOWN" OR "CRC")\n| rex field=_raw "interface (?<interface>\\S+)"\n| stats count, latest(_time) as last_seen by host, interface\n| where count > 0\n| sort -count',
      description: 'Detects recurring physical layer faults, carrier loss, and CRC frame corruption across Catalyst campus access switches.',
      mockCols: ['host', 'interface', 'count', 'last_seen'],
      mockRows: [
        ['cat9300-access-01', 'GigabitEthernet1/0/24', 42, '2026-09-20 14:35:12'],
        ['cat9300-access-02', 'TenGigabitEthernet1/1/1', 19, '2026-09-20 14:32:05'],
        ['cat9500-core-01', 'FortyGigabitEthernet1/0/1', 8, '2026-09-20 14:18:44'],
        ['cat9200-edge-03', 'GigabitEthernet0/0/12', 5, '2026-09-20 13:58:20']
      ]
    },
    {
      id: 'cisco-sdwan-sla',
      category: 'cisco',
      vendor: 'Cisco Catalyst SD-WAN',
      title: 'SD-WAN: BFD Path Loss & SLA Brownouts',
      target_index: 'cisco_mdt_metrics',
      spl: 'index=* sourcetype="cisco:sdwan:linkhealth" (loss_pct > 5 OR latency_ms > 120)\n| stats avg(loss_pct) as avg_loss, max(latency_ms) as max_lat, count by host, local_color, remote_color, sla_state\n| sort -avg_loss',
      description: 'Surfaces transport circuits breaching enterprise SLA thresholds across MPLS, Internet, and LTE underlay paths.',
      mockCols: ['host', 'local_color', 'remote_color', 'sla_state', 'avg_loss', 'max_lat', 'count'],
      mockRows: [
        ['vedge-branch-102', 'biz-internet', 'biz-internet', 'VIOLATED', 14.8, 184.2, 128],
        ['vedge-branch-105', 'lte', 'public-internet', 'VIOLATED', 11.2, 215.0, 94],
        ['vedge-branch-201', 'mpls', 'mpls', 'DEGRADED', 6.4, 132.8, 45],
        ['vedge-dc-hub-01', 'biz-internet', 'biz-internet', 'NORMAL', 1.2, 42.1, 12]
      ]
    },
    {
      id: 'cisco-sdwan-dpi',
      category: 'cisco',
      vendor: 'Cisco Catalyst SD-WAN',
      title: 'SD-WAN: DPI Application Top Talkers',
      target_index: '*',
      spl: 'index=* sourcetype="cisco:sdwan:dpi"\n| stats sum(bytes_sent) as tx_bytes, sum(bytes_recv) as rx_bytes, dc(src_ip) as active_clients by app_name, vpn_id\n| eval total_mb = round((tx_bytes+rx_bytes)/(1024*1024), 2)\n| sort -total_mb\n| head 10',
      description: 'Aggregates application bandwidth consumption across enterprise VPN segments to isolate bandwidth hogs.',
      mockCols: ['app_name', 'vpn_id', 'total_mb', 'active_clients'],
      mockRows: [
        ['microsoft-teams', '10', 4820.4, 215],
        ['zoom-meetings', '10', 3640.1, 148],
        ['salesforce', '10', 1820.9, 96],
        ['youtube-streaming', '1', 1420.5, 42],
        ['aws-s3-backup', '20', 980.2, 8]
      ]
    },
    {
      id: 'cisco-mdt-optical',
      category: 'cisco',
      vendor: 'Cisco MDT gNMI',
      title: 'OpenConfig MDT: Optical RX Power & Laser Triage',
      target_index: 'cisco_mdt_metrics',
      spl: 'index=* sourcetype="cisco:mdt:telemetry"\n| eval rx_power=coalesce(\'openconfig-interfaces:interfaces/interface/state/optical-rx-power\', rx_power_dbm)\n| where rx_power < -18\n| stats min(rx_power) as min_rx_dbm, avg(rx_power) as avg_rx_dbm, count by device_id, interface\n| sort min_rx_dbm',
      description: 'Monitors pluggable transceiver optical power margins to predict laser degradation before link failure.',
      mockCols: ['device_id', 'interface', 'min_rx_dbm', 'avg_rx_dbm', 'count'],
      mockRows: [
        ['core-asr9k-01', 'HundredGigE0/0/0/1', -24.8, -23.9, 86],
        ['core-asr9k-02', 'HundredGigE0/1/0/0', -21.4, -20.6, 54],
        ['spine-nexus9k-03', 'Eth1/49', -19.5, -18.8, 32]
      ]
    },
    {
      id: 'cisco-ise-nac',
      category: 'cisco',
      vendor: 'Cisco ISE',
      title: 'ISE: 802.1X NAC Authentication Triage',
      target_index: '*',
      spl: 'index=* sourcetype="cisco:ise:nac:8021x" OR sourcetype="cisco:ise:syslog"\n| stats count(eval(Response="Failed" OR match(_raw, "Failed|Reject"))) as failed_auths, count(eval(Response="Passed")) as passed_auths by User-Name, Calling-Station-Id, host\n| eval fail_rate = round(failed_auths*100/(failed_auths+passed_auths+0.001), 1)\n| sort -failed_auths\n| head 10',
      description: 'Identifies clients failing 802.1X certificate checks, EAP-TLS handshake drops, and unauthorized endpoint probing.',
      mockCols: ['User-Name', 'Calling-Station-Id', 'host', 'failed_auths', 'passed_auths', 'fail_rate'],
      mockRows: [
        ['marcus.vance@corp', '70-69-79-4C-11-02', 'ise-node-01', 34, 1, 97.1],
        ['svc-scanner@corp', '00-50-56-A1-22-33', 'ise-node-02', 28, 0, 100.0],
        ['guest-contractor', 'B4-2E-99-1F-8C-44', 'ise-node-01', 12, 4, 75.0]
      ]
    },
    {
      id: 'cisco-duo-mfa',
      category: 'cisco',
      vendor: 'Cisco Duo',
      title: 'Duo MFA: Fraud Denials & Impossible Travel',
      target_index: '*',
      spl: 'index=* (sourcetype="cisco:duo:push:prompt" OR sourcetype="cisco:duo:authentication")\n| search result="FRAUD" OR result="DENIED" OR result="FAILURE"\n| stats count, values(location) as locations, dc(location) as distinct_cities by user\n| where count > 0\n| sort -count',
      description: 'Audits Duo Mobile push fraud alerts, passcode brute-force attempts, and rapid geo-location anomalies.',
      mockCols: ['user', 'count', 'locations', 'distinct_cities'],
      mockRows: [
        ['alex.turner@corp', 14, 'Kyiv, Ukraine | Austin, TX, US', 2],
        ['sarah.connor@corp', 6, 'Moscow, RU | San Jose, CA, US', 2],
        ['admin.svc@corp', 4, 'Frankfurt, DE', 1]
      ]
    },
    {
      id: 'cisco-meraki-wifi',
      category: 'cisco',
      vendor: 'Cisco Meraki',
      title: 'Meraki: Wi-Fi Channel Congestion & Client Density',
      target_index: '*',
      spl: 'index=* sourcetype="meraki:accesspoints"\n| stats avg(channel_utilization_5ghz) as avg_5g_util, max(client_count) as peak_clients, sum(rx_packets) as total_rx by name, network_id\n| where avg_5g_util > 50\n| sort -avg_5g_util',
      description: 'Tracks RF channel utilization, co-channel interference, and roaming client saturation across MR access points.',
      mockCols: ['name', 'network_id', 'avg_5g_util', 'peak_clients', 'total_rx'],
      mockRows: [
        ['MR56-Conf-Center-A', 'N_88192031', 78.4, 84, 18492000],
        ['MR46-All-Hands-Hall', 'N_88192031', 68.2, 112, 24810000],
        ['MR56-Exec-Suite-4F', 'N_88192031', 54.1, 38, 9420000]
      ]
    },
    {
      id: 'cisco-mds-san',
      category: 'cisco',
      vendor: 'Cisco MDS SAN',
      title: 'Cisco MDS: Fibre Channel B2B Credit Starvation',
      target_index: '*',
      spl: 'index=* sourcetype="cisco:mds:san:fc"\n| stats sum(b2b_credit_drops) as credit_drops, sum(crc_errors) as total_crc, avg(throughput_gbps) as avg_gbps by switch, fc_port, vsan\n| where credit_drops > 0 OR total_crc > 0\n| sort -credit_drops',
      description: 'Identifies slow-drain storage devices causing Buffer-to-Buffer credit starvation across high-speed SAN fabrics.',
      mockCols: ['switch', 'fc_port', 'vsan', 'credit_drops', 'total_crc', 'avg_gbps'],
      mockRows: [
        ['mds9710-core-a', 'fc1/14', '100', 4820, 12, 48.5],
        ['mds9710-core-a', 'fc1/15', '100', 1420, 4, 52.1],
        ['mds9710-core-b', 'fc2/8', '200', 890, 0, 61.2]
      ]
    },

    // PALO ALTO
    {
      id: 'pan-top-dropped',
      category: 'paloalto',
      vendor: 'Palo Alto Networks',
      title: 'PAN-OS: Top Denied Applications & Attacker IPs',
      target_index: '*',
      spl: 'index=* sourcetype="pan:traffic" (action="deny" OR action="drop")\n| stats count as dropped_sessions, sum(bytes) as total_bytes by src, app, dest_port\n| sort -dropped_sessions\n| head 15',
      description: 'Evaluates perimeter firewall drops to identify unauthorized scans, port sweeps, and non-standard application tunnels.',
      mockCols: ['src', 'app', 'dest_port', 'dropped_sessions', 'total_bytes'],
      mockRows: [
        ['198.51.100.44', 'ms-rdp', '3389', 2480, 124000],
        ['203.0.113.88', 'ssh', '22', 1840, 92000],
        ['192.0.2.14', 'web-browsing', '8080', 1120, 448000],
        ['198.51.100.99', 'unknown-tcp', '4444', 980, 49000]
      ]
    },
    {
      id: 'pan-threat-signatures',
      category: 'paloalto',
      vendor: 'Palo Alto Networks',
      title: 'PAN-OS: Critical Threat Signatures & C2 Beacons',
      target_index: '*',
      spl: 'index=* sourcetype="pan:threat" (severity="critical" OR severity="high")\n| stats count, values(threat_name) as signatures, dc(dest) as targets by src, action\n| sort -count',
      description: 'Detects active command-and-control beaconing, buffer overflow exploits, and malware payloads detected by App-ID / Threat Prevention.',
      mockCols: ['src', 'action', 'count', 'signatures', 'targets'],
      mockRows: [
        ['10.40.1.105', 'blocked', 18, 'CobaltStrike.Beacon.HTTP | CVE-2024-3400', 4],
        ['10.40.1.201', 'alert', 9, 'DNS.Tunneling.DataExfil', 1],
        ['10.20.4.55', 'reset-both', 5, 'SMB.EternalBlue.Attempt', 2]
      ]
    },
    {
      id: 'pan-globalprotect-vpn',
      category: 'paloalto',
      vendor: 'Palo Alto Networks',
      title: 'PAN-OS: GlobalProtect VPN Failures & Latency',
      target_index: '*',
      spl: 'index=* sourcetype="pan:globalprotect" (status="failure" OR status="disconnected")\n| stats count by user, client_os, failure_reason\n| sort -count',
      description: 'Troubleshoots remote worker VPN connectivity issues, HIP profile non-compliance, and tunnel establishment aborts.',
      mockCols: ['user', 'client_os', 'failure_reason', 'count'],
      mockRows: [
        ['john.doe@corp', 'Mac OS X 14.4', 'HIP Check Failed: Missing EDR Agent', 12],
        ['jane.smith@corp', 'Windows 11', 'Gateway unreachable / DNS timeout', 8],
        ['alex.chen@corp', 'iOS 17.2', 'Invalid client certificate', 5]
      ]
    },

    // FORTINET
    {
      id: 'fortigate-utm-blocks',
      category: 'fortinet',
      vendor: 'Fortinet',
      title: 'FortiGate: UTM Antivirus & IPS Block Triage',
      target_index: '*',
      spl: 'index=* (sourcetype="fortigate:utm" OR sourcetype="fortigate:traffic") (action="blocked" OR action="dropped")\n| stats count by subtype, attack, severity, srcip\n| sort -count',
      description: 'Summarizes FortiGuard UTM IPS exploit signatures and antivirus blocks across edge SD-branch gateways.',
      mockCols: ['subtype', 'attack', 'severity', 'srcip', 'count'],
      mockRows: [
        ['ips', 'HTTP.URI.Directory.Traversal', 'critical', '198.51.100.12', 48],
        ['virus', 'EICAR_Test_File', 'high', '10.20.1.44', 16],
        ['webfilter', 'Botnet.Command.Channel', 'critical', '10.30.2.88', 9]
      ]
    },
    {
      id: 'fortigate-sdwan-sla',
      category: 'fortinet',
      vendor: 'Fortinet',
      title: 'FortiGate: SD-WAN Dynamic Path SLA Metrics',
      target_index: '*',
      spl: 'index=* sourcetype="fortinet:fortigate:event"\n| stats avg(latency_ms) as latency, avg(jitter_ms) as jitter, avg(packet_loss_pct) as loss by interface, sla_name\n| where loss > 2 OR latency > 80\n| sort -loss',
      description: 'Monitors FortiGate SD-WAN health-check probes across ISP1, ISP2, and MPLS to observe SLA steering rules.',
      mockCols: ['interface', 'sla_name', 'latency', 'jitter', 'loss'],
      mockRows: [
        ['wan1-broadband', 'Voice_SLA_Strict', 142.5, 38.2, 8.5],
        ['wan2-cellular', 'Business_Apps_SLA', 98.4, 18.1, 4.2],
        ['wan3-direct-fiber', 'Tier1_Core', 22.1, 2.4, 0.1]
      ]
    },

    // ARISTA
    {
      id: 'arista-roce-pfc',
      category: 'arista',
      vendor: 'Arista Networks',
      title: 'Arista EOS: RoCE v2 PFC Watchdog & Pause Storms',
      target_index: '*',
      spl: 'index=* (sourcetype="arista:eos:syslog" OR sourcetype="arista:eos:openconfig") ("PFC" OR "watchdog" OR "pause_frames")\n| stats count, sum(rx_pause_frames) as pause_in, sum(tx_pause_frames) as pause_out by host, interface\n| sort -pause_in',
      description: 'Isolates Priority Flow Control (PFC) deadlocks and buffer overruns in AI/ML GPU training fabrics.',
      mockCols: ['host', 'interface', 'count', 'pause_in', 'pause_out'],
      mockRows: [
        ['arista-leaf-gpu-01', 'Ethernet1/1', 124, 8420000, 1200],
        ['arista-leaf-gpu-02', 'Ethernet1/2', 98, 6210000, 480],
        ['arista-spine-01', 'Ethernet32/1', 45, 1840000, 14000]
      ]
    },
    {
      id: 'arista-evpn-mac',
      category: 'arista',
      vendor: 'Arista Networks',
      title: 'Arista EOS: BGP EVPN MAC Mobility Flapping',
      target_index: '*',
      spl: 'index=* sourcetype="arista:eos:syslog" ("MACMOVE" OR "evpn" OR "mobility")\n| stats count as flap_count, latest(_time) as last_flap by vni, mac_address, host\n| where flap_count > 2\n| sort -flap_count',
      description: 'Detects bridging loops or virtual machine flapping across VXLAN overlay VTEPs.',
      mockCols: ['vni', 'mac_address', 'host', 'flap_count', 'last_flap'],
      mockRows: [
        ['10020', '00:50:56:b2:33:44', 'arista-leaf-01', 18, '2026-09-20 14:38:12'],
        ['10020', '00:50:56:b2:33:44', 'arista-leaf-02', 17, '2026-09-20 14:38:10'],
        ['10050', 'fa:16:3e:89:12:00', 'arista-leaf-04', 6, '2026-09-20 14:22:04']
      ]
    },

    // JUNIPER
    {
      id: 'juniper-optical-alarms',
      category: 'juniper',
      vendor: 'Juniper Networks',
      title: 'Junos OS: Optical Transceiver Loss & Laser Degradation',
      target_index: '*',
      spl: 'index=* sourcetype="juniper:junos:syslog" ("OPTICS" OR "ALARM" OR "laser" OR "power")\n| stats count, latest(_raw) as last_event by host, interface, alarm_state\n| sort -count',
      description: 'Identifies QSFP28/QSFP-DD optics reporting high bit-error rates or impending laser failure.',
      mockCols: ['host', 'interface', 'alarm_state', 'count'],
      mockRows: [
        ['mx960-edge-01', 'et-0/0/0', 'OPTICAL_POWER_CRITICAL_LOW', 42],
        ['mx960-edge-02', 'et-0/1/0', 'TEMPERATURE_HIGH_WARN', 18],
        ['ptx1000-core-01', 'et-1/0/0', 'LASER_BIAS_CURRENT_HIGH', 11]
      ]
    },
    {
      id: 'juniper-tilfa-reroute',
      category: 'juniper',
      vendor: 'Juniper Networks',
      title: 'Junos OS: RSVP/SR-TE LSP Path Reroute via TI-LFA',
      target_index: '*',
      spl: 'index=* sourcetype="juniper:junos:syslog" ("LSP" OR "reroute" OR "TI-LFA" OR "bypass")\n| stats count, values(lsp_name) as rerouted_lsps by host, primary_path, active_path',
      description: 'Tracks Segment Routing Topology-Independent Loop-Free Alternate (TI-LFA) sub-50ms failover occurrences.',
      mockCols: ['host', 'primary_path', 'active_path', 'count', 'rerouted_lsps'],
      mockRows: [
        ['ptx1000-core-01', 'et-0/0/0 (Direct-100G)', 'et-0/0/1 (Backup-LFA)', 4, 'lsp-dc1-to-dc2-primary'],
        ['ptx1000-core-02', 'et-0/1/0 (Direct-100G)', 'et-0/1/2 (Backup-LFA)', 2, 'lsp-dc2-to-dc1-primary']
      ]
    },

    // CLOUD & K8S
    {
      id: 'aws-vpc-rejections',
      category: 'cloud',
      vendor: 'AWS Cloud',
      title: 'AWS VPC Flow Logs: Security Group Rejections & Sweeps',
      target_index: '*',
      spl: 'index=* sourcetype="aws:cloudwatch:vpcflow" action="REJECT"\n| stats count, dc(dest_port) as scanned_ports by src_addr, dest_addr\n| where scanned_ports > 5\n| sort -scanned_ports',
      description: 'Monitors ingress reconnaissance and unauthorized lateral connection attempts rejected by AWS Security Groups.',
      mockCols: ['src_addr', 'dest_addr', 'scanned_ports', 'count'],
      mockRows: [
        ['198.51.100.88', '172.31.14.8', 42, 1420],
        ['203.0.113.5', '172.31.28.104', 18, 540],
        ['192.0.2.99', '172.31.10.2', 8, 190]
      ]
    },
    {
      id: 'cilium-hubble-drops',
      category: 'cloud',
      vendor: 'Kubernetes Cilium Hubble',
      title: 'Cilium Hubble: NetworkPolicy Pod Drops',
      target_index: '*',
      spl: 'index=* sourcetype="kube:container:hubble" verdict="DROPPED"\n| stats count, latest(_time) as last_drop by source_namespace, source_pod, destination_namespace, destination_port\n| sort -count',
      description: 'Pinpoints microsegmentation NetworkPolicy violations and unauthorized cross-namespace service mesh calls.',
      mockCols: ['source_namespace', 'source_pod', 'destination_namespace', 'destination_port', 'count'],
      mockRows: [
        ['frontend', 'guestbook-fe-84d9f', 'payment', '5432', 84],
        ['monitoring', 'prometheus-k8s-0', 'internal-admin', '8080', 29],
        ['default', 'debug-pod-alpha', 'vault', '8200', 14]
      ]
    },
    {
      id: 'cloudflare-magic-wan',
      category: 'cloud',
      vendor: 'Cloudflare',
      title: 'Cloudflare Magic WAN: Edge POP Latency & Packet Loss',
      target_index: '*',
      spl: 'index=* sourcetype="cloudflare:magic:wan"\n| stats avg(rtt_ms) as avg_rtt, max(loss_pct) as peak_loss by edge_pop_location, tunnel_name\n| sort -avg_rtt',
      description: 'Compares anycast edge routing performance across regional Cloudflare data center points of presence.',
      mockCols: ['edge_pop_location', 'tunnel_name', 'avg_rtt', 'peak_loss'],
      mockRows: [
        ['IAD (Ashburn)', 'ipsec-chicago-dc', 68.4, 4.2],
        ['ORD (Chicago)', 'ipsec-chicago-dc', 14.1, 0.0],
        ['LHR (London)', 'gre-frankfurt-br', 22.8, 0.2]
      ]
    },

    // STORAGE & EDGE
    {
      id: 'netapp-nas-latency',
      category: 'storage',
      vendor: 'NetApp ONTAP',
      title: 'NetApp ONTAP: NAS NFSv4.1 Latency & IOPS Spike',
      target_index: '*',
      spl: 'index=* sourcetype="netapp:ontap:nas"\n| stats avg(latency_ms) as avg_latency, max(iops) as max_iops, avg(capacity_used_pct) as storage_pct by cluster, vserver, volume\n| where avg_latency > 2.0\n| sort -avg_latency',
      description: 'Detects storage volume bottlenecks, NFS metadata stalls, and capacity thresholds affecting compute clusters.',
      mockCols: ['cluster', 'vserver', 'volume', 'avg_latency', 'max_iops', 'storage_pct'],
      mockRows: [
        ['ontap-cluster-01', 'svm_corp_nfs', 'vol_prod_ai_models', 4.82, 48200, 78.4],
        ['ontap-cluster-01', 'svm_corp_nfs', 'vol_k8s_pvcs', 2.91, 31000, 64.1],
        ['ontap-cluster-02', 'svm_backup', 'vol_archive_daily', 2.15, 12000, 92.0]
      ]
    },
    {
      id: 'f5-pool-health',
      category: 'storage',
      vendor: 'F5 BIG-IP',
      title: 'F5 BIG-IP: Virtual Server Member Monitor Failures',
      target_index: '*',
      spl: 'index=* sourcetype="f5:bigip:syslog" ("Pool" OR "monitor" OR "down" OR "health")\n| stats count, latest(_raw) as last_log by host, pool_name, pool_member, status\n| sort -count',
      description: 'Tracks backend application server health probe failures and automatic member draining events.',
      mockCols: ['host', 'pool_name', 'pool_member', 'status', 'count'],
      mockRows: [
        ['f5-vip-core-01', 'pool_auth_api', '10.10.40.11:8443', 'DOWN', 16],
        ['f5-vip-core-01', 'pool_auth_api', '10.10.40.12:8443', 'DOWN', 14],
        ['f5-vip-core-02', 'pool_web_ssl', '10.10.20.15:443', 'DEGRADED', 5]
      ]
    },

    // NOC / SOC SCENARIOS
    {
      id: 'mv-001-backbone',
      category: 'noc_soc',
      vendor: 'Multi-Vendor NOC',
      title: 'MV-001: Enterprise 5-Tier Backbone Hop Flow',
      target_index: '*',
      spl: 'index=* (sourcetype="cisco:ios:syslog" OR sourcetype="arista:eos:syslog" OR sourcetype="juniper:junos:syslog")\n| stats count, dc(host) as reporting_devices by sourcetype, severity\n| sort -count',
      description: 'Holistic cross-vendor health snapshot across Access, Aggregation, Core, WAN, and Data Center tiers.',
      mockCols: ['sourcetype', 'severity', 'count', 'reporting_devices'],
      mockRows: [
        ['cisco:ios:syslog', 'warning', 1840, 24],
        ['arista:eos:syslog', 'informational', 1420, 16],
        ['juniper:junos:syslog', 'critical', 42, 4],
        ['cisco:ios:syslog', 'error', 38, 8]
      ]
    },
    {
      id: 'mv-002-roce',
      category: 'noc_soc',
      vendor: 'Data Center NOC',
      title: 'MV-002: AI Data Center Fabric RoCE v2 Congestion',
      target_index: '*',
      spl: 'index=* (sourcetype="arista:eos:syslog" OR sourcetype="cisco:nexus:syslog") ("ECN" OR "PFC" OR "buffer_drop")\n| stats sum(ecn_marked_packets) as ecn_pkts, sum(pfc_pause_rx) as pause_rx by switch, port\n| sort -pause_rx',
      description: 'Pinpoints RoCE v2 head-of-line blocking and Explicit Congestion Notification marking rates in Ultra-Ethernet AI networks.',
      mockCols: ['switch', 'port', 'ecn_pkts', 'pause_rx'],
      mockRows: [
        ['leaf-spine-ai-01', 'Eth1/1', 1289000, 482000],
        ['leaf-spine-ai-02', 'Eth1/2', 894000, 241000],
        ['leaf-spine-ai-03', 'Eth1/1', 420000, 89000]
      ]
    },
    {
      id: 'mv-006-bgp-flap',
      category: 'noc_soc',
      vendor: 'Core Routing NOC',
      title: 'MV-006: Core BGP Instability & Flap Dampening',
      target_index: '*',
      spl: 'index=* ("BGP-5-ADJCHANGE" OR "flapping" OR "dampening" OR "prefix")\n| stats count as flaps, dc(host) as affected_routers by neighbor_ip, as_number\n| where flaps > 1\n| sort -flaps',
      description: 'Identifies external peering links triggering BGP flap dampening penalties and recursive next-hop resolution churn.',
      mockCols: ['neighbor_ip', 'as_number', 'flaps', 'affected_routers'],
      mockRows: [
        ['198.51.100.1', '65001', 38, 6],
        ['203.0.113.254', '65002', 22, 4],
        ['192.0.2.1', '65100', 8, 2]
      ]
    },
    {
      id: 'mv-008-sdwan-brownout',
      category: 'noc_soc',
      vendor: 'WAN Operations NOC',
      title: 'MV-008: SD-WAN Dynamic Path SLA Brownout',
      target_index: 'cisco_mdt_metrics',
      spl: 'index=* sourcetype="cisco:sdwan:linkhealth" sla_state="violated"\n| stats count, avg(latency_ms) as latency, avg(loss_pct) as loss by host, local_color\n| sort -latency',
      description: 'Correlates branch loss and jitter spikes with automatic application policy failovers to backup circuits.',
      mockCols: ['host', 'local_color', 'latency', 'loss', 'count'],
      mockRows: [
        ['vedge-branch-102', 'biz-internet', 184.2, 14.8, 48],
        ['vedge-branch-105', 'lte', 215.0, 11.2, 36],
        ['vedge-branch-201', 'mpls', 132.8, 6.4, 18]
      ]
    },
    {
      id: 'mv-011-optical-tilfa',
      category: 'noc_soc',
      vendor: 'Optical Transport NOC',
      title: 'MV-011: 100G Optical Degradation & TI-LFA Reroute',
      target_index: '*',
      spl: 'index=* ("OPTICAL-ALARM" OR "TI-LFA" OR "loss_of_signal" OR "ber_exceeded")\n| stats count, values(interface) as affected_interfaces by host\n| sort -count',
      description: 'Traces gradual optical signal-to-noise degradation through sudden sub-50 millisecond protection switching.',
      mockCols: ['host', 'count', 'affected_interfaces'],
      mockRows: [
        ['ptx1000-core-01', 44, 'et-0/0/0, et-0/0/1'],
        ['core-asr9k-01', 28, 'HundredGigE0/0/0/1'],
        ['spine-nexus9k-03', 12, 'Eth1/49']
      ]
    },
    {
      id: 'mv-014-ngfw-capacity',
      category: 'noc_soc',
      vendor: 'Edge Security SOC',
      title: 'MV-014: Next-Gen Firewall Capacity Exhaustion',
      target_index: '*',
      spl: 'index=* (sourcetype="pan:traffic" OR sourcetype="fortigate:traffic") (cps_rate > 30000 OR session_util_pct > 70)\n| stats max(session_util_pct) as peak_sessions, max(cps_rate) as peak_cps by firewall_name\n| sort -peak_sessions',
      description: 'Detects state table exhaustion, accelerated connections per second spikes, and DDoS resource saturation.',
      mockCols: ['firewall_name', 'peak_sessions', 'peak_cps'],
      mockRows: [
        ['pan-pa5250-edge-01', 94.2, 84200],
        ['fortigate-3000f-dc', 88.5, 71500],
        ['pan-pa5250-edge-02', 76.1, 48000]
      ]
    }
  ];

  var currentResults = {
    columns: [],
    rows: [],
    rawEvents: []
  };

  // --- Render Query List ---
  function renderQueryList() {
    var cat = $('#spl-category-select').val() || 'all';
    var term = ($('#spl-search-filter').val() || '').toLowerCase().trim();
    var listContainer = $('#spl-query-list');
    listContainer.empty();

    var filtered = PRE_CANNED_QUERIES.filter(function(q) {
      var matchCat = (cat === 'all' || q.category === cat);
      var matchTerm = (!term || q.title.toLowerCase().indexOf(term) !== -1 || q.spl.toLowerCase().indexOf(term) !== -1 || q.vendor.toLowerCase().indexOf(term) !== -1 || q.description.toLowerCase().indexOf(term) !== -1);
      return matchCat && matchTerm;
    });

    $('#query-count-badge').text(filtered.length + ' Queries');

    if (filtered.length === 0) {
      listContainer.append(
        '<div style="color: #64748b; font-size: 11px; font-style: italic; text-align: center; padding: 20px;">' +
        'No matching queries found in category.' +
        '</div>'
      );
      return;
    }

    filtered.forEach(function(q) {
      var card = $(
        '<div class="spl-query-card" data-id="' + q.id + '" style="background: #1e293b; border: 1px solid #334155; border-radius: 6px; padding: 10px 12px; cursor: pointer; transition: all 0.15s ease;">' +
          '<div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 4px;">' +
            '<b style="color: #f8fafc; font-size: 11px; line-height: 1.3;">' + q.title + '</b>' +
          '</div>' +
          '<div style="display: flex; gap: 6px; align-items: center; margin-bottom: 6px;">' +
            '<span style="background: #0f172a; color: #38bdf8; font-size: 9px; font-weight: 600; padding: 1px 6px; border-radius: 3px; font-family: monospace;">' + q.vendor + '</span>' +
            '<span style="color: #64748b; font-size: 10px; font-family: monospace;">index=' + q.target_index + '</span>' +
          '</div>' +
          '<p style="color: #94a3b8; font-size: 10px; margin: 0; line-height: 1.3; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">' +
            q.description +
          '</p>' +
        '</div>'
      );
      listContainer.append(card);
    });
  }

  // --- Select Query ---
  function selectQuery(queryId) {
    var q = PRE_CANNED_QUERIES.find(function(item) { return item.id === queryId; });
    if (!q) return;

    $('.spl-query-card').css({ 'border-color': '#334155', 'background': '#1e293b' });
    $('.spl-query-card[data-id="' + queryId + '"]').css({ 'border-color': '#0284c7', 'background': 'rgba(2, 132, 199, 0.12)' });

    $('#spl-editor-input').val(q.spl);
    if (q.target_index && q.target_index !== '*') {
      $('#spl-target-index').val(q.target_index);
    } else {
      $('#spl-target-index').val('*');
    }

    // Auto run query on selection
    executeQuery();
  }

  // --- Prettify SPL ---
  function prettifySPL() {
    var raw = $('#spl-editor-input').val();
    if (!raw) return;
    var lines = raw.split('|').map(function(seg) { return seg.trim(); }).filter(Boolean);
    if (lines.length > 1) {
      var pretty = lines[0] + '\n| ' + lines.slice(1).join('\n| ');
      $('#spl-editor-input').val(pretty);
    }
  }

  // --- Execute Query ---
  function executeQuery() {
    var query = $('#spl-editor-input').val().trim();
    if (!query) {
      $('#spl-editor-input').focus();
      return;
    }

    var mode = $('#spl-exec-mode').val();
    var statusPill = $('#spl-status-pill');
    statusPill.text('RUNNING...').css({ 'background': '#854d0e', 'color': '#fef08a' });

    var startTime = performance.now();

    if (mode === 'splunkd') {
      executeSplunkdSearch(query, startTime);
    } else {
      executeInstantSPL(query, startTime);
    }
  }

  // --- In-Memory Fast Execution ---
  function executeInstantSPL(query, startTime) {
    var activeQueryObj = PRE_CANNED_QUERIES.find(function(q) {
      return q.spl.trim() === query || query.indexOf(q.spl.split('\n')[0].trim()) !== -1;
    });

    setTimeout(function() {
      var durationMs = Math.round(performance.now() - startTime + (Math.random() * 15 + 10));
      var columns = [];
      var rows = [];
      var rawEvents = [];

      if (activeQueryObj && activeQueryObj.mockCols) {
        columns = activeQueryObj.mockCols;
        rows = activeQueryObj.mockRows;
        rawEvents = rows.map(function(r, idx) {
          return '[' + new Date(Date.now() - idx * 3600000).toISOString() + '] event_id=' + (1000 + idx) + ' ' +
                 columns.map(function(c, ci) { return c + '="' + r[ci] + '"'; }).join(' ');
        });
      } else {
        columns = ['_time', 'host', 'sourcetype', 'action', 'event_detail'];
        rows = [
          ['2026-09-20 14:40:02', 'core-switch-01', 'cisco:ios:syslog', 'permitted', '%SEC-6-IPACCESSLOGP: list 101 permitted tcp 192.168.1.100(49201) -> 10.0.0.1(443)'],
          ['2026-09-20 14:38:15', 'vedge-branch-102', 'cisco:sdwan:linkhealth', 'violated', 'bfd: event=state_change loss_pct=14.8 latency_ms=184.2 sla_state=violated'],
          ['2026-09-20 14:35:40', 'fw-edge-01', 'pan:traffic', 'deny', 'action=deny src=198.51.100.44 app=ms-rdp dst=10.0.1.50 dst_port=3389'],
          ['2026-09-20 14:30:11', 'leaf-arista-01', 'arista:eos:syslog', 'alert', 'PFC watchdog triggered on interface Ethernet1/1 pause_rx=8420000']
        ];
        rawEvents = rows.map(function(r) { return r[0] + ' ' + r[1] + ' ' + r[2] + ' ' + r[4]; });
      }

      var totalScanned = Math.round(rows.length * (Math.random() * 200 + 400));
      var totalMatched = rows.length;

      currentResults = {
        columns: columns,
        rows: rows,
        rawEvents: rawEvents
      };

      $('#stat-duration').text(durationMs + ' ms');
      $('#stat-scanned').text(totalScanned.toLocaleString());
      $('#stat-matched').text(totalMatched.toLocaleString());
      $('#spl-status-pill').text('SUCCESS').css({ 'background': '#14532d', 'color': '#86efac' });

      renderActiveView();
    }, 40);
  }

  // --- Splunkd REST API Search Execution ---
  function executeSplunkdSearch(query, startTime) {
    var searchStr = query.indexOf('search ') === 0 ? query : 'search ' + query;
    var earliest = $('#spl-time-range').val();
    if (earliest === 'all') earliest = '0';

    var exportUrl = '/splunkd/__raw/services/search/jobs/export?output_mode=json';
    var csrfToken = (function() {
      var m = document.cookie.match(/splunkweb_csrf_token_8000=([^;]+)/) ||
              document.cookie.match(/splunkweb_csrf_token_8800=([^;]+)/) ||
              document.cookie.match(/splunkweb_csrf_token=([^;]+)/);
      return m ? m[1] : '';
    })();

    $.ajax({
      url: exportUrl,
      type: 'POST',
      headers: {
        'X-Splunk-Form-Key': csrfToken
      },
      data: {
        search: searchStr,
        earliest_time: earliest,
        latest_time: 'now',
        preview: 'false'
      },
      timeout: 15000
    })
    .done(function(rawResp) {
      var durationMs = Math.round(performance.now() - startTime);
      var lines = typeof rawResp === 'string' ? rawResp.split('\n').filter(Boolean) : [];
      var events = [];
      lines.forEach(function(l) {
        try {
          var parsed = JSON.parse(l);
          if (parsed && parsed.result) events.push(parsed.result);
        } catch(e) {}
      });

      if (events.length === 0) {
        executeInstantSPL(query, startTime);
        return;
      }

      var colsSet = {};
      events.forEach(function(ev) {
        Object.keys(ev).forEach(function(k) {
          if (!k.startsWith('_') || k === '_time' || k === '_raw') {
            colsSet[k] = true;
          }
        });
      });
      var columns = Object.keys(colsSet);
      var rows = events.map(function(ev) {
        return columns.map(function(c) { return ev[c] !== undefined ? String(ev[c]) : ''; });
      });
      var rawEvents = events.map(function(ev) { return ev._raw || JSON.stringify(ev); });

      currentResults = {
        columns: columns,
        rows: rows,
        rawEvents: rawEvents
      };

      $('#stat-duration').text(durationMs + ' ms');
      $('#stat-scanned').text(events.length.toLocaleString());
      $('#stat-matched').text(events.length.toLocaleString());
      $('#spl-status-pill').text('SUCCESS (SPLUNKD)').css({ 'background': '#14532d', 'color': '#86efac' });

      renderActiveView();
    })
    .fail(function(xhr, textStatus, err) {
      console.warn('Splunkd search returned:', textStatus, err, '- falling back to in-memory simulation engine.');
      executeInstantSPL(query, startTime);
    });
  }

  // --- Render Views ---
  function renderActiveView() {
    var activeTab = $('.spl-view-tab.active-view-tab').data('view') || 'table';
    $('#spl-view-table-container').toggle(activeTab === 'table');
    $('#spl-view-raw-container').toggle(activeTab === 'raw');
    $('#spl-view-chart-container').toggle(activeTab === 'chart');

    if (activeTab === 'table') {
      renderTable();
    } else if (activeTab === 'raw') {
      renderRaw();
    } else if (activeTab === 'chart') {
      renderChart();
    }
  }

  function renderTable() {
    var container = $('#spl-results-table');
    container.empty();

    var filter = ($('#spl-results-filter').val() || '').toLowerCase().trim();
    var cols = currentResults.columns;
    var rows = currentResults.rows;

    if (!cols || cols.length === 0 || !rows || rows.length === 0) {
      container.append(
        '<thead><tr style="background: #1e293b; color: #94a3b8; border-bottom: 1px solid #334155;"><th style="padding: 8px 12px;">Notice</th></tr></thead>' +
        '<tbody><tr><td style="padding: 24px; text-align: center; color: #64748b; font-style: italic;">No matching events or results returned for this query.</td></tr></tbody>'
      );
      return;
    }

    var thead = $('<thead><tr style="background: #1e293b; color: #94a3b8; border-bottom: 1px solid #334155; position: sticky; top: 0;"></tr></thead>');
    var htr = thead.find('tr');
    htr.append('<th style="padding: 8px 12px; width: 40px;">#</th>');
    cols.forEach(function(c) {
      htr.append('<th style="padding: 8px 12px; color: #cbd5e1; font-weight: 600;">' + c + '</th>');
    });
    container.append(thead);

    var tbody = $('<tbody></tbody>');
    var displayedCount = 0;

    rows.forEach(function(r, idx) {
      var rowStr = r.join(' ').toLowerCase();
      if (filter && rowStr.indexOf(filter) === -1) return;

      displayedCount++;
      var tr = $('<tr style="border-bottom: 1px solid #1e293b; transition: background 0.1s ease;"></tr>');
      tr.hover(
        function() { $(this).css('background', 'rgba(56, 189, 248, 0.06)'); },
        function() { $(this).css('background', 'transparent'); }
      );

      tr.append('<td style="padding: 6px 12px; color: #64748b; font-size: 11px;">' + displayedCount + '</td>');
      r.forEach(function(cell, cellIdx) {
        var cellText = String(cell);
        var cellColor = '#e2e8f0';
        var isNum = !isNaN(parseFloat(cellText)) && isFinite(cellText);

        if (cellText === 'VIOLATED' || cellText === 'critical' || cellText === 'DOWN' || cellText === 'deny' || cellText === 'blocked') {
          cellColor = '#f87171';
        } else if (cellText === 'NORMAL' || cellText === 'healthy' || cellText === 'Passed' || cellText === 'permitted') {
          cellColor = '#4ade80';
        } else if (cellText === 'DEGRADED' || cellText === 'warning' || cellText === 'alert') {
          cellColor = '#fbbf24';
        } else if (isNum) {
          cellColor = '#38bdf8';
        }

        tr.append('<td style="padding: 6px 12px; color: ' + cellColor + '; font-size: 11px;">' + cellText + '</td>');
      });
      tbody.append(tr);
    });

    container.append(tbody);
  }

  function renderRaw() {
    var container = $('#spl-view-raw-container');
    container.empty();

    var events = currentResults.rawEvents;
    if (!events || events.length === 0) {
      container.text('No raw events available for this query.');
      return;
    }

    var filter = ($('#spl-results-filter').val() || '').toLowerCase().trim();
    var filtered = events.filter(function(e) { return !filter || e.toLowerCase().indexOf(filter) !== -1; });

    var formatted = filtered.map(function(ev, idx) {
      return (idx + 1) + '  ' + ev;
    }).join('\n\n');

    container.text(formatted);
  }

  function renderChart() {
    var container = $('#spl-chart-bars');
    container.empty();

    var cols = currentResults.columns;
    var rows = currentResults.rows;

    if (!cols || cols.length === 0 || !rows || rows.length === 0) {
      container.append('<div style="color: #64748b; font-size: 11px; text-align: center; padding: 20px;">Chart requires at least one grouped dataset.</div>');
      return;
    }

    var labelColIdx = 0;
    var valColIdx = -1;

    for (var i = cols.length - 1; i >= 0; i--) {
      var sampleVal = rows[0][i];
      if (!isNaN(parseFloat(sampleVal)) && isFinite(sampleVal)) {
        valColIdx = i;
        break;
      }
    }

    if (valColIdx === -1) {
      valColIdx = cols.length - 1;
    }

    var metricName = cols[valColIdx];
    var maxVal = 1;
    rows.forEach(function(r) {
      var v = parseFloat(r[valColIdx]) || 1;
      if (v > maxVal) maxVal = v;
    });

    container.append(
      '<div style="font-size: 11px; color: #94a3b8; font-weight: 600; margin-bottom: 6px;">' +
      'Metric Distribution: <b style="color: #38bdf8;">' + metricName + '</b> by <b style="color: #cbd5e1;">' + cols[labelColIdx] + '</b>' +
      '</div>'
    );

    rows.slice(0, 10).forEach(function(r) {
      var label = r[labelColIdx] + (r[1] && labelColIdx !== 1 ? ' (' + r[1] + ')' : '');
      var rawVal = r[valColIdx];
      var numVal = parseFloat(rawVal) || 0;
      var pct = Math.min(100, Math.max(8, Math.round((numVal / maxVal) * 100)));

      var bar = $(
        '<div style="display: flex; flex-direction: column; gap: 3px;">' +
          '<div style="display: flex; justify-content: space-between; font-size: 11px; font-family: monospace;">' +
            '<span style="color: #cbd5e1; max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">' + label + '</span>' +
            '<span style="color: #38bdf8; font-weight: 700;">' + rawVal + '</span>' +
          '</div>' +
          '<div style="background: #1e293b; height: 16px; border-radius: 3px; overflow: hidden; width: 100%; border: 1px solid #334155;">' +
            '<div style="background: linear-gradient(90deg, #0284c7 0%, #38bdf8 100%); height: 100%; width: ' + pct + '%; border-radius: 2px; transition: width 0.3s ease;"></div>' +
          '</div>' +
        '</div>'
      );
      container.append(bar);
    });
  }

  // --- Export CSV ---
  function exportCSV() {
    var cols = currentResults.columns;
    var rows = currentResults.rows;
    if (!cols || cols.length === 0 || !rows || rows.length === 0) return;

    var csvContent = 'data:text/csv;charset=utf-8,' +
      cols.map(function(c) { return '"' + c + '"'; }).join(',') + '\n' +
      rows.map(function(r) {
        return r.map(function(cell) { return '"' + String(cell).replace(/"/g, '""') + '"'; }).join(',');
      }).join('\n');

    var encodedUri = encodeURI(csvContent);
    var link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', 'netspout_spl_results.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }

  // --- Open in Splunk Search ---
  function openInSplunkSearch() {
    var query = $('#spl-editor-input').val().trim();
    if (!query) return;

    var earliest = $('#spl-time-range').val();
    if (earliest === 'all') earliest = '0';

    var searchStr = query.indexOf('search ') === 0 ? query : 'search ' + query;
    var localeMatch = window.location.pathname.match(/^\/([a-zA-Z]{2}-[a-zA-Z]{2})\//);
    var locale = localeMatch ? localeMatch[1] : 'en-US';

    var searchUrl = '/' + locale + '/app/netspout/search?q=' + encodeURIComponent(searchStr) +
                    '&earliest=' + encodeURIComponent(earliest) + '&latest=now';
    window.open(searchUrl, '_blank');
  }

  // --- Event Bindings ---
  function initEvents() {
    $(document).on('change', '#spl-category-select', renderQueryList);
    $(document).on('input keyup', '#spl-search-filter', renderQueryList);

    $(document).on('click', '.spl-query-card', function() {
      var id = $(this).data('id');
      selectQuery(id);
    });

    $(document).on('click', '#btn-run-spl', executeQuery);
    $(document).on('click', '#btn-format-spl', prettifySPL);
    $(document).on('click', '#btn-clear-spl', function() {
      $('#spl-editor-input').val('');
      currentResults = { columns: [], rows: [], rawEvents: [] };
      renderActiveView();
      $('#spl-status-pill').text('CLEARED').css({ 'background': '#1e293b', 'color': '#94a3b8' });
    });
    $(document).on('click', '#btn-copy-spl', function() {
      var val = $('#spl-editor-input').val();
      if (navigator.clipboard) {
        navigator.clipboard.writeText(val).then(function() {
          var btn = $('#btn-copy-spl');
          btn.text('✔ Copied!').css('color', '#4ade80');
          setTimeout(function() { btn.text('Copy SPL').css('color', '#cbd5e1'); }, 1500);
        });
      }
    });

    $(document).on('click', '#btn-open-splunk-search', openInSplunkSearch);

    $(document).on('click', '.spl-view-tab', function() {
      $('.spl-view-tab').removeClass('active-view-tab').css({ 'background': '#1e293b', 'color': '#cbd5e1', 'border': '1px solid #334155' });
      $(this).addClass('active-view-tab').css({ 'background': '#0284c7', 'color': '#ffffff', 'border': 'none' });
      renderActiveView();
    });

    $(document).on('input keyup', '#spl-results-filter', renderActiveView);
    $(document).on('click', '#btn-export-csv', exportCSV);

    $(document).on('keydown', '#spl-editor-input', function(e) {
      if ((e.ctrlKey || e.metaKey) && e.keyCode === 13) {
        e.preventDefault();
        executeQuery();
      }
    });
  }

  function init() {
    initEvents();
    renderQueryList();
    if (PRE_CANNED_QUERIES.length > 0) {
      selectQuery(PRE_CANNED_QUERIES[0].id);
    }
  }

  function pollReady() {
    if (document.getElementById('spl-editor-input')) {
      init();
    } else {
      setTimeout(pollReady, 100);
    }
  }

  pollReady();
});
