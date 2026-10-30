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
sys.path.insert(0, str(ROOT / 'scripts'))
import build_scenario_dashboards as gen

PACKS = rp.packs()
SOURCES = gen.sources()
VIEWS = ROOT / 'netspout/default/data/ui/views'
EV = ROOT / 'docs/verification/evidence/dashboards'
LEVELS = ['DASHBOARD_SPECIFIED', 'DASHBOARD_IMPLEMENTED', 'DASHBOARD_DATA_VALIDATED', 'DASHBOARD_VISUALLY_VERIFIED']


def spec(pid):
    root = ET.parse(VIEWS / f'pf_{pid}.xml').getroot()
    return root, json.loads(root.find('definition').text)


@pytest.mark.parametrize('src', SOURCES, ids=[x['id'] for x in SOURCES])
def test_view_is_a_dashboard_studio_v2_definition_built_only_from_searches_over_the_scenario(src):
    root, d = spec(src['id'])
    assert root.tag == 'dashboard' and root.get('version') == '2'
    for k in ('inputs', 'dataSources', 'visualizations', 'layout'):
        assert d[k]
    queries = [v['options']['query'] for v in d['dataSources'].values()]
    assert any('netspout_scenario_id="%s"' % src['scenario_value'] in q and src['key_field'] in q for q in queries)
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
    assert {'run_tok', 'global_time', 'index_tok'} <= bound and (('mindex_tok' in bound) == src['metric'])
    labels = [t['label'] for t in d['layout']['tabs']['items']]
    assert labels == (['NOC', 'Engineer', 'Evidence'] if src['kind'] == 'operational' else ['Overview', 'Investigation', 'Evidence'])
    assert all(t['layoutId'] in d['layout']['layoutDefinitions'] for t in d['layout']['tabs']['items'])


def test_incident_dashboards_use_only_real_fields_and_mstats_with_the_metric_index():
    inc = [x for x in SOURCES if x['family'] == 'incident_pack']
    assert len(inc) == 37
    for x in inc:
        text = json.dumps(spec(x['id'])[1])
        assert '| mstats' in text and 'metric_name=*' in text and 'netspout_site_id' in text and 'min(severity)' in text
    for x in SOURCES:
        if x['family'] != 'incident_pack':
            t = json.dumps(spec(x['id'])[1])
            assert 'mstats' not in t and 'netspout_site_id' not in t and 'min(severity)' not in t   # no sites, severity or metrics asserted where the telemetry has none


def test_security_dashboards_state_detection_status_and_never_claim_a_verified_detection():
    sec = [x for x in SOURCES if x['kind'] == 'security']
    assert len(sec) == 37
    for x in sec:
        text = json.dumps(spec(x['id'])[1])
        assert 'Detection status: **NOT VERIFIED**' in text and 'Severity:** not asserted' in text and 'Original analytics (Splunk Security Content)' in text
    ops = [x for x in SOURCES if x['kind'] == 'operational']
    assert len(ops) == 59 and all('Before / during / after' in json.dumps(spec(x['id'])[1]) and 'Recovery / validation evidence' in json.dumps(spec(x['id'])[1]) for x in ops)


def test_palette_follows_the_figma_v2_tokens_and_perspective_tabs_exist():
    text = (VIEWS / 'pf_ind_telco_change_induced_outage.xml').read_text()
    assert '#17191b' in text and '#d4764f' in text and '#1' + '9b5c4' not in text           # dark canvas + terracotta family, not the earlier teal
    assert 'NOC' in text and 'Engineer' in text and 'Evidence' in text


def test_every_scenario_pack_the_explorer_lists_as_runnable_is_accepted_by_the_generation_route():
    from netspout_core.authentic_scenario_packs import SCENARIO_PACK_IDS
    from netspout_core.generator_modes import generator_service
    for pid in SCENARIO_PACK_IDS:
        r = generator_service.generate_universe_scenario(pid, run_id='t-' + pid)
        assert r['count_generated'] > 0 and r['run_id'] == 't-' + pid


def test_original_analytic_links_come_from_exact_dataset_matches_only():
    text = json.dumps(spec('ind_bank_account_takeover_resilience')[1])
    assert 'research.splunk.com/' in text and 'Azure Automation Runbook Created' in text
    assert 'No detection in the pinned Security Content catalog lists a dataset' in json.dumps(spec('ind_bank_payments_edge_defense')[1])


def test_maturity_is_assembled_from_evidence_and_visual_claims_need_an_inspected_screenshot():
    m = json.loads((EV / 'dashboard_maturity.json').read_text())['dashboards']
    insp = json.loads((EV / 'visual_inspection.json').read_text())['inspected']
    data = json.loads((EV / 'data_validation.json').read_text())['dashboards']
    inst = json.loads((EV / 'install.json').read_text())['views']
    assert set(m) == {x['id'] for x in SOURCES} and all(v['maturity'] in LEVELS for v in m.values())
    for pid, v in m.items():
        if v['maturity'] == 'DASHBOARD_VISUALLY_VERIFIED':
            assert pid in insp and list((EV / 'screens').glob(f'{pid}__*.jpg')) and v['data_validated'] and v['browser_render_checks_pass']
        if v['maturity'] in LEVELS[2:]:
            assert data[pid]['pass'] and not data[pid]['datasources_empty'] and all(k['equal'] for k in data[pid]['kpi'].values()) and not data[pid]['tokens']['unbound']
        if v['maturity'] != 'DASHBOARD_SPECIFIED':
            assert inst['pf_' + pid]['matches_source']


def test_explorer_links_every_scenario_with_a_view_to_it_with_the_run_as_context():
    client = TestClient(main.app)
    m = json.loads((EV / 'dashboard_maturity.json').read_text())['dashboards']
    ex = main._explorer()
    linked = [e for e in ex.all_entries() if e['kind'] == 'operational' and e.get('dashboard') and e['dashboard'].get('scale')]
    assert {e['scenario_id'] for e in linked} == {x['id'] for x in SOURCES if x['kind'] == 'operational'} | {x['id'] for x in SOURCES if x['kind'] == 'security' and x['family'] == 'replay'} | \
        {x['id'] for x in SOURCES if x['kind'] == 'security' and x['family'] == 'native_pack'}
    for e in linked:
        assert e['dashboard']['splunk_view'] == 'pf_' + e['scenario_id'] and e['dashboard']['dashboard_maturity'] == m[e['scenario_id']]['maturity']
        step = {s_['step']: s_ for s_ in e['workflow']}['DASHBOARD']
        assert step['available'] and step['endpoint']['path'] == f"/app/netspout/pf_{e['scenario_id']}?form.run_tok={{run_id}}"
        assert not e['dashboard_verified']                        # the legacy DASHBOARD_READY gate is not claimed
