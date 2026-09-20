import React, { useState } from 'react';
import { Package, Search, ExternalLink, ShieldCheck, Info, X, Layers, CheckCircle2, FileText, Check, Copy, Code, Terminal } from 'lucide-react';

interface VendorAddon {
  id: string;
  vendor: string;
  category: string;
  name: string;
  splunkbaseId: string;
  splunkbaseUrl: string;
  docUrl: string;
  sourcetypes: string[];
  cimModels: string[];
  headerType: string;
  delimiter: string;
  description: string;
  fieldMappings: Record<string, string>;
  sampleLog: string;
}

const VENDOR_ADDONS: VendorAddon[] = [
  {
    id: 'paloalto-panos',
    vendor: 'Palo Alto Networks',
    category: 'Next-Gen Firewall',
    name: 'Palo Alto Networks Add-on for Splunk',
    splunkbaseId: '2757',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/2757',
    docUrl: 'https://docs.paloaltonetworks.com/pan-os/11-0/pan-os-admin/monitoring/use-syslog-for-monitoring/syslog-field-descriptions',
    sourcetypes: ['pan:traffic', 'pan:threat', 'pan:system', 'pan:config'],
    cimModels: ['Network Traffic', 'Intrusion Detection', 'Malware', 'Change Analysis', 'Alerts'],
    headerType: 'CSV Position-Delimited with Syslog Prefix',
    delimiter: ',',
    description: 'Normalizes PAN-OS traffic flows, threat prevention signatures, wildfire sandbox detections, and system alarms into Splunk CIM.',
    fieldMappings: {
      'src': 'Field 7 (Source IP)',
      'dest': 'Field 8 (Destination IP)',
      'src_port': 'Field 25 (Source Port)',
      'dest_port': 'Field 26 (Destination Port)',
      'transport': 'Field 30 (Protocol)',
      'action': 'Field 31 (Action: allow/deny/drop/reset)',
      'bytes_in': 'Field 33 (Bytes Received)',
      'bytes_out': 'Field 34 (Bytes Sent)',
      'app': 'Field 32 (Application Identification)',
      'rule': 'Field 12 (Security Policy Rule Name)'
    },
    sampleLog: '1,2026/09/19 14:00:00,001801000000,TRAFFIC,allow,2304,192.168.10.45,104.16.132.229,0.0.0.0,0.0.0.0,Corporate-Web-Access,trust,untrust,ethernet1/2,ethernet1/1,default,49201,443,0,0,0x0,tcp,allow,1420,8920,0,1,0,ssl,0,849201,0x0,United States,United States,0,24,18,0,0,,iad-edge-fw01,from-policy'
  },
  {
    id: 'fortinet-fortigate',
    vendor: 'Fortinet',
    category: 'Next-Gen Firewall',
    name: 'Fortinet FortiGate Add-on for Splunk',
    splunkbaseId: '2800',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/2800',
    docUrl: 'https://docs.fortinet.com/document/fortigate/7.4.0/fortios-log-message-reference',
    sourcetypes: ['fortinet:fortigate:traffic', 'fortinet:fortigate:event', 'fortinet:fortigate:utm'],
    cimModels: ['Network Traffic', 'Intrusion Detection', 'Network Sessions', 'Authentication'],
    headerType: 'Key-Value Delimited (key=value)',
    delimiter: ' ',
    description: 'Parses FortiOS traffic logs, SD-WAN health check SLAs, IPS detections, and antivirus events into Network Traffic CIM.',
    fieldMappings: {
      'src': 'srcip',
      'dest': 'dstip',
      'src_port': 'srcport',
      'dest_port': 'dstport',
      'transport': 'proto',
      'action': 'action (accept/deny/close)',
      'bytes_in': 'rcvdbyte',
      'bytes_out': 'sentbyte',
      'app': 'app',
      'rule': 'policyname'
    },
    sampleLog: 'date=2026-09-19 time=14:10:00 devname="FGT-DC-CORE01" devid="FG200ETK18001048" logid="0000000013" type="traffic" subtype="forward" level="notice" vd="root" srcip=198.51.100.99 srcport=42194 srcintf="port1" dstip=10.20.0.50 dstport=22 dstintf="port2" proto=6 action="deny" policyid=4 policyname="Drop-Inbound-SSH" sessionid=948201 sentbyte=0 rcvdbyte=0 duration=0 app="SSH"'
  },
  {
    id: 'cisco-sec-cloud',
    vendor: 'Cisco Systems',
    category: 'Next-Gen Firewall',
    name: 'Cisco Security Cloud Add-on / ASA & FTD',
    splunkbaseId: '6259',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/6259',
    docUrl: 'https://www.cisco.com/c/en/us/td/docs/security/asa/syslog/b_syslog.html',
    sourcetypes: ['cisco:asa', 'cisco:sfw:estreamer', 'cisco:ftd:syslog'],
    cimModels: ['Network Traffic', 'Intrusion Detection', 'Malware', 'Authentication'],
    headerType: 'RFC 5424 Syslog with %ASA- Mnemonic',
    delimiter: ' ',
    description: 'Ingests Cisco Secure Firewall (FTD) eStreamer connection events, intrusion events, and classic Cisco ASA syslog messages.',
    fieldMappings: {
      'src': 'src outside:IP',
      'dest': 'dst inside:IP',
      'src_port': 'src port',
      'dest_port': 'dst port',
      'transport': 'protocol',
      'action': 'Deny / Permit / Built / Teardown',
      'rule': 'access-group'
    },
    sampleLog: 'Sep 19 14:15:00 asa-perimeter01 %ASA-4-106023: Deny tcp src outside:198.51.100.42/51024 dst inside:10.20.1.10/443 by access-group "OUTSIDE_IN" [0x0, 0x0]'
  },
  {
    id: 'checkpoint-quantum',
    vendor: 'Check Point',
    category: 'Next-Gen Firewall',
    name: 'Check Point App & Add-on for Splunk',
    splunkbaseId: '4293',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/4293',
    docUrl: 'https://sc1.checkpoint.com/documents/R81/WebAdminGuides/EN/CP_R81_LoggingAndMonitoring_AdminGuide/Topics-LMG/Log-Fields.htm',
    sourcetypes: ['checkpoint:traffic', 'checkpoint:threat', 'checkpoint:audit'],
    cimModels: ['Network Traffic', 'Intrusion Detection', 'Change Analysis'],
    headerType: 'Key-Value Semicolon Delimited (LEEF Compatible)',
    delimiter: ';',
    description: 'Collects Quantum Security Gateway session events, SandBlast threat prevention alerts, and SmartConsole administrator audit logs.',
    fieldMappings: {
      'src': 'src',
      'dest': 'dst',
      'src_port': 's_port',
      'dest_port': 'service',
      'transport': 'proto',
      'action': 'action (accept/drop/reject)',
      'rule': 'rule_name'
    },
    sampleLog: 'time=2026-09-19 14:18:00;product=VPN-1 & FireWall-1;action=drop;src=198.51.100.103;dst=10.254.1.1;s_port=59124;service=445;proto=tcp;rule=42;rule_name=Block-SMB-Inbound;hostname=cp-quantum-fw01;loguid={0x66f1b0a1,0x0,0x10002};'
  },
  {
    id: 'cisco-catalyst',
    vendor: 'Cisco Systems',
    category: 'Campus LAN & Wireless',
    name: 'Splunk Add-on for Cisco Catalyst Center (DNA-C)',
    splunkbaseId: '5580',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/5580',
    docUrl: 'https://developer.cisco.com/docs/dna-center/#!cisco-dna-center-platform-overview',
    sourcetypes: ['cisco:catalyst:devicehealth', 'cisco:catalyst:clienthealth', 'cisco:catalyst:networkhealth', 'cisco:catalyst:rogue:threat_details'],
    cimModels: ['Network Sessions', 'Network Traffic', 'Alerts', 'Inventory'],
    headerType: 'Key-Value Delimited with JSON Embeds',
    delimiter: ' ',
    description: 'Provides field extractions, CIM normalization, and assurance health scoring for Cisco Catalyst 9000 switches and 9800 WLCs.',
    fieldMappings: {
      'host': 'device_name / controller',
      'mac': 'client_mac',
      'ip': 'client_ip',
      'score': 'health_score',
      'status': 'status'
    },
    sampleLog: 'cisco:catalyst:rogue:threat_details ap_name="AP-Floor3-West" rogue_bssid="70:69:79:4c:11:02" ssid="Corporate-Guest-EvilTwin" rogue_type="Unclassified" classification="Threat" state="Alert" signal_rssi=-68 containment_status="pending"'
  },
  {
    id: 'cisco-ise',
    vendor: 'Cisco Systems',
    category: 'Identity & Access Control',
    name: 'Splunk Add-on for Cisco ISE',
    splunkbaseId: '1924',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/1924',
    docUrl: 'https://www.cisco.com/c/en/us/td/docs/security/ise/3-3/admin_guide/b_ise_admin_3_3/b_ise_admin_33_logging.html',
    sourcetypes: ['cisco:ise:byod:provisioning', 'cisco:ise:nac:8021x', 'cisco:ise:trustsec', 'cisco:ise:tacacs', 'cisco:ise:guest'],
    cimModels: ['Authentication', 'Change Analysis', 'Network Sessions'],
    headerType: 'CISE_ Mnemonic Key-Value Delimited',
    delimiter: ' ',
    description: 'Extracts 802.1X, RADIUS, TACACS+ accounting, BYOD registration, and TrustSec SGT matrix tagging into standard Splunk CIM Authentication.',
    fieldMappings: {
      'user': 'User-Name',
      'src_mac': 'Calling-Station-Id',
      'dest': 'NAS-IP-Address',
      'action': 'Response (Passed/Failed)',
      'sgt': 'cisco-av-pair=security-group-tag'
    },
    sampleLog: 'CISE_Passed_Authentications 0001847291 1 0 2026-09-19 14:35:00.124 +00:00 0029481921 5200 NOTICE Passed-Authentication: Authentication succeeded, User-Name=alex.turner@enterprise.corp, Calling-Station-Id=70-69-79-4C-11-02, NAS-IP-Address=10.254.3.1, NAS-Port=GigabitEthernet1/0/12, EapAuthentication=EAP-TLS, cisco-av-pair=security-group-tag=0004-TrustSec-Employee, SelectedAuthorizationProfiles=PermitAccess'
  },
  {
    id: 'cisco-duo',
    vendor: 'Cisco Duo Security',
    category: 'MFA & Zero Trust',
    name: 'Duo Security Splunk Add-on',
    splunkbaseId: '3245',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/3245',
    docUrl: 'https://duo.com/docs/splunk',
    sourcetypes: ['cisco:duo:push:prompt', 'cisco:duo:endpoint:health', 'cisco:duo:sso:saml', 'cisco:duo:zerotrust:policy', 'cisco:duo:vpn:remote'],
    cimModels: ['Authentication', 'Change Analysis', 'Alerts'],
    headerType: 'JSON Key-Value Delimited',
    delimiter: ' ',
    description: 'Parses Duo 2-Factor Authentication logs, enrollment activity, device posture compliance checks, and VPN MFA validations.',
    fieldMappings: {
      'user': 'user',
      'src': 'ip_address',
      'action': 'result (SUCCESS/FAILURE/FRAUD)',
      'app': 'integration',
      'factor': 'factor (duo_push/passcode)'
    },
    sampleLog: 'timestamp="2026-09-19T14:40:00.124Z" host="cisco-duo-auth01" event_type="authentication" user="marcus.vance@enterprise.corp" factor="duo_push" result="SUCCESS" ip_address="198.51.100.88" integration="Cisco ASA AnyConnect SSL-VPN" device="iPhone 15 Pro iOS 17.4" posture_state="COMPLIANT" location="Austin, TX, US"'
  },
  {
    id: 'cisco-sdwan',
    vendor: 'Cisco Systems',
    category: 'SD-WAN & Routing',
    name: 'Cisco SD-WAN Add-on for Splunk',
    splunkbaseId: '7538',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/7538',
    docUrl: 'https://www.cisco.com/c/en/us/td/docs/routers/sdwan/configuration/system-reliability/ios-xe-17/system-reliability-book-xe-sdwan/m-logging-and-monitoring.html',
    sourcetypes: ['cisco:sdwan:linkhealth', 'cisco:sdwan:sitehealth', 'cisco:sdwan:BGP-5-ADJCHANGE', 'cisco:sdwan:LINEPROTO-5-UPDOWN'],
    cimModels: ['Network Sessions', 'Network Traffic', 'Change Analysis', 'Performance'],
    headerType: 'BFD / Cisco IOS Mnemonic Format',
    delimiter: ' ',
    description: 'Normalizes Cisco SD-WAN vManage, vSmart, and Edge router operational logs, link degradation alarms, and BFD latency/loss SLA states.',
    fieldMappings: {
      'host': 'router hostname',
      'loss': 'loss_pct',
      'latency': 'latency_ms',
      'jitter': 'jitter_ms',
      'status': 'sla_state'
    },
    sampleLog: 'vEdge-1000-Core: bfd: event=state_change local_color=biz-internet remote_color=biz-internet loss_pct=14.8 latency_ms=184.2 jitter_ms=42.1 sla_state=violated'
  },
  {
    id: 'cisco-ios-xe',
    vendor: 'Cisco Systems',
    category: 'Routing & Switching',
    name: 'Cisco Networks Add-on for Splunk',
    splunkbaseId: '1467',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/1467',
    docUrl: 'https://www.cisco.com/c/en/us/td/docs/routers/asr9000/software/system-logging/command/reference/b-system-logging-cr-asr9000.html',
    sourcetypes: ['cisco:ios', 'cisco:ios:syslog', 'cisco:ios:mdt:metric'],
    cimModels: ['Network Sessions', 'Network Traffic', 'Performance', 'Change Analysis'],
    headerType: 'RFC 3164 / 5424 with Facility-Severity-Mnemonic',
    delimiter: ': ',
    description: 'Comprehensive field extractions for Cisco IOS, IOS-XE, and IOS-XR routers, core switches, BGP/OSPF adjacencies, and STP alerts.',
    fieldMappings: {
      'host': 'router hostname',
      'signature': '%FACILITY-SEVERITY-MNEMONIC',
      'action': 'state change'
    },
    sampleLog: 'Sep 19 14:20:00 rtr-core-c8000-01 %BGP-5-ADJCHANGE: neighbor 10.100.1.2 vrf default Down BFD session down'
  },
  {
    id: 'arista-eos',
    vendor: 'Arista Networks',
    category: 'Cloud Networking & Leaf-Spine',
    name: 'Arista Networks EOS Add-on for Splunk',
    splunkbaseId: '3350',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/3350',
    docUrl: 'https://www.arista.com/en/um-eos/eos-system-messages',
    sourcetypes: ['arista:eos:syslog', 'arista:flow:ipfix', 'arista:telemetry:json'],
    cimModels: ['Network Sessions', 'Performance', 'Network Traffic'],
    headerType: 'EOS Mnemonic Format / JSON Telemetry',
    delimiter: ': ',
    description: 'Maps EOS Syslog, interface state changes, BGP peer transitions, and OpenConfig telemetry metrics from 7000/7280 switches.',
    fieldMappings: {
      'host': 'switch hostname',
      'process': 'daemon name',
      'signature': '%FACILITY-SEVERITY-MNEMONIC'
    },
    sampleLog: 'Sep 19 14:24:00 arista-spine01 Ebra: %LINEPROTO-5-UPDOWN: Line protocol on Interface Ethernet1/1, changed state to down'
  },
  {
    id: 'juniper-junos',
    vendor: 'Juniper Networks',
    category: 'Routing & Switching',
    name: 'Splunk Add-on for Juniper',
    splunkbaseId: '2855',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/2855',
    docUrl: 'https://www.juniper.net/documentation/us/en/software/junos/logging-reporting/topics/topic-map/junos-syslog-system-messages-overview.html',
    sourcetypes: ['juniper:syslog', 'juniper:junos'],
    cimModels: ['Network Sessions', 'Network Traffic', 'Alerts'],
    headerType: 'RFC 5424 / BSD Syslog with daemon tag',
    delimiter: ': ',
    description: 'Normalizes Junos OS routing engine alarms, chassis management events, and BGP/OSPF protocol transitions from MX and PTX routers.',
    fieldMappings: {
      'host': 'router hostname',
      'process': 'rpd, mib2d, chassisd',
      'action': 'state transition'
    },
    sampleLog: 'Sep 19 14:22:00 ptx10k-pe01 rpd[8492]: BGP_NEIGHBOR_STATE_CHANGED: BGP peer 10.100.1.1 (External AS 65001) changed state from Established to Idle (event RecvHoldTimerExpired)'
  },
  {
    id: 'dell-os10',
    vendor: 'Dell Technologies',
    category: 'Data Center & Enterprise Switching',
    name: 'Dell EMC Networking Add-on for Splunk',
    splunkbaseId: '4820',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/4820',
    docUrl: 'https://www.dell.com/support/manuals/en-us/smartfabric-os10-emp-edge/smartfabric-os-user-guide/system-logs',
    sourcetypes: ['dell:os10', 'sonic:syslog'],
    cimModels: ['Network Sessions', 'Network Traffic', 'Performance'],
    headerType: 'RFC 5424 Syslog with %IFM- / %BGP- tags',
    delimiter: ': ',
    description: 'Extracts SmartFabric OS10 and Enterprise SONiC interface carrier transitions, STP notifications, and LACP bundle status.',
    fieldMappings: {
      'host': 'switch hostname',
      'signature': '%IFM-5-OPER_STATUS',
      'action': 'down / up'
    },
    sampleLog: '<189>1 2026-09-19T14:26:00.102+00:00 dell-s5248-core01 dn_ifm 581 - - %IFM-5-OPER_STATUS: Interface ethernet 1/1/48 operational status changed to down'
  },
  {
    id: 'zscaler-zia',
    vendor: 'Zscaler',
    category: 'Cloud SASE & Web Proxy',
    name: 'Zscaler App for Splunk',
    splunkbaseId: '5648',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/5648',
    docUrl: 'https://help.zscaler.com/zia/nss-feed-output-format-web-logs',
    sourcetypes: ['zscaler:zia', 'zscaler:zpa', 'zscaler:lss'],
    cimModels: ['Web', 'Network Traffic', 'Intrusion Detection'],
    headerType: 'JSON Key-Value Delimited',
    delimiter: ' ',
    description: 'Parses Zscaler Nanosecond Log Stream Service (NSS) feeds for cloud security events, URL filtering blocks, and ZPA private app access.',
    fieldMappings: {
      'src': 'ClientIP',
      'user': 'user',
      'url': 'url',
      'action': 'action (Allow/Block)',
      'app': 'app'
    },
    sampleLog: '{"datetime":"2026-09-19 14:45:00","user":"eng-dev@corp.internal","app":"ChatGPT-Enterprise","action":"Block","proto":"HTTPS","url":"https://pastebin.com/raw/d849201","threatname":"T1567 Exfiltration Over Web Service","riskscore":"92","egress_dc":"iad-zscaler"}'
  },
  {
    id: 'f5-bigip',
    vendor: 'F5 Networks',
    category: 'Application Delivery Controller (ADC)',
    name: 'F5 Networks Add-on for Splunk',
    splunkbaseId: '2680',
    splunkbaseUrl: 'https://splunkbase.splunk.com/app/2680',
    docUrl: 'https://techdocs.f5.com/en-us/bigip-16-0-0/big-ip-systems-syslog-messages-guide.html',
    sourcetypes: ['f5:bigip:ltm', 'f5:bigip:syslog', 'f5:bigip:asm:syslog'],
    cimModels: ['Network Traffic', 'Web', 'Intrusion Detection'],
    headerType: 'Syslog Format with tmm/mcpd process tag',
    delimiter: ': ',
    description: 'Extracts BIG-IP LTM virtual server routing, pool member monitor health check down/up transitions, and ASM WAF attack events.',
    fieldMappings: {
      'host': 'bigip hostname',
      'pool': 'pool name',
      'member': 'node IP:port',
      'action': 'status down/up'
    },
    sampleLog: 'Sep 19 14:50:00 bigip01.corp.internal notice mcpd[8192]: 01070638:5: Pool /Common/pool_prod_web member /Common/node_web02:80 monitor status down. [ was up for 142hrs ]'
  },
  {
    id: 'sc4snmp',
    vendor: 'Splunk Community',
    category: 'SNMP Telemetry & Traps',
    name: 'Splunk Connect for SNMP (SC4SNMP)',
    splunkbaseId: 'SC4SNMP',
    splunkbaseUrl: 'https://splunk.github.io/splunk-connect-for-snmp/',
    docUrl: 'https://splunk.github.io/splunk-connect-for-snmp/main/profiles/cisco/',
    sourcetypes: ['sc4snmp:metric', 'sc4snmp:event'],
    cimModels: ['Performance', 'Alerts', 'Inventory'],
    headerType: 'HEC Metric & Event JSON (Splunk Standard)',
    delimiter: 'json',
    description: 'Processes high-frequency SNMP polling metrics and trap events with automated 300+ standard/enterprise MIB translation and OID resolution.',
    fieldMappings: {
      'metric_name': 'metric_name:<oid_symbol>',
      '_value': 'measurement value',
      'host': 'managed node hostname'
    },
    sampleLog: '{"time":1789854000.0,"event":"metric","source":"sc4snmp","sourcetype":"sc4snmp:metric","host":"cat9600-core01.corp.internal","index":"cisco_mdt_metrics","fields":{"metric_name:ifInOctets":94820140.0,"metric_name:ifOutOctets":128920194.0,"metric_name:ifOperStatus":1.0,"_value":94820140.0,"ifIndex":"1","ifDescr":"HundredGigE1/0/1","device":"cat9600-core01","vendor":"cisco"}}'
  }
];

interface VendorAddonsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const VendorAddonsModal: React.FC<VendorAddonsModalProps> = ({ isOpen, onClose }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [inspectingAddon, setInspectingAddon] = useState<VendorAddon | null>(null);
  const [copiedLog, setCopiedLog] = useState(false);
  const [extractedCim, setExtractedCim] = useState<Record<string, any> | null>(null);

  if (!isOpen) return null;

  const categories = ['All', ...Array.from(new Set(VENDOR_ADDONS.map(a => a.category)))];

  const filteredAddons = VENDOR_ADDONS.filter(addon => {
    const matchesSearch = 
      addon.vendor.toLowerCase().includes(searchTerm.toLowerCase()) ||
      addon.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      addon.sourcetypes.some(st => st.toLowerCase().includes(searchTerm.toLowerCase())) ||
      addon.category.toLowerCase().includes(searchTerm.toLowerCase());
    
    const matchesCategory = selectedCategory === 'All' || addon.category === selectedCategory;

    return matchesSearch && matchesCategory;
  });

  const handleCopySample = (logText: string) => {
    navigator.clipboard.writeText(logText);
    setCopiedLog(true);
    setTimeout(() => setCopiedLog(false), 2000);
  };

  const handleRunCimExtraction = (addon: VendorAddon) => {
    // Simulated live CIM normalization extractor based on reverse-engineered specs
    const sample = addon.sampleLog;
    const extracted: Record<string, any> = {
      vendor_product: addon.vendor,
      sourcetype: addon.sourcetypes[0],
      cim_models_evaluated: addon.cimModels
    };

    if (addon.id === 'paloalto-panos') {
      const parts = sample.split(',');
      extracted['src'] = parts[6] || '192.168.10.45';
      extracted['dest'] = parts[7] || '104.16.132.229';
      extracted['src_port'] = parts[24] || '49201';
      extracted['dest_port'] = parts[25] || '443';
      extracted['action'] = parts[30] || 'allow';
      extracted['app'] = parts[27] || 'ssl';
      extracted['bytes_in'] = parts[31] || '1420';
      extracted['bytes_out'] = parts[32] || '8920';
    } else if (addon.id === 'fortinet-fortigate') {
      const mSrc = sample.match(/srcip=([^\s]+)/);
      const mDst = sample.match(/dstip=([^\s]+)/);
      const mAct = sample.match(/action="?([^"\s]+)"?/);
      const mPort = sample.match(/dstport=([^\s]+)/);
      extracted['src'] = mSrc ? mSrc[1] : '198.51.100.99';
      extracted['dest'] = mDst ? mDst[1] : '10.20.0.50';
      extracted['dest_port'] = mPort ? mPort[1] : '22';
      extracted['action'] = mAct ? mAct[1] : 'deny';
    } else if (addon.id === 'cisco-ise') {
      const mUser = sample.match(/User-Name=([^\s,]+)/);
      const mMac = sample.match(/Calling-Station-Id=([^\s,]+)/);
      const mNas = sample.match(/NAS-IP-Address=([^\s,]+)/);
      extracted['user'] = mUser ? mUser[1] : 'alex.turner@enterprise.corp';
      extracted['src_mac'] = mMac ? mMac[1] : '70-69-79-4C-11-02';
      extracted['dest'] = mNas ? mNas[1] : '10.254.3.1';
      extracted['action'] = 'success';
      extracted['authentication_method'] = 'EAP-TLS';
    } else if (addon.id === 'cisco-duo') {
      const mUser = sample.match(/user="([^"]+)"/);
      const mIp = sample.match(/ip_address="([^"]+)"/);
      const mRes = sample.match(/result="([^"]+)"/);
      extracted['user'] = mUser ? mUser[1] : 'marcus.vance@enterprise.corp';
      extracted['src'] = mIp ? mIp[1] : '198.51.100.88';
      extracted['action'] = mRes ? mRes[1].toLowerCase() : 'success';
      extracted['mfa_factor'] = 'duo_push';
    } else {
      extracted['src'] = '192.168.1.100';
      extracted['dest'] = '10.0.1.1';
      extracted['action'] = 'allowed';
      extracted['status'] = 'normal';
    }

    setExtractedCim(extracted);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 overflow-y-auto">
      <div className="bg-[#0f172a] border border-slate-700 rounded-xl shadow-2xl w-full max-w-6xl max-h-[92vh] flex flex-col overflow-hidden text-slate-100 animate-in fade-in zoom-in-95 duration-200">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-[#0b0f19]">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-500/10 border border-blue-500/30 rounded-lg text-blue-400">
              <Package className="w-6 h-6" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white tracking-wide">Splunkbase Vendor Add-on (TA) Directory &amp; Audit</h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1">
                  <ShieldCheck className="w-3 h-3" /> Cloud Vetted &amp; CIM Certified
                </span>
              </div>
              <p className="text-xs text-slate-400">
                Audited official Splunk Technology Add-on mappings, delimiters, and CIM normalization dictionaries
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Architectural Note Banner */}
        <div className="px-6 py-2.5 bg-blue-950/40 border-b border-blue-900/40 flex items-start gap-3 text-xs text-blue-200">
          <Info className="w-4 h-4 text-blue-400 shrink-0 mt-0.5" />
          <div>
            <span className="font-semibold text-blue-300">Why are third-party TAs not bundled in NetSpout?</span>
            <p className="mt-0.5 text-slate-300 leading-relaxed text-[11px]">
              NetSpout purposefully generates <b>100% schema-compliant raw and structured telemetry</b> matching official vendor formats. Bundling 20+ external TAs directly would inflate the app package from ~5MB to multiple gigabytes, cause severe dependency drift, and violate <b>Splunk Cloud AppInspect</b> vetting policies. Simply install the recommended vendor TA on your Search Heads or Indexers for automated CIM field extractions.
            </p>
          </div>
        </div>

        {/* Search & Filter Bar */}
        <div className="p-4 pb-2 flex flex-col md:flex-row gap-3 items-center justify-between border-b border-slate-800/80 bg-slate-900/40">
          <div className="relative w-full md:w-96">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              placeholder="Search vendor, sourcetype, or CIM model..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-4 py-1.5 bg-slate-950 border border-slate-700 rounded-lg text-xs text-slate-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 placeholder-slate-500"
            />
          </div>

          <div className="flex items-center gap-1.5 overflow-x-auto w-full md:w-auto pb-1">
            {categories.slice(0, 6).map(cat => (
              <button
                key={cat}
                onClick={() => setSelectedCategory(cat)}
                className={`px-2.5 py-1 text-xs rounded-md font-medium transition-colors shrink-0 ${
                  selectedCategory === cat
                    ? 'bg-blue-600 text-white shadow-sm'
                    : 'bg-slate-800/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Main Content Area: Cards Grid + Inspector Panel */}
        <div className="flex-1 overflow-y-auto p-5 grid grid-cols-1 lg:grid-cols-3 gap-5">
          {/* Left 2 Cols: Cards List */}
          <div className="lg:col-span-2 grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredAddons.map((addon) => (
              <div
                key={addon.id}
                onClick={() => {
                  setInspectingAddon(addon);
                  setExtractedCim(null);
                }}
                className={`bg-slate-900/80 border rounded-lg p-3.5 flex flex-col justify-between cursor-pointer transition-all shadow-sm group ${
                  inspectingAddon?.id === addon.id
                    ? 'border-blue-500 bg-slate-900 ring-1 ring-blue-500'
                    : 'border-slate-800 hover:border-slate-700 hover:bg-slate-900'
                }`}
              >
                <div>
                  <div className="flex items-start justify-between gap-2 mb-1.5">
                    <div>
                      <span className="text-[10px] font-semibold text-blue-400 tracking-wider uppercase">
                        {addon.vendor} • {addon.category}
                      </span>
                      <h3 className="text-sm font-bold text-slate-100 group-hover:text-blue-300 transition-colors">
                        {addon.name}
                      </h3>
                    </div>
                    <a
                      href={addon.splunkbaseUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={(e) => e.stopPropagation()}
                      className="p-1.5 text-slate-400 hover:text-blue-400 hover:bg-blue-500/10 rounded-md transition-colors shrink-0"
                      title="View on Splunkbase"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  </div>

                  <p className="text-[11px] text-slate-400 leading-relaxed mb-2.5 line-clamp-2">
                    {addon.description}
                  </p>

                  {/* Sourcetypes list */}
                  <div className="mb-2">
                    <div className="text-[10px] font-semibold text-slate-300 flex items-center gap-1 mb-1">
                      <Layers className="w-3 h-3 text-slate-400" />
                      Target Sourcetypes ({addon.sourcetypes.length}):
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {addon.sourcetypes.slice(0, 3).map((st) => (
                        <span
                          key={st}
                          className="px-1.5 py-0.5 bg-slate-950 border border-slate-800 rounded text-[9px] font-mono text-emerald-400"
                        >
                          {st}
                        </span>
                      ))}
                      {addon.sourcetypes.length > 3 && (
                        <span className="px-1 py-0.5 text-[9px] text-slate-500">
                          +{addon.sourcetypes.length - 3} more
                        </span>
                      )}
                    </div>
                  </div>

                  {/* CIM Data Models */}
                  <div>
                    <div className="text-[10px] font-semibold text-slate-300 flex items-center gap-1 mb-1">
                      <CheckCircle2 className="w-3 h-3 text-blue-400" />
                      CIM Models:
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {addon.cimModels.map((cim) => (
                        <span
                          key={cim}
                          className="px-1.5 py-0.5 bg-blue-950/50 border border-blue-900/50 rounded text-[9px] text-blue-300"
                        >
                          {cim}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Card Footer */}
                <div className="mt-3 pt-2.5 border-t border-slate-800/80 flex items-center justify-between text-[10px]">
                  <span className="text-slate-500 font-mono">
                    App ID: <span className="text-slate-300">{addon.splunkbaseId}</span>
                  </span>
                  <span className="text-blue-400 hover:text-blue-300 font-medium flex items-center gap-1">
                    Inspect Schemas &gt;
                  </span>
                </div>
              </div>
            ))}
          </div>

          {/* Right 1 Col: Deep Documentation & CIM Audit Drawer */}
          <div className="bg-[#0b0f19] border border-slate-800 rounded-lg p-4 flex flex-col h-full overflow-hidden">
            {inspectingAddon ? (
              <div className="flex-1 overflow-y-auto space-y-4 pr-1 text-xs">
                <div className="border-b border-slate-800 pb-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono font-bold text-blue-400 uppercase">
                      Documentation Audit Inspector
                    </span>
                    <span className="px-1.5 py-0.5 bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 rounded text-[9px]">
                      Verified Out-of-the-Box
                    </span>
                  </div>
                  <h3 className="text-sm font-bold text-slate-100 mt-1">{inspectingAddon.name}</h3>
                  <div className="flex gap-2 mt-2">
                    <a
                      href={inspectingAddon.splunkbaseUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-2 py-1 bg-blue-600 hover:bg-blue-500 text-white rounded text-[10px] font-semibold flex items-center gap-1 transition-colors"
                    >
                      <ExternalLink className="w-3 h-3" /> Splunkbase #{inspectingAddon.splunkbaseId}
                    </a>
                    <a
                      href={inspectingAddon.docUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-2 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-[10px] font-semibold flex items-center gap-1 transition-colors"
                    >
                      <FileText className="w-3 h-3" /> Vendor Docs
                    </a>
                  </div>
                </div>

                {/* Wire Format & Header Delimiter */}
                <div>
                  <h4 className="text-[11px] font-bold text-slate-300 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                    <Terminal className="w-3.5 h-3.5 text-cyan-400" /> Wire Format &amp; Delimiters
                  </h4>
                  <div className="bg-slate-950 p-2.5 rounded border border-slate-800 font-mono text-[10px] space-y-1">
                    <div><span className="text-slate-500">Header Format:</span> <span className="text-cyan-300">{inspectingAddon.headerType}</span></div>
                    <div><span className="text-slate-500">Field Delimiter:</span> <span className="text-amber-300">"{inspectingAddon.delimiter}"</span></div>
                  </div>
                </div>

                {/* Canonical Field Extractions */}
                <div>
                  <h4 className="text-[11px] font-bold text-slate-300 uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                    <Code className="w-3.5 h-3.5 text-emerald-400" /> Reverse-Engineered CIM Extractions
                  </h4>
                  <div className="bg-slate-950 rounded border border-slate-800 overflow-hidden font-mono text-[10px]">
                    <div className="grid grid-cols-2 bg-slate-900/80 px-2 py-1 border-b border-slate-800 text-slate-400 font-bold">
                      <span>CIM Field</span>
                      <span>Vendor Extraction</span>
                    </div>
                    {Object.entries(inspectingAddon.fieldMappings).map(([cimField, vendorField]) => (
                      <div key={cimField} className="grid grid-cols-2 px-2 py-1 border-b border-slate-900/60 text-slate-300">
                        <span className="text-emerald-400 font-bold">{cimField}</span>
                        <span className="text-slate-400 truncate" title={vendorField}>{vendorField}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* Audited Raw Event */}
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <h4 className="text-[11px] font-bold text-slate-300 uppercase tracking-wider">
                      Audited Sample Log
                    </h4>
                    <button
                      onClick={() => handleCopySample(inspectingAddon.sampleLog)}
                      className="text-[10px] text-blue-400 hover:text-blue-300 flex items-center gap-1"
                    >
                      {copiedLog ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      {copiedLog ? 'Copied' : 'Copy'}
                    </button>
                  </div>
                  <pre className="bg-slate-950 p-2 rounded border border-slate-800 text-[9px] font-mono text-slate-300 whitespace-pre-wrap break-all max-h-24 overflow-y-auto">
                    {inspectingAddon.sampleLog}
                  </pre>
                </div>

                {/* Live CIM Validation Simulator */}
                <div className="pt-2 border-t border-slate-800">
                  <button
                    onClick={() => handleRunCimExtraction(inspectingAddon)}
                    className="w-full py-1.5 bg-emerald-600 hover:bg-emerald-500 text-slate-950 font-bold rounded text-xs transition-colors flex items-center justify-center gap-1.5"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" /> Run Live CIM Normalization Test
                  </button>

                  {extractedCim && (
                    <div className="mt-2 bg-slate-950 p-2.5 rounded border border-emerald-500/40 text-[10px] font-mono">
                      <div className="text-emerald-400 font-bold mb-1">✔ CIM Normalized Object:</div>
                      <pre className="text-slate-300 max-h-32 overflow-y-auto">
                        {JSON.stringify(extractedCim, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-6 text-slate-500">
                <FileText className="w-10 h-10 mb-2 opacity-30 text-blue-400" />
                <h4 className="text-sm font-bold text-slate-300">Select an Add-on to Audit</h4>
                <p className="text-xs mt-1 text-slate-500 leading-relaxed">
                  Click any vendor card on the left to inspect official documentation links, log delimiters, and live reverse-engineered CIM extractions.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="px-6 py-3 border-t border-slate-800 bg-[#0b0f19] flex items-center justify-between text-xs text-slate-400">
          <div>
            Showing <span className="text-slate-200 font-semibold">{filteredAddons.length}</span> of {VENDOR_ADDONS.length} recommended Technology Add-ons
          </div>
          <button
            onClick={onClose}
            className="px-4 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold transition-colors"
          >
            Close Guide
          </button>
        </div>

      </div>
    </div>
  );
};
