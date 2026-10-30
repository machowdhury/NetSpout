"""Replay API: destination authorization (Connection Center only), limits, lifecycle, restart safety, independent verification."""
import json
import sys
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
from netspout_core.models import TelemetryTransportConfig
from netspout_core.replay_service import ReplayService
from netspout_core.sample_replay import ReplayError

client = TestClient(main.app)
CFG = {'configured': True, 'deployment_mode': 'DOCKER_LAB', 'indexes': ['dev_test_replay', 'other_ok'], 'hec_url': 'https://127.0.0.1:8088/services/collector'}
GT = TelemetryTransportConfig(hec_url='https://127.0.0.1:8088/services/collector', hec_token='tok-test')


class FakeSink:
    sent = []

    def __init__(self, *a, **k):
        self.a = a

    def send(self, raw, when, meta=None):
        FakeSink.sent.append((self.a, raw, when))
        return 'accepted'


@pytest.fixture(autouse=True)
def env(tmp_path):
    FakeSink.sent = []
    main.replay_service = ReplayService(tmp_path / 'replay_state.json')
    with patch.object(main.release_candidate_configuration, 'load', return_value=dict(CFG)), \
            patch.object(main.current_topology, 'global_transport', GT, create=True), patch.object(main, 'HecSink', FakeSink):
        yield


def start(**kw):
    body = {'source_id': 'aws_cloudtrail', 'speed': 500, 'loops': 1, **kw}
    return client.post('/api/replay/sessions', json=body)


def test_sources_expose_defaults_and_no_file_paths():
    r = client.get('/api/replay/sources').json()
    assert r['defaults'] == {'index': 'dev_test_replay', 'host': 'replayed-log-generator'} and len(r['sources']) >= 10
    assert all('file' not in s for s in r['sources'])


def test_preview_shows_transformed_records_and_refuses_sources_without_timestamps():
    p = client.post('/api/replay/preview', json={'source_id': 'suricata_eve', 'count': 3}).json()
    assert p['chronology'] == 'SOURCE_TIMESTAMPS' and len(p['rows']) >= 3 and p['rows'][0]['original'] != p['rows'][0]['transformed']
    r = client.post('/api/replay/preview', json={'text': 'a\nb\n', 'format': 'text', 'sourcetype': 'x:y'})
    assert r.status_code == 422 and 'refusing to invent' in r.json()['detail']


def test_session_uses_the_default_isolated_index_and_host_and_a_unique_source():
    s = start().json()
    assert s['index'] == 'dev_test_replay' and s['host'] == 'replayed-log-generator' and s['source'].startswith('pulseforge:replay:aws_cloudtrail:rp-')
    for _ in range(100):
        if client.get('/api/replay/sessions/' + s['session_id']).json()['state'] == 'COMPLETED':
            break
        time.sleep(0.1)
    assert FakeSink.sent[0][0][2:4] == ('dev_test_replay', 'replayed-log-generator')


@pytest.mark.parametrize('body,code', [
    ({'index': 'prod_main'}, 403),                      # not on the Connection Center allowlist
    ({'index': 'bad index!'}, 422),
    ({'transport_config': {'hec_url': 'https://attacker.example:8088/services/collector'}}, 422),   # caller destinations are never accepted
    ({'speed': 0}, 422), ({'speed': 5000}, 422), ({'eps_limit': 0}, 422), ({'queue_size': 0}, 422), ({'loops': 0}, 422),
    ({'host': 'bad host;'}, 422), ({'source_id': 'nope'}, 422),
])
def test_destination_and_parameter_validation(body, code):
    assert start(**body).status_code == code and not FakeSink.sent


def test_no_connection_center_destination_means_no_replay():
    with patch.object(main.release_candidate_configuration, 'load', return_value={'configured': False}):
        assert start().status_code == 409
    with patch.object(main.current_topology, 'global_transport', None):
        assert start().status_code == 409


def test_non_lab_destination_requires_a_dev_index_and_confirmation():
    cfg = {**CFG, 'deployment_mode': 'SPLUNK_ENTERPRISE'}
    with patch.object(main.release_candidate_configuration, 'load', return_value=cfg):
        assert start().status_code == 403                                              # no confirmation
        assert start(index='other_ok', confirm_destination=True).status_code == 403    # not a dev_ index
        assert start(confirm_destination=True).status_code == 200


def test_pause_resume_stop_controls_and_conflicts():
    s = start(loops=None, continuous=True, speed=50).json()
    sid = s['session_id']
    assert client.post(f'/api/replay/sessions/{sid}/pause').json()['state'] == 'PAUSED'
    assert client.post(f'/api/replay/sessions/{sid}/pause').status_code == 409
    assert client.post(f'/api/replay/sessions/{sid}/resume').json()['state'] == 'RUNNING'
    assert client.post(f'/api/replay/sessions/{sid}/stop').json()['state'] == 'STOPPED'
    assert client.post(f'/api/replay/sessions/{sid}/dance').status_code == 404
    assert client.get('/api/replay/sessions/rp-unknown').status_code == 404


def test_session_limit():
    ids = [start(loops=None, continuous=True, speed=1).json()['session_id'] for _ in range(4)]
    assert start(loops=None, continuous=True).status_code == 422
    for i in ids:
        client.post(f'/api/replay/sessions/{i}/stop')


def test_independent_verification_reads_splunk_not_the_sender_counters():
    sid = start().json()['session_id']
    main.replay_service.get(sid).wait(10)
    n = main.replay_service.get(sid).counts['accepted']
    with patch.object(main.release_candidate_configuration, 'execute_read_only_search', return_value=([{'indexed': str(n), 'first_time': '1', 'last_time': '2'}], None)) as search:
        r = client.post(f'/api/replay/sessions/{sid}/verify').json()
    assert r['verified'] and r['indexed'] == n and r['complete'] is True and sid in search.call_args[0][0]
    with patch.object(main.release_candidate_configuration, 'execute_read_only_search', return_value=([{'indexed': '1'}], None)):
        assert client.post(f'/api/replay/sessions/{sid}/verify').json()['complete'] is False   # fewer indexed than accepted is never reported complete
    with patch.object(main.release_candidate_configuration, 'execute_read_only_search', return_value=([], 'authenticated Splunk search is not configured')):
        assert client.post(f'/api/replay/sessions/{sid}/verify').json()['verified'] is False


def test_restart_marks_active_sessions_interrupted_and_never_resends(tmp_path):
    state = tmp_path / 's.json'
    state.write_text(json.dumps({'rp-old': {'session_id': 'rp-old', 'state': 'RUNNING', 'counts': {'accepted': 3}}, 'rp-done': {'session_id': 'rp-done', 'state': 'COMPLETED'}}))
    svc = ReplayService(state)
    assert svc.status('rp-old')['state'] == 'INTERRUPTED' and 'NOT resumed' in svc.status('rp-old')['note'] and svc.status('rp-done')['state'] == 'COMPLETED'
    with pytest.raises(KeyError):
        svc.get('rp-old')            # no live session object exists, so nothing can be resumed
    assert json.loads(state.read_text())['rp-old']['state'] == 'INTERRUPTED' and not FakeSink.sent
