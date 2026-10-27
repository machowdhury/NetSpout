"""Deploy a namespaced run dashboard using explicitly configured management access."""
import json
import os
import re
from urllib.parse import quote
import httpx
from fastapi import HTTPException


def studio_definition(title, query):
    return {
        "title": title, "description": "PulseForge indexed run evidence",
        "inputs": {"time": {"type": "input.timerange", "title": "Time", "options": {"token": "global_time", "defaultValue": "-1h,now"}}},
        "defaults": {"dataSources": {"ds.search": {"options": {"queryParameters": {"earliest": "$global_time.earliest$", "latest": "$global_time.latest$"}}}}},
        "dataSources": {"events": {"type": "ds.search", "options": {"query": query}}},
        "visualizations": {"table": {"type": "splunk.table", "title": "Indexed scenario events", "dataSources": {"primary": "events"}}},
        "layout": {"type": "absolute", "options": {"width": 1200, "height": 600}, "globalInputs": ["time"], "structure": [{"item": "table", "type": "block", "position": {"x": 0, "y": 0, "w": 1200, "h": 550}}]},
    }


def register_live_dashboard(app, runner, destinations):
    @app.post('/api/acceptance/dashboards/{run_id}')
    def deploy(run_id: str, payload: dict):
        manifest = runner.get_run(run_id)
        dest = destinations.destinations.get(payload.get('destination_id'))
        if not manifest or not dest:
            raise HTTPException(404, 'Run or destination not found')
        # Never guess management endpoints or silently use credentials on another host.
        management = os.environ.get('PULSEFORGE_DASHBOARD_MANAGEMENT_URL', '')
        web = os.environ.get('PULSEFORGE_DASHBOARD_WEB_URL', '')
        if not management or management.rstrip('/') != (dest.search_url or '').rstrip('/') or not web:
            raise HTTPException(400, 'Explicit matching dashboard management and web URLs required; export fallback remains available')
        user = os.environ.get('NETSPOUT_SPLUNK_USER', '')
        password = os.environ.get('NETSPOUT_SPLUNK_PASSWORD', '')
        if not user or not password:
            raise HTTPException(400, 'Management credentials unavailable; use export fallback')
        if not re.fullmatch(r'[\w-]+', run_id) or not re.fullmatch(r'[\w-]+', dest.hec_index):
            raise HTTPException(400, 'Invalid run or index identifier')
        dashboard_id = 'pulseforge_acceptance_' + run_id.lower().replace('-', '_')
        query = f'index={dest.hec_index} netspout_run_id="{run_id}" | table _time host sourcetype netspout_phase _raw'
        definition = studio_definition('PulseForge ' + manifest.scenario_name, query)
        xml = '<dashboard version="2" theme="dark"><label>PulseForge acceptance</label><definition><![CDATA[' + json.dumps(definition) + ']]></definition></dashboard>'
        try:
            with httpx.Client(verify=dest.hec_ssl_verify and not dest.hec_allow_insecure_tls, timeout=15, trust_env=False, auth=(user, password)) as client:
                response = client.post(management.rstrip('/') + '/servicesNS/nobody/search/data/ui/views', data={'name': dashboard_id, 'eai:data': xml, 'output_mode': 'json'})
            if response.status_code not in (200, 201):
                raise HTTPException(response.status_code, f'Dashboard create HTTP {response.status_code}; existing dashboards are never overwritten')
        except httpx.HTTPError:
            raise HTTPException(502, 'Dashboard management connection failed')
        return {'dashboard_id': dashboard_id, 'status': 'created', 'url': web.rstrip('/') + '/en-US/app/search/' + quote(dashboard_id), 'query': query, 'definition': definition}


def observe_run(manifest, dest):
    """Bounded independent counts; never infer indexing from an HEC response."""
    management = os.environ.get('PULSEFORGE_DASHBOARD_MANAGEMENT_URL', '')
    if not management or management.rstrip('/') != (dest.search_url or '').rstrip('/'):
        return
    user, password = os.environ.get('NETSPOUT_SPLUNK_USER'), os.environ.get('NETSPOUT_SPLUNK_PASSWORD')
    if not user or not password:
        return
    if not all(re.fullmatch(r'[\w-]+', value) for value in (dest.hec_index, dest.hec_metric_index, manifest.run_id)):
        return
    queries = [
        f'search index={dest.hec_index} netspout_run_id="{manifest.run_id}" earliest=-1h latest=now | stats count',
        f'| mstats count(_value) as points WHERE index={dest.hec_metric_index} metric_name=* netspout_run_id="{manifest.run_id}" earliest=-1h latest=now BY netspout_event_id | stats count sum(points) as points',
    ]
    try:
        with httpx.Client(verify=dest.hec_ssl_verify and not dest.hec_allow_insecure_tls, timeout=10, trust_env=False, auth=(user, password)) as client:
            counts = []
            for query in queries:
                response = client.post(management.rstrip('/') + '/services/search/jobs/export', data={'search': query, 'output_mode': 'json', 'preview': 'false'})
                response.raise_for_status()
                messages = [json.loads(line) for line in response.text.splitlines() if line.strip()]
                if any(item.get('type') in ('ERROR', 'FATAL') for item in messages):
                    raise ValueError('Search rejected')
                counts.append(sum(int(float(item['result'].get('count', 0))) for item in messages if 'result' in item))
        manifest.event_observed_count, manifest.metric_observed_count = counts
        manifest.observed_count = sum(counts)
        # Metric point count differs from record count when a record contains several metrics.
        expected_events = sum(value for key, value in manifest.actual_generated_counts.items() if key not in ('cisco:ios:mdt', 'cisco:ios:mdt:metric'))
        expected_metrics = manifest.total_events_generated - expected_events
        complete = counts[0] == expected_events and counts[1] == expected_metrics
        manifest.observation_status = 'VERIFIED' if complete else 'OBSERVATION_PENDING'
        manifest.destination_validation = 'PASS' if complete else 'PENDING'
        manifest.observation_completeness_pct = 100.0 * sum(counts) / max(1, manifest.total_events_generated)
        if complete:
            manifest.overall_validation = 'PASS' if all(str(rule.status) in ('PASS', 'ValidationStatus.PASS') for rule in manifest.validation_results) else 'FAIL'
        if not complete:
            manifest.errors.append('Indexed observation incomplete: events %s/%s; metric records %s/%s' % (counts[0], expected_events, counts[1], expected_metrics))
    except (httpx.HTTPError, ValueError, KeyError):
        manifest.errors.append('Independent indexed observation failed: management access or search unavailable')
