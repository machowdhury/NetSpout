"""Batch 3 native renderers: explicit formats grounded in selector-linked RAW.

Only declared native time/address fields vary. No generic JSON fallback exists.
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

UNIVERSE_BATCH3_SOURCE_SOURCETYPES={
 'pfsense:filterlog':'pfsense','SysdigSecureEvents':'sysdig','sailpoint_identitynow':'sailpoint',
 'imperva:securesphere:cef':'imperva','barracuda:waf:web_firewall':'barracuda',
 'oracle:audit:text':'oracle','darktrace':'darktrace','ccx:beyondinsight:passwordsafe':'beyondtrust',
 'tenable:io:audit_logs':'tenable','ibm:mq:errorlog':'ibmmq',
}
BATCH3_SCENARIO_IDS=['ub3_identity_runtime_audit','ub3_multivendor_edge_observation','ub3_database_message_audit']


@lru_cache(maxsize=1)
def batch_registry():
    here=Path(__file__).resolve().parent
    for directory in [here/'catalog_data',here.parents[1]/'catalog',here.parent/'catalog']:
        path=directory/'universe_batch3.json'
        if path.is_file():return json.loads(path.read_text())
    raise FileNotFoundError('Batch 3 canonical runtime catalog missing')


def _now(when):
    value=when or datetime.now(timezone.utc)
    if value.tzinfo is None or value.utcoffset() is None:raise ValueError('when must be timezone-aware')
    return value.astimezone(timezone.utc)


def _address(value):
    return str(ipaddress.ip_address(value))


class UniverseBatch3Engine:
    @classmethod
    def format_universe_batch3_log(cls,device:Node,sourcetype:str,family:str,when=None,src_ip=None,dest_ip=None):
        source=next((s for s in batch_registry()['sources'] if s['splunk_sourcetype']==sourcetype),None)
        if source is None:raise ValueError('Unsupported Batch 3 sourcetype: '+sourcetype)
        selected=next((f for f in source['families'] if f['id']==family),None)
        if selected is None:raise ValueError('Unsupported native event family: '+family)
        now=_now(when);iso=now.isoformat(timespec='milliseconds').replace('+00:00','Z')
        host=device.name
        if not re.fullmatch(r'[A-Za-z0-9_.-]{1,253}',host):raise ValueError('Invalid native host name')
        src=_address(src_ip or '192.0.2.10');dst=_address(dest_ip or '198.51.100.20')
        value=copy.deepcopy(selected['template']);sid=source['batch_source_id'];protocol='TCP'
        if sid=='pfsense':
            header,csv=value.split(': ',1);fields=csv.split(',')
            if fields[8]=='6':
                src=_address(src_ip or '2001:db8::10');dst=_address(dest_ip or '2001:db8::20')
                if ipaddress.ip_address(src).version!=6 or ipaddress.ip_address(dst).version!=6:raise ValueError('IPv6 family requires IPv6 endpoints')
                fields[15:17]=[src,dst];protocol=fields[12].upper()
            else:
                if ipaddress.ip_address(src).version!=4 or ipaddress.ip_address(dst).version!=4:raise ValueError('IPv4 family requires IPv4 endpoints')
                fields[18:20]=[src,dst];protocol=fields[16].upper()
            value=re.sub(r'^(<\d+>).+?( filterlog\[\d+\])$',lambda m:m[1]+now.strftime('%b %e %H:%M:%S')+m[2],header)+': '+','.join(fields)
        elif sid=='sysdig':
            old=value['timestamp'];epoch_ns=int(now.timestamp())*1_000_000_000+now.microsecond*1000
            delta=epoch_ns-old;value['timestamp']=epoch_ns
            for key in ['proc.pid.ts','proc.ppid.ts']:
                fields=value.get('content',{}).get('fields',{})
                if key in fields and str(fields[key]).isdigit():fields[key]=str(int(fields[key])+delta)
            # Native rule/source/action data is preserved, including k8s audit content.
        elif sid=='sailpoint':
            value['created']=iso
            if 'synced' in value:value['synced']=iso
            if value.get('ipAddress'):
                value['ipAddress']=src
                if 'hostName' in value.get('attributes',{}):value['attributes']['hostName']=src
        elif sid=='imperva':
            native_time=now.strftime('%b %d %Y %H:%M:%S')
            value=re.sub(r'rt=[A-Za-z]{3} \d{1,2} \d{4} \d{2}:\d{2}:\d{2}',lambda _:'rt='+native_time,value)
            for key,address in [('src',src),('dst',dst)]:
                old=re.search(r'\b'+key+r'=([0-9.]+)',value)
                if old:value=value.replace(old[1],address)
            if family=='administrator_login':value=value.replace('81.2.69.192',src)
        elif sid=='barracuda':
            _,body=value.split(' WF ',1);fields=body.split(' ',5)
            fields[2]=src;fields[4]=dst
            value='<129>'+now.strftime('%Y-%m-%d %H:%M:%S.')+f'{now.microsecond//1000:03d} +0000  '+host+' WF '+' '.join(fields)
        elif sid=='oracle':
            # LENGTH and per-attribute byte lengths refer to the unchanged audit body.
            # No client address is present in this selected native record.
            value=now.strftime('%a %b %d %H:%M:%S %Y +00:00')+'\n'+value.split('\n',1)[1]
            src='0.0.0.0';dst=device.ip_address;protocol='SQL'
        elif sid=='darktrace':
            anchor=value.get('creationTime',value['time']);delta=int(now.timestamp()*1000)-anchor
            for key in ['creationTime','time']:
                if key in value:value[key]+=delta
            for component in value.get('triggeredComponents',[]):
                if 'time' in component:component['time']+=delta
            # Model modified time and device inventories are historical context.
        elif sid=='beyondtrust':
            value['CreateDate']=iso;value['IPAddress']=src
        elif sid=='tenable':
            value['received']=iso
            value['id']=uuid.uuid5(uuid.NAMESPACE_DNS,'tenable|'+device.id+'|'+family).hex
            for field in value.get('fields',[]):
                if field['key']=='X-Forwarded-For':field['value']=src
        elif sid=='ibmmq':
            value=re.sub(r'^\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}',now.strftime('%m/%d/%y %H:%M:%S'),value)
            value=re.sub(r'Time\([^)]+\)',lambda _:'Time('+iso+')',value)
            value=re.sub(r'Host\([^)]+\)',lambda _:'Host('+host+')',value);protocol='MQ'
        else:
            raise ValueError('No native renderer for source')
        raw=json.dumps(value,ensure_ascii=False,separators=(',',':')) if isinstance(value,dict) else value
        return LogEntry(timestamp=now.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3],device_id=device.id,
                        src_ip=src,dest_ip=dst,protocol=protocol,duration='0ms',action=selected['action'],
                        signature=family,status=selected['status'],raw_log=raw,node_type=device.type.value,
                        node_id=device.id,vendor=source['vendor'],sourcetype=sourcetype)


def run_batch3_scenario(scenario_id,run_id,tagger,source_ip='192.0.2.10',when=None):
    registry=batch_registry()
    if scenario_id not in registry['scenarios']:raise ValueError('Unsupported Batch 3 scenario')
    now=_now(when);records=[]
    for i,sid in enumerate(registry['scenarios'][scenario_id]):
        source=next(s for s in registry['sources'] if s['batch_source_id']==sid)
        device=Node(id='ub3-'+sid,name=sid+'-01.example.test',type=NodeType.ROUTER if sid=='pfsense' else NodeType.WEB_SERVER,ip_address='198.51.100.'+str(i+10))
        for family in source['event_families']:
            records.append(UniverseBatch3Engine.format_universe_batch3_log(device,source['splunk_sourcetype'],family,when=now,
                            src_ip=source_ip if family!='ipv6_udp_block' and sid!='oracle' else None))
    groups={phase:[] for phase in ['BASELINE','OBSERVE','VALIDATE']}
    for i,event in enumerate(records):groups[list(groups)[min(2,i*3//len(records))]].append(event)
    events=[event for phase,group in groups.items() for event in tagger(group,run_id,scenario_id,phase)]
    previous=None
    for event in events:event.netspout_parent_event_id=previous;previous=event.netspout_event_id
    return events
