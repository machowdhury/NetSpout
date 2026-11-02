"""Network-denied native OTLP destination and acknowledgement contracts."""
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import types
import unittest
import urllib.error
from unittest.mock import MagicMock, patch
import test_splunk_setup_workflow as fixtures

handler = fixtures.handler
import native_run_monitor as monitor
import run_simulation as runner
from netspout_core.telemetry_dispatcher import TelemetryDispatcher

SECRET = 'dummy-otlp-private'


def response(body=b'{}', status=200):
    result = MagicMock(status=status)
    result.__enter__.return_value = result
    result.read.return_value = body
    return result


class NativeOTLPTests(unittest.TestCase):
    setUp = fixtures.NativeSetupTests.setUp
    rest = fixtures.NativeSetupTests.rest

    def request(self, action='configure_otlp', **values):
        return handler.execute_request(dict(action=action, session_key='admin', **values))

    def scenario(self, metric=False):
        folder = self.app / 'scenarios'; folder.mkdir(exist_ok=True)
        path = folder / 'dummy.yml'
        path.write_text('samples:\n  - name: dummy\n    lines:\n      - index: ' + ('cisco_mdt_metrics' if metric else 'main') +
            '\n        sourcetype: ' + ('cisco:ios:mdt' if metric else 'cisco:ios') +
            '\n        host: router-1\n        source: vendor\n        _raw: "vendor original raw"\n')
        return path

    def config(self, **values):
        return dict(handler.OTLP_DEFAULTS, **values)

    def test_admin_and_request_envelope(self):
        for action in ('configure_otlp','get_otlp_config','test_otlp'):
            self.assertEqual(handler.execute_request(dict(action=action,session_key='viewer'))[0],403)
        request = {'session':{'authtoken':'viewer'},'payload':json.dumps(dict(action='configure_otlp',session_key='admin',otlp_token=SECRET))}
        self.assertEqual(handler.DataBlasterRestHandler().handle(json.dumps(request))['status'],403)
        self.assertFalse(self.credentials)

    def test_settings_defaults_persistence_and_legacy_boundaries(self):
        self.assertEqual(self.request(native_transport='otlp',otlp_endpoint='http://collector.invalid:4318')[0],200)
        code, result = self.request('get_otlp_config')
        self.assertEqual(code,200); self.assertEqual(result['native_transport'],'otlp')
        saved = json.loads(self.path.read_text())
        self.assertEqual(saved['otlp_endpoint'],'http://collector.invalid:4318')
        before = self.path.read_bytes()
        self.assertEqual(self.request('configure_syslog', native_transport='otlp')[0],400)
        self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(self.request('configure_syslog', syslog_port=1515)[0],200)
        self.assertEqual(json.loads(self.path.read_text())['native_transport'],'otlp')
        self.request('save_config',otlp_endpoint='http://override.invalid',otlp_credential_ref='invalid')
        self.assertEqual(json.loads(self.path.read_text())['otlp_endpoint'],saved['otlp_endpoint'])
        self.assertEqual(self.request('configure_hec',otlp_endpoint='http://override.invalid')[0],400)

    def test_invalid_settings_are_atomic(self):
        self.request()
        before = self.path.read_bytes()
        for values in (dict(otlp_endpoint='grpc://collector.invalid'),dict(otlp_endpoint='https://u:p@collector.invalid'),
                       dict(otlp_endpoint='https://collector.invalid/v1/logs'),dict(otlp_endpoint='https://collector.invalid?secret=x'),
                       dict(otlp_transport='grpc'),dict(otlp_signal='traces'),dict(otlp_auth='basic'),
                       dict(otlp_credential_ref='hec_token'),dict(otlp_endpoint='https://collector.invalid:0'),
                       dict(otlp_endpoint=None),dict(otlp_token='bad\r\nvalue',otlp_auth='bearer'),
                       dict(otlp_token=SECRET,otlp_auth='bearer',otlp_endpoint='http://collector.invalid'),
                       dict(otlp_token=SECRET,otlp_credential_ref='otlp_token_v_'+'a'*32),dict(unknown=SECRET)):
            with self.subTest(values=list(values)):
                code,result=self.request(**values)
                self.assertEqual(code,400); self.assertNotIn(SECRET,json.dumps(result))
                self.assertEqual(self.path.read_bytes(),before)
        self.assertFalse(self.credentials)

    def test_token_stage_replace_and_endpoint_only_keep(self):
        self.credentials['hec_token']='dummy-hec-existing'
        code,result=self.request(otlp_auth='bearer',otlp_token=SECRET)
        self.assertEqual(code,200)
        first=result['config']['otlp_credential_ref']
        self.assertTrue(first.startswith('otlp_token_v_'))
        self.assertEqual(handler.OTLPCredentialStore('admin').read(first),SECRET)
        self.assertEqual(self.request(otlp_endpoint='https://other.invalid:4318')[0],200)
        self.assertEqual(json.loads(self.path.read_text())['otlp_credential_ref'],first)
        _,result=self.request(otlp_token='dummy-replacement')
        self.assertNotEqual(result['config']['otlp_credential_ref'],first)
        self.assertEqual(self.credentials[first],SECRET)
        self.assertEqual(self.credentials['hec_token'],'dummy-hec-existing')
        for action in ('get_config','get_otlp_config'):
            self.assertNotIn(SECRET,json.dumps(self.request(action)))
        self.assertNotIn(SECRET,self.path.read_text())
        self.assertNotIn('dummy-replacement',self.path.read_text())

    def test_staging_publication_and_missing_reference_fail_closed(self):
        self.request(otlp_auth='bearer',otlp_token=SECRET)
        before=self.path.read_bytes()
        self.fail_write=True
        self.assertEqual(self.request(otlp_token='dummy-stage-failure')[0],503)
        self.assertEqual(self.path.read_bytes(),before)
        self.fail_write=False
        with patch.object(handler,'_write_config',side_effect=OSError('dummy-private-error')):
            code,result=self.request(otlp_token='dummy-orphan')
        self.assertEqual(code,503); self.assertNotIn('dummy-private-error',json.dumps(result))
        self.assertEqual(self.path.read_bytes(),before)
        active=json.loads(before)['otlp_credential_ref']
        self.assertEqual(handler._otlp_snapshot(handler.get_stored_config(),'admin')['headers']['Authorization'],'Bearer '+SECRET)
        del self.credentials[active]
        self.assertEqual(self.request('test_otlp')[0],503)
        self.assertEqual(self.path.read_bytes(),before)

    def test_reference_selection_is_explicit_and_app_owned(self):
        ref='otlp_token_v_'+'a'*32
        self.credentials[ref]=SECRET
        self.assertEqual(self.request(otlp_auth='bearer',otlp_credential_ref=ref)[0],200)
        self.assertEqual(self.request(otlp_credential_ref='otlp_token_v_'+'b'*32)[0],503)
        self.assertEqual(json.loads(self.path.read_text())['otlp_credential_ref'],ref)

    def test_logs_preserve_payload_resource_and_correlation(self):
        event=dict(host='router-1',source='vendor',sourcetype='cisco:ios',index='main')
        raw='<165>1 vendor raw body'
        payload,metric,count=runner.build_native_otlp(event,raw,'server-run','scenario.yml',now=1)
        self.assertFalse(metric);self.assertEqual(count,1)
        resource=payload['resourceLogs'][0]
        record=resource['scopeLogs'][0]['logRecords'][0]
        self.assertEqual(record['body']['stringValue'],raw)
        self.assertEqual(record['timeUnixNano'],'1000000000')
        attrs={a['key']:a['value']['stringValue'] for a in resource['resource']['attributes']}
        self.assertEqual(attrs['sourcetype'],'cisco:ios')
        self.assertEqual(attrs['netspout_run_id'],'server-run')
        self.assertEqual(attrs['netspout_scenario_id'],'scenario.yml')
        self.assertEqual(attrs['netspout_device_id'],'router-1')
        self.assertEqual(record['attributes'],resource['resource']['attributes'])

    def test_metric_gauges_have_correlation_dimensions(self):
        event=dict(host='router-1',source='vendor',sourcetype='cisco:ios:mdt',index='cisco_mdt_metrics')
        payload,metric,count=runner.build_native_otlp(event,'vendor metric template','server-run','scenario.yml',now=1)
        self.assertTrue(metric);self.assertEqual(count,5)
        resource=payload['resourceMetrics'][0]
        metrics=resource['scopeMetrics'][0]['metrics']
        self.assertEqual(len(metrics),5)
        for metric in metrics:
            point=metric['gauge']['dataPoints'][0]
            self.assertIsInstance(point['asDouble'],float)
            self.assertEqual(point['attributes'],resource['resource']['attributes'])
            self.assertIn({'key':'netspout_run_id','value':{'stringValue':'server-run'}},point['attributes'])

    def test_success_partial_rejection_and_wire_request(self):
        dispatcher=TelemetryDispatcher()
        for metric,field in ((False,'rejectedLogRecords'),(True,'rejectedDataPoints')):
            for rejected in (0,2,5):
                body=json.dumps({'partialSuccess':{field:str(rejected),'errorMessage':SECRET}}).encode()
                with patch('urllib.request.urlopen',return_value=response(body)) as send:
                    result=dispatcher.emit_otel_result({'test':'payload'},'https://collector.invalid:4318',metric,{'Authorization':'Bearer '+SECRET},5)
                self.assertEqual(result['acknowledged'],5-rejected)
                self.assertEqual(result['rejected'],rejected);self.assertEqual(result['unknown'],0)
                self.assertNotIn(SECRET,json.dumps(result))
                request=send.call_args.args[0]
                self.assertTrue(request.full_url.endswith('/v1/metrics' if metric else '/v1/logs'))
                self.assertEqual(json.loads(request.data),{'test':'payload'})
                self.assertEqual(request.get_header('Authorization'),'Bearer '+SECRET)
                self.assertTrue(send.call_args.kwargs['context'].check_hostname)
                self.assertEqual(send.call_args.kwargs['timeout'],3.0)
        with patch('urllib.request.urlopen',return_value=response()):
            self.assertEqual(dispatcher.emit_otel_result({},'http://collector.invalid',False)['acknowledged'],1)

    def test_ambiguous_responses_and_errors_never_acknowledge(self):
        dispatcher=TelemetryDispatcher()
        cases=[response(b'not JSON'),response(b'[]'),response(b'{}',202),response(b'x'*65537),
               response(b'{"partialSuccess":{"rejectedLogRecords":true}}'),
               response(b'{"partialSuccess":{"rejectedLogRecords":"9"}}')]
        for reply in cases:
            with patch('urllib.request.urlopen',return_value=reply):
                result=dispatcher.emit_otel_result({},'https://collector.invalid',False)
            self.assertEqual(result['acknowledged'],0);self.assertEqual(result['unknown'],1)
        for error in (TimeoutError(SECRET),OSError(SECRET),urllib.error.HTTPError('https://user:'+SECRET+'@collector.invalid',503,SECRET,{},io.BytesIO(SECRET.encode()))):
            with patch('urllib.request.urlopen',side_effect=error):
                result=dispatcher.emit_otel_result({},'https://collector.invalid',False)
            self.assertEqual(result['unknown'],1)
            self.assertNotIn(SECRET,json.dumps(result));self.assertNotIn(SECRET,json.dumps(dispatcher.stats))
        with patch('urllib.request.urlopen',side_effect=urllib.error.HTTPError('https://collector.invalid',403,SECRET,{},None)):
            result=dispatcher.emit_otel_result({},'https://collector.invalid',False)
        self.assertEqual(result['rejected'],1);self.assertEqual(result['http_status'],403)

    def test_diagnostic_uses_one_saved_request_without_mutation(self):
        self.request(otlp_auth='bearer',otlp_token=SECRET)
        before=self.path.read_bytes()
        cfg=handler._otlp_snapshot(handler.get_stored_config(),'admin')
        with patch('urllib.request.urlopen',return_value=response()) as send:
            result=runner.native_otlp_diagnostic(cfg)
        self.assertEqual(send.call_count,1);self.assertEqual(result['acknowledged'],1)
        self.assertIsNone(result['indexed']);self.assertFalse(result['indexing_verified'])
        with patch.object(handler,'_otlp_runner_check',return_value=result) as check:
            code,reply=self.request('test_otlp')
        self.assertEqual(code,200);self.assertEqual(check.call_args.args[0]['headers']['Authorization'],'Bearer '+SECRET)
        self.assertNotIn(SECRET,json.dumps(reply));self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(self.request('test_otlp',otlp_endpoint='http://override.invalid')[0],400)
        for error in (subprocess.TimeoutExpired('runner',10),RuntimeError(SECRET)):
            with patch.object(handler,'_otlp_runner_check',side_effect=error):
                code,reply=self.request('test_otlp')
            self.assertEqual(code,503);self.assertNotIn(SECRET,json.dumps(reply))

    def test_signal_preflight_and_cli_no_dispatch(self):
        logs=self.scenario()
        self.assertEqual(len(runner.validate_otlp_scenario(str(logs),self.config())),1)
        with self.assertRaises(ValueError): runner.validate_otlp_scenario(str(logs),self.config(otlp_signal='metrics'))
        metrics=self.scenario(True)
        with self.assertRaises(ValueError): runner.validate_otlp_scenario(str(metrics),self.config())
        self.assertEqual(len(runner.validate_otlp_scenario(str(metrics),self.config(otlp_signal='both'))),1)
        with patch.object(runner,'APP_DIR',str(self.app)),patch.object(sys,'argv',['runner','--otlp-preflight','--scenario',str(metrics)]), \
             patch.object(sys,'stdin',io.StringIO(json.dumps({'otlp':self.config(otlp_signal='metrics')}))), \
             patch.object(sys,'stdout',io.StringIO()) as output,patch.object(runner,'send_native_otlp',side_effect=AssertionError('send forbidden')):
            runner._main()
        self.assertEqual(json.loads(output.getvalue())['status'],'success')

    def test_server_saved_routing_private_subprocess_and_history(self):
        self.request(native_transport='otlp',otlp_auth='bearer',otlp_token=SECRET)
        path=self.scenario()
        class Pipe(io.StringIO):
            def close(self): self.saved=self.getvalue()
        pipe=Pipe();proc=types.SimpleNamespace(pid=123,stdin=pipe)
        with patch.object(handler,'_otlp_runner_check',return_value={'status':'success'}), \
             patch.object(handler,'get_current_status',return_value={'running':False}), \
             patch.object(handler.subprocess,'Popen',return_value=proc) as spawn, \
             patch.object(handler.HECCredentialStore,'read',side_effect=AssertionError('HEC access')):
            code,result=self.request('start',scenario=str(path),eps=10,otlp_endpoint='http://override.invalid',otlp_token='browser',run_id='browser')
        self.assertEqual(code,200)
        command=spawn.call_args.args[0]
        self.assertIn('--native-otlp',command);self.assertNotIn('--hec',command)
        self.assertNotIn(SECRET,' '.join(command))
        private=json.loads(pipe.saved)
        self.assertEqual(private['otlp']['headers']['Authorization'],'Bearer '+SECRET)
        self.assertNotEqual(private['run_id'],'browser')
        record=result['native_run']
        self.assertEqual(record['destination']['transport'],'OTLP')
        self.assertEqual(record['destination']['host'],'127.0.0.1')
        self.assertTrue(all(v is None for v in record['otlp_delivery'].values()))
        self.assertNotIn(SECRET,Path(handler.STATUS_FILE).read_text())
        with patch.object(handler,'is_process_running',return_value=True),patch.object(handler.rest,'simpleRequest',side_effect=AssertionError('search forbidden')):
            _,verified=monitor.verification(record['run_id'],'admin')
        self.assertEqual(verified['run']['verification']['state'],'INCONCLUSIVE')

    def test_streamer_counts_partial_points_and_preserves_correlation(self):
        class End(BaseException): pass
        path=self.scenario(True);config=self.config(otlp_signal='metrics')
        record=monitor.begin('start',dict(native_transport='otlp',otlp=config))
        reply=response(b'{"partialSuccess":{"rejectedDataPoints":"2"}}')
        with patch('urllib.request.urlopen',return_value=reply) as send,patch.object(runner.time,'sleep',side_effect=End):
            with self.assertRaises(End): runner.run_python_otlp_streamer(str(path),config,10,record['run_id'])
        self.assertEqual(send.call_count,1)
        stored=next(r for r in monitor.history() if r['run_id']==record['run_id'])
        self.assertEqual(stored['otlp_delivery'],dict(attempted=5,acknowledged=3,rejected=2,failed=0,unknown=0))
        self.assertEqual(stored['counters']['generated'],5)
        self.assertEqual(stored['counters']['accepted'],3)
        wire=json.loads(send.call_args.args[0].data)
        self.assertIn(record['run_id'],json.dumps(wire))

    def test_runner_boundary_is_bounded_and_uses_private_stdin(self):
        config=self.config()
        config['headers']={'Authorization':'Bearer '+SECRET}
        completed=types.SimpleNamespace(returncode=0,stdout='{"status":"success"}')
        with patch.object(handler.subprocess,'run',return_value=completed) as run:
            handler._otlp_runner_check(config)
        self.assertIn('--otlp-diagnostic',run.call_args.args[0])
        self.assertNotIn(SECRET,' '.join(run.call_args.args[0]))
        self.assertEqual(run.call_args.kwargs['timeout'],10)
        self.assertEqual(json.loads(run.call_args.kwargs['input'])['otlp'],config)

    def test_real_ui_save_and_diagnostic_states(self):
        program=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const deny=()=>{throw Error('network forbidden');};
require('net').Socket.prototype.connect=deny;require('dns').lookup=deny;
const source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('  function initNativeOtlp()');
const finish=source.indexOf('  var otlpMountAttempts',start);
async function run(saveStatus,sendStatus){
 let nodes={},calls=[];
 const element=id=>nodes[id]||(nodes[id]={value:'',textContent:'',checked:false,disabled:true});
 const config={otlp_endpoint:'https://collector.invalid:4318',otlp_signal:'logs',otlp_auth:'bearer'};
 const ctx={document:{getElementById:element},getRestUrl:()=>'/mock',getHeaders:()=>({}),
 fetch:async(url,options)=>{let payload=JSON.parse(options.body);calls.push(payload);
 let status=payload.action==='configure_otlp'?saveStatus:payload.action==='test_otlp'?sendStatus:200;
 return {ok:status===200,status,json:async()=>payload.action==='test_otlp'?
  {status:status===200?'success':'error',message:'Collector evidence only',counter_unit:'log_records',attempted:1,acknowledged:status===200?1:0,rejected:0,failed:0,unknown:status===200?0:1}:
  {status:status===200?'success':'error',config,native_transport:'otlp'}};}};
 vm.runInNewContext(source.slice(start,finish),ctx);ctx.initNativeOtlp();
 await new Promise(setImmediate);
 assert(!element('btn-save-otlp').disabled);
 element('cfg-otlp-token').value='dummy-private-token';
 await element('btn-save-otlp').onclick();
 assert.equal(element('cfg-otlp-token').value,'');
 if(saveStatus===200) assert(element('otlp-status').textContent.includes('OTLP settings saved'));
 else assert(element('otlp-status').textContent.includes('Save not confirmed'));
 await element('btn-test-otlp').onclick();
 assert.deepStrictEqual(calls[calls.length-1],{action:'test_otlp'});
 assert(element('otlp-status').textContent.includes('acknowledged: '+(sendStatus===200?1:0)));
 assert(element('otlp-status').textContent.includes('Splunk indexing: unsupported'));
 assert(!element('otlp-status').textContent.includes('VERIFIED'));
 assert(!element('otlp-status').textContent.includes('dummy-private-token'));
}
(async()=>{await run(200,200);await run(400,502);})().catch(e=>{console.error(e);process.exitCode=1;});
"""
        result=subprocess.run(['node','-e',program,'netspout/appserver/static/configuration.js'],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_syslog_ui_preserves_active_otlp_without_routing_through_syslog(self):
        program=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('  function initNativeSyslog()');
const finish=source.indexOf('  var syslogMountAttempts',start);
const nodes={},calls=[];
const element=id=>nodes[id]||(nodes[id]={value:'',textContent:'',disabled:true});
const config={native_transport:'otlp',syslog_host:'saved.invalid',syslog_port:1514,
 syslog_protocol:'udp',syslog_format:'rfc5424',syslog_facility:16,syslog_severity:6};
const context={document:{getElementById:element},getRestUrl:()=>'/mock',getHeaders:()=>({}),
 fetch:async(url,options)=>{const payload=JSON.parse(options.body);calls.push(payload);
 return {ok:true,status:200,json:async()=>({status:'success',config})};}};
vm.runInNewContext(source.slice(start,finish),context);context.initNativeSyslog();
(async()=>{
 await new Promise(setImmediate);
 assert.equal(element('cfg-native-transport').value,'');
 await element('btn-save-syslog').onclick();
 assert.equal(calls[calls.length-1].action,'configure_syslog');
 assert(!Object.hasOwn(calls[calls.length-1],'native_transport'));
 element('cfg-native-transport').value='syslog';
 await element('btn-save-syslog').onclick();
 assert.equal(calls[calls.length-1].native_transport,'syslog');
})().catch(e=>{console.error(e);process.exitCode=1;});
"""
        result=subprocess.run(['node','-e',program,'netspout/appserver/static/configuration.js'],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        import xml.etree.ElementTree as ET
        root=ET.parse('netspout/default/data/ui/views/configuration.xml').getroot()
        legacy=root.find('.//select[@id="cfg-native-transport"]')
        self.assertIsNotNone(legacy)
        self.assertEqual([option.get('value') for option in legacy.findall('option')],
                         ['', 'hec', 'syslog'])
        manager=root.find('.//select[@id="destination-protocol"]')
        self.assertIsNotNone(manager)
        self.assertIn('otlp', [option.get('value') for option in manager.findall('option')])

    def test_stdlib_only_native_otlp_diagnostic(self):
        code=r"""
import sys
sys.path.insert(0,'netspout/bin');sys.path.insert(0,'tests')
from run_sec2b_offline import network_guard
sys.addaudithook(network_guard)
from unittest.mock import MagicMock,patch
import run_simulation as runner
from datablaster_rest import OTLP_DEFAULTS
reply=MagicMock(status=200);reply.__enter__.return_value=reply;reply.read.return_value=b'{}'
with patch('urllib.request.urlopen',return_value=reply) as send:
 result=runner.native_otlp_diagnostic(OTLP_DEFAULTS)
assert result['acknowledged']==1 and result['indexed'] is None
assert send.call_count==1
assert 'pydantic' not in sys.modules
"""
        result=subprocess.run([sys.executable,'-B','-S','-c',code],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_ui_has_truthful_status_and_secret_field(self):
        xml=Path('netspout/default/data/ui/views/configuration.xml').read_text()
        self.assertIn('type="password"',xml);self.assertIn('OTLP destination',xml)
        for name in ('datablaster_console.js','guided_onboarding.js'):
            text=Path('netspout/appserver/static',name).read_text()
            self.assertIn('run.otlp_delivery',text)
            self.assertIn('OTLP search verification is unsupported',text)
        text=Path('netspout/appserver/static/configuration.js').read_text()
        self.assertIn("data.status !== 'success'",text)
        self.assertIn('Save not confirmed.',text)
        self.assertIn("element('token').value = ''",text)


if __name__ == '__main__':
    from run_sec2b_offline import network_guard
    sys.addaudithook(network_guard)
    unittest.main(verbosity=2,failfast=True)
