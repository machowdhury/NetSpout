"""Regression for scenario startup under Splunk's persistent module loader."""
import unittest
from test_native_loader_context import NativeLoaderTests


class RunnerLoaderTests(unittest.TestCase):
    probe = NativeLoaderTests.probe

    def test_runner_binds_existing_runtime_without_path_or_module_duplicates(self):
        self.probe(r'''
runner = handler._simulation_runner()
assert runner._NATIVE_REST_RUNTIME is handler
assert runner.get_stored_config is handler.get_stored_config
assert runner.cleanup_stale_run_files is handler.cleanup_stale_run_files
assert runner._NATIVE_REST_RUNTIME._START_LOCK is handler._START_LOCK
assert runner is handler._simulation_runner() is sys.modules['run_simulation']
assert 'datablaster_rest' not in sys.modules
assert sys.path == original_path
''')

    def test_concurrent_resolution_reuses_runner(self):
        self.probe(r'''
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
    runners=list(pool.map(lambda _:handler._simulation_runner(), range(24)))
assert all(r is runners[0] for r in runners)
assert 'datablaster_rest' not in sys.modules
assert sys.path == original_path
''')

    def test_foreign_runner_and_second_handler_rejected(self):
        self.probe(r'''
runner=handler._simulation_runner()
second=load(alias+'_second')
try:
    second._simulation_runner()
    raise AssertionError('Second runtime accepted')
except RuntimeError as e:
    assert str(e)=='Simulation runner module identity conflict'
runner.__file__='/other/app/run_simulation.py'
try:
    handler._simulation_runner()
    raise AssertionError('Foreign runner accepted')
except RuntimeError as e:
    assert str(e)=='Simulation runner module identity conflict'
assert sys.modules['run_simulation'] is runner
assert 'datablaster_rest' not in sys.modules
''')

    def test_startup_resolves_runner_and_passes_run_identity_to_subprocess(self):
        self.probe(r'''
from unittest.mock import patch, MagicMock
with tempfile.TemporaryDirectory() as home:
    os.environ['SPLUNK_HOME']=home
    handler.get_active_run_dir()
    helper=handler._native_monitor()
    proc=MagicMock();proc.pid=12345
    params={'scenario':str(filename.parent.parent/'appserver/static/scenarios/scenario_network_22_authentication_storm.yml'),
        'eps':10,'hec':'https://127.0.0.1:8088/services/collector','ssl_verify':True,
        'token':'dummy-only','_native_record':{'run_id':'00000000-0000-4000-8000-000000000001'}}
    with patch.object(handler,'get_current_status',return_value={'running':False}), \
         patch.object(handler,'cleanup_stale_run_files'), \
         patch.object(helper,'_update_lock_held'), \
         patch.object(helper,'publish_status'), \
         patch.object(handler.subprocess,'Popen',return_value=proc) as spawn:
        result=handler._start_simulation_locked(params)
    assert result['status']=='success'
    assert spawn.call_args.args[0][1]==str(filename.with_name('run_simulation.py'))
    sent=json.loads(proc.stdin.write.call_args.args[0])
    assert sent['run_id']==params['_native_record']['run_id']
    assert handler._simulation_runner()._NATIVE_REST_RUNTIME is handler
    assert 'datablaster_rest' not in sys.modules
    assert sys.path==original_path
''')
