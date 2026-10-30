"""Replay scenario packs: replay + native phases on one timeline, phase/run tagging, per-cycle regeneration, API."""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT / 'src'), str(ROOT / 'backend')):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from fastapi.testclient import TestClient

from app import main
from netspout_core import replay_packs as rp
from netspout_core.models import TelemetryTransportConfig
from netspout_core.replay_service import ReplayService, preview, sources
from netspout_core.sample_replay import ReplaySession, iter_transformed

PACKS = rp.packs()
ANCHOR = datetime(2026, 11, 1, 12, 0, 0, tzinfo=timezone.utc)
TAXONOMY = {i['id'] for i in json.loads((ROOT / 'catalog/explorer_taxonomy.json').read_text())['industries']}
client = TestClient(main.app)


class Sink:
    def __init__(self):
        self.got = []

    def send(self, raw, when, meta=None):
        self.got.append((raw, when, meta))
        return 'accepted'


def test_definitions_reference_only_real_sources_real_native_packs_and_approved_industries():
    from netspout_core.authentic_scenario_packs import SCENARIO_PACK_IDS
    ids = {s['id'] for s in sources()}
    assert len(PACKS) == 7 and len({p['id'] for p in PACKS}) == 7
    for p in PACKS:
        assert set(p['industries']) <= TAXONOMY and p['category'] in ('SOC', 'NOC', 'ITOPS', 'AI_SECURITY') and p['seed'] and p['verification_spl'] and p['detection_prerequisites']
        for ph in p['phases']:
            s = ph['source']
            assert (s['kind'] == 'replay' and s['source_id'] in ids) or (s['kind'] == 'native' and s['pack'] in SCENARIO_PACK_IDS)


@pytest.mark.parametrize('pack', PACKS, ids=[p['id'] for p in PACKS])
def test_timeline_is_ordered_tagged_and_recorded_bytes_survive(pack):
    tl = rp.build_pack_timeline(pack['id'])
    offs = [i.offset for i in tl.items]
    assert offs == sorted(offs) and tl.chronology == 'PACK_SCHEDULE_OVER_SOURCE_SPACING' and tl.loop_gap_s > 0
    assert {i.fields['netspout_phase'] for i in tl.items} == {ph['id'] for ph in pack['phases']}
    assert {i.fields['netspout_scenario_id'] for i in tl.items} == {pack['id']} and len({i.fields['netspout_run_id'] for i in tl.items}) == 1
    rows = list(iter_transformed(tl, ANCHOR, loops=2))
    stamps = [r[3] for r in rows]
    assert stamps == sorted(stamps)
    boundary = [i for i, r in enumerate(rows) if r[0] == 1][0]
    assert stamps[boundary] > stamps[boundary - 1]                          # cycle boundary never overlaps or regresses
    for k, i, off, stamp, raw in rows[:len(tl.items)]:
        it = tl.items[i]
        if it.producer is None:                                              # replayed: only the timestamp bytes may differ
            a, b = it.span
            assert raw[:a] == it.record[:a] and raw[len(raw) - (len(it.record) - b):] == it.record[b:]


def test_hybrid_pack_mixes_replay_and_native_phases_and_regenerates_native_events_per_cycle():
    pack = rp.get('rp_agentic_ai_mcp_runtime_hybrid')
    assert rp.correlation_level(pack) == 'MIXED_TEMPORAL_ONLY_BETWEEN_SOURCES'
    tl = rp.build_pack_timeline(pack['id'])
    kinds = {i.fields['netspout_source_kind'] for i in tl.items}
    assert kinds == {'replay', 'native'}
    native = [i for i in tl.items if i.producer]
    c0, c1 = native[0].producer(0), native[0].producer(1)
    assert c0 and c1 and rp.build_pack_timeline(pack['id']).items[-1].fields['netspout_run_id'] == tl.items[-1].fields['netspout_run_id']   # deterministic run id


def test_session_delivers_tags_and_cycle_numbers_with_every_event_in_order():
    tl = rp.build_pack_timeline('rp_cloud_control_plane_activity', cycle_gap_s=1)
    sink = Sink()
    s = ReplaySession(tl, sink, source_label='rp_cloud_control_plane_activity', sourcetype='(per event)', speed=1000, loops=2).start()
    assert s.wait(10) == 'COMPLETED'
    assert len(sink.got) == 24 and [g[2]['fields']['netspout_cycle'] for g in sink.got] == ['0'] * 12 + ['1'] * 12
    assert all(g[2]['sourcetype'] == 'aws:cloudtrail' and g[2]['fields']['netspout_phase'] == 'ACTIVITY' for g in sink.got)
    stamps = [g[1] for g in sink.got]
    assert stamps == sorted(stamps)


# ---------------------------------------------------------------- API
CFG = {'configured': True, 'deployment_mode': 'DOCKER_LAB', 'indexes': ['dev_test_replay'], 'hec_url': 'https://127.0.0.1:8088/services/collector'}
GT = TelemetryTransportConfig(hec_url='https://127.0.0.1:8088/services/collector', hec_token='tok-test')


class ApiSink:
    sent = []

    def __init__(self, *a, **k):
        pass

    def send(self, raw, when, meta=None):
        ApiSink.sent.append((raw, when, meta))
        return 'accepted'


@pytest.fixture()
def api(tmp_path):
    ApiSink.sent = []
    main.replay_service = ReplayService(tmp_path / 'st.json')
    with patch.object(main.release_candidate_configuration, 'load', return_value=dict(CFG)), patch.object(main.current_topology, 'global_transport', GT, create=True), \
            patch.object(main, 'HecSink', ApiSink):
        yield


def test_api_lists_packs_previews_and_runs_one_shot_and_continuous(api):
    listing = client.get('/api/replay/packs').json()
    assert len(listing['packs']) == 7 and all(p['correlation_level'] for p in listing['packs']) and 'phases' in listing['packs'][0]
    pv = client.post('/api/replay/preview', json={'pack_id': 'rp_workload_sysmon_ebpf_hybrid', 'count': 4}).json()
    assert pv['pack_id'] == 'rp_workload_sysmon_ebpf_hybrid' and pv['rows'][0]['phase'] == 'WORKLOAD'
    one = client.post('/api/replay/sessions', json={'pack_id': 'rp_cloud_control_plane_activity', 'speed': 1000, 'loops': 1}).json()
    main.replay_service.get(one['session_id']).wait(10)
    assert len(ApiSink.sent) == 12
    ApiSink.sent = []
    cont = client.post('/api/replay/sessions', json={'pack_id': 'rp_cloud_control_plane_activity', 'speed': 1000, 'continuous': True, 'loop_gap_s': 0.5}).json()
    time.sleep(1.5)
    client.post(f"/api/replay/sessions/{cont['session_id']}/stop")
    cycles = {g[2]['fields']['netspout_cycle'] for g in ApiSink.sent}
    assert len(cycles) >= 2 and main.replay_service.status(cont['session_id'])['state'] == 'STOPPED'


def test_unknown_pack_is_refused(api):
    assert client.post('/api/replay/sessions', json={'pack_id': 'nope'}).status_code == 422
    assert client.post('/api/replay/preview', json={'pack_id': 'nope'}).status_code == 422


def test_explorer_exposes_replay_packs_as_runnable_contracted_with_honest_verification():
    items = client.get('/api/explorer/entries?kind=operational&q=rp_&limit=50').json()['items']
    packs = {i['scenario_id']: i for i in items if i['engine'] == 'replay_pack'}
    assert set(packs) == {p['id'] for p in PACKS}
    for e in packs.values():
        assert e['runnable'] and e['blocked_reason'] is None and e['maturity']['tier'] == 'CONTRACTED'     # never promoted because events indexed
        assert e['live_verified'] and not e['dashboard_verified'] and e['dashboard'] is None
        assert e['source_modes'] and all(i['basis'] == 'editorial' for i in e['industries']) and e['industries']
        steps = {s['step']: s for s in e['workflow']}
        assert steps['GENERATE']['endpoint']['path'] == '/api/replay/sessions' and steps['GENERATE']['available']
        assert steps['VERIFY']['endpoint']['path'] == '/api/replay/sessions/{session_id}/verify'
        assert not steps['DASHBOARD']['available']
    assert packs['rp_agentic_ai_mcp_runtime_hybrid']['source_modes'] == ['native', 'replay']
    assert packs['rp_cloud_control_plane_activity']['source_modes'] == ['replay']
