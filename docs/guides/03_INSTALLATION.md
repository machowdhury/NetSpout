# 03 Installation

Procedure A (Docker-hosted Splunk Enterprise) is the one that was actually run and verified (isolated lab, Splunk Enterprise 10.2.7, engine on the macOS host). Procedure B differs only where marked and has **not** been executed on a VM.

## Prerequisites
| Item | Detail |
|---|---|
| Splunk Enterprise | Tested on 10.2.7. An admin account, the management port (8089) and a HEC endpoint |
| Permissions | Splunk admin for app install; a Splunk user holding `admin`, `sc_admin` or `power` can start runs; other roles are read-only (verified) |
| Indexes | **Create them yourself** (the product never creates indexes): one event index and one metric index, e.g. `dev_test_replay` (event) and `dev_test_replay_metrics` (metric) |
| HEC | An enabled HEC token whose default or allowed indexes include those indexes |
| Engine host | Python 3.11+ with `backend/requirements.txt`; repository checkout or an equivalent deployment of `backend/` and `src/netspout_core` |
| Optional tools | `gnmic`, GoFlow2, Net-SNMP CLI/`snmptrapd`, `tshark` for protocol interoperability checks |

## A. Docker-hosted Splunk Enterprise
1. **Build the package**
   ```bash
   cd NetSpout && python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
   PYTHONPATH=src:backend .venv/bin/python scripts/build_splunk_package.py      # writes netspout.spl and netspout.spl.manifest.json
   ```
2. **Install the app** (Apps > Manage Apps > Install app from file, or by REST):
   ```bash
   docker cp netspout.spl <splunk-container>:/tmp/netspout.spl
   curl -sk -u admin:"$SPLUNK_PASSWORD" https://127.0.0.1:<mgmt-port>/services/apps/local \
        -d name=/tmp/netspout.spl -d filename=true -d update=true -d output_mode=json
   ```
   Expected: app `netspout` 2.0.0, enabled, visible. The package carries 138 `pf_*` dashboards, the nav, the UI and the recorded samples.
3. **Create indexes and a HEC token** in Splunk (Settings). The app ships no inputs enabled and creates nothing.
4. **Start the engine** (secrets only in the environment; use a dedicated config directory):
   ```bash
   export NETSPOUT_CONFIG_DIR=$HOME/.pulseforge-engine NETSPOUT_REPLAY_STATE=$NETSPOUT_CONFIG_DIR/replay_sessions.json
   export NETSPOUT_HEC_TOKEN=...  NETSPOUT_SPLUNK_PASSWORD=...        # never commit these
   cd backend && PYTHONPATH=../src:. ../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8091
   ```
5. **Point the gateway at the engine.** Inside Docker the gateway defaults to `http://host.docker.internal:8081`. For another port add `NETSPOUT_BACKEND_URL=http://host.docker.internal:8091` **on its own line** of `$SPLUNK_HOME/etc/splunk-launch.conf` (a missing trailing newline corrupts the previous line) and restart splunkd (`POST /services/server/control/restart`).
6. **Configure the Connection Center** (System > Connections in the UI, or `POST /api/setup` on the engine):
   ```json
   {"deployment_mode":"DOCKER_LAB","hec_url":"https://127.0.0.1:<hec-port>/services/collector",
    "search_url":"https://127.0.0.1:<mgmt-port>/services/search/jobs/export","auth_method":"HEC_TOKEN_AND_BASIC_SEARCH",
    "search_username":"admin","hec_token":"...","search_secret":"...","indexes":["dev_test_replay","dev_test_replay_metrics"],"allow_insecure_tls":true}
   ```
   `allow_insecure_tls` is accepted only for loopback lab endpoints. `POST /api/setup/validate` must return `PASS` for hec, search and indexes.
7. **Verify the installation end to end**: `python scripts/validate_installed_app.py` (needs the isolated-lab credentials file) checks: app installed and enabled; 138 views and nav present; gateway reaches the engine; Connection Center configured and secret-free; read-only Splunk user refused; unauthorized index refused; replay session accepted equals indexed; native pack indexed; incident pack events and `mstats` datapoints indexed; no index created; no secret in any response. Last result: **12 of 12 passed** (`docs/verification/evidence/installed_app/e2e.json`). `scripts/render_installed_app.mjs` then opens the Command Center, the Explorer and two dashboards in a browser.

## B. Splunk Enterprise on a VM or physical host
Same steps. Differences: install the package by Splunk Web or by unpacking into `$SPLUNK_HOME/etc/apps` and restarting; the gateway defaults to `http://127.0.0.1:8081`; run the engine as a service account (systemd) bound to loopback or a firewalled interface; use real TLS (`allow_insecure_tls` stays false). **Not run on a VM by the maintainers.**

## C. The engine (customer-hosted; no repository checkout needed)
Build once with `python scripts/sync_core.py && python scripts/build_engine_package.py`, which writes `pulseforge-engine.tar.gz` (engine code, catalog, recorded samples and launcher; no tests). On the engine host:
```bash
sudo tar xzf pulseforge-engine.tar.gz -C /opt             # extracts /opt/pulseforge-engine; any directory works
/opt/pulseforge-engine/deploy/engine/install.sh          # creates venv/ and installs backend/requirements.txt
sudo install -m 600 /opt/pulseforge-engine/deploy/engine/engine.env.example /etc/pulseforge/engine.env   # then edit: port, state dir, HEC token, search credentials
/opt/pulseforge-engine/deploy/engine/pulseforge-engine   # or the systemd unit / launchd plist in deploy/engine/
```
Nothing is hardcoded: bind address and port come from `PULSEFORGE_ENGINE_HOST`/`PULSEFORGE_ENGINE_PORT` (default 127.0.0.1:8081), state from `PULSEFORGE_STATE_DIR`, the package location from `PULSEFORGE_ENGINE_HOME`. Point the Splunk gateway at it with `NETSPOUT_BACKEND_URL`. **Restart behaviour:** the saved Connection Center destination is rebuilt on start (secrets from the environment), active runs and replay sessions come back `INTERRUPTED`, and nothing is re-sent. Verified here by extracting the package outside the repository and starting it with a fresh state directory (Explorer 727 entries, 33 replay packs and 25 generation scenarios, identical to the repository engine; `docs/verification/evidence/monitor/`). Flow scenarios additionally need the collector: `docker compose -f deploy/collector/docker-compose.collector.yml up` with `SPLUNK_HEC_TOKEN`, and optionally `SPLUNK_HEC_URL` and `SPLUNK_INDEX` to point it at your HEC; then set `NETSPOUT_GOFLOW_METRICS_URL`, `NETSPOUT_FLOW_FORWARDER_STATUS_URL` and `NETSPOUT_COLLECTOR_HOST` for the engine.

After reinstalling the app, **restart splunkd** (or run a Splunk Web `_bump`): Splunk caches the static UI bundle and keeps serving the old one until then.

## Upgrade
Rebuild, reinstall with `update=true`; restart splunkd when the REST handler or nav changed. Keep `NETSPOUT_CONFIG_DIR`. Replay sessions that were active are reported `INTERRUPTED` after an engine restart and are never resumed or re-sent.

## Uninstall
`curl -sk -u admin:... -X DELETE https://127.0.0.1:<mgmt-port>/services/apps/local/netspout`, stop the engine, delete `NETSPOUT_CONFIG_DIR`, and remove the `NETSPOUT_BACKEND_URL` line. Indexes and data you created are yours to keep or delete.

## Troubleshooting
See [09 Troubleshooting](09_TROUBLESHOOTING.md).
