"""Native source contracts, queue conservation and real parser evidence boundaries."""
import ast
import hashlib
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
from netspout_core.universe_batch3_engine import UniverseBatch3Engine as E,batch_registry,BATCH3_SCENARIO_IDS
from netspout_core.authentic_scenario_packs import run_scenario_pack
from netspout_core.generator_modes import TelemetryGeneratorService
REG=batch_registry();CASES=[(s,f) for s in REG['sources'] for f in s['families']]
NOW=datetime(2026,10,26,21,1,2,123456,timezone.utc)
DEV=Node(id='ub3-test',name='host.example.test',ip_address='198.51.100.30')


def read(path):return json.loads((ROOT/path).read_text())


@pytest.mark.parametrize('source,family',CASES,ids=[s['batch_source_id']+':'+f['id'] for s,f in CASES])
def test_exact_provenance_selectors_and_native_field_semantics(source,family):
    ref=next(r for r in read('catalog/raw_reference/universe_batch3/references.json') if r['id']==family['origin'])
    data=(ROOT/ref['raw_reference_file']).read_bytes()
    assert hashlib.sha256(data).hexdigest()==ref['sha256'] and len(data)==ref['bytes']
    text=data.decode();selector=family['selector']
    if selector.startswith('line:'):original=text.splitlines()[int(selector.split(':')[1])-1]
    elif selector=='first_blank_delimited_record_include_separator':original=text.split('\n\n',1)[0]+'\n\n'
    else:original=json.loads(text)['events'][int(re.search(r'\[(\d+)\]',selector)[1])]['event']['original']
    assert (json.loads(original) if isinstance(family['template'],dict) else original)==family['template']
    entry=E.format_universe_batch3_log(DEV,source['splunk_sourcetype'],family['id'],when=NOW)
    assert entry.raw_log==E.format_universe_batch3_log(DEV,source['splunk_sourcetype'],family['id'],when=NOW).raw_log
    assert entry.timestamp=='2026-10-26 21:01:02.123'
    assert entry.sourcetype==source['splunk_sourcetype'] and entry.vendor==source['vendor']
    assert 'netspout_' not in entry.raw_log and 'ub3-test' not in entry.raw_log
    sid=source['batch_source_id']
    if isinstance(family['template'],dict):
        value=json.loads(entry.raw_log)
        assert value.keys()==family['template'].keys()
        if sid=='sysdig':
            assert value['timestamp']==int(NOW.timestamp())*1_000_000_000+NOW.microsecond*1000
            assert value['source']==family['template']['source']
        elif sid=='sailpoint':
            assert value['created']==value['synced']=='2026-10-26T21:01:02.123Z'
            assert value['action']==family['template']['action']
        elif sid=='darktrace':
            assert value['creationTime']==int(NOW.timestamp()*1000)
            assert value['creationTime']-value['time']==family['template']['creationTime']-family['template']['time']
            assert value['model']==family['template']['model']
        elif sid=='beyondtrust':
            assert value['CreateDate']=='2026-10-26T21:01:02.123Z'
            assert value['ActionType']=='Add' and value['Section']=='SecretsSafeFolder'
        elif sid=='tenable':
            assert value['received']=='2026-10-26T21:01:02.123Z'
            assert value['action']==family['template']['action'] and value['is_failure']==family['template']['is_failure']
    elif sid=='pfsense':
        assert entry.raw_log.startswith('<134>Oct 26 21:01:02 filterlog[')
        fields=entry.raw_log.split(': ',1)[1].split(',')
        original_fields=family['template'].split(': ',1)[1].split(',')
        assert len(fields)==len(original_fields)
        assert fields[6:9]==original_fields[6:9]
        if fields[8]=='6':assert fields[15:17]==['2001:db8::10','2001:db8::20']
        else:assert fields[18:20]==['192.0.2.10','198.51.100.20']
    elif sid=='oracle':
        header,length,body=entry.raw_log.split('\n',2)
        assert header=='Mon Oct 26 21:01:02 2026 +00:00'
        assert int(re.search(r"'(\d+)'",length)[1])==len(body.encode())
        assert body==family['template'].split('\n',2)[2]
        assert entry.src_ip=='0.0.0.0'
    elif sid=='ibmmq':
        assert entry.raw_log.startswith('10/26/26 21:01:02 - Process(')
        assert 'Time(2026-10-26T21:01:02.123Z)' in entry.raw_log
        assert 'Host(host.example.test)' in entry.raw_log
        assert re.search(r'AMQ\d+[IWE]',entry.raw_log)[0]==re.search(r'AMQ\d+[IWE]',family['template'])[0]
    elif sid=='imperva':
        assert '|Imperva Inc.|SecureSphere|' in entry.raw_log and 'rt=Oct 26 2026 21:01:02' in entry.raw_log
        assert '${' not in entry.raw_log and '"ecs"' not in entry.raw_log
    elif sid=='barracuda':
        assert entry.raw_log.startswith('<129>2026-10-26 21:01:02.123 +0000  host.example.test WF ALER ')
        # Native action LOG remains observational; do not invent a block verdict.
        assert ' LOG NONE ' in entry.raw_log


@pytest.mark.parametrize('sid',BATCH3_SCENARIO_IDS)
def test_scenario_registration_phases_and_correlation_chain(sid):
    entries=run_scenario_pack(sid,'ub3-correlation')
    assert {e.sourcetype for e in entries}=={s['splunk_sourcetype'] for s in REG['sources'] if s['batch_source_id'] in REG['scenarios'][sid]}
    assert {e.netspout_phase for e in entries}=={'BASELINE','OBSERVE','VALIDATE'}
    ids=[e.netspout_event_id for e in entries]
    assert len(ids)==len(set(ids))
    assert [e.netspout_parent_event_id for e in entries]==[None]+ids[:-1]
    assert all(e.netspout_run_id=='ub3-correlation' and 'ub3-correlation' not in e.raw_log for e in entries)


@pytest.mark.parametrize('source',REG['sources'],ids=[s['batch_source_id'] for s in REG['sources']])
def test_user_facing_generation_and_actual_dispatcher_boundary(source):
    service=TelemetryGeneratorService()
    single=service.generate_single_event(source['vendor'],source['splunk_sourcetype'])
    assert single['status']=='GROUNDED' and single['provenance']['source']=='catalog/universe_batch3.json'
    with patch('netspout_core.generator_modes.dispatcher.dispatch_log',return_value={'hec':{'success':True}}) as dispatch:
        result=service.generate_sourcetype_batch(source['vendor'],source['splunk_sourcetype'],count=3,dispatch=True)
        assert result['count_generated']==result['count_dispatched']==dispatch.call_count==3
        assert all(call.args[0].sourcetype==source['splunk_sourcetype'] for call in dispatch.call_args_list)
    with pytest.raises(ValueError):service.generate_single_event('wrong_vendor',source['splunk_sourcetype'])
    with pytest.raises(ValueError):service.generate_sourcetype_batch(source['vendor'],source['splunk_sourcetype'],event_families=['invented'])


def test_native_validation_failures_and_template_immutability():
    before=json.dumps(REG,sort_keys=True)
    with pytest.raises(ValueError):E.format_universe_batch3_log(DEV,'unknown','family')
    with pytest.raises(ValueError):E.format_universe_batch3_log(DEV,'pfsense:filterlog','ipv6_udp_block',src_ip='192.0.2.1')
    with pytest.raises(ValueError):E.format_universe_batch3_log(DEV,'pfsense:filterlog','ipv4_tcp_block',when=datetime(2026,1,1))
    assert json.dumps(REG,sort_keys=True)==before


def test_all_original_candidates_conserved_with_status_and_ibm_scope():
    old=read('catalog/vendor_universe/batch2_candidate_queue_baseline.json')
    assert len(REG['candidate_queue'])==len(old['vendors'])==66
    assert {v['vendor_key'] for v in REG['candidate_queue']}=={v['vendor_key'] for v in old['vendors']}
    statuses=[v['batch3_status'] for v in REG['candidate_queue']]
    assert statuses.count('IMPLEMENTED_LIMITED_FAMILIES_BATCH3')==9
    assert statuses.count('IMPLEMENTED_LIMITED_FAMILIES_BATCH2')==9
    assert len(REG['candidate_products'])==len(REG['product_candidate_statuses'])==583
    assert REG['candidate_products']==old['products']
    assert all(v['status'] in {'IMPLEMENTED_LIMITED_FAMILIES','BLOCKED_SELECTED_RAW_REFERENCE','PENDING_REVIEW'} for v in REG['product_candidate_statuses'])
    assert next(v for v in REG['candidate_queue'] if v['vendor_key']=='ibm_qradar')['batch3_status']=='PENDING_REVIEW'
    assert REG['additional_snapshot_product']['uid']==3829


def test_real_ta_parser_results_preserve_blocked_expectation():
    result=read('catalog/universe_batch3_ise_parser_results.json')
    assert result['indexed_events']==len(result['checks'])==10
    assert result['passes']==9
    failed=[c for c in result['checks'] if c['verdict']=='FAIL']
    assert len(failed)==1 and failed[0]['label']=='current-generator-5205'
    assert failed[0]['expected_fields']['src_mac']=='00:1a:2b:3c:4d:5e'
    assert failed[0]['actual_fields']['src_mac'] is None
    assert failed[0]['actual_fields']['src_ip']=='00:1a:2b:3c:4d'
    assert all(c['lookup_status']=='VERIFIED' and c['timestamp_check']['ok'] for c in result['checks'])
    assert result['event_breaking']['actual_events']==2 and result['event_breaking']['exact_records']
    assert result['verified_sourcetypes']==[] and result['configuration_changes']==0
    tree=ast.parse((ROOT/'src/netspout_core/log_engine.py').read_text())
    methods=[ast.dump(n,include_attributes=False) for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name in {'format_cisco_ise_log','format_cisco_ise_coa_log'}]
    assert hashlib.sha256('\n'.join(methods).encode()).hexdigest()==result['generator_method_ast_sha256']
    inventory=read('catalog/universe_batch3_ta_inventory.json')
    assert inventory['ise_installed_files']['lookups/cisco_ise_message_catalog_500.csv']['sha256']==result['lookup_sha256']
    assert {a['id'] for a in inventory['installed_apps'] if 'parser_stanzas' in a}=={'Splunk_TA_cisco-ise'}
    assert inventory['downloaded_packages']==inventory['installed_packages']==0


@pytest.mark.parametrize('target,package',[('src','netspout_core'),('backend','app'),('netspout/bin','netspout_core')])
def test_runtime_mirror_imports_and_native_templates(target,package):
    code=f'''import sys;sys.path.insert(0,{str(ROOT/target)!r})
from {package}.universe_batch3_engine import batch_registry,UniverseBatch3Engine
from {package}.models import Node
from {package}.log_engine import SplunkLogEngine
assert len(SplunkLogEngine.UNIVERSE_BATCH3_SOURCE_SOURCETYPES)==10
for s in batch_registry()['sources']:
 e=UniverseBatch3Engine.format_universe_batch3_log(Node(id='test',name='test',ip_address='192.0.2.1'),s['splunk_sourcetype'],s['event_families'][0]);assert e.raw_log
'''
    result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stderr


def test_api_source_and_scenario_pack_paths():
    sys.path.insert(0,str(ROOT/'backend'))
    from app.main import app
    from fastapi.testclient import TestClient
    client=TestClient(app)
    result=client.post('/api/generate/scenario-pack',json={'scenario_id':BATCH3_SCENARIO_IDS[0],'dispatch':False})
    assert result.status_code==200 and result.json()['count_generated']==8
    response=client.post('/api/generate/single-event',json={'vendor_id':'ibm_mq','sourcetype':'ibm:mq:errorlog'})
    assert response.status_code==200 and 'AMQ8001I' in response.json()['raw']


def test_current_live_raw_bytes_and_parent_metadata():
    result=read('catalog/universe_batch3_current_raw_equality_results.json')
    submitted=read('docs/verification/universe_batch3/batch3_submitted_events.json')
    assert result['passes']==result['posted']==result['indexed_rows']==20
    assert len(result['distinct_sourcetypes'])==10
    assert result['engine_sha256']==hashlib.sha256((ROOT/result['generator_module']).read_bytes()).hexdigest()
    by_id={event['fields']['netspout_event_id']:event for event in submitted['events']}
    assert len(by_id)==20
    for check in result['raw_equality']:
        raw=by_id[check['label']]['event'].encode()
        assert hashlib.sha256(raw).hexdigest()==check['submitted_sha256']==check['indexed_sha256']
        assert len(raw)==check['submitted_bytes']==check['indexed_bytes'] and not check['correlation_leak']
    for event in submitted['events']:
        parent=event['fields'].get('netspout_parent_event_id')
        assert parent is None or parent in by_id
    assert result['ta_parser_checks_performed']==result['detection_checks_performed']==0


def test_ta_mapping_assessment_covers_every_canonical_source():
    matrix=read('catalog/universe_batch3_parser_assessments.json')
    assert len(matrix['sources'])==336 and matrix['new_verified_sourcetypes']==0
    batch4_sts={s['splunk_sourcetype'] for s in read('catalog/universe_batch4.json')['sources']}
    assert {s['sourcetype'] for s in matrix['sources']}=={s['splunk_sourcetype'] for s in read('catalog/sourcetypes.json')}-batch4_sts-{s['splunk_sourcetype'] for s in read('catalog/universe_batch7.json')['sources']}
    actual=[s for s in matrix['sources'] if s['status']=='ACTUAL_EXECUTION_PARTIAL_WITH_BLOCKER']
    assert len(actual)==1 and actual[0]['sourcetype']=='cisco:ise:syslog'
    assert all(s['ta_metadata']['parser_verified'] is False for s in REG['sources'])
    assert sum(s['ta_metadata']['sourcetype_declared_in_snapshot'] for s in REG['sources'])==6
