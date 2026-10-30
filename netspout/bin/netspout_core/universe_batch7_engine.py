"""Batch 7 native renderer: authentic NGINX Plus key=value access records (sourcetype nginx:plus:access).

Captured text is emitted verbatim; the only declared token is the record's own time_local value. No other field varies.
"""
from datetime import datetime, timezone
from functools import lru_cache
import ipaddress
import json
from pathlib import Path

try:
    from netspout_core.models import LogEntry, Node
except ImportError:
    try:
        from app.models import LogEntry, Node
    except ImportError:
        from models import LogEntry, Node


@lru_cache(maxsize=1)
def batch_registry():
    here = Path(__file__).resolve().parent
    for directory in [here / 'catalog_data', here.parents[1] / 'catalog', here.parent / 'catalog']:
        path = directory / 'universe_batch7.json'
        if path.is_file():
            return json.loads(path.read_text())
    raise FileNotFoundError('Batch 7 canonical runtime catalog missing')


UNIVERSE_BATCH7_SOURCE_SOURCETYPES = {s['splunk_sourcetype']: s['batch_source_id'] for s in batch_registry()['sources']}


class UniverseBatch7Engine:
    @classmethod
    def format_universe_batch7_log(cls, device: Node, sourcetype: str, family: str = None, when=None, src_ip=None, dest_ip=None):
        source = next((s for s in batch_registry()['sources'] if s['splunk_sourcetype'] == sourcetype), None)
        if source is None:
            raise ValueError('Unsupported Batch 7 sourcetype: ' + sourcetype)
        selected = source['families'][0] if family is None else next((f for f in source['families'] if f['id'] == family), None)
        if selected is None:
            raise ValueError('Unsupported native event family: ' + family)
        now = when or datetime.now(timezone.utc)
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError('when must be timezone-aware')
        now = now.astimezone(timezone.utc)
        raw = selected['template'].replace('$NGINX_TS$', now.strftime('%d/%b/%Y:%H:%M:%S +0000'))
        address = str(ipaddress.ip_address(device.ip_address))
        return LogEntry(timestamp=now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3], device_id=device.id, src_ip=address,
                        dest_ip=str(ipaddress.ip_address(dest_ip or '10.20.1.16')), protocol='HEC', duration='0ms',
                        action=selected['id'], signature=source['batch_source_id'], status='observed', raw_log=raw,
                        node_type=device.type.value, node_id=device.id, vendor=source['vendor'], sourcetype=sourcetype)
