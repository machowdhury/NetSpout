"""Offline native history, correlation, search and UI contract regressions."""
import concurrent.futures
import copy
import io
import json
import os
import signal
from pathlib import Path
import subprocess
import sys
import time
import types
import unittest
import uuid
from unittest.mock import MagicMock, patch
import test_splunk_setup_workflow as fixtures

handler = fixtures.handler
import native_run_monitor as monitor
import run_simulation as runner


class MonitoringTests(unittest.TestCase):
    setUp = fixtures.NativeSetupTests.setUp
    rest = fixtures.NativeSetupTests.rest

    def record(self):
        return monitor.begin('onboard_sample', dict(index='main', hec=handler.DEFAULT_CONFIG['hec_url']), 'admin')

    def complete(self, r, age=120):
        return monitor.update(r['run_id'], lambda x: x.update(started_at=time.time()-age-10,
            ended_at=time.time()-age, execution_state='COMPLETED'))

    def test_retention_limits_expiry_and_active_preservation(self):
        r = self.record()
        now = time.time()
        rows = []
        for n in range(110):
            item = copy.deepcopy(r)
            item.update(run_id=str(uuid.uuid4()), started_at=now-1000, ended_at=now-n, execution_state='COMPLETED')
            rows.append(item)
        expired = copy.deepcopy(rows[0]); expired.update(run_id=str(uuid.uuid4()), started_at=now-monitor.TTL-1, ended_at=now-monitor.TTL)
        rows.extend([expired, r, {'run_id': 'malformed'}])
        kept = monitor.retain(rows, now)
        self.assertEqual(len(kept), 101)
        self.assertIn(r, kept)
        self.assertNotIn(expired, kept)
        self.assertEqual(kept, monitor.retain(list(reversed(rows)), now))

    def test_concurrent_updates_and_atomic_failure(self):
        records = [self.record() for _ in range(8)]
        def edit(r):
            monitor.update(r['run_id'], lambda x: x['counters'].update(generated=7))
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            list(pool.map(edit, records))
        rows = monitor.history()
        self.assertEqual(len(rows), 8)
        self.assertTrue(all(r['counters']['generated'] == 7 for r in rows))
        before = Path(handler.STATUS_FILE).read_bytes()
        with patch.object(handler.os, 'replace', side_effect=OSError('dummy-private')):
            with self.assertRaises(OSError):
                edit(records[0])
        self.assertEqual(Path(handler.STATUS_FILE).read_bytes(), before)

    def test_legacy_status_and_secret_free_records(self):
        handler._write_config(handler.STATUS_FILE, {'pid': 123, 'scenario': 'existing.yml'})
        r = self.record()
        with handler.simulation_start_lock():
            monitor.publish_status({'pid': 456})
        state = monitor.read_state()
        self.assertEqual(state['pid'], 456)
        self.assertEqual(state['scenario'], 'existing.yml')
        self.assertEqual(state['native_runs'][0]['run_id'], r['run_id'])
        self.assertEqual(r['counters'], dict.fromkeys(monitor.COUNTERS))
        self.assertEqual(set(r['destination']), {'transport', 'host', 'port'})
        self.assertNotIn('credential', json.dumps(state))
        self.assertNotIn('sample_content', json.dumps(state))
        self.assertEqual(os.stat(handler.STATUS_FILE).st_mode & 0o777, 0o600)

    def test_log_and_metric_fields_preserve_payload(self):
        rid = str(uuid.uuid4())
        for event in ({'event': '%ASA-4-TEST original', 'sourcetype': 'cisco:asa'},
                      {'event': 'metric', 'sourcetype': 'vendor:metric', 'fields': {'metric_name:cpu': 3.0}}):
            original = copy.deepcopy(event)
            result = monitor.attach(event, rid)
            self.assertEqual(event, original)
            self.assertEqual(result['event'], original['event'])
            self.assertEqual(result['sourcetype'], original['sourcetype'])
            self.assertEqual(result['fields']['netspout_run_id'], rid)

    def test_server_ownership_and_actual_hec_payload(self):
        self.credentials['hec_token'] = 'dummy-provisioned-token'
        reply = MagicMock(status=200); reply.__enter__.return_value = reply; reply.read.return_value = b'{"code":0}'
        supplied = str(uuid.uuid4())
        with patch('urllib.request.urlopen', return_value=reply) as send:
            code, response = handler.execute_request(dict(action='onboard_sample', session_key='admin',
                run_id=supplied, sample_content='dummy vendor raw', sourcetype='cisco:ios', index='main'))
        self.assertEqual(code, 200)
        r = response['native_run']
        self.assertNotEqual(r['run_id'], supplied)
        event = json.loads(send.call_args.args[0].data)
        self.assertEqual(event['fields']['netspout_run_id'], r['run_id'])
        self.assertEqual(event['event'], 'dummy vendor raw')
        self.assertEqual(r['counters']['accepted'], 1)
        self.assertEqual(r['verification']['state'], 'NOT_CHECKED')
        self.assertNotIn('dummy-provisioned-token', Path(handler.STATUS_FILE).read_text())
        self.assertEqual(handler.execute_request(dict(action='native_runs', session_key='viewer'))[0], 403)

    def test_public_and_lock_held_updates_share_atomic_writer(self):
        r = self.record()
        with patch.object(handler, '_write_config', wraps=handler._write_config) as writer:
            with patch.object(handler, 'simulation_start_lock', wraps=handler.simulation_start_lock) as lock:
                monitor.update(r['run_id'], lambda x: x['counters'].update(generated=1))
                self.assertEqual(lock.call_count, 1)
            with handler.simulation_start_lock():
                with patch.object(handler, 'simulation_start_lock', side_effect=AssertionError('Lock reacquired')):
                    monitor._update_lock_held(r['run_id'], lambda x: x['counters'].update(generated=2))
            self.assertEqual(writer.call_count, 2)
        self.assertEqual(monitor.history()[0]['counters']['generated'], 2)

    def test_subprocess_private_propagation_and_binary_unsupported(self):
        self.credentials['hec_token'] = 'dummy-token'
        r = monitor.begin('start', dict(hec=handler.DEFAULT_CONFIG['hec_url']))
        scenario = self.app / 'scenario.yml'; scenario.write_text('samples: []')
        clean = dict(scenario=str(scenario), eps=10, hec=handler.DEFAULT_CONFIG['hec_url'],
                     token='dummy-token', ssl_verify=False, _native_record=r)
        pipe = io.StringIO()
        class Pipe(io.StringIO):
            def close(self):
                self.saved = self.getvalue()
        pipe = Pipe()
        proc = types.SimpleNamespace(pid=99, stdin=pipe)
        with patch.object(handler, 'get_current_status', return_value={'running': False}), \
             patch.object(handler.subprocess, 'Popen', return_value=proc), \
             patch.object(runner, 'resolve_binary', return_value='/dummy/external-binary'):
            def deadline(signum, frame):
                raise TimeoutError('Scenario startup exceeded the five-second lock deadline')
            previous_handler = signal.signal(signal.SIGALRM, deadline)
            previous_timer = signal.setitimer(signal.ITIMER_REAL, 5)
            try:
                result = handler.start_simulation(clean)
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
                signal.signal(signal.SIGALRM, previous_handler)
                signal.setitimer(signal.ITIMER_REAL, *previous_timer)
        self.assertEqual(json.loads(pipe.saved)['run_id'], r['run_id'])
        self.assertEqual(result['pid'], 99)
        self.assertEqual(monitor.read_state()['native_runs'][0]['correlation'], 'UNSUPPORTED')

    def search(self, r, results, status=None, error=False):
        calls = []
        def request(url, **kw):
            calls.append((url, kw))
            if error:
                raise TimeoutError('dummy-private')
            data = ({'sid': 'dummy-sid'} if kw.get('method') == 'POST' else
                    {'results': results} if '/results?' in url else
                    {'entry': [{'content': status or {'isDone': True, 'dispatchState': 'DONE'}}]})
            return types.SimpleNamespace(status=200), json.dumps(data)
        with patch.object(handler.rest, 'simpleRequest', side_effect=request), \
             patch.object(handler, 'is_process_running', return_value=True):
            code, response = monitor.verification(r['run_id'], 'admin')
        return code, response, calls

    def test_matching_search_is_separate_from_acceptance_and_bounded(self):
        r = self.complete(self.record())
        code, response, calls = self.search(r, [{'netspout_run_id': r['run_id'], 'count': '2'}])
        self.assertEqual(response['run']['verification']['state'], 'VERIFIED')
        self.assertIsNone(response['run']['counters']['accepted'])
        query = calls[0][1]['postargs']['search']
        self.assertIn('index="main"', query)
        self.assertIn('netspout_run_id::"' + r['run_id'] + '"', query)
        self.assertIn('earliest=' + str(int(r['started_at'])), query)
        self.assertNotIn('index=*', query)

    def test_nonmatching_results_are_inconclusive(self):
        r = self.complete(self.record())
        _, response, _ = self.search(r, [{'netspout_run_id': str(uuid.uuid4()), 'count': '100'}])
        self.assertEqual(response['run']['verification']['state'], 'INCONCLUSIVE')

    def test_no_matches_delay_and_completed_window(self):
        for age, expected in ((1, 'INCONCLUSIVE'), (120, 'NOT_FOUND')):
            r = self.complete(self.record(), age)
            _, response, _ = self.search(r, [])
            self.assertEqual(response['run']['verification']['state'], expected)

    def test_incomplete_search_job_is_reused(self):
        r = self.complete(self.record())
        _, response, _ = self.search(r, [], {'isDone': False, 'dispatchState': 'RUNNING'})
        self.assertEqual(response['run']['verification']['state'], 'INCONCLUSIVE')
        _, response, calls = self.search(r, [{'netspout_run_id': r['run_id'], 'count': '1'}])
        self.assertFalse(any(kw.get('method') == 'POST' for _, kw in calls))
        self.assertEqual(response['run']['verification']['state'], 'VERIFIED')

    def test_errors_and_partial_search_never_verify(self):
        r = self.complete(self.record())
        _, response, _ = self.search(r, [], error=True)
        self.assertEqual(response['run']['verification']['state'], 'ERROR')
        for status in ({'isDone': True, 'dispatchState': 'DONE', 'isFinalized': True},
                       {'isDone': True, 'dispatchState': 'DONE', 'messages': ['warning']},
                       {'isFailed': True, 'dispatchState': 'FAILED'}):
            _, response, _ = self.search(r, [], status)
            self.assertNotEqual(response['run']['verification']['state'], 'VERIFIED')

    def test_expired_unknown_malformed_and_metric_unsupported(self):
        r = self.record()
        monitor.update(r['run_id'], lambda x: x.update(classification='METRIC'))
        _, response, calls = self.search(r, [])
        self.assertEqual(calls, [])
        self.assertIn('unsupported', response['run']['verification']['message'])
        self.assertEqual(monitor.verification(str(uuid.uuid4()), 'admin')[0], 404)
        self.complete(r, monitor.TTL + 1)
        self.assertEqual(monitor.verification(r['run_id'], 'admin')[0], 404)
        handler._write_config(handler.STATUS_FILE, {'native_runs': [{'run_id': 'invalid'}]})
        self.assertEqual(monitor.history(), [])

    def test_streamer_log_and_metric_correlation_with_measured_counts(self):
        class EndBatch(BaseException):
            pass
        for index, st, raw in [('main', 'cisco:ios', '%LINK-3-UPDOWN preserved'),
                               ('cisco_mdt_metrics', 'cisco:ios:metric', 'metric template')]:
            r = monitor.begin('start', dict(hec=handler.DEFAULT_CONFIG['hec_url']))
            source = self.app / 'dummy.yml'
            source.write_text('samples:\n  - name: dummy\n    lines:\n      - index: ' + index +
                '\n        sourcetype: ' + st + '\n        _raw: ' + raw + '\n')
            reply = MagicMock(status=200)
            reply.__enter__.return_value = reply
            reply.read.return_value = b'{"code":0}'
            with patch('urllib.request.urlopen', return_value=reply) as send, \
                 patch.object(runner.time, 'sleep', side_effect=EndBatch):
                with self.assertRaises(EndBatch):
                    runner.run_python_streamer(str(source), handler.DEFAULT_CONFIG['hec_url'], 'dummy-token', 10, r['run_id'])
            events = [json.loads(e) for e in send.call_args.args[0].data.splitlines()]
            self.assertEqual(len(events), 5)
            for event in events:
                self.assertEqual(event['fields']['netspout_run_id'], r['run_id'])
                self.assertEqual(event['sourcetype'], st)
                self.assertEqual(event['event'], 'metric' if index == 'cisco_mdt_metrics' else raw)
            stored = next(x for x in monitor.history() if x['run_id'] == r['run_id'])
            self.assertEqual(stored['indexes'], [index])
            self.assertEqual(stored['counters'], dict(generated=5, attempted=5, accepted=5, failed=0, unknown=0))

    def test_process_lock_preserves_parallel_updates(self):
        r = self.record()
        root = str(Path('netspout/bin').resolve())
        program = ("import sys; sys.path.insert(0, " + repr(root) + "); "
            "import native_run_monitor as m; "
            "sys.path.insert(0, " + repr(str(Path('tests').resolve())) + "); "
            "from run_sec2b_offline import network_guard; sys.addaudithook(network_guard); "
            "[m.update(" + repr(r['run_id']) + ", lambda r: r['counters'].update(generated=(r['counters']['generated'] or 0)+1)) for _ in range(10)]")
        processes = [subprocess.Popen([sys.executable, '-c', program], stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(2)]
        for proc in processes:
            _, stderr = proc.communicate(timeout=15)
            self.assertEqual(proc.returncode, 0, stderr)
        self.assertEqual(monitor.history()[0]['counters']['generated'], 20)

    def test_permission_error_and_partial_results(self):
        r = self.complete(self.record())
        with patch.object(handler.rest, 'simpleRequest', return_value=(types.SimpleNamespace(status=403), '{}')):
            _, response = monitor.verification(r['run_id'], 'admin')
        self.assertEqual(response['run']['verification']['state'], 'ERROR')
        replies = [dict(sid='id'), dict(entry=[dict(content=dict(isDone=True, dispatchState='DONE'))]),
                   dict(results=[dict(netspout_run_id=r['run_id'], count='1')], preview=True)]
        with patch.object(handler.rest, 'simpleRequest', side_effect=[(types.SimpleNamespace(status=200), json.dumps(x)) for x in replies]):
            _, response = monitor.verification(r['run_id'], 'admin')
        self.assertEqual(response['run']['verification']['state'], 'INCONCLUSIVE')

    def test_ui_runtime_missing_zero_counts_and_verification(self):
        program = r"""
const fs=require('fs'), vm=require('vm'), assert=require('assert');
const source=fs.readFileSync(process.argv[1], 'utf8');
const start=source.indexOf('  // Native server-owned run history.');
const finish=source.indexOf('  mountNativeMonitorWhenReady();', start)+'  mountNativeMonitorWhenReady();'.length;
const ids={};
function element(tag){ return {tag, children:[],style:{},value:'',disabled:false,
  setAttribute(){},appendChild(el){this.children.push(el);if(tag==='select'&&!this.value)this.value=el.value;},
  insertBefore(el){this.children.push(el);ids[el.id]=el;}}; }
const parent=element('div'); ids['console-log-output']={parentNode:parent};
const run={run_id:'dummy-server-run',started_at:1,execution:{action:'onboard_sample'},execution_state:'COMPLETED',
  correlation:'SUPPORTED',classification:'LOG',indexes:['main'],
  counters:{generated:1,attempted:1,accepted:0,failed:null,unknown:1},verification:{state:'NOT_CHECKED',message:'Not checked'}};
let calls=[];
const context={document:{getElementById:id=>ids[id]||null,createElement:element},window:{addEventListener(){}},
  getRestUrl:()=>'/mock',getHeaders:()=>({}),setTimeout(){},
  fetch:async(url,options)=>{let payload=JSON.parse(options.body);calls.push(payload);
    return {ok:true,json:async()=>payload.action==='native_runs'?{status:'success',runs:[run]}:
      {status:'success',run:{...run,verification:{state:'VERIFIED',message:'Matching indexed log events found'}}}};}};
vm.runInNewContext(source.slice(start,finish),context);
(async()=>{await new Promise(setImmediate);
 const panel=ids['native-run-monitor']; assert(panel);
 const output=panel.children[4], verify=panel.children[3];
 assert(output.textContent.includes('accepted: 0')); assert(output.textContent.includes('failed: not measured'));
 assert(output.textContent.includes('NOT_CHECKED')); assert(!output.textContent.includes('VERIFIED'));
 verify.onclick(); await new Promise(setImmediate);
 assert(output.textContent.includes('VERIFIED')); assert(calls[1].run_id==='dummy-server-run');
})().catch(e=>{console.error(e);process.exitCode=1;});
"""
        for name in ('guided_onboarding.js', 'datablaster_console.js'):
            result = subprocess.run(['node', '-e', program, str(Path('netspout/appserver/static', name))],
                capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_ui_uses_text_and_explicit_missing_metrics(self):
        for name in ('guided_onboarding.js', 'datablaster_console.js'):
            source = Path('netspout/appserver/static', name).read_text()
            panel = source[source.index('function mountNativeRunMonitor'):source.index('var nativeMonitorMountAttempts')]
            self.assertNotIn('innerHTML', panel)
            self.assertIn('not measured', panel)
            self.assertIn('verify_native_run', panel)
            self.assertIn("run.classification !== 'LOG'", panel)


if __name__ == '__main__':
    from run_sec2b_offline import network_guard
    sys.addaudithook(network_guard)
    unittest.main(verbosity=2, failfast=True)
