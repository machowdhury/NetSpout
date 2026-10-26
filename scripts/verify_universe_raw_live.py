"""Bounded HEC RAW-byte verification in the existing isolated lab; no config writes.

Credentials stay inside the container. Posts each event once; polls at most 12
searches. Does not install TAs or claim parser/detection validation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

CONTAINER_CODE = r'''
import os, json, urllib.request, urllib.parse, ssl, base64, time, hashlib
payload = json.loads(PAYLOAD_JSON)
ctx = ssl._create_unverified_context()  # isolated localhost Splunk self-signed TLS
password = os.environ.get('SPLUNK_PASSWORD')
if not password:
    raise RuntimeError('Lab credential unavailable')
auth = 'Basic ' + base64.b64encode(('admin:' + password).encode()).decode()
def request(path, data=None, token=None):
    base = 'https://127.0.0.1:' + ('8088' if token else '8089')
    headers = {'Authorization': 'Splunk ' + token if token else auth}
    if data is not None:
        headers['Content-Type'] = 'application/json' if token else 'application/x-www-form-urlencoded'
    req = urllib.request.Request(base + path, data=data, headers=headers)
    with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
        return response.read().decode()
inputs = json.loads(request('/services/data/inputs/http?output_mode=json&count=100'))
entries = [e for e in inputs.get('entry', []) if e['name'].removeprefix('http://') == 'pf-ta-ise-val']
if len(entries) != 1:
    raise RuntimeError('Existing isolated HEC input not found; no input will be created')
config = entries[0]['content']
if str(config.get('disabled', '0')).lower() not in ('0', 'false'):
    raise RuntimeError('Existing isolated HEC input disabled')
if config.get('index') != 'idx_ta_ise_test':
    raise RuntimeError('Existing token default index is not the isolated test index')
token = config.get('token')
if not token:
    raise RuntimeError('Existing isolated HEC token unavailable')
apps = json.loads(request('/services/apps/local?output_mode=json&count=200'))
installed = [{'id': e['name'], 'version': e.get('content', {}).get('version')} for e in apps.get('entry', []) if e['name'].startswith(('TA', 'Splunk_TA'))]
posted = []
for event in payload['events']:
    response = json.loads(request('/services/collector/event', json.dumps(event).encode(), token))
    if response.get('code') != 0:
        raise RuntimeError('HEC rejected bounded event; no automatic repost')
    posted.append(event)
query = 'search index=idx_ta_ise_test earliest=-15m source="' + payload['source'] + '" | table _raw sourcetype netspout_event_id'
rows = []
for attempt in range(12):
    body = urllib.parse.urlencode({'search': query, 'output_mode': 'json', 'preview': 'false'}).encode()
    output = request('/services/search/jobs/export', body)
    rows = [j['result'] for line in output.splitlines() if line.strip() for j in [json.loads(line)] if 'result' in j]
    if len(rows) >= len(posted):
        break
    time.sleep(2)
checks = []
for event in posted:
    event_id = event['fields']['netspout_event_id']
    matches = [r for r in rows if r.get('netspout_event_id') == event_id]
    raw = event['event'].encode('utf-8')
    indexed = matches[0].get('_raw', '').encode('utf-8') if len(matches) == 1 else b''
    ok = len(matches) == 1 and indexed == raw and matches[0].get('sourcetype') == event['sourcetype']
    checks.append({'label': event_id, 'sourcetype': event['sourcetype'], 'matches': len(matches),
                   'verdict': 'PASS' if ok else 'FAIL', 'submitted_bytes': len(raw),
                   'indexed_bytes': len(indexed), 'submitted_sha256': hashlib.sha256(raw).hexdigest(),
                   'indexed_sha256': hashlib.sha256(indexed).hexdigest(),
                   'correlation_leak': payload['run_id'] in indexed.decode('utf-8') or 'netspout_' in indexed.decode('utf-8')})
result = {'run_id': payload['run_id'], 'source': payload['source'], 'index': 'idx_ta_ise_test',
          'posted': len(posted), 'indexed_rows': len(rows), 'post_failures': [], 'raw_equality': checks,
          'passes': sum(c['verdict'] == 'PASS' and not c['correlation_leak'] for c in checks),
          'distinct_sourcetypes': sorted({e['sourcetype'] for e in posted}),
          'installed_ta_inventory': installed, 'ta_parser_checks_performed': 0,
          'detection_checks_performed': 0, 'search_attempts': attempt + 1,
          'query': query, 'configuration_changes': 0}
print(json.dumps(result))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--batch', choices=['1', '2', '3'], required=True)
    args = parser.parse_args()
    from netspout_core.authentic_scenario_packs import run_scenario_pack
    run_id = f'pf-ub{args.batch}-current-{uuid.uuid4()}'
    if args.batch == '1':
        scenario_ids = ['ub1_ot_proxy_host_hunt']
        module = ROOT / 'src/netspout_core/universe_batch1_engine.py'
    elif args.batch == '3':
        from netspout_core.universe_batch3_engine import BATCH3_SCENARIO_IDS
        scenario_ids = BATCH3_SCENARIO_IDS
        module = ROOT / 'src/netspout_core/universe_batch3_engine.py'
    else:
        from netspout_core.universe_batch2_engine import BATCH2_SCENARIO_IDS
        scenario_ids = BATCH2_SCENARIO_IDS
        module = ROOT / 'src/netspout_core/universe_batch2_engine.py'
    logs = [event for sid in scenario_ids for event in run_scenario_pack(sid, run_id)]
    if not 0 < len(logs) <= 60:
        raise ValueError('Live event bound exceeded')
    source = f'pulseforge:universe:raw-check:{run_id}'
    events = []
    for i, event in enumerate(logs):
        fields = {k: v for k, v in event.model_dump().items() if k.startswith('netspout_') and v is not None}
        if args.batch != '3':
            fields['netspout_event_id'] = f'ub{args.batch}-{i:03d}'
        events.append(dict(event=event.raw_log, sourcetype=event.sourcetype,
                           host=event.device_id, source=source, index='idx_ta_ise_test', fields=fields))
    payload = dict(run_id=run_id, source=source, events=events)
    program = ('PAYLOAD_JSON = ' + repr(json.dumps(payload)) + '\nimport traceback\ntry:\n'
               + '\n'.join('    ' + line for line in CONTAINER_CODE.splitlines())
               + '\nexcept Exception as exc:\n    print(json.dumps({"error_type": type(exc).__name__, "http_status": getattr(exc, "code", None), "line": traceback.extract_tb(exc.__traceback__)[-1].lineno, "stage": str(exc) if isinstance(exc, RuntimeError) else "request-or-decode"}))\n')
    proc = subprocess.run(['docker', 'exec', '-i', 'pf-native-lab', '/usr/bin/python3', '-'],
                          input=program, text=True, capture_output=True, timeout=240)
    if proc.returncode:
        # Never echo container stderr: HTTP failures could contain credential material.
        raise RuntimeError(f'Isolated lab verification failed (exit {proc.returncode}); no credentials logged')
    result = json.loads(proc.stdout)
    if 'error_type' in result:
        raise RuntimeError('Sanitized lab diagnostic: ' + json.dumps(result))
    result['engine_sha256'] = hashlib.sha256(module.read_bytes()).hexdigest()
    result['generator_module'] = str(module.relative_to(ROOT))
    result['scenario_module_sha256'] = hashlib.sha256((ROOT / 'src/netspout_core/authentic_scenario_packs.py').read_bytes()).hexdigest()
    result['method'] = 'Current host-generated UTF-8 bytes, existing isolated HEC input, exact indexed byte and sourcetype comparison'
    dest = ROOT / f'catalog/universe_batch{args.batch}_current_raw_equality_results.json'
    dest.write_text(json.dumps(result, indent=2) + '\n')
    evidence_batch = '3' if args.batch == '3' else '2'
    evidence = ROOT / f'docs/verification/universe_batch{evidence_batch}/batch{args.batch}_submitted_events.json'
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(json.dumps(payload, indent=2) + '\n')
    print(json.dumps({k: result[k] for k in ['run_id', 'posted', 'indexed_rows', 'passes', 'distinct_sourcetypes', 'search_attempts']}))
    return 0 if result['passes'] == len(events) and result['indexed_rows'] == len(events) else 1

if __name__ == '__main__':
    raise SystemExit(main())
