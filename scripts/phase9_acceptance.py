#!/usr/bin/env python3
"""Run the Phase 9 browser-to-Splunk acceptance groups against the isolated TA-validation lab.

  python scripts/phase9_acceptance.py [--rc] [group ...]   groups: asa ios fortinet pan metrics   (default: all, in that order)

--rc runs the same suite against the PACKAGED release candidate: the browser signs in to Splunk Web of the RC install lab (tests/lab/rc_install, web 39000), the app's own static bundle is served by
Splunk, every API call goes through the app's gateway to the engine container built from the candidate's tarball, the event and metric indexes are the ones the app defines (idx_network_ops,
cisco_mdt_metrics), a tap on 39990 fronts that lab's HEC, and add-ons are installed into that lab with scripts/phase10_rc_install.py. Evidence goes to docs/verification/evidence/phase10_rc[_ui].

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
RC = False
LAB_TA = [sys.executable, str(ROOT / "scripts/lab_ta.py")]
CHROMIUM = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH") or str(Path.home() / "Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell")


def installed():
    import json
    return {a for a, _ in json.loads(subprocess.run(LAB_TA + ["apps"], check=True, capture_output=True, text=True).stdout.strip().splitlines()[-1])}


def rc_mode():
    global RC, LAB_TA
    RC = True
    LAB_TA = [sys.executable, str(ROOT / "scripts/phase10_rc_install.py")]



def ensure(app, pkg):
    have = installed()
    for other in sorted((have & MANAGED) - {app}):
        subprocess.run(LAB_TA + ["remove-ta" if RC else "remove", other], check=True, capture_output=True)
    if app not in have:
        subprocess.run(LAB_TA + ["install-ta" if RC else "install", str(PACKS / pkg)], check=True, capture_output=True)
    print("lab add-on:", sorted(installed() & MANAGED))


def run_group(g):
    ensure(*TA[g])
    env = dict(os.environ, PHASE9_ONLY=g, PHASE9_API_BASE="http://127.0.0.1:18681", PHASE9_TAP="http://127.0.0.1:19990", PHASE9_LAB_ENV=str(ROOT / "tests/lab/ta_validation/.env.lab"),
               PLAYWRIGHT_BASE_URL="http://127.0.0.1:14273", PLAYWRIGHT_CHROMIUM_PATH=CHROMIUM)
    if RC:
        env.update(PHASE9_SPLUNK_WEB="http://127.0.0.1:39000", PHASE9_API_BASE="http://127.0.0.1:39000/en-US/splunkd/__raw/services/netspout_gateway", PHASE9_TAP="http://127.0.0.1:39990",
                   PHASE9_ENGINE_TAP="http://host.docker.internal:39990", PHASE9_ENGINE_SEARCH_URL="https://splunk:8089/services/search/jobs/export", PHASE9_LAB_ENV=str(ROOT / "tests/lab/rc_install/.env.lab"),
                   PHASE9_EVENT_INDEX="idx_network_ops", PHASE9_METRIC_INDEX="cisco_mdt_metrics", PHASE9_OUT="phase10_rc", PLAYWRIGHT_BASE_URL="http://127.0.0.1:39000")
    return subprocess.run(["npx", "playwright", "test", "tests/phase9-acceptance.spec.ts", "--workers=1", "--trace", "off", "--reporter=list"], cwd=ROOT / "frontend", env=env).returncode


def main(a):
    if "--rc" in a:
        a.remove("--rc")
        rc_mode()
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
