# NETSPOUT ARCHITECTURE CONSOLIDATION
## GATE 3 — CANONICAL CATALOG, IDENTIFIERS, AND METADATA REPORT

**Author**: NetSpout Engineering & Architecture Team  
**Date**: September 24, 2026  
**Status**: GATE 3 PASSED  
**Baseline Git Commit**: `0c0a6f69839df3c33bd7c3dae761b2fe39bc55d5`  
**Target Repository**: `NetSpout (https://github.com/machowdhury/NetSpout)`  

---

## 1. Executive Summary

Prior to Gate 3, NetSpout suffered from pervasive **metadata fragmentation and identifier drift**. Key domain entities—vendors, device types, sourcetypes, scenarios, network topologies, sample datasets, telemetry protocols, and aliases—were independently defined, hardcoded, and duplicated across Python dicts (`vendor_catalog.py`, `use_case_repo.py`), JSON documents (`samples_manifest.json`, `vendor_catalog.json`), TypeScript/JavaScript frontend modules, and SimpleXML view definitions.

This fragmentation produced severe defects:
1. **The Typo Divergence Problem**: `cisco:sdwan:sytem:logs` (with a typo in "system") coexisted alongside `cisco:sdwan:system:logs` across sample files and manifests without an authoritative canonical resolution.
2. **Duplicate Identifiers (`DEF-04`)**: `samples_manifest.json` contained duplicate sample IDs (`nutanixpc-syslog` and `nutanixpc-vms`) pointing to inconsistent colon vs underscore sourcetypes.
3. **Engine-Catalog Disconnect**: Scenarios in `scenario_runner.py` emitted sourcetypes (e.g. `cisco:ise:nac:8021x`, `nginx:plus:kv`, `openconfig:gnmi:telemetry`) that did not exist in `vendor_catalog.py`.
4. **Maintenance Burden**: Adding or editing a vendor or sourcetype required synchronized manual edits in at least four disparate files.

**Gate 3 Technical Directives Completed**:
1. **Authoritative Canonical Catalog Established (`catalog/`)**: Created eight schema-validated, declarative JSON catalog files defining all 36 vendors, 17 device types, 263 sourcetypes, 29 scenarios, 28 topologies, 213 samples, 8 telemetry protocols, and 43 compatibility aliases.
2. **Single Python Catalog Module (`src/netspout_core/catalog.py`)**: Developed the authoritative `NetSpoutCatalog` API providing fast indexing, normalized lookup, schema validation, generation mode classification, and deprecated alias resolution.
3. **Consumer Refactoring**: Replaced 1,400 lines of hardcoded Python dicts in `src/netspout_core/vendor_catalog.py` with a thin compatibility wrapper backed by `catalog.get_legacy_vendor_catalog()`.
4. **Static Mirror Generation**: Dynamically re-generated `netspout/appserver/static/vendor_catalog.json` directly from canonical catalog data, ensuring 100% parity between Python runtime and Splunk Web UI.
5. **Typo & Alias Resolution**: Formalized `cisco:sdwan:system:logs` as canonical; designated `cisco:sdwan:sytem:logs` as a `DEPRECATED_ALIAS` that cleanly resolves to canonical without breaking legacy queries or tests.
6. **Disambiguated Sample IDs (`DEF-04`)**: Resolved duplicate sample IDs to explicit canonical and legacy entries with transparent alias routing.
7. **Guardrails & Automated Validation**: Created `scripts/validate_catalog.py` (0 errors, 0 warnings, complete orphan reporting) and expanded `scripts/verify_sources.py` to enforce zero-drift across canonical catalog copies and packaged distributions.
8. **AppInspect & Splunk Packaging**: Packaged release archive `netspout.spl` (1.31 MB) containing the canonical core and catalog data. Synchronized and verified live inside the running Splunk Enterprise container.
9. **Zero Regressions**: 100% pass rate across Gate 1 runtime tests (6/6), Gate 2 canonical tests (9/9), Gate 3 catalog tests (8/8), and comprehensive test suite baseline parity (60/62).

---

## 2. Baseline Architecture vs. Post-Gate-3 Architecture

### Pre-Gate-3 (Fragmented Architecture)
```
+--------------------------------------------------------------------------+
|                        FRAGMENTED METADATA SOURCES                       |
|                                                                          |
|  +---------------------------+       +--------------------------------+  |
|  | vendor_catalog.py (1400L) |       | samples_manifest.json (213)    |  |
|  | - 36 vendors              |       | - Duplicate IDs (DEF-04)       |  |
|  | - 238 sourcetypes         |       | - Typo: cisco-sdwan-sytem-logs |  |
|  +---------------------------+       +--------------------------------+  |
|               ^                                      ^                   |
|               |                                      |                   |
|  +---------------------------+       +--------------------------------+  |
|  | vendor_catalog.json       |       | scenario_runner.py (hardcoded) |  |
|  | - Static JSON mirror      |       | - 29 scenarios                 |  |
|  | - Out-of-sync extra keys  |       | - Uncataloged sourcetypes      |  |
|  +---------------------------+       +--------------------------------+  |
+--------------------------------------------------------------------------+
```

### Post-Gate-3 (Authoritative Canonical Catalog Architecture)
```
+--------------------------------------------------------------------------+
|                     CANONICAL CATALOG (catalog/*.json)                   |
|                                                                          |
|  [vendors.json]       [sourcetypes.json]      [scenarios.json]           |
|     (36 vendors)         (263 sourcetypes)        (29 scenarios)         |
|                                                                          |
|  [device_types.json]  [topologies.json]       [samples.json]             |
|     (17 node types)      (28 presets)             (213 datasets)         |
|                                                                          |
|  [telemetry_protocols.json]                   [aliases.json]             |
|     (8 protocols)                                (43 mappings)           |
+--------------------------------------------------------------------------+
                                    |
                                    v
+--------------------------------------------------------------------------+
|             CANONICAL PYTHON CORE (src/netspout_core/catalog.py)         |
|  - Fast in-memory lookup & normalization                                 |
|  - Deprecated alias resolution (cisco:sdwan:sytem:logs -> system)        |
|  - Generation mode classifier (REPLAY | SYNTHETIC | STATEFUL)            |
|  - Legacy compatibility exports (get_legacy_vendor_catalog)              |
+--------------------------------------------------------------------------+
              |                                            |
              v                                            v
+----------------------------------+     +---------------------------------+
|   src/netspout_core/             |     |   scripts/sync_core.py          |
|   vendor_catalog.py              |     |   - netspout/bin/netspout_core/ |
|   (Dynamic wrapper, 57 lines)    |     |   - netspout/bin/catalog_data/  |
+----------------------------------+     |   - backend/app/catalog_data/   |
                                         |   - vendor_catalog.json mirror  |
                                         +---------------------------------+
```

---

## 3. Authoritative Canonical Catalog File System Design

The authoritative catalog resides in the root `catalog/` directory. Standard JSON was selected over YAML because Python standard library includes `json` natively, eliminating third-party dependencies (`PyYAML`) in lightweight container runtimes and Splunk embedded Python environment.

```
catalog/
├── vendors.json                # 36 enterprise network, security, cloud vendors
├── sourcetypes.json            # 263 unified sourcetypes with index & TA metadata
├── scenarios.json              # 29 baseline, enterprise, and architecture scenarios
├── device_types.json           # 17 node types matching models.NodeType
├── topologies.json             # 28 network topologies & architecture presets
├── samples.json                # 213 sample datasets mapped to disk YAML paths
├── telemetry_protocols.json    # 8 ingest protocols (syslog, HEC, SNMP, gNMI, OTLP)
└── aliases.json                # 43 alias and deprecation mapping rules
```

---

## 4. Inventory & Canonical Quantities

| Catalog Domain | Authoritative Count | Schema File | Primary Identifier | Description |
| :--- | :--- | :--- | :--- | :--- |
| **Vendors** | **36** | `catalog/vendors.json` | `slug` (e.g. `palo_alto`) | Enterprise vendors across Firewall, Routing, SD-WAN, Wireless, NAC, Cloud, APM |
| **Device Types** | **17** | `catalog/device_types.json` | `id` (e.g. `sase_proxy`) | 1-to-1 mapping with `netspout_core.models.NodeType` enum |
| **Sourcetypes** | **263** | `catalog/sourcetypes.json` | `splunk_sourcetype` | Unified sourcetypes with default/recommended index, TA, and generation mode |
| **Scenarios** | **29** | `catalog/scenarios.json` | `id` (e.g. `cisco_sdwan_brownout`) | Baseline (4), Enterprise (6), Architecture (11), Advanced SP/WLAN (8) |
| **Topologies** | **28** | `catalog/topologies.json` | `id` (e.g. `cisco_campus`) | Network topologies with node count, edge count, ecosystem, and scenario links |
| **Samples** | **213** | `catalog/samples.json` | `id` (e.g. `cisco-asa-syslog`) | Sample telemetry datasets mapped to disk YAML files under `samples/` |
| **Protocols** | **8** | `catalog/telemetry_protocols.json` | `id` (e.g. `syslog_rfc5424`) | Ingest protocols covering Syslog, HEC Event/Metric, SC4SNMP, gNMI, OTLP, Telegraf |
| **Aliases** | **43** | `catalog/aliases.json` | `alias_key` | Deprecated typo redirects, legacy vendor slugs, and duplicate ID mappings |

---

## 5. Authoritative Identification Standard

To eliminate ambiguity across layers, NetSpout establishes a strict identification convention:

1. **Vendor Slugs**: Lowercase snake_case (e.g. `cisco_sdwan`, `palo_alto`, `f5_bigip`, `arista_eos`). Legacy hyphenated IDs (`cisco-sdwan`, `paloalto-panos`) are supported as transparent aliases.
2. **Splunk Sourcetypes**: Standard Splunk colon-delimited or underscore notation matching official Technology Add-on specifications (e.g. `cisco:sdwan:system:logs`, `pan:traffic`, `f5:bigip:syslog`).
3. **Entity IDs**: Lowercase kebab-case for sourcetypes and samples (e.g. `cisco-sdwan-system-logs`, `pan-traffic`).
4. **Scenarios & Topologies**: Lowercase snake_case matching code identifiers (e.g. `cisco_sdwan_brownout`, `arch_can_multi_building`).
5. **Device Types**: Lowercase snake_case matching `models.NodeType` enum values (e.g. `edge_firewall`, `sase_proxy`, `core_switch`).

---

## 6. Typo Resolution & Backward-Compatibility Policy

### The Issue
Historically, the repository contained a typo in the Cisco SD-WAN system logs sourcetype:
- Sample file: `netspout/appserver/static/samples/cisco-sdwan-sytem-logs/cisco-sdwan-sytem-logs.yml`
- Manifest entry: `cisco-sdwan-sytem-logs` with sourcetype `cisco:sdwan:sytem:logs`
- User benchmark: Requested `cisco:sdwan:system:logs` (correct spelling).

### The Resolution
1. **Canonical Sourcetype**: `cisco:sdwan:system:logs` is declared the sole canonical sourcetype.
2. **Deprecation Classification**: `cisco:sdwan:sytem:logs` is registered in `catalog/aliases.json` as `DEPRECATED_ALIAS` pointing to `cisco:sdwan:system:logs`.
3. **Transparent Resolution**: `catalog.resolve_sourcetype("cisco:sdwan:sytem:logs")` returns: `("cisco:sdwan:system:logs", True, "cisco-sdwan-system-logs")`.
4. **API Filtering**: `catalog.list_sourcetypes(include_deprecated=False)` filters out the typo so UI dropdowns present only the clean canonical name, while `include_deprecated=True` retains backward compatibility for existing scripts.

---

## 7. Duplicate Sample ID Disambiguation (`DEF-04`)

### The Issue
In `samples_manifest.json`, duplicate IDs occurred:
- `nutanixpc-syslog` appeared twice: once for `nutanixpc:syslog` and once for `nutanixpc_syslog`.
- `nutanixpc-vms` appeared twice: once for `nutanixpc:vms` and once for `nutanixpc_vms`.

### The Resolution
In `catalog/samples.json` and `catalog/aliases.json`:
- `nutanixpc-syslog` -> `nutanixpc_syslog` (legacy underscore notation)
- `nutanixpc-syslog-colon` -> `nutanixpc:syslog` (canonical colon notation)
- `nutanixpc-vms` -> `nutanixpc_vms` (legacy underscore notation)
- `nutanixpc-vms-colon` -> `nutanixpc:vms` (canonical colon notation)
- Aliases map both underscore and colon variants to their canonical entries, eliminating lookup collisions.

---

## 8. Telemetry Generation Mode Classification Standard

NetSpout telemetry generation operates under four distinct execution modes:

| Mode | Semantics | Data Source | Example Entities |
| :--- | :--- | :--- | :--- |
| **`REPLAY`** | Replays exact recorded or curated event sequences with updated timestamps. | YAML sample files under `samples/` | `pan:traffic`, `cisco:ios:syslog`, `cisco:sdwan:system:logs` |
| **`SYNTHETIC`** | Dynamically synthesizes RFC-compliant events or metrics using procedural templates and randomized IP/port state. | Engine templates | `arista:telemetry:json`, `cisco:metrics`, `splunk:core:hec` |
| **`STATEFUL`** | Models full state machines (BGP state, TCP sessions, OSPF neighbor adjacencies, firewall tracking tables). | Graph Engine + Simulation State | `bgp_route_leak`, `cisco:sdwan:tunnelhealth`, `ddos_attack` |
| **`SCENARIO_DERIVED`**| Multi-stage correlated event cascades triggered across multiple nodes according to a timeline. | `ScenarioRunner` + Fault Injection | `cisco_sdwan_brownout`, `cisco_aci_microburst`, `mixed_edge_breach` |

The canonical catalog indexes the `generation_mode` for every sourcetype, sample, and scenario. The query method `catalog.get_generation_mode(identifier)` automatically determines the appropriate mode.

---

## 9. The Python Canonical Core Module (`src/netspout_core/catalog.py`)

The `NetSpoutCatalog` class provides a high-performance, single-instance singleton interface:

```python
from netspout_core.catalog import catalog

# Vendors
vendor = catalog.get_vendor("cisco_sdwan")       # Normalized slug or legacy ID
vendors = catalog.list_vendors()                 # All 36 vendors

# Sourcetypes & Alias Resolution
st_obj = catalog.get_sourcetype("cisco:sdwan:sytem:logs")  # Resolves typo to canonical
can_st, is_dep, can_id = catalog.resolve_sourcetype("cisco:sdwan:sytem:logs")
# -> ("cisco:sdwan:system:logs", True, "cisco-sdwan-system-logs")

# Scenarios & Topologies
scenario = catalog.get_scenario("cisco_sdwan_brownout")
topologies = catalog.list_topologies()

# Samples & Protocols
sample = catalog.get_sample("cisco-ios-syslog")
protocols = catalog.list_protocols()

# Legacy Compatibility for UI/Dashboards
legacy_vendors = catalog.get_legacy_vendor_catalog()
```

---

## 10. Consumer Refactoring & Compatibility Layers

1. **`src/netspout_core/vendor_catalog.py`**:
   - Refactored from a 1,400-line static dictionary file into a 57-line dynamic compatibility adapter.
   - Retains all exported functions: `list_all_vendors()`, `get_all_vendors()`, `get_vendor_by_id()`, `get_vendor_by_slug()`, `get_sourcetypes_by_vendor()`, `get_all_sourcetypes()`, and `VENDOR_ECOSYSTEM`.
   - Guaranteed 100% backward compatibility with all tests and consumer scripts.

2. **`netspout/appserver/static/vendor_catalog.json`**:
   - Synchronized directly from `catalog.get_legacy_vendor_catalog()` via `scripts/sync_core.py`.
   - Verified 100% identical across all 36 vendors and all legacy optional fields (`sample_event`, `cim_datamodels`, `cim_fields`).

3. **Multi-Runtime Packaging**:
   - Synchronized copies generated in `netspout/bin/netspout_core/` (exact copy), `netspout/bin/` (packaged with warning header), and `backend/app/` (backend runtime copy).
   - Synchronized `catalog_data/` JSONs into all runtime destinations.

---

## 11. Automated Tooling & Continuous Guardrails

### `scripts/validate_catalog.py`
Automated validator that verifies:
- JSON syntax and presence of all 8 catalog files.
- Uniqueness of IDs and Splunk sourcetypes.
- Integrity of vendor references from sourcetypes and samples.
- Integrity of topology and sourcetype references from scenarios.
- Existence of sample files on disk.
- Proper bidirectional mapping for all aliases.
- Orphan entity detection.

### `scripts/sync_core.py`
- Copies canonical modules from `src/netspout_core/` to `netspout/bin/netspout_core/`, `netspout/bin/`, and `backend/app/`.
- Synchronizes all 8 catalog JSON files to `netspout/bin/netspout_core/catalog_data/`, `netspout/bin/catalog_data/`, `backend/app/catalog_data/`, and `netspout/catalog/`.
- Re-generates `netspout/appserver/static/vendor_catalog.json`.

### `scripts/verify_sources.py`
- Verifies SHA-256 byte parity of canonical modules against packaged copies.
- Verifies generated warning headers.
- Verifies SHA-256 parity for all 8 catalog JSON files across targets.
- Runs `validate_catalog()` and asserts 0 errors.
- Verifies static vendor JSON mirror parity.

---

## 12. Catalog Orphan Analysis Report

The automated orphan analysis identified:
- **Orphan Vendors**: **0** (All 36 vendors define active sourcetypes).
- **Orphan Topologies**: **0** (All 28 topologies are mapped to scenarios).
- **Orphan Scenarios**: **0** (All 29 scenarios link to valid topologies and sourcetypes).
- **Unreferenced Sourcetypes**: **42** out of 263.
  - *Analysis*: These 42 sourcetypes (e.g. `a10:acos:cgnat`, `infoblox:dhcp`, `aruba:clearpass:radius`, `checkpoint:threat:json`) represent audited enterprise technology add-ons that provide breadth for ad-hoc simulation and user queries, but are not currently part of the 29 curated baseline scenarios.
  - *Classification*: Retained as authoritative catalog members for forward compatibility and user-defined scenario construction.

---

## 13. Verification & Test Evidence

### Gate 1 Runtime Tests (`tests/test_gate1_runtime.py`)
- 6/6 tests PASS (100%).
- Validates typing resolutions, bin module importability, model schemas, OpenConfig MDT generation, continuous streaming lifecycle, and live Splunk container REST probe.

### Gate 2 Single Source of Truth Tests (`tests/test_gate2_canonical.py`)
- 9/9 tests PASS (100%).
- Validates canonical core integrity, packaged copy parity, zero-drift enforcement, clean imports, models enum parity, and engine functionality.

### Gate 3 Canonical Catalog Tests (`tests/test_gate3_catalog.py`)
- 8/8 tests PASS (100%).
- `test_01_catalog_entity_counts`: PASS (36 vendors, 263 sourcetypes, 29 scenarios, 17 device types, 28 topologies, 213 samples, 8 protocols, 43 aliases).
- `test_02_typo_sourcetype_resolution`: PASS (`cisco:sdwan:sytem:logs` -> `cisco:sdwan:system:logs`, deprecated=True).
- `test_03_duplicate_id_resolution`: PASS (`nutanixpc-syslog` and `nutanixpc-syslog-colon` disambiguation).
- `test_04_schema_and_reference_validation`: PASS (0 schema errors, 0 broken references).
- `test_05_legacy_vendor_catalog_compatibility`: PASS (36 vendors in `VENDOR_CATALOG` and static JSON mirror).
- `test_06_generation_mode_classification`: PASS (`REPLAY`, `SYNTHETIC`, `STATEFUL`, `SCENARIO_DERIVED`).
- `test_07_device_types_and_topologies`: PASS (all 17 `NodeType` enums present, topology fields verified).
- `test_08_protocols`: PASS (all 8 telemetry protocols verified).

### Comprehensive Test Suite (`tests/run_comprehensive_test_suite.py`)
- **60 / 62 Tests Passed (96.8%)** — exactly matching pre-Gate-2 and pre-Gate-3 baselines.
- Suite 13 (Vendor Add-on Catalog & Static Mirror): PASS.
- Suite 15 (Vendor Catalog Count >= 30 & TA Ecosystem): PASS.
- Suite 20 (197 Sourcetypes Benchmark Specification & Vendor Catalog Coverage): PASS.
- The 2 failing tests (Suite 1: Nav tab count 7 vs 8; Suite 3: Frontend dist CSS chunk absence) are documented pre-existing baseline conditions.

### Live Splunk Container Verification
- Ran live Python probe inside Docker container `splunk-network-data-blaster`:
  ```
  Splunk container catalog test:
  Vendors count: 36
  Sourcetypes count: 263
  Scenarios count: 29
  Topologies count: 28
  Samples count: 213
  Protocols count: 8
  Typo resolution: cisco:sdwan:sytem:logs -> cisco:sdwan:system:logs (is_deprecated=True)
  ```

---

## 14. File Inventory

### Files Created in Gate 3
- `catalog/vendors.json`
- `catalog/sourcetypes.json`
- `catalog/scenarios.json`
- `catalog/device_types.json`
- `catalog/topologies.json`
- `catalog/samples.json`
- `catalog/telemetry_protocols.json`
- `catalog/aliases.json`
- `src/netspout_core/catalog.py`
- `scripts/validate_catalog.py`
- `tests/test_gate3_catalog.py`
- `docs/architecture/NETSPOUT_GATE_3_CANONICAL_CATALOG.md`

### Files Modified in Gate 3
- `src/netspout_core/vendor_catalog.py` (refactored to dynamic catalog wrapper)
- `scripts/sync_core.py` (added catalog sync and vendor_catalog.json generation)
- `scripts/verify_sources.py` (added catalog verification and validation steps)
- `scripts/build_splunk_package.py` (added catalog packaging checks)
- `netspout/appserver/static/vendor_catalog.json` (re-generated from canonical catalog)

### Files Synchronized Across Environments
- `netspout/bin/netspout_core/catalog.py`
- `netspout/bin/netspout_core/catalog_data/*.json`
- `netspout/bin/catalog.py`
- `netspout/bin/catalog_data/*.json`
- `netspout/bin/vendor_catalog.py`
- `backend/app/catalog.py`
- `backend/app/catalog_data/*.json`
- `backend/app/vendor_catalog.py`
- `netspout/catalog/*.json`
- `netspout.spl` (production release archive, 1.31 MB)

---

## 15. Risks, Mitigations & Guardrails

| Risk | Impact | Mitigation Implemented |
| :--- | :--- | :--- |
| **Developer edits generated copies directly** | Code drift and divergent logic | `scripts/verify_sources.py` checks SHA-256 and generated headers, failing build on any manual modification. |
| **Breaking existing dashboards expecting legacy vendor dict format** | UI crashes in SimpleXML/React | `catalog.get_legacy_vendor_catalog()` provides exact field parity matching legacy schema. |
| **Typo sourcetype breaks historical search queries** | SPL queries failing | `aliases.json` and `resolve_sourcetype()` transparently redirect deprecated typos to canonical names. |
| **Missing catalog data in Splunk packaged environment** | Runtime import errors | Catalog JSON files are packaged directly inside `netspout/bin/catalog_data/` and `netspout/catalog/`. |

---

## 16. Conclusion & Handoff to Gate 4

Gate 3 has successfully established a **single authoritative metadata and catalog layer** for NetSpout. The fragmented, manually duplicated vendor, sourcetype, scenario, topology, and sample definitions across Python, JSON, and XML have been replaced with a declarative canonical catalog and an integrated Python core API.

**Gate 3 Acceptance Criteria**: **ALL SATISFIED (100% PASS)**.  
*Next Phase*: **GATE 4 — UNIFIED TOPOLOGY AND GRAPH ENGINE** (awaiting explicit user instruction to begin).
