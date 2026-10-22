"""All fifteen finite incidents through native routing; no network receivers."""
import copy
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
import uuid
from unittest.mock import MagicMock, patch
import test_splunk_setup_workflow as fixtures
import run_simulation as runner
import native_run_monitor as monitor
import network_incidents as pack
from netspout_core.telemetry_dispatcher import HecOutcome
from netspout_core.snmp_ber import SnmpBerEncoder

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'netspout/appserver/static/scenarios'
RUN='12345678-1234-4234-8234-123456789abc'


def arguments(protocol):
    args=dict(eps=10,hec=fixtures.handler.DEFAULT_CONFIG['hec_url'],token='dummy-incident',run_id=RUN)
    for p in ('syslog','otlp','snmp','forwarding'):
        args['native_'+p]=p==protocol
        args[p+'_preflight']=False
    return types.SimpleNamespace(**args)


def settings(protocol):
    api=fixtures.handler
    return {'hec':dict(api.DEFAULT_CONFIG),'syslog':dict(api.SYSLOG_DEFAULTS),
            'otlp':dict(api.OTLP_DEFAULTS,otlp_signal='both'),
            'snmp':dict(api.SNMP_DEFAULTS,community='dummy-community'),
            'forwarding':dict(api.FORWARDING_DEFAULTS,forwarding_group='existing_group')}[protocol]


class IncidentTests(unittest.TestCase):
    def test_registration_and_native_ui_all_fifteen(self):
        manifest=json.loads((FOLDER.parent/'scenarios_manifest.json').read_text())
        import xml.etree.ElementTree as ET
        root=ET.parse(ROOT/'netspout/default/data/ui/views/datablaster_console.xml')
        buttons=root.findall('.//section[@id="network-incident-packs"]/button')
        self.assertEqual(len(pack.CATALOG),15)
        self.assertEqual(len(buttons),15)
        for slug,row in pack.CATALOG.items():
            with self.subTest(scenario=slug):
                filename='scenario_network_'+slug+'.yml'
                self.assertEqual(pack.descriptor(FOLDER/filename),dict(pulseforge_incident=slug,seed=42,version=1))
                self.assertEqual(sum(m['filename']==filename for m in manifest),1)
                self.assertEqual(sum(b.get('data-scenario')==filename for b in buttons),1)
                self.assertIn(row[1],(ROOT/'docs/NETWORK_INCIDENT_PACKS.md').read_text())

    def test_deterministic_bounded_timeline_and_correlated_topology(self):
        for slug in pack.CATALOG:
            with self.subTest(scenario=slug):
                events=pack.generate(slug,42,1700000000,RUN,10)
                self.assertEqual(events,pack.generate(slug,42,1700000000,RUN,10))
                self.assertNotEqual(events,pack.generate(slug,43,1700000000,RUN,10))
                self.assertEqual(len(events),40)
                self.assertEqual(sum('metrics' in e for e in events),10)
                self.assertEqual([e['time'] for e in events],sorted(set(e['time'] for e in events)))
                self.assertEqual([e['fields']['sequence'] for e in events],list(range(40)))
                self.assertEqual([events[n*4]['fields']['netspout_phase'] for n in range(10)],list(pack.PHASES))
                for e in events:
                    fields=e['fields'];ip,role,interface=pack.DEVICES[e['host']]
                    self.assertEqual((fields['device_ip'],fields['device_role'],fields['interface']),(ip,role,interface))
                    self.assertEqual(fields['netspout_site_id'],pack.SITE)
                    self.assertEqual(fields['netspout_run_id'],RUN)
                    self.assertEqual(fields['netspout_scenario_id'],slug)
                    self.assertEqual(fields['netspout_incident_id'],events[0]['fields']['netspout_incident_id'])
                    self.assertLess(len(e['raw'].encode()),1200)
                self.assertEqual(events[3]['metrics'],events[-1]['metrics'])
                self.assertNotEqual(events[3]['metrics'],events[15]['metrics'])
                self.assertIn('Post-recovery',events[-4]['raw'])
                self.assertIn('Operator',events[24]['raw'])
                self.assertLess(events[12]['fields']['severity'],events[0]['fields']['severity'])
        for a,ai,b,bi in pack.LINKS:
            self.assertIn(a,pack.DEVICES);self.assertIn(b,pack.DEVICES)
            self.assertTrue(ai);self.assertTrue(bi)

    def test_signal_filtering_and_metric_resource_fidelity(self):
        for slug in pack.CATALOG:
            with self.subTest(scenario=slug):
                events=pack.generate(slug,run_id=RUN)
                for protocol in ('syslog','snmp','forwarding'):
                    selected=pack.select_events(events,protocol,{})
                    self.assertEqual(len(selected),30)
                    self.assertFalse(any('metrics' in e for e in selected))
                self.assertEqual(len(pack.select_events(events,'otlp',{'otlp_signal':'metrics'})),10)
                for event in events:
                    payload,metric,count=pack.otlp_payload(runner,event,RUN,slug)
                    resource=payload['resourceMetrics' if metric else 'resourceLogs'][0]
                    attributes={a['key']:a['value']['stringValue'] for a in resource['resource']['attributes']}
                    self.assertEqual(attributes['netspout_phase'],event['fields']['netspout_phase'])
                    self.assertEqual(attributes['netspout_incident_id'],event['fields']['netspout_incident_id'])
                    self.assertEqual(attributes['host.name'],event['host'])
                    if metric:
                        metrics=resource['scopeMetrics'][0]['metrics']
                        self.assertEqual({m['name']:m['gauge']['dataPoints'][0]['asDouble'] for m in metrics},event['metrics'])
                        self.assertEqual(count,len(event['metrics']))
                    else:
                        self.assertEqual(resource['scopeLogs'][0]['logRecords'][0]['body']['stringValue'],event['raw'])

    def test_snmp_all_incident_logs_encode_within_existing_limit(self):
        config=settings('snmp')
        for slug in pack.CATALOG:
            for event in pack.select_events(pack.generate(slug,run_id=RUN),'snmp',config):
                with self.subTest(scenario=slug,sequence=event['fields']['sequence']):
                    message=runner.build_native_snmp(event,event['raw'],config,RUN,slug,event['fields']['netspout_phase'])
                    wire=SnmpBerEncoder.encode_message(message)
                    self.assertEqual(wire[0],0x30)
                    self.assertLessEqual(len(wire),1472)
                    self.assertIn(event['raw'].encode(),wire)
                    self.assertIn(RUN.encode(),wire)

    def test_execute_all_fifteen_over_each_existing_adapter(self):
        import pulseforge_forwarding as forwarding
        from netspout_core.telemetry_dispatcher import TelemetryDispatcher
        for slug in pack.CATALOG:
            for protocol in ('hec','syslog','otlp','snmp','forwarding'):
                with self.subTest(scenario=slug,protocol=protocol):
                    config=settings(protocol)
                    record=dict(counters={k:None for k in monitor.COUNTERS},indexes=[],classification='UNKNOWN')
                    capture=[]
                    def update(run,edit): self.assertEqual(run,RUN);edit(record)
                    def hec(event,*args,**kwargs): capture.append(copy.deepcopy(event));return HecOutcome(True,'accepted','ACCEPTED',200)
                    def syslog(d,c,raw,host): capture.append((raw,host));return dict(sent=1,attempted=1,failed=0,unknown=0)
                    def otlp(d,c,payload,metric,count): capture.append(payload);return dict(acknowledged=count,rejected=0,failed=0,unknown=0)
                    def snmp(t,message,c): capture.append(message);return dict(sent=1,acknowledged=None,failed=0,unknown=0)
                    with patch.object(monitor,'update',side_effect=update),patch.object(pack.time,'time',return_value=1700000000),patch.object(pack.time,'sleep'), \
                         patch.object(runner,'runtime_config',return_value=config),patch.object(TelemetryDispatcher,'emit_hec',side_effect=hec), \
                         patch.object(runner,'send_native_syslog',side_effect=syslog),patch.object(runner,'send_native_otlp',side_effect=otlp), \
                         patch.object(runner,'native_snmp_transport',return_value=object()),patch.object(runner,'send_native_snmp',side_effect=snmp), \
                         patch.object(forwarding,'publish',side_effect=lambda r:capture.append(copy.deepcopy(r))):
                        pack.execute(runner,arguments(protocol),{protocol:config},dict(pulseforge_incident=slug,seed=42))
                    self.assertEqual(record['execution_state'],'COMPLETED')
                    self.assertEqual(len(capture),40 if protocol in ('hec','otlp') else 30)
                    self.assertEqual(record['counters']['unknown'],0)
                    self.assertNotIn('indexed',record['counters'])
                    if protocol=='hec':
                        self.assertEqual(record['counters']['accepted'],40)
                        self.assertEqual(capture[0]['fields']['netspout_run_id'],RUN)
                        self.assertEqual(capture[-1]['event'],'metric')
                        self.assertEqual(capture[-1]['fields']['netspout_phase'],'VERIFIED_HEALTHY')
                    elif protocol=='otlp':
                        self.assertEqual(record['otlp_delivery']['acknowledged'],
                                         80 if slug=='01_campus_link' else 70 if slug=='15_device_resources' else 60)
                    else:
                        self.assertIsNone(record['counters']['accepted'])
                        self.assertEqual(record[protocol+'_delivery']['published' if protocol=='forwarding' else 'sent'],30)
                        if protocol=='forwarding':
                            self.assertEqual(capture[-1]['data']['netspout_phase'],'VERIFIED_HEALTHY')
                            self.assertEqual(capture[-1]['data']['netspout_run_id'],RUN)

    def test_unknown_hec_response_is_not_acceptance_or_indexing(self):
        from netspout_core.telemetry_dispatcher import TelemetryDispatcher
        record=dict(counters={k:None for k in monitor.COUNTERS},indexes=[])
        with patch.object(monitor,'update',side_effect=lambda run,edit:edit(record)),patch.object(pack.time,'sleep'), \
             patch.object(runner,'runtime_config',return_value=settings('hec')), \
             patch.object(TelemetryDispatcher,'emit_hec',return_value=HecOutcome(False,'unknown','UNKNOWN',200)):
            pack.execute(runner,arguments('hec'),{},dict(pulseforge_incident='01_campus_link',seed=42))
        self.assertEqual(record['counters']['accepted'],0)
        self.assertEqual(record['counters']['unknown'],40)
        self.assertNotIn('verification',record)

    def test_partial_otlp_and_interrupted_send_keep_conservative_evidence(self):
        event=pack.generate('01_campus_link',run_id=RUN)[3]
        count=len(event['metrics'])
        record=dict(counters={k:None for k in monitor.COUNTERS},indexes=[])
        with patch.object(pack,'generate',return_value=[event]),patch.object(pack.time,'sleep'), \
             patch.object(monitor,'update',side_effect=lambda run,edit:edit(record)), \
             patch.object(runner,'send_native_otlp',return_value=dict(acknowledged=count-1,rejected=1,failed=0,unknown=0)):
            pack.execute(runner,arguments('otlp'),{'otlp':settings('otlp')},dict(pulseforge_incident='01_campus_link',seed=42))
        self.assertEqual(record['counters']['accepted'],count-1)
        self.assertEqual(record['counters']['failed'],1)
        self.assertEqual(record['counters']['unknown'],0)
        record=dict(counters={k:None for k in monitor.COUNTERS},indexes=[])
        with patch.object(pack.time,'sleep'),patch.object(monitor,'update',side_effect=lambda run,edit:edit(record)), \
             patch.object(runner,'send_native_syslog',side_effect=SystemExit(143)):
            with self.assertRaises(SystemExit):
                pack.execute(runner,arguments('syslog'),{'syslog':settings('syslog')},dict(pulseforge_incident='01_campus_link',seed=42))
        self.assertEqual(record['counters']['attempted'],1)
        self.assertEqual(record['counters']['unknown'],1)
        self.assertEqual(record['syslog_delivery']['unknown'],1)
        self.assertNotIn('execution_state',record)

    def test_cli_intercepts_pack_before_external_binary_and_preflight_sends_nothing(self):
        path=FOLDER/'scenario_network_01_campus_link.yml'
        with tempfile.TemporaryDirectory() as home, \
             patch.dict(os.environ, {'SPLUNK_HOME': home}), \
             patch.object(sys,'argv',['run_simulation.py','--scenario',str(path),'--syslog-preflight','--eps','10']), \
             patch.object(sys,'stdin',io.StringIO(json.dumps({'syslog':settings('syslog')}))), \
             patch.object(sys,'stdout',io.StringIO()) as output,patch.object(pack,'execute',wraps=pack.execute) as execute, \
             patch.object(runner,'resolve_binary',side_effect=AssertionError('external engine selected')), \
             patch.object(runner,'send_native_syslog',side_effect=AssertionError('preflight sent')):
            runner._main()
        self.assertEqual(json.loads(output.getvalue())['templates'],30)
        self.assertEqual(execute.call_count,1)

    def test_invalid_descriptors_and_incompatible_signals_fail_closed(self):
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'incident.yml'
            for data in (dict(pulseforge_incident='missing',seed=42,version=1),dict(pulseforge_incident='01_campus_link',seed=True,version=1)):
                path.write_text(json.dumps(data))
                with self.assertRaises(ValueError): pack.descriptor(path)
            path.write_text('samples:\n - name: legacy\n')
            self.assertIsNone(pack.descriptor(path))
        with self.assertRaises(ValueError): pack.select_events([], 'unimplemented', {})
        with self.assertRaises(ValueError): pack.select_events([], 'otlp', {'otlp_signal':'traces'})


class IncidentRebuildCompatibilityTests(unittest.TestCase):
    setUp=fixtures.NativeSetupTests.setUp
    rest=fixtures.NativeSetupTests.rest

    def rebuild(self,path):
        import yaml
        with patch.object(runner,'runtime_config',return_value=fixtures.handler.DEFAULT_CONFIG):
            result=Path(runner.prepare_scenario_config(str(path),10,
                fixtures.handler.DEFAULT_CONFIG['hec_url'],'dummy-rebuild-secret'))
        self.assertEqual(result.stat().st_mode & 0o777,0o600)
        self.assertEqual(result.parent.resolve(),Path(fixtures.handler.resolve_run_dir()).resolve())
        self.assertIn(str(result),runner._PRIVATE_FILES)
        return yaml.safe_load(result.read_text())

    def test_all_descriptors_materialize_deterministic_ordered_log_samples(self):
        for slug in pack.CATALOG:
            with self.subTest(scenario=slug):
                path=FOLDER/('scenario_network_'+slug+'.yml')
                original=path.read_bytes()
                actual=self.rebuild(path)
                self.assertEqual(actual,self.rebuild(path))
                expected=pack.select_events(pack.generate(slug,42,eps=10),'syslog',{})
                self.assertEqual(len(actual['samples']),30)
                self.assertEqual([s['name'] for s in actual['samples']],[slug+'_'+str(i) for i in range(30)])
                for sample,event in zip(actual['samples'],expected):
                    self.assertEqual(sample['count'],1)
                    self.assertFalse(sample['randomizeEvents'])
                    self.assertEqual(sample['lines'],[dict(index=event['index'],source=event['source'],
                        sourcetype=event['sourcetype'],host=event['host'],_time=event['time'],_raw=event['raw'])])
                self.assertNotIn('dummy-rebuild-secret',json.dumps(actual['samples']))
                self.assertEqual(path.read_bytes(),original)

    def test_legacy_order_samples_and_destination_sanitization_preserved(self):
        path=self.app/'legacy.yml'
        path.write_text('''general:
  output: {endpoints: ["https://untrusted.invalid"], splunkHECToken: untrusted-secret}
  earliest: "https://untrusted.invalid"
samples:
  - name: first
    syslogDestinationHost: untrusted.invalid
    lines:
      - {host: first, source: "app://sample", _raw: original-first, index: main, token: untrusted-secret}
  - name: second
    lines:
      - {host: second, _raw: original-second, index: main}
''')
        result=self.rebuild(path)
        self.assertEqual([s['name'] for s in result['samples']],['first','second'])
        self.assertEqual([s['lines'][0]['_raw'] for s in result['samples']],['original-first','original-second'])
        self.assertEqual(result['samples'][0]['lines'][0]['source'],'app://sample')
        self.assertNotIn('untrusted',json.dumps(result))
        self.assertEqual(result['general']['output']['endpoints'],[fixtures.handler.DEFAULT_CONFIG['hec_url']])
        self.assertEqual(result['general']['output']['splunkHECToken'],'dummy-rebuild-secret')

    def test_explicit_descriptor_gate_seed_and_rejection_before_file_creation(self):
        path=self.app/'descriptor.yml'
        path.write_text(json.dumps(dict(pulseforge_incident='01_campus_link',seed=43,version=1)))
        result=self.rebuild(path)
        expected=pack.select_events(pack.generate('01_campus_link',43,eps=10),'syslog',{})
        self.assertEqual([s['lines'][0]['_raw'] for s in result['samples']],[e['raw'] for e in expected])
        before=set(Path(fixtures.handler.resolve_run_dir()).iterdir())
        for invalid in (dict(pulseforge_incident='missing',seed=42,version=1),
                        dict(pulseforge_incident='01_campus_link',seed=42,version=1,samples=[])):
            path.write_text(json.dumps(invalid))
            with self.assertRaises(ValueError): self.rebuild(path)
            self.assertEqual(set(Path(fixtures.handler.resolve_run_dir()).iterdir()),before)
        path.write_text('pulseforge_incident: 01_campus_link\nseed: 42\nversion: 1\n')
        with self.assertRaises(ValueError): self.rebuild(path)


class IncidentNativeRoutingTests(unittest.TestCase):
    setUp=fixtures.NativeSetupTests.setUp
    rest=fixtures.NativeSetupTests.rest

    def test_each_scenario_named_snapshot_and_history_missing_disabled_fail_closed(self):
        api=fixtures.handler
        folder=self.app/'scenarios';folder.mkdir()
        code,value=api.execute_request(dict(action='create_destination',session_key='admin',name='Incident receiver',protocol='syslog',target_class='external_platform',settings={'syslog_host':'receiver.invalid'}))
        self.assertEqual(code,200,value)
        destination=value['destination']['id']
        for slug in pack.CATALOG:
            with self.subTest(scenario=slug):
                path=folder/('scenario_network_'+slug+'.yml');path.write_text((FOLDER/path.name).read_text())
                class Pipe(io.StringIO):
                    def close(self): self.saved=self.getvalue()
                pipe=Pipe();proc=types.SimpleNamespace(pid=123,stdin=pipe)
                with patch.object(api,'_syslog_runner_check',return_value={'status':'success'}),patch.object(api,'get_current_status',return_value={'running':False}),patch.object(api.subprocess,'Popen',return_value=proc):
                    code,value=api.execute_request(dict(action='start',session_key='admin',destination_id=destination,scenario=str(path),eps=10))
                self.assertEqual(code,200,value)
                self.assertEqual(json.loads(pipe.saved)['syslog']['syslog_host'],'receiver.invalid')
                self.assertEqual(value['native_run']['named_destination']['id'],destination)
                self.assertEqual(json.loads(pipe.saved)['run_id'],value['native_run']['run_id'])
                self.assertNotIn('credential',value['native_run'])
        self.assertEqual(api.execute_request(dict(action='start',session_key='admin',destination_id=str(uuid.uuid4()),scenario=str(path),eps=10))[0],400)
        self.assertEqual(api.execute_request(dict(action='disable_destination',session_key='admin',destination_id=destination))[0],200)
        self.assertEqual(api.execute_request(dict(action='start',session_key='admin',destination_id=destination,scenario=str(path),eps=10))[0],400)


if __name__=='__main__':
    from run_sec2b_offline import network_guard
    sys.addaudithook(network_guard)
    unittest.main(verbosity=2,failfast=True)
