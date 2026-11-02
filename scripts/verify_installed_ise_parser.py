"""Actual bounded installed-TA parser, timestamp, lookup and raw-stream breaking check.

Uses only the already-installed ISE TA and existing isolated HEC input. No TA
installation, configuration, lookup modification or eval/rex parser substitute.
"""
import hashlib
import argparse
import time
import json
from pathlib import Path
import re
import subprocess
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from verify_universe_raw_live import CONTAINER_CODE

PARSER_CODE=r'''
import csv, pathlib, hashlib, time
from datetime import datetime
ise=pathlib.Path('/opt/splunk/etc/apps/Splunk_TA_cisco-ise')
lookup=ise/'lookups/cisco_ise_message_catalog_500.csv'
with lookup.open() as handle:lookup_rows=list(csv.DictReader(handle))
lookup_by_code={row['MESSAGE_CODE']:row for row in lookup_rows}
start=payload['submitted_at_epoch']
raw_source=payload['source']+':raw-stream'
if not payload.get('resume',False):
    for event in payload['events']:
        response=json.loads(request('/services/collector/event',json.dumps(event).encode(),token))
        if response.get('code')!=0:raise RuntimeError('Installed parser test HEC event rejected; no repost')
    query_args=urllib.parse.urlencode(dict(index='idx_ta_ise_test',sourcetype='cisco:ise:syslog',source=raw_source,host='ise-parser-test'))
    raw_data=('\n'.join(payload['raw_stream'])+'\n').encode()
    req=urllib.request.Request('https://127.0.0.1:8088/services/collector/raw?'+query_args,data=raw_data,
                              headers={'Authorization':'Splunk '+token,'Content-Type':'text/plain','X-Splunk-Request-Channel':payload['channel']})
    with urllib.request.urlopen(req,context=ctx,timeout=15) as response:raw_response=json.loads(response.read())
    if raw_response.get('code')!=0:raise RuntimeError('Installed parser test HEC raw stream rejected; no repost')
query=('search index=idx_ta_ise_test earliest='+str(int(start)-60)+' latest='+str(int(start)+120)+' source="'+payload['source']+'*" '
       '| eval parser_event_epoch=_time | table _raw parser_event_epoch _time _indextime source sourcetype MESSAGE_CODE x_status user src_ip src_mac '
       'MESSAGE_CLASS MESSAGE_TEXT vendor product vendor_product eventtype netspout_run_id')
rows=[]
for attempt in range(12):
    body=urllib.parse.urlencode(dict(search=query,output_mode='json',preview='false')).encode()
    output=request('/services/search/jobs/export',body)
    rows=[j['result'] for line in output.splitlines() if line.strip() for j in [json.loads(line)] if 'result' in j]
    if len(rows)>=len(payload['events'])+len(payload['raw_stream']):break
    time.sleep(2)
checks=[]
for expected in payload['expected']:
    matches=[row for row in rows if row.get('_raw')==expected['raw']]
    row=matches[0] if len(matches)==1 else {}
    actual_code=str(row.get('MESSAGE_CODE',''))
    field_checks={key:row.get(key)==value for key,value in expected['fields'].items()}
    native_lookup=lookup_by_code.get(expected['fields']['MESSAGE_CODE'])
    lookup_checks={key:row.get(key)==native_lookup.get(key) for key in ['MESSAGE_CLASS','MESSAGE_TEXT']} if native_lookup else {}
    timestamp=float(row.get('parser_event_epoch',0))
    received=float(row.get('_indextime',0))
    current_time_ok=(start-5<=timestamp<=start+60 and abs(timestamp-received)<15)
    checks.append(dict(label=expected['label'],framing=expected['framing'],matches=len(matches),
                       expected_fields=expected['fields'],actual_fields={k:row.get(k) for k in ['MESSAGE_CODE','x_status','user','src_ip','src_mac','MESSAGE_CLASS','MESSAGE_TEXT','vendor','product','eventtype']},
                       field_checks=field_checks,lookup_checks=lookup_checks,lookup_reference=native_lookup,
                       lookup_status='VERIFIED' if native_lookup and all(lookup_checks.values()) else 'NO_LOOKUP_ROW' if not native_lookup else 'FAILED',
                       timestamp_check=dict(expected='DATETIME_CONFIG=CURRENT',actual_time=timestamp,index_time=received,ok=current_time_ok),
                       raw_sha256=hashlib.sha256(expected['raw'].encode()).hexdigest(),
                       indexed_sha256=hashlib.sha256(row.get('_raw','').encode()).hexdigest(),
                       verdict='PASS' if len(matches)==1 and all(field_checks.values()) and all(lookup_checks.values()) and current_time_ok else 'FAIL'))
raw_rows=[row for row in rows if row.get('source')==raw_source]
event_breaking=dict(method='One HEC /raw POST containing two newline-delimited ISE records; installed SHOULD_LINEMERGE=false',
                    expected_events=2,actual_events=len(raw_rows),exact_records=sorted(row['_raw'] for row in raw_rows)==sorted(payload['raw_stream']))
result=dict(run_id=payload['run_id'],resumed_without_reingestion=bool(payload.get('resume')),source=payload['source'],index='idx_ta_ise_test',ta='Splunk_TA_cisco-ise',version='5.0.0',
            sourcetype='cisco:ise:syslog',hec_event_posts=len(payload['events']),hec_raw_posts=1,indexed_events=len(rows),
            checks=checks,passes=sum(check['verdict']=='PASS' for check in checks),event_breaking=event_breaking,
            lookup_sha256=hashlib.sha256(lookup.read_bytes()).hexdigest(),search_attempts=attempt+1,query=query,
            verified_sourcetypes=['cisco:ise:syslog'] if all(check['verdict']=='PASS' for check in checks) and event_breaking['exact_records'] else [],
            parser_execution='INSTALLED_SPLUNK_TA_SEARCH_TIME_EXTRACTIONS_AND_LOOKUPS',configuration_changes=0,packages_installed=0,
            note='All checks scoped to tested records. Eventtypes reported, not used as detection validation. HEC event posts alone are not event-breaking evidence.')
print(json.dumps(result))
'''


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--resume',action='store_true');args=parser.parse_args()
    from netspout_core.models import Node
    from netspout_core.log_engine import SplunkLogEngine as E
    run_id='pf-ub3-ise-parser-'+str(uuid.uuid4());source='pulseforge:ta-parser:'+run_id
    records=[]
    lines=(ROOT/'netspout/samples/cisco_ise_syslog.sample').read_text().splitlines()
    expected_originals=[(104,'58005','system','127.0.0.1'),(17,'5201','splunk','10.0.10.104'),(1,'5400','assiutdotcom','45.149.145.155'),(2,'11036','CTS client','10.0.10.9'),(134,'3302','intersight','10.0.10.3')]
    for line,code,user,ip in expected_originals:
        records.append(dict(label=f'original-line-{line}',raw=lines[line-1],fields={'MESSAGE_CODE':code,'user':user,'src_ip':ip}))
    device=Node(id='parser-ise',name='ise-parser.example.test',ip_address='198.51.100.20')
    for action,code in [('allowed','5200'),('blocked','5400')]:
        event=E.format_cisco_ise_log(device,user='parser.training',client_ip='192.0.2.50',action=action)
        records.append(dict(label='current-generator-'+code,raw=event.raw_log,fields={'MESSAGE_CODE':code,'user':'parser.training','src_ip':'192.0.2.50'}))
    coa=E.format_cisco_ise_coa_log(device,'00:1a:2b:3c:4d:5e','192.0.2.50','parser.training','training-profile','allowed','normal','CoA observation')
    records.append(dict(label='current-generator-5205',raw=coa.raw_log,fields={'MESSAGE_CODE':'5205','user':'parser.training','src_mac':'00:1a:2b:3c:4d:5e'}))
    raw_stream=[];raw_expected=[]
    for record in records[5:7]:
        old=re.sub(r'<181>\w{3}\s+\d+ \d{2}:\d{2}:\d{2}','<181>Jan  1 01:02:03',record['raw'])
        old=re.sub(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+ \+00:00','2001-01-01 01:02:03.004 +00:00',old)
        raw_stream.append(old);raw_expected.append({**record,'label':'raw-stream-old-time-'+record['fields']['MESSAGE_CODE'],'raw':old,'framing':'HEC_RAW_STREAM'})
    events=[dict(event=record['raw'],sourcetype='cisco:ise:syslog',source=source,index='idx_ta_ise_test',fields={'netspout_run_id':run_id}) for record in records]
    expected=[{**record,'framing':'HEC_EVENT'} for record in records]+raw_expected
    payload=dict(run_id=run_id,source=source,events=events,raw_stream=raw_stream,expected=expected,channel=str(uuid.uuid4()))
    stored=ROOT/'docs/verification/universe_batch3/ise_parser_submitted.json'
    if args.resume:
        payload=json.loads(stored.read_text())
        payload['submitted_at_epoch']=payload.get('submitted_at_epoch',stored.stat().st_mtime)
        payload['resume']=True
        expected=payload['expected']
    else:
        payload['submitted_at_epoch']=time.time()
    code=CONTAINER_CODE.split('apps = json.loads')[0]+PARSER_CODE
    program='PAYLOAD_JSON='+repr(json.dumps(payload))+'\nimport json,traceback\ntry:\n'+'\n'.join('    '+line for line in code.splitlines())+'\nexcept Exception as exc:\n    print(json.dumps({"error_type":type(exc).__name__,"status":getattr(exc,"code",None),"line":traceback.extract_tb(exc.__traceback__)[-1].lineno}))'
    out=ROOT/'docs/verification/universe_batch3';out.mkdir(parents=True,exist_ok=True)
    (out/'ise_parser_submitted.json').write_text(json.dumps(payload,indent=2)+'\n')
    proc=subprocess.run(['docker','exec','--user','0','-i','pf-native-lab','/usr/bin/python3','-'],input=program,text=True,capture_output=True,timeout=240)
    if proc.returncode:raise RuntimeError('Installed-TA test execution failed; no credential-bearing stderr emitted')
    result=json.loads(proc.stdout)
    if 'error_type' in result:raise RuntimeError('Sanitized parser diagnostic: '+json.dumps(result))
    import ast
    tree=ast.parse((ROOT/'src/netspout_core/log_engine.py').read_text())
    methods=[ast.dump(node,include_attributes=False) for node in ast.walk(tree) if isinstance(node,ast.FunctionDef) and node.name in {'format_cisco_ise_log','format_cisco_ise_coa_log'}]
    result['generator_method_ast_sha256']=hashlib.sha256('\n'.join(methods).encode()).hexdigest()
    existing=ROOT/'catalog/universe_batch3_ise_parser_results.json'
    if args.resume and existing.is_file():
        previous=json.loads(existing.read_text())
        if previous.get('run_id')==result['run_id'] and 'reporting_attempts' in previous:
            result['reporting_attempts']=previous['reporting_attempts']
    result['overall_status']='VERIFIED_TESTED_SCOPE' if result['passes']==len(expected) else 'PARTIAL_WITH_COMPATIBILITY_BLOCKER'
    result['blocked_cases']=[check['label'] for check in result['checks'] if check['verdict']=='FAIL']
    result['new_verified_sourcetypes']=0
    result['generator_sha256']=hashlib.sha256((ROOT/'src/netspout_core/log_engine.py').read_bytes()).hexdigest()
    out=ROOT/'docs/verification/universe_batch3';out.mkdir(parents=True,exist_ok=True)
    (out/'ise_parser_submitted.json').write_text(json.dumps(payload,indent=2)+'\n')
    (ROOT/'catalog/universe_batch3_ise_parser_results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['run_id','indexed_events','passes','verified_sourcetypes','event_breaking']}))
    return 0 if result['passes']==len(expected) and result['event_breaking']['exact_records'] else 1

if __name__=='__main__':raise SystemExit(main())
