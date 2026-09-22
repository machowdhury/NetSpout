# NetSpout ⚡

**Network Telemetry Generator, Simulation Canvas & Live SPL Playground for Splunk**

[![Splunk Enterprise](https://img.shields.io/badge/Splunk_Enterprise-9.0%2B_|_Cloud-ed5b26.svg?logo=splunk&logoColor=white)](https://www.splunk.com/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![GitHub](https://img.shields.io/badge/GitHub-machowdhury%2FNetSpout-181717.svg?logo=github&logoColor=white)](https://github.com/machowdhury/NetSpout)

NetSpout is a tool that sends realistic network logs, syslogs, and metrics directly into your Splunk instance. 

Normally, if you want to test network alerts, build NOC dashboards, or practice writing SPL searches, you need expensive routers, switches, and firewalls running in a real lab. NetSpout solves this problem: it generates realistic network events (Cisco, Palo Alto, Fortinet, Arista, Juniper, and more) and sends them to Splunk over the HTTP Event Collector (HEC) or Syslog in real time.

---

## 🎯 What You Can Do With NetSpout

1. **Test Splunk Searches & Alerts**: Generate real network failure scenarios (like BGP flaps, interface drops, or rogue access points) to see if your alerts fire properly.
2. **Build & Demo Dashboards**: Populate empty Splunk indexes with rich, realistic network data matching standard Splunk CIM (Common Information Model) data models.
3. **Trace Multi-Hop Paths**: Watch traffic and logs flow across multiple hops (user → switch → firewall → router → cloud).
4. **Practice SPL**: Run queries directly against your live Splunk server using our built-in library of 108 production network queries.

---

## 🧭 How to Use NetSpout (The 4 Main Tools)

NetSpout has 4 main panels. Here is a simple, step-by-step guide on how to use each one:

### 1. Guided Telemetry Onboarding Wizard
> **Best for:** Quickly blasting a batch of sample logs into Splunk or streaming a continuous test scenario.

* **Step 1: Choose Your Mode**
  * Pick **Batch Ingestion** if you want to instantly send a set number of events (e.g. 50 or 500 events) to test a query.
  * Pick **Continuous Scenario Stream** if you want ongoing traffic to test real-time dashboards.
* **Step 2: Pick Your Device & Vendor**
  * Select from 30 enterprise vendors (Cisco IOS-XE, Catalyst Center, Cisco SD-WAN, Cisco ISE, Cisco Duo, Palo Alto Networks, Fortinet FortiGate, Arista EOS, Juniper Junos, etc.).
* **Step 3: Choose a Scenario Preset**
  * Pick a prebuilt scenario like *BGP Flapping*, *Firewall Port Scan Blocked*, *802.1X Wireless Quarantine*, or *Optical Power Loss*.
* **Step 4: Send to Splunk**
  * Verify your Splunk HEC URL and target index (defaults to `idx_network_ops` or `main`).
  * Click **Blast Events to Splunk** (or **Start Streaming**). NetSpout immediately pushes the events to your Splunk HTTP Event Collector.

---

### 2. Scenario Builder & Path Emitter
> **Best for:** Seeing how a single network transaction or threat moves across multiple network hops.

In real networks, an event rarely happens on just one device. When a user connects to a server, logs are generated across switches, firewalls, and routers.

* **Step 1: Pick a Scenario**
  * Choose from 22 prebuilt path scenarios in the dropdown (e.g. *Campus 802.1X Auth Flow*, *Data Center Leaf-Spine Microburst*, or *SD-WAN Brownout Failover*).
* **Step 2: Inspect the Animated Path**
  * NetSpout displays an interactive diagram showing each hop in the network path (e.g. `Client` → `Catalyst 9300` → `Catalyst 9800 WLC` → `Cisco ISE` → `Firepower NGFW`).
* **Step 3: Click "Stream Path to Splunk"**
  * NetSpout will emit synchronized logs for every device in the path with matching IP addresses, MAC addresses, and timestamps.
* **Step 4: Stop Anytime**
  * Click **Stop Streaming** when you have collected enough data.

---

### 3. SPL Playground
> **Best for:** Learning and testing real Splunk searches against your actual Splunk index.

* **Step 1: Browse the Query Library**
  * Browse or filter 108 ready-to-use production search queries organized by category (BGP Routing, Firewall Drops, Transceiver Light Levels, Identity Quarantines, DNS Security, etc.).
* **Step 2: Load Query into Editor**
  * Click any query card to automatically load the SPL into the search editor. You can edit the query text or adjust time ranges whenever you want.
* **Step 3: Run the Search**
  * Click **Execute Search (Splunk REST API)**. NetSpout sends the query directly to your live Splunkd REST API (`/services/search/jobs`), tracks search progress, and pulls down the actual results.
* **Step 4: View Results**
  * **Table View**: Browse rows and columns with sorting.
  * **Raw Events / CIM View**: Inspect individual raw events and verify extracted fields like `action`, `src_ip`, `dest_ip`, `vendor`, and `sourcetype`.

---

### 4. NetSpout Canvas & Telemetry Orchestrator
> **Best for:** Designing visual network topologies, injecting live faults, and monitoring real-time telemetry.

* **Visual Canvas**:
  * Drag and drop routers, switches, access points, and firewalls onto the canvas.
  * Use the **Link Tool** to draw cables between device interfaces (e.g. `TenGigE1/0/1` to `TenGigE1/0/2`).
* **Live Transmission Status**:
  * Look at the top bar to verify the active transmission status:
    `HEC: 127.0.0.1:8888 -> idx_network_ops`
* **Pause & Resume Controls**:
  * Click **Pause Telemetry** to freeze event emission. A sticky banner lets you know the stream is paused so you can inspect current events without them scrolling away.
  * Click **Resume Telemetry** to resume sending live events.
* **Telemetry Tools Menu**:
  * Click the **Telemetry Tools ▾** dropdown in the top header to:
    * Toggle the **Live Log Drawer** at the bottom of the screen.
    * Export or Import your topology JSON.
    * Adjust generation frequency and packet rates.
* **Injecting Faults**:
  * Click on any router, switch, or cable and click **Cut Link** or **Simulate Port Down**.
  * The canvas immediately changes state and sends realistic `%LINK-3-UPDOWN`, `%LINEPROTO-5-UPDOWN`, and BGP neighbor drop logs to Splunk.

---

## ⚡ Quickstart

### Prerequisites
- Docker (optional, for all-in-one local setup) OR a running Splunk Enterprise / Splunk Cloud instance.
- Python 3.11+ (if running backend locally)
- Node.js 18+ (if running frontend locally)

### Quick Run with Docker
Run a complete environment with Splunk Enterprise + NetSpout in one command:
```bash
docker run -d \
  --name splunk-netspout-standalone \
  -p 8000:8000 \
  -p 8088:8088 \
  -p 8089:8089 \
  -p 8081:8081 \
  -e SPLUNK_START_ARGS="--accept-license" \
  -e SPLUNK_GENERAL_TERMS="--accept-sgt-current-at-splunk-com" \
  -e SPLUNK_PASSWORD="SplunkPassword123!" \
  netspout:standalone
```

Access points:
- **Splunk Web**: `http://localhost:8000` (User: `admin`, Password: `SplunkPassword123!`)
- **NetSpout Web UI**: `http://localhost:8081`
- **Splunk HEC Endpoint**: `https://localhost:8088/services/collector`

### Running From Source
1. **Start the Backend**:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   python3 run.py
   ```
   *The backend starts at `http://localhost:8000` (or configured port).*

2. **Start the Frontend**:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```
   *Open `http://localhost:5173` in your browser.*

---

## 🔌 Supported Vendors & Splunk Sourcetypes

NetSpout emits real log formats matching the official Splunk Technology Add-ons (TAs):

| Vendor | Device / Technology | Target Splunk Sourcetype | Recommended Splunk Add-on |
| :--- | :--- | :--- | :--- |
| **Cisco Systems** | Cisco IOS / IOS-XE Switches & Routers | `cisco:ios:syslog` | [Splunk Add-on for Cisco IOS](https://splunkbase.splunk.com/app/1467) |
| **Cisco Systems** | Catalyst Center (DNA Center) | `cisco:catalyst:devicehealth` | [Splunk Add-on for Cisco Catalyst Center](https://splunkbase.splunk.com/app/5580) |
| **Cisco Systems** | Cisco SD-WAN (Viptela) | `cisco:sdwan:linkhealth` | [Cisco SD-WAN Add-on for Splunk](https://splunkbase.splunk.com/app/7538) |
| **Cisco Systems** | Identity Services Engine (ISE) | `cisco:ise:syslog` | [Splunk Add-on for Cisco ISE](https://splunkbase.splunk.com/app/1924) |
| **Cisco Systems** | Secure Firewall (FTD / ASA) | `cisco:asa`, `cisco:sfw:estreamer` | [Cisco Security Cloud Add-on](https://splunkbase.splunk.com/app/6259) |
| **Cisco Systems** | Duo Security MFA | `cisco:duo:auth` | [Splunk Add-on for Cisco Duo Security](https://splunkbase.splunk.com/app/3466) |
| **Cisco Systems** | Meraki Cloud Managed WLAN | `meraki:accesspoints` | [Cisco Meraki Add-on for Splunk](https://splunkbase.splunk.com/app/6043) |
| **Palo Alto Networks** | PAN-OS Next-Gen Firewall | `pan:traffic`, `pan:threat` | [Palo Alto Networks Add-on for Splunk](https://splunkbase.splunk.com/app/2757) |
| **Fortinet** | FortiGate Next-Gen Firewall | `fortinet:fortigate:traffic` | [Fortinet FortiGate Add-on for Splunk](https://splunkbase.splunk.com/app/2800) |
| **Arista Networks** | EOS Data Center Switching | `arista:eos:syslog` | [Arista Networks EOS Add-on](https://splunkbase.splunk.com/app/3350) |
| **Juniper Networks** | Junos OS Routing & Switching | `juniper:junos:syslog` | [Splunk Add-on for Juniper](https://splunkbase.splunk.com/app/2855) |
| **F5 Networks** | BIG-IP Local Traffic Manager | `f5:bigip:traffic` | [F5 BIG-IP Add-on for Splunk](https://splunkbase.splunk.com/app/2680) |
| **Zscaler** | Zscaler Internet Access (ZIA) | `zscaler:web` | [Zscaler Add-on for Splunk](https://splunkbase.splunk.com/app/4363) |

---

## 🔍 Example SPL Searches

Once NetSpout is sending data into your Splunk index, try these searches in the **SPL Playground** or in Splunk Web:

### 1. View All Ingested Network Events by Sourcetype
```spl
index=idx_network_ops
| stats count by sourcetype, host
| sort -count
```

### 2. Find BGP Adjacency Flaps & State Changes
```spl
index=idx_network_ops (sourcetype="cisco:ios:syslog" OR sourcetype="arista:eos:syslog" OR sourcetype="juniper:junos:syslog") ("%BGP-5-ADJCHANGE" OR "HoldTimer" OR "DAMP")
| stats count, latest(_raw) as latest_event by host
| sort -count
```

### 3. Blocked Firewall Connections by Vendor and Port
```spl
index=idx_network_ops (sourcetype="cisco:asa" OR sourcetype="pan:traffic" OR sourcetype="fortinet:fortigate:traffic") action="blocked" OR action="deny" OR action="dropped"
| stats count by vendor, dest_port, src_ip
| sort -count
| head 20
```

---

## 👨‍💻 Creator & Contributors

- **Creator and Maintainer**: [machowdhury@yahoo.com](mailto:machowdhury@yahoo.com)
- **Contributor**: [machowdhury](https://github.com/machowdhury)
- **Project Repository**: [https://github.com/machowdhury/NetSpout](https://github.com/machowdhury/NetSpout)
- **License**: Apache-2.0
