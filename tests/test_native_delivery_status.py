"""Offline native delivery evidence regressions; no real HTTP."""
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest
import urllib.error
from unittest.mock import MagicMock, patch
import test_splunk_setup_workflow as setup_fixture

handler = setup_fixture.handler


class NativeDeliveryTests(unittest.TestCase):
    setUp = setup_fixture.NativeSetupTests.setUp
    rest = setup_fixture.NativeSetupTests.rest

    def request(self, body=b'{"code":0}', status=200, error=None):
        reply = MagicMock(status=status)
        reply.__enter__.return_value = reply
        reply.read.return_value = body
        clean = dict(action='onboard_sample', sourcetype='dummy:sample', index='main',
                     sample_content='dummy one\ndummy two', count=3,
                     hec=handler.DEFAULT_CONFIG['hec_url'], token='dummy-token', ssl_verify=True)
        with patch.object(handler, 'validate_and_sanitize', return_value=clean), \
             patch.object(handler, 'has_netspout_admin', return_value=True), \
             patch('urllib.request.urlopen', side_effect=error, return_value=reply) as send:
            code, result = handler.execute_request(dict(action='onboard_sample', session_key='admin'))
        self.assertEqual(send.call_count, 1)
        self.assertEqual(result['generated'], 6)
        self.assertEqual(result['attempted'], 6)
        self.assertIsNone(result['indexed'])
        self.assertFalse(result['indexing_verified'])
        self.assertNotIn('dummy-token', json.dumps(result))
        self.assertEqual(result['accepted'] + result['failed'] + result['unknown'], 6)
        return code, result

    def test_acknowledged_is_accepted_not_indexed(self):
        code, result = self.request()
        self.assertEqual((code, result['delivery_state'], result['accepted']), (200, 'ACCEPTED', 6))

    def test_unexpected_responses_are_unknown(self):
        for body in (b'not JSON dummy-secret', b'{}', b'{"code":4}', b'{"code":false}'):
            with self.subTest(body=body):
                code, result = self.request(body)
                self.assertEqual((code, result['delivery_state'], result['unknown']), (200, 'UNKNOWN', 6))
                self.assertNotIn('dummy-secret', json.dumps(result))
                self.assertEqual(result['accepted'], 0)
                self.assertEqual(result['status'], 'error')

    def test_transport_failure_is_unknown(self):
        _, result = self.request(error=OSError('dummy-secret'))
        self.assertEqual(result['unknown'], 6)
        self.assertNotIn('dummy-secret', json.dumps(result))

    def test_http_rejection_and_server_ambiguity(self):
        for status, state in ((400, 'FAILED'), (403, 'FAILED'), (500, 'UNKNOWN'), (503, 'UNKNOWN')):
            with self.subTest(status=status):
                error = urllib.error.HTTPError('https://dummy.invalid', status, 'dummy-secret', {}, io.BytesIO(b'dummy-secret'))
                _, result = self.request(error=error)
                self.assertEqual(result['delivery_state'], state)
                self.assertEqual(result['http_status'], status)
                self.assertNotIn('dummy-secret', json.dumps(result))

    def test_wizard_error_handlers_never_report_success(self):
        source = Path('netspout/appserver/static/guided_onboarding.js').read_text()
        dispatch = source[source.index("if (wizardState.mode === \"single\")", source.index('function execute') if 'function execute' in source else 0):]
        callbacks = re.findall(r'\.catch\(function\(err\) \{(.*?)\n      \}\);', dispatch, re.S)
        self.assertGreaterEqual(len(callbacks), 3)
        program = "const assert=require('assert'); const logOutput=s=>{assert(!/✔|SUCCESS|Dispatched|executed via/.test(s));}; const btn={prop(){return this},css(){return this}}; const spinner={hide(){}}; const showVerification=()=>{throw Error('false verification')};\n"
        for callback in callbacks[-3:]:
            program += '(function(err){' + callback + '})(new Error("dummy-secret"));\n'
        result = subprocess.run(['node', '-e', program], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_legacy_console_explicit_demo_only(self):
        source = Path('netspout/appserver/static/datablaster_react_app.js').read_text()
        for false_claim in ('HTTP 200 OK', 'Indexer ack received', '99.85% Ack Rate', '"Total Events Sent"', '"Indexed Events"', 'Simulated 200 OK', 'Token Authorization verified', 'data.latency_ms || 14'):
            self.assertNotIn(false_claim, source)
        self.assertIn('Demo Events (not sent)', source)
        self.assertIn('No collector acknowledgement', source)
        self.assertIn('delivery, HEC acceptance and indexing are unverified', source)
        self.assertIn('Request failed or response unavailable', source)
        self.assertIn('Server reported probe success; HTTP status', source)


if __name__ == '__main__':
    from run_sec2b_offline import network_guard
    sys.addaudithook(network_guard)
    unittest.main(verbosity=2, failfast=True)
