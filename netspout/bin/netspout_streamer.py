"""
NetSpout Splunk Modular Input
Emits real-time network telemetry (Syslog, SNMP, Flow, gNMI metrics) directly into Splunk index pipeline.
"""

import os
import sys
import xml.dom.minidom
import time

BIN_DIR = os.path.dirname(os.path.abspath(__file__))
if BIN_DIR not in sys.path:
    sys.path.insert(0, BIN_DIR)

SCHEME = """<scheme>
    <title>NetSpout Telemetry Streamer</title>
    <description>Streams synthetic multi-vendor enterprise telemetry and OpenConfig MDT metrics.</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>xml</streaming_mode>
    <use_single_instance>true</use_single_instance>
    <endpoint>
        <args>
            <arg name="ecosystem_mode">
                <title>Ecosystem Mode</title>
                <description>pure_cisco or mixed_vendor</description>
            </arg>
            <arg name="scenario">
                <title>Active Scenario</title>
                <description>Network simulation scenario name</description>
            </arg>
            <arg name="target_hec_url">
                <title>Splunk HEC URL</title>
                <description>Destination HEC endpoint</description>
            </arg>
            <arg name="metric_index">
                <title>Metric Index</title>
                <description>Splunk metric index (default: cisco_mdt_metrics)</description>
            </arg>
            <arg name="event_index">
                <title>Event Index</title>
                <description>Splunk event index (default: idx_network_ops)</description>
            </arg>
        </args>
    </endpoint>
</scheme>
"""

def print_scheme():
    sys.stdout.write(SCHEME)

def validate_arguments():
    # Read XML from stdin
    val_data = sys.stdin.read()
    sys.exit(0)

def run_input():
    # Simple continuous generator loop if enabled
    while True:
        time.sleep(10)

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            print_scheme()
        elif sys.argv[1] == "--validate-arguments":
            validate_arguments()
    else:
        run_input()
