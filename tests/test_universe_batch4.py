"""Batch 4 native source contracts, queue conservation and live RAW equality boundaries."""
import hashlib
import ipaddress
import json
import re
import subprocess
import sys
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from netspout_core.models import Node,TelemetryTransportConfig
from netspout_core.universe_batch4_engine import UniverseBatch4Engine as E,batch_registry,BATCH4_SCENARIO_IDS
from netspout_core.authentic_scenario_packs import run_scenario_pack
from netspout_core.generator_modes import TelemetryGeneratorService
REG=batch_registry();CASES=[(s,f) for s in REG['sources'] for f in s['families']]
NOW=datetime(2026,10,27,12,0,0,123456,timezone.utc)
DEV=Node(id='ub4-test',name='host.example.test',ip_address='198.51.100.30')
ISO='2026-10-27T12:00:00.123Z'


def read(path):return json.loads((ROOT/path).read_text())


def fixture_original(family):
    ref=next(r for r in read('catalog/raw_reference/universe_batch4/references.json') if r['id']==family['origin'])
    data=(ROOT/ref['raw_reference_file']).read_bytes()
    assert hashlib.sha256(data).hexdigest()==ref['sha256'] and len(data)==ref['bytes']
    text=data.decode();selector=family['selector']
    if selector.startswith('line:'):original=text.splitlines()[int(selector.split(':')[1])-1]
    elif selector.startswith('array_element:'):original=json.dumps(json.loads(text)[int(selector.split(':')[1])])
    else:original=json.loads(text)['events'][int(re.search(r'\[(\d+)\]',selector)[1])]['message']
    return ref,original


@pytest.mark.parametrize('source,family',CASES,ids=[s['batch_source_id']+':'+f['id'] for s,f in CASES])
def test_exact_provenance_selectors_and_native_field_semantics(source,family):
    ref,original=fixture_original(family)
    assert (json.loads(original) if isinstance(family['template'],dict) else original)==family['template']
    entry=E.format_universe_batch4_log(DEV,source['splunk_sourcetype'],family['id'],when=NOW)
    assert entry.raw_log==E.format_universe_batch4_log(DEV,source['splunk_sourcetype'],family['id'],when=NOW).raw_log
    assert entry.timestamp=='2026-10-27 12:00:00.123'
    assert entry.sourcetype==source['splunk_sourcetype'] and entry.vendor==source['vendor']
    assert 'netspout_' not in entry.raw_log and 'ub4-test' not in entry.raw_log
    value=json.loads(entry.raw_log);template=family['template']
    assert value.keys()==template.keys()
    sid=source['batch_source_id']
    if sid=='slack':
        assert value['date_create']==int(NOW.timestamp())
        location=template['context'].get('location',{})
        if location.get('ip_address'):assert value['context']['location']['ip_address']=='192.0.2.10'
        if template['context'].get('ip_address'):assert value['context']['ip_address']=='192.0.2.10'
    elif sid=='github':
        assert value['@timestamp']==int(NOW.timestamp()*1000)
        assert value['actor_location']['ip']=='192.0.2.10'
    elif sid=='gitlab':
        assert value['time']==ISO and value['created_at']=='2026-10-27T12:00:00.123+00:00'
        assert value['meta.remote_ip']=='192.0.2.10'
    elif sid=='cybereason':
        created=int(value['simpleValues']['creationTime']['values'][0])
        assert created==int(NOW.timestamp()*1000)
        for key,stamp in template['suspicions'].items():
            assert value['suspicions'][key]-created==stamp-int(template['simpleValues']['creationTime']['values'][0])
        assert entry.src_ip=='0.0.0.0' and entry.dest_ip==DEV.ip_address
        assert '192.0.2.10' not in entry.raw_log
    elif sid=='qualys':
        assert value['Date']=='2026-10-27T12:00:00Z' and value['User IP']=='192.0.2.10'
    elif sid=='rapid7':
        assert value['last_scan_end']==ISO and value['ip']=='192.0.2.10'
        span=(datetime.fromisoformat(value['last_scan_end'].replace('Z','+00:00'))
              -datetime.fromisoformat(value['last_scan_start'].replace('Z','+00:00')))
        template_span=(datetime.fromisoformat(template['last_scan_end'].replace('Z','+00:00'))
                       -datetime.fromisoformat(template['last_scan_start'].replace('Z','+00:00')))
        assert span==template_span
    elif sid=='sentinelone':
        assert value['threatInfo']['createdAt']=='2026-10-27T12:00:00.123456Z'
        assert value['agentDetectionInfo']['agentIpV4']=='192.0.2.10'
        spacing=lambda t:(datetime.fromisoformat(t['threatInfo']['updatedAt'].replace('Z','+00:00'))
                          -datetime.fromisoformat(t['threatInfo']['createdAt'].replace('Z','+00:00')))
        assert spacing(value)==spacing(template)
    elif sid=='tanium':
        assert value['UpdatedAt']=='2026-10-27 12:00:00 +00:00'
        assert value['IpAddress']=='192.0.2.10' and value['NatIpAddress']=='192.0.2.10'
    elif sid=='trellix':
        lag=(datetime.fromisoformat(template['EPOEvents.ReceivedUTC'])-datetime.fromisoformat(template['EPOEvents.DetectedUTC']))
        assert value['EPOEvents.DetectedUTC']=='2026-10-27T12:00:00+00:00'
        assert value['EPOEvents.ReceivedUTC']==(NOW+lag).isoformat(timespec='seconds')
        if 'EPOEvents.EventTimeLocal' in template:assert value['EPOEvents.EventTimeLocal']=='2026-10-27T12:00:00+00:00'
        if isinstance(template['EPOEvents.AnalyzerIPV4'],int):
            assert value['EPOEvents.AnalyzerIPV4']==int(ipaddress.IPv4Address('192.0.2.10'))
        if isinstance(template.get('EPOEvents.TargetIPV4'),int):
            assert value['EPOEvents.TargetIPV4']==int(ipaddress.IPv4Address('198.51.100.20'))
    elif sid=='bitdefender':
        for key in ['timestamp','last_blocked']:
            if template.get(key):assert value[key]==ISO
        if template.get('computer_ip'):assert value['computer_ip']=='192.0.2.10'
    elif sid=='ibm_qradar':
        assert value['start_time']==int(NOW.timestamp()*1000)
        assert value['last_persisted_time']-value['start_time']==template['last_persisted_time']-template['start_time']
        native=str(template.get('offense_source'))
        try:
            native_ip = ipaddress.ip_address(native).version==4
        except ValueError:
            native_ip = False
        assert (value['offense_source']=='192.0.2.10') if native_ip else (value['offense_source']==template.get('offense_source'))
    elif sid=='elasticsearch':
        assert value['@timestamp']==ISO
        assert entry.src_ip=='0.0.0.0' and entry.dest_ip==DEV.ip_address
        assert value['elasticsearch.node.name']==template['elasticsearch.node.name']
    else:
        raise AssertionError('Untested Batch 4 source: '+sid)


@pytest.mark.parametrize('sid',BATCH4_SCENARIO_IDS)
def test_scenario_registration_phases_and_correlation_chain(sid):
    entries=run_scenario_pack(sid,'ub4-correlation')
    assert {e.sourcetype for e in entries}=={s['splunk_sourcetype'] for s in REG['sources'] if s['batch_source_id'] in REG['scenarios'][sid]}
    assert {e.netspout_phase for e in entries}=={'BASELINE','OBSERVE','VALIDATE'}
    ids=[e.netspout_event_id for e in entries]
    assert len(ids)==len(set(ids))
    assert [e.netspout_parent_event_id for e in entries]==[None]+ids[:-1]
    assert all(e.netspout_run_id=='ub4-correlation' and 'ub4-correlation' not in e.raw_log for e in entries)


def test_scenario_pack_event_bounds_match_live_contract():
    counts={sid:len(run_scenario_pack(sid,'ub4-bounds')) for sid in BATCH4_SCENARIO_IDS}
    assert counts=={'ub4_saas_collaboration_audit':7,'ub4_endpoint_threat_pipeline':10,'ub4_exposure_infra_logging':9}
    assert sum(counts.values())==sum(s['event_family_count'] for s in REG['sources'])==26<=60


@pytest.mark.parametrize('source',REG['sources'],ids=[s['batch_source_id'] for s in REG['sources']])
def test_user_facing_generation_and_actual_dispatcher_boundary(source):
    service=TelemetryGeneratorService()
    single=service.generate_single_event(source['vendor'],source['splunk_sourcetype'])
    assert single['status']=='GROUNDED' and single['provenance']['source']=='catalog/universe_batch4.json'
    with patch('netspout_core.generator_modes.dispatcher.dispatch_log',return_value={'hec':{'success':True}}) as dispatch:
        result=service.generate_sourcetype_batch(source['vendor'],source['splunk_sourcetype'],count=3,dispatch=True)
        assert result['count_generated']==result['count_dispatched']==dispatch.call_count==3
        assert all(call.args[0].sourcetype==source['splunk_sourcetype'] for call in dispatch.call_args_list)
    with pytest.raises(ValueError):service.generate_single_event('wrong_vendor',source['splunk_sourcetype'])
    with pytest.raises(ValueError):service.generate_sourcetype_batch(source['vendor'],source['splunk_sourcetype'],event_families=['invented'])


def test_native_validation_failures_and_template_immutability():
    before=json.dumps(REG,sort_keys=True)
    with pytest.raises(ValueError):E.format_universe_batch4_log(DEV,'unknown','family')
    with pytest.raises(ValueError):E.format_universe_batch4_log(DEV,'slack:audit','invented_family')
    with pytest.raises(ValueError):E.format_universe_batch4_log(DEV,'slack:audit','user_login',when=datetime(2026,1,1))
    assert json.dumps(REG,sort_keys=True)==before


def test_all_original_candidates_conserved_with_batch4_status():
    old=read('catalog/vendor_universe/batch2_candidate_queue_baseline.json')
    assert len(REG['candidate_queue'])==len(old['vendors'])==66
    assert {v['vendor_key'] for v in REG['candidate_queue']}=={v['vendor_key'] for v in old['vendors']}
    statuses=[v['batch4_status'] for v in REG['candidate_queue']]
    assert statuses.count('IMPLEMENTED_LIMITED_FAMILIES_BATCH4')==12
    assert statuses.count('IMPLEMENTED_LIMITED_FAMILIES_BATCH3')==9
    assert statuses.count('IMPLEMENTED_LIMITED_FAMILIES_BATCH2')==9
    assert statuses.count('BLOCKED_SELECTED_PRODUCT_REFERENCE')==3
    assert statuses.count('PENDING_REVIEW')==33
    assert len(REG['candidate_products'])==len(REG['product_candidate_statuses'])==583
    assert REG['candidate_products']==old['products']
    assert all(v['status'] in {'IMPLEMENTED_LIMITED_FAMILIES','BLOCKED_SELECTED_RAW_REFERENCE','PENDING_REVIEW'} for v in REG['product_candidate_statuses'])
    implemented={v['vendor_key'] for v in REG['candidate_queue'] if v['batch4_status']=='IMPLEMENTED_LIMITED_FAMILIES_BATCH4'}
    assert implemented=={s['vendor'] for s in REG['sources']}
    assert next(v for v in REG['candidate_queue'] if v['vendor_key']=='trellix_mcafee')['batch4_status']=='IMPLEMENTED_LIMITED_FAMILIES_BATCH4'
    assert next(v for v in REG['candidate_queue'] if v['vendor_key']=='corelight')['batch4_status']=='BLOCKED_SELECTED_PRODUCT_REFERENCE'


def test_batch1_and_batch3_statuses_remain_visible_in_batch4_registry():
    batch3=read('catalog/universe_batch3.json')
    by_key={v['vendor_key']:v for v in REG['candidate_queue']}
    for source in batch3['sources']:
        if source['vendor'] in by_key:
            assert by_key[source['vendor']]['batch3_status']=='IMPLEMENTED_LIMITED_FAMILIES_BATCH3'
    assert sum(1 for v in REG['candidate_queue'] if v['batch3_status']=='IMPLEMENTED_LIMITED_FAMILIES_BATCH3')==9


def test_ta_mapping_assessment_covers_every_canonical_source():
    matrix=read('catalog/universe_batch4_parser_assessments.json')
    assert len(matrix['sources'])==348 and matrix['new_verified_sourcetypes']==0
    assert {s['sourcetype'] for s in matrix['sources']}=={s['splunk_sourcetype'] for s in read('catalog/sourcetypes.json')}
    actual=[s for s in matrix['sources'] if s['status']=='ACTUAL_EXECUTION_PARTIAL_WITH_BLOCKER']
    assert len(actual)==1 and actual[0]['sourcetype']=='cisco:ise:syslog'
    assert actual[0]['evidence']=='catalog/universe_batch3_ise_parser_results.json'
    assert all(s['ta_metadata']['parser_verified'] is False for s in REG['sources'])
    assert sum(s['ta_metadata']['sourcetype_declared_in_snapshot'] for s in REG['sources'])==11
    qradar=next(s for s in REG['sources'] if s['batch_source_id']=='ibm_qradar')
    assert qradar['ta_metadata']['authority']=='PULSEFORGE_DEFINED_PENDING_TA_MAPPING'
    assert {s['ta_metadata']['authority'] for s in REG['sources']}=={'SPLUNKBASE_METADATA','PULSEFORGE_DEFINED_PENDING_TA_MAPPING'}


def test_snapshot_app_identity_separate_from_publisher():
    apps={a['uid']:a for a in read('catalog/vendor_universe/splunkbase_apps_snapshot.json')['rows']}
    for source in REG['sources']:
        app=apps[source['ta_metadata']['uid']]
        assert source['ta_metadata']['name']==app['name'] and source['ta_metadata']['publisher']==app['author']
        declared={t for ts in app['rel_tags_st'].values() for t in ts}
        assert (source['splunk_sourcetype'] in declared)==source['ta_metadata']['sourcetype_declared_in_snapshot']
    vendors={v['id'] for v in read('catalog/vendors.json')}
    assert {s['vendor'] for s in REG['sources']}<=vendors


@pytest.mark.parametrize('target,package',[('src','netspout_core'),('backend','app'),('netspout/bin','netspout_core')])
def test_runtime_mirror_imports_and_native_templates(target,package):
    code=f'''import sys;sys.path.insert(0,{str(ROOT/target)!r})
from {package}.universe_batch4_engine import batch_registry,UniverseBatch4Engine
from {package}.models import Node
from {package}.log_engine import SplunkLogEngine
assert len(SplunkLogEngine.UNIVERSE_BATCH4_SOURCE_SOURCETYPES)==12
for s in batch_registry()['sources']:
 e=UniverseBatch4Engine.format_universe_batch4_log(Node(id='test',name='test',ip_address='192.0.2.1'),s['splunk_sourcetype'],s['event_families'][0]);assert e.raw_log
'''
    result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stderr


def test_api_source_and_scenario_pack_paths():
    sys.path.insert(0,str(ROOT/'backend'))
    from app.main import app
    from fastapi.testclient import TestClient
    client=TestClient(app)
    result=client.post('/api/generate/scenario-pack',json={'scenario_id':BATCH4_SCENARIO_IDS[0],'dispatch':False})
    assert result.status_code==200 and result.json()['count_generated']==7
    response=client.post('/api/generate/single-event',json={'vendor_id':'tanium','sourcetype':'tanium:discover:managed'})
    assert response.status_code==200 and 'TaniumComputerId' in response.json()['raw']


def test_current_live_raw_bytes_and_parent_metadata():
    result=read('catalog/universe_batch4_current_raw_equality_results.json')
    submitted=read('docs/verification/universe_batch4/batch4_submitted_events.json')
    assert result['passes']==result['posted']==result['indexed_rows']==26
    assert len(result['distinct_sourcetypes'])==12
    assert result['engine_sha256']==hashlib.sha256((ROOT/result['generator_module']).read_bytes()).hexdigest()
    by_id={event['fields']['netspout_event_id']:event for event in submitted['events']}
    assert len(by_id)==26
    for check in result['raw_equality']:
        raw=by_id[check['label']]['event'].encode()
        assert hashlib.sha256(raw).hexdigest()==check['submitted_sha256']==check['indexed_sha256']
        assert len(raw)==check['submitted_bytes']==check['indexed_bytes'] and not check['correlation_leak']
    for event in submitted['events']:
        parent=event['fields'].get('netspout_parent_event_id')
        assert parent is None or parent in by_id
    assert result['ta_parser_checks_performed']==result['detection_checks_performed']==0
    assert result['configuration_changes']==0
    assert REG['live_verification']['status']=='PASS' and REG['live_verification']['run_id']==result['run_id']
