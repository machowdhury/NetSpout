# NetSpout — Quickstart Guide

This guide walks you through installing NetSpout, verifying preflight prerequisites, executing your first multi-protocol network simulation, and investigating evidence in Splunk.

---

## 1. System Requirements

- **Operating System:** macOS (Sonoma/Sequoia) or Linux (Ubuntu 22.04+, RHEL 9+)
- **Python:** 3.10, 3.11, or 3.12 (Python 3.14 compatible)
- **Node.js:** 18+ (only needed if building frontend from source)
- **Splunk:** Splunk Enterprise 9.0+ or Splunk Cloud
- **Optional Tools (for Native Transport modes):**
  - `gnmic` (v0.40+): `brew install gnmic` or `curl -sL https://gnmic.openconfig.net/install.sh | sudo bash`
  - Net-SNMP tools: `/usr/bin/snmpget`, `/usr/sbin/snmptrapd` (included by default on macOS/Linux)

---

## 2. Fast Setup (5 Minutes)

### Step 1: Clone the Repository
```bash
git clone https://github.com/machowdhury/NetSpout.git
cd NetSpout
```

### Step 2: Install Python Dependencies
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 3: Configure Splunk Connection
NetSpout interacts with Splunk via the HTTP Event Collector (HEC) and the Splunk REST search API. Set your environment variables:

```bash
# Splunk HEC Settings (Port 8888 or 8088 depending on your instance)
export NETSPOUT_HEC_URL="https://127.0.0.1:8888/services/collector/event"
export NETSPOUT_HEC_TOKEN="00000000-0000-0000-0000-000000000000"

# Splunk REST Search Settings (Port 8889 or 8089)
export NETSPOUT_SPLUNK_USER="admin"
export NETSPOUT_SPLUNK_PASSWORD="SplunkPassword123!"
```

### Step 4: Start NetSpout
```bash
python3 run.py
```
Open your browser to:
👉 `http://localhost:8081` (or `http://localhost:8000`)

---

## 3. Running Your First Scenario: `service_provider_cisco`

NetSpout organizes simulation into a 5-step operational workflow:

### Step 1: Choose Scenario
- In the NetSpout UI, select **Service Provider Cisco Edge & Core**.
- Notice the badges: `NATIVE TRANSPORT`, `MODELED DEVICE STATE`, `BEGINNER`.

### Step 2: Preview Topology & Lifecycle
- Review the network topology (`cisco-asr9k-pe1` → `cisco-8000-p1` → `cisco-asr9k-pe2`).
- Check the 4 phases:
  1. `BASELINE`: All interfaces UP, BGP established, nominal transit metrics.
  2. `DEGRADE`: HundredGigE0/0/0/0 optical power drops, discards rise.
  3. `FAILOVER`: Primary link goes DOWN, BGP adjacency tears down, traffic diverts to secondary path.
  4. `RECOVERY`: Interface restored, BGP re-establishes, traffic normalizes.

### Step 3: Run Preflight
- Click **Step 3: Connect**.
- NetSpout checks Splunk HEC, Splunk REST API, target index `idx_network_ops`, and local loopback bind permissions.
- When all checks show green, click **Proceed to Run**.

### Step 4: Execute Simulation
- Click **Start Simulation**.
- Watch the live phase indicator advance from `BASELINE` through `RECOVERY`.

### Step 5: Prove in Splunk
- In **Step 5: Prove**, review the 7-stage evidence ledger:
  - `GENERATED` → `ENCODED` → `COLLECTOR` → `NORMALIZED` → `ADAPTED` → `DISPATCHED` → `OBSERVED`.
- Copy the pre-built investigation queries directly into your Splunk Search bar.

---

## 4. Querying Evidence in Splunk

Open Splunk Web (`http://localhost:8000`) and paste any of the following queries:

### 1. View Interface & BGP Transitions
```spl
search index=idx_network_ops (sourcetype="netspout:gnmi:event" OR sourcetype="netspout:snmp:trap")
| table _time netspout_phase gnmi_target gnmi_leaf gnmi_value snmp_trap_name
```

### 2. View MDT Metrics in Metric Index
```spl
| mstats avg(_value) WHERE index=cisco_mdt_metrics metric_name=* BY metric_name span=1s
```

### 3. Verify Stage Accounting
```spl
search index=idx_network_ops sourcetype="netspout:gnmi:event"
| stats count by origin_evidence_stage, current_evidence_stage, netspout_phase
```

---

## 5. Next Steps

- Explore [docs/TROUBLESHOOTING.md](TROUBLESHOOTING.md) if preflight fails.
- Read [docs/LIMITATIONS.md](LIMITATIONS.md) to understand protocol coverage boundaries.
- Inspect [docs/ROADMAP.md](ROADMAP.md) for post-1.0 features.
