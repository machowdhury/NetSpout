# NetSpout ⚡

**Carrier-Grade Network Telemetry Generator, Simulation Canvas & Live Incident Verification Platform for Splunk**

[![Splunk Enterprise](https://img.shields.io/badge/Splunk_Enterprise-9.0%2B_|_Cloud-ed5b26.svg?logo=splunk&logoColor=white)](https://www.splunk.com/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-machowdhury%2FNetSpout-181717.svg?logo=github&logoColor=white)](https://github.com/machowdhury/NetSpout)
[![Release](https://img.shields.io/badge/Release-1.0.0--rc1-emerald.svg)](https://github.com/machowdhury/NetSpout/releases)

NetSpout generates multi-protocol network telemetry across realistic operational failure and security incident scenarios, streaming evidence into Splunk without requiring physical network equipment or simulated virtual machines.

```text
                    SCENARIO / NETWORK STATE
                              │
                              ▼
                     ScenarioStateStore
                              │
        ┌─────────────┬───────┼─────────┬─────────────┐
        │             │       │         │             │
      SYSLOG         SNMP    gNMI    NetFlow/IPFIX   HEC
        │             │       │         │             │
        └─────────────┴───────┼─────────┴─────────────┘
                              │
                        Collectors / Splunk
                              │
                              ▼
                    Investigation / Validation
```

---

## 🎯 What NetSpout Does

1. **Demonstrates Realistic Network Incidents**: Models end-to-end incident lifecycles (`BASELINE` → `DEGRADE` → `FAILOVER` → `RECOVERY`) across Cisco, Arista, Juniper, and multi-vendor networks.
2. **True Multi-Protocol Telemetry**:
   - **Native gNMI / OpenConfig**: Wire-pure Protobuf/HTTP2 streaming to external collectors (`gnmic`), normalized to event (`netspout:gnmi:event`) and metric (`netspout:gnmi:metric`) stores.
   - **Native SNMPv2c**: Wire-pure ASN.1 BER UDP Traps (0xA7), Informs (0xA6), and Polling (GET/GETNEXT/GETBULK) to `snmptrapd` and Net-SNMP poller.
   - **Native Flow (NetFlow v9 & IPFIX)**: Wire-compliant RFC 3954 / RFC 7011 binary UDP datagrams to GoFlow2 / Splunk Stream.
   - **Direct HEC & Syslog**: Standards-compliant log generation matching official Splunk Technology Add-ons.
3. **Strict Telemetry Honesty**:
   - Clearly separates `NATIVE TRANSPORT` (actual standard byte serialization over network sockets) from `MODELED DEVICE STATE` (synthetic simulated device parameters).
   - Zero fabricated vendor schemas: Unsupported items (e.g., proprietary Cisco ACI APIC DME Managed Objects) are explicitly flagged as `UNSUPPORTED_TELEMETRY` rather than invented.
4. **End-to-End Audit & Verification**:
   - 7-to-8 stage evidence separation: `GENERATED` → `ENCODED` → `SENT` → `COLLECTOR_RECEIVED` → `NORMALIZED` → `SPLUNK_DISPATCHED` → `SPLUNK_OBSERVED` → `VALIDATED`.
   - Live Splunk REST query verification (`search` and `| mstats`) proving indexed presence before assertions pass.

---

## 🧭 The 5-Step Customer Workflow

NetSpout guides users through a clean 5-step operational workflow:

### Step 1 — CHOOSE
Select an operational failure scenario or security detection use case from the scenario catalog. Filter by vendor, domain, difficulty, or telemetry transport method (Syslog, SNMP, gNMI, Flow, HEC).

### Step 2 — PREVIEW
Inspect the scenario story, multi-hop topology, affected device entities, lifecycle phases, telemetry provenance, and clear fidelity badges (`NATIVE TRANSPORT` vs `MODELED DEVICE STATE`).

### Step 3 — CONNECT
One-click preflight verification checks all external prerequisites for the chosen scenario:
- Splunk HEC health (`https://127.0.0.1:8888/services/collector/health`)
- Splunk REST search API (`https://127.0.0.1:8889/services/search/jobs/export`)
- Target event index (`idx_network_ops`) & metric index (`cisco_mdt_metrics`)
- External collector binaries (`gnmic`, `snmptrapd`, Net-SNMP tools)
- Local socket bind permissions on loopback (`127.0.0.1`)

### Step 4 — RUN
Execute the lifecycle progression with real-time phase updates:
`BASELINE established` → `DEGRADE triggered` → `Collector observed` → `Splunk indexed` → `FAILOVER` → `RECOVERY`.

### Step 5 — PROVE
Audit the complete evidence ledger, inspect copyable SPL and `| mstats` investigation queries, review contract validation rules, and export companion run manifests.

---

## ⚡ Quickstart

### Prerequisites
- Python 3.10+ (macOS / Linux)
- Node.js 18+ (for building frontend)
- Splunk Enterprise 9.0+ or Splunk Cloud (running locally or remotely)
- Optional external collectors for native modes:
  - `gnmic` (v0.40+): `brew install gnmic` (macOS) or `curl -sL https://gnmic.openconfig.net/install.sh | sudo bash`
  - Net-SNMP (`snmpget`, `snmptrapd`): standard on macOS/Linux

### 1. Clone & Set Up NetSpout
```bash
git clone https://github.com/machowdhury/NetSpout.git
cd NetSpout
```

### 2. Configure Splunk Credentials
Set your Splunk environment variables or use the defaults:
```bash
export NETSPOUT_HEC_URL="https://127.0.0.1:8888/services/collector/event"
export NETSPOUT_HEC_TOKEN="00000000-0000-0000-0000-000000000000"
export NETSPOUT_SPLUNK_USER="admin"
export NETSPOUT_SPLUNK_PASSWORD="SplunkPassword123!"
```

### 3. Launch NetSpout Server
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 run.py
```
*Access the Web UI at `http://localhost:8081` or `http://localhost:8000`.*

---

## 📦 Splunk App Packaging

NetSpout is packaged as a standard self-contained Splunk Enterprise application package (`netspout.spl`):

```bash
# Build the production React frontend bundle
python3 scripts/build_frontend.py

# Package the release .spl archive
python3 scripts/build_splunk_package.py
```

The resulting `netspout.spl` archive can be installed via Splunk Web (**Manage Apps → Install app from file**) or uncompressed directly into `$SPLUNK_HOME/etc/apps/netspout`.

---

## 🔍 Canonical Splunk Investigation Queries

### Native gNMI Telemetry Events (`idx_network_ops`)
```spl
search index=idx_network_ops sourcetype="netspout:gnmi:event" netspout_run_id="$RUN_ID"
| table _time netspout_phase gnmi_target gnmi_origin gnmi_path gnmi_leaf gnmi_value
```

### Model-Driven Telemetry Metrics (`cisco_mdt_metrics`)
```spl
| mstats avg(_value) WHERE index=cisco_mdt_metrics netspout_run_id="$RUN_ID" metric_name=* BY metric_name span=1s
```

### Native SNMPv2c Traps & Informs (`idx_network_ops`)
```spl
search index=idx_network_ops sourcetype="netspout:snmp:trap" netspout_run_id="$RUN_ID"
| table _time netspout_phase snmp_pdu_type snmp_trap_name snmp_oid_name snmp_value sys_uptime
```

### Cross-Protocol Incident Correlation
```spl
search index=idx_network_ops netspout_run_id="$RUN_ID" (sourcetype="netspout:gnmi:event" OR sourcetype="netspout:snmp:trap" OR sourcetype="cisco:ios:syslog")
| stats count as records dc(sourcetype) as source_count values(sourcetype) as sourcetypes by netspout_phase netspout_device_id
```

---

## 📚 Documentation Suite

- [Quickstart Guide](docs/QUICKSTART.md): Step-by-step installation, collector setup, and first run.
- [Troubleshooting & Diagnostics](docs/TROUBLESHOOTING.md): Preflight failure fixes, collector debugging, and Splunk HEC validation.
- [Known Limitations](docs/LIMITATIONS.md): Unsupported protocol scopes, loopback bindings, and telemetry honesty declarations.
- [Future Roadmap](docs/ROADMAP.md): Post-1.0 goals including OTLP streaming, NETCONF/RESTCONF, and AI fabric topologies.
- [Gate 13E Acceptance Report](docs/acceptance/NETSPOUT_GATE_13E_GNMI_CUSTOMER_ACCEPTANCE.md): Independent customer verification evidence and evaluation.

---

## 🛡️ Security & Privacy Notice

- **Loopback Only**: All native simulated servers (gNMI gRPC, SNMP agent, UDP listeners) bind strictly to `127.0.0.1` by default.
- **Read-Only / Simulation Bound**: gNMI `SetRequest` is disabled; SNMP `SetRequest` is explicitly rejected with `noAccess`.
- **Zero Secrets Committed**: Default HEC tokens and passwords are standard lab placeholders; environment variables override all credentials.

---

## 👨‍💻 Creator & Contributors

- **Creator and Maintainer**: [machowdhury@yahoo.com](mailto:machowdhury@yahoo.com)
- **Contributor**: [machowdhury](https://github.com/machowdhury)
- **Project Repository**: [https://github.com/machowdhury/NetSpout](https://github.com/machowdhury/NetSpout)
- **License**: Apache-2.0
