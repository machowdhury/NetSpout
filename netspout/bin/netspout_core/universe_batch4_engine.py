"""Batch 4 native renderers: SaaS audit, endpoint threat and exposure logs grounded in selector-linked RAW.

Only declared native time/address fields vary. No generic JSON fallback exists.
"""
import copy
from datetime import datetime, timezone
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

UNIVERSE_BATCH4_SOURCE_SOURCETYPES={
 'slack:audit':'slack','github:enterprise:audit':'github','gitlab:audit:json':'gitlab',
 'cybereason:malops':'cybereason','qualys:activityLog':'qualys',
 'rapid7:insightvm:asset:vulnerability_finding':'rapid7','sentinelone:channel:threats':'sentinelone',
 'tanium:discover:managed':'tanium','trellix_epo:threat_events':'trellix','bitdefender:gz':'bitdefender',
 'ibm:qradar:offense':'ibm_qradar','elasticsearch:json':'elasticsearch',
}
BATCH4_SCENARIO_IDS=['ub4_saas_collaboration_audit','ub4_endpoint_threat_pipeline','ub4_exposure_infra_logging']


@lru_cache(maxsize=1)
def batch_registry():
    here=Path(__file__).resolve().parent
    for directory in [here/'catalog_data',here.parents[1]/'catalog',here.parent/'catalog']:
        path=directory/'universe_batch4.json'
        if path.is_file():return json.loads(path.read_text())
    raise FileNotFoundError('Batch 4 canonical runtime catalog missing')


def _now(when):
    value=when or datetime.now(timezone.utc)
    if value.tzinfo is None or value.utcoffset() is None:raise ValueError('when must be timezone-aware')
    return value.astimezone(timezone.utc)


def _address(value):
    return str(ipaddress.ip_address(value))


def _millis(value):
    return datetime.fromisoformat(value.replace('Z','+00:00'))


class UniverseBatch4Engine:
    @classmethod
    def format_universe_batch4_log(cls,device:Node,sourcetype:str,family:str,when=None,src_ip=None,dest_ip=None):
        source=next((s for s in batch_registry()['sources'] if s['splunk_sourcetype']==sourcetype),None)
        if source is None:raise ValueError('Unsupported Batch 4 sourcetype: '+sourcetype)
        selected=next((f for f in source['families'] if f['id']==family),None)
        if selected is None:raise ValueError('Unsupported native event family: '+family)
        now=_now(when);iso=now.isoformat(timespec='milliseconds').replace('+00:00','Z')
        host=device.name
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,253}',host):raise ValueError('Invalid native host name')
        src=_address(src_ip or '192.0.2.10');dst=_address(dest_ip or '198.51.100.20')
        value=copy.deepcopy(selected['template']);sid=source['batch_source_id'];protocol='TCP'
        if sid=='slack':
            value['date_create']=int(now.timestamp())
            context=value.get('context',{})
            if context.get('location',{}).get('ip_address'):context['location']['ip_address']=src
            if context.get('ip_address'):context['ip_address']=src
        elif sid=='github':
            value['@timestamp']=int(now.timestamp()*1000)
            if value.get('actor_location',{}).get('ip'):value['actor_location']['ip']=src
        elif sid=='gitlab':
            value['time']=iso
            if 'created_at' in value:value['created_at']=now.isoformat(timespec='milliseconds')
            if value.get('meta.remote_ip'):value['meta.remote_ip']=src
        elif sid=='cybereason':
            # Malop history spacing is preserved; the native record carries no routable address.
            anchor=int(value['simpleValues']['creationTime']['values'][0]);delta=int(now.timestamp()*1000)-anchor
            for key in ['creationTime','malopStartTime','malopLastUpdateTime']:
                holder=value['simpleValues'].get(key)
                if holder:holder['values']=[str(int(v)+delta) for v in holder['values']]
            for key,stamp in value['suspicions'].items():value['suspicions'][key]=stamp+delta
            src='0.0.0.0';dst=device.ip_address
        elif sid=='qualys':
            value['Date']=now.strftime('%Y-%m-%dT%H:%M:%SZ')
            if 'User IP' in value:value['User IP']=src
        elif sid=='rapid7':
            start=_millis(value['last_scan_start']);end=_millis(value['last_scan_end'])
            value['last_scan_start']=(now-(end-start)).isoformat(timespec='milliseconds').replace('+00:00','Z')
            value['last_scan_end']=iso
            if value.get('last_assessed_for_vulnerabilities'):value['last_assessed_for_vulnerabilities']=iso
            if value.get('ip'):value['ip']=src
        elif sid=='sentinelone':
            threat=value['threatInfo'];anchor=_millis(threat['createdAt']);delta=now-anchor
            for key in ['createdAt','updatedAt','identifiedAt']:
                if isinstance(threat.get(key),str):
                    threat[key]=(_millis(threat[key])+delta).strftime('%Y-%m-%dT%H:%M:%S.%f')+'Z'
            native=value.get('agentDetectionInfo',{}).get('agentIpV4')
            if isinstance(native,str) and native.count('.')==3:
                try:value['agentDetectionInfo']['agentIpV4']=src if ipaddress.ip_address(native).version==4 else native
                except ValueError:pass
        elif sid=='tanium':
            def parse(v):return datetime.fromisoformat(v.replace(' +00:00','+00:00'))
            def fmt(v):return v.strftime('%Y-%m-%d %H:%M:%S')+' +00:00'
            delta=now-parse(value['UpdatedAt'])
            for key in ['CreatedAt','UpdatedAt','LastManagedAt']:
                if isinstance(value.get(key),str):value[key]=fmt(parse(value[key])+delta)
            if value.get('IpAddress'):value['IpAddress']=src
            if value.get('NatIpAddress'):value['NatIpAddress']=src
        elif sid=='trellix':
            lag=_millis(value['EPOEvents.ReceivedUTC'])-_millis(value['EPOEvents.DetectedUTC'])
            value['EPOEvents.DetectedUTC']=now.isoformat(timespec='seconds')
            if 'EPOEvents.EventTimeLocal' in value:value['EPOEvents.EventTimeLocal']=now.isoformat(timespec='seconds')
            value['EPOEvents.ReceivedUTC']=(now+lag).isoformat(timespec='seconds')
            for key,address in [('EPOEvents.AnalyzerIPV4',src),('EPOEvents.TargetIPV4',dst),('EPOEvents.SourceIPV4',src)]:
                if isinstance(value.get(key),int):value[key]=int(ipaddress.IPv4Address(address))
            protocol='EPOLL'
        elif sid=='bitdefender':
            # Rendered record is the inner events[].message notification; wrapper unpacking is
            # a documented PulseForge framing choice pending installed-TA verification.
            for key in ['timestamp','last_blocked']:
                if value.get(key):value[key]=iso
            if value.get('computer_ip'):value['computer_ip']=src
        elif sid=='ibm_qradar':
            anchor=value['start_time'];delta=int(now.timestamp()*1000)-anchor
            for key in ['start_time','last_updated_time','last_persisted_time']:
                if isinstance(value.get(key),int):value[key]+=delta
            native=value.get('offense_source')
            if isinstance(native,str):
                try:
                    if ipaddress.ip_address(native).version==4:value['offense_source']=src
                except ValueError:pass
        elif sid=='elasticsearch':
            # Cluster node identity and historical message text remain fixture-derived.
            value['@timestamp']=iso
            src='0.0.0.0';dst=device.ip_address
        else:
            raise ValueError('No native renderer for source')
        raw=json.dumps(value,ensure_ascii=False,separators=(',',':')) if isinstance(value,dict) else value
        return LogEntry(timestamp=now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],device_id=device.id,
                        src_ip=src,dest_ip=dst,protocol=protocol,duration='0ms',action=selected['action'],
                        signature=family,status=selected['status'],raw_log=raw,node_type=device.type.value,
                        node_id=device.id,vendor=source['vendor'],sourcetype=sourcetype)


def run_batch4_scenario(scenario_id,run_id,tagger,source_ip='192.0.2.10',when=None):
    registry=batch_registry()
    if scenario_id not in registry['scenarios']:raise ValueError('Unsupported Batch 4 scenario')
    now=_now(when);records=[]
    for i,sid in enumerate(registry['scenarios'][scenario_id]):
        source=next(s for s in registry['sources'] if s['batch_source_id']==sid)
        device=Node(id='ub4-'+sid,name=sid+'-01.example.test',type=NodeType.WEB_SERVER,ip_address='198.51.100.'+str(i+10))
        for family in source['event_families']:
            records.append(UniverseBatch4Engine.format_universe_batch4_log(device,source['splunk_sourcetype'],family,when=now,
                            src_ip=source_ip if sid not in ('cybereason','elasticsearch') else None))
    groups={phase:[] for phase in ['BASELINE','OBSERVE','VALIDATE']}
    for i,event in enumerate(records):groups[list(groups)[min(2,i*3//len(records))]].append(event)
    events=[event for phase,group in groups.items() for event in tagger(group,run_id,scenario_id,phase)]
    previous=None
    for event in events:event.netspout_parent_event_id=previous;previous=event.netspout_event_id
    return events
