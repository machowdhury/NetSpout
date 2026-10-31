# 07 Dashboard guide

## Families (138 Dashboard Studio views, one per scenario that emits indexed telemetry)
| Family | Views | Run key (token `run_tok`) | Metric panels |
|---|---|---|---|
| Replay packs (recorded and hybrid) | 33 | `netspout_replay_session` | no |
| Authentic native packs | 26 | `netspout_run_id` | no |
| Incident packs (network and telecom, modeled) | 37 | `netspout_run_id` | yes (`mstats`), plus sites, devices and syslog severity, which these events really carry |
| ScenarioRunner scenarios | 17 | `netspout_run_id` | only the 5 whose runs emit gauge datapoints |
| Unified-generation scenarios | 20 of 25 | `netspout_run_id` | no |
The 5 SEC-P9 unified scenarios that need the flow collector have no dashboard. SEC-P9-B DNS anomaly keeps its earlier verified view (`pulseforge_dns_anomaly_studio`) as the primary link; it also has a generated one.

## Tabs
Operational: **NOC / Engineer / Evidence**. Security: **Overview / Investigation / Evidence**. Shared inputs: time range, run (dropdown of runs found in the index), incident phase, index, and metric index where used. Every KPI, chart and table is a search over the scenario's own indexed events; nothing is hardcoded. Static text is limited to title, objective, provenance, detection prerequisites and links.

## Derived fields (why they exist)
`pf_phase` = `coalesce(netspout_pack_phase, netspout_phase)`. `pf_host` is the last value of `host` and `pf_st` the first value of `sourcetype`, because replayed JSON often carries its own `host`/`sourcetype` keys that Splunk extracts as extra values. The Windows add-on rewrites `XmlWinEventLog:<channel>` to `XmlWinEventLog` and `source` to the channel, so dashboards key on the indexed run fields, never on `source`.

## Design
Dark canvas `#17191b`, terracotta accent from the Figma V2 tokens in `design/` (lightened for contrast on dark), restrained status colors, KPI cards, bar/column/line charts with labeled axes. Dashboard Studio cannot load custom web fonts, so the IBM Plex Mono identifiers from the design are rendered with markdown code formatting; markdown links keep Splunk's link color (weak contrast on dark cards).

## Maturity (kept separate; stored as evidence)
`DASHBOARD_SPECIFIED` (template contract exists) < `DASHBOARD_IMPLEMENTED` (installed in Splunk and read back identical) < `DASHBOARD_DATA_VALIDATED` (every data source populated for the run, KPIs equal independent searches, tokens bound, drilldowns return rows) < `DASHBOARD_VISUALLY_VERIFIED` (also opened in Splunk Web with the run context, all three tabs rendered, and a human inspected the screenshot). Current: see `docs/verification/evidence/dashboards/dashboard_maturity.json` (138 data-validated except one recipe dashboard recorded as SPL_VALIDATED, 9 visually verified). The older `DASHBOARD_READY` gate is not claimed for any generated dashboard.

## Regenerate and revalidate
```bash
PYTHONPATH=src:backend .venv/bin/python scripts/build_scenario_dashboards.py          # writes netspout/default/data/ui/views/pf_*.xml and the nav
PYTHONPATH=src python3 scripts/validate_scenario_dashboards.py probe|install|validate|maturity [id1,id2|__runner__|__native__|__unified__]
cd frontend && SHOT=id1,id2 node ../scripts/render_scenario_dashboards.mjs [ids]      # real-browser render, screenshots only for SHOT ids
```
Validation runs against the isolated lab and needs its credentials file. Re-run only the families a change touches.

## Open a dashboard for a run
`/app/netspout/pf_<scenario id>?form.run_tok=<run id or replay session id>`; the Explorer's Dashboard step builds this link.
