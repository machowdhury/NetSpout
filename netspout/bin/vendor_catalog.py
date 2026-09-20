"""
Splunkbase Vendor Discovery & Official Log Documentation Audit Engine
Provides comprehensive catalog of network, security, and infrastructure Technology Add-ons (TAs).
Audits:
  - Splunkbase App IDs and official documentation URLs
  - Log formats, headers, and key-value delimiters
  - Splunk Common Information Model (CIM) data model mappings
  - Canonical field extractions and test sample events
Author: Mahamudul Chowdhury (mchowdhury@splunk.com)
"""

from typing import Dict, List, Any, Optional

VENDOR_CATALOG: List[Dict[str, Any]] = [
    # =========================================================================
    # 1. NEXT-GENERATION FIREWALLS (NGFW) & PERIMETER SECURITY
    # =========================================================================
    {
        "id": "paloalto-panos",
        "vendor": "Palo Alto Networks",
        "vendor_slug": "palo_alto",
        "category": "Next-Gen Firewall",
        "name": "Palo Alto Networks Add-on for Splunk",
        "splunkbase_id": "2757",
        "splunkbase_url": "https://splunkbase.splunk.com/app/2757",
        "doc_url": "https://docs.paloaltonetworks.com/pan-os/11-0/pan-os-admin/monitoring/use-syslog-for-monitoring/syslog-field-descriptions",
        "sourcetypes": ["pan:traffic", "pan:threat", "pan:system", "pan:config"],
        "header_type": "CSV Position-Delimited with Syslog Prefix",
        "delimiter": ",",
        "timestamp_format": "%Y/%m/%d %H:%M:%S",
        "cim_models": ["Network Traffic", "Intrusion Detection", "Malware", "Change Analysis", "Alerts"],
        "field_mappings": {
            "src": "Field 7 (Source IP)",
            "dest": "Field 8 (Destination IP)",
            "src_port": "Field 25 (Source Port)",
            "dest_port": "Field 26 (Destination Port)",
            "transport": "Field 30 (Protocol)",
            "action": "Field 31 (Action: allow/deny/drop/reset)",
            "bytes_in": "Field 33 (Bytes Received)",
            "bytes_out": "Field 34 (Bytes Sent)",
            "app": "Field 32 (Application Identification)",
            "rule": "Field 12 (Security Rule Name)",
            "vendor_product": "PAN-OS"
        },
        "sample_events": {
            "traffic_allow": "1,2026/09/19 14:00:00,001801000000,TRAFFIC,allow,2304,192.168.10.45,104.16.132.229,0.0.0.0,0.0.0.0,Corporate-Web-Access,trust,untrust,ethernet1/2,ethernet1/1,default,49201,443,0,0,0x0,tcp,allow,1420,8920,0,1,0,ssl,0,849201,0x0,United States,United States,0,24,18,0,0,,iad-edge-fw01,from-policy",
            "threat_ips": "1,2026/09/19 14:02:15,001801000000,THREAT,vulnerability,9901,198.51.100.42,10.20.10.1,0.0.0.0,0.0.0.0,Perimeter-Drop-Exploit,untrust,trust,ethernet1/1,ethernet1/2,default,52410,80,0,0,0x0,tcp,drop,0,0,0,0,0,,(99012) Apache Struts OGNL Injection,web-browsing,informational,server-to-client,4920194,0x0,198.51.100.0-198.51.100.255,United States,0,,0,,,0,,,,0,0,iad-edge-fw01,from-policy",
            "wildfire_malware": "1,2026/09/19 14:05:30,001801000000,THREAT,wildfire,9902,198.51.100.88,10.20.10.45,0.0.0.0,0.0.0.0,Perimeter-Wildfire-Block,untrust,trust,ethernet1/1,ethernet1/2,default,58192,443,0,0,0x0,tcp,reset-both,0,0,0,0,0,,WildFire.Malware.Gen (Trojan-Ransomware-Locky.exe),web-browsing,critical,server-to-client,5928104,0x0,198.51.100.0-198.51.100.255,United States,0,,0,,,0,,,,0,0,iad-edge-fw01,from-policy"
        }
    },
    {
        "id": "fortinet-fortigate",
        "vendor": "Fortinet",
        "vendor_slug": "fortinet",
        "category": "Next-Gen Firewall",
        "name": "Fortinet FortiGate Add-on for Splunk",
        "splunkbase_id": "2800",
        "splunkbase_url": "https://splunkbase.splunk.com/app/2800",
        "doc_url": "https://docs.fortinet.com/document/fortigate/7.4.0/fortios-log-message-reference",
        "sourcetypes": ["fortinet:fortigate:traffic", "fortinet:fortigate:event", "fortinet:fortigate:utm"],
        "header_type": "Key-Value Delimited (key=value)",
        "delimiter": " ",
        "timestamp_format": "date=%Y-%m-%d time=%H:%M:%S",
        "cim_models": ["Network Traffic", "Intrusion Detection", "Network Sessions", "Authentication"],
        "field_mappings": {
            "src": "srcip",
            "dest": "dstip",
            "src_port": "srcport",
            "dest_port": "dstport",
            "transport": "proto",
            "action": "action (accept/deny/close/timeout)",
            "bytes_in": "rcvdbyte",
            "bytes_out": "sentbyte",
            "app": "app",
            "rule": "policyname / policyid",
            "vendor_product": "FortiGate"
        },
        "sample_events": {
            "traffic_deny": 'date=2026-09-19 time=14:10:00 devname="FGT-DC-CORE01" devid="FG200ETK18001048" logid="0000000013" type="traffic" subtype="forward" level="notice" vd="root" srcip=198.51.100.99 srcport=42194 srcintf="port1" dstip=10.20.0.50 dstport=22 dstintf="port2" proto=6 action="deny" policyid=4 policyname="Drop-Inbound-SSH" sessionid=948201 sentbyte=0 rcvdbyte=0 duration=0 app="SSH"',
            "ips_signature": 'date=2026-09-19 time=14:12:30 devname="FGT-DC-CORE01" devid="FG200ETK18001048" logid="0419016384" type="utm" subtype="ips" level="alert" vd="root" srcip=198.51.100.42 srcport=54102 srcintf="port1" dstip=10.20.10.1 dstport=80 dstintf="port2" policyid=1 proto=6 action="dropped" attack="OpenSSL.Heartbleed.Information.Disclosure" attackid=38192 severity="high" msg="OpenSSL TLS heartbeat information disclosure attempt"'
        }
    },
    {
        "id": "cisco-sec-fw",
        "vendor": "Cisco Systems",
        "vendor_slug": "cisco_asa",
        "category": "Next-Gen Firewall",
        "name": "Cisco Security Cloud Add-on / ASA & FTD",
        "splunkbase_id": "6259",
        "splunkbase_url": "https://splunkbase.splunk.com/app/6259",
        "doc_url": "https://www.cisco.com/c/en/us/td/docs/security/asa/syslog/b_syslog.html",
        "sourcetypes": ["cisco:asa", "cisco:sfw:estreamer", "cisco:ftd:syslog"],
        "header_type": "RFC 5424 Syslog Header with %ASA- Tag",
        "delimiter": " ",
        "timestamp_format": "%b %d %H:%M:%S",
        "cim_models": ["Network Traffic", "Intrusion Detection", "Malware", "Authentication"],
        "field_mappings": {
            "src": "src outside:IP",
            "dest": "dst inside:IP",
            "src_port": "src port",
            "dest_port": "dst port",
            "transport": "protocol",
            "action": "Built/Teardown/Deny",
            "duration": "duration H:M:S",
            "vendor_product": "Cisco ASA / FTD"
        },
        "sample_events": {
            "deny_packet": "Sep 19 14:15:00 asa-perimeter01 %ASA-4-106023: Deny tcp src outside:198.51.100.42/51024 dst inside:10.20.1.10/443 by access-group \"OUTSIDE_IN\" [0x0, 0x0]",
            "connection_teardown": "Sep 19 14:15:22 asa-perimeter01 %ASA-6-302014: Teardown TCP connection 948102 for outside:192.168.10.45/49201 to inside:10.20.1.50/80 duration 0:02:14 bytes 49201 TCP FINs"
        }
    },
    {
        "id": "checkpoint-quantum",
        "vendor": "Check Point",
        "vendor_slug": "checkpoint",
        "category": "Next-Gen Firewall",
        "name": "Check Point App & Add-on for Splunk",
        "splunkbase_id": "4293",
        "splunkbase_url": "https://splunkbase.splunk.com/app/4293",
        "doc_url": "https://sc1.checkpoint.com/documents/R81/WebAdminGuides/EN/CP_R81_LoggingAndMonitoring_AdminGuide/Topics-LMG/Log-Fields.htm",
        "sourcetypes": ["checkpoint:traffic", "checkpoint:threat", "checkpoint:audit"],
        "header_type": "Key-Value Delimited (LEEF/OPSEC compatible)",
        "delimiter": ";",
        "timestamp_format": "time=%Y-%m-%d %H:%M:%S",
        "cim_models": ["Network Traffic", "Intrusion Detection", "Change Analysis"],
        "field_mappings": {
            "src": "src",
            "dest": "dst",
            "src_port": "s_port",
            "dest_port": "service",
            "transport": "proto",
            "action": "action (accept/drop/reject)",
            "bytes_in": "client_inbound_bytes",
            "bytes_out": "server_outbound_bytes",
            "vendor_product": "Check Point Quantum"
        },
        "sample_events": {
            "drop_session": "time=2026-09-19 14:18:00;product=VPN-1 & FireWall-1;action=drop;src=198.51.100.103;dst=10.254.1.1;s_port=59124;service=445;proto=tcp;rule=42;rule_name=Block-SMB-Inbound;hostname=cp-quantum-fw01;loguid={0x66f1b0a1,0x0,0x10002};"
        }
    },

    # =========================================================================
    # 2. ROUTING, SWITCHING & CORE TRANSPORT
    # =========================================================================
    {
        "id": "cisco-ios-xe",
        "vendor": "Cisco Systems",
        "vendor_slug": "cisco_ios",
        "category": "Routing & Switching",
        "name": "Cisco Networks Add-on for Splunk",
        "splunkbase_id": "1467",
        "splunkbase_url": "https://splunkbase.splunk.com/app/1467",
        "doc_url": "https://www.cisco.com/c/en/us/td/docs/routers/asr9000/software/system-logging/command/reference/b-system-logging-cr-asr9000.html",
        "sourcetypes": ["cisco:ios", "cisco:ios:syslog", "cisco:ios:mdt:metric"],
        "header_type": "RFC 3164 / 5424 with Facility-Severity-Mnemonic",
        "delimiter": ": ",
        "timestamp_format": "%b %d %H:%M:%S",
        "cim_models": ["Network Sessions", "Network Traffic", "Performance", "Change Analysis"],
        "field_mappings": {
            "host": "syslog host",
            "facility": "%FACILITY",
            "severity": "%SEVERITY",
            "mnemonic": "%MNEMONIC",
            "signature": "Facility-Mnemonic (e.g. BGP-5-ADJCHANGE)",
            "vendor_product": "Cisco IOS-XE / XR"
        },
        "sample_events": {
            "bgp_down": "Sep 19 14:20:00 rtr-core-c8000-01 %BGP-5-ADJCHANGE: neighbor 10.100.1.2 vrf default Down BFD session down",
            "link_flap": "Sep 19 14:20:02 sw-cat9600-core %LINK-3-UPDOWN: Interface HundredGigE1/0/1, changed state to down",
            "bpdu_guard": "Sep 19 14:20:05 sw-cat9300-acc %SPANTREE-2-BLOCK_BPDUGUARD: Received BPDU on port Gi1/0/12 with BPDU Guard enabled. Disabling port."
        }
    },
    {
        "id": "juniper-junos",
        "vendor": "Juniper Networks",
        "vendor_slug": "juniper_junos",
        "category": "Routing & Switching",
        "name": "Splunk Add-on for Juniper",
        "splunkbase_id": "2855",
        "splunkbase_url": "https://splunkbase.splunk.com/app/2855",
        "doc_url": "https://www.juniper.net/documentation/us/en/software/junos/logging-reporting/topics/topic-map/junos-syslog-system-messages-overview.html",
        "sourcetypes": ["juniper:syslog", "juniper:junos"],
        "header_type": "RFC 5424 / BSD Syslog with daemon tag",
        "delimiter": ": ",
        "timestamp_format": "%b %d %H:%M:%S",
        "cim_models": ["Network Sessions", "Network Traffic", "Alerts"],
        "field_mappings": {
            "host": "router hostname",
            "process": "daemon name (rpd, mib2d, chassisd)",
            "action": "state transition",
            "vendor_product": "Junos OS"
        },
        "sample_events": {
            "bgp_neighbor_loss": "Sep 19 14:22:00 ptx10k-pe01 rpd[8492]: BGP_NEIGHBOR_STATE_CHANGED: BGP peer 10.100.1.1 (External AS 65001) changed state from Established to Idle (event RecvHoldTimerExpired)",
            "link_down": "Sep 19 14:22:01 ptx10k-pe01 mib2d[1042]: SNMP_TRAP_LINK_DOWN: ifIndex 531, ifAdminStatus up(1), ifOperStatus down(2), ifName et-0/0/0"
        }
    },
    {
        "id": "arista-eos",
        "vendor": "Arista Networks",
        "vendor_slug": "arista_eos",
        "category": "Cloud Networking & Leaf-Spine",
        "name": "Arista Networks EOS Add-on for Splunk",
        "splunkbase_id": "3350",
        "splunkbase_url": "https://splunkbase.splunk.com/app/3350",
        "doc_url": "https://www.arista.com/en/um-eos/eos-system-messages",
        "sourcetypes": ["arista:eos:syslog", "arista:flow:ipfix", "arista:telemetry:json"],
        "header_type": "EOS Mnemonic Format / JSON Telemetry",
        "delimiter": ": ",
        "timestamp_format": "%b %d %H:%M:%S",
        "cim_models": ["Network Sessions", "Performance", "Network Traffic"],
        "field_mappings": {
            "host": "switch hostname",
            "process": "Ebra / Bgp / Phy",
            "signature": "%FACILITY-SEVERITY-MNEMONIC",
            "vendor_product": "Arista EOS"
        },
        "sample_events": {
            "line_down": "Sep 19 14:24:00 arista-spine01 Ebra: %LINEPROTO-5-UPDOWN: Line protocol on Interface Ethernet1/1, changed state to down",
            "bgp_peer_down": "Sep 19 14:24:02 arista-spine01 Bgp: %BGP-5-ADJCHANGE: peer 10.100.2.2 (AS 65002) state changed from Established to Idle"
        }
    },
    {
        "id": "dell-os10",
        "vendor": "Dell Technologies",
        "vendor_slug": "dell",
        "category": "Data Center & Enterprise Switching",
        "name": "Dell EMC Networking Add-on for Splunk",
        "splunkbase_id": "4820",
        "splunkbase_url": "https://splunkbase.splunk.com/app/4820",
        "doc_url": "https://www.dell.com/support/manuals/en-us/smartfabric-os10-emp-edge/smartfabric-os-user-guide/system-logs",
        "sourcetypes": ["dell:os10", "sonic:syslog"],
        "header_type": "RFC 5424 Syslog with %IFM- / %BGP- tags",
        "delimiter": ": ",
        "timestamp_format": "%Y-%m-%dT%H:%M:%S%z",
        "cim_models": ["Network Sessions", "Network Traffic", "Performance"],
        "field_mappings": {
            "host": "switch hostname",
            "signature": "%MODULE-SEVERITY-EVENT",
            "vendor_product": "Dell SmartFabric OS10"
        },
        "sample_events": {
            "oper_down": "<189>1 2026-09-19T14:26:00.102+00:00 dell-s5248-core01 dn_ifm 581 - - %IFM-5-OPER_STATUS: Interface ethernet 1/1/48 operational status changed to down"
        }
    },
    {
        "id": "nokia-sros",
        "vendor": "Nokia",
        "vendor_slug": "nokia_sros",
        "category": "Carrier IP Routing & Optical Transport",
        "name": "Nokia 7750 SR OS Add-on for Splunk",
        "splunkbase_id": "5120",
        "splunkbase_url": "https://splunkbase.splunk.com/app/5120",
        "doc_url": "https://documentation.nokia.com/html/0_add-h-f/pkg/7750_SR_Syslog_Guide.html",
        "sourcetypes": ["nokia:sros", "nokia:sros:syslog"],
        "header_type": "TiMOS Event Log with Major/Minor Classification",
        "delimiter": " - ",
        "timestamp_format": "%Y/%m/%d %H:%M:%S.%f",
        "cim_models": ["Network Sessions", "Alerts", "Performance"],
        "field_mappings": {
            "host": "carrier router name",
            "signature": "Event ID & Classification",
            "vendor_product": "Nokia 7750 SR OS"
        },
        "sample_events": {
            "optical_los": "1 2026/09/19 14:28:00.412 UTC nokia-7750-sr12-core01 SYSTEM-WARNING-SYSTEM-1002 - [port 1/1/c1] Optical carrier Loss of Signal (LOS) detected on DWDM transceiver. Bit Error Rate (BER) exceeded 1.0E-4"
        }
    },

    # =========================================================================
    # 3. CAMPUS LAN, WIRELESS & CONTROLLERS
    # =========================================================================
    {
        "id": "cisco-catalyst",
        "vendor": "Cisco Systems",
        "vendor_slug": "cisco_catalyst",
        "category": "Campus LAN & Wireless",
        "name": "Splunk Add-on for Cisco Catalyst Center (DNA-C)",
        "splunkbase_id": "5580",
        "splunkbase_url": "https://splunkbase.splunk.com/app/5580",
        "doc_url": "https://developer.cisco.com/docs/dna-center/#!cisco-dna-center-platform-overview",
        "sourcetypes": ["cisco:catalyst:networkhealth", "cisco:catalyst:clienthealth", "cisco:catalyst:rogue:threat_details", "cisco:catalyst:issue"],
        "header_type": "Structured Key-Value / JSON Webhook",
        "delimiter": " ",
        "timestamp_format": "timestamp=\"%Y-%m-%dT%H:%M:%S.%fZ\"",
        "cim_models": ["Network Sessions", "Network Traffic", "Alerts", "Inventory"],
        "field_mappings": {
            "device_name": "host / device",
            "overall_health": "health_score",
            "rogue_bssid": "rogue_mac",
            "vendor_product": "Cisco Catalyst Center"
        },
        "sample_events": {
            "rogue_ap_threat": 'cisco:catalyst:rogue:threat_details ap_name="AP-Floor3-West" rogue_bssid="70:69:79:4c:11:02" ssid="Corporate-Guest-EvilTwin" rogue_type="Unclassified" classification="Threat" state="Alert" signal_rssi=-68 containment_status="pending"',
            "client_health": 'cisco:catalyst:clienthealth timestamp="2026-09-19T14:30:00.000Z" controller="Catalyst-9800-WLC" client_mac="70:69:79:4c:11:02" ap_name="Catalyst-9130AX-AP" client_ip="10.40.1.105" ssid="Corp-Secure-WPA3" health_score=98 rssi=-58 snr=38 channel=36 throughput_mbps=482.5 status=HEALTHY'
        }
    },
    {
        "id": "cisco-meraki",
        "vendor": "Cisco Systems",
        "vendor_slug": "meraki",
        "category": "Cloud Networking",
        "name": "Splunk Add-on for Cisco Meraki",
        "splunkbase_id": "5619",
        "splunkbase_url": "https://splunkbase.splunk.com/app/5619",
        "doc_url": "https://documentation.meraki.com/General_Administration/Monitoring_and_Reporting/Syslog_Event_Types_and_Log_Samples",
        "sourcetypes": ["meraki:accesspoints", "meraki:airmarshal", "meraki:switchports", "meraki:devices"],
        "header_type": "JSON Webhook Payload / RFC 5424 Syslog",
        "delimiter": " ",
        "timestamp_format": "timestamp=\"%Y-%m-%dT%H:%M:%S.%fZ\"",
        "cim_models": ["Network Traffic", "Network Sessions", "Alerts"],
        "field_mappings": {
            "device_serial": "serial",
            "client_count": "clients",
            "vendor_product": "Cisco Meraki"
        },
        "sample_events": {
            "ap_telemetry": 'meraki:accesspoints timestamp="2026-09-19T14:32:00.000Z" network_id="N_88192031" device_serial="Q2KD-99A1-XZ34" name="Meraki-MR56-AP" client_count=34 channel_utilization_2_4ghz=18% channel_utilization_5ghz=42% tx_power_dbm=17 rx_packets=1289004 tx_packets=2490182 mesh_role="root" status="online"'
        }
    },

    # =========================================================================
    # 4. IDENTITY, ACCESS CONTROL & ZERO TRUST
    # =========================================================================
    {
        "id": "cisco-ise",
        "vendor": "Cisco Systems",
        "vendor_slug": "cisco_ise",
        "category": "Identity & Access Control",
        "name": "Splunk Add-on for Cisco ISE",
        "splunkbase_id": "1924",
        "splunkbase_url": "https://splunkbase.splunk.com/app/1924",
        "doc_url": "https://www.cisco.com/c/en/us/td/docs/security/ise/3-3/admin_guide/b_ise_admin_3_3/b_ise_admin_33_logging.html",
        "sourcetypes": [
            "cisco:ise:byod:provisioning",
            "cisco:ise:nac:8021x",
            "cisco:ise:trustsec",
            "cisco:ise:tacacs",
            "cisco:ise:guest"
        ],
        "header_type": "CISE_ Mnemonic Key-Value Delimited",
        "delimiter": " ",
        "timestamp_format": "%Y-%m-%d %H:%M:%S.%f",
        "cim_models": ["Authentication", "Change Analysis", "Network Sessions"],
        "field_mappings": {
            "user": "User-Name",
            "src_mac": "Calling-Station-Id",
            "dest": "NAS-IP-Address",
            "action": "Response (Passed/Failed)",
            "app": "EapAuthentication",
            "sgt": "cisco-av-pair=security-group-tag",
            "vendor_product": "Cisco ISE"
        },
        "sample_events": {
            "passed_auth": "CISE_Passed_Authentications 0001847291 1 0 2026-09-19 14:35:00.124 +00:00 0029481921 5200 NOTICE Passed-Authentication: Authentication succeeded, User-Name=alex.turner@enterprise.corp, Calling-Station-Id=70-69-79-4C-11-02, NAS-IP-Address=10.254.3.1, NAS-Port=GigabitEthernet1/0/12, EapAuthentication=EAP-TLS, cisco-av-pair=security-group-tag=0004-TrustSec-Employee, SelectedAuthorizationProfiles=PermitAccess",
            "tacacs_admin": "CISE_TACACS_Accounting 0001847399 1 0 2026-09-19 14:36:12.891 +00:00 0029482094 3300 NOTICE TACACS-Accounting: Command authorization accounting, User-Name=netadmin_root, NAS-IP-Address=10.254.1.1, Port=vty0, Cmd=configure terminal <args: >, CmdArg=interface HundredGigE1/0/1 <args: shutdown>, Privilege-Level=15, Response=Success"
        }
    },
    {
        "id": "cisco-duo",
        "vendor": "Cisco Duo Security",
        "vendor_slug": "cisco_duo",
        "category": "MFA & Zero Trust",
        "name": "Duo Security Splunk Add-on",
        "splunkbase_id": "3245",
        "splunkbase_url": "https://splunkbase.splunk.com/app/3245",
        "doc_url": "https://duo.com/docs/splunk",
        "sourcetypes": [
            "cisco:duo:push:prompt",
            "cisco:duo:endpoint:health",
            "cisco:duo:sso:saml",
            "cisco:duo:zerotrust:policy",
            "cisco:duo:vpn:remote"
        ],
        "header_type": "JSON Key-Value Delimited",
        "delimiter": " ",
        "timestamp_format": "timestamp=\"%Y-%m-%dT%H:%M:%S.%fZ\"",
        "cim_models": ["Authentication", "Change Analysis", "Alerts"],
        "field_mappings": {
            "user": "user",
            "action": "result (SUCCESS/FAILURE/FRAUD)",
            "src": "ip_address",
            "app": "integration",
            "factor": "factor (duo_push/passcode/touchid)",
            "vendor_product": "Cisco Duo"
        },
        "sample_events": {
            "push_auth": 'timestamp="2026-09-19T14:40:00.124Z" host="cisco-duo-auth01" event_type="authentication" user="marcus.vance@enterprise.corp" factor="duo_push" result="SUCCESS" ip_address="198.51.100.88" integration="Cisco ASA AnyConnect SSL-VPN" device="iPhone 15 Pro iOS 17.4" posture_state="COMPLIANT" location="Austin, TX, US"',
            "posture_check": 'timestamp="2026-09-19T14:40:02.891Z" host="cisco-duo-auth01" event_type="endpoint_health" user="marcus.vance@enterprise.corp" tpm_version="2.0" disk_encryption="FileVault2_Enabled" biometrics="TouchID_Verified" firewall_active=true result="COMPLIANT"'
        }
    },

    # =========================================================================
    # 5. CLOUD SECURITY, SASE & PROXIES
    # =========================================================================
    {
        "id": "zscaler-zia",
        "vendor": "Zscaler",
        "vendor_slug": "zscaler",
        "category": "Cloud SASE & Web Proxy",
        "name": "Zscaler App for Splunk",
        "splunkbase_id": "5648",
        "splunkbase_url": "https://splunkbase.splunk.com/app/5648",
        "doc_url": "https://help.zscaler.com/zia/nss-feed-output-format-web-logs",
        "sourcetypes": ["zscaler:zia", "zscaler:zpa", "zscaler:lss"],
        "header_type": "JSON / Delimited Nanosecond Event",
        "delimiter": " ",
        "timestamp_format": "datetime=\"%Y-%m-%d %H:%M:%S\"",
        "cim_models": ["Web", "Network Traffic", "Intrusion Detection"],
        "field_mappings": {
            "src": "ClientIP",
            "user": "user",
            "url": "url",
            "action": "action (Allow/Block)",
            "app": "app",
            "riskscore": "riskscore",
            "vendor_product": "Zscaler ZIA"
        },
        "sample_events": {
            "url_block": '{"datetime":"2026-09-19 14:45:00","user":"eng-dev@corp.internal","app":"ChatGPT-Enterprise","action":"Block","proto":"HTTPS","url":"https://pastebin.com/raw/d849201","threatname":"T1567 Exfiltration Over Web Service","riskscore":"92","egress_dc":"iad-zscaler"}'
        }
    },

    # =========================================================================
    # 6. LOAD BALANCERS & APPLICATION DELIVERY
    # =========================================================================
    {
        "id": "f5-bigip",
        "vendor": "F5 Networks",
        "vendor_slug": "f5_bigip",
        "category": "Application Delivery Controller (ADC)",
        "name": "F5 Networks Add-on for Splunk",
        "splunkbase_id": "2680",
        "splunkbase_url": "https://splunkbase.splunk.com/app/2680",
        "doc_url": "https://techdocs.f5.com/en-us/bigip-16-0-0/big-ip-systems-syslog-messages-guide.html",
        "sourcetypes": ["f5:bigip:ltm", "f5:bigip:syslog", "f5:bigip:asm:syslog"],
        "header_type": "Syslog Format with tmm/mcpd process tag",
        "delimiter": ": ",
        "timestamp_format": "%b %d %H:%M:%S",
        "cim_models": ["Network Traffic", "Web", "Intrusion Detection"],
        "field_mappings": {
            "host": "f5 hostname",
            "pool": "pool name",
            "member": "node IP:port",
            "action": "Pool member state / failover",
            "vendor_product": "F5 BIG-IP LTM"
        },
        "sample_events": {
            "pool_member_down": "Sep 19 14:50:00 bigip01.corp.internal notice mcpd[8192]: 01070638:5: Pool /Common/pool_prod_web member /Common/node_web02:80 monitor status down. [ was up for 142hrs ]",
            "pool_routing": "Sep 19 14:50:05 bigip01.corp.internal info tmm[1002]: Rule /Common/irule_http_route <HTTP_REQUEST>: Client 192.168.1.100:49201 routed to active pool member 10.0.1.11:80"
        }
    },

    # =========================================================================
    # 7. SC4SNMP TELEMETRY & OPENCONFIG
    # =========================================================================
    {
        "id": "sc4snmp-core",
        "vendor": "Splunk Connect for SNMP",
        "vendor_slug": "sc4snmp",
        "category": "SNMP Polling & Trap Ingestion",
        "name": "Splunk Connect for SNMP (SC4SNMP)",
        "splunkbase_id": "SC4SNMP",
        "splunkbase_url": "https://splunk.github.io/splunk-connect-for-snmp/",
        "doc_url": "https://splunk.github.io/splunk-connect-for-snmp/main/profiles/cisco/",
        "sourcetypes": ["sc4snmp:metric", "sc4snmp:event"],
        "header_type": "HEC Metric & Event JSON (Splunk Standard)",
        "delimiter": "json",
        "timestamp_format": "epoch",
        "cim_models": ["Performance", "Alerts", "Inventory"],
        "field_mappings": {
            "metric_name": "metric_name:<oid_symbol>",
            "_value": "numerical metric measurement",
            "host": "managed network node",
            "vendor_product": "SC4SNMP"
        },
        "sample_events": {
            "metric_octets": '{"time":1789854000.0,"event":"metric","source":"sc4snmp","sourcetype":"sc4snmp:metric","host":"cat9600-core01.corp.internal","index":"cisco_mdt_metrics","fields":{"metric_name:ifInOctets":94820140.0,"metric_name:ifOutOctets":128920194.0,"metric_name:ifOperStatus":1.0,"_value":94820140.0,"ifIndex":"1","ifDescr":"HundredGigE1/0/1","device":"cat9600-core01","vendor":"cisco"}}',
            "trap_event": '{"time":1789854002.0,"event":"snmp_trap","source":"sc4snmp:trap","sourcetype":"sc4snmp:event","host":"ptx10k-pe01.corp.internal","index":"idx_network_ops","fields":{"snmp_trap_oid":"1.3.6.1.6.3.1.1.5.3","snmp_trap_name":"linkDown","severity":"critical","varbinds":{"ifIndex":531,"ifDescr":"et-0/0/0","ifOperStatus":2},"device":"ptx10k-pe01","vendor":"juniper"}}'
        }
    }
]

def get_vendor_by_id(addon_id: str) -> Optional[Dict[str, Any]]:
    for a in VENDOR_CATALOG:
        if a["id"] == addon_id:
            return a
    return None

def get_vendor_by_slug(slug: str) -> Optional[Dict[str, Any]]:
    for a in VENDOR_CATALOG:
        if a.get("vendor_slug") == slug:
            return a
    return None

def list_all_vendors() -> List[Dict[str, Any]]:
    return VENDOR_CATALOG
