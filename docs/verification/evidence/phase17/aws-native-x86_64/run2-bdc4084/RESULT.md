# AWS native x86_64 run 2: candidate bdc4084 (measured results only)

Run: ca-central-1, m6i.2xlarge, Ubuntu 24.04 amd64, Splunk Enterprise 10.6.1.1, no SSH key, 0 inbound rules, Session Manager. Started 2026-11-10 ~23:41 UTC.
Native package built on the instance, twice, identical: gzip `171837b0087587d8f488976358743c6aed5acc4861f11f5ae420542d1057c8ef`, tar `0904a5100825e3b9736c8752cf516e6e74d35d335a6227de2b4af0a758ee5394` (equals the local reference tar; the gzip differs only by zlib build; local gzip `2db9bb21b6f45f8ee5b977424cc72b90ee0a428db3c7e9dd9bc3501e456f83a1`).

## Sustained 3,600 s at 200 events/s
Attempted 720,025; independently indexed 720,025; rejected 0, unknown 0, dropped 0. Mean 200.0/s. Max 201 events in any second (p99 200; limit 230). Engine RSS 162-164 MB (no growth), engine CPU mean 29.5%, 0 worker restarts. Verdict: all six criteria pass (run 1: 124.5/s, fail).

## Harness defects, disclosed
1. `indexed_eps_per_full_minute` in `splunk-10.6.1.1/sustained_200eps.json` is wrong (min 25.1): the export helper kept preview rows as well as final rows. Original left untouched; `sustained_per_minute_corrected.json` uses final rows only (59 full minutes, each 200.0/s, sum 720,025 = independent count). The helper is fixed in the commit that adds this file; the fix was not re-run on AWS.
2. `single_package_install_census` records `ok=false` (fresh and after upgrade; run 1 identical). Ports 5433/5434/6432 appear about 2 minutes after Splunk starts. A control (stock Splunk 10.6.1, no NetSpout, no published ports) showed the same ports, so this is Splunk's own startup services and a timing artifact of the census's early "before" snapshot. The app's engine listens on a Unix socket and exactly 2 app processes were seen. The step shows PASS in `steps.log` only because the script exits 0.
3. Splunk logged 7 HttpListener WARN lines in the run window (run 1: 6). Message text was not captured. 0 events were rejected and all were indexed. Uncharacterised.

## Lifecycle (21 steps, 0 FAIL in steps.log)
Install via Splunk Web, restart, idle (0 events, 3 min) fresh / after load / after upgrade, browser spec, acceptance, engine kill and recovery, stop/start, v2.0.1 then upgrade via Splunk Web, uninstall.

## AppInspect 4.4.0
Baseline v2.0.1 8 failures; single package 9 (precert), cloud tag 8 and 8. Only new: `check_aarch64_compatibility`. See `docs/contracts/phase17/APPINSPECT_DISPOSITION.md`.

## Regression on the instance (tree, Python 3.12, bare Ubuntu)
Selection: 11 failed, 4107 passed. Full tree: 56 failed, 49 errors, 5396 passed, 23 skipped. 96 failing IDs; 50 also fail in the local baseline/candidate comparison (7649 vs 7634 tests, identical 53 failing IDs, 0 candidate-only). 46 fail only on the instance and were NOT compared against v2.0.1 there (no further AWS runs were authorised):
- about 34 need tools absent from the instance (`snmptrapd`, `gnmic`, `tshark`, snmp utilities);
- about 10 are golden-output / checkpoint / repo-layout tests (e.g. `test_pan_raw_and_samples_unchanged`, `test_original_25_outputs_unchanged`, `test_release_packages_are_not_tracked...`) unrelated to the changed files; cause on the instance not established;
- `tests/test_stream_pacer.py::test_rate_never_exceeds_the_request`: 51.005 > 51 on the loaded instance (a test added in this PR; passes locally). The 3,600 s run showed max 201/s against 200. The test limit is strict and was not changed.

## Cleanup
Instance auto-terminated (10 h cap); its volume went with it. Security group, role, instance profile and S3 bucket were deleted by name from the state file and verified gone; 0 tagged instances remain. Wall time was about 10 h, so cost is about $4.5 (estimate, not billing data), above the earlier "<$2" estimate.
