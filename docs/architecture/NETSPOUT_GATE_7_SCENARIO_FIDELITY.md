# NETSPOUT GATE 7: GOLDEN PATH EXPANSION & MULTI-VENDOR SCENARIO FIDELITY

**Author**: Mahamudul Chowdhury (`machowdhury@yahoo.com`)  
**Gate**: Gate 7 — Golden Path Expansion & Multi-Vendor Scenario Fidelity  
**Status**: COMPLETE  
**Repository**: `machowdhury/NetSpout`  
**Date**: September 25, 2026  

---

## 1. Executive Summary

NetSpout Gate 7 expands the simulation platform from a single Golden-Path scenario (`cisco_sdwan_brownout`) into a multi-domain, multi-vendor network operations platform. Following the recommendations of Gate 6.5 (Master Specification Reconciliation & Product Gap Analysis), Gate 7 focuses with strict discipline on exactly three target scenarios across distinct network domains without expanding vendor catalogs, introducing duplicate hydrators, or claiming unimplemented wire-level protocols.

### Target Scenario Triad

| Scenario ID | Code | Domain | Multi-Vendor / Device Scope | Telemetry & Wire Formats | Maturity |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `cisco_campus_rogue` | `CISCO-A1` | Campus / Wireless | Cisco Catalyst 9300, Cisco Catalyst 9800 WLC, Cisco ISE | Syslog RFC 5424, 802.1X RADIUS, MAC flap notification | `E2E_VALIDATED` |
| `cisco_aci_microburst` | `CISCO-A3` | Datacenter / ACI Fabric | Cisco Nexus 9300 Leaf, Cisco ACI APIC Spine/Leaf | Cisco MDT JSON telemetry, Nexus 9K ASIC syslog, ACI Fabric Health score | `E2E_VALIDATED` |
| `mixed_edge_breach` | `MIXED-B1` | Multi-Vendor Security | Cisco Meraki AP, Palo Alto NGFW, Fortinet FortiGate, NGINX Web Server | Meraki JSON Webhook, PAN-OS 54-field CSV, FortiOS Key-Value Syslog, W3C HTTP | `E2E_VALIDATED` |

---

## 2. Architectural Guardrails & Invariants Preserved

NetSpout Gate 7 preserves and strengthens all core architectural invariants established in Gates 1 through 6:

1. **Single Source of Truth**: All simulation logic resides strictly in `src/netspout_core/`. Generated packaged copies in `netspout/bin/` and `backend/app/` are automatically synchronized via `scripts/sync_core.py` and audited via `scripts/verify_sources.py`.
2. **Canonical Catalog Discipline**: Canonical catalogs remain in `catalog/` (synced to `netspout/catalog/` and runtime dirs). No uncontracted or synthetic vendors were added beyond the audited 36 vendors.
3. **Execution Separation Invariant**:
   $$\text{GENERATED} \neq \text{DISPATCHED} \neq \text{OBSERVED} \neq \text{VALIDATED}$$
   Simulation generation produces local `LogEntry` records; dispatcher attempts transport transmission; observation independently queries destination search indexes; validation verifies explicit contract rules.
4. **Destination Evidence Requirement**: A scenario run cannot report `destination_validation: PASS` unless the Splunk REST API confirms at least one indexed event matching the unique `netspout_run_id`.
5. **No Wire Flow False Claims**: NetFlow v9/IPFIX binary UDP 2055 and native SNMP binary UDP 162 remain honestly documented as simulated JSON/HEC payloads rather than unverified socket listeners.

---

## 3. Dedicated Scenario Telemetry Generators

### 3.1 Cisco Campus Rogue AP (`cisco_campus_rogue`)
- **Domain**: Campus Enterprise LAN / Wireless Security
- **Progression**:
  - `BASELINE`: Catalyst 9300 core switch and Cisco ISE generate nominal 802.1X client authentication events (`cisco:catalyst:security:events`, `cisco:ise:syslog`).
  - `FAULT`: Unsanctioned Rogue AP powers on emitting corporate SSID beacon frames; Catalyst 9800 WLC flags rogue on RF matrix (`cisco:catalyst:rogue:threat_details`, action=alerted, status=breached).
  - `PROPAGATE`: Rogue broadcast injection induces Layer 2 broadcast disturbance and MAC address flapping between access ports `GigabitEthernet1/0/12` and `1/0/48` (`cisco:ios:syslog`, `%SW_MATM-4-MACFLAP_NOTIF`).
  - `FAILOVER`: Cisco ISE issues Change of Authorization (CoA) quarantine profile; Catalyst switch places flapping port in error-disabled quarantine state (`cisco:ise:syslog`, `cisco:catalyst:security:events`, action=blocked).
  - `RECOVER`: Rogue AP de-authenticated and removed from RF matrix; switchport re-enabled in standard VLAN (`status=restored`).

### 3.2 Cisco ACI Microburst (`cisco_aci_microburst`)
- **Domain**: Spine-Leaf Datacenter Fabric / ASIC Buffer Queuing
- **Temporal Modeling**:
  - `BASELINE`: East-West container traffic flowing with nominal queue depth (< 2MB, e.g. 1.25MB), peak buffer utilization at 12.5%, 0 dropped packets, and fabric health score 100/100 (`cisco:ios:mdt`, `cisco:dc:aci:health`, `cisco:dc:nexus9k:syslog`).
  - `FAULT`: Sub-millisecond microburst incast saturates leaf switch ingress ASIC buffers; queue depth spikes to 26.5MB (> 25MB), 1,250 dropped packets recorded, and ACI fabric health score drops to 58 (`status=degraded`).
  - `PROPAGATE`: Priority Flow Control (PFC) pause storm propagates upstream; egress queue climbs to 28.9MB, peak buffer reaches 99.1%, and health drops to 52 (`%ETHPORT-5-IF_RX_OVERFLOW`).
  - `FAILOVER`: ASIC QoS dynamic buffer reserving expands burst absorption pools; packet drops drop from 1,250 to 5, and fabric health score recovers to 85.
  - `RECOVER`: Incast traffic drains; queue depth normalizes to 1.4MB, dropped packets return to 0, and fabric health score is restored to 100/100 (`status=restored`).

### 3.3 Mixed Edge Breach (`mixed_edge_breach`)
- **Domain**: Multi-Vendor Edge Security Perimeter
- **Multi-Vendor Wire Format Diversity**:
  1. **Cisco Meraki AP**: Native JSON Webhook payload (`meraki:assurancealerts`, with `alertType="air_marshal_rogue_detected"`).
  2. **Palo Alto Networks NGFW**: 54-field CSV format string (`pan:threat` and `pan:traffic`, with `THREAT,vulnerability,...`).
  3. **Fortinet FortiOS**: Standard Key-Value UTM Syslog (`fortinet:fortigate:utm`, with `<189>date=... devname="..." logid="0419016384" type="utm" subtype="ips" attack="..." action="dropped"`).
  4. **NGINX Web Server**: W3C Combined HTTP Access Log (`nginx:plus:kv`, with HTTP `POST /api/v1/admin/exploit 403 Forbidden`).
- **Progression**:
  - `BASELINE`: Permitted corporate web traffic flowing through Palo Alto NGFW (`pan:traffic`, action=allowed) and FortiGate UTM (`fortinet:fortigate:utm`, action=allowed).
  - `FAULT`: Adversary probes wireless edge; Meraki Air Marshal triggers rogue detection alert (JSON), while Palo Alto NGFW detects initial port scan (`pan:threat`, action=dropped).
  - `PROPAGATE`: Lateral movement attempts exploit internal API; Fortinet FortiOS IPS drops Cobalt Strike beacon attempt (`fortinet:fortigate:utm`, action=dropped), while NGINX reverse proxy denies unauthorized URI path with HTTP 403.
  - `FAILOVER`: Automated perimeter response triggers Palo Alto microsegmentation isolation (`action=blocked`) and Fortinet dynamic IP blacklist quarantine (`action=dropped`).
  - `RECOVER`: Attacker source IP isolated; clean enterprise traffic resumes across Palo Alto and Fortinet perimeter (`status=restored`).

---

## 4. Contract Validation Rules & Negative Testing

Each target scenario includes 4 distinct contract validation rules registered in `catalog/scenarios.json`:

| Scenario ID | Rule ID | Rule Type | Target Field / Sourcetype | Expected Value / Min Count |
| :--- | :--- | :--- | :--- | :--- |
| `cisco_campus_rogue` | `rogue-val-01` | `COUNT_THRESHOLD` | `cisco:catalyst:rogue:threat_details` | $\ge 1$ |
| | `rogue-val-02` | `EVENT_EXISTS` | `action` | `"alerted"` |
| | `rogue-val-03` | `COUNT_THRESHOLD` | `cisco:ise:syslog` | $\ge 1$ |
| | `rogue-val-04` | `EVENT_EXISTS` | `status` | `"restored"` |
| `cisco_aci_microburst` | `aci-val-01` | `COUNT_THRESHOLD` | `cisco:dc:aci:health` | $\ge 1$ |
| | `aci-val-02` | `EVENT_EXISTS` | `status` | `"degraded"` |
| | `aci-val-03` | `COUNT_THRESHOLD` | `cisco:dc:nexus9k:syslog` | $\ge 1$ |
| | `aci-val-04` | `EVENT_EXISTS` | `status` | `"restored"` |
| `mixed_edge_breach` | `mixed-val-01` | `COUNT_THRESHOLD` | `pan:threat` | $\ge 1$ |
| | `mixed-val-02` | `EVENT_EXISTS` | `action` | `"dropped"` |
| | `mixed-val-03` | `COUNT_THRESHOLD` | `fortinet:fortigate:utm` | $\ge 1$ |
| | `mixed-val-04` | `COUNT_THRESHOLD` | `meraki:assurancealerts` | $\ge 1$ |

### Negative Test Enforcement
Automated tests in `tests/test_gate7_fidelity.py` verify:
1. Missing sourcetypes immediately cause `COUNT_THRESHOLD` rules to fail with status `FAIL`.
2. Unexpected or altered field values cause `EVENT_EXISTS` rules to fail.
3. Unattainable count thresholds (e.g. min_count=999) evaluate to `FAIL`.
4. User cancellation mid-run sets overall status to `BLOCKED`.

---

## 5. Live Splunk E2E Evidence Matrix

Executed live against Docker container `splunk-network-data-blaster` running Splunk Enterprise 10.2:
- **HEC Endpoint**: `https://127.0.0.1:8888/services/collector` (Token: `00000000-0000-0000-0000-000000000000`)
- **REST Query Endpoint**: `https://127.0.0.1:8889/services/search/jobs/export`
- **Index**: `idx_network_ops`

| Scenario ID | Run ID | Generated | Dispatched | Observed (REST) | Observation Status | Destination Validation | Contract Validation | Overall Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `cisco_campus_rogue` | `NS-20260925-a75cbaad` | 10 | 10 | 8 | `VERIFIED` | `PASS` | 4/4 `PASS` | `PASS` |
| `cisco_aci_microburst` | `NS-20260925-0064cb00` | 14 | 14 | 10 | `VERIFIED` | `PASS` | 4/4 `PASS` | `PASS` |
| `mixed_edge_breach` | `NS-20260925-80fc8fdc` | 10 | 10 | 10 | `VERIFIED` | `PASS` | 4/4 `PASS` | `PASS` |

*Note*: 100% of dispatched events received HTTP 200 from Splunk HEC and were indexed in `idx_network_ops`. Observed counts reflect the bounded sampling window of the REST search export.

---

## 6. Verification and Test Results

### 6.1 Gate 7 Dedicated Test Suite (`tests/test_gate7_fidelity.py`)
- **25 Tests**: 25/25 PASSED (100%)
- **Runtime**: 0.011s

### 6.2 Full Repository Gate Regression Suite (`tests/test_gate*.py`)
- **Gate 1**: Runtime & Process Isolation (15 tests) — PASS
- **Gate 2**: Canonical Core Synchronization (12 tests) — PASS
- **Gate 3**: Canonical Catalog Validation (15 tests) — PASS
- **Gate 4**: Use-Case Contracts & Ground Truth (22 tests) — PASS
- **Gate 5**: Unified UX & Frontend Integrity (22 tests) — PASS
- **Gate 6**: Evidence Semantics & Invariants (15 tests) — PASS
- **Gate 7**: Multi-Vendor Scenario Fidelity (25 tests) — PASS
- **Total**: **106 / 106 Tests Passed (100%)**

### 6.3 Packaging & Release Artifacts
- **Frontend Bundle**: Vite production build compiled into `frontend/dist/` (664KB JS, 0 lint errors).
- **Splunk Release Archive**: `netspout.spl` built (1.37MB, 652 files, SHA-256: `6e357c977c3bddcd4431e2ca4a622322c47da03220ab782de31ff4002c576a54`).

---

## 7. Status & Readiness

All three target scenarios (`cisco_campus_rogue`, `cisco_aci_microburst`, and `mixed_edge_breach`) are now marked `maturity: E2E_VALIDATED` and are **READY FOR ACCEPTANCE TESTING** in Golden Paths 02, 03, and 04.

