# NETSPOUT GATE 13C — EXTERNAL gNMI COLLECTOR & TELEMETRY PIPELINE ARCHITECTURE

**Document ID:** `NETSPOUT-ARCH-G13C-COLLECTOR`  
**Gate:** Gate 13C (External gNMI Collector & Telemetry Pipeline Integration)  
**Baseline Commit:** `495d324191307fb7a662f3dc9c97e6ecd9baba6e`  
**Status:** IMPLEMENTED & VERIFIED (Stops at `NORMALIZED`; `SPLUNK_OBSERVED = False`)  

---

## 1. Architectural Overview & Pipeline Topology

Gate 13C implements and independently verifies the **collector and normalization tier** of NetSpout's native gNMI (`0.10.0`) / OpenConfig streaming telemetry architecture without modifying or weakening the Gate 13B native gNMI server:

```text
NetSpout ScenarioStateStore (Shared Deterministic State)
        │
        ▼
NativeGnmiServer (Gate 13B)
TCP → HTTP/2 → gRPC → gNMI Protobuf (v0.10.0)
        │
        ▼
EXTERNAL gNMI COLLECTOR (/opt/homebrew/bin/gnmic v0.49.0)
        │
        ├── OpenConfig normalization (openconfig-*)
        ├── Vendor-native normalization (Cisco-IOS-XR-*, Cisco-IOS-XE-*, eos_native, junos)
        ├── Nanosecond & ISO-8601 timestamps
        ├── Source address & canonical device identity resolution
        ├── Full keyed gNMI path preservation (/interfaces/interface[name=...]/...)
        ├── Native datatype preservation (int, float, bool, str, object)
        ├── Out-of-band NetSpout scenario correlation enrichment
        └── Deterministic reconnect duplicate accounting (deduplication_key)
        │
        ▼
Collector Output (NormalizedGnmiTelemetryRecord)
        │
        ├── Structured container events (value_type = "object")
        └── Leaf telemetry metrics & state records (value_type = "int" | "float" | "bool" | "str")
        │
        ▼
Future Gate 13D (Out of Scope for Gate 13C)
Splunk HEC / Collector Ingestion + SPL Search + Validation
```

---

## 2. Non-Negotiable Telemetry Provenance Registry

All 34 canonical sensors in [`src/netspout_core/gnmi/sensor_registry.py`](file:///Users/mahamudc/Documents/NetSpout/src/netspout_core/gnmi/sensor_registry.py) are audited by [`audit_sensor_provenance_registry()`](file:///Users/mahamudc/Documents/NetSpout/src/netspout_core/gnmi/collector_pipeline.py) against `SENSOR_PROVENANCE_CATALOG`:
- **Total Canonical Sensors:** `34` (`15` OpenConfig + `19` Vendor-Native across `CISCO_IOS_XR`, `CISCO_IOS_XE`, `ARISTA_EOS`, and `JUNIPER_JUNOS`)
- **Provenance Verified Count:** `34 / 34` (`100%`)
- **Fabricated Vendor Paths Found:** `0`

### Honest Multi-Vendor Telemetry Coverage Differences
NetSpout does not force artificial uniformity across vendor NOS platforms where underlying documentation differs:
1. **OpenConfig EVPN/VXLAN (`oc_evpn_vxlan`):** Supported on EVPN-capable data-center spine/leaf targets (`node-arista-spine` / `ARISTA_EOS`), and explicitly classified as `NOT_SUPPORTED` (`StatusCode.NOT_FOUND`) on pure L3 core/edge targets (`node-cisco8k`, `node-juniper-ptx`, `node-cat-leaf`).
2. **Cisco IOS XR (`CISCO_IOS_XR`):** Exposes `Cisco-IOS-XR-infra-statsd-oper`, `Cisco-IOS-XR-pfi-im-cmd-oper`, `Cisco-IOS-XR-ipv4-bgp-oper`, `Cisco-IOS-XR-qos-ma-oper`, `Cisco-IOS-XR-controller-optics-oper` (where optical power is represented in `0.01 dBm` integer units per XR YANG schema), and `Cisco-IOS-XR-wdsysmon-fd-oper`.
3. **Cisco IOS XE (`CISCO_IOS_XE`):** Exposes `Cisco-IOS-XE-interfaces-oper`, `Cisco-IOS-XE-bgp-oper`, `Cisco-IOS-XE-environment-oper`, `Cisco-IOS-XE-transceiver-oper`, and `Cisco-IOS-XE-process-cpu-oper`. Never emits `Cisco-IOS-XR-*` modules.
4. **Arista EOS (`ARISTA_EOS`):** Exposes `origin="eos_native"` paths for Sysdb Ethernet counters (`/Sysdb/interface/counter/eth/slice/phy/[intf=*]/currentStatistics`), LANZ microburst queue status (`/Sysdb/hardware/counter/Lanz/[intf=*]/queueStatus`), Smash BGP peer status (`/Smash/routing/bgp/...`), and Smash VXLAN VTEP status (`/Smash/vxlan/vtepStatus`), while using standard OpenConfig models for CPU, memory, and platform environment.
5. **Juniper Junos (`JUNIPER_JUNOS`):** Exposes `origin="junos"` Junos Telemetry Interface (JTI) paths for linecard interface statistics (`/junos/system/linecard/interface[name=*]/statistics`), linecard optics (`/junos/system/linecard/optics[name=*]`), linecard queue monitoring (`/junos/system/linecard/qmon[interface=*]`), and BGP neighbor telemetry (`/junos/services/bgp/neighbors/neighbor[neighbor-address=*]`), while using OpenConfig for system CPU/memory.

---

## 3. Canonical Telemetry Envelope & Datatype/Path Preservation

[`NormalizedGnmiTelemetryRecord`](file:///Users/mahamudc/Documents/NetSpout/src/netspout_core/gnmi/collector_pipeline.py) retains all original gNMI semantics:
- **Identity & Timing:** `timestamp` (int64 ns), `timestamp_iso` (ISO-8601 UTC), `vendor`, `platform`, `device_id`, `source_address`
- **gNMI Protocol Metadata:** `gnmi_origin`, `gnmi_target`, `gnmi_path` (full path with list keys preserved, e.g., `/interfaces/interface[name=HundredGigE0/0/0/0]/state/counters/in-octets`), `gnmi_subscription_mode` (`ONCE`, `POLL`, `STREAM/SAMPLE`, `STREAM/ON_CHANGE`), `gnmi_encoding` (`JSON_IETF`, `JSON`, `PROTO`)
- **Schema & Provenance Metadata:** `yang_model`, `telemetry_model` (`OPENCONFIG` | `VENDOR_NATIVE`), `telemetry_category`, `sensor_id`, `fidelity_classification` (`VERIFIED` | `MODELED`), `transport_classification` (`NATIVE_GNMI_GRPC`), `provenance_reference`
- **Typed Value Preservation:**
  - `int`: 64-bit counters (RFC 7951 stringified `uint64`/`int64` values such as `"98504200000"` are deterministically restored to native Python `int` `98504200000`)
  - `float`: optical DOM power (`-6.2` dBm), laser bias (`38.5` mA), temperature (`41.2` °C), pre-FEC BER (`1.0e-9`)
  - `bool`: LACP `aggregatable`, `collecting`, `distributing`, interface `enabled`
  - `str`: enumerations and identifiers (`"UP"`, `"DOWN"`, `"ESTABLISHED"`, `"IDLE"`)
  - `object`: structured container dictionaries

---

## 4. Out-of-Band Correlation & Native Wire Payload Purity

NetSpout enforces strict separation between native wire telemetry and scenario correlation:
1. **Wire Payload Purity:** On the gRPC wire (`gnmi.Notification`), zero `netspout_*` fields exist. [`verify_wire_payload_purity()`](file:///Users/mahamudc/Documents/NetSpout/src/netspout_core/gnmi/collector_pipeline.py) inspects every raw `gnmic` notification prior to normalization and verifies zero occurrences of `netspout_run_id`, `netspout_scenario_id`, `netspout_phase`, `netspout_device_id`, or `netspout_event_id`.
2. **Collector Boundary Enrichment:** `GnmiTelemetryNormalizer` attaches `netspout_run_id`, `netspout_scenario_id`, `netspout_phase`, `netspout_device_id`, and deterministic `netspout_event_id` exclusively on `NormalizedGnmiTelemetryRecord`.

---

## 5. Scenario Selection Rationale

Without creating artificial scenarios, Gate 13C exercises four existing canonical scenarios:
1. **`openconfig_mdt_streaming` (`topology_id: openconfig_core`):** Primary 4-vendor topology (`node-cisco8k`, `node-cat-leaf`, `node-arista-spine`, `node-juniper-ptx`) exercising multi-vendor interface state/counters, BGP, system CPU/memory, QoS queues, platform environment, optics, and EVPN across `BASELINE -> DEGRADE -> FAILOVER -> RECOVERY`.
2. **`service_provider_cisco` (`cisco-asr9k-pe1`):** Primary cross-transport coherence scenario linking Gate 12F Native SNMPv2c (`IF-MIB`, `BGP4-MIB`), Syslog (`LINK-3-UPDOWN`, `BGP-5-ADJCHANGE`), NetFlow/IPFIX, and Native gNMI.
3. **`cisco_aci_microburst`:** Exercises high-resolution QoS queue occupancy (`14,850,000` bytes) and packet tail-drop (`4,820` packets) telemetry during `DEGRADE`.
4. **`mixed_backbone_optical`:** Exercises optical transceiver DOM degradation (`rx-power` `-6.2 dBm -> -24.8 dBm`, `pre-fec-ber` `1.0e-9 -> 1.4e-3`, `osnr` `28.5 dB -> 11.2 dB`) and recovery.

---

## 6. Reconnect & Duplication Semantics

When an external collector (`gnmic --retry 200ms subscribe --mode stream`) reconnects after a gNMI server restart with `updates_only=false`, the gNMI specification mandates that the target send a full initial synchronization snapshot followed by `sync_response=true`.
- If `ScenarioStateStore` is at the same `(phase, tick)` across the reconnect boundary, the re-synchronized update produces a duplicate observation with an identical `(device_id, gnmi_origin, gnmi_path, timestamp, canonical_value_json)` tuple.
- `GnmiTelemetryNormalizer` computes `deduplication_key = sha256(device_id|gnmi_origin|gnmi_path|timestamp|canonical_value_json)[:24]` on every record and reports `original_count`, `duplicate_count`, and `suppressed_count` (when `suppress_duplicates=True`).
