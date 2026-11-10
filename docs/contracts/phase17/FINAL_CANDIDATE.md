# Phase 17 final candidate (AWS run 2)

- Source commit: `bdc4084bb038ebbec00f33de9c613f0a52018300` (PR #11 `feature/single-package-enterprise`). Harness commits after it change only `scripts/aws/*`, `scripts/phase17_*`, evidence and docs, never the package inputs (`netspout`, `backend`, `src`, `scripts/build_single_package.py`, `scripts/single_package_lock.json`); `run_all.sh stage` enforces this.
- Local reference build (macOS arm64, Python 3.15 venv, built twice, the second from an empty wheel cache with touched files; both identical):
  - gzip SHA-256 `2db9bb21b6f45f8ee5b977424cc72b90ee0a428db3c7e9dd9bc3501e456f83a1` (15,977,713 bytes)
  - uncompressed tar SHA-256 `0904a5100825e3b9736c8752cf516e6e74d35d335a6227de2b4af0a758ee5394`
- Dependency lock: `scripts/single_package_lock.json` (SHA-256 `ccc2bb5da393f02b…`, in the package's `bin/lib/MANIFEST.json` as `lock_sha256`): 19 wheels for `py313-linux-x86_64`, pinned by file name and sha256, fetched with `--no-deps --require-hashes`. The build fails if a downloaded wheel differs from the lock.
- Locked versions are those of the 1d60daa screening build: `annotated_doc` 0.0.6. The approved `91af353` artifact had `annotated_doc` 0.0.5; the module is a version marker only.
- Superseded: `1d60daa` (unpinned dependencies; reference gzip `724fef13…`). It was screened locally and is not the AWS candidate.
- Local focused checks on this exact artifact (emulated amd64 Splunk 10.6.1, `docs/verification/evidence/phase17/screening/final-bdc4084/`): idle 2 min fresh and after load, 0 events indexed; events 6/6, metrics 1/1, authz 10/10; 300 s at 200/s: 199.9/s, 59,975 of 59,975 indexed, 0 rejected/unknown/dropped, at most 204 events in any second. Screening only: not the native result.
- Package contents scan: no private keys and no credential values (five regex/detection-text mentions of "PRIVATE KEY" are not keys).
