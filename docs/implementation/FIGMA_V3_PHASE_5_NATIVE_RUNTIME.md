# NetSpout Figma v3 — Phase 5 Native Runtime

## Scope and baseline

- Starting commit: `51cb05a1812d5f29097a7b94dc6cb5767bf4f81a`
- Branch: `feature/figma-v3-unified-telemetry-lab`
- Final implementation commit: `d5286325f46c4835cc57af72aefb906c79ee4f44`
- Report/evidence finalization: documentation-only successor commit
- Phase 6: not started

Phase 5 extends the Phase 3/4 workflow without adding a second native-protocol
product surface. A selected source or scenario still follows
Choose → Preview → Configure → Run → Observe → Investigate. Native
source-side transport is now distinct from destination-side Splunk delivery.

## Audit before implementation

The accepted Phase 4 commit was re-tested rather than relying on earlier gate
results.

| Transport | Generator / encoding / send | Receiver or collector | Normalization | Splunk delivery / observation | Docker | Phase 3/4 UX | Baseline classification |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Syslog | RFC 5424 modeling and socket send existed | UDP receiver code existed but was not started; no equivalent TCP receiver proof | HEC-oriented log model | Modeled RFC 5424 → HEC was proven; native receiver path was not | Splunk 514 inputs existed | Only modeled HEC path | PARTIAL |
| SNMPv2c | Trap, Inform, ACK, GET, GETNEXT, GETBULK, Response and BER passed host tests | Net-SNMP receiver/poller integration existed | Decoded receiver records with out-of-band run fields | HEC plus fresh search implementation existed | Python 3.9 syntax failure and missing Net-SNMP packages | Separate native endpoints, not unified | BROKEN in Docker; functional on host |
| gNMI/OpenConfig | Canonical protobuf over TCP/HTTP2/gRPC; Capabilities, Get and Subscribe existed; Set rejected | Native target existed; runtime collector depended on user-installed `gnmic` | Collector normalizer existed | HEC and fresh event/metric searches existed | Protobuf generated/runtime mismatch and missing collector binary | Separate native endpoints, not unified | BROKEN in Docker; PARTIAL self-containment |
| NetFlow v9 | Binary templates/data and UDP transport passed local tests | Pinned GoFlow2 compose existed separately | GoFlow2 decoded JSON | Forwarder existed but targeted the wrong root-stack port | Not part of root Compose; backend probed its own loopback | Separate native endpoints, not unified | PARTIAL |
| IPFIX | Binary templates/data and UDP transport passed local tests | Same separate GoFlow2 tier | Same decoded boundary | Same disconnected forwarder | Same root-Compose gap | Separate native endpoints, not unified | PARTIAL |
| OpenTelemetry | OTLP receiver config for logs and metrics existed | OpenTelemetry Collector 0.96.0 ran | Collector batch processing configured | No fresh OTLP → Splunk observation proof; no traces pipeline | No collector health extension | Not unified | PARTIAL |

The baseline `/api/health/pipelines` response was misleading: it returned
aggregate `HEALTHY` while Syslog, SNMP, gNMI and Flow were only
`INITIALIZED`. SNMP and gNMI preflight returned HTTP 500 in the running root
container, and Flow health reported `STOPPED` even while the separately
started collector stack was running.

## Files changed

The implementation changes are grouped as follows:

- Runtime and orchestration: `src/netspout_core/native_runtime.py`,
  `unified_generation.py`, SNMP/gNMI/Flow adapters, encoders, collector
  evidence, safety policy, and their packaged mirrors.
- API and catalog: `backend/app/main.py`, Phase 5 source/composition
  declarations in `catalog/*.json`, and synchronized catalog mirrors.
- Containers: `Dockerfile.standalone`, `docker-compose.yml`,
  `entrypoint-standalone.sh`, Flow collector/forwarder deployment files, and
  OTel health wrapper.
- UX: Generation Lab, Guided Scenario Lab, topology, Pipeline Health, shared
  types/styles, and live/static Playwright acceptance coverage.
- Verification: Phase 5 backend tests, native Flow regression hardening, and
  this report plus inspected screenshots.

Generated historical Gate 13 evidence was restored after regression runs; it
is not part of the Phase 5 change set.

## Runtime architecture

```text
ScenarioStateStore / Enterprise State / Simulation Clock
        ├── Syslog generator ── native UDP ── bundled receiver ──┐
        ├── SNMP generator ─── native BER/UDP ─ bundled receiver/poller ─┤
        ├── gNMI target ────── gRPC/HTTP2 ─ bundled subscriber ─┤
        └── Flow exporter ──── NetFlow v9 or IPFIX/UDP ─ GoFlow2 ─┤
                                                                  ↓
                                                    Normalized Observation
                                                                  ↓
                                                    Destination Adapter
                                                                  ↓
                                                          Splunk HEC
                                                                  ↓
                                                  Authenticated Splunk Search
```

Collectors do not own Splunk-specific destination logic. Source bindings
declare both `transport_id` (native source side) and
`destination_transport_id` (HEC for this phase). The runtime invokes only
allow-listed adapters.

## Contract and fidelity boundaries

The runtime keeps four contracts separate:

1. **Native contract** — bytes or protobuf exchanged by the source protocol.
2. **Collector observation** — a receiver-confirmed decoded representation.
3. **Splunk contract** — the event or metric submitted by the destination
   adapter.
4. **CIM result** — only a later integration/parsing claim, when independently
   validated.

NetSpout metadata such as run, scenario, entity and phase identifiers is
attached only after native receipt/decode. Native SNMP PDUs, gNMI
notifications and Flow packets are not mutated to carry NetSpout fields.
Syslog raw text is preserved exactly at receiver observation.

Flow correlation uses a short-lived observation-domain registration in the
bundled forwarder. The exporter sends an ordinary RFC 3954/RFC 7011 packet;
the forwarder attaches the registered metadata to its decoded copy before
HEC delivery.

## Simulation state and clock

The existing `ScenarioStateStore` remains the authority for correlated SNMP
and gNMI state. A correlated run has one run ID, scenario ID, entity ID, seed
and ordered phase sequence. Protocol adapters project that shared state rather
than creating unrelated incidents. Flow and Syslog correlation remains
out-of-band at the collector boundary.

NetFlow v9 sequence accounting was corrected to increment once per export
packet as required by RFC 3954. IPFIX continues to count exported data
records.

## Docker topology

The supported deployment remains:

```shell
docker compose up -d
```

| Service | Responsibility | Health evidence | Exposed port |
| --- | --- | --- | --- |
| `splunk-netspout` | Splunk, NetSpout API/UI, native runtime | HEC endpoint plus API health | 8000, 8081, 8088, 8089; Syslog 514 UDP/TCP |
| `netspout-flow-collector` | GoFlow2 NetFlow v9/IPFIX receive and decode | Prometheus metrics endpoint | loopback 2055/UDP, 4739/UDP, 8080 |
| `netspout-flow-forwarder` | Decoded Flow → destination adapter | status, counters and last error | loopback 8082 |
| `otel-collector` | OTLP logs/metrics receiver | health extension on loopback | 4317, 4318, loopback 13133 |

Internal service addresses are orchestrated by Compose and are not normal
Connection Center inputs.

## Third-party components

| Project | Version / image | License | Purpose | Modification |
| --- | --- | --- | --- | --- |
| GoFlow2 | `netsampler/goflow2:v2.2.5` pinned by digest | BSD-3-Clause | NetFlow v9/IPFIX receive and decode | Unmodified image |
| OpenTelemetry Collector Contrib | `0.96.0` | Apache-2.0 | OTLP logs/metrics receive and processing | Unmodified binary in a health-enabled wrapper image |
| Net-SNMP | Distribution-pinned package | BSD-style Net-SNMP license | SNMP receiver and independent CLI polling | Unmodified package |

Required notices and source links must remain in the repository licensing
audit; no third-party source was silently vendored.

## Capability classification

| Capability | Classification | Strongest live evidence |
| --- | --- | --- |
| Syslog RFC 5424 / UDP | SUPPORTED | Generated 1, UDP sent 1, exact raw receiver observation 1, HEC accepted, authenticated Splunk observation 1 |
| Syslog / TCP | PARTIAL | Container input exists; the unified embedded receiver journey proves UDP, not an equivalent TCP receiver boundary |
| SNMPv2c Trap | SUPPORTED | BER generation/send, bundled receiver decode, HEC dispatch and Splunk observation |
| SNMPv2c Inform | SUPPORTED | 4 informs acknowledged in the live standalone run; receiver and Splunk evidence remained distinct |
| SNMP GET/GETNEXT/GETBULK/Response | SUPPORTED | Bundled agent/poller and OID-store regression plus clean-container end-to-end run |
| gNMI Capabilities/Get/Subscribe | SUPPORTED | Canonical protobuf over gRPC/HTTP2; live generated 7, collector received 122, Splunk observed 434 |
| gNMI Set | UNSUPPORTED | Intentionally rejected; no Set claim |
| NetFlow v9 / UDP | SUPPORTED | Binary template/data send, GoFlow2 collector/decode and HEC-indexed record |
| IPFIX / UDP | SUPPORTED | Binary template/data send, GoFlow2 collector/decode and HEC-indexed record |
| OpenTelemetry logs/metrics | PARTIAL | Bundled collector health is proven; independent OTLP-to-Splunk observation is not |
| OpenTelemetry traces | UNSUPPORTED | No configured or tested traces pipeline |

## Evidence semantics

- Syslog: `GENERATED → UDP_SENT → RECEIVER_OBSERVED → NORMALIZED →
  SPLUNK_DISPATCHED → SPLUNK_OBSERVED`.
- SNMP: `GENERATED → BER_ENCODED → UDP_SENT → RECEIVER_OBSERVED → DECODED →
  SPLUNK_DISPATCHED → SPLUNK_OBSERVED → VALIDATED`; Inform also requires
  `ACKNOWLEDGED`.
- gNMI: `TARGET_STARTED → SUBSCRIPTION_ESTABLISHED → UPDATE_RECEIVED →
  NORMALIZED → SPLUNK_DISPATCHED → SPLUNK_OBSERVED → VALIDATED`.
- Flow: `TEMPLATE_SENT → DATA_SENT → COLLECTOR_OBSERVED → DECODED →
  FORWARDED → SPLUNK_OBSERVED`.
- OTel: `OTLP_ACCEPTED` is not promoted to backend or Splunk observation.

UDP send is never treated as delivery proof.

## Pipeline health and preflight

Pipeline health reports individual components using only:
`RUNNING`, `REACHABLE`, `READY`, `DEGRADED`, `FAILED`, and
`NOT_CONFIGURED`. A process or import alone cannot produce `READY`.
Splunk HEC and authenticated Splunk search are separate checks.

Preflight evaluates every required source binding. A required failed channel
blocks the run; an optional failed channel yields `READY_WITH_WARNINGS`.
Simple Mode hides collector endpoints. Advanced Mode exposes read-only
transport, receiver, encoding, evidence and failure details without exposing
credentials.

## Tests and exact results

- Full Python regression: **486 passed, 1 skipped, 58 subtests passed** in
  106.78 seconds. The suite emitted 2,317 inherited deprecation warnings.
- Final focused Phase 5/backend matrix: **49 passed**.
- Final runtime facade/unified workflow subset after mirror synchronization:
  **23 passed**.
- Final post-hardening correlation/observation subset: **23 passed**.
- Frontend production build: passed.
- Frontend lint: passed with 12 inherited warnings and no error.
- Phase 5 Playwright component journeys: **4 passed**.
- Guided Scenario plus Phase 5 frontend journeys: **8 passed**.
- Live screenshot journey: **1 passed**; focused failure and recovery captures
  each passed with the non-applicable live test skipped.
- Historical Flow tests now consume runtime credentials rather than a
  committed password literal; the three live Flow checks passed after this
  correction.

## Live Docker acceptance

A clean, uniquely named volume set was started with
`docker compose up -d --build --force-recreate`; no existing user volume was
deleted.

- Journey A — Syslog: PASS. Native UDP receiver observed the exact raw
  payload, HEC accepted the normalized observation, and authenticated search
  observed the run.
- Journey B — SNMP: PASS. The live run generated 8 notifications,
  acknowledged 4 informs, exercised polling responses, dispatched to HEC and
  produced indexed source-scoped evidence.
- Journey C — gNMI: PASS. The target and bundled subscriber completed
  Capabilities/Get/Subscribe-backed execution; the UI reported 7 generated,
  122 collector-received and 434 Splunk-observed records for the run.
- Journey D — NetFlow v9: PASS. GoFlow2 independently observed and decoded the
  template/data packet; the forwarder delivered it and authenticated Splunk
  search found the observation-domain record.
- Journey D — IPFIX: PASS with the equivalent template/data/collector/search
  boundary.
- Correlation: PASS. Final run
  `e4e1001d-d8ab-4811-bead-67f41dea437b` used seed `905`, one
  `ScenarioStateStore`, one simulation clock, entity `cisco-asr9k-pe1` and
  interface `HundredGigE0/0/0/1`. SNMP and gNMI reported the same clock state
  (`2026-10-06T17:40:59.350876Z`) and validated all four ordered
  baseline/degradation/failover/recovery states. SNMP generated/encoded/sent
  8 notifications, acknowledged 4 informs, and Splunk observed 326 normalized
  trap/poll records. gNMI generated 4 lifecycle states, the subscriber
  received 80 protocol updates, and Splunk observed 212 event records. Every
  required source-scoped scenario validation was `PROVEN`, and the final run
  state was `OBSERVED`.

The final clean stack health was:

- Syslog receiver: READY
- SNMP receiver: READY
- gNMI subscriber: READY
- NetFlow v9 runtime: READY
- IPFIX runtime: READY
- OTel runtime: NOT_CONFIGURED
- Splunk HEC: REACHABLE
- Splunk authenticated search: READY

## Failure and recovery

The GoFlow2 service was deliberately stopped. Pipeline Health changed both
Flow channels to `DEGRADED`, and IPFIX preflight returned `BLOCKED`; no
receiver or Splunk success was fabricated. Restarting the collector and
forwarder restored both channels to `READY`. Container existence was never
used as readiness proof.

## Screenshots

All screenshots were captured from the live Docker API; unsupported OTel
operation was not manufactured:

1. `images/phase5-01-pipeline-health.png`
2. `images/phase5-02-multi-telemetry-ready.png`
3. `images/phase5-03-native-topology.png`
4. `images/phase5-04-telemetry-lens.png`
5. `images/phase5-05-splunk-lens.png`
6. `images/phase5-06-scenario-preview.png`
7. `images/phase5-07-advanced-diagnostics.png`
8. `images/phase5-08-protocol-preflight.png`
9. `images/phase5-09-correlated-ready-to-run.png`
10. `images/phase5-10-splunk-observation.png`
11. `images/phase5-11-syslog-runtime.png`
12. `images/phase5-12-snmp-runtime.png`
13. `images/phase5-13-gnmi-runtime.png`
14. `images/phase5-14-netflow-runtime.png`
15. `images/phase5-15-ipfix-evidence-inspector.png`
16. `images/phase5-16-deliberate-collector-failure.png`
17. `images/phase5-17-recovery.png`

## Security and privacy

- No new credential, token, private key or certificate literal is introduced.
  Runtime credentials are supplied through environment/configuration and are
  not returned to the UI.
- Existing demo credentials and local TLS exceptions remain inherited Phase 0
  defects unless separately remediated and tested.
- Newly generated runtime fixtures use documentation IP ranges, `.example` or
  `.invalid` DNS names and deterministic fictional identifiers.
- The generated gNMI test chain was inspected on 2026-10-06. CA, server and
  client certificates were valid from 2026-10-06 through 2026-10-13, used
  RSA-2048 public keys and SHA-256 signatures. The CA was intentionally
  self-signed; server and client certificates were CA-signed. This ephemeral
  chain is suitable only for local testing and is never a public-production
  trust claim.

## Unresolved limitations and Phase 6 recommendation

- OTel remains PARTIAL and has no traces or independent Splunk observation
  claim.
- Unified native lifecycle adapters intentionally accept one lifecycle per
  run; unsupported count/duration and native Single Event requests fail
  closed. Existing modeled RFC 5424 four-mode behavior remains available.
- Syslog TCP has not reached the same unified receiver proof as UDP.
- Native contracts and collector-normalized records are not CIM claims.
- Existing local demo credentials and inherited TLS exceptions remain Phase 0
  defects outside this phase's remediation scope.
- The generated gNMI chain is local-test-only and intentionally uses a
  self-signed CA.

Recommendation: Phase 5 meets its bounded acceptance scope. Keep OTel and
Syslog TCP at their documented non-supported classifications, and do not begin
Phase 6 until explicit authorization.
