"""Vendor structure evidence only; no selected-version TA compatibility claim."""
from pathlib import Path
from types import SimpleNamespace
import re
import unittest
from unittest.mock import patch
import yaml
from netspout_core.log_engine import SplunkLogEngine as Engine

ROOT = Path(__file__).resolve().parents[1]

class NetworkVendorRawTests(unittest.TestCase):
    def setUp(self):
        self.device = SimpleNamespace(id='lab-01', name='lab-switch',
            ip_address='192.0.2.10', type=SimpleNamespace(value='switch'))
        self.clock = patch.object(Engine, 'current_timestamp_syslog', return_value='May 20 14:00:15')
        self.clock.start()
        self.addCleanup(self.clock.stop)
        self.iso = patch.object(Engine, 'current_timestamp_iso', return_value='2026-05-20 14:00:15.000 UTC')
        self.iso.start()
        self.addCleanup(self.iso.stop)

    def lines(self, name):
        path = ROOT / 'netspout/appserver/static/samples' / name / (name+'.yml')
        return yaml.safe_load(path.read_text())['samples'][0]['lines']

    def test_mac_native_grammar_and_equivalent_notation(self):
        expected = ('May 20 14:00:15 lab-switch %SW_MATM-4-MACFLAP_NOTIF: Host 0011.2233.4455 '
                    'in vlan 10 is flapping between port Gi1/0/10 and port Po1.')
        for mac in ('00:11:22:33:44:55', '0011.2233.4455', '00-11-22-33-44-55'):
            event = Engine.format_cisco_mac_flap_log(self.device, mac, 10, 'Gi1/0/10', 'Po1', 'allowed', 'normal')
            self.assertEqual(event.raw_log, expected)
            self.assertEqual(event.sourcetype, 'cisco:ios:syslog')
            self.assertEqual(event.node_id, 'lab-01')
            self.assertEqual(event.status, 'normal')
            self.assertNotIn('signature=', event.raw_log)

    def test_mac_invalid_address_rejected(self):
        for mac in ('xyz', '00112233445566', '00112233zz55'):
            with self.assertRaises(ValueError):
                Engine.format_cisco_mac_flap_log(self.device, mac, 10, 'Gi1', 'Gi2', 'allowed', 'normal')

    def test_junos_native_path_change_without_invented_hops(self):
        event = Engine.format_juniper_junos_log(self.device, 'lab-lsp', '192.0.2.1 (DWDM)',
            '192.0.2.2 (backup)', 'allowed', 'normal')
        self.assertEqual(event.raw_log, 'May 20 14:00:15 lab-switch rpd[2941]: '
            'RPD_MPLS_LSP_CHANGE: MPLS LSP lab-lsp change on primary(any) Route  192.0.2.1')
        self.assertEqual(event.sourcetype, 'juniper:junos')
        self.assertEqual(event.dest_ip, '192.0.2.2 (backup)')
        self.assertNotIn('DOWN', event.raw_log)
        self.assertNotIn('status=', event.raw_log)

    def test_arista_native_interface_lifecycle(self):
        lines = self.lines('arista-eos-syslog')
        self.assertEqual(len(lines), 2)
        for line, state in zip(lines, ('down', 'up')):
            self.assertEqual(line['sourcetype'], 'arista:eos:syslog')
            self.assertEqual(line['source'], 'syslog:udp:514')
            self.assertRegex(line['_raw'], r'^May 20 14:00:\d{2} switch-leaf-01.acme.local Ebra: %LINEPROTO-5-UPDOWN: Line protocol on Interface Ethernet22, changed state to '+state+'$')
            self.assertNotRegex(line['_raw'], r'\$|signature=|status=')

    def test_f5_monitor_ids_process_severity_and_member(self):
        lines = self.lines('f5-bigip-ltm')
        self.assertEqual(len(lines), 3)
        for line, message_id, state in zip(lines, ('01070727', '01070638', '01070727'), ('up', 'down', 'up')):
            raw = line['_raw']
            self.assertIn('notice mcpd[14820]: '+message_id+':5: Pool /Common/pool_corp_web member /Common/10.20.1.10:80 monitor status '+state+'.', raw)
            self.assertEqual(line['sourcetype'], 'f5:bigip:ltm')
            self.assertNotIn('received connection', raw)
            self.assertEqual(raw.count('['), raw.count(']'))
            self.assertNotRegex(raw, r'\$|signature=|device_id=')
        self.assertIn('@2026/05/20 14:00:16.', lines[1]['_raw'])

    def test_generated_mirrors(self):
        canonical = (ROOT/'src/netspout_core/log_engine.py').read_bytes()
        for path in ('backend/app/log_engine.py', 'netspout/bin/log_engine.py', 'netspout/bin/netspout_core/log_engine.py'):
            self.assertTrue((ROOT/path).read_bytes().endswith(canonical), path)
