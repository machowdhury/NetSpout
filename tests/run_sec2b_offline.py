"""One-pass SEC-2B harness: Unix socketpair allowed; network and DNS denied.

Run with the existing D6 venv Python, PYTHONDONTWRITEBYTECODE=1, and
PYTHONPATH=src:tests from the SEC-2B worktree. No application startup is imported.
"""
import ast
import asyncio
import json
from pathlib import Path
import socket
import ssl  # Load before installing the process-local guard.
import sys
import unittest
import urllib.request


class NetworkDenied(RuntimeError):
    pass


def network_guard(event, args):
    if event == 'socket.__new__' and args[1] != socket.AF_UNIX:
        raise NetworkDenied('Only AF_UNIX sockets are permitted')
    if event in ('socket.connect', 'socket.sendto', 'socket.sendmsg',
                 'socket.getaddrinfo', 'socket.gethostbyname',
                 'socket.gethostbyaddr', 'socket.getnameinfo',
                 'urllib.Request'):
        raise NetworkDenied('Network connections, DNS and real HTTP are denied')


class NetworkGuardTests(unittest.TestCase):
    def test_unix_socketpair_and_asyncio_are_permitted(self):
        left, right = socket.socketpair(socket.AF_UNIX)
        with left, right:
            left.send(b'x')
            self.assertEqual(right.recv(1), b'x')

        async def ready():
            return True
        self.assertTrue(asyncio.run(ready()))

    def test_internet_dns_and_real_http_are_denied_before_io(self):
        for family in (socket.AF_INET, socket.AF_INET6):
            with self.assertRaises(NetworkDenied):
                socket.socket(family)
        with self.assertRaises(NetworkDenied):
            socket.getaddrinfo('dummy.invalid', 443)
        with self.assertRaises(NetworkDenied):
            socket.create_connection(('127.0.0.1', 8088))
        with self.assertRaises(NetworkDenied):
            urllib.request.urlopen('https://dummy.invalid')


class FastAPIWireTests(unittest.TestCase):
    """Real Request/HTTPException/response processing via in-memory ASGI HTTP."""

    def apps(self):
        import fastapi
        from test_sec2b_shared_transport import handlers, ROOT
        from test_sec2a_serialization import load_model
        from netspout_core.telemetry_config_api import (
            TelemetryConfigRoute, TelemetryConfigUpdate, CONFIG_UPDATE_RESPONSES,
            invalid_update_error,
        )
        for directory in ('backend/app', 'netspout/bin'):
            model = load_model(directory + '/models.py', False)
            ns = handlers(directory + '/main.py', model)
            app = fastapi.FastAPI()
            ns.update(app=app, APIRouter=fastapi.APIRouter, HTTPException=fastapi.HTTPException,
                      TelemetryConfigRoute=TelemetryConfigRoute, TelemetryConfigUpdate=TelemetryConfigUpdate,
                      CONFIG_UPDATE_RESPONSES=CONFIG_UPDATE_RESPONSES, invalid_update_error=invalid_update_error)
            tree = ast.parse((ROOT / directory / 'main.py').read_text())
            selected = []
            for node in tree.body:
                if isinstance(node, ast.AsyncFunctionDef) and node.name in (
                        'get_telemetry_config', 'set_telemetry_config'):
                    selected.append(node)
                elif isinstance(node, ast.Assign) and any(
                        isinstance(target, ast.Name) and target.id == 'telemetry_config_router'
                        for target in node.targets):
                    selected.append(node)
                elif (isinstance(node, ast.Expr) and isinstance(node.value, ast.Call)
                      and isinstance(node.value.func, ast.Attribute) and node.value.func.attr == 'include_router'
                      and any(isinstance(arg, ast.Name) and arg.id == 'telemetry_config_router'
                              for arg in node.value.args)):
                    selected.append(node)
            exec(compile(ast.Module(body=selected, type_ignores=[]), directory + '/main.py', 'exec'), ns)
            yield app, ns, model

    def exercise(self, app, scenario):
        import httpx
        async def run():
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),
                                         base_url='http://in-memory.invalid', trust_env=False) as client:
                await scenario(client)
        asyncio.run(run())

    def test_actual_fastapi_roundtrip_clear_and_redaction(self):
        from test_sec2b_shared_transport import SECRETS
        from unittest.mock import patch
        import os
        for app, ns, model in self.apps():
            async def scenario(client):
                before = dict(os.environ)
                response = await client.post('/api/telemetry/config', json={'hec_index': 'wire-test'})
                self.assertEqual(response.status_code, 200)
                cfg = ns['current_topology'].global_transport
                for key, value in SECRETS.items():
                    self.assertEqual(getattr(cfg, key), value)
                for response in (response, await client.get('/api/telemetry/config')):
                    public = response.json()['global_transport']
                    for key in SECRETS:
                        self.assertNotIn(key, public)
                    for secret in ('dummy-phase2-hec', 'dummy-phase2-header', 'dummy-phase2-community'):
                        self.assertNotIn(secret, response.text)
                response = await client.post('/api/telemetry/config', json={
                    'credential_updates': {key: {'operation': 'clear'} for key in SECRETS}})
                self.assertEqual(response.status_code, 200)
                response = await client.post('/api/telemetry/config', json={'token': ''})
                self.assertEqual(response.status_code, 200)
                for key in SECRETS:
                    self.assertFalse(getattr(ns['current_topology'].global_transport, key))
                self.assertEqual(dict(os.environ), before)
            with patch.dict(os.environ, {'NETSPOUT_HEC_TOKEN': 'dummy-environment'}):
                self.exercise(app, scenario)

    def test_actual_fastapi_rejection_is_atomic_and_errors_are_safe(self):
        for app, ns, model in self.apps():
            async def scenario(client):
                original = ns['current_topology'].global_transport
                for body in (b'{broken-dummy-private', b'null',
                             b'{"token":"dummy-private","hec_token":"dummy-private"}',
                             b'{"token":"dummy-private","token":"dummy-private"}',
                             b'{"hec_enabled":[]}',
                             b'{"credential_updates":{"hec_token":{"operation":"replace","value":""}}}'):
                    response = await client.post('/api/telemetry/config', content=body,
                                                 headers={'Content-Type': 'application/json'})
                    self.assertEqual(response.status_code, 422)
                    self.assertIsInstance(response.json()['detail'], list)
                    self.assertNotIn('dummy-private', response.text)
                    self.assertIs(ns['current_topology'].global_transport, original)
            self.exercise(app, scenario)

    def test_openapi_and_validation_comparison_with_previous_typed_boundary(self):
        import fastapi
        for app, ns, model in self.apps():
            old = fastapi.FastAPI()
            async def previous(config: model.TelemetryTransportConfig):
                return config
            old.post('/api/telemetry/config')(previous)
            new_operation = app.openapi()['paths']['/api/telemetry/config']['post']
            old_operation = old.openapi()['paths']['/api/telemetry/config']['post']
            self.assertIn('requestBody', new_operation)
            self.assertIn('requestBody', old_operation)
            self.assertIn('422', new_operation['responses'])
            self.assertIn('415', new_operation['responses'])
            self.assertIn('422', old_operation['responses'])
            async def previous_errors(client):
                response = await client.post('/api/telemetry/config', content=b'{broken',
                                             headers={'Content-Type': 'application/json'})
                self.assertEqual(response.status_code, 422)
                self.assertIsInstance(response.json()['detail'], list)
                response = await client.post('/api/telemetry/config', json={'unknown': True})
                self.assertEqual(response.status_code, 200)
            self.exercise(old, previous_errors)

    def test_content_type_and_unknown_field_compatibility(self):
        for app, ns, model in self.apps():
            async def scenario(client):
                # Unsupported explicit content types are rejected before mutation.
                response = await client.post('/api/telemetry/config', content=b'{"hec_index":"text-json"}',
                                             headers={'Content-Type': 'text/plain'})
                self.assertEqual(response.status_code, 415)
                response = await client.post('/api/telemetry/config', json={'unknown': True})
                self.assertEqual(response.status_code, 422)
                response = await client.post('/api/telemetry/config', content=b'')
                self.assertEqual(response.status_code, 422)
            self.exercise(app, scenario)

    def test_json_content_types_including_missing_header(self):
        for app, ns, model in self.apps():
            async def scenario(client):
                for content_type in (None, 'application/json', 'application/json; charset=utf-8',
                                     'application/vnd.netspout+json; charset=UTF-8',
                                     'Application/JSON'):
                    headers = {} if content_type is None else {'Content-Type': content_type}
                    response = await client.post('/api/telemetry/config', content=b'{"hec_index":"json-update"}',
                                                 headers=headers)
                    self.assertEqual(response.status_code, 200, content_type)
                original = ns['current_topology'].global_transport
                for content_type in ('text/plain', 'application/xml', 'application/jsonp',
                                     'text/x+json', 'application/+json', ''):
                    response = await client.post('/api/telemetry/config', content=b'{}',
                                                 headers={'Content-Type': content_type})
                    self.assertEqual(response.status_code, 415)
                    self.assertIs(ns['current_topology'].global_transport, original)
                    self.assertIsInstance(response.json()['detail'], list)
            self.exercise(app, scenario)

    def test_constructor_aliases_equal_null_conflicting_and_stale_mirrors(self):
        for app, ns, model in self.apps():
            async def scenario(client):
                url = 'https://dummy.invalid/services/collector'
                for payload in ({'endpoint': url, 'index': 'alias-index'},
                                {'hec_url': url, 'endpoint': url, 'hec_endpoint': url,
                                 'hec_index': 'alias-index', 'index': 'alias-index', 'default_index': 'alias-index'},
                                {'hec_endpoint': None, 'default_index': None, 'endpoint': None, 'index': None}):
                    response = await client.post('/api/telemetry/config', json=payload)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(ns['current_topology'].global_transport.hec_url, url)
                    self.assertEqual(ns['current_topology'].global_transport.hec_index, 'alias-index')
                cfg = ns['current_topology'].global_transport
                cfg.hec_endpoint = 'https://stale.invalid/services/collector'
                cfg.default_index = 'stale-index'
                response = await client.post('/api/telemetry/config', json={
                    'endpoint': model.DEFAULT_SPLUNK_HEC_URL, 'index': 'idx_network_ops'})
                self.assertEqual(response.status_code, 200)
                cfg = ns['current_topology'].global_transport
                self.assertEqual(cfg.hec_url, model.DEFAULT_SPLUNK_HEC_URL)
                self.assertEqual(cfg.hec_index, 'idx_network_ops')
                for payload in ({'endpoint': url, 'hec_url': 'https://other.invalid'},
                                {'index': 'one', 'default_index': 'two'},
                                {'token': 'dummy-private', 'hec_token': 'dummy-private'},
                                {'token': '', 'hec_token': ''}):
                    response = await client.post('/api/telemetry/config', json=payload)
                    self.assertEqual(response.status_code, 422)
                    self.assertIs(ns['current_topology'].global_transport, cfg)
                    self.assertNotIn('dummy-private', response.text)
            self.exercise(app, scenario)

    def test_duplicate_keys_rejected_before_typed_validation(self):
        for app, ns, model in self.apps():
            async def scenario(client):
                cfg = ns['current_topology'].global_transport
                for body in (
                    b'{"hec_enabled":[],"hec_enabled":true}',
                    b'{"credential_updates":{"hec_token":{"operation":"replace","value":"dummy-private","value":"other"}}}',
                    b'{"credential_updates":{"hec_token":{"operation":"clear"},"hec_token":{"operation":"keep"}}}',
                    b'{"otel_headers":{"Authorization":"dummy-private","Authorization":"other"}}',
                ):
                    response = await client.post('/api/telemetry/config', content=body,
                                                 headers={'Content-Type': 'application/json'})
                    self.assertEqual(response.status_code, 422)
                    self.assertEqual(response.json()['detail'][0]['type'], 'invalid_json')
                    self.assertNotIn('dummy-private', response.text)
                    self.assertIs(ns['current_topology'].global_transport, cfg)
            self.exercise(app, scenario)

    def test_typed_and_semantic_errors_never_echo_inputs_or_unknown_names(self):
        for app, ns, model in self.apps():
            async def scenario(client):
                cfg = ns['current_topology'].global_transport
                for payload in (
                    {'dummy-private-field': 'dummy-private-value'},
                    {'hec_token': {'dummy-private-field': 'dummy-private-value'}},
                    {'otel_headers': {'dummy-private-field': []}},
                    {'credential_updates': {'dummy-private-field': {'operation': 'clear'}}},
                    {'credential_updates': {'hec_token': {'operation': 'dummy-private-value'}}},
                    {'credential_updates': {'hec_token': {'operation': 'clear', 'value': 'dummy-private-value'}}},
                    {'token': 'dummy-private-value', 'credential_updates': {}},
                    {'hec_url': None}, {'hec_token': None}, {'credential_updates': None},
                ):
                    response = await client.post('/api/telemetry/config', json=payload)
                    self.assertEqual(response.status_code, 422)
                    self.assertNotIn('dummy-private', response.text)
                    for issue in response.json()['detail']:
                        self.assertEqual(set(issue), {'loc', 'type', 'msg'})
                    self.assertIs(ns['current_topology'].global_transport, cfg)
            self.exercise(app, scenario)

    def test_openapi_request_types_and_writeonly_do_not_drop_credentials(self):
        from netspout_core.telemetry_config_api import TelemetryConfigUpdate
        for app, ns, model in self.apps():
            self.assertFalse(issubclass(TelemetryConfigUpdate, model.TelemetryTransportConfig))
            schema = app.openapi()
            operation = schema['paths']['/api/telemetry/config']['post']
            self.assertTrue(operation['requestBody']['required'])
            request_schema = schema['components']['schemas']['TelemetryConfigUpdate']
            for name in ('token', 'hec_token', 'otel_headers', 'native_snmp_community', 'credential_updates'):
                self.assertTrue(request_schema['properties'][name]['writeOnly'])
                self.assertNotIn('default', request_schema['properties'][name])
            for name in ('ReplaceStringCredential', 'ReplaceHeaderCredential'):
                self.assertTrue(schema['components']['schemas'][name]['properties']['value']['writeOnly'])
            self.assertIn('endpoint', request_schema['properties'])
            self.assertIn('index', request_schema['properties'])
            self.assertEqual(set(model.TelemetryTransportConfig.model_fields) - set(request_schema['properties']), set())
            raw = TelemetryConfigUpdate(hec_token='dummy-private-value')
            self.assertEqual(raw.model_dump(exclude_unset=True), {'hec_token': 'dummy-private-value'})
            self.assertNotIn('dummy-private', repr(raw))
            self.assertEqual(TelemetryConfigUpdate().model_dump(exclude_unset=True), {})

    def test_actual_replace_extracts_secrets_and_legacy_blank_keeps(self):
        for app, ns, model in self.apps():
            async def scenario(client):
                replacements = {'hec_token': 'dummy-new-hec', 'otel_headers': {'X-Token': 'dummy-new-header'},
                                'native_snmp_community': 'dummy-new-community'}
                response = await client.post('/api/telemetry/config', json={
                    'credential_updates': {key: {'operation': 'replace', 'value': value}
                                           for key, value in replacements.items()}})
                self.assertEqual(response.status_code, 200)
                for key, value in replacements.items():
                    self.assertEqual(getattr(ns['current_topology'].global_transport, key), value)
                    self.assertNotIn(key, response.json()['global_transport'])
                for payload in ({key: '' for key in replacements}, {},
                                {'credential_updates': {key: {'operation': 'keep'} for key in replacements}}):
                    response = await client.post('/api/telemetry/config', json=payload)
                    self.assertEqual(response.status_code, 200)
                    for key, value in replacements.items():
                        self.assertEqual(getattr(ns['current_topology'].global_transport, key), value)
            self.exercise(app, scenario)

    def test_boundary_does_not_replace_global_validation_handler(self):
        from fastapi.exceptions import RequestValidationError
        from fastapi.exception_handlers import request_validation_exception_handler
        for app, ns, model in self.apps():
            self.assertIs(app.exception_handlers[RequestValidationError],
                          request_validation_exception_handler)
            @app.post('/unrelated')
            async def unrelated(count: int):
                return {'count': count}
            async def scenario(client):
                response = await client.post('/unrelated', params={'count': 'not-an-integer'})
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.json()['detail'][0]['loc'], ['query', 'count'])
            self.exercise(app, scenario)


if __name__ == '__main__':
    sys.addaudithook(network_guard)
    import fastapi
    import httpx
    import pydantic
    root = Path(__file__).resolve().parents[1]
    print('Worktree:', root, flush=True)
    print('Python:', sys.executable, flush=True)
    print('Versions:', pydantic.__version__, fastapi.__version__, httpx.__version__, flush=True)
    import os
    from unittest.mock import patch
    with patch.dict(os.environ, {'NETSPOUT_HEC_TOKEN': '', 'NETSPOUT_SPLUNK_PASSWORD': '',
                                 'NETSPOUT_SPLUNK_TOKEN': ''}):
        suite = unittest.defaultTestLoader.loadTestsFromNames([
            'test_sec2a_serialization', 'test_sec2b_credential_updates',
            'test_sec2b_shared_transport',
        ])
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(NetworkGuardTests))
        suite.addTests(unittest.defaultTestLoader.loadTestsFromTestCase(FastAPIWireTests))
        result = unittest.TextTestRunner(verbosity=2, failfast=True).run(suite)
    print('SUMMARY: run=%d failures=%d errors=%d skipped=%d' % (
        result.testsRun, len(result.failures), len(result.errors), len(result.skipped)), flush=True)
    raise SystemExit(not result.wasSuccessful())
