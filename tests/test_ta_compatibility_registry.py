"""The compatibility registry may only claim what it can point at: referenced files and generators exist, every VERIFIED check names its evidence,
and the product refuses the non-canonical ASA name."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]
REG = json.loads((ROOT / "docs/contracts/ta_compatibility_registry.json").read_text())
STATUS = {"VERIFIED", "UNVERIFIED", "BLOCKED", "NON_CANONICAL"}


def test_registry_entries_are_backed():
    seen = set()
    for e in REG["entries"]:
        assert (ROOT / e["sample_file"]).is_file(), e["sample_file"]
        assert e["canonical_sourcetype"] not in seen
        seen.add(e["canonical_sourcetype"])
        for name, chk in e["verification"].items():
            assert chk["status"] in STATUS, (e["canonical_sourcetype"], name)
            assert chk.get("evidence"), (e["canonical_sourcetype"], name)


def test_no_ta_parsing_claim_without_a_package():
    for e in REG["entries"]:
        v = e["verification"].get("ta_parsing_in_splunk")
        assert v is None or v["status"] != "VERIFIED"   # no add-on package was available


def test_registry_sourcetypes_exist_in_catalog_and_non_canonical_is_refused():
    from netspout_core.generator_modes import TelemetryGeneratorService
    import pytest
    svc = TelemetryGeneratorService()
    names = {s["splunk_sourcetype"] for s in svc.catalog._sourcetypes}
    assert {e["canonical_sourcetype"] for e in REG["entries"]} <= names
    with pytest.raises(ValueError, match="NON_CANONICAL_SOURCETYPE"):
        svc.generate_sourcetype_batch("cisco_asa", "cisco:asa:syslog", 1, 1)
