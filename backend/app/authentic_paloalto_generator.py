"""
Authentic Palo Alto Networks PAN-OS Telemetry Generator.
Generates vendor-accurate synthetic PAN-OS logs in LEEF 2.0 and syslog formats.
Phase 4B implementation.
"""

import random
import json
import ipaddress
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from enum import Enum

class PANOSVersion(Enum):
    """PAN-OS version support."""
    PANOS_10_2 = "10.2"
    PANOS_10_1 = "10.1"
    PANOS_10_0 = "10.0"
    PANOS_9_1 = "9.1"

class PaloAltoLogType(Enum):
    """Palo Alto log types."""
    TRAFFIC = "TRAFFIC"
    THREAT = "THREAT"
    SYSTEM = "SYSTEM"
    CONFIG = "CONFIG"
    USERID = "USERID"
    GLOBALPROTECT = "GLOBALPROTECT"
    WILDFIRE = "WILDFIRE"
    HIP = "HIP"

class AuthenticPaloAltoGenerator:
    """Authentic Palo Alto Networks PAN-OS log generator."""
    
    def __init__(self, seed: Optional[int] = None, panos_version: PANOSVersion = PANOSVersion.PANOS_10_2):
        """
        Initialize generator.
        
        Args:
            seed: Random seed for deterministic generation
            panos_version: PAN-OS version to emulate
        """
        if seed is not None:
            random.seed(seed)
        
        self.panos_version = panos_version
        self.firewall_serials = [
            "007051000012345", "007051000054321", "007051000098765",
            "007201000012345", "007201000054321"
        ]
        
        # Initialize data pools
        self._init_data_pools()
    
    def _init_data_pools(self):
        """Initialize data pools for realistic generation."""
        # Source and destination IPs (RFC 1918 and public IPs)
        self.source_ips = [
            "192.168.1.100", "192.168.1.101", "192.168.1.102",
            "10.0.0.50", "10.0.0.51", "10.0.0.52",
            "172.16.0.25", "172.16.0.26", "172.16.0.27"
        ]
        
        self.destination_ips = [
            "8.8.8.8", "1.1.1.1", "9.9.9.9",
            "208.67.222.222", "208.67.220.220",
            "142.250.185.78", "52.114.128.90", "104.16.124.96"
        ]
        
        # Applications
        self.applications = [
            "ssl", "web-browsing", "dns", "http", "https", "ssh",
            "netbios", "ftp", "smtp", "pop3", "imap", "sql-server",
            "oracle", "mysql", "rdp", "vnc", "teamviewer", "zoom"
        ]
        
        # Users
        self.usernames = [
            "jsmith", "bjohnson", "rwilliams", "mjones", "mbrown",
            "ddavis", "jmiller", "rwilson", "amoore", "wtaylor"
        ]
        
        # Threat categories and names
        self.threat_categories = [
            "virus", "spyware", "vulnerability", "phishing", "command-and-control",
            "exploit", "malware", "ransomware", "trojan", "backdoor"
        ]
        
        self.threat_names = [
            "Generic Malware", "Trojan.Win32.Generic", "Phishing.Email.Generic",
            "Command.and.Control", "Exploit.Kit.Generic", "Ransomware.Win32.Generic",
            "Spyware.Generic", "Vulnerability.Generic", "Backdoor.Generic"
        ]
        
        # Zones
        self.zones = [
            "trust", "untrust", "dmz", "internal", "external",
            "guest", "wifi", "vpn", "management"
        ]
        
        # Firewall hostnames
        self.firewall_hostnames = [
            "pa-firewall-01", "pa-firewall-02", "pa-firewall-03",
            "palo-alto-01", "palo-alto-02", "security-gw-01"
        ]
    
    def generate_traffic_log(self, log_count: int = 1, **kwargs) -> List[Dict]:
        """
        Generate Palo Alto traffic logs in LEEF 2.0 format.
        
        Args:
            log_count: Number of logs to generate
            **kwargs: Override parameters
            
        Returns:
            List of event dictionaries
        """
        events = []
        
        for i in range(log_count):
            # Generate session data
            session_id = random.randint(1000000000, 9999999999)
            src_ip = kwargs.get('src_ip', random.choice(self.source_ips))
            dst_ip = kwargs.get('dst_ip', random.choice(self.destination_ips))
            src_port = kwargs.get('src_port', random.randint(1024, 65535))
            dst_port = kwargs.get('dst_port', random.choice([80, 443, 53, 22, 25, 3389]))
            app = kwargs.get('app', random.choice(self.applications))
            action = kwargs.get('action', random.choice(["allow", "deny", "drop"]))
            bytes_sent = kwargs.get('bytes_sent', random.randint(1000, 100000))
            bytes_received = kwargs.get('bytes_received', random.randint(100, 50000))
            packets_sent = kwargs.get('packets_sent', random.randint(10, 1000))
            packets_received = kwargs.get('packets_received', random.randint(5, 500))
            
            # Generate LEEF 2.0 format
            leef_parts = [
                f"LEEF:2.0|PaloAlto|PAN-OS|{self.panos_version.value}|TRAFFIC|{random.choice(['start', 'end'])}|",
                f"devTime={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"src={src_ip}",
                f"dst={dst_ip}",
                f"sourcePort={src_port}",
                f"destinationPort={dst_port}",
                f"app={app}",
                f"action={action}",
                f"bytesSent={bytes_sent}",
                f"bytesReceived={bytes_received}",
                f"packetsSent={packets_sent}",
                f"packetsReceived={packets_received}",
                f"sessionid={session_id}",
                f"protocol={random.choice(['tcp', 'udp', 'icmp'])}",
                f"rule={random.choice(['Outbound-Allow', 'Inbound-Deny', 'Default-Deny'])}",
                f"srcZone={random.choice(self.zones)}",
                f"dstZone={random.choice(self.zones)}",
                f"user={random.choice(self.usernames)}"
            ]
            
            leef_event = "".join(leef_parts)
            
            event = {
                "sourcetype": "paloalto:traffic",
                "timestamp": datetime.now().isoformat(),
                "host": random.choice(self.firewall_hostnames),
                "source": "syslog",
                "event": leef_event,
                "fields": {
                    "vendor": "Palo Alto Networks",
                    "product": "PAN-OS",
                    "version": self.panos_version.value,
                    "event_type": "traffic",
                    "severity": "medium" if action == "allow" else "high",
                    "session_id": session_id,
                    "src_ip": src_ip,
                    "dst_ip": dst_ip,
                    "src_port": src_port,
                    "dst_port": dst_port,
                    "application": app,
                    "action": action,
                    "bytes_sent": bytes_sent,
                    "bytes_received": bytes_received,
                    "packets_sent": packets_sent,
                    "packets_received": packets_received,
                    "protocol": kwargs.get('protocol', random.choice(['tcp', 'udp', 'icmp'])),
                    "rule_name": kwargs.get('rule_name', random.choice(['Outbound-Allow', 'Inbound-Deny', 'Default-Deny'])),
                    "src_zone": kwargs.get('src_zone', random.choice(self.zones)),
                    "dst_zone": kwargs.get('dst_zone', random.choice(self.zones)),
                    "user": kwargs.get('user', random.choice(self.usernames)),
                    "serial_number": random.choice(self.firewall_serials),
                    "generator": "authentic_paloalto",
                    "test_event": True
                }
            }
            
            events.append(event)
        
        return events
    
    def generate_threat_log(self, log_count: int = 1, **kwargs) -> List[Dict]:
        """
        Generate Palo Alto threat logs in LEEF 2.0 format.
        
        Args:
            log_count: Number of logs to generate
            **kwargs: Override parameters
            
        Returns:
            List of event dictionaries
        """
        events = []
        
        for i in range(log_count):
            threat_category = kwargs.get('threat_category', random.choice(self.threat_categories))
            threat_name = kwargs.get('threat_name', random.choice(self.threat_names))
            action = kwargs.get('action', random.choice(["block", "alert", "default"]))
            severity = kwargs.get('severity', random.choice(["critical", "high", "medium"]))
            
            # Generate LEEF 2.0 format
            leef_parts = [
                f"LEEF:2.0|PaloAlto|PAN-OS|{self.panos_version.value}|THREAT|{random.choice(['start', 'end'])}|",
                f"devTime={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                f"src={random.choice(self.source_ips)}",
                f"dst={random.choice(self.destination_ips)}",
                f"threatCategory={threat_category}",
                f"threatName={threat_name}",
                f"action={action}",
                f"severity={severity}",
                f"direction={random.choice(['inbound', 'outbound'])}",
                f"srcUser={random.choice(self.usernames)}",
                f"dstUser={random.choice(self.usernames)}",
                f"app={random.choice(self.applications)}",
                f"rule={random.choice(['Security-Policy', 'Threat-Policy', 'Default'])}",
                f"srcZone={random.choice(self.zones)}",
                f"dstZone={random.choice(self.zones)}",
                f"uriCategory={random.choice(['unknown', 'malware', 'phishing'])}",
                f"misc={'Sample misc field for ' + threat_name}"
            ]
            
            leef_event = "".join(leef_parts)
            
            event = {
                "sourcetype": "paloalto:threat",
                "timestamp": datetime.now().isoformat(),
                "host": random.choice(self.firewall_hostnames),
                "source": "syslog",
                "event": leef_event,
                "fields": {
                    "vendor": "Palo Alto Networks",
                    "product": "PAN-OS",
                    "version": self.panos_version.value,
                    "event_type": "threat",
                    "severity": severity,
                    "threat_category": threat_category,
                    "threat_name": threat_name,
                    "action": action,
                    "direction": kwargs.get('direction', random.choice(['inbound', 'outbound'])),
                    "src_ip": kwargs.get('src_ip', random.choice(self.source_ips)),
                    "dst_ip": kwargs.get('dst_ip', random.choice(self.destination_ips)),
                    "application": kwargs.get('application', random.choice(self.applications)),
                    "rule_name": kwargs.get('rule_name', random.choice(['Security-Policy', 'Threat-Policy', 'Default'])),
                    "src_zone": kwargs.get('src_zone', random.choice(self.zones)),
                    "dst_zone": kwargs.get('dst_zone', random.choice(self.zones)),
                    "src_user": kwargs.get('src_user', random.choice(self.usernames)),
                    "dst_user": kwargs.get('dst_user', random.choice(self.usernames)),
                    "uri_category": kwargs.get('uri_category', random.choice(['unknown', 'malware', 'phishing'])),
                    "serial_number": random.choice(self.firewall_serials),
                    "generator": "authentic_paloalto",
                    "test_event": True
                }
            }
            
            events.append(event)
        
        return events
    
    def generate_system_log(self, log_count: int = 1, **kwargs) -> List[Dict]:
        """
        Generate Palo Alto system logs in syslog format.
        
        Args:
            log_count: Number of logs to generate
            **kwargs: Override parameters
            
        Returns:
            List of event dictionaries
        """
        events = []
        
        system_event_types = [
            ("System", "configuration change"),
            ("System", "high availability state change"),
            ("System", "license expiration warning"),
            ("System", "user authentication"),
            ("System", "administrator login"),
            ("System", "administrator logout"),
            ("System", "service started"),
            ("System", "service stopped"),
            ("GlobalProtect", "gateway login"),
            ("GlobalProtect", "gateway logout"),
            ("GlobalProtect", "portal login"),
            ("GlobalProtect", "portal logout")
        ]
        
        for i in range(log_count):
            subsystem, event_desc = random.choice(system_event_types)
            severity_level = random.choice(["emergency", "alert", "critical", "error", "warning", "notice", "informational", "debug"])
            facility = random.randint(1, 23)
            
            # Generate RFC 5424 syslog format
            timestamp = datetime.now().strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
            hostname = random.choice(self.firewall_hostnames)
            app_name = "PAN-OS"
            proc_id = str(random.randint(1000, 9999))
            msg_id = f"ID{random.randint(10000, 99999)}"
            
            # Structured data (optional in RFC 5424)
            structured_data = f"[exampleSDID@32473 eventSource=\"{subsystem}\" eventID=\"{random.randint(1, 1000)}\"]"
            
            message = f"{subsystem}: {event_desc} performed by {random.choice(self.usernames)}"
            
            syslog_message = f"<{facility * 8 + random.randint(0, 7)}>1 {timestamp} {hostname} {app_name} {proc_id} {msg_id} {structured_data} {message}"
            
            event = {
                "sourcetype": "paloalto:system",
                "timestamp": datetime.now().isoformat(),
                "host": hostname,
                "source": "syslog",
                "event": syslog_message,
                "fields": {
                    "vendor": "Palo Alto Networks",
                    "product": "PAN-OS",
                    "version": self.panos_version.value,
                    "event_type": "system",
                    "severity": severity_level,
                    "subsystem": subsystem,
                    "event_description": event_desc,
                    "username": random.choice(self.usernames),
                    "facility": facility,
                    "app_name": app_name,
                    "process_id": proc_id,
                    "message_id": msg_id,
                    "serial_number": random.choice(self.firewall_serials),
                    "generator": "authentic_paloalto",
                    "test_event": True
                }
            }
            
            events.append(event)
        
        return events
    
    def generate_log(self, log_type: PaloAltoLogType, log_count: int = 1, **kwargs) -> List[Dict]:
        """
        Generate Palo Alto logs by type.
        
        Args:
            log_type: Type of log to generate
            log_count: Number of logs to generate
            **kwargs: Override parameters
            
        Returns:
            List of event dictionaries
        """
        generator_map = {
            PaloAltoLogType.TRAFFIC: self.generate_traffic_log,
            PaloAltoLogType.THREAT: self.generate_threat_log,
            PaloAltoLogType.SYSTEM: self.generate_system_log,
        }
        
        generator = generator_map.get(log_type)
        if not generator:
            raise ValueError(f"Unsupported log type: {log_type}")
        
        return generator(log_count, **kwargs)

# Integration with existing generator architecture
def generate_paloalto_events(sourcetype: str, count: int = 1, seed: Optional[int] = None) -> List[Dict]:
    """
    Generate Palo Alto events for integration with existing generator system.
    
    Args:
        sourcetype: Palo Alto sourcetype to generate
        count: Number of events to generate
        seed: Random seed for deterministic generation
        
    Returns:
        List of event dictionaries
    """
    generator = AuthenticPaloAltoGenerator(seed=seed)
    
    sourcetype_map = {
        "paloalto-traffic": PaloAltoLogType.TRAFFIC,
        "paloalto-threat": PaloAltoLogType.THREAT,
        "paloalto-system": PaloAltoLogType.SYSTEM,
        "paloalto-config": PaloAltoLogType.CONFIG,
        "paloalto-userid": PaloAltoLogType.USERID,
        "paloalto-globalprotect": PaloAltoLogType.GLOBALPROTECT,
        "paloalto-wildfire": PaloAltoLogType.WILDFIRE,
    }
    
    log_type = sourcetype_map.get(sourcetype)
    if not log_type:
        # Default to traffic logs if sourcetype not mapped
        log_type = PaloAltoLogType.TRAFFIC
    
    return generator.generate_log(log_type, count)

if __name__ == "__main__":
    # Test the generator
    print("🧪 Testing Authentic Palo Alto Generator")
    print("=" * 60)
    
    generator = AuthenticPaloAltoGenerator(seed=42)
    
    # Generate sample events
    traffic_events = generator.generate_traffic_log(2)
    threat_events = generator.generate_threat_log(2)
    system_events = generator.generate_system_log(2)
    
    print(f"Generated {len(traffic_events)} traffic events")
    print(f"Generated {len(threat_events)} threat events")
    print(f"Generated {len(system_events)} system events")
    
    # Show first event of each type
    print("\n📋 Sample Traffic Event:")
    print(f"  Sourcetype: {traffic_events[0]['sourcetype']}")
    print(f"  Event: {traffic_events[0]['event'][:100]}...")
    print(f"  Fields: {list(traffic_events[0]['fields'].keys())[:5]}...")
    
    print("\n📋 Sample Threat Event:")
    print(f"  Sourcetype: {threat_events[0]['sourcetype']}")
    print(f"  Event: {threat_events[0]['event'][:100]}...")
    print(f"  Fields: {list(threat_events[0]['fields'].keys())[:5]}...")
    
    print("\n📋 Sample System Event:")
    print(f"  Sourcetype: {system_events[0]['sourcetype']}")
    print(f"  Event: {system_events[0]['event'][:100]}...")
    print(f"  Fields: {list(system_events[0]['fields'].keys())[:5]}...")