"""Verify DestinationManager resolves its config independently of CWD.

Regression guard for the defect where a bare relative "destinations.json"
default made the active destination depend on the process working directory,
silently selecting a stale copy whose metric index the HEC token rejects.
"""
import os
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.join(REPO, "backend"))

from app.destination_manager import DestinationManager  # noqa: E402

EXPECTED = os.path.join(REPO, "backend", "destinations.json")
CWDS = (REPO, os.path.join(REPO, "backend"), "/tmp")

failures = []
for cwd in CWDS:
    os.chdir(cwd)
    m = DestinationManager()
    d = m.destinations.get(m.active_destination_id)
    print(f"CWD={cwd}")
    print(f"  resolved   = {m.config_file}")
    print(f"  active     = {m.active_destination_id}")
    print(f"  event idx  = {d.hec_index if d else None}")
    print(f"  metric idx = {d.hec_metric_index if d else None}")
    if m.config_file != EXPECTED:
        failures.append(cwd)

# The defect's symptom was selecting the stale metric index, which the lab
# HEC token does not allow (HTTP 400 "Incorrect index"). Guard against it.
STALE_METRIC_INDEX = "cisco_mdt_metrics"
os.chdir(REPO)
_mgr = DestinationManager()
active = _mgr.destinations.get(_mgr.active_destination_id)
if active is None or active.hec_metric_index == STALE_METRIC_INDEX:
    failures.append(f"metric-index-stale-or-missing({getattr(active, 'hec_metric_index', None)})")

print("\nRESULT:", "PASS" if not failures else f"FAIL {failures}")
sys.exit(0 if not failures else 1)
