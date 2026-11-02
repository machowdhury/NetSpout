"""
Palo Alto Networks syslog generator for PulseForge.
Generates realistic Palo Alto PAN-OS logs in LEEF and syslog formats.
"""

import random
import json
from datetime import datetime
from typing import Dict, List, Any

def generate_paloalto_syslog(sourcetype: str, count: int = 1, seed: int = None) -> List[Dict]:
    """
    Generate Palo Alto Networks syslog events.
    
    Args:
        sourcetype: Type of Palo Alto log to generate
        count: Number of events to generate
        seed: Random seed for deterministic generation
        
    Returns:
        List of event dictionaries
    """
    if seed is not None:
        random.seed(seed)
    
    events = []
    sourcetype_map = {
        "paloalto-traffic": generate_paloalto_traffic,
        "paloalto-threat": generate_paloalto_threat,
        "paloalto-system": generate_paloalto_system,
        "paloalto-config": generate_paloalto_config,
        "paloalto-userid": generate_paloalto_userid,
        "paloalto-globalprotect": generate_paloalto_globalprotect,
        "paloalto-wildfire": generate_paloalto_wildfire,
        "paloalto-cortex": generate_paloalto_cortex
    }
    
    generator_func = sourcetype_map.get(sourcetype, generate_paloalto_traffic)
    
    for i in range(count):
        event = generator_func(i)
        events.append(event)
    
    return events

def generate_paloalto_traffic(index: int = 0) -> Dict:
    """Generate Palo Alto traffic log event."""
    src_ips = ["192.168.1.100", "10.0.0.50", "172.16.0.25", "192.168.2.150"]
    dst_ips = ["8.8.8.8", "1.1.1.1", "9.9.9.9", "208.67.222.222"]
    apps = ["ssl", "web-browsing", "dns", "http", "https", "ssh"]
    actions = ["allow", "deny", "drop"]
    
    event = {
        "sourcetype": "paloalto-traffic",
        "timestamp": datetime.now().isoformat(),
        "host": f"pa-firewall-{random.randint(1,5)}.example.com",
        "source": "syslog",
        "event": f"LEEF:2.0|PaloAlto|PAN-OS|10.1.0|TRAFFIC|{random.choice(['start', 'end', 'deny'])}|"
                f"src={random.choice(src_ips)} dst={random.choice(dst_ips)} "
                f"app={random.choice(apps)} action={random.choice(actions)}",
        "fields": {
            "vendor": "Palo Alto Networks",
            "product": "PAN-OS",
            "event_type": "traffic",
            "severity": "medium",
            "protocol": "tcp",
            "src_port": random.randint(1024, 65535),
            "dst_port": random.choice([80, 443, 53, 22]),
            "bytes_sent": random.randint(100, 10000),
            "bytes_received": random.randint(100, 5000),
            "test_event": True,
            "paloalto_generated": True
        }
    }
    return event

def generate_paloalto_threat(index: int = 0) -> Dict:
    """Generate Palo Alto threat log event."""
    threats = ["MALWARE", "PHISHING", "COMMAND-AND-CONTROL", "SPYWARE", "EXPLOIT"]
    categories = ["malware", "phishing", "command-and-control", "spyware", "vulnerability"]
    
    event = {
        "sourcetype": "paloalto-threat",
        "timestamp": datetime.now().isoformat(),
        "host": f"pa-firewall-{random.randint(1,5)}.example.com",
        "source": "syslog",
        "event": f"LEEF:2.0|PaloAlto|PAN-OS|10.1.0|THREAT|end|"
                f"threat=\"{random.choice(threats)}\" category=\"{random.choice(categories)}\"",
        "fields": {
            "vendor": "Palo Alto Networks",
            "product": "PAN-OS",
            "event_type": "threat",
            "severity": "high",
            "threat_name": random.choice(threats),
            "category": random.choice(categories),
            "action": "blocked",
            "test_event": True,
            "paloalto_generated": True
        }
    }
    return event

# Note: Full implementation would include all generator functions
# This stub provides the foundation for integration

if __name__ == "__main__":
    # Test generation
    test_events = generate_paloalto_syslog("paloalto-traffic", count=2)
    print(f"Generated {len(test_events)} Palo Alto events")
    for i, event in enumerate(test_events):
        print(f"Event {i+1}: {event['sourcetype']}")
