#!/usr/bin/env python3
"""
Phase 4C P0: Create SNMP metrics generator.
Build executable SNMP OID-backed metrics engine.
"""

import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum

BASE_DIR = Path(__file__).parent.absolute()
SNMP_INVENTORY_PATH = BASE_DIR / "backend" / "app" / "catalog_data" / "snmp_mib_oid_inventory.json"

class DeviceType(Enum):
    """Network device types."""
    ROUTER = "router"
    SWITCH = "switch"
    FIREWALL = "firewall"
    LOAD_BALANCER = "load_balancer"

class SNMPMetricGenerator:
    """SNMP metrics generator with realistic device modeling."""
    
    def __init__(self, seed: Optional[int] = None):
        """
        Initialize generator.
        
        Args:
            seed: Random seed for deterministic generation
        """
        if seed is not None:
            random.seed(seed)
        
        # Load SNMP OID inventory
        self.oid_registry = self._load_oid_registry()
        
        # Initialize device pools
        self._init_device_pools()
        
        # Device state tracking
        self.device_states = {}
    
    def _load_oid_registry(self) -> List[Dict]:
        """Load and categorize SNMP OID registry."""
        with open(SNMP_INVENTORY_PATH, 'r') as f:
            data = json.load(f)
        
        oids = data.get('rows', [])
        registry = []
        
        for oid in oids:
            entry = {
                'oid': oid.get('engine_oid'),
                'name': oid.get('engine_name', ''),
                'description': oid.get('engine_desc', ''),
                'module': oid.get('engine_module', ''),
                'vendor': oid.get('vendor', ''),
                'type': oid.get('engine_type', ''),
                'status': oid.get('status', ''),
                'coverage_ok': oid.get('coverage_ok', False)
            }
            
            # Categorize by function
            entry['category'] = self._categorize_oid(entry)
            entry['semantics'] = self._infer_semantics(entry)
            entry['unit'] = self._infer_unit(entry)
            
            registry.append(entry)
        
        return registry
    
    def _categorize_oid(self, oid: Dict) -> str:
        """Categorize OID by function."""
        name = oid['name'].lower()
        desc = oid['description'].lower()
        
        if 'if' in name and any(keyword in name for keyword in ['index', 'descr', 'type', 'mtu']):
            return 'interface_identity'
        elif 'if' in name and any(keyword in name for keyword in ['operstatus', 'adminstatus']):
            return 'interface_status'
        elif 'if' in name and any(keyword in name for keyword in ['inoctets', 'outoctets', 'inucastpkts', 'outucastpkts']):
            return 'interface_traffic'
        elif 'if' in name and any(keyword in name for keyword in ['inerrors', 'outerrors', 'indiscards', 'outdiscards']):
            return 'interface_errors'
        elif 'sysuptime' in name:
            return 'system_uptime'
        elif 'cpu' in name or 'load' in name:
            return 'cpu_utilization'
        elif 'memory' in name or 'mem' in name:
            return 'memory_utilization'
        elif 'storage' in name or 'disk' in name:
            return 'storage_utilization'
        elif 'temp' in name or 'temperature' in desc:
            return 'environment_temperature'
        elif 'fan' in name or 'power' in name:
            return 'environment_power'
        else:
            return 'other'
    
    def _infer_semantics(self, oid: Dict) -> str:
        """Infer metric semantics."""
        oid_type = oid['type'].lower()
        
        if 'counter' in oid_type:
            return 'counter'
        elif 'gauge' in oid_type:
            return 'gauge'
        elif 'timetick' in oid_type:
            return 'counter'
        else:
            return 'gauge'  # Default
    
    def _infer_unit(self, oid: Dict) -> str:
        """Infer unit from OID."""
        desc = oid['description'].lower()
        
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
        elif 'uptime' in oid['name'].lower():
            return 'hundredths_seconds'
        elif 'temperature' in desc:
            return 'celsius'
        else:
            return ''
    
    def _init_device_pools(self):
        """Initialize device pools for realistic generation."""
        # Device models by vendor
        self.device_models = {
            'cisco': {
                DeviceType.ROUTER: ['ISR 4451', 'ASR 1001', 'CSR 1000v'],
                DeviceType.SWITCH: ['Catalyst 9300', 'Nexus 93180', 'Catalyst 3850'],
                DeviceType.FIREWALL: ['ASA 5516', 'FTD 1010']
            },
            'juniper': {
                DeviceType.ROUTER: ['MX204', 'SRX380', 'vSRX'],
                DeviceType.SWITCH: ['EX4300', 'QFX5100'],
                DeviceType.FIREWALL: ['SRX1500', 'vSRX']
            },
            'arista': {
                DeviceType.SWITCH: ['DCS-7050SX3', 'DCS-7280SR3']
            }
        }
        
        # Interface naming conventions
        self.interface_formats = {
            DeviceType.ROUTER: ['GigabitEthernet{}/{}', 'TenGigabitEthernet{}/{}', 'Serial{}/{}/{}'],
            DeviceType.SWITCH: ['Ethernet{}/{}', 'GigabitEthernet{}/{}', 'TenGigabitEthernet{}/{}'],
            DeviceType.FIREWALL: ['ethernet{}/{}', 'management{}']
        }
        
        # IP address pools (RFC 1918)
        self.ip_pools = [
            '10.0.{}.{}', '172.16.{}.{}', '192.168.{}.{}'
        ]
    
    def create_device(self, device_type: DeviceType, vendor: str = None) -> Dict:
        """Create a realistic network device."""
        if vendor is None:
            vendor = random.choice(['cisco', 'juniper', 'arista'])
        
        # Get available models for this vendor and type
        models = self.device_models.get(vendor, {}).get(device_type, [f'{vendor}-{device_type.value}-01'])
        model = random.choice(models)
        
        # Generate hostname
        location = random.choice(['nyc', 'sfo', 'lax', 'dfw', 'ord'])
        role = random.choice(['core', 'edge', 'access', 'distribution'])
        number = random.randint(1, 99)
        hostname = f'{location}-{role}-{device_type.value}-{number:02d}'
        
        # Generate interfaces
        interface_count = random.randint(4, 48)
        interfaces = []
        
        for i in range(1, interface_count + 1):
            if_format = random.choice(self.interface_formats[device_type])
            
            # Generate interface name based on format
            if '{}/{}' in if_format:
                if_name = if_format.format(random.randint(0, 3), i)
            elif '{}/{}/{}' in if_format:
                if_name = if_format.format(random.randint(0, 3), random.randint(0, 3), i)
            else:
                if_name = if_format.format(i)
            
            # Generate IP address
            ip_pool = random.choice(self.ip_pools)
            ip_address = ip_pool.format(random.randint(1, 254), random.randint(1, 254))
            
            interfaces.append({
                'name': if_name,
                'description': f'Uplink to {random.choice(["core", "access", "isp", "client"])}',
                'ip_address': ip_address,
                'speed_mbps': random.choice([100, 1000, 10000]),
                'admin_status': random.choices(['up', 'down'], weights=[95, 5])[0],
                'oper_status': 'up'  # Initial state
            })
        
        device = {
            'hostname': hostname,
            'vendor': vendor,
            'model': model,
            'type': device_type.value,
            'interfaces': interfaces,
            'location': location,
            'role': role,
            'sys_up_time': random.randint(86400, 8640000),  # 1-100 days in seconds
            'created_at': datetime.now().isoformat()
        }
        
        # Store device state
        device_id = f"{vendor}_{hostname}"
        self.device_states[device_id] = {
            'device': device,
            'interface_counters': {},
            'last_sample_time': datetime.now()
        }
        
        # Initialize counters for each interface
        for interface in interfaces:
            counter_key = f"{device_id}_{interface['name']}"
            self.device_states[device_id]['interface_counters'][interface['name']] = {
                'in_octets': random.randint(1000000, 1000000000),
                'out_octets': random.randint(1000000, 1000000000),
                'in_errors': random.randint(0, 100),
                'out_errors': random.randint(0, 100),
                'in_discards': random.randint(0, 50),
                'out_discards': random.randint(0, 50)
            }
        
        return device
    
    def generate_interface_metrics(self, device: Dict, include_errors: bool = True) -> List[Dict]:
        """Generate interface metrics for a device."""
        device_id = f"{device['vendor']}_{device['hostname']}"
        
        if device_id not in self.device_states:
            self.device_states[device_id] = {
                'device': device,
                'interface_counters': {},
                'last_sample_time': datetime.now()
            }
        
        metrics = []
        timestamp = datetime.now()
        
        for interface in device['interfaces']:
            # Get or initialize counters
            if interface['name'] not in self.device_states[device_id]['interface_counters']:
                self.device_states[device_id]['interface_counters'][interface['name']] = {
                    'in_octets': random.randint(1000000, 1000000000),
                    'out_octets': random.randint(1000000, 1000000000),
                    'in_errors': random.randint(0, 100),
                    'out_errors': random.randint(0, 100),
                    'in_discards': random.randint(0, 50),
                    'out_discards': random.randint(0, 50)
                }
            
            counters = self.device_states[device_id]['interface_counters'][interface['name']]
            
            # Simulate traffic increment (with occasional counter reset/wrap)
            traffic_increment = random.randint(1000, 1000000)
            
            # 1% chance of counter reset
            if random.random() < 0.01:
                counters['in_octets'] = random.randint(1000, 1000000)
                counters['out_octets'] = random.randint(1000, 1000000)
            else:
                counters['in_octets'] += traffic_increment
                counters['out_octets'] += traffic_increment // 2  # Outbound typically less
            
            # Generate interface status metric
            status_metric = {
                "time": int(timestamp.timestamp()),
                "event": "metric",
                "host": device['hostname'],
                "source": "snmp",
                "sourcetype": "snmp:metric",
                "fields": {
                    "metric_name": "ifOperStatus",
                    "_value": 1 if interface['oper_status'] == 'up' else 2,
                    "oid": "1.3.6.1.2.1.2.2.1.8",
                    "interface": interface['name'],
                    "vendor": device['vendor'],
                    "device_type": device['type'],
                    "status_text": interface['oper_status'],
                    "unit": "status_code",
                    "semantics": "gauge",
                    "device_model": device['model'],
                    "location": device['location'],
                    "snmp_generated": True
                }
            }
            metrics.append(status_metric)
            
            # Generate traffic in metric
            traffic_in_metric = {
                "time": int(timestamp.timestamp()),
                "event": "metric",
                "host": device['hostname'],
                "source": "snmp",
                "sourcetype": "snmp:metric",
                "fields": {
                    "metric_name": "ifInOctets",
                    "_value": counters['in_octets'],
                    "oid": "1.3.6.1.2.1.2.2.1.10",
                    "interface": interface['name'],
                    "vendor": device['vendor'],
                    "device_type": device['type'],
                    "unit": "bytes",
                    "semantics": "counter",
                    "device_model": device['model'],
                    "location": device['location'],
                    "snmp_generated": True
                }
            }
            metrics.append(traffic_in_metric)
            
            # Generate traffic out metric
            traffic_out_metric = {
                "time": int(timestamp.timestamp()),
                "event": "metric",
                "host": device['hostname'],
                "source": "snmp",
                "sourcetype": "snmp:metric",
                "fields": {
                    "metric_name": "ifOutOctets",
                    "_value": counters['out_octets'],
                    "oid": "1.3.6.1.2.1.2.2.1.16",
                    "interface": interface['name'],
                    "vendor": device['vendor'],
                    "device_type": device['type'],
                    "unit": "bytes",
                    "semantics": "counter",
                    "device_model": device['model'],
                    "location": device['location'],
                    "snmp_generated": True
                }
            }
            metrics.append(traffic_out_metric)
            
            if include_errors:
                # Generate error metrics
                errors_in_metric = {
                    "time": int(timestamp.timestamp()),
                    "event": "metric",
                    "host": device['hostname'],
                    "source": "snmp",
                    "sourcetype": "snmp:metric",
                    "fields": {
                        "metric_name": "ifInErrors",
                        "_value": counters['in_errors'],
                        "oid": "1.3.6.1.2.1.2.2.1.14",
                        "interface": interface['name'],
                        "vendor": device['vendor'],
                        "device_type": device['type'],
                        "unit": "errors",
                        "semantics": "counter",
                        "device_model": device['model'],
                        "location": device['location'],
                        "snmp_generated": True
                    }
                }
                metrics.append(errors_in_metric)
        
        # Update last sample time
        self.device_states[device_id]['last_sample_time'] = timestamp
        
        return metrics
    
    def generate_system_metrics(self, device: Dict) -> List[Dict]:
        """Generate system metrics for a device."""
        metrics = []
        timestamp = datetime.now()
        
        # System uptime (increment by time since last check)
        device_id = f"{device['vendor']}_{device['hostname']}"
        
        if device_id in self.device_states:
            last_time = self.device_states[device_id]['last_sample_time']
            time_diff = (timestamp - last_time).total_seconds()
            device['sys_up_time'] += int(time_diff * 100)  # Convert to hundredths of seconds
        
        # System uptime metric
        uptime_metric = {
            "time": int(timestamp.timestamp()),
            "event": "metric",
            "host": device['hostname'],
            "source": "snmp",
            "sourcetype": "snmp:metric",
            "fields": {
                "metric_name": "sysUpTime",
                "_value": device['sys_up_time'],
                "oid": "1.3.6.1.2.1.1.3",
                "vendor": device['vendor'],
                "device_type": device['type'],
                "unit": "hundredths_seconds",
                "semantics": "counter",
                "uptime_days": device['sys_up_time'] / 8640000,  # Convert to days
                "device_model": device['model'],
                "location": device['location'],
                "snmp_generated": True
            }
        }
        metrics.append(uptime_metric)
        
        # CPU utilization (simulate realistic patterns)
        hour = timestamp.hour
        if 9 <= hour <= 17:  # Business hours
            cpu_util = random.randint(30, 80)
        else:
            cpu_util = random.randint(5, 30)
        
        cpu_metric = {
            "time": int(timestamp.timestamp()),
            "event": "metric",
            "host": device['hostname'],
            "source": "snmp",
            "sourcetype": "snmp:metric",
            "fields": {
                "metric_name": "cpuUtilization",
                "_value": cpu_util,
                "oid": "1.3.6.1.4.1.9.9.109.1.1.1.1.5",  # Cisco CPU 5-minute avg
                "vendor": device['vendor'],
                "device_type": device['type'],
                "unit": "percent",
                "semantics": "gauge",
                "device_model": device['model'],
                "location": device['location'],
                "snmp_generated": True
            }
        }
        metrics.append(cpu_metric)
        
        # Memory utilization
        memory_util = random.randint(40, 90)
        memory_metric = {
            "time": int(timestamp.timestamp()),
            "event": "metric",
            "host": device['hostname'],
            "source": "snmp",
            "sourcetype": "snmp:metric",
            "fields": {
                "metric_name": "memoryUtilization",
                "_value": memory_util,
                "vendor": device['vendor'],
                "device_type": device['type'],
                "unit": "percent",
                "semantics": "gauge",
                "device_model": device['model'],
                "location": device['location'],
                "snmp_generated": True
            }
        }
        metrics.append(memory_metric)
        
        return metrics
    
    def generate_metrics_batch(self, device_count: int = 3, include_system: bool = True) -> List[Dict]:
        """Generate a batch of SNMP metrics."""
        metrics = []
        
        # Create or get devices
        devices = []
        for i in range(device_count):
            device_type = random.choice([DeviceType.ROUTER, DeviceType.SWITCH, DeviceType.FIREWALL])
            vendor = random.choice(['cisco', 'juniper', 'arista'])
            device = self.create_device(device_type, vendor)
            devices.append(device)
        
        # Generate metrics for each device
        for device in devices:
            # Interface metrics
            interface_metrics = self.generate_interface_metrics(device)
            metrics.extend(interface_metrics)
            
            # System metrics
            if include_system:
                system_metrics = self.generate_system_metrics(device)
                metrics.extend(system_metrics)
        
        return metrics

def main():
    """Test the SNMP metrics generator."""
    print(f"\n{'='*60}")
    print(f"🧪 TESTING SNMP METRICS GENERATOR")
    print(f"{'='*60}")
    
    # Create generator with deterministic seed
    generator = SNMPMetricGenerator(seed=42)
    
    # Generate metrics batch
    print(f"\nGenerating SNMP metrics...")
    metrics = generator.generate_metrics_batch(device_count=2)
    
    print(f"✅ Generated {len(metrics)} SNMP metric events")
    
    # Show sample metrics
    print(f"\n📋 Sample Interface Metric:")
    interface_metrics = [m for m in metrics if 'if' in m['fields']['metric_name'].lower()]
    if interface_metrics:
        sample = interface_metrics[0]
        print(f"  Metric: {sample['fields']['metric_name']}")
        print(f"  Value: {sample['fields']['_value']}")
        print(f"  Host: {sample['host']}")
        print(f"  Interface: {sample['fields'].get('interface', 'N/A')}")
        print(f"  OID: {sample['fields'].get('oid', 'N/A')}")
        print(f"  Semantics: {sample['fields'].get('semantics', 'N/A')}")
        print(f"  Unit: {sample['fields'].get('unit', 'N/A')}")
    
    print(f"\n📋 Sample System Metric:")
    system_metrics = [m for m in metrics if 'sys' in m['fields']['metric_name'].lower() or 'cpu' in m['fields']['metric_name'].lower()]
    if system_metrics:
        sample = system_metrics[0]
        print(f"  Metric: {sample['fields']['metric_name']}")
        print(f"  Value: {sample['fields']['_value']}")
        print(f"  Host: {sample['host']}")
        print(f"  OID: {sample['fields'].get('oid', 'N/A')}")
        print(f"  Semantics: {sample['fields'].get('semantics', 'N/A')}")
        print(f"  Unit: {sample['fields'].get('unit', 'N/A')}")
    
    # Save sample metrics to file
    output_file = BASE_DIR / "snmp_metrics_sample.json"
    with open(output_file, 'w') as f:
        json.dump(metrics[:20], f, indent=2)  # Save first 20 metrics as sample
    
    print(f"\n📁 Sample metrics saved to: {output_file}")
    
    # Test Splunk HEC ingestion
    print(f"\n{'='*60}")
    print(f"🔧 TESTING SPLUNK HEC INGESTION")
    print(f"{'='*60}")
    
    try:
        import requests
        
        # Prepare HEC payload
        hec_events = []
        run_id = f"SNMP-TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        for metric in metrics[:10]:  # Send first 10 metrics
            hec_event = {
                "time": metric["time"],
                "event": metric["event"],
                "host": metric["host"],
                "source": metric["source"],
                "sourcetype": metric["sourcetype"],
                "fields": metric["fields"]
            }
            hec_event["fields"]["snmp_test_run"] = True
            hec_event["fields"]["test_run_id"] = run_id
            
            hec_events.append(hec_event)
        
        # Send to HEC
        hec_url = "https://localhost:18088/services/collector"
        hec_token = "1379bbf9-5535-48d8-ab4e-b20e2ff6deee"
        
        print(f"  Sending {len(hec_events)} SNMP metrics to HEC...")
        
        response = requests.post(
            hec_url,
            headers={"Authorization": f"Splunk {hec_token}"},
            json=hec_events,
            verify=False,
            timeout=10
        )
        
        if response.status_code == 200:
            print(f"  ✅ HEC accepted SNMP metrics (HTTP {response.status_code})")
            print(f"  Run ID for verification: {run_id}")
            
            # Example SPL queries
            print(f"\n  Example SPL queries:")
            print(f"    search index=* test_run_id=\"{run_id}\"")
            print(f"    | stats count by sourcetype, metric_name")
            print(f"\n    | mstats count WHERE index=* test_run_id=\"{run_id}\"")
            print(f"    | timechart span=1m count by metric_name")
            
        else:
            print(f"  ❌ HEC rejected SNMP metrics: HTTP {response.status_code}")
            print(f"  Response: {response.text[:200]}")
            
    except ImportError:
        print(f"  ⚠️ Requests module not available, skipping HEC test")
    except Exception as e:
        print(f"  ⚠️ HEC test error: {e}")
    
    print(f"\n{'='*60}")
    print(f"✅ SNMP METRICS GENERATOR READY")
    print(f"{'='*60}")
    
    print(f"\n🎯 Next steps:")
    print(f"  1. Integrate generator with existing metric pipeline")
    print(f"  2. Test mstats queries in Splunk")
    print(f"  3. Create device health and capacity scenarios")
    print(f"  4. Implement multi-device, multi-interface metric streams")
    
    return metrics

if __name__ == "__main__":
    metrics = main()