"""Batch 6: captured Cisco Catalyst Center / SD-WAN / ACI / Nexus records. Fidelity to the capture, declared time fields, correlation."""
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT / 'src'), str(ROOT / 'backend')):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from netspout_core.authentic_scenario_packs import SCENARIO_PACK_IDS, run_scenario_pack
from netspout_core.generator_modes import TelemetryGeneratorService
from netspout_core.log_engine import SplunkLogEngine
from netspout_core.models import Node, NodeType
from netspout_core.universe_batch6_engine import BATCH6_SCENARIO_IDS, UniverseBatch6Engine as E, batch_registry

REG = batch_registry()
CASES = [(s, f) for s in REG['sources'] for f in s['families']]
NOW = datetime(2026, 10, 30, 12, 0, 5, 123456, timezone.utc)
DEV = Node(id='ub6-test', name='collector.example.test', type=NodeType.WEB_SERVER, ip_address='10.20.1.16')
CATALOG = {r['splunk_sourcetype']: r for r in json.loads((ROOT / 'catalog' / 'sourcetypes.json').read_text())}
UTD_TS = re.compile(r"\d{4}/\d\d/\d\d-\d\d:\d\d:\d\d\.\d{6} UTC")
MX_EPOCH = re.compile(r"(?<= )1\d{9}\.\d{9}(?= )")
NOT_PROMOTED = ['cisco:catalyst:rogue:allowed', 'cisco:catalyst:rogue:counts', 'cisco:catalyst:script:heartbeat', 'cisco:catalyst:threat:list']


def capture_at(family):
    text = next((ROOT / 'netspout/appserver/static/samples' / family['sample']).glob('*.yml')).read_text()
    line = text.splitlines()[family['sample_line'] - 1]
    return re.search(r"_raw: '(.*)'\s*$", line)[1].replace("''", "'")


def test_ten_catalogued_sources_each_with_a_native_generator_and_empty_pollers_left_out():
    assert len(REG['sources']) == 10 and len(CASES) == 18
    for s in REG['sources']:
        assert s['splunk_sourcetype'] in CATALOG and s['vendor'] == CATALOG[s['splunk_sourcetype']]['vendor_id']
        assert SplunkLogEngine.UNIVERSE_BATCH6_SOURCE_SOURCETYPES[s['splunk_sourcetype']] == s['batch_source_id']
    assert not set(NOT_PROMOTED) & {s['splunk_sourcetype'] for s in REG['sources']}


@pytest.mark.parametrize('source,family', CASES, ids=[s['batch_source_id'] + ':' + f['id'] for s, f in CASES])
def test_template_is_the_recorded_capture_and_only_declared_time_fields_vary(source, family):
    captured = capture_at(family)
    assert hashlib.sha256(captured.encode()).hexdigest() == family['captured_sha256']
    assert MX_EPOCH.sub('$EPOCH_NS$', UTD_TS.sub('$UTD_TS$', captured)) == family['template']
    entry = E.format_universe_batch6_log(DEV, source['splunk_sourcetype'], family['id'], when=NOW)
    assert not re.search(r"\$[A-Z_]+\$", entry.raw_log), 'every declared token must be resolved'
    assert entry.raw_log == E.format_universe_batch6_log(DEV, source['splunk_sourcetype'], family['id'], when=NOW).raw_log
    if '$EPOCH_MS$' in family['tokens']:
        assert str(int(NOW.timestamp() * 1000)) in entry.raw_log
    if '$GOTS$' in family['tokens']:
        assert '2026-10-30T12:00:05Z' in entry.raw_log
    if '$TS$' in family['tokens']:
        assert entry.raw_log.startswith('Oct 30 12:00:05 ')
    if '$UTD_TS$' in family['tokens']:
        assert '2026/10/30-12:00:05.123456 UTC' in entry.raw_log
    if '$EPOCH_NS$' in family['tokens']:
        assert f' {int(NOW.timestamp())}.123456000 ' in entry.raw_log
    # JSON payloads stay valid and keep the captured key order
    if family['template'].lstrip().startswith('{'):
        rendered = json.loads(entry.raw_log)
        original = json.loads(family['template'].replace('$EPOCH_MS$', '0').replace('$GOTS$', 'x'))
        assert list(rendered) == list(original)
    assert 'netspout_' not in entry.raw_log and 'ub6-test' not in entry.raw_log
    assert entry.sourcetype == source['splunk_sourcetype'] and entry.vendor == source['vendor']


def test_invalid_inputs_are_refused():
    with pytest.raises(ValueError):
        E.format_universe_batch6_log(DEV, 'cisco:sdwan:nope', when=NOW)
    with pytest.raises(ValueError):
        E.format_universe_batch6_log(DEV, 'cisco:sdwan:utdhealth', 'invented', when=NOW)
    with pytest.raises(ValueError):
        E.format_universe_batch6_log(DEV, 'cisco:sdwan:utdhealth', when=datetime(2026, 1, 1))


@pytest.mark.parametrize('scenario_id', BATCH6_SCENARIO_IDS)
def test_scenarios_are_ordered_registered_and_catalogued(scenario_id):
    assert scenario_id in SCENARIO_PACK_IDS
    events = run_scenario_pack(scenario_id, 'ub6-run')
    spec = REG['scenarios'][scenario_id]
    assert [e.netspout_phase for e in events] == [s['phase'] for s in spec] and len(events) == 6
    assert all(e.netspout_run_id == 'ub6-run' and 'ub6-run' not in e.raw_log for e in events)
    assert all(events[i].netspout_parent_event_id == events[i - 1].netspout_event_id for i in range(1, len(events)))
    cat = next(s for s in json.loads((ROOT / 'catalog' / 'scenarios.json').read_text()) if s['id'] == scenario_id)
    assert set(cat['sourcetypes']) == {e.sourcetype for e in events} and cat['maturity'] == 'CONTRACTED'


def test_utd_detections_correlate_with_utd_health_on_native_system_ip_and_hostname():
    events = run_scenario_pack('ub6_sdwan_utd_threat_pipeline', 'r')
    health = {json.loads(e.raw_log)['vdevice-dataKey']: json.loads(e.raw_log)['vdevice-host-name'] for e in events if e.sourcetype.endswith('utdhealth')}
    drops = [e.raw_log for e in events if e.sourcetype.endswith('utd:logs')]
    assert len(drops) == 2 and len(health) == 2
    for raw in drops:
        ip, host = re.search(r'\[System_IP: ([\d.]+)\]', raw)[1], re.search(r'\[Hostname: (\S+?)\]', raw)[1]
        assert ip in health and health[ip].lower() == host.lower()


@pytest.mark.parametrize('source', REG['sources'], ids=[s['batch_source_id'] for s in REG['sources']])
def test_user_facing_generation_and_dispatcher_boundary(source):
    service = TelemetryGeneratorService()
    single = service.generate_single_event(source['vendor'], source['splunk_sourcetype'])
    assert single['status'] == 'GROUNDED' and single['provenance']['source'] == 'catalog/universe_batch6.json'
    with patch('netspout_core.generator_modes.dispatcher.dispatch_log', return_value={'hec': {'success': True}}) as dispatch:
        result = service.generate_sourcetype_batch(source['vendor'], source['splunk_sourcetype'], count=2, dispatch=True)
        assert result['count_generated'] == result['count_dispatched'] == dispatch.call_count == 2
    with pytest.raises(ValueError):
        service.generate_single_event('wrong_vendor', source['splunk_sourcetype'])
