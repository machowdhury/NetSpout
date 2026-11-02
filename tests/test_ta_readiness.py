"""Validation-before-expansion guards: coverage arithmetic closes, single-event never mislabels, TA evidence is honest."""
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT / "src"), str(ROOT / "backend")):
    if _p not in sys.path:
        sys.path.insert(0, _p)


def _script():
    spec = importlib.util.spec_from_file_location("coverage_report", ROOT / "scripts" / "generate_coverage_report.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_coverage_origin_arithmetic_closes_and_partitions_the_catalog(capsys):
    _script().main(check=True)  # raises AssertionError if baseline + corrections + batch net-new != native, or the partition is not disjoint
    out = json.loads(capsys.readouterr().out)["sourcetypes"]
    assert out["native_generators"] + out["sample_replay_only"] + out["no_generator"] == out["catalog_sourcetypes"] == 349


def test_indexed_evidence_requires_a_harness_that_posted_and_searched(tmp_path):
    mod = _script()
    rows = [{"verdict": "PASS", "sourcetype": "st:a", "matches": 1}]
    def write(name, **extra):
        (tmp_path / name).write_text(json.dumps({"raw_equality": rows, **extra}))
    write("a_raw_equality_results.json", posted=1, indexed_rows=1, post_failures=[])           # live, row-level proof
    passed, live, proven = mod.raw_equality_passes(tmp_path)
    assert (passed, live, proven) == ({"st:a"}, {"st:a"}, {"st:a"})
    (tmp_path / "a_raw_equality_results.json").unlink()
    write("b_raw_equality_results.json", posted=0, post_failures=[])                            # nothing was posted: not independent indexing
    assert mod.raw_equality_passes(tmp_path) == ({"st:a"}, set(), set())
    write("b_raw_equality_results.json", posted=1, post_failures=["HEC rejected"])              # a post failed: not counted
    assert mod.raw_equality_passes(tmp_path) == ({"st:a"}, set(), set())
    write("b_raw_equality_results.json", posted=1, post_failures=[])                            # older file, no row counts: file-level only
    (tmp_path / "b_raw_equality_results.json").write_text(json.dumps({"raw_equality": [{"verdict": "PASS", "sourcetype": "st:a"}], "posted": 1, "post_failures": []}))
    assert mod.raw_equality_passes(tmp_path) == ({"st:a"}, {"st:a"}, set())


def test_generator_transport_fails_closed_and_checks_the_effective_index(tmp_path, monkeypatch):
    import pytest
    from fastapi import HTTPException
    import app.main as main
    gt = main.current_topology.global_transport
    saved = (gt.hec_url, gt.hec_index)
    gt.hec_url, gt.hec_index = "https://127.0.0.1:1/services/collector", "not_allowed_idx"
    try:
        monkeypatch.setattr(main.release_candidate_configuration, "load", lambda: {"configured": False})
        assert main._generator_transport("idx_network_ops") is None  # unconfigured: callers fail closed
        monkeypatch.setattr(main.release_candidate_configuration, "load", lambda: {"configured": True, "indexes": ["idx_network_ops"]})
        assert main._generator_transport("idx_network_ops").hec_index == "idx_network_ops"
        with pytest.raises(HTTPException) as err:  # index omitted: the destination's own index must be allowed too
            main._generator_transport(None)
        assert err.value.status_code == 403
    finally:
        gt.hec_url, gt.hec_index = saved


def test_single_event_does_not_emit_a_sibling_sourcetypes_event():
    from netspout_core.generator_modes import TelemetryGeneratorService
    svc = TelemetryGeneratorService()
    for st in ("XmlWinEventLog:Microsoft-Windows-Sysmon/Operational", "XmlWinEventLog:Microsoft-Windows-NTLM/Operational", "XmlWinEventLog:System"):
        r = svc.generate_single_event("microsoft_windows", st)
        # either honestly ungrounded, or the event really belongs to the requested channel
        assert r["status"] == "TELEMETRY_NOT_GROUNDED" or f"<Channel>{st.split(':', 1)[1]}</Channel>" in r["raw"], (st, r.get("raw", "")[:120])


def test_ta_evidence_keeps_claims_inside_what_was_run():
    ev = ROOT / "docs/verification/evidence/ta_validation/windows_sysmon.json"
    assert ev.exists(), "run scripts/validate_ta_windows.py against tests/lab/ta_validation"
    d = json.loads(ev.read_text())
    assert d["cim_installed"] is False  # CIM data models are not claimed while Splunk_SA_CIM is absent
    assert set(d["installed_vendor_apps"]) == {"Splunk_TA_windows", "Splunk_TA_microsoft_sysmon"}
    assert d["summary"]["B"]["indexed"] == d["summary"]["B"]["events"] > 0
