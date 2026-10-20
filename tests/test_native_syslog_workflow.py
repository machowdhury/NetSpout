"""Offline native syslog settings, subprocess routing and existing adapter tests."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import types
import unittest
from unittest.mock import MagicMock, patch
import test_splunk_setup_workflow as fixtures

handler = fixtures.handler
import native_run_monitor as monitor
import run_simulation as runner
from netspout_core.telemetry_dispatcher import TelemetryDispatcher


class NativeSyslogTests(unittest.TestCase):
    setUp = fixtures.NativeSetupTests.setUp
    rest = fixtures.NativeSetupTests.rest

    def request(self, action='configure_syslog', **values):
        return handler.execute_request(dict(action=action, session_key='admin', **values))

    def scenario(self, metric=False):
        folder = self.app / 'scenarios'; folder.mkdir(exist_ok=True)
        path = folder / 'dummy.yml'
        path.write_text('samples:\n  - name: dummy\n    lines:\n      - index: ' + ('cisco_mdt_metrics' if metric else 'main') +
            '\n        sourcetype: ' + ('vendor:metric' if metric else 'cisco:ios') +
            '\n        host: router-01\n        _raw: dummy vendor raw\n')
        return path

    def test_admin_enforcement_and_new_defaults(self):
        code, response = handler.execute_request(dict(action='configure_syslog', session_key='viewer', syslog_port=1514))
        self.assertEqual(code, 403)
        self.assertFalse(self.path.exists())
        code, response = self.request('get_syslog_config')
        self.assertEqual(code, 200)
        self.assertEqual(response['config'], handler.SYSLOG_DEFAULTS)

    def test_settings_persist_atomically_and_preserve_hec_reference(self):
        self.credentials['hec_token'] = 'dummy-old-token'
        code, response = handler.execute_request(dict(action='configure_hec', session_key='admin', hec_token='dummy-new-token'))
        reference = response['config']['hec_credential_ref']
        credentials = dict(self.credentials)
        code, response = self.request(native_transport='syslog',syslog_host='collector.example.test',syslog_port=5514,
            syslog_protocol='tcp',syslog_format='rfc3164',syslog_facility=3,syslog_severity=4)
        self.assertEqual(code,200)
        disk=json.loads(self.path.read_text())
        self.assertEqual(disk['hec_credential_ref'],reference)
        self.assertEqual(self.credentials,credentials)
        self.assertNotIn('dummy-new-token',self.path.read_text())
        self.assertEqual(self.request('get_syslog_config')[1]['config'],response['config'])
        self.assertEqual(self.path.stat().st_mode & 0o777,0o600)
        previous=self.path.read_bytes()
        with patch.object(handler.os,'replace',side_effect=OSError('dummy-private')):
            self.assertEqual(self.request(syslog_port=5515)[0],503)
        self.assertEqual(self.path.read_bytes(),previous)

    def test_invalid_settings_are_rejected_without_mutation(self):
        self.request()
        before=self.path.read_bytes()
        bad=[dict(syslog_host='https://user:secret@host'),dict(syslog_host='::1'),dict(syslog_host='0.0.0.0'),
             dict(syslog_host='224.0.0.1'),dict(syslog_host='host\nsecret'),dict(syslog_port=0),dict(syslog_port=True),
             dict(syslog_port=65536),dict(syslog_port='514'),dict(syslog_protocol='tls'),dict(syslog_format='raw'),
             dict(syslog_facility=24),dict(syslog_severity=-1),dict(native_transport='otlp'),dict(hec_token='dummy-private')]
        for values in bad:
            with self.subTest(values=values):
                code,response=self.request(**values)
                self.assertEqual(code,400)
                self.assertEqual(self.path.read_bytes(),before)
                self.assertNotIn('dummy-private',json.dumps(response))

    def test_hec_and_legacy_updates_cannot_bypass_syslog_validation(self):
        self.credentials['hec_token']='dummy-token'
        self.request(native_transport='syslog',syslog_port=5514)
        self.assertEqual(handler.execute_request(dict(action='configure_hec',session_key='admin',syslog_port=0))[0],400)
        self.assertEqual(handler.execute_request(dict(action='save_config',session_key='admin',syslog_port=0))[0],200)
        self.assertEqual(json.loads(self.path.read_text())['syslog_port'],5514)

    def test_diagnostic_uses_saved_snapshot_does_not_persist_or_send_hec(self):
        self.request(syslog_host='saved.example.test',syslog_port=5514)
        before=self.path.read_bytes()
        diagnostic=dict(status='success',delivery_state='SENT',attempted=1,sent=1,failed=0,unknown=0,indexed=None)
        with patch.object(handler.subprocess,'run',return_value=types.SimpleNamespace(returncode=0,stdout=json.dumps(diagnostic))) as process, \
             patch.object(handler.HECCredentialStore,'read',side_effect=AssertionError('HEC access')):
            code,result=self.request('test_syslog')
        self.assertEqual(code,200)
        self.assertEqual(result['delivery_state'],'SENT')
        self.assertEqual(json.loads(process.call_args.kwargs['input'])['syslog']['syslog_host'],'saved.example.test')
        self.assertIn('--syslog-diagnostic',process.call_args.args[0])
        self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(self.request('test_syslog',syslog_host='override.example.test')[0],400)

    def test_diagnostic_error_and_timeout_are_not_success(self):
        failed=dict(status='error',delivery_state='UNKNOWN',attempted=1,sent=0,failed=0,unknown=1,indexed=None)
        with patch.object(handler.subprocess,'run',return_value=types.SimpleNamespace(returncode=0,stdout=json.dumps(failed))):
            self.assertEqual(self.request('test_syslog')[0],502)
        with patch.object(handler.subprocess,'run',side_effect=subprocess.TimeoutExpired('dummy',10)):
            code,result=self.request('test_syslog')
        self.assertEqual(code,503)
        self.assertNotEqual(result['status'],'success')

    def test_existing_adapter_udp_tcp_and_framing(self):
        for protocol in ('udp','tcp'):
            for format_ in ('rfc3164','rfc5424'):
                config=handler.validate_syslog_settings(dict(syslog_protocol=protocol,syslog_format=format_))
                socket=MagicMock()
                with patch('netspout_core.telemetry_dispatcher.socket.socket',return_value=socket):
                    result=runner.send_native_syslog(TelemetryDispatcher(),config,'%LINK-3-UPDOWN preserved','router-01')
                self.assertEqual(result['delivery_state'],'SENT')
                self.assertFalse(result['indexing_verified'])
                if protocol=='udp':
                    raw=socket.sendto.call_args.args[0]
                    self.assertEqual(socket.sendto.call_args.args[1],('127.0.0.1',1514))
                else:
                    socket.connect.assert_called_once_with(('127.0.0.1',1514))
                    raw=socket.sendall.call_args.args[0]
                    self.assertTrue(raw.endswith(b'\n'))
                self.assertIn(b'%LINK-3-UPDOWN preserved',raw)
                self.assertIn(b'router-01',raw)
                self.assertTrue(raw.startswith(b'<134>1 ') if format_=='rfc5424' else raw.startswith(b'<134>'))

    def test_adapter_failure_is_unknown_not_receiver_failure(self):
        with patch('netspout_core.telemetry_dispatcher.socket.socket',side_effect=OSError('dummy-private')):
            result=runner.native_syslog_diagnostic(handler.SYSLOG_DEFAULTS)
        self.assertEqual((result['sent'],result['unknown'],result['failed']),(0,1,0))
        self.assertIsNone(result['receiver_observed'])
        self.assertNotIn('dummy-private',json.dumps(result))

    def test_log_parser_shared_and_metric_scenarios_rejected(self):
        path=self.scenario()
        parsed=runner.load_python_scenario_events(str(path))
        self.assertEqual(runner.validate_syslog_scenario(str(path)),parsed)
        self.assertEqual(parsed[0]['raw'],'dummy vendor raw')
        path=self.scenario(metric=True)
        with self.assertRaises(ValueError): runner.validate_syslog_scenario(str(path))
        path.write_text('samples:\n  - lines:\n    - _raw: valid\n    - _raw: "invalid JSON\n')
        with self.assertRaises(ValueError): runner.validate_syslog_scenario(str(path))

    def test_scenario_routing_requires_no_hec_credential_and_cannot_use_request_destination(self):
        self.request(native_transport='syslog',syslog_host='saved.example.test')
        path=self.scenario()
        with patch.object(handler,'_syslog_runner_check',return_value={'status':'success'}) as preflight, \
             patch.object(handler.HECCredentialStore,'read',side_effect=AssertionError('HEC access')):
            clean=handler.validate_and_sanitize(dict(action='start',scenario=str(path),eps=10,session_key='admin',
                native_transport='hec',syslog_host='override.example.test'))
        self.assertEqual(clean['native_transport'],'syslog')
        self.assertIsNone(clean['token'])
        self.assertEqual(clean['syslog']['syslog_host'],'saved.example.test')
        self.assertEqual(Path(preflight.call_args.args[1]).resolve(), path.resolve())

    def test_startup_routes_private_config_to_python_and_preserves_history(self):
        self.request(native_transport='syslog')
        path=self.scenario()
        class Pipe(io.StringIO):
            def close(self): self.saved=self.getvalue()
        pipe=Pipe();proc=types.SimpleNamespace(pid=123,stdin=pipe)
        with patch.object(handler,'_syslog_runner_check',return_value={'status':'success'}), \
             patch.object(handler,'get_current_status',return_value={'running':False}), \
             patch.object(handler.subprocess,'Popen',return_value=proc) as spawn:
            code,result=self.request('start',scenario=str(path),eps=10)
        self.assertEqual(code,200)
        self.assertIn('--native-syslog',spawn.call_args.args[0])
        self.assertNotIn('--hec',spawn.call_args.args[0])
        private=json.loads(pipe.saved)
        self.assertIsNone(private['credential'])
        self.assertEqual(private['run_id'],result['native_run']['run_id'])
        record=result['native_run']
        self.assertEqual(record['destination']['transport'],'SYSLOG')
        self.assertEqual(record['correlation'],'UNSUPPORTED')
        with patch.object(handler,'is_process_running',return_value=True):
            _,verification=monitor.verification(record['run_id'],'admin')
        self.assertEqual(verification['run']['verification']['state'],'INCONCLUSIVE')
        self.assertIn('unsupported',verification['run']['verification']['message'])

    def test_streamer_measures_local_socket_evidence_without_indexing_claims(self):
        class End(BaseException): pass
        path=self.scenario()
        config=handler.validate_syslog_settings(dict(native_transport='syslog'))
        record=monitor.begin('start',dict(native_transport='syslog',syslog=config))
        with patch('netspout_core.telemetry_dispatcher.TelemetryDispatcher.emit_syslog',return_value=(True,'sent')) as send, \
             patch.object(runner.time,'sleep',side_effect=End):
            with self.assertRaises(End): runner.run_python_syslog_streamer(str(path),config,10,record['run_id'])
        self.assertEqual(send.call_args.kwargs['raw_message'],'dummy vendor raw')
        stored=next(r for r in monitor.history() if r['run_id']==record['run_id'])
        self.assertEqual(stored['syslog_delivery'],dict(attempted=1,sent=1,failed=0,unknown=0))
        self.assertIsNone(stored['counters']['accepted'])
        self.assertEqual(stored['correlation'],'UNSUPPORTED')

    def test_stdlib_only_runner_can_reuse_existing_adapter(self):
        code=r'''
import sys
sys.path.insert(0, 'netspout/bin');sys.path.insert(0,'tests')
from run_sec2b_offline import network_guard
sys.addaudithook(network_guard)
import socket
class Socket:
 def settimeout(self,value): pass
 def sendto(self,data,destination): return len(data)
 def close(self): pass
socket.socket=lambda *args,**kwargs: Socket()
import run_simulation as runner
from datablaster_rest import SYSLOG_DEFAULTS
result=runner.native_syslog_diagnostic(SYSLOG_DEFAULTS)
assert result['sent']==1 and result['indexed'] is None
assert 'pydantic' not in sys.modules
'''
        result=subprocess.run([sys.executable,'-B','-S','-c',code],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_native_syslog_ui_reports_confirmed_save_and_truthful_send(self):
        program=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('  function initNativeSyslog()');
const finish=source.indexOf('  var syslogMountAttempts',start);
async function run(saveStatus,sendStatus){
 let nodes={},calls=[];
 const element=id=>nodes[id]||(nodes[id]={value:'',textContent:'',disabled:true});
 const config={native_transport:'syslog',syslog_host:'saved.example.test',syslog_port:1514,
  syslog_protocol:'udp',syslog_format:'rfc5424',syslog_facility:16,syslog_severity:6};
 const ctx={document:{getElementById:element},getRestUrl:()=>'/mock',getHeaders:()=>({}),
 fetch:async(url,options)=>{let payload=JSON.parse(options.body);calls.push(payload);
 let status=payload.action==='configure_syslog'?saveStatus:payload.action==='test_syslog'?sendStatus:200;
 return {ok:status===200,status,json:async()=>payload.action==='test_syslog'?
  {status:status===200?'success':'error',delivery_state:status===200?'SENT':'UNKNOWN',message:'Indexing unverified',attempted:1,sent:status===200?1:0,failed:0,unknown:status===200?0:1}:
  {status:status===200?'success':'error',config}};}};
 vm.runInNewContext(source.slice(start,finish),ctx);ctx.initNativeSyslog();
 await new Promise(setImmediate);
 assert(!element('btn-save-syslog').disabled);
 element('cfg-syslog-host').value='unsaved.example.test';
 await element('btn-save-syslog').onclick();
 if(saveStatus===200) assert(element('syslog-status').textContent.includes('Destination saved'));
 else assert(!element('syslog-status').textContent.includes('Destination saved'));
 await element('btn-test-syslog').onclick();
 assert.deepStrictEqual(calls[calls.length-1],{action:'test_syslog'});
 assert(element('syslog-status').textContent.startsWith(sendStatus===200?'SENT':'UNKNOWN'));
 assert(!element('syslog-status').textContent.includes('VERIFIED'));
 assert(!element('btn-test-syslog').disabled);
}
(async()=>{await run(200,200);await run(400,502);})().catch(e=>{console.error(e);process.exitCode=1;});
"""
        result=subprocess.run(['node','-e',program,'netspout/appserver/static/configuration.js'],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_cli_preflight_rejects_metrics_without_network(self):
        path=self.scenario(metric=True)
        with patch.object(runner,'APP_DIR',str(self.app)), \
             patch.object(sys,'argv',['run_simulation.py','--syslog-preflight','--scenario',str(path)]), \
             patch.object(sys,'stdin',io.StringIO(json.dumps({'syslog':handler.SYSLOG_DEFAULTS}))), \
             patch.object(runner,'native_syslog_diagnostic',side_effect=AssertionError('Unexpected send')):
            with self.assertRaises(ValueError): runner._main()


if __name__=='__main__':
    from run_sec2b_offline import network_guard
    sys.addaudithook(network_guard)
    unittest.main(verbosity=2,failfast=True)
