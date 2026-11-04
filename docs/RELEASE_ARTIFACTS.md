# Release artifacts: where they come from

The installable packages are **generated** and are **not stored in Git** (since version 2.0.1; policy in `docs/contracts/phase12/PHASE12_BINARY_POLICY.md`). Do not look for `netspout.spl` in a clone. You get a package in one of two ways.

## 1. Download a versioned release artifact (normal path)
Each published release carries, next to the files, `SHA256SUMS` and `BUILD_MANIFEST.json` (built-from commit, versions, sizes, checksums):

| File | What it is | Install |
|---|---|---|
| `netspout.spl` | the Splunk Enterprise app (UI, gateway, dashboards, catalogs) | Splunk Web > Apps > Manage Apps > Install app from file |
| `netspout_cloud.spl` | dashboards-only Cloud edition; needs a customer-hosted engine; **separate validation track, not tested yet** | via the Splunk Cloud app-vetting process |
| `pulseforge-engine.tar.gz` | the PulseForge Engine (customer-hosted) | `docs/guides/03_INSTALLATION.md` section C |

Verify before installing: `shasum -a 256 -c SHA256SUMS`, and check that the version in `BUILD_MANIFEST.json` is the one you expect. **Never install `netspout.spl` and `netspout_cloud.spl` into the same Splunk**: both use the app id `netspout`, so the second replaces the first.

## 2. Build from source
From a clean checkout (no sample folders needed), with Node 20+ and a virtualenv holding `backend/requirements.txt`:
```
(cd frontend && npm ci)
python scripts/build_frontend.py
python scripts/build_splunk_package.py          # netspout.spl (+ manifest); syncs and verifies the mirrored core first
python scripts/build_splunk_cloud_package.py    # netspout_cloud.spl (+ manifest)
python scripts/build_engine_package.py          # pulseforge-engine.tar.gz; refuses to build if the mirrors drifted
python scripts/phase10_package_audit.py out.json netspout.spl netspout_cloud.spl pulseforge-engine.tar.gz --repo .
shasum -a 256 netspout.spl netspout_cloud.spl pulseforge-engine.tar.gz > SHA256SUMS
```
The builders write to the repository root; those files are git-ignored. Before using one, compare its version (`tar -xzOf netspout.spl netspout/default/app.conf | grep ^version`) with `netspout/default/app.conf`. `NETSPOUT_STRICT_BINARIES=1 pytest tests/test_phase12_release_consistency.py` fails when a root package is stale.

`Dockerfile.standalone` needs a freshly built `netspout.spl` (see the comment at its top).

## Older 2.0.0 packages
The 2.0.0 files that used to be tracked are archived outside the repository (`~/netspout/released-artifacts-2.0.0-pre-policy-a/` on the maintainer's machine, with checksums). They remain in Git history (`git show 3cb4322:netspout.spl`). 2.0.0 reads its engine address from a default or `NETSPOUT_BACKEND_URL`; 2.0.1 does not (see `docs/contracts/phase11/PHASE11_UPGRADE.md`).
