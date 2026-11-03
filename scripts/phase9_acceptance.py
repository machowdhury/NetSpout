#!/usr/bin/env python3
"""Run the Phase 9 browser-to-Splunk acceptance groups against the isolated TA-validation lab.

  python scripts/phase9_acceptance.py [group ...]          groups: asa ios fortinet pan metrics   (default: all, in that order)

Prerequisites (started by the operator, all isolated from the demo): the recording tap (scripts/phase9_hec_proxy.py, 19990), a backend with its own config dir
(backend/run.py --port 18681 with NETSPOUT_CONFIG_DIR set), and the Vite dev server (14273). For each group the matching add-on is installed in the lab (one at a time, via
scripts/lab_ta.py), the Playwright spec runs with PHASE9_ONLY=<group>, and the lab is returned to the Splunk Add-on for Cisco ASA at the end (its state before Phase 9).
Credentials come only from tests/lab/ta_validation/.env.lab and are never printed.
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKS = Path.home() / "netspout/private-packs"
ASA = ("Splunk_TA_cisco-asa", "splunk-add-on-for-cisco-asa_612.spl")
TA = {"asa": ASA, "ios": ("TA_cisco_catalyst", "cisco-enterprise-networking-add-on-for-splunk_4060.tgz"), "fortinet": ("Splunk_TA_fortinet_fortigate", "fortinet-fortigate-add-on-for-splunk_1610.tar.gz"),
      "pan": ("Splunk_TA_paloalto_networks", "splunk-add-on-for-palo-alto-networks_400.spl"), "metrics": ASA}
MANAGED = {v[0] for v in TA.values()}
LAB_TA = [sys.executable, str(ROOT / "scripts/lab_ta.py")]
CHROMIUM = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH") or str(Path.home() / "Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell")


def installed():
    import json
    return {a for a, _ in json.loads(subprocess.run(LAB_TA + ["apps"], check=True, capture_output=True, text=True).stdout.strip().splitlines()[-1])}


def ensure(app, pkg):
    have = installed()
    for other in sorted((have & MANAGED) - {app}):
        subprocess.run(LAB_TA + ["remove", other], check=True, capture_output=True)
    if app not in have:
        subprocess.run(LAB_TA + ["install", str(PACKS / pkg)], check=True, capture_output=True)
    print("lab add-on:", sorted(installed() & MANAGED))


def run_group(g):
    ensure(*TA[g])
    env = dict(os.environ, PHASE9_ONLY=g, PHASE9_API_BASE="http://127.0.0.1:18681", PHASE9_TAP="http://127.0.0.1:19990", PHASE9_LAB_ENV=str(ROOT / "tests/lab/ta_validation/.env.lab"),
               PLAYWRIGHT_BASE_URL="http://127.0.0.1:14273", PLAYWRIGHT_CHROMIUM_PATH=CHROMIUM)
    return subprocess.run(["npx", "playwright", "test", "tests/phase9-acceptance.spec.ts", "--workers=1", "--trace", "off", "--reporter=list"], cwd=ROOT / "frontend", env=env).returncode


def main(a):
    groups = a or ["asa", "ios", "fortinet", "pan", "metrics"]
    rc = {}
    try:
        for g in groups:
            rc[g] = run_group(g)
    finally:
        ensure(*ASA)
    print("exit codes:", rc)
    return 1 if any(rc.values()) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
