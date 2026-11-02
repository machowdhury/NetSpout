#!/usr/bin/env python3
"""Splunk-managed XML modular input for the app-owned PulseForge spool."""
import sys
import xml.etree.ElementTree as ET
from pulseforge_forwarding import STANZA, drain, active_settings, readiness

SCHEME = '''<scheme><title>NetSpout PulseForge Spool</title>
<description>Drain synthetic scenario events into Splunk; uses operator-managed forwarding.</description>
<use_external_validation>true</use_external_validation><streaming_mode>xml</streaming_mode>
<use_single_instance>false</use_single_instance><endpoint><args>
<arg name="spool_mode"><title>Spool mode</title><data_type>string</data_type>
<required_on_create>false</required_on_create></arg></args></endpoint></scheme>'''


def main(args=None, input_stream=None, output=None):
    args = sys.argv[1:] if args is None else args
    input_stream = sys.stdin if input_stream is None else input_stream
    output = sys.stdout if output is None else output
    if args == ['--scheme']:
        output.write(SCHEME)
        return
    if args == ['--validate-arguments']:
        root = ET.fromstring(input_stream.read())
        for param in root.findall('.//param'):
            if param.get('name') == 'spool_mode' and param.text != 'native':
                raise ValueError('Unsupported spool mode')
        return
    if args:
        raise ValueError('Unsupported input arguments')
    root = ET.fromstring(input_stream.read())
    stanzas = root.findall('.//configuration/stanza')
    if len(stanzas) != 1 or stanzas[0].get('name') != STANZA:
        raise ValueError('Unsupported spool input stanza')
    if readiness(active_settings())['state'] != 'READY':
        raise ValueError('Forwarding input is not ready')
    drain(output)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        sys.stderr.write('PulseForge spool input unavailable; handoff is unverified\n')
        sys.exit(1)
