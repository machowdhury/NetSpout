"""Recovery regression checks for supported Batch 1 formats and packaging."""
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from netspout_core.authentic_scenario_packs import run_scenario_pack
from netspout_core.log_engine import SplunkLogEngine
from netspout_core.models import Node
from netspout_core.universe_batch1_engine import UniverseBatch1Engine as E

DEV = Node(id='ub1-test', name='ub1-test', ip_address='192.0.2.10')


def read(path):
    return json.loads((ROOT / path).read_text())


def test_supported_families_and_scenario_contract():
    registry = read('catalog/universe_batch1.json')
    events = run_scenario_pack('ub1_ot_proxy_host_hunt', 'ub1-recovery-test')
    assert len(events) == sum(s['event_family_count'] for s in registry['sources']) == 7
    assert {e.sourcetype for e in events} == {s['splunk_sourcetype'] for s in registry['sources']}
    assert {e.netspout_phase for e in events} == {'BASELINE', 'FAULT', 'PROPAGATE', 'VALIDATE'}
    for event in events:
        assert event.netspout_run_id == 'ub1-recovery-test'
        assert 'ub1-recovery-test' not in event.raw_log
        assert 'netspout_' not in event.raw_log
    assert registry['counts_summary']['scenario_packs'] == 1


@pytest.mark.parametrize('family', E.DOCKER_EVENTS_FAMILIES)
def test_docker_grammar_and_container_identity(family):
    raw = E.format_docker_events_log(DEV, family).raw_log
    assert re.match(r'^\d{4}-.*\.\d{9}\+00:00 (container create|network connect) [a-f0-9]{64} \(', raw)
    if family == 'network_connect':
        container = E.format_docker_events_log(DEV, 'container_lifecycle').raw_log.split()[3]
        assert f'container={container[:4]}...{container[-4:]}' in raw


@pytest.mark.parametrize('family', E.WAZUH_FAMILIES)
def test_wazuh_current_header_matches_epoch(family):
    raw = E.format_wazuh_alert_log(DEV, family).raw_log
    epoch = int(raw.split()[2].split('.')[0])
    assert raw.splitlines()[1].startswith(datetime.fromtimestamp(epoch, timezone.utc).strftime('%Y %b %d %H:%M:%S'))
    if family == 'rootcheck_hidden_file':
        assert "File '/dev/.hidden' present on /dev." in raw


@pytest.mark.parametrize('family', E.PROXYSG_FAMILIES)
def test_proxy_positional_shape(family):
    import shlex
    fixture = (ROOT / 'catalog/raw_reference/universe_batch1/bluecoat_proxysg_access_file__head.bin').read_text()
    raw = E.format_proxysg_access_log(DEV, family, '192.0.2.1').raw_log
    assert len(shlex.split(raw)) == len(shlex.split(fixture))
    assert ('TCP_DENIED' in raw) == (family == 'proxy_denied')


def test_nozomi_documented_type_and_endpoints():
    raw = json.loads(E.format_nozomi_alert_log(DEV, 'ot_ids_program_change', src_ip='192.0.2.1', dest_ip='192.0.2.2').raw_log)
    fixture = read('catalog/raw_reference/universe_batch1/nozomi_universal_alert__head.bin')
    assert raw.keys() == fixture.keys()
    assert raw['type_id'] == fixture['type_id'] == 'SIGN:PROGRAM:CHANGE'
    assert raw['ip_src'] == raw['id_src'] == raw['properties']['from_id'] == '192.0.2.1'
    assert raw['ip_dst'] == raw['id_dst'] == raw['properties']['to_id'] == '192.0.2.2'
    assert 'tcp port 58679 and tcp port 44818' in raw['bpf_filter']


@pytest.mark.parametrize('method,family', [('format_docker_events_log', 'volume_event'), ('format_nozomi_alert_log', 'ot_ids_threat_actor')])
def test_unsupported_families_are_blocked(method, family):
    with pytest.raises(ValueError):
        getattr(E, method)(DEV, family)


def test_provenance_hashes_and_evidence_categories():
    refs = [r for r in read('catalog/raw_reference/provenance.json')['references'] if r.get('batch') == 'universe_batch1']
    assert len(refs) == 4
    for ref in refs:
        data = (ROOT / ref['raw_reference_file']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == ref['fetched_sha256']
        assert len(data) == ref['fetched_bytes']
    registry = read('catalog/universe_batch1.json')
    assert registry['ta_parser_verification']['verified_sourcetypes'] == 0
    assert registry['detection_validation']['verified_detections'] == 0
    assert registry['live_verification']['status'] == 'HISTORICAL_PASS_PRE_RECOVERY'
    live = read('catalog/universe_batch1_live_raw_equality_results.json')
    assert live['passes'] == len(live['raw_equality']) == 9
    assert all(e['verdict'] == 'PASS' for e in live['raw_equality'])


@pytest.mark.parametrize('target', ['src', 'backend', 'netspout/bin'])
def test_runtime_import_and_bindings_in_fresh_process(target):
    package = 'app' if target == 'backend' else 'netspout_core'
    code = f'''import sys; sys.path.insert(0, {str(ROOT / target)!r})
from {package}.log_engine import SplunkLogEngine
from {package}.authentic_scenario_packs import run_scenario_pack
assert len(SplunkLogEngine.UNIVERSE_BATCH1_SOURCE_SOURCETYPES) == 4
assert len(run_scenario_pack("ub1_ot_proxy_host_hunt", "packaging-test")) == 7
'''
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stderr
