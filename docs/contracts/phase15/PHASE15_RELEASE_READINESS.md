# Phase 15 — release readiness and decision

Product 2.0.1, `main` `856418ba19d14a38a9a003308c09bcf68e1f327b`, candidate `v2.0.1-docker-856418b` (checksums in `PHASE15_DOCKER_LAB.md`). Validation was Docker-only, by design. Nothing was published, deployed or merged; no PR opened.

## Gates

| # | gate | result |
|---|---|---|
| 1 | Branch from `origin/main`, merge commit and version 2.0.1 verified | PASS |
| 2 | Clean-checkout build of all three packages; mirrored-core guardrail; audit 0 findings; `SHA256SUMS`, `BUILD_MANIFEST.json`; RC1–RC7 and 2.0.0 untouched | PASS |
| 3 | Isolated Docker lab (own project, network, volumes, ports, health checks, disposable credentials) | PASS |
| 4 | Fresh install; engine address set in Connections; missing and unreachable engine | PASS (`PHASE15_FRESH_INSTALL.md`) |
| 5 | Workflows A–F in the installed UI with independent indexing verification | PASS (29/29; `PHASE15_WORKFLOW_ACCEPTANCE.md`) |
| 6 | Upgrade 2.0.0 → 2.0.1 with persisted data | PASS |
| 6b | Rollback to 2.0.0: data and config | PASS; generation under 2.0.0 through the UI NOT TESTED |
| 7 | Persistence: Splunk restart, engine restart, recreate with volumes | PASS |
| 8 | Install checks 20/20; packaged acceptance 29/29; source browser regression 26/26; Python vs baseline (same nine, no new failure); audit and checksums | PASS (nine known failures remain failures) |
| 9 | Non-Docker Splunk Enterprise; distributed Splunk; Splunk Cloud; other Splunk versions or browsers; engine as a VM service or with TLS | **NOT TESTED** |
| 10 | Product behaviour when idle: no data written without a user action | **FAIL** (defect B1) |

## Release-blocking defect

**B1 — the app writes synthetic events into `idx_network_ops` on its own, from the moment it is installed.** Evidence: `docs/verification/evidence/phase15/streamer_finding.json`. In the fresh lab, 2,601 events from `source="netspout:streamer"` had been indexed 27 minutes after the install, about 78 per minute, in sourcetypes `pan:traffic`, `pan:threat`, `cisco:ios:syslog`, `cisco:ise:syslog`, `cisco:duo:auth`, `arista:eos:syslog`, `fortinet:fortigate:utm`, `juniper:junos:syslog`. No run was active (all engine runs stopped). A `netspout_streamer.py` process runs under splunkd although the app's only stanza (`netspout/default/inputs.conf`, `[netspout_streamer://default]`) says `disabled = 1`. Cause in the source: `netspout/bin/netspout_streamer.py` `run_input()` loops forever generating events with built-in defaults when no input configuration arrives on stdin; the scheme sets `use_single_instance`, and Splunk starts the script. It also happens in the archived 2.0.0 package (27 events seen shortly after its install in the upgrade lab), so it predates 2.0.1, but it was not caught earlier because every NetSpout verification searches by run id. Impact: fake firewall, IDS and identity events in a customer's network index, which pollute real searches and detections. No in-product setting disables it that I found. Not fixed here (this phase is validation only). Proposed minimal fix: make the script exit when no enabled input stanza is passed, add a packaged test that the idle app indexes nothing, rebuild, and re-run the gates.

## Other findings (not blocking)

- **Upgrade needs one manual step**: restart Splunk and set the engine address in Connections (2.0.0's `NETSPOUT_BACKEND_URL` is no longer read). Documented above.
- **Process incident, disclosed**: in the rollback lab the 2.0.0 gateway, with no engine configured, answered `/health` from the host's port 8081 through its implicit `host.docker.internal:8081` fallback. That is most likely the protected demo engine. It was one read-only health GET; I stopped and made no other request. This is the hazard 2.0.1 removed (no implicit fallback), and a reason not to run a 2.0.0 gateway on a machine where an engine listens on 8081.
- The wrong-metric-index test needs the extra index `dev_test_replay_metrics` in a new lab (lab prerequisite, now documented).
- Index `totalEventCount` metadata lags search results briefly after ingest.
- Add-on parsing is verified for six sourcetypes and 14 IOS XR metric names only; everything else is labelled not verified. Dashboards for all 372 scenarios are generic apart from those that ship their own.

## Tested configuration (the only one with evidence)

Splunk Enterprise 10.2.7 (Docker, linux/amd64 emulated on an arm64 host, Docker 29.7.2), standalone, single instance, with the four vendor add-ons listed in `PHASE15_DOCKER_LAB.md`; engine in Docker on Python 3.13.18 on the same private network; plain HTTP between Splunk and the engine inside the lab; Chromium (Playwright 1.63.0).

## Decisions

**A. Controlled Docker-based Enterprise release: NO-GO as the candidate stands.** Every functional, upgrade, rollback and persistence gate passed, but B1 means installing the app puts unsolicited synthetic data into the customer's index. It flips to GO once B1 is fixed, the candidate is rebuilt, and gates 4–8 are re-run (the fresh-install and idle-index checks are quick; the full packaged suite takes about 25 minutes). The three upgrade/rollback/persistence labs need only a short repeat.

**B. General Splunk Enterprise compatibility: NO-GO — NOT TESTED.** No non-Docker, distributed, clustered, other-version, TLS-engine or VM-service-engine evidence exists. A passing Docker run does not stand in for it.

**C. Splunk Cloud: NO-GO — NOT TESTED.** `netspout_cloud.spl` is dashboards only and needs a customer-hosted engine reachable from the Splunk side and a way to set the engine address; neither was exercised. It has its own validation track and no feature parity is claimed.

Approvals needed: whether to fix B1 on a new branch (small, source change), and whether to open a PR for the Phase 15 lab, harness and documentation changes. Not done: PR, merge, release, deployment, publishing the candidate.
