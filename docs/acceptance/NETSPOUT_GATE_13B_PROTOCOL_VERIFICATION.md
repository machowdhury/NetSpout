# NETSPOUT GATE 13B — PROTOCOL VERIFICATION & ACCEPTANCE REPORT

| Field | Value |
|---|---|
| **Document ID** | `NETSPOUT-ACCEPTANCE-GATE-13B` |
| **Gate** | Gate 13B — Native gNMI Server + OpenConfig Core Engine Protocol Verification |
| **Starting Commit** | `4bb547eea4094093fd6755943588a7dfcb90ff7a` |
| **Target Endpoint** | `127.0.0.1:57400` (`TCP -> HTTP/2 -> gRPC -> gNMI Protobuf`) |
| **External Clients Verified** | `gnmic v0.49.0` (`/opt/homebrew/bin/gnmic`), `pygnmi v0.8.15` (`pygnmi.client.gNMIclient`) |
| **Golden Scenario Verified** | `openconfig_mdt_streaming` (`topology_id: openconfig_core`) + `service_provider_cisco` coherence |
| **Gate 13B Status** | **COMPLETE & CERTIFIED** |

---

## 1. Evidence Stage Matrix (Gate 13B Scope Boundary)

| Evidence Stage | Status | Evidence Artifact |
|---|---|---|
| `SCENARIO_STATE_GENERATED` | **VERIFIED** | [`cross_transport_coherence_proof.json`](file:///Users/mahamudc/Documents/NetSpout/docs/acceptance/evidence/gate13b/cross_transport_coherence_proof.json) |
| `GNMI_SERVER_LISTENING` | **VERIFIED** (`127.0.0.1:57400`) | [`gate13b_verification_manifest.json`](file:///Users/mahamudc/Documents/NetSpout/docs/acceptance/evidence/gate13b/gate13b_verification_manifest.json) |
| `GNMI_CAPABILITIES_VERIFIED` | **VERIFIED** (All 4 vendors) | [`capabilities_cisco_ios_xr.json`](file:///Users/mahamudc/Documents/NetSpout/docs/acceptance/evidence/gate13b/capabilities_cisco_ios_xr.json), [`capabilities_cisco_ios_xe.json`](file:///Users/mahamudc/Documents/NetSpout/docs/acceptance/evidence/gate13b/capabilities_cisco_ios_xe.json), [`capabilities_arista_eos.json`](file:///Users/mahamudc/Documents/NetSpout/docs/acceptance/evidence/gate13b/capabilities_arista_eos.json), [`capabilities_juniper_junos.json`](file:///Users/mahamudc/Documents/NetSpout/docs/acceptance/evidence/gate13b/capabilities_juniper_junos.json) |
| `GNMI_GET_VERIFIED` | **VERIFIED** (`ALL`, `CONFIG`, `STATE`, `OPERATIONAL`) | [`get_openconfig_all_vendors.json`](file:///Users/mahamudc/Documents/NetSpout/docs/acceptance/evidence/gate13b/get_openconfig_all_vendors.json), [`get_vendor_native_all_vendors.json`](file:///Users/mahamudc/Documents/NetSpout/docs/acceptance/evidence/gate13b/get_vendor_native_all_vendors.json) |
| `GNMI_SUBSCRIBE_ONCE_VERIFIED` | **VERIFIED** | [`subscribe_once_all_vendors.json`](file:///Users/mahamudc/Documents/NetSpout/docs/acceptance/evidence/gate13b/subscribe_once_all_vendors.json) |
| `GNMI_SUBSCRIBE_POLL_VERIFIED` | **VERIFIED** | [`subscribe_poll_phases.json`](file:///Users/mahamudc/Documents/NetSpout/docs/acceptance/evidence/gate13b/subscribe_poll_phases.json) |
| `GNMI_SUBSCRIBE_STREAM_SAMPLE_VERIFIED` | **VERIFIED** (`500ms` floor) | [`subscribe_stream_sample.json`](file:///Users/mahamudc/Documents/NetSpout/docs/acceptance/evidence/gate13b/subscribe_stream_sample.json) |
| `GNMI_SUBSCRIBE_STREAM_ON_CHANGE_VERIFIED` | **VERIFIED** (`BASELINE` $\rightarrow$ `DEGRADE` $\rightarrow$ `FAILOVER` $\rightarrow$ `RECOVERY`) | [`subscribe_stream_on_change_phases.json`](file:///Users/mahamudc/Documents/NetSpout/docs/acceptance/evidence/gate13b/subscribe_stream_on_change_phases.json) |
| `EXTERNAL_CLIENT_DECODED` | **VERIFIED** (`gnmic` + `pygnmi`) | [`gate13b_verification_manifest.json`](file:///Users/mahamudc/Documents/NetSpout/docs/acceptance/evidence/gate13b/gate13b_verification_manifest.json) |
| `SPLUNK_DISPATCHED` | **NOT VERIFIED** (Deferred to Gate 13D) | N/A — Gate 13B stops at external gNMI client decode |
| `SPLUNK_OBSERVED` | **NOT VERIFIED** (Deferred to Gate 13D) | N/A — Gate 13B stops at external gNMI client decode |

---

## 2. Positive Test Matrix (`T13B-01` .. `T13B-12`)

| Test ID | Description | Result |
|---|---|---|
| `T13B-01` | `Capabilities` RPC across `CISCO_IOS_XR`, `CISCO_IOS_XE`, `ARISTA_EOS`, `JUNIPER_JUNOS` (`gNMI 0.10.0`, encodings, models) | **PASS** |
| `T13B-02` | `Get` RPC across `ALL`, `CONFIG`, `STATE`, `OPERATIONAL`, prefix + multi-path, and `[name=*]` wildcards | **PASS** |
| `T13B-03` | Encoding verification (`JSON_IETF` RFC 7951 stringified 64-bit counters, `JSON` numeric, `PROTO` scalar `TypedValue`) | **PASS** |
| `T13B-04` | `Subscribe ONCE` across all 4 vendors with initial `Notification` burst + `sync_response=true` | **PASS** |
| `T13B-05` | `Subscribe POLL` on-demand polling across `BASELINE` $\rightarrow$ `DEGRADE` $\rightarrow$ `FAILOVER` $\rightarrow$ `RECOVERY` | **PASS** |
| `T13B-06` | `Subscribe STREAM / SAMPLE` at `500ms` cadence with monotonic counter progression | **PASS** |
| `T13B-07` | `Subscribe STREAM / ON_CHANGE` event-driven state transitions across all 4 phases | **PASS** |
| `T13B-08` | Multi-vendor OpenConfig (all 11 domains) + 4 vendor-native origins (`Cisco-IOS-XR-*-oper`, `Cisco-IOS-XE-*-oper`, `eos_native`, `junos`) | **PASS** |
| `T13B-09` | Prefix compression (`Notification.prefix` + relative `Update.path`) and `suppress_redundant` | **PASS** |
| `T13B-10` | Cross-transport coherence (`gNMI` $\leftrightarrow$ `SNMP` $\leftrightarrow$ `Syslog` $\leftrightarrow$ `NetFlow/IPFIX`) | **PASS** |
| `T13B-11` | Security modes (`INSECURE_LOCAL_LAB`, `TLS_SERVER_AUTH`, `MTLS_CLIENT_AUTH`), metadata auth, and credential redaction | **PASS** |
| `T13B-12` | External client verification (`gnmic v0.49.0` + `pygnmi v0.8.15`) and `1`/`8`/`16`/`32` stream concurrency benchmark | **PASS** |

---

## 3. Negative & Controlled-Failure Matrix (`T13B-NEG-01` .. `T13B-NEG-08` / Failures A–J)

| Controlled Failure | Test ID | Condition | Expected gRPC Status / Exception | Observed | Result |
|---|---|---|---|---|---|
| **Failure A** | `T13B-NEG-01` | `Set` RPC invoked on read-only target | `StatusCode.UNIMPLEMENTED` | `StatusCode.UNIMPLEMENTED` | **PASS** |
| **Failure B** | `T13B-NEG-02` | Malformed path syntax (`interfaces[broken`) | `StatusCode.INVALID_ARGUMENT` | `StatusCode.INVALID_ARGUMENT` | **PASS** |
| **Failure C** | `T13B-NEG-03` | Unknown path (`/openconfig-nonexistent/foo/bar`) or unknown target | `StatusCode.NOT_FOUND` | `StatusCode.NOT_FOUND` | **PASS** |
| **Failure C2** | `T13B-NEG-04` | Foreign vendor origin (`eos_native` on `CISCO_IOS_XR`) | `StatusCode.NOT_FOUND` (`FOREIGN_VENDOR_ORIGIN`) | `StatusCode.NOT_FOUND` | **PASS** |
| **Failure D** | `T13B-NEG-05` | `sample_interval` below `500ms` floor (`100ms`) | `StatusCode.INVALID_ARGUMENT` (or clamped to `500ms`) | `StatusCode.INVALID_ARGUMENT` & clamped | **PASS** |
| **Failure E** | `T13B-NEG-06` | Invalid metadata credentials (`username` / `password`) | `StatusCode.UNAUTHENTICATED` | `StatusCode.UNAUTHENTICATED` | **PASS** |
| **Failure F** | `T13B-NEG-07a` | Excessive paths per request (`65 > 64`) | `StatusCode.INVALID_ARGUMENT` (`MAX_PATHS_EXCEEDED`) | `StatusCode.INVALID_ARGUMENT` | **PASS** |
| **Failure G** | `T13B-NEG-07b` | Excessive concurrent streams (`> max_active_streams`) | `StatusCode.RESOURCE_EXHAUSTED` | `StatusCode.RESOURCE_EXHAUSTED` | **PASS** |
| **Failure H** | `T13B-NEG-08c` | Slow consumer queue overflow (`max_queue_size_per_stream`) | `StatusCode.RESOURCE_EXHAUSTED` (`STREAM_QUEUE_OVERFLOW`) | `StatusCode.RESOURCE_EXHAUSTED` | **PASS** |
| **Failure I** | `T13B-NEG-08b` | Non-loopback bind (`0.0.0.0`) without `allow_non_loopback=True` | `ValueError: NON_LOOPBACK_BIND_REJECTED` | `ValueError` | **PASS** |
| **Failure J** | `T13B-NEG-08a` | Unsupported encoding (`BYTES`, `ASCII`) | `StatusCode.UNIMPLEMENTED` | `StatusCode.UNIMPLEMENTED` | **PASS** |

---

## 4. Cross-Transport Coherence Proof (`cisco-asr9k-pe1`)

| Phase | gNMI `oper-status` | SNMP `ifOperStatus.1` | gNMI `in-octets` | SNMP `ifHCInOctets.1` | gNMI BGP `session-state` | SNMP `bgpPeerState` | Syslog Mnemonic | NetFlow `in_bytes_total` |
|---|---|---|---|---|---|---|---|---|
| `BASELINE` | `"UP"` | `1` (`up`) | `98504200000` | `98504200000` | `"ESTABLISHED"` | `6` (`established`) | `LINK-3-UPDOWN` (up), `BGP-5-ADJCHANGE` (Up) | `98504200000` |
| `DEGRADE` | `"DOWN"` | `2` (`down`) | `98654200000` | `98654200000` | `"IDLE"` | `1` (`idle`) | `LINK-3-UPDOWN` (down), `BGP-5-ADJCHANGE` (Down) | `98654200000` |
| `FAILOVER` | `"DOWN"` | `2` (`down`) | `98654200000` | `98654200000` | `"IDLE"` | `1` (`idle`) | `LINK-3-UPDOWN` (down), `BGP-5-ADJCHANGE` (Down) | `98654200000` |
| `RECOVERY` | `"UP"` | `1` (`up`) | `102404200000` | `102404200000` | `"ESTABLISHED"` | `6` (`established`) | `LINK-3-UPDOWN` (up), `BGP-5-ADJCHANGE` (Up) | `102404200000` |

---

## 5. Concurrency & Performance Benchmark Summary

| Concurrent Streams | Initial Syncs Completed | Total Setup + Sync Time (ms) | Avg Per-Stream Latency (ms) | Deadlocks / Drops |
|---|---|---|---|---|
| `1` | `1 / 1` | `1.39 ms` | `1.39 ms` | `0` |
| `8` | `8 / 8` | `6.12 ms` | `0.77 ms` | `0` |
| `16` | `16 / 16` | `11.45 ms` | `0.72 ms` | `0` |
| `32` | `32 / 32` | `22.84 ms` | `0.71 ms` | `0` |
