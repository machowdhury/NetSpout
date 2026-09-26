#!/usr/bin/env python3
"""
NetSpout Flow Collector Lifecycle & Health Manager
Provides programmatic control over the Docker Compose GoFlow2 + Forwarder stack.
"""

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.request

COMPOSE_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "docker-compose.collector.yml"))
DOCKER_BIN = "/Applications/Docker.app/Contents/Resources/bin/docker"
ENV = os.environ.copy()
ENV["PATH"] = f"/Applications/Docker.app/Contents/Resources/bin:{ENV.get('PATH', '')}"


def run_cmd(cmd: list) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, env=ENV, capture_output=True, text=True)


def start_collector() -> bool:
    print(f"Starting collector stack with {COMPOSE_FILE}...")
    res = run_cmd([DOCKER_BIN, "compose", "-f", COMPOSE_FILE, "up", "-d", "--build"])
    if res.returncode != 0:
        print(f"Failed to start collector: {res.stderr}")
        return False
    print("Waiting for collector and forwarder initialization...")
    time.sleep(2)
    return check_health()


def stop_collector() -> bool:
    print("Stopping collector stack...")
    res = run_cmd([DOCKER_BIN, "compose", "-f", COMPOSE_FILE, "stop"])
    return res.returncode == 0


def down_collector() -> bool:
    print("Tearing down collector stack...")
    res = run_cmd([DOCKER_BIN, "compose", "-f", COMPOSE_FILE, "down", "-v"])
    return res.returncode == 0


def check_health() -> bool:
    healthy = True
    # 1. Check GoFlow2 metrics
    try:
        req = urllib.request.Request("http://127.0.0.1:8080/metrics")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                print("  [PASS] GoFlow2 collector metrics endpoint (127.0.0.1:8080/metrics) is reachable")
            else:
                print(f"  [FAIL] GoFlow2 metrics returned HTTP {resp.status}")
                healthy = False
    except Exception as exc:
        print(f"  [FAIL] GoFlow2 metrics not reachable: {exc}")
        healthy = False

    # 2. Check Forwarder status
    try:
        req = urllib.request.Request("http://127.0.0.1:8082/status")
        with urllib.request.urlopen(req, timeout=3) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                print(f"  [PASS] Forwarder status endpoint (127.0.0.1:8082/status): {data.get('status')}")
                print(f"         Flows Read: {data.get('flows_read')}, Forwarded: {data.get('flows_forwarded')}")
            else:
                print(f"  [FAIL] Forwarder status returned HTTP {resp.status}")
                healthy = False
    except Exception as exc:
        print(f"  [FAIL] Forwarder status not reachable: {exc}")
        healthy = False

    return healthy


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
    parser = argparse.ArgumentParser(description="NetSpout Flow Collector Manager")
    parser.add_argument("action", choices=["start", "stop", "down", "status", "simulate-failure", "restore"])
    args = parser.parse_args()

    if args.action == "start":
        success = start_collector()
        sys.exit(0 if success else 1)
    elif args.action == "stop":
        success = stop_collector()
        sys.exit(0 if success else 1)
    elif args.action == "down":
        success = down_collector()
        sys.exit(0 if success else 1)
    elif args.action == "status":
        success = check_health()
        sys.exit(0 if success else 1)
    elif args.action == "simulate-failure":
        success = simulate_splunk_failure(True)
        sys.exit(0 if success else 1)
    elif args.action == "restore":
        success = simulate_splunk_failure(False)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
