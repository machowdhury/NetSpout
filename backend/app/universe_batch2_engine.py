# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/universe_batch2_engine.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""Bounded Batch 2 native formatters grounded in pinned, selector-addressable RAW.

Templates ship in the canonical batch catalog and its generated runtime mirrors.
Only native identity/time/address fields are varied. Source event IDs, action
codes, message grammars and product field names come from the selected fixture.
"""
import copy
from datetime import datetime, timezone
from functools import lru_cache
import ipaddress
import json
from pathlib import Path
import re
import uuid

try:
    from netspout_core.models import LogEntry, Node, NodeType
except ImportError:
    try:
        from app.models import LogEntry, Node, NodeType
    except ImportError:
        from models import LogEntry, Node, NodeType


UNIVERSE_BATCH2_SOURCE_SOURCETYPES = {
    'hashicorp_vault_audit_log': 'vault', 'traefik:access:json': 'traefik',
    'claroty:cef': 'claroty', 'mongodb:log': 'mongodb',
    'Confluence:audit log': 'confluence', 'nginx:access': 'nginx',
    'proofpoint_tap_siem': 'proofpoint', 'veeam_vbr_syslog': 'veeam',
    'mikrotik:routeros': 'mikrotik',
}
BATCH2_SCENARIO_IDS = ['ub2_cloud_identity_mail_hunt', 'ub2_ot_edge_routing_observation',
                       'ub2_database_backup_integrity']


@lru_cache(maxsize=1)
def batch_registry():
    here = Path(__file__).resolve().parent
    for base in [here / 'catalog_data', here.parents[1] / 'catalog', here.parent / 'catalog']:
        path = base / 'universe_batch2.json'
        if path.is_file():
            return json.loads(path.read_text())
    raise FileNotFoundError('Batch 2 canonical runtime catalog is missing')


def _utc(when):
    when = when or datetime.now(timezone.utc)
    if when.tzinfo is None or when.utcoffset() is None:
        raise ValueError('when must be timezone-aware')
    return when.astimezone(timezone.utc)


def _uuid(seed):
    return str(uuid.uuid5(uuid.NAMESPACE_DNS, seed))


def _safe(value):
    if not isinstance(value, str) or any(c in value for c in '\r\n\x00'):
        raise ValueError('Native field values must be single-line text')
    return value


class UniverseBatch2Engine:
    @classmethod
    def format_universe_batch2_log(cls, device: Node, sourcetype: str, family: str,
                                    when=None, src_ip='192.0.2.10', user_name='training.operator'):
        """Render one validated native family. Unknown sources/families fail closed."""
        source = next((s for s in batch_registry()['sources'] if s['splunk_sourcetype'] == sourcetype), None)
        if source is None:
            raise ValueError(f'Unsupported Batch 2 sourcetype: {sourcetype}')
        template = next((f for f in source['families'] if f['id'] == family), None)
        if template is None:
            raise ValueError(f'Unsupported {sourcetype} family: {family}')
        now = _utc(when)
        src_ip = str(ipaddress.ip_address(src_ip))
        dest_ip = str(ipaddress.ip_address(device.ip_address))
        user_name = _safe(user_name)
        host = _safe(device.name)
        iso = now.isoformat(timespec='microseconds').replace('+00:00', 'Z')
        sec = now.strftime('%Y-%m-%dT%H:%M:%SZ')
        value = copy.deepcopy(template['template'])
        source_id = source['batch_source_id']
        protocol = 'TCP'
        if source_id == 'vault':
            value['time'] = iso
            value['request']['id'] = _uuid('vault-request|' + device.id)
            value['request']['remote_address'] = src_ip
            # Tokens remain the public sample's HMAC digests; never emit a real token.
        elif source_id == 'traefik':
            value.update(StartUTC=iso, StartLocal=iso, time=sec,
                         ClientHost=src_ip, ClientAddr=src_ip + ':' + value['ClientPort'])
            # Preserve native Duration and OriginDuration units (nanoseconds).
        elif source_id == 'mongodb':
            value['t']['$date'] = now.isoformat(timespec='milliseconds')
            if 'host' in value.get('attr', {}):
                value['attr']['host'] = host
        elif source_id == 'confluence':
            value['creationDate'] = int(now.timestamp() * 1000)
            value['remoteAddress'] = src_ip
            value['author']['displayName'] = user_name
        elif source_id == 'proofpoint':
            value['messageTime'] = iso
            value['senderIP'] = src_ip
            value['id'] = _uuid('proofpoint|' + device.id + '|' + family)
            for threat in value.get('threatsInfoMap', []):
                threat['threatTime'] = iso
        elif source_id == 'claroty':
            value = re.sub(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z', sec, value, count=1)
            # CEF's native generated/real-time fields contain local human-readable time.
            ctd_time = now.strftime('%b %d %Y %H:%M:%S')
            value = re.sub(r'(Ctd(?:TimeGenerated|RealTime)=)[A-Za-z]{3} \d{1,2} \d{4} \d{2}:\d{2}:\d{2}', lambda m: m[1] + ctd_time, value)
            for field, address in [('CtdSourceIp', src_ip), ('CtdDestinationIp', dest_ip)]:
                original = re.search(field + r'=([0-9.]+)', value)
                if original:
                    value = value.replace(original[1], address)
            # Only native CEF extension values change; no ECS wrapper is emitted.
        elif source_id == 'nginx':
            value = re.sub(r'^\S+', src_ip, value)
            value = re.sub(r'\[[^]]+\]', '[' + now.strftime('%d/%b/%Y:%H:%M:%S +0000') + ']', value, count=1)
        elif source_id == 'veeam':
            # These are native message bodies; no timestamp field is invented.
            # Record time belongs to LogEntry/HEC, while existing payload fields stay native.
            value = re.sub(r'VbrHostName="[^"]*"', lambda _: 'VbrHostName="' + host.replace('"', '') + '"', value)
            value = re.sub(r'DetectionTimeUTC="[^"]*"', lambda _: 'DetectionTimeUTC="' + now.strftime('%m/%d/%Y %H:%M:%S') + '"', value)
            for key in ['JobID', 'JobSessionID']:
                value = re.sub(key + r'="[^"]*"', lambda _, k=key: k + '="' + _uuid('veeam|' + device.id + '|' + k) + '"', value)
        elif source_id == 'mikrotik':
            if family == 'administrator_login':
                if not re.fullmatch(r'[A-Za-z0-9_.@-]{1,64}', user_name):
                    raise ValueError('RouterOS user name contains unsupported characters')
                value = re.sub(r'^[a-z]{3}/\d{2} \d{2}:\d{2}:\d{2}', now.strftime('%b/%d %H:%M:%S').lower(), value)
                value = value.replace('user admin ', 'user ' + user_name + ' ')
                value = value.replace('10.1.101.212', src_ip)
            else:
                protocol = 'OSPF'
                value = now.strftime('%H:%M:%S') + value[8:]
                value = value.replace('10.255.255.1', dest_ip)
                dest_ip = '224.0.0.5'
                src_ip = device.ip_address
        raw = json.dumps(value, separators=(',', ':'), ensure_ascii=False) if isinstance(value, dict) else value
        return LogEntry(timestamp=now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3], device_id=device.id,
                        src_ip=src_ip, dest_ip=dest_ip, protocol=protocol, duration='0ms',
                        action=template['action'], signature=family, status=template['status'], raw_log=raw,
                        node_type=device.type.value, node_id=device.id, vendor=source['vendor'], sourcetype=sourcetype)


def run_batch2_scenario(scenario_id, run_id, tagger, source_ip='192.0.2.10', when=None):
    """Execute every supported family of the scenario's selected sources, in order.

    Phases represent observations, not assertion of a causal intrusion or recovery.
    All events use one explicit episode time, making RAW deterministic when supplied.
    """
    registry = batch_registry()
    if scenario_id not in registry['scenarios']:
        raise ValueError(f'Unsupported Batch 2 scenario: {scenario_id}')
    now = _utc(when)
    groups = registry['scenarios'][scenario_id]
    records = []
    for i, source_id in enumerate(groups):
        source = next(s for s in registry['sources'] if s['batch_source_id'] == source_id)
        device = Node(id='ub2-' + source_id, name=source_id + '-01.example.test',
                      type=NodeType.ROUTER if source_id == 'mikrotik' else NodeType.WEB_SERVER,
                      ip_address='198.51.100.' + str(i + 10))
        records.extend(UniverseBatch2Engine.format_universe_batch2_log(device, source['splunk_sourcetype'], family,
                                                                       when=now, src_ip=source_ip)
                       for family in source['event_families'])
    buckets = {phase: [] for phase in ['BASELINE', 'OBSERVE', 'VALIDATE']}
    for i, event in enumerate(records):
        phase = list(buckets)[min(2, i * 3 // len(records))]
        buckets[phase].append(event)
    events = [event for phase, group in buckets.items() for event in tagger(group, run_id, scenario_id, phase)]
    previous = None
    for event in events:
        event.netspout_parent_event_id = previous
        previous = event.netspout_event_id
    return events
