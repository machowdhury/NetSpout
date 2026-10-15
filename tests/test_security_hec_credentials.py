"""Offline HEC credential and endpoint behavior checks."""
import importlib
import io
import json
import os
from pathlib import Path
import ssl
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch, Mock
import uuid

BIN = Path(__file__).resolve().parents[1] / 'netspout' / 'bin'
sys.path.insert(0, str(BIN))
import datablaster_rest as handler
import run_simulation as runner


class SecurityHECTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.env = patch.dict(os.environ, {'SPLUNK_HOME': self.folder.name})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.fake = 'fake-' + uuid.uuid4().hex
        self.saved = ''
        self.calls = []
        self.http_calls = []
        self.authorized = True
        self.rest_mock = patch.object(handler.rest, 'simpleRequest', self.rest_call, create=True)
        self.rest_mock.start()
        self.addCleanup(self.rest_mock.stop)
        self.app_path = Path(self.folder.name, 'app')
        self.app_path.mkdir()
        (self.app_path / 'scenarios').mkdir()
        self.scenario = self.app_path / 'scenarios' / 'ok.yml'
        self.scenario.write_text('generatorWorkers: 1\n')
        runner_patch = patch.object(runner, 'APP_DIR', str(self.app_path))
        runner_patch.start()
        self.addCleanup(runner_patch.stop)
        self.temp_path = Path(self.folder.name, 'temp')
        self.temp_path.mkdir()
        app_patch = patch.object(handler, 'APP_DIR', str(self.app_path))
        app_patch.start()
        self.addCleanup(app_patch.stop)
        temp_patch = patch.object(handler.tempfile, 'gettempdir', return_value=str(self.temp_path))
        temp_patch.start()
        self.addCleanup(temp_patch.stop)
        handler.get_active_run_dir()
        self.http_mock = patch('urllib.request.urlopen', self.http_call)
        self.http_mock.start()
        self.addCleanup(self.http_mock.stop)

    def rest_call(self, url, sessionKey='', method='GET', postargs=None, **kwargs):
        self.calls.append((url, sessionKey, method))
        if 'current-context' in url:
            capabilities = ['netspout_admin'] if self.authorized and sessionKey == 'admin' else []
            return Mock(status=200), json.dumps({'entry': [{'content': {'capabilities': capabilities}}]})
        if method == 'POST':
            if '/netspout%3A' in url and not self.saved:
                return Mock(status=404), '{}'
            self.saved = postargs['password']
        if not self.saved:
            return Mock(status=404), '{}'
        return Mock(status=200), json.dumps({'entry': [{'content': {'clear_password': self.saved}}]})

    def http_call(self, request, **kwargs):
        self.http_calls.append((request.full_url, request.get_header('Authorization'), kwargs['context']))
        response = Mock(status=200)
        response.read.return_value = self.fake.encode()
        response.getcode.return_value = 200
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        return response

    def request(self, action, **kwargs):
        return handler.execute_request(dict(action=action, session_key='admin', **kwargs))

    def provision(self):
        handler.HECCredentialStore('admin').save(self.fake)

    def test_destination_and_request_credential_are_ignored(self):
        self.provision()
        supplied = 'fake-' + uuid.uuid4().hex
        code, result = self.request('test_hec', hec='https://unlisted.invalid:8088', token=supplied)
        self.assertEqual(code, 200)
        self.assertEqual(self.http_calls[0][0], handler.DEFAULT_CONFIG['hec_url'])
        self.assertEqual(self.http_calls[0][1], 'Splunk ' + self.fake)
        self.assertNotIn(self.fake, json.dumps(result))
        self.assertNotIn(supplied, json.dumps(result))

    def test_unlisted_server_destination_refused_before_credential_delivery(self):
        self.provision()
        handler._write_config(handler.CONFIG_FILE, {'hec_url': 'https://unlisted.invalid:8088'})
        code, result = self.request('test_hec')
        self.assertEqual(code, 400)
        self.assertFalse(self.http_calls)
        self.assertIn('allowed host and port', result['message'])

    def test_resolution_is_pure_but_delivery_enforces_server_allow_list(self):
        destination = 'https://127.0.0.1:8888'
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(handler.os, 'makedirs') as mkdir:
            self.assertEqual(handler.resolve_hec_urls(destination), [destination])
            mkdir.assert_not_called()
        with self.assertRaises(handler.HECConfigurationError):
            handler.test_hec_connection(destination, self.fake)
        with self.assertRaises(handler.HECConfigurationError):
            handler.hec_request(destination)
        with patch.object(runner.subprocess, 'Popen') as spawn:
            with self.assertRaises(handler.HECConfigurationError):
                runner.validate_and_stream_mv_scenario('example.yml', destination, self.fake, 10)
            spawn.assert_not_called()
        self.assertFalse(self.http_calls)

    def test_authorization_all_actions(self):
        self.provision()
        for action in ['start', 'run_scenario', 'save_config', 'test_hec', 'get_config',
                       'validate', 'validate_environment', 'blast_hec', 'stream_canvas_topology', 'stop', 'logs', 'status']:
            with self.subTest(action=action):
                self.authorized = False
                code, _ = self.request(action)
                self.assertEqual(code, 403)
        self.authorized = True
        for action in ['save_config', 'test_hec', 'get_config']:
            self.assertEqual(self.request(action)[0], 200)
        with patch.object(handler, 'get_current_status', return_value={'running': True, 'pid': 42}):
            code, result = self.request('start', scenario=str(self.scenario))
        self.assertEqual(code, 200)
        self.assertEqual(result['status'], 'warning')

    def test_round_trip_and_no_credential_files_on_save(self):
        with self.assertLogs(handler.logger, level='WARNING') as logs:
            handler.save_stored_config({'hec_token': self.fake, 'ssl_verify': False}, 'admin')
        self.assertEqual(handler.HECCredentialStore('admin').read(), self.fake)
        self.assertNotIn(self.fake, '\n'.join(logs.output))
        for path in Path(self.folder.name).rglob('*'):
            if path.is_file():
                self.assertNotIn(self.fake.encode(), path.read_bytes())
        code, response = self.request('get_config')
        self.assertEqual(code, 200)
        self.assertTrue(response['config']['hec_token_configured'])
        self.assertNotIn('hec_token', response['config'])
        self.assertNotIn(self.fake, json.dumps(response))

    def test_legacy_migration_removes_value_and_logs_rotation(self):
        Path(handler.CONFIG_FILE).write_text(json.dumps({'hec_token': self.fake, 'target_eps': 12}))
        with self.assertLogs(handler.logger, level='WARNING') as logs:
            code, result = self.request('get_config')
        self.assertEqual(code, 200)
        self.assertEqual(self.saved, self.fake)
        self.assertNotIn(self.fake, Path(handler.CONFIG_FILE).read_text())
        self.assertNotIn(self.fake, '\n'.join(logs.output))
        self.assertIn('rotated', '\n'.join(logs.output))
        self.assertEqual(result['config']['target_eps'], 12)

    def test_run_directory_private_and_no_fallback(self):
        path = handler.resolve_run_dir()
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o700)
        self.assertEqual(path, os.path.join(self.folder.name, 'var', 'run', 'netspout'))
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, 'SPLUNK_HOME'):
                handler.resolve_run_dir()
        with patch.object(handler.os, 'makedirs', side_effect=PermissionError):
            with self.assertRaisesRegex(RuntimeError, 'private NetSpout'):
                handler.resolve_run_dir()

    def test_import_without_splunk_home(self):
        environment = dict(os.environ)
        environment.pop('SPLUNK_HOME', None)
        environment['PYTHONDONTWRITEBYTECODE'] = '1'
        result = subprocess.run(
            [sys.executable, '-c',
             'import datablaster_rest, run_simulation, datablaster_executor; '
             'assert datablaster_rest.RUN_DIR == ""; '
             'assert datablaster_rest.CONFIG_FILE == ""; '
             'assert run_simulation.RUN_DIR == ""'],
            cwd=str(BIN), env=environment, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_first_runtime_operation_without_splunk_home_fails_without_files(self):
        before = sorted(str(path) for path in Path(self.folder.name).rglob('*'))
        with patch.dict(os.environ, {}, clear=True), \
             patch.object(handler.os, 'makedirs') as mkdir, \
             patch.object(handler.tempfile, 'mkstemp') as temporary:
            with self.assertRaisesRegex(handler.RunFolderError,
                                        'SPLUNK_HOME is required for the NetSpout run folder'):
                handler.get_stored_config('admin')
            code, response = self.request('status')
            self.assertEqual(code, 400)
            self.assertEqual(response['message'],
                             'SPLUNK_HOME is required for the NetSpout run folder')
            mkdir.assert_not_called()
            temporary.assert_not_called()
        self.assertEqual(before, sorted(str(path) for path in Path(self.folder.name).rglob('*')))

    def test_tls_requires_explicit_saved_admin_setting(self):
        self.provision()
        self.assertEqual(self.request('test_hec', ssl_verify=False)[0], 200)
        self.assertEqual(self.http_calls[-1][2].verify_mode, ssl.CERT_REQUIRED)
        self.authorized = False
        self.assertEqual(self.request('save_config', ssl_verify=False)[0], 403)
        self.authorized = True
        with self.assertLogs(handler.logger, level='WARNING'):
            self.assertEqual(self.request('save_config', ssl_verify=False)[0], 200)
        self.assertEqual(self.request('test_hec')[0], 200)
        self.assertEqual(self.http_calls[-1][2].verify_mode, ssl.CERT_NONE)

    def test_request_save_never_persists_supplied_credential_or_destination(self):
        self.provision()
        code, result = self.request('save_config', token=self.fake, hec_token=self.fake,
                                    hec='https://unlisted.invalid', hec_url='https://unlisted.invalid')
        self.assertEqual(code, 200)
        self.assertNotIn(self.fake, json.dumps(result))
        self.assertEqual(result['config']['hec_url'], handler.DEFAULT_CONFIG['hec_url'])
        self.assertNotIn(self.fake, Path(handler.CONFIG_FILE).read_text())

    def test_children_receive_stdin_without_credential_argv(self):
        self.provision()
        proc = Mock(pid=45, stdin=io.StringIO())
        class Pipe(io.StringIO):
            def close(self):
                self.captured = self.getvalue()
        proc.stdin = Pipe()
        with patch.object(handler, 'get_current_status', return_value={'running': False}), \
             patch.object(handler, 'get_orchestration_log_path', return_value=os.path.join(self.folder.name, 'launch.log')), \
             patch.object(handler.subprocess, 'Popen', return_value=proc) as spawn:
            code, result = self.request('start', scenario=str(self.scenario))
        self.assertEqual(code, 200)
        argv = spawn.call_args[0][0]
        self.assertNotIn(self.fake, argv)
        self.assertNotIn('--token', argv)
        self.assertNotIn('--splunkHECToken', argv)
        self.assertEqual(json.loads(proc.stdin.captured)['credential'], self.fake)
        self.assertNotIn(self.fake, Path(self.folder.name, 'launch.log').read_text())
        proc.stdin = Pipe()
        with patch.object(runner.subprocess, 'Popen', return_value=proc) as spawn:
            self.assertEqual(runner.validate_and_stream_mv_scenario('example.yml', handler.DEFAULT_CONFIG['hec_url'], self.fake, 10), 45)
        self.assertNotIn(self.fake, spawn.call_args[0][0])
        self.assertEqual(json.loads(proc.stdin.captured)['credential'], self.fake)

    def test_private_scenario_mode(self):
        original = self.app_path / 'scenarios' / 'original.yml'
        original.write_text('global:\n  output:\n    endpoints:\n      - https://localhost:8088\n    splunkHECToken:\n')
        path = runner.prepare_scenario_config(str(original), 10, handler.DEFAULT_CONFIG['hec_url'], self.fake)
        self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)
        self.assertEqual(Path(path).parent, Path(handler.RUN_DIR))
        self.assertIn(self.fake, Path(path).read_text())
        os.unlink(path)
        self.assertFalse(Path(path).exists())

    def test_native_run_deletes_private_config_and_redacts_output(self):
        self.provision()
        handler.save_stored_config({'ssl_verify': False}, 'admin')
        original = self.app_path / 'scenarios' / 'original.yml'
        original.write_text('global:\n  output:\n    endpoints:\n      - https://localhost:8088\n    splunkHECToken:\n')
        proc = Mock(stdout=io.StringIO(self.fake + '\n'), returncode=0)
        argv = ['runner', '--scenario', str(original), '--hec', handler.DEFAULT_CONFIG['hec_url']]
        with patch.object(sys, 'argv', argv), patch.object(sys, 'stdin', io.StringIO(json.dumps({'credential': self.fake}))), \
             patch.object(runner, 'resolve_binary', return_value='/fake/engine'), \
             patch.object(runner.signal, 'signal'), patch.object(runner.subprocess, 'Popen', return_value=proc) as spawn, \
             patch.object(sys, 'stdout', io.StringIO()) as output:
            with self.assertRaises(SystemExit) as exit_result:
                runner.main()
        self.assertEqual(exit_result.exception.code, 0)
        args = spawn.call_args[0][0]
        self.assertNotIn(self.fake, args)
        self.assertNotIn('--splunkHECToken', args)
        self.assertFalse(Path(args[2]).exists())
        self.assertNotIn(self.fake, output.getvalue())

    def test_executor_command_builder_contains_no_credential(self):
        import datablaster_executor
        values = {'config_file': 'scenario.yml', 'output': 'splunkhec',
                  'hec_url': handler.DEFAULT_CONFIG['hec_url'], 'hec_token': self.fake}
        args = datablaster_executor.DataBlasterExecutor.build_command_args('/fake/engine', values)
        self.assertNotIn(self.fake, args)
        self.assertNotIn('--splunkHECToken', args)


    def test_session_from_envelope_cannot_be_replaced_by_payload(self):
        self.provision()
        envelope = {'session': {'authtoken': 'viewer'}, 'payload': json.dumps({'action': 'get_config', 'session_key': 'admin'})}
        result = handler.DataBlasterRestHandler().handle(json.dumps(envelope))
        self.assertEqual(result['status'], 403)
        self.assertNotIn(self.fake, result['payload'])

class ReviewBoundaryTests(unittest.TestCase):
    setUp = SecurityHECTests.setUp
    rest_call = SecurityHECTests.rest_call
    http_call = SecurityHECTests.http_call
    provision = SecurityHECTests.provision

    def test_shared_configuration_and_unrecognized_keys_ignored(self):
        for folder in (self.temp_path, self.temp_path / 'netspout_run'):
            folder.mkdir(exist_ok=True)
            (folder / 'datablaster_config.json').write_text(json.dumps({
                'hec_url': 'https://unlisted.invalid:8088', 'hec_token': self.fake,
                'hec_allowed_hosts': ['unlisted.invalid'], 'ssl_verify': False}))
        cfg = handler.get_stored_config('admin')
        self.assertEqual(cfg, handler.DEFAULT_CONFIG)
        self.assertEqual(self.saved, '')
        handler.write_private_file(handler.CONFIG_FILE, json.dumps({'unknown': self.fake}))
        self.assertNotIn(self.fake, json.dumps(handler.get_stored_config('admin')))

    def test_migration_preserves_existing_and_is_idempotent(self):
        self.provision()
        legacy = 'fake-' + uuid.uuid4().hex
        handler.write_private_file(handler.CONFIG_FILE, json.dumps({'hec_token': legacy}))
        self.assertNotIn('hec_token', handler.get_stored_config('viewer'))
        self.assertIn(legacy, Path(handler.CONFIG_FILE).read_text())
        handler.get_stored_config('admin')
        handler.get_stored_config('admin')
        self.assertEqual(self.saved, self.fake)
        self.assertNotIn(legacy, Path(handler.CONFIG_FILE).read_text())
        self.saved = ''
        handler.write_private_file(handler.CONFIG_FILE, json.dumps({'hec_token': legacy}))
        handler.get_stored_config('admin')
        posts = len([call for call in self.calls if call[2] == 'POST'])
        handler.get_stored_config('admin')
        self.assertEqual(posts, len([call for call in self.calls if call[2] == 'POST']))
        self.assertEqual(self.saved, legacy)

    def test_private_folder_and_files_refuse_symlinks(self):
        outside = Path(self.folder.name, 'outside')
        outside.write_text('original')
        link = Path(handler.RUN_DIR, 'link')
        link.symlink_to(outside)
        with self.assertRaises(OSError):
            handler.write_private_file(str(link), 'replacement')
        self.assertEqual(outside.read_text(), 'original')
        Path(handler.CONFIG_FILE).symlink_to(outside)
        self.assertEqual(handler.get_stored_config('admin'), handler.DEFAULT_CONFIG)
        Path(handler.CONFIG_FILE).unlink()
        handler.write_private_file(handler.CONFIG_FILE, json.dumps({'ssl_verify': False}))
        os.chmod(handler.CONFIG_FILE, 0o666)
        self.assertTrue(handler.get_stored_config('admin')['ssl_verify'])
        os.chmod(handler.RUN_DIR, 0o755)
        handler.resolve_run_dir()
        self.assertEqual(os.stat(handler.RUN_DIR).st_mode & 0o777, 0o700)
        with patch.object(handler.os, 'fstat', return_value=Mock(st_uid=os.getuid() + 1)):
            with self.assertRaises(handler.RunFolderError):
                handler.resolve_run_dir()

    def test_scenarios_and_native_destination_boundary(self):
        self.provision()
        outside = Path(self.folder.name, 'outside.yml')
        outside.write_text('generatorWorkers: 1\n')
        (self.app_path / 'scenarios' / 'link.yml').symlink_to(outside)
        for name in (str(outside), 'link.yml', 'scenarios/../../outside.yml'):
            with self.assertRaises(ValueError):
                handler.validate_and_sanitize({'action': 'start', 'scenario': name, 'session_key': 'admin'})
        self.assertEqual(handler.resolve_scenario_path('ok.yml'), os.path.realpath(self.scenario))
        self.scenario.write_text('endpoints:\n  - "https://unlisted.invalid:8088"\n'
                                 "other: 'https://unlisted.invalid:8088'\n")
        output = runner.prepare_scenario_config(str(self.scenario), 10, handler.DEFAULT_CONFIG['hec_url'], self.fake)
        self.assertNotIn('unlisted.invalid', Path(output).read_text())
        self.assertIn(handler.DEFAULT_CONFIG['hec_url'], Path(output).read_text())
        with self.assertRaises(handler.HECConfigurationError):
            runner.prepare_scenario_config(str(self.scenario), 10, 'https://unlisted.invalid:8088', self.fake)

    def test_stop_group_and_stale_cleanup(self):
        outside = Path(self.folder.name, 'outside.yml')
        outside.write_text('keep')
        for name in ('active_sim_one.yml', 'canvas_custom_two.yml'):
            handler.write_private_file(os.path.join(handler.RUN_DIR, name), self.fake)
        Path(handler.RUN_DIR, 'active_sim_link.yml').symlink_to(outside)
        handler.write_private_file(handler.STATUS_FILE, '{}')
        handler.write_private_file(handler.PID_FILE, '42')
        with patch.object(handler, 'get_current_status', return_value={'running': True, 'pid': 42}), \
             patch.object(handler.os, 'killpg', side_effect=[None, ProcessLookupError]) as kill:
            self.assertEqual(handler.stop_simulation()['status'], 'success')
        self.assertEqual(kill.call_args_list[0].args, (42, handler.signal.SIGTERM))
        self.assertEqual(outside.read_text(), 'keep')
        self.assertEqual(os.listdir(handler.RUN_DIR), ['datablaster_status.json'])

    def test_binary_trust_boundary(self):
        import datablaster_executor as executor
        binary_dir = self.app_path / 'bin'
        binary_dir.mkdir()
        plat = 'linux' if sys.platform.startswith('linux') else ('darwin' if sys.platform == 'darwin' else 'win32')
        binary = binary_dir / ('data-blaster-' + plat)
        binary.write_bytes(b'\x7fELF' + b'\0' * 60)
        os.chmod(binary, 0o755)
        self.assertEqual(runner.resolve_binary(), str(binary))
        with patch.object(executor, 'APP_DIR', str(self.app_path)):
            self.assertEqual(executor.DataBlasterExecutor.get_platform_binary(), str(binary))
        os.chmod(binary, 0o775)
        self.assertEqual(runner.resolve_binary(), 'python_engine')
        binary.unlink()
        binary.symlink_to(self.scenario)
        self.assertEqual(runner.resolve_binary(), 'python_engine')

    def test_folder_symlink_refused_and_kill_waits_for_runner_grace(self):
        import shutil
        rd = handler.RUN_DIR
        shutil.rmtree(rd)
        elsewhere = Path(self.folder.name, 'elsewhere')
        elsewhere.mkdir()
        os.symlink(elsewhere, rd)
        with self.assertRaises(handler.RunFolderError):
            handler.resolve_run_dir()
        os.unlink(rd)
        handler.get_active_run_dir()
        with patch.object(handler, 'get_current_status', return_value={'running': True, 'pid': 42}), \
             patch.object(handler.os, 'killpg') as kill, \
             patch.object(handler.time, 'monotonic', side_effect=[0, 1, 6]), \
             patch.object(handler.time, 'sleep'):
            self.assertEqual(handler.stop_simulation()['status'], 'success')
        self.assertEqual(kill.call_args_list[-1].args, (42, handler.signal.SIGKILL))

    def test_runner_signal_removes_canvas_file(self):
        self.provision()
        canvas = Path(handler.RUN_DIR, 'canvas_custom_signal.yml')
        handler.write_private_file(str(canvas), 'generatorWorkers: 1\n')
        registered = {}
        def register(sig, callback):
            registered[sig] = callback
        def stream(*args):
            registered[runner.signal.SIGINT](runner.signal.SIGINT, None)
        with patch.object(sys, 'argv', ['runner', '--scenario', str(canvas), '--python-stream']), \
             patch.object(sys, 'stdin', io.StringIO(json.dumps({'credential': self.fake}))), \
             patch.object(runner.signal, 'signal', side_effect=register), \
             patch.object(runner, 'run_python_streamer', side_effect=stream):
            with self.assertRaises(SystemExit):
                runner.main()
        self.assertFalse(canvas.exists())



class V4BoundaryTests(unittest.TestCase):
    setUp = SecurityHECTests.setUp
    rest_call = SecurityHECTests.rest_call
    http_call = SecurityHECTests.http_call
    provision = SecurityHECTests.provision
    request = SecurityHECTests.request

    def test_native_rebuild_and_builtin_sample_preservation(self):
        self.provision()
        self.scenario.write_text(
            'dest: &d "https\\x3a//evil.example:8088"\n'
            'general: {output: {endpoints: [*d], outputs: [{url: *d}]}}\n'
            'samples: [{name: sample, syslogDestinationHost: evil.example, '
            'lines: [{source: "app://ok", _raw: "hello", index: main}]}]\n')
        out = runner.prepare_scenario_config(str(self.scenario), 100, handler.DEFAULT_CONFIG['hec_url'], self.fake)
        text = Path(out).read_text()
        self.assertNotIn('evil.example', text)
        self.assertIn('source: app://ok', text)
        self.assertIn(handler.DEFAULT_CONFIG['hec_url'], text)
        self.assertIn('outputter: splunkhec', text)
        self.assertIn('bufferBytes: 4096', text)
        for src in (BIN.parent / 'appserver' / 'static' / 'scenarios').glob('*.yml'):
            output = runner.prepare_scenario_config(str(src), 100, handler.DEFAULT_CONFIG['hec_url'], self.fake)
            content = Path(output).read_text()
            self.assertIn('samples:', content, src.name)
            self.assertIn(self.fake, content, src.name)
            self.assertIn(handler.DEFAULT_CONFIG['hec_url'], content, src.name)
            os.unlink(output)
        with patch.dict(sys.modules, {'yaml': None}):
            with self.assertRaises(ImportError):
                runner.prepare_scenario_config(str(self.scenario), 100, handler.DEFAULT_CONFIG['hec_url'], self.fake)

    def test_canvas_validation_and_json_values(self):
        self.provision()
        for field in ('id', 'vendor', 'host', 'index', 'source', 'sourcetype', 'sampleEvent'):
            for value in ('x\nfoo', 'x\u0085foo', 'x\u2028foo', 'x"foo', 'x\\foo', 1, 'x' * 4097):
                code, _ = self.request('stream_canvas_topology', nodes=[{field: value}])
                self.assertEqual(code, 400)
        for nodes in ({}, [None], [{}] * 501):
            self.assertEqual(self.request('stream_canvas_topology', nodes=nodes)[0], 400)
        with patch.object(runner, 'validate_and_stream_mv_scenario', return_value=123):
            runner.stream_custom_canvas_topology([{'id': 'n1', 'host': 'true', 'index': '123',
                                                   'source': 'app://ok', 'sampleEvent': 'hello: world'}], [],
                                                  handler.DEFAULT_CONFIG['hec_url'], self.fake, 10)
        canvas = next(Path(handler.RUN_DIR).glob('canvas_custom_*'))
        values = {}
        for entry in canvas.read_text().splitlines():
            field, sep, value = entry.strip().removeprefix('- ').partition(':')
            if sep and field in ('host', 'index', '_raw'):
                values[field] = json.loads(value)
        self.assertEqual(values['host'], 'true')
        self.assertEqual(values['index'], '123')
        self.assertEqual(values['_raw'], 'hello: world')

    def test_legacy_sources_retry_without_losing_plaintext(self):
        for app_source in (False, True):
            for failing in ('read', 'save'):
                self.saved = ''
                path = (self.app_path / 'var' / 'run' / 'datablaster_config.json'
                        if app_source else Path(handler.CONFIG_FILE))
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(json.dumps({'hec_token': self.fake, 'target_eps': 7}))
                os.chmod(path, 0o644)
                handler.get_stored_config('viewer')
                self.assertIn(self.fake, path.read_text())
                self.assertEqual(path.stat().st_mode & 0o077, 0)
                with patch.object(handler.HECCredentialStore, failing, side_effect=RuntimeError(self.fake)):
                    with self.assertLogs(handler.logger, level='WARNING') as logs:
                        cfg = handler.get_stored_config('admin')
                self.assertNotIn(self.fake, json.dumps(cfg))
                self.assertNotIn(self.fake, str(logs.output))
                self.assertIn(self.fake, path.read_text())
                handler.get_stored_config('admin')
                self.assertEqual(self.saved, self.fake)
                self.assertFalse(path.exists() and self.fake in path.read_text())
                posts = len(self.calls)
                handler.get_stored_config('admin')
                self.assertEqual(len(self.calls), posts)

    def test_app_legacy_writable_copy_set_aside_and_symlink_ignored(self):
        path = self.app_path / 'var' / 'run' / 'datablaster_config.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'hec_token': self.fake}))
        os.chmod(path, 0o666)
        handler.get_stored_config('admin')
        handler.get_stored_config('admin')
        self.assertEqual(self.saved, '')
        copies = list(path.parent.iterdir())
        self.assertEqual(len(copies), 1)
        self.assertIn(self.fake, copies[0].read_text())
        self.assertEqual(copies[0].stat().st_mode & 0o077, 0)
        path.symlink_to(copies[0])
        handler.get_stored_config('admin')
        self.assertEqual(self.saved, '')
        self.assertIn(self.fake, copies[0].read_text())

    def test_overlapping_starts_and_canvas_launch_once(self):
        import threading
        self.provision()
        for first, second in (('start', 'start'), ('start', 'stream_canvas_topology'),
                              ('stream_canvas_topology', 'start'), ('stream_canvas_topology', 'stream_canvas_topology')):
            handler.cleanup_stale_run_files()
            Path(handler.PID_FILE).unlink(missing_ok=True)
            entered, release = threading.Event(), threading.Event()
            running = {'value': False}
            calls = []
            class Pipe(io.StringIO):
                def close(self):
                    pass
            def spawn(cmd, **kwargs):
                calls.append(cmd)
                entered.set()
                release.wait(1)
                running['value'] = True
                return Mock(pid=123, stdin=Pipe())
            def status():
                return {'running': running['value'], 'pid': 123 if running['value'] else None}
            results = []
            def request(action):
                results.append(self.request(action, scenario='ok.yml', eps=100, nodes=[{'id': 'n1'}], links=[]))
            with patch.object(handler, 'get_current_status', side_effect=status), \
                 patch.object(subprocess, 'Popen', side_effect=spawn):
                a = threading.Thread(target=request, args=(first,))
                a.start()
                self.assertTrue(entered.wait(3))
                b = threading.Thread(target=request, args=(second,))
                b.start()
                release.set()
                a.join(5)
                b.join(5)
            self.assertFalse(a.is_alive() or b.is_alive())
            self.assertEqual(len(calls), 1, results)
            self.assertEqual(Path(handler.PID_FILE).read_text(), '123')
            self.assertEqual(sum(body['status'] == 'warning' for code, body in results), 1)

    def test_start_stop_restart_and_real_exited_child(self):
        import signal
        import time
        self.provision()
        real_popen = subprocess.Popen
        children = []
        def spawn(cmd, **kw):
            child = real_popen([sys.executable, '-c',
                               'import sys,time; sys.stdin.read(); time.sleep(60)'],
                              stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL, text=True, start_new_session=True)
            children.append(child)
            return child
        def cleanup():
            for child in children:
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGKILL)
                child.wait(timeout=5)
        self.addCleanup(cleanup)
        with patch.object(subprocess, 'Popen', side_effect=spawn):
            self.assertEqual(self.request('start', scenario='ok.yml')[0], 200)
            self.assertEqual(self.request('stream_canvas_topology', nodes=[{'id': 'n1'}])[0], 409)
            self.assertEqual(len(children), 1)
            self.assertEqual(handler.stop_simulation()['status'], 'success')
            self.assertIsNotNone(children[0].poll())
            self.assertEqual(self.request('stream_canvas_topology', nodes=[{'id': 'n1'}])[0], 200)
            self.assertEqual(len(children), 2)
            self.assertEqual(handler.stop_simulation()['status'], 'success')
        child = real_popen([sys.executable, '-c', 'pass'])
        children.append(child)
        deadline = time.monotonic() + 5
        while handler.is_process_running(child.pid) and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertFalse(handler.is_process_running(child.pid))

    def test_start_lock_is_private_and_excludes_other_process(self):
        code = (
            'import fcntl,os,sys\n'
            'fd=os.open(sys.argv[1], os.O_RDWR)\n'
            'try:\n fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)\n'
            'except BlockingIOError:\n sys.exit(0)\n'
            'sys.exit(1)\n')
        with handler.simulation_start_lock():
            path = os.path.join(handler.RUN_DIR, 'datablaster.lock')
            result = subprocess.run([sys.executable, '-c', code, path], capture_output=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o600)

    def test_exited_child_reaped_before_process_probe(self):
        with patch.object(handler.os, 'waitpid', return_value=(123, 0)), \
             patch.object(handler.os, 'kill') as kill:
            self.assertFalse(handler.is_process_running(123))
            kill.assert_not_called()
        with patch.object(handler.os, 'waitpid', side_effect=ChildProcessError), \
             patch.object(handler.os, 'kill') as kill:
            self.assertTrue(handler.is_process_running(123))
            kill.assert_called_once_with(123, 0)

    def test_onboard_count_and_executor_scenarios(self):
        self.provision()
        for count, expected in ((5, 5), (5000, 1000), (0, 1)):
            self.http_calls.clear()
            code, body = self.request('onboard_sample', count=count, sample_content='hello', sourcetype='custom:telemetry')
            self.assertEqual(code, 200)
            self.assertEqual(body['events_count'], expected)
        import datablaster_executor as executor
        with patch.object(handler, 'APP_DIR', str(BIN.parent)):
            for alias in list(executor.DataBlasterExecutor.SCENARIO_MAP) + [None]:
                payload = {'eps': 10, 'session_key': 'admin'}
                if alias is not None:
                    payload['scenario'] = alias
                out = executor.DataBlasterExecutor.sanitize_inputs(payload)
                self.assertEqual(out['config_file'], handler.resolve_scenario_path(out['config_file'], str(BIN.parent)))


if __name__ == "__main__":
    unittest.main()
