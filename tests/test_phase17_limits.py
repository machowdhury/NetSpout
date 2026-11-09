"""Phase 17: install-level streaming bounds from the managed launcher."""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for p in (str(ROOT / "src"), str(ROOT / "backend"), str(ROOT / "netspout" / "bin")):
    if p not in sys.path:
        sys.path.insert(0, p)
from app import main
import pulseforge_engine_launcher as L


def test_open_ended_stream_gets_the_cap_and_oversized_requests_are_refused(monkeypatch):
    monkeypatch.setenv("NETSPOUT_MAX_STREAM_SECONDS", "3600")
    monkeypatch.setenv("NETSPOUT_MAX_STREAM_EPS", "200")
    assert main._stream_limits(None, 5) == 3600.0 and main._stream_limits(60, 5) == 60
    with pytest.raises(ValueError):
        main._stream_limits(7200, 5)
    with pytest.raises(ValueError):
        main._stream_limits(10, 500)


def test_without_the_managed_launcher_nothing_changes(monkeypatch):
    monkeypatch.delenv("NETSPOUT_MAX_STREAM_SECONDS", raising=False)
    monkeypatch.delenv("NETSPOUT_MAX_STREAM_EPS", raising=False)
    assert main._stream_limits(None, 5000) is None


def test_launcher_passes_the_caps_to_the_engine(tmp_path):
    s = L.Supervisor(str(tmp_path), command=["true"])
    (tmp_path / "config").mkdir()
    s.key = "k"
    env = s._env()
    assert env["NETSPOUT_MAX_STREAM_SECONDS"] == "3600" and env["NETSPOUT_MAX_STREAM_EPS"] == "200"
