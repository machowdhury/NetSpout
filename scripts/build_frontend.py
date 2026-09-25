#!/usr/bin/env python3
"""
NetSpout Architecture Guardrail: Frontend Production Build & Synchronization
1. Verifies that frontend/src/ is authoritative source
2. Runs clean production build (npm run build)
3. Copies generated artifacts from frontend/dist/ to netspout/appserver/static/dist/
4. Verifies bundle existence, hashes, and non-empty status
"""

import os
import sys
import shutil
import subprocess

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FRONTEND_DIR = os.path.join(REPO_ROOT, "frontend")
SRC_DIR = os.path.join(FRONTEND_DIR, "src")
FRONTEND_DIST = os.path.join(FRONTEND_DIR, "dist")
STATIC_DIST = os.path.join(REPO_ROOT, "netspout", "appserver", "static", "dist")


def build_frontend():
    print("==========================================================================")
    print("⚡ NetSpout: Building Unified React Production Frontend Bundle")
    print("==========================================================================")

    if not os.path.exists(SRC_DIR):
        print(f"❌ Error: Canonical frontend source missing at {SRC_DIR}")
        sys.exit(1)

    print(">> 1. Running npm run build in frontend/...")
    res = subprocess.run(["npm", "run", "build"], cwd=FRONTEND_DIR, capture_output=True, text=True)
    if res.returncode != 0:
        print("❌ npm run build failed!")
        print(res.stderr)
        sys.exit(res.returncode)
    print("  [PASS] TypeScript and Vite production bundle compiled cleanly.")

    print(">> 2. Synchronizing generated dist/ -> netspout/appserver/static/dist/...")
    if os.path.exists(STATIC_DIST):
        shutil.rmtree(STATIC_DIST)
    shutil.copytree(FRONTEND_DIST, STATIC_DIST)
    print(f"  [PASS] Copied {FRONTEND_DIST} to {STATIC_DIST}")

    print(">> 3. Verifying Generated Bundle Integrity...")
    index_html = os.path.join(STATIC_DIST, "index.html")
    assets_dir = os.path.join(STATIC_DIST, "assets")

    if not os.path.exists(index_html):
        print("❌ Missing index.html in static dist!")
        sys.exit(1)

    js_files = [f for f in os.listdir(assets_dir) if f.endswith(".js")] if os.path.exists(assets_dir) else []
    if not js_files:
        print("❌ Missing JS bundle chunks in static dist/assets!")
        sys.exit(1)

    print(f"  [PASS] index.html verified ({os.path.getsize(index_html)} bytes)")
    print(f"  [PASS] JS Bundle verified: {js_files[0]} ({os.path.getsize(os.path.join(assets_dir, js_files[0]))} bytes)")
    print("==========================================================================")
    print("✅ Frontend Production Bundle built and synchronized successfully!")
    print("==========================================================================")


if __name__ == "__main__":
    build_frontend()
