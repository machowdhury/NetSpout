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
* **Not complete delivery.** In the Docker Desktop lab the collector decoded between roughly 82% and 100% of exported records per run (most losses were about one datagram, about 21 records). In the final API runs 5 of 11 runs were fully decoded and 6 were `PARTIAL` (for example 224 exported, 203 decoded). The cause was not isolated; slower pacing (50 datagrams/s) did not remove it. The run panel shows exported versus decoded as measured and the HEC path is independent, so no indexed or accepted count depends on it.
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
