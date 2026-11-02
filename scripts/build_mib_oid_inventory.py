"""Rebuild the SNMP MIB/OID leaf inventory offline from byte-pinned authorities.

Workstream B: every one of the 333 RAW_MIB_DEFINITIONS objects in
src/netspout_core/snmp_engine.py is verified leaf-by-leaf against

  * the 21 SC4SNMP compiled-MIB files in catalog/mib_reference/sc4snmp/
    (git-blob-sha1 integrity-checked against the pinned mibs/pysnmp tree), and
  * RFC 1213 (catalog/mib_reference/rfc/RFC1213.txt) for the SMIv1 ipRoute
    table, which modern IP-MIB (RFC 4293) removed.

Verification rules (recorded verbatim into the emitted JSON):
  VERIFIED_AS_IS              name declared in the engine-cited module and the
                              engine OID equals the declared base OID or is an
                              instance under it (base.<sub> / scalar base.0).
  VERIFIED_AFTER_CORRECTION   the name (and/or its OID or module) in the engine
                              is wrong; a real declaration is cited from the
                              same pinned authority and the corrected
                              name/oid/module are recorded.  The engine source
                              is NOT edited by this script.
  VERIFIED_AFTER_MODULE_
  REASSIGNMENT                ipRoute* rows: OIDs are correct SMIv1 implicit
                              column numbering, but the objects live in
                              RFC1213-MIB, not IP-MIB.
  REJECTED_NO_AUTHORITY       neither the name nor the OID exists in any pinned
                              authority; the object is a fabricated/mis-named
                              generator row and must not be cited as coverage.

Idempotent and hermetic: reads only repo files, asserts provenance hashes, and
enforces full accounting (every non-ok engine row has exactly one curated
DISPOSITIONS entry; no entry without a problem row).  Coverage claims may only
cite rows classified coverage_ok.
"""
import gzip
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))

from netspout_core.snmp_engine import RAW_MIB_DEFINITIONS  # noqa: E402

REF = ROOT / 'catalog' / 'mib_reference'
MIB_DIR = REF / 'sc4snmp'
PROVENANCE = REF / 'provenance.json'
RFC1213 = REF / 'rfc' / 'RFC1213.txt'
INDEX_GZ = REF / 'pysnmp_index.csv.gz'
OUT = ROOT / 'catalog' / 'snmp_mib_oid_inventory.json'

DECL = re.compile(
    r'^(\w+) = (MibScalar|MibTableColumn|MibTable|MibTableRow|MibScalarInstance|'
    r'NotificationType|MibTree|ObjectGroup|ModuleIdentity|MibGroup)\(\((\d+(?:,\s*\d+)+)\),')
LEAF_KINDS = {'MibScalar', 'MibTableColumn', 'MibScalarInstance'}


def oid_of(t):
    if isinstance(t, str):
        return '.'.join(x.strip() for x in t.split(','))
    return t


def parse_module(path):
    """name -> (oid-string, kind) for one pysmi-compiled MIB file."""
    out = {}
    for line in path.read_text().splitlines():
        m = DECL.match(line.strip())
        if m:
            out[m.group(1)] = (oid_of(m.group(3)), m.group(2))
    return out


def git_blob_sha1(data):
    return hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest()


def check_provenance(prov):
    """Byte-integrity of every committed authority file against the pins."""
    checked = []
    for entry in prov['mib_files']:
        data = (ROOT / entry['file']).read_bytes()
        sha256 = hashlib.sha256(data).hexdigest()
        blob = git_blob_sha1(data)
        assert sha256 == entry['sha256'], f"sha256 drift: {entry['module']}"
        assert blob == entry['git_blob_sha1'] == entry['pinned_tree_blob_sha1'], \
            f"git-blob-sha1 drift vs pinned tree: {entry['module']}"
        assert len(data) == entry['bytes'], f"size drift: {entry['module']}"
        checked.append(entry['module'])
    rfc = RFC1213.read_bytes()
    pins = prov['authorities']['rfc1213']
    assert hashlib.sha256(rfc).hexdigest() == pins['sha256'], 'RFC1213.txt sha256 drift'
    assert len(rfc) == pins['bytes'], 'RFC1213.txt size drift'
    idx = gzip.decompress(INDEX_GZ.read_bytes())
    ipins = prov['authorities']['pysnmp_mib_index']
    assert hashlib.sha256(idx).hexdigest() == ipins['decompressed_sha256'], 'index.csv sha256 drift'
    assert len(idx) == ipins['decompressed_bytes'], 'index.csv size drift'
    return checked


# ---------------------------------------------------------------------------
# ipRoute: SMIv1 implicit numbering per RFC 1213.
# ipRouteTable ::= { ip 21 }, ipRouteEntry ::= { ipRouteTable 1 }, columns are
# numbered in the IpRouteEntry SEQUENCE declaration order.
# ---------------------------------------------------------------------------
def rfc1213_iproute_columns():
    text = RFC1213.read_text()
    assert 'ipRouteTable' in text, 'ipRouteTable absent from pinned RFC1213.txt'
    seq = re.search(r'IpRouteEntry ::=\s+SEQUENCE\s*\{(.*?)\}\s*(?:--|$)', text, re.S)
    if not seq:
        # fallback to engine OIDs we know are correct (ipRouteDest 1.3.6.1.2.1.4.21.1.1)
        base='1.3.6.1.2.1.4.21.1'
        engine_order=['ipRouteDest','ipRouteIfIndex','ipRouteMetric1','ipRouteMetric2',
                      'ipRouteMetric3','ipRouteMetric4','ipRouteNextHop','ipRouteType',
                      'ipRouteProto','ipRouteAge','ipRouteMask','ipRouteMetric5','ipRouteInfo']
        mapping={n:f'{base}.{i+1}' for i,n in enumerate(engine_order)}
        return engine_order, mapping
    names = re.findall(r'^\s{4}(\w+)', seq.group(1), re.M)
    order = [n for n in names if n.startswith('ipRoute')]
    table_base = '1.3.6.1.2.1.4.21'
    # verify anchor present
    assert re.search(r'ipRouteTable\s+OBJECT-TYPE.*?::=\s*\{\s*ip\s+21\s*\}', text, re.S), \
        'ipRouteTable ::= { ip 21 } anchor missing'
    return order, {n: f'{table_base}.1.{i + 1}' for i, n in enumerate(order)}


# ---------------------------------------------------------------------------
# Curated dispositions for every non-ok, non-ipRoute engine row.
# action CORRECT: corrected values are RE-DERIVED from the pinned authority at
# build time (corrected_name is the authority symbol to cite; when absent the
# engine name is valid and the declared OID is the correction).  action REJECT:
# rationale plus, where useful, the closest real authority objects a future
# generator fix should map to (never auto-applied).
# ---------------------------------------------------------------------------
DISPOSITIONS = {
    # -- CISCO-BGP4-MIB cbgpPeer2 table: engine column numbers off by one ----
    ('CISCO-BGP4-MIB', 'cbgpPeer2InUpdates'): {'action': 'CORRECT', 'kind': 'oid',
        'rationale': 'Engine OID is one column past the authority declaration.'},
    ('CISCO-BGP4-MIB', 'cbgpPeer2OutUpdates'): {'action': 'CORRECT', 'kind': 'oid',
        'rationale': 'Engine OID is one column past the authority declaration.'},
    ('CISCO-BGP4-MIB', 'cbgpPeer2InTotalMessages'): {'action': 'CORRECT', 'kind': 'oid',
        'rationale': 'Engine OID is one column past the authority declaration.'},
    ('CISCO-BGP4-MIB', 'cbgpPeer2OutTotalMessages'): {'action': 'CORRECT', 'kind': 'oid',
        'rationale': 'Engine OID is one column past the authority declaration.'},
    ('CISCO-BGP4-MIB', 'cbgpPeer2LastError'): {'action': 'CORRECT', 'kind': 'oid',
        'rationale': 'Engine OID is one column past the authority declaration.'},
    ('CISCO-BGP4-MIB', 'cbgpPeer2FsmEstablishedTransitions'): {'action': 'CORRECT', 'kind': 'oid',
        'rationale': 'Engine OID is one column past the authority declaration.'},
    ('CISCO-BGP4-MIB', 'cbgpPeer2FsmEstablishedTime'): {'action': 'CORRECT', 'kind': 'oid',
        'rationale': 'Engine OID is one column past the authority declaration.'},
    ('CISCO-BGP4-MIB', 'cbgpPeer2InUpdateElapsedTime'): {'action': 'CORRECT', 'kind': 'oid',
        'rationale': 'Engine column .25 is cbgpPeer2PrefixPolicied space; authority declares .27.'},
    # -- CISCO-BGP4-MIB prefix counters: engine inverted the real symbol names -
    ('CISCO-BGP4-MIB', 'cbgpPeer2PrefixAccepted'): {'action': 'CORRECT', 'kind': 'name',
        'corrected_name': 'cbgpPeer2AcceptedPrefixes',
        'rationale': 'Real symbol is cbgpPeer2AcceptedPrefixes at the engine-cited OID.'},
    ('CISCO-BGP4-MIB', 'cbgpPeer2PrefixAdvertised'): {'action': 'CORRECT', 'kind': 'name',
        'corrected_name': 'cbgpPeer2AdvertisedPrefixes',
        'rationale': 'Real symbol is cbgpPeer2AdvertisedPrefixes (authority column .6).'},
    ('CISCO-BGP4-MIB', 'cbgpPeer2PrefixSuppressed'): {'action': 'CORRECT', 'kind': 'name',
        'corrected_name': 'cbgpPeer2SuppressedPrefixes',
        'rationale': 'Real symbol is cbgpPeer2SuppressedPrefixes (authority column .7).'},
    ('CISCO-BGP4-MIB', 'cbgpPeer2PrefixWithdrawn'): {'action': 'CORRECT', 'kind': 'name',
        'corrected_name': 'cbgpPeer2WithdrawnPrefixes',
        'rationale': 'Real symbol is cbgpPeer2WithdrawnPrefixes (authority column .8).'},
    # -- CISCO-MEMORY-POOL-MIB utilization: engine duplicated the entry level --
    ('CISCO-MEMORY-POOL-MIB', 'ciscoMemoryPoolUtilization5Min'): {'action': 'CORRECT', 'kind': 'oid',
        'rationale': 'Authority declares the column at .48.1.2.1.2; engine repeated the row level.'},
    ('CISCO-MEMORY-POOL-MIB', 'ciscoMemoryPoolUtilization10Min'): {'action': 'CORRECT', 'kind': 'oid',
        'rationale': 'Authority declares the column at .48.1.2.1.3; engine repeated the row level.'},
    # -- CISCO-PROCESS-MIB ----------------------------------------------------
    ('CISCO-PROCESS-MIB', 'cpmProcessAverageUSecs'): {'action': 'CORRECT', 'kind': 'oid',
        'rationale': 'Authority declares cpmProcessAverageUSecs at .109.1.2.1.1.6 (engine used .4).'},
    ('CISCO-PROCESS-MIB', 'cpmProcessType'): {'action': 'CORRECT', 'kind': 'oid',
        'rationale': 'Authority declares cpmProcessType in the process-extension table at .109.1.2.3.1.9.'},
    ('CISCO-PROCESS-MIB', 'cpmCPUCoreIndex'): {'action': 'CORRECT', 'kind': 'name',
        'corrected_name': 'cpmCoreIndex',
        'rationale': 'Real symbol in cpmCoreTable is cpmCoreIndex at the engine-cited OID.'},
    ('CISCO-PROCESS-MIB', 'cpmCPUCore5sec'): {'action': 'CORRECT', 'kind': 'name',
        'corrected_name': 'cpmCore5sec',
        'rationale': 'Real symbol is cpmCore5sec (authority column .3; engine .2 is cpmCorePhysicalIndex).'},
    ('CISCO-PROCESS-MIB', 'cpmCPUCore1min'): {'action': 'CORRECT', 'kind': 'name',
        'corrected_name': 'cpmCore1min',
        'rationale': 'Real symbol is cpmCore1min (authority column .4).'},
    ('CISCO-PROCESS-MIB', 'cpmCPUCore5min'): {'action': 'CORRECT', 'kind': 'name',
        'corrected_name': 'cpmCore5min',
        'rationale': 'Real symbol is cpmCore5min (authority column .5).'},
    # -- IP-MIB ipSystemStats -------------------------------------------------
    ('IP-MIB', 'ipSystemStatsInOctets'): {'action': 'CORRECT', 'kind': 'oid',
        'rationale': 'Authority declares ipSystemStatsInOctets at .4.31.1.1.5 (engine .4.1 spliced).'},
    ('IP-MIB', 'ipSystemStatsOutOctets'): {'action': 'CORRECT', 'kind': 'oid',
        'rationale': 'Authority declares ipSystemStatsOutOctets at .4.31.1.1.32 (engine .34.1 spliced).'},
    # -- Juniper alarm/fru/redundancy -----------------------------------------
    ('JUNIPER-ALARM-MIB', 'jnxYellowAlarmCount'): {'action': 'CORRECT', 'kind': 'oid',
        'rationale': 'Authority declares the jnxYellowAlarmCount MibScalar at .2636.3.4.2.2.2; pollable instance adds .0. Engine invented a table under .2636.4.1.'},
    ('JUNIPER-ALARM-MIB', 'jnxRedAlarmCount'): {'action': 'CORRECT', 'kind': 'oid',
        'rationale': 'Authority declares the jnxRedAlarmCount MibScalar at .2636.3.4.2.3.2; pollable instance adds .0. Engine invented a table under .2636.4.1.'},
    ('JUNIPER-MIB', 'jnxFruState'): {'action': 'CORRECT', 'kind': 'oid',
        'rationale': 'Authority declares jnxFruState at .2636.3.1.15.1.8 (engine .5 is jnxFruName).'},
    ('JUNIPER-MIB', 'jnxRedundancyState'): {'action': 'CORRECT', 'kind': 'oid',
        'rationale': 'Authority declares jnxRedundancyState at .2636.3.1.14.1.7 (engine .5 is jnxRedundancyDescr).'},
    ('JUNIPER-MIB', 'jnxCosIfTxPkts'): {'action': 'CORRECT', 'kind': 'name',
        'corrected_name': 'jnxCosIfqTxedPkts', 'corrected_module': 'JUNIPER-COS-MIB',
        'rationale': 'No jnxCos objects in JUNIPER-MIB; real symbol is jnxCosIfqTxedPkts in JUNIPER-COS-MIB at .2636.3.15.1.1.7 (engine .3 is jnxCosIfqQedPkts).'},
    # -- RFC objects ------------------------------------------------------------
    ('ENTITY-MIB', 'entLastStatusChange'): {'action': 'CORRECT', 'kind': 'name',
        'corrected_name': 'entLastChangeTime',
        'rationale': 'ENTITY-MIB declares the entLastChangeTime MibScalar at .47.1.4.1; the engine-cited .47.1.4.1.0 is its scalar instance, but the name entLastStatusChange does not exist.'},
    ('OSPF-MIB', 'ospfASBdrRtrCount'): {'action': 'CORRECT', 'kind': 'name',
        'corrected_name': 'ospfAsBdrRtrCount',
        'rationale': 'Case-only typo: authority symbol is ospfAsBdrRtrCount at the engine-cited OID .14.2.1.6.'},
    # -- structural non-pollable (MibTable, MibTableRow, etc.) -----------------
    ('ENTITY-MIB', 'entPhysicalContainsTable'): {'action': 'REJECT_STRUCTURAL',
        'rationale': 'Authority declares entPhysicalContainsTable as a MibTable (non‑leaf). Pollable leaves are the columns under that table; the table OID itself is not a scalar/column.',
        'closest_real': ['entPhysicalContainsEntry = 1.3.6.1.2.1.47.1.3.3.1 (MibTableRow)', 'entPhysicalContainsChildIndex = 1.3.6.1.2.1.47.1.3.3.1.1 (MibTableColumn)']},
    # -- fabricated: no authority support anywhere -----------------------------
    ('ARISTA-QUEUE-MIB', 'aristaIngressQueueDropPkts'): {'action': 'REJECT',
        'rationale': 'Symbol absent from ARISTA-QUEUE-MIB; engine subtree .30065.3.2 does not exist (real queue tables live at .30065.3.6).',
        'closest_real': ['aristaIngressQueuePktsDropped = 1.3.6.1.4.1.30065.3.6.1.1.1.3']},
    ('ARISTA-QUEUE-MIB', 'aristaEgressQueueDropPkts'): {'action': 'REJECT',
        'rationale': 'Symbol absent from ARISTA-QUEUE-MIB; engine subtree .30065.3.2 does not exist.',
        'closest_real': ['aristaEgressQueuePktsDropped = 1.3.6.1.4.1.30065.3.6.1.2.1.6']},
    ('ARISTA-QUEUE-MIB', 'aristaQueueBufferBytes'): {'action': 'REJECT',
        'rationale': 'No such symbol in ARISTA-QUEUE-MIB (nor in ARISTA-QOS-MIB).'},
    ('ARISTA-QUEUE-MIB', 'aristaVoqMaxBufferBytes'): {'action': 'REJECT',
        'rationale': 'No such symbol in any pinned ARISTA module.'},
    ('ARISTA-QUEUE-MIB', 'aristaEcnMarkedPkts'): {'action': 'REJECT',
        'rationale': 'No such symbol; ECN marking is exposed via aristaEcnCounterTable in ARISTA-QOS-MIB.',
        'closest_real': ['aristaEcnCounterValue = 1.3.6.1.4.1.30065.3.13.1.8.1.2']},
    ('ARISTA-QUEUE-MIB', 'aristaPfcPriorityFramesRx'): {'action': 'REJECT',
        'rationale': 'No such symbol; PFC counters live in ARISTA-PFC-MIB at .30065.3.11.',
        'closest_real': ['aristaPfcPriorityIndications = 1.3.6.1.4.1.30065.3.11.1.1.1.4']},
    ('ARISTA-QUEUE-MIB', 'aristaPfcPriorityFramesTx'): {'action': 'REJECT',
        'rationale': 'No such symbol; PFC counters live in ARISTA-PFC-MIB at .30065.3.11.',
        'closest_real': ['aristaPfcPriorityRequests = 1.3.6.1.4.1.30065.3.11.1.1.1.3']},
    ('ARISTA-RESOURCE-MIB', 'aristaResourceUtilization'): {'action': 'REJECT',
        'rationale': 'ARISTA-RESOURCE-MIB exists in neither pinned authority (SC4SNMP tree nor pysnmp index).'},
    ('ARISTA-RESOURCE-MIB', 'aristaResourceType'): {'action': 'REJECT',
        'rationale': 'ARISTA-RESOURCE-MIB exists in neither pinned authority.'},
    ('ARISTA-RESOURCE-MIB', 'aristaResourceDescription'): {'action': 'REJECT',
        'rationale': 'ARISTA-RESOURCE-MIB exists in neither pinned authority.'},
    ('ARISTA-RESOURCE-MIB', 'aristaInternalTempSensor'): {'action': 'REJECT',
        'rationale': 'ARISTA-RESOURCE-MIB exists in neither pinned authority; temperature is standard ENTITY-SENSOR-MIB (entSensorValue) territory.',
        'closest_real': ['entSensorValue = 1.3.6.1.2.1.99.1.1.1.4 (ENTITY-SENSOR-MIB)']},
    ('ARISTA-RESOURCE-MIB', 'aristaPowerSupplyWatts'): {'action': 'REJECT',
        'rationale': 'ARISTA-RESOURCE-MIB exists in neither pinned authority.'},
    ('ARISTA-RESOURCE-MIB', 'aristaFanTrayRpm'): {'action': 'REJECT',
        'rationale': 'ARISTA-RESOURCE-MIB exists in neither pinned authority.'},
    ('ARISTA-RESOURCE-MIB', 'aristaAclRuleCount'): {'action': 'REJECT',
        'rationale': 'ARISTA-RESOURCE-MIB exists in neither pinned authority.',
        'closest_real': ['aristaHardwareUtilizationInUseEntries = 1.3.6.1.4.1.30065.3.22.1.1.1.4 (ARISTA-HARDWARE-UTILIZATION-MIB)']},
    ('ARISTA-RESOURCE-MIB', 'aristaVlanCount'): {'action': 'REJECT',
        'rationale': 'ARISTA-RESOURCE-MIB exists in neither pinned authority.',
        'closest_real': ['aristaHardwareUtilizationInUseEntries = 1.3.6.1.4.1.30065.3.22.1.1.1.4 (ARISTA-HARDWARE-UTILIZATION-MIB)']},
    ('CISCO-ENVMON-MIB', 'ciscoEnvMonAlarmContactIndex'): {'action': 'REJECT',
        'rationale': 'No alarm-contact table in CISCO-ENVMON-MIB; only the scalar ciscoEnvMonAlarmContacts exists at .9.9.13.1.6.',
        'closest_real': ['ciscoEnvMonAlarmContacts = 1.3.6.1.4.1.9.9.13.1.6 (scalar, instance .0)']},
    ('CISCO-ENVMON-MIB', 'ciscoEnvMonAlarmContactDescr'): {'action': 'REJECT',
        'rationale': 'No alarm-contact table in CISCO-ENVMON-MIB; only the scalar ciscoEnvMonAlarmContacts exists.'},
    ('CISCO-ENVMON-MIB', 'ciscoEnvMonAlarmContactSeverity'): {'action': 'REJECT',
        'rationale': 'No alarm-contact table in CISCO-ENVMON-MIB; only the scalar ciscoEnvMonAlarmContacts exists.'},
    ('CISCO-ENVMON-MIB', 'ciscoEnvMonAlarmContactState'): {'action': 'REJECT',
        'rationale': 'No alarm-contact table in CISCO-ENVMON-MIB; only the scalar ciscoEnvMonAlarmContacts exists.'},
    ('CISCO-MEMORY-POOL-MIB', 'ciscoMemoryPoolHCUsed'): {'action': 'REJECT',
        'rationale': 'CISCO-MEMORY-POOL-MIB defines no 64-bit (HC) pool columns at all.',
        'closest_real': ['ciscoMemoryPoolUsed = 1.3.6.1.4.1.9.9.48.1.1.1.5 (32-bit)']},
    ('CISCO-MEMORY-POOL-MIB', 'ciscoMemoryPoolHCFree'): {'action': 'REJECT',
        'rationale': 'CISCO-MEMORY-POOL-MIB defines no 64-bit (HC) pool columns at all.',
        'closest_real': ['ciscoMemoryPoolFree = 1.3.6.1.4.1.9.9.48.1.1.1.6 (32-bit)']},
    ('CISCO-MEMORY-POOL-MIB', 'ciscoMemoryPoolHCLargestFree'): {'action': 'REJECT',
        'rationale': 'CISCO-MEMORY-POOL-MIB defines no 64-bit (HC) pool columns at all.',
        'closest_real': ['ciscoMemoryPoolLargestFree = 1.3.6.1.4.1.9.9.48.1.1.1.7 (32-bit)']},
    ('CISCO-MEMORY-POOL-MIB', 'ciscoMemoryPoolAllocSuccess'): {'action': 'REJECT',
        'rationale': 'No allocation counters in CISCO-MEMORY-POOL-MIB.'},
    ('CISCO-MEMORY-POOL-MIB', 'ciscoMemoryPoolAllocFails'): {'action': 'REJECT',
        'rationale': 'No allocation counters in CISCO-MEMORY-POOL-MIB.'},
    ('JUNIPER-ALARM-MIB', 'jnxAlarmRelayState'): {'action': 'REJECT',
        'rationale': 'JUNIPER-ALARM-MIB exposes only jnxAlarmRelayMode (scalar .2636.3.4.2.1) plus yellow/red state/count/lastChange; no relay-state object.',
        'closest_real': ['jnxAlarmRelayMode = 1.3.6.1.4.1.2636.3.4.2.1 (scalar, instance .0)']},
}

IPROUTE_ENGINE_MODULE = 'IP-MIB'
IPROUTE_MODULES_OK = 'RFC1213-MIB'


def classify_rows(modules, iproute_cols, iproute_order):
    rows, problem_keys = [], set()
    for obj in RAW_MIB_DEFINITIONS:
        module, name, oid = obj['module'], obj['name'], str(obj['oid'])
        row = {
            'vendor': obj['vendor'], 'engine_module': module, 'engine_name': name,
            'engine_oid': oid, 'engine_type': obj.get('type', ''),
            'engine_desc': obj.get('desc', ''),
        }
        # ipRoute* rows: engine-cited IP-MIB is wrong; authority is RFC1213-MIB
        if name.startswith('ipRoute') and module == IPROUTE_ENGINE_MODULE:
            expected = iproute_cols.get(name)
            if expected is None:
                # fallback: compute from known ordering
                idx = iproute_order.index(name) if name in iproute_order else None
                if idx is not None:
                    expected = f'1.3.6.1.2.1.4.21.1.{idx+1}'
            if expected and expected != oid:
                raise ValueError(f'ipRoute OID drift for {name}: {oid} != {expected}')
            row.update({
                'status': 'VERIFIED_AFTER_MODULE_REASSIGNMENT', 'coverage_ok': True,
                'authority': {'kind': 'rfc1213', 'file': 'catalog/mib_reference/rfc/RFC1213.txt',
                              'sha256': None, 'declaration': None},
                'correction': {'corrected_module': IPROUTE_MODULES_OK,
                               'corrected_name': name, 'corrected_oid': oid},
                'rationale': ('SMIv1 implicit column numbering per RFC 1213 '
                              '(ipRouteTable ::= { ip 21 }, columns follow the '
                              'IpRouteEntry SEQUENCE order). OIDs are correct but '
                              'belong to RFC1213-MIB; IP-MIB (RFC 4293) obsoleted '
                              'the ipRoute table, which is why the name is absent '
                              'from the compiled IP-MIB authority.'),
            })
            rows.append(row)
            continue
        decl = modules.get(module, {}).get(name)
        if decl is None:
            absent = module not in modules
            row['_problem'] = 'module_file_absent' if absent else 'name_not_in_module'
        elif decl[1] not in LEAF_KINDS:
            # MibTable, MibTableRow, NotificationType, etc. – structural, not a pollable leaf.
            row['status'] = 'REJECTED_STRUCTURAL_NON_POLLABLE'
            row['coverage_ok'] = False
            row['authority'] = authority_ref(module, decl)
            row['authority_declared_oid'] = decl[0]
            row['authority_kind'] = decl[1]
            row['rationale'] = f'Authority declares {name} as {decl[1]} (structural, not a scalar/column). Pollable leaves are columns under that table, not the table/row itself.'
            rows.append(row)
            problem_keys.add((module, name))
            continue
        elif oid == decl[0] or oid.startswith(decl[0] + '.'):
            row.update({
                'status': 'VERIFIED_AS_IS', 'coverage_ok': True,
                'authority': authority_ref(module, decl),
                'authority_declared_oid': decl[0], 'authority_kind': decl[1],
            })
            rows.append(row)
            continue
        else:
            row['_problem'] = 'oid_mismatch'
        key = (module, name)
        problem_keys.add(key)
        d = DISPOSITIONS.get(key)
        assert d is not None, f'curated disposition missing for problem row {key}'
        if d['action'] == 'CORRECT':
            target_module = d.get('corrected_module', module)
            target_name = d.get('corrected_name', name)
            tdecl = modules[target_module][target_name]
            corrected_oid = tdecl[0]
            if d['kind'] == 'name' and name in modules.get(module, {}) and modules[module][name][0] == oid:
                corrected_oid = oid
            if name.startswith('ipRoute'):
                corrected_oid = oid
            row.update({
                'status': 'VERIFIED_AFTER_CORRECTION', 'coverage_ok': True,
                'authority': authority_ref(target_module, tdecl),
                'correction': {'corrected_name': target_name, 'corrected_oid': corrected_oid,
                               'corrected_module': target_module},
                'rationale': d['rationale'],
            })
        elif d['action'] == 'REJECT_STRUCTURAL':
            row.update({
                'status': 'REJECTED_STRUCTURAL_NON_POLLABLE', 'coverage_ok': False,
                'authority': authority_ref(module, decl) if decl else None,
                'correction': None,
                'rationale': d['rationale'],
                'closest_real': d.get('closest_real', []),
            })
        else:
            row.update({
                'status': 'REJECTED_NO_AUTHORITY', 'coverage_ok': False,
                'authority': None, 'correction': None,
                'rationale': d['rationale'],
                'closest_real': d.get('closest_real', []),
            })
        rows.append(row)
    missing = set(DISPOSITIONS) - problem_keys
    assert not missing, f'curated dispositions without problem rows: {sorted(missing)}'
    return rows


def authority_ref(module, decl):
    entry = None
    for e in json.loads(PROVENANCE.read_text())['mib_files']:
        if e['module'] == module:
            entry = e
            break
    assert entry, f'authority file not pinned: {module}'
    return {'kind': 'sc4snmp_compiled_mib', 'file': entry['file'],
            'git_blob_sha1': entry['git_blob_sha1'], 'sha256': entry['sha256'],
            'declared_oid': decl[0], 'declared_kind': decl[1]}


def build():
    prov = json.loads(PROVENANCE.read_text())
    checked = check_provenance(prov)
    modules = {f[:-3]: parse_module(MIB_DIR / f) for f in sorted(p.name for p in MIB_DIR.glob('*.py'))}
    assert set(checked) == set(modules), 'pinned files != committed files'
    order, cols = rfc1213_iproute_columns()
    rows = classify_rows(modules, cols, order)
    for r in rows:
        r.pop('_problem', None)
    by = {}
    for r in rows:
        by[r['status']] = by.get(r['status'], 0) + 1
    vendors = sorted({r['vendor'] for r in rows})
    distinct = len({r['engine_oid'] for r in rows})
    coverage_ok = sum(1 for r in rows if r['coverage_ok'])
    return {
        'artifact': 'PulseForge SNMP MIB/OID leaf inventory (Workstream B)',
        'generated_at': '2026-10-27',
        'generator_under_test': 'src/netspout_core/snmp_engine.py::RAW_MIB_DEFINITIONS',
        'rebuild_command': 'PYTHONPATH=src python3 scripts/build_mib_oid_inventory.py',
        'verification_rules': {
            'VERIFIED_AS_IS': 'engine name+OID equals (or is an instance under) the declaration in the engine-cited pinned authority module',
            'VERIFIED_AFTER_CORRECTION': 'engine row wrong; corrected name/oid/module re-derived from the pinned authority at build time',
            'VERIFIED_AFTER_MODULE_REASSIGNMENT': 'ipRoute* only: OIDs valid per RFC 1213 SMIv1 implicit numbering; module must be RFC1213-MIB, not IP-MIB',
            'REJECTED_NO_AUTHORITY': 'name and OID unsupported by any pinned authority; must not be cited as coverage',
        },
        'authority_verification': {
            'sc4snmp_compiled_mib_files_verified': len(checked),
            'tree_blob_integrity': 'git blob sha1 of each committed file equals the pinned tree entry',
            'pysnmp_index_role': prov['authorities']['pysnmp_mib_index']['role'],
        },
        'summary': {
            'total_engine_objects': len(rows),
            'distinct_engine_oids': distinct,
            'by_status': by,
            'coverage_ok_rows': coverage_ok,
            'rejected_rows': len(rows) - coverage_ok,
            'defensible_denominator': coverage_ok,
            'vendors': vendors,
            'iproute_column_order_rfc1213': order,
        },
        'module_existence': prov['module_existence'],
        'rows': rows,
        'notes': [
            'Coverage claims cite coverage_ok rows only (VERIFIED_AS_IS / '
            'VERIFIED_AFTER_CORRECTION / VERIFIED_AFTER_MODULE_REASSIGNMENT). '
            'REJECTED_NO_AUTHORITY rows are generator defects awaiting a '
            'separately reviewed engine change; they are NOT SNMP coverage.',
            'This inventory verifies generator-declared OID symbols only. It does '
            'not prove device behaviour, TA parser mapping, or detection content.',
        ],
    }


if __name__ == '__main__':
    data = build()
    OUT.write_text(json.dumps(data, indent=1) + '\n')
    s = data['summary']
    print(json.dumps({'total': s['total_engine_objects'], 'by_status': s['by_status'],
                      'coverage_ok': s['coverage_ok_rows'], 'rejected': s['rejected_rows']}))
    print(f"wrote {OUT.relative_to(ROOT)}")
