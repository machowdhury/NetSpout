"""Live delivery monitor: real counters, accounting semantics, controls, persistence, API, destination authorization."""
import json
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT / 'src'), str(ROOT / 'backend')):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from fastapi.testclient import TestClient

from app import main
from netspout_core.delivery_monitor import DeliveryRun, Item, RunMonitorService
from netspout_core.models import TelemetryTransportConfig
from netspout_core.replay_service import ReplayService


def items(n, outcomes=None, delay=0.0, st='x:y', phase='P1'):
    outcomes = outcomes or {}
    def mk(i):
        def send():
            time.sleep(delay)
            r = outcomes.get(i, 'accepted')
            return r, (None if r == 'accepted' else 'HEC HTTP 403 (code 4)')
        return Item(st, phase, send)
    return [mk(i) for i in range(n)]


def test_counters_are_exact_and_accepted_is_never_indexed():
    run = DeliveryRun('sourcetype', 'x:y', 'x:y', 'dest', 'idx', items(10, {3: 'rejected', 4: 'unknown', 5: 'unknown'})).start()
    assert run.wait(10) == 'COMPLETED'
    s = run.snapshot()
    c = s['counters']
    assert (c['generated'], c['attempts'], c['accepted'], c['rejected'], c['unknown'], c['pending']) == (10, 10, 7, 1, 2, 0)
    assert c['indexed'] is None and s['verification']['status'] == 'NOT_RUN'          # nothing claims indexing until an independent search ran
    assert s['by_sourcetype']['x:y']['accepted'] == 7 and s['by_phase'][0]['total'] == 10
    assert [e['outcome'] for e in s['recent_errors']] == ['rejected', 'unknown', 'unknown'] and 'code 4' in s['recent_errors'][0]['message']
    assert s['progress'] == {'total': 10, 'done': 10, 'pct': 100.0} and s['mode'] == 'finite'


def test_pause_resume_stop_keep_counters_and_never_invent_completion():
    run = DeliveryRun('sourcetype', 't', 't', 'd', 'i', items(200, delay=0.01)).start()
    time.sleep(0.3)
    run.pause()
    time.sleep(0.2)
    n = run.snapshot()['counters']['attempts']
    time.sleep(0.4)
    assert run.snapshot()['counters']['attempts'] == n and run.snapshot()['state'] == 'PAUSED' and run.snapshot()['controls']['resume']
    run.resume()
    time.sleep(0.2)
    run.stop()
    s = run.snapshot()
    assert s['state'] == 'STOPPED' and 0 < s['counters']['attempts'] < 200 and s['counters']['pending'] == 200 - s['counters']['attempts']
    assert s['eta_s'] is None and s['progress']['pct'] < 100


def test_eps_limit_and_rate_fields_are_measured():
    run = DeliveryRun('sourcetype', 't', 't', 'd', 'i', items(30), eps_limit=50).start()
    run.wait(10)
    s = run.snapshot()
    assert 15 <= s['rate']['average_eps'] <= 60 and s['rate']['limit_eps'] == 50 and s['elapsed_s'] >= 0.4


def test_sender_exception_becomes_a_visible_rejection():
    def boom():
        raise RuntimeError('socket reset')
    run = DeliveryRun('sourcetype', 't', 't', 'd', 'i', [Item('a', None, boom), Item('a', None, lambda: ('accepted', None))]).start()
    run.wait(5)
    s = run.snapshot()
    assert s['counters']['rejected'] == 1 and s['counters']['accepted'] == 1 and s['recent_errors'][0]['message'] == 'RuntimeError'


def test_persistence_marks_active_runs_interrupted_and_keeps_counters(tmp_path):
    state = tmp_path / 'runs.json'
    svc = RunMonitorService(state)
    run = DeliveryRun('sourcetype', 't', 't', 'd', 'i', items(100, delay=0.02))
    svc.start(run)
    time.sleep(0.5)
    saved = json.loads(state.read_text())[run.id]
    assert saved['state'] in ('RUNNING', 'COMPLETED')
    run.stop()
    # simulate a crash: persisted file says RUNNING
    saved['state'] = 'RUNNING'
    state.write_text(json.dumps({run.id: saved}))
    svc2 = RunMonitorService(state)
    h = svc2.snapshot(run.id)
    assert h['state'] == 'INTERRUPTED' and h['counters']['attempts'] == saved['counters']['attempts'] and 'not resumed' in h['interrupted_note'] and not any(h['controls'].values())


# ---------------------------------------------------------------- API
client = TestClient(main.app)
CFG = {'configured': True, 'deployment_mode': 'DOCKER_LAB', 'indexes': ['dev_test_replay', 'dev_test_replay_metrics'], 'hec_url': 'https://127.0.0.1:8088/services/collector'}
GT = TelemetryTransportConfig(hec_url='https://127.0.0.1:8088/services/collector', hec_token='tok-test', hec_metric_index='dev_test_replay_metrics')


class FakeOutcome(tuple):
    def __new__(cls, ok, msg, state):
        o = super().__new__(cls, (ok, msg))
        o.state = state
        return o


@pytest.fixture()
def env(tmp_path):
    main.run_monitor = RunMonitorService(tmp_path / 'runs.json')
    main.replay_service = ReplayService(tmp_path / 'replay.json')
    sent = []

    def fake_dispatch_log(entry, cfg):
        sent.append((entry.sourcetype, cfg.hec_index, entry.netspout_run_id))
        return {'hec': {'success': True, 'state': 'ACCEPTED', 'message': 'HEC HTTP 200'}}

    def fake_emit(payload, url, token, **kw):
        sent.append((payload['sourcetype'], payload['index'], payload['fields'].get('netspout_run_id')))
        return FakeOutcome(True, 'HEC HTTP 200', 'ACCEPTED')

    with patch.object(main.release_candidate_configuration, 'load', return_value=dict(CFG)), patch.object(main.current_topology, 'global_transport', GT, create=True), \
            patch.object(main.dispatcher, 'dispatch_log', side_effect=fake_dispatch_log), patch.object(main.dispatcher, 'emit_hec', side_effect=fake_emit):
        yield sent


def wait_done(rid, timeout=15):
    for _ in range(int(timeout * 10)):
        s = client.get('/api/runs/' + rid).json()
        if s['state'] in ('COMPLETED', 'STOPPED', 'FAILED'):
            return s
        time.sleep(0.1)
    return s


def test_scenario_pack_run_reports_per_sourcetype_and_per_phase_progress(env):
    r = client.post('/api/runs', json={'kind': 'scenario', 'target': 'ub5_cisco_change_induced_outage', 'eps': 500})
    assert r.status_code == 200, r.text
    s = wait_done(r.json()['run_id'])
    assert s['state'] == 'COMPLETED' and s['counters']['generated'] == s['counters']['accepted'] == 20 and s['counters']['indexed'] is None
    assert {p['phase'] for p in s['by_phase']} == {'BASELINE', 'CHANGE', 'FAULT', 'RECOVERY'} and sum(p['accepted'] for p in s['by_phase']) == 20
    assert len(s['by_sourcetype']) > 3 and all(i == 'dev_test_replay' for _, i, _ in env) and {x[2] for x in env} == {s['run_id']}


def test_incident_pack_uses_the_metric_index_and_is_verified_independently(env):
    r = client.post('/api/runs', json={'kind': 'scenario', 'target': 'network_01_campus_link', 'eps': 500}).json()
    s = wait_done(r['run_id'])
    assert s['counters']['accepted'] == 40 and s['destination']['metric_index'] == 'dev_test_replay_metrics'
    assert {i for _, i, _ in env} == {'dev_test_replay', 'dev_test_replay_metrics'}
    dp = main.run_monitor.snapshot(r['run_id'])['metric_accepted']['datapoints']
    assert dp > 10 and main.run_monitor.snapshot(r['run_id'])['metric_accepted']['events'] == 10     # one metric event carries several datapoints
    calls = []
    def search(q):
        calls.append(q)
        return ([{'indexed': '30'}] if 'stats count as indexed' in q else [{'n': str(dp)}]), None
    with patch.object(main.release_candidate_configuration, 'execute_read_only_search', side_effect=search):
        v = client.post('/api/runs/%s/verify' % r['run_id']).json()
    assert v['status'] == 'VERIFIED' and v['indexed'] == 30 and v['metric_datapoints_indexed'] == dp and any('mstats' in q for q in calls)
    assert client.get('/api/runs/' + r['run_id']).json()['counters']['indexed'] == 40
    with patch.object(main.release_candidate_configuration, 'execute_read_only_search', return_value=([{'indexed': '12'}], None)):
        v2 = client.post('/api/runs/%s/verify' % r['run_id']).json()
    assert v2['status'] == 'INCOMPLETE'                    # fewer found than accepted is never reported verified


def test_single_sourcetype_run_and_grounding_refusal(env):
    ok = client.post('/api/runs', json={'kind': 'sourcetype', 'target': 'cisco:sdwan:utdhealth', 'vendor_id': 'cisco_sdwan', 'count': 12, 'eps': 500})
    assert ok.status_code == 200, ok.text
    s = wait_done(ok.json()['run_id'])
    assert s['counters']['accepted'] == 12 and list(s['by_sourcetype']) == ['cisco:sdwan:utdhealth']
    bad = client.post('/api/runs', json={'kind': 'sourcetype', 'target': 'not:a:real:sourcetype', 'vendor_id': 'cisco_sdwan', 'count': 3})
    assert bad.status_code == 422 and 'GROUNDED' in bad.json()['detail']


def test_replay_pack_run_uses_the_same_schema_with_finite_and_continuous_modes(env):
    with patch.object(main, 'HecSink') as sink:
        sink.return_value.send.return_value = 'accepted'
        sink.return_value.last_error = None
        r = client.post('/api/runs', json={'kind': 'scenario', 'target': 'rp_cloud_control_plane_activity', 'speed': 1000, 'loops': 1}).json()
        s = wait_done(r['run_id'])
        assert s['kind'] == 'replay' and s['mode'] == 'finite' and s['counters']['accepted'] == 12 and s['progress'] == {'total': 12, 'done': 12, 'pct': 100.0}
        assert s['by_sourcetype']['aws:cloudtrail']['accepted'] == 12 and s['by_phase'][0]['phase'] == 'ACTIVITY'
        c = client.post('/api/runs', json={'kind': 'scenario', 'target': 'rp_cloud_control_plane_activity', 'speed': 1000, 'continuous': True}).json()
        time.sleep(1.0)
        live = client.get('/api/runs/' + c['run_id']).json()
        assert live['mode'] == 'continuous' and live['progress']['total'] is None and live['progress']['pct'] is None and live['state'] == 'RUNNING' and live['eta_s'] is None
        assert client.post('/api/runs/%s/pause' % c['run_id']).json()['state'] == 'PAUSED'
        assert client.post('/api/runs/%s/stop' % c['run_id']).json()['state'] in ('STOPPED', 'STOPPING')


@pytest.mark.parametrize('body,code', [
    ({'kind': 'scenario', 'target': 'ub5_cisco_change_induced_outage', 'index': 'prod_main'}, 403),
    ({'kind': 'scenario', 'target': 'ub5_cisco_change_induced_outage', 'transport_config': {'hec_url': 'https://evil.example:8088/services/collector'}}, 422),
    ({'kind': 'scenario', 'target': 'ub5_cisco_change_induced_outage', 'eps': 0}, 422),
    ({'kind': 'nope', 'target': 'x'}, 422),
])
def test_destination_authorization_and_honest_refusals(env, body, code):
    assert client.post('/api/runs', json=body).status_code == code and not env


def test_unknown_run_and_actions(env):
    assert client.get('/api/runs/run-unknown').status_code == 404
    assert client.post('/api/runs/run-unknown/pause').status_code == 404
    assert client.post('/api/runs/run-unknown/dance').status_code == 404
    assert client.get('/api/runs').status_code == 200


def test_observed_run_counts_only_what_crosses_the_delivery_boundary(tmp_path):
    from netspout_core.delivery_monitor import ObservedRun, observe_dispatch, set_service
    svc = RunMonitorService(tmp_path / 'r.json')
    set_service(svc)
    with svc.observe(ObservedRun('scenario', 't', 't', 'd', 'i', expected=4, run_id='obs-1')):
        observe_dispatch('a:b', 'P1', {'hec': {'state': 'ACCEPTED', 'success': True}})
        observe_dispatch('a:b', 'P1', {'hec': {'state': 'FAILED', 'success': False, 'message': 'HEC HTTP 403 (code 4)'}})
        observe_dispatch('a:c', 'P2', {'hec': {'state': 'UNKNOWN', 'success': False, 'message': 'timeout'}})
        observe_dispatch('a:c', 'P2', {'hec': None})                                   # never attempted: generated, not an attempt
        mid = svc.snapshot('obs-1')
        assert mid['state'] == 'RUNNING' and mid['progress']['pct'] == 75.0 and mid['mode'] == 'observed'
    s = svc.snapshot('obs-1')
    c = s['counters']
    assert (c['generated'], c['attempts'], c['accepted'], c['rejected'], c['unknown'], c['pending'], c['indexed']) == (4, 3, 1, 1, 1, 1, None)
    assert s['state'] == 'COMPLETED' and s['controls'] == {'pause': False, 'resume': False, 'stop': False} and 'not supported' in s['controls_note']
    assert {e['outcome'] for e in s['recent_errors']} == {'rejected', 'unknown', 'not_attempted'}
    observe_dispatch('x', None, {'hec': {'success': True}})                            # outside a run: nothing recorded anywhere
    assert svc.snapshot('obs-1')['counters']['generated'] == 4


def test_scenario_runner_run_is_monitored_through_the_real_dispatcher(env):
    from app import scenario_runner as sr
    with patch.object(sr.dispatcher, '_dispatch_log', return_value={'hec': {'success': True, 'state': 'ACCEPTED', 'message': 'ok'}}):
        r = client.post('/api/runs', json={'kind': 'scenario', 'target': 'arch_lan_campus_access'})
        assert r.status_code == 200, r.text
        s = wait_done(r.json()['run_id'], 60)
    assert s['state'] == 'COMPLETED' and s['mode'] == 'observed', s['error']
    c = s['counters']
    assert c['generated'] == c['attempts'] == c['accepted'] > 0 and c['rejected'] == c['unknown'] == 0 and c['indexed'] is None
    manifest = main.scenario_runner.get_run(r.json()['run_id'])
    assert manifest is not None and manifest.dispatch_attempted == c['attempts']          # the monitor and the runner's own manifest agree
