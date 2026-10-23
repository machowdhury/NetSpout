"""Generate native discovery projection/views from existing catalogs, not a registry."""
import argparse
import json
from pathlib import Path
import re
import sys
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'netspout/appserver/static/discovery_catalog.json'


def read(path):
    return json.loads((ROOT / path).read_text())


def incident_contracts():
    """Read existing descriptors and bounded producers; never dispatch telemetry."""
    import importlib.util
    old_path = list(sys.path)
    try:
        sys.path.insert(0, str(ROOT / 'netspout/bin'))
        spec = importlib.util.spec_from_file_location('discovery_incident_producer', ROOT / 'netspout/bin/network_incidents.py')
        producer = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(producer)
        result = {}
        for item in read('netspout/appserver/static/scenarios_manifest.json'):
            descriptor = ROOT / 'netspout/appserver/static/scenarios' / item['filename']
            # Only the committed JSON-form incident descriptors are in this gate.
            text = descriptor.read_text()
            if not text.lstrip().startswith('{'):
                continue
            data = json.loads(text)
            slug = data.get('pulseforge_incident')
            if not slug:
                continue
            if slug not in producer.CATALOG and slug not in producer.telecom_incidents.CATALOG:
                raise ValueError('Unrecognized executable incident descriptor')
            events = producer.generate(slug, 42, 1792497600, '00112233-4455-6677-8899-aabbccddeeff', 10)
            logs = [e for e in events if 'metrics' not in e]
            metrics = [e for e in events if 'metrics' in e]
            definition = producer.CATALOG.get(slug, ())
            context = definition[13] if len(definition)>13 else {}
            result[item['id']] = dict(runtime_scenario_id=slug,
                domain=context.get('domain'), industry=context.get('industry'),
                modeled_products=context.get('products', []),
                external_use_cases=context.get('uc', []), proposal=context.get('proposal'),
                log_sourcetypes=sorted({e['sourcetype'] for e in logs}),
                metric_sourcetypes=sorted({e['sourcetype'] for e in metrics}),
                log_fields=sorted(set.intersection(*(set(e['fields']) for e in logs))),
                metric_names=sorted({k for e in metrics for k in e['metrics']}),
                entities=sorted({e['fields']['netspout_device_id'] for e in events}),
                field_provenance='netspout/bin/' + ('telecom_incidents.py' if slug.startswith('telco_') else 'network_incidents.py') + ': generate()')
        return result
    finally:
        sys.path[:] = old_path


def build():
    incidents = incident_contracts()
    vendors = read('catalog/vendors.json')
    sources = read('catalog/telemetry_catalog.json')
    profiles = [p for i in sources['integrations'] for p in i.get('profiles', [])]
    evidence = {e['evidence_id']: e for e in sources['evidence']}
    recipes = [r for r in read('catalog/dashboard_recipes.json')['recipes'] if r.get('native_view')]
    manifest = read('netspout/appserver/static/scenarios_manifest.json')
    canonical = {s['id']: s for s in read('catalog/scenarios.json')}
    vendor_names = {v['id']: v['name'] for v in vendors}
    sts = {}
    for st in read('catalog/sourcetypes.json'):
        name = st['splunk_sourcetype']
        contracts = [s for s in sources['sources'] if name in [t['name'] for t in s['splunk_contract']['sourcetypes']]]
        selected_profiles = [p for p in profiles if name in p.get('sourcetypes', [])]
        sts[name] = dict(kind='sourcetype', id=name, title=name, domain=st['category'],
            industries=['Cross-industry'], vendors=[vendor_names.get(st['vendor_id'], st['vendor_id'])],
            readiness='Evidence review required', description=st['display_name'],
            sourcetypes=[name], scenario_ids=[], dashboard_ids=[],
            formats=sorted({s['native_contract']['format'] for s in contracts}),
            profiles=selected_profiles,
            evidence=[evidence[e] for s in contracts for e in s.get('evidence_ids', []) if e in evidence],
            gaps=['Catalog identity is not proof of raw-event fidelity or selected-version TA parsing.']+
                 [gap for s in contracts for gap in s.get('known_limitations', [])])
    entries=[]
    ids=set()
    for record in manifest + [s for s in canonical.values() if s['id'] not in {m['id'] for m in manifest}]:
        sid=record['id']
        if sid in ids: raise ValueError('Duplicate scenario ID')
        ids.add(sid)
        c=canonical.get(sid, {})
        native = sid in incidents
        telco = sid.startswith('telco_')
        domain='Telecom' if telco else 'Network / infrastructure' if native else c.get('category', record.get('group','Other'))
        matching=[r for r in recipes if sid in r['selectors']]
        if sid in ('network_08_firewall_policy','network_09_ddos_flood'): domain='Security'
        if sid in ('network_10_dns_failure','network_15_device_resources'): domain='Cloud / application'
        domain=incidents.get(sid, {}).get('domain') or domain
        matching.sort(key=lambda r:(r['domain']!=domain,r['recipe_id']))
        names=record.get('sourcetypes',c.get('sourcetypes',[]))
        for name in names:
            if name not in sts:
                sts[name]=dict(kind='sourcetype',id=name,title=name,domain=domain,
                    industries=['Telecommunications' if telco else 'Cross-industry'],vendors=['PulseForge'],
                    readiness='Executable custom simulation' if native else 'Evidence review required',
                    description='Owned synthetic contract' if native else 'Scenario-declared sourcetype; evidence pending',
                    sourcetypes=[name],scenario_ids=[],dashboard_ids=[],formats=['PulseForge structured simulation'] if native else [],
                    profiles=[],evidence=[],gaps=['Not vendor-native or TA-verified.' if native else 'Raw format/parser verification not established.'])
            sts[name]['scenario_ids'].append(sid)
        row=dict(kind='scenario',id=sid,title=record.get('name',c.get('display_name',sid)),domain=domain,
            industries=[incidents.get(sid, {}).get('industry') or ('Telecommunications' if telco else 'Cross-industry')],
            vendors=sorted({v for name in names for v in sts[name]['vendors']}),
            readiness='Executable custom simulation' if native else 'Legacy / verification pending',
            description=record.get('description',c.get('description','')),sourcetypes=names,
            scenario_ids=[sid],dashboard_ids=[r['recipe_id'] for r in matching],
            required_telemetry=c.get('use_case',{}).get('required_telemetry',names),
            gaps=['Vendor-native telemetry is not established by this custom incident pack.'] if native else ['Execution and parser compatibility require separate validation.'],
            objective=c.get('use_case',{}).get('objective',record.get('description','')),
            filename=record.get('filename'),evidence=[])
        if native:
            contract = incidents[sid]
            if not matching:
                raise ValueError('Executable incident has no primary dashboard')
            primary = matching[0]
            if not set(primary['required_sourcetypes']) <= set(contract['log_sourcetypes']):
                raise ValueError('Dashboard requires unavailable log sourcetypes')
            if not set(primary['required_fields']) <= set(contract['log_fields']):
                raise ValueError('Dashboard requires unavailable event fields')
            row.update(executable=True, incident_contract=contract, modeled_products=contract['modeled_products'],
                       primary_dashboard_id=primary['recipe_id'],
                       required_fields=primary['required_fields'],
                       field_provenance=primary['field_provenance'],
                       telemetry_status='NOT_CHECKED',
                       prerequisites=['Local indexed event data with extracted structured fields; run and scenario IDs must survive collection.',
                                      'KPI panels require the configured local Splunk metrics index and HEC metric dimensions. Logs-only destinations cannot supply metric panels.'])
        else:
            row['executable'] = False  # not assessed by the committed incident gate
        entries.append(row)
    for r in recipes:
        if not set(r['selectors']) <= ids: raise ValueError('Dashboard selector missing from scenario catalog')
        entries.append(dict(kind='dashboard',id=r['recipe_id'],title=r['title'],domain=r['domain'],
            industries=r['industries'],vendors=['PulseForge'],readiness='Definition ready / data not checked',
            description=r['purpose'],sourcetypes=r['required_sourcetypes'],scenario_ids=r['selectors'],
            dashboard_ids=[r['recipe_id']],view=r['native_view'],required_fields=r['required_fields'],
            metric_sourcetypes=r.get('metric_sourcetypes', []), field_provenance=r.get('field_provenance', {}), data_status='NOT_CHECKED',gaps=['Installed Splunk rendering/search and field extraction are unverified.'],evidence=[]))
        for name in r['required_sourcetypes'] + r.get('metric_sourcetypes', []):
            sts[name]['dashboard_ids'].append(r['recipe_id'])
    entries += list(sts.values())
    # Read-only projection of the approved research; no import into schema claims.
    for line in (ROOT/'docs/catalog/EXTERNAL_USE_CASE_MAPPING.md').read_text().splitlines():
        if not line.startswith('| [UC-'): continue
        cells=[c.strip() for c in line.strip('|').split('|')]
        match=re.match(r'\[UC-([^]]+)\]\(([^)]+)\) — (.*)',cells[0])
        uid,url,title=match.groups()
        related=[]
        for prefix,num in re.findall(r'\b([NT])(\d{2})\b',cells[4]):
            related += [sid for sid in ids if sid.startswith(('network_' if prefix=='N' else 'telco_')+num+'_')]
        related += [sid for sid,c in incidents.items() if uid in c.get('external_use_cases', [])]
        entries.append(dict(kind='use_case',id='UC-'+uid,title=title,domain=cells[1].split('/')[0].strip(),
            industries=[cells[1].split('/',1)[1].strip()] if '/' in cells[1] else ['Cross-industry'],
            vendors=[],readiness=cells[7],description=cells[2],required_telemetry=[cells[3]],
            sourcetypes=[],scenario_ids=sorted(set(related)),dashboard_ids=sorted({d for s in entries if s['kind']=='scenario' and s['id'] in related for d in s['dashboard_ids']}),
            gaps=[cells[5], 'External TA/CIM claims require independent validation: '+cells[6]],
            evidence=[dict(title='Attributed external UC; research only',reference=url)],behavior=cells[8]))
    return dict(schema_version=1, executable_incident_count=len(incidents), provenance='Generated from canonical catalogs, native manifest and approved research; never edit projection.',entries=entries)


def dashboard_xml(recipe):
    contracts = incident_contracts()
    selected = [contracts[sid] for sid in recipe['selectors']]
    form=ET.Element('form', {'version':'1.1','theme':'dark'})
    ET.SubElement(form,'label').text='PulseForge — '+recipe['title']
    ET.SubElement(form,'description').text=recipe['purpose']+' Local indexed synthetic data only. KPI panels require HEC metrics and retained dimensions. Empty KPI results mean unavailable data, not zero impact. VERIFIED_HEALTHY is a simulated phase, not indexing verification. Remote destination data is not searched.'
    fs=ET.SubElement(form,'fieldset',{'submitButton':'true','autoRun':'false'})
    for token,label,default in [('index','Local event index','idx_network_ops'),('metric_index','Local metrics index','idx_performance_metrics'),('run_id','Server-owned run UUID',None),('entity','Device ID (* means all)','*')]:
        inp=ET.SubElement(fs,'input',{'type':'text','token':token});ET.SubElement(inp,'label').text=label
        if default: ET.SubElement(inp,'default').text=default
    for token,label,choices in [('scenario_id','Scenario',sorted({c['runtime_scenario_id'] for c in selected})),('log_source','Log sourcetype',recipe['required_sourcetypes'])]:
        inp=ET.SubElement(fs,'input',{'type':'dropdown','token':token});ET.SubElement(inp,'label').text=label
        if token=='scenario_id': ET.SubElement(inp,'choice',{'value':'*'}).text='All scenarios in this dashboard'
        for value in choices: ET.SubElement(inp,'choice',{'value':value}).text=value
        ET.SubElement(inp,'default').text='*' if token=='scenario_id' else choices[0]
    timer=ET.SubElement(fs,'input',{'type':'dropdown','token':'window'})
    ET.SubElement(timer,'label').text='Bounded time range'
    for value,label in [('-15m','Last 15 minutes'),('-1h','Last hour'),('-24h','Last 24 hours'),('-7d','Last 7 days')]:
        ET.SubElement(timer,'choice',{'value':value}).text=label
    ET.SubElement(timer,'default').text='-24h'
    html=ET.SubElement(ET.SubElement(ET.SubElement(form,'row'),'panel'),'html')
    ET.SubElement(html,'a',{'href':'pulseforge_discovery?q='+recipe['required_sourcetypes'][0]}).text='Back to discovery — related scenarios and telemetry prerequisites'
    # Every free-text token is escaped by Splunk's string token filter.
    source=' OR '.join('sourcetype="'+v+'"' for v in recipe['required_sourcetypes'])
    scenario=' OR '.join('netspout_scenario_id="'+c['runtime_scenario_id']+'"' for c in selected)
    base='search index=$index|s$ ('+source+') ('+scenario+') sourcetype=$log_source|s$ netspout_run_id=$run_id|s$ netspout_scenario_id=$scenario_id|s$ netspout_device_id=$entity|s$'
    fields=recipe['required_fields']
    counts=' '.join('count('+f+') as present_'+f for f in fields)
    checks=' AND '.join('present_'+f+'=observed_records' for f in fields)
    phase_order='BASELINE WARNING DEGRADATION FAILURE NETWORK_IMPACT USER_IMPACT INTERVENTION RECOVERY RECONVERGENCE VERIFIED_HEALTHY'.split()
    order='case('+','.join('netspout_phase="'+phase+'",'+str(i) for i,phase in enumerate(phase_order))+')'
    metric_source=' OR '.join('sourcetype="'+v+'"' for v in recipe.get('metric_sourcetypes', []))
    metric='| mstats avg(_value) as simulated_value WHERE metric_name=* index=$metric_index|s$ ('+metric_source+') ('+scenario+') netspout_run_id=$run_id|s$ netspout_scenario_id=$scenario_id|s$ netspout_device_id=$entity|s$ BY metric_name netspout_scenario_id netspout_phase netspout_device_id span=1s'
    panels=[('Data / field readiness (not delivery proof)',base+' | stats count as observed_records '+counts+' | eval data_status=case(observed_records=0,"MISSING_DATA",'+checks+',"FIELDS_PRESENT",1=1,"MISSING_FIELDS")'),
        ('Incident start, duration and affected entities',base+' | stats min(_time) as first_observation max(_time) as last_observation dc(netspout_device_id) as observed_entities min(eval(if(netspout_phase="FAILURE",_time,null()))) as first_failure by netspout_incident_id netspout_scenario_id | eval observed_span_seconds=last_observation-first_observation | convert ctime(first_observation) ctime(last_observation) ctime(first_failure)'),
        ('Impact and recovery by phase — synthetic severity (lower is worse)',base+' | stats min(severity) as most_severe dc(netspout_device_id) as observed_entities min(_time) as phase_start max(_time) as phase_end by netspout_scenario_id netspout_phase | eval phase_order='+order+' | sort 0 netspout_scenario_id phase_order'),
        ('Simulated KPI progression — missing rows are not zero',metric+' | eval phase_order='+order+' | sort 0 netspout_scenario_id metric_name phase_order _time'),
        ('Correlated supporting observations (maximum 500)',base+' | sort 0 _time | head 500 | table _time netspout_incident_id netspout_scenario_id netspout_phase netspout_device_id severity _raw')]
    if recipe['recipe_id']=='discovery-telecom':
        panels.insert(3,('Synthetic service/cohort impact — do not sum repeated observer counts',base+' | stats max(affected_synthetic_subscribers) as affected_synthetic_cohort values(netspout_device_id) as observed_devices by netspout_scenario_id netspout_service_id netspout_phase | eval phase_order='+order+' | sort 0 netspout_scenario_id phase_order'))
    for title,query in panels:
        panel=ET.SubElement(ET.SubElement(form,'row'),'panel');ET.SubElement(panel,'title').text=title
        table=ET.SubElement(panel,'table');search=ET.SubElement(table,'search')
        ET.SubElement(search,'query').text=query;ET.SubElement(search,'earliest').text='$window$';ET.SubElement(search,'latest').text='now'
        ET.SubElement(table,'option',{'name':'count'}).text='20'
    ET.indent(form)
    return ET.tostring(form,encoding='unicode')+'\n'


def generate(check=False):
    outputs={DEST:json.dumps(build(),indent=2,ensure_ascii=False)+'\n'}
    recipes=read('catalog/dashboard_recipes.json')['recipes']
    for r in recipes:
        if r.get('native_view'):
            outputs[ROOT/'netspout/default/data/ui/views'/ (r['native_view']+'.xml')]=dashboard_xml(r)
    for p,text in outputs.items():
        if check:
            if not p.exists() or p.read_text()!=text: raise ValueError('Discovery projection drift: '+str(p))
        else: p.write_text(text)
    return outputs

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true')
    args=parser.parse_args();generate(args.check)
