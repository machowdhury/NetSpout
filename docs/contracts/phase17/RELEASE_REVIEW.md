# Phase 17 pre-merge release review (local only; no AWS, no full suite)

Candidate `bdc4084`; later commits change docs, harness and evidence only (`git diff bdc4084 HEAD -- netspout backend src frontend/src scripts/build_single_package.py scripts/single_package_lock.json` is empty).

## 1. Failures classified
Instance-only failures (46) were read from `aws-native-x86_64/run2-bdc4084/regression/full_tests_tree.txt`. None is a product defect.
| Group | Cause (from the log) | Class |
|---|---|---|
| about 34 SNMP/gNMI/tshark tests | `snmptrapd`, `gnmic`, `tshark` not installed on the bare instance | environment |
| 10 golden-output / layout tests (`test_original_25_outputs_unchanged`, `test_previous_31_outputs_preserved`, `test_pan_raw_and_samples_unchanged`, `test_batch3b_output_identical_to_checkpoint`, `test_catalog_contract_and_legacy_recipes`, `test_recipe_inventory_preserved`, `test_candidates_are_not_parser_verified...`, `test_legacy_executor_and_runner_helpers...`, `test_guarded_run_preserves...`, `test_release_packages_are_not_tracked...`) | `fatal: not a git repository`: they call `git show`/`git status`/`git ls-files` and the instance copy of the tree had no `.git` | test/environment |
| `test_21_no_references_to_removed_js` | `git grep` exit 128 (same cause) | test/environment |
| `test_real_ta_parser_results_preserve_blocked_expectation` | hashes `ast.dump` of two functions in `src/netspout_core/log_engine.py`, which this PR does not touch; `ast.dump` text depends on the Python version (instance 3.12) | test portability |
| `test_cloud_edition_contains_only...` | `netspout_cloud.spl` not built on the instance (also fails locally) | environment |
| `test_24_validation_engine_fails_on_missing_splunk_evidence` | 600 s pytest timeout in the SNMP lab path | environment |
| `test_rate_never_exceeds_the_request` | **Test bound, not product.** 50 events at 50/s span 49 intervals, so the highest rate the test can measure is 50 x 50/49 = 51.02; the assertion is `<= 51`. Local repeats: 50.75-50.97; instance 51.005. The 3,600 s run (the real check) peaked at 201 in any second against 200. | test bound |
No release blocker; no code changed. The golden-output and AST-hash tests were not re-run against v2.0.1 on an instance with `.git` (no further AWS runs); locally, baseline and candidate fail on the identical 53 IDs, with none candidate-only. Follow-ups (not blockers): raise the pacer test bound to 52; make the git-based tests skip when there is no `.git`.

## 2. Evidence by property (what was verified on which candidate)
| Property | Final candidate bdc4084 | Earlier candidate only |
|---|---|---|
| Idle generation | 0 indexed events in 3-min windows: fresh, after load, after upgrade, on native x86_64 10.6.1.1 (AWS run 2); 2-min windows locally | n/a |
| Burst | native 3,600 s: max 201 in any second, p99 200 (limit 230); 59 full minutes at 200.0/s | n/a |
| Single-package install, restart, lifecycle (kill, launcher recovery, stop/start, restart), upgrade from v2.0.1 through Splunk Web, uninstall, authz | native 10.6.1.1, 21 steps, 0 FAIL | n/a |
| Install census | recorded `ok=false`: Splunk's own startup ports (control run); harness artifact | n/a |
| Splunk 10.2.7 | **Not run on bdc4084 and never run natively.** | Run on 91af353 under amd64 emulation on an arm64 host (`splunk-10.2.7/`). The 91af353 to bdc4084 product delta is the HEC send path and pacer (`telemetry_dispatcher.py`, `delivery_monitor.py`, 4 copies each) and the build script. |
| aarch64 | not supported (AppInspect finding 9) | n/a |
| Sustained 3,600 s | native, final candidate | n/a |

## 3. Dependency lock and provenance
- `scripts/single_package_lock.json`, sha256 `ccc2bb5da393f02bf3ed83d4af9736adb5cdae60e0098345899b8ce63d3aa3c6`: 19 hash-pinned wheels, `py313-linux-x86_64`. The build downloads with `--no-deps --require-hashes` into an empty directory and fails on any difference; `tests/test_single_package_lock.py` passes (2 tests).
- Reproduced in this review: a build from a clean `git archive bdc4084` gives gzip `2db9bb21b6f45f8ee5b977424cc72b90ee0a428db3c7e9dd9bc3501e456f83a1` (15,977,713 B) and tar `0904a5100825e3b9736c8752cf516e6e74d35d335a6227de2b4af0a758ee5394`.
- Native instance build (Python 3.12.3, Linux zlib, built twice, identical): gzip `171837b0087587d8f488976358743c6aed5acc4861f11f5ae420542d1057c8ef` (15,766,717 B), tar `0904a510...5394`. **Tar content is identical; the gzip stream differs only because the zlib build differs.** The tested artifact is the native gzip.
- Caveat: the lock pins `annotated_doc` 0.0.6; the earlier approved artifact had 0.0.5.
- **Build only from a clean archive.** `build/single_package` built from a working tree with ignored runtime logs included `netspout/var/log/*.log` (tar `189e0bae...`, 15,978,126 B). The clean archive has none. The build script was not changed (that would change the candidate); excluding `var/` is a follow-up.

## 4. PR review: blockers
None found in the final candidate. Checked: HEC pool key (scheme, netloc, TLS mode, token), per-thread, closed at stream end; ambiguous delivery is `unknown`, never re-sent, never `accepted`; TLS policy unchanged; no credential in the diff or evidence (14 `0600` credential values and AWS key patterns: 0 hits); gateway capability gate and destination authorisation exercised (authz 10/10, viewer refused); no generation at idle.
Fixed here (docs only): the AWS plan doc, in a public repository, named an Organizations ID, an SCP ID and an IAM user name; they are redacted. They remain in earlier commits of this branch, so prefer **squash-merge**. Account id, instance ids and the S3 bucket name remain in the evidence files; those resources are deleted.
