# NetSpout PulseForge 2.0.1 — limited support statement (Docker-tested Enterprise release)

Source commit: `5f172042d6b359572868195f5862ded02194b3ab` (merge of PR #8, main). Version 2.0.1. Nothing here is published; it describes the local candidate `v2.0.1-final-5f17204`.

## Artifacts (local, not uploaded)

| File | Bytes | sha256 |
|---|---|---|
| netspout.spl | 7,530,156 | `53f09e5f8c16e6615ecd9c73c0504e9ac938fa28b0029313384be5f09105ff17` |
| netspout_cloud.spl | 709,799 | `876b7d5cd68a2903a33abb420408e89a1f17b4e9a4c18c7b84edfff48f83ead1` |
| pulseforge-engine.tar.gz | 10,544,275 | `d8d515a6abe1fb80b8b525948d3084e13077b2943268fdbfc9063b056cb7ba94` |

`netspout.spl` is byte-identical to the build that passed the Phase 16 live tests (`v2.0.1-fix-b1-97006de`). The Cloud package and engine archive have the same file contents as that build and as the Phase 15 candidate; only archive bytes (build timestamps) differ, so their checksums differ. **Release assets are `netspout.spl` and `pulseforge-engine.tar.gz` only.** `netspout_cloud.spl` is built for completeness but is NOT a supported release asset and is not validated on Splunk Cloud; the two `.spl` files share app id `netspout` and must not be installed together.

## Tested

This release is not Splunk Cloud compatible and makes no such claim.

- Splunk Enterprise 10.2.7, single instance, in Docker (amd64 image emulated on an arm64 host).
- The PulseForge engine run by the customer in Docker (Python 3.13 image) next to Splunk.
- The validated workflows (Phase 15 A–F; packaged browser acceptance 29/29) and the Phase 15 add-on set.
- Fresh install, restart, container recreation, upgrade from 2.0.0 (data and configuration intact).

## Not validated

Splunk Cloud (including `netspout_cloud.spl` in a real Cloud stack); distributed or non-Docker Splunk deployments; other Splunk versions; engine on a VM, or behind TLS; multi-day soak behaviour.

## Behaviour customers can rely on

- **An idle installation produces no telemetry.** Measured across all indexes with a control index: 0 events after install, after a 10-minute idle window, after Splunk restart, after container recreation, and after an upgrade from 2.0.0. Splunk still starts the legacy script at each restart; it now exits silently without an enabled stanza.
- **Legacy inputs run only when explicitly enabled.** An enabled `[netspout_streamer://…]` stanza in `local/inputs.conf` generates events (333 per 3 minutes in the lab, with one process) and stops when removed. Upgrading does not enable it, and does not remove one an administrator already enabled.
- **A PulseForge run is a separate, user-initiated action** from the UI or API. It is the only way events get created without the legacy input.
- **Historic events are not deleted.** Synthetic events written by 2.0.0 or an earlier 2.0.1 build stay in `idx_network_ops`. Count them with `index=* (source="netspout:*" OR source="pulseforge*") | stats count by index, source`; deleting is an administrator decision.
- **Rolling back to 2.0.0 reintroduces the defect** (continuous generation at about 78 events a minute).
- **Eventgen:** all 34 shipped `eventgen.conf` stanzas ship `disabled = true`. This is unit-tested but not tested live (the lab has no Splunk Eventgen).

## Known test failures (accepted, unchanged by this release)

Python selection: 9 failed, 4072 passed, 2 skipped, the same nine on main before the fix:
- `test_gate6_integrity::test_07_successful_hec`
- `test_gate9_5_telemetry_semantics::test_01`, seven sub-failures: `ub1_ot_proxy_host_hunt`, `ub2_cloud_identity_mail_hunt`, `ub2_database_backup_integrity`, `ub2_ot_edge_routing_observation`, `ub3_database_message_audit`, `ub3_identity_runtime_audit`, `ub3_multivendor_edge_observation`
- `test_phase12_agentic_supply_chain::…test_dashboard_recipe_families_integrate_without_regression`

Separate, outside that selection: `tests/test_cloud_package.py::test_cloud_edition_contains_only_dashboards_navigation_and_metadata` fails (372 views packaged, 148 with maturity evidence). It is identical on main before this fix and concerns the Cloud package, which is not part of this support statement.

## Process note

An earlier 2.0.0 test in an unisolated lab reached a host service through `host.docker.internal`. The lab template now maps that name to an unroutable address, and the isolation was verified with a decoy listener (see `PHASE16_FIX_AND_TESTS.md`).
