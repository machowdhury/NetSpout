# Phase 4F: Demo readiness, live verification (sanitized)

Lab: `netspout_phase4e_splunk`, Splunk Enterprise 10.2.7 (Docker, loopback), app `netspout` 2.0.0 installed from the `netspout.spl` built from this branch.
Backend: FastAPI on the host, reached **only through Splunk** (see 2). Credentials live in the git-ignored `tests/lab/phase4e/.env.lab`
and are never written to this repository. Evidence files: `docs/verification/evidence/phase4f/`.

## 1. Splunk navigation

| Entry | URL (lab) |
|---|---|
| PulseForge Command Center (app default) | `http://127.0.0.1:18000/en-US/app/netspout/pulseforge_command_center` |
| Use Case Explorer | `http://127.0.0.1:18000/en-US/app/netspout/use_case_explorer` |
| Operational dashboard (Dashboard Studio v2) | `http://127.0.0.1:18000/en-US/app/netspout/pulseforge_dns_anomaly_studio` |
| Canvas Orchestrator, Security Content Lab and the rest | unchanged |

The existing nav is preserved. The views reuse `netspout_canvas.js`, which selects the React route from the view name.

## 2. Same-origin API routing, authentication and authorization

* The React app (served from Splunk static assets) calls `/<locale>/splunkd/__raw/services/netspout_gateway/api/...` on the Splunk origin.
  A persistent REST handler (`bin/netspout_gateway.py`, stdlib only) forwards to the backend server-side. The browser never contacts `:8081`
  (spec asserts zero requests to that port).
* Splunk authenticates the session (`requireAuthentication`). The handler allows GET `/api/*` and `/health` only; **POST requires a Splunk
  `admin`, `sc_admin` or `power` role**, checked against splunkd; an unknown role fails closed (403). Verified with a stock `user`-role account:
  read 200, write 403 (`phase4f-splunk-web.spec.ts`; the probe account is deleted afterwards).
* Destination configuration lives in the backend Connection Center (secrets in memory only, never serialized to the browser: the setup
  response was asserted not to contain `search_secret`/`hec_token`). Page reloads and navigation between the three views keep the Splunk
  session and the configured destination (`configured: true` after reload). **A backend restart clears the in-memory secrets by design;
  re-enter the destination before the demo** (see section 8).
* Backend location: `NETSPOUT_BACKEND_URL`, defaulting to `http://host.docker.internal:8081` inside Docker and `http://127.0.0.1:8081` otherwise.

## 3. Operational dashboard (Dashboard Studio)

`pulseforge_dns_anomaly_studio` ships in the app as a version-2 Dashboard Studio view: 6 KPIs, ingest-volume column chart over the scenario clock,
phase summary table, hourly cross-run area trend, top-clients table and an incident timeline table; inputs for time range, scenario run, phase
and client. Every panel is a real SPL search over `idx_network_ops` (`netspout:dns:wire`, scenario `SEC-P9-B-DNS-ANOMALY`); there is no static or synthetic data
(guarded by `tests/test_phase4f_splunk_app_surface.py`, which also runs the product's Dashboard Studio export validator).

Rehearsal run `f7df21e1-c966-4410-9d10-d2536c71f0e9`: dashboard KPIs equal an independent splunkd search of that run
(queries 9, NXDOMAIN 6, unique domains 9).

Visual validation (Playwright against authenticated Splunk Web; each check is measured, not asserted by hand;
`evidence/phase4f/visual-validation.json`):

| Check | Result | What was measured |
|---|---|---|
| browser_rendered | pass | 11 panels render; KPIs numeric; charts have SVG; tables have rows |
| scenario_run_binding | pass | KPIs equal the independent run-scoped search |
| visualization_compatible | pass | only supported Studio types; no error / no-result text |
| drilldowns_tested | pass | phase-table click sets the phase token and filters the timeline; client click sets the client token; timeline row opens Search in a new tab |
| inspector_tested | pass | panel Inspect opens the Splunk job inspector |
| responsive_tested | pass | panels stay inside the viewport at 1280 and 1024 px |

The backend then recorded `DASHBOARD_READY` for this dashboard and run (HTTP 200 from `validate-visual`). Scope of that claim: this dashboard,
validated against this run, in this lab, on Chromium. Maturity is recorded per run, so a fresh run starts again at `DATA_VALIDATED` until it is
visually validated. Known limits found while testing: below roughly 1000 px Dashboard Studio stops scaling and the page scrolls horizontally;
clicking chart segments does not set tokens in this Studio build, so drilldowns are on the tables (the chart carries no click claim).

## 4. Operational demo path (run through the Explorer inside Splunk Web)

Select (DNS Diversity and NXDOMAIN Indicators) → Configure → Generate → Ingest (`SPLUNK_DISPATCHED PROVEN`) → Verify (`SPLUNK_OBSERVED PROVEN`) →
Dashboard (`DATA_VALIDATED`) → "Open the Splunk Dashboard Studio dashboard for this run" (opens the view with the run preselected).
Run `f7df21e1-c966-4410-9d10-d2536c71f0e9`; independent count 9 events / 6 NXDOMAIN / 9 domains.

Defects found and fixed while rehearsing (both were indexing-latency races, reproduced 3 of 3):
* Dashboard validation ran its searches a moment after Verify and got empty results (`SPL_VALIDATED`). It now retries an empty or short-shaped
  panel up to 8 times, 4 s apart; the verdict still rests only on rows Splunk returned (`tests/test_phase4f_dashboard_validation_retry.py`).
* Verify reported `PENDING` immediately after ingest. The step now polls while the state is `PENDING`; it never upgrades it.

## 5. Security demo path (Explorer inside Splunk Web)

React2Shell → Prerequisites → Generate (pinned dataset, SHA-256 verified) → Ingest (replay run `p13a-65df80f3-3e90-4d82-beb3-55b0634816fd`, Splunk observed 1 event) →
Enable detection (saved search read back enabled and scheduled `*/15 * * * *`) → Verify (`POSITIVE_CASE_VALIDATED`).
Independent check via splunkd: Splunk's own scheduler ran `NetSpout - Cisco Secure Firewall - React Server Components RCE Attempt` at
2026-10-30 12:30:00 GMT, after the replay, `status=success`, `result_count=1`; the replayed event is present in `idx_security_fw`
(`evidence/phase4f/security-run.json`).

**Not claimed:** Enterprise Security, CIM data models, notable events, the upstream Cisco TA parser (not installed; NetSpout's JSON aliasing is used),
production detection efficacy. Only one detection is runtime-approved.

## 6. Taxonomy

The approved 18 industries replace the proposed list (`taxonomy_status` `APPROVED`); Government carries four subdomains. Scenario mappings
remain editorial unless an industry pack binds them; no scenario is mapped to a subdomain; Non-Profit, NGOs and Global Aid and other industries
without a supported scenario show 0 and are not padded.

## 7. Lab hygiene

The app's `netspout_streamer` modular input was found running in the lab container (about 68k generic events in `idx_network_ops`, source `netspout:streamer`)
although `disabled = 1`. It was stopped inside this lab container only. Those events are not part of any dashboard (panels filter by scenario and run).
No other container was touched.

## 8. Regression and release

| Check | Result |
|---|---|
| Background pytest jobs from the previous session | Both had finished (no pytest processes). `full_final.log` (no lab): 54 failed, 1334 passed. `full_live.log` (lab): 42 failed, 1349 passed. Four stuck wait-loop shells (`pgrep -f` matched their own command line) were stopped. |
| Full suite, lab configured, Phase 4F final | **42 failed, 1354 passed, 9 skipped.** Failing set identical to the Phase 4E lab baseline: 0 new, 0 fixed (gate13d 25 and gate13e 5 need an external collector; gate9_5 7; gate4 2; gate11f 1; gate12f 1; phase12 1). |
| Focused | Gate 8 27/27; Explorer 25/25; dashboard retry 2/2; app surface 3/3; Splunk Web nav/gateway/RBAC 2/2; operational and security rehearsals 1/1 each |
| Secret scan | Lab password and HEC token: 0 hits in tracked files, untracked files and the `.spl` |
| Package | `netspout.spl` contains the gateway, nav, views, taxonomy and Explorer code (byte-compared); lab-installed files hashed equal to the source tree |

Two intermediate full runs were not clean and were fixed rather than excused: one used a wrongly-formed `NETSPOUT_REST_URL` (it needs the full
`/services/search/jobs/export` URL) and showed 9 SNMP failures; it also exposed two tests that assumed a pristine Connection Center and were
affected by a saved lab config on disk. Both are now hermetic.

## 9. Remaining demo blockers and caveats

* Re-enter the destination in Connection Center (or re-run the lab config helper) after any backend restart; secrets are in memory by design.
* The backend must run on the Docker host (`:8081`) while the demo runs; the gateway returns a clear 502 if it does not.
* Enterprise Security, CIM validation, gNMI end-to-end (needs an external collector) and the Cisco TA remain unverified.
* Dashboard readiness is per run; run the Explorer path once and the visual validation spec to leave a `DASHBOARD_READY` record for the demo run if the presenter needs it.
