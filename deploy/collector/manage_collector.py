#!/usr/bin/env python3
"""
NetSpout Flow Collector Lifecycle & Health Manager (Productized CLI).
Provides comprehensive control over the containerized GoFlow2 + Forwarder stack.
Supports: start, stop, restart, down, status, diagnostics, preflight, cleanup, simulate-failure, restore.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from typing import Dict, Any, Optional

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

COMPOSE_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "docker-compose.collector.yml"))

DOCKER_SEARCH_LOCATIONS = [
    "/usr/local/bin/docker",
    "/opt/homebrew/bin/docker",
    "/Applications/Docker.app/Contents/Resources/bin/docker",
    os.path.expanduser("~/.docker/bin/docker"),
]


def find_docker_bin() -> Optional[str]:
    """
    Finds available docker binary across standard PATH first, then common macOS
    Docker Desktop binary locations without hardcoding a user home directory.
    """
    which_docker = shutil.which("docker")
    if which_docker and os.path.exists(which_docker) and os.access(which_docker, os.X_OK):
        return which_docker

    for c in DOCKER_SEARCH_LOCATIONS:
        if c and os.path.exists(c) and os.access(c, os.X_OK):
            return c
    return None


DOCKER_BIN = find_docker_bin()
ENV = os.environ.copy()
if DOCKER_BIN:
    docker_dir = os.path.dirname(DOCKER_BIN)
    ENV["PATH"] = f"{docker_dir}:/usr/local/bin:/opt/homebrew/bin:{ENV.get('PATH', '')}"
else:
    ENV["PATH"] = f"/usr/local/bin:/opt/homebrew/bin:{ENV.get('PATH', '')}"


def ensure_docker_bin() -> Optional[str]:
    """Returns discovered docker binary or prints an actionable error message."""
    binary = find_docker_bin()
    if not binary:
        print(
            "[FAIL] Docker executable not found in PATH or standard macOS locations "
            "(/usr/local/bin/docker, /opt/homebrew/bin/docker, "
            "/Applications/Docker.app/Contents/Resources/bin/docker, ~/.docker/bin/docker). "
            "Please install Docker Desktop or add the docker binary directory to PATH."
        )
        return None
    return binary


def run_cmd(cmd: list) -> subprocess.CompletedProcess:
    if cmd and cmd[0] in (DOCKER_BIN, "docker", None):
        binary = ensure_docker_bin()
        if not binary:
            return subprocess.CompletedProcess(cmd, returncode=127, stdout="", stderr="Docker executable not found")
        cmd = [binary] + list(cmd[1:])
    return subprocess.run(cmd, env=ENV, capture_output=True, text=True)


def start_collector() -> bool:
    if not ensure_docker_bin():
        return False
    print(f"Starting NetSpout Native Collector stack...")
    print(f"Compose file: {COMPOSE_FILE}")
    res = run_cmd([DOCKER_BIN or "docker", "compose", "-f", COMPOSE_FILE, "up", "-d", "--build"])
    if res.returncode != 0:
        print(f"[FAIL] Failed to start collector: {res.stderr}")
        return False
    print("Waiting for collector and forwarder initialization (2s)...")
    time.sleep(2)
    return check_health()


def stop_collector() -> bool:
    if not ensure_docker_bin():
        return False
    print("Stopping NetSpout Native Collector stack...")
    res = run_cmd([DOCKER_BIN or "docker", "compose", "-f", COMPOSE_FILE, "stop"])
    if res.returncode == 0:
        print("[OK] Collector stack stopped.")
        return True
    print(f"[FAIL] Failed to stop collector: {res.stderr}")
    return False


def restart_collector() -> bool:
    print("Restarting NetSpout Native Collector stack...")
    res = run_cmd([DOCKER_BIN, "compose", "-f", COMPOSE_FILE, "restart"])
    if res.returncode != 0:
        print(f"[FAIL] Failed to restart collector: {res.stderr}")
        return False
    print("Waiting for services to re-initialize (2s)...")
    time.sleep(2)
    return check_health()


def down_collector() -> bool:
    print("Tearing down NetSpout Native Collector stack and volumes...")
    res = run_cmd([DOCKER_BIN, "compose", "-f", COMPOSE_FILE, "down", "-v"])
    if res.returncode == 0:
        print("[OK] Collector stack and volumes removed.")
        return True
    print(f"[FAIL] Failed to tear down collector: {res.stderr}")
    return False


def cleanup_storage() -> bool:
    print("Cleaning up collector flows and buffer data...")
    try:
        req = urllib.request.Request("http://127.0.0.1:8082/clear", data=b"", method="POST")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                print("  [OK] In-memory flow buffer cleared.")
    except Exception as exc:
        print(f"  [WARN] Failed to clear in-memory buffer: {exc}")

    res = run_cmd([
        DOCKER_BIN, "run", "--rm",
        "-v", "netspout_flow_data:/flows",
        "busybox:1.36",
        "sh", "-c", "rm -f /flows/flows.json* && touch /flows/flows.json && chmod 666 /flows/flows.json"
    ])
    if res.returncode == 0:
        print("  [OK] Shared volume /flows/flows.json reset.")
        return True
    print(f"  [FAIL] Failed to reset flow files: {res.stderr}")
    return False


def check_health(as_json: bool = False) -> bool:
    healthy = True
    report: Dict[str, Any] = {
        "collector_process": False,
        "forwarder_process": False,
        "goflow_metrics_url": "http://127.0.0.1:8080/metrics",
        "forwarder_status_url": "http://127.0.0.1:8082/status",
        "state": "UNKNOWN"
    }

    # 1. Probe GoFlow2
    try:
        req = urllib.request.Request("http://127.0.0.1:8080/metrics")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                report["collector_process"] = True
                if not as_json:
                    print("  [PASS] GoFlow2 collector metrics (127.0.0.1:8080/metrics) is UP")
    except Exception as exc:
        healthy = False
        report["goflow_error"] = str(exc)
        if not as_json:
            print(f"  [FAIL] GoFlow2 metrics (127.0.0.1:8080/metrics) unreachable: {exc}")

    # 2. Probe Forwarder
    try:
        req = urllib.request.Request("http://127.0.0.1:8082/status")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                report["forwarder_process"] = True
                report["forwarder_details"] = data
                if not as_json:
                    print(f"  [PASS] Forwarder status (127.0.0.1:8082/status): {data.get('status')}")
                    print(f"         Flows Read: {data.get('flows_read')}, Forwarded: {data.get('flows_forwarded')}, Failures: {data.get('forward_failures')}")
    except Exception as exc:
        healthy = False
        report["forwarder_error"] = str(exc)
        if not as_json:
            print(f"  [FAIL] Forwarder status (127.0.0.1:8082/status) unreachable: {exc}")

    report["healthy"] = healthy
    report["state"] = "HEALTHY" if healthy else "DEGRADED"

    if as_json:
        print(json.dumps(report, indent=2))

    return healthy


def print_diagnostics() -> bool:
    print("=" * 60)
    print("🔍 NetSpout Native Flow Pipeline Diagnostics")
    print("=" * 60)
    
    # Process inspection
    res = run_cmd([DOCKER_BIN, "ps", "--filter", "name=netspout-flow", "--format", "table {{.Names}}\t{{.Status}}\t{{.Ports}}"])
    print("Container Status:")
    print(res.stdout.strip() if res.stdout else "No containers found")
    print("-" * 60)

    # Scrape Prometheus metrics
    try:
        req = urllib.request.Request("http://127.0.0.1:8080/metrics")
        with urllib.request.urlopen(req, timeout=3) as resp:
            lines = [l.decode().strip() for l in resp.readlines() if "goflow2_flow" in l.decode() and not l.decode().startswith("#")]
            print("GoFlow2 Operational Metrics:")
            for l in lines[:10]:
                print(f"  {l}")
    except Exception as e:
        print(f"  [WARN] Failed to scrape GoFlow2 metrics: {e}")

    print("-" * 60)
    # Scrape Forwarder status
    try:
        req = urllib.request.Request("http://127.0.0.1:8082/status")
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            print("Forwarder Telemetry Status:")
            for k, v in data.items():
                print(f"  {k}: {v}")
    except Exception as e:
        print(f"  [WARN] Failed to scrape Forwarder status: {e}")

    print("=" * 60)
    return True


def run_preflight() -> bool:
    print("=" * 60)
    print("🚀 NetSpout Native Flow Pre-Flight Readiness Audit")
    print("=" * 60)
    from netspout_core.collector_evidence import CollectorEvidenceAdapter
    adapter = CollectorEvidenceAdapter()
    results = adapter.run_preflight_check()
    for check_name, check_data in results["checks"].items():
        status = check_data.get("status", "UNKNOWN")
        badge = "[PASS]" if status == "PASS" else "[FAIL]"
        print(f"  {badge} {check_name}: {status}")
        if "message" in check_data:
            print(f"         {check_data['message']}")
        if "note" in check_data:
            print(f"         ℹ️ {check_data['note']}")
    print("-" * 60)
    print(f"Overall Pre-Flight Status: {'READY' if results['overall_ready'] else 'NOT READY'}")
    print("=" * 60)
    return results["overall_ready"]


def simulate_splunk_failure(fail: bool) -> bool:
    try:
        data = json.dumps({"fail": fail}).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:8082/simulate_splunk_failure", data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=3) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            print(f"Simulate Splunk failure state updated: {res}")
            return True
    except Exception as exc:
        print(f"Failed to set simulate Splunk failure: {exc}")
        return False


def main():
    parser = argparse.ArgumentParser(description="NetSpout Native Flow Collector Lifecycle Manager")
    parser.add_argument(
        "action",
        choices=["start", "stop", "restart", "down", "status", "diagnostics", "preflight", "cleanup", "simulate-failure", "restore"]
    )
    parser.add_argument("--json", action="store_true", help="Output status report in JSON format")
    args = parser.parse_args()

    if args.action == "start":
        success = start_collector()
    elif args.action == "stop":
        success = stop_collector()
    elif args.action == "restart":
        success = restart_collector()
    elif args.action == "down":
        success = down_collector()
    elif args.action == "cleanup":
        success = cleanup_storage()
    elif args.action == "status":
        success = check_health(as_json=args.json)
    elif args.action == "diagnostics":
        success = print_diagnostics()
    elif args.action == "preflight":
        success = run_preflight()
    elif args.action == "simulate-failure":
        success = simulate_splunk_failure(True)
    elif args.action == "restore":
        success = simulate_splunk_failure(False)
    else:
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
