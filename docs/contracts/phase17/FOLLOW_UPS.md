# Phase 17 follow-ups (recorded at merge; none is a release blocker; scope not expanded now)
1. **Install census check** (`scripts/phase17_census.py`): reports `ok=false` because Splunk opens ports 5433/5434/6432 about 2 minutes after start, after the check's early "before" snapshot (control run on stock Splunk 10.6.1). Make the check settle first or exclude Splunk's own services.
2. **Pacer test tolerance** (`tests/test_stream_pacer.py::test_rate_never_exceeds_the_request`): 50 events at 50/s can measure up to 51.02; raise the bound to 52. The product limit is covered by the 3,600 s run (max 201 in any second at 200/s).
3. **Git-dependent tests** (golden-output, recipe-inventory, release-layout, `git grep` tests): skip when there is no `.git`; and the `ast.dump` hash test in `test_universe_batch3.py` depends on the Python version.
4. **Clean-archive packaging**: `scripts/build_single_package.py` includes ignored files such as `netspout/var/log/*.log` when run from a dirty working tree. Release packages must be built from a clean `git archive`; make the build exclude `var/`.
5. Harness: the `search()` preview fix was not re-run on AWS; per-minute figures in the run 2 JSON are superseded by `sustained_per_minute_corrected.json`.
6. Splunk 10.2.7 on the final candidate, aarch64 support, and the AppInspect metadata items are unscheduled.
