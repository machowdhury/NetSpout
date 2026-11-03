# NetSpout PulseForge: presenter script

Demo: November 3, 2026, 9:00 AM ET. Length: 23 minutes plus questions. Deck: `NetSpout_PulseForge_Demo.pptx` (15 slides, speaker notes on every slide). One-page version: `NetSpout_Demo_Cheat_Sheet.md`.

No credentials appear in this file. The lab password and HEC token live only in the git-ignored `tests/lab/phase4e/.env.lab`.

## Ground rules for what you say

| Say | Do not say |
|---|---|
| The demo environment runs the **released app**. 148 scenarios are runnable here. | "All 372 scenarios are in this demo." |
| 372 are runnable on current `main`. 224 of them are new, independently indexed in an isolated lab, **not installed here**. | "The new 224 are live in this environment." |
| 184 of the 224 are **modeled**: the labeled `netspout:scenario:state` schema, not vendor logs. | "All scenarios produce vendor-authentic logs." |
| "Indexed" means an independent Splunk search found the events by run ID. | "HEC accepted it, so it is indexed." |
| The single-package installer is **experimental and not released**. | "You can install it with one package today." |
| Metric dashboards were validated in the lab. This Splunk has no metrics index. | "Metric dashboards are working here." |
| Flow data shows indicators (volume, flags, targets). It cannot prove loss of availability. | "PulseForge proves the attack caused an outage." |

## Time allocation (23 minutes)

| Block | Slides | Minutes | Running total |
|---|---|---|---|
| A. Story | 1 to 5 | 7 | 7 |
| B. Product tour | 6 to 9 | 5 | 12 |
| C. Live demo | 10 to 13 (slides are the fallback) | 8 | 20 |
| D. Evidence and close | 13 to 15 | 3 | 23 |
| Questions | | 5 to 10 | |

---

## Block A: the story (7 minutes)

**Slide 1: Title (0:45)**
"This is NetSpout PulseForge. In one sentence: it lets you pick an incident, run it, and prove in Splunk what actually arrived. Today I will show the released app on our lab Splunk, and I will be explicit about what is merged but not installed here."
Transition: "Why build it?"

**Slide 2: The problem (1:15)**
"Three problems. Incidents are rare and you cannot rehearse them in production. Detections and dashboards need data with the right fields and order, not random events. And lab data rarely tells you what is real, what is modeled, and what reached the index. PulseForge is built around those three gaps: runnable scenarios, labeled provenance, and verified indexing."
Transition: "So what does it do?"

**Slide 3: What it enables (1:15)**
"Four verbs: choose, run, observe, investigate. The numbers: 349 sourcetypes across 88 vendors in the catalog. 372 scenarios are defined and runnable on main. In the released app you will see in this demo, 148 are runnable. I will keep those two numbers apart all session."
Transition: "Here is the whole thing on one page."

**Slide 4: Application mind map (1:30)**
Walk clockwise from Experience. "Experience is the Splunk Web app. Catalog is what we can emit. Scenarios are the stories. Generate is the engine: vendor-native formats, recorded samples, and a clearly labeled modeled state. Deliver is HEC and native protocols. Splunk is searchable events and run-bound dashboards. Operate is how you install it. The single-package installer under Operate is experimental. The technical version of this map, with repo evidence per statement, is in the handout."
Transition: "And the path a run takes."

**Slide 5: End-to-end workflow (1:45)**
Read the nine steps quickly, then stop on the orange ones. "Step 6: delivered is not indexed. HEC acknowledges a batch; that does not make it searchable. Step 8: the app reports indexed only when a separate search finds events with that run ID. Remember that when we watch the counters in a minute. The app talks to the engine through a Splunk REST handler called netspout_gateway, so everything stays inside Splunk Web."
Transition: "Let me show you the product."

## Block B: product tour (5 minutes)

**Slide 6: Command Center (1:15)**
"This is the app in Splunk Web. The perspective tabs are honest: NetOps is available, SecOps and Observability are partial, the rest are labeled planned. The strip shows the workflow. Telemetry trust separates native contract, Splunk contract and NetSpout schema, which is the provenance idea."
If asked about "Splunk observation NOT AVAILABLE": "That is the page before any run is observed. It fills in once we run something."

**Slide 7: Catalog (1:15)**
"The catalog is searchable by title, vendor, sourcetype or MITRE ID. Searching cloudtrail returns dashboards, scenarios and sourcetypes together, with the maturity label on each. 159 sourcetypes have a native engine, 143 have recorded-sample replay, 47 have no generator yet, and the app says so instead of inventing data."

**Slide 8: Scenario Explorer (1:15)**
"This is where we start the live demo. Search volumetric DDoS: one dashboard and one scenario, NF-SEC-06-DDOS, labeled Runnable and independently indexed. The counters up top are catalog entries, not a runnable count; each card is labeled."

**Slide 9: Declarative contracts (1:15)**
Say the lab label first. "This slide is from an isolated validation lab, not this demo." "A scenario contract is data: shared nodes, ordered phases, and streams that bind a formatter to a node. Every event is tagged with run, scenario, phase and parent event. Of the 224 contract scenarios, 10 are vendor-native, 30 mixed, 184 modeled. 224 of 224 were indexed in the lab and all 224 dashboards pass the Splunk parser and return data; 24 were rendered and 11 visually inspected."
Transition: "Now the real thing, live."

---

## Block C: live demo (8 minutes)

Open a browser (fresh profile or cleared site data so the Explorer shows no remembered run). Splunk is signed in as `admin`; the password is not shown here.

| # | Time | Action | Say | Expect |
|---|---|---|---|---|
| 1 | 0:00 | Open `http://localhost:18000/en-US/app/netspout/use_case_explorer` | "The Use Case Explorer." | Page renders; counters 372 and 365 |
| 2 | 0:30 | In the search box type `volumetric DDoS` | "One dashboard, one scenario." | "2 results: 1 dashboard, 1 scenario"; scenario `NetFlow: volumetric DDoS indicators (SYN flood and UDP)`, ID `NF-SEC-06-DDOS`, label RUNNABLE; dashboard `pf_NF-SEC-06-DDOS` DASHBOARD_VISUALLY_VERIFIED |
| 3 | 1:00 | Click **Open scenario workflow** on the scenario card | Read the preview: phases, volume, destination, limits. Do **not** read the banners aloud (see "Known UI inconsistency" below) | Phases `traffic (100) → syn-flood (560) → udp-flood (160)`; 820 events; destination `127.0.0.1:18088`, index `idx_network_ops`, sourcetype `netflow:collector`; relation label "NetFlow profile of SEC-P9-A-TRAFFIC-FLOOD" |
| 4 | 2:00 | Leave the defaults (scale 1, window 180 s, delivery EPS 50, Index `idx_network_ops`, IPFIX UDP export ticked) | "Defaults are fine. The IPFIX box also sends real flow packets to the collector; the monitor counts the HEC path." | |
| 5 | 2:30 | Click **Run scenario with live delivery monitor** | "Watch generated, accepted, and the last number, Indexed (verified)." | State RUNNING, then COMPLETED about 20 s later; Generated 820, Attempts 820, HEC accepted 820, Rejected 0, Pending 0; Indexed (verified) 820 (it can trail by seconds) |
| 6 | 3:30 | Point at the NetFlow stage rows | "UDP exported and collector decoded are reported separately; decoded can be a little under 100 percent from datagram loss, and the app says so." | Stage rows present; do not claim 100 percent decoded |
| 7 | 4:00 | Wait for readiness READY (button to open the dashboard enables) | "Readiness is another independent search keyed to this run ID." | READY; if INDEXING or PARTIALLY_READY, wait about 30 s |
| 8 | 4:30 | Open a new tab: `http://localhost:18000/en-US/app/search/search` and run the SPL in "Searches" below | "Here are the events themselves." | Table with `netspout_phase` traffic and syn-flood |
| 9 | 5:30 | Click **Open dashboard** (or open the URL below with your new run ID) | Walk the panels | See "Dashboard walk" below |
| 10 | 7:30 | Return to slide 14 or 15 | | |

### Known UI inconsistency (do not read the banners aloud)

The scenario preview shows both "Live Splunk evidence recorded for this scenario (counts verified independently)" and "Contract only: this scenario has not been validated end to end". They contradict each other, and the cause has not been investigated. If asked: "That is a known inconsistency in the released UI. The evidence is the reconciled counts and the search by run ID." Do not describe either banner as the validation status.

### Normal pre-run state

On the Command Center, "Splunk observation: NOT AVAILABLE" and "Detection evaluation: NOT CONFIGURED" are the normal state before any run is observed. They are not errors.

### Scenario facts

| Item | Value |
|---|---|
| Scenario ID | `NF-SEC-06-DDOS` |
| Scenario name | NetFlow: volumetric DDoS indicators (SYN flood and UDP) |
| Dashboard | `pf_NF-SEC-06-DDOS`, title "PulseForge · Volumetric DDoS indicators" |
| Index / sourcetype | `idx_network_ops` / `netflow:collector` |
| MITRE | T1498.001 |
| Total events | 820 per run (verified on seven runs) |
| Phase counts | traffic 100, syn-flood 560, udp-flood 160 (verified for `run-cfcfd30d23f8`) |

### Searches (read-only; set the time range to Last 7 days or Last 24 hours)

1. Which runs exist:
   `index=idx_network_ops sourcetype="netflow:collector" netspout_scenario_id="NF-SEC-06-DDOS" | stats count by netspout_run_id`
   Expect one row per run, 820 each.
2. The events of your run (replace the run ID with the one on screen; the prepared run is `run-cfcfd30d23f8`):
   `index=idx_network_ops sourcetype="netflow:collector" netspout_scenario_id="NF-SEC-06-DDOS" netspout_run_id="run-cfcfd30d23f8" | head 8 | table _time src dest dest_port transport tcp_flags_text packets bytes netspout_phase netspout_run_id`
   Expect traffic rows (PSH|ACK to 443, a UDP 53 row) and syn-flood rows (SYN to 192.0.2.80:443 from 203.0.113.x).
3. The phases:
   `index=idx_network_ops sourcetype="netflow:collector" netspout_run_id="run-cfcfd30d23f8" | stats count by netspout_phase`
   Expect syn-flood 560, traffic 100, udp-flood 160.
4. The target:
   `index=idx_network_ops sourcetype="netflow:collector" netspout_run_id="run-cfcfd30d23f8" tcp_flags_text=SYN | stats dc(src) as syn_sources count by dest | sort - count`
   Expect one destination, 192.0.2.80, 560 flows from 171 distinct sources.
5. Whole-run totals:
   `index=idx_network_ops sourcetype="netflow:collector" netspout_run_id="run-cfcfd30d23f8" | stats count dc(src) as sources dc(dest) as dests sum(packets) as packets`
   Expect 820 events, 258 sources, 22 destinations, 4,531 packets.

All five were run read-only against the demo Splunk on November 2, 2026 and returned the values above.

### Dashboard walk

URL pattern (replace the run ID if you use a new one):
`http://localhost:18000/en-US/app/netspout/pf_NF-SEC-06-DDOS?form.run_tok=run-cfcfd30d23f8&form.index_tok=idx_network_ops`

If you open the view by hand, set the **Index** input to `idx_network_ops` (it defaults to `dev_test_replay`) or every panel says "No search results returned".

| Order | Panel | What to say | Expect (for `run-cfcfd30d23f8`) |
|---|---|---|---|
| 1 | Header and question | "The page states its question and its limits." | Limits: synthetic flood patterns; flow data cannot show whether availability was lost |
| 2 | Packet rate (5 s buckets) | "Where does the rate peak?" | Several peaks; the peak value differs between runs, so describe the shape and quote no fixed number |
| 3 | KPI tiles | "Headline numbers." | Peak packets/s (varies, do not quote); Flows 820; SYN-only flows 68.3%; Distinct sources 258; Destinations receiving SYN-only flows 1 |
| 4 | TCP flags over time | "SYN grows as the flood builds." | SYN and PSH|ACK stacked bars, SYN rising |
| 5 | Packets by protocol | | Mostly tcp, a small udp slice |
| 6 | Targeted assets (packets) | "One asset takes the brunt." | 192.0.2.80 leads |
| 7 | Attack progression: distinct sources per 15 s | "Sources escalate, then drop." | Rising line, then a fall |
| 8 | Top sources by packets | "Click a source for flow evidence." | Top rows 198.51.100.52 (197 packets), .41 (174), .36 (150) |
| 9 | Data prerequisites | "It tells you what it needs and that the flows are synthetic (RFC 5737 documentation addresses)." | |

### Backup scenario and prepared runs (no live run needed)

| Need | Use |
|---|---|
| The live run fails or stalls | Slide 10 to 12, or open the dashboard URL above with `run-cfcfd30d23f8` (already indexed, 820 events) |
| A second NetFlow story | `pf_NF-SEC-07-PORTSCAN` with `form.run_tok=run-29ded2aa12c9` (262 events; ports versus hosts per source, T1046) |
| An operations story | `pf_NF-NOC-01-ELEPHANT` with `form.run_tok=run-b7052460b396` (224 events; which few flows carry the bytes) |

Add `&form.index_tok=idx_network_ops` to each URL. Prepared run IDs were read from the demo Splunk on November 2, 2026.

---

## Block D: evidence and close (3 minutes)

**Slide 13: NetFlow and metric visualization (1:00, skip if short on time)**
"Top: NetFlow events from this run. Bottom: gauge metrics. Those go to a metric index and are read with mstats. I am showing that from the validation lab, because this Splunk has no metrics index. I am not claiming it works here."

**Slide 14: Deployment, evidence, limits (1:30)**
"Released today: the Splunk app plus the engine tarball, verified end to end on Splunk Enterprise 10.2.7 in an isolated lab; a Docker evaluation stack whose Compose file validates but whose clean-checkout run has not been repeated; and netspout_cloud.spl, which is dashboards only. Splunk Cloud itself was not validated. A single-package installer exists as an experiment, validated once, not merged, not released."
"Evidence, kept separate: 148 scenarios validated in the released app. 224 new scenarios: 224 of 224 independently indexed in the lab with 4,994 events accepted and none rejected. 224 of 224 dashboards pass the parser and return data; 24 rendered, 11 visually inspected."
"Limits: 184 of the 224 are modeled, not vendor logs. 47 catalog sourcetypes have no generator. The new scenarios are on main, not installed here. Metric dashboards need a metric index."

**Slide 15: Close (0:30)**
"Pick it, run it, prove it in Splunk. I am happy to take questions, and I can go back into the Explorer or the dashboard."

---

## Expected questions

| Question | Answer |
|---|---|
| Is the telemetry real? | It depends on the scenario and the label. NetFlow here is synthetic, from RFC 5737 documentation addresses, and the dashboard says so. Native formats follow the protocol (NetFlow v9, IPFIX, SNMP v2c, gNMI). Modeled events use a labeled schema and are not vendor logs. |
| How do I know it reached Splunk? | The monitor shows HEC accepted, and a separate Splunk search by run ID produces the Indexed count. That second number is the proof. |
| Why does Indexed sometimes lag Accepted? | Indexing and search visibility trail the HEC acknowledgement by seconds. The monitor re-checks every 5 seconds. |
| How many scenarios can I run? | 372 are runnable on current main. In the released app in this demo, 148. The 224 new ones were validated in an isolated lab and are not installed here. |
| Are the 224 new scenarios vendor-authentic? | Ten are vendor-native, 30 mixed, 184 modeled. Modeled ones are labeled and are not product logs. |
| Does it work on Splunk Cloud? | Not validated. `netspout_cloud.spl` is dashboards only, and no Cloud HEC token was available for validation. A metrics-only proof against a Cloud test index was done separately and is evidence only (`docs/verification/evidence/metrics/remote_test_metrics_2026-11-02.json`). |
| Can I install it with one package? | Not in the release. A single-package installer is experimental, validated once on Splunk 10.6.1.1, and not merged. The released options are the app plus engine, or the Docker stack. |
| Does it send configuration to devices? | No. It is read-only and simulates state. gNMI and SNMP Set requests are rejected. Native listeners bind to 127.0.0.1 by default. |
| What about SNMPv3, OTLP, sFlow, NETCONF? | Deferred from the 1.0 release (`docs/LIMITATIONS.md`). |
| Can it prove the DDoS took a service down? | No. Flow data shows indicators (rate, flags, targets) and cannot show loss of availability. The dashboard says so. |
| Can I create my own scenario? | Declarative contracts make that data-driven on main; Scenario Studio is in the app. Do not demo it live. |
| Is it production-certified? | No. |

## Safe fallbacks

| Problem | Do this |
|---|---|
| The live run stalls | Press **Stop**, start a new run (new run ID). Or switch to the prepared run `run-cfcfd30d23f8`. `curl -s localhost:8091/api/runs` lists runs; none should stay RUNNING after Stop. |
| Indexed trails Accepted | Wait about 30 s. Cross-check with search 1 or 3 above. |
| Dashboard says "No search results returned" | Set the Index input to `idx_network_ops`; check the run token and the time range (24 h). |
| A panel is empty | Re-run, or use the prepared run. |
| Browser lost a status poll | Refresh; the run is server-side and unaffected. |
| Splunk Web unavailable | `docker ps` for `netspout_phase4e_splunk`; `tests/lab/phase4e/lab.sh up`; wait for `(healthy)`, port 18000. |
| "Search failed (404)" or gateway unreachable | The gateway reads `NETSPOUT_BACKEND_URL` from `splunk-launch.conf` inside the container; it must be `http://host.docker.internal:8091` on its own line. Restart splunkd afterwards. This is a repair, not a live step. |
| Engine not answering | `scripts/start_lab_engine.sh` (state is in `.lab_engine_cfg/`). Check `curl -s localhost:8091/api/health`. Only do this if the demo cannot proceed. |
| NetFlow stage shows COLLECTOR_UNREACHABLE | Untick **IPFIX UDP export** and run again; the HEC-delivered dashboard does not need the collector. |
| A splunk usage notice appears on first Search | Click **Got it!** once before the session; it is a one-time admin notice. |
| Everything is down | Present slides 10 to 13 as the recorded evidence (they carry the source and date in the notes) and say so. |

## Do not demo

- The 37 telecom and industry incident packs in this lab: they also emit gauge metrics, and this Splunk has no metrics index, so the run is refused ("Metric index is not authorized by Connection Center").
- Anything from the 224 contract scenarios (not installed here).
- Restarting, upgrading, rebuilding or reconfiguring the demo environment before or during the session.

## Pre-session checks (30 minutes before)

1. `docker ps --format '{{.Names}} {{.Status}}' | grep -E 'phase4e|netspout-flow'` shows Splunk healthy and the two flow containers up.
2. `curl -s localhost:8091/api/health` returns `"status":"healthy"`.
3. Open `http://localhost:18000/en-US/app/netspout/pulseforge_command_center` and sign in; click **Got it!** on any one-time Splunk notice.
4. Open the prepared dashboard URL with `run-cfcfd30d23f8` and confirm the panels are populated.
5. Clear site data for `localhost:18000` so the Explorer does not show a remembered run.
6. Dismiss the one-time Splunk product-usage notice: open Search once as `admin` and click **Got it!**; it otherwise covers the first search on stage.
7. Close other heavy processes; a click that records no response under load should be retried before it is called a failure.

## Credential rotation (record only; no values here)

Three credentials were pasted into working sessions during development and must be rotated before this material is shared more widely: the HEC token, the `socadmin` password, and the Splunk Cloud bearer token. The lab password and HEC token for the demo environment live only in the git-ignored `tests/lab/phase4e/.env.lab`. No secret appears in the deck, screenshots, diagrams, script or cheat sheet.
