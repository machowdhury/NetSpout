# NETSPOUT GATE 13C — EXTERNAL gNMI COLLECTOR VERIFICATION & ACCEPTANCE REPORT

**Document ID:** `NETSPOUT-ACCEPT-G13C-VERIFICATION`  
**Gate:** Gate 13C (External gNMI Collector & Telemetry Pipeline Integration)  
**Baseline Commit:** `495d324191307fb7a662f3dc9c97e6ecd9baba6e`  
**External Collector:** `/opt/homebrew/bin/gnmic` (`v0.49.0`, commit `Homebrew`, `https://github.com/openconfig/gnmic`)  
**Highest Evidence Stage Verified:** `NORMALIZED` (`SPLUNK_DISPATCHED = False`, `SPLUNK_OBSERVED = False`)  

---

## 1. Executive Verification Summary

Gate 13C independently verifies that a real external gNMI collector (`/opt/homebrew/bin/gnmic` `v0.49.0`) connects to NetSpout's Gate 13B `NativeGnmiServer` over `TCP -> HTTP/2 -> gRPC -> gNMI Protobuf (v0.10.0)`, consumes `ONCE`, `POLL`, `STREAM / SAMPLE`, and `STREAM / ON_CHANGE` subscriptions across all 4 supported vendor profiles (`CISCO_IOS_XR`, `CISCO_IOS_XE`, `ARISTA_EOS`, `JUNIPER_JUNOS`), and normalizes both OpenConfig and vendor-native telemetry into `NormalizedGnmiTelemetryRecord` envelopes with 100% datatype preservation, keyed path preservation, out-of-band correlation enrichment, and cross-transport state coherence.

| Verification Dimension | Status | Evidence Artifact |
| :--- | :--- | :--- |
| **1. Telemetry Provenance (`34/34` sensors, `0` fabricated paths)** | `PASS` | [`multi_vendor_evidence.json`](file:///Users/mahamudc/Documents/NetSpout/docs/acceptance/evidence/gate13c/multi_vendor_evidence.json) |
| **2. External Collector (`gnmic v0.49.0`) `ONCE` Mode** | `PASS` | [`subscription_evidence.json`](file:///Users/mahamudc/Documents/NetSpout/docs/acceptance/evidence/gate13c/subscription_evidence.json) |
| **3. External Collector (`gnmic v0.49.0`) `POLL` Mode Across Phases** | `PASS` | [`subscription_evidence.json`](file:///Users/mahamudc/Documents/NetSpout/docs/acceptance/evidence/gate13c/subscription_evidence.json) |
| **4. External Collector (`gnmic v0.49.0`) `STREAM / SAMPLE` Mode** | `PASS` | [`subscription_evidence.json`](file:///Users/mahamudc/Documents/NetSpout/docs/acceptance/evidence/gate13c/subscription_evidence.json) |
| **5. External Collector (`gnmic v0.49.0`) `STREAM / ON_CHANGE` Mode** | `PASS` | [`subscription_evidence.json`](file:///Users/mahamudc/Documents/NetSpout/docs/acceptance/evidence/gate13c/subscription_evidence.json) |
| **6. Multi-Vendor OpenConfig + Vendor-Native Collection (4 Vendors)** | `PASS` | [`multi_vendor_evidence.json`](file:///Users/mahamudc/Documents/NetSpout/docs/acceptance/evidence/gate13c/multi_vendor_evidence.json) |
| **7. Native Datatype (`int`, `float`, `bool`, `str`, `object`) & Path Preservation** | `PASS` | [`normalized_output.json`](file:///Users/mahamudc/Documents/NetSpout/docs/acceptance/evidence/gate13c/normalized_output.json) |
| **8. Wire Payload Purity & Out-of-Band Correlation Enrichment** | `PASS` | [`raw_collector_output.json`](file:///Users/mahamudc/Documents/NetSpout/docs/acceptance/evidence/gate13c/raw_collector_output.json) |
| **9. Cross-Transport Coherence (gNMI $\leftrightarrow$ SNMP $\leftrightarrow$ Syslog $\leftrightarrow$ NetFlow)** | `PASS` | [`cross_transport_coherence_evidence.json`](file:///Users/mahamudc/Documents/NetSpout/docs/acceptance/evidence/gate13c/cross_transport_coherence_evidence.json) |
| **10. Controlled Failures (`A`–`H`) & Honest Stage Accounting** | `PASS` | [`failure_evidence.json`](file:///Users/mahamudc/Documents/NetSpout/docs/acceptance/evidence/gate13c/failure_evidence.json) |
| **11. Collector Reconnection & Deterministic Deduplication Accounting** | `PASS` | [`reconnect_evidence.json`](file:///Users/mahamudc/Documents/NetSpout/docs/acceptance/evidence/gate13c/reconnect_evidence.json) |
| **12. Performance & 4 Simultaneous Multi-Vendor Subscriptions** | `PASS` | [`performance_summary.json`](file:///Users/mahamudc/Documents/NetSpout/docs/acceptance/evidence/gate13c/performance_summary.json) |

---

## 2. Multi-Vendor Coherence & Heterogeneous Telemetry Proof

In `DEGRADE` phase, the same underlying operational condition (`queue.dropped_pkts = 4820`, `queue.max_queue_len = 14850000`, `oper-status = DOWN`, `bgp.session_state = IDLE`) is observed by `gnmic` through both OpenConfig and each vendor's legitimate native schema:

| Vendor Profile | Target Device | Native `gnmi_origin` | Native `gnmi_path` | Observed Value (`int` / `str`) |
| :--- | :--- | :--- | :--- | :--- |
| **`CISCO_IOS_XR`** | `node-cisco8k` | `Cisco-IOS-XR-qos-ma-oper` | `/qos/interface-table/interface[interface-name=HundredGigE0/0/0/0]/output/service-policy-names/service-policy-instance/statistics/tail-drop-packets` | `4820` (`int`) |
| **`CISCO_IOS_XE`** | `node-cat-leaf` | `Cisco-IOS-XE-interfaces-oper` | `/interfaces/interface[name=FortyGigE1/0/1]/statistics/oper-status` | `"if-oper-state-no-pass"` (`str`) |
| **`ARISTA_EOS`** | `node-arista-spine` | `eos_native` | `/Sysdb/hardware/counter/Lanz[intf=Ethernet1/1]/queueStatus/outDiscards` | `4820` (`int`) |
| **`JUNIPER_JUNOS`** | `node-juniper-ptx` | `junos` | `/junos/system/linecard/qmon[interface=et-0/0/0]/tail-drop-packets` | `4820` (`int`) |

---

## 3. Cross-Transport State Coherence (`cisco-asr9k-pe1`)

Verified via [`verify_cross_transport_coherence_via_collector()`](file:///Users/mahamudc/Documents/NetSpout/src/netspout_core/gnmi/collector_pipeline.py) across all four phases:

| Phase | gNMI `oper-status` | SNMP `ifOperStatus.1` | Syslog Mnemonic | gNMI BGP `session-state` | SNMP `bgpPeerState` | gNMI AFT `next-hop` | NetFlow `active_next_hop` |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`BASELINE`** | `"UP"` | `1` (`up`) | `LINK-3-UPDOWN` (up) | `"ESTABLISHED"` | `6` (`established`) | `"10.255.0.2"` | `"10.255.0.2"` |
| **`DEGRADE`** | `"DOWN"` | `2` (`down`) | `LINK-3-UPDOWN` (down) | `"IDLE"` | `1` (`idle`) | `"10.255.0.3"` | `"10.255.0.3"` |
| **`FAILOVER`** | `"DOWN"` | `2` (`down`) | `LINK-3-UPDOWN` (down) | `"IDLE"` | `1` (`idle`) | `"10.255.0.3"` | `"10.255.0.3"` |
| **`RECOVERY`** | `"UP"` | `1` (`up`) | `LINK-3-UPDOWN` (up) | `"ESTABLISHED"` | `6` (`established`) | `"10.255.0.2"` | `"10.255.0.2"` |

---

## 4. Controlled Failure Matrix (`A`–`H`)

| Failure Case | Condition | Observed Result | `COLLECTOR_RECEIVED` | `NORMALIZED` |
| :--- | :--- | :--- | :--- | :--- |
| **A. Collector Unavailable** | Server active; collector binary missing | `FileNotFoundError` (`rc=127`); `SERVER_PUBLISHED=True`, no false delivery claim | `False` (`0`) | `False` (`0`) |
| **B. gNMI Server Unavailable** | Collector dials closed port | `connection refused` (`rc=1`); zero fabricated records | `False` (`0`) | `False` (`0`) |
| **C. Authentication Failure** | Wrong password against `require_metadata_auth=True` | `StatusCode.UNAUTHENTICATED` (`rc=1`) | `False` (`0`) | `False` (`0`) |
| **D. TLS Validation Failure** | Untrusted server cert without `--tls-ca` / `--skip-verify` | `x509: certificate signed by unknown authority` (`rc=1`) | `False` (`0`) | `False` (`0`) |
| **E. Unsupported Path / Foreign Origin** | `/openconfig-fabricated/nonexistent/state` or `eos_native` on XR | `StatusCode.NOT_FOUND` (`rc=1`); zero synthesized data | `False` (`0`) | `False` (`0`) |
| **F. Subscription Interruption** | Server stopped and restarted during `STREAM / ON_CHANGE` | `gnmic --retry 200ms` reconnects in `576.2 ms` and receives `FAILOVER` update | `True` (post-reconnect) | `True` |
| **G. Invalid/Unsupported Encoding** | `gnmic -e ascii` | `StatusCode.UNIMPLEMENTED` (`rc=1`) | `False` (`0`) | `False` (`0`) |
| **H. Excessive Sampling Request** | `sample_interval=100ms` (`< 500ms` floor) | `StatusCode.INVALID_ARGUMENT` (`SAMPLE_INTERVAL_BELOW_FLOOR`) | `False` (`0`) | `False` (`0`) |

---

## 5. Reconnect, Duplication & Performance Metrics

- **Reconnect & Duplication Accounting:**
  - Reconnect time after server restart: `576.2 ms`
  - Unfiltered reconnect stream: `original_count = 3`, `duplicate_count = 1`, `suppressed_count = 0`, `retained_count = 3`
  - Deduplicated reconnect stream (`suppress_duplicates=True`): `original_count = 3`, `duplicate_count = 1`, `suppressed_count = 1`, `retained_count = 2`
  - Deduplication key formula: `sha256(device_id|gnmi_origin|gnmi_path|timestamp|canonical_value_json)[:24]` (sample key: `bfcccc17f330c089376201f7`)
- **Performance Benchmark (4 Simultaneous Multi-Vendor `gnmic` Subscriptions):**
  - Raw gNMI updates/sec: `107.99 updates/sec` (`168` updates in `1.556s`)
  - Collector normalized records/sec (end-to-end): `1,131.99 records/sec` (`1,761` records in `1.556s`)
  - Pure normalizer throughput: `80,782.29 records/sec`
  - Normalization latency `p50`: `0.1042 ms`
  - Normalization latency `p95`: `0.2035 ms`
  - Process + Collector CPU utilization: `20.54%`
  - Peak RSS Memory: `53.05 MiB`
