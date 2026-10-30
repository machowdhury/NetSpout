# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/log_engine.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
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
import zlib
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
        now = datetime.utcnow()
        day = f"{now.day:2d}"
        return f"{now.strftime('%b')} {day} {now.strftime('%H:%M:%S')}"

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
        duration_ms: int = 12,
        connection_id: Optional[int] = None,
        event_type: str = "build",
        mapped_src: Optional[str] = None,
        mapped_dest: Optional[str] = None,
        src_interface: str = "outside",
        dest_interface: str = "inside",
        bytes_count: int = 0,
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        now_syslog = SplunkLogEngine.current_timestamp_syslog()
        dev_id = device.name or device.id
        
        # Cisco ASA 302013/14 (TCP), 302015/16 (UDP), 106023 (deny).
        # Simulation annotations remain on LogEntry, never inside the vendor body.
        protocol = proto.upper()
        if protocol not in {"TCP", "UDP"} or event_type not in {"build", "teardown"}:
            raise ValueError("Unsupported ASA connection event")
        if connection_id is None:
            identity = f"{device.id}|{src_ip}|{src_port}|{dest_ip}|{dest_port}|{protocol}"
            connection_id = zlib.crc32(identity.encode("utf-8")) & 0x7fffffff
        if (type(connection_id) is not int or connection_id < 0 or
                type(bytes_count) is not int or bytes_count < 0 or duration_ms < 0):
            raise ValueError("Invalid ASA connection counters")
        source = f"{src_interface}:{src_ip}/{src_port}"
        destination = f"{dest_interface}:{dest_ip}/{dest_port}"
        if action in {"blocked", "dropped"}:
            message = (f'%ASA-4-106023: Deny {protocol.lower()} src {source} '
                       f'dst {destination} by access-group "OUTSIDE_IN" [0x0, 0x0]')
        elif event_type == "teardown":
            code = 302014 if protocol == "TCP" else 302016
            seconds = int(duration_ms // 1000)
            duration = f"{seconds // 3600}:{seconds // 60 % 60:02}:{seconds % 60:02}"
            reason = " TCP FINs" if protocol == "TCP" else ""
            message = (f"%ASA-6-{code}: Teardown {protocol} connection {connection_id} "
                       f"for {source} to {destination} duration {duration} bytes {bytes_count}{reason}")
        else:
            code = 302013 if protocol == "TCP" else 302015
            # Identity translation unless explicit mapped socket values are supplied.
            message = (f"%ASA-6-{code}: Built inbound {protocol} connection {connection_id} "
                       f"for {source} ({mapped_src or f'{src_ip}/{src_port}'}) "
                       f"to {destination} ({mapped_dest or f'{dest_ip}/{dest_port}'})")
        raw = f"{now_syslog} {dev_id} {message}"

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
            vendor="cisco_asa",
            sourcetype="cisco:asa"
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
            vendor="palo_alto",
            sourcetype="pan:traffic"
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
            vendor="nginx",
            sourcetype="nginx:plus:kv"
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
            f"connection established client={src_ip} vip={dest_ip}:80 target={backend_ip}:{backend_port}"
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
            vendor="f5_bigip",
            sourcetype="f5:bigip:ltm"
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
            vendor="postgresql",
            sourcetype="postgresql:audit"
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
            f"from {src_ip} to {dest_ip} via BGP-RIB"
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
            vendor=getattr(device, "vendor", "cisco_ios") or "cisco_ios",
            sourcetype=getattr(device, "sourcetype", "cisco:ios:syslog") or "cisco:ios:syslog"
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
            f"rogue_mac={rogue_mac} bssid={bssid} ssid=\"{ssid}\" channel={channel} rssi={rssi}dBm"
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
        client_mac: str = "00:1A:2B:3C:4D:5E",
        client_ip: str = "10.10.30.50",
        user: str = "corporate_user",
        auth_status: Optional[str] = None,
        profile: str = "Corporate-Access",
        action: str = "allowed",
        status: str = "normal",
        signature: str = "802.1X Quarantine Profile Applied via Cisco ISE",
        sourcetype: str = "cisco:ise:syslog",
        **kwargs
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        now_syslog = SplunkLogEngine.current_timestamp_syslog()
        dev_id = device.name or device.id
        c_mac = kwargs.get("mac_address", client_mac)
        c_prof = kwargs.get("endpoint_profile", profile)
        outcome = (auth_status or ("FAILED" if action in {"blocked", "dropped"} else "SUCCESS")).upper()
        if outcome == "PASSED":
            outcome = "SUCCESS"
        if outcome not in {"SUCCESS", "FAILED", "FAILURE"}:
            raise ValueError("Unsupported ISE authentication outcome")
        success = outcome == "SUCCESS"
        category = "CISE_Passed_Authentications" if success else "CISE_Failed_Attempts"
        code = 5200 if success else 5400
        classification = "Passed-Authentication" if success else "Failed-Attempt"
        description = "Authentication succeeded" if success else "Authentication failed"
        response = "AccessAccept" if success else "AccessReject"
        # Local store timestamp includes numeric timezone; remote transport header
        # precedes it. Counters may be supplied by a correlated synthetic timeline.
        local_ts = now_ts.removesuffix(" UTC") + " +00:00"
        sequence = kwargs.get("sequence_num", 1)
        if type(sequence) is not int or not 0 <= sequence <= 9999999999:
            raise ValueError("Invalid ISE sequence")
        raw = (
            f"<181>{now_syslog} {dev_id} {category} {sequence:010d} 1 0 "
            f"{local_ts} {sequence:010d} {code} NOTICE {classification}: {description}, "
            f"User-Name={user}, Calling-Station-ID={c_mac}, Framed-IP-Address={client_ip}, "
            f"NAS-IP-Address=10.0.0.1, Protocol=Radius, AuthorizationProfiles={c_prof}, "
            f"Response={{RadiusPacketType={response};}}"
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
            sourcetype=sourcetype
        )

    @staticmethod
    def format_cisco_ise_coa_log(
        device: Node,
        client_mac: str,
        client_ip: str,
        user: str,
        profile: str,
        action: str,
        status: str,
        signature: str,
        sequence_num: int = 1,
    ) -> LogEntry:
        """Simulate Cisco ISE 5205: dynamic authorization succeeded.

        Cisco ISE Syslogs, Passed Authentications, printed pp. 491-492:
        NOTICE Dynamic-Authorization, not authentication or proof of quarantine.
        The category groups this event with passed authentications, but the code
        and message class distinguish it from 5200. No CoA is actually issued.
        """
        if type(sequence_num) is not int or not 1 <= sequence_num <= 4294967295:
            raise ValueError("Invalid ISE CoA sequence")
        now_ts = SplunkLogEngine.current_timestamp_iso()
        local_ts = now_ts.removesuffix(" UTC") + " +00:00"
        dev_id = device.name or device.id
        raw = (
            f"<181>{SplunkLogEngine.current_timestamp_syslog()} {dev_id} "
            f"CISE_Passed_Authentications {sequence_num:010d} 1 0 "
            f"{local_ts} {sequence_num:010d} 5205 NOTICE Dynamic-Authorization: "
            f"Dynamic Authorization succeeded, User-Name={user}, Calling-Station-ID={client_mac}"
        )
        return LogEntry(
            timestamp=now_ts, device_id=dev_id, src_ip=client_ip,
            dest_ip=device.ip_address, protocol="RADIUS", duration="14ms",
            action=action, status=status,
            signature=(f"{signature} [SIMULATED CoA success; profile={profile}; "
                       "quarantine enforcement unverified]"),
            raw_log=raw, node_type=device.type.value, node_id=device.id,
            vendor="cisco_ise", sourcetype="cisco:ise:syslog",
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
        # Cisco prints Ethernet addresses in dotted hexadecimal notation.
        compact_mac = mac.replace(":", "").replace("-", "").replace(".", "")
        if len(compact_mac) != 12 or any(c not in "0123456789abcdefABCDEF" for c in compact_mac):
            raise ValueError("Invalid MAC address")
        native_mac = ".".join(compact_mac[i:i + 4].lower() for i in (0, 4, 8))
        raw = (
            f"{now_syslog} {dev_id} %SW_MATM-4-MACFLAP_NOTIF: Host {native_mac} in vlan {vlan} "
            f"is flapping between port {port1} and port {port2}."
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
    def format_cisco_catalyst_security_event(
        device: Node,
        client_mac: str,
        event_type: str,
        action: str,
        status: str,
        signature: Optional[str] = None
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        now_syslog = SplunkLogEngine.current_timestamp_syslog()
        dev_id = device.name or device.id
        sig = signature or f"Catalyst Security Event: {event_type}"
        raw = (
            f"{now_syslog} {dev_id} %CATALYST_SEC-6-EVENT: event_type=\"{event_type}\" "
            f"client_mac=\"{client_mac}\""
        )
        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=device.ip_address,
            dest_ip="255.255.255.255",
            protocol="802.1X",
            duration="1ms",
            action=action,
            signature=sig,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="cisco_catalyst",
            sourcetype="cisco:catalyst:security:events"
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
            f"loss={loss_pct:.1f}% sla_class=VoIP_Gold sla_compliance={sla_status}"
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
            f"BFD session down; failover to secondary LTE/Broadband transport engaged"
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
            f"buffer_util={buffer_util_pct:.1f}% dropped_packets={dropped_packets} fabricHealthScore={fabric_health}"
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
    def format_cisco_aci_health_log(
        device: Node,
        fabric_health: int,
        action: str,
        status: str,
        signature: Optional[str] = None
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        now_syslog = SplunkLogEngine.current_timestamp_syslog()
        dev_id = device.name or device.id
        sig = signature or f"ACI Fabric Health Score: {fabric_health}/100"
        raw = (
            f"{now_syslog} {dev_id} %ACI-HEALTH-4-SCORE: fabricHealthScore={fabric_health}"
        )
        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=device.ip_address,
            dest_ip="10.255.0.1",
            protocol="DC-ETHERNET",
            duration="1ms",
            action=action,
            signature=sig,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="cisco_aci",
            sourcetype="cisco:dc:aci:health"
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
        signature: str = "Meraki Wireless Intrusion / Rogue Probe Alert",
        sourcetype: str = "meraki:assurancealerts"
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
            sourcetype=sourcetype
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
    def format_fortinet_ips_log(
        device: Node,
        src_ip: str,
        dest_ip: str,
        src_port: int,
        dest_port: int,
        attack: str,
        action: str,
        status: str,
        duration_ms: int = 2,
        signature: Optional[str] = None
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        dev_id = device.name or device.id
        sig = signature or f"FortiGate IPS Detection: {attack}"
        # FortiOS 7.2.0 IPS signature event subset (logid 0419016384).
        # Non-blocking detection is 'detected', not a claim that a session passed.
        forti_action = "dropped" if action in ("dropped", "blocked") else "detected"
        # This bounded formatter rejects characters whose native escaping has not
        # been established, rather than inventing a general FortiOS string codec.
        if any(c in str(value) for value in (dev_id, attack) for c in ('"', "\\", "\r", "\n")):
            raise ValueError("Unsupported FortiOS quoted value")
        now_utc = datetime.utcnow()
        raw = (
            f"<189>date={now_utc.strftime('%Y-%m-%d')} time={now_utc.strftime('%H:%M:%S')} "
            f"tz=\"+0000\" devname=\"{dev_id}\" devid=\"FG60ET4619000000\" logid=\"0419016384\" "
            f"type=\"utm\" subtype=\"ips\" eventtype=\"signature\" level=\"alert\" severity=\"high\" "
            f"srcip={src_ip} srcport={src_port} srcintf=\"port1\" "
            f"dstip={dest_ip} dstport={dest_port} dstintf=\"port2\" proto=6 "
            f"action=\"{forti_action}\" attack=\"{attack}\" msg=\"IPS: {attack}\""
        )
        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=src_ip,
            dest_ip=dest_ip,
            protocol="TCP",
            duration=f"{duration_ms}ms",
            action=action,
            signature=sig,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="fortinet",
            sourcetype="fortinet:fortigate:utm"
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
            f"RSVP-TE LSP {lsp_name} path failed. Fast Reroute (FRR) facility bypass engaged."
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
        # The documented event reports a path change, not confirmed FRR enforcement.
        # Legacy callers decorate next hops with display labels; keep those out of raw.
        from ipaddress import ip_address
        route = str(ip_address(primary_nh.split()[0]))
        raw = (
            f"{now_syslog} {dev_id} rpd[2941]: RPD_MPLS_LSP_CHANGE: "
            f"MPLS LSP {lsp_name} change on primary(any) Route  {route}"
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
        status: str = "normal",
        sourcetype: str = "cisco:ios:mdt"
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
            sourcetype=sourcetype
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

    @staticmethod
    def format_cisco_catalyst_dhcp_snooping_log(
        device: Node,
        client_mac: str,
        vlan_id: int,
        interface: str,
        rogue_ip: str,
        event_code: str,
        action: str,
        status: str,
        signature: Optional[str] = None
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        now_syslog = SplunkLogEngine.current_timestamp_syslog()
        dev_id = device.name or device.id
        sig = signature or f"Catalyst Access Security: {event_code}"

        if event_code == "DHCP_OFFER_DROPPED":
            msg = f"%DHCP_SNOOPING-5-DHCP_OFFER_DROPPED: Rogue DHCP offer packet dropped on untrusted port {interface}, vlan {vlan_id}, rogue server IP {rogue_ip}, client MAC {client_mac}"
        elif event_code == "DAI_BURST_EXCEEDED":
            msg = f"%SW_DAI-4-PACKET_BURST_RATE_EXCEEDED: 15 packets received per second exceeded burst rate on {interface}, vlan {vlan_id}"
        elif event_code == "ERR_DISABLE":
            msg = f"%PM-4-ERR_DISABLE: arp-inspection error detected on {interface}, putting {interface} in err-disable state"
        elif event_code == "PORT_RESTORED":
            msg = f"%PM-4-ERR_RECOVER: Attempting to recover from arp-inspection err-disable state on {interface}, port restored to forwarding"
        else:
            msg = f"%CATALYST_SEC-5-STATUS: Interface {interface} vlan {vlan_id} security event {event_code}"

        raw = f"{now_syslog} {dev_id} {msg}"
        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=rogue_ip,
            dest_ip="255.255.255.255",
            protocol="UDP",
            duration="1ms",
            action=action,
            signature=sig,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="cisco_catalyst",
            sourcetype="cisco:catalyst:security:events"
        )

    @staticmethod
    def format_cisco_duo_vpn_log(
        device: Node,
        user: str,
        client_ip: str,
        factor: str,
        result: str,
        reason: str,
        country: str,
        action: str,
        status: str,
        sourcetype: str = "cisco:duo:remote:vpn",
        signature: Optional[str] = None
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        dev_id = device.name or device.id
        sig = signature or f"Cisco Duo MFA: {factor} - {result} ({reason})"
        event_payload = {
            "timestamp": now_ts,
            "eventtype": "authentication",
            "username": user,
            "factor": factor,
            "result": result,
            "reason": reason,
            "ip_address": client_ip,
            "access_device": {
                "ip": client_ip,
                "location": {
                    "city": "Moscow" if country == "RU" else "Dallas",
                    "country": country
                }
            },
            "application": {
                "name": "Cisco AnyConnect SSL-VPN",
                "device": dev_id
            },
            "action": action,
            "status": status,
            "signature": sig
        }
        raw = json.dumps(event_payload)
        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=client_ip,
            dest_ip=device.ip_address,
            protocol="HTTPS",
            duration="2ms",
            action=action,
            signature=sig,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="cisco_duo",
            sourcetype=sourcetype
        )

    @staticmethod
    def format_cisco_ios_xr_bgp_log(
        device: Node,
        neighbor_ip: str,
        event_type: str,
        action: str,
        status: str,
        prefix: str = "10.200.0.0/16",
        signature: Optional[str] = None
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        now_syslog = SplunkLogEngine.current_timestamp_syslog()
        dev_id = device.name or device.id

        if event_type == "BGP_DOWN":
            sig = signature or f"BGP Neighbor {neighbor_ip} Down: Carrier Link Flap"
            msg = f"%ROUTING-BGP-5-ADJCHANGE: neighbor {neighbor_ip} Down - Interface flap on HundredGigE0/0/0/1"
        elif event_type == "TI_LFA_REROUTE":
            sig = signature or "TI-LFA Modeled Sub-50ms Fast Reroute Activated"
            msg = f"%MPLS-6-TI_LFA_LOCAL_REPAIR: Fast reroute activated for prefix {prefix} via HundredGigE0/0/0/2 backup path, convergence_ms=32"
        elif event_type == "BGP_UP":
            sig = signature or f"BGP Neighbor {neighbor_ip} Up: Peering Restored"
            msg = f"%ROUTING-BGP-5-ADJCHANGE: neighbor {neighbor_ip} Up - Peering re-established after carrier stabilization"
        elif event_type == "ROUTE_STABLE":
            sig = signature or "Core BGP/MPLS Routing Equilibrium Restored"
            msg = f"%ROUTING-BGP-6-STABILITY: Prefix {prefix} active via primary path HundredGigE0/0/0/1, fast-reroute disarmed"
        else:
            sig = signature or f"BGP Routing Event: {event_type}"
            msg = f"%ROUTING-BGP-6-INFO: Peering {neighbor_ip} state={event_type}"

        raw = f"{now_syslog} {dev_id} {msg}"
        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=device.ip_address,
            dest_ip=neighbor_ip,
            protocol="BGP",
            duration="1ms",
            action=action,
            signature=sig,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="cisco_ios",
            sourcetype="cisco:ios:syslog"
        )

    @staticmethod
    def format_cisco_catalyst_wlan_rf_log(
        device: Node,
        channel: int,
        util_pct: float,
        noise_floor: int,
        event_type: str,
        action: str,
        status: str,
        sourcetype: str = "cisco:catalyst:clienthealth",
        signature: Optional[str] = None
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        now_syslog = SplunkLogEngine.current_timestamp_syslog()
        dev_id = device.name or device.id

        if event_type == "INTERFERENCE_SURGE":
            sig = signature or f"CleanAir Non-Wi-Fi RF Interference Surge on Channel {channel}"
            msg = f"%DOT11-4-CLEANAIR_INTERFERENCE: Radio 1 Channel {channel} interference surge detected: utilization={util_pct}% noise_floor={noise_floor}dBm duty_cycle=88%"
        elif event_type == "CHANNEL_SWITCH":
            sig = signature or "CleanAir Dynamic Channel Assignment (DCA) Reassignment"
            msg = f"%DOT11-5-CLEANAIR_CHANNEL_SWITCH: Radio 1 shifted from congested Channel {channel} to pristine Channel 100 via automated DCA/RRM"
        elif event_type == "ROGUE_CONTAINED":
            sig = signature or "Air Marshal Evil-Twin SSID Rogue Containment Active"
            msg = f"%AIRMARSHAL-4-ROGUE_CONTAINMENT: Rogue AP with spoofed SSID 'Corp-Executive-Secure' suppressed on channel {channel}"
        elif event_type == "RF_RESTORED":
            sig = signature or "WLAN RF Spectrum & Client SNR Restored to Nominal"
            msg = f"%DOT11-6-CLEANAIR_HEALTH: Channel 100 clean, channel utilization={util_pct}% noise_floor={noise_floor}dBm, client SNR=38dB"
        else:
            sig = signature or f"WLAN Telemetry: {event_type}"
            msg = f"%DOT11-6-INFO: Radio 1 channel={channel} util={util_pct}%"

        raw = f"{now_syslog} {dev_id} {msg}"
        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=device.ip_address,
            dest_ip="255.255.255.255",
            protocol="802.11ax",
            duration="1ms",
            action=action,
            signature=sig,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor="cisco_catalyst",
            sourcetype=sourcetype
        )

    @staticmethod
    def format_g8032_erps_log(
        device: Node,
        ring_id: str,
        port_id: str,
        event_type: str,
        action: str,
        status: str,
        vendor: str = "nokia_sros",
        sourcetype: str = "nokia:sros:syslog",
        signature: Optional[str] = None
    ) -> LogEntry:
        now_ts = SplunkLogEngine.current_timestamp_iso()
        now_syslog = SplunkLogEngine.current_timestamp_syslog()
        dev_id = device.name or device.id

        if event_type == "SIGNAL_FAIL":
            sig = signature or f"G.8032 ERPS Ring {ring_id} Span {port_id} Fiber Cut Signal Failure"
            msg = f"%ETH_RING-4-SIGNAL_FAILURE: Ring {ring_id} port {port_id} Terrestrial Fiber Cut detected, state transitioned to SIGNAL_FAIL (SF)"
        elif event_type == "RPL_UNBLOCK":
            sig = signature or f"G.8032 ERPS Ring {ring_id} RPL Unblocked (Modeled Sub-50ms Failover)"
            msg = f"%ETH_RING-4-RPL_UNBLOCK: Ring {ring_id} Ring Protection Link (RPL) unblocked in 38ms, traffic forwarding maintained across alternate span"
        elif event_type == "REVERTIVE_RESTORE":
            sig = signature or f"G.8032 ERPS Ring {ring_id} WTR Expired Revertive Restoration"
            msg = f"%ETH_RING-5-REVERTIVE_RESTORE: Ring {ring_id} fiber span spliced, WTR timer expired, ring reverted to IDLE state"
        else:
            sig = signature or f"G.8032 ERPS Ring Event: {event_type}"
            msg = f"%ETH_RING-6-INFO: Ring {ring_id} port {port_id} state={event_type}"

        raw = f"{now_syslog} {dev_id} {msg}"
        return LogEntry(
            timestamp=now_ts,
            device_id=dev_id,
            src_ip=device.ip_address,
            dest_ip="224.0.0.251",
            protocol="G.8032",
            duration="1ms",
            action=action,
            signature=sig,
            status=status,
            raw_log=raw,
            node_type=device.type.value,
            node_id=device.id,
            vendor=vendor,
            sourcetype=sourcetype
        )


# ---------------------------------------------------------------------------
# Wave-1 authentic source expansion (2026-10-26)
# Genuinely new vendor-native source families (Windows/CrowdStrike/AWS/M365/
# Azure/Suricata/auditd/Okta/osquery), implemented in a dedicated module with
# pinned-upstream RAW references. Delegated here so SplunkLogEngine consumers
# (scenario runners, PulseForge lab harness) can emit them directly.
# Correlation metadata remains HEC-side only; RAW is vendor-native.
# ---------------------------------------------------------------------------
try:
    from netspout_core.wave1_authentic_engine import (
        Wave1AuthenticEngine as _Wave1Engine,
        SOURCETYPE_WINDOWS_SECURITY as _W1_ST_SEC,
        SOURCETYPE_WINDOWS_SYSMON as _W1_ST_SYSMON,
        SOURCETYPE_WINDOWS_POWERSHELL as _W1_ST_PS,
        SOURCETYPE_CROWDSTRIKE_SENSOR as _W1_ST_CS,
        SOURCETYPE_SYSMON_LINUX as _W1_ST_SL,
        SOURCETYPE_AWS_CLOUDTRAIL as _W1_ST_CT,
        SOURCETYPE_O365_MANAGEMENT as _W1_ST_O365,
        SOURCETYPE_AZURE_AAD as _W1_ST_AZ,
        SOURCETYPE_SURICATA as _W1_ST_SURICATA,
        SOURCETYPE_AUDITD as _W1_ST_AUDITD,
        SOURCETYPE_OKTA as _W1_ST_OKTA,
        SOURCETYPE_OSQUERY as _W1_ST_OSQUERY,
    )

    WAVE1_SOURCE_SOURCETYPES = {
        _W1_ST_SEC: "format_windows_security_xml_log",
        _W1_ST_SYSMON: "format_windows_sysmon_xml_log",
        _W1_ST_PS: "format_windows_powershell_xml_log",
        _W1_ST_CS: "format_crowdstrike_falcon_sensor_log",
        _W1_ST_SL: "format_sysmon_linux_log",
        _W1_ST_CT: "format_aws_cloudtrail_log",
        _W1_ST_O365: "format_o365_management_log",
        _W1_ST_AZ: "format_azure_monitor_aad_log",
        _W1_ST_SURICATA: "format_suricata_eve_log",
        _W1_ST_AUDITD: "format_linux_auditd_log",
        _W1_ST_OKTA: "format_okta_log",
        _W1_ST_OSQUERY: "format_osquery_results_log",
    }

    SplunkLogEngine.WAVE1_SOURCE_SOURCETYPES = WAVE1_SOURCE_SOURCETYPES

    def _w1_delegate(name):
        engine_method = getattr(_Wave1Engine, name)

        @classmethod
        def delegate(cls, *args, **kwargs):
            return engine_method(*args, **kwargs)

        return delegate

    SplunkLogEngine.format_windows_security_xml_log = _w1_delegate(
        "format_windows_security_xml_log")
    SplunkLogEngine.format_windows_sysmon_xml_log = _w1_delegate(
        "format_windows_sysmon_xml_log")
    SplunkLogEngine.format_windows_powershell_xml_log = _w1_delegate(
        "format_windows_powershell_xml_log")
    SplunkLogEngine.format_crowdstrike_falcon_sensor_log = _w1_delegate(
        "format_crowdstrike_falcon_sensor_log")
    SplunkLogEngine.format_sysmon_linux_log = _w1_delegate(
        "format_sysmon_linux_log")
    SplunkLogEngine.format_aws_cloudtrail_log = _w1_delegate(
        "format_aws_cloudtrail_log")
    SplunkLogEngine.format_o365_management_log = _w1_delegate(
        "format_o365_management_log")
    SplunkLogEngine.format_azure_monitor_aad_log = _w1_delegate(
        "format_azure_monitor_aad_log")
    SplunkLogEngine.format_suricata_eve_log = _w1_delegate(
        "format_suricata_eve_log")
    SplunkLogEngine.format_linux_auditd_log = _w1_delegate(
        "format_linux_auditd_log")
    SplunkLogEngine.format_okta_log = _w1_delegate(
        "format_okta_log")
    SplunkLogEngine.format_osquery_results_log = _w1_delegate(
        "format_osquery_results_log")
except ImportError:  # pragma: no cover - wave-1 module unavailable
    pass

# ---------------------------------------------------------------------------
# Wave-2 authentic source expansion (2026-10-26)
# 12 new vendor-native sourcetypes (Defender/NTLM XML, ollama, MCP, Google
# Workspace login, Azure Activity Log, AWS VPC Flow, /var/log/messages,
# Kubernetes audit, Falco, CrushFTP) plus full generator support for the
# existing cisco:sfw:estreamer row. Same guarantees as Wave-1: RAW is pure
# vendor-native, correlation metadata stays in LogEntry fields only.
# ---------------------------------------------------------------------------
try:
    from netspout_core.wave2_authentic_engine import (
        Wave2AuthenticEngine as _Wave2Engine,
        WAVE2_SOURCE_SOURCETYPES as _W2_MAP,
    )

    SplunkLogEngine.WAVE2_SOURCE_SOURCETYPES = _W2_MAP

    def _w2_delegate(name):
        engine_method = getattr(_Wave2Engine, name)

        @classmethod
        def delegate(cls, *args, **kwargs):
            return engine_method(*args, **kwargs)

        return delegate

    for _w2_fmt in _W2_MAP.values():
        setattr(SplunkLogEngine, _w2_fmt, _w2_delegate(_w2_fmt))
except ImportError:  # pragma: no cover - wave-2 module unavailable
    pass

# ---------------------------------------------------------------------------
# Wave-3 authentic source expansion (2026-10-26)
# Splunkbase-scale batch: VMware vSphere, Cisco Cloud Security (firewall/ns
# DNS/proxy), Cisco Isovalent Tetragon, CloudTrail Lake, linux_secure, IIS,
# Zeek conn, MSExchange Management, CloudFront, M365/Gmail traces, Zscaler NSS,
# Secure Access RA-VPN, SD-WAN, IOS SEC_LOGIN, Meraki syslog, dhcpd, GCP audit,
# OpenTelemetry OTLP, Windows System channel XML plus the cisco:duo:administrator
# generator-gap fill. Same guarantees as Wave-1/2.
# ---------------------------------------------------------------------------
try:
    from netspout_core.wave3_authentic_engine import (
        Wave3AuthenticEngine as _Wave3Engine,
        WAVE3_SOURCE_SOURCETYPES as _W3_MAP,
    )

    SplunkLogEngine.WAVE3_SOURCE_SOURCETYPES = _W3_MAP

    def _w3_delegate(name):
        engine_method = getattr(_Wave3Engine, name)

        @classmethod
        def delegate(cls, *args, **kwargs):
            return engine_method(*args, **kwargs)

        return delegate

    for _w3_fmt in _W3_MAP.values():
        setattr(SplunkLogEngine, _w3_fmt, _w3_delegate(_w3_fmt))
except ImportError:  # pragma: no cover - wave-3 module unavailable
    pass

# ---------------------------------------------------------------------------
# Universal Vendor Coverage — evidence-backed generator batch 1 (2026-10-26)
# Bounded multi-vendor batch: docker_events, bluecoat:proxysg:access:file,
# wazuh:alerts, nozomi:universal_alert. Same guarantees as the wave engines.
# ---------------------------------------------------------------------------
try:
    try:
        from netspout_core.universe_batch1_engine import (
            UniverseBatch1Engine as _UB1Engine,
            UNIVERSE_BATCH1_SOURCE_SOURCETYPES as _UB1_MAP,
        )
    except ImportError:
        try:
            from app.universe_batch1_engine import (
                UniverseBatch1Engine as _UB1Engine,
                UNIVERSE_BATCH1_SOURCE_SOURCETYPES as _UB1_MAP,
            )
        except ImportError:
            from universe_batch1_engine import (
                UniverseBatch1Engine as _UB1Engine,
                UNIVERSE_BATCH1_SOURCE_SOURCETYPES as _UB1_MAP,
            )

    SplunkLogEngine.UNIVERSE_BATCH1_SOURCE_SOURCETYPES = _UB1_MAP

    def _ub1_delegate(name):
        engine_method = getattr(_UB1Engine, name)

        @classmethod
        def delegate(cls, *args, **kwargs):
            return engine_method(*args, **kwargs)

        return delegate

    for _ub1_fmt in _UB1_MAP.values():
        setattr(SplunkLogEngine, _ub1_fmt, _ub1_delegate(_ub1_fmt))
except ImportError:  # pragma: no cover - batch-1 module unavailable
    pass


# Batch 2: exact sourcetype/family dispatch; unsupported families fail closed.
try:
    from netspout_core.universe_batch2_engine import UniverseBatch2Engine, UNIVERSE_BATCH2_SOURCE_SOURCETYPES
except ImportError:
    try:
        from app.universe_batch2_engine import UniverseBatch2Engine, UNIVERSE_BATCH2_SOURCE_SOURCETYPES
    except ImportError:
        from universe_batch2_engine import UniverseBatch2Engine, UNIVERSE_BATCH2_SOURCE_SOURCETYPES
SplunkLogEngine.UNIVERSE_BATCH2_SOURCE_SOURCETYPES = UNIVERSE_BATCH2_SOURCE_SOURCETYPES
SplunkLogEngine.format_universe_batch2_log = UniverseBatch2Engine.format_universe_batch2_log

# Batch 3 native source/family dispatch, including specialized infrastructure formats.
try:
    from netspout_core.universe_batch3_engine import UniverseBatch3Engine, UNIVERSE_BATCH3_SOURCE_SOURCETYPES
except ImportError:
    try:
        from app.universe_batch3_engine import UniverseBatch3Engine, UNIVERSE_BATCH3_SOURCE_SOURCETYPES
    except ImportError:
        from universe_batch3_engine import UniverseBatch3Engine, UNIVERSE_BATCH3_SOURCE_SOURCETYPES
SplunkLogEngine.UNIVERSE_BATCH3_SOURCE_SOURCETYPES = UNIVERSE_BATCH3_SOURCE_SOURCETYPES
SplunkLogEngine.format_universe_batch3_log = UniverseBatch3Engine.format_universe_batch3_log

# Batch 4 native source/family dispatch for SaaS audit, endpoint threat and exposure logs.
try:
    from netspout_core.universe_batch4_engine import UniverseBatch4Engine, UNIVERSE_BATCH4_SOURCE_SOURCETYPES
except ImportError:
    try:
        from app.universe_batch4_engine import UniverseBatch4Engine, UNIVERSE_BATCH4_SOURCE_SOURCETYPES
    except ImportError:
        from universe_batch4_engine import UniverseBatch4Engine, UNIVERSE_BATCH4_SOURCE_SOURCETYPES
SplunkLogEngine.UNIVERSE_BATCH4_SOURCE_SOURCETYPES = UNIVERSE_BATCH4_SOURCE_SOURCETYPES
SplunkLogEngine.format_universe_batch4_log = UniverseBatch4Engine.format_universe_batch4_log

# Batch 5 native source/family dispatch for Cisco IOS-XE change, fault and health device syslog.
try:
    from netspout_core.universe_batch5_engine import UniverseBatch5Engine, UNIVERSE_BATCH5_SOURCE_SOURCETYPES
except ImportError:
    try:
        from app.universe_batch5_engine import UniverseBatch5Engine, UNIVERSE_BATCH5_SOURCE_SOURCETYPES
    except ImportError:
        from universe_batch5_engine import UniverseBatch5Engine, UNIVERSE_BATCH5_SOURCE_SOURCETYPES
SplunkLogEngine.UNIVERSE_BATCH5_SOURCE_SOURCETYPES = UNIVERSE_BATCH5_SOURCE_SOURCETYPES
SplunkLogEngine.format_universe_batch5_log = UniverseBatch5Engine.format_universe_batch5_log

# Batch 6 native source/family dispatch for captured Cisco Catalyst Center, SD-WAN, ACI and Nexus records.
try:
    from netspout_core.universe_batch6_engine import UniverseBatch6Engine, UNIVERSE_BATCH6_SOURCE_SOURCETYPES
except ImportError:
    try:
        from app.universe_batch6_engine import UniverseBatch6Engine, UNIVERSE_BATCH6_SOURCE_SOURCETYPES
    except ImportError:
        from universe_batch6_engine import UniverseBatch6Engine, UNIVERSE_BATCH6_SOURCE_SOURCETYPES
SplunkLogEngine.UNIVERSE_BATCH6_SOURCE_SOURCETYPES = UNIVERSE_BATCH6_SOURCE_SOURCETYPES
SplunkLogEngine.format_universe_batch6_log = UniverseBatch6Engine.format_universe_batch6_log
