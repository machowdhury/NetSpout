# Release-support matrix — NetSpout PulseForge 2.0.1 (RC3)

Everything marked **tested** was run in an isolated lab against the packaged candidate. Anything not listed was not run. Versions of vendor add-ons are read from the package file names used in the lab.

## Splunk platform

| Platform | Status | What was run |
|---|---|---|
| Splunk Enterprise 10.2.7 (container `splunk/splunk:10.2`, linux/amd64, on Docker 29.7.2, macOS host) | **Tested** | Fresh install of RC3 `netspout.spl` by Splunk's own app endpoint; Splunk Web; HEC; search by REST; `mstats`; Dashboard Studio and Simple XML dashboards; 20/20 install checks; Phase 9 browser suite (asa, ios, fortinet, pan, metrics, multi, engine) |
| Splunk Enterprise, non-Docker (VM or bare metal), any version | **NOT TESTED** | Procedure documented only (`docs/guides/03_INSTALLATION.md`) |
| Splunk Enterprise other than 10.2.x | **NOT TESTED** | |
| Splunk Cloud (any stack) | **NOT TESTED** | Needs Splunk Cloud app vetting, an install through the Cloud process, a HEC token and an engine reachable from the Cloud stack. `netspout_cloud.spl` is a dashboards-only package; its Cloud AppInspect result was recorded earlier, not an installed Cloud test. The reference instance was not contacted. |
| Distributed Splunk (search head cluster, indexer cluster, heavy forwarder in front of HEC) | **NOT TESTED** | |
| In-place upgrade 2.0.0 → 2.0.1 (fresh 2.0.0 install, REST app endpoint, lab) | **Tested**; an upgrade of a real install with data: NOT TESTED (`PHASE11_UPGRADE.md`) | |

## Engine

| Configuration | Status |
|---|---|
| Engine built from `pulseforge-engine.tar.gz` (RC3) into a Docker image, Python 3.13.18, venv from `backend/requirements.txt`, Linux container; Splunk reaches it over the Docker network (`http://engine:8081`) | **Tested** (Phase 10.1 and the Phase 11 re-run) |
| Same engine process from the source tree on a macOS host (Python venv) | **Tested** (source-stack Phase 9 acceptance and browser regression) |
| Engine as a systemd/launchd service on a VM, TLS between Splunk and the engine | **NOT TESTED** (units shipped in `deploy/engine/`, never run on a VM) |
| Engine on a host reached by `host.docker.internal` from a Splunk container | **Tested in earlier phases only** (2.0.0 default route); not re-tested after the default was removed |
| Docker Engine 29.7.2 + Compose on macOS arm64 (Splunk image emulated as amd64) | **Tested**. Linux Docker hosts and Docker Desktop on Windows: **NOT TESTED** |
| Browser | Chromium headless (Playwright 1.x). Firefox, Safari, Edge: **NOT TESTED** |

## Vendor add-ons used in the lab (not shipped with NetSpout)

| Add-on | Version (package name) | Used for |
|---|---|---|
| Splunk Add-on for Cisco ASA | 6.1.2 | `cisco:asa` |
| Cisco Enterprise Networking Add-on for Splunk | 4.0.6 | `cisco:ios` |
| Fortinet FortiGate Add-on for Splunk | 1.6.10 | `fortigate_traffic` |
| Splunk Add-on for Palo Alto Networks | 4.0.0 | `pan:traffic`, `pan:threat`, `pan:system` |

## Verified sourcetypes (add-on parsing and indexing confirmed in the packaged install)

| Sourcetype | Vendor / product | Index | Evidence |
|---|---|---|---|
| `cisco:asa` | Cisco ASA | `idx_network_ops` | `phase101_rc/journey_asa.json` |
| `cisco:ios` | Cisco IOS | `idx_network_ops` | `journey_ios.json` |
| `fortigate_traffic` | Fortinet FortiGate | `idx_network_ops` | `journey_fortinet.json` |
| `pan:traffic` | Palo Alto Networks | `idx_network_ops` | `journey_pan.json` |
| `pan:threat` | Palo Alto Networks | `idx_network_ops` | `scenario_paloalto_threat_investigation.json` (fields extracted on every event) |
| `pan:system` | Palo Alto Networks | `idx_network_ops` | same |

All other sourcetypes in the catalog use the same generators and dispatcher but are **not verified** in a packaged install; the UI labels each one as verified, not verified or unsupported, and never says *Verified* without a search that found the run's events.

## Verified metrics (found by `mstats`, metric index `cisco_mdt_metrics`)

Sourcetype `cisco:ios:mdt:metric` (IOS XR model-driven telemetry). Names generated and confirmed (`journey_metrics.json`):

- `interface_generic_counters.bandwidth`, `.bytes_received`, `.bytes_sent`, `.input_drops`, `.input_errors`, `.input_load`, `.output_drops`, `.output_errors`, `.output_load`, `.packets_received`, `.packets_sent`
- `Cisco-IOS-XR-wdsysmon-fd-oper:system-monitoring/cpu-utilization.total_cpu_one_minute`, `…total_cpu_five_minute`, `…total_cpu_fifteen_minute`

No other metric names are claimed. Metrics are checked by datapoint count for the run (`mstats`); `mpreview` was not used.

## Verified workflows

| Workflow | Status |
|---|---|
| One sourcetype → Preview → Generate → Verify → Investigate (ASA, IOS, FortiGate, PAN) | Tested, packaged |
| Several sourcetypes in one run, per-sourcetype verification, mixed event + metric, bounded and continuous | Tested, packaged |
| Scenario `paloalto_threat_investigation` with Dashboard Studio investigation | Tested, packaged. Other scenarios: preview exists for the scenario-runner and declarative-contract families; none of the other 371 definitions was run against a vendor add-on |
| Failure honesty: no engine URL, unreachable engine, invalid destination, partly rejected batch, unsupported sourcetype, accepted-not-indexed, search unavailable | Tested, packaged |

## Known limitations

1. Engine address must be set once under Connections after install or upgrade; there is no default. Until then: *Engine not configured.*
2. Splunk Cloud, non-Docker Splunk and distributed Splunk are untested (above).
3. Run investigation is one generic dashboard; per-scenario Dashboard Studio views exist only for scenarios that have one.
4. Scenario duration is an estimate (0.1 s per event), not a measurement.
5. Failure tests inject faults with a recording tap in front of a real HEC; they are not natural server faults. The tap is lab scaffolding, not a product feature.
6. Plain HTTP and unverified TLS are refused for any non-loopback destination or search URL by design. The Docker lab keeps them on loopback inside the engine container.
7. Indexing confirmation retries for about 30 s; a slower indexer shows *Not confirmed* until **Check Splunk again**.
8. Phase 4 browser specs bound to the protected lab were not run in Phases 10, 10.1 or 11; builds are not byte-reproducible.
9. Vendor add-ons are not shipped; parsing claims apply only to the add-on versions listed above.
