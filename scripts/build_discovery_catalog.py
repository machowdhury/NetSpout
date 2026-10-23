"""Generate native discovery projection/views from existing catalogs, not a registry."""
import argparse
import json
from pathlib import Path
import re
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / 'netspout/appserver/static/discovery_catalog.json'


def read(path):
    return json.loads((ROOT / path).read_text())


def build():
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
        native = sid.startswith(('network_', 'telco_'))
        telco = sid.startswith('telco_')
        domain='Telecom' if telco else 'Network / infrastructure' if native else c.get('category', record.get('group','Other'))
        matching=[r for r in recipes if sid in r['selectors']]
        if sid in ('network_08_firewall_policy','network_09_ddos_flood'): domain='Security'
        if sid in ('network_10_dns_failure','network_15_device_resources'): domain='Cloud / application'
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
            industries=['Telecommunications' if telco else 'Cross-industry'],
            vendors=sorted({v for name in names for v in sts[name]['vendors']}),
            readiness='Executable custom simulation' if native else 'Legacy / verification pending',
            description=record.get('description',c.get('description','')),sourcetypes=names,
            scenario_ids=[sid],dashboard_ids=[r['recipe_id'] for r in matching],
            required_telemetry=c.get('use_case',{}).get('required_telemetry',names),
            gaps=['Vendor-native telemetry is not established by this custom incident pack.'] if native else ['Execution and parser compatibility require separate validation.'],
            objective=c.get('use_case',{}).get('objective',record.get('description','')),
            filename=record.get('filename'),evidence=[])
        entries.append(row)
    for r in recipes:
        if not set(r['selectors']) <= ids: raise ValueError('Dashboard selector missing from scenario catalog')
        entries.append(dict(kind='dashboard',id=r['recipe_id'],title=r['title'],domain=r['domain'],
            industries=r['industries'],vendors=['PulseForge'],readiness='Definition ready / data not checked',
            description=r['purpose'],sourcetypes=r['required_sourcetypes'],scenario_ids=r['selectors'],
            dashboard_ids=[r['recipe_id']],view=r['native_view'],required_fields=r['required_fields'],
            data_status='NOT_CHECKED',gaps=['Installed Splunk rendering/search and field extraction are unverified.'],evidence=[]))
        for name in r['required_sourcetypes']:
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
        entries.append(dict(kind='use_case',id='UC-'+uid,title=title,domain=cells[1].split('/')[0].strip(),
            industries=[cells[1].split('/',1)[1].strip()] if '/' in cells[1] else ['Cross-industry'],
            vendors=[],readiness=cells[7],description=cells[2],required_telemetry=[cells[3]],
            sourcetypes=[],scenario_ids=sorted(set(related)),dashboard_ids=sorted({d for s in entries if s['kind']=='scenario' and s['id'] in related for d in s['dashboard_ids']}),
            gaps=[cells[5], 'External TA/CIM claims require independent validation: '+cells[6]],
            evidence=[dict(title='Attributed external UC; research only',reference=url)],behavior=cells[8]))
    return dict(schema_version=1,provenance='Generated from canonical catalogs, native manifest and approved research; never edit projection.',entries=entries)


def dashboard_xml(recipe):
    form=ET.Element('form', {'version':'1.1','theme':'dark'})
    ET.SubElement(form,'label').text='PulseForge — '+recipe['title']
    ET.SubElement(form,'description').text=recipe['purpose']+' Local indexed data only. Choose the configured event index and server-owned run ID. Remote destinations may have no data here. VERIFIED_HEALTHY is a simulated phase, not independent indexing verification.'
    fs=ET.SubElement(form,'fieldset',{'submitButton':'true','autoRun':'false'})
    for token,label,default in [('index','Local event index','idx_network_ops'),('run_id','Server-owned run ID',None)]:
        inp=ET.SubElement(fs,'input',{'type':'text','token':token});ET.SubElement(inp,'label').text=label
        if default: ET.SubElement(inp,'default').text=default
    source=' OR '.join('sourcetype="'+s+'"' for s in recipe['required_sourcetypes'])
    # |s escapes token values as SPL strings; no arbitrary SPL from URL/input.
    base='search index=$index|s$ ('+source+') netspout_run_id=$run_id|s$'
    fields=recipe['required_fields']
    counts=' '.join('count('+f+') as present_'+f for f in fields)
    checks=' AND '.join('present_'+f+'=observed_records' for f in fields)
    panels=[('Data / field readiness (not delivery proof)',base+' | stats count as observed_records '+counts+' | eval data_status=case(observed_records=0,"MISSING_DATA",'+checks+',"FIELDS_PRESENT",1=1,"MISSING_FIELDS")'),
            ('Observed records by incident phase',base+' | stats count as observed_records by netspout_scenario_id netspout_phase netspout_device_id'),
            ('Indexed observation timeline',base+' | sort 0 _time | head 500 | table _time netspout_run_id netspout_scenario_id netspout_phase netspout_device_id _raw')]
    for title,query in panels:
        panel=ET.SubElement(ET.SubElement(form,'row'),'panel');ET.SubElement(panel,'title').text=title
        table=ET.SubElement(panel,'table');search=ET.SubElement(table,'search')
        ET.SubElement(search,'query').text=query;ET.SubElement(search,'earliest').text='-24h';ET.SubElement(search,'latest').text='now'
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
