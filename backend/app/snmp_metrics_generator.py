"""
SNMP Metrics Generator for PulseForge.
Produces SC4SNMP-compatible metric events for Splunk indexing.
Phase 4C implementation.
"""

import random
import time
import json
import ipaddress
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from pathlib import Path

class SNMPMetricType(Enum):
    """SNMP metric types."""
    INTERFACE_STATUS = "interface_status"
    INTERFACE_TRAFFIC = "interface_traffic"
    INTERFACE_ERRORS = "interface_errors"
    SYSTEM_UPTIME = "system_uptime"
    CPU_UTILIZATION = "cpu_utilization"
    MEMORY_UTILIZATION = "memory_utilization"
    TEMPERATURE = "temperature"

class SNMPMetricsGenerator:
    """Generates realistic SNMP metrics for network devices."""
    
    def __init__(self, seed: Optional[int] = None):
        """Initialize generator."""
        if seed is not None:
            random.seed(seed)
        
        # Load SNMP OID inventory
        self.oid_registry = self._load_oid_registry()
        
        # Device configuration
        self.device_configs = [
            {
                "hostname": "core-router-01",
                "vendor": "cisco",
                "device_type": "router",
                "model": "ISR 4451",
                "location": "nyc",
                "interfaces": [
                    {"name": "GigabitEthernet0/0", "description": "Uplink to ISP"},
                    {"name": "GigabitEthernet0/1", "description": "To core-switch-01"},
                    {"name": "TenGigabitEthernet1/0", "description": "To distribution-01"}
                ]
            },
            {
                "hostname": "access-switch-01",
                "vendor": "arista",
                "device_type": "switch",
                "model": "DCS-7050SX3",
                "location": "sfo",
                "interfaces": [
                    {"name": "Ethernet1/1", "description": "To server-01"},
                    {"name": "Ethernet1/2", "description": "To server-02"},
                    {"name": "Ethernet1/3", "description": "To workstation-01"}
                ]
            },
            {
                "hostname": "fw-perimeter-01",
                "vendor": "paloalto",
                "device_type": "firewall",
                "model": "PA-5220",
                "location": "dfw",
                "interfaces": [
                    {"name": "ethernet1/1", "description": "Untrusted zone"},
                    {"name": "ethernet1/2", "description": "DMZ zone"},
                    {"name": "ethernet1/3", "description": "Trusted zone"}
                ]
            }
        ]
        
        # Device state tracking
        self.device_states = {}
        
        # Initialize device states
        for device in self.device_configs:
            device_id = device["hostname"]
            self.device_states[device_id] = {
                "uptime_counter": random.randint(8640000, 86400000),  # 1-100 days in hundredths
                "interface_counters": {},
                "cpu_history": [],
                "memory_history": [],
                "last_sample_time": datetime.now()
            }
            
            # Initialize interface counters
            for interface in device["interfaces"]:
                self.device_states[device_id]["interface_counters"][interface["name"]] = {
                    "in_octets": random.randint(1000000, 1000000000),
                    "out_octets": random.randint(1000000, 1000000000),
                    "in_errors": random.randint(0, 100),
                    "out_errors": random.randint(0, 100),
                    "in_discards": random.randint(0, 50),
                    "out_discards": random.randint(0, 50),
                    "oper_status": 1  # 1=up, 2=down, 3=testing
                }
    
    def _load_oid_registry(self) -> List[Dict]:
        """Load SNMP OID registry from inventory."""
        inventory_path = Path(__file__).parent / "catalog_data" / "snmp_mib_oid_inventory.json"
        
        try:
            with open(inventory_path, 'r') as f:
                data = json.load(f)
            
            registry = []
            for oid in data.get("rows", []):
                registry.append({
                    "oid": oid.get("engine_oid"),
                    "name": oid.get("engine_name", ""),
                    "description": oid.get("engine_desc", ""),
                    "module": oid.get("engine_module", ""),
                    "vendor": oid.get("vendor", ""),
                    "type": oid.get("engine_type", ""),
                    "status": oid.get("status", "")
                })
            
            return registry
        except Exception as e:
            print(f"Warning: Could not load OID registry: {e}")
            return []
    
    def _create_sc4snmp_metric_event(self, device: Dict, metric_data: Dict) -> Dict:
        """Create a SC4SNMP-compatible metric event."""
        timestamp = int(datetime.now().timestamp())
        
        # Create the metric event structure
        event = {
            "time": timestamp,
            "event": "metric",
            "host": device["hostname"],
            "source": "snmp",
            "sourcetype": "sc4snmp:event",
            "fields": {
                "metric_name": metric_data["metric_name"],
                "_value": metric_data["value"],
                "oid": metric_data.get("oid", ""),
                "sourcetype": "sc4snmp:event",  # Added for canonical resolution
                "index": "cisco_mdt_metrics",  # Standard SC4SNMP metrics index
                "vendor": device["vendor"],
                "device_type": device["device_type"],
                "model": device["model"],
                "location": device["location"],
                "unit": metric_data.get("unit", ""),
                "semantics": metric_data.get("semantics", "gauge"),
                "snmp_generated": True,
                "test_run": True,
                "netspout_generated": True
            }
        }
        
        # Add interface-specific fields
        if "interface" in metric_data:
            event["fields"]["interface"] = metric_data["interface"]
            event["fields"]["interface_description"] = metric_data.get("interface_description", "")
        
        # Add metric-specific metadata
        if metric_data["metric_name"] == "ifOperStatus":
            status_map = {1: "up", 2: "down", 3: "testing", 4: "unknown"}
            event["fields"]["status_text"] = status_map.get(metric_data["value"], "unknown")
        
        return event
    
    def generate_interface_metrics(self, device: Dict) -> List[Dict]:
        """Generate interface metrics for a device."""
        events = []
        device_id = device["hostname"]
        device_state = self.device_states[device_id]
        
        for interface in device["interfaces"]:
            interface_name = interface["name"]
            counters = device_state["interface_counters"][interface_name]
            
            # Update counters (simulate traffic)
            traffic_increment = random.randint(1000, 1000000)
            counters["in_octets"] += traffic_increment
            counters["out_octets"] += traffic_increment // 2
            
            # 1% chance of counter reset (wrap)
            if random.random() < 0.01:
                counters["in_octets"] = random.randint(1000, 1000000)
                counters["out_octets"] = random.randint(1000, 1000000)
            
            # 2% chance of interface status change
            if random.random() < 0.02:
                counters["oper_status"] = random.choices([1, 2, 3], weights=[95, 3, 2])[0]
            
            # Interface status metric
            status_event = self._create_sc4snmp_metric_event(
                device,
                {
                    "metric_name": "ifOperStatus",
                    "value": counters["oper_status"],
                    "oid": "1.3.6.1.2.1.2.2.1.8",
                    "interface": interface_name,
                    "interface_description": interface.get("description", ""),
                    "unit": "status_code",
                    "semantics": "gauge"
                }
            )
            events.append(status_event)
            
            # Inbound octets metric
            in_octets_event = self._create_sc4snmp_metric_event(
                device,
                {
                    "metric_name": "ifInOctets",
                    "value": counters["in_octets"],
                    "oid": "1.3.6.1.2.1.2.2.1.10",
                    "interface": interface_name,
                    "interface_description": interface.get("description", ""),
                    "unit": "bytes",
                    "semantics": "counter"
                }
            )
            events.append(in_octets_event)
            
            # Outbound octets metric
            out_octets_event = self._create_sc4snmp_metric_event(
                device,
                {
                    "metric_name": "ifOutOctets",
                    "value": counters["out_octets"],
                    "oid": "1.3.6.1.2.1.2.2.1.16",
                    "interface": interface_name,
                    "interface_description": interface.get("description", ""),
                    "unit": "bytes",
                    "semantics": "counter"
                }
            )
            events.append(out_octets_event)
            
            # Inbound errors metric
            errors_event = self._create_sc4snmp_metric_event(
                device,
                {
                    "metric_name": "ifInErrors",
                    "value": counters["in_errors"],
                    "oid": "1.3.6.1.2.1.2.2.1.14",
                    "interface": interface_name,
                    "interface_description": interface.get("description", ""),
                    "unit": "errors",
                    "semantics": "counter"
                }
            )
            events.append(errors_event)
        
        return events
    
    def generate_system_metrics(self, device: Dict) -> List[Dict]:
        """Generate system metrics for a device."""
        events = []
        device_id = device["hostname"]
        device_state = self.device_states[device_id]
        
        # Update uptime (increment by time since last sample)
        now = datetime.now()
        time_diff = (now - device_state["last_sample_time"]).total_seconds()
        device_state["uptime_counter"] += int(time_diff * 100)  # Convert to hundredths
        device_state["last_sample_time"] = now
        
        # System uptime metric
        uptime_event = self._create_sc4snmp_metric_event(
            device,
            {
                "metric_name": "sysUpTime",
                "value": device_state["uptime_counter"],
                "oid": "1.3.6.1.2.1.1.3",
                "unit": "hundredths_seconds",
                "semantics": "counter"
            }
        )
        events.append(uptime_event)
        
        # CPU utilization (realistic pattern based on time of day)
        hour = now.hour
        if 9 <= hour <= 17:  # Business hours
            cpu_util = random.randint(30, 80)
        elif 18 <= hour <= 22:  # Evening
            cpu_util = random.randint(15, 40)
        else:  # Night
            cpu_util = random.randint(5, 20)
        
        cpu_event = self._create_sc4snmp_metric_event(
            device,
            {
                "metric_name": "cpuUtilization",
                "value": cpu_util,
                "oid": "1.3.6.1.4.1.9.9.109.1.1.1.1.5",  # Cisco CPU 5-minute avg
                "unit": "percent",
                "semantics": "gauge"
            }
        )
        events.append(cpu_event)
        
        # Memory utilization
        memory_util = random.randint(40, 90)
        memory_event = self._create_sc4snmp_metric_event(
            device,
            {
                "metric_name": "memoryUtilization",
                "value": memory_util,
                "unit": "percent",
                "semantics": "gauge"
            }
        )
        events.append(memory_event)
        
        # Temperature (simulate realistic range)
        temperature = random.randint(25, 45)
        temp_event = self._create_sc4snmp_metric_event(
            device,
            {
                "metric_name": "temperature",
                "value": temperature,
                "oid": "1.3.6.1.4.1.9.9.13.1.3.1.3",  # Cisco environmental temperature
                "unit": "celsius",
                "semantics": "gauge"
            }
        )
        events.append(temp_event)
        
        return events
    
    def generate_metrics_batch(self, device_count: Optional[int] = None) -> List[Dict]:
        """Generate a batch of SNMP metrics."""
        events = []
        
        # Select devices to generate metrics for
        if device_count is None or device_count >= len(self.device_configs):
            devices = self.device_configs
        else:
            devices = random.sample(self.device_configs, device_count)
        
        for device in devices:
            # Generate interface metrics
            interface_events = self.generate_interface_metrics(device)
            events.extend(interface_events)
            
            # Generate system metrics
            system_events = self.generate_system_metrics(device)
            events.extend(system_events)
        
        return events

def generate_snmp_metrics(count: int = 20, seed: Optional[int] = None) -> List[Dict]:
    """
    Generate SNMP metrics for integration.
    
    Args:
        count: Approximate number of metric events to generate
        seed: Random seed for deterministic generation
    
    Returns:
        List of metric events
    """
    generator = SNMPMetricsGenerator(seed=seed)
    
    # Estimate device count based on desired event count
    # Each device generates ~10-15 metrics
    device_count = max(1, min(3, count // 10))
    
    # Generate metrics
    events = generator.generate_metrics_batch(device_count)
    
    # Limit to requested count if needed
    if len(events) > count:
        events = events[:count]
    
    return events

if __name__ == "__main__":
    """Test the SNMP metrics generator."""
    print("🧪 Testing SNMP Metrics Generator (SC4SNMP-compatible)")
    print("=" * 60)
    
    # Generate sample metrics
    generator = SNMPMetricsGenerator(seed=42)
    events = generator.generate_metrics_batch()
    
    print(f"✅ Generated {len(events)} SNMP metric events")
    
    # Show sample events
    print(f"\n📋 Sample Interface Metric:")
    interface_events = [e for e in events if "if" in e["fields"]["metric_name"].lower()]
    if interface_events:
        sample = interface_events[0]
        print(f"  Metric: {sample['fields']['metric_name']}")
        print(f"  Value: {sample['fields']['_value']}")
        print(f"  Host: {sample['host']}")
        print(f"  Sourcetype: {sample['sourcetype']}")
        print(f"  OID: {sample['fields'].get('oid', 'N/A')}")
        print(f"  Semantics: {sample['fields'].get('semantics', 'N/A')}")
        print(f"  Unit: {sample['fields'].get('unit', 'N/A')}")
    
    print(f"\n📋 Sample System Metric:")
    system_events = [e for e in events if "sys" in e["fields"]["metric_name"].lower() or 
                     "cpu" in e["fields"]["metric_name"].lower() or 
                     "memory" in e["fields"]["metric_name"].lower()]
    if system_events:
        sample = system_events[0]
        print(f"  Metric: {sample['fields']['metric_name']}")
        print(f"  Value: {sample['fields']['_value']}")
        print(f"  Host: {sample['host']}")
        print(f"  Sourcetype: {sample['sourcetype']}")
        print(f"  OID: {sample['fields'].get('oid', 'N/A')}")
        print(f"  Semantics: {sample['fields'].get('semantics', 'N/A')}")
    
    # Save sample to file
    output_file = Path(__file__).parent / "snmp_metrics_sample.json"
    with open(output_file, 'w') as f:
        json.dump(events[:10], f, indent=2)
    
    print(f"\n📁 Sample metrics saved to: {output_file}")
    
    # Generate example SPL queries
    print(f"\n🔍 Example Splunk SPL queries:")
    print(f"  search index=cisco_mdt_metrics sourcetype=sc4snmp:event")
    print(f"  | stats count by metric_name, host, vendor")
    print(f"\n  | mstats count WHERE index=cisco_mdt_metrics sourcetype=sc4snmp:event earliest=-5m latest=now")
    print(f"  | timechart span=1m count by metric_name")
    print(f"\n  | mstats avg(_value) WHERE index=cisco_mdt_metrics metric_name=ifInOctets earliest=-1h latest=now")
    print(f"  | timechart span=5m avg(_value) by host")
    
    print(f"\n{'=' * 60}")
    print(f"✅ SNMP Metrics Generator Ready for Splunk Integration")
    print(f"{'=' * 60}")