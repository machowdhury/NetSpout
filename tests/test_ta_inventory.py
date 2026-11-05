"""Archive safety of scripts/ta_inventory.py and invariants of the committed registry/inventory."""
import io
import json
import sys
import tarfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import ta_inventory  # noqa: E402

PACKS = Path("~/netspout/private-packs").expanduser()


def _tar(tmp_path, members):
    p = tmp_path / "x.tgz"
    with tarfile.open(p, "w:gz") as tf:
        for name, content, kind in members:
            ti = tarfile.TarInfo(name)
            if kind == "file":
                b = content.encode(); ti.size = len(b); tf.addfile(ti, io.BytesIO(b))
            elif kind == "sym":
                ti.type = tarfile.SYMTYPE; ti.linkname = "/etc/passwd"; tf.addfile(ti)
            elif kind == "hard":
                ti.type = tarfile.LNKTYPE; ti.linkname = "A/default/app.conf"; tf.addfile(ti)
    return p


def test_unsafe_members_are_skipped_and_counted_never_read(tmp_path):
    p = _tar(tmp_path, [("A/default/app.conf", "[launcher]\nversion = 1.2.3\n[ui]\nlabel = L\n", "file"), ("../evil/default/app.conf", "[launcher]\nversion = 9\n", "file"),
                        ("/abs/default/app.conf", "[launcher]\nversion = 8\n", "file"), ("A/default/props.conf", "", "sym"), ("A/default/x.conf", "", "hard")])
    files, st = ta_inventory.read_package(str(p))
    assert list(files) == ["A/default/app.conf"] and st["unsafe_path"] == 2 and st["links_or_devices"] == 2
    assert not (tmp_path / "evil").exists() and not Path("/abs").exists()          # nothing is extracted to disk


def test_oversize_config_is_not_read(tmp_path, monkeypatch):
    monkeypatch.setattr(ta_inventory, "MAX_MEMBER", 10)
    p = _tar(tmp_path, [("A/default/app.conf", "[launcher]\nversion = 1.2.3\n" + "#" * 50, "file")])
    files, st = ta_inventory.read_package(str(p))
    assert files == {} and st["oversize_config"] == 1


def test_inventory_records_identity_sourcetypes_and_classification(tmp_path):
    p = _tar(tmp_path, [("A/default/app.conf", "[launcher]\nversion = 2.0\n[ui]\nlabel = Demo TA\n", "file"),
                        ("A/default/props.conf", "[v:p]\nREPORT-x = t\nTIME_FORMAT = %b %d\n[source::udp:514]\nTRANSFORMS-a = f\n", "file"),
                        ("A/default/transforms.conf", "[t]\nREGEX = (?<a>x)\n[f]\nDEST_KEY = MetaData:Sourcetype\nREGEX = %V\nFORMAT = sourcetype::v:p\n", "file"),
                        ("A/default/inputs.conf", "[monitor:///var/x]\nsourcetype = v:in\n", "file")])
    files, _ = ta_inventory.read_package(str(p))
    a = ta_inventory.inventory_app(files, ta_inventory.app_roots(files)[0])
    assert (a["version"], a["label"]) == ("2.0", "Demo TA")
    assert {s["sourcetype"] for s in a["sourcetypes"]} == {"v:p", "v:in"}          # source:: stanzas are not sourcetypes
    assert "TA (parsing/extraction)" in a["classification"]


def test_committed_inventory_covers_all_14_packages_and_stores_no_configuration_text():
    d = json.loads((ROOT / "docs/verification/evidence/ta_inventory/packages.json").read_text())
    assert len(d["packages"]) == 14 and all(p["status"] == "INSPECTED" for p in d["packages"])
    assert all(p["archive_safety"]["unsafe_path"] == 0 for p in d["packages"])
    text = json.dumps(d)
    assert "REGEX" not in text and "DEST_KEY" not in text                           # names and file:stanza references only


@pytest.mark.skipif(not all((PACKS / n).is_file() for n in ta_inventory.PHASE4_PACKAGES), reason="downloaded add-on packages not present (never committed)")
def test_real_packages_inspect_without_error(tmp_path):
    assert ta_inventory.main(PACKS, str(tmp_path / "inv.json")) == 0                  # writes to a temp file, never over the committed evidence
    d = json.loads((tmp_path / "inv.json").read_text())
    assert [p["package"] for p in d["packages"]] == sorted(ta_inventory.PHASE4_PACKAGES) and all(p["status"] == "INSPECTED" for p in d["packages"])


def test_registry_status_invariants():
    reg = json.loads((ROOT / "docs/contracts/ta_backed_registry.json").read_text())
    live = json.loads((ROOT / "docs/contracts/ta_live_results.json").read_text())
    for r in reg["rows"]:
        s = set(r["statuses"])
        assert "TA_DEFINED" in s and r["evidence"]
        if "SPLUNK_VERIFIED" in s:
            rec = live[r["canonical_sourcetype"]]
            assert rec["passed"] and rec["package"] == r["package"]               # verification belongs to the package it ran against
        if "FORMAT_VERIFIED" in s:
            assert "GENERATOR_AVAILABLE" in s
        assert not ({"UNSUPPORTED", "GENERATOR_AVAILABLE"} <= s)
        if r["conflict_types"]:
            assert "CONFLICT" in s
