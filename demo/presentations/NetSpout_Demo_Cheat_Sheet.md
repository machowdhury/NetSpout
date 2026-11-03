# NetSpout PulseForge demo cheat sheet

Nov 3, 2026, 9:00 AM ET · 23 min + Q&A · no credentials here (lab password and HEC token live only in git-ignored `tests/lab/phase4e/.env.lab`)

## Say it straight
- Demo = **released app**, **148** scenarios runnable here. **372** runnable on main; the other **224** are lab-validated, **not installed here**.
- **184 of 224 are modeled** (labeled `netspout:scenario:state`), not vendor logs. 47 catalog sourcetypes have no generator.
- **Indexed = an independent search by run ID found it.** HEC accepted is not proof.
- Single-package installer = **experimental, not released**. Splunk Cloud **not validated**. Metric (mstats) views = **lab only**; this Splunk has no metrics index.
- Flow data shows indicators; it cannot prove an outage.

## Slides (talking point · minutes)
| # | Slide | Point | Min |
|---|---|---|---|
| 1 | Title | Pick it, run it, prove it in Splunk | 0:45 |
| 2 | Problem | Rare incidents, content needs shape, no provenance | 1:15 |
| 3 | Enables | Choose, Run, Observe, Investigate; 349 sourcetypes, 88 vendors, 372 vs 148 | 1:15 |
| 4 | Mind map | Seven branches; installer is experimental | 1:30 |
| 5 | Workflow | Delivered is not indexed; indexed = search by run ID | 1:45 |
| 6 | Command Center | Honest perspectives, telemetry trust | 1:15 |
| 7 | Catalog | 159 native, 143 replay, 47 none | 1:15 |
| 8 | Explorer | NF-SEC-06-DDOS is runnable | 1:15 |
| 9 | Contracts (LAB) | 10 vendor-native, 30 mixed, 184 modeled | 1:15 |
| 10-13 | Live demo / fallback slides | Run, search, dashboard, metrics (LAB) | 8:00 |
| 14 | Deploy, evidence, limits | Released vs experimental; evidence kept separate | 1:30 |
| 15 | Close | Questions | 0:30 |

## Live demo
- **URL:** `http://localhost:18000/en-US/app/netspout/use_case_explorer` (sign in as `admin`)
- **Scenario:** `NF-SEC-06-DDOS` "NetFlow: volumetric DDoS indicators (SYN flood and UDP)"
- **Steps:** search `volumetric DDoS` → **Open scenario workflow** → keep defaults (scale 1, 180 s, EPS 50, index `idx_network_ops`) → **Run scenario with live delivery monitor** → wait Indexed (verified) → Splunk Search → **Open dashboard**
- **Expect:** phases traffic 100 → syn-flood 560 → udp-flood 160 = **820**; Generated 820, HEC accepted 820, Rejected 0, Indexed 820 (~20 s; can trail by seconds)

## Searches (index `idx_network_ops`, last 24 h or 7 d)
```
index=idx_network_ops sourcetype="netflow:collector" netspout_scenario_id="NF-SEC-06-DDOS" | stats count by netspout_run_id
index=idx_network_ops sourcetype="netflow:collector" netspout_run_id="<RUN>" | stats count by netspout_phase
index=idx_network_ops sourcetype="netflow:collector" netspout_run_id="<RUN>" tcp_flags_text=SYN | stats dc(src) as syn_sources count by dest | sort - count
```
Expect 820 per run; syn-flood 560 / traffic 100 / udp-flood 160; one target **192.0.2.80**, 560 flows, 171 sources.

## Dashboard
`pf_NF-SEC-06-DDOS` · `http://localhost:18000/en-US/app/netspout/pf_NF-SEC-06-DDOS?form.run_tok=<RUN>&form.index_tok=idx_network_ops`
Expect: Flows **820** · SYN-only **68.3%** · Distinct sources **258** · SYN-only destinations **1** · peak packets/s ~60-90 (varies) · 192.0.2.80 leads targeted assets · sources climb then drop · top source 198.51.100.52.
Panel empty / "No search results"? Set **Index** to `idx_network_ops`.

## Prepared runs and backup (already indexed, no live run needed)
- **Prepared:** `run-cfcfd30d23f8` (NF-SEC-06-DDOS, 820 events, Nov 2)
- **Backup scenario:** `pf_NF-SEC-07-PORTSCAN`, `run-29ded2aa12c9` (262 events)
- **Ops story:** `pf_NF-NOC-01-ELEPHANT`, `run-b7052460b396` (224 events)

## Recovery
| Problem | Fix |
|---|---|
| Run stalls | **Stop**, start a new run; or use `run-cfcfd30d23f8` |
| Indexed trails Accepted | Wait ~30 s; cross-check search 2 |
| Browser lost a poll | Refresh; the run is server-side |
| COLLECTOR_UNREACHABLE | Untick **IPFIX UDP export**, re-run |
| Search 404 / gateway unreachable | `NETSPOUT_BACKEND_URL` must be `http://host.docker.internal:8091` (repair, not live) |
| Engine silent | `curl -s localhost:8091/api/health`; `scripts/start_lab_engine.sh` only if needed |
| Splunk down | `docker ps`; `tests/lab/phase4e/lab.sh up`; wait `(healthy)` |
| Everything down | Present slides 10-13 as dated evidence and say so |

## Never
Demo the 37 telecom/industry packs (no metrics index) · show any of the 224 as installed · restart or reconfigure the demo environment · claim Splunk Cloud, production certification or a released single-package installer.
