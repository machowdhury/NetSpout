"""SEC-2A offline regression checks; all credentials are dummy values."""
import ast
import asyncio
import importlib.util
import json
from pathlib import Path
import types
import unittest
from unittest.mock import patch
import builtins
from netspout_core.transport_credential_updates import (
    CredentialUpdateError, decode_transport_update, update_shared_transport,
)

ROOT = Path(__file__).resolve().parents[1]
COPIES = ('src/netspout_core/models.py', 'backend/app/models.py',
          'netspout/bin/models.py', 'netspout/bin/netspout_core/models.py')
SECRETS = dict(hec_token='dummy-sec2a-hec',
               otel_headers={'aUtHoRiZaTiOn': 'Bearer dummy-sec2a-otel'},
               native_snmp_community='dummy-sec2a-community')
HAS_PYDANTIC = importlib.util.find_spec('pydantic') is not None
HAS_FASTAPI = importlib.util.find_spec('fastapi') is not None


def load_model(path, fallback):
    spec = importlib.util.spec_from_file_location('sec2a_models', ROOT / path)
    module = importlib.util.module_from_spec(spec)
    original = builtins.__import__

    def offline_import(name, *args, **kwargs):
        if fallback and name == 'pydantic':
            raise ImportError('Exercise dependency-free models')
        return original(name, *args, **kwargs)

    with patch('builtins.__import__', side_effect=offline_import):
        spec.loader.exec_module(module)
    return module


class SerializationChecks:
    fallback = True

    def models(self):
        for path in COPIES:
            yield load_model(path, self.fallback)

    def assert_safe(self, value):
        wire = json.dumps(value)
        for secret in ('dummy-sec2a-hec', 'dummy-sec2a-otel', 'dummy-sec2a-community'):
            self.assertNotIn(secret, wire)
        for field in SECRETS:
            self.assertNotIn('"' + field + '"', wire)

    def test_direct_nested_and_json_serialization(self):
        for m in self.models():
            cfg = m.TelemetryTransportConfig(**SECRETS)
            topology = m.TopologyState(global_transport=cfg, nodes=[
                m.Node(id='dummy-node', transport_config=cfg)])
            for obj in (cfg, topology):
                self.assert_safe(obj.dict())
                if hasattr(obj, 'model_dump'):
                    self.assert_safe(obj.model_dump())
                for method in ('json', 'model_dump_json'):
                    if hasattr(obj, method):
                        self.assert_safe(json.loads(getattr(obj, method)()))
            self.assertEqual(cfg.dict()['hec_index'], 'idx_network_ops')
            self.assertEqual(topology.dict()['nodes'][0]['id'], 'dummy-node')
            self.assert_safe(m.Node(id='nested', config={'list': [cfg]}).dict())

    def test_backend_access_and_destination_copy(self):
        for m in self.models():
            cfg = m.TelemetryTransportConfig(**SECRETS, syslog_enabled=True)
            for method in ('copy', 'model_copy'):
                for deep in (False, True):
                    clone = getattr(cfg, method)(update={'syslog_enabled': False}, deep=deep)
                    for field, value in SECRETS.items():
                        self.assertEqual(getattr(clone, field), value)
                        self.assertEqual(getattr(cfg, field), value)
                    self.assertFalse(clone.syslog_enabled)
                    self.assertTrue(cfg.syslog_enabled)
                    self.assert_safe(clone.dict())
                    if deep:
                        self.assertIsNot(clone.otel_headers, cfg.otel_headers)
            alias = m.TelemetryTransportConfig(token=SECRETS['hec_token'])
            self.assertEqual(alias.hec_token, SECRETS['hec_token'])
            self.assertNotIn('token', alias.dict())

    def test_actual_configuration_and_topology_handler_bodies(self):
        # Execute the real handlers without importing application startup services.
        for model_path, main_path in [('backend/app/models.py', 'backend/app/main.py'),
                                      ('netspout/bin/models.py', 'netspout/bin/main.py')]:
            m = load_model(model_path, self.fallback)
            topology = m.TopologyState(nodes=[m.Node(id='node', transport_config=
                m.TelemetryTransportConfig(**SECRETS))])
            names = {'get_telemetry_config', 'set_telemetry_config', 'get_topology', 'update_topology'}
            tree = ast.parse((ROOT / main_path).read_text())
            handlers = [n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name in names]
            self.assertEqual({n.name for n in handlers}, names)
            for handler in handlers:
                handler.decorator_list = []
            async def broadcast_log(_):
                pass
            ns = dict(TelemetryTransportConfig=m.TelemetryTransportConfig,
                      TelemetryConfigUpdate=object, CredentialUpdateError=CredentialUpdateError,
                      update_shared_transport=update_shared_transport,
                      TopologyState=m.TopologyState, current_topology=topology,
                      dispatcher=types.SimpleNamespace(stats={}),
                      manager=types.SimpleNamespace(broadcast_log=broadcast_log))
            exec(compile(ast.Module(body=handlers, type_ignores=[]), main_path, 'exec'), ns)
            class Request:
                def model_dump(self, **kwargs):
                    return SECRETS
            for name, args in [('set_telemetry_config', (Request(),)), ('get_telemetry_config', ()),
                               ('update_topology', (topology,)), ('get_topology', ())]:
                response = asyncio.run(ns[name](*args))
                if self.fallback:
                    if isinstance(response, dict):
                        response = {k: v.dict() if hasattr(v, 'dict') else v for k, v in response.items()}
                    else:
                        response = response.dict()
                else:
                    from fastapi.encoders import jsonable_encoder
                    response = jsonable_encoder(response)
                self.assert_safe(response)
            self.assertEqual(ns['current_topology'].global_transport.hec_token, SECRETS['hec_token'])


class FallbackTests(SerializationChecks, unittest.TestCase):
    pass


@unittest.skipUnless(HAS_PYDANTIC, 'NOT RUN: Pydantic is not installed')
class PydanticTests(SerializationChecks, unittest.TestCase):
    fallback = False

    @unittest.skipUnless(HAS_FASTAPI, 'NOT RUN: FastAPI is not installed')
    def test_actual_configuration_and_topology_handler_bodies(self):
        super().test_actual_configuration_and_topology_handler_bodies()


class GeneratedCopyTests(unittest.TestCase):
    def test_model_copies_match_canonical(self):
        canonical = (ROOT / COPIES[0]).read_bytes()
        self.assertEqual((ROOT / COPIES[3]).read_bytes(), canonical)
        for path in COPIES[1:3]:
            self.assertEqual((ROOT / path).read_bytes().split(b'\n', 5)[5], canonical)


if __name__ == '__main__':
    unittest.main()
