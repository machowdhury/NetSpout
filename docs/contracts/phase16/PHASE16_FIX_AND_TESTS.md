# Phase 16 — the fix and its tests

Tested commit: `97006de92b7f9098bfcb3feea59aa1bde86d879d` (branch `fix/phase16-idle-telemetry`, one commit on `origin/main` `856418b`). Later commits on the branch change documentation only.

## Invariant

A fresh NetSpout installation produces zero synthetic telemetry unless generation has been explicitly authorized. Three different things must not be confused:

| situation | what happens |
|---|---|
| **Idle installation** (default) | nothing is generated: no event, no metric, no running generator. Splunk may start the streamer script at (re)start; it exits at once, silently |
| **Explicitly enabled legacy input** (an admin sets `[netspout_streamer://default] disabled = 0` in `local/inputs.conf`) | the legacy streamer generates its multi-vendor stream into the configured index, as documented; it keeps doing so until the admin removes the setting. The fix never enables or disables it |
| **User-initiated PulseForge run** (Generate Data, Scenarios, streaming through the engine and gateway) | generated only for that run, tagged with its run id, verified by independent search; unaffected by the fix |

## Files changed (5)

| file | change |
|---|---|
| `netspout/bin/netspout_streamer.py` | `parse_input_config()` returns settings only when Splunk passed an enabled `netspout_streamer://` stanza, else `None` (missing, empty, other-scheme or unparsable input is never authorization); new `read_input_xml()` waits up to 30 s for the `<input>` document; `run_input()` returns silently without a stanza. `--test` / `--dry-run` remain an explicit one-cycle request. Scheme unchanged |
| `netspout/default/eventgen.conf` | every sample ships `disabled = true` (34 stanzas), header explains how to enable one deliberately in `local/eventgen.conf` |
| `netspout/default/inputs.conf` | comment stating the policy (both inputs ship disabled; no automatic generation) |
| `tests/test_phase16_idle_telemetry.py` | 11 tests (below) |
| `scripts/phase16_idle_check.py` | live idle checker with attribution and a control index |

The Cloud package and the engine archive are byte-for-byte the same members as before; the Enterprise package differs in exactly the three `netspout/` files above.

## Tests

**Unit and static (no Splunk), `tests/test_phase16_idle_telemetry.py`:** every shipped input is disabled; every eventgen sample is disabled; the scheme stays valid for Splunk (single-instance, `interval` declared); no other scripted/monitor/network input ships; empty stdin, a document without a stanza, another scheme's stanza and an unparsable document all emit nothing and exit by themselves (the normal cases also write nothing to stderr); an enabled stanza generates; `--test` is explicit; and, when a built `netspout.spl` exists, the package ships no enabled input or sample and contains the check. Negative control against `origin/main`: the old streamer is still running after 8 s and has emitted 10 KB with no stanza (`evidence/phase16/streamer_unit_control.json`).

**Live, in disposable Splunk 10.2.7 Docker labs, attribution method.** An event counts as NetSpout-generated if its source starts with `netspout:`/`pulseforge` or it carries `netspout_run_id`, in **any** index, from the beginning of time; plus the app indexes' totals, metric datapoints, running generator processes and `splunkd.log` launches. A **control index** receives 5 canary events in every lab so a zero is a real zero, not a broken search. Measured before installation, after installation, after restart and after upgrade (`evidence/phase16/live_*.json`):

| step | NetSpout-attributed events | generator process | result |
|---|---|---|---|
| Unfixed `origin/main` 2.0.1, idle 30 min | **3,231** | running | defect reproduced |
| Archived 2.0.0, a few minutes | 342 | running | defect pre-exists |
| **Fixed**, fresh lab, empty Splunk before install | 0 (control 5) | none | baseline |
| Fixed, after install + restart | 0 | none | PASS |
| Fixed, idle 10 minutes | **0 new** (0 total) | none | PASS |
| Fixed, after `docker restart` of Splunk, 3 min | 0 new | none | PASS |
| Fixed, after container **recreation** with persisted volumes (control index still 5), 3 min | 0 new | none | PASS |
| Upgrade 2.0.0 → fixed 2.0.1, default config, 5 min | **0 new** (351 historic events untouched) | none | PASS |
| Upgrade data/config check (events 120/40, 30 metric datapoints, saved search, dashboard, custom config, `local/` file hashes) | all unchanged | | PASS |
| Legacy streamer **explicitly enabled**, fixed build, 3 min | 333 new (about 108 per minute, source `netspout:streamer`) | 1 | documented behaviour |
| Legacy input removed again + restart, 3 min | 0 new | none | PASS |
| After the full packaged acceptance (user runs), idle 3 min | 0 new; 0 events with `source="netspout:streamer"` | none | PASS |

Explicit generation, packaged UI → gateway → engine → HEC → independent search, on the fixed build: **29/29** (single source ASA/IOS/FortiGate/PAN, four sourcetypes together, events plus IOS XR metrics, streaming start/stop, the Palo Alto scenario with its dashboard, and the failure cases). Install checks 20/20. No `ERROR` line for the streamer in `splunkd.log` after the fix.

## Regression results (candidate `v2.0.1-fix-b1-97006de`)

| gate | result |
|---|---|
| Package audit (3 archives, git provenance, allowlist) | 0 findings |
| `verify_sources.py` mirrored-core guardrail | PASS |
| Strict release tests (`NETSPOUT_STRICT_BINARIES=1`: release consistency, idle telemetry) | PASS (18 passed: release consistency + idle telemetry) |
| Install checks | PASS 20/20 |
| Packaged browser acceptance | PASS 29/29 |
| Source browser regression | PASS 26/26 |
| Focused Python selection (39 files + the new test file) | 9 failed, **4072 passed**, 2 skipped: exactly the established nine, **no new failure** (the nine remain failures) |
| `tests/test_cloud_package.py` (not in the selection; run for completeness) | 1 failure, **pre-existing**: fails identically on unmodified `main` `856418b` (372 packaged views vs 148 maturity entries); unrelated to B1 |

## Legacy-compatibility statement

An input that an administrator explicitly enabled before the upgrade (in `local/inputs.conf`) is **kept enabled** and keeps generating, exactly as in 2.0.0: the upgrade does not enable, disable or rewrite it (`local/inputs.conf` hash identical after upgrade). It is now identifiable and stoppable (see `PHASE16_RELEASE_IMPACT.md`). A stanza that only exists with `disabled = 1`, including the shipped one, no longer produces anything.

## Process-incident follow-up (legacy 2.0.0 lab isolation)

Lab containers could reach host loopback services through `host.docker.internal` (this is how the 2.0.0 fallback reached port 8081 in Phase 15). The lab template now maps `host.docker.internal` and `gateway.docker.internal` to `192.0.2.1` (RFC 5737, never routed). Verified with a **decoy** listener on an unused host port, so the protected demo's port was not probed: an unisolated lab reached the decoy (200); the isolated lab did not, by either name or the IPv6 address, causing zero decoy hits, and the 2.0.0 gateway's no-engine `/health` got no answer (`evidence/phase16/legacy_lab_isolation_check.json`). The lab harness is on branch `phase16/lab-harness` (not part of this fix).
