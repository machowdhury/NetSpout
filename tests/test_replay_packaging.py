"""The deployable Splunk app must carry everything replay needs: sample recordings, registries, engine modules, dashboard views and nav."""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / 'netspout'


def test_every_registered_recording_ships_inside_the_app_and_matches_the_hash():
    import hashlib
    reg = json.loads((ROOT / 'catalog/replay_sources.json').read_text())['sources']
    for s in reg:
        shipped = APP / s['file']
        assert shipped.is_file(), s['file']
        assert hashlib.sha256(shipped.read_bytes()).hexdigest() == s['sha256']


def test_packaged_replay_service_loads_samples_without_the_repository_checkout(tmp_path):
    """Copy only the app tree (as installed) and load every registered recording through the packaged replay_service."""
    import shutil
    import subprocess
    shutil.copytree(APP, tmp_path / 'netspout', ignore=shutil.ignore_patterns('__pycache__', 'dist', 'local'))
    code = (
        "import sys; sys.path.insert(0, %r)\n"
        "from netspout_core import replay_service as rs\n"
        "from netspout_core.sample_replay import build_timeline, TimestampRule\n"
        "n = 0\n"
        "for s in rs.sources():\n"
        "    tl = build_timeline(rs.source_text(s), s['format'], TimestampRule(**s['timestamp_rule']))\n"
        "    assert len(tl.items) == s['records'], s['id']\n"
        "    n += 1\n"
        "print(n)\n" % str(tmp_path / 'netspout' / 'bin'))
    out = subprocess.run([sys.executable, '-I', '-c', code], capture_output=True, text=True, cwd=tmp_path)
    assert out.returncode == 0, out.stderr[-600:]
    assert int(out.stdout.strip()) == len(json.loads((ROOT / 'catalog/replay_sources.json').read_text())['sources'])


def test_app_ships_engine_modules_registries_views_and_navigation():
    for m in ('sample_replay.py', 'replay_service.py', 'replay_packs.py'):
        assert (APP / 'bin' / m).is_file() and (APP / 'bin' / 'netspout_core' / m).is_file()
    for c in ('replay_sources.json', 'replay_packs.json'):
        assert (APP / 'catalog' / c).is_file()
    maturity = json.loads((ROOT / 'docs/verification/evidence/dashboards/dashboard_maturity.json').read_text())['dashboards']
    for pid in maturity:
        assert (APP / 'default/data/ui/views' / f'pf_{pid}.xml').is_file(), pid
    nav = (APP / 'default/data/ui/nav/default.xml').read_text()
    assert all('name="pf_%s"' % pid in nav for pid in maturity)   # every dashboard has an explicit nav entry


def test_app_tree_contains_no_credentials():
    bad = [str(p) for p in APP.rglob('*') if p.is_file() and (p.name in ('.env', '.env.lab') or p.suffix in ('.pem', '.key'))]
    assert not bad
