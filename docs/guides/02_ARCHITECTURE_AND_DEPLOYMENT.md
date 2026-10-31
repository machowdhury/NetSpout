# 02 Architecture and deployment

```text
 Splunk Web (user session, RBAC)                       Customer-hosted engine (Python/FastAPI)
 +--------------------------------------+   REST        +-------------------------------------------+
 | PulseForge app                       |  (splunkd)    | Telemetry generation  | Replay engine     |
 |  nav, React UI (appserver/static)    | ------------> | Scenario packs / ScenarioRunner / unified |
 |  Dashboard Studio views (pf_*)       | netspout_     | Protocol adapters: syslog, SNMP, gNMI,    |
 |  gateway REST handler (stdlib only)  | gateway       |   NetFlow v9 / IPFIX, OTLP                |
 +--------------------------------------+               | Connection Center (destination, indexes)  |
        ^   dashboards read indexed data                +--------------------+----------------------+
        |                                                                    | HEC / native protocols
        |                         Splunk indexers  <--------------------------+  (events, metrics)
        +-- searches (mstats / SPL) ------------------------------------------+
                                  ^ independent verification: authenticated search, never sender counters
```

## Components
| Component | Where | Notes |
|---|---|---|
| Splunk app `netspout` | Splunk | `netspout.spl`: nav, views, static UI, gateway handler, catalogs, recorded samples |
| Gateway | Splunk (persistent REST handler) | Forwards authenticated Splunk calls to the engine; non-GET needs a Splunk write role (`admin`, `sc_admin`, `power`); standard library only |
| Engine | Customer host or container | `backend/app` (FastAPI); canonical code in `src/netspout_core`, mirrored by `scripts/sync_core.py` |
| Replay engine | Engine | `sample_replay`, `replay_service`, `replay_packs`; sessions persisted for restart safety |
| Dashboard generator | Build time | `scripts/build_scenario_dashboards.py` writes the `pf_*` views |
| Connection Center | Engine | One saved destination (HEC URL, search URL, allowed indexes); credentials from environment |
| Native collectors | Customer side | GoFlow2 for flow, gnmic for gNMI, Net-SNMP tools for SNMP (used for verification) |

## Data flow and indexing
Events go to an event index through HEC; gauge metrics go to a metric index (`mstats`). Native protocols reach their own collector first. Verification searches key on indexed fields carried by every event (`netspout_replay_session`, `netspout_run_id`, `netspout_scenario_id`, `netspout_phase`) because add-ons can rewrite `source` and `sourcetype` (the Windows add-on does).

## Deployment models
| Model | Status |
|---|---|
| **A. Docker-hosted Splunk Enterprise** | Installed and tested (isolated lab, Splunk 10.2.7): [03](03_INSTALLATION.md), evidence `docs/verification/evidence/installed_app/` |
| **B. Splunk Enterprise on a VM or server** | Same package and procedure; the gateway defaults to `127.0.0.1:8081`. **Not tested on a VM** (no authorized VM available) |
| **C. Splunk Cloud** | Dashboards-only **Cloud edition** (`netspout_cloud.spl`) passes AppInspect cloud rules with 0 failures; the engine must stay outside Splunk. **User validation pending** ([04](04_SPLUNK_CLOUD_GUIDE.md)) |

Docker is a way to host Splunk or the engine, not a dependency of the app: nothing in `netspout.spl` calls Docker (the gateway only picks `host.docker.internal` as its default when it detects a container).
