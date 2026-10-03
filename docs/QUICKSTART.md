# NetSpout — Quickstart Guide

This guide walks you through launching NetSpout in 1 click, verifying preflight prerequisites, executing your first multi-protocol network simulation, and investigating evidence in Splunk.

---

## 1. Zero-Touch 1-Click Setup (Recommended)

NetSpout is completely self-contained. It embeds all necessary collectors, encoders, and state engines. You do **not** need to install or run external collectors like `gnmic`, `snmptrapd`, `goflow2`, `telegraf`, or `SC4S`.

### Step 1: Clone the Repository
```bash
git clone https://github.com/machowdhury/NetSpout.git
cd NetSpout
```

### Step 2: Start NetSpout & Splunk
```bash
docker compose up -d
```

### Step 3: Access Web Interfaces
- **Splunk Enterprise**: [`http://localhost:8000`](http://localhost:8000) (Login: `admin` / `SplunkPassword123!`)
  - The NetSpout app is pre-installed at `/en-US/app/netspout/guided_onboarding`.
  - The HEC token `00000000-0000-0000-0000-000000000000` is pre-provisioned for the local `DEMO` profile.
- **NetSpout Standalone NOC UI**: [`http://localhost:8081`](http://localhost:8081) (Visibly badged as `DEMO / LOCAL LAB`).
- **Splunk HEC Port**: `8088` (`https://localhost:8088/services/collector`)
- **Splunk Management Port**: `8089` (`https://localhost:8089`)

> [!NOTE]
> The above credentials are exclusively for the local `DEMO` profile. For production or shared environments, switch to `NETSPOUT_PROFILE=secure` and supply dedicated secrets. See [docs/SECURITY.md](SECURITY.md) for details.

---

## 2. Alternative: Bare-Metal / Local Python Setup

If you prefer running NetSpout locally without Docker:

### Prerequisites
- macOS (Sonoma/Sequoia) or Linux (Ubuntu 22.04+, RHEL 9+)
- Python 3.10+ (compatible up to 3.14)
- Splunk Enterprise 9.0+ or Splunk Cloud

### Setup Steps
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure Splunk Connection (Canonical Ports)
export NETSPOUT_HEC_URL="https://127.0.0.1:8088/services/collector/event"
export NETSPOUT_HEC_TOKEN="00000000-0000-0000-0000-000000000000"
export NETSPOUT_SPLUNK_USER="admin"
export NETSPOUT_SPLUNK_PASSWORD="SplunkPassword123!"

# Launch NetSpout Backend
python3 run.py
```
Open browser to `http://localhost:8081`.

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
