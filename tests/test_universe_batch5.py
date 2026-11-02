"""Batch 5: Cisco IOS-XE change/fault/health syslog. Text fidelity to captured messages, slot validation, scenario correlation."""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from netspout_core.authentic_scenario_packs import run_scenario_pack
from netspout_core.log_engine import SplunkLogEngine
from netspout_core.models import Node, NodeType
from netspout_core.universe_batch5_engine import BATCH5_SCENARIO_IDS, UniverseBatch5Engine as E, batch_registry

REG = batch_registry()
CASES = [(s, f) for s in REG['sources'] for f in s['families']]
NOW = datetime(2026, 10, 30, 12, 0, 5, 123456, timezone.utc)
DEV = Node(id='ub5-test', name='edge.example.test', type=NodeType.SWITCH, ip_address='10.201.48.119')
HEADER = re.compile(r'^Oct 30 12:00:05 10\.201\.48\.119 (\d+): (\*?)Oct 30 12:00:05\.123: (%.*)$')
CATALOG = {r['splunk_sourcetype'] for r in json.loads((ROOT / 'catalog' / 'sourcetypes.json').read_text())}


def captured_bodies(sample):
    text = next((ROOT / 'netspout/appserver/static/samples' / sample).glob('*.yml')).read_text()
    bodies = []
    for line in text.splitlines():
        m = re.search(r"_raw: '(.*)'\s*$", line)
        if m:
            bodies.append(re.search(r'(%[A-Z0-9_]+-\d-[A-Z0-9_]+:.*)$', m.group(1).replace("''", "'"))[1])
    return bodies


def test_every_source_is_a_catalogued_sourcetype_with_a_native_generator():
    assert len(REG['sources']) == 31
    for s in REG['sources']:
        assert s['splunk_sourcetype'] in CATALOG
        assert SplunkLogEngine.UNIVERSE_BATCH5_SOURCE_SOURCETYPES[s['splunk_sourcetype']] == s['batch_source_id']
        assert callable(SplunkLogEngine.format_universe_batch5_log)


@pytest.mark.parametrize('source,family', CASES, ids=[s['batch_source_id'] + ':' + f['id'] for s, f in CASES])
def test_text_is_a_captured_device_message(source, family):
    entry = E.format_universe_batch5_log(DEV, source['splunk_sourcetype'], family['id'], when=NOW, sequence=4391)
    m = HEADER.match(entry.raw_log)
    assert m, entry.raw_log
    assert m.group(1) == '4391' and bool(m.group(2)) == family['star']
    body = m.group(3)
    # the %FACILITY-SEV-MNEMONIC tag always equals the sourcetype's mnemonic
    assert body.startswith('%' + source['batch_source_id'] + ':')
    captured = captured_bodies(family['sample'])
    if family['origin'] == 'captured':
        assert body in captured
    else:
        # a linked family's template must regenerate at least one captured line (only the declared slots differ)
        pattern = re.escape(family['body'])
        for slot in family['params']:
            pattern = pattern.replace(re.escape('{' + slot + '}'), '(.+?)')
        assert any(re.fullmatch(pattern, b) for b in captured), (family['id'], family['body'])
    assert 'netspout_' not in entry.raw_log and 'ub5-test' not in entry.raw_log
    assert entry.sourcetype == source['splunk_sourcetype'] and entry.vendor == 'cisco_sdwan'
    assert entry.raw_log == E.format_universe_batch5_log(DEV, source['splunk_sourcetype'], family['id'], when=NOW, sequence=4391).raw_log


def test_slots_vary_only_where_declared_and_are_validated():
    ospf = lambda **p: E.format_universe_batch5_log(DEV, 'cisco:sdwan:OSPF-5-ADJCHG', 'adjacency', when=NOW, params=p).raw_log
    assert 'Nbr 10.9.9.9 on Vlan30 from FULL to DOWN' in ospf(neighbor='10.9.9.9', interface='Vlan30')
    for bad in ({'neighbor': 'not-an-ip'}, {'neighbor': '10.0.0.1; rm'}, {'interface': 'Gi1\n%SYS-1-FAKE'}, {'bogus': 'x'}):
        with pytest.raises(ValueError):
            ospf(**bad)
    with pytest.raises(ValueError):
        E.format_universe_batch5_log(DEV, 'cisco:sdwan:DMI-5-SYNC_NEEDED', 'sync_needed', when=NOW, params={'command': "x'; reload"})
    with pytest.raises(ValueError):
        E.format_universe_batch5_log(DEV, 'cisco:sdwan:NOPE', 'x', when=NOW)
    with pytest.raises(ValueError):
        E.format_universe_batch5_log(DEV, 'cisco:sdwan:LINK-5-UPDOWN', 'link_state', when=datetime(2026, 1, 1))
    # the MDT slot defaults to the rendering device address so the line stays self-consistent
    assert 'pubd: Connection state changed (id 6 - 10.20.1.16:25103:0:10.201.48.119): DOWN' in E.format_universe_batch5_log(DEV, 'cisco:sdwan:MDT_CONNECTION-6-STATE_CHANGED', 'connection_state', when=NOW).raw_log


@pytest.mark.parametrize('scenario_id', BATCH5_SCENARIO_IDS)
def test_scenarios_are_ordered_correlated_and_keep_metadata_out_of_raw(scenario_id):
    events = run_scenario_pack(scenario_id, 'ub5-run')
    spec = REG['scenarios'][scenario_id]
    assert len(events) == len(spec) >= 8
    assert [e.netspout_phase for e in events] == [s['phase'] for s in spec]
    assert all(e.netspout_run_id == 'ub5-run' and e.netspout_scenario_id == scenario_id for e in events)
    assert events[0].netspout_parent_event_id is None and all(events[i].netspout_parent_event_id == events[i - 1].netspout_event_id for i in range(1, len(events)))
    assert all('ub5-run' not in e.raw_log and 'netspout_' not in e.raw_log for e in events)
    seqs = [int(HEADER_ANY.match(e.raw_log)[1]) for e in events]
    assert seqs == sorted(seqs) and len(set(seqs)) == len(seqs)
    assert {e.sourcetype for e in events} <= CATALOG
    cat = next(s for s in json.loads((ROOT / 'catalog' / 'scenarios.json').read_text()) if s['id'] == scenario_id)
    assert set(cat['sourcetypes']) == {e.sourcetype for e in events} and cat['maturity'] == 'CONTRACTED'


HEADER_ANY = re.compile(r'^\w{3} \d\d \d\d:\d\d:\d\d \S+ (\d+): ')


def test_change_induced_outage_tells_the_change_to_fault_to_recovery_story():
    raws = [e.raw_log for e in run_scenario_pack('ub5_cisco_change_induced_outage', 'r')]
    idx = lambda needle, start=0: next(i for i in range(start, len(raws)) if needle in raws[i])
    change = idx('DMI-5-SYNC_NEEDED')
    mismatch = idx('NATIVE_VLAN_MISMATCH', change)
    down = idx('changed state to down', mismatch)
    ospf = idx('from FULL to DOWN', down)
    up = idx('changed state to up', ospf)
    assert change < mismatch < down < ospf < up and 'allowed vlan 2052' in raws[change]
    assert any('LOADING to FULL' in r for r in raws[up:])


def test_catalog_scenarios_and_registry_agree_on_counts():
    assert REG['counts_summary'] == {'new_native_sourcetypes': 31, 'families': len(CASES), 'scenario_packs': 3}


from unittest.mock import patch
from netspout_core.generator_modes import TelemetryGeneratorService


@pytest.mark.parametrize('source', REG['sources'], ids=[s['batch_source_id'] for s in REG['sources']])
def test_user_facing_generation_and_dispatcher_boundary(source):
    service = TelemetryGeneratorService()
    single = service.generate_single_event(source['vendor'], source['splunk_sourcetype'])
    assert single['status'] == 'GROUNDED' and single['provenance']['source'] == 'catalog/universe_batch5.json'
    with patch('netspout_core.generator_modes.dispatcher.dispatch_log', return_value={'hec': {'success': True}}) as dispatch:
        result = service.generate_sourcetype_batch(source['vendor'], source['splunk_sourcetype'], count=3, dispatch=True)
        assert result['count_generated'] == result['count_dispatched'] == dispatch.call_count == 3
        assert all(c.args[0].sourcetype == source['splunk_sourcetype'] for c in dispatch.call_args_list)
    with pytest.raises(ValueError):
        service.generate_single_event('wrong_vendor', source['splunk_sourcetype'])
    with pytest.raises(ValueError):
        service.generate_sourcetype_batch(source['vendor'], source['splunk_sourcetype'], event_families=['invented'])


def test_scenario_pack_route_dispatches_to_the_configured_destination(monkeypatch):
    sys.path.insert(0, str(ROOT / 'backend'))
    from fastapi.testclient import TestClient
    import app.main as main
    from app.generator_modes import generator_service
    sent = []
    monkeypatch.setattr(generator_service, 'generate_universe_scenario',
                        lambda sid, run_id=None, dispatch=False, transport_config=None: sent.append((sid, dispatch, transport_config)) or {'run_id': 'r', 'count_generated': 0, 'dispatch_results': []})
    gt = main.current_topology.global_transport
    saved = (gt.hec_url, gt.hec_index)
    gt.hec_url, gt.hec_index = 'https://127.0.0.1:1/services/collector', 'event_idx'
    monkeypatch.setattr(main.release_candidate_configuration, 'load', lambda: {'configured': True, 'indexes': ['idx_network_ops']})
    try:
        r = TestClient(main.app).post('/api/generate/scenario-pack', json={'scenario_id': 'ub5_cisco_nac_radius_outage', 'dispatch': True, 'index': 'idx_network_ops'})
        assert r.status_code == 200
        sid, dispatch, cfg = sent[0]
        assert (sid, dispatch, cfg.hec_url, cfg.hec_index) == ('ub5_cisco_nac_radius_outage', True, 'https://127.0.0.1:1/services/collector', 'idx_network_ops')
        sent.clear()
        TestClient(main.app).post('/api/generate/scenario-pack', json={'scenario_id': 'ub5_cisco_nac_radius_outage'})
        assert sent[0][1:] == (False, None)
    finally:
        gt.hec_url, gt.hec_index = saved


def test_explorer_runs_packs_through_the_pack_engine_and_marks_contract_only_scenarios_not_runnable():
    from netspout_core.use_case_explorer import UseCaseExplorer, load_taxonomy
    from netspout_core.security_content_lab import SecurityContentCatalog
    scenarios = [{"id": "ub5_cisco_nac_radius_outage", "maturity": "CONTRACTED"}, {"id": "sleepy", "maturity": "CONTRACTED"},
                 {"id": "cisco_aci_microburst", "maturity": "GOLDEN_PATH_CERTIFIED"}]
    ex = UseCaseExplorer(taxonomy=load_taxonomy(), generation_scenarios=[], generation_sources=[], dashboards=[], catalog_scenarios=scenarios,
                         security_catalog=SecurityContentCatalog(), validations=lambda: [], runtime_approved_detections=[],
                         pack_scenario_ids=['ub5_cisco_nac_radius_outage'], runner_scenario_ids=['cisco_aci_microburst'])
    by = {e['scenario_id']: e for e in ex.search(kind='operational', demo_ready=None, limit=10)['items']}
    pack, sleepy, runner = by['ub5_cisco_nac_radius_outage'], by['sleepy'], by['cisco_aci_microburst']
    assert (pack['engine'], pack['runnable'], pack['entry_id']) == ('scenario_pack', True, 'op:pack:ub5_cisco_nac_radius_outage')
    steps = {s['step']: s for s in pack['workflow']}
    assert steps['GENERATE']['endpoint']['path'] == '/api/generate/scenario-pack' and steps['VERIFY']['endpoint']['path'] == '/api/explorer/observe'
    assert steps['DASHBOARD']['available'] is False  # no dashboard is claimed for a pack
    assert not pack['demo_ready']  # CONTRACTED stays out of the demo-ready filter even though it runs
    assert sleepy['runnable'] is False and 'Contract only' in sleepy['blocked_reason'] and sleepy['workflow'][2]['available'] is False
    assert runner['engine'] == 'scenario_runner' and runner['runnable'] and runner['demo_ready']


def test_generator_route_refuses_an_index_the_connection_center_does_not_authorize(tmp_path, monkeypatch):
    sys.path.insert(0, str(ROOT / 'backend'))
    import app.main as main
    from fastapi import HTTPException
    from netspout_core.release_candidate import ReleaseCandidateConfiguration
    cfg = ReleaseCandidateConfiguration(config_dir=str(tmp_path))
    monkeypatch.setattr(main, 'release_candidate_configuration', cfg)
    monkeypatch.setattr(cfg, 'load', lambda: {'configured': True, 'indexes': ['idx_network_ops']})
    gt = main.current_topology.global_transport
    saved = gt.hec_url
    gt.hec_url = 'https://127.0.0.1:1/services/collector'
    try:
        assert main._generator_transport('idx_network_ops').hec_index == 'idx_network_ops'
        with pytest.raises(HTTPException) as err:
            main._generator_transport('some_other_index')
        assert err.value.status_code == 403
    finally:
        gt.hec_url = saved
