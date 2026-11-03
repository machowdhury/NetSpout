# Phase 6 — simplified UI and honest capability status

Flow: **Vendor → Product → Sourcetype → Preview → Generate → Verify**. Simple mode (the default) has three places in its navigation: **Generate Data**, **Scenarios**, **Connections**. Advanced mode restores the full navigation, domain selector and all earlier tools (the previous Generator Modes page moved to *Generator Modes (legacy)*; the guided scenario lab is still what Advanced mode shows under Scenarios). Deep links to any page still open.

## Where status comes from
`catalog/capability_status.json` is built by `scripts/build_capability_status.py` from evidence only: `docs/contracts/phase5/master_matrix.json` (generator really produced events, offline format check against the add-on, conflicts), `docs/contracts/ta_live_results.json` (live Splunk verification, Phase 4) and `docs/reference/scenario_coverage.json`. Catalog tier labels are not an input. Served by `GET /api/compat/catalog` and `GET /api/compat/scenarios` (`netspout_core/capability.py`).

| UI status | Rule | Count |
|---|---|---|
| Verified in Splunk | passed live check against the add-on (Phase 4) | 4 |
| Format checked, not live verified | generator produces events and they satisfy the add-on's extraction rules offline | 13 |
| Generator available, unverified | generator produces events; not (fully) checked against an add-on | 216 |
| Unsupported or incompatible | no generator (102), metric/event routing conflict (3), events do not match the add-on's extractions (11) | 116 |

Generation is **blocked** (UI control removed, `409` from `/api/runs` and `/api/generate/preview`, and the dispatcher itself refuses to send routing conflicts) for the three *Unsupported* causes. The three routing conflicts are `cisco:thousandeyes:metric`, `cisco:intersight:metrics`, `vmware:perf:cpu`: they are neither sent as metric-index payloads nor converted into logs. A scenario is blocked when it needs one of them (6 of 372 scenarios, including 4 contract scenarios that emit `cisco:thousandeyes:metric`). Sources that only a scenario's own engine builds do not block a scenario.

## Preview
`POST /api/generate/preview` calls `prepare_sourcetype_entries` (the function a run uses) and the dispatcher's own HEC payload builder (`_dispatch_log(..., capture=)`), sending nothing. It shows the raw event, the exact sourcetype and the index. Values differ between runs. It states that it does not prove an add-on parses the data.

## Delivery and verification messages
Accepted by HEC is reported separately from found-by-search. The result panel auto-runs the independent search after delivery and says one of: verified (n of n found), accepted but only n searchable yet, accepted but this app could not confirm (with the reason), partly rejected, or not received (with the destination's error).

## Scenarios
The list shows *Runnable, not verified in Splunk* (every source can be generated; at least one is untested in Splunk), *Verified in Splunk* (every source verified; currently no scenario) or *Cannot run* (with reasons). Investigation links to Dashboard Studio (`?dashboard=scenario-<id>&run=<run id>`).

## Remaining UX problems
- The Connections page is the legacy Connection Center form with restyled colours; its two test sections (Validate, Test connection) overlap and the section headings are plain.
- Vendor names repeat for Cisco families, so the picker shows the catalog vendor id next to the name.
- The product list is long for vendors where every sourcetype is its own product (for example SD-WAN: 41).
- Dashboard Studio exists for only 29 scenarios; the others show no investigation link.
- Scenario names, categories and the "verified" bar are catalog terms a new user may not know.
- The packaged Splunk app bundle (`netspout/appserver/static/dist`) was not rebuilt in this phase.
- Older Playwright specs that need a live Splunk or the previous navigation (`phase4*`) were not rerun; `unified-shell.spec.ts` was updated for the new navigation.
