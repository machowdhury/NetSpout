#!/usr/bin/env python3
"""Build pulseforge-engine.tar.gz: the customer-hosted engine as a self-contained package (no repository checkout needed on the engine host).
Layout keeps the repository-relative paths the code resolves (backend/, src/netspout_core/, catalog/, selected docs/verification/evidence), plus deploy/engine (launcher, units, env example).
Run scripts/sync_core.py first. Usage: python scripts/build_engine_package.py"""
import hashlib
import json
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "pulseforge-engine.tar.gz"
INCLUDE = ["backend/app", "backend/run.py", "backend/requirements.txt", "src/netspout_core", "catalog", "netspout/bin/network_incidents.py", "netspout/bin/telecom_incidents.py", "netspout/samples", "netspout/appserver/static/samples", "netspout/catalog", "netspout/default/data/ui/views", "deploy/engine", "deploy/collector",
           "docs/verification/evidence/replay/replay_live.json", "docs/verification/evidence/incident_packs/live_results.json", "docs/verification/evidence/flow/scenarios.json",
           "docs/verification/evidence/monitor/live.json", "docs/verification/evidence/dashboards/dashboard_maturity.json"]
SKIP = ("__pycache__", ".pyc", ".DS_Store")


def main():
    n = 0
    with tarfile.open(OUT, "w:gz") as tar:
        for rel in INCLUDE:
            base = ROOT / rel
            if not base.exists():
                continue
            for p in ([base] if base.is_file() else sorted(base.rglob("*"))):
                if p.is_file() and not any(s in str(p) for s in SKIP):
                    info = tar.gettarinfo(str(p), arcname="pulseforge-engine/" + str(p.relative_to(ROOT)))
                    info.uid = info.gid = 0
                    info.uname = info.gname = ""
                    info.mtime = 0
                    with open(p, "rb") as fh:
                        tar.addfile(info, fh)
                    n += 1
    print(json.dumps({"artifact": OUT.name, "files": n, "bytes": OUT.stat().st_size, "sha256": hashlib.sha256(OUT.read_bytes()).hexdigest()}))


main()
