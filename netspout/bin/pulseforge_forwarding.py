"""Bounded app-owned handoff to a Splunk XML modular input; never S2S encoding."""
import configparser
from contextlib import contextmanager
import fcntl
import io
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import time
import uuid
import xml.etree.ElementTree as ET

MAX_PENDING = 100
MAX_BYTES = 10 * 1024 * 1024
MAX_EVENT_BYTES = 65536
MAX_RECEIPTS = 100
RECEIPT_TTL = 86400
STANZA = 'pulseforge_spool://native'
NAME = re.compile(r'[A-Za-z0-9_][A-Za-z0-9_-]{0,127}')
FILE = re.compile(r'[0-9a-f]{32}\.(json|done)')


def validate(settings):
    result = {k: settings.get(k, v) for k, v in
              dict(forwarding_index='idx_network_ops', forwarding_group='').items()}
    if not all(isinstance(v, str) and NAME.fullmatch(v) for v in result.values()):
        raise ValueError('Invalid forwarding settings')
    return result


def root():
    home = os.environ.get('SPLUNK_HOME')
    if not home:
        raise ValueError('Splunk runtime unavailable')
    # Validate every existing component we create/use; never follow spool links.
    parent = Path(home) / 'var' / 'run' / 'netspout'
    folder = parent / 'forwarding'
    for path in (parent, folder):
        path.mkdir(mode=0o700, parents=path == parent, exist_ok=True)
        info = path.lstat()
        if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('Private forwarding directory unavailable')
    return folder


def read_private(path, max_bytes=None):
    limit=MAX_EVENT_BYTES if max_bytes is None else max_bytes
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077 or info.st_size > limit:
            raise ValueError('Invalid spool file')
        return json.loads(stream.read(limit + 1))


@contextmanager
def locked():
    folder = root()
    fd = os.open(folder / '.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise ValueError('Invalid spool lock')
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield folder
    finally:
        os.close(fd)


def atomic(path, value):
    data = json.dumps(value, ensure_ascii=True, allow_nan=False).encode()
    if len(data) > MAX_EVENT_BYTES:
        raise ValueError('Event exceeds spool limit')
    fd, name = tempfile.mkstemp(prefix='.staged-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def cleanup(folder, now):
    """Never expire unread events. Receipts authorize removal of handed-off files."""
    receipts = []
    for path in sorted(folder.glob('*.done')):
        if not FILE.fullmatch(path.name):
            raise ValueError('Invalid spool receipt')
        record = read_private(path)
        stamp = record['handed_off_at']
        if type(stamp) not in (int, float) or not 0 <= stamp <= now:
            raise ValueError('Invalid spool receipt')
        pending = path.with_suffix('.json')
        if pending.exists() or pending.is_symlink():
            read_private(pending)
            pending.unlink()
        receipts.append((stamp, path))
    receipts.sort(key=lambda item: (item[0], item[1].name), reverse=True)
    for i, (stamp, path) in enumerate(receipts):
        if i >= MAX_RECEIPTS or now - stamp > RECEIPT_TTL:
            path.unlink()


def event_record(event, raw, run_id, scenario, index, timestamp):
    if (str(uuid.UUID(run_id)) != run_id or not NAME.fullmatch(index)
            or type(timestamp) not in (int,float) or not math.isfinite(timestamp) or timestamp < 0):
        raise ValueError('Invalid run scope')
    for value in (raw, scenario, event['host'], event['source'], event['sourcetype']):
        if not isinstance(value, str) or any((ord(c) < 32 and c not in '\n\t\r') or 0xD800 <= ord(c) <= 0xDFFF or ord(c) in (0xFFFE,0xFFFF) for c in value):
            raise ValueError('Invalid event metadata')
    # Vendor text is preserved inside the envelope, not passed off as raw-wire fidelity.
    data = dict(original_event=raw, netspout_run_id=run_id, netspout_scenario_id=scenario,
                netspout_device_id=event['host'], netspout_phase='BASELINE')
    return dict(time=timestamp, host=event['host'], source=event['source'],
                sourcetype=event['sourcetype'], index=index, data=data)


def publish(record, now=None):
    now = time.time() if now is None else now
    with locked() as folder:
        cleanup(folder, now)
        entries = [p for p in folder.iterdir() if p.name != '.lock']
        if any(p.is_symlink() or not p.is_file() for p in entries):
            raise ValueError('Unsafe spool entry')
        pending = [p for p in entries if p.suffix != '.done']
        size = len(json.dumps(record, ensure_ascii=True, allow_nan=False).encode())
        # Include staging/orphan files in bounds; never silently discard them.
        if len(pending) >= MAX_PENDING or sum(p.stat().st_size for p in entries) + size > MAX_BYTES:
            raise ValueError('Spool full; unread events retained')
        path = folder / (uuid.uuid4().hex + '.json')
        atomic(path, record)
        return path.name


def xml_event(record):
    event = ET.Element('event', {'stanza': STANZA, 'unbroken': '1'})
    for key in ('time', 'host', 'source', 'sourcetype', 'index'):
        ET.SubElement(event, key).text = str(record[key])
    ET.SubElement(event, 'data').text = json.dumps(record['data'], ensure_ascii=True, allow_nan=False)
    ET.SubElement(event, 'done')
    return ET.tostring(event, encoding='unicode')


def drain(output, now=None):
    """Flush to Splunk's input pipe, then receipt. This is not ingestion proof.

    Crash between flush and receipt can duplicate an event on a later invocation.
    Pending files are never deleted merely for age or storage pressure.
    """
    now = time.time() if now is None else now
    count = 0
    with locked() as folder:
        cleanup(folder, now)
        output.write('<stream>\n')
        for path in sorted(folder.glob('*.json'))[:MAX_PENDING]:
            if not FILE.fullmatch(path.name):
                raise ValueError('Invalid spool entry')
            record = read_private(path)
            # Render before writing so malformed files cannot emit partial events.
            text = xml_event(record)
            output.write(text + '\n')
            output.flush()
            atomic(path.with_suffix('.done'), dict(handed_off_at=now, run_id=record['data']['netspout_run_id']))
            path.unlink()
            count += 1
        output.write('</stream>\n')
        output.flush()
        cleanup(folder, now)
    return count


def pending_count():
    with locked() as folder:
        return len(list(folder.glob('*.json')))


def active_settings():
    return validate(read_private(root().parent / 'datablaster_config.json',max_bytes=524288))


def readiness(settings):
    """Read effective configuration only. Never create/modify tcpout groups."""
    config = validate(settings)
    home = os.environ.get('SPLUNK_HOME', '')
    command = str(Path(home) / 'bin' / 'splunk')
    def effective(kind, stanza):
        done = subprocess.run([command, 'btool', kind, 'list', stanza], capture_output=True, text=True, timeout=10)
        if done.returncode:
            raise ValueError('Effective configuration unavailable')
        parser = configparser.ConfigParser(interpolation=None, strict=True)
        parser.read_string(done.stdout)
        return parser[stanza] if parser.has_section(stanza) else {}
    try:
        inp = effective('inputs', STANZA)
        group = effective('outputs', 'tcpout:' + config['forwarding_group'])
        ready = (inp.get('disabled', '1').lower() in ('0', 'false')
                 and inp.get('_tcp_routing', '') == config['forwarding_group']
                 and group.get('disabled', '0').lower() in ('0', 'false')
                 and bool(group.get('server', '').strip()))
        with locked() as folder:
            cleanup(folder, time.time())
            pending = len(list(folder.glob('*.json')))
        return dict(status='success' if ready else 'error', state='READY' if ready else 'NOT_READY',
                    message='Input and forwarding group configured; delivery is unverified' if ready else
                    'Enable the dedicated input and route it to the existing forwarding group',
                    pending_files=pending, ingested=None, forwarded=None, indexed=None)
    except Exception:
        return dict(status='error', state='UNAVAILABLE', message='Forwarding readiness unavailable',
                    ingested=None, forwarded=None, indexed=None)
