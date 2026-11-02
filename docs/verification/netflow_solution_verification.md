# NetFlow/IPFIX solution: verification record (2026-10-31)

Isolated Docker Splunk 10.2.7 lab (`netspout_tavalidation_splunk`), installed `netspout.spl` (app 2.0.0, splunkd restarted after install), engine on port 8091, GoFlow2 v2.2.5 + repo forwarder started from `deploy/collector` for the wire stage. No Splunk Cloud endpoint was contacted. Index used: `dev_test_replay` (the `netflow` index does not exist in the lab and was not created). Scripts and evidence under `docs/verification/evidence/netflow/`.

| Check | Script | Result |
|---|---|---|
| Generators and normalizer (determinism, bounds, semantics, 25 tests) | `tests/test_netflow_solution.py` | pass |
| Run-bound delivery: HEC accepted = independently indexed = generated, readiness READY, 10 scenarios + 1 run with sourcetype `cisco:ios:ipfix` | `scripts/validate_netflow_live.py` → `live_runs.json` | 11 of 11 pass (rejected 0, unknown 0) |
| Dashboard SPL: every data source and every drilldown executed with the dashboard's own token defaults on real indexed data | `scripts/validate_netflow_dashboards.py` → `dashboard_validation.json` | 10 of 10 pass |
| Rendered in Splunk Web (installed app), run bound, no error text | `scripts/render_netflow_live.mjs` → `browser_render.json`, `screens/` | 10 of 10 pass; all ten screenshots inspected (`visual_inspection.json`) |
| Search → configure → preview → run → monitor → READY → run-bound dashboard, each scenario starting from a clean browser state | `scripts/render_netflow_flow.mjs` → `browser_flow.json` | 10 of 10 pass |
| Wire round trip: IPFIX over UDP → GoFlow2 → decoded row → normalize equals source normalize | `scripts/validate_netflow_wire.py` → `wire_roundtrip.json` | every decoded record equals its source on all 18 compared fields (0 mismatches); see loss below |

## Wire path: what is and is not proven

* Proven: for every record the collector decoded, all compared fields (times, 5-tuple, protocol, TCP flags, ToS/DSCP, interfaces, ASNs, bytes, packets, duration, app) equal the generated record.
* **UDP loss: root cause found and fixed (2026-11-01).** Earlier runs decoded 82–100% of exported records, usually missing one or two datagrams (about 21 records each) from the first exporter. GoFlow2 logged `template error`: the collector ran `workers=2` on one socket, so a data datagram could reach the worker that had not received the exporter's template and was dropped. `deploy/collector/docker-compose.collector.yml` now starts both listeners with `?workers=1`. After the change, the wire round trip decoded **100% (0 mismatches) for all ten scenarios** and all 11 API runs reached `COLLECTOR_DECODED` (exported equals decoded). Slower pacing never helped because pacing was not the cause. The fix applies to collectors started from the repository's compose file; an externally managed GoFlow2 needs the same setting. UDP is still unreliable by nature: the run panel keeps exported and decoded separate and reports any gap, and no accepted or indexed count depends on the wire stage.
* The first scripted pass reported SEC-10 as failed because a parallel diagnostic export wrote extra rows into the same collector file (more decoded than exported). Rerun alone it passed (699 of 720 decoded, 0 field mismatches).

## Findings fixed during verification

* Dashboard KPI tiles showed the first numeric field (raw bytes) instead of the value: all KPI queries now return a single `v` field.
* `timechart` zero-padded a minutes-long run across the 24-hour default range; time series now use the data's own span.
* `proto` in GoFlow2 rows is a string (`TCP`); the CIM `transport` alias lowercases it instead of comparing to numbers.
* The first browser flow check silently reused the Explorer's remembered run for later scenarios; it now clears browser storage and asserts the configure heading, monitor title and dashboard view belong to the scenario.
* Bubble charts did not plot (values at zero); replaced with scatter charts.

## Limits that remain

* No CIM data-model validation, no detection verification; labels are synthetic truth and are not used by any dashboard query.
* Flow-only DNS and routing-loop dashboards are indicators with stated limits (no query names, no TTL).
* `cisco:ios:ipfix` is selectable per run but is not a catalog sourcetype.
* No Classic Simple XML versions were produced.

## Final acceptance in the `netspout_phase4e_splunk` lab (2026-11-01)

Splunk Enterprise 10.2.x container, Web 18000, management 18191, HEC 18088, installed from the final `netspout.spl`, splunkd restarted, engine on 8091 (never 8081), index `idx_network_ops` (no `dev_test_replay`, no `netflow`; nothing was created).

| Check | Result |
|---|---|
| Ten scenarios + one `cisco:ios:ipfix` run via `/api/runs` | 11 of 11: generated = HEC accepted = independently indexed, rejected 0, unknown 0, readiness READY, IPFIX wire `COLLECTOR_DECODED` with exported = decoded (`live_runs.json`) |
| Wire round trip | 10 of 10 at 100% decoded, 0 field mismatches (`wire_roundtrip.json`) after the GoFlow2 `workers=1` fix |
| Dashboard data sources and drilldowns on this lab's index | 10 of 10 return rows (`dashboard_validation.json`) |
| Dashboards rendered in Splunk Web with run and index bound, empty-panel check | 10 of 10, 0 "No search results returned" panels (`browser_render.json`); screenshots re-captured, 3 inspected again (NOC-01, NOC-04, SEC-07), the other 7 inspected in the first pass |
| Browser flow: search → configure → preview → run → monitor → READY → run-bound dashboard, clean browser state | 10 of 10 (SEC-06 timed out once waiting for the wire table, passed on rerun alone; `browser_flow.json` records both) |
| Search, continuous stream, pause/resume/stop, refresh reattach, scenario run, readiness toast, run-bound dashboard | pass (`evidence/search/browser.json`), 0 orphan runs |
| Native (`barracuda:waf:web_firewall`) and recorded-sample (`arista:eos:syslog`) sourcetypes: finite (40), timed (6 s) and continuous with pause (counters held) / resume / stop | all runs: accepted = indexed (continuous: 89 accepted, 89 indexed after stop), rejected 0, unknown 0; no run left active |
| External HEC connection test | 8 of 8 cases as expected; no token or password in evidence |
| Native collector (GoFlow2 + forwarder) | forwarder HEALTHY, 46,313 of 46,315 flows forwarded to this lab's HEC with bounded retry |

### Defects found and fixed in this pass

* **Dashboards ignored the run's index.** Every Studio view defaults its Index input to `dev_test_replay`; the run-bound link carried only the run id, so in a lab without that index every panel was empty. The first browser pass reported PASS because the empty-panel check looked for the wrong text ("No results found" instead of Splunk Web's "No search results returned"). Fixed: the readiness handoff and the Explorer link now carry `form.index_tok` (and `form.mindex_tok` for metric runs), both checks now count the real empty-state text and fail on it, and all browser checks were rerun. Anyone opening a dashboard by hand still sees the `dev_test_replay` default and must set the Index input.
* **UDP loss** (see above): GoFlow2 `workers=2` template race.
* **Gateway backend URL.** The app's gateway defaults to `http://host.docker.internal:8081`; a lab whose engine is on another port needs `NETSPOUT_BACKEND_URL` in `splunk-launch.conf` (set for this lab to 8091).
* **Dashboard count reconciliation.** The 147 vs 148 difference was SEC-P9-B: the Explorer's primary link for it was the older recipe view `pulseforge_dns_anomaly_studio` (SPL-validated only) while its `pf_SEC-P9-B-DNS-ANOMALY` view was already data-validated. The pf view is now primary and the recipe view is kept as `alternate_view`. All 148 `pf_` views have data-validated evidence; 20 are visually verified.
