# 01 Product overview

PulseForge (repository name NetSpout) generates, replays and verifies realistic telemetry for Splunk. It is a **Splunk app plus a separate engine**: the app supplies navigation, the Use Case Explorer UI, Splunk dashboards and a same-origin gateway; the engine (a Python service) generates and sends telemetry and verifies what Splunk indexed. Splunk owns authentication and authorization; PulseForge has no login of its own.

## Who it is for
Splunk solution engineers, architects, security, network and observability engineers, and demo builders who need believable data with provable provenance.

## Capabilities (each with its verification status in [10 Limitations and status](10_LIMITATIONS_AND_STATUS.md))
- **Native generators** for vendor log formats (159 of 349 cataloged sourcetypes; 129 byte-verified in Splunk).
- **Continuous sample replay**: authentic recordings (10 vendored) re-emitted on the current clock; only the selected timestamp bytes change; looping, pause/resume/stop, speed, EPS limit, backpressure.
- **Scenarios**: finite incidents across 18 approved industries and SOC/NOC/ITOps/AI/supply-chain categories, run from native generators, replay, or both. See [Scenario reference](../reference/SCENARIO_REFERENCE.md).
- **Network protocols**: SNMPv2c polling/traps/informs, gNMI/OpenConfig (and vendor-native paths) streaming, NetFlow v9 and IPFIX export. See [06](06_NETWORK_TELEMETRY_GUIDE.md).
- **Dashboards**: 133 Dashboard Studio dashboards with NOC/Engineer/Evidence (operational) or Overview/Investigation/Evidence (security) tabs. See [07](07_DASHBOARD_GUIDE.md).
- **Independent verification**: every run can be checked by a Splunk search written separately from the sender's counters.

## What it does not do
- It does not assert detection results, CIM compliance or Enterprise Security behavior without evidence (none are validated here).
- Replayed independent recordings are aligned in time only; PulseForge never rewrites identifiers to fake a shared incident.
- Sample replay is not a native generator and is never counted as one.
- Splunk Cloud has **not** been validated by the maintainers (user validation pending; see [04](04_SPLUNK_CLOUD_GUIDE.md)).

## Safety
Telemetry is synthetic and labeled (modeled payloads say so). Destinations come only from the Connection Center; caller-supplied transports are refused; every index must be on the allowlist; the product never creates indexes, tokens or listeners in Splunk. Secrets are held in environment variables or the OS secret store of the engine host, never in the app package, Git or evidence files.
