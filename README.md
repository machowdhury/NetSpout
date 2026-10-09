# NetSpout ⚡

**Carrier-Grade Network Telemetry Generator, Simulation Canvas & Live Incident Verification Platform for Splunk**

[![Splunk Enterprise](https://img.shields.io/badge/Splunk_Enterprise-9.0%2B-ed5b26.svg?logo=splunk&logoColor=white)](https://www.splunk.com/)
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

1. **Demonstrates Realistic Network Incidents**: Models end-to-end incident lifecycles (`BASELINE` → `DEGRADE` → `FAILOVER` → `RECOVERY`) across **22 modern network domains** and **37 canonical scenarios** ([Scenario Catalog](docs/SCENARIO_CATALOG.md), [Network Domains](docs/NETWORK_DOMAINS.md)).
2. **True Multi-Protocol Telemetry**:
   - **Native gNMI / OpenConfig**: Wire-pure Protobuf/HTTP2 streaming to external collectors (`gnmic`), normalized to event (`netspout:gnmi:event`) and metric (`netspout:gnmi:metric`) stores.
   - **Native SNMPv2c**: Wire-pure ASN.1 BER UDP Traps (0xA7), Informs (0xA6), and Polling (GET/GETNEXT/GETBULK) to `snmptrapd` and Net-SNMP poller.
   - **Native Flow (NetFlow v9 & IPFIX)**: Wire-compliant RFC 3954 / RFC 7011 binary UDP datagrams to GoFlow2 / Splunk Stream.
   - **Direct HEC & Syslog**: Standards-compliant log generation matching official Splunk Technology Add-ons.
3. **Strict Telemetry Honesty & Provenance**:
   - Clearly separates `NATIVE TRANSPORT` (actual standard byte serialization over network sockets) from `MODELED DEVICE STATE` (synthetic simulated device parameters).
   - Zero fabricated vendor schemas: All telemetry is grounded in authoritative vendor documentation or RFCs ([Provenance Registry](docs/TELEMETRY_PROVENANCE.md)). Unsupported items are explicitly flagged as `UNSUPPORTED_TELEMETRY`.
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
One-click preflight verification checks all prerequisites for the chosen scenario:
- Splunk HEC health (`https://127.0.0.1:8088/services/collector/health`)
- Splunk REST search API (`https://127.0.0.1:8089/services/search/jobs/export`)
- Target event index (`idx_network_ops`) & metric index (`cisco_mdt_metrics`)
- Embedded telemetry pipelines (Native gNMI server, SNMP agent, Flow encoders, Syslog engine)
- Local socket bind permissions on loopback (`127.0.0.1`)

### Step 4 — RUN
Execute the lifecycle progression with real-time phase updates:
`BASELINE established` → `DEGRADE triggered` → `Collector observed` → `Splunk indexed` → `FAILOVER` → `RECOVERY`.

### Step 5 — PROVE
Audit the complete evidence ledger, inspect copyable SPL and `| mstats` investigation queries, review contract validation rules, and export companion run manifests.

---

## ⚡ 1-Click Zero-Touch Quickstart (Docker)

NetSpout is completely self-contained. You do **not** need to install or configure external collectors (`gnmic`, `snmptrapd`, `goflow2`, `telegraf`, `SC4S`, etc.) — all telemetry generation, encoding, and ingestion pipelines are built right into the platform.

### Step 1: Clone the Repository
```bash
git clone https://github.com/machowdhury/NetSpout.git
cd NetSpout
```

### Step 2: Launch with Docker Compose
```bash
cp .env.example .env
# Supply unique SPLUNK_PASSWORD and SPLUNK_HEC_TOKEN values in .env.
docker compose up -d
```

### Step 3: Open in Browser
- **Splunk Enterprise Web**: [`http://localhost:8000`](http://localhost:8000)
  - Use the administrator name and password supplied through your local `.env`.
  - Pre-installed App: **NetSpout Telemetry Generator** (`/en-US/app/netspout/guided_onboarding`)
- **NetSpout Standalone NOC Web UI**: [`http://localhost:8081`](http://localhost:8081)
- **Splunk HEC Endpoint**: `https://localhost:8088/services/collector` using the token supplied through `.env`
- **Splunk REST Management API**: `https://localhost:8089`

> [!NOTE]
> NetSpout has no repository default credentials. Never reuse disposable lab
> credentials for an external Splunk environment. See
> [the release-candidate guide](docs/RELEASE_CANDIDATE_GUIDE.md).

---

## 💻 Alternative: Bare-Metal / Local Python Development

For local development or testing without Docker:

### Prerequisites
- Python 3.10+ (macOS / Linux)
- Node.js 18+ (for compiling frontend)
- Splunk Enterprise 9.0+ or Splunk Cloud

### 1. Set Up Environment & Install Dependencies
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Splunk Credentials
```bash
export NETSPOUT_HEC_URL="https://127.0.0.1:8088/services/collector/event"
export NETSPOUT_HEC_TOKEN="<provided securely at runtime>"
export NETSPOUT_SPLUNK_USER="admin"
export NETSPOUT_SPLUNK_PASSWORD="<provided securely at runtime>"
```

### 3. Launch NetSpout Backend
```bash
python3 run.py
```
*Access the Standalone Web UI at `http://localhost:8081`.*

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
