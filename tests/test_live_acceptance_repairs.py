"""Focused regression checks for destination routing, honest results and safe probes."""
import json
import asyncio
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / 'backend'), str(ROOT / 'netspout/bin')]
from app.destination_manager import DestinationManager, SplunkDestination
from app.live_dashboard import studio_definition


def destination(**updates):
    return SplunkDestination(id='lab', name='Lab', deployment_type='external_enterprise', **updates)


def test_transport_preserves_routing_and_secure_defaults(monkeypatch):
    monkeypatch.setenv('PULSEFORGE_TEST_TOKEN', 'test-secret')
    dest = destination(hec_token_env='PULSEFORGE_TEST_TOKEN', hec_index='events', hec_metric_index='metrics')
    transport = dest.to_transport_config()
    assert transport.hec_token == 'test-secret'
    assert transport.hec_index == 'events' and transport.hec_metric_index == 'metrics'
    assert transport.hec_ssl_verify and not transport.hec_allow_insecure_tls
    assert dest.mask_secrets().hec_index == 'events'
    assert 'test-secret' not in json.dumps(transport.model_dump())


def test_persistence_excludes_secrets_and_preserves_environment_reference(tmp_path, monkeypatch):
    manager = DestinationManager(str(tmp_path / 'destinations.json'))
    manager.add_destination(destination(hec_token='token-secret', search_password='password-secret', hec_token_env='PULSEFORGE_TEST_TOKEN'))
    persisted = Path(manager.config_file).read_text()
    assert 'token-secret' not in persisted and 'password-secret' not in persisted
    manager.update_destination('lab', {'name': 'Changed'})
    assert manager.destinations['lab'].hec_token == 'token-secret'
    monkeypatch.setenv('PULSEFORGE_TEST_TOKEN', 'restored-token')
    reloaded = DestinationManager(manager.config_file)
    assert reloaded.destinations['lab'].to_transport_config().hec_token == 'restored-token'


@pytest.mark.parametrize('url', ['http://external.example:8088', 'https://user:secret@example.com', 'https://example.com/?token=secret'])
def test_reject_insecure_or_credential_bearing_urls(url):
    with pytest.raises(ValueError):
        destination(hec_url=url)


@pytest.mark.parametrize('status,expected', [(200, True), (403, False)])
def test_probe_is_read_only_and_honors_tls(tmp_path, monkeypatch, status, expected):
    manager = DestinationManager(str(tmp_path / 'destinations.json'))
    manager.add_destination(destination(hec_token='probe-token'))
    seen = []
    real_client = httpx.AsyncClient
    def handler(request):
        seen.append(request)
        return httpx.Response(status, json={'code': 17})
    def factory(**kwargs):
        assert kwargs['verify'] is True
        return real_client(**kwargs, transport=httpx.MockTransport(handler))
    monkeypatch.setattr('app.destination_manager.httpx.AsyncClient', factory)
    result = asyncio.run(manager.test_destination('lab'))
    assert result.success is expected
    assert len(seen) == 1 and seen[0].method == 'GET'
    assert not result.details['ingestion_verified']
    assert 'probe-token' not in result.model_dump_json()


def test_probe_failure_redacts_exception(tmp_path, monkeypatch):
    manager = DestinationManager(str(tmp_path / 'destinations.json'))
    manager.add_destination(destination(hec_token='secret'))
    real_client = httpx.AsyncClient
    def handler(request):
        raise httpx.ConnectError('secret', request=request)
    monkeypatch.setattr('app.destination_manager.httpx.AsyncClient', lambda **kw: real_client(**kw, transport=httpx.MockTransport(handler)))
    result = asyncio.run(manager.test_destination('lab'))
    assert not result.success and 'secret' not in result.model_dump_json()


def test_static_route_and_run_transport(monkeypatch, tmp_path):
    import app.main as main
    import app.destination_api as api
    from app.models import RunManifest
    manager = DestinationManager(str(tmp_path / 'destinations.json'))
    manager.add_destination(destination(hec_token='secret', hec_index='test_events'))
    monkeypatch.setattr(main, 'destination_manager', manager)
    monkeypatch.setattr(api, 'destination_manager', manager)
    seen = []
    def run(req):
        seen.append(req)
        return RunManifest(run_id='test-run', scenario_id=req.scenario_id, total_events_generated=2, dispatch_attempted=2, dispatch_succeeded=1, dispatch_failed=1)
    monkeypatch.setattr(main.scenario_runner, 'run_scenario', run)
    client = TestClient(main.app)
    assert client.get('/api/destinations/deployment-types').status_code == 200
    response = client.post('/api/scenarios/run-with-destination', json={'scenario_id': 'cisco_aci_microburst', 'destination_id': 'lab'})
    assert response.status_code == 200
    assert seen[0].dispatch_telemetry and seen[0].transport_config.hec_token == 'secret'
    assert seen[0].transport_config.hec_index == 'test_events'
    assert response.json()['dispatch_succeeded'] == 1
    assert manager.destinations['lab'].total_events_sent == 1
    assert 'secret' not in response.text


def test_studio_structure_and_time_tokens():
    definition = studio_definition('test', 'index=events | stats count')
    assert isinstance(definition['visualizations'], dict)
    assert definition['layout']['structure'][0]['item'] in definition['visualizations']
    assert definition['defaults']['dataSources']['ds.search']['options']['queryParameters']['earliest'] == '$global_time.earliest$'


def test_observer_uses_metric_wildcard_and_distinct_records(monkeypatch):
    from app.live_dashboard import observe_run
    from app.models import RunManifest
    monkeypatch.setenv('PULSEFORGE_DASHBOARD_MANAGEMENT_URL', 'https://localhost:8089')
    monkeypatch.setenv('NETSPOUT_SPLUNK_USER', 'admin')
    monkeypatch.setenv('NETSPOUT_SPLUNK_PASSWORD', 'private')
    calls = []
    real_client = httpx.Client
    def handler(request):
        calls.append(request.content.decode())
        return httpx.Response(200, text=json.dumps({'result': {'count': '4' if len(calls) == 2 else '10'}})+'\n')
    monkeypatch.setattr('app.live_dashboard.httpx.Client', lambda **kw: real_client(**kw, transport=httpx.MockTransport(handler)))
    manifest = RunManifest(run_id='run-1', scenario_id='aci', total_events_generated=14, actual_generated_counts={'events': 10, 'cisco:ios:mdt': 4})
    observe_run(manifest, destination(search_url='https://localhost:8089'))
    assert manifest.observed_count == 14 and manifest.observation_status == 'VERIFIED'
    from urllib.parse import parse_qs
    query = parse_qs(calls[1])['search'][0]
    assert 'metric_name=*' in query and 'BY netspout_event_id' in query


def test_dashboard_permission_failure_is_explicit(monkeypatch):
    from fastapi import FastAPI
    from app.live_dashboard import register_live_dashboard
    from types import SimpleNamespace
    monkeypatch.setenv('PULSEFORGE_DASHBOARD_MANAGEMENT_URL', 'https://localhost:8089')
    monkeypatch.setenv('PULSEFORGE_DASHBOARD_WEB_URL', 'http://localhost:8000')
    monkeypatch.setenv('NETSPOUT_SPLUNK_USER', 'reader')
    monkeypatch.setenv('NETSPOUT_SPLUNK_PASSWORD', 'secret')
    real_client = httpx.Client
    monkeypatch.setattr('app.live_dashboard.httpx.Client', lambda **kw: real_client(**kw, transport=httpx.MockTransport(lambda r: httpx.Response(403))))
    app = FastAPI()
    register_live_dashboard(app, SimpleNamespace(get_run=lambda _: SimpleNamespace(scenario_name='Test')), SimpleNamespace(destinations={'lab': destination(search_url='https://localhost:8089')}))
    response = TestClient(app).post('/api/acceptance/dashboards/run-1', json={'destination_id':'lab'})
    assert response.status_code == 403 and 'never overwritten' in response.text
    assert 'secret' not in response.text
