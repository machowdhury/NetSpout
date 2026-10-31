"""The Splunk Cloud edition must stay dashboards-only: nothing AppInspect's cloud rules reject (code, inputs, indexes, REST handlers, custom conf)."""
import json
import re
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_cloud_edition_contains_only_dashboards_navigation_and_metadata():
    with tarfile.open(ROOT / 'netspout_cloud.spl', 'r:gz') as tar:
        names = [m.name for m in tar.getmembers() if m.isfile()]
        app_conf = tar.extractfile('netspout/default/app.conf').read().decode()
    forbidden = [n for n in names if n.endswith(('.py', '.js', '.sh')) or any(x in n for x in ('inputs.conf', 'indexes.conf', 'restmap.conf', 'props.conf', 'transforms.conf', 'eventgen', '/bin/', '/lib/'))]
    assert not forbidden, forbidden
    views = [n for n in names if re.search(r'default/data/ui/views/pf_.*\.xml$', n)]
    maturity = json.loads((ROOT / 'docs/verification/evidence/dashboards/dashboard_maturity.json').read_text())['dashboards']
    assert len(views) == len(maturity) == len(list((ROOT / 'netspout/default/data/ui/views').glob('pf_*.xml')))
    assert '[id]' in app_conf and 'is_configured' not in app_conf


def test_cloud_edition_appinspect_evidence_is_clean():
    d = json.loads((ROOT / 'docs/verification/evidence/appinspect/cloud_edition.json').read_text())
    assert d['summary']['failure'] == d['summary']['error'] == d['summary']['warning'] == 0 and d['summary']['success'] > 50
