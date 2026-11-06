# Phase 16 — release impact, upgrade instructions and decisions

Candidate (not published): `~/netspout/release-candidates/v2.0.1-fix-b1-97006de/`, built from commit `97006de92b7f9098bfcb3feea59aa1bde86d879d` in a fresh clone (npm ci, virtualenv with only `backend/requirements.txt`, Python 3.15.0; `git status` empty afterwards). Product version is still 2.0.1; the identity of this build is its directory, commit and checksums. Superseded candidates `…-f239de3` and `…-e9b7b52` are marked and must not be used.

| file | bytes | sha256 |
|---|---|---|
| `netspout.spl` | 7,530,156 | `53f09e5f8c16e6615ecd9c73c0504e9ac938fa28b0029313384be5f09105ff17` |
| `netspout_cloud.spl` | 709,799 | `84c2b22728a4f0447bed6812ecbdc3e7672fc3c0b9d14b7e572cfbd2729e4fd8` |
| `pulseforge-engine.tar.gz` | 10,544,275 | `b2a17065a25a5a49f974a54756d9dff251d6555efbb7bbc491002422cdce7fa1` |

`SHA256SUMS` (also the two `.manifest.json` files) verifies. Compared with the Phase 15 candidate (`v2.0.1-docker-856418b`): the Enterprise package differs in exactly `netspout_streamer.py`, `eventgen.conf` and `inputs.conf`; the Cloud package and the engine archive have identical members. Because the Cloud and engine content did not change, their hashes differ from Phase 15 only in archive metadata.

## What changes for customers

- A fresh install produces no data by itself. Nothing to configure.
- Only an explicitly authorized source writes data: a user's PulseForge run, or a legacy input an administrator enabled on purpose.

## Upgrade and rollback instructions (changes to the Phase 15 guide)

1. Install the new package over the old one, restart Splunk, set the engine address once under Connections > PulseForge Engine (unchanged from Phase 15), and upgrade the engine to the same build.
2. **Check for a previously enabled legacy input.** The upgrade never enables, disables or rewrites it. Look for it:
   - `$SPLUNK_HOME/bin/splunk btool inputs list netspout_streamer --debug` (an enabled one shows `disabled = 0` from a `local/` file), or
   - search `index=* source="netspout:streamer" earliest=-15m | stats count`; a non-zero count means it is running.
   To stop it, remove or disable the stanza in the app's `local/inputs.conf` and restart Splunk. To keep it, do nothing.
3. **Historic synthetic events stay.** Installs that ran 2.0.0 or the earlier 2.0.1 build already contain `source="netspout:streamer"` events in `idx_network_ops`. They are not removed automatically. Count them first: `index=idx_network_ops source="netspout:streamer" | stats count by sourcetype`. Deleting is an admin decision (`| delete` needs the `can_delete` role and is irreversible); it was not exercised here.
4. Rollback to 2.0.0 is unchanged from Phase 15 (data and settings survive) but **re-introduces the defect**: 2.0.0 starts generating again. A machine that must stay on 2.0.0 has no tested workaround; disabling the app was not tested.
5. If Splunk Eventgen is installed on the same Splunk, the app's samples no longer run by default (`disabled = true`). To use one on purpose, override `disabled = false` in `local/eventgen.conf`. **This path was not exercised live (Eventgen is not in the lab).**

## Remaining limitations

- Eventgen path: fixed and unit-tested, not exercised against a real Eventgen.
- Not tested in this phase, still open from Phase 15: non-Docker, distributed or clustered Splunk, other Splunk versions, TLS or VM-service engine, Splunk Cloud, Phase 15's full rollback suite on the new build (only the upgrade, restart, recreation and legacy-policy checks relevant to B1 were repeated).
- `tests/test_cloud_package.py` has one pre-existing failure on `main` (372 views vs 148 maturity entries), unrelated; the nine established Python failures are unchanged.
- The idle measurements cover 10 minutes fresh and 3–5 minutes elsewhere in Docker with the Splunk image emulated on arm64; they establish that no generator runs, not a multi-day soak.
- Splunk's own launches of the script at restart still appear in `splunkd.log` (it exits immediately and silently).

## Decisions

**GO to merge the B1 fix** (after your review of the draft PR): five files, no new scheduler, no architecture change; the defect is reproduced and removed with a control index proving the measurement; every Phase 15 gate relevant to it was re-run on the built fix (20/20, 29/29, 26/26, Python = the established nine, audit clean); the only behavioural change for existing installs is that nothing generates unless explicitly enabled.

**GO for a controlled Docker-based Enterprise release**, scoped to the tested configuration (single Splunk Enterprise 10.2.7 in Docker, customer-operated Docker engine, the four vendor add-ons of Phase 15) and conditional on (a) the fix being merged and the release artifacts being **rebuilt from the merged `main` commit** and their checksums recorded (the candidate above was built from the PR branch), and (b) the upgrade notes above going out with it. B1, the Phase 15 blocker, is closed. This is not a customer-release approval; that remains yours. General Splunk Enterprise compatibility and Splunk Cloud remain **NO-GO (not tested)**, unchanged.
