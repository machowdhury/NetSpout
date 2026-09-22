"""
NetSpout Splunk Modular Input
Emits real-time multi-vendor network telemetry (Syslog, SNMP, Flow, gNMI metrics)
directly into Splunk indexing pipeline via stdout streaming XML mode.

Author: Mahamudul Chowdhury (machowdhury@yahoo.com)
"""

import os
import sys
import time
import json
import random
import select
from datetime import datetime, timezone
import xml.dom.minidom
import xml.etree.ElementTree as ET

BIN_DIR = os.path.dirname(os.path.abspath(__file__))
if BIN_DIR not in sys.path:
    sys.path.insert(0, BIN_DIR)

try:
    from vendor_catalog import VENDOR_CATALOG
except ImportError:
    try:
        from app.vendor_catalog import VENDOR_CATALOG
    except ImportError:
        VENDOR_CATALOG = []

SCHEME = """<scheme>
    <title>NetSpout Telemetry Streamer</title>
    <description>Streams synthetic multi-vendor enterprise telemetry and OpenConfig MDT metrics directly into Splunk.</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <use_single_instance>true</use_single_instance>
    <endpoint>
        <args>
            <arg name="ecosystem_mode">
                <title>Ecosystem Mode</title>
                <description>pure_cisco or mixed_vendor</description>
                <data_type>string</data_type>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="scenario">
                <title>Active Scenario</title>
                <description>Network simulation scenario name</description>
                <data_type>string</data_type>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="target_hec_url">
                <title>Splunk HEC URL</title>
                <description>Optional secondary HEC destination endpoint</description>
                <data_type>string</data_type>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="metric_index">
                <title>Metric Index</title>
                <description>Splunk metric index (default: cisco_mdt_metrics)</description>
                <data_type>string</data_type>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="event_index">
                <title>Event Index</title>
                <description>Splunk event index (default: idx_network_ops)</description>
                <data_type>string</data_type>
                <required_on_create>false</required_on_create>
            </arg>
            <arg name="interval">
                <title>Interval (seconds)</title>
                <description>Polling and stream generation interval</description>
                <data_type>number</data_type>
                <required_on_create>false</required_on_create>
            </arg>
        </args>
    </endpoint>
</scheme>
"""


def print_scheme():
    sys.stdout.write(SCHEME)
    sys.stdout.flush()


def validate_arguments():
    # Read XML from stdin
    val_data = sys.stdin.read()
    if val_data.strip():
        try:
            root = ET.fromstring(val_data)
        except Exception as e:
            sys.stderr.write(f"XML Validation Error: {e}\n")
            sys.exit(1)
    sys.exit(0)


def parse_input_config(xml_str: str) -> dict:
    """Parses Splunk input XML configuration passed on stdin."""
    config = {
        "ecosystem_mode": "mixed_vendor",
        "scenario": "mixed_edge_breach",
        "target_hec_url": "",
        "metric_index": "cisco_mdt_metrics",
        "event_index": "idx_network_ops",
        "interval": 5.0
    }
    if not xml_str or not xml_str.strip():
        return config

    try:
        root = ET.fromstring(xml_str)
        for param in root.findall(".//param"):
            name = param.get("name")
            text = param.text
            if name in config and text:
                if name == "interval":
                    try:
                        config[name] = float(text)
                    except ValueError:
                        pass
                else:
                    config[name] = text.strip()
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to parse input config XML: {e}\n")

    return config


def generate_event_batch(config: dict) -> list:
    """
    Generates a realistic multi-vendor telemetry event batch covering:
    - Cisco IOS-XE BGP/OSPF and Interface logs
    - Palo Alto Networks PAN-OS Traffic & Threat logs
    - Fortinet FortiGate UTM & System logs
    - Juniper Junos syslog & mib2d SNMP events
    - Arista EOS BGP/interface syslog
    - Cisco ISE & Duo Security logs
    - OpenConfig MDT Metric records
    """
    events = []
    now_ts = time.time()
    now_dt = datetime.now(timezone.utc)
    now_syslog = now_dt.strftime("%b %d %H:%M:%S")
    now_slash = now_dt.strftime("%Y/%m/%d %H:%M:%S")
    date_str = now_dt.strftime("%Y-%m-%d")
    time_str = now_dt.strftime("%H:%M:%S")
    ev_idx = config.get("event_index", "idx_network_ops")
    met_idx = config.get("metric_index", "cisco_mdt_metrics")

    # 1. Cisco IOS-XE Carrier & BGP
    events.append({
        "time": f"{now_ts:.3f}",
        "source": "netspout:streamer",
        "sourcetype": "cisco:ios:syslog",
        "index": ev_idx,
        "host": "sfo-core-rtr01.corp.internal",
        "data": f"<189>{now_syslog} sfo-core-rtr01 %LINK-3-UPDOWN: Interface GigabitEthernet0/0/1, changed state to up"
    })
    events.append({
        "time": f"{now_ts:.3f}",
        "source": "netspout:streamer",
        "sourcetype": "cisco:ios:syslog",
        "index": ev_idx,
        "host": "sfo-core-rtr01.corp.internal",
        "data": f"<189>{now_syslog} sfo-core-rtr01 %BGP-5-ADJCHANGE: neighbor 10.0.1.2 Up (BGP Adjacency Established)"
    })

    # 2. Palo Alto Networks Next-Gen Firewall Traffic Allow
    events.append({
        "time": f"{now_ts:.3f}",
        "source": "netspout:streamer",
        "sourcetype": "pan:traffic",
        "index": ev_idx,
        "host": "iad-edge-fw01.corp.internal",
        "data": f"1,{now_slash},001801000000,TRAFFIC,allow,2304,192.168.10.45,104.16.132.229,0.0.0.0,0.0.0.0,Corporate-Web-Access,trust,untrust,ethernet1/2,ethernet1/1,default,49201,443,0,0,0x0,tcp,allow,1420,8920,0,1,0,ssl,0,849201,0x0,United States,United States,0,24,18,0,0,,iad-edge-fw01,from-policy"
    })

    # 3. Palo Alto Networks Threat Prevention Drop
    events.append({
        "time": f"{now_ts:.3f}",
        "source": "netspout:streamer",
        "sourcetype": "pan:threat",
        "index": ev_idx,
        "host": "iad-edge-fw01.corp.internal",
        "data": f"1,{now_slash},001801000000,THREAT,vulnerability,9901,198.51.100.42,10.20.10.1,0.0.0.0,0.0.0.0,Perimeter-Drop-Exploit,untrust,trust,ethernet1/1,ethernet1/2,default,52410,80,0,0,0x0,tcp,drop,0,0,0,0,0,,(99012) Apache Struts OGNL Injection,web-browsing,informational,server-to-client,4920194,0x0,198.51.100.0-198.51.100.255,United States,0,,0,,,0,,,,0,0,iad-edge-fw01,from-policy"
    })

    # 4. Fortinet FortiGate UTM Signature Block
    events.append({
        "time": f"{now_ts:.3f}",
        "source": "netspout:streamer",
        "sourcetype": "fortinet:fortigate:utm",
        "index": ev_idx,
        "host": "FGT-DC-CORE01",
        "data": f'date={date_str} time={time_str} devname="FGT-DC-CORE01" devid="FG200ETK18001048" logid="0419016384" type="utm" subtype="ips" level="alert" vd="root" srcip=198.51.100.42 srcport=54102 srcintf="port1" dstip=10.20.10.1 dstport=80 dstintf="port2" policyid=1 proto=6 action="dropped" attack="OpenSSL.Heartbleed.Information.Disclosure" attackid=38192 severity="high" msg="OpenSSL TLS heartbeat information disclosure attempt"'
    })

    # 5. Juniper Junos syslog & rpd
    events.append({
        "time": f"{now_ts:.3f}",
        "source": "netspout:streamer",
        "sourcetype": "juniper:junos:syslog",
        "index": ev_idx,
        "host": "jnx-border-gw01",
        "data": f"<189>{now_syslog} jnx-border-gw01 rpd[2104]: %DAEMON-5-BGP_NEIGHBOR_STATE_CHANGED: neighbor 198.51.100.1 (External AS 64512): State changed from OpenConfirm to Established"
    })

    # 6. Arista EOS Line Protocol
    events.append({
        "time": f"{now_ts:.3f}",
        "source": "netspout:streamer",
        "sourcetype": "arista:eos:syslog",
        "index": ev_idx,
        "host": "leaf-sw01",
        "data": f"<189>{now_syslog} leaf-sw01 Ebra: %LINEPROTO-5-UPDOWN: Line protocol on Interface Ethernet1/1, changed state to up"
    })

    # 7. Cisco ISE 802.1X Authentication
    events.append({
        "time": f"{now_ts:.3f}",
        "source": "netspout:streamer",
        "sourcetype": "cisco:ise:syslog",
        "index": ev_idx,
        "host": "ise-node-01.corp.internal",
        "data": f"<181>{now_syslog} ise-node-01 CISE_Passed_Authentications 0000021481 1 0 {date_str} {time_str}.012 +00:00 0001234566 5200 NOTICE Passed-Authentication: Authentication succeeded, User-Name=alice.engineer, NAS-IP-Address=10.0.1.10, NetworkDeviceName=sfo-access-sw01"
    })

    # 8. Cisco Duo MFA Push Success
    duo_json = json.dumps({
        "timestamp": int(now_ts),
        "username": "alice.engineer",
        "eventtype": "authentication",
        "result": "SUCCESS",
        "reason": "User approved Duo Push",
        "ip": "192.168.10.45",
        "factor": "duo_push"
    })
    events.append({
        "time": f"{now_ts:.3f}",
        "source": "netspout:streamer",
        "sourcetype": "cisco:duo:auth",
        "index": ev_idx,
        "host": "duo-sso-proxy",
        "data": duo_json
    })

    # 9. OpenConfig MDT Metric Data (Indexed to cisco_mdt_metrics)
    cpu_metric = {
        "metric_name:cpu.utilization": round(random.uniform(22.0, 48.0), 2),
        "metric_name:memory.utilization": round(random.uniform(50.0, 68.0), 2),
        "metric_name:interface.octets.rx": random.randint(1000000, 50000000),
        "metric_name:interface.octets.tx": random.randint(1000000, 50000000),
        "_value": round(random.uniform(22.0, 48.0), 2),
        "device": "sfo-core-rtr01",
        "component": "Routing-Processor-0",
        "subscription_mode": "STREAMING"
    }
    events.append({
        "time": f"{now_ts:.3f}",
        "source": "cisco:ios:mdt",
        "sourcetype": "cisco:ios:mdt:metric",
        "index": met_idx,
        "host": "sfo-core-rtr01.corp.internal",
        "data": json.dumps(cpu_metric)
    })

    return events


def emit_xml_events(events: list):
    """Emits valid Splunk modular input XML event chunks to stdout."""
    sys.stdout.write("<stream>\n")
    for ev in events:
        sys.stdout.write('  <event unbroken="1">\n')
        sys.stdout.write(f"    <time>{ev['time']}</time>\n")
        sys.stdout.write(f"    <source>{ev['source']}</source>\n")
        sys.stdout.write(f"    <sourcetype>{ev['sourcetype']}</sourcetype>\n")
        sys.stdout.write(f"    <index>{ev['index']}</index>\n")
        sys.stdout.write(f"    <host>{ev['host']}</host>\n")
        sys.stdout.write(f"    <data><![CDATA[{ev['data']}]]></data>\n")
        sys.stdout.write("    <done/>\n")
        sys.stdout.write("  </event>\n")
    sys.stdout.write("</stream>\n")
    sys.stdout.flush()


def run_input(single_cycle: bool = False):
    """Main continuous loop for Splunk modular input."""
    xml_input = ""
    try:
        if select.select([sys.stdin], [], [], 0.2)[0]:
            xml_input = sys.stdin.read()
    except Exception:
        pass

    config = parse_input_config(xml_input)
    interval = config.get("interval", 5.0)

    while True:
        events = generate_event_batch(config)
        emit_xml_events(events)

        if single_cycle:
            break

        time.sleep(interval)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg == "--scheme":
            print_scheme()
        elif arg == "--validate-arguments":
            validate_arguments()
        elif arg in ("--test", "--dry-run"):
            run_input(single_cycle=True)
        else:
            print_scheme()
    else:
        run_input(single_cycle=False)
