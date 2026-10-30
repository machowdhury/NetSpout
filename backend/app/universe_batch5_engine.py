# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/universe_batch5_engine.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""Batch 5 native renderers: Cisco IOS-XE change, fault and health device syslog.

Family text comes from captured IOS-XE messages (see scripts/build_universe_batch5.py). Only declared fields vary:
timestamps, the device address and sequence number in the header, and validated slots (interface, neighbor, state, CLI
command, ...) whose surrounding text is unchanged. There is no generic fallback.
"""
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import ipaddress
import json
from pathlib import Path
import re

try:
    from netspout_core.models import LogEntry, Node, NodeType
except ImportError:
    try:
        from app.models import LogEntry, Node, NodeType
    except ImportError:
        from models import LogEntry, Node, NodeType

BATCH5_SCENARIO_IDS = [
    'ub5_cisco_change_induced_outage', 'ub5_cisco_platform_health_degradation', 'ub5_cisco_nac_radius_outage',
]
_IP_SLOTS = {'neighbor', 'device_ip'}
_SLOT_VALUE = re.compile(r"[A-Za-z0-9_./:() -]{1,80}")
_COMMAND = re.compile(r"[A-Za-z0-9 _./:-]{1,120}")
_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


@lru_cache(maxsize=1)
def batch_registry():
    here = Path(__file__).resolve().parent
    for directory in [here / 'catalog_data', here.parents[1] / 'catalog', here.parent / 'catalog']:
        path = directory / 'universe_batch5.json'
        if path.is_file():
            return json.loads(path.read_text())
    raise FileNotFoundError('Batch 5 canonical runtime catalog missing')


UNIVERSE_BATCH5_SOURCE_SOURCETYPES = {s['splunk_sourcetype']: s['batch_source_id'] for s in batch_registry()['sources']}


def _now(when):
    value = when or datetime.now(timezone.utc)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('when must be timezone-aware')
    return value.astimezone(timezone.utc)


def _stamp(now):
    return '%s %02d %s' % (_MONTHS[now.month - 1], now.day, now.strftime('%H:%M:%S'))


class UniverseBatch5Engine:
    @classmethod
    def format_universe_batch5_log(cls, device: Node, sourcetype: str, family: str = None, when=None, src_ip=None,
                                   dest_ip=None, params=None, sequence: int = None):
        source = next((s for s in batch_registry()['sources'] if s['splunk_sourcetype'] == sourcetype), None)
        if source is None:
            raise ValueError('Unsupported Batch 5 sourcetype: ' + sourcetype)
        selected = source['families'][0] if family is None else next((f for f in source['families'] if f['id'] == family), None)
        if selected is None:
            raise ValueError('Unsupported native event family: ' + family)
        now = _now(when)
        address = str(ipaddress.ip_address(device.ip_address))
        slots = dict(selected['params'])
        if 'device_ip' in slots:
            slots['device_ip'] = address
        for key, value in (params or {}).items():
            if key not in selected['params']:
                raise ValueError('Unsupported slot for %s: %s' % (selected['id'], key))
            slots[key] = value
        for key, value in slots.items():
            value = str(value)
            if key in _IP_SLOTS:
                ipaddress.IPv4Address(value)
            elif not (_COMMAND if key == 'command' else _SLOT_VALUE).fullmatch(value):
                raise ValueError('Invalid value for slot ' + key)
            slots[key] = value
        body = selected['body'].format(**slots) if slots else selected['body']
        seq = int(sequence if sequence is not None else now.timestamp() % 100000)
        raw = '%s %s %d: %s%s.%03d: %s' % (_stamp(now), address, seq, '*' if selected['star'] else '', _stamp(now),
                                           now.microsecond // 1000, body)
        return LogEntry(timestamp=now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3], device_id=device.id,
                        src_ip=address, dest_ip=str(ipaddress.ip_address(dest_ip or '10.20.1.16')), protocol='UDP',
                        duration='0ms', action=selected['id'], signature=source['batch_source_id'],
                        status=source['status'], raw_log=raw, node_type=device.type.value, node_id=device.id,
                        vendor=source['vendor'], sourcetype=sourcetype)


def run_batch5_scenario(scenario_id, run_id, tagger, source_ip='192.0.2.10', when=None):
    registry = batch_registry()
    if scenario_id not in registry['scenarios']:
        raise ValueError('Unsupported Batch 5 scenario')
    steps = registry['scenarios'][scenario_id]
    end = _now(when)
    device = Node(id='ub5-edge', name='edge-sw-01.example.test', type=NodeType.SWITCH, ip_address='10.201.48.119')
    by_id = {s['batch_source_id']: s for s in registry['sources']}
    groups = {}
    seq = 4390
    for i, step in enumerate(steps):
        source = by_id[step['sourcetype']]
        seq += 1
        entry = UniverseBatch5Engine.format_universe_batch5_log(
            device, source['splunk_sourcetype'], step['family'], when=end - timedelta(seconds=10 * (len(steps) - 1 - i)),
            params=step['params'], sequence=seq)
        groups.setdefault(step['phase'], []).append(entry)
    events = [event for phase, group in groups.items() for event in tagger(group, run_id, scenario_id, phase)]
    previous = None
    for event in events:
        event.netspout_parent_event_id = previous
        previous = event.netspout_event_id
    return events
