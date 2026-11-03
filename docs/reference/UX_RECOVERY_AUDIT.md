# Product integration and UX recovery: audit, root causes and repair

Date: 2026-11-02. Branch `fix/product-integration-ux` (from `main` `3f2e63f`). Nothing here was installed in, or run against, the demo environment (`netspout_phase4e_splunk`, engine 8091). Every "before" and "after" observation below comes from the **installed Splunk Web UI** of the isolated lab Splunk (`pf-validation-splunk`, Splunk Web 28000) with **real runs**; the screenshots are in `docs/verification/evidence/ux_recovery/`.

## 1. Deployment and version comparison

| Item | Finding | How it was checked |
|---|---|---|
| Deployed app (demo Splunk) | `netspout` 2.0.0, build 20260919, 148 `pf_*` views. **Identical to the released `netspout.spl`** (sha256 `3b086b80e2e5…`); the only difference is the `install_source_checksum` line Splunk adds to `app.conf`. | Read-only `tar` of `/opt/splunk/etc/apps/netspout` (as the `splunk` user) diffed against the unpacked release |
| Release build source | `netspout.spl` last rebuilt by commit `5a2405c` (2026-11-01) | `git log -- netspout.spl` |
| Frontend bundle | Deployed, released and `main` all ship `assets/index-CDpm2bR2.js`. `frontend/src` has **not changed since `5a2405c`**, so no frontend change is waiting to be built or installed on `main` or on any open branch. | `git log -- frontend/src`; `install/two-options-audit` changes no `frontend/`, `appserver/` or view file |
| Demo engine | Process started 2026-11-02 07:17 from the working tree (`uvicorn app.main:app`, `PYTHONPATH=../src:.`) at `5a2405c`; later commits were documentation only | `ps`, `git reflog` |
| `main` (`3f2e63f`) vs deployed | `main` adds 224 contract scenarios and dashboards, the dispatcher fixes and `scenario_contracts`; none of that is installed in the demo | Release-vs-repo `diff -rq` |
| Open branches | `install/two-options-audit` (`d83c9a6`, installer only) and `demo/presentation-materials` (PR #5) | `git branch -r --no-merged origin/main` |
| PR #5 | Presentation only: all 25 files are under `demo/presentations/`; it contains **no application fix** | `gh pr view 5 --json files` |

So the screens that look wrong in the demo environment are the released product behaving as written, not an unbuilt or uninstalled fix.

## 2. One real run, end to end (released app, before)

Lab: released `netspout.spl` and the released engine archive, destination index `dev_test_replay`.

| Step | Result |
|---|---|
| 1. Generate and dispatch | Scenarios > `NF-SEC-06-DDOS` > Run: run `run-7b6d33db3b00`, 820 events (traffic 100, syn-flood 560, udp-flood 160) |
| 2. HEC acceptance | Monitor: generated 820, HEC accepted 820, rejected 0 |
| 3. Independent indexing | REST search `index=* netspout_run_id="run-7b6d33db3b00"`: **820 events, index `dev_test_replay`, sourcetype `netflow:collector`**, 2026-11-03 01:03:14 to 01:06:11 UTC. Monitor "Indexed (verified)" 820. |
| 4. Observe shows consistent evidence | **Fails.** Overview: "Splunk observation: NOT AVAILABLE" and "No evidence" after the run (screenshot b03). Live Runs does not list the run. In the 6-step run, the Observe stage shows `SPLUNK OBSERVED 0 PENDING` until Refresh is pressed (b05). |
| 5. Investigate opens a working view | **Fails.** The four Investigate/Telemetry sidebar items are "PLANNED" stubs ("no supported runtime path", b07). The 6-step Investigate runs the query inside the engine, offers no link to Splunk Search, and for a run in `dev_test_replay` searches `idx_network_ops` and reports a green **"SUCCEEDED · 0 results"** (b06). |
| 6. Open the matching dashboard with the same run context | Works only from the Explorer monitor ("Open dashboard", tokens `run_tok`, `index_tok`). Not reachable from Live Runs, Overview or Investigate. |
| 7. Validate represents the evidence | **Fails.** For a finished 6-step run the monitor showed "Engine unreachable: No answer from the engine within 5s. Showing the last known counters", generated 0, "Indexed (verified): Not verified" (b04), and, for the HEC scenario, "READY: 6 events indexed" together with "Indexed (verified) 0". |

## 3. Root causes

1. **The Overview "Splunk observation" badge is a constant.** `frontend/src/components/home/HomeView.tsx` rendered `<StatusBadge status="NOT AVAILABLE" />` (and "Detection evaluation: NOT CONFIGURED") without reading any data. It can never change, whatever the run indexed. The pipeline table below it reads `/api/health/pipelines`, which is about receivers, not runs.
2. **Two run systems, two verification paths, no shared view.** The Explorer's runs are delivery-monitor runs (`run-…`, `/api/runs`) whose verification and dashboard readiness run automatically. The page called "Live Runs" was actually the 6-step lab (`GenerationLab`, UUID run ids, a per-channel evidence ladder); its `SPLUNK_OBSERVED` stage is computed only when someone presses "Refresh Splunk Observation". Neither feeds the Overview. So Observe can say zero while the monitor and the dashboard show 820 for the same data.
3. **Stale and contradictory monitor state.** The Splunk gateway handles one request at a time, so a long readiness search makes the 1 s status poll time out (5 s limit). `LiveDeliveryMonitor.tsx` re-polled on every state change, kept the "engine unreachable" banner after the run had finished, and read the Indexed tile from `counters.indexed` instead of the verification record or the readiness search.
4. **Investigation recipes hard-code the lab index.** The packs (`phase9_security_packs.py` and the catalog recipes) carry `index="idx_network_ops"`; only `$run_id$` was substituted, so any other destination index searched the wrong index. The result was shown as green SUCCEEDED with zero results. In the demo environment the destination index happens to be `idx_network_ops`, which hides this one; root causes 1 to 3 still apply there.
5. **There was no Investigate destination.** The Splunk bar had 16 top-level entries over three rows, a second 22-item NetSpout sidebar repeated them, dashboards were split across three Splunk menus plus a gallery that said "0 dashboards ready", and Investigate was four placeholder pages.
6. **Guided Workflow bypassed the gateway.** `GuidedWorkflow.tsx` called `fetch('/api/…')` on the Splunk origin, so Splunk answered with an HTML 404 and the page showed `Unexpected token '<'… is not valid JSON`.

Run ids, indexes, sourcetypes and freshness, as asked: run ids differ between the two systems (`run-…` vs UUID); the index differs only in the investigation recipes; sourcetype mapping was correct; observation freshness was the gap (it never ran by itself); the verification logic differs (monitor verify vs per-channel ladder). I could not see the user's own Splunk screens, only reproduce the behaviour in the lab; the demo environment was not run against.

## 4. What changed

| Area | Change | Files |
|---|---|---|
| Navigation, Splunk bar | Five destinations in one row (Overview, Scenarios, Live Runs, Investigate, Dashboards) plus **More**. Dashboards holds the Dashboard Gallery and the three existing menus; More holds the tools, Operations and Search. No view was removed: all 400 views stay reachable. The destination names come from the view titles because Splunk ignores a `label` attribute on a nav `<view>`. | `netspout/default/data/ui/nav/default.xml`, `views/pulseforge_command_center.xml`, `use_case_explorer.xml`, new `pulseforge_live_runs.xml`, `pulseforge_investigate.xml`, `pulseforge_dashboards.xml`, `appserver/static/netspout_canvas.js` |
| Navigation, sidebar | Grouped under the same five destinations plus Reference. The four placeholder pages are gone; their old links redirect (`LEGACY_REDIRECTS`). | `frontend/src/app/navigation.ts`, `useHashRoute.ts`, `App.tsx` |
| Live Runs | A real list of every run with counters, the independent verification, index, and **Investigate** and **Verify in Splunk** actions. The 6-step lab moved to "Run in 6 Steps" (`/generate/unified`). | `frontend/src/components/runs/RunsView.tsx` |
| Investigate | Pick a run: validation stated from its own counters and verification; Splunk Search links that carry the run's index, run id, sourcetype and a time range covering the run; the matching dashboard with the same `run_tok` and `index_tok`. | `RunsView.tsx`, `frontend/src/lib/splunkLinks.ts`, `runsApi.ts` |
| Overview | "Splunk observation" is derived from the latest run (VERIFIED, n of m indexed, which index); the constant "Detection evaluation" claim was removed. | `HomeView.tsx` |
| Monitor | A finished run's snapshot is kept and retried quietly, no stale banner; the Indexed tile uses the verification or the readiness search. | `LiveDeliveryMonitor.tsx` |
| 6-step run | Observe starts the authenticated search by itself and repeats it while indexing catches up; Investigate shows "Open in Splunk Search" and reports 0 results as `NO RESULTS`, not success. | `GenerationLab.tsx`, `types/generation.ts` |
| Index binding | Recipes are bound to the run's destination index when the run is created and again when executed; the result carries the index and an openable search path. | `src/netspout_core/unified_generation.py` (mirrored to `backend/app` and `netspout/bin` by `scripts/sync_core.py`) |
| Guided Workflow | Calls go through `apiUrl()` (the gateway) and a non-JSON answer is reported plainly. | `GuidedWorkflow.tsx` |
| Bundle | Rebuilt with `scripts/build_frontend.py` (`index-GeR4gVNr.js`). The release artifacts at the repository root were not rebuilt or overwritten. | `netspout/appserver/static/dist/` |

## 5. Tests and acceptance

* `tests/test_investigation_index_binding.py` (3): index binding, idempotence, search path.
* `tests/test_navigation_architecture.py` (7): five primary destinations in one row, every nav entry is a real view appearing once, every shipped view still reachable, view titles carry the destination names, new destinations map to their React routes, no placeholder pages in the sidebar, the dashboard generators' regexes still match the nested menu.
* `tests/test_phase4f_splunk_app_surface.py`: destination labels updated.
* `frontend/tests/unified-shell.spec.ts` and three specs that opened the 6-step lab at `#/observe/live-runs` now use `#/generate/unified` (Playwright specs were edited, not run here).
* `scripts/acceptance_ux_live.py`: the browser acceptance against an installed Splunk with real runs. **Result on the repaired build: 18 checks, 0 failed** (`after/acceptance_result.json`). It covers: one-row navigation; real run, 820/820/820 in the monitor, no stale banner; independent Splunk search finds 820 events (index and sourcetype recorded); Overview shows VERIFIED 820 of 820; Live Runs lists the run; Investigate states the verified evidence; the Search link carries index, run id and time range and Splunk Search opens with **820 events**; the dashboard link carries the same run and index and shows 820 flows; the 6-step Observe proves `SPLUNK OBSERVED` unaided; the recipe query uses `dev_test_replay` and Run in Splunk returns 6 results with an Open-in-Search link; Guided Workflow loads; the sidebar has no placeholder pages.
* Regression (Python, all test files except the six with known baseline failures): **4,943 passed, 11 skipped, 3 failed**. The three, classified: `test_gate11f…collector_preflight_without_pythonpath` is the known environment-dependent baseline failure (it needs an HEC answering on 127.0.0.1:8088 or :8888); `test_phase12…dashboard_recipe_families_integrate_without_regression` (34 recipes found, 30 pinned) **fails identically on a pristine `origin/main`**, so it predates this work and is not in the earlier baseline list because that run did not include the file; `test_gate5_ux::test_02_canonical_navigation` pinned the placeholder "Security Intelligence" page and was updated to the new navigation (22 of 22 pass). The six baseline files (52 known failures: gNMI/SNMP end-to-end and customer-acceptance) were not re-run.
* Frontend: `tsc -b` clean and `oxlint` shows only pre-existing style warnings. The Playwright specs in `frontend/tests` could not be run here: this machine lacks the Chromium build the frontend's Playwright version expects (the real-browser acceptance above used a different Playwright installation).

## 6. Navigation architecture

| Destination | Splunk bar | Sidebar group | What it is |
|---|---|---|---|
| Overview | Overview | Overview | Status, the latest run's observation, entry points |
| Scenarios | Scenarios | Scenarios | Use Case Explorer, Quick Generate, Guided Scenarios, Run in 6 Steps, Scenario/Industry Studio, Scenario Builder (advanced) |
| Live Runs | Live Runs | Live Runs | All runs with counters and verification; Pipeline Health |
| Investigate | Investigate | Investigate | Run-centred search and dashboard links with validation; Detection Explorer |
| Dashboards | Dashboards (menu) | Dashboards | Dashboard Gallery, PulseForge, Scenario and NetFlow / IPFIX dashboards |
| Reference | More (menu) | Reference | Catalog, Connections, Destination Manager, Guided Workflow, SPL Playground, Security Content Lab, Operations, Search |

## 7. Remaining limits

* Operational and Security scenario dashboards remain two menus of 300 and 62 entries; they are reachable but still long. A searchable dashboard picker is the next step.
* The demo environment still runs the released app. Installing this build there is a separate, approved step.
* The lab has no GoFlow2 collector, so the native-IPFIX packs (for example `SEC-P9-A-TRAFFIC-FLOOD` in the 6-step lab) deliver nothing to Splunk there. Their Observe stage correctly stays PENDING; this was seen and is not changed.
* Splunk shows its own one-time product-usage notice on the first Search; it is Splunk's and was dismissed in the lab runs.
