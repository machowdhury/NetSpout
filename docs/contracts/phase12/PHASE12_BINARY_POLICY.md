# Release-binary policy — audit and recommendation

**Recommendation: Policy A. Keep generated binaries out of Git and publish them as versioned release artifacts.** No compatibility blocker was found; four small dependencies exist and each has a safe answer (below). **Nothing was deleted, untracked or replaced in Phase 12.** Executing the migration needs your approval (see `PHASE12_RELEASE_DECISION.md`, A1).

## 1. What is tracked today

| File (repo root) | In Git on the branch | Size | Version inside | Notes |
|---|---|---|---|---|
| `netspout.spl` | **tracked on `origin/main`** (since PR #4, 2026-11-02); this branch does not change it | 6,652,946 B | **2.0.0** | built at commit `5a2405c` (2026-11-01); sha256 `3b086b80…c46f` |
| `netspout.spl.manifest.json` | tracked on `origin/main` | 268 B | 2.0.0 hash | written by the builder |
| `netspout_cloud.spl` | **tracked on `origin/main`**; unchanged by this branch | 263,674 B | **2.0.0** | sha256 `3f8a7cf7…a3a7` |
| `netspout_cloud.spl.manifest.json` | tracked on `origin/main` | 176 B | 2.0.0 hash | |
| `pulseforge-engine.tar.gz` | **not tracked** (listed in `.gitignore`; present on disk only) | 9,678,174 B | **2.0.0** | sha256 `9b54120b…bf1b` |

Source version on this branch is **2.0.1**; `origin/main` has 2.0.0 source *and* 2.0.0 binaries, so today they agree. The recovery PR raises the source to 2.0.1 and leaves the binaries at 2.0.0: **merging it as is creates the mismatch**. RC3 and RC4 (2.0.1) exist only under `~/netspout/release-candidates/`.

History cost: 59 blobs of the two `.spl` files exist in reachable history (≈162 MiB uncompressed; the pack is 110 MiB in total). Every rebuild that is committed adds about 6 MB.

## 2. Every dependency on the root paths

| Dependency | Kind | Effect if the files are not tracked | Answer |
|---|---|---|---|
| `scripts/build_splunk_package.py`, `build_splunk_cloud_package.py`, `build_engine_package.py` | writers | none: they create the files (and the two `.manifest.json`) | unchanged; the builders keep writing to the repo root, which stays git-ignored |
| `tests/test_gate2_canonical.py::test_08_splunk_package_integrity` | test | failed with "does not exist" in a clean checkout | **changed in Phase 12**: skips when no binary is built |
| `tests/test_phase13_release_candidate.py::test_built_package_layout_when_archive_exists` | test | already skips when absent | none |
| `tests/test_phase5_inventory.py::test_no_package_archives_or_config_text_are_tracked` | test | allow-lists the two `.spl`; stays true when they are untracked | optionally tighten later (drop the allowance) |
| `tests/run_comprehensive_test_suite.py` Suite 19 | script (not collected by pytest) | records a failed "netspout.spl Exists" check | build first (`python scripts/build_splunk_package.py`), as its own header says; or skip when absent (not changed) |
| `scripts/run_phase13_release_audit.py` | script | exits "Build netspout.spl before running the release audit" | already build-first; documented |
| `Dockerfile.standalone` (`COPY netspout.spl …`) and `docker-compose.standalone.yml` | build input | the image build fails without a built `netspout.spl` | build the app first; the release steps in `PHASE12_PACKAGING_REPRODUCIBILITY.md` do that. No CI builds this image |
| `scripts/phase10_rc_install.py`, `tests/lab/rc_install/*` | RC tooling | none: they read a candidate directory, not the repo root | **hardened in Phase 12**: `install` refuses a `netspout.spl` whose version differs from the source |
| Documentation (`docs/INSTALL.md`, guides, Gate and Phase reports) | prose | readers are told to install `netspout.spl` | point to the release artifact; Phase 11 docs already name the RC directory |
| CI / GitHub workflows | — | none exist (`.github/` absent) | nothing to migrate |

New guard (Phase 12, `tests/test_phase12_release_consistency.py`): a stale binary in the working tree is reported (skip) or, with `NETSPOUT_STRICT_BINARIES=1`, fails. Today, in strict mode, both tracked `.spl` files fail as **stale 2.0.0**; that is the evidence for the recommendation.

## 3. Why A

- A binary that is derived from the source cannot be reviewed in a PR and goes stale the moment any packaged file changes (it already has).
- The Enterprise archive rebuilt byte-for-byte from a clean checkout (Phase 12 reproducibility test), so a tracked copy adds no information a build does not give.
- Release assets can carry `SHA256SUMS` and `BUILD_MANIFEST.json` beside the files, with the built-from commit.
- Policy B would need the final 2.0.1 binary committed in the same PR, rebuilt on every later packaged change, and the history grows ~6 MB each time.

## 4. Migration steps (all need approval; none done)

1. **Archive what exists.** Copy the three root files and their manifests to a safe place outside the repo (for example `~/netspout/released-2.0.0/`) with `sha256sum`. `~/netspout/release-candidates/rc3-ae3342d/existing-released-artifacts.sha256` already holds their checksums; they matched on 2026-11-04.
   *Why first:* when a pulled commit removes tracked files, Git deletes them from every working tree that checks it out, including this one.
2. **Publish** the final 2.0.1 artifacts as a versioned release (asset names with the version, e.g. `netspout-2.0.1.spl`), with `SHA256SUMS` and `BUILD_MANIFEST.json`. The RC3 files are the current candidate; rebuilding from the merge commit gives a byte-identical `netspout.spl` if no packaged source changed.
3. **Untrack:** `git rm --cached netspout.spl netspout_cloud.spl netspout.spl.manifest.json netspout_cloud.spl.manifest.json`, add them (and `*.spl`, `*.tar.gz` at the root, `BUILD_MANIFEST.json`, `SHA256SUMS`) to `.gitignore`.
4. Update `docs/INSTALL.md` and the install guide to say "download from the release", and note the build-first requirement for `Dockerfile.standalone`.
5. Keep `NETSPOUT_STRICT_BINARIES=1 pytest tests/test_phase12_release_consistency.py` as a release gate; it fails if a stale binary is left in the tree.

## 5. Rollback

- Git keeps every previous blob. `git checkout 5a2405c -- netspout.spl netspout_cloud.spl` restores the 2.0.0 files (and `git checkout origin/main -- netspout.spl` gives the same file as the tracked one today).
- Reverting the untracking commit restores the tracked files; the archived copies from step 1 and the release assets are independent of Git.
- Rolling the product back is unchanged: reinstall the previous `.spl` (see `docs/contracts/phase11/PHASE11_UPGRADE.md`).
- If Policy A is rejected, Policy B minimum: replace the two tracked `.spl` and manifests with the rebuilt 2.0.1 files in the merge commit and run the strict test as a gate. I would not do this without your approval either.
