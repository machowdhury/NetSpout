"""Offline named destinations over existing native transport boundaries."""
import io
import json
from pathlib import Path
import subprocess
import sys
import types
import unittest
import uuid
from unittest.mock import MagicMock,patch
import test_splunk_setup_workflow as fixtures

api=fixtures.handler
import native_run_monitor as monitor
import run_simulation as runner
SECRET='dummy-destination-secret'


class DestinationTests(unittest.TestCase):
    setUp=fixtures.NativeSetupTests.setUp
    rest=fixtures.NativeSetupTests.rest

    def request(self,action='list_destinations',**values):
        return api.execute_request(dict(action=action,session_key='admin',**values))

    def create(self,protocol='syslog',**values):
        params=dict(name='Receiver',protocol=protocol,target_class='external_platform',settings={})
        params.update(values)
        code,result=self.request('create_destination',**params)
        self.assertEqual(code,200,result)
        return result['destination']

    def scenario(self):
        folder=self.app/'scenarios';folder.mkdir(exist_ok=True)
        path=folder/'dummy.yml'
        path.write_text('samples:\n - name: dummy\n   lines:\n    - index: main\n      sourcetype: cisco:ios\n      host: router-1\n      _raw: "dummy raw"\n')
        return path

    def test_admin_and_server_session(self):
        for action in ('list_destinations','create_destination','update_destination','disable_destination','select_destination','diagnose_destination'):
            self.assertEqual(api.execute_request(dict(action=action,session_key='viewer'))[0],403)
        envelope=dict(session={'authtoken':'viewer'},payload=json.dumps(dict(action='create_destination',session_key='admin',credential=SECRET)))
        self.assertEqual(api.DataBlasterRestHandler().handle(json.dumps(envelope))['status'],403)
        self.assertFalse(self.credentials)

    def test_read_only_legacy_migration_has_stable_ids(self):
        self.credentials['hec_token']=SECRET
        first=self.request()[1];second=self.request()[1]
        self.assertEqual(first,second)
        self.assertFalse(self.path.exists())
        self.assertEqual(len(first['destinations']),5)
        self.assertEqual(first['selected_id'],api._destination_legacy_id('hec'))
        self.assertNotIn(SECRET,json.dumps(first))
        d=self.create()
        saved=json.loads(self.path.read_text())
        self.assertEqual(saved['destination_manager']['version'],1)
        self.assertIn(first['selected_id'],[r['id'] for r in saved['destination_manager']['destinations']])
        self.assertEqual(str(uuid.UUID(d['id'])),d['id'])

    def test_multiple_protocol_peers_and_classification_are_metadata(self):
        ids=[]
        for target in ('local_splunk','remote_splunk','external_platform'):
            d=self.create(target_class=target,settings={'syslog_host':'remote-receiver.invalid'})
            ids.append(d['id']);self.assertEqual(d['target_class'],target)
            self.assertEqual(d['settings']['syslog_host'],'remote-receiver.invalid')
        self.assertEqual(len(set(ids)),3)
        self.assertEqual(len(self.request()[1]['destinations']),8)

    def test_edit_disable_and_selected_disabled_fail_closed(self):
        d=self.create()
        self.assertEqual(self.request('select_destination',destination_id=d['id'])[0],200)
        code,result=self.request('update_destination',destination_id=d['id'],name='Edited',settings={'syslog_port':2514})
        self.assertEqual(code,200);self.assertEqual(result['destination']['id'],d['id'])
        config=api.get_stored_config('admin')
        self.assertEqual(config['syslog_port'],2514)
        self.assertEqual(self.request('disable_destination',destination_id=d['id'])[0],200)
        with self.assertRaises(ValueError): api._destination_resolve(api.get_stored_config())
        self.assertEqual(self.request('select_destination',destination_id=d['id'])[0],400)
        self.assertEqual(self.request('diagnose_destination',destination_id=d['id'])[0],400)
        self.assertEqual(self.request('update_destination',destination_id=d['id'],enabled=True)[0],200)
        self.assertEqual(api._destination_resolve(api.get_stored_config())[1]['id'],d['id'])

    def test_invalid_atomic_requests_never_echo_values(self):
        self.create();before=self.path.read_bytes()
        for values in (dict(name=''),dict(protocol='s2s'),dict(target_class='unknown'),dict(enabled='yes'),
                       dict(settings={'syslog_protocol':'tls'}),dict(settings={'unknown-secret-key':SECRET}),
                       dict(credential=SECRET),dict(destination_id=str(uuid.uuid4()))):
            params=dict(name='Test',protocol='syslog',target_class='remote_splunk',settings={});params.update(values)
            code,result=self.request('create_destination',**params)
            self.assertEqual(code,400,result);self.assertEqual(self.path.read_bytes(),before)
            self.assertNotIn(SECRET,json.dumps(result));self.assertNotIn('unknown-secret-key',json.dumps(result))

    def test_credentials_staged_replaced_kept_and_redacted(self):
        d=self.create('hec',credential=SECRET,target_class='local_splunk')
        first=d['settings']['hec_credential_ref']
        self.assertTrue(first.startswith('hec_token_v_'))
        code,result=self.request('update_destination',destination_id=d['id'],name='Same credential')
        self.assertEqual(code,200);self.assertEqual(result['destination']['settings']['hec_credential_ref'],first)
        code,result=self.request('update_destination',destination_id=d['id'],credential='dummy-replacement')
        self.assertEqual(code,200);self.assertNotEqual(result['destination']['settings']['hec_credential_ref'],first)
        self.assertEqual(self.credentials[first],SECRET)
        self.assertNotIn(SECRET,json.dumps(self.request()))
        self.assertNotIn(SECRET,self.path.read_text())
        self.assertNotIn('dummy-replacement',self.path.read_text())

    def test_initial_hec_never_implicitly_copies_legacy_token(self):
        self.credentials['hec_token']=SECRET
        code,result=self.request('create_destination',name='New',protocol='hec',target_class='local_splunk')
        self.assertEqual(code,400)
        self.assertFalse(self.path.exists())
        self.assertEqual(self.credentials,{'hec_token':SECRET})

    def test_validation_staging_and_publication_failure_keep_old_registry(self):
        d=self.create('hec',credential=SECRET)
        before=self.path.read_bytes()
        self.fail_write=True
        self.assertEqual(self.request('update_destination',destination_id=d['id'],credential='dummy-failed')[0],503)
        self.fail_write=False
        with patch.object(api,'_write_config',side_effect=OSError('private-exception')):
            code,result=self.request('update_destination',destination_id=d['id'],credential='dummy-orphan')
        self.assertEqual(code,503);self.assertNotIn('private-exception',json.dumps(result))
        self.assertEqual(self.path.read_bytes(),before)
        self.assertIn('dummy-orphan',self.credentials.values())
        self.assertEqual(self.request('update_destination',destination_id=d['id'],credential=SECRET,settings={'hec_credential_ref':''})[0],400)
        self.assertEqual(self.path.read_bytes(),before)

    def test_otlp_snmp_refs_and_capabilities(self):
        otlp=self.create('otlp',settings={'otlp_auth':'bearer','otlp_signal':'both'},credential=SECRET)
        snmp=self.create('snmp',credential='dummy-community')
        self.assertEqual(otlp['signals'],['logs','metrics'])
        self.assertTrue(otlp['settings']['otlp_credential_ref'].startswith('otlp_token_v_'))
        self.assertEqual(snmp['signals'],['events'])
        self.assertTrue(snmp['settings']['snmp_credential_ref'].startswith('snmp_community_v_'))
        before=self.path.read_bytes()
        self.assertEqual(self.request('update_destination',destination_id=snmp['id'],settings={'snmp_version':'3'})[0],400)
        self.assertEqual(self.path.read_bytes(),before)

    def test_legacy_mutations_preserve_registry_and_active_identity(self):
        d=self.create();self.request('select_destination',destination_id=d['id'])
        code,_=self.request('configure_syslog',syslog_host='legacy-update.invalid')
        self.assertEqual(code,200)
        config=api.get_stored_config()
        resolved,identity=api._destination_resolve(config)
        self.assertEqual(identity['id'],d['id']);self.assertEqual(resolved['syslog_host'],'legacy-update.invalid')
        self.assertEqual(self.request('configure_syslog',native_transport='hec')[0],200)
        self.assertEqual(api._destination_resolve(api.get_stored_config())[1]['id'],api._destination_legacy_id('hec'))

    def test_missing_destination_never_falls_back(self):
        d=self.create()
        with self.assertRaises(ValueError): api._destination_resolve(api.get_stored_config(),str(uuid.uuid4()))
        cfg=api.get_stored_config();cfg['destination_manager']['selected_id']=str(uuid.uuid4())
        with self.assertRaises(ValueError): api._destination_resolve(cfg)
        self.assertEqual(self.request('update_destination',destination_id=str(uuid.uuid4()),name='Missing')[0],400)

    def test_server_selected_per_run_snapshot_and_history(self):
        first=self.create(settings={'syslog_host':'first.invalid'})
        other=self.create(settings={'syslog_host':'other.invalid'})
        self.request('select_destination',destination_id=first['id'])
        class Pipe(io.StringIO):
            def close(self): self.saved=self.getvalue()
        pipe=Pipe();proc=types.SimpleNamespace(pid=123,stdin=pipe)
        with patch.object(api,'_syslog_runner_check',return_value={'status':'success'}),patch.object(api,'get_current_status',return_value={'running':False}),patch.object(api.subprocess,'Popen',return_value=proc):
            code,result=self.request('start',destination_id=other['id'],scenario=str(self.scenario()),eps=10,syslog_host='browser.invalid')
        self.assertEqual(code,200,result)
        private=json.loads(pipe.saved)
        self.assertEqual(private['syslog']['syslog_host'],'other.invalid')
        self.assertEqual(private['runtime_config']['syslog_host'],'other.invalid')
        self.assertEqual(result['native_run']['named_destination']['id'],other['id'])
        self.assertEqual(api._destination_resolve(api.get_stored_config())[1]['id'],first['id'])
        self.assertEqual(result['native_run']['destination']['host'],'other.invalid')

    def test_runtime_tls_and_allowlist_snapshot_not_live_settings(self):
        config=dict(api.DEFAULT_CONFIG,ssl_verify=False,hec_allowed_hosts=['receiver.invalid'],hec_allowed_ports=[443])
        with patch.object(runner,'_RUNTIME_CONFIG',config),patch.object(runner,'get_stored_config',side_effect=AssertionError('live read forbidden')):
            self.assertIs(runner.runtime_config(),config)
            request=api.hec_request('https://receiver.invalid/services/collector',configuration=runner.runtime_config(),headers={'Authorization':'Splunk '+SECRET})
        self.assertEqual(request.full_url,'https://receiver.invalid/services/collector')
        self.assertEqual(request.unredirected_hdrs['Authorization'],'Splunk '+SECRET)

    def test_explicit_bounded_diagnostics_do_not_select_or_persist(self):
        d=self.create();before=self.path.read_bytes()
        evidence={'status':'error','delivery_state':'UNKNOWN','attempted':1,'sent':0,'unknown':1,'message':'Outcome unknown'}
        with patch.object(api,'_syslog_runner_check',return_value=evidence) as send:
            code,result=self.request('diagnose_destination',destination_id=d['id'])
        self.assertEqual(code,200);self.assertEqual(send.call_count,1)
        self.assertEqual(result['result']['delivery_state'],'UNKNOWN')
        self.assertFalse(result['indexing_verified']);self.assertEqual(self.path.read_bytes(),before)
        f=self.create('forwarding',settings={'forwarding_group':'group'})
        with patch.object(api._forwarding(),'readiness',return_value={'status':'error','state':'NOT_READY'}) as check:
            code,result=self.request('diagnose_destination',destination_id=f['id'])
        self.assertEqual(check.call_count,1);self.assertEqual(result['result']['state'],'NOT_READY')

    def test_named_hec_diagnostic_requires_collector_acceptance(self):
        reply=MagicMock(status=200);reply.__enter__.return_value=reply
        for body,state in ((b'{"code":0}','ACCEPTED'),(b'{"unexpected":1}','UNKNOWN')):
            reply.read.return_value=body
            private=dict(credential=SECRET,runtime_config=dict(api.DEFAULT_CONFIG,hec_url='https://127.0.0.1:8088/services/collector'))
            with patch.object(runner,'_RUNTIME_CONFIG',None),patch.object(sys,'argv',['runner','--named-hec-diagnostic']),patch.object(sys,'stdin',io.StringIO(json.dumps(private))),patch.object(sys,'stdout',io.StringIO()) as output,patch('urllib.request.urlopen',return_value=reply) as send:
                runner._main()
            result=json.loads(output.getvalue());self.assertEqual(result['state'],state)
            self.assertEqual(send.call_count,1);self.assertIsNone(result['indexed'])
            self.assertNotIn(SECRET,json.dumps(result))

    def test_forwarding_group_switch_blocks_pending_spool(self):
        d=self.create('forwarding',settings={'forwarding_group':'new_group'})
        before=self.path.read_bytes()
        with patch.object(api._forwarding(),'pending_count',return_value=1):
            self.assertEqual(self.request('select_destination',destination_id=d['id'])[0],400)
        self.assertEqual(self.path.read_bytes(),before)

    def test_manager_ui_create_selection_and_secret_handling(self):
        code=r"""
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const deny=()=>{throw Error('network forbidden');};require('net').Socket.prototype.connect=deny;require('dns').lookup=deny;
const source=fs.readFileSync(process.argv[1],'utf8'),start=source.indexOf('  function initDestinationManager()'),end=source.indexOf('  var destinationMountAttempts',start);
const nodes={},calls=[];let records=[],selected='';
function element(tag){const n={tag,style:{},children:[],value:'',checked:false,disabled:false,textContent:'',appendChild(c){this.children.push(c);}};
 Object.defineProperty(n,'id',{get(){return this._id;},set(value){this._id=value;nodes[value]=this;}});return n;}
function node(id){if(!nodes[id]){let n=element('div');n.id=id;}return nodes[id];}
const ctx={document:{getElementById:node,createElement:element},getRestUrl:()=>'/mock',getHeaders:()=>({}),fetch:async(url,options)=>{
 const payload=JSON.parse(options.body);calls.push(payload);
 if(payload.action==='create_destination'){
  records.push({id:'server-id',name:payload.name,protocol:payload.protocol,target_class:payload.target_class,enabled:true,legacy:false,settings:payload.settings,signals:['logs']});
  return {ok:true,json:async()=>({status:'success',destination:records[0]})};
 }
 return {ok:true,json:async()=>({status:'success',destinations:records,selected_id:selected})};
}};
vm.runInNewContext(source.slice(start,end),ctx);ctx.initDestinationManager();
(async()=>{await new Promise(setImmediate);
 node('destination-protocol').value='syslog';node('destination-protocol').onchange();
 node('destination-name').value='<img onerror=bad> receiver';node('destination-class').value='remote_splunk';
 node('destination-setting-syslog_host').value='remote.invalid';
 await node('destination-save').onclick();
 const submitted=calls.find(c=>c.action==='create_destination');
 assert.equal(submitted.settings.syslog_host,'remote.invalid');assert.equal(submitted.target_class,'remote_splunk');
 assert(!Object.hasOwn(submitted,'destination_id'));assert.equal(node('destination-credential').value,'');
 assert(node('destination-manager-status').textContent.includes('Destination saved'));
 const row=node('destination-list').children.at(-1);assert(row.children[0].textContent.includes('<img onerror=bad> receiver'));
 assert(!source.slice(start,end).includes('innerHTML'));
})().catch(e=>{console.error(e);process.exitCode=1;});
"""
        result=subprocess.run(['node','-e',code,'netspout/appserver/static/configuration.js'],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_forwarding_reads_bounded_registry_sized_config(self):
        import pulseforge_forwarding as f
        config=dict(api.DEFAULT_CONFIG,forwarding_group='group')
        config['destination_manager']={'padding':'x'*70000}
        api._write_config(api.CONFIG_FILE,{k:v for k,v in config.items() if k!='destination_manager'})
        # A private config can exceed event-size limits once it has named profiles.
        api.write_private_file(api.CONFIG_FILE,json.dumps(config))
        self.assertEqual(f.active_settings()['forwarding_group'],'group')

    def test_native_ui_and_legacy_interfaces_remain(self):
        xml=Path('netspout/default/data/ui/views/configuration.xml').read_text()
        self.assertIn('Destination Manager',xml);self.assertIn('id="destination-credential" type="password"',xml)
        for name in ('guided_onboarding.js','datablaster_console.js'):
            text=Path('netspout/appserver/static',name).read_text()
            self.assertIn('native-destination-choice',text);self.assertIn('destination_id:',text)
            self.assertIn('run.named_destination',text);self.assertIn('/services/datablaster/execute',text)


if __name__=='__main__':
    from run_sec2b_offline import network_guard
    sys.addaudithook(network_guard)
    unittest.main(verbosity=2,failfast=True)
