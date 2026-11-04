# Upgrade instructions — 2.0.0 → 2.0.1

Applies to an existing NetSpout PulseForge install (Splunk app plus customer-hosted engine). Use only the RC3 or later 2.0.1 artifacts and check `SHA256SUMS` first.

## What changes for an existing install
| Item | 2.0.0 | 2.0.1 |
|---|---|---|
| Engine address | gateway default (`host.docker.internal:8081` in a container, `127.0.0.1:8081` otherwise) or `NETSPOUT_BACKEND_URL` in `splunk-launch.conf` | **Saved setting only** (Connections > PulseForge Engine). No default, variable ignored |
| Missing address | silently went to the default | **Engine not configured.** (HTTP 503); sending disabled |
| Unreachable address | generic errors | **Engine not connected.** (HTTP 502) |
| Engine dependencies | — | adds PyYAML (`backend/requirements.txt`) |
| App contents | | new `netspout_engine.conf` (+ spec), new dashboard view `netspout_run_investigation`, new UI bundle |
| Run results | | new `PARTIAL` verification status; a run that sent nothing is `FAILED` |

Nothing is migrated or deleted. Saved Connection Center destinations, indexes, data, run history and replay state are untouched. The old `NETSPOUT_BACKEND_URL` line is harmless and ignored; remove it when convenient.

## Steps
1. **Note the engine address** the app currently uses (the `NETSPOUT_BACKEND_URL` value if you set one; otherwise the old default). After the upgrade nothing falls back to it.
2. **Upgrade the engine first.** Stop it; extract the new `pulseforge-engine.tar.gz` over its directory (or build the new Docker image); refresh dependencies (`deploy/engine/install.sh`, or rebuild the image); keep the state directory (`PULSEFORGE_STATE_DIR` / `NETSPOUT_CONFIG_DIR`); start it. `GET /api/health` must answer and the OpenAPI version must be 2.0.1.
3. **Upgrade the app**: Apps > Manage Apps > Install app from file > `netspout.spl`, tick **Upgrade app**. **Restart Splunk** and wait until Splunk Web answers.
4. **Set the engine address** (admin, power or sc_admin): NetSpout > Connections > PulseForge Engine > enter the URL as the Splunk server reaches it > Save. The status must read *Connected* with version 2.0.1. See the runbook, section 2.
5. **Check**: Connections > Test the Splunk destination; generate 20 `cisco:asa` events and confirm *Verified*.

If a URL was already saved in `local/netspout_engine.conf` it is kept by the upgrade (Splunk never overwrites `local/`).

## What was tested
Run in the isolated RC lab only (`docs/verification/evidence/phase11/upgrade_2.0.0_to_2.0.1.txt`): RC1 (2.0.0) installed, then RC3 (2.0.1) installed over it with `update=true` through Splunk's app endpoint. Result: version 2.0.1; a previously saved engine URL survived; with the URL blanked the gateway answered *Engine not configured.* (HTTP 503) for `/engine` and `/api/runs`, and after saving the URL again it answered *Engine connected.*

**Not tested:** an upgrade of a real 2.0.0 install that had data, saved destinations and runs (the RC1 install in the lab was fresh); an upgrade through Splunk Web's file upload (the REST app endpoint was used); a non-Docker Splunk; Splunk Cloud. During the test the lab's Splunk restart overran its 360 s shutdown limit and had to be started by hand inside the container; that is a lab/emulation effect (amd64 image on arm64), not seen in any other restart, but a customer should confirm Splunk is running after the restart in step 3.

## Rollback
Reinstall the previous `netspout.spl` (2.0.0) and restart Splunk; the 2.0.0 gateway falls back to its old default or `NETSPOUT_BACKEND_URL`. The extra `local/netspout_engine.conf` is ignored by 2.0.0. Keep the previous engine package and roll the engine back together with the app: a 2.0.1 engine with a 2.0.0 app, or the reverse, was not tested.

## Warnings
- A 2.0.0 install that pointed at a non-default engine through `splunk-launch.conf` must enter that URL again in step 4; the variable is not read.
- Anyone using a script or automation that depended on the implicit engine default must set the URL once (the same Splunk configuration endpoint the UI uses: `servicesNS/nobody/netspout/configs/conf-netspout_engine`).
- The protected demo app, if it is upgraded, needs the same one-time step. It was not touched in Phase 11.
