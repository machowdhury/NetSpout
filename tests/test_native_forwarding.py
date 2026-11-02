"""Supported modular-input forwarding: offline spool and evidence contracts."""
import configparser
import io
import json
import re
from pathlib import Path
import subprocess
import sys
import types
import unittest
import uuid
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import test_splunk_setup_workflow as fixtures

handler=fixtures.handler
import pulseforge_forwarding as forwarding
import pulseforge_spool as spool
import native_run_monitor as monitor
import run_simulation as runner


def validate_input_spec(spec_text, config_text, scheme_text):
    """Structural check for this app's spec subset, including '*' documentation.

    This is not a replacement for Splunk's installed-app configuration checks.
    Ordinary inputs.conf remains INI; its companion spec contains declarations
    and placeholders, not runnable configuration values.
    """
    sections = {}
    current = None
    for line in spec_text.splitlines():
        text = line.strip()
        if not text or text.startswith(('*', '#', ';')):
            continue
        stanza = re.fullmatch(r'\[([^\[\]]+)\]', text)
        if stanza:
            current = stanza.group(1)
            if current in sections:
                raise ValueError('Duplicate spec stanza')
            sections[current] = {}
            continue
        setting = re.fullmatch(r'([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*(\S.*?)', text)
        if current is None or not setting:
            raise ValueError('Malformed spec declaration')
        key, value = setting.groups()
        if key in sections[current]:
            raise ValueError('Duplicate spec setting')
        sections[current][key] = value
    expected = {'spool_mode': 'native', '_TCP_ROUTING': '<existing-tcpout-group>'}
    if sections.get(forwarding.STANZA) != expected:
        raise ValueError('Missing or unsupported native input specification')
    config = configparser.ConfigParser(interpolation=None, strict=True)
    config.read_string(config_text)
    if not config.has_section(forwarding.STANZA):
        raise ValueError('Missing configured native input')
    native = config[forwarding.STANZA]
    if (set(native) != {'disabled', 'interval', 'spool_mode', 'python.version'}
            or native['spool_mode'] != expected['spool_mode']
            or native['disabled'] != '1' or native['interval'] != '5'
            or native['python.version'] != 'python3'):
        raise ValueError('Native input configuration/spec mismatch')
    scheme = ET.fromstring(scheme_text)
    if ({arg.get('name') for arg in scheme.findall('./endpoint/args/arg')} != {'spool_mode'}
            or scheme.findtext('streaming_mode') != 'xml'):
        raise ValueError('Native input scheme/spec mismatch')


class NativeForwardingTests(unittest.TestCase):
    setUp=fixtures.NativeSetupTests.setUp
    rest=fixtures.NativeSetupTests.rest

    def request(self,action='configure_forwarding',**values):
        return handler.execute_request(dict(action=action,session_key='admin',**values))

    def record(self,raw='vendor <text> & ]]> original'):
        return forwarding.event_record(dict(host='router-1',source='vendor-source',sourcetype='cisco:ios'),
            raw,str(uuid.uuid4()),'scenario.yml','idx_network_ops',1234.5)

    def scenario(self,metric=False):
        folder=self.app/'scenarios';folder.mkdir(exist_ok=True)
        path=folder/'dummy.yml'
        path.write_text('samples:\n  - name: dummy\n    lines:\n      - index: '+('metrics' if metric else 'main')+
            '\n        sourcetype: '+('vendor:metric' if metric else 'cisco:ios')+
            '\n        host: router-1\n        source: vendor-source\n        _raw: "original vendor event"\n')
        return path

    def configured_btool(self,command,**kwargs):
        if command[2]=='inputs':
            text='[pulseforge_spool://native]\ndisabled = 0\n_TCP_ROUTING = lab_group\nspool_mode = native\n'
        else:
            text='[tcpout:lab_group]\ndisabled = 0\nserver = receiver.invalid:9997\n'
        return types.SimpleNamespace(returncode=0,stdout=text)

    def test_admin_settings_and_no_outputs_modifications(self):
        for action in ('configure_forwarding','get_forwarding_config','test_forwarding'):
            self.assertEqual(handler.execute_request(dict(action=action,session_key='viewer'))[0],403)
        self.assertEqual(self.request(forwarding_group='lab_group',native_transport='forwarding')[0],200)
        _,reply=self.request('get_forwarding_config')
        self.assertEqual(reply['config'],dict(forwarding_group='lab_group',forwarding_index='idx_network_ops'))
        self.assertEqual(reply['native_transport'],'forwarding')
        self.assertFalse((self.app/'local/outputs.conf').exists())
        self.assertEqual(self.credentials,{})

    def test_configuration_validation_and_atomic_failure(self):
        self.request(forwarding_group='lab_group')
        before=self.path.read_bytes()
        for values in (dict(forwarding_group=''),dict(forwarding_group='../escape'),dict(forwarding_index='bad index'),
                       dict(forwarding_index='*'),dict(forwarding_host='unexpected'),dict(native_transport='s2s'),dict(forwarding_group=7)):
            self.assertEqual(self.request(**values)[0],400)
            self.assertEqual(self.path.read_bytes(),before)
        with patch.object(handler,'_write_config',side_effect=OSError('private-error')):
            code,reply=self.request(forwarding_group='other')
        self.assertEqual(code,503);self.assertNotIn('private-error',json.dumps(reply))
        self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(self.request('configure_syslog',native_transport='forwarding')[0],400)
        self.assertEqual(self.request('configure_otlp',native_transport='forwarding')[0],400)
        self.request('save_config',forwarding_group='override')
        self.assertEqual(json.loads(self.path.read_text())['forwarding_group'],'lab_group')

    def test_readiness_is_config_only_and_no_delivery_proof(self):
        self.request(forwarding_group='lab_group')
        with patch.object(forwarding.subprocess,'run',side_effect=self.configured_btool) as run:
            code,reply=self.request('test_forwarding')
        self.assertEqual(code,200);self.assertEqual(reply['state'],'READY')
        self.assertEqual(run.call_count,2)
        for call in run.call_args_list:
            self.assertEqual(call.args[0][1],'btool');self.assertEqual(call.kwargs['timeout'],10)
        for key in ('ingested','forwarded','indexed'): self.assertIsNone(reply[key])
        self.assertEqual(forwarding.pending_count(),0)
        self.assertEqual(self.request('test_forwarding',forwarding_group='override')[0],400)

    def test_readiness_disabled_mismatched_and_missing_output_fail(self):
        config=dict(forwarding_group='lab_group',forwarding_index='idx_network_ops')
        for text in ('[pulseforge_spool://native]\ndisabled=1\n_TCP_ROUTING=lab_group\n',
                     '[pulseforge_spool://native]\ndisabled=0\n_TCP_ROUTING=other\n'):
            def read(command,**kwargs):
                return types.SimpleNamespace(returncode=0,stdout=text if command[2]=='inputs' else '[tcpout:lab_group]\nserver=x:9997\n')
            with patch.object(forwarding.subprocess,'run',side_effect=read):
                self.assertEqual(forwarding.readiness(config)['state'],'NOT_READY')
        with patch.object(forwarding.subprocess,'run',side_effect=subprocess.TimeoutExpired('btool',10)):
            self.assertEqual(forwarding.readiness(config)['state'],'UNAVAILABLE')
        with patch.object(forwarding.subprocess,'run',return_value=types.SimpleNamespace(returncode=0,stdout='')):
            self.assertEqual(forwarding.readiness(config)['state'],'NOT_READY')

    def test_metadata_xml_and_original_text_roundtrip(self):
        record=self.record()
        event=ET.fromstring(forwarding.xml_event(record))
        self.assertEqual(event.get('stanza'),forwarding.STANZA)
        for key in ('host','source','sourcetype','index','time'):
            self.assertEqual(event.findtext(key),str(record[key]))
        data=json.loads(event.findtext('data'))
        self.assertEqual(data,record['data'])
        self.assertEqual(data['original_event'],'vendor <text> & ]]> original')
        self.assertEqual(data['netspout_device_id'],'router-1')
        self.assertEqual(data['netspout_phase'],'BASELINE')
        self.assertEqual(data['netspout_scenario_id'],'scenario.yml')

    def test_atomic_publication_and_failure_cleanup(self):
        record=self.record()
        name=forwarding.publish(record,now=100)
        path=forwarding.root()/name
        self.assertEqual(forwarding.read_private(path),record)
        self.assertEqual(path.stat().st_mode & 0o777,0o600)
        before=set(forwarding.root().iterdir())
        with patch.object(forwarding.os,'replace',side_effect=OSError('storage-failed')):
            with self.assertRaises(OSError): forwarding.publish(record,now=100)
        self.assertEqual(set(forwarding.root().iterdir()),before)

    def test_spool_caps_keep_unread_events_and_group_scope(self):
        self.request(forwarding_group='lab_group')
        with patch.object(forwarding,'MAX_PENDING',2):
            first=forwarding.publish(self.record(),now=100)
            forwarding.publish(self.record(),now=100)
            with self.assertRaises(ValueError): forwarding.publish(self.record(),now=1000000)
            self.assertTrue((forwarding.root()/first).exists())
        self.assertEqual(self.request(forwarding_group='other')[0],400)
        with patch.object(forwarding,'MAX_BYTES',1):
            with self.assertRaises(ValueError): forwarding.publish(self.record())
        with patch.object(forwarding,'MAX_EVENT_BYTES',10):
            with self.assertRaises(ValueError): forwarding.publish(self.record())

    def test_concurrent_publications_and_link_boundaries(self):
        with ThreadPoolExecutor(max_workers=4) as pool:
            names=list(pool.map(lambda _:forwarding.publish(self.record()),range(8)))
        self.assertEqual(len(set(names)),8)
        self.assertEqual(forwarding.pending_count(),8)
        target=self.app/'outside';target.write_text('unchanged')
        (forwarding.root()/'linked.json').symlink_to(target)
        with self.assertRaises(ValueError): forwarding.publish(self.record())
        with self.assertRaises(ValueError): forwarding.drain(io.StringIO())
        self.assertEqual(target.read_text(),'unchanged')

    def test_flush_failure_retains_pending_and_receipts_expire(self):
        name=forwarding.publish(self.record(),now=100)
        class Broken(io.StringIO):
            def flush(self): raise OSError('pipe-failure')
        with self.assertRaises(OSError): forwarding.drain(Broken(),now=100)
        self.assertTrue((forwarding.root()/name).exists())
        output=io.StringIO()
        self.assertEqual(forwarding.drain(output,now=100),1)
        self.assertEqual(len(ET.fromstring(output.getvalue()).findall('event')),1)
        self.assertEqual(forwarding.pending_count(),0)
        self.assertEqual(len(list(forwarding.root().glob('*.done'))),1)
        forwarding.drain(io.StringIO(),now=100+forwarding.RECEIPT_TTL+1)
        self.assertFalse(list(forwarding.root().glob('*.done')))

    def test_receipt_count_bound_and_no_payload_in_receipts(self):
        with patch.object(forwarding,'MAX_RECEIPTS',2):
            for _ in range(3): forwarding.publish(self.record(),now=100)
            forwarding.drain(io.StringIO(),now=100)
        receipts=list(forwarding.root().glob('*.done'))
        self.assertEqual(len(receipts),2)
        for path in receipts:
            self.assertEqual(set(forwarding.read_private(path)),{'handed_off_at','run_id'})
            self.assertNotIn('original_event',path.read_text())

    def test_supported_input_disabled_by_default_and_spool_handoff(self):
        config=configparser.ConfigParser(interpolation=None)
        config.read('netspout/default/inputs.conf')
        self.assertEqual(config[forwarding.STANZA]['disabled'],'1')
        self.assertNotIn('_tcp_routing',config[forwarding.STANZA])
        self.assertEqual(ET.fromstring(spool.SCHEME).findtext('streaming_mode'),'xml')
        self.request(forwarding_group='lab_group')
        forwarding.publish(self.record())
        xml='<input><configuration><stanza name="pulseforge_spool://native"/></configuration></input>'
        output=io.StringIO()
        with patch.object(forwarding.subprocess,'run',side_effect=self.configured_btool):
            spool.main([],io.StringIO(xml),output)
        self.assertEqual(len(ET.fromstring(output.getvalue()).findall('event')),1)
        self.assertEqual(forwarding.pending_count(),0)
        with self.assertRaises(ValueError): spool.main([],io.StringIO(xml.replace('native','other')),io.StringIO())

    def test_spec_structure_matches_configuration_and_modular_scheme(self):
        validate_input_spec(Path('netspout/README/inputs.conf.spec').read_text(),
                            Path('netspout/default/inputs.conf').read_text(), spool.SCHEME)

    def test_spec_check_rejects_missing_malformed_and_mismatched_declarations(self):
        spec = Path('netspout/README/inputs.conf.spec').read_text()
        config = Path('netspout/default/inputs.conf').read_text()
        for bad_spec in (spec.replace('[pulseforge_spool://native]', '[pulseforge_spool://other]'),
                         spec.replace('spool_mode = native', 'spool_mode native'),
                         spec.replace('spool_mode = native', 'spool_mode ='),
                         spec.replace('spool_mode = native', 'spool_mode = other'),
                         spec.replace('_TCP_ROUTING = <existing-tcpout-group>', ''),
                         spec + '\nunsupported_option = value\n',
                         spec + '\nspool_mode = native\n',
                         spec + '\n[pulseforge_spool://native]\n'):
            with self.subTest(kind='spec', suffix=bad_spec[-40:]):
                with self.assertRaises(ValueError): validate_input_spec(bad_spec, config, spool.SCHEME)
        for bad_config in (config.replace('[pulseforge_spool://native]', '[pulseforge_spool://other]'),
                           config.replace('spool_mode = native', 'spool_mode = other'),
                           config + '\n_TCP_ROUTING = unapproved_default\n'):
            with self.subTest(kind='config'):
                with self.assertRaises(ValueError): validate_input_spec(spec, bad_config, spool.SCHEME)
        with self.assertRaises(ValueError):
            validate_input_spec(spec, config, spool.SCHEME.replace('name="spool_mode"', 'name="unknown"'))

    def test_server_routing_and_history_remain_unverified(self):
        self.request(forwarding_group='lab_group',native_transport='forwarding')
        path=self.scenario()
        class Pipe(io.StringIO):
            def close(self): self.saved=self.getvalue()
        pipe=Pipe();proc=types.SimpleNamespace(pid=123,stdin=pipe)
        with patch.object(forwarding,'readiness',return_value={'state':'READY'}), \
             patch.object(handler.subprocess,'run',return_value=types.SimpleNamespace(returncode=0,stdout='{"status":"success"}')), \
             patch.object(handler,'get_current_status',return_value={'running':False}), \
             patch.object(handler.subprocess,'Popen',return_value=proc) as spawn, \
             patch.object(handler.HECCredentialStore,'read',side_effect=AssertionError('HEC access')):
            code,result=self.request('start',scenario=str(path),eps=10,forwarding_group='browser',run_id='browser')
        self.assertEqual(code,200);self.assertIn('--native-forwarding',spawn.call_args.args[0])
        private=json.loads(pipe.saved)
        self.assertEqual(private['forwarding']['forwarding_group'],'lab_group')
        self.assertNotEqual(private['run_id'],'browser')
        record=result['native_run'];self.assertEqual(record['destination']['transport'],'FORWARDING')
        self.assertEqual(record['indexes'],['idx_network_ops']);self.assertIsNone(record['counters']['accepted'])
        with patch.object(handler,'is_process_running',return_value=True),patch.object(handler.rest,'simpleRequest',side_effect=AssertionError('search forbidden')):
            _,reply=monitor.verification(record['run_id'],'admin')
        self.assertEqual(reply['run']['verification']['state'],'INCONCLUSIVE')

    def test_producer_counts_publication_not_ingestion_and_rejects_metrics(self):
        class End(BaseException): pass
        config=dict(forwarding_group='lab_group',forwarding_index='idx_network_ops')
        path=self.scenario()
        record=monitor.begin('start',dict(native_transport='forwarding',forwarding=config))
        with patch.object(runner.time,'sleep',side_effect=End):
            with self.assertRaises(End): runner.run_python_forwarding_streamer(str(path),config,10,record['run_id'])
        stored=next(r for r in monitor.history() if r['run_id']==record['run_id'])
        self.assertEqual(stored['forwarding_delivery'],dict(published=1,failed=0,unknown=0))
        self.assertIsNone(stored['counters']['accepted'])
        data=forwarding.read_private(next(forwarding.root().glob('*.json')))
        self.assertEqual(data['data']['netspout_run_id'],record['run_id'])
        self.assertEqual(data['data']['original_event'],'original vendor event')
        with self.assertRaises(ValueError): runner.validate_forwarding_scenario(str(self.scenario(True)),config)

    def test_failed_publication_is_unknown_and_stops_without_retry(self):
        config=dict(forwarding_group='lab_group',forwarding_index='idx_network_ops')
        record=monitor.begin('start',dict(native_transport='forwarding',forwarding=config))
        with patch.object(forwarding,'publish',side_effect=OSError('private-storage-error')) as publish:
            runner.run_python_forwarding_streamer(str(self.scenario()),config,10,record['run_id'])
        self.assertEqual(publish.call_count,1)
        stored=next(r for r in monitor.history() if r['run_id']==record['run_id'])
        self.assertEqual(stored['forwarding_delivery']['unknown'],1)
        self.assertEqual(stored['forwarding_delivery']['published'],0)
        self.assertIsNone(stored['counters']['accepted'])

    def test_persistent_loader_uses_one_stateless_utility(self):
        from test_native_loader_context import PRELUDE
        code=PRELUDE+'''
utility=handler._forwarding()
assert utility is handler._forwarding()
assert 'datablaster_rest' not in sys.modules
assert handler._native_monitor().api() is handler
'''
        result=subprocess.run([sys.executable,'-B','-c',code],capture_output=True,text=True,timeout=10,
                              env=dict(__import__('os').environ,PYTHONPATH='src:backend:tests'))
        self.assertEqual(result.returncode,0,result.stderr)

    def test_stdlib_only_input_scheme_and_spool(self):
        code=r"""
import sys,io,json,os,tempfile,xml.etree.ElementTree as ET,uuid
sys.path.insert(0,'netspout/bin');sys.path.insert(0,'tests')
from run_sec2b_offline import network_guard
sys.addaudithook(network_guard)
import pulseforge_forwarding as f,pulseforge_spool as s
with tempfile.TemporaryDirectory() as home:
 os.environ['SPLUNK_HOME']=home
 record=f.event_record(dict(host='r1',source='vendor',sourcetype='vendor:log'),'original',str(uuid.uuid4()),'scenario','idx_network_ops',100)
 f.publish(record)
 out=io.StringIO();assert f.drain(out)==1
 assert json.loads(ET.fromstring(out.getvalue()).findtext('event/data'))['original_event']=='original'
 scheme=io.StringIO();s.main(['--scheme'],io.StringIO(),scheme)
 assert ET.fromstring(scheme.getvalue()).findtext('streaming_mode')=='xml'
 assert 'pydantic' not in sys.modules
"""
        result=subprocess.run([sys.executable,'-B','-S','-c',code],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_real_ui_readiness_never_claims_forwarding(self):
        program=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const deny=()=>{throw Error('network forbidden');};require('net').Socket.prototype.connect=deny;require('dns').lookup=deny;
const source=fs.readFileSync(process.argv[1],'utf8');
const start=source.indexOf('  function initNativeForwarding()');const finish=source.indexOf('  var forwardingMountAttempts',start);
async function run(saveStatus,ready){
 const nodes={},calls=[];const node=id=>nodes[id]||(nodes[id]={value:'',textContent:'',checked:false,disabled:true});
 const config={forwarding_group:'lab_group',forwarding_index:'idx_network_ops'};
 const ctx={document:{getElementById:node},getRestUrl:()=>'/mock',getHeaders:()=>({}),fetch:async(url,options)=>{
  const payload=JSON.parse(options.body);calls.push(payload);
  const status=payload.action==='configure_forwarding'?saveStatus:payload.action==='test_forwarding'?(ready?200:503):200;
  return {ok:status===200,status,json:async()=>payload.action==='test_forwarding'?
    {status:ready?'success':'error',state:ready?'READY':'NOT_READY',message:'Configuration evidence only'}:
    {status:status===200?'success':'error',config,native_transport:'forwarding'}};
 }};
 vm.runInNewContext(source.slice(start,finish),ctx);ctx.initNativeForwarding();await new Promise(setImmediate);
 await node('btn-save-forwarding').onclick();
 assert(node('forwarding-status').textContent.includes(saveStatus===200?'Forwarding settings saved':'Save not confirmed'));
 await node('btn-test-forwarding').onclick();
 assert.deepStrictEqual(calls[calls.length-1],{action:'test_forwarding'});
 assert(node('forwarding-status').textContent.startsWith(ready?'READY:':'NOT_READY:'));
 assert(node('forwarding-status').textContent.includes('downstream forwarding: not measured'));
 assert(!node('forwarding-status').textContent.includes('VERIFIED'));
}
(async()=>{await run(200,true);await run(400,false);})().catch(e=>{console.error(e);process.exitCode=1;});
"""
        result=subprocess.run(['node','-e',program,'netspout/appserver/static/configuration.js'],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_ui_labels_are_truthful_and_keep_legacy_routes(self):
        xml=Path('netspout/default/data/ui/views/configuration.xml').read_text()
        self.assertIn('PulseForge Splunk-managed forwarding',xml)
        self.assertIn('READY means configuration readiness',xml)
        self.assertIn('original_event',xml)
        for name in ('guided_onboarding.js','datablaster_console.js'):
            text=Path('netspout/appserver/static',name).read_text()
            self.assertIn('run.forwarding_delivery',text)
            self.assertIn('Local publication is not delivery proof',text)
            self.assertIn('/services/datablaster/execute',text)


if __name__=='__main__':
    from run_sec2b_offline import network_guard
    sys.addaudithook(network_guard)
    unittest.main(verbosity=2,failfast=True)
