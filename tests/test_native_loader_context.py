"""Offline reproduction of Splunk's file-based, mangled-name REST loader."""
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
PRELUDE = r'''
import concurrent.futures, importlib.util, json, os, pathlib, sys, tempfile, types
from run_sec2b_offline import network_guard
sys.addaudithook(network_guard)
filename = pathlib.Path('netspout/bin/datablaster_rest.py').resolve()
helperfile = filename.with_name('native_run_monitor.py')
assert all(pathlib.Path(p or os.getcwd()).resolve() != filename.parent for p in sys.path)
original_path = list(sys.path)
assert 'datablaster_rest' not in sys.modules

def load(name, path=filename):
    # Same spec/module/registration/exec sequence as Splunk 10.2.7 appserver.py.
    spec = importlib.util.spec_from_file_location(name, str(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module

alias = 'pschand__datablaster_rest__in__opt_splunk_etc_apps_netspout_bin'
handler = load(alias)
'''


class NativeLoaderTests(unittest.TestCase):
    def probe(self, body):
        result = subprocess.run([sys.executable, '-B', '-c', PRELUDE + body],
            cwd=ROOT, env=dict(os.environ, PYTHONPATH=os.pathsep.join(str(ROOT / p) for p in ('src','backend','tests'))),
            capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_loader_resolves_helper_and_preserves_handler_lock_identity(self):
        self.probe(r'''
helper = handler._native_monitor()
assert helper.api() is handler
assert helper.api()._START_LOCK is handler._START_LOCK
assert helper.api().simulation_start_lock is handler.simulation_start_lock
assert helper is sys.modules['native_run_monitor']
assert 'datablaster_rest' not in sys.modules
assert handler._native_monitor() is helper
assert sys.path == original_path
''')

    def test_native_runs_uses_loader_state_and_authorization(self):
        self.probe(r'''
with tempfile.TemporaryDirectory() as folder:
    os.environ['SPLUNK_HOME'] = folder
    handler.has_netspout_admin = lambda session: session == 'dummy-authorized-session'
    instance = handler.DataBlasterRestHandler([], None)
    denied = instance.handle(json.dumps({'payload': json.dumps({'action':'native_runs'})}))
    assert denied['status'] == 403
    assert not pathlib.Path(folder, 'var').exists()
    reply = instance.handle(json.dumps({'session':{'authtoken':'dummy-authorized-session'},
        'payload':json.dumps({'action':'native_runs'})}))
    assert reply['status'] == 200
    assert json.loads(reply['payload']) == {'status':'success','runs':[]}
    assert handler.STATUS_FILE == str(pathlib.Path(folder, 'var/run/netspout/datablaster_status.json'))
    assert handler._native_monitor().api().STATUS_FILE == handler.STATUS_FILE
    assert pathlib.Path(handler.STATUS_FILE).stat().st_mode & 0o777 == 0o600
assert 'datablaster_rest' not in sys.modules
assert sys.path == original_path
''')

    def test_repeated_concurrent_resolution_reuses_one_helper(self):
        self.probe(r'''
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    helpers = list(pool.map(lambda _:handler._native_monitor(), range(32)))
assert all(item is helpers[0] for item in helpers)
assert helpers[0].api() is handler
assert 'datablaster_rest' not in sys.modules
assert sys.path == original_path
''')

    def test_existing_unbound_helper_is_reused(self):
        self.probe(r'''
existing = load('native_run_monitor', helperfile)
assert existing._runtime is None
assert handler._native_monitor() is existing
assert existing.api() is handler
assert 'datablaster_rest' not in sys.modules
''')

    def test_conflicting_helper_origin_is_rejected(self):
        self.probe(r'''
foreign = types.ModuleType('native_run_monitor')
foreign.__file__ = '/different/app/native_run_monitor.py'
sys.modules['native_run_monitor'] = foreign
try:
    handler._native_monitor()
    raise AssertionError('Conflicting helper accepted')
except RuntimeError as exc:
    assert str(exc) == 'Native monitor module identity conflict'
assert sys.modules['native_run_monitor'] is foreign
assert 'datablaster_rest' not in sys.modules
''')

    def test_second_handler_and_ordinary_duplicate_are_rejected(self):
        self.probe(r'''
helper = handler._native_monitor()
second = load(alias + '_second')
try:
    second._native_monitor()
    raise AssertionError('Second runtime accepted')
except RuntimeError as exc:
    assert str(exc) == 'Native monitor runtime identity conflict'
assert helper.api() is handler
assert handler._START_LOCK is not second._START_LOCK
ordinary = types.ModuleType('datablaster_rest')
ordinary.__file__ = str(filename)
sys.modules['datablaster_rest'] = ordinary
try:
    handler._native_monitor()
    raise AssertionError('Ordinary duplicate accepted')
except RuntimeError as exc:
    assert str(exc) == 'Native monitor runtime identity conflict'
assert helper.api() is handler
assert sys.modules['datablaster_rest'] is ordinary
assert sys.path == original_path
''')

    def test_failed_initial_binding_does_not_leave_cached_helper(self):
        self.probe(r'''
foreign = types.ModuleType('datablaster_rest')
foreign.__file__ = str(filename)
sys.modules['datablaster_rest'] = foreign
try:
    handler._native_monitor()
    raise AssertionError('Conflicting initial binding accepted')
except RuntimeError:
    pass
assert 'native_run_monitor' not in sys.modules
assert sys.modules['datablaster_rest'] is foreign
''')


if __name__ == '__main__':
    from run_sec2b_offline import network_guard
    sys.addaudithook(network_guard)
    unittest.main(verbosity=2, failfast=True)
