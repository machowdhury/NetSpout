# Universal Vendor Coverage Batch 2 — 2026-10-26

Continues `b1ad10ab26adc4bc4c256431f15aae1ba3cc13ad` on
`oc/ise-ta-1915-record`. Existing discovery reused; no ecosystem rescan.

| Canonical dimension | Before | Added | After |
| --- | ---: | ---: | ---: |
| Vendor/product-family registry rows | 57 | 9 | 66 |
| Product integrations in this batch | — | 9 | — |
| Sourcetypes | 317 | 9 | 326 |
| Source-registry event-family instances | 163 | 18 | 181 |
| Scenarios | 41 | 3 | 44 |

Vendor rows are technology identities, not independent parent corporations.
NGINX is an F5 product identity; the older BIG-IP row remains separate. There is
no canonical product table: nine product integrations are implementations, not
nine newly discovered products in the global ecosystem. Family instances are
not a globally deduplicated event taxonomy.

## Sources and evidence

| Product | Canonical sourcetype | Implemented families | Evidence |
| --- | --- | --- | --- |
| HashiCorp Vault | `hashicorp_vault_audit_log` | audit request, audit response | Pinned integration RAW |
| Traefik Proxy | `traefik:access:json` | HTTP access | Pinned integration RAW |
| Claroty CTD | `claroty:cef` | new asset, asset information change, health | Pinned integration RAW, extracted from `event.original` |
| MongoDB server | `mongodb:log` | server startup, index build | Pinned integration RAW |
| Confluence Cloud | `Confluence:audit log` | space creation, group membership added | Pinned integration RAW |
| NGINX | `nginx:access` | combined HTTP access | Pinned integration RAW |
| Proofpoint TAP | `proofpoint_tap_siem` | blocked malware message, blocked phishing message | Pinned integration RAW |
| Veeam Backup & Replication | `veeam_vbr_syslog` | backup started, backup completed, malware detected | Pinned integration RAW |
| MikroTik RouterOS | `mikrotik:routeros` | administrator login, OSPF hello transmission | Vendor-documented console records |

Eight sources use public `elastic/integrations` native test fixtures, pinned to
`37ef1a028f3cc4b049779fa20578f7ee6f3cddbe`. These are integration-test examples,
not independently captured production traffic. One source uses small native
RAW excerpts from the vendor's RouterOS Log documentation. **Zero sources rely
only on a generic standard without a native example.** Paths, hashes, upstream
license notice and exact extraction selectors are retained under
`catalog/raw_reference/universe_batch2/` and `catalog/universe_batch2.json`.

Every supported family has an executable formatter and a selector-linked
fixture. JSON structures, native event codes and message grammar are preserved;
time and permitted identity/address fields vary. RAW contains no NetSpout
correlation fields or ECS wrappers. Veeam's record is a native message body:
record time is metadata; an existing `DetectionTimeUTC` is updated when present.
RouterOS examples are console grammar, not remote syslog conformance evidence.
HashiCorp coverage is Vault secrets/audit, not a claim of additional cloud
provider control-plane coverage. Carrier routing is represented by OSPF;
cellular PPP/LTE/5G families are not claimed.

Six sourcetype names are declared by the selected frozen Splunkbase app records.
MongoDB server, NGINX access and RouterOS console mappings are explicitly
PulseForge-defined pending TA mapping. A metadata declaration does not establish
input-format compatibility. Technology vendors remain distinct from publishers:
for example the Traefik add-on is published by Mathieu Hanotaux, Confluence's by
Avotrix, and Veeam's by Matthew Orme; these publishers were not promoted to vendors.

## Executable behavior and dispatch

| Pack | Events | Behavior |
| --- | ---: | --- |
| `ub2_cloud_identity_mail_hunt` | 6 | Vault request/response, Confluence changes and TAP blocked-message observations |
| `ub2_ot_edge_routing_observation` | 7 | RouterOS login/OSPF, Traefik, CTD asset/health observations and NGINX access |
| `ub2_database_backup_integrity` | 5 | MongoDB startup/index, backup lifecycle and Veeam malware observations |

Each pack executes BASELINE → OBSERVE → VALIDATE, has unique event IDs and an
ordered parent chain in returned metadata. The sequence is synthetic; it does
not prove causal intrusion, recovery, detection efficacy or live device state.

Canonical sourcetype, single-event and data-source generation now route Batch 1
and Batch 2 sources through their engines. Family/vendor mismatches fail closed.
Batch generation cycles only requested supported families, with a 1–1,000-event
bound. Existing code called a nonexistent `dispatch_log_entry` method; routing
now uses the actual `dispatch_log` interface. Tests exercise the real dispatcher
up to its mocked network boundary and assert RAW/HEC-field separation.

Observation packs are exposed through **`POST /api/generate/scenario-pack`**:

```json
{"scenario_id":"ub2_cloud_identity_mail_hunt","dispatch":false}
```

Dispatch requires explicit transport configuration. Invalid source families
return HTTP 400. The canonical `/api/generate/scenario` graph-runner refusal
guard remains intact. These packs do not claim support in that graph runner or
its native UI lifecycle. The implementation and mirrors are committed locally;
no application or TA was installed into the lab.

## Current live evidence — separate from parsing and detections

The existing healthy `pf-native-lab`, `pf-ta-ise-val` HEC input and
`idx_ta_ise_test` were reused. Credentials stayed inside the container and are
absent from logs, results and commits. No token or Splunk configuration was changed.

| Check | Posted / indexed / exact-byte PASS | Sourcetypes |
| --- | --- | ---: |
| Current Batch 1 | 7 / 7 / 7 | 4 |
| Current Batch 2 | 18 / 18 / 18 | 9 |

Batch 1 run: `pf-ub1-current-b2f2e962-d45d-4543-9121-b08d68ccc17c`, two search polls.
Batch 2 run: `pf-ub2-current-11501fb3-dfb7-49b7-83ff-6dcc3a031f93`, one search poll.
All 25 checks match submitted/indexed UTF-8 byte lengths, SHA-256 hashes and
sourcetype; no correlation leakage. Live result files record current engine
hashes, matching final committed engine bytes. Full submitted synthetic payloads
are retained here. HEC metadata adds verification labels; this checks RAW
transport fidelity, not indexed scenario parent-chain semantics or native timestamp
parsing. No current check is substituted with the historical Batch 1 summary.

**Installed-TA parser verification: 0 new, 1 historical overall.** Read-only app
inventory found `Splunk_TA_cisco-ise` 5.0.0; no Batch 2 required TA was installed
or exercised. Every new source retains its parser blocker. No additional parser
compatibility or CIM claim is inferred from HEC RAW equality. **Detection
validation: 0**, no ESCU/CIM or detection configuration changes.

The historical all-wave RAW-equality union is 65 sourcetypes. Only 13 distinct
sourcetypes received current-byte checks in this batch; the other historical
records are not represented as fresh validation.

## Validation and regression comparison

- Focused integration suite: **199 passed, 1 skipped, 154 subtests passed**, exit 0.
- Cisco RAW and serialization contracts: **19 passed**, exit 0.
- Total: **218 distinct tests passed**, one skip. The skipped generic HEC test
  requires `NETSPOUT_HEC_TOKEN`; the separate isolated-lab live checks above ran.
- Vendor-universe checks rerun after ordering repair: **10 passed**; this repeats
  tests already counted above and is not added to the distinct-test count.
- Catalog validation and source/mirror audit: exit 0. All nine new sources are
  scenario-referenced. Existing catalog orphan count stays 42; zero orphan vendors
  and zero orphan topologies.
- A second offline rebuild and synchronization left **187 checked catalog JSON
  files byte-identical**. Sorting declared-sourcetype references fixed unstable
  ordering among tied crossmap counts.
- Frozen PAN formatter ASTs match the Batch 1 baseline exactly.

`validation.json` records commands, actual exit statuses, JUnit outputs and gate
logs. It compares failing identities with the preserved **69-entry Wave 3 list**
(69 failed / 1,025 passed / 10 skipped). Final focused failure identities: none.
An introduced canonical-API guard regression was caught at
`tests/test_fallback_guard.py::TestFallbackGuard::test_api_refusal` for four pack
IDs and fixed by using the explicit pack endpoint; the guard was not weakened.
The broader 69 baseline failures were not rerun or claimed fixed. No broad
background pytest was used.

## Remaining queue

The unchanged 1,871-row Splunkbase snapshot remains the discovery denominator;
this is not global exhaustive vendor coverage. Its 853 publisher spellings
normalize to 848. `catalog/vendor_universe/batch2_candidate_queue_baseline.json`
and Batch 2's registry retain **all original 66 vendor and 583 product candidates**.
Nine vendors are marked `IMPLEMENTED_LIMITED_FAMILIES`; every other input remains
visible as unassessed or evidence/TA blocked. The current derived active queue
has **57 vendor keys**. Its derived product count is 566 because classification
moves implemented entries; the original 583 candidates are preserved, not discarded.

Leading remaining keys include Cisco other, IBM QRadar, PAVO Metrics,
Trellix/McAfee, Akamai, Oracle, Tenable, Vectra AI and BeyondTrust. Specific blockers:

- Trellix ePO, Illumio and Proofpoint PDS: earlier native RAW gaps retained.
  TAP coverage does not cover every Proofpoint product.
- CyberArk PAS: fetched example uses a custom Elastic JSON output template;
  retained as rejected research evidence, excluded from native coverage.
- Corelight / IBM MQ: selected fixture paths were unavailable in the bounded
  lookup; this is not proof no public evidence exists.
- Veeam: the selected native backup and malware fixtures unblock three families,
  not the full product portfolio. All other newly implemented vendors also remain
  limited to the named families.
- RouterOS cellular/PPP/LTE/5G, Batch 1 Docker volume and Nozomi threat-command
  families: unsupported examples remain blocked. No quota-based formats invented.
- All new installed-TA parser checks and detection validation remain outstanding.

## Rebuild

Offline, no discovery or lab access:

```sh
.venv-test/bin/python scripts/build_universe_batch1_registry.py
.venv-test/bin/python scripts/build_universe_batch2_catalog.py
.venv-test/bin/python scripts/build_vendor_universe.py
.venv-test/bin/python scripts/sync_core.py
.venv-test/bin/python scripts/verify_sources.py
.venv-test/bin/python scripts/validate_catalog.py
```

Exact pytest commands are in `validation.json`; set `PYTHONPATH=src:backend`.
`fetch_universe_batch2_references.py` is an explicit, bounded public-fixture
refresh, not part of runtime or offline builds. `verify_universe_raw_live.py
--batch 1` and `--batch 2` explicitly ingest new bounded test events; do not run
them merely to rebuild mirrors. No push, merge, reset, cleanup, TA installation,
Splunk configuration change or paid external API was performed.
