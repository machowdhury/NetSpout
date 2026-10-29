#!/usr/bin/env python3
"""
Phase 4C P0: Build typed SNMP OID registry.
Analyze SNMP OID inventory and create typed registry for metrics generation.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from enum import Enum

BASE_DIR = Path(__file__).parent.absolute()
SNMP_INVENTORY_PATH = BASE_DIR / "backend" / "app" / "catalog_data" / "snmp_mib_oid_inventory.json"

class SNMPDataType(Enum):
    """SNMP data types."""
    INTEGER = "Integer32"
    COUNTER32 = "Counter32"
    COUNTER64 = "Counter64"
    GAUGE32 = "Gauge32"
    TIMETICKS = "TimeTicks"
    OCTET_STRING = "OCTET STRING"
    DISPLAY_STRING = "DisplayString"
    IP_ADDRESS = "IpAddress"
    UNKNOWN = "unknown"

class SNMPMetricSemantics(Enum):
    """SNMP metric semantics."""
    COUNTER = "counter"  # Monotonically increasing, may wrap
    GAUGE = "gauge"      # Instantaneous value, can go up/down
    DERIVE = "derive"    # Rate of change of counter
    ABSOLUTE = "absolute" # Counter that gets reset upon reading
    UNKNOWN = "unknown"

def analyze_snmp_inventory():
    """Analyze SNMP OID inventory and create typed registry."""
    
    print(f"\n{'='*60}")
    print(f"📊 SNMP OID INVENTORY ANALYSIS")
    print(f"{'='*60}")
    
    # Load inventory
    with open(SNMP_INVENTORY_PATH, 'r') as f:
        data = json.load(f)
    
    oids = data.get('rows', [])
    print(f"Total OIDs in inventory: {len(oids)}")
    
    # 1. Vendor distribution
    print(f"\n1. Vendor Distribution:")
    vendor_counts = {}
    for oid in oids:
        vendor = oid.get('vendor', 'unknown')
        vendor_counts[vendor] = vendor_counts.get(vendor, 0) + 1
    
    for vendor, count in sorted(vendor_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(oids)) * 100
        print(f"   {vendor:<10} {count:>4} ({pct:>5.1f}%)")
    
    # 2. Data type analysis
    print(f"\n2. Data Type Analysis:")
    type_counts = {}
    type_examples = {}
    
    for oid in oids:
        engine_type = oid.get('engine_type', 'unknown')
        type_counts[engine_type] = type_counts.get(engine_type, 0) + 1
        
        if engine_type not in type_examples:
            type_examples[engine_type] = {
                'name': oid.get('engine_name', 'N/A'),
                'oid': oid.get('engine_oid', 'N/A'),
                'desc': oid.get('engine_desc', 'N/A')[:50]
            }
    
    for dtype, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        pct = (count / len(oids)) * 100
        example = type_examples.get(dtype, {})
        print(f"   {dtype:<20} {count:>4} ({pct:>5.1f}%)")
        if example:
            print(f"     Example: {example['name']} - {example['desc']}")
    
    # 3. MIB module analysis
    print(f"\n3. MIB Module Analysis:")
    module_counts = {}
    for oid in oids:
        module = oid.get('engine_module', 'unknown')
        module_counts[module] = module_counts.get(module, 0) + 1
    
    print(f"   Top 10 MIB modules:")
    for module, count in sorted(module_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
        pct = (count / len(oids)) * 100
        print(f"     {module:<20} {count:>4} ({pct:>5.1f}%)")
    
    # 4. OID syntax validation
    print(f"\n4. OID Syntax Validation:")
    valid_oids = []
    invalid_oids = []
    
    for oid in oids:
        engine_oid = oid.get('engine_oid', '')
        if engine_oid and re.match(r'^\d+(\.\d+)+$', engine_oid):
            valid_oids.append(oid)
        else:
            invalid_oids.append(oid)
    
    print(f"   Valid OID syntax: {len(valid_oids)}/{len(oids)} ({len(valid_oids)/len(oids)*100:.1f}%)")
    print(f"   Invalid/missing: {len(invalid_oids)}/{len(oids)}")
    
    if invalid_oids and len(invalid_oids) < 5:
        print(f"   Invalid examples:")
        for oid in invalid_oids[:3]:
            print(f"     {oid.get('engine_name', 'N/A')}: {oid.get('engine_oid', 'N/A')}")
    
    # 5. Create typed registry
    print(f"\n5. Creating Typed OID Registry...")
    
    typed_registry = []
    interface_oids = []
    system_oids = []
    counter_oids = []
    gauge_oids = []
    
    for oid in valid_oids:
        entry = {
            'oid': oid.get('engine_oid'),
            'name': oid.get('engine_name', ''),
            'description': oid.get('engine_desc', ''),
            'module': oid.get('engine_module', ''),
            'vendor': oid.get('vendor', ''),
            'type': oid.get('engine_type', 'unknown'),
            'semantics': infer_semantics(oid),
            'unit': infer_unit(oid),
            'index_dimensions': infer_index_dimensions(oid),
            'validation_status': oid.get('status', 'unknown'),
            'coverage_ok': oid.get('coverage_ok', False)
        }
        
        typed_registry.append(entry)
        
        # Categorize
        if 'if' in entry['name'].lower() or 'interface' in entry['description'].lower():
            interface_oids.append(entry)
        elif 'system' in entry['name'].lower() or 'sys' in entry['name'].lower():
            system_oids.append(entry)
        
        if entry['semantics'] == SNMPMetricSemantics.COUNTER:
            counter_oids.append(entry)
        elif entry['semantics'] == SNMPMetricSemantics.GAUGE:
            gauge_oids.append(entry)
    
    print(f"   Created registry with {len(typed_registry)} typed OIDs")
    print(f"   Interface OIDs: {len(interface_oids)}")
    print(f"   System OIDs: {len(system_oids)}")
    print(f"   Counter semantics: {len(counter_oids)}")
    print(f"   Gauge semantics: {len(gauge_oids)}")
    
    # 6. Show representative OIDs for metrics generation
    print(f"\n6. Representative OIDs for Metrics Generation:")
    
    print(f"\n   Interface Status & Counters:")
    interface_samples = [
        oid for oid in interface_oids 
        if any(keyword in oid['name'].lower() for keyword in ['ifindex', 'ifoperstatus', 'ifinoctets', 'ifoutoctets'])
    ][:5]
    
    for oid in interface_samples:
        print(f"     {oid['name']} ({oid['oid']})")
        print(f"       Type: {oid['type']}, Semantics: {oid['semantics'].value}")
        print(f"       Desc: {oid['description'][:60]}...")
    
    print(f"\n   System Metrics:")
    system_samples = [
        oid for oid in system_oids
        if any(keyword in oid['name'].lower() for keyword in ['sysuptime', 'cpuload', 'mem', 'storage'])
    ][:5]
    
    for oid in system_samples:
        print(f"     {oid['name']} ({oid['oid']})")
        print(f"       Type: {oid['type']}, Semantics: {oid['semantics'].value}")
        print(f"       Desc: {oid['description'][:60]}...")
    
    # Save typed registry
    registry_path = BASE_DIR / "snmp_typed_registry.json"
    with open(registry_path, 'w') as f:
        json.dump(typed_registry, f, indent=2)
    
    print(f"\n📁 Typed registry saved to: {registry_path}")
    
    return typed_registry

def infer_semantics(oid: Dict) -> SNMPMetricSemantics:
    """Infer metric semantics from OID properties."""
    engine_type = oid.get('engine_type', '').lower()
    name = oid.get('engine_name', '').lower()
    desc = oid.get('engine_desc', '').lower()
    
    # Counter types
    if 'counter' in engine_type or 'counter' in name:
        return SNMPMetricSemantics.COUNTER
    
    # Gauge types
    if 'gauge' in engine_type or 'gauge' in name:
        return SNMPMetricSemantics.GAUGE
    
    # Time ticks (usually counters)
    if 'timetick' in engine_type:
        return SNMPMetricSemantics.COUNTER
    
    # Based on description keywords
    if any(keyword in desc for keyword in ['counter', 'count', 'total', 'accumulated']):
        return SNMPMetricSemantics.COUNTER
    
    if any(keyword in desc for keyword in ['current', 'level', 'utilization', 'percentage', 'rate']):
        return SNMPMetricSemantics.GAUGE
    
    # Default based on common patterns
    if any(keyword in name for keyword in ['octets', 'packets', 'errors', 'discards']):
        return SNMPMetricSemantics.COUNTER
    
    if any(keyword in name for keyword in ['status', 'state', 'load', 'util']):
        return SNMPMetricSemantics.GAUGE
    
    return SNMPMetricSemantics.UNKNOWN

def infer_unit(oid: Dict) -> str:
    """Infer unit from OID properties."""
    desc = oid.get('engine_desc', '').lower()
    name = oid.get('engine_name', '').lower()
    
    if 'octet' in desc or 'byte' in desc:
        return 'bytes'
    elif 'packet' in desc:
        return 'packets'
    elif 'second' in desc:
        return 'seconds'
    elif 'millisecond' in desc:
        return 'milliseconds'
    elif 'percentage' in desc or 'percent' in desc:
        return 'percent'
    elif 'uptime' in name:
        return 'seconds'
    elif any(keyword in desc for keyword in ['temperature', 'celsius', 'fahrenheit']):
        return 'degrees_celsius'
    
    return ''

def infer_index_dimensions(oid: Dict) -> List[str]:
    """Infer index dimensions from OID properties."""
    dimensions = []
    desc = oid.get('engine_desc', '').lower()
    name = oid.get('engine_name', '').lower()
    
    if 'interface' in desc or 'if' in name:
        dimensions.append('interface')
    
    if 'cpu' in desc or 'processor' in desc:
        dimensions.append('cpu')
    
    if 'memory' in desc:
        dimensions.append('memory_pool')
    
    if 'storage' in desc or 'disk' in desc:
        dimensions.append('storage')
    
    return dimensions

def create_snmp_metrics_generator(registry: List[Dict]):
    """Create SNMP metrics generator based on typed registry."""
    
    print(f"\n{'='*60}")
    print(f"🔧 CREATING SNMP METRICS GENERATOR")
    print(f"{'='*60}")
    
    generator_code = '''"""
SNMP Metrics Generator for PulseForge.
Generates realistic SNMP metrics based on typed OID registry.
Phase 4C implementation.
"""

import random
import time
import ipaddress
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum

class SNMPMetricType(Enum):
    """SNMP metric types for generation."""
    INTERFACE_STATUS = "interface_status"
    INTERFACE_TRAFFIC = "interface_traffic"
    INTERFACE_ERRORS = "interface_errors"
    SYSTEM_UPTIME = "system_uptime"
    CPU_UTILIZATION = "cpu_utilization"
    MEMORY_UTILIZATION = "memory_utilization"
    STORAGE_UTILIZATION = "storage_utilization"

class DeviceType(Enum):
    """Network device types."""
    ROUTER = "router"
    SWITCH = "switch"
    FIREWALL = "firewall"
    LOAD_BALANCER = "load_balancer"
    SERVER = "server"

class SNMPMetricsGenerator:
    """SNMP metrics generator based on typed OID registry."""
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize generator.
        
        Args:
            seed: Random seed for deterministic generation
        """
        if seed is not None:
            random.seed(seed)
        
        self.device_types = [DeviceType.ROUTER, DeviceType.SWITCH, DeviceType.FIREWALL]
        self.vendors = ['cisco', 'juniper', 'arista', 'paloalto']
        
        # Device pools
        self._init_device_pools()
        
        # OID mapping (simplified - in production would load from registry)
        self.oid_mapping = {
            SNMPMetricType.INTERFACE_STATUS: {
                'oid': '1.3.6.1.2.1.2.2.1.8',
                'name': 'ifOperStatus',
                'type': 'Integer32',
                'semantics': 'gauge',
                'values': {
                    1: 'up',
                    2: 'down',
                    3: 'testing',
                    4: 'unknown',
                    5: 'dormant',
                    6: 'notPresent',
                    7: 'lowerLayerDown'
                }
            },
            SNMPMetricType.INTERFACE_TRAFFIC: {
                'in_octets': {
                    'oid': '1.3.6.1.2.1.2.2.1.10',
                    'name': 'ifInOctets',
                    'type': 'Counter32',
                    'semantics': 'counter'
                },
                'out_octets': {
                    'oid': '1.3.6.1.2.1.2.2.1.16',
                    'name': 'ifOutOctets',
                    'type': 'Counter32',
                    'semantics': 'counter'
                }
            },
            SNMPMetricType.SYSTEM_UPTIME: {
                'oid': '1.3.6.1.2.1.1.3',
                'name': 'sysUpTime',
                'type': 'TimeTicks',
                'semantics': 'counter'
            },
            SNMPMetricType.CPU_UTILIZATION: {
                'oid': '1.3.6.1.4.1.9.9.109.1.1.1.1.5',
                'name': 'cpmCPUTotal5min',
                'type': 'Gauge32',
                'semantics': 'gauge',
                'unit': 'percent'
            }
        }
    
    def _init_device_pools(self):
        """Initialize device pools for realistic generation."""
        # Device hostnames
        self.hostnames = {
            DeviceType.ROUTER: [
                'core-router-01', 'core-router-02', 'edge-router-01',
                'isp-edge-01', 'dc-gateway-01'
            ],
            DeviceType.SWITCH: [
                'access-switch-01', 'distribution-switch-01',
                'core-switch-01', 'top-of-rack-01', 'spine-01'
            ],
            DeviceType.FIREWALL: [
                'fw-perimeter-01', 'fw-dmz-01',
                'fw-internal-01', 'pa-firewall-01'
            ]
        }
        
        # Interface names
        self.interface_names = {
            DeviceType.ROUTER: [
                'GigabitEthernet0/0', 'GigabitEthernet0/1',
                'TenGigabitEthernet1/0', 'TenGigabitEthernet1/1',
                'Serial0/0/0', 'Serial0/0/1'
            ],
            DeviceType.SWITCH: [
                'GigabitEthernet1/0/1', 'GigabitEthernet1/0/2',
                'TenGigabitEthernet1/0/1', 'TenGigabitEthernet1/0/2',
                'Vlan10', 'Vlan20'
            ],
            DeviceType.FIREWALL: [
                'ethernet1/1', 'ethernet1/2',
                'ethernet1/3', 'ethernet1/4'
            ]
        }
    
    def generate_interface_metrics(self, count: int = 1, device_type: Optional[DeviceType] = None, **kwargs) -> List[Dict]:
        """
        Generate interface metrics.
        
        Args:
            count: Number of metric sets to generate
            device_type: Type of device
            **kwargs: Override parameters
            
        Returns:
            List of metric events
        """
        if device_type is None:
            device_type = random.choice(self.device_types)
        
        events = []
        
        for i in range(count):
            # Device identity
            hostname = kwargs.get('hostname', random.choice(self.hostnames[device_type]))
            vendor = kwargs.get('vendor', random.choice(self.vendors))
            
            # Interface selection
            interface_count = random.randint(1, 8)
            base_interface_idx = random.randint(1, 48)
            
            for if_idx in range(base_interface_idx, base_interface_idx + interface_count):
                interface_name = kwargs.get('interface_name', 
                    f"{random.choice(self.interface_names[device_type])}{if_idx}")
                
                # Interface status (1=up, 2=down, etc.)
                status_value = random.choices([1, 1, 1, 2, 3], weights=[85, 5, 5, 3, 2])[0]
                
                # Traffic counters (simulate increment)
                in_octets = random.randint(1000000, 1000000000)
                out_octets = random.randint(1000000, 1000000000)
                
                # Error counters
                in_errors = random.randint(0, 100)
                out_errors = random.randint(0, 100)
                in_discards = random.randint(0, 50)
                out_discards = random.randint(0, 50)
                
                # Generate metric events
                timestamp = datetime.now()
                
                # Interface status metric
                status_event = {
                    "time": int(timestamp.timestamp()),
                    "event": "metric",
                    "host": hostname,
                    "source": "snmp",
                    "sourcetype": "snmp:metric",
                    "fields": {
                        "metric_name": "ifOperStatus",
                        "_value": status_value,
                        "oid": self.oid_mapping[SNMPMetricType.INTERFACE_STATUS]['oid'],
                        "interface": interface_name,
                        "vendor": vendor,
                        "device_type": device_type.value,
                        "status_text": self.oid_mapping[SNMPMetricType.INTERFACE_STATUS]['values'][status_value],
                        "unit": "status_code",
                        "semantics": "gauge",
                        "snmp_generated": True,
                        "test_metric": True
                    }
                }
                
                # Traffic in metric
                traffic_in_event = {
                    "time": int(timestamp.timestamp()),
                    "event": "metric",
                    "host": hostname,
                    "source": "snmp",
                    "sourcetype": "snmp:metric",
                    "fields": {
                        "metric_name": "ifInOctets",
                        "_value": in_octets,
                        "oid": self.oid_mapping[SNMPMetricType.INTERFACE_TRAFFIC]['in_octets']['oid'],
                        "interface": interface_name,
                        "vendor": vendor,
                        "device_type": device_type.value,
                        "unit": "bytes",
                        "semantics": "counter",
                        "snmp_generated": True,
                        "test_metric": True
                    }
                }
                
                # Traffic out metric
                traffic_out_event = {
                    "time": int(timestamp.timestamp()),
                    "event": "metric",
                    "host": hostname,
                    "source": "snmp",
                    "sourcetype": "snmp:metric",
                    "fields": {
                        "metric_name": "ifOutOctets",
                        "_value": out_octets,
                        "oid": self.oid_mapping[SNMPMetricType.INTERFACE_TRAFFIC]['out_octets']['oid'],
                        "interface": interface_name,
                        "vendor": vendor,
                        "device_type": device_type.value,
                        "unit": "bytes",
                        "semantics": "counter",
                        "snmp_generated": True,
                        "test_metric": True
                    }
                }
                
                events.extend([status_event, traffic_in_event, traffic_out_event])
        
        return events
    
    def generate_system_metrics(self, count: int = 1, **kwargs) -> List[Dict]:
        """
        Generate system metrics.
        
        Args:
            count: Number of metric sets to generate
            **kwargs: Override parameters
            
        Returns:
            List of metric events
        """
        events = []
        
        for i in range(count):
            device_type = kwargs.get('device_type', random.choice(self.device_types))
            hostname = kwargs.get('hostname', random.choice(self.hostnames[device_type]))
            vendor = kwargs.get('vendor', random.choice(self.vendors))
            
            timestamp = datetime.now()
            
            # System uptime (in hundredths of seconds)
            uptime = random.randint(8640000, 864000000)  # 1-100 days in hundredths
            
            # CPU utilization (0-100%)
            cpu_util = random.randint(5, 80)
            
            # Memory utilization (0-100%)
            memory_util = random.randint(20, 90)
            
            # Uptime metric
            uptime_event = {
                "time": int(timestamp.timestamp()),
                "event": "metric",
                "host": hostname,
                "source": "snmp",
                "sourcetype": "snmp:metric",
                "fields": {
                    "metric_name": "sysUpTime",
                    "_value": uptime,
                    "oid": self.oid_mapping[SNMPMetricType.SYSTEM_UPTIME]['oid'],
                    "vendor": vendor,
                    "device_type": device_type.value,
                    "unit": "hundredths_seconds",
                    "semantics": "counter",
                    "uptime_days": uptime / 8640000,
                    "snmp_generated": True,
                    "test_metric": True
                }
            }
            
            # CPU utilization metric
            cpu_event = {
                "time": int(timestamp.timestamp()),
                "event": "metric",
                "host": hostname,
                "source": "snmp",
                "sourcetype": "snmp:metric",
                "fields": {
                    "metric_name": "cpuUtilization",
                    "_value": cpu_util,
                    "oid": self.oid_mapping[SNMPMetricType.CPU_UTILIZATION]['oid'],
                    "vendor": vendor,
                    "device_type": device_type.value,
                    "unit": "percent",
                    "semantics": "gauge",
                    "snmp_generated": True,
                    "test_metric": True
                }
            }
            
            # Memory utilization metric
            memory_event = {
                "time": int(timestamp.timestamp()),
                "event": "metric",
                "host": hostname,
                "source": "snmp",
                "sourcetype": "snmp:metric",
                "fields": {
                    "metric_name": "memoryUtilization",
                    "_value": memory_util,
                    "vendor": vendor,
                    "device_type": device_type.value,
                    "unit": "percent",
                    "semantics": "gauge",
                    "snmp_generated": True,
                    "test_metric": True
                }
            }
            
            events.extend([uptime_event, cpu_event, memory_event])
        
        return events
    
    def generate_metrics_batch(self, metric_types: List[SNMPMetricType], device_count: int = 3, **kwargs) -> List[Dict]:
        """
        Generate a batch of SNMP metrics.
        
        Args:
            metric_types: Types of metrics to generate
            device_count: Number of devices to generate metrics for
            **kwargs: Override parameters
            
        Returns:
            List of metric events
        """
        events = []
        
        for device_idx in range(device_count):
            device_type = random.choice(self.device_types)
            
            for metric_type in metric_types:
                if metric_type in [SNMPMetricType.INTERFACE_STATUS, 
                                  SNMPMetricType.INTERFACE_TRAFFIC,
                                  SNMPMetricType.INTERFACE_ERRORS]:
                    # Interface metrics
                    if_events = self.generate_interface_metrics(
                        count=random.randint(2, 6),
                        device_type=device_type,
                        **kwargs
                    )
                    events.extend(if_events)
                
                elif metric_type in [SNMPMetricType.SYSTEM_UPTIME,
                                    SNMPMetricType.CPU_UTILIZATION,
                                    SNMPMetricType.MEMORY_UTILIZATION]:
                    # System metrics
                    sys_events = self.generate_system_metrics(
                        count=1,
                        device_type=device_type,
                        **kwargs
                    )
                    events.extend(sys_events)
        
        return events

def generate_snmp_metrics(metric_types: List[str], count: int = 10, seed: Optional[int] = None) -> List[Dict]:
    """
    Generate SNMP metrics for integration with existing generator system.
    
    Args:
        metric_types: List of metric type strings
        count: Approximate number of metric events to generate
        seed: Random seed for deterministic generation
        
    Returns:
        List of metric events
    """
    generator = SNMPMetricsGenerator(seed=seed)
    
    # Convert string metric types to enum
    enum_types = []
    type_map = {
        'interface_status': SNMPMetricType.INTERFACE_STATUS,
        'interface_traffic': SNMPMetricType.INTERFACE_TRAFFIC,
        'interface_errors': SNMPMetricType.INTERFACE_ERRORS,
        'system_uptime': SNMPMetricType.SYSTEM_UPTIME,
        'cpu_utilization': SNMPMetricType.CPU_UTILIZATION,
        'memory_utilization': SNMPMetricType.MEMORY_UTILIZATION,
        'storage_utilization': SNMPMetricType.STORAGE_UTILIZATION
    }
    
    for mt in metric_types:
        if mt in type_map:
            enum_types.append(type_map[mt])
    
    if not enum_types:
        # Default to interface and system metrics
        enum_types = [SNMPMetricType.INTERFACE_STATUS, SNMPMetricType.INTERFACE_TRAFFIC, SNMPMetricType.SYSTEM_UPTIME]
    
    # Estimate device count based on desired event count
    # Each device generates multiple metrics
    device_count = max(1, count // 10)
    
    return generator.generate_metrics_batch(enum_types, device_count=device_count)

if __name__ == "__main__":
    # Test the generator
    print("🧪 Testing SNMP Metrics Generator")
    print("=" * 60)
    
    generator = SNMPMetricsGenerator(seed=42)
    
    # Generate sample metrics
    interface_events = generator.generate_interface_metrics(count=2)
    system_events = generator.generate_system_metrics(count=2)
    
    print(f"Generated {len(interface_events)} interface metric events")
    print(f"Generated {len(system_events)} system metric events")
    
    # Show sample events
    print("\\n📋 Sample Interface Metric:")
    if interface_events:
        event = interface_events[0]
        print(f"  Metric: {event['fields']['metric_name']}")
        print(f"  Value: {event['fields']['_value']}")
        print(f"  Host: {event['host']}")
        print(f"  Interface: {event['fields'].get('interface', 'N/A')}")
        print(f"  OID: {event['fields'].get('oid', 'N/A')}")
    
    print("\\n📋 Sample System Metric:")
    if system_events:
        event = system_events[0]
        print(f"  Metric: {event['fields']['metric_name']}")
        print(f"  Value: {event['fields']['_value']}")
        print(f"  Host: {event['host']}")
        print(f"  Unit: {event['fields'].get('unit', 'N/A')}")
    '''
    
    generator_path = BASE_DIR / "backend" / "app" / "snmp_metrics_generator.py"
    with open(generator_path, 'w') as f:
        f.write(generator_code)
    
    print(f"✅ Created generator: {generator_path}")
    print(f"   Includes interface and system metrics")
    print(f"   Realistic device and interface modeling")
    print(f"   Counter and gauge semantics")
    
    return generator_path

def main():
    """Main entry point."""
    print("Starting Phase 4C SNMP OID Registry Analysis...")
    
    # Analyze SNMP inventory
    registry = analyze_snmp_inventory()
    
    # Create metrics generator
    generator_path = create_snmp_metrics_generator(registry)
    
    print(f"\n{'='*60}")
    print(f"✅ PHASE 4C P0 SNMP FOUNDATION COMPLETE")
    print(f"{'='*60}")
    
    print(f"\n🎯 Next steps:")
    print(f"   1. Test SNMP metrics generator")
    print(f"   2. Integrate with existing metric pipeline")
    print(f"   3. Test Splunk mstats indexing")
    print(f"   4. Create Palo Alto live acceptance test")
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())