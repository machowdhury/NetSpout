# Phase 15 — fresh-install validation (lab `nsp15`)

Result: **PASS** (with one release-blocking defect found, B1, in `PHASE15_RELEASE_READINESS.md`).

| gate | result | evidence |
|---|---|---|
| Empty persistent volumes; stock Splunk 10.2.7 with no NetSpout app | PASS | `splunk_etc/var` empty volumes, app list contains only built-ins |
| Install `netspout.spl` through Splunk's own app-install endpoint (`/services/apps/local`, install from file) and restart | PASS | app `NetSpout PulseForge` 2.0.1, enabled |
| Engine started from the new `pulseforge-engine.tar.gz` (Docker, Python 3.13.18) | PASS | engine `/openapi.json` version 2.0.1 |
| Engine address NOT preconfigured; `NETSPOUT_BACKEND_URL` not used | PASS | before configuration the gateway returns `503 "Engine not configured."` on `/health` and `/api/runs`; `/engine` reports `configured:false` |
| Engine address set in **Connections > PulseForge Engine** (browser, packaged UI) | PASS | packaged test `[engine]`; afterwards `/engine` → `connected:true, url http://engine:8081, version 2.0.1` |
| Missing engine URL named, nothing generated | PASS | gateway 503, UI "Engine not configured." (`failure_engine_connection.json`) |
| Unreachable engine URL named, nothing generated, saved address is the one used | PASS | gateway 502, UI "Engine not connected."; invalid URL refused (422) |
| Package install checks | **PASS 20/20** | `evidence/phase15/fresh_install_check.json`: versions equal everywhere (2.0.1), installed files byte-equal to the archive, 6 verified sourcetypes equal the live evidence, indexes defined by the app, 432 dashboards, gateway reaches the engine, URL is the configured setting |
| Package audit and checksums | PASS | 0 findings; `SHA256SUMS` verifies |

Note on the supported installation process: the Splunk REST app-install endpoint is the same mechanism as Apps > Manage Apps > Install app from file; the Splunk Web upload form itself was not driven by the browser test.
