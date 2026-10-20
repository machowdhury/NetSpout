"""Native SNMPv2c workflow with captured BER datagrams; no real sockets."""
import io
import json
from pathlib import Path
import socket
import subprocess
import sys
import types
import unittest
from unittest.mock import patch
import test_splunk_setup_workflow as fixtures

handler = fixtures.handler
import native_run_monitor as monitor
import run_simulation as runner
from netspout_core.snmp_ber import SnmpBerEncoder, SnmpBerDecoder
from netspout_core.models import SnmpResponse

SECRET='dummy-snmp-community'


class DatagramBoundary:
    def __init__(self, outcome='success'):
        self.outcome=outcome
        self.datagrams=[]
        self.receives=0

    def sendto(self,data,destination):
        if self.outcome=='send_error': raise OSError(SECRET)
        self.datagrams.append((bytes(data),destination))
        return len(data)-1 if self.outcome=='short' else len(data)

    def settimeout(self,value): pass
    def close(self): pass

    def recvfrom(self,size):
        self.receives+=1
        if self.outcome=='timeout' or self.receives>1: raise socket.timeout(SECRET)
        msg=SnmpBerDecoder.decode_message(self.datagrams[-1][0],expected_community=SECRET)
        response=SnmpResponse.from_inform(msg)
        if self.outcome=='wrong_id': response.request_id+=1
        if self.outcome=='error_status': response.error_status=5
        if self.outcome=='wrong_community': response.community='dummy-other'
        return SnmpBerEncoder.encode_message(response),self.datagrams[-1][1]


class NativeSNMPTests(unittest.TestCase):
    setUp=fixtures.NativeSetupTests.setUp
    rest=fixtures.NativeSetupTests.rest

    def request(self,action='configure_snmp',**values):
        return handler.execute_request(dict(action=action,session_key='admin',**values))

    def config(self,**values):
        return dict(handler.SNMP_DEFAULTS,community=SECRET,**values)

    def event(self):
        return dict(host='router-1',source='vendor',sourcetype='cisco:ios',index='main')

    def scenario(self,metric=False,raw='vendor original raw'):
        folder=self.app/'scenarios';folder.mkdir(exist_ok=True)
        path=folder/'dummy.yml'
        path.write_text('samples:\n  - name: dummy\n    lines:\n      - index: '+('cisco_mdt_metrics' if metric else 'main')+
            '\n        sourcetype: '+('cisco:ios:mdt' if metric else 'cisco:ios')+
            '\n        host: router-1\n        source: vendor\n        _raw: '+json.dumps(raw)+'\n')
        return path

    def test_admin_and_request_session_boundary(self):
        for action in ('configure_snmp','get_snmp_config','test_snmp'):
            self.assertEqual(handler.execute_request(dict(action=action,session_key='viewer'))[0],403)
        request=dict(session={'authtoken':'viewer'},payload=json.dumps(dict(action='configure_snmp',session_key='admin',snmp_community=SECRET)))
        self.assertEqual(handler.DataBlasterRestHandler().handle(json.dumps(request))['status'],403)
        self.assertFalse(self.credentials)

    def test_provision_replace_keep_and_secret_free_config(self):
        self.credentials['hec_token']='dummy-hec'
        code,result=self.request(native_transport='snmp',snmp_community=SECRET)
        self.assertEqual(code,200)
        first=result['config']['snmp_credential_ref']
        self.assertTrue(first.startswith('snmp_community_v_'))
        self.assertEqual(self.request(snmp_host='10.0.0.2',snmp_port=2162)[0],200)
        self.assertEqual(json.loads(self.path.read_text())['snmp_credential_ref'],first)
        code,result=self.request(snmp_community='dummy-new-community')
        self.assertEqual(code,200);self.assertNotEqual(result['config']['snmp_credential_ref'],first)
        self.assertEqual(self.credentials[first],SECRET)
        self.assertEqual(self.credentials['hec_token'],'dummy-hec')
        for action in ('get_config','get_snmp_config'):
            self.assertNotIn(SECRET,json.dumps(self.request(action)))
        self.assertNotIn(SECRET,self.path.read_text())
        self.assertNotIn('dummy-new-community',self.path.read_text())

    def test_invalid_settings_and_ambiguous_credentials_are_atomic(self):
        self.request(snmp_community=SECRET)
        before=self.path.read_bytes()
        cases=[dict(snmp_version='1'),dict(snmp_version='3'),dict(snmp_protocol='tcp'),dict(snmp_message_type='get'),
               dict(snmp_host='receiver.invalid'),dict(snmp_host='8.8.8.8'),dict(snmp_host='::1'),dict(snmp_host='0.0.0.0'),
               dict(snmp_port=162),dict(snmp_port=True),dict(snmp_host='224.0.0.1'),dict(snmp_port=65536),
               dict(snmp_credential_ref='hec_token'),dict(snmp_community=''),dict(snmp_community='bad\ncommunity'),
               dict(snmp_community='x'*256),dict(snmp_community=SECRET,snmp_credential_ref='snmp_community_v_'+'a'*32),
               dict(unknown=SECRET),dict(snmp_version='3',snmp_community='dummy-invalid-staged')]
        for values in cases:
            with self.subTest(fields=list(values)):
                code,result=self.request(**values)
                self.assertEqual(code,400)
                self.assertEqual(self.path.read_bytes(),before)
                self.assertNotIn(SECRET,json.dumps(result))
        self.assertNotIn('dummy-invalid-staged',self.credentials.values())

    def test_staging_and_publication_failures_preserve_active_reference(self):
        self.request(snmp_community=SECRET)
        before=self.path.read_bytes();active=json.loads(before)['snmp_credential_ref']
        self.fail_write=True
        self.assertEqual(self.request(snmp_community='dummy-failed-stage')[0],503)
        self.fail_write=False
        with patch.object(handler,'_write_config',side_effect=OSError('dummy-storage-private')):
            code,result=self.request(snmp_community='dummy-orphan')
        self.assertEqual(code,503);self.assertNotIn('dummy-storage-private',json.dumps(result))
        self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(handler._snmp_snapshot(handler.get_stored_config(),'admin')['community'],SECRET)
        self.assertEqual(json.loads(before)['snmp_credential_ref'],active)
        self.assertIn('dummy-orphan',self.credentials.values())

    def test_missing_and_cleared_credentials_never_use_lab_default(self):
        self.assertEqual(self.request(native_transport='snmp')[0],400)
        self.request(snmp_community=SECRET)
        before=self.path.read_bytes();ref=json.loads(before)['snmp_credential_ref']
        del self.credentials[ref]
        self.assertEqual(self.request('test_snmp')[0],503)
        self.assertEqual(self.path.read_bytes(),before)
        with self.assertRaises(ValueError): runner.native_snmp_transport(dict(handler.SNMP_DEFAULTS,community=''))
        with self.assertRaises(ValueError): handler._snmp_snapshot(dict(handler.SNMP_DEFAULTS),'admin')

    def test_explicit_reference_and_legacy_route_isolation(self):
        ref='snmp_community_v_'+'a'*32;self.credentials[ref]=SECRET
        self.assertEqual(self.request(snmp_credential_ref=ref,native_transport='snmp')[0],200)
        before=self.path.read_bytes()
        self.assertEqual(self.request('configure_syslog',native_transport='snmp')[0],400)
        self.assertEqual(self.request('configure_otlp',native_transport='snmp')[0],400)
        self.assertEqual(self.path.read_bytes(),before)
        self.request('save_config',snmp_host='10.10.10.10',snmp_credential_ref='bad')
        self.assertEqual(json.loads(self.path.read_text())['snmp_host'],'127.0.0.1')
        self.assertEqual(self.request('configure_syslog',syslog_port=1515)[0],200)
        self.assertEqual(json.loads(self.path.read_text())['native_transport'],'snmp')

    def test_real_ber_trap_wire_and_correlation(self):
        config=self.config();raw='<165>1 vendor original payload'
        message=runner.build_native_snmp(self.event(),raw,config,'server-run','scenario.yml','FAULT',17)
        boundary=DatagramBoundary()
        with patch('netspout_core.transport_native_snmp.socket.socket',return_value=boundary) as create:
            result=runner.send_native_snmp(runner.native_snmp_transport(config),message,config)
        create.assert_called_once_with(socket.AF_INET,socket.SOCK_DGRAM)
        self.assertEqual(len(boundary.datagrams),1)
        data,destination=boundary.datagrams[0]
        self.assertEqual(destination,('127.0.0.1',1162))
        self.assertEqual(data[0],0x30);self.assertIn(b'\x02\x01\x01',data)
        decoded=SnmpBerDecoder.decode_message(data,expected_community=SECRET)
        self.assertEqual(decoded.version,1);self.assertEqual(decoded.pdu_type,0xA7)
        self.assertEqual(decoded.request_id,17)
        self.assertEqual(decoded.varbinds[0].oid,'1.3.6.1.2.1.1.3.0')
        self.assertEqual(decoded.varbinds[0].asn1_type,'TimeTicks')
        self.assertEqual(decoded.varbinds[1].oid,'1.3.6.1.6.3.1.1.4.1.0')
        self.assertEqual(decoded.trap_oid,runner.NATIVE_SNMP_OID+'.0')
        self.assertEqual([v.value for v in decoded.varbinds[2:]],['server-run','scenario.yml','router-1','FAULT',raw,'cisco:ios','vendor'])
        self.assertEqual(SnmpBerEncoder.encode_message(decoded),data)
        self.assertEqual(result['sent'],1);self.assertIsNone(result['acknowledged'])
        self.assertIsNone(result['receiver_observed']);self.assertIsNone(result['indexed'])
        self.assertNotIn(SECRET,json.dumps(result))

    def test_inform_matching_response_and_no_retries(self):
        config=self.config(snmp_message_type='inform')
        transport=runner.native_snmp_transport(config)
        self.assertEqual(transport.inform_max_retries,0);self.assertEqual(transport.inform_timeout_ms,500)
        message=runner.build_native_snmp(self.event(),'raw',config,'run','scenario')
        boundary=DatagramBoundary()
        with patch('netspout_core.transport_native_snmp.socket.socket',return_value=boundary):
            result=runner.send_native_snmp(transport,message,config)
        self.assertEqual(len(boundary.datagrams),1)
        self.assertEqual(SnmpBerDecoder.decode_message(boundary.datagrams[0][0]).pdu_type,0xA6)
        self.assertEqual(result['acknowledged'],1);self.assertEqual(result['unknown'],0)
        self.assertIsNone(result['indexed'])

    def test_inform_timeout_wrong_id_community_and_error_are_unknown(self):
        config=self.config(snmp_message_type='inform')
        for outcome in ('timeout','wrong_id','wrong_community','error_status'):
            with self.subTest(outcome=outcome):
                boundary=DatagramBoundary(outcome)
                message=runner.build_native_snmp(self.event(),'raw',config,'run','scenario')
                with patch('netspout_core.transport_native_snmp.socket.socket',return_value=boundary):
                    result=runner.send_native_snmp(runner.native_snmp_transport(config),message,config)
                self.assertEqual(len(boundary.datagrams),1)
                self.assertEqual(result['sent'],1);self.assertEqual(result['acknowledged'],0)
                self.assertEqual(result['unknown'],1);self.assertNotIn(SECRET,json.dumps(result))

    def test_socket_send_failures_short_send_and_no_secret_errors(self):
        config=self.config();message=runner.build_native_snmp(self.event(),'raw',config,'run','scenario')
        for outcome in ('send_error','short'):
            with patch('netspout_core.transport_native_snmp.socket.socket',return_value=DatagramBoundary(outcome)):
                result=runner.send_native_snmp(runner.native_snmp_transport(config),message,config)
            self.assertEqual(result['unknown'],1);self.assertEqual(result['sent'],0)
            self.assertNotIn(SECRET,json.dumps(result))
        with patch('netspout_core.transport_native_snmp.socket.socket',side_effect=OSError(SECRET)):
            result=runner.send_native_snmp(runner.native_snmp_transport(config),message,config)
        self.assertEqual(result['failed'],1);self.assertEqual(result['unknown'],0)

    def test_metrics_and_oversized_scenarios_rejected_before_startup(self):
        config=self.config()
        path=self.scenario(True)
        with self.assertRaises(ValueError): runner.validate_snmp_scenario(str(path),config)
        path=self.scenario(raw='x'*2000)
        with self.assertRaises(ValueError): runner.validate_snmp_scenario(str(path),config)
        path=self.scenario()
        self.assertEqual(len(runner.validate_snmp_scenario(str(path),config)),1)

    def test_one_diagnostic_saved_credentials_and_no_persistence(self):
        self.request(snmp_community=SECRET)
        before=self.path.read_bytes();config=handler._snmp_snapshot(handler.get_stored_config(),'admin')
        boundary=DatagramBoundary()
        with patch('netspout_core.transport_native_snmp.socket.socket',return_value=boundary):
            result=runner.native_snmp_diagnostic(config)
        self.assertEqual(len(boundary.datagrams),1);self.assertEqual(result['sent'],1)
        with patch.object(handler,'_snmp_runner_check',return_value=result) as check:
            code,reply=self.request('test_snmp')
        self.assertEqual(code,200);self.assertEqual(check.call_args.args[0]['community'],SECRET)
        self.assertNotIn(SECRET,json.dumps(reply));self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(self.request('test_snmp',snmp_host='10.0.0.1')[0],400)
        with patch.object(handler,'_snmp_runner_check',side_effect=subprocess.TimeoutExpired('runner',10)):
            self.assertEqual(self.request('test_snmp')[0],503)

    def test_server_routing_private_stdin_history_and_no_search(self):
        self.request(snmp_community=SECRET,native_transport='snmp')
        path=self.scenario()
        class Pipe(io.StringIO):
            def close(self): self.saved=self.getvalue()
        pipe=Pipe();proc=types.SimpleNamespace(pid=123,stdin=pipe)
        with patch.object(handler,'_snmp_runner_check',return_value={'status':'success'}), \
             patch.object(handler,'get_current_status',return_value={'running':False}), \
             patch.object(handler.subprocess,'Popen',return_value=proc) as spawn, \
             patch.object(handler.HECCredentialStore,'read',side_effect=AssertionError('HEC access')):
            code,result=self.request('start',scenario=str(path),eps=10,snmp_host='10.2.2.2',snmp_community='browser',run_id='browser')
        self.assertEqual(code,200)
        self.assertIn('--native-snmp',spawn.call_args.args[0]);self.assertNotIn(SECRET,' '.join(spawn.call_args.args[0]))
        private=json.loads(pipe.saved);self.assertEqual(private['snmp']['community'],SECRET)
        record=result['native_run'];self.assertNotEqual(record['run_id'],'browser')
        self.assertEqual(record['destination']['transport'],'SNMP')
        self.assertEqual(record['destination']['host'],'127.0.0.1')
        self.assertTrue(all(v is None for v in record['snmp_delivery'].values()))
        self.assertNotIn(SECRET,Path(handler.STATUS_FILE).read_text())
        with patch.object(handler,'is_process_running',return_value=True),patch.object(handler.rest,'simpleRequest',side_effect=AssertionError('search forbidden')):
            _,reply=monitor.verification(record['run_id'],'admin')
        self.assertEqual(reply['run']['verification']['state'],'INCONCLUSIVE')

    def test_streamer_records_local_send_without_trap_acceptance(self):
        class End(BaseException): pass
        config=self.config();path=self.scenario()
        record=monitor.begin('start',dict(native_transport='snmp',snmp=config))
        boundary=DatagramBoundary()
        with patch('netspout_core.transport_native_snmp.socket.socket',return_value=boundary),patch.object(runner.time,'sleep',side_effect=End):
            with self.assertRaises(End): runner.run_python_snmp_streamer(str(path),config,10,record['run_id'])
        stored=next(r for r in monitor.history() if r['run_id']==record['run_id'])
        self.assertEqual(stored['snmp_delivery'],dict(attempted=1,sent=1,failed=0,unknown=0,acknowledged=None))
        self.assertIsNone(stored['counters']['accepted'])
        self.assertEqual(stored['counters']['generated'],1)
        self.assertIn(record['run_id'].encode(),boundary.datagrams[0][0])

    def test_bounded_runner_and_rate_validation(self):
        completed=types.SimpleNamespace(returncode=0,stdout='{"status":"success"}')
        with patch.object(handler.subprocess,'run',return_value=completed) as check:
            handler._snmp_runner_check(self.config())
        self.assertIn('--snmp-diagnostic',check.call_args.args[0]);self.assertEqual(check.call_args.kwargs['timeout'],10)
        self.assertNotIn(SECRET,' '.join(check.call_args.args[0]))
        self.assertEqual(json.loads(check.call_args.kwargs['input'])['snmp']['community'],SECRET)
        self.request(snmp_community=SECRET,native_transport='snmp',snmp_message_type='inform')
        path=self.scenario()
        with patch.object(handler,'_snmp_runner_check',side_effect=AssertionError('preflight not reached')):
            with self.assertRaises(ValueError): handler.validate_and_sanitize(dict(action='start',session_key='admin',scenario=str(path),eps=26))

    def test_cli_preflight_does_not_send(self):
        path=self.scenario()
        with patch.object(runner,'APP_DIR',str(self.app)),patch.object(sys,'argv',['runner','--snmp-preflight','--scenario',str(path)]), \
             patch.object(sys,'stdin',io.StringIO(json.dumps({'snmp':self.config()}))),patch.object(sys,'stdout',io.StringIO()) as output, \
             patch.object(runner,'send_native_snmp',side_effect=AssertionError('send forbidden')):
            runner._main()
        self.assertEqual(json.loads(output.getvalue())['status'],'success')

    def test_stdlib_only_wire_adapter(self):
        code=r'''
import sys
sys.path.insert(0,'netspout/bin');sys.path.insert(0,'tests')
from run_sec2b_offline import network_guard
sys.addaudithook(network_guard)
from unittest.mock import patch
import run_simulation as r
from datablaster_rest import SNMP_DEFAULTS
from netspout_core.snmp_ber import SnmpBerDecoder
class Socket:
 def sendto(self,data,target):
  assert SnmpBerDecoder.decode_message(data,expected_community='dummy-test').pdu_type==0xA7
  assert target==('127.0.0.1',1162)
  return len(data)
 def settimeout(self,timeout): pass
 def recvfrom(self,size):
  import socket
  raise socket.timeout
 def close(self): pass
config=dict(SNMP_DEFAULTS,community='dummy-test')
with patch('netspout_core.transport_native_snmp.socket.socket',return_value=Socket()):
 result=r.native_snmp_diagnostic(config)
assert result['sent']==1 and result['indexed'] is None
assert 'pydantic' not in sys.modules
'''
        result=subprocess.run([sys.executable,'-B','-S','-c',code],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_real_ui_save_failure_and_diagnostic_evidence(self):
        program=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const deny=()=>{throw Error('network forbidden');};require('net').Socket.prototype.connect=deny;require('dns').lookup=deny;
const source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('  function initNativeSnmp()');const finish=source.indexOf('  var snmpMountAttempts',start);
async function run(saveStatus,sendStatus){
 const nodes={},calls=[];const node=id=>nodes[id]||(nodes[id]={value:'',textContent:'',checked:false,disabled:true});
 const config={snmp_host:'127.0.0.1',snmp_port:1162,snmp_message_type:'trap'};
 const ctx={document:{getElementById:node},getRestUrl:()=>'/mock',getHeaders:()=>({}),fetch:async(url,options)=>{
  const payload=JSON.parse(options.body);calls.push(payload);
  const status=payload.action==='configure_snmp'?saveStatus:payload.action==='test_snmp'?sendStatus:200;
  return {ok:status===200,status,json:async()=>payload.action==='test_snmp'?
   {status:status===200?'success':'error',attempted:1,sent:status===200?1:0,acknowledged:null,failed:0,unknown:status===200?0:1,message:'Local evidence only'}:
   {status:status===200?'success':'error',config,native_transport:'snmp'}};
 }};
 vm.runInNewContext(source.slice(start,finish),ctx);ctx.initNativeSnmp();await new Promise(setImmediate);
 node('cfg-snmp-community').value='dummy-private-community';
 await node('btn-save-snmp').onclick();
 assert.equal(node('cfg-snmp-community').value,'');
 assert(node('snmp-status').textContent.includes(saveStatus===200?'SNMP settings saved':'Save not confirmed'));
 await node('btn-test-snmp').onclick();
 assert.deepStrictEqual(calls[calls.length-1],{action:'test_snmp'});
 assert(node('snmp-status').textContent.includes('acknowledged: not measured'));
 assert(node('snmp-status').textContent.includes('sent: '+(sendStatus===200?1:0)));
 assert(!node('snmp-status').textContent.includes('VERIFIED'));
 assert(!node('snmp-status').textContent.includes('dummy-private-community'));
}
(async()=>{await run(200,200);await run(400,502);})().catch(e=>{console.error(e);process.exitCode=1;});
"""
        result=subprocess.run(['node','-e',program,'netspout/appserver/static/configuration.js'],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_ui_labels_and_secret_input(self):
        xml=Path('netspout/default/data/ui/views/configuration.xml').read_text()
        self.assertIn('id="cfg-snmp-community" type="password"',xml)
        self.assertIn('SNMPv2c UDP traps or informs',xml)
        self.assertIn('not a vendor MIB',xml)
        for name in ('guided_onboarding.js','datablaster_console.js'):
            text=Path('netspout/appserver/static',name).read_text()
            self.assertIn('run.snmp_delivery',text)
            self.assertIn('Splunk indexing verification is unsupported',text)


if __name__=='__main__':
    from run_sec2b_offline import network_guard
    sys.addaudithook(network_guard)
    unittest.main(verbosity=2,failfast=True)
