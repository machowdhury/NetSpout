"""The single package's vendored Python dependencies are hash-pinned: nothing is resolved at build time (annotated_doc moved 0.0.5 to 0.0.6 between two builds before this)."""
import importlib.util
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bsp", ROOT / "scripts" / "build_single_package.py")
bsp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bsp)
LOCK = json.loads((ROOT / "scripts" / "single_package_lock.json").read_text())


def test_every_default_variant_has_a_complete_hash_lock():
    for v in bsp.DEFAULT_VARIANTS:
        wheels = LOCK[v]
        names = [w["file"].split("-")[0].lower().replace("_", "-") for w in wheels]
        assert len(set(names)) == len(names), "one wheel per distribution"
        assert all(re.fullmatch(r"[0-9a-f]{64}", w["sha256"]) and w["file"].endswith(".whl") for w in wheels)
        for r in bsp.REQ:                                           # every direct requirement is locked at exactly its declared version
            n, ver = r.split("==")
            assert any(w["file"].lower().startswith(n.lower().replace("-", "_") + "-" + ver + "-") for w in wheels), r
        assert any(w["file"].startswith("annotated_doc-") for w in wheels)      # the transitive one that drifted


def test_a_variant_without_a_lock_is_refused_not_resolved_live(tmp_path):
    ok, note = bsp.download("py39-linux-x86_64", tmp_path)
    assert ok is False and "no pinned lock" in note[0]
