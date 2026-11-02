"""Graduate only selected fixture-backed Batch 4 sources; rebuild offline, idempotently."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'catalog'
CORPUS = CATALOG / 'raw_reference/universe_batch4'

# Technology identity is separate from the publisher in the frozen Splunkbase metadata.
# NOTE: the projected product/category wording below must stay free of the literal
# tokens 'soar' and 'phantom'. scripts/build_discovery_catalog.py projects vendor
# product + category into the native discovery catalog, and tests/test_native_discovery.py
# guards that no external research attribution is promoted into product schema. The real
# Splunkbase app title ("IBM QRadar SOAR Add-on for Splunk") is kept verbatim in the
# non-projected splunk_app_name / required_ta fields, where it is factually correct.
SPECS = [
 ('slack','slack','Slack','Enterprise Grid audit logs','slack:audit','Collaboration SaaS',4986),
 ('github','github','GitHub','Enterprise audit logs','github:enterprise:audit','Source Control SaaS',8703),
 ('gitlab','gitlab','GitLab','Self-Managed audit events','gitlab:audit:json','Source Control Self-Managed',9890),
 ('cybereason','cybereason','Cybereason','Malops feed','cybereason:malops','Endpoint Detection',6427),
 ('qualys','qualys','Qualys','Platform user activity log','qualys:activityLog','Exposure Management SaaS',2964),
 ('rapid7','rapid7','Rapid7','InsightVM asset vulnerabilities','rapid7:insightvm:asset:vulnerability_finding','Vulnerability Management SaaS',5097),
 ('sentinelone','sentinelone','SentinelOne','Threats channel','sentinelone:channel:threats','Endpoint Security SaaS',5433),
 ('tanium','tanium','Tanium','Discover managed machines','tanium:discover:managed','Endpoint Management',4439),
 ('trellix','trellix_mcafee','Trellix (formerly McAfee)','ePO threat events','trellix_epo:threat_events','Endpoint Security',8351),
 ('bitdefender','bitdefender','Bitdefender','GravityZone push notifications','bitdefender:gz','Endpoint Security',7661),
 ('ibm_qradar','ibm_qradar','IBM','QRadar offense events','ibm:qradar:offense','SIEM & Incident Response',6498),
 ('elasticsearch','elastic','Elastic','Elasticsearch server logs','elasticsearch:json','Search Infrastructure',7839),
]
SCENARIO_SOURCES = {
 'ub4_saas_collaboration_audit': ['slack','github','gitlab'],
 'ub4_endpoint_threat_pipeline': ['cybereason','sentinelone','tanium','trellix','bitdefender'],
 'ub4_exposure_infra_logging': ['qualys','rapid7','ibm_qradar','elasticsearch'],
}

# Gate 9.5 telemetry-semantics wording per Batch 4 pack. Every Batch 4 payload is
# rendered into Splunk as a MODELED PAYLOAD over HEC, never a native vendor
# agent/API streaming session, so the badge stays honest for all three packs.
SCENARIO_TELEMETRY_MODEL = {
 'ub4_saas_collaboration_audit': 'SaaS Collaboration Audit JSON',
 'ub4_endpoint_threat_pipeline': 'Endpoint / EDR Threat Event JSON',
 'ub4_exposure_infra_logging': 'Vulnerability Exposure & Infra Audit JSON',
}

TELEMETRY_NOTES = (
    'PulseForge renders vendor-native event/audit payload shapes taken from pinned '
    'upstream integration reference RAW and delivers them to Splunk through HEC. '
    'This is a modeled payload rather than a native vendor agent or API streaming '
    'session, and correlation metadata stays on HEC fields instead of the RAW event.'
)


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
    cybereason = load(CORPUS / 'cybereason.bin')[0]
    bitdefender = load(CORPUS / 'bitdefender.bin')['events']
    return {
     'slack': [f('user_login',line('slack',1),'slack','line:1'),
               f('admin_console_anomaly',line('slack',4),'slack','line:4','flagged','breached'),
               f('malicious_file_detected',line('slack',6),'slack','line:6','alerted','breached')],
     'github': [f('enterprise_user_login',line('github',1),'github','line:1'),
                f('repository_merge',line('github',16),'github','line:16')],
     'gitlab': [f('session_login',line('gitlab',1),'gitlab','line:1'),
                f('git_operation',line('gitlab',4),'gitlab','line:4')],
     'cybereason': [f('malop_process_injection',cybereason,'cybereason','array_element:0','alerted','breached')],
     'qualys': [f('console_login',line('qualys',1),'qualys','line:1'),
                f('configuration_change',line('qualys',9),'qualys','line:9','changed')],
     'rapid7': [f('steady_state_asset_exposure',line('rapid7',1),'rapid7','line:1','observed','degraded'),
                f('critical_findings_asset_exposure',line('rapid7',3),'rapid7','line:3','alerted','degraded')],
     'sentinelone': [f('threat_trojan_detected',line('sentinelone',1),'sentinelone','line:1','alerted','breached'),
                    f('threat_malware_agent_reported',line('sentinelone',7),'sentinelone','line:7','alerted','breached')],
     'tanium': [f('managed_endpoint_inventory',line('tanium',1),'tanium','line:1')],
     'trellix': [f('nips_port_scan_handled',line('trellix',1),'trellix','line:1','blocked','breached'),
                 f('blocked_process_access',line('trellix',5),'trellix','line:5','blocked','breached'),
                 f('nids_would_block_unhandled',line('trellix',12),'trellix','line:12','alerted','breached')],
     'bitdefender': [f('phishing_blocked',__import__('json').loads(bitdefender[0]['message']),'bitdefender','events[0].message','blocked','breached'),
                     f('av_malware_detected',__import__('json').loads(bitdefender[3]['message']),'bitdefender','events[3].message','alerted','breached'),
                     f('firewall_portscan_blocked',__import__('json').loads(bitdefender[6]['message']),'bitdefender','events[6].message','blocked','breached')],
     'ibm_qradar': [f('generic_log_offense',line('ibm_qradar',1),'ibm_qradar','line:1','alerted','degraded'),
                    f('message_offense',line('ibm_qradar',2),'ibm_qradar','line:2'),
                    f('authentication_offense',line('ibm_qradar',3),'ibm_qradar','line:3','alerted','breached')],
     'elasticsearch': [f('data_stream_provisioning',line('elasticsearch',1),'elasticsearch','line:1'),
                       f('shard_bootstrapping',line('elasticsearch',4),'elasticsearch','line:4')],
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
        app = apps[uid]
        declared = st in {t for ts in app['rel_tags_st'].values() for t in ts}
        sources.append(dict(batch_source_id=source_id, vendor=vendor_id, product=product,
                            splunk_sourcetype=st, generator='format_universe_batch4_log',
                            event_families=[f['id'] for f in source_templates[source_id]],
                            event_family_count=len(source_templates[source_id]),
                            families=source_templates[source_id],
                            evidence_level=ref_by_id[source_id]['evidence_level'],
                            ta_metadata=dict(uid=uid, name=app['name'], publisher=app['author'], app_type=app['app_type'],
                                             version=app['rel_version'],
                                             sourcetype_declared_in_snapshot=declared,
                                             authority='SPLUNKBASE_METADATA' if declared else 'PULSEFORGE_DEFINED_PENDING_TA_MAPPING',
                                             parser_verified=False,
                                             blocker='Installed TA and controlled parser check unavailable; declared sourcetype does not prove input-format compatibility.'),
                            raw_evidence=sorted({ref_by_id[f['origin']]['raw_reference_file'] for f in source_templates[source_id]})))
        vendor = dict(id=vendor_id, legacy_id=vendor_id, name=vendor_name, slug=vendor_id,
                      category=category, splunk_app_name=app['name'],
                      splunkbase_id=str(uid), splunkbase_url=app['url'],
                      doc_url=ref_by_id[source_id]['url'], supported_device_types=['web_server'],
                      supported_protocols=['hec'], header_type='Vendor-native documented payload', delimiter='',
                      timestamp_format='Source-specific UTC or native console time', cim_models=[], field_mappings={},
                      sample_events=[], primary_sourcetypes=[st])
        st_row = dict(id=st.lower().replace(':','-').replace(' ','-'), splunk_sourcetype=st,
                      display_name=product, vendor_id=vendor_id, category=category, data_kind='event',
                      default_index='idx_network_ops', recommended_index='netops_logs', generation_mode='STATEFUL',
                      protocol='hec', sample_file=None, required_ta=app['name'] if declared else 'Mapping pending: ' + app['name'],
                      aliases=[st], deprecated_aliases=[], is_benchmark_197=False, status='active')
        canon_vendors = [v for v in canon_vendors if v['id'] != vendor_id] + [vendor]
        canon_sts = [s for s in canon_sts if s['splunk_sourcetype'] != st] + [st_row]
    precise_mapping_blockers = {
        'ibm_qradar': 'Snapshot app 6498 (IBM QRadar SOAR Add-on) declares no sourcetype tags; selected offense shape is pinned integration RAW, not a QRadar DSM payload; package binding pending.',
        'bitdefender': 'Snapshot app 7661 declares bitdefender:gz, but the installed-TA framing of the push wrapper is unverified; only the inner events[].message notification is rendered.',
        'trellix': 'Snapshot app 8351 is a community package; selected RAW uses Elastic flattened dotted keys, not native ePO query output; input-format binding unverified.',
    }
    for source in sources:
        if source['batch_source_id'] in precise_mapping_blockers:
            source['ta_metadata']['blocker'] = precise_mapping_blockers[source['batch_source_id']]
    for sid, ids in SCENARIO_SOURCES.items():
        sts = [s['splunk_sourcetype'] for s in sources if s['batch_source_id'] in ids]
        vendors = [s['vendor'] for s in sources if s['batch_source_id'] in ids]
        tm = SCENARIO_TELEMETRY_MODEL[sid]
        row = dict(id=sid, code='SEC-UB4-'+str(list(SCENARIO_SOURCES).index(sid)+1).zfill(2),
                   name=sid.replace('_',' ').title(), display_name=sid.replace('_',' ').title(),
                   category='SECURITY' if 'threat' in sid else 'INFRASTRUCTURE', ecosystem='mixed_vendor',
                   maturity='CONTRACTED', description='Executable observation sequence from pinned native RAW fixtures. Correlation stays on HEC fields; no detection efficacy or real causality claimed.',
                   generation_mode='SCENARIO_DERIVED', generation_modes=['SCENARIO_DERIVED'], sourcetypes=sts,
                   default_topology_id='mixed_sase', topology_id='mixed_sase', difficulty='ADVANCED',
                   estimated_duration_sec=40, vendor_scope=vendors, telemetry_requirements=['hec_event'],
                   affected_entities=['mixed_sase'], expected_observations=[f'{s["product"]}: {", ".join(s["event_families"])}' for s in sources if s['batch_source_id'] in ids],
                   expected_phases=['baseline','observe','validate'],
                   telemetry_model=tm, transport_protocol='Splunk HEC',
                   splunk_storage='Splunk Event Index (idx_network_ops)',
                   fidelity_badge='MODELED PAYLOAD', telemetry_notes=TELEMETRY_NOTES,
                   phases=[dict(phase=p, name=p.title(), duration_ticks=1, description='Fixture-backed native source observation') for p in ['BASELINE','OBSERVE','VALIDATE']],
                   registry_reference='catalog/universe_batch4.json')
        canon_scenarios = [s for s in canon_scenarios if s['id'] != sid] + [row]
    queue = load(CATALOG / 'vendor_universe/batch2_candidate_queue_baseline.json')
    batch2_vendors = {s['vendor'] for s in load(CATALOG / 'universe_batch2.json')['sources']}
    batch3_vendors = {s['vendor'] for s in load(CATALOG / 'universe_batch3.json')['sources']}
    implemented = {s['vendor'] for s in sources}
    blocked_keys = {'cyberark','corelight','netapp'}
    partial_products = {
        'slack':'slack', 'gitlab':'gitlab', 'gitlab self-managed':'gitlab', 'tanium':'tanium',
        'rapid7 insightvm':'rapid7', 'sentinelone':'sentinelone', 'cybereason':'cybereason',
        'qualyscloudplatform':'qualys', 'elasticsearch':'elastic', 'elastic search':'elastic',
        'ibm qradar soar':'ibm_qradar', 'gravityzone':'bitdefender',
        'bitdefender gravityzone for splunk dashboard':'bitdefender',
        'trellix mvision epo':'trellix_mcafee', 'trellix epo saas connector':'trellix_mcafee', 'trellix epo':'trellix_mcafee',
        'hashicorp vault':'hashicorp', 'claroty continuous threat detection (ctd)':'claroty',
        'confluence and jira audit':'atlassian', 'proofpoint tap':'proofpoint',
        'pfsense':'pfsense', 'sysdig':'sysdig',
        'sailpoint identity security cloud auditevent':'sailpoint', 'darktrace':'darktrace', 'tenable':'tenable',
    }
    blocked_products = {'illumio','proofpoint on demand email security','corelight','corelightfor'}
    product_statuses = [dict(product=name,baseline_app_count=count,
                            status='IMPLEMENTED_LIMITED_FAMILIES' if name in partial_products else 'BLOCKED_SELECTED_RAW_REFERENCE' if name in blocked_products else 'PENDING_REVIEW',
                            mapped_vendor=partial_products.get(name),
                            note='Only selected source families; no whole-product coverage claim' if name in partial_products else 'Earlier bounded RAW evidence/path blocker retained' if name in blocked_products else 'Original title-derived candidate retained; exact source mapping pending')
                        for name,count in queue['products']]
    registry = dict(schema_version='1.0', registry_version='universe-batch4-2026-10-27',
                    baseline_commit='dd9f3ac642120bde4ebbc89c7c8a71c199b9d189', baseline_counts=dict(vendors=76,sourcetypes=336,scenarios=47),
                    sources=sources, scenarios=SCENARIO_SOURCES,
                    counts_summary=dict(new_canonical_vendors=12,new_product_integrations=12,new_canonical_sourcetypes=12,
                                        event_families=sum(s['event_family_count'] for s in sources), scenario_packs=3),
                    candidate_queue=[{**v,'batch3_status':'IMPLEMENTED_LIMITED_FAMILIES_BATCH3' if v['vendor_key'] in batch3_vendors else 'IMPLEMENTED_LIMITED_FAMILIES_BATCH2' if v['vendor_key'] in batch2_vendors else 'BLOCKED_SELECTED_PRODUCT_REFERENCE' if v['vendor_key'] in {'cyberark','corelight','netapp'} else 'PENDING_REVIEW',
                                      'batch4_status':'IMPLEMENTED_LIMITED_FAMILIES_BATCH4' if v['vendor_key'] in implemented else 'IMPLEMENTED_LIMITED_FAMILIES_BATCH3' if v['vendor_key'] in batch3_vendors else 'IMPLEMENTED_LIMITED_FAMILIES_BATCH2' if v['vendor_key'] in batch2_vendors else 'BLOCKED_SELECTED_PRODUCT_REFERENCE' if v['vendor_key'] in blocked_keys else 'PENDING_REVIEW'} for v in queue['vendors']],
                    candidate_products=queue['products'],
                    product_candidate_statuses=product_statuses,
                    bounded_deferrals=[dict(candidate='Corelight; Akamai; CyberArk PAS',reason='Pinned fixture availability blockers retained; no format invented.'),
                                       dict(candidate='Vectra AI; ManageEngine/Zoho; Hitachi Vantara; Ubiquiti; NetApp; Varonis; Pure Storage; DocuSign; Kaspersky; SolarWinds; WireGuard; Veritas; HPE; PAVO/Metrics; Malwarebytes; Zyxel; ClickHouse; Cilium/Isovalent; VirusTotal; Cisco (other)',reason='No authentic pinned public RAW found for these queue keys; they remain PENDING_REVIEW.'),
                                       dict(candidate='IBM QRadar SOAR; Bitdefender GravityZone; Trellix ePO',reason='Native RAW implemented but source-to-TA input mapping or framing remains unverified for these three sourcetypes.')],
                    live_verification=dict(results_file='catalog/universe_batch4_current_raw_equality_results.json',status='PENDING'),
                    ta_parser_verification=dict(new_verified_sourcetypes=0,status='BLOCKED_NO_CONTROLLED_INSTALLED_TA_CHECKS'),
                    detection_validation=dict(verified_detections=0,status='NOT_PERFORMED'),
                    parser_inventory='catalog/universe_batch3_ta_inventory.json',
                    parser_results='catalog/universe_batch3_ise_parser_results.json',
                    limitations=['All selected sources use pinned native integration RAW, not independent production captures.',
                                 'One sourcetype (ibm:qradar:offense) is PulseForge-defined pending TA mapping; three further sources carry precise input-format blockers.',
                                 'Bitdefender records render the inner events[].message notification; wrapper unpacking is a PulseForge framing choice pending installed-TA verification.',
                                 'Queue retains all original 66 vendor and 583 product candidates; nothing was dropped or silently reclassified.',
                                 'Only selected native fields and times vary; native action codes and field semantics remain fixture-derived.'])

    live = CATALOG / 'universe_batch4_current_raw_equality_results.json'
    if live.exists():
        result=load(live)
        expected = sum(source['event_family_count'] for source in sources)
        engine_hash = hashlib.sha256((ROOT / 'src/netspout_core/universe_batch4_engine.py').read_bytes()).hexdigest()
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
    dump(CATALOG/'universe_batch4_parser_assessments.json',dict(sources=assessments,new_verified_sourcetypes=0,
         scope='Mapping assessment for every canonical row; actual execution only for the installed ISE TA (evidence retained from Batch 3). Built-in sourcetype behavior is not counted as installed vendor TA verification.'))
    registry['parser_assessments']='catalog/universe_batch4_parser_assessments.json'
    registry['ta_parser_verification']['existing_ise_result']='PARTIAL: 9/10 controlled records; CoA 5205 MAC mapping blocker'
    dump(CATALOG/'vendors.json',canon_vendors);dump(CATALOG/'sourcetypes.json',canon_sts)
    dump(CATALOG/'scenarios.json',canon_scenarios);dump(CATALOG/'universe_batch4.json',registry)
    provenance=load(CATALOG/'raw_reference/provenance.json')
    provenance['references']=[r for r in provenance['references'] if r.get('batch')!='universe_batch4']
    for ref in references:
        provenance['references'].append(dict(batch='universe_batch4',documentation_url=ref['url'],
                                            raw_reference_file=ref['raw_reference_file'], fetched_bytes=ref['bytes'],
                                            fetched_sha256=ref['sha256'], evidence_level=ref['evidence_level'],
                                            evidence_role=ref.get('limitation') or ref.get('excerpt'),pinned_commit=ref.get('pinned_commit')))
    dump(CATALOG/'raw_reference/provenance.json',provenance)
    print('Batch 4:',registry['counts_summary'])
    print('Canonical:',len(canon_vendors),'vendors,',len(canon_sts),'sourcetypes,',len(canon_scenarios),'scenarios')

if __name__=='__main__':
    main()
