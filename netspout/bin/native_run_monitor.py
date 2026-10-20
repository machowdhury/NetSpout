"""Bounded native run records in the existing status snapshot (no credentials)."""
import copy
import json
import math
import os
import re
import time
import uuid
from urllib.parse import quote, urlsplit

COUNTERS = ('generated', 'attempted', 'accepted', 'failed', 'unknown')
STATES = {'NOT_CHECKED', 'VERIFIED', 'NOT_FOUND', 'INCONCLUSIVE', 'ERROR'}
INDEX = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_-]{0,127}')
TTL = 7 * 86400
MAX_WINDOW = 86400


def api():
    import datablaster_rest
    return datablaster_rest


def valid(record):
    try:
        return (isinstance(record, dict) and str(uuid.UUID(record['run_id'])) == record['run_id']
                and record['execution_state'] in ('ACTIVE', 'COMPLETED', 'INTERRUPTED')
                and type(record['started_at']) in (int, float) and math.isfinite(record['started_at'])
                and (record['ended_at'] is None or (type(record['ended_at']) in (int, float)
                     and math.isfinite(record['ended_at']) and record['ended_at'] >= record['started_at']))
                and (record['execution_state'] == 'ACTIVE') == (record['ended_at'] is None)
                and isinstance(record['indexes'], list) and len(record['indexes']) <= 100
                and all(isinstance(i, str) and INDEX.fullmatch(i) for i in record['indexes'])
                and record['classification'] in ('LOG', 'METRIC', 'MIXED', 'UNKNOWN')
                and record['correlation'] in ('SUPPORTED', 'UNSUPPORTED')
                and isinstance(record['destination'], dict) and record['destination'].get('transport') == 'HEC'
                and isinstance(record['destination'].get('host'), str)
                and type(record['destination'].get('port')) is int
                and isinstance(record['execution'], dict) and isinstance(record['execution'].get('action'), str)
                and (record.get('pid') is None or (type(record['pid']) is int and record['pid'] > 0))
                and record['verification']['state'] in STATES
                and set(record['counters']) == set(COUNTERS)
                and all(v is None or (type(v) is int and v >= 0) for v in record['counters'].values()))
    except (KeyError, TypeError, ValueError, AttributeError):
        return False


def retain(records, now):
    usable = [r for r in records if valid(r) and r['started_at'] <= now]
    active = [r for r in usable if r['execution_state'] == 'ACTIVE']
    completed = sorted((r for r in usable if r['execution_state'] != 'ACTIVE'
                        and now - r['ended_at'] < TTL),
                       key=lambda r: (r['ended_at'], r['run_id']), reverse=True)[:100]
    return active + completed


def read_state():
    a = api()
    a.get_active_run_dir()
    try:
        state = json.loads(a._read_private_file(a.STATUS_FILE))
    except FileNotFoundError:
        return {}
    if not isinstance(state, dict) or not isinstance(state.get('native_runs', []), list):
        raise ValueError('Native run history unavailable')
    return state


def _change_lock_held(edit, now=None):
    """Internal: caller MUST hold datablaster_rest.simulation_start_lock().

    Both public and lock-held updates share this atomic read/modify/replace.
    This helper does not acquire a lock and is not a REST operation.
    """
    a = api()
    now = time.time() if now is None else now
    state = read_state()
    records = retain(state.get('native_runs', []), now)
    result = edit(records)
    state['native_runs'] = retain(records, now)
    a._write_config(a.STATUS_FILE, state)
    return copy.deepcopy(state['native_runs'] if result is records else result)


def change(edit, now=None):
    with api().simulation_start_lock():
        return _change_lock_held(edit, now)


def publish_status(metadata):
    """Called while the existing simulation lock is already held."""
    a = api()
    state = read_state()
    state.update(metadata)
    a._write_config(a.STATUS_FILE, state)


def attach(event, run_id):
    """HEC indexed log field / metric dimension; never alter vendor raw data."""
    value = copy.deepcopy(event)
    fields = value.get('fields', {})
    if not isinstance(fields, dict):
        raise ValueError('Invalid event fields')
    value['fields'] = dict(fields, netspout_run_id=run_id)
    return value


def begin(action, clean, session_key=""):
    cfg = api().get_stored_config()
    url = urlsplit(clean.get('hec') or cfg['hec_url'])
    indexes, kind = [], 'UNKNOWN'
    events = clean.get('events', [])
    if action == 'onboard_sample':
        indexes = [clean['index']]
        kind = 'METRIC' if 'metric' in clean['index'].lower() else 'LOG'
    elif action == 'blast_hec':
        scoped = []
        current_index = 'idx_network_ops'
        for event in events:
            if isinstance(event, dict):
                if 'index' in event:
                    current_index = event['index']
                    scoped.append(current_index)
            elif isinstance(event, str):
                scoped.append(current_index)
        indexes = sorted(set(scoped))
        kinds = {'METRIC' if isinstance(e, dict) and e.get('event') == 'metric' else 'LOG' for e in events}
        kind = next(iter(kinds)) if len(kinds) == 1 else 'MIXED'
    elif action == 'blast_single_device':
        device = clean.get('device_info', {})
        indexes = [device.get('index', 'idx_network_ops')]
        kind = 'METRIC' if device.get('metricsMode') or 'metric' in device.get('sourcetype', '') else 'LOG'
    if not all(isinstance(i, str) and INDEX.fullmatch(i) for i in indexes) or len(indexes) > 100:
        raise ValueError('Run index scope unavailable')
    principal = None
    try:
        response, body = api().rest.simpleRequest(api().MANAGEMENT_URL +
            '/services/authentication/current-context?output_mode=json', sessionKey=session_key, method='GET')
        candidate = json.loads(body)['entry'][0]['content'].get('username')
        if int(response.status) == 200 and isinstance(candidate, str) and len(candidate) <= 128:
            principal = candidate
    except Exception:
        pass
    record = dict(run_id=str(uuid.uuid4()), started_at=time.time(), ended_at=None,
                  execution_state='ACTIVE', execution={'action': action, 'principal': principal, 'runtime_uid': os.getuid()}, pid=None,
                  destination={'transport': 'HEC', 'host': url.hostname, 'port': url.port or 443},
                  indexes=indexes, classification=kind,
                  correlation='SUPPORTED' if action in ('blast_hec', 'onboard_sample', 'blast_single_device') else 'UNSUPPORTED',
                  counters={k: None for k in COUNTERS}, verification={'state': 'NOT_CHECKED', 'message': 'Not checked'})
    if action == 'blast_hec' and any(isinstance(e, dict) and not e.get('index') for e in events):
        record['correlation'] = 'UNSUPPORTED'
    if action == 'blast_hec':
        record['counters']['generated'] = sum(isinstance(e, (dict, str)) for e in events)
    elif action == 'blast_single_device':
        record['counters']['generated'] = 1
    return change(lambda rows: (rows.append(record), record)[1])


def _update_lock_held(run_id, edit):
    """Internal update; caller MUST already hold simulation_start_lock()."""
    def apply(rows):
        record = next((r for r in rows if r['run_id'] == run_id), None)
        if record is None:
            raise ValueError('Run unavailable')
        edit(record)
        if not valid(record):
            raise ValueError("Invalid run update")
        return record
    return _change_lock_held(apply)


def update(run_id, edit):
    with api().simulation_start_lock():
        return _update_lock_held(run_id, edit)


def finish(record, response):
    def apply(r):
        pid = response.get('pid')
        if type(pid) is int and pid > 0 and response.get('status') == 'success':
            r['pid'] = pid
        else:
            r['execution_state'] = 'COMPLETED'
            r['ended_at'] = time.time()
        for key in COUNTERS:
            value = response.get(key)
            if type(value) is int and value >= 0:
                r['counters'][key] = value
        # Older paths supply no batch acceptance evidence: keep these null.
    return update(record['run_id'], apply)


def history():
    def refresh(rows):
        for r in rows:
            if r['execution_state'] == 'ACTIVE' and r.get('pid') and not api().is_process_running(r['pid']):
                r['execution_state'] = 'COMPLETED'
                # This is an observation time, not an inferred precise exit time.
                r['ended_at'] = time.time()
        return rows
    return change(refresh)


def verification(run_id, session_key):
    rows = history()
    r = next((r for r in rows if r['run_id'] == run_id), None)
    if r is None:
        return 404, {'status': 'error', 'message': 'Run unavailable'}
    def result(state, message, count=None):
        value = {'state': state, 'message': message, 'matching_events': count}
        saved = update(run_id, lambda rec: rec.update(verification=value))
        return 200, {'status': 'success', 'run': saved}
    # A local Splunk search can only verify the local destination.
    if r['destination']['host'] not in ('127.0.0.1', 'localhost', '::1'):
        return result('INCONCLUSIVE', 'Remote destination search is unsupported')
    if r['correlation'] != 'SUPPORTED' or r['classification'] != 'LOG' or not r['indexes']:
        return result('INCONCLUSIVE', 'Indexing verification unsupported for this output path')
    now = time.time()
    end = min(r['ended_at'] or now, now)
    if end - r['started_at'] > MAX_WINDOW:
        return result('INCONCLUSIVE', 'Run exceeds the bounded verification window')
    earliest, latest = math.floor(r['started_at']), math.ceil(end) + 1
    scope = ' OR '.join('index="' + i + '"' for i in r['indexes'])
    query = ('search (' + scope + ') netspout_run_id::"' + r['run_id'] + '"'
             + ' earliest=' + str(earliest) + ' latest=' + str(latest)
             + ' | stats count by netspout_run_id')
    a = api()
    def request(path, method='GET', args=None):
        response, body = a.rest.simpleRequest(a.MANAGEMENT_URL + path, sessionKey=session_key,
            method=method, postargs=args, raiseAllErrors=False, timeout=10)
        if int(response.status) not in (200, 201):
            raise RuntimeError()
        return json.loads(body)
    try:
        cached = r.get('search_job', {})
        sid = cached.get('sid')
        if not sid:
            job = request('/services/search/jobs?output_mode=json', 'POST', {
                'search': query, 'exec_mode': 'normal', 'max_time': '10', 'auto_cancel': '60'})
            sid = job.get('sid')
            if isinstance(sid, str) and sid and len(sid) <= 256:
                update(run_id, lambda rec: rec.update(search_job={'sid': sid, 'latest': latest}))
        if not isinstance(sid, str) or not sid or len(sid) > 256:
            raise RuntimeError()
        path = '/services/search/jobs/' + quote(sid, safe='')
        status = request(path + '?output_mode=json')['entry'][0]['content']
        if status.get('isFailed') in (True, 1, '1') or status.get('dispatchState') == 'FAILED':
            return result('ERROR', 'Splunk search failed or was denied')
        if (status.get('isDone') not in (True, 1, '1') or status.get('dispatchState') != 'DONE'
                or status.get('isFinalized') in (True, 1, '1') or status.get('messages')):
            return result('INCONCLUSIVE', 'Search is incomplete or returned diagnostics; check again later')
        data = request(path + '/results?output_mode=json&count=0')
        if data.get('messages') or data.get('preview') in (True, 1, '1') or not isinstance(data.get('results'), list):
            return result('INCONCLUSIVE', 'Search results are incomplete')
        total = 0
        for row in data['results']:
            if row.get('netspout_run_id') != r['run_id'] or not re.fullmatch(r'\d+', str(row.get('count', ''))):
                return result('INCONCLUSIVE', 'Search returned unrelated or unusable results')
            total += int(row['count'])
        if total > 0:
            return result('VERIFIED', 'Matching indexed log events found in the recorded run window', total)
        if r['execution_state'] == 'ACTIVE' or now - end < 60 or cached.get('latest', latest) < latest:
            update(run_id, lambda rec: rec.pop('search_job', None))
            return result('INCONCLUSIVE', 'No matches yet; run activity or ingestion delay may explain this', 0)
        return result('NOT_FOUND', 'Completed scoped search found no matches; ingestion may still be delayed', 0)
    except Exception:
        update(run_id, lambda rec: rec.pop('search_job', None))
        return result('ERROR', 'Splunk search failed, timed out or was denied')
