"""Offline telecom packs: generated simulation evidence, never real signaling."""
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import test_network_incidents as network_tests
import telecom_incidents as telecom

pack=network_tests.pack
runner=network_tests.runner
monitor=network_tests.monitor
fixtures=network_tests.fixtures
RUN=network_tests.RUN
ROOT=network_tests.ROOT
FOLDER=network_tests.FOLDER


class TelecomTests(unittest.TestCase):
    def test_registration_descriptors_and_ui(self):
        manifest=json.loads((FOLDER.parent/'scenarios_manifest.json').read_text())
        view=ET.parse(ROOT/'netspout/default/data/ui/views/datablaster_console.xml')
        buttons=view.findall('.//section[@id="telecom-incident-packs"]/button')
        self.assertEqual(len(telecom.CATALOG),10)
        self.assertEqual(len(buttons),10)
        for slug,row in telecom.CATALOG.items():
            with self.subTest(scenario=slug):
                filename='scenario_'+slug+'.yml'
                self.assertEqual(pack.descriptor(FOLDER/filename),dict(pulseforge_incident=slug,seed=42,version=1))
                self.assertEqual(sum(m['filename']==filename for m in manifest),1)
                self.assertEqual(sum(b.get('data-scenario')==filename for b in buttons),1)
                self.assertIn(row[0],(ROOT/'docs/TELECOM_INCIDENT_PACKS.md').read_text())

    def test_determinism_order_topology_service_impact_and_recovery(self):
        for slug,row in telecom.CATALOG.items():
            with self.subTest(scenario=slug):
                events=pack.generate(slug,42,1700000000,RUN,10)
                self.assertEqual(events,pack.generate(slug,42,1700000000,RUN,10))
                self.assertNotEqual(events,pack.generate(slug,43,1700000000,RUN,10))
                self.assertEqual(len(events),40)
                self.assertEqual(sum('metrics' in e for e in events),10)
                self.assertEqual([e['time'] for e in events],sorted(set(e['time'] for e in events)))
                self.assertAlmostEqual(events[-1]['time']-events[0]['time'],3.9,places=5)
                self.assertEqual([events[n*4]['fields']['netspout_phase'] for n in range(10)],list(pack.PHASES))
                for number,e in enumerate(events):
                    f=e['fields'];ip,role,interface=telecom.DEVICES[e['host']]
                    self.assertEqual((f['device_ip'],f['device_role'],f['interface']),(ip,role,interface))
                    self.assertEqual(f['sequence'],number)
                    self.assertEqual(f['netspout_run_id'],RUN)
                    self.assertEqual(f['netspout_scenario_id'],slug)
                    self.assertEqual(f['netspout_site_id'],telecom.SITE)
                    self.assertEqual(f['netspout_cell_id'],row[3])
                    self.assertEqual(f['netspout_service_id'],row[2])
                    self.assertEqual(f['netspout_subscriber_cohort'],telecom.COHORT)
                    self.assertEqual(f['netspout_incident_id'],events[0]['fields']['netspout_incident_id'])
                    self.assertEqual(f['simulation'],'true')
                    self.assertNotRegex(json.dumps(e).lower(),r'\b(imsi|msisdn|supi|suci)\b')
                    if 'metrics' not in e:
                        self.assertTrue(e['raw'].startswith('SIMULATED '))
                        self.assertIn('netspout_subscriber_cohort='+telecom.COHORT,e['raw'])
                        self.assertIn('interface='+interface,e['raw'])
                self.assertEqual(events[3]['metrics'],events[-1]['metrics'])
                self.assertNotEqual(events[3]['metrics'],events[15]['metrics'])
                self.assertEqual(events[0]['fields']['affected_synthetic_subscribers'],0)
                self.assertGreater(events[20]['fields']['affected_synthetic_subscribers'],0)
                self.assertEqual(events[36]['fields']['affected_synthetic_subscribers'],0)
                self.assertEqual(events[24]['fields']['evidence_kind'],'simulated_action')
                self.assertEqual(events[24]['fields']['remediation_executed'],'false')
                self.assertIn('Simulated operator action',events[24]['raw'])
                self.assertEqual(events[12]['fields']['evidence_kind'],'simulated_alarm')
                self.assertIn('Synthetic recovery verification',events[36]['raw'])
                for name,healthy,peak in row[-1]:
                    self.assertEqual(events[3]['metrics'][name],healthy)
                    self.assertEqual(events[15]['metrics'][name],peak)
        for a,b,relationship in telecom.RELATIONSHIPS:
            self.assertIn(a,telecom.DEVICES);self.assertIn(b,telecom.DEVICES);self.assertTrue(relationship)
        for path in telecom.SERVICE_PATHS.values():
            for node in path: self.assertIn(node,telecom.DEVICES)
        self.assertEqual(telecom.CELL_NODES['synthetic-lte-cell-A'],'enb01')
        self.assertEqual(pack.generate('telco_08_roaming_mobility')[0]['fields']['target_cell_id'],'synthetic-cell-B')
        cross=pack.generate('telco_10_cross_layer')
        self.assertEqual({e['host'] for e in cross[:3]},{'transport01','gnb01','upf01'})
        self.assertGreater(cross[-1]['fields']['consumed_sla_budget_seconds'],0)

    def test_signals_resource_attributes_and_snmp_wire_bounds(self):
        from netspout_core.snmp_ber import SnmpBerEncoder
        for slug in telecom.CATALOG:
            events=pack.generate(slug,run_id=RUN)
            for protocol in ('syslog','snmp','forwarding'):
                self.assertEqual(len(pack.select_events(events,protocol,{})),30)
                self.assertFalse(any('metrics' in e for e in pack.select_events(events,protocol,{})))
            self.assertEqual(len(pack.select_events(events,'otlp',{'otlp_signal':'metrics'})),10)
            for e in events:
                with self.subTest(scenario=slug,sequence=e['fields']['sequence']):
                    payload,metric,count=pack.otlp_payload(runner,e,RUN,slug)
                    resource=payload['resourceMetrics' if metric else 'resourceLogs'][0]
                    attrs={a['key']:a['value']['stringValue'] for a in resource['resource']['attributes']}
                    for key in ('netspout_cell_id','netspout_service_id','netspout_subscriber_cohort','evidence_kind','netspout_phase'):
                        self.assertEqual(attrs[key],e['fields'][key])
                    if metric:
                        self.assertEqual(count,3)
                        self.assertEqual({m['name']:m['gauge']['dataPoints'][0]['asDouble'] for m in resource['scopeMetrics'][0]['metrics']},e['metrics'])
                    else:
                        self.assertEqual(resource['scopeLogs'][0]['logRecords'][0]['body']['stringValue'],e['raw'])
                        for kind in ('trap','inform'):
                            config=dict(network_tests.settings('snmp'),snmp_message_type=kind)
                            message=runner.build_native_snmp(e,e['raw'],config,RUN,slug,e['fields']['netspout_phase'])
                            wire=SnmpBerEncoder.encode_message(message)
                            self.assertLessEqual(len(wire),1472)
                            self.assertEqual(wire[0],0x30)
                            self.assertIn(e['raw'].encode(),wire)
                            self.assertIn(RUN.encode(),wire)
        with self.assertRaises(ValueError):pack.select_events(events,'otlp',{'otlp_signal':'traces'})

    def test_all_ten_execute_through_existing_adapter_boundaries(self):
        import pulseforge_forwarding as forwarding
        from netspout_core.telemetry_dispatcher import TelemetryDispatcher,HecOutcome
        for slug in telecom.CATALOG:
            for protocol in ('hec','syslog','otlp','snmp','forwarding'):
                with self.subTest(scenario=slug,protocol=protocol):
                    cfg=network_tests.settings(protocol)
                    record=dict(counters={k:None for k in monitor.COUNTERS},indexes=[])
                    captured=[]
                    def hec(e,*a,**k):captured.append(copy.deepcopy(e));return HecOutcome(True,'accepted','ACCEPTED',200)
                    def syslog(d,c,raw,host):captured.append(raw);return dict(sent=1,failed=0,unknown=0)
                    def otlp(d,c,payload,metric,count):captured.append(payload);return dict(acknowledged=count,rejected=0,failed=0,unknown=0)
                    def snmp(t,message,c):captured.append(message);return dict(sent=1,acknowledged=None,failed=0,unknown=0)
                    with patch.object(monitor,'update',side_effect=lambda run,edit:edit(record)),patch.object(pack.time,'time',return_value=1700000000),patch.object(pack.time,'sleep'), \
                         patch.object(runner,'runtime_config',return_value=cfg),patch.object(TelemetryDispatcher,'emit_hec',side_effect=hec), \
                         patch.object(runner,'send_native_syslog',side_effect=syslog),patch.object(runner,'send_native_otlp',side_effect=otlp), \
                         patch.object(runner,'native_snmp_transport',return_value=object()),patch.object(runner,'send_native_snmp',side_effect=snmp), \
                         patch.object(forwarding,'publish',side_effect=lambda e:captured.append(copy.deepcopy(e))):
                        pack.execute(runner,network_tests.arguments(protocol),{protocol:cfg},dict(pulseforge_incident=slug,seed=42))
                    self.assertEqual(record['execution_state'],'COMPLETED')
                    self.assertEqual(len(captured),40 if protocol in ('hec','otlp') else 30)
                    self.assertEqual(record['counters']['unknown'],0)
                    self.assertNotIn('indexed',record['counters'])
                    self.assertNotIn('verification',record)
                    if protocol=='hec':
                        self.assertEqual(record['counters']['accepted'],40)
                        self.assertEqual(captured[-1]['fields']['netspout_subscriber_cohort'],telecom.COHORT)
                    elif protocol=='otlp':self.assertEqual(record['otlp_delivery']['acknowledged'],60)
                    else:
                        self.assertIsNone(record['counters']['accepted'])
                        self.assertEqual(record[protocol+'_delivery']['published' if protocol=='forwarding' else 'sent'],30)
                        if protocol=='forwarding':self.assertEqual(captured[-1]['data']['netspout_service_id'],telecom.CATALOG[slug][2])

    def test_batch3b_output_identical_to_checkpoint(self):
        source=subprocess.run(['git','show','1440113:netspout/bin/network_incidents.py'],capture_output=True,text=True,check=True,timeout=10).stdout
        baseline=types.ModuleType('baseline_network_incidents')
        exec(compile(source,'<checkpoint-network-incidents>','exec'),baseline.__dict__)
        self.assertEqual(len(baseline.CATALOG),15)
        self.assertTrue(set(baseline.CATALOG)<=set(pack.CATALOG))
        self.assertEqual(len(pack.CATALOG),21)
        for slug in baseline.CATALOG:
            self.assertEqual(pack.generate(slug,42,1700000000,RUN,10),baseline.generate(slug,42,1700000000,RUN,10))

    def test_dependency_free_generator(self):
        code="import sys;sys.path[:0]=['netspout/bin','tests'];from run_sec2b_offline import network_guard;sys.addaudithook(network_guard);import network_incidents as p;import telecom_incidents as t;assert len(t.CATALOG)==10;assert all(len(p.generate(s))==40 for s in t.CATALOG);assert 'pydantic' not in sys.modules"
        result=subprocess.run([sys.executable,'-B','-S','-c',code],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)


class TelecomNativeTests(unittest.TestCase):
    setUp=fixtures.NativeSetupTests.setUp
    rest=fixtures.NativeSetupTests.rest

    def test_named_destination_snapshots_history_and_fail_closed(self):
        api=fixtures.handler
        folder=self.app/'scenarios';folder.mkdir()
        code,result=api.execute_request(dict(action='create_destination',session_key='admin',name='Telecom lab',protocol='syslog',target_class='external_platform',settings={'syslog_host':'telecom.invalid'}))
        self.assertEqual(code,200,result);destination=result['destination']['id']
        for slug in telecom.CATALOG:
            path=folder/('scenario_'+slug+'.yml');path.write_text((FOLDER/path.name).read_text())
            class Pipe(io.StringIO):
                def close(self):self.saved=self.getvalue()
            pipe=Pipe()
            with patch.object(api,'_syslog_runner_check',return_value={'status':'success'}),patch.object(api,'get_current_status',return_value={'running':False}), \
                 patch.object(api.subprocess,'Popen',return_value=types.SimpleNamespace(pid=123,stdin=pipe)):
                code,result=api.execute_request(dict(action='start',session_key='admin',destination_id=destination,scenario=str(path),eps=10))
            self.assertEqual(code,200,result)
            private=json.loads(pipe.saved)
            self.assertEqual(private['syslog']['syslog_host'],'telecom.invalid')
            self.assertEqual(private['run_id'],result['native_run']['run_id'])
            self.assertEqual(result['native_run']['named_destination']['id'],destination)
        self.assertEqual(api.execute_request(dict(action='disable_destination',session_key='admin',destination_id=destination))[0],200)
        self.assertEqual(api.execute_request(dict(action='start',session_key='admin',destination_id=destination,scenario=str(path),eps=10))[0],400)
        self.assertEqual(api.execute_request(dict(action='start',session_key='admin',destination_id='missing',scenario=str(path),eps=10))[0],400)

    def test_all_telecom_descriptors_rebuild_and_preflight_without_sends(self):
        import yaml
        for slug in telecom.CATALOG:
            path=FOLDER/('scenario_'+slug+'.yml')
            with patch.object(runner,'runtime_config',return_value=fixtures.handler.DEFAULT_CONFIG):
                result=runner.prepare_scenario_config(str(path),10,fixtures.handler.DEFAULT_CONFIG['hec_url'],'dummy-telecom')
            document=yaml.safe_load(Path(result).read_text())
            self.assertEqual(len(document['samples']),30)
            self.assertNotIn('dummy-telecom',json.dumps(document['samples']))
            self.assertIn('netspout_scenario_id='+slug,document['samples'][0]['lines'][0]['_raw'])
            with patch.object(sys,'argv',['run_simulation.py','--scenario',str(path),'--syslog-preflight','--eps','10']), \
                 patch.object(sys,'stdin',io.StringIO(json.dumps({'syslog':network_tests.settings('syslog')}))),patch.object(sys,'stdout',io.StringIO()) as output, \
                 patch.object(runner,'resolve_binary',side_effect=AssertionError('external binary')),patch.object(runner,'send_native_syslog',side_effect=AssertionError('preflight send')):
                runner._main()
            self.assertEqual(json.loads(output.getvalue()),dict(status='success',templates=30))


if __name__=='__main__':
    from run_sec2b_offline import network_guard
    sys.addaudithook(network_guard)
    unittest.main(verbosity=2,failfast=True)
