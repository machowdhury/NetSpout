"""SEC-2C offline redaction tests and socket-free D6 verifier adapter.

Run with the D6 venv, PYTHONDONTWRITEBYTECODE=1 and PYTHONPATH=src:backend:tests.
D6 verifier assertions are unmodified; collector/TLS/HTTP fixtures are mocked.
No real TLS handshake, HTTP server, DNS lookup, or socket connection is tested.
"""
import ast
import asyncio
import http.client
import importlib.util
import io
import json
import os
from pathlib import Path
import ssl
import sys
import types
import unittest
from unittest.mock import MagicMock, patch
import urllib.error

from run_sec2b_offline import network_guard

ROOT = Path(__file__).resolve().parents[1]
SECRET = 'dummy-sec2c-private'
URL = 'https://dummy-user:dummy-url-password@collector.invalid:7777/private?token=dummy-query'
REMOTE = 'dummy-remote-body'


def response(status=200, body=None):
    result = MagicMock()
    result.__enter__.return_value = result
    result.status = status
    result.read.return_value = body if body is not None else json.dumps({'code': 0, 'text': REMOTE + SECRET}).encode()
    return result


def families():
    for index, path in enumerate(('src/netspout_core/telemetry_dispatcher.py',
                                  'backend/app/telemetry_dispatcher.py',
                                  'netspout/bin/telemetry_dispatcher.py',
                                  'netspout/bin/netspout_core/telemetry_dispatcher.py')):
        spec = importlib.util.spec_from_file_location('sec2c_dispatcher_' + str(index), ROOT / path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module


class DispatchRedactionTests(unittest.TestCase):
    def safe(self, value):
        wire = json.dumps(value, default=str)
        for fragment in (SECRET, REMOTE, URL, 'dummy-url-password', 'dummy-query',
                         'collector.invalid', 'dummy-user'):
            self.assertNotIn(fragment, wire)

    def hec_result(self, module, dispatcher, outcome, state, status, error_class, success):
        self.assertIsInstance(outcome, tuple)
        self.assertEqual(len(outcome), 2)
        self.assertIs(outcome[0], success)
        self.assertIsInstance(outcome[1], str)
        self.assertEqual(module.hec_outcome_fields(outcome), {
            'state': state, 'http_status': status, 'error_class': error_class})
        self.assertEqual(dispatcher.stats['hec_dispatching'], 0)
        self.assertEqual(dispatcher.stats['hec_generated'], 1)
        self.safe({'outcome': outcome, 'stats': dispatcher.stats})

    def test_hec_remote_success_and_unexpected_bodies_are_not_public(self):
        for module in families():
            for body, state in ((None, 'ACCEPTED'), ((SECRET + REMOTE).encode(), 'UNKNOWN')):
                dispatcher = module.TelemetryDispatcher()
                with patch('urllib.request.urlopen', return_value=response(body=body)) as send:
                    outcome = dispatcher.emit_hec({}, URL, SECRET)
                self.assertEqual(send.call_count, 1)
                self.assertEqual(send.call_args.args[0].get_header('Authorization'), 'Splunk ' + SECRET)
                self.hec_result(module, dispatcher, outcome, state, 200,
                                None if state == 'ACCEPTED' else 'unexpected_response', True)

    def test_hec_http_rejections_and_uncertainty_preserve_evidence(self):
        for module in families():
            for status, code, state, error_class in (
                (401, 4, 'FAILED', 'auth_rejected'), (403, 1, 'FAILED', 'auth_rejected'),
                (400, 6, 'FAILED', 'request_rejected'), (503, 9, 'FAILED', 'collector_busy'),
                (500, 8, 'UNKNOWN', 'collector_error_uncertain'),
                (503, 8, 'UNKNOWN', 'collector_error_uncertain')):
                dispatcher = module.TelemetryDispatcher()
                body = json.dumps({'code': code, 'text': SECRET + REMOTE}).encode()
                error = urllib.error.HTTPError(URL, status, SECRET, {}, io.BytesIO(body))
                with patch('urllib.request.urlopen', side_effect=error) as send:
                    outcome = dispatcher.emit_hec({}, URL, SECRET)
                self.assertEqual(send.call_count, 1)
                self.hec_result(module, dispatcher, outcome, state, status, error_class, False)

    def test_hec_exception_classes_are_safe_and_unchanged(self):
        for module in families():
            for error, state, error_class in (
                (urllib.error.URLError(SECRET + URL), 'FAILED', 'unreachable'),
                (ssl.SSLCertVerificationError(SECRET + URL), 'FAILED', 'tls_verification'),
                (ValueError(SECRET + URL), 'FAILED', 'invalid_endpoint'),
                (RuntimeError(SECRET + URL), 'UNKNOWN', 'no_answer_after_send')):
                dispatcher = module.TelemetryDispatcher()
                with patch('urllib.request.urlopen', side_effect=error):
                    outcome = dispatcher.emit_hec({}, URL, SECRET)
                self.hec_result(module, dispatcher, outcome, state, None, error_class, False)

    def test_real_crlf_header_validation_exception_is_not_public(self):
        token = SECRET + '\r\nInjected: ' + SECRET
        def validate_headers(request, **kwargs):
            connection = http.client.HTTPConnection('dummy.invalid')
            connection.putrequest('POST', '/')  # Buffers locally; never endheaders/connect.
            for name, value in request.header_items():
                connection.putheader(name, value)
            self.fail('CR/LF header must be rejected before I/O')
        for module in families():
            dispatcher = module.TelemetryDispatcher()
            with patch('urllib.request.urlopen', side_effect=validate_headers):
                outcome = dispatcher.emit_hec({}, URL, token)
            self.hec_result(module, dispatcher, outcome, 'FAILED', None, 'invalid_endpoint', False)

    def test_hec_payload_request_and_read_failures_do_not_echo(self):
        for module in families():
            dispatcher = module.TelemetryDispatcher()
            with patch('urllib.request.urlopen') as send:
                outcome = dispatcher.emit_hec({'event': object()}, URL, SECRET)
            send.assert_not_called()
            self.hec_result(module, dispatcher, outcome, 'FAILED', None, 'invalid_payload', False)
            dispatcher = module.TelemetryDispatcher()
            with patch('urllib.request.Request', side_effect=ValueError(SECRET + URL)):
                outcome = dispatcher.emit_hec({}, URL, SECRET)
            self.hec_result(module, dispatcher, outcome, 'FAILED', None, 'invalid_endpoint', False)
            dispatcher = module.TelemetryDispatcher()
            reply = response()
            reply.read.side_effect = ValueError(SECRET + REMOTE)
            with patch('urllib.request.urlopen', return_value=reply):
                outcome = dispatcher.emit_hec({}, URL, SECRET)
            self.hec_result(module, dispatcher, outcome, 'UNKNOWN', 200, 'no_answer_after_send', False)

    def test_hec_unreadable_error_body_is_safe(self):
        for module in families():
            dispatcher = module.TelemetryDispatcher()
            error = urllib.error.HTTPError(URL, 503, SECRET, {}, None)
            error.read = MagicMock(side_effect=RuntimeError(SECRET + REMOTE))
            with patch('urllib.request.urlopen', side_effect=error):
                outcome = dispatcher.emit_hec({}, URL, SECRET)
            self.hec_result(module, dispatcher, outcome, 'UNKNOWN', 503, 'collector_error_uncertain', False)

    def test_otel_and_telegraf_errors_hide_headers_urls_and_exception_text(self):
        for module in families():
            for pipeline in ('otel', 'telegraf'):
                for error in (ValueError(SECRET + URL), urllib.error.URLError(SECRET + URL),
                              urllib.error.HTTPError(URL, 401, SECRET, {}, io.BytesIO((SECRET + REMOTE).encode()))):
                    dispatcher = module.TelemetryDispatcher()
                    kwargs = {'headers': {'Authorization': SECRET}} if pipeline == 'otel' else {}
                    with patch('urllib.request.urlopen', side_effect=error):
                        result = getattr(dispatcher, 'emit_' + pipeline)({}, URL, **kwargs)
                    self.assertIs(result[0], False)
                    self.assertIsInstance(result[1], str)
                    self.assertEqual(dispatcher.stats[pipeline + '_errors'], 1)
                    self.safe({'result': result, 'stats': dispatcher.stats})

    def test_otel_and_telegraf_success_bodies_are_not_public(self):
        for module in families():
            for pipeline in ('otel', 'telegraf'):
                dispatcher = module.TelemetryDispatcher()
                with patch('urllib.request.urlopen', return_value=response()):
                    result = getattr(dispatcher, 'emit_' + pipeline)({}, URL)
                self.assertIs(result[0], True)
                self.assertEqual(dispatcher.stats[pipeline + '_dispatched'], 1)
                self.safe({'result': result, 'stats': dispatcher.stats})

    def test_syslog_socket_failures_and_success_do_not_echo_destinations(self):
        for module in families():
            for protocol in ('udp', 'tcp'):
                dispatcher = module.TelemetryDispatcher()
                with patch.object(module.socket, 'socket', side_effect=OSError(SECRET + URL)):
                    result = dispatcher.emit_syslog(SECRET, host=URL, protocol=protocol)
                self.assertFalse(result[0])
                self.safe({'result': result, 'stats': dispatcher.stats})
                for fail in (True, False):
                    dispatcher = module.TelemetryDispatcher()
                    sock = MagicMock()
                    if fail:
                        getattr(sock, 'sendto' if protocol == 'udp' else 'connect').side_effect = OSError(SECRET + URL)
                    with patch.object(module.socket, 'socket', return_value=sock):
                        result = dispatcher.emit_syslog(SECRET, host=URL, protocol=protocol)
                    self.assertIs(result[0], not fail)
                    sock.close.assert_called_once()
                    self.safe({'result': result, 'stats': dispatcher.stats})

    def test_connection_results_preserve_shape_without_exception_or_remote_text(self):
        expected_keys = {'status', 'state', 'stage', 'reachable', 'authenticated',
                         'event_accepted', 'target_index', 'message', 'detail', 'latency_ms'}
        for module in families():
            config = module.TelemetryTransportConfig(hec_url=URL, hec_token=SECRET)
            for error in (urllib.error.URLError(SECRET + URL), ssl.SSLCertVerificationError(SECRET + URL),
                          ValueError(SECRET + URL)):
                dispatcher = module.TelemetryDispatcher()
                with patch('urllib.request.urlopen', side_effect=error):
                    result = dispatcher.test_connection(config)
                self.assertEqual(set(result), expected_keys)
                self.assertEqual(result['state'], 'ERROR')
                self.safe(result)
            for status, body, state in ((200, {'code': 0, 'text': SECRET + REMOTE}, 'VERIFIED'),
                                        (200, {'text': SECRET + REMOTE}, 'VERIFIED'),
                                        (401, {'code': 4, 'text': SECRET + REMOTE}, 'ERROR'),
                                        (500, {'text': SECRET + REMOTE}, 'ERROR')):
                dispatcher = module.TelemetryDispatcher()
                answer = response(status, json.dumps(body).encode())
                failure = urllib.error.HTTPError(URL, status, SECRET, {}, io.BytesIO(json.dumps(body).encode()))
                with patch('urllib.request.urlopen', side_effect=[response(), answer if status == 200 else failure]):
                    result = dispatcher.test_connection(config)
                self.assertEqual(set(result), expected_keys)
                self.assertEqual(result['state'], state)  # Preserve existing UNKNOWN/VERIFIED behavior.
                self.safe({'result': result, 'stats': dispatcher.stats})

    def test_pipeline_messages_do_not_echo_pipeline_inputs(self):
        for module in families():
            dispatcher = module.TelemetryDispatcher()
            config = module.TelemetryTransportConfig(hec_token=SECRET, otel_endpoint=URL,
                                                       telegraf_endpoint=URL, otel_headers={'Authorization': SECRET})
            self.safe(dispatcher.test_pipeline(SECRET + URL, config))
            self.safe(dispatcher.test_connection(config, pipeline=SECRET + URL))
            for pipeline in ('otel', 'telegraf'):
                with patch('urllib.request.urlopen', side_effect=ValueError(SECRET + URL)):
                    self.safe(dispatcher.test_pipeline(pipeline, config))

    def test_dispatch_evidence_and_configuration_get_propagate_only_safe_messages(self):
        from fastapi.encoders import jsonable_encoder
        for module in families():
            dispatcher = module.TelemetryDispatcher()
            config = module.TelemetryTransportConfig(hec_url=URL, hec_token=SECRET)
            entry = module.LogEntry(timestamp='2026-10-20T00:00:00Z', device_id='dummy-node',
                src_ip='10.0.0.1', dest_ip='10.0.0.2', protocol='TCP', duration='1ms',
                action='allowed', signature='dummy', status='normal', raw_log='dummy event',
                node_type='router', node_id='dummy-node', sourcetype='cisco:ios:syslog')
            error = urllib.error.HTTPError(URL, 401, SECRET, {}, io.BytesIO((SECRET + REMOTE).encode()))
            with patch('urllib.request.urlopen', side_effect=error):
                evidence = dispatcher.dispatch_log(entry, config)
            self.assertEqual(evidence['hec']['state'], 'FAILED')
            self.assertEqual(evidence['hec']['error_class'], 'auth_rejected')
            self.safe(evidence)
            # Keep endpoint values out of this response check: the existing API
            # intentionally returns configured non-secret endpoint fields.
            public_config = config.model_copy(update={'hec_url': 'https://safe.invalid'})
            for main in ('backend/app/main.py', 'netspout/bin/main.py'):
                tree = ast.parse((ROOT / main).read_text())
                function = next(n for n in tree.body if isinstance(n, ast.AsyncFunctionDef)
                                and n.name == 'get_telemetry_config')
                function.decorator_list = []
                ns = {'current_topology': types.SimpleNamespace(global_transport=public_config),
                      'dispatcher': dispatcher}
                exec(compile(ast.Module(body=[function], type_ignores=[]), main, 'exec'), ns)
                self.safe(jsonable_encoder(asyncio.run(ns['get_telemetry_config']())))

    def test_numeric_status_only_and_generated_copy_parity(self):
        for module in families():
            self.assertEqual(module._http_summary('HEC', 401), 'HEC HTTP 401')
            self.assertEqual(module._http_summary('HEC', SECRET + URL), 'HEC HTTP response')
        source = (ROOT / 'src/netspout_core/telemetry_dispatcher.py').read_bytes()
        self.assertEqual((ROOT / 'netspout/bin/netspout_core/telemetry_dispatcher.py').read_bytes(), source)
        for directory in ('backend/app', 'netspout/bin'):
            self.assertEqual((ROOT / directory / 'telemetry_dispatcher.py').read_bytes().split(b'\n', 5)[5], source)


def run_d6(mode, folder):
    """Run original verifier assertions once, replacing only I/O fixtures."""
    sys.path.insert(0, str(folder))
    import d6_collector as collector
    spec = importlib.util.spec_from_file_location('sec2c_d6_verifier', folder / ('test_d6' + mode + '_acceptance.py'))
    verifier = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(verifier)
    active = {}

    class MockCollector:
        def __init__(self, behaviour, dispatcher=None, tls=None):
            self.behaviour, self.dispatcher, self.tls = behaviour, dispatcher, tls
            self.requests = []
            self.url = 'https://d6.mock.invalid:7777/' + str(id(self))
        def __enter__(self):
            active[self.url] = self
            return self
        def __exit__(self, *args):
            active.pop(self.url)

    def mocked_http(request, **kwargs):
        if request.full_url == 'https://closed.mock.invalid:7777':
            raise urllib.error.URLError('dummy unreachable')
        instance = active[request.full_url]
        if instance.tls and kwargs['context'].verify_mode != ssl.CERT_NONE:
            raise ssl.SSLCertVerificationError('dummy untrusted certificate')
        instance.requests.append({'auth': request.get_header('Authorization'), 'body': request.data,
            'dispatching': None if instance.dispatcher is None else instance.dispatcher.stats['hec_dispatching']})
        if instance.behaviour in ('no_answer', 'drop'):
            raise TimeoutError('dummy no answer after send')
        status, payload = collector.BEHAVIOURS[instance.behaviour]
        body = payload.encode() if isinstance(payload, str) else json.dumps(payload).encode()
        if status >= 400:
            raise urllib.error.HTTPError(request.full_url, status, 'dummy rejection', {}, io.BytesIO(body))
        return response(status, body)

    with patch.object(collector, 'Collector', MockCollector), \
         patch.object(collector, 'closed_port_url', return_value='https://closed.mock.invalid:7777'), \
         patch.object(collector, 'self_signed_cert', return_value=('dummy-cert', 'dummy-key')), \
         patch('urllib.request.urlopen', side_effect=mocked_http):
        suite = unittest.defaultTestLoader.loadTestsFromModule(verifier)
        return unittest.TextTestRunner(verbosity=2, failfast=True).run(suite)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--d6', choices=('a', 'b'))
    parser.add_argument('--verifier-dir', type=Path)
    args = parser.parse_args()
    sys.addaudithook(network_guard)
    with patch.dict(os.environ, {'NETSPOUT_HEC_TOKEN': '', 'NETSPOUT_SPLUNK_PASSWORD': '',
                                 'NETSPOUT_SPLUNK_TOKEN': '', 'NETSPOUT_ROOT': str(ROOT)}):
        if args.d6:
            if args.verifier_dir is None:
                parser.error('--verifier-dir is required with --d6')
            result = run_d6(args.d6, args.verifier_dir)
        else:
            result = unittest.TextTestRunner(verbosity=2, failfast=True).run(
                unittest.defaultTestLoader.loadTestsFromTestCase(DispatchRedactionTests))
    print('SUMMARY: run=%d failures=%d errors=%d skipped=%d' % (
        result.testsRun, len(result.failures), len(result.errors), len(result.skipped)))
    raise SystemExit(not result.wasSuccessful())
