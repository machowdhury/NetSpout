# NetSpout PulseForge 2.0.1 — controlled-demo runbook

Scope: the packaged release candidate **RC3** (`rc3-ae3342d`, version 2.0.1) in an isolated Splunk Enterprise plus a Docker engine. It is repeatable: every step below was run by the automated packaged-browser suite (`scripts/phase9_acceptance.py --rc`, Chromium through Splunk Web and the app's gateway), and the Phase 11 re-run is in `docs/verification/evidence/phase11_demo/` (data) and `phase11_demo_ui/` (screenshots).

No credentials appear here. Lab passwords and HEC tokens live only in git-ignored `.env.lab` files. Never use a customer or reference Splunk for rehearsal.

## 0. Artifacts

Use only the RC3 files and verify them first (`sha256sum -c SHA256SUMS`):

| file | sha256 |
|---|---|
| `netspout.spl` | `c070b29e9c98712e17c8606c2fe076a6b510eff6e1259771888362a7d0018149` |
| `netspout_cloud.spl` (dashboards only; not part of this demo) | `01f0bd84e6d218ea21342ff8af9d27ab7ca7ec869e83dc97b36a272ab966ea9c` |
| `pulseforge-engine.tar.gz` | `aa33e60ac09121264d559482431dd98bb46483e77e8a233086124f40f767ddcb` |

They live in `~/netspout/release-candidates/rc3-ae3342d/` with `SHA256SUMS` and `BUILD_MANIFEST.json`. The repo-root `netspout.spl`, `netspout_cloud.spl` and `pulseforge-engine.tar.gz` are older builds; do not demo from them (see the PR summary).

## 1. One-time preparation (the day before)

1. **Splunk Enterprise** (tested: 10.2.7, Docker, linux/amd64) with:
   - an event index `idx_network_ops` and a metrics index `cisco_mdt_metrics` (the app defines both in its `indexes.conf`; PulseForge never creates an index at run time);
   - a HEC token allowed to write to both indexes;
   - the vendor add-ons whose sourcetypes you will show: Splunk Add-on for Cisco ASA, Cisco Enterprise Networking (IOS), Fortinet FortiGate, Palo Alto Networks. They are not shipped with NetSpout; install them from Splunkbase.
2. **Install the app**: Apps > Manage Apps > Install app from file > `netspout.spl` (tick *Upgrade app* on an existing install). **Restart Splunk** and wait until Splunk Web answers.
3. **Start the engine** from `pulseforge-engine.tar.gz` (or the Docker image built from it) on a host the Splunk server can reach. State directory and bind address are the engine's own settings (`docs/guides/03_INSTALLATION.md` section C).
4. **Set the engine address (once)** — see section 2.
5. **Connections > Splunk destination**: HEC URL, token, event index `idx_network_ops`, metric index `cisco_mdt_metrics`, the search (management-port) URL and search credentials used for independent verification. Press **Test**. Plain HTTP and unverified TLS are accepted only for a loopback address in the Docker lab; anything else needs real TLS.
6. Open the app once as the demo user so the first screen is clean.

## 2. Engine address setup (one time, under Connections)

There is **no default engine**, no environment variable and no `splunk-launch.conf` entry. The app uses exactly the address you save.

1. Sign in to Splunk Web as a user with the `admin`, `power` or `sc_admin` role.
2. Open **NetSpout > Connections**. The first card is **PulseForge Engine**.
3. Enter the engine URL *as the Splunk server reaches it*, in the form `http(s)://host[:port]`, with no path:
   - engine on the same machine as Splunk: `http://127.0.0.1:8081`
   - Splunk in Docker, engine on the Docker host: `http://host.docker.internal:8081`
   - Splunk and engine in one Docker network: `http://engine:8081` (the lab value)
   - production: an `https://` URL with a certificate the Splunk server trusts.
4. Press **Save**. The status line shows **Connected** and the engine version.

What you will see otherwise:

| state | message | HTTP | what the UI does |
|---|---|---|---|
| nothing saved | **Engine not configured.** | 503 | Generate Data and Scenarios show a notice; sending is disabled |
| saved, nothing answers | **Engine not connected.** | 502 | same notice; nothing is sent anywhere else |
| saved, answering | **Connected** + version | 200 | normal |

The value is stored in `$SPLUNK_HOME/etc/apps/netspout/local/netspout_engine.conf` (`[engine] url`). A non-admin sees the status and cannot change it. The packaged tests prove all three states (`failure_engine_connection.json`).

## 3. Demo script (about 20 minutes)

Order of the app: **Generate Data | Scenarios | Connections**. The flow on every screen: **Select → Preview → Generate → Verify → Investigate.**

Keep the **Verify** result on screen each time. The word *Verified* appears only when an independent Splunk search by run id found the events (or `mstats` found the metric datapoints). *HEC accepted* is a different, weaker statement and is shown separately.

### Demo 1 — Cisco ASA, single source (2 min)
1. Generate Data > **One sourcetype**. Vendor **Cisco**, product **ASA**, sourcetype **cisco:asa**. Note the label *Verified in Splunk* (the add-on parsing was tested).
2. **Preview** shows the real first event, the index and the generator.
3. Count 20 > **Generate**. The result card: sent 20, accepted 20, then **Verified: found 20 of 20 events in index idx_network_ops**.
4. **Investigate > Open this run in the investigation dashboard** (also *Search this run in Splunk*).
Evidence: `journey_asa.json`.

### Demo 2 — ASA + IOS + FortiGate + Palo Alto in one run (4 min)
1. Switch to **Several sourcetypes**. **Add** `cisco:asa`, `cisco:ios`, `fortigate_traffic`, `pan:traffic`. Each row shows vendor, product, sourcetype; set counts per source (or accept the default). The total is shown.
2. **Preview** each source (one sample event each).
3. **Generate**. The result has one row per sourcetype: accepted, found, index, hosts, and the aggregate. Aggregate found equals aggregate accepted; nothing is double counted.
4. Point out that events keep their own sourcetype, host, timestamp and index.
Evidence: `multi_four_sourcetypes.json`.

### Demo 3 — events and metrics together (3 min)
1. Several sourcetypes: `cisco:asa` (event) and `cisco:ios:mdt:metric` (IOS XR metrics).
2. Events go to `idx_network_ops`, metrics to `cisco_mdt_metrics`. The result reads: found N of N events (search) and M of M metric datapoints (`mstats`) *that this run sent*.
3. If no metric index is configured the page refuses and says why; it does not guess.
Evidence: `multi_mixed_event_and_metric.json`. Metric names found: see the support matrix.

### Demo 4 — Palo Alto scenario and Dashboard Studio (5 min)
1. **Scenarios** > `paloalto_threat_investigation`.
2. **Preview**: sources, phases and order, events per sourcetype and per phase, a sample event per source, and a rough duration (an estimate of 0.1 s per event, not a measurement).
3. **Run**. The result shows 47 events, 3 sources, 5 phases, verified per sourcetype, with correlation ids preserved and phase order intact.
4. **Investigate > Open the scenario's Dashboard Studio dashboard**. It opens with the run id, index and time range already bound; 47 events, 3 sources and 5 phases are visible.
5. Do not say all 372 scenarios behave this way: only scenarios that have their own dashboard show that button; others offer the generic run investigation dashboard.
Evidence: `scenario_paloalto_threat_investigation.json`, `p101_scenario_studio_dashboard.png`.

### Demo 5 — Splunk cannot confirm indexing (3 min)
Use the lab tap (test scaffolding; it is not part of the product) to inject the fault in front of a real Splunk:

| injected condition | what the product shows |
|---|---|
| HEC says success, nothing is indexed (`drop`) | the page says *Not confirmed: Splunk accepted 20, but a search found none of it* after its retries (red) — never *Verified*; **Check Splunk again** re-runs the search |
| one source rejected in a multi run (`reject_st`) | *Only N of M were accepted* with the HEC reason, a red *Partly verified: k of n sources were found* line, that source shows *Nothing accepted*, the others *Verified*; verification status **PARTIAL** |
| search unreachable or refused | *Splunk accepted N, but this app could not check whether it is searchable: <error>* (red); the numbers shown are HEC acceptance only |
| unreachable or wrong HEC destination | *Splunk did not receive this data* with the reason; the run is FAILED, and a run that sent nothing is never COMPLETED |
| unsupported sourcetype | the whole request is refused and the sourcetype is named; nothing is skipped silently |

Evidence: `failure_accepted_not_indexed.json`, `failure_multi_partial_rejection.json`, `failure_search_unavailable.json`, `failure_invalid_destination.json`, `failure_multi_unsupported.json`.

## 4. What not to claim

- Only six sourcetypes have add-on parsing verified in a packaged install: `cisco:asa`, `cisco:ios`, `fortigate_traffic`, `pan:traffic`, and (in the Palo Alto scenario run) `pan:threat` and `pan:system`. Every other sourcetype is generated by the same dispatcher but is labelled as not verified in Splunk.
- Splunk Cloud was **NOT TESTED**. `netspout_cloud.spl` is dashboards only and needs a customer-hosted engine reachable from the Splunk server.
- Metrics: only the IOS XR series listed in the support matrix are generated and confirmed.
- Run investigation is one generic dashboard, not one per sourcetype. No claim that all 372 scenarios are compatible with a vendor add-on.
- The scenario duration is an estimate.

## 5. If something goes wrong

| symptom | cause and fix |
|---|---|
| Notice **Engine not configured.** | No URL saved. Connections > PulseForge Engine > Save |
| Notice **Engine not connected.** | URL saved but unreachable from the Splunk server: check the engine process, port, firewall, and that the URL is valid from the Splunk side (for Docker, `localhost` is the Splunk container itself) |
| **Not confirmed**, accepted > found | Indexing can lag by seconds: press **Check Splunk again**. If it stays, the index or token routing is wrong |
| *…could not check whether it is searchable* | search URL, credentials or role problem: Connections > search settings; the generation itself was not affected |
| Pages look old after an upgrade | restart Splunk after installing the app |

## 6. Re-running the automated demo

```
# lab stack: tests/lab/rc_install (containers netspout_rc_splunk, netspout_rc_engine, ports 39000/39088/39191)
python scripts/phase10_rc_install.py install ~/netspout/release-candidates/rc3-ae3342d   # installs the app, sets engine, restarts
python scripts/phase10_rc_install.py start-tap                                           # test scaffolding inside the engine container
PHASE9_OUT=phase11_demo python scripts/phase9_acceptance.py --rc asa multi pan engine
```
Evidence goes to `docs/verification/evidence/phase11_demo[_ui]`.

## 7. Phase 11 re-run results (RC3, packaged, isolated lab, 2026-11-04)
`phase9_acceptance.py --rc asa multi pan`: asa 11 passed, multi 8 passed, pan 3 passed (22 tests, all exit codes 0). Install check against the RC3 directory: 20/20 PASS (`evidence/phase11/rc_install_check.json`). RC3 checksums re-verified OK. Upgrade 2.0.0 → 2.0.1: `evidence/phase11/upgrade_2.0.0_to_2.0.1.txt`. Screenshots: `evidence/phase11_demo_ui/`.
