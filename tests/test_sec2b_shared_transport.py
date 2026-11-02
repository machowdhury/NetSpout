"""Offline shared-config checks; execute real handlers without startup services."""
import ast
import asyncio
import json
import os
from pathlib import Path
import types
import unittest
from unittest.mock import patch

from test_sec2a_serialization import load_model, HAS_FASTAPI, HAS_PYDANTIC
from netspout_core.transport_credential_updates import (
    CredentialUpdateError, decode_transport_update, update_shared_transport,
)

ROOT = Path(__file__).resolve().parents[1]
SECRETS = dict(hec_token='dummy-phase2-hec', otel_headers={'Authorization': 'dummy-phase2-header'},
               native_snmp_community='dummy-phase2-community')


class HTTPError(Exception):
    def __init__(self, status_code, detail):
        self.status_code, self.detail = status_code, detail


class Request:
    def __init__(self, payload):
        self.payload = payload if isinstance(payload, bytes) else json.dumps(payload).encode()

    async def body(self):
        return self.payload


def handlers(main_path, model):
    tree = ast.parse((ROOT / main_path).read_text())
    functions = [node for node in tree.body if isinstance(node, ast.AsyncFunctionDef)
                 and node.name in ('get_telemetry_config', 'set_telemetry_config')]
    for node in functions:
        node.decorator_list = []
    ns = dict(TelemetryConfigUpdate=object, HTTPException=HTTPError,
              invalid_update_error=lambda: HTTPError(422, [{'loc': ['body'],
                  'type': 'invalid_configuration', 'msg': 'Invalid telemetry configuration update'}]),
              CredentialUpdateError=CredentialUpdateError,
              decode_transport_update=decode_transport_update,
              update_shared_transport=update_shared_transport,
              TelemetryTransportConfig=model.TelemetryTransportConfig,
              current_topology=model.TopologyState(global_transport=model.TelemetryTransportConfig(**SECRETS)),
              dispatcher=types.SimpleNamespace(stats={}))
    exec(compile(ast.Module(body=functions, type_ignores=[]), main_path, 'exec'), ns)
    return ns


class SharedTransportTests(unittest.TestCase):
    fallback = True

    def cases(self):
        for directory in ('backend/app', 'netspout/bin'):
            model = load_model(directory + '/models.py', self.fallback)
            yield model, handlers(directory + '/main.py', model)

    def send(self, ns, payload):
        try:
            decoded = decode_transport_update(Request(payload).payload)
        except CredentialUpdateError:
            raise HTTPError(422, [{'loc': ['body'], 'type': 'invalid_json', 'msg': 'Invalid JSON'}]) from None
        config = types.SimpleNamespace(model_dump=lambda **kwargs: decoded)
        return asyncio.run(ns['set_telemetry_config'](config))

    def test_omission_legacy_and_explicit_operations_repeated(self):
        for model, ns in self.cases():
            for payload in ({'hec_index': 'updated'}, {}, {key: '' for key in SECRETS},
                            {'credential_updates': {key: {'operation': 'keep'} for key in SECRETS}}):
                self.send(ns, payload)
                for key, value in SECRETS.items():
                    self.assertEqual(getattr(ns['current_topology'].global_transport, key), value)
            self.assertEqual(ns['current_topology'].global_transport.hec_index, 'updated')
            for key in SECRETS:
                self.send(ns, {'credential_updates': {key: {'operation': 'clear'}}})
                self.assertFalse(getattr(ns['current_topology'].global_transport, key))
                self.send(ns, {'credential_updates': {key: {'operation': 'replace', 'value': SECRETS[key]}}})
                self.assertEqual(getattr(ns['current_topology'].global_transport, key), SECRETS[key])
            self.send(ns, {'token': 'dummy-alias'})
            self.assertEqual(ns['current_topology'].global_transport.hec_token, 'dummy-alias')
            self.send(ns, {'token': ''})
            self.assertEqual(ns['current_topology'].global_transport.hec_token, 'dummy-alias')
            self.send(ns, SECRETS)
            self.assertEqual(ns['current_topology'].global_transport.hec_token, SECRETS['hec_token'])

    def test_invalid_requests_are_atomic_and_redacted(self):
        bad = [None, [], {'token': 'dummy-private', 'hec_token': 'dummy-private'},
               {'hec_token': 'dummy-private', 'credential_updates': {'hec_token': {'operation': 'clear'}}},
               {'token': '', 'credential_updates': {'hec_token': {'operation': 'keep'}}},
               {'hec_token': 'dummy-private', 'credential_updates': {'otel_headers': {'operation': 'clear'}}},
               {'hec_token': '', 'credential_updates': {}},
               {'hec_index': 'changed', 'credential_updates': {'hec_token': {'operation': 'clear'},
                 'otel_headers': {'operation': 'replace', 'value': {}}}},
               {'credential_updates': None}, {'credential_updates': {'token': {'operation': 'clear'}}},
               {'hec_token': None}, {'otel_headers': []}, {'native_snmp_community': '   '},
               {'credential_updates': {'hec_token': {'operation': 'replace', 'value': ''}}},
               {'credential_updates': {'hec_token': {'operation': 'clear', 'value': 'dummy-private'}}},
               {'credential_updates': {'hec_token': {'operation': 'inherit'}}},
               {'unknown': 'dummy-private'},
               b'{"token":"dummy-private","token":"dummy-private"}',
               b'{"credential_updates":{"hec_token":{"operation":"clear"},"hec_token":{"operation":"keep"}}}',
               b'{"credential_updates":{"hec_token":{"operation":"clear","operation":"keep"}}}',
               b'{invalid dummy-private']
        for model, ns in self.cases():
            old = ns['current_topology'].global_transport
            for payload in bad:
                with self.subTest(payload=payload):
                    with self.assertRaises(HTTPError) as caught:
                        self.send(ns, payload)
                    self.assertEqual(caught.exception.status_code, 422)
                    self.assertNotIn('dummy-private', json.dumps(caught.exception.detail))
                    self.assertIs(ns['current_topology'].global_transport, old)
                    for key, value in SECRETS.items():
                        self.assertEqual(getattr(old, key), value)

    def test_clear_with_environment_survives_updates_and_backend_copies(self):
        with patch.dict(os.environ, {'NETSPOUT_HEC_TOKEN': 'dummy-environment'}):
            for model, ns in self.cases():
                before = dict(os.environ)
                self.send(ns, {'credential_updates': {key: {'operation': 'clear'} for key in SECRETS}})
                for payload in ({}, {'hec_index': 'updated'}, {'hec_token': ''}, {'token': ''}):
                    self.send(ns, payload)
                    cfg = ns['current_topology'].global_transport
                    for key in SECRETS:
                        self.assertFalse(getattr(cfg, key))
                        self.assertFalse(getattr(cfg.model_copy(deep=True), key))
                        self.assertFalse(getattr(cfg.copy(), key))
                self.assertEqual(dict(os.environ), before)

    def test_get_update_and_roundtrip_redaction_and_input_isolation(self):
        for model, ns in self.cases():
            payload = dict(SECRETS, otel_headers=dict(SECRETS['otel_headers']))
            response = self.send(ns, payload)
            payload['otel_headers']['Authorization'] = 'changed'
            for response in (response, asyncio.run(ns['get_telemetry_config']())):
                if self.fallback:
                    public = response['global_transport'].dict()
                else:
                    from fastapi.encoders import jsonable_encoder
                    public = jsonable_encoder(response)['global_transport']
                wire = json.dumps(public)
                for key, value in SECRETS.items():
                    self.assertNotIn(key, public)
                    for secret in value.values() if isinstance(value, dict) else [value]:
                        self.assertNotIn(secret, wire)
                self.send(ns, public)
            cfg = ns['current_topology'].global_transport
            for key, value in SECRETS.items():
                self.assertEqual(getattr(cfg, key), value)

    def test_keep_does_not_revalidate_existing_header_policy(self):
        for model, ns in self.cases():
            ns['current_topology'].global_transport.otel_headers = {'X-Existing': ''}
            self.send(ns, {'hec_index': 'updated'})
            self.assertEqual(ns['current_topology'].global_transport.otel_headers, {'X-Existing': ''})

    def test_backend_credentials_and_unchanged_hec_lifecycle(self):
        import io
        import urllib.error
        from netspout_core.telemetry_dispatcher import TelemetryDispatcher, hec_outcome_fields

        for model, ns in self.cases():
            self.send(ns, {'token': 'dummy-replacement'})
            cfg = ns['current_topology'].global_transport
            for outcome_body, expected in ((b'{"code":0}', 'ACCEPTED'),
                                           (b'{"code":true}', 'UNKNOWN'),
                                           (b'not-json', 'UNKNOWN')):
                response = unittest.mock.MagicMock()
                response.__enter__.return_value = response
                response.status = 200
                response.read.return_value = outcome_body
                dispatcher = TelemetryDispatcher()
                with patch('urllib.request.urlopen', return_value=response) as send:
                    outcome = dispatcher.emit_hec({}, cfg.hec_url, cfg.hec_token)
                self.assertEqual(send.call_count, 1)
                self.assertEqual(send.call_args.args[0].get_header('Authorization'), 'Splunk dummy-replacement')
                self.assertEqual(outcome.state, expected)
                self.assertEqual(dispatcher.stats['hec_' + expected.lower()], 1)
                self.assertEqual(dispatcher.stats['hec_dispatching'], 0)
                self.assertNotIn('OBSERVED', hec_outcome_fields(outcome).values())
            for status, expected in ((401, 'FAILED'), (500, 'UNKNOWN')):
                dispatcher = TelemetryDispatcher()
                error = urllib.error.HTTPError('https://dummy.invalid', status, 'dummy-error', {}, io.BytesIO(b'{}'))
                with patch('urllib.request.urlopen', side_effect=error) as send:
                    outcome = dispatcher.emit_hec({}, cfg.hec_url, cfg.hec_token)
                self.assertEqual(send.call_count, 1)
                self.assertEqual(outcome.state, expected)
            self.assertEqual(hec_outcome_fields((True, 'legacy'))['state'], 'UNKNOWN')


@unittest.skipUnless(HAS_PYDANTIC and HAS_FASTAPI, 'Pydantic/FastAPI not installed; no dependency installation')
class PydanticSharedTransportTests(SharedTransportTests):
    fallback = False


class PackagedAdapterTests(unittest.TestCase):
    def test_generated_modules_match_canonical(self):
        for name in ('credential_transitions.py', 'transport_credential_updates.py', 'telemetry_config_api.py'):
            source = (ROOT / 'src/netspout_core' / name).read_bytes()
            self.assertEqual((ROOT / 'netspout/bin/netspout_core' / name).read_bytes(), source)
            for directory in ('backend/app', 'netspout/bin'):
                self.assertEqual((ROOT / directory / name).read_bytes().split(b'\n', 5)[5], source)


if __name__ == '__main__':
    unittest.main()
