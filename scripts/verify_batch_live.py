"""Live verification of a native-generator batch (--batch 5|6) against a local Splunk lab (reads the git-ignored tests/lab/phase4e/.env.lab).

1. RAW equality: every family is posted once over HEC; the indexed _raw must equal the submitted bytes.
2. Product path: each scenario pack is run through the backend API (/api/generate/scenario-pack, dispatching to the
   Connection Center destination) and independent splunkd searches must count the expected events per phase.
No TA is installed or claimed; this proves delivery and byte fidelity, not parsing or detection. Writes
catalog/universe_batch<N>_live_raw_equality_results.json (no credentials). Usage: verify_batch_live.py --batch N [--backend URL]
"""
import argparse
import base64
import hashlib
import json
import ssl
import sys
import time
import urllib.parse
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from netspout_core.models import Node, NodeType
import importlib

ENV = dict(l.strip().split('=', 1) for l in (ROOT / 'tests/lab/phase4e/.env.lab').read_text().splitlines() if '=' in l)
CTX = ssl._create_unverified_context()  # isolated loopback lab with a self-signed certificate
INDEX = 'idx_network_ops'
SOURCE = None


def splunk(path, data=None, method=None):
    req = urllib.request.Request('https://127.0.0.1:%s%s' % (ENV['LAB_MGMT_PORT'], path),
                                 data=urllib.parse.urlencode(data).encode() if data else None, method=method)
    req.add_header('Authorization', 'Basic ' + base64.b64encode(('admin:' + ENV['LAB_SPLUNK_PASSWORD']).encode()).decode())
    return urllib.request.urlopen(req, context=CTX, timeout=60).read().decode()


def search(spl, earliest='-30m'):
    out = splunk('/services/search/jobs/export', {'search': spl, 'output_mode': 'json', 'earliest_time': earliest, 'preview': 'false'})
    return [json.loads(l)['result'] for l in out.splitlines() if '"result"' in l]


def hec(event):
    req = urllib.request.Request('https://127.0.0.1:%s/services/collector/event' % ENV['LAB_HEC_PORT'], json.dumps(event).encode(),
                                 {'Authorization': 'Splunk ' + ENV['LAB_HEC_TOKEN'], 'Content-Type': 'application/json'})
    body = json.loads(urllib.request.urlopen(req, context=CTX, timeout=30).read())
    if body.get('code') != 0:
        raise RuntimeError('HEC rejected event')


def backend(base, path, body=None):
    req = urllib.request.Request(base + path, json.dumps(body).encode() if body is not None else None, {'Content-Type': 'application/json'})
    return json.loads(urllib.request.urlopen(req, timeout=120).read())


def raw_equality(run_id, reg, fmt):
    dev = Node(id='ub5-live', name='edge.example.test', type=NodeType.SWITCH, ip_address='10.201.48.119')
    posted = []
    for s in reg['sources']:
        for f in s['families']:
            e = fmt(dev, s['splunk_sourcetype'], f['id'], when=datetime.now(timezone.utc))
            event_id = '%s-%s-%s' % (run_id, s['batch_source_id'], f['id'])
            hec({'event': e.raw_log, 'sourcetype': s['splunk_sourcetype'], 'index': INDEX, 'source': SOURCE, 'host': dev.name,
                 'fields': {'netspout_event_id': event_id, 'netspout_run_id': run_id}})
            posted.append((event_id, s['splunk_sourcetype'], e.raw_log))
    rows = []
    for _ in range(15):
        rows = search('search index=%s source="%s" netspout_run_id="%s" | table _raw sourcetype netspout_event_id' % (INDEX, SOURCE, run_id))
        if len(rows) >= len(posted):
            break
        time.sleep(3)
    checks = []
    for event_id, st, raw in posted:
        match = [r for r in rows if r['netspout_event_id'] == event_id]
        got = match[0]['_raw'].encode() if len(match) == 1 else b''
        ok = len(match) == 1 and got == raw.encode() and match[0]['sourcetype'] == st
        checks.append({'label': event_id.split(run_id + '-')[1], 'sourcetype': st, 'matches': len(match), 'verdict': 'PASS' if ok else 'FAIL',
                       'submitted_bytes': len(raw.encode()), 'indexed_bytes': len(got), 'submitted_sha256': hashlib.sha256(raw.encode()).hexdigest(),
                       'indexed_sha256': hashlib.sha256(got).hexdigest(), 'correlation_leak': run_id in raw or 'netspout_' in raw})
    return checks, len(rows)


def scenarios(base, reg):
    results = []
    for sid, steps in reg['scenarios'].items():
        run = backend(base, '/api/generate/scenario-pack', {'scenario_id': sid, 'dispatch': True, 'index': INDEX})
        run_id = run['run_id']
        expected = {}
        for st in steps:
            expected[st['phase']] = expected.get(st['phase'], 0) + 1
        by_phase = {}
        for _ in range(12):
            time.sleep(3)
            by_phase = {r['netspout_phase']: int(r['count']) for r in search('search index=%s netspout_run_id="%s" | stats count by netspout_phase' % (INDEX, run_id))}
            if sum(by_phase.values()) >= sum(expected.values()):
                break
        sent = sum(1 for d in run['dispatch_results'] if d.get('hec', {}).get('success'))
        raws = search('search index=%s netspout_run_id="%s" | table _raw sourcetype' % (INDEX, run_id))
        leak = any(run_id in r['_raw'] or 'netspout_' in r['_raw'] for r in raws)
        results.append({'scenario_id': sid, 'run_id': run_id, 'events_generated': run['count_generated'], 'hec_accepted': sent,
                        'independent_count_by_phase': by_phase, 'expected_by_phase': expected,
                        'distinct_sourcetypes_indexed': sorted({r['sourcetype'] for r in raws}), 'correlation_leak_in_raw': leak,
                        'verdict': 'PASS' if by_phase == expected and sent == run['count_generated'] and not leak else 'FAIL'})
    return results


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--batch', required=True, choices=['5', '6'])
    ap.add_argument('--backend', default='http://127.0.0.1:8081')
    a = ap.parse_args()
    ap_batch = a.batch
    mod = importlib.import_module('netspout_core.universe_batch%s_engine' % ap_batch)
    reg = mod.batch_registry()
    fmt = getattr(getattr(mod, 'UniverseBatch%sEngine' % ap_batch), 'format_universe_batch%s_log' % ap_batch)
    SOURCE = 'netspout-ub%s-live' % ap_batch
    run_id = 'pf-ub%s-live-' % ap_batch + str(uuid.uuid4())
    checks, indexed = raw_equality(run_id, reg, fmt)
    scen = scenarios(a.backend, reg)
    result = {'run_id': run_id, 'source': SOURCE, 'index': INDEX, 'posted': len(checks), 'indexed_rows': indexed, 'post_failures': [],
              'raw_equality': checks, 'passes': sum(c['verdict'] == 'PASS' and not c['correlation_leak'] for c in checks),
              'scenario_runs': scen, 'ta_parser_checks_performed': 0, 'detection_checks_performed': 0, 'configuration_changes': 0}
    (ROOT / 'catalog' / ('universe_batch%s_live_raw_equality_results.json' % ap_batch)).write_text(json.dumps(result, indent=1) + '\n')
    print(json.dumps({'raw_equality_pass': '%d/%d' % (result['passes'], len(checks)), 'scenarios': [(s['scenario_id'], s['verdict'], s['independent_count_by_phase']) for s in scen]}, indent=1))
