"""Bounded native run records in the existing status snapshot (no credentials)."""
import copy
import json
import math
import os
import re
import time
import sys
import uuid
from urllib.parse import quote, urlsplit

COUNTERS = ('generated', 'attempted', 'accepted', 'failed', 'unknown')
STATES = {'NOT_CHECKED', 'VERIFIED', 'NOT_FOUND', 'INCONCLUSIVE', 'ERROR'}
INDEX = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_-]{0,127}')
TTL = 7 * 86400
MAX_WINDOW = 86400


_runtime = None


def _bind_runtime(runtime):
    """Bind a loader-created handler without importing an ordinary-name copy.

    Binding is idempotent for the same module. Refuse a different handler or
    helper origin, so a second simulation lock cannot silently be selected.
    """
    global _runtime
    expected = os.path.realpath(os.path.join(os.path.dirname(__file__), 'datablaster_rest.py'))
    ordinary = sys.modules.get('datablaster_rest')
    if (sys.modules.get(getattr(runtime, '__name__', None)) is not runtime
            or os.path.realpath(getattr(runtime, '__file__', '')) != expected
            or (ordinary is not None and ordinary is not runtime)
            or (_runtime is not None and _runtime is not runtime)):
        raise RuntimeError('Native monitor runtime identity conflict')
    _runtime = runtime


def api():
    if _runtime is not None:
        return _runtime
    # CLI/Python-streamer processes use the ordinary module, as before. The
    # persistent handler always binds explicitly before invoking this helper.
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
                and isinstance(record['destination'], dict) and record['destination'].get('transport') in ('HEC', 'SYSLOG', 'OTLP', 'SNMP', 'FORWARDING')
                and isinstance(record['destination'].get('host'), str)
                and type(record['destination'].get('port')) is int
                and isinstance(record['execution'], dict) and isinstance(record['execution'].get('action'), str)
                and (record.get('pid') is None or (type(record['pid']) is int and record['pid'] > 0))
                and record['verification']['state'] in STATES
                and ('syslog_delivery' not in record or (isinstance(record['syslog_delivery'], dict)
                     and set(record['syslog_delivery']) == {'attempted', 'sent', 'failed', 'unknown'}
                     and all(v is None or (type(v) is int and v >= 0) for v in record['syslog_delivery'].values())))
                and ('otlp_delivery' not in record or (isinstance(record['otlp_delivery'], dict)
                     and set(record['otlp_delivery']) == {'attempted', 'acknowledged', 'rejected', 'failed', 'unknown'}
                     and all(v is None or (type(v) is int and v >= 0) for v in record['otlp_delivery'].values())))
                and ('snmp_delivery' not in record or (isinstance(record['snmp_delivery'], dict)
                     and set(record['snmp_delivery']) == {'attempted','sent','failed','unknown','acknowledged'}
                     and all(v is None or (type(v) is int and v >= 0) for v in record['snmp_delivery'].values())))
                and ('forwarding_delivery' not in record or (isinstance(record['forwarding_delivery'],dict)
                     and set(record['forwarding_delivery']) == {'published','failed','unknown'}
                     and all(v is None or (type(v) is int and v >= 0) for v in record['forwarding_delivery'].values())))
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
    if clean.get('native_transport') == 'syslog':
        config = clean['syslog']
        record.update(destination={'transport': 'SYSLOG', 'host': config['syslog_host'],
                      'port': config['syslog_port'], 'protocol': config['syslog_protocol'],
                      'format': config['syslog_format']}, classification='LOG', indexes=[],
                      correlation='UNSUPPORTED',
                      syslog_delivery=dict(attempted=None, sent=None, failed=None, unknown=None))
    if clean.get('native_transport') == 'otlp':
        config = clean['otlp']
        endpoint = urlsplit(config['otlp_endpoint'])
        record.update(destination={'transport':'OTLP', 'host':endpoint.hostname,
                      'port':endpoint.port or (443 if endpoint.scheme == 'https' else 80),
                      'protocol':'http_json', 'signal':config['otlp_signal']}, indexes=[],
                      classification={'logs':'LOG','metrics':'METRIC','both':'MIXED'}[config['otlp_signal']],
                      correlation='UNSUPPORTED', otlp_delivery={k:None for k in ('attempted','acknowledged','rejected','failed','unknown')})
    if clean.get('native_transport') == 'snmp':
        config = clean['snmp']
        record.update(destination={'transport':'SNMP','host':config['snmp_host'],'port':config['snmp_port'],
                      'protocol':'udp','version':'2c','message_type':config['snmp_message_type']},indexes=[],
                      classification='LOG',correlation='UNSUPPORTED',
                      snmp_delivery={k:None for k in ('attempted','sent','failed','unknown','acknowledged')})
    if clean.get('native_transport') == 'forwarding':
        config = clean['forwarding']
        record.update(destination={'transport':'FORWARDING','host':'splunk-managed','port':0,
                      'group':config['forwarding_group']},indexes=[config['forwarding_index']],
                      classification='LOG',correlation='UNSUPPORTED',
                      forwarding_delivery={k:None for k in ('published','failed','unknown')})
    if clean.get('_destination_identity'):
        record['named_destination']=copy.deepcopy(clean['_destination_identity'])
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
    def result(state, message, count=None, metric_points=None):
        value = {'state': state, 'message': message, 'matching_events': count}
        if metric_points is not None:
            value['matching_metric_points'] = metric_points
        saved = update(run_id, lambda rec: rec.update(verification=value))
        return 200, {'status': 'success', 'run': saved}
    # A local Splunk search can only verify the local destination.
    if r['destination']['transport'] == 'FORWARDING':
        return result('INCONCLUSIVE','Spool publication is not ingestion or downstream forwarding proof')
    if r['destination']['transport'] == 'SNMP':
        return result('INCONCLUSIVE','SNMP indexing verification is unsupported; synthetic correlation varbinds are emitted')
    if r['destination']['transport'] == 'OTLP':
        return result('INCONCLUSIVE', 'OTLP indexing verification is unsupported; correlation attributes are emitted')
    if r['destination']['transport'] == 'SYSLOG':
        return result('INCONCLUSIVE', 'Syslog run correlation and indexing verification are unsupported')
    if r['destination']['host'] not in ('127.0.0.1', 'localhost', '::1'):
        return result('INCONCLUSIVE', 'Remote destination search is unsupported')
    if r['correlation'] != 'SUPPORTED' or r['classification'] not in ('LOG', 'MIXED') or not r['indexes']:
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
        mixed = r['classification'] == 'MIXED'
        if mixed:
            # Resolve signal scopes from recorded indexes, never live app defaults
            # or index-name guesses. Ordinary search cannot read metric indexes.
            scopes = {'event': [], 'metric': []}
            for index in r['indexes']:
                metadata = request('/services/data/indexes/' + quote(index, safe='')
                                   + '?output_mode=json&f=datatype')
                entries = metadata.get('entry', [])
                datatype = entries[0].get('content', {}).get('datatype') if len(entries) == 1 else None
                if datatype not in scopes:
                    return result('INCONCLUSIVE', 'Recorded index signal types are unavailable')
                scopes[datatype].append('index="' + index + '"')
            if not all(scopes.values()):
                return result('INCONCLUSIVE', 'Mixed run requires recorded log and metric index scopes')
            bounds = ' earliest=' + str(earliest) + ' latest=' + str(latest)
            query = ('search (' + ' OR '.join(scopes['event']) + ') netspout_run_id="' + r['run_id'] + '"'
                     + bounds + ' | stats count by netspout_run_id | eval netspout_signal="LOG"'
                     + ' | append [ | mstats count(_value) as count WHERE ('
                     + ' OR '.join(scopes['metric']) + ') metric_name=* netspout_run_id="'
                     + r['run_id'] + '"' + bounds + ' BY netspout_run_id'
                     + ' | eval netspout_signal="METRIC" ]')
        # Mixed search semantics differ from the original log-only contract.
        # Never reuse a cached job generated by the previous mixed query.
        cached = r.get('search_job', {})
        if mixed and cached.get('contract') != 'mixed-v2':
            cached = {}
        def has_diagnostics(messages):
            if not messages:
                return False
            benign = {"Your timerange was substituted based on your search string",
                      "[subsearch]: Your timerange was substituted based on your 'where' clause"}
            return not (mixed and isinstance(messages, list) and all(
                isinstance(message, dict) and message.get('type') == 'INFO'
                and message.get('text') in benign for message in messages))
        sid = cached.get('sid')
        if not sid:
            job = request('/services/search/jobs?output_mode=json', 'POST', {
                'search': query, 'exec_mode': 'normal', 'max_time': '10', 'auto_cancel': '60'})
            sid = job.get('sid')
            if isinstance(sid, str) and sid and len(sid) <= 256:
                update(run_id, lambda rec: rec.update(search_job=dict(
                    sid=sid, latest=latest, **({'contract': 'mixed-v2'} if mixed else {}))))
        if not isinstance(sid, str) or not sid or len(sid) > 256:
            raise RuntimeError()
        path = '/services/search/jobs/' + quote(sid, safe='')
        status = request(path + '?output_mode=json')['entry'][0]['content']
        if status.get('isFailed') in (True, 1, '1') or status.get('dispatchState') == 'FAILED':
            return result('ERROR', 'Splunk search failed or was denied')
        if (status.get('isDone') not in (True, 1, '1') or status.get('dispatchState') != 'DONE'
                or status.get('isFinalized') in (True, 1, '1') or has_diagnostics(status.get('messages'))):
            return result('INCONCLUSIVE', 'Search is incomplete or returned diagnostics; check again later')
        data = request(path + '/results?output_mode=json&count=0')
        if has_diagnostics(data.get('messages')) or data.get('preview') in (True, 1, '1') or not isinstance(data.get('results'), list):
            return result('INCONCLUSIVE', 'Search results are incomplete')
        total = 0
        metric_total = 0
        for row in data['results']:
            if row.get('netspout_run_id') != r['run_id'] or not re.fullmatch(r'\d+', str(row.get('count', ''))):
                return result('INCONCLUSIVE', 'Search returned unrelated or unusable results')
            if mixed:
                signal = row.get('netspout_signal')
                if signal not in ('LOG', 'METRIC'):
                    return result('INCONCLUSIVE', 'Search returned unrelated or unusable results')
                if signal == 'METRIC':
                    metric_total += int(row['count'])
                    continue
            total += int(row['count'])
        if mixed and total > 0 and metric_total > 0:
            return result('VERIFIED', 'Matching indexed logs and metric points found in the recorded run window',
                          total, metric_total)
        if mixed and (total > 0 or metric_total > 0):
            update(run_id, lambda rec: rec.pop('search_job', None))
            return result('INCONCLUSIVE', 'Only one signal found; mixed run needs indexed logs and metric points',
                          total, metric_total)
        if total > 0:
            return result('VERIFIED', 'Matching indexed log events found in the recorded run window', total)
        if r['execution_state'] == 'ACTIVE' or now - end < 60 or cached.get('latest', latest) < latest:
            update(run_id, lambda rec: rec.pop('search_job', None))
            return result('INCONCLUSIVE', 'No matches yet; run activity or ingestion delay may explain this', 0)
        return result('NOT_FOUND', 'Completed scoped search found no matches; ingestion may still be delayed', 0)
    except Exception:
        update(run_id, lambda rec: rec.pop('search_job', None))
        return result('ERROR', 'Splunk search failed, timed out or was denied')
