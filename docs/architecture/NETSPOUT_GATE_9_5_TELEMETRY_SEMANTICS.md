# NetSpout Gate 9.5: Telemetry Semantics & UX Clarification Architecture

## 1. Executive Summary & Design Rationale

During the Wave 1 Independent Product Acceptance phase, NetSpout demonstrated end-to-end telemetry generation, controlled failure integrity, multi-vendor payload formatting, and automated validation across representative scenarios. However, testing highlighted friction point **`W1-P2-001`**:

> **Problem Statement:** A first-time user seeing "OpenConfig MDT Streaming" and "gNMI" could mistakenly assume that NetSpout establishes a native gRPC/gNMI dial-out or dial-in session over TCP/UDP to an external collector. When encountering Splunk HEC as the transport and observing dual-destination indexing (`cisco_mdt_metrics` + `idx_network_ops`), ambiguity arose regarding what is modeled versus how it is transported.

**Gate 9.5 resolves this friction permanently through explicit UX semantics without requiring architectural bloat or mock network protocol stacks.**

NetSpout models authentic RFC 7951 JSON-IETF Model-Driven Telemetry (MDT) and delivers these modeled payloads directly to Splunk via the high-throughput HTTP Event Collector (HEC). Gate 9.5 codifies these semantics across the canonical data catalog, core models, backend API, and React workflow UI so that users have complete architectural transparency *before* initiating execution.

---

## 2. Telemetry Semantics Data Contract

The canonical catalog (`src/netspout_core/models.py`, `scripts/build_canonical_catalog.py`, `catalog/scenarios.json`) defines five explicit telemetry semantics fields on every `ScenarioContract` and `UseCaseContract`:

| Field Name | Type | Description | Allowed Values / Standard Formats |
| :--- | :--- | :--- | :--- |
| `telemetry_model` | `string` | What telemetry domain and schema is modeled | e.g. `"OpenConfig / MDT"`, `"SD-WAN BFD Tunnel & ThousandEyes Synthetics"`, `"Perimeter Firewall, WAF & Database Audit"` |
| `transport_protocol` | `string` | How telemetry is transmitted across the wire | e.g. `"Splunk HEC"` (HTTP Event Collector) |
| `splunk_storage` | `string` | Exact destination Splunk index(es) where data lands | e.g. `"Metrics Index (cisco_mdt_metrics) + Event Index (idx_network_ops)"`, `"Splunk Event Index (idx_network_ops)"` |
| `fidelity_badge` | `string` | Explicit categorization of transport/payload fidelity | Strictly constrained to: `NATIVE TRANSPORT`, `MODELED PAYLOAD`, or `SYNTHETIC` |
| `telemetry_notes` | `string` (optional) | Educational guidance explaining simulation behavior | Educational callout for advanced/modeled scenarios; omitted or concise on standard syslog |

---

## 3. Fidelity Badge Semantics

The fidelity badge clearly establishes user expectations:

1. **`NATIVE TRANSPORT`**: Reserved for future scenarios where the transport wire protocol natively matches the network hardware protocol (e.g. native syslog UDP/TCP port 514 or native SNMP UDP port 162).
2. **`MODELED PAYLOAD`**: Used when NetSpout models authentic vendor payloads (e.g., OpenConfig YANG RFC 7951 JSON-IETF, PAN-OS CSV, Cisco IOS-XE syslog, ThousandEyes JSON metrics) and transmits them through an enterprise integration pipeline (such as Splunk HEC).
3. **`SYNTHETIC`**: Used for lightweight benchmark generators and synthetic traffic probes.

For `openconfig_mdt_streaming`, the fidelity badge is strictly **`MODELED PAYLOAD`**. NetSpout never makes misleading claims such as "NATIVE STREAMING" or "NATIVE gNMI SESSION".

---

## 4. UI/UX Clarification Architecture

The frontend workflow presents telemetry semantics at two distinct moments in the user journey:

### 4.1 Step 1: Use Case Selection (`StepChoose.tsx`)
- **Card Top Row**: A compact fidelity badge (`MODELED PAYLOAD` in violet) appears alongside the domain and difficulty pills.
- **Collapsible "Advanced Details"**: Clicking reveals:
  - **Telemetry Model**: `OpenConfig / MDT`
  - **Transport**: `Splunk HEC`
  - **Storage**: `Metrics Index (cisco_mdt_metrics) + Event Index (idx_network_ops)`
  - **Target Sourcetypes**: `cisco:ios:mdt`, `arista:telemetry:json`, `cisco:ios:syslog`

### 4.2 Step 2: Scenario Preview (`StepPreview.tsx`)
A dedicated **"Telemetry Semantics & Architecture"** card is placed prominently in the left-hand column:
- Displays **Fidelity Badge**: `MODELED PAYLOAD`
- Displays **Telemetry Model**: `OpenConfig / MDT`
- Displays **Transport Protocol**: `Splunk HEC`
- Displays **Splunk Storage**: `Metrics Index (cisco_mdt_metrics) + Event Index (idx_network_ops)`
- Displays **Educational Callout Box**:
  > ℹ️ *NetSpout models OpenConfig/MDT telemetry fields and metric behavior. In this scenario the telemetry is delivered to Splunk through HEC rather than a native gNMI/gRPC session.*

### 4.3 Topology Preset Description Refinement (`defaultTopologies.ts`)
Updated the zone description in `PRESET_OPENCONFIG_CORE`:
- **Before**: `"OpenConfig YANG streaming routers emitting gNMI telemetry"`
- **After**: `"OpenConfig YANG streaming routers with modeled telemetry payload"`

---

## 5. Verification & Test Architecture

A dedicated regression test suite was introduced:
`tests/test_gate9_5_telemetry_semantics.py`

| Test Case | Description | Result |
| :--- | :--- | :--- |
| `test_01_all_scenarios_have_telemetry_semantics_metadata` | Verifies all 29 scenarios define `telemetry_model`, `transport_protocol`, `splunk_storage`, and `fidelity_badge`. | **PASS** |
| `test_02_openconfig_mdt_streaming_semantics` | Verifies `openconfig_mdt_streaming` has `MODELED PAYLOAD`, `Splunk HEC`, both storage indices, and the educational callout. | **PASS** |
| `test_03_topology_preset_description_updated` | Verifies topology zone descriptions do not claim native gRPC sessions. | **PASS** |
| `test_04_wave1_acceptance_maturity_promotions` | Verifies post-Wave 1 maturity distribution (`GOLDEN_PATH_CERTIFIED`). | **PASS** |
| `test_05_backend_api_use_cases_serialization` | Verifies `/api/use-cases` exposes all 5 semantics fields to the frontend. | **PASS** |
| `test_06_golden_paths_regression_execution` | Executes mock runs across all certified Golden Paths to ensure zero regressions. | **PASS** |

### Complete Regression Suite
All 150 gate tests across Gates 1, 2, 3, 4, 5, 6, 7, 8, 9, and 9.5 passed cleanly (`Ran 150 tests in 11.729s — OK`).
