"""Graduate only selected fixture-backed Batch 3 sources; rebuild offline, idempotently."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'catalog'
CORPUS = CATALOG / 'raw_reference/universe_batch3'

# Technology identity is separate from the publisher in the frozen Splunkbase metadata.
SPECS = [
 ('pfsense','pfsense_netgate','pfSense (Netgate)','pfSense filterlog','pfsense:filterlog','Network Security',5613),
 ('sysdig','sysdig','Sysdig','Sysdig Secure runtime and Kubernetes audit','SysdigSecureEvents','Cloud Runtime Security',5331),
 ('sailpoint','sailpoint','SailPoint','Identity Security Cloud audit','sailpoint_identitynow','Identity SaaS',4088),
 ('imperva','imperva','Imperva','SecureSphere CEF','imperva:securesphere:cef','Database & Web Security',3507),
 ('barracuda','barracuda','Barracuda Networks','Web Application Firewall','barracuda:waf:web_firewall','Application Security',6183),
 ('oracle','oracle','Oracle','Database native audit','oracle:audit:text','Database Infrastructure',1910),
 ('darktrace','darktrace','Darktrace','Model breach alerts','darktrace','Network Detection',3539),
 ('beyondtrust','beyondtrust','BeyondTrust','Password Safe audit','ccx:beyondinsight:passwordsafe','Privileged Access',6897),
 ('tenable','tenable','Tenable','Vulnerability Management audit','tenable:io:audit_logs','Exposure Management SaaS',4060),
 ('ibmmq','ibm_mq','IBM MQ','IBM MQ native error log','ibm:mq:errorlog','Messaging Infrastructure',3829),
]
SCENARIO_SOURCES = {
 'ub3_identity_runtime_audit': ['sailpoint','beyondtrust','tenable','sysdig'],
 'ub3_multivendor_edge_observation': ['pfsense','barracuda','imperva','darktrace'],
 'ub3_database_message_audit': ['oracle','ibmmq'],
}



def load(path):
    return json.loads(path.read_text())


def dump(path, data):
    path.write_text(json.dumps(data, indent=1) + '\n')


def fixture_lines(name):
    return (CORPUS / f'{name}.bin').read_text().splitlines()


def templates():
    def line(name, n):
        value = fixture_lines(name)[n-1]
        try:
            return __import__('json').loads(value)
        except ValueError:
            return value
    def f(name, value, origin, selector, action='observed', status='normal'):
        return dict(id=name, template=value, origin=origin, selector=selector, action=action, status=status)
    imperva = load(CORPUS / 'imperva.bin')['events']
    beyond = load(CORPUS / 'beyondtrust.bin')['events'][0]['event']['original']
    oracle = (CORPUS / 'oracle.bin').read_text().split('\n\n',1)[0]+'\n\n'
    return {
     'pfsense': [f('ipv4_tcp_block',line('pfsense',1),'pfsense','line:1','blocked','breached'),
                 f('ipv4_udp_pass',line('pfsense',3),'pfsense','line:3','allowed'),
                 f('ipv6_udp_block',line('pfsense',7),'pfsense','line:7','blocked')],
     'sysdig': [f('runtime_activity',line('sysdig',7),'sysdig','line:7'),
                f('kubernetes_audit',line('sysdig',9),'sysdig','line:9')],
     'sailpoint': [f('password_update',line('sailpoint',1),'sailpoint','line:1'),
                   f('machine_identity_created',line('sailpoint',3),'sailpoint','line:3')],
     'imperva': [f('administrator_login',imperva[1]['event']['original'],'imperva','events[1].event.original'),
                 f('database_audit',imperva[2]['event']['original'],'imperva','events[2].event.original')],
     'barracuda': [f('parameter_profile_violation',line('barracuda',1),'barracuda','line:1','alerted','degraded'),
                   f('url_profile_violation',line('barracuda',4),'barracuda','line:4','alerted','degraded')],
     'oracle': [f('sql_select_audit',oracle,'oracle','first_blank_delimited_record_include_separator')],
     'darktrace': [f('uncommon_outbound_model',line('darktrace',10),'darktrace','line:10','alerted','degraded'),
                   f('antigena_internal_transfer',line('darktrace',11),'darktrace','line:11','alerted','breached')],
     'beyondtrust': [f('secret_folder_added',__import__('json').loads(beyond),'beyondtrust','events[0].event.original')],
     'tenable': [f('password_authentication_failure',line('tenable',1),'tenable','line:1','blocked','degraded'),
                 f('session_created',line('tenable',2),'tenable','line:2'),
                 f('session_deleted',line('tenable',3),'tenable','line:3')],
     'ibmmq': [f('queue_manager_created',line('ibmmq',2),'ibmmq','line:2'),
               f('control_command_issued',line('ibmmq',3),'ibmmq','line:3')],
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
                            splunk_sourcetype=st, generator='format_universe_batch3_log',
                            event_families=[f['id'] for f in source_templates[source_id]],
                            event_family_count=len(source_templates[source_id]),
                            families=source_templates[source_id],
                            evidence_level=ref_by_id[source_id]['evidence_level'],
                            ta_metadata=dict(uid=uid, name=app['name'] if app else None,
                                             publisher=app['author'] if app else None, app_type=app['app_type'] if app else None,
                                             version=app['rel_version'] if app else None,
                                             sourcetype_declared_in_snapshot=declared,
                                             authority='SPLUNKBASE_METADATA' if declared else 'PULSEFORGE_DEFINED_PENDING_TA_MAPPING',
                                             parser_verified=False,
                                             blocker='Installed TA and controlled parser check unavailable; declared sourcetype does not prove input-format compatibility.'),
                            raw_evidence=sorted({ref_by_id[f['origin']]['raw_reference_file'] for f in source_templates[source_id]})))
        vendor = dict(id=vendor_id, legacy_id=vendor_id, name=vendor_name, slug=vendor_id,
                      category=category, splunk_app_name=app['name'] if app else 'Mapping pending',
                      splunkbase_id=str(uid) if uid else '', splunkbase_url=app['url'] if app else '',
                      doc_url=ref_by_id[source_id]['url'], supported_device_types=['router' if source_id=='pfsense' else 'web_server'],
                      supported_protocols=['hec'], header_type='Vendor-native documented payload', delimiter='',
                      timestamp_format='Source-specific UTC or native console time', cim_models=[], field_mappings={},
                      sample_events=[], primary_sourcetypes=[st])
        st_row = dict(id=st.lower().replace(':','-').replace(' ','-'), splunk_sourcetype=st,
                      display_name=product, vendor_id=vendor_id, category=category, data_kind='event',
                      default_index='idx_network_ops', recommended_index='netops_logs', generation_mode='STATEFUL',
                      protocol='hec', sample_file=None, required_ta=app['name'] if declared else 'Mapping pending: ' + (app['name'] if app else 'no app candidate'),
                      aliases=[st], deprecated_aliases=[], is_benchmark_197=False, status='active')
        canon_vendors = [v for v in canon_vendors if v['id'] != vendor_id] + [vendor]
        canon_sts = [s for s in canon_sts if s['splunk_sourcetype'] != st] + [st_row]
    precise_mapping_blockers = {
        'pfsense': 'Snapshot app 5613 declares no sourcetype tags; native filterlog-to-TA binding unestablished and package absent.',
        'imperva': 'Snapshot app 3507 declares SecureSphere JSON and Incapsula CEF names, not the selected SecureSphere CEF contract; matching installed parser absent.',
        'barracuda': 'Snapshot app 6183 declares generic firewall/access/audit names, not this vendor-qualified WAF name; package and matching parser unavailable.',
        'ibmmq': 'Snapshot app 3829 identifies MQ error logs but declares no sourcetype tags; package absent and native-format parser binding pending.',
    }
    for source in sources:
        if source['batch_source_id'] in precise_mapping_blockers:
            source['ta_metadata']['blocker'] = precise_mapping_blockers[source['batch_source_id']]
    for sid, ids in SCENARIO_SOURCES.items():
        sts = [s['splunk_sourcetype'] for s in sources if s['batch_source_id'] in ids]
        vendors = [s['vendor'] for s in sources if s['batch_source_id'] in ids]
        row = dict(id=sid, code='SEC-UB3-'+str(list(SCENARIO_SOURCES).index(sid)+1).zfill(2),
                   name=sid.replace('_',' ').title(), display_name=sid.replace('_',' ').title(),
                   category='SECURITY' if 'hunt' in sid else 'INFRASTRUCTURE', ecosystem='mixed_vendor',
                   maturity='CONTRACTED', description='Executable observation sequence from pinned native RAW fixtures. Correlation stays on HEC fields; no detection efficacy or real causality claimed.',
                   generation_mode='SCENARIO_DERIVED', generation_modes=['SCENARIO_DERIVED'], sourcetypes=sts,
                   default_topology_id='mixed_sase', topology_id='mixed_sase', difficulty='ADVANCED',
                   estimated_duration_sec=40, vendor_scope=vendors, telemetry_requirements=['hec_event'],
                   affected_entities=['mixed_sase'], expected_observations=[f'{s["product"]}: {", ".join(s["event_families"])}' for s in sources if s['batch_source_id'] in ids],
                   expected_phases=['baseline','observe','validate'],
                   phases=[dict(phase=p, name=p.title(), duration_ticks=1, description='Fixture-backed native source observation') for p in ['BASELINE','OBSERVE','VALIDATE']],
                   registry_reference='catalog/universe_batch3.json')
        canon_scenarios = [s for s in canon_scenarios if s['id'] != sid] + [row]
    queue = load(CATALOG / 'vendor_universe/batch2_candidate_queue_baseline.json')
    implemented = {s['vendor'] for s in sources}
    partial_products = {
        'pfsense':'pfsense', 'sysdig':'sysdig',
        'sailpoint identity security cloud auditevent':'sailpoint', 'darktrace':'darktrace', 'tenable':'tenable',
        'hashicorp vault':'hashicorp', 'claroty continuous threat detection (ctd)':'claroty',
        'confluence and jira audit':'atlassian', 'proofpoint tap':'proofpoint',
    }
    blocked_products = {'illumio','trellix mvision epo','trellix epo saas connector','trellix epo',
                        'proofpoint on demand email security','corelight','corelightfor'}
    product_statuses = [dict(product=name,baseline_app_count=count,
                            status='IMPLEMENTED_LIMITED_FAMILIES' if name in partial_products else 'BLOCKED_SELECTED_RAW_REFERENCE' if name in blocked_products else 'PENDING_REVIEW',
                            mapped_vendor=partial_products.get(name),
                            note='Only selected source families; no whole-product coverage claim' if name in partial_products else 'Earlier bounded RAW evidence/path blocker retained' if name in blocked_products else 'Original title-derived candidate retained; exact source mapping pending')
                        for name,count in queue['products']]
    registry = dict(schema_version='1.0', registry_version='universe-batch3-2026-10-26',
                    baseline_commit='a25c4c124ad41d8e976c7471f7929f3086718e9b', baseline_counts=dict(vendors=66,sourcetypes=326,scenarios=44),
                    sources=sources, scenarios=SCENARIO_SOURCES,
                    counts_summary=dict(new_canonical_vendors=10,new_product_integrations=10,new_canonical_sourcetypes=10,
                                        event_families=sum(s['event_family_count'] for s in sources), scenario_packs=3),
                    candidate_queue=[{**v,'batch3_status':'IMPLEMENTED_LIMITED_FAMILIES_BATCH3' if v['vendor_key'] in implemented else 'IMPLEMENTED_LIMITED_FAMILIES_BATCH2' if v['vendor_key'] in {row['vendor'] for row in load(CATALOG / 'universe_batch2.json')['sources']} else 'BLOCKED_SELECTED_PRODUCT_REFERENCE' if v['vendor_key'] in {'trellix_mcafee','cyberark','corelight','netapp'} else 'PENDING_REVIEW'} for v in queue['vendors']],
                    candidate_products=queue['products'],
                    product_candidate_statuses=product_statuses,
                    bounded_deferrals=[dict(candidate='NetApp ONTAP',reason='Selected integration fixture path unavailable; no format invented.'),
                                       dict(candidate='Trellix ePO; Illumio; Proofpoint PDS; CyberArk PAS',reason='Earlier RAW-format blockers retained; no new evidence graduation.'),
                                       dict(candidate='pfSense; Imperva SecureSphere CEF; Barracuda WAF; IBM MQ',reason='Native RAW implemented but selected source-to-TA mapping remains unestablished for these four sourcetypes.')],
                    live_verification=dict(results_file='catalog/universe_batch3_current_raw_equality_results.json',status='PENDING'),
                    ta_parser_verification=dict(new_verified_sourcetypes=0,status='BLOCKED_NO_CONTROLLED_INSTALLED_TA_CHECKS'),
                    detection_validation=dict(verified_detections=0,status='NOT_PERFORMED'),
                    additional_snapshot_product=dict(uid=3829,vendor_key='ibm_mq',status='IMPLEMENTED_LIMITED_FAMILIES',reason='IBM MQ entry exists in the original 1871-app snapshot but was omitted by the original title-derived product candidate classifier. Does not mark IBM QRadar covered.'),
                    parser_inventory='catalog/universe_batch3_ta_inventory.json',
                    parser_results='catalog/universe_batch3_ise_parser_results.json',
                    limitations=['All selected sources use pinned native integration RAW, not independent production captures.',
                                 'Four source-to-TA mappings are PulseForge-defined pending parser review.',
                                 'Queue retains all original 66 vendor and 583 product candidates; IBM MQ is linked separately to its original snapshot UID.',
                                 'Only selected native fields and times vary; native action codes and field semantics remain fixture-derived.'])

    live = CATALOG / 'universe_batch3_current_raw_equality_results.json'
    if live.exists():
        result=load(live)
        expected = sum(source['event_family_count'] for source in sources)
        engine_hash = hashlib.sha256((ROOT / 'src/netspout_core/universe_batch3_engine.py').read_bytes()).hexdigest()
        valid = (result['engine_sha256'] == engine_hash and result['passes'] == result['posted'] == result['indexed_rows'] == expected
                 and set(result['distinct_sourcetypes']) == {source['splunk_sourcetype'] for source in sources}
                 and all(check['submitted_sha256'] == check['indexed_sha256'] and not check['correlation_leak'] for check in result['raw_equality']))
        registry['live_verification']['status']='PASS' if valid else 'STALE_OR_FAILED'
        registry['live_verification']['run_id']=result['run_id']
    parser_result_path = CATALOG/'universe_batch3_ise_parser_results.json'
    parser_result = load(parser_result_path) if parser_result_path.is_file() else {}
    assessments = []
    for row in canon_sts:
        ise = row['splunk_sourcetype'] == 'cisco:ise:syslog'
        assessments.append(dict(sourcetype=row['splunk_sourcetype'], vendor=row['vendor_id'], required_ta=row.get('required_ta'),
                                installed_app='Splunk_TA_cisco-ise' if ise else None,
                                status='ACTUAL_EXECUTION_PARTIAL_WITH_BLOCKER' if ise and parser_result else 'MAPPING_ONLY_NO_INSTALLED_VENDOR_PARSER_EVIDENCE',
                                evidence='catalog/universe_batch3_ise_parser_results.json' if ise else None,
                                blocker='5205 colon-delimited MAC extracted into truncated src_ip; src_mac absent' if ise else 'Required vendor parser unavailable in inspected installed apps/local authorized packages; source name alone is not verification'))
    dump(CATALOG/'universe_batch3_parser_assessments.json',dict(sources=assessments,new_verified_sourcetypes=0,
         scope='Mapping assessment for every canonical row; actual execution only for the installed ISE TA. Built-in sourcetype behavior is not counted as installed vendor TA verification.'))
    registry['parser_assessments']='catalog/universe_batch3_parser_assessments.json'
    registry['ta_parser_verification']['existing_ise_result']='PARTIAL: 9/10 controlled records; CoA 5205 MAC mapping blocker'
    dump(CATALOG/'vendors.json',canon_vendors);dump(CATALOG/'sourcetypes.json',canon_sts)
    dump(CATALOG/'scenarios.json',canon_scenarios);dump(CATALOG/'universe_batch3.json',registry)
    provenance=load(CATALOG/'raw_reference/provenance.json')
    provenance['references']=[r for r in provenance['references'] if r.get('batch')!='universe_batch3']
    for ref in references:
        provenance['references'].append(dict(batch='universe_batch3',documentation_url=ref['url'],
                                            raw_reference_file=ref['raw_reference_file'], fetched_bytes=ref['bytes'],
                                            fetched_sha256=ref['sha256'], evidence_level=ref['evidence_level'],
                                            evidence_role=ref.get('limitation') or ref.get('excerpt'),pinned_commit=ref.get('pinned_commit')))
    dump(CATALOG/'raw_reference/provenance.json',provenance)
    print('Batch 3:',registry['counts_summary'])
    print('Canonical:',len(canon_vendors),'vendors,',len(canon_sts),'sourcetypes,',len(canon_scenarios),'scenarios')

if __name__=='__main__':
    main()
