"""Batch 2 native grammar, selector provenance, runtime dispatch and live evidence."""
import hashlib
import importlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from netspout_core.authentic_scenario_packs import run_scenario_pack
from netspout_core.generator_modes import TelemetryGeneratorService
from netspout_core.models import Node
from netspout_core.universe_batch2_engine import UniverseBatch2Engine as E, batch_registry, BATCH2_SCENARIO_IDS

REG = batch_registry()
CASES = [(s, f) for s in REG['sources'] for f in s['families']]
NOW = datetime(2026, 10, 26, 19, 0, 1, 123456, timezone.utc)
DEV = Node(id='ub2-test', name='test-host.example.test', ip_address='198.51.100.22')


def read(path):
    return json.loads((ROOT / path).read_text())


@pytest.mark.parametrize('source,family', CASES, ids=[s['batch_source_id']+':'+f['id'] for s,f in CASES])
def test_pinned_selector_and_current_native_semantics(source, family):
    refs = {r['id']: r for r in read('catalog/raw_reference/universe_batch2/references.json')}
    ref = refs[family['origin']]
    fixture = ROOT / ref['raw_reference_file']
    assert hashlib.sha256(fixture.read_bytes()).hexdigest() == ref['sha256']
    selector = family['selector']
    original = fixture.read_text().splitlines()[int(selector.split(':')[1])-1] if selector.startswith('line:') else json.loads(fixture.read_text())['events'][int(re.search(r'\[(\d+)\]', selector)[1])]['event']['original']
    if isinstance(family['template'], dict):
        assert json.loads(original) == family['template']
    else:
        assert original == family['template']
    entry = E.format_universe_batch2_log(DEV, source['splunk_sourcetype'], family['id'], when=NOW)
    assert entry.timestamp == '2026-10-26 19:00:01.123'
    assert entry.sourcetype == source['splunk_sourcetype']
    assert 'netspout_' not in entry.raw_log and 'ub2-test' not in entry.raw_log
    assert entry.raw_log == E.format_universe_batch2_log(DEV, entry.sourcetype, family['id'], when=NOW).raw_log
    sid = source['batch_source_id']
    if sid in {'vault','traefik','mongodb','confluence','proofpoint'}:
        value = json.loads(entry.raw_log)
        assert value.keys() == family['template'].keys()
        if sid == 'vault':
            assert value['time'] == NOW.isoformat(timespec='microseconds').replace('+00:00','Z')
            assert value['request']['remote_address'] == '192.0.2.10'
            assert value['type'] in {'request','response'}
            assert value['auth']['client_token'].startswith('hmac-sha256:')
        if sid == 'traefik':
            assert value['ClientAddr'].startswith('192.0.2.10:')
            assert value['StartUTC'] == value['StartLocal']
            assert value['Duration'] == family['template']['Duration']
        if sid == 'mongodb':
            assert value['id'] == family['template']['id']
            assert value['msg'] == family['template']['msg']
            assert value['t']['$date'] == '2026-10-26T19:00:01.123+00:00'
        if sid == 'confluence':
            assert value['creationDate'] == int(NOW.timestamp()*1000)
            assert value['remoteAddress'] == '192.0.2.10'
        if sid == 'proofpoint':
            classification = 'malware' if family['id'].startswith('malware') else 'phish'
            assert value['threatsInfoMap'][0]['classification'] == classification
            assert value['messageTime'].startswith('2026-10-26T19:00:01')
    elif sid == 'claroty':
        assert 'CEF:0|Claroty|CTD|' in entry.raw_log
        assert '2026-10-26T19:00:01Z' in entry.raw_log
        assert 'CtdTimeGenerated=Oct 26 2026 19:00:01' in entry.raw_log
        assert '"ecs"' not in entry.raw_log and '"agent"' not in entry.raw_log
        if 'CtdSourceIp=' in entry.raw_log:
            assert 'CtdSourceIp=192.0.2.10' in entry.raw_log
            assert 'CtdDestinationIp=198.51.100.22' in entry.raw_log
    elif sid == 'nginx':
        assert entry.raw_log.startswith('192.0.2.10 - - [26/Oct/2026:19:00:01 +0000]')
        assert '"GET / HTTP/1.1" 200 612' in entry.raw_log
    elif sid == 'veeam':
        assert re.search(r'instanceId=(\d+)', entry.raw_log)[1] == re.search(r'instanceId=(\d+)', family['template'])[1]
        assert 'VbrHostName="test-host.example.test"' in entry.raw_log
        assert re.match(r'^(?:\[WRN\] )?\[categoryId=', entry.raw_log) and entry.raw_log.endswith(']')
    else:
        if family['id'] == 'ospf_hello_sent':
            assert 'SEND: Hello Packet 198.51.100.22 -> 224.0.0.5 on lo0' in entry.raw_log
            assert entry.protocol == 'OSPF' and entry.dest_ip == '224.0.0.5'
        else:
            assert entry.raw_log.startswith('oct/26 19:00:01 system,info,account')


@pytest.mark.parametrize('sid', BATCH2_SCENARIO_IDS)
def test_scenario_all_sources_unique_events_and_parent_chain(sid):
    entries = run_scenario_pack(sid, 'batch2-correlation-check')
    ids = [e.netspout_event_id for e in entries]
    assert len(ids) == len(set(ids))
    assert {e.netspout_phase for e in entries} == {'BASELINE','OBSERVE','VALIDATE'}
    expected = {s['splunk_sourcetype'] for s in REG['sources'] if s['batch_source_id'] in REG['scenarios'][sid]}
    assert {e.sourcetype for e in entries} == expected
    assert len(entries) == sum(s['event_family_count'] for s in REG['sources'] if s['batch_source_id'] in REG['scenarios'][sid])
    assert [e.netspout_parent_event_id for e in entries] == [None] + ids[:-1]
    for entry in entries:
        assert entry.netspout_run_id == 'batch2-correlation-check'
        assert 'batch2-correlation-check' not in entry.raw_log
        assert 'netspout_' not in entry.raw_log


@pytest.mark.parametrize('source', REG['sources'], ids=[s['batch_source_id'] for s in REG['sources']])
def test_user_facing_single_and_batch_generation_use_native_engine(source):
    service = TelemetryGeneratorService()
    result = service.generate_single_event(source['vendor'], source['splunk_sourcetype'])
    assert result['status'] == 'GROUNDED' and result['raw']
    with patch('netspout_core.generator_modes.dispatcher.dispatch_log', return_value={'hec': {'success': True}}) as dispatch:
        result = service.generate_sourcetype_batch(source['vendor'], source['splunk_sourcetype'], count=3, dispatch=True)
        assert result['count_generated'] == result['count_dispatched'] == dispatch.call_count == 3
        assert all(call.args[0].sourcetype == source['splunk_sourcetype'] for call in dispatch.call_args_list)
    with pytest.raises(ValueError):
        service.generate_single_event('wrong_vendor', source['splunk_sourcetype'])
    with pytest.raises(ValueError):
        service.generate_sourcetype_batch(source['vendor'], source['splunk_sourcetype'], count=1, event_families=['invented_family'])


def test_fail_closed_validation_and_no_mutation_of_templates():
    original = json.dumps(REG, sort_keys=True)
    for st in ['unknown', '']:
        with pytest.raises(ValueError): E.format_universe_batch2_log(DEV, st, 'http_access')
    with pytest.raises(ValueError): E.format_universe_batch2_log(DEV, 'nginx:access', 'http_access', when=datetime(2026,1,1))
    with pytest.raises(ValueError): E.format_universe_batch2_log(DEV, 'nginx:access', 'http_access', src_ip='not_an_ip')
    with pytest.raises(ValueError): E.format_universe_batch2_log(DEV, 'mikrotik:routeros', 'administrator_login', user_name='forged\nlog')
    assert json.dumps(REG, sort_keys=True) == original


def test_batch1_single_event_path_is_current_not_historical_replay():
    result=TelemetryGeneratorService().generate_single_event('wazuh','wazuh:alerts')
    assert result['status']=='GROUNDED'
    assert datetime.now(timezone.utc).strftime('%Y %b %d') in result['raw']


@pytest.mark.parametrize('target,package', [('src','netspout_core'),('backend','app'),('netspout/bin','netspout_core')])
def test_fresh_runtime_imports_and_templates(target,package):
    code=f'''import sys; sys.path.insert(0,{str(ROOT/target)!r})
from {package}.universe_batch2_engine import UniverseBatch2Engine, batch_registry
from {package}.models import Node
from {package}.log_engine import SplunkLogEngine
assert len(SplunkLogEngine.UNIVERSE_BATCH2_SOURCE_SOURCETYPES)==9
assert len(batch_registry()['sources'])==9
for s in batch_registry()['sources']:
 e=UniverseBatch2Engine.format_universe_batch2_log(Node(id="test",name="test",ip_address="192.0.2.2"),s['splunk_sourcetype'],s['event_families'][0])
 assert e.raw_log
'''
    r=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=20)
    assert r.returncode==0,r.stderr


def test_complete_original_queue_retained_and_no_false_parser_claims():
    baseline=read('catalog/vendor_universe/batch2_candidate_queue_baseline.json')
    assert len(REG['candidate_queue'])==len(baseline['vendors'])==66
    assert REG['candidate_products']==baseline['products'] and len(REG['candidate_products'])==583
    assert sum(v['batch2_status']=='IMPLEMENTED_LIMITED_FAMILIES' for v in REG['candidate_queue'])==9
    assert all(s['ta_metadata']['parser_verified'] is False for s in REG['sources'])
    assert sum(s['ta_metadata']['sourcetype_declared_in_snapshot'] for s in REG['sources'])==6
    assert sum(s['evidence_level']=='INTEGRATION_TEST_RAW' for s in REG['sources'])==8
    assert sum(s['evidence_level']=='VENDOR_DOCUMENTED' for s in REG['sources'])==1


def test_current_batch1_live_bytes_have_exact_hash_evidence():
    result=read('catalog/universe_batch1_current_raw_equality_results.json')
    assert result['passes']==result['posted']==result['indexed_rows']==7
    assert result['engine_sha256']==hashlib.sha256((ROOT/result['generator_module']).read_bytes()).hexdigest()
    for check in result['raw_equality']:
        assert check['submitted_sha256']==check['indexed_sha256']
        assert check['submitted_bytes']==check['indexed_bytes']
        assert not check['correlation_leak']


def test_api_scenario_and_source_generation():
    sys.path.insert(0,str(ROOT/'backend'))
    from fastapi.testclient import TestClient
    from app.main import app
    client=TestClient(app)
    response=client.post('/api/generate/scenario-pack',json={'scenario_id':BATCH2_SCENARIO_IDS[0],'dispatch':False})
    assert response.status_code==200,response.text
    assert response.json()['count_generated']==6
    assert response.json()['dispatch_results']==[]
    response=client.post('/api/generate/single-event',json={'vendor_id':'hashicorp','sourcetype':'hashicorp_vault_audit_log'})
    assert response.status_code==200 and response.json()['status']=='GROUNDED'
    import tempfile
    from unittest.mock import patch
    import app.main as main
    from netspout_core.release_candidate import ReleaseCandidateConfiguration
    with tempfile.TemporaryDirectory() as empty, patch.object(main,'release_candidate_configuration',ReleaseCandidateConfiguration(config_dir=empty)):
        response=client.post('/api/generate/scenario-pack',json={'scenario_id':BATCH2_SCENARIO_IDS[0],'dispatch':True})
    assert response.status_code==400  # Fail closed without explicit transport or a configured Connection Center.


def test_batch2_live_evidence_matches_submitted_current_bytes():
    result=read('catalog/universe_batch2_current_raw_equality_results.json')
    submitted=read('docs/verification/universe_batch2/batch2_submitted_events.json')
    assert result['passes']==result['posted']==result['indexed_rows']==18
    assert len(result['distinct_sourcetypes'])==9
    assert result['engine_sha256']==hashlib.sha256((ROOT/result['generator_module']).read_bytes()).hexdigest()
    actual={e['fields']['netspout_event_id']:e['event'] for e in submitted['events']}
    for check in result['raw_equality']:
        assert hashlib.sha256(actual[check['label']].encode()).hexdigest()==check['submitted_sha256']==check['indexed_sha256']
        assert check['submitted_bytes']==check['indexed_bytes']
        assert not check['correlation_leak']
    assert result['installed_ta_inventory']==[{'id':'Splunk_TA_cisco-ise','version':'5.0.0'}]
    assert result['ta_parser_checks_performed']==result['detection_checks_performed']==0


def test_actual_dispatcher_preserves_native_raw_and_hec_metadata():
    from netspout_core.models import TelemetryTransportConfig
    from netspout_core.telemetry_dispatcher import dispatcher, HecOutcome
    config=TelemetryTransportConfig(hec_enabled=True, hec_url='https://127.0.0.1:8088/services/collector',
                                    hec_token='offline-test-placeholder', hec_index='idx_network_ops',
                                    syslog_enabled=False, otel_enabled=False, telegraf_enabled=False)
    with patch.object(dispatcher,'emit_hec',return_value=HecOutcome(True,'accepted','ACCEPTED',200)) as emit:
        result=TelemetryGeneratorService().generate_universe_scenario(BATCH2_SCENARIO_IDS[0],
                            run_id='dispatch-metadata-test',dispatch=True,transport_config=config)
    assert emit.call_count==len(result['events'])==6
    for call,event in zip(emit.call_args_list,result['events']):
        payload=call.args[0]
        assert payload['event']==event['raw_log']
        assert payload['sourcetype']==event['sourcetype']
        assert payload['fields']['netspout_run_id']=='dispatch-metadata-test'
        assert 'dispatch-metadata-test' not in payload['event']


def test_api_invalid_family_is_refused_without_dispatch():
    sys.path.insert(0,str(ROOT/'backend'))
    from fastapi.testclient import TestClient
    from app.main import app
    response=TestClient(app).post('/api/generate/sourcetype',json={
        'vendor_id':'veeam','sourcetype':'veeam_vbr_syslog','event_families':['invented'],'dispatch':False})
    assert response.status_code==400
