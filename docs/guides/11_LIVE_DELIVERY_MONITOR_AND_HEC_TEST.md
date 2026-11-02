# 11 Live Delivery Monitor and External HEC Connection Test

## Live Delivery Monitor
Every run that delivers events shows the same monitor, backed by counters incremented where the event is delivered (never estimated from the requested count).

Where to open it
- **Use Case Explorer, any scenario**: replay packs show it as soon as Generate/Replay starts; every other engine has a **Run with live delivery monitor** button.
- **Quick Generate / Scenarios** (the generation lab): the monitor appears under the run metadata once the run is created.
- A browser refresh re-attaches to the same run (the run id is kept for the browser tab). After an engine restart, a run that was active is shown as `INTERRUPTED` with the counters it last persisted; it is never resumed or re-sent.

Counters (all exact)
| Counter | Meaning |
|---|---|
| Generated | Events built and ready to deliver. For runners that own the loop it is the number of events that reached the delivery boundary so far |
| Attempts | Events handed to the transport |
| HEC accepted | Splunk's own acknowledgement (HEC code 0). **It is not proof of indexing** |
| Rejected | HEC refused the event, or the send failed (the reason is listed under recent errors, tokens scrubbed) |
| Unknown | The answer could not be read; the event is **never re-sent** |
| Pending | Generated minus attempts |
| Indexed (verified) | Shows `Not verified` until you press **Verify in Splunk**. Then it is the count found by an independent Splunk search for this run (`netspout_run_id` or `netspout_replay_session`); metric datapoints are counted with `mstats` and compared with the datapoints of the accepted metric events |

Also shown: state, destination and index, run id, current and average events per second, elapsed time, ETA and percent for finite runs (an indeterminate bar for continuous runs and for runners that do not know their total), per-sourcetype and per-phase tables, a throughput chart, and recent errors.

Controls by family
| Family | Pause / Resume / Stop |
|---|---|
| Replay packs, native packs, incident packs, single-sourcetype batches | Supported (pause holds delivery; stop discards unsent events and reports them as pending) |
| ScenarioRunner scenarios, unified-generation scenarios (including the flow-based SEC-P9 scenarios) | **Not supported**: the runner executes synchronously inside the engine. The monitor says so and the buttons stay disabled. Counters are read at the delivery boundary (the dispatcher), so they are real |

Honest limits: events a runner sends over a native non-HEC transport (UDP flow export, SNMP, gNMI) are not HEC deliveries and are not counted by the HEC counters. Flow scenarios are proven by the collector's own counters and by the indexed decoded flows (see the flow evidence). A run is `COMPLETED` only when its worker finished; `STOPPED` when you stopped it; `FAILED` with the error shown.

## External HEC Connection Test (Connection Center)
Connection Center, section **HEC connection test**. Name the test index explicitly; it must be on the allowlist you saved. The test uses the **saved destination only** (a caller cannot supply a URL, token or search endpoint) and sends at most one synthetic event (`sourcetype netspout:connection_test`, marked with a unique test id).

| Status | Values | Meaning |
|---|---|---|
| connection | REACHABLE / FAILED | DNS, TCP and TLS, plus the HEC health endpoint |
| authentication | AUTHENTICATED / FAILED | The token is accepted by HEC |
| acceptance | ACCEPTED / REJECTED / UNKNOWN | HEC acknowledged the event |
| indexing | VERIFIED / NOT_FOUND / SEARCH_FAILED / NOT_CONFIGURED | An independent search found the event in the test index |

Overall: `FULLY_VERIFIED` only when all four hold. `ACCEPTED_NOT_VERIFIED` is shown when HEC accepted the event but indexing was not confirmed (no search credentials, search failed, or the event was not found). Reachability or acceptance alone is never reported as verified. Errors name their category: `DNS`, `REFUSED`/timeout, `TLS_CERTIFICATE`, `AUTH`, `INDEX_NOT_ALLOWED`, HEC code errors, search errors. Timeouts and retries are bounded; the event itself is never re-sent. Tokens and passwords are scrubbed from every message.

Splunk Cloud: set the HEC URL to `https://http-inputs-<stack>.splunkcloud.com/services/collector` (Enterprise-style stacks use `https://<host>:8088/services/collector`), keep TLS verification on (`allow_insecure_tls` is refused outside the loopback lab), and supply the token and search credentials through the engine environment (`NETSPOUT_HEC_TOKEN`, `NETSPOUT_SPLUNK_PASSWORD` or `NETSPOUT_SPLUNK_TOKEN`), never in files. Cloud HEC tokens are scoped to indexes: a token with no access to the test index produces a rejection, and an unknown index can be accepted and still never found, which is why indexing is a separate status.
Splunk Cloud testing is yours to run; see the checklist in [04](04_SPLUNK_CLOUD_GUIDE.md).

## Engine deployment and restart
See [03](03_INSTALLATION.md) section C (`pulseforge-engine.tar.gz`, launcher, systemd and launchd units). After a restart the engine rebuilds its in-memory destination from the saved Connection Center configuration (the token comes from the environment) and reports active runs and replay sessions as `INTERRUPTED`.

## Universal search

The Use Case Explorer starts with one search box over sourcetypes (349), scenarios (737 searchable Explorer entries, which include the 372 deduplicated scenario definitions plus replay, native and incident packs) and installed dashboards (148). Statuses are copied from the registries: catalog-only scenarios and sourcetypes without a generator stay in the results, labelled "catalog only", and are never offered as runnable. Filters cover type, runnable/catalog-only and dashboard availability; the API (`GET /api/search`) also filters by vendor, protocol, category, industry, execution mode, maturity and independently-indexed. The query is kept for the browser session. Dashboards open in Splunk Web; scenarios open the existing workflow and monitor.

Sourcetype results that PulseForge can stream authentically show **Stream this sourcetype**. A sourcetype is streamable only when `generator_service.prepare_sourcetype_entries` can ground it: 77 have a native event generator and 182 replay authentic recorded samples; the other 90 stay searchable as catalog-only because no authentic format or verified sample exists. (This counts streaming capability for one sourcetype; it is not the independently-indexed count.)

## Continuous single-sourcetype streaming

Choose one sourcetype, an index and an EPS (0.1 to 2000), then pick **Continuous (until stopped)**, **Finite: event count** or **Finite: duration**, and press **Start Streaming**. The run is a server-side thread on the engine with its own run id, so it keeps streaming with the browser closed and the monitor reattaches after a refresh. Events are generated just before each send, so each carries a current timestamp. Pause holds the counters, Resume continues, Stop ends the run; a stopped run leaves no thread behind. The engine allows four active runs at once. Backpressure: a failing destination makes the stream back off (up to 5 s between events) and after 50 rejected events in a row the run ends as FAILED with the reason, instead of hammering the destination. `GET /api/runs/{id}` shows `mode: continuous`, `progress.pct: null` (no total) and `source_mode` (`native` or `grounded_sample`).

## Scenario preview, readiness and the run-bound dashboard

Selecting a scenario opens its workflow with a preview (`GET /api/explorer/entries/{id}/preview`): telemetry, phases and event/metric volume where the pack defines them, destination and index, the dashboard view, and an estimated duration only when planned events and EPS are both known. Scenarios whose volume is decided at run time say so. Catalog-only scenarios show their exact blocker and no Run button.

After a run ends the monitor calls `POST /api/runs/{id}/readiness` about every 5 s (at most 60 times). States: `GENERATING`, `DELIVERING`, `INDEXING`, `PARTIALLY_READY`, `READY`, `DEGRADED`, `FAILED`, `UNKNOWN`, plus `NOT_STARTED` for an unknown id. READY requires an independent search keyed by this run id to find the indexed events, every sourcetype and phase the run delivered with acceptance, and the metric datapoints; unrelated data in the index never counts, and any rejected or unknown events make it DEGRADED. If evidence is still missing 180 s after delivery ended the state becomes DEGRADED and names what is missing. No ETA is shown because none is measured. READY shows a notification with the scenario, run id, indexed counts, elapsed time, **Open dashboard** (run id and a time window passed as `form.run_tok` and `form.global_time.*`) and **View evidence**.

## Dashboard design audit

`scripts/audit_dashboards.py` reads the installed views' JSON (`evidence/dashboards/design_audit.json`). Before this change all 138 shared six visualization types and five panel signatures. The 37 incident-pack dashboards gained a **Metric impact** tab (per-metric scorecard against its own baseline, metric shapes scaled to their own range on one axis, phase-by-phase narrative). A first version with device bubbles, role donut and severity area was removed: incident packs carry 30 events, 3 devices and one site over a few seconds, so those charts were misleading. The other 101 dashboards are unchanged and remain template-based; they are the remaining repetition.
