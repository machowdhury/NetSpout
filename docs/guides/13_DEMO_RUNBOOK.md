# 13 Demo runbook (Nov 3, 2026, 9 AM ET)

One page for the live demo against the isolated Docker lab. No credentials appear here: the lab password and HEC token live only in the git-ignored `tests/lab/phase4e/.env.lab`, and the engine reads them from there (`scripts/start_lab_engine.sh`). Never use port 8081 (another engine may own it); this runbook uses 8091.

Lab: Splunk Web <http://localhost:18000>, management 18191, HEC 18088 (container `netspout_phase4e_splunk`). Sign in as `admin` with the password from `.env.lab`.

## Pre-demo (about 10 minutes, the day before and 1 hour before)

| # | Check | Command / action | Pass |
|---|---|---|---|
| 1 | Docker Splunk is up | `docker ps --format '{{.Names}} {{.Status}}' \| grep phase4e` (start: `tests/lab/phase4e/lab.sh up`) | `Up … (healthy)` |
| 2 | App installed from the final package | Apps > Manage Apps > Install app from file > `netspout.spl` (check "Upgrade app") | version 2.0.0 listed |
| 3 | **Restart splunkd** after any install | Settings > Server controls > Restart; wait about 35 s after it is back | stale-UI problem avoided |
| 4 | Engine running on 8091 | `scripts/start_lab_engine.sh` (needs `.venv`, see README); then `curl -s localhost:8091/api/health` | `"status":"healthy"` |
| 5 | HEC destination | In the app: Connection Center > **Test HEC connection** | success, index allowed |
| 6 | Index exists | the lab uses `idx_network_ops` (Settings > Indexes). PulseForge does not create indexes | listed |
| 7 | Splunk Web reachable | open <http://localhost:18000/en-US/app/netspout/pulseforge_command_center> | page renders |
| 8 | (Optional) native flow collector | `SPLUNK_HEC_URL=https://host.docker.internal:18088/services/collector/event SPLUNK_HEC_TOKEN=… SPLUNK_HEC_ALLOW_INSECURE_TLS=true docker compose -p pf-lab-flow -f deploy/collector/docker-compose.collector.yml up -d` (token from `.env.lab`, not typed into shared terminals) | 3 containers healthy |

Run the browser flow once beforehand: `cd frontend && LAB_ENV_DIR=tests/lab/phase4e node ../scripts/render_netflow_flow.mjs NF-SEC-06-DDOS`. The Explorer remembers the last run in browser storage; use a fresh profile or clear site data so the first screen is clean.

## Live demo

1. **Command Center** — open the app; it shows only evidence the engine reports.
2. **Search a sourcetype** — Use Case Explorer, type `cloudtrail`; note `Stream this sourcetype`.
3. **Start continuous streaming** — index `idx_network_ops`, EPS 5, **Continuous (until stopped)**, Start Streaming.
4. **Pause, Resume, Stop** — the monitor counters hold, continue, end. Refresh the browser mid-run to show it reattaches.
5. **Independent indexing** — press Verify: *indexed* equals *accepted* (it can trail by seconds). Only *indexed* is proof.
6. **Search a scenario** — type `NF-SEC-06` or `volumetric DDoS`. Point out the relation label ("NetFlow profile of SEC-P9-A-TRAFFIC-FLOOD").
7. **Preview and execute** — open it, read the preview and limits, accept defaults (scale 1, 180 s, EPS 50, wire on), press **Run scenario with live delivery monitor**.
8. **Live Delivery Monitor** — generated → accepted → indexed; the NetFlow stage table shows *UDP exported* and *collector decoded* separately (decoded can be below 100% from UDP datagram loss; say so).
9. **Wait for READY** — readiness is from an independent search keyed to the run id.
10. **Open the dashboard** — the button opens `pf_NF-SEC-06-DDOS` with the run bound (`form.run_tok`).
11. **NetFlow investigation** — security: `pf_NF-SEC-07-PORTSCAN` (ports vs hosts per source, T1046) or `pf_NF-SEC-09-BEACON` (interval regularity). Operations: `pf_NF-NOC-01-ELEPHANT` (which few flows carry the bytes). Say what flow data cannot show (see limits below).

Dashboard URL pattern: `http://localhost:18000/en-US/app/netspout/pf_<SCENARIO_ID>?form.run_tok=<run id>`.

## What not to claim

- Flow data has no TTL (NOC-03 shows loop *indicators* only), cannot separate routing asymmetry from sampling/coverage (NOC-04), says nothing about latency (NOC-05), shows volume not theft (SEC-08), regularity not malice (SEC-09), and no DNS query names (SEC-10).
- HEC acceptance and indexing do not prove the IPFIX UDP stage; that stage is reported on its own line.
- The product is not production-certified and Splunk Cloud was not validated (no Cloud HEC token was available; `netspout_cloud.spl` is dashboards only).

## Backup plan

| Problem | Do this |
|---|---|
| A live run stalls | Press **Stop**, start a new run (new run id). `curl -s localhost:8091/api/runs` lists runs; none should stay `RUNNING` after Stop. |
| Indexing is delayed | Readiness shows `INDEXING`/`PARTIALLY_READY`; wait about 30 s (it re-checks every 5 s, 60 times). Cross-check: `index=idx_network_ops netspout_run_id=<id> \| stats count`. |
| The browser lost a status poll | The monitor retries and reattaches; refresh the page. The run is server-side and unaffected. |
| Splunk Web shows stale frontend assets | Restart splunkd, wait about 35 s, hard-refresh. |
| Native collector unavailable | Demo with wire off (untick **IPFIX UDP export**): the HEC-delivered normalized events and all ten dashboards work without the collector. |
| Engine not answering | `scripts/start_lab_engine.sh` again; state is in `.lab_engine_cfg/`. |
| A dashboard panel is empty | Check the run token and time range (default 24 h); re-run the scenario; the panel SQL is validated in `docs/verification/evidence/netflow/dashboard_validation.json`. |

Evidence: [NetFlow verification](../verification/netflow_solution_verification.md), [Live monitor and HEC test](11_LIVE_DELIVERY_MONITOR_AND_HEC_TEST.md), [Limitations](10_LIMITATIONS_AND_STATUS.md).
