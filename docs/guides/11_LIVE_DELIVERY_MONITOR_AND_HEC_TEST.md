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
