# Phase 6 — simplified UI and honest capability status

Flow: **Vendor → Product → Sourcetype → Preview → Generate → Verify**. Simple mode (the default) has three places in its navigation: **Generate Data**, **Scenarios**, **Connections**. Advanced mode restores the full navigation, domain selector and all earlier tools (the previous Generator Modes page moved to *Generator Modes (legacy)*; the guided scenario lab is still what Advanced mode shows under Scenarios). Deep links to any page still open.

## Where status comes from
`catalog/capability_status.json` is built by `scripts/build_capability_status.py` from evidence only: `docs/contracts/phase5/master_matrix.json` (generator really produced events, offline format check against the add-on, conflicts), `docs/contracts/ta_live_results.json` (live Splunk verification, Phase 4) and `docs/reference/scenario_coverage.json`. Catalog tier labels are not an input. Served by `GET /api/compat/catalog` and `GET /api/compat/scenarios` (`netspout_core/capability.py`).

| UI status | Rule | Count |
|---|---|---|
| Verified in Splunk | passed live check against the add-on (Phase 4) | 4 |
| Checked offline only, not tested in Splunk | generator produces events and they satisfy the add-on's extraction rules offline | 13 |
| Can send data, not tested in Splunk | generator produces events; not (fully) checked against an add-on | 216 |
| Cannot send data | no generator (102), metric/event routing conflict (3), events do not match the add-on's extractions (11) | 116 |

Generation is **blocked** (UI control removed, `409` from `/api/runs` and `/api/generate/preview`, and the dispatcher itself refuses to send routing conflicts) for the three *Unsupported* causes. The routing conflicts are `cisco:thousandeyes:metric` and `cisco:intersight:metrics` (`vmware:perf:cpu` was a third until Phase 8, when real data and the add-on showed it is a TSV event and a generator for that format was added): they are neither sent as metric-index payloads nor converted into logs. A scenario is blocked when it needs one of them (6 of 372 scenarios, including 4 contract scenarios that emit `cisco:thousandeyes:metric`). Sources that only a scenario's own engine builds do not block a scenario.

## Preview
`POST /api/generate/preview` calls `prepare_sourcetype_entries` (the function a run uses) and the dispatcher's own HEC payload builder (`_dispatch_log(..., capture=)`), sending nothing. It shows the raw event, the exact sourcetype and the index. Values differ between runs. It states that it does not prove an add-on parses the data.

## Delivery and verification messages
Accepted by HEC is reported separately from found-by-search. The result panel auto-runs the independent search after delivery and says one of: verified (n of n found), accepted but only n searchable yet, accepted but this app could not confirm (with the reason), partly rejected, or not received (with the destination's error).

## Scenarios
The list shows *Can run, not fully tested in Splunk* (every source can be generated; at least one is untested in Splunk), *Verified in Splunk* (every source verified; currently no scenario) or *Cannot run* (with reasons). Investigation links to Dashboard Studio (`?dashboard=scenario-<id>&run=<run id>`).

## Phase 9 changes to this contract
- **Connections**: one **Test connection** control replaces the overlapping Validate and HEC connection test. It checks HEC and search, sends one marked test event and looks for it, and answers in one sentence: *Working*, *Partly working* (events can probably be sent but cannot be confirmed searchable) or *Not working*. The individual checks are behind "Show the individual checks". The form stays locked until the saved destination has loaded.
- **Status wording** (build_capability_status.py, UI): *Verified in Splunk*, *Checked offline only, not tested in Splunk*, *Can send data, not tested in Splunk*, *Cannot send data*; scenarios: *Verified in Splunk*, *Can run, not fully tested in Splunk*, *Cannot run*.
- **Result messages** (one component for Generate Data and Scenarios): *Verified* only when an independent search found the run's data: events in the event index, metric datapoints by an `mstats` search of the metric index (never an event-index search). After the retries a run that is accepted but not found says *Not confirmed* and why it may have happened; a search that cannot run says it could not check; neither is ever Verified.
- **Runs without an index** use the saved destination's first event index (the old fixed default is kept only where it is configured). A metric sourcetype run records its metric index and datapoints, so verification searches the right place.
- **Picker**: the Cisco families have readable names (Cisco ASA and Cloud Security, Cisco IOS, IOS-XE and IOS-XR, Cisco SD-WAN, ...); vendors with more than eight products get a search box; mode and rate are under "More options"; a failed preview disables Generate.
- **Scenarios**: "Why it cannot run" lists the exact reason per source; the Dashboard Studio link uses the real dashboard id (it was never shown before because the lookup read the wrong field).

## Remaining UX problems
- The Connections page is still the Connection Center form, now with one test control; the field layout was not redesigned.
- Dashboard Studio exists for only 29 scenarios; the other 343 show "no Dashboard Studio dashboard yet" (some have a native Splunk dashboard, which is not linked from the page).
- Scenario names and categories are catalog terms a new user may not know.
- Metric runs in "keep streaming" mode record the metric index but were not browser-tested.
