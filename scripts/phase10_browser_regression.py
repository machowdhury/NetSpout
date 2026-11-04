#!/usr/bin/env python3
"""Browser regression that needs no Splunk: a fresh, isolated stack (fake HEC, engine with its own state directory, Vite pointed at that engine) and the specs in the order they require.

  python scripts/phase10_browser_regression.py

Order matters: tests/phase4e-use-case-explorer.spec.ts expects an UNCONFIGURED destination, and tests/phase6-simple-ui.spec.ts configures one, so the explorer runs first.
The Vite proxy is pointed at the isolated engine with NETSPOUT_DEV_BACKEND; nothing here talks to the default engine port (8081, the demo) or to any Splunk.
Specs: phase4e-use-case-explorer, phase6-scenario-studio (mocked), phase6-simple-ui (fake receiver), unified-shell.
"""
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API, HEC, WEB = 18581, 18599, 14173
CHROMIUM = os.environ.get("PLAYWRIGHT_CHROMIUM_PATH") or str(Path.home() / "Library/Caches/ms-playwright/chromium_headless_shell-1248/chrome-headless-shell-mac-arm64/chrome-headless-shell")


def up(url, tries=40):
    for _ in range(tries):
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(1)
    return False


def main():
    for p in (API, HEC, WEB):
        if subprocess.run(["lsof", "-nP", "-iTCP:%d" % p, "-sTCP:LISTEN"], capture_output=True).stdout:
            sys.exit("port %d is already in use; stop that process first (this runner never reuses a running stack)" % p)
    state = tempfile.mkdtemp(prefix="pf-p10-")
    procs = []
    try:
        procs.append(subprocess.Popen([sys.executable, str(ROOT / "scripts/phase6_fake_hec.py"), str(HEC)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True))
        procs.append(subprocess.Popen([sys.executable, str(ROOT / "backend/run.py"), "--port", str(API)], env=dict(os.environ, NETSPOUT_CONFIG_DIR=state, NETSPOUT_HEC_TOKEN="fake"), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True))
        procs.append(subprocess.Popen(["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(WEB)], cwd=ROOT / "frontend", env=dict(os.environ, NETSPOUT_DEV_BACKEND="http://127.0.0.1:%d" % API), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True))
        assert up("http://127.0.0.1:%d/api/setup" % API) and up("http://127.0.0.1:%d/_stats" % HEC) and up("http://127.0.0.1:%d/" % WEB), "stack did not start"
        assert b'"configured":false' in urllib.request.urlopen("http://127.0.0.1:%d/api/setup" % WEB).read().replace(b" ", b""), "the dev proxy must reach the fresh isolated engine"
        env = dict(os.environ, PHASE6_API_BASE="http://127.0.0.1:%d" % API, PHASE6_HEC_STATS="http://127.0.0.1:%d" % HEC, PLAYWRIGHT_BASE_URL="http://127.0.0.1:%d" % WEB, PLAYWRIGHT_CHROMIUM_PATH=CHROMIUM)
        rc = subprocess.run(["npx", "playwright", "test", "tests/phase4e-use-case-explorer.spec.ts", "tests/phase6-scenario-studio.spec.ts", "tests/phase6-simple-ui.spec.ts", "tests/unified-shell.spec.ts",
                             "--workers=1", "--trace", "off", "--reporter=list"], cwd=ROOT / "frontend", env=env).returncode
        return rc
    finally:
        for p in procs:
            try:
                os.killpg(os.getpgid(p.pid), signal.SIGTERM)   # npm starts a child; stop the whole group
            except Exception:
                pass
        time.sleep(1)
        shutil.rmtree(state, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
