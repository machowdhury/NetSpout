"""C2B synthetic structure checks, not selected-version TA parser verification."""
import json
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import yaml
import test_splunk_setup_workflow  # Existing isolated native import fixture.
import run_simulation as runner
from netspout_core.log_engine import SplunkLogEngine as Engine

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / 'netspout/appserver/static/samples'
NOW = 1792497600.125


class CiscoRawEventTests(unittest.TestCase):
    def setUp(self):
        self.device = SimpleNamespace(id='fw-lab', name='fw-lab-01',
            type=SimpleNamespace(value='firewall'), ip_address='192.0.2.10')

    def asa(self, **updates):
        args = dict(device=self.device, src_ip='198.51.100.20', dest_ip='192.0.2.30',
            src_port=52140, dest_port=443, proto='TCP', action='allowed',
            signature='synthetic only', status='normal')
        args.update(updates)
        with patch.object(Engine, 'current_timestamp_syslog', return_value='Oct 20 12:00:00'), \
             patch.object(Engine, 'current_timestamp_iso', return_value='2026-10-20 12:00:00.125 UTC'):
            return Engine.format_cisco_asa_log(**args)

    def ise(self, **updates):
        with patch.object(Engine, 'current_timestamp_syslog', return_value='Oct 20 12:00:00'), \
             patch.object(Engine, 'current_timestamp_iso', return_value='2026-10-20 12:00:00.125 UTC'):
            return Engine.format_cisco_ise_log(self.device, user='lab_user', **updates)

    def fixtures(self, name):
        return yaml.safe_load((SAMPLES / name / (name + '.yml')).read_text())['samples']

    def test_tcp_build_teardown_native_identity_and_mapping(self):
        built = self.asa(connection_id=42, mapped_src='203.0.113.20/52140',
                         mapped_dest='192.0.2.40/443')
        self.assertIn('%ASA-6-302013: Built inbound TCP connection 42 for outside:198.51.100.20/52140 '
                      '(203.0.113.20/52140) to inside:192.0.2.30/443 (192.0.2.40/443)', built.raw_log)
        down = self.asa(connection_id=42, event_type='teardown', duration_ms=134000, bytes_count=148920)
        self.assertTrue(down.raw_log.endswith('duration 0:02:14 bytes 148920 TCP FINs'))
        self.assertIn('connection 42 for outside:198.51.100.20/52140 to inside:192.0.2.30/443', down.raw_log)
        self.assertEqual(built.sourcetype, 'cisco:asa')
        self.assertEqual(built.signature, 'synthetic only')
        for entry in (built, down):
            self.assertNotRegex(entry.raw_log, r'\b(timestamp|device_id|signature|status|action)=')
        self.assertEqual(self.asa().raw_log, self.asa().raw_log)
        cid = re.search(r'connection (\d+)', self.asa().raw_log).group(1)
        self.assertIn('connection ' + cid, self.asa(event_type='teardown').raw_log)

    def test_deny_and_udp_connection_identifiers(self):
        self.assertTrue(self.asa(action='blocked').raw_log.endswith(
            '%ASA-4-106023: Deny tcp src outside:198.51.100.20/52140 '
            'dst inside:192.0.2.30/443 by access-group "OUTSIDE_IN" [0x0, 0x0]'))
        self.assertIn('%ASA-6-302015: Built inbound UDP', self.asa(proto='UDP').raw_log)
        self.assertIn('%ASA-6-302016: Teardown UDP', self.asa(proto='UDP', event_type='teardown').raw_log)
        for args in ({'proto':'unsupported'}, {'connection_id':True}, {'bytes_count':-1}):
            with self.assertRaises(ValueError):
                self.asa(**args)

    def test_ise_success_failure_headers_and_balanced_response(self):
        for status, code, category, classification, response in (
            ('SUCCESS',5200,'CISE_Passed_Authentications','Passed-Authentication','AccessAccept'),
            ('FAILED',5400,'CISE_Failed_Attempts','Failed-Attempt','AccessReject')):
            raw = self.ise(auth_status=status, sequence_num=42).raw_log
            self.assertTrue(raw.startswith('<181>Oct 20 12:00:00 fw-lab-01 ' + category + ' 0000000042 1 0 '))
            self.assertIn(f'2026-10-20 12:00:00.125 +00:00 0000000042 {code} NOTICE {classification}:', raw)
            self.assertTrue(raw.endswith('Response={RadiusPacketType=' + response + ';}'))
            self.assertEqual(raw.count('{'), raw.count('}'))
            self.assertNotRegex(raw, r'\b(device_id|signature|status|action)=')
        self.assertIn('5400 NOTICE', self.ise(action='blocked').raw_log)
        self.assertIn('5200 NOTICE', self.ise(action='allowed').raw_log)
        self.assertEqual(self.ise().sourcetype, 'cisco:ise:syslog')
        self.assertEqual(self.ise(sourcetype='cisco:ise:nac:8021x').sourcetype, 'cisco:ise:nac:8021x')
        with self.assertRaises(ValueError):
            self.ise(auth_status='unknown')

    def test_legacy_passed_is_equivalent_to_success(self):
        self.assertEqual(self.ise(auth_status="PASSED").model_dump(),
                         self.ise(auth_status="SUCCESS").model_dump())
        self.assertEqual(self.ise(auth_status="FAILURE").raw_log,
                         self.ise(auth_status="FAILED").raw_log)
        with self.assertRaises(ValueError):
            self.ise(auth_status="CONTAINED")

    def test_separate_coa_success_is_not_authentication_or_enforcement_proof(self):
        with patch.object(Engine, 'current_timestamp_syslog', return_value='Oct 20 12:00:00'), \
             patch.object(Engine, 'current_timestamp_iso', return_value='2026-10-20 12:00:00.125 UTC'):
            event = Engine.format_cisco_ise_coa_log(self.device,
                client_mac='02:00:00:00:00:01', client_ip='192.0.2.30', user='lab_user',
                profile='Quarantine_Restricted_VLAN', action='blocked', status='blocked',
                signature='ISE CoA Dynamic Quarantine Profile Enforced', sequence_num=42)
        self.assertEqual(event.raw_log,
            '<181>Oct 20 12:00:00 fw-lab-01 CISE_Passed_Authentications 0000000042 1 0 '
            '2026-10-20 12:00:00.125 +00:00 0000000042 5205 NOTICE Dynamic-Authorization: '
            'Dynamic Authorization succeeded, User-Name=lab_user, Calling-Station-ID=02:00:00:00:00:01')
        self.assertNotRegex(event.raw_log, r'5200|5400|AccessAccept|AccessReject|Quarantine|SIMULATED|profile=')
        self.assertIn('SIMULATED', event.signature)
        self.assertIn('profile=Quarantine_Restricted_VLAN', event.signature)
        self.assertIn('enforcement unverified', event.signature)
        self.assertEqual((event.action,event.status,event.sourcetype),
                         ('blocked','blocked','cisco:ise:syslog'))

    def test_campus_containment_routes_only_to_coa_with_run_correlation(self):
        from netspout_core.scenario_runner import ScenarioRunner
        from netspout_core.models import ScenarioRunRequest
        engine = ScenarioRunner()
        manifest = engine.run_scenario(ScenarioRunRequest(
            scenario_id='cisco_campus_rogue', seed=42, time_mode='TEST'))
        events = engine.get_run_logs(manifest.run_id)
        coa = [e for e in events if '5205 NOTICE Dynamic-Authorization:' in e.raw_log]
        self.assertEqual(len(coa), 1)
        self.assertEqual(coa[0].netspout_phase, 'FAILOVER')
        self.assertTrue(coa[0].netspout_run_id)
        self.assertEqual(coa[0].netspout_scenario_id, 'cisco_campus_rogue')
        self.assertTrue(any('5200 NOTICE Passed-Authentication:' in e.raw_log for e in events))
        self.assertTrue(any('5400 NOTICE Failed-Attempt:' in e.raw_log for e in events))

    def test_deterministic_bounded_tokens_and_rejection(self):
        raw = '$TS$ $HOST$ $SYSLOG_TIMESTAMP$ $ISE_TIMESTAMP$'
        result = runner.render_cisco_fixture_tokens(raw, 'ise-lab-01', NOW)
        self.assertEqual(result, 'Oct 20 12:00:00 ise-lab-01 Oct 20 12:00:00 2026-10-20 12:00:00.125 +00:00')
        self.assertEqual(result, runner.render_cisco_fixture_tokens(raw, 'ise-lab-01', NOW))
        for raw, host in (('$UNSUPPORTED$', 'lab'), ('$HOST$', '$HOST$')):
            with self.assertRaises(runner.CiscoFixtureTokenError) as caught:
                runner.render_cisco_fixture_tokens(raw, host, NOW)
            self.assertNotIn('UNSUPPORTED', str(caught.exception))
        self.assertEqual(runner.render_cisco_fixture_tokens('$FLOW_ID$', 'lab', NOW), '$FLOW_ID$')

    def test_approved_fixture_loader_resolves_tokens_without_altering_sourcetypes(self):
        for name, sourcetype in (('cisco-asa','cisco:asa'), ('cisco-asa-syslog','cisco:asa:syslog'),
                                 ('cisco-ise-syslog','cisco:ise:syslog')):
            with patch.object(runner.time, 'time', return_value=NOW):
                events = runner.load_python_scenario_events(str(SAMPLES/name/(name+'.yml')), strict=True)
            self.assertTrue(events)
            self.assertEqual({e['sourcetype'] for e in events}, {sourcetype})
            for event in events:
                self.assertNotRegex(event['raw'], r'\$[A-Za-z_][A-Za-z0-9_]*\$')
                self.assertNotIn('$', event['host'])

    def test_loader_fails_instead_of_returning_partial_approved_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/'fixture.yml'
            path.write_text('samples:\n - lines:\n  - sourcetype: cisco:ise:syslog\n    _raw: "valid"\n    _raw: "$UNKNOWN$"\n')
            with self.assertRaises(runner.CiscoFixtureTokenError):
                runner.load_python_scenario_events(str(path))
            path.write_text('sourcetype: netspout:network:syslog\n_raw: "$CUSTOM$"\n')
            self.assertEqual(runner.load_python_scenario_events(str(path))[0]['raw'], '$CUSTOM$')

    def test_asa_fixture_lifecycle_and_source_backed_mismatch_repairs(self):
        for name in ('cisco-asa','cisco-asa-syslog'):
            sample = self.fixtures(name)[0]
            self.assertFalse(sample['randomizeEvents'])
            lines = [line['_raw'] for line in sample['lines']]
            built = next(s for s in lines if '%ASA-6-302013:' in s)
            down = next(s for s in lines if '%ASA-6-302014:' in s)
            self.assertLess(lines.index(built), lines.index(down))
            self.assertEqual(re.search(r'connection (\d+)', built).group(1), re.search(r'connection (\d+)', down).group(1))
            self.assertEqual(built.count('('), 2)
            self.assertIn('outside:198.51.100.80/443', down)
            for raw in lines:
                if '725001:' in raw: self.assertIn('Starting SSL handshake', raw)
                if '605005:' in raw: self.assertIn('Login permitted', raw)
                if '106023:' in raw: self.assertRegex(raw, r'by access-group .+ \[0x[0-9a-f]+, 0x[0-9a-f]+\]$')

    def test_ise_baseline_and_failure_samples_are_complete(self):
        samples = self.fixtures('cisco-ise-syslog')
        self.assertIn('5200 NOTICE Passed-Authentication', samples[0]['lines'][0]['_raw'])
        for sample in samples:
            raw = sample['lines'][0]['_raw']
            self.assertEqual(raw.count('{'), raw.count('}'))
            self.assertRegex(raw, r'Response=\{RadiusPacketType=Access(Accept|Reject);\}$')
        self.assertTrue(all('5400 NOTICE Failed-Attempt' in s['lines'][0]['_raw'] for s in samples[1:]))

    def test_generated_log_engine_mirrors(self):
        source = (ROOT/'src/netspout_core/log_engine.py').read_bytes()
        self.assertEqual(source, (ROOT/'netspout/bin/netspout_core/log_engine.py').read_bytes())
        for name in ('backend/app/log_engine.py','netspout/bin/log_engine.py'):
            self.assertTrue((ROOT/name).read_bytes().endswith(source))
