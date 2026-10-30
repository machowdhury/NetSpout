# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/universe_batch6_engine.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""Batch 6 native renderers: captured Cisco Catalyst Center, SD-WAN, ACI and Nexus records.

Captured text is emitted verbatim. Only declared time tokens are resolved ($GOTS$, $EPOCH_MS$, $TS$, $UTD_TS$, $EPOCH_NS$);
there is no generic fallback and no other field varies, so identifiers shared between records stay consistent.
"""
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import ipaddress
import json
from pathlib import Path

try:
    from netspout_core.models import LogEntry, Node, NodeType
except ImportError:
    try:
        from app.models import LogEntry, Node, NodeType
    except ImportError:
        from models import LogEntry, Node, NodeType

BATCH6_SCENARIO_IDS = ['ub6_sdwan_utd_threat_pipeline', 'ub6_catalyst_wireless_rogue_threat']
_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']


@lru_cache(maxsize=1)
def batch_registry():
    here = Path(__file__).resolve().parent
    for directory in [here / 'catalog_data', here.parents[1] / 'catalog', here.parent / 'catalog']:
        path = directory / 'universe_batch6.json'
        if path.is_file():
            return json.loads(path.read_text())
    raise FileNotFoundError('Batch 6 canonical runtime catalog missing')


UNIVERSE_BATCH6_SOURCE_SOURCETYPES = {s['splunk_sourcetype']: s['batch_source_id'] for s in batch_registry()['sources']}


def _now(when):
    value = when or datetime.now(timezone.utc)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError('when must be timezone-aware')
    return value.astimezone(timezone.utc)


def _tokens(now):
    return {
        '$GOTS$': now.strftime('%Y-%m-%dT%H:%M:%SZ'),
        '$EPOCH_MS$': str(int(now.timestamp() * 1000)),
        '$TS$': '%s %02d %s' % (_MONTHS[now.month - 1], now.day, now.strftime('%H:%M:%S')),
        '$UTD_TS$': now.strftime('%Y/%m/%d-%H:%M:%S.%f') + ' UTC',
        '$EPOCH_NS$': '%d.%09d' % (int(now.timestamp()), now.microsecond * 1000),
    }


class UniverseBatch6Engine:
    @classmethod
    def format_universe_batch6_log(cls, device: Node, sourcetype: str, family: str = None, when=None, src_ip=None, dest_ip=None):
        source = next((s for s in batch_registry()['sources'] if s['splunk_sourcetype'] == sourcetype), None)
        if source is None:
            raise ValueError('Unsupported Batch 6 sourcetype: ' + sourcetype)
        selected = source['families'][0] if family is None else next((f for f in source['families'] if f['id'] == family), None)
        if selected is None:
            raise ValueError('Unsupported native event family: ' + family)
        now = _now(when)
        raw = selected['template']
        for token, value in _tokens(now).items():
            raw = raw.replace(token, value)
        address = str(ipaddress.ip_address(device.ip_address))
        return LogEntry(timestamp=now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3], device_id=device.id, src_ip=address,
                        dest_ip=str(ipaddress.ip_address(dest_ip or '10.20.1.16')), protocol='HEC', duration='0ms',
                        action=selected['id'], signature=source['batch_source_id'], status='observed', raw_log=raw,
                        node_type=device.type.value, node_id=device.id, vendor=source['vendor'], sourcetype=sourcetype)


def run_batch6_scenario(scenario_id, run_id, tagger, source_ip='192.0.2.10', when=None):
    registry = batch_registry()
    if scenario_id not in registry['scenarios']:
        raise ValueError('Unsupported Batch 6 scenario')
    steps = registry['scenarios'][scenario_id]
    end = _now(when)
    device = Node(id='ub6-collector', name='collector.example.test', type=NodeType.WEB_SERVER, ip_address='10.20.1.16')
    groups = {}
    for i, step in enumerate(steps):
        entry = UniverseBatch6Engine.format_universe_batch6_log(
            device, step['sourcetype'], step['family'], when=end - timedelta(seconds=15 * (len(steps) - 1 - i)))
        groups.setdefault(step['phase'], []).append(entry)
    events = [event for phase, group in groups.items() for event in tagger(group, run_id, scenario_id, phase)]
    previous = None
    for event in events:
        event.netspout_parent_event_id = previous
        previous = event.netspout_event_id
    return events
