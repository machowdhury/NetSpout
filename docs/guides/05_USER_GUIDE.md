# 05 User guide

## 1. Command Center
Open the app (`NetSpout PulseForge`) in Splunk Web. The Command Center shows the runtime evidence the engine currently reports (backend, Splunk observation, detection evaluation), the six perspectives (NetOps, SecOps, ITOps, Observability, Agentic AI, Supply Chain) and the shared flow **Choose, Run, Observe, Correlate, Investigate**. A state shown as `NOT AVAILABLE` or `NOT CONFIGURED` means no evidence exists yet; nothing is assumed.

## 2. Find a scenario (Use Case Explorer)
- Search by title, vendor, sourcetype or MITRE ID; filter by type (operational, security story), industry (18 approved industries) and "Demo-ready only".
- Cards show the maturity tier recorded for the scenario (CERTIFIED, VALIDATED, FORMAT_VALIDATED, CONTRACTED, CATALOGED). Industry tags marked `*` are editorial mappings, not customer-validated claims.
- Entries that cannot run show why (for example "Contract only: no executable telemetry"); they have no Run button.
- The full deduplicated list with requirements is in the [Scenario reference](../reference/SCENARIO_REFERENCE.md).

## 3. Configure the destination
All runs use the single destination saved in the Connection Center (HEC URL, search URL, allowed indexes). Choose an **index from that allowlist**; any other index is refused (HTTP 403). Replay defaults to index `dev_test_replay` and host `replayed-log-generator`; outside a lab destination the replay index must start with `dev_` and you must confirm the destination.

## 4. Run a scenario (Select, Configure, Generate or Replay, Ingest, Verify, Dashboard)
| Step | What happens | Success means |
|---|---|---|
| Configure | Preflight (or a replay preview showing original and timestamp-shifted records) | No data is sent yet |
| Generate / Replay | Native events are produced, or a replay session starts | A run id (native) or session id (replay) is shown |
| Ingest | HEC outcome counted per event | accepted equals generated, rejected 0, unknown 0 |
| Verify | An independent Splunk search counts events for the run | indexed equals accepted (it can trail briefly) |
| Dashboard | Opens the Studio dashboard with the run as context | Panels populate from that run |

Counts: **generated** (rendered), **delivered** (sent), **accepted** (HEC success), **rejected**, **unknown** (answer unreadable; never re-sent), and **indexed** (found by Splunk). Only `indexed` proves ingestion.

## 5. Replay packs and continuous replay
Replay packs combine authentic recordings and/or existing native packs on one timeline. Controls: mode **one-shot** or **continuous cycles**, **speed** (0.01 to 1000), optional **EPS limit**, **Pause / Resume / Stop**. The engine keeps source spacing, restarts each loop after a documented gap (median source spacing by default, at least 1 ms), never overlaps or regresses timestamps, and refuses sources that have no trustworthy timestamp. A full queue slows the producer; nothing is dropped. After an engine restart active sessions show `INTERRUPTED` and are not resumed.
Independent recordings in one pack are aligned in time only; they do not share identifiers.

## 6. Dashboards
Operational: tabs **NOC** (KPIs, timeline, phases, affected assets, recovery), **Engineer** (volume trends, before/during/after, metrics via `mstats` where the run has gauges, impact events) and **Evidence** (provenance, verification search, raw events). Security: **Overview** (KPIs, timeline, detection status, original analytic links), **Investigation** (hosts, progression, users when present, evidence events) and **Evidence**. Inputs: time range, run, phase, index (and metric index). Click a phase bar to filter; click table rows to open the supporting search. See [07](07_DASHBOARD_GUIDE.md).

## 7. Understanding detection status
Every security dashboard says **Detection status: NOT VERIFIED** and asserts no severity. Original analytic links appear only for detections whose published test data is a dataset the scenario replays. Running a detection needs the add-ons, CIM data models, macros and lookups named by that content ([08](08_SECURITY_TA_CIM_GUIDE.md)).

## 8. Failed runs
Check the Connection Center validation, the index allowlist, the HEC token's allowed indexes, and the engine pipeline health (`/api/health/pipelines`). `rejected > 0` means HEC refused events; `unknown > 0` means the answer was unreadable and nothing was resent. See [09](09_TROUBLESHOOTING.md).

## 9. Evidence you can keep
Every validation script writes JSON under `docs/verification/evidence/` (replay, dashboards, installed app, protocols, AppInspect). The Explorer shows only what that evidence supports.
