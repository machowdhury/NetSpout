"""Phase 5: archive safety of the inventory reader and the invariants of the committed inventory/matrix (derived metadata only)."""
import io
import json
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts")]
import ta_inventory  # noqa: E402

P5 = ROOT / "docs/contracts/phase5"
APP_CONF = b"[launcher]\nversion = 1.0.0\n[package]\nid = TA-x\n"


def _tar(path, members):
    with tarfile.open(path, "w:gz") as tf:
        for name, data, kind in members:
            ti = tarfile.TarInfo(name)
            if kind == "sym":
                ti.type, ti.linkname = tarfile.SYMTYPE, "/etc/passwd"
                tf.addfile(ti)
            else:
                ti.size = len(data)
                tf.addfile(ti, io.BytesIO(data))


def test_unsafe_members_are_skipped_and_counted_never_read(tmp_path):
    p = tmp_path / "a.tgz"
    _tar(p, [("TA-x/default/app.conf", APP_CONF, "f"), ("../evil/default/app.conf", b"[x]", "f"), ("/abs/default/props.conf", b"[x]", "f"), ("TA-x/default/props.conf", b"", "sym")])
    files, st = ta_inventory.read_package(str(p))
    assert list(files) == ["TA-x/default/app.conf"]
    assert st["unsafe_path"] == 2 and st["links_or_devices"] == 1


def test_bomb_guards_trip(tmp_path, monkeypatch):
    p = tmp_path / "b.tgz"
    _tar(p, [("TA-x/f%d" % i, b"x", "f") for i in range(20)])
    monkeypatch.setattr(ta_inventory, "MAX_MEMBERS", 5)
    with pytest.raises(ta_inventory.UnsafeArchive):
        ta_inventory.read_package(str(p))
    monkeypatch.setattr(ta_inventory, "MAX_MEMBERS", 1000)
    monkeypatch.setattr(ta_inventory, "MAX_DECLARED_BYTES", 10)
    big = tmp_path / "c.tgz"
    _tar(big, [("TA-x/blob.bin", b"y" * 100, "f")])
    with pytest.raises(ta_inventory.UnsafeArchive):
        ta_inventory.read_package(str(big))


def test_zip_packages_are_read_in_memory(tmp_path):
    p = tmp_path / "z.spl"
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("TA-x/default/app.conf", APP_CONF)
        zf.writestr("../up/default/app.conf", "[x]")
    files, st = ta_inventory.read_package(str(p))
    assert list(files) == ["TA-x/default/app.conf"] and st["format"] == "zip" and st["unsafe_path"] == 1
    assert [a["id"] for a in (ta_inventory.inventory_app(files, r) for r in ta_inventory.app_roots(files))] == ["TA-x"]


def test_sha256_is_streamed(tmp_path):
    f = tmp_path / "x"
    f.write_bytes(b"abc")
    assert ta_inventory.sha256_file(f) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def _load(name):
    p = P5 / name
    if not p.exists():
        pytest.skip("run scripts/build_phase5_matrix.py")
    return json.loads(p.read_text())


def test_every_package_file_has_a_row_with_hash_and_status():
    inv = _load("package_inventory.json")
    s = inv["summary"]
    assert s["files_found"] == len(inv["packages"]) == s["inspected"] + s["failed"] + s["no_app_found"]
    assert all(len(p["sha256"]) == 64 and p["status"] for p in inv["packages"])
    # duplicates keep their own row and point at the first copy
    assert sum(1 for p in inv["packages"] if p["duplicate_of"]) == s["byte_identical_duplicates"]


def test_matrix_reconciles_with_catalog_and_phase4_evidence():
    m = _load("master_matrix.json")
    cov = json.loads((ROOT / "docs/reference/sourcetype_coverage.json").read_text())["rows"]
    vendors = json.loads((ROOT / "catalog/vendors.json").read_text())
    assert len(m["rows"]) == len(cov) == m["summary"]["catalog_sourcetypes"]
    assert {r["catalog_sourcetype"] for r in m["rows"]} == {r["sourcetype"] for r in cov}
    vc = _load("vendor_coverage.json")
    assert {v["vendor_id"] for v in vc["vendors"]} == {v["id"] for v in vendors}
    assert sum(v["catalog_sourcetypes"] for v in vc["vendors"]) == len(cov)
    live = json.loads((ROOT / "docs/contracts/ta_live_results.json").read_text())
    verified = {r["catalog_sourcetype"] for r in m["rows"] if r["live_verification"].startswith("SPLUNK_VERIFIED")}
    assert verified == {k for k, v in live.items() if v["passed"]} and len(verified) == 6   # asa, ios, fortigate_traffic, pan:traffic, pan:threat, pan:system (Phase 10 added the last two)


def test_no_candidate_or_conflict_is_reported_as_confirmed():
    for r in _load("master_matrix.json")["rows"]:
        if r["match_type"] == "exact":
            assert r["evidence"] and r["canonical_ta_sourcetype"] == r["catalog_sourcetype"] and not r["naming_conflict"]
        if r["match_type"] in ("conflict", "candidate", "none"):
            assert not r["live_verification"].startswith("SPLUNK_VERIFIED")
        if r["match_type"] == "none":
            assert not r["covering_packages"]


def test_top10_candidates_are_unverified_exact_and_have_working_generators():
    m = {r["catalog_sourcetype"]: r for r in _load("master_matrix.json")["rows"]}
    top = _load("top10_shortlist.json")
    assert len(top) == 10 and [t["rank"] for t in top] == list(range(1, 11))
    for t in top:
        for st in t["exact_sourcetypes_ready"]:
            r = m[st]
            assert r["match_type"] == "exact" and r["generator_valid"] and r["live_verification"] == "NOT_VERIFIED" and r["ingestion_support"] != "NOT_EMULATED"


def test_no_package_archives_or_config_text_are_tracked():
    out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split("\n")
    assert not [f for f in out if f.endswith((".spl", ".tgz", ".tar.gz")) and f not in ("netspout.spl", "netspout_cloud.spl")]   # those two are NetSpout's own builds
    assert not [f for f in out if f.startswith("samples/") or "private-packs" in f]
    for f in P5.glob("*.json"):
        assert '"REGEX"' not in f.read_text() and '"TIME_PREFIX"' not in f.read_text()
