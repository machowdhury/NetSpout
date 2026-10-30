"""Scenario Dashboard Studio views: structure, real-data-only rule, token binding, maturity honesty, Explorer link."""
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT / 'src'), str(ROOT / 'backend')):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from fastapi.testclient import TestClient

from app import main
from netspout_core import replay_packs as rp

PACKS = rp.packs()
VIEWS = ROOT / 'netspout/default/data/ui/views'
EV = ROOT / 'docs/verification/evidence/dashboards'
LEVELS = ['DASHBOARD_SPECIFIED', 'DASHBOARD_IMPLEMENTED', 'DASHBOARD_DATA_VALIDATED', 'DASHBOARD_VISUALLY_VERIFIED']


def spec(pid):
    root = ET.parse(VIEWS / f'pf_{pid}.xml').getroot()
    return root, json.loads(root.find('definition').text)


@pytest.mark.parametrize('pack', PACKS, ids=[p['id'] for p in PACKS])
def test_view_is_a_dashboard_studio_v2_definition_built_only_from_searches_over_the_scenario(pack):
    root, d = spec(pack['id'])
    assert root.tag == 'dashboard' and root.get('version') == '2'
    for k in ('inputs', 'dataSources', 'visualizations', 'layout'):
        assert d[k]
    queries = [v['options']['query'] for v in d['dataSources'].values()]
    assert all(pack['id'] in q for q in queries if 'netspout_scenario_id' in q) and any('netspout_scenario_id' in q for q in queries)
    for key, v in d['visualizations'].items():
        if v['type'] == 'splunk.markdown':
            md = v['options']['markdown']
            assert '<' not in md.replace('<br>', '') and not re.search(r'\|\s*---', md)          # markdown viz renders neither HTML nor tables
        else:
            assert v['dataSources']['primary'] in d['dataSources'], key                         # every chart/KPI/table is bound to a search: nothing hardcoded
    kpis = [v for v in d['visualizations'].values() if v['type'] == 'splunk.singlevalue']
    assert len(kpis) == 6 and all(re.search(r'stats', d['dataSources'][k['dataSources']['primary']]['options']['query']) for k in kpis)
    assert all(not re.search(r'\| *(eval|makeresults)[^|]*\bvalue *= *\d+\b', q) for q in queries)   # no literal KPI values
    bound = {i['options']['token'] for i in d['inputs'].values()}
    used = set(re.findall(r'\$([A-Za-z_]\w*)', json.dumps(d))) - {'global_time', 'row', 'click'}
    assert used <= bound, used - bound
    assert {'run_tok', 'global_time', 'index_tok'} <= bound


def test_security_dashboards_state_detection_status_and_never_claim_a_verified_detection():
    for p in PACKS:
        if (p.get('kind') or 'security') != 'security':
            continue
        text = json.dumps(spec(p['id'])[1])
        assert 'Detection status: **NOT VERIFIED**' in text and 'Severity:** not asserted' in text and 'Original analytics (Splunk Security Content)' in text
    ops = [p for p in PACKS if p.get('kind') == 'operational']
    assert len(ops) == 9 and all('Before / during / after' in json.dumps(spec(p['id'])[1]) and 'Recovery / validation evidence' in json.dumps(spec(p['id'])[1]) for p in ops)


def test_original_analytic_links_come_from_exact_dataset_matches_only():
    text = json.dumps(spec('ind_bank_account_takeover_resilience')[1])
    assert 'research.splunk.com/' in text and 'Azure Automation Runbook Created' in text
    assert 'No detection in the pinned Security Content catalog lists a dataset' in json.dumps(spec('ind_bank_payments_edge_defense')[1])


def test_maturity_is_assembled_from_evidence_and_visual_claims_need_an_inspected_screenshot():
    m = json.loads((EV / 'dashboard_maturity.json').read_text())['dashboards']
    insp = json.loads((EV / 'visual_inspection.json').read_text())['inspected']
    data = json.loads((EV / 'data_validation.json').read_text())['dashboards']
    inst = json.loads((EV / 'install.json').read_text())['views']
    assert set(m) == {p['id'] for p in PACKS} and all(v['maturity'] in LEVELS for v in m.values())
    for pid, v in m.items():
        if v['maturity'] == 'DASHBOARD_VISUALLY_VERIFIED':
            assert pid in insp and (EV / 'screens' / f'{pid}.jpg').is_file() and v['data_validated'] and v['browser_render_checks_pass']
        if v['maturity'] in LEVELS[2:]:
            assert data[pid]['pass'] and not data[pid]['datasources_empty'] and all(k['equal'] for k in data[pid]['kpi'].values()) and not data[pid]['tokens']['unbound']
        if v['maturity'] != 'DASHBOARD_SPECIFIED':
            assert inst['pf_' + pid]['matches_source']


def test_explorer_links_each_replay_pack_to_its_view_with_the_session_as_run_context():
    client = TestClient(main.app)
    items = client.get('/api/explorer/entries?kind=operational&q=rp_&limit=100').json()['items'] + client.get('/api/explorer/entries?kind=operational&q=ind_&limit=100').json()['items']
    packs = list({e['scenario_id']: e for e in items if e['engine'] == 'replay_pack'}.values())
    assert len(packs) == len(PACKS)
    m = json.loads((EV / 'dashboard_maturity.json').read_text())['dashboards']
    for e in packs:
        assert e['dashboard']['splunk_view'] == 'pf_' + e['scenario_id'] and e['dashboard']['dashboard_maturity'] == m[e['scenario_id']]['maturity']
        step = {s['step']: s for s in e['workflow']}['DASHBOARD']
        assert step['available'] and step['endpoint']['path'] == f"/app/netspout/pf_{e['scenario_id']}?form.run_tok={{session_id}}"
        assert not e['dashboard_verified']                        # the legacy DASHBOARD_READY gate is not claimed
