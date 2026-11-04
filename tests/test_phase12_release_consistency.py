"""Phase 12: the release version is one value everywhere, the mirror guardrail covers every mirrored module, and a release binary in the working tree can never be a stale version unnoticed.

Set NETSPOUT_STRICT_BINARIES=1 (release checks) to make a stale or missing repo-root binary a failure instead of a skip.
"""
import json
import os
import re
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


def source_versions():
    conf = re.search(r"^version\s*=\s*(\S+)", (ROOT / "netspout/default/app.conf").read_text(), re.M).group(1)
    manifest = json.loads((ROOT / "netspout/app.manifest").read_text())["info"]["id"]["version"]
    pkg = json.loads((ROOT / "frontend/package.json").read_text())["version"]
    main = re.findall(r'version="(\d+\.\d+\.\d+)"|"version":\s*"(\d+\.\d+\.\d+)"', (ROOT / "backend/app/main.py").read_text())
    cloud = re.findall(r"^version = (\S+)", (ROOT / "scripts/build_splunk_cloud_package.py").read_text(), re.M)
    return {"app.conf": conf, "app.manifest": manifest, "frontend/package.json": pkg, "backend main.py": {a or b for a, b in main}, "cloud builder": set(cloud)}


def test_one_release_version_in_every_source():
    v = source_versions()
    values = {x for k, val in v.items() for x in (val if isinstance(val, set) else {val})}
    assert len(values) == 1, v


def test_mirror_guardrail_checks_every_module_that_sync_core_mirrors():
    import sync_core
    import verify_sources
    assert verify_sources.CORE_MODULES is sync_core.CORE_MODULES


def test_mirrors_match_the_canonical_source():
    pytest.importorskip("pydantic")   # verify_sources imports the catalog, which needs the engine's own dependencies
    r = subprocess.run([sys.executable, str(ROOT / "scripts/verify_sources.py")], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout[-800:]


@pytest.mark.parametrize("name", ["netspout.spl", "netspout_cloud.spl"])
def test_repo_root_release_binary_is_not_a_stale_version(name):
    path = ROOT / name
    strict = os.environ.get("NETSPOUT_STRICT_BINARIES") == "1"
    if not path.exists():
        pytest.skip("no %s in the working tree (built by the release process)" % name) if not strict else pytest.fail("missing " + name)
    with tarfile.open(path) as tf:
        conf = [m for m in tf.getmembers() if m.name.endswith("/default/app.conf")][0]
        built = re.search(r"^version\s*=\s*(\S+)", tf.extractfile(conf).read().decode(), re.M).group(1)
    want = source_versions()["app.conf"]
    if built != want:
        msg = "%s in the repository root is version %s but the source is %s: it is a stale build; do not install it" % (name, built, want)
        pytest.fail(msg) if strict else pytest.skip(msg)
