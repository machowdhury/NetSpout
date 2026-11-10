# Phase 17 — validation matrix (Splunk 10.6.1 primary, 10.2.7 compatibility)

Artifact `netspout.spl` sha256 `4bf1d21469f5e699069797d654f7ccc57e00fbcade9b9304dcccdab2bd33be40` (15,972,349 bytes), source commit `91af353`. v2.0.1 (sha256 `53f09e5f…ff17`, the GitHub pre-release asset) is unchanged.
**Host: an arm64 Mac running the `linux/amd64` Splunk image under emulation. Native Linux x86_64 was NOT available, so no result here is a native-x86_64 result.** The same Docker host also ran an unrelated Splunk evaluation container that used about one CPU core throughout, so timings and throughput are unreliable. Evidence is kept apart by version: `docs/verification/evidence/phase17/splunk-10.6.1/` and `.../splunk-10.2.7/` (older artifact: `splunk-10.2.7/previous_artifact_3ea5aface/`).

## Runtime compatibility (measured, not assumed) — `splunk-10.6.1/runtime_probe.json`

| | 10.2.7 | 10.6.1 (10.6.1.1, build b2ae2962645c) |
|---|---|---|
| Embedded Python | 3.13.11 (3.9 also present) | 3.13.11 (3.9.25 also present) |
| OpenSSL | 3.0.21 | **3.5.9** |
| protobuf / grpc / cryptography / PyYAML | 6.32.0 / 1.74.0 / 44.0.2 / 6.0.2 | **6.33.6** / 1.74.0 / 44.0.2 / 6.0.2 |
The bundled wheels (cp313, manylinux x86_64) loaded and ran on both. The differences did not require code changes, but they are why 10.6.1 was tested in full.

## Results

| Gate | 10.6.1 (primary) | 10.2.7 (compat) |
|---|---|---|
| Install only `netspout.spl` through Splunk Web, no external engine; 1 launcher + 1 engine, no new listening port | pass | pass |
| First-run configuration in the Splunk Web UI + tested connection + Generate Data from the UI ("found 10 of 10") | pass | pass |
| Cisco ASA, Cisco IOS, Fortinet, Palo Alto traffic/threat/system events (independent search) | 6/6 | 6/6 |
| IOS XR metrics, independent `mstats` | pass | pass |
| Palo Alto scenario + dashboard searches | pass | pass |
| Streaming start/stop/duration, caps (200 eps, 3,600 s), no run without authorization | 6/6 | 6/6 |
| Unauthenticated / no-capability / viewer / admin / power; secrets never returned | 10/10 | 10/10 |
| Credential persistence (engine kill, launcher kill + recovery, `splunk stop`/`start`, restart) | pass | pass |
| Zero unsolicited telemetry (events indexed in 3-min windows, all non-internal indexes) | fresh unconfigured, after upgrade, after runs + lifecycle + sustained load: all 0 | fresh unconfigured and after upgrade: 0 |
| Upgrade from released v2.0.1 through Splunk Web (local config byte-identical, managed engine takes over, workflows pass afterwards) | pass | pass |
| Uninstall | 0 processes, data kept, state directory left | same |
| Browser (headless Chromium) | 4 passed | 4 passed |
| **Sustained at the 200 events/s ceiling** | 15 min requested: 132,350 events, **147 events/s achieved (ceiling not reached)**, 0 rejected, all indexed and verified; engine RSS 216 → 287 MB then flat from minute 8; splunkd ≤ 503 MB; search latency 0.03–0.37 s | 5 min requested: 16,975 events, **57 events/s achieved**, 0 rejected, all verified; engine RSS 217 → 242 MB |
| **AWS native x86_64, Splunk 10.6.1.1** (m6i.2xlarge, ca-central-1, Docker 29.1.3, tested package gzip `d28719f3…`, tar content identical to approved `99c23bbb…`) | install via Splunk Web, restart, census, 0 idle events (fresh / after runs / after upgrade), browser 4/4, events/metrics/scenario/stream/authz, engine kill, launcher recovery, Splunk stop/start, restart, upgrade from v2.0.1 (local config identical), uninstall (0 processes, state dir left): **all pass** | |
| **Sustained at the 200 events/s ceiling, native, 3,600 s** | 448,075 events, **124.5 events/s achieved (ceiling NOT reached; criterion ≥190 FAILED)**; 0 rejected, 0 dropped, all indexed within 0.1 s of the last send; engine at ~92% of one core (the engine is single-process and CPU-bound); engine RSS growth 0.3%, splunkd 4.1%; 0 restarts; search latency 0.03-0.15 s; 6 HttpListener WARNs in the window | |

## Not met / open

- **200 events/s was not reached on native hardware either**: 124.5 events/s over the full 3,600 s on an m6i.2xlarge, with the engine saturating one core. The supported ceiling must be stated as ~120 events/s per engine, or the engine must be made faster, before any release. (Earlier emulated runs: were limited by emulation and by the competing container. They show no loss, no leak plateau problem within 15 minutes and Splunk staying responsive, but they do **not** validate the 200 events/s ceiling or the 3,600 s cap. This gate needs a native host.)  The 3,600 s run itself was loss-free and stable.
- Native x86_64 ran once, on one instance. No distributed Splunk, Windows, macOS, aarch64, Splunk Cloud, Python 3.9.
- AppInspect 4.4.0 (artifact `4bf1d214…`): baseline v2.0.1 **8** failures, new package **9** (same 8 plus `check_aarch64_compatibility`: three x86_64 `.so` files). Cloud tag: 8 and 8. The package is not suitable for Splunkbase or Splunk Cloud.
- Regression: 9 failed / 4110 passed / 5 skipped on the Phase 16 selection plus the files touched here; the 9 are the known v2.0.1 failures.
- The 10.2.7 upgrade and 10.6.1 stop/start/uninstall each ran once, on one container.
- Uninstall leaves `$SPLUNK_HOME/var/lib/netspout`; a killed launcher is restarted only by Splunk's next start or by Restart engine; saving credentials needs `edit_storage_passwords` (admin).

## Gates before any merge or release

1. Either raise engine throughput to ≥190 events/s (it is CPU-bound at ~125) or lower the documented and enforced ceiling to what was measured; native 10.2.7 is still untested.
2. Review of the AppInspect failures and the self-distribution decision.
3. Review of the support statement and release notes drafts (`SUPPORT_STATEMENT.md`, `RELEASE_NOTES_DRAFT.md`).

## AWS run deviations (recorded, not hidden)
- First launch blocked by an organization SCP until the `splunkit_data_classification=private` and `splunkit_environment_type=non-prd` tags were added; partial resources were cleaned.
- Census step printed FAILED once because Splunk's own listeners (5433/5434/6432) appeared after the "before" snapshot; a direct socket listing shows the engine only on its Unix socket.
- Regression: harness needed `git init` (2 tests need a repo). Selection: 9 failed / 4108 passed (the known 9). Full tree excluding live-lab tests: 33 failed vs 30 on main; the one PR-only failure, `test_get_routes_never_return_configured_secrets`, fails only under the 30 s timeout cap and passes alone with a 600 s timeout.
- Tested gzip differs from the approved one (zlib build difference); tar contents are identical.
- Cleanup initially read a new, empty state file because the date rolled over at 00:00 UTC; it deleted nothing, I re-ran with the original run name and verified instance, volume, security group, role, profile and bucket are gone and 0 tagged instances remain.
