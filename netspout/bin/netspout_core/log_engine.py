"""
Dynamic Splunk Log Engine
Generates authentic raw Splunk Key-Value (KV) format logs for:
- Cisco ASA Firewall (%ASA-4-106023)
- Palo Alto Networks PAN-OS (Traffic/Threat CSV-KV)
- Nginx Web Server (Combined access with KV tags)
- F5 BIG-IP Local Traffic Manager (LTM pool routing)
- PostgreSQL Database Server (Audit statement logs)
- Cisco IOS / Arista EOS Routers & Switches
Every log entry adheres to Splunk CIM Network Traffic and Security Data Models.
"""

import time
import random
import json
from datetime import datetime
from typing import Dict, Any, Optional
try:
    from netspout_core.models import LogEntry, Node, NodeType
except ImportError:
    try:
        from app.models import LogEntry, Node, NodeType
    except ImportError:
        from models import LogEntry, Node, NodeType


class SplunkLogEngine:

    @staticmethod
    def current_timestamp_iso() -> str:
        return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3] + " UTC"

    @staticmethod
    def current_timestamp_syslog() -> str:
        return datetime.utcnow().strftime("%b %d %H:%M:%S")

    @staticmethod
    def format_cisco_asa_log(
        device: Node,
        src_ip: str,
        dest_ip: str,
        src_port: int,
        dest_port: int,
        proto: str,
        action: str,
        signature: str,
        status: str,
        duration_ms: int = 12
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        now_syslog = SplunkLogEngine.current_timestamp_syslog()
        dev_id = device.name or device.id
        
        asa_action = "Deny" if action in ("blocked", "dropped") else "Permit"
        code = "%ASA-4-106023" if asa_action == "Deny" else "%ASA-6-302013"
        
        # Raw Cisco ASA Syslog with embedded Splunk KV attributes
        raw = (
            f"{now_syslog} {dev_id} {code}: {asa_action} {proto.lower()} src outside:{src_ip}/{src_port} "
            f"dst inside:{dest_ip}/{dest_port} by access-group \"OUTSIDE_IN\" [0x0, 0x0] "
            f"timestamp=\"{now_ts}\" device_id=\"{dev_id}\" src_ip={src_ip} dest_ip={dest_ip} "
            f"src_port={src_port} dest_port={dest_port} protocol={proto} duration={duration_ms}ms "
            f"action={action} signature=\"{signature}\" status={status}"
        )

        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=src_ip,
            dest_ip=dest_ip,
            protocol=proto,
            duration=f"{duration_ms}ms",
            action=action,
            signature=signature,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="cisco_asa"
        )

    @staticmethod
    def format_palo_alto_log(
        device: Node,
        src_ip: str,
        dest_ip: str,
        src_port: int,
        dest_port: int,
        proto: str,
        action: str,
        signature: str,
        status: str,
        duration_ms: int = 15
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        dev_id = device.name or device.id
        pan_action = "drop" if action in ("blocked", "dropped") else "allow"
        rule_name = "Perimeter-Block-Threat" if action in ("blocked", "dropped") else "Perimeter-Web-Access"

        raw = (
            f"1,{datetime.utcnow().strftime('%Y/%m/%d %H:%M:%S')},001801000000,TRAFFIC,{pan_action},2304,"
            f"{src_ip},{dest_ip},0.0.0.0,0.0.0.0,{rule_name},untrust,trust,ethernet1/1,ethernet1/2,default,"
            f"{src_port},{dest_port},0,0,0x0,{proto.lower()},{pan_action},128,128,0,1,0,any,0,12345,0x0,"
            f"timestamp=\"{now_ts}\" device_id=\"{dev_id}\" src_ip={src_ip} dest_ip={dest_ip} "
            f"protocol={proto} duration={duration_ms}ms action={action} signature=\"{signature}\" status={status}"
        )

        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=src_ip,
            dest_ip=dest_ip,
            protocol=proto,
            duration=f"{duration_ms}ms",
            action=action,
            signature=signature,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="palo_alto"
        )

    @staticmethod
    def format_nginx_web_log(
        device: Node,
        src_ip: str,
        dest_ip: str,
        method: str,
        uri: str,
        http_code: int,
        bytes_sent: int,
        action: str,
        signature: str,
        status: str,
        duration_ms: int = 24
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        dev_id = device.name or device.id
        nginx_time = datetime.utcnow().strftime("%d/%b/%Y:%H:%M:%S +0000")

        # Nginx Combined Access Log with Splunk KV trail
        raw = (
            f"{src_ip} - - [{nginx_time}] \"{method} {uri} HTTP/1.1\" {http_code} {bytes_sent} "
            f"\"-\" \"Mozilla/5.0 (Security-Operations-Center)\" "
            f"timestamp=\"{now_ts}\" device_id=\"{dev_id}\" src_ip={src_ip} dest_ip={dest_ip} "
            f"protocol=HTTP http_method={method} http_status={http_code} uri=\"{uri}\" "
            f"duration={duration_ms}ms action={action} signature=\"{signature}\" status={status}"
        )

        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=src_ip,
            dest_ip=dest_ip,
            protocol="HTTP",
            duration=f"{duration_ms}ms",
            action=action,
            signature=signature,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="nginx"
        )

    @staticmethod
    def format_f5_lb_log(
        device: Node,
        src_ip: str,
        dest_ip: str,
        backend_ip: str,
        backend_port: int,
        action: str,
        signature: str,
        status: str,
        duration_ms: int = 5
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        now_syslog = SplunkLogEngine.current_timestamp_syslog()
        dev_id = device.name or device.id

        raw = (
            f"{now_syslog} {dev_id} local/tmm[1104]: 01070727:3: Pool /Common/web_farm member /Common/{backend_ip}:{backend_port} "
            f"connection established client={src_ip} vip={dest_ip}:80 target={backend_ip}:{backend_port} "
            f"timestamp=\"{now_ts}\" device_id=\"{dev_id}\" src_ip={src_ip} dest_ip={dest_ip} "
            f"backend_server={backend_ip}:{backend_port} protocol=TCP duration={duration_ms}ms "
            f"action={action} signature=\"{signature}\" status={status}"
        )

        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=src_ip,
            dest_ip=dest_ip,
            protocol="TCP",
            duration=f"{duration_ms}ms",
            action=action,
            signature=signature,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="f5_bigip"
        )

    @staticmethod
    def format_postgres_db_log(
        device: Node,
        src_ip: str,
        dest_ip: str,
        sql_statement: str,
        action: str,
        signature: str,
        status: str,
        duration_ms: int = 48
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        now_syslog = SplunkLogEngine.current_timestamp_syslog()
        dev_id = device.name or device.id

        raw = (
            f"{now_syslog} {dev_id} postgres[1482]: [3-1] user=app_service db=prod_finance host={src_ip} "
            f"LOG: statement: {sql_statement} "
            f"timestamp=\"{now_ts}\" device_id=\"{dev_id}\" src_ip={src_ip} dest_ip={dest_ip} "
            f"database=\"prod_finance\" protocol=TCP duration={duration_ms}ms "
            f"action={action} signature=\"{signature}\" status={status}"
        )

        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=src_ip,
            dest_ip=dest_ip,
            protocol="TCP",
            duration=f"{duration_ms}ms",
            action=action,
            signature=signature,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="postgresql"
        )

    @staticmethod
    def format_router_switch_log(
        device: Node,
        src_ip: str,
        dest_ip: str,
        interface: str,
        action: str,
        signature: str,
        status: str,
        duration_ms: int = 2
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        now_syslog = SplunkLogEngine.current_timestamp_syslog()
        dev_id = device.name or device.id
        proto = "IP/TCP"

        raw = (
            f"{now_syslog} {dev_id} %ROUTING-5-FLOW: Ingress interface {interface} forward packet "
            f"from {src_ip} to {dest_ip} via BGP-RIB "
            f"timestamp=\"{now_ts}\" device_id=\"{dev_id}\" src_ip={src_ip} dest_ip={dest_ip} "
            f"interface={interface} protocol={proto} duration={duration_ms}ms "
            f"action={action} signature=\"{signature}\" status={status}"
        )

        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=src_ip,
            dest_ip=dest_ip,
            protocol="IP",
            duration=f"{duration_ms}ms",
            action=action,
            signature=signature,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="cisco_ios"
        )

    # =========================================================================
    # SPECIALIZED LOG GENERATORS FOR CORRELATED SCENARIOS (MODES A & B)
    # =========================================================================

    @staticmethod
    def format_cisco_catalyst_rogue_log(
        device: Node,
        rogue_mac: str,
        bssid: str,
        ssid: str,
        channel: int,
        rssi: int,
        action: str,
        status: str,
        signature: str = "Rogue AP Detected: Unsanctioned BSSID on Campus Perimeter"
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        now_syslog = SplunkLogEngine.current_timestamp_syslog()
        dev_id = device.name or device.id
        raw = (
            f"{now_syslog} {dev_id} %CATALYST_SEC-4-ROGUE_ALERT: Rogue AP detected on campus RF matrix. "
            f"rogue_mac={rogue_mac} bssid={bssid} ssid=\"{ssid}\" channel={channel} rssi={rssi}dBm "
            f"timestamp=\"{now_ts}\" device_id=\"{dev_id}\" src_ip=0.0.0.0 dest_ip=255.255.255.255 "
            f"protocol=802.11 duration=0ms action={action} signature=\"{signature}\" status={status}"
        )
        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip="0.0.0.0",
            dest_ip="255.255.255.255",
            protocol="802.11",
            duration="0ms",
            action=action,
            signature=signature,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="cisco_catalyst",
            sourcetype="cisco:catalyst:rogue:threat_details"
        )

    @staticmethod
    def format_cisco_ise_log(
        device: Node,
        client_mac: str,
        client_ip: str,
        user: str,
        auth_status: str,
        profile: str,
        action: str,
        status: str,
        signature: str = "802.1X Quarantine Profile Applied via Cisco ISE"
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        now_syslog = SplunkLogEngine.current_timestamp_syslog()
        dev_id = device.name or device.id
        raw = (
            f"{now_syslog} {dev_id} CISE_Failed_Authentications 0000042812 1 0 {now_ts} "
            f"Event-Timestamp={int(time.time())}, User-Name={user}, Calling-Station-Id={client_mac}, "
            f"Framed-IP-Address={client_ip}, Audit-Session-Id=0A0101010000005C61, "
            f"Failure-Reason=Unauthorized_Supplicant, Authorization-Profile={profile}, "
            f"timestamp=\"{now_ts}\" device_id=\"{dev_id}\" src_ip={client_ip} dest_ip=10.0.0.1 "
            f"protocol=RADIUS duration=14ms action={action} signature=\"{signature}\" status={status}"
        )
        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=client_ip,
            dest_ip="10.0.0.1",
            protocol="RADIUS",
            duration="14ms",
            action=action,
            signature=signature,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="cisco_ise",
            sourcetype="cisco:ise:syslog"
        )

    @staticmethod
    def format_cisco_mac_flap_log(
        device: Node,
        mac: str,
        vlan: int,
        port1: str,
        port2: str,
        action: str,
        status: str,
        signature: str = "%SW_MATM-4-MACFLAP_NOTIF: L2 Loop / Rogue Device Flapping"
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        now_syslog = SplunkLogEngine.current_timestamp_syslog()
        dev_id = device.name or device.id
        raw = (
            f"{now_syslog} {dev_id} %SW_MATM-4-MACFLAP_NOTIF: Host {mac} in vlan {vlan} "
            f"is flapping between port {port1} and port {port2} "
            f"timestamp=\"{now_ts}\" device_id=\"{dev_id}\" src_ip=10.0.1.1 dest_ip=10.0.1.254 "
            f"protocol=ETHERNET duration=1ms action={action} signature=\"{signature}\" status={status}"
        )
        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip="10.0.1.1",
            dest_ip="10.0.1.254",
            protocol="ETHERNET",
            duration="1ms",
            action=action,
            signature=signature,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="cisco_ios",
            sourcetype="cisco:ios:syslog"
        )

    @staticmethod
    def format_cisco_sdwan_linkhealth_log(
        device: Node,
        remote_system_ip: str,
        latency_ms: float,
        jitter_ms: float,
        loss_pct: float,
        sla_status: str,
        action: str,
        status: str,
        signature: str = "SD-WAN Tunnel SLA Threshold Violated"
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        now_syslog = SplunkLogEngine.current_timestamp_syslog()
        dev_id = device.name or device.id
        raw = (
            f"{now_syslog} {dev_id} SDWAN-BFD-SLA[512]: local_color=biz-internet remote_color=mpls "
            f"remote_system_ip={remote_system_ip} latency={latency_ms:.1f}ms jitter={jitter_ms:.1f}ms "
            f"loss={loss_pct:.1f}% sla_class=VoIP_Gold sla_compliance={sla_status} "
            f"timestamp=\"{now_ts}\" device_id=\"{dev_id}\" src_ip={device.ip_address} "
            f"dest_ip={remote_system_ip} protocol=BFD duration=8ms action={action} "
            f"signature=\"{signature}\" status={status}"
        )
        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=device.ip_address,
            dest_ip=remote_system_ip,
            protocol="BFD",
            duration="8ms",
            action=action,
            signature=signature,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="cisco_sdwan",
            sourcetype="cisco:sdwan:linkhealth"
        )

    @staticmethod
    def format_cisco_sdwan_bgp_log(
        device: Node,
        neighbor_ip: str,
        state_change: str,
        action: str,
        status: str,
        signature: str = "BGP Neighbor State Flap & SD-WAN Route Failover"
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        now_syslog = SplunkLogEngine.current_timestamp_syslog()
        dev_id = device.name or device.id
        raw = (
            f"{now_syslog} {dev_id} %BGP-5-ADJCHANGE: neighbor {neighbor_ip} vpn 10 {state_change} "
            f"BFD session down; failover to secondary LTE/Broadband transport engaged "
            f"timestamp=\"{now_ts}\" device_id=\"{dev_id}\" src_ip={device.ip_address} "
            f"dest_ip={neighbor_ip} protocol=BGP duration=3ms action={action} "
            f"signature=\"{signature}\" status={status}"
        )
        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=device.ip_address,
            dest_ip=neighbor_ip,
            protocol="BGP",
            duration="3ms",
            action=action,
            signature=signature,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="cisco_sdwan",
            sourcetype="cisco:sdwan:BGP-5-ADJCHANGE"
        )

    @staticmethod
    def format_cisco_thousandeyes_log(
        device: Node,
        target_url: str,
        latency_ms: float,
        packet_loss_pct: float,
        http_code: int,
        action: str,
        status: str,
        signature: str = "ThousandEyes Synthetic HTTP Probe Degradation"
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        dev_id = device.name or device.id
        raw = (
            f"{{\"testId\": 98412, \"testName\": \"Enterprise-SaaS-Synthetic\", \"target\": \"{target_url}\", "
            f"\"metrics\": {{\"avgLatencyMs\": {latency_ms:.1f}, \"packetLossPct\": {packet_loss_pct:.1f}, \"httpCode\": {http_code}, \"dnsTime\": 14.2, \"tcpConnectTime\": 45.8}}, "
            f"\"timestamp\": \"{now_ts}\", \"device_id\": \"{dev_id}\", \"src_ip\": \"{device.ip_address}\", "
            f"\"dest_ip\": \"198.51.100.200\", \"protocol\": \"HTTPS\", \"duration\": \"{int(latency_ms)}ms\", "
            f"\"action\": \"{action}\", \"signature\": \"{signature}\", \"status\": \"{status}\"}}"
        )
        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=device.ip_address,
            dest_ip="198.51.100.200",
            protocol="HTTPS",
            duration=f"{int(latency_ms)}ms",
            action=action,
            signature=signature,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="cisco_thousandeyes",
            sourcetype="cisco:thousandeyes:metric"
        )

    @staticmethod
    def format_cisco_aci_nexus_log(
        device: Node,
        asic_interface: str,
        buffer_util_pct: float,
        dropped_packets: int,
        fabric_health: int,
        action: str,
        status: str,
        signature: str = "Nexus 9K Ingress Microburst Queue Saturation"
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        now_syslog = SplunkLogEngine.current_timestamp_syslog()
        dev_id = device.name or device.id
        raw = (
            f"{now_syslog} {dev_id} %BUFFER_MGR-3-QUEUE_DROP: Ingress queue threshold exceeded on {asic_interface}. "
            f"buffer_util={buffer_util_pct:.1f}% dropped_packets={dropped_packets} fabricHealthScore={fabric_health} "
            f"timestamp=\"{now_ts}\" device_id=\"{dev_id}\" src_ip={device.ip_address} "
            f"dest_ip=10.255.0.1 protocol=DC-ETHERNET duration=1ms action={action} "
            f"signature=\"{signature}\" status={status}"
        )
        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=device.ip_address,
            dest_ip="10.255.0.1",
            protocol="DC-ETHERNET",
            duration="1ms",
            action=action,
            signature=signature,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="cisco_nexus",
            sourcetype="cisco:dc:nexus9k:syslog"
        )

    @staticmethod
    def format_cisco_mdt_log(
        device: Node,
        sensor_path: str,
        queue_depth_bytes: int,
        peak_buffer_pct: float,
        action: str,
        status: str,
        signature: str = "Cisco IOS-XE MDT Streaming Telemetry Ingress Incast"
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        dev_id = device.name or device.id
        raw = (
            f"{{\"node_id_str\": \"{dev_id}\", \"subscription_id\": 108, \"sensor_path\": \"{sensor_path}\", "
            f"\"telemetry_timestamp\": {int(time.time() * 1000)}, \"data\": {{\"queue_depth_bytes\": {queue_depth_bytes}, "
            f"\"buffer_utilization_pct\": {peak_buffer_pct:.1f}, \"egress_drops\": 1420}}, "
            f"\"timestamp\": \"{now_ts}\", \"device_id\": \"{dev_id}\", \"src_ip\": \"{device.ip_address}\", "
            f"\"dest_ip\": \"10.255.1.1\", \"protocol\": \"gNMI/MDT\", \"duration\": \"2ms\", "
            f"\"action\": \"{action}\", \"signature\": \"{signature}\", \"status\": \"{status}\"}}"
        )
        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=device.ip_address,
            dest_ip="10.255.1.1",
            protocol="gNMI/MDT",
            duration="2ms",
            action=action,
            signature=signature,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="cisco_mdt",
            sourcetype="cisco:ios:mdt"
        )

    @staticmethod
    def format_meraki_alert_log(
        device: Node,
        client_mac: str,
        alert_type: str,
        channel: int,
        action: str,
        status: str,
        signature: str = "Meraki Wireless Intrusion / Rogue Probe Alert"
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        dev_id = device.name or device.id
        raw = (
            f"{{\"version\": \"0.1\", \"sharedSecret\": \"meraki-secret\", \"alertId\": \"19842\", "
            f"\"alertType\": \"{alert_type}\", \"occurredAt\": \"{now_ts}\", \"deviceSerial\": \"Q2KD-9821-XMR1\", "
            f"\"deviceName\": \"{dev_id}\", \"clientMac\": \"{client_mac}\", \"channel\": {channel}, "
            f"\"timestamp\": \"{now_ts}\", \"device_id\": \"{dev_id}\", \"src_ip\": \"10.128.0.55\", "
            f"\"dest_ip\": \"10.128.0.1\", \"protocol\": \"802.11\", \"duration\": \"1ms\", "
            f"\"action\": \"{action}\", \"signature\": \"{signature}\", \"status\": \"{status}\"}}"
        )
        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip="10.128.0.55",
            dest_ip="10.128.0.1",
            protocol="802.11",
            duration="1ms",
            action=action,
            signature=signature,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="meraki",
            sourcetype="meraki:assurancealerts"
        )

    @staticmethod
    def format_palo_alto_threat_log(
        device: Node,
        src_ip: str,
        dest_ip: str,
        src_port: int,
        dest_port: int,
        threat_name: str,
        threat_id: int,
        action: str,
        status: str,
        duration_ms: int = 4
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        dev_id = device.name or device.id
        pan_action = "drop" if action in ("blocked", "dropped") else "alert"
        severity = "high" if action in ("blocked", "dropped") else "critical"
        raw = (
            f"1,{datetime.utcnow().strftime('%Y/%m/%d %H:%M:%S')},001801000000,THREAT,vulnerability,2304,"
            f"{src_ip},{dest_ip},0.0.0.0,0.0.0.0,Perimeter-Inspection,trust,untrust,ethernet1/1,ethernet1/2,default,"
            f"{src_port},{dest_port},0,0,0x0,tcp,{pan_action},\"({threat_id}) {threat_name}\",any,{severity},"
            f"client-to-server,12345,0x0,timestamp=\"{now_ts}\" device_id=\"{dev_id}\" src_ip={src_ip} "
            f"dest_ip={dest_ip} protocol=TCP duration={duration_ms}ms action={action} "
            f"signature=\"{threat_name}\" status={status}"
        )
        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=src_ip,
            dest_ip=dest_ip,
            protocol="TCP",
            duration=f"{duration_ms}ms",
            action=action,
            signature=threat_name,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="palo_alto",
            sourcetype="pan:threat"
        )

    @staticmethod
    def format_zscaler_zia_log(
        device: Node,
        client_ip: str,
        dest_url: str,
        latency_ms: int,
        action: str,
        status: str,
        signature: str = "SASE Zscaler Cloud Edge Inspection Latency"
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        dev_id = device.name or device.id
        zia_status = "BLOCK" if action in ("blocked", "dropped") else "ALLOW"
        raw = (
            f"datetime=\"{now_ts}\" device_id=\"{dev_id}\" user=\"j.doe@enterprise.corp\" department=\"Engineering\" "
            f"client_ip={client_ip} server_ip=104.16.132.229 url=\"{dest_url}\" req_method=GET proto=HTTPS "
            f"resp_code=200 total_duration_ms={latency_ms} tls_version=TLSv1.3 action={action} "
            f"zia_rule=\"Cloud-App-Inspection\" signature=\"{signature}\" status={status}"
        )
        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=client_ip,
            dest_ip="104.16.132.229",
            protocol="HTTPS",
            duration=f"{latency_ms}ms",
            action=action,
            signature=signature,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="zscaler",
            sourcetype="zscaler:zia"
        )

    @staticmethod
    def format_nokia_sros_log(
        device: Node,
        port_id: str,
        lsp_name: str,
        action: str,
        status: str,
        signature: str = "Nokia SR-OS Optical Carrier Loss of Signal (LOS) / Fast Reroute"
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        now_syslog = SplunkLogEngine.current_timestamp_syslog()
        dev_id = device.name or device.id
        raw = (
            f"{now_syslog} {dev_id} Base %ROUTING-3-OPTICAL_LOS: Optical DWDM port {port_id} Loss of Signal. "
            f"RSVP-TE LSP {lsp_name} path failed. Fast Reroute (FRR) facility bypass engaged. "
            f"timestamp=\"{now_ts}\" device_id=\"{dev_id}\" src_ip={device.ip_address} "
            f"dest_ip=10.200.0.2 protocol=MPLS-RSVP duration=2ms action={action} "
            f"signature=\"{signature}\" status={status}"
        )
        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=device.ip_address,
            dest_ip="10.200.0.2",
            protocol="MPLS-RSVP",
            duration="2ms",
            action=action,
            signature=signature,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="nokia_sros",
            sourcetype="nokia:sros:syslog"
        )

    @staticmethod
    def format_juniper_junos_log(
        device: Node,
        lsp_name: str,
        primary_nh: str,
        bypass_nh: str,
        action: str,
        status: str,
        signature: str = "Juniper Junos MPLS RSVP-TE FRR Switchover"
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        now_syslog = SplunkLogEngine.current_timestamp_syslog()
        dev_id = device.name or device.id
        raw = (
            f"{now_syslog} {dev_id} rpd[2941]: RPD_MPLS_LSP_CHANGE: LSP {lsp_name}: "
            f"Primary next-hop {primary_nh} DOWN. Switched to Fast-Reroute Bypass next-hop {bypass_nh} "
            f"timestamp=\"{now_ts}\" device_id=\"{dev_id}\" src_ip={device.ip_address} "
            f"dest_ip={bypass_nh} protocol=MPLS duration=1ms action={action} "
            f"signature=\"{signature}\" status={status}"
        )
        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=device.ip_address,
            dest_ip=bypass_nh,
            protocol="MPLS",
            duration="1ms",
            action=action,
            signature=signature,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="juniper_junos",
            sourcetype="juniper:junos"
        )

    @staticmethod
    def format_arista_ipfix_log(
        device: Node,
        src_ip: str,
        dest_ip: str,
        bytes_transferred: int,
        egress_intf: str,
        reroute_flag: int,
        action: str,
        status: str,
        signature: str = "Arista EOS IPFIX Flow Telemetry Rerouted Egress"
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        dev_id = device.name or device.id
        raw = (
            f"{{\"flowRecord\": {{\"version\": 10, \"observationDomain\": 1, \"src_ip\": \"{src_ip}\", "
            f"\"dest_ip\": \"{dest_ip}\", \"protocol\": 6, \"bytes\": {bytes_transferred}, \"packets\": 120, "
            f"\"egress_interface\": \"{egress_intf}\", \"reroute_flag\": {reroute_flag}}}, "
            f"\"timestamp\": \"{now_ts}\", \"device_id\": \"{dev_id}\", \"duration\": \"1ms\", "
            f"\"action\": \"{action}\", \"signature\": \"{signature}\", \"status\": \"{status}\"}}"
        )
        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=src_ip,
            dest_ip=dest_ip,
            protocol="IPFIX",
            duration="1ms",
            action=action,
            signature=signature,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="arista_eos",
            sourcetype="arista:flow:ipfix"
        )

    # =========================================================================
    # MULTI-PROTOCOL TELEMETRY ENGINES (MDT, SNMP, IPFIX, REST WEBHOOKS)
    # =========================================================================

    @staticmethod
    def format_mdt_stream(
        device: Node,
        interface_name: str = "GigabitEthernet0/0/1",
        in_octets: int = 48291048,
        out_octets: int = 59482019,
        cpu_pct: float = 24.5,
        memory_pct: float = 38.2,
        action: str = "allowed",
        status: str = "normal"
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        dev_id = device.name or device.id
        raw_mdt = json.dumps({
            "node_id_str": dev_id,
            "subscription_id_str": "gnmi-cadence-subscription-42",
            "encoding": "JSON_IETF",
            "time": int(time.time() * 1000),
            "data_gpbkv": [
                {
                    "timestamp": int(time.time() * 1000),
                    "path": f"openconfig-interfaces:interfaces/interface[name={interface_name}]/state/counters",
                    "content": {
                        "in-octets": in_octets,
                        "out-octets": out_octets,
                        "in-pkts": int(in_octets / 1200),
                        "out-pkts": int(out_octets / 1200),
                        "in-errors": 0 if status != "degraded" else 142,
                        "out-errors": 0,
                        "in-discards": 0 if status != "congested" else 8420
                    }
                },
                {
                    "timestamp": int(time.time() * 1000),
                    "path": "openconfig-platform:components/component[name=CPU]/state",
                    "content": {
                        "cpu-utilization": cpu_pct,
                        "memory-utilization": memory_pct,
                        "temperature-celsius": 42.5
                    }
                }
            ]
        })

        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=device.ip_address,
            dest_ip="10.0.1.254",
            protocol="gNMI/gRPC",
            duration="1ms",
            action=action,
            signature="Model-Driven Telemetry (MDT) OpenConfig Streaming Metrics",
            status=status,
            raw_log=raw_mdt,
            node_type=device.type.value,
            node_id=device.id,
            vendor=device.vendor or "cisco",
            sourcetype="cisco:ios:mdt"
        )

    @staticmethod
    def format_snmp_trap(
        device: Node,
        trap_type: str = "linkDown",
        interface_name: str = "GigabitEthernet0/0/1",
        action: str = "alerted",
        status: str = "warning"
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        now_syslog = SplunkLogEngine.current_timestamp_syslog()
        dev_id = device.name or device.id

        trap_oids = {
            "linkDown": "1.3.6.1.6.3.1.1.5.3",
            "linkUp": "1.3.6.1.6.3.1.1.5.4",
            "authenticationFailure": "1.3.6.1.6.3.1.1.5.5",
            "coldStart": "1.3.6.1.6.3.1.1.5.1",
            "bgpNeighborLoss": "1.3.6.1.4.1.9.9.187.0.1"
        }
        oid = trap_oids.get(trap_type, "1.3.6.1.6.3.1.1.5.3")

        raw = (
            f"{now_syslog} {dev_id} snmptrapd[1048]: "
            f"SNMPv2-MIB::snmpTrapOID.0 = OID: IF-MIB::{trap_type} ({oid}) "
            f"IF-MIB::ifDescr = \"{interface_name}\" IF-MIB::ifOperStatus = {1 if trap_type == 'linkUp' else 2} "
            f"device=\"{dev_id}\" ip={device.ip_address} trap_type={trap_type} action={action} status={status}"
        )

        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=device.ip_address,
            dest_ip="10.0.1.250",
            protocol="SNMP-TRAP",
            duration="1ms",
            action=action,
            signature=f"SNMP Notification Trap: {trap_type} on {interface_name}",
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor=device.vendor or "generic",
            sourcetype="snmp:trap"
        )

    @staticmethod
    def format_snmp_poll(
        device: Node,
        interface_name: str = "GigabitEthernet0/0/1",
        in_octets: int = 194820104,
        out_octets: int = 284019284
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        dev_id = device.name or device.id
        raw = json.dumps({
            "timestamp": now_ts,
            "device": dev_id,
            "ip": device.ip_address,
            "sysUpTime": "142 days, 08:24:12",
            "ifTable": [
                {
                    "ifIndex": 1,
                    "ifDescr": interface_name,
                    "ifType": "ethernetCsmacd(6)",
                    "ifSpeed": 1000000000,
                    "ifAdminStatus": "up(1)",
                    "ifOperStatus": "up(1)",
                    "ifInOctets": in_octets,
                    "ifOutOctets": out_octets,
                    "ifInErrors": 0,
                    "ifOutErrors": 0
                }
            ]
        })

        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=device.ip_address,
            dest_ip="10.0.1.250",
            protocol="SNMP-POLL",
            duration="5ms",
            action="allowed",
            signature="SNMPv2c Scheduled Polling: MIB-II / IF-MIB Metrics",
            status="normal",
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor=device.vendor or "generic",
            sourcetype="snmp:poll"
        )

    @staticmethod
    def format_ipfix_flow(
        device: Node,
        src_ip: str,
        dest_ip: str,
        src_port: int,
        dest_port: int,
        protocol: str = "TCP",
        bytes_count: int = 14820,
        packets_count: int = 18,
        tcp_flags: str = "SYN,ACK",
        action: str = "allowed",
        status: str = "normal"
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        dev_id = device.name or device.id
        raw = (
            f"IPFIX flow_export: exp_ip={device.ip_address} src_ip={src_ip} dest_ip={dest_ip} "
            f"src_port={src_port} dest_port={dest_port} proto={protocol} bytes={bytes_count} "
            f"packets={packets_count} tcp_flags=\"{tcp_flags}\" duration=14ms action={action} "
            f"status={status} device_id=\"{dev_id}\""
        )

        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=src_ip,
            dest_ip=dest_ip,
            protocol=protocol,
            duration="14ms",
            action=action,
            signature="NetFlow v9 / IPFIX Synthetic Flow Record",
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor=device.vendor or "generic",
            sourcetype="netflow:ipfix"
        )

    @staticmethod
    def format_controller_webhook_event(
        device: Node,
        controller_type: str = "palo_alto_panorama",
        alert_category: str = "security_threat",
        details: Dict[str, Any] = None
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        dev_id = device.name or device.id
        event_payload = {
            "source_controller": controller_type,
            "managed_device": dev_id,
            "timestamp": now_ts,
            "event_category": alert_category,
            "severity": "CRITICAL" if alert_category == "security_threat" else "INFO",
            "payload": details or {
                "rule_name": "Edge-Perimeter-Block",
                "attacker_ip": "198.51.100.99",
                "attack_vector": "T1190 Exploit Public-Facing Application",
                "mitigation": "Dynamic Quarantine Address Group Enforced"
            }
        }

        raw = json.dumps(event_payload)
        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=device.ip_address,
            dest_ip="10.0.1.100",
            protocol="HTTPS-WEBHOOK",
            duration="2ms",
            action="blocked" if alert_category == "security_threat" else "allowed",
            signature=f"Mock Controller Webhook Alert: {controller_type} [{alert_category}]",
            status="blocked" if alert_category == "security_threat" else "normal",
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="controller_push",
            sourcetype="controller:webhook:event"
        )

