# NetSpout Gate 13D — Native gNMI/OpenConfig → External Collector → Splunk End-to-End Architecture

## 1. Executive Summary & Purpose

NetSpout Gate 13D completes the end-to-end production-grade telemetry pipeline for native gNMI and OpenConfig:

```text
┌─────────────────────────┐
│   ScenarioStateStore    │  Modeled Network State Transitions (BASELINE -> DEGRADE -> FAILOVER -> RECOVERY)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│    Native gNMI Server   │  gNMI 0.8.0 / Protobuf over gRPC / HTTP/2 / TCP (100% Standards-Pure Wire Payloads)
└────────────┬────────────┘
             │  (TCP loopback: 127.0.0.1, Ephemeral Port)
             ▼
┌─────────────────────────┐
│ External gnmic v0.49.0  │  Independent Production Collector Binary (/opt/homebrew/bin/gnmic)
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Normalization Boundary │  GnmiTelemetryNormalizer + GnmiSplunkAdapter (Out-of-band NetSpout Correlation)
└────────────┬────────────┘
             │
             ├─── State Leaves / Events ───────────────┐
             │                                         │
             ▼                                         ▼
┌─────────────────────────┐               ┌─────────────────────────┐
│   Splunk Event Store    │               │   Splunk Metric Store   │
│   Index: idx_network_ops│               │   Index: cisco_mdt_metrics│
│   netspout:gnmi:event   │               │   netspout:gnmi:metric  │
└────────────┬────────────┘               └────────────┬────────────┘
             │                                         │
             ▼                                         ▼
┌─────────────────────────┐               ┌─────────────────────────┐
│  SPL Search Inspection  │               │    | mstats Analysis    │
└────────────┬────────────┘               └────────────┬────────────┘
             │                                         │
             └─────────────────┬───────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────┐
│       ValidationEngine & 7-Stage Evidence Ledger        │
│   GENERATED -> SERVER_PUBLISHED -> COLLECTOR_RECEIVED   │
│   -> NORMALIZED -> SPLUNK_DISPATCHED -> SPLUNK_OBSERVED │
│   -> VALIDATED                                          │
└─────────────────────────────────────────────────────────┘
```

---

## 2. Telemetry Provenance & Anti-Fabrication Principles

NetSpout strictly enforces the rule: **NO FABRICATED VENDOR TELEMETRY**.
- Network conditions and state transitions are simulated.
- Telemetry values and metrics are modeled.
- Vendor telemetry contracts, paths, field names, and datatypes must **never** be invented.

### Provenance Hierarchy
1. **Tier 1:** Vendor Official Documentation
2. **Tier 2:** Vendor-Maintained YANG / Model Repositories (e.g., `Cisco-IOS-XR-*`, `Cisco-IOS-XE-*`, `junos-*`, `eos_native`)
3. **Tier 3:** OpenConfig Specifications and Models (`openconfig-interfaces`, `openconfig-bgp`, `openconfig-platform`, `openconfig-qos`, `openconfig-system`)
4. **Tier 4:** IETF RFC Specifications (e.g., RFC 7951 JSON_IETF encoding)
5. **Tier 5:** Vendor-Maintained Public Repositories
6. **Tier 6:** Splunk-Supported / Vendor-Supported Splunkbase Applications

### Unsupported Telemetry Handling
Proprietary protocols or proprietary REST trees that do not have legitimate gNMI/YANG representations are explicitly classified as `UNSUPPORTED_TELEMETRY`. For example, Cisco ACI DME Managed Objects (`dbgacTenant`, `eqptIngrTotal5min`, `qosmIngrPkts5min`) utilize proprietary APIC MIT tree paths rather than OpenConfig or YANG-modeled gNMI paths; NetSpout refuses to fabricate synthetic gNMI paths for APIC DME objects and instead issues an honest declaration while monitoring QoS via standard OpenConfig QoS and Cisco IOS XR Native QoS operational models.

---

## 3. Strict 7-Stage Evidence Progression

Gate 13D guarantees that each telemetry observation is tracked through seven distinct, non-conflated lifecycle stages:

| Stage | Name | Verification Method | Gate 13D Meaning |
|---|---|---|---|
| 1 | `GENERATED` | `ScenarioStateStore.set_phase()` | Synthetic network condition mutated in device state store. |
| 2 | `SERVER_PUBLISHED` | `NativeGnmiServer` gRPC stream | Notification emitted across HTTP/2 wire to external collector. |
| 3 | `COLLECTOR_RECEIVED` | `gnmic` subprocess output | External collector received and decoded raw gNMI update. |
| 4 | `NORMALIZED` | `GnmiTelemetryNormalizer` | Path keys extracted, RFC 7951 values typed, correlation attached. |
| 5 | `SPLUNK_DISPATCHED` | Splunk HEC HTTP 200 response | Event and metric batches accepted by Splunk HEC. |
| 6 | `SPLUNK_OBSERVED` | Fresh REST `search` / `\| mstats` | Record queried and retrieved from live Splunk index. |
| 7 | `VALIDATED` | `ValidationEngine` evaluation | Contract assertions passed against Splunk-observed rows. |

**Crucial Separation:** NetSpout never conflates `SPLUNK_DISPATCHED` (HEC HTTP 200 acknowledgment) with `SPLUNK_OBSERVED` (actual retrieval from a live Splunk search). The pipeline verifies that indexed data is queryable and discoverable.

---

## 4. Dual-Store Splunk Data Model

To preserve the architectural integrity of Splunk event indexing and metric indexing:

### A. Event / State Telemetry Store
- **Destination Index:** `idx_network_ops`
- **Sourcetype:** `netspout:gnmi:event`
- **Data Types Routed:** Operational status (`UP`, `DOWN`), administrative status, BGP session states (`ESTABLISHED`, `IDLE`), structured JSON containers (`object`), string attributes, and booleans.
- **HEC Envelope:** Sent with `"event": <event_dict>` without duplicating keys into `"fields"` to guarantee single-value field extraction in Splunk search (`count=1` per event in `\| stats`).

### B. Metric / Time-Series Telemetry Store
- **Destination Index:** `cisco_mdt_metrics`
- **Sourcetype:** `netspout:gnmi:metric`
- **Data Types Routed:** Numeric sampled telemetry (`int`, `float`), interface octet/packet counters, error counters, QoS queue depth bytes, drop packet counters, optical power (dBm), CPU utilization (%), and memory utilization.
- **Metric Naming Schema:** `gnmi.<telemetry_category>.<leaf_name>` (e.g., `gnmi.qos.queue_current_size_bytes`, `gnmi.interface.in_octets`, `gnmi.optics.laser_rx_optical_power_dbm`).
- **HEC Envelope:** Formatted with `"event": "metric"`, `"fields": {"metric_name:<name>": <float_value>, "_value": <float_value>, ...dimensions}`.
- **Splunk Query Semantics:** Queryable via `\| mstats` using `WHERE index=cisco_mdt_metrics metric_name=* ...`.

---

## 5. Wire Purity & Out-of-Band Correlation

In accordance with strict standards-compliance:
- **Wire Purity:** The native gNMI server wire stream contains **zero** proprietary NetSpout fields (`netspout_run_id`, `netspout_phase`, etc.). Wire payload purity is verified via cryptographic check across all raw `gnmic` collector notifications.
- **Correlation Attachment:** Correlation attributes are injected exclusively at the external collector normalization boundary (`GnmiSplunkAdapter`):
  - `netspout_run_id`
  - `netspout_scenario_id`
  - `netspout_phase`
  - `netspout_device_id`
  - `netspout_event_id`
  - `fault_correlation_id`
- **Path Richness:** Full keyed gNMI paths (e.g., `/interfaces/interface[name=HundredGigE0/0/0/0]/state/oper-status`) are fully preserved in normalized and indexed records, allowing engineers to trace the precise YANG model, origin, and key hierarchy.

---

## 6. Supported Vendor Profiles

Gate 13D validates end-to-end telemetry across all four canonical vendor profiles:

| Vendor | OS / Platform | Origin | Sample Native Sensor Paths |
|---|---|---|---|
| **Cisco IOS XR** | `cisco-asr9k-pe1`, `node-cisco8k` | `openconfig`, `Cisco-IOS-XR-*` | `Cisco-IOS-XR-infra-statsd-oper`, `Cisco-IOS-XR-pfi-im-cmd-oper`, `Cisco-IOS-XR-ipv4-bgp-oper`, `Cisco-IOS-XR-qos-ma-oper`, `Cisco-IOS-XR-controller-optics-oper` |
| **Cisco IOS XE** | `node-cat-leaf` | `openconfig`, `Cisco-IOS-XE-*` | `Cisco-IOS-XE-interfaces-oper`, `Cisco-IOS-XE-bgp-oper`, `Cisco-IOS-XE-process-cpu-oper`, `Cisco-IOS-XE-environment-oper` |
| **Arista EOS** | `node-arista-spine` | `openconfig`, `eos_native` | `eos_native:/Sysdb/interface/counter/...`, `eos_native:/Sysdb/hardware/counter/Lanz/...`, `eos_native:/Smash/routing/bgp/...` |
| **Juniper Junos** | `node-juniper-ptx` | `openconfig`, `junos` | `junos:/junos/system/linecard/interface/...`, `junos:/junos/system/linecard/optics/...`, `junos:/junos/services/bgp/...` |

---

## 7. Cross-Transport Coherence Model

NetSpout demonstrates the multi-telemetry synthesis capability of modern network operations: a single network anomaly emits coherent telemetry across multiple transports simultaneously.

During the four scenario phases (`BASELINE` → `DEGRADE` → `FAILOVER` → `RECOVERY`), NetSpout emits and correlates:
1. **gNMI / OpenConfig:** Operational status transitions and sampled queue/counter telemetry.
2. **SNMPv2c Traps & Polling:** `IF-MIB::linkDown` / `linkUp`, `BGP4-MIB::bgpBackwardTransition`, and `ifOperStatus` polling.
3. **Cisco Syslog:** `%LINK-3-UPDOWN`, `%LINEPROTO-5-UPDOWN`, and `%ROUTING-BGP-5-ADJCHANGE`.
4. **NetFlow / IPFIX:** Flow records showing traffic path redirection and bandwidth degradation.

Unified investigation query `q10_cross_source_correlation_spl` aggregates these distinct transports by `netspout_phase` and `netspout_device_id` into a coherent operational incident narrative.
