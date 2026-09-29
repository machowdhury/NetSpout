# NETSPOUT GATE 13B — NATIVE gNMI / OPENCONFIG CORE ENGINE TEST PLAN

**Document ID:** `NETSPOUT-ARCH-G13B-TEST`  
**Gate:** Gate 13 (Architecture & Test Specification for Gate 13B)  
**Target Gate:** Gate 13B — Native gNMI Server & OpenConfig Core Engine  
**Status:** APPROVED SPECIFICATION  

---

## 1. Bounded Gate 13B Implementation Scope

Gate 13B is strictly bounded to implementing and proving the **Native gNMI Server & OpenConfig Core Engine** against independent external gNMI clients (`pygnmi` / `gnmic`).

| Scope Dimension | Gate 13B Requirement |
| :--- | :--- |
| **gNMI RPCs** | `Capabilities`, `Get`, `Subscribe` (`ONCE`, `POLL`, `STREAM/SAMPLE`, `STREAM/ON_CHANGE`), `Set` (explicit `UNIMPLEMENTED` rejection) |
| **Encodings** | `JSON_IETF` (mandatory primary), `JSON`, `PROTO` (scalar/counter fields) |
| **Vendor Profiles** | `CISCO_IOS_XR`, `CISCO_IOS_XE`, `ARISTA_EOS`, `JUNIPER_JUNOS` |
| **Golden Multi-Vendor Scenario** | `openconfig_mdt_streaming` (`topology_id: openconfig_core`, 4 nodes across all 4 vendors) |
| **Core Sensor Domains** | Interfaces (`openconfig-interfaces` + vendor native), LLDP (`openconfig-lldp`), BGP (`openconfig-network-instance` / `bgp`), System/Platform (`openconfig-system`, `openconfig-platform`), QoS (`openconfig-qos`) |
| **Cross-Transport State Coherence** | Shared `ScenarioStateStore` snapshot verification across gNMI `Get`/`Subscribe`, SNMPv2c (`IF-MIB`), and Syslog/JSON |
| **Splunk E2E Included** | **NO** (Deferred to Gate 13D — External gNMI Collector $\rightarrow$ Splunk E2E) |
| **UI Workflow Polish Included** | **NO** (Deferred to Gate 13E — Productization & UI) |

---

## 2. Test Suite Architecture (`tests/test_gate13b_gnmi_core.py`)

Gate 13B will introduce an automated unit and integration test suite (`tests/test_gate13b_gnmi_core.py`) alongside an independent external client verification harness (`scripts/verify_gnmi_agent.py`).

### 2.1 Test Category Matrix

| Test ID | Category | RPC / Mode | Description | Expected Outcome |
| :--- | :--- | :--- | :--- | :--- |
| `T13B-01` | Capabilities | `Capabilities()` | Query supported models, encodings, and gNMI version (`0.10.0`) per vendor node (`target="Cisco-8000-Core01"`, etc.) | Returns `gNMI_version="0.10.0"`, `JSON_IETF`/`JSON`/`PROTO`, OpenConfig + vendor-native `ModelData` list |
| `T13B-02` | Unary Get | `Get(ALL, JSON_IETF)` | Exact path query `/interfaces/interface[name=HundredGigE0/0/0/0]/state` on `Cisco-8000-Core01` | Returns single `Notification` with RFC 7951 JSON payload (`openconfig-interfaces:state`) and stringified `uint64` counters |
| `T13B-03` | Unary Get (Wildcard) | `Get(STATE, JSON_IETF)` | Wildcard key query `/interfaces/interface[name=*]/state/counters` on `Arista-7280R-Spine` | Returns notifications for `Ethernet1/1`, `Ethernet2/1`, and `Management1` |
| `T13B-04` | Subscribe ONCE | `Subscribe(ONCE)` | Snapshot subscription for `/system/state` and `/lldp/interfaces` | Emits initial `Notification` batch followed immediately by `sync_response: true`, then closes stream cleanly (`StatusCode.OK`) |
| `T13B-05` | Subscribe POLL | `Subscribe(POLL)` | On-demand poll subscription for `/interfaces/interface[name=et-0/0/0]/state/counters`; send 3 `Poll()` messages | Each `Poll()` triggers a fresh snapshot + `sync_response: true` with monotonically advancing counters |
| `T13B-06` | Subscribe STREAM (`SAMPLE`) | `Subscribe(STREAM, SAMPLE)` | `sample_interval = 1_000_000_000` (1s) across interface + QoS counters | Emits initial snapshot + `sync_response: true`, followed by periodic notifications at 1s intervals |
| `T13B-07` | Subscribe STREAM (`ON_CHANGE`) | `Subscribe(STREAM, ON_CHANGE)` | Subscribe to `/interfaces/interface[name=HundredGigE0/0/0/0]/state/oper-status` and BGP `session-state`; advance scenario to `degrade` | Emits initial state (`UP` / `ESTABLISHED`) + `sync_response: true`; emits immediate event-driven update (`DOWN` / `ACTIVE`) on phase transition |
| `T13B-08` | Heartbeat & Suppress Redundant | `Subscribe(STREAM)` | `ON_CHANGE` with `heartbeat_interval = 2s` and `SAMPLE` with `suppress_redundant = true` | `ON_CHANGE` re-emits unchanged leaf after 2s; `SAMPLE` suppresses unchanged static leaves |
| `T13B-09` | Prefix Compression | `Subscribe(STREAM)` | `SubscriptionList.prefix = /interfaces/interface[name=FortyGigE1/0/1]` with relative sub-paths `state/oper-status` and `state/counters` | `Notification.prefix` carries interface root; `Update.path` carries relative leaf path |
| `T13B-10` | PROTO Encoding | `Get(STATE, PROTO)` | Query scalar/counter leaves with `encoding = PROTO` | `Update.val` uses typed `uint_val`, `string_val`, `bool_val` instead of `json_ietf_val` |
| `T13B-11` | Cross-Vendor Native Origin | `Get` / `Subscribe` | Query `Cisco-IOS-XR-infra-statsd-oper:*`, `Cisco-IOS-XE-interfaces-oper:*`, `eos_native:/Sysdb/...`, and `junos:/junos/system/...` | Each vendor node serves its own native origin paths and rejects foreign vendor origins with `NOT_FOUND` |
| `T13B-12` | Cross-Transport Coherence | gNMI + SNMP + Syslog | Simultaneously query gNMI `/interfaces/interface/state/counters/in-octets` and SNMP `ifHCInOctets` (`1.3.6.1.2.1.31.1.1.1.6`) at fixed tick `t` | Counter values and `oper-status` / `ifOperStatus` match 1:1 from shared `ScenarioStateStore` |

---

## 3. Negative, Error Handling, and Security Tests

| Test ID | Condition Tested | Input | Expected gRPC Status / Behavior |
| :--- | :--- | :--- | :--- |
| `T13B-NEG-01` | Write Protection (`Set` RPC) | Any `SetRequest` (`delete`, `replace`, `update`) | `StatusCode.UNIMPLEMENTED`: `"NetSpout gNMI target is read-only; Set RPC is disabled by security policy."` |
| `T13B-NEG-02` | Malformed XPath | `/interfaces/interface[name=Ethernet1/1/state` (unclosed bracket) | `StatusCode.INVALID_ARGUMENT` |
| `T13B-NEG-03` | Unknown Target Device | `Prefix.target = "NonExistentRouter"` | `StatusCode.NOT_FOUND` |
| `T13B-NEG-04` | Unsupported Encoding | `encoding = ASCII` or `BYTES` | `StatusCode.UNIMPLEMENTED` |
| `T13B-NEG-05` | Sample Interval Floor | `sample_interval = 10_000_000` (10ms < 500ms floor) | Clamped to `500_000_000` ns (or rejected when strict clamping disabled) |
| `T13B-NEG-06` | Authentication Failure | Invalid `username` / `password` in gRPC metadata when auth enabled | `StatusCode.UNAUTHENTICATED` |
| `T13B-NEG-07` | Subscription Cap | Open $> 32$ concurrent streams or $> 64$ paths in one request | `StatusCode.RESOURCE_EXHAUSTED` |
| `T13B-NEG-08` | Slow Consumer Backpressure | Client stops reading stream while `SAMPLE` notifications queue $> 256$ messages | Server terminates stalled stream with `StatusCode.RESOURCE_EXHAUSTED` without leaking tasks |

---

## 4. Independent External Client Verification Protocol

Gate 13B completion requires executing an external gNMI client against the live NetSpout gNMI port (`127.0.0.1:57400`) while running `openconfig_mdt_streaming`:

```bash
# 1. Capabilities check via gnmic / pygnmi
gnmic -a 127.0.0.1:57400 --target Cisco-8000-Core01 --insecure capabilities

# 2. Unary Get check across all 4 vendors
gnmic -a 127.0.0.1:57400 --target Cisco-8000-Core01 --insecure get \
  --path "/interfaces/interface[name=HundredGigE0/0/0/0]/state"
gnmic -a 127.0.0.1:57400 --target Arista-7280R-Spine --insecure get \
  --path "/interfaces/interface[name=Ethernet1/1]/state"
gnmic -a 127.0.0.1:57400 --target Juniper-PTX10K-PE01 --insecure get \
  --path "/interfaces/interface[name=et-0/0/0]/state"
gnmic -a 127.0.0.1:57400 --target Catalyst-9600-Leaf --insecure get \
  --path "/interfaces/interface[name=FortyGigE1/0/1]/state"

# 3. Streaming SAMPLE + ON_CHANGE verification
gnmic -a 127.0.0.1:57400 --target Cisco-8000-Core01 --insecure subscribe \
  --path "/interfaces/interface[name=HundredGigE0/0/0/0]/state/counters" \
  --stream-mode sample --sample-interval 1s --once=false
```

---

## 5. Gate 13B Exit Criteria

1. All `T13B-01` through `T13B-12` and `T13B-NEG-01` through `T13B-NEG-08` tests pass (`0` failures).
2. External client (`pygnmi` / `gnmic`) verifies `Capabilities`, `Get`, and `Subscribe` (`ONCE`, `POLL`, `SAMPLE`, `ON_CHANGE`) against all 4 vendor targets on `openconfig_mdt_streaming`.
3. Cross-transport coherence check proves identical counter/state values between gNMI and SNMPv2c at the same simulation tick.
4. Existing 13 `GOLDEN_PATH_CERTIFIED` scenarios, NetFlow/IPFIX tests, and SNMP Gate 12 tests pass with zero regressions.
