"""Graduate only selected fixture-backed Batch 2 sources; rebuild offline, idempotently."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'catalog'
CORPUS = CATALOG / 'raw_reference/universe_batch2'

# Technology identity is separate from the publisher in the frozen Splunkbase metadata.
SPECS = [
 ('vault', 'hashicorp', 'HashiCorp', 'Vault audit', 'hashicorp_vault_audit_log', 'Cloud & Secrets Management', 5093),
 ('traefik', 'traefik', 'Traefik Labs', 'Traefik Proxy access', 'traefik:access:json', 'Networking & Observability', 6733),
 ('claroty', 'claroty', 'Claroty', 'CTD CEF', 'claroty:cef', 'OT & ICS Security', 5450),
 ('mongodb', 'mongodb', 'MongoDB', 'MongoDB structured server log', 'mongodb:log', 'Database Infrastructure', None),
 ('confluence', 'atlassian', 'Atlassian', 'Confluence Cloud audit', 'Confluence:audit log', 'SaaS Audit', 8784),
 ('nginx', 'nginx_f5', 'NGINX (F5)', 'NGINX combined access log', 'nginx:access', 'Web Observability', None),
 ('proofpoint', 'proofpoint', 'Proofpoint', 'Targeted Attack Protection SIEM', 'proofpoint_tap_siem', 'Email Security SaaS', 3681),
 ('veeam', 'veeam', 'Veeam', 'Backup & Replication', 'veeam_vbr_syslog', 'Backup Infrastructure', 7786),
 ('mikrotik', 'mikrotik', 'MikroTik', 'RouterOS console log', 'mikrotik:routeros', 'Carrier & Enterprise Routing', 3845),
]
SCENARIO_SOURCES = {
 'ub2_cloud_identity_mail_hunt': ['vault', 'confluence', 'proofpoint'],
 'ub2_ot_edge_routing_observation': ['mikrotik', 'traefik', 'claroty', 'nginx'],
 'ub2_database_backup_integrity': ['mongodb', 'veeam'],
}


def load(path):
    return json.loads(path.read_text())


def dump(path, data):
    path.write_text(json.dumps(data, indent=1) + '\n')


def fixture_lines(name):
    return (CORPUS / f'{name}.bin').read_text().splitlines()


def templates():
    def jl(name):
        return [json.loads(line) for line in fixture_lines(name) if line.strip()]
    def family(name, value, origin, selector, action='observed', status='normal'):
        return dict(id=name, template=value, origin=origin, selector=selector, action=action, status=status)
    claroty = load(CORPUS / 'claroty.bin')['events']
    return {
     'vault': [family('audit_request', jl('vault')[0], 'vault', 'line:1'), family('audit_response', jl('vault')[1], 'vault', 'line:2')],
     'traefik': [family('http_access', jl('traefik')[1], 'traefik', 'line:2', 'allowed')],
     'claroty': [family('new_asset', claroty[1]['event']['original'], 'claroty', 'events[1].event.original', 'alerted', 'breached'),
                 family('asset_information_change', claroty[3]['event']['original'], 'claroty', 'events[3].event.original', 'alerted', 'degraded'),
                 family('health', claroty[4]['event']['original'], 'claroty', 'events[4].event.original')],
     'mongodb': [family('server_start', jl('mongodb')[0], 'mongodb', 'line:1'), family('index_build', jl('mongodb')[4], 'mongodb', 'line:5')],
     'confluence': [family('space_created', jl('confluence')[4], 'confluence', 'line:5'), family('group_membership_added', jl('confluence')[7], 'confluence', 'line:8')],
     'nginx': [family('http_access', fixture_lines('nginx')[0], 'nginx', 'line:1', 'allowed')],
     'proofpoint': [family('malware_message_blocked', jl('proofpoint')[0], 'proofpoint', 'line:1', 'blocked', 'breached'), family('phishing_message_blocked', jl('proofpoint')[3], 'proofpoint', 'line:4', 'blocked', 'breached')],
     'veeam': [family('backup_job_started', fixture_lines('veeam')[12], 'veeam', 'line:13'), family('backup_job_completed', fixture_lines('veeam')[15], 'veeam', 'line:16'), family('malware_detected', fixture_lines('veeam_malware')[13], 'veeam_malware', 'line:14', 'alerted', 'breached')],
     'mikrotik': [family('administrator_login', fixture_lines('mikrotik')[0], 'mikrotik', 'line:1'), family('ospf_hello_sent', fixture_lines('mikrotik')[1], 'mikrotik', 'line:2')],
    }


def main():
    references = load(CORPUS / 'references.json')
    ref_by_id = {r['id']: r for r in references}
    for ref in references:
        data = (ROOT / ref['raw_reference_file']).read_bytes()
        if hashlib.sha256(data).hexdigest() != ref['sha256'] or len(data) != ref['bytes']:
            raise ValueError(f'Fixture integrity failed: {ref["id"]}')
    snapshot = load(CATALOG / 'vendor_universe/splunkbase_apps_snapshot.json')
    apps = {a['uid']: a for a in snapshot['rows']}
    canon_vendors = load(CATALOG / 'vendors.json')
    canon_sts = load(CATALOG / 'sourcetypes.json')
    canon_scenarios = load(CATALOG / 'scenarios.json')
    source_templates = templates()
    sources = []
    for source_id, vendor_id, vendor_name, product, st, category, uid in SPECS:
        app = apps[uid] if uid else None
        declared = bool(app and st in {t for ts in app['rel_tags_st'].values() for t in ts})
        sources.append(dict(batch_source_id=source_id, vendor=vendor_id, product=product,
                            splunk_sourcetype=st, generator='format_universe_batch2_log',
                            event_families=[f['id'] for f in source_templates[source_id]],
                            event_family_count=len(source_templates[source_id]),
                            families=source_templates[source_id],
                            evidence_level=ref_by_id[source_id]['evidence_level'],
                            ta_metadata=dict(uid=uid, name=app['name'] if app else None,
                                             publisher=app['author'] if app else None,
                                             version=app['rel_version'] if app else None,
                                             sourcetype_declared_in_snapshot=declared,
                                             authority='SPLUNKBASE_METADATA' if declared else 'PULSEFORGE_DEFINED_PENDING_TA_MAPPING',
                                             parser_verified=False,
                                             blocker='Installed TA and controlled parser check unavailable; declared sourcetype does not prove input-format compatibility.'),
                            raw_evidence=sorted({ref_by_id[f['origin']]['raw_reference_file'] for f in source_templates[source_id]})))
        vendor = dict(id=vendor_id, legacy_id=vendor_id, name=vendor_name, slug=vendor_id,
                      category=category, splunk_app_name=app['name'] if app else 'Mapping pending',
                      splunkbase_id=str(uid) if uid else '', splunkbase_url=app['url'] if app else '',
                      doc_url=ref_by_id[source_id]['url'], supported_device_types=['router' if source_id=='mikrotik' else 'web_server'],
                      supported_protocols=['hec'], header_type='Vendor-native documented payload', delimiter='',
                      timestamp_format='Source-specific UTC or native console time', cim_models=[], field_mappings={},
                      sample_events=[], primary_sourcetypes=[st])
        st_row = dict(id=st.lower().replace(':','-').replace(' ','-'), splunk_sourcetype=st,
                      display_name=product, vendor_id=vendor_id, category=category, data_kind='event',
                      default_index='idx_network_ops', recommended_index='netops_logs', generation_mode='STATEFUL',
                      protocol='hec', sample_file=None, required_ta=app['name'] if app else 'Mapping pending',
                      aliases=[st], deprecated_aliases=[], is_benchmark_197=False, status='active')
        canon_vendors = [v for v in canon_vendors if v['id'] != vendor_id] + [vendor]
        canon_sts = [s for s in canon_sts if s['splunk_sourcetype'] != st] + [st_row]
    for sid, ids in SCENARIO_SOURCES.items():
        sts = [s['splunk_sourcetype'] for s in sources if s['batch_source_id'] in ids]
        vendors = [s['vendor'] for s in sources if s['batch_source_id'] in ids]
        row = dict(id=sid, code='SEC-UB2-'+str(list(SCENARIO_SOURCES).index(sid)+1).zfill(2),
                   name=sid.replace('_',' ').title(), display_name=sid.replace('_',' ').title(),
                   category='SECURITY' if 'hunt' in sid else 'INFRASTRUCTURE', ecosystem='mixed_vendor',
                   maturity='CONTRACTED', description='Executable observation sequence from pinned native RAW fixtures. Correlation stays on HEC fields; no detection efficacy or real causality claimed.',
                   generation_mode='SCENARIO_DERIVED', generation_modes=['SCENARIO_DERIVED'], sourcetypes=sts,
                   default_topology_id='mixed_sase', topology_id='mixed_sase', difficulty='ADVANCED',
                   estimated_duration_sec=40, vendor_scope=vendors, telemetry_requirements=['hec_event'],
                   affected_entities=['mixed_sase'], expected_observations=[f'{s["product"]}: {", ".join(s["event_families"])}' for s in sources if s['batch_source_id'] in ids],
                   expected_phases=['baseline','observe','validate'],
                   phases=[dict(phase=p, name=p.title(), duration_ticks=1, description='Fixture-backed native source observation') for p in ['BASELINE','OBSERVE','VALIDATE']],
                   registry_reference='catalog/universe_batch2.json')
        canon_scenarios = [s for s in canon_scenarios if s['id'] != sid] + [row]
    queue = load(CATALOG / 'vendor_universe/batch2_candidate_queue_baseline.json')
    implemented = {s['vendor'] for s in sources}
    registry = dict(schema_version='1.0', registry_version='universe-batch2-2026-10-26',
                    baseline_commit=queue['baseline_commit'], baseline_counts=dict(vendors=57,sourcetypes=317,scenarios=41),
                    sources=sources, scenarios=SCENARIO_SOURCES,
                    counts_summary=dict(new_canonical_vendors=9,new_product_integrations=9,new_canonical_sourcetypes=9,
                                        event_families=sum(s['event_family_count'] for s in sources), scenario_packs=3),
                    candidate_queue=[{**v,'batch2_status':'IMPLEMENTED_LIMITED_FAMILIES' if v['vendor_key'] in implemented else 'UNASSESSED_OR_EVIDENCE_TA_BLOCKED'} for v in queue['vendors']],
                    candidate_products=queue['products'],
                    bounded_deferrals=[dict(candidate='CyberArk PAS',reason='Fetched fixture is a custom Elastic JSON syslog template, not default vendor-native CEF; no generator graduated.'),
                                       dict(candidate='Trellix ePO; Illumio; Proofpoint PDS',reason='Existing RAW evidence blockers retained; Proofpoint TAP does not cover PDS.'),
                                       dict(candidate='Corelight; IBM MQ',reason='Selected integration fixture paths unavailable in the bounded lookup; not proof products lack public evidence.'),
                                       dict(candidate='RouterOS LTE, PPP and 5G core',reason='Only documented administrator-login and OSPF hello messages selected; no cellular event-family claim.')],
                    live_verification=dict(results_file='catalog/universe_batch2_current_raw_equality_results.json',status='PENDING'),
                    ta_parser_verification=dict(new_verified_sourcetypes=0,status='BLOCKED_NO_CONTROLLED_INSTALLED_TA_CHECKS'),
                    detection_validation=dict(verified_detections=0,status='NOT_PERFORMED'),
                    limitations=['Integration fixtures are evidence of native grammar, not production captures.','RouterOS console records are vendor documented, not remote syslog conformance tests.','Veeam fixture is native message payload without a record timestamp; current event time is provided in LogEntry/HEC metadata.','Three sourcetype mappings are PulseForge-defined pending TA mapping; no parser compatibility assumed.','Complete candidate input retained; limited implemented families do not imply complete vendor/product coverage.'])
    live = CATALOG / 'universe_batch2_current_raw_equality_results.json'
    if live.exists():
        result=load(live)
        expected = sum(source['event_family_count'] for source in sources)
        engine_hash = hashlib.sha256((ROOT / 'src/netspout_core/universe_batch2_engine.py').read_bytes()).hexdigest()
        valid = (result['engine_sha256'] == engine_hash and result['passes'] == result['posted'] == result['indexed_rows'] == expected
                 and set(result['distinct_sourcetypes']) == {source['splunk_sourcetype'] for source in sources}
                 and all(check['submitted_sha256'] == check['indexed_sha256'] and not check['correlation_leak'] for check in result['raw_equality']))
        registry['live_verification']['status']='PASS' if valid else 'STALE_OR_FAILED'
        registry['live_verification']['run_id']=result['run_id']
    dump(CATALOG/'vendors.json',canon_vendors);dump(CATALOG/'sourcetypes.json',canon_sts)
    dump(CATALOG/'scenarios.json',canon_scenarios);dump(CATALOG/'universe_batch2.json',registry)
    provenance=load(CATALOG/'raw_reference/provenance.json')
    provenance['references']=[r for r in provenance['references'] if r.get('batch')!='universe_batch2']
    for ref in references:
        provenance['references'].append(dict(batch='universe_batch2',documentation_url=ref['url'],
                                            raw_reference_file=ref['raw_reference_file'], fetched_bytes=ref['bytes'],
                                            fetched_sha256=ref['sha256'], evidence_level=ref['evidence_level'],
                                            evidence_role=ref.get('limitation') or ref.get('excerpt'),pinned_commit=ref.get('commit')))
    dump(CATALOG/'raw_reference/provenance.json',provenance)
    print('Batch 2:',registry['counts_summary'])
    print('Canonical:',len(canon_vendors),'vendors,',len(canon_sts),'sourcetypes,',len(canon_scenarios),'scenarios')

if __name__=='__main__':
    main()
