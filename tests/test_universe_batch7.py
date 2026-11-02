"""Batch 7: authentic NGINX Plus key=value access records (nginx:plus:access). Fidelity to the capture; only time_local varies."""
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
from netspout_core.generator_modes import TelemetryGeneratorService
from netspout_core.log_engine import SplunkLogEngine
from netspout_core.models import Node, NodeType
from netspout_core.universe_batch7_engine import UniverseBatch7Engine as E, batch_registry

REG = batch_registry()
SOURCE = REG['sources'][0]
NOW = datetime(2026, 10, 30, 12, 0, 5, 123456, timezone.utc)
DEV = Node(id='ub7-test', name='collector.example.test', type=NodeType.WEB_SERVER, ip_address='10.20.1.16')
CATALOG = {r['splunk_sourcetype']: r for r in json.loads((ROOT / 'catalog' / 'sourcetypes.json').read_text())}
TIME_LOCAL = re.compile(r'(?<=time_local=")\d\d/[A-Z][a-z]{2}/\d{4}:\d\d:\d\d:\d\d \+0000(?=")')


def test_catalogued_with_a_splunkbase_declared_ta_and_dispatch_registered():
    row = CATALOG['nginx:plus:access']
    assert row['vendor_id'] == SOURCE['vendor'] == 'nginx_f5' and row['required_ta'] == 'Splunk Add-on for NGINX'
    assert row['required_ta_review']['splunkbase_ids'] == [3258]
    assert SplunkLogEngine.UNIVERSE_BATCH7_SOURCE_SOURCETYPES['nginx:plus:access'] == 'nginx:plus:access'


@pytest.mark.parametrize('family', SOURCE['families'], ids=[f['id'] for f in SOURCE['families']])
def test_template_is_the_recorded_capture_and_only_time_local_varies(family):
    captured = (Path.home() / 'Downloads/attack_data/datasets/attack_techniques/T1190/confluence' / family['dataset'])
    if not captured.is_file():
        pytest.skip('attack_data checkout not present; fidelity is pinned by captured_sha256 in the registry')
    line = captured.read_bytes().decode().splitlines()[family['dataset_line'] - 1]
    assert hashlib.sha256(line.encode()).hexdigest() == family['captured_sha256']
    assert TIME_LOCAL.sub('$NGINX_TS$', line) == family['template']
    raw = E.format_universe_batch7_log(DEV, 'nginx:plus:access', family['id'], when=NOW).raw_log
    assert 'time_local="30/Oct/2026:12:00:05 +0000"' in raw
    assert raw.replace('30/Oct/2026:12:00:05 +0000', '$NGINX_TS$') == family['template']
    assert re.findall(r'(\w+)=', raw)[:3] == ['site', 'server', 'dest_port'] and 'netspout_' not in raw and 'ub7-test' not in raw


def test_invalid_inputs_are_refused():
    with pytest.raises(ValueError):
        E.format_universe_batch7_log(DEV, 'nginx:plus:nope', when=NOW)
    with pytest.raises(ValueError):
        E.format_universe_batch7_log(DEV, 'nginx:plus:access', 'invented', when=NOW)
    with pytest.raises(ValueError):
        E.format_universe_batch7_log(DEV, 'nginx:plus:access', when=datetime(2026, 1, 1))


def test_user_facing_generation_and_dispatcher_boundary():
    service = TelemetryGeneratorService()
    single = service.generate_single_event('nginx_f5', 'nginx:plus:access')
    assert single['status'] == 'GROUNDED' and single['provenance']['source'] == 'catalog/universe_batch7.json'
    with patch('netspout_core.generator_modes.dispatcher.dispatch_log', return_value={'hec': {'success': True}}) as dispatch:
        result = service.generate_sourcetype_batch('nginx_f5', 'nginx:plus:access', count=2, dispatch=True)
        assert result['count_generated'] == result['count_dispatched'] == dispatch.call_count == 2
    with pytest.raises(ValueError):
        service.generate_single_event('wrong_vendor', 'nginx:plus:access')
