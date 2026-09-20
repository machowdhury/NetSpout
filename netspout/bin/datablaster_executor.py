#!/usr/bin/env python3
"""
TA-datablaster Backend Execution Engine
Cross-Platform Data Blaster Process Management & Input Sanitization
Compliant with Splunk Cloud Vetting and AppInspect Guidelines
"""

import os
import sys
import re
import json
import time
import signal
import subprocess
import logging
from urllib.parse import urlparse

# Resolve Base Application Directory
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENARIOS_DIR = os.path.join(APP_DIR, "scenarios")
SAMPLES_DIR = os.path.join(APP_DIR, "samples")

# Resolve Splunk Home and Standard Log Path
SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
if SPLUNK_HOME and os.path.isdir(SPLUNK_HOME):
    LOG_DIR = os.path.join(SPLUNK_HOME, "var", "log", "splunk")
else:
    LOG_DIR = os.path.join(APP_DIR, "var", "log", "splunk")

os.makedirs(LOG_DIR, exist_ok=True)
EXECUTION_LOG_PATH = os.path.join(LOG_DIR, "ta_datablaster_execution.log")
PID_FILE_PATH = os.path.join(LOG_DIR, "ta_datablaster.pid")

# Configure Python Logger
logger = logging.getLogger("ta_datablaster")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.FileHandler(EXECUTION_LOG_PATH, mode="a", encoding="utf-8")
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [PID:%(process)d] %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)


class DataBlasterExecutor:
    """
    Manages asynchronous lifecycle of cross-platform data-blaster processes.
    Enforces AppInspect security, platform detection, and input sanitization.
    """

    # Static Platform Binary Mappings
    PLATFORM_BINARIES = {
        "darwin": "/Users/mahamudc/Documents/network-sim/data-blaster-mac",
        "linux": "/Users/mahamudc/Documents/network-sim/data-blaster-linux",
        "win32": "/Users/mahamudc/Documents/network-sim/data-blaster-win.exe",
    }

    # Safe Fallback Search Paths
    FALLBACK_PATHS = {
        "darwin": [
            "/Users/mahamudc/Documents/network-sim/data-blaster-mac",
            "/Users/mahamudc/Documents/network-sim/data-blaster-mac-2022-03-22",
            os.path.join(APP_DIR, "data-blaster"),
            os.path.join(APP_DIR, "bin", "data-blaster-mac"),
        ],
        "linux": [
            "/Users/mahamudc/Documents/network-sim/data-blaster-linux",
            "/Users/mahamudc/Documents/network-sim/data-blaster",
            os.path.join(APP_DIR, "data-blaster"),
            os.path.join(APP_DIR, "bin", "data-blaster-linux"),
        ],
        "win32": [
            "/Users/mahamudc/Documents/network-sim/data-blaster-win.exe",
            "/Users/mahamudc/Documents/network-sim/data-blaster.exe",
            os.path.join(APP_DIR, "data-blaster.exe"),
            os.path.join(APP_DIR, "bin", "data-blaster-win.exe"),
        ],
    }

    # Allowed Scenario Aliases to Local Files
    SCENARIO_MAP = {
        "normal": os.path.join(APP_DIR, "global.yml"),
        "global": os.path.join(APP_DIR, "global.yml"),
        "acme_network": os.path.join(SCENARIOS_DIR, "scenario_acme_full_network_topology.yml"),
        "ddos": os.path.join(SCENARIOS_DIR, "scenario_core.yml"),
        "brute_force": os.path.join(SCENARIOS_DIR, "scenario_maple_security.yml"),
        "aci_bd": os.path.join(SCENARIOS_DIR, "scenario_acme_bridge_domain_withdrawal.yml"),
        "meraki": os.path.join(SCENARIOS_DIR, "scenario_meraki_branch_assurance.yml"),
        "sdwan": os.path.join(SCENARIOS_DIR, "scenario_acme_sdwan_toronto_degradation.yml"),
        "campus": os.path.join(SCENARIOS_DIR, "scenario_acme_campus_cross_domain_visibility.yml"),
        "mpls": os.path.join(SCENARIOS_DIR, "scenario_acme_mpls_backbone_realtime.yml"),
        "srv6": os.path.join(SCENARIOS_DIR, "scenario_acme_mpls_to_srv6_transition.yml"),
    }

    @classmethod
    def get_platform_binary(cls) -> str:
        """
        Dynamically identifies host OS using sys.platform and locates
        the verified executable binary.
        """
        plat = sys.platform
        primary_path = cls.PLATFORM_BINARIES.get(plat)

        # 1. Check primary specified path
        if primary_path and os.path.isfile(primary_path) and os.access(primary_path, os.X_OK):
            return primary_path

        # 2. Check candidate fallbacks for current OS
        candidates = cls.FALLBACK_PATHS.get(plat, [])
        for candidate in candidates:
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate

        # 3. Raise informative error if no compatible binary exists
        raise FileNotFoundError(
            f"No executable data-blaster binary found for platform '{plat}'. "
            f"Primary expected: {primary_path}. Candidates checked: {candidates}"
        )

    @classmethod
    def sanitize_inputs(cls, payload: dict) -> dict:
        """
        AppInspect Security Enforcement:
        Validates, type-checks, and sanitizes all incoming UI request parameters.
        Completely neutralizes command injection and path traversal risks.
        """
        if not isinstance(payload, dict):
            raise ValueError("Payload must be a valid JSON dictionary.")

        sanitized = {}

        # 1. Sanitize Target EPS (Integer, range: 1 - 50,000)
        raw_eps = payload.get("eps", payload.get("target_eps", 50))
        try:
            eps = int(raw_eps)
            if eps < 1 or eps > 50000:
                raise ValueError("EPS out of bounds (allowed: 1 - 50,000)")
            sanitized["eps"] = eps
        except (ValueError, TypeError):
            raise ValueError(f"Invalid EPS parameter: '{raw_eps}'. Must be integer between 1 and 50,000.")

        # 2. Sanitize HEC URL (Scheme, Hostname, Port validation)
        raw_url = str(payload.get("hec_url", payload.get("url", ""))).strip()
        if not raw_url:
            raw_url = "https://http-inputs.pog0-poc-premium.splunkcloud.com/services/collector"

        parsed_url = urlparse(raw_url)
        if parsed_url.scheme not in ("http", "https"):
            raise ValueError(f"Invalid HEC URL scheme '{parsed_url.scheme}'. Must be http or https.")
        if not parsed_url.netloc or not re.match(r"^[a-zA-Z0-9\.\-:_]+$", parsed_url.netloc):
            raise ValueError(f"Invalid HEC hostname/netloc: '{parsed_url.netloc}'.")
        # Check for forbidden shell metacharacters in path
        if re.search(r"[\s;&|`$><\"']", raw_url):
            raise ValueError("HEC URL contains forbidden shell metacharacters.")
        sanitized["hec_url"] = raw_url

        # 3. Sanitize HEC Token (UUID or Alphanumeric Hex/JWT format)
        raw_token = str(payload.get("hec_token", payload.get("token", ""))).strip()
        if not raw_token:
            raw_token = "c9c483a6-b69b-4136-8805-a8e4b345fe06"
        if not re.match(r"^[a-zA-Z0-9_\-\.]{8,256}$", raw_token):
            raise ValueError("Invalid HEC Token format. Must be 8-256 alphanumeric characters, hyphens, or dots.")
        sanitized["hec_token"] = raw_token

        # 4. Sanitize Scenario / Config Path
        raw_scenario = str(payload.get("scenario", "normal")).strip().lower()
        if ".." in raw_scenario or ("/" in raw_scenario and not os.path.abspath(raw_scenario).startswith(APP_DIR)):
            raise ValueError("Invalid scenario parameter: directory traversal sequences are strictly prohibited.")

        if raw_scenario in cls.SCENARIO_MAP:
            config_file = cls.SCENARIO_MAP[raw_scenario]
        else:
            # Custom file path: restrict strictly to APP_DIR, no directory traversal
            clean_name = os.path.basename(raw_scenario)
            possible_path = os.path.join(SCENARIOS_DIR, clean_name)
            if os.path.isfile(possible_path):
                config_file = possible_path
            else:
                config_file = cls.SCENARIO_MAP["normal"]

        if not os.path.isfile(config_file):
            raise FileNotFoundError(f"Configuration scenario file not found: '{config_file}'")
        sanitized["config_file"] = os.path.abspath(config_file)
        sanitized["scenario"] = raw_scenario

        # 5. Sanitize Output Mode
        raw_output = str(payload.get("output", "splunkhec")).strip().lower()
        if raw_output not in ("splunkhec", "stdout", "file"):
            raw_output = "splunkhec"
        sanitized["output"] = raw_output

        # 6. Realtime toggle
        sanitized["realtime"] = bool(payload.get("realtime", True))

        return sanitized

    @classmethod
    def build_command_args(cls, binary_path: str, sanitized: dict) -> list:
        """
        Builds a strictly structured argument list for subprocess.Popen(shell=False).
        Guarantees zero shell interpolation.
        """
        cmd = [
            binary_path,
            "-c", sanitized["config_file"]
        ]

        # Outputter configuration
        if sanitized["output"] == "splunkhec":
            cmd.extend([
                "-o", "splunkhec",
                "--url", sanitized["hec_url"],
                "--splunkHECToken", sanitized["hec_token"]
            ])
        elif sanitized["output"] == "stdout":
            cmd.extend(["-o", "stdout"])

        cmd.append("gen")

        # Map target EPS / count
        eps = sanitized.get("eps", 50)
        if eps > 0:
            cmd.extend(["-c", str(eps), "-i", "1"])

        if sanitized.get("realtime", True):
            cmd.append("-r")
        else:
            cmd.extend(["--endIntervals", "1"])

        return cmd

    @classmethod
    def is_running(cls) -> tuple:
        """
        Checks if a Data Blaster simulation process is currently running.
        Returns: (bool is_running, int pid or None)
        """
        if not os.path.isfile(PID_FILE_PATH):
            return False, None

        try:
            with open(PID_FILE_PATH, "r", encoding="utf-8") as f:
                pid_str = f.read().strip()
                if not pid_str:
                    return False, None
                pid = int(pid_str)

            # Check if process is alive (signal 0 does not kill process)
            os.kill(pid, 0)
            return True, pid
        except (ProcessLookupError, ValueError):
            # Process dead or stale PID file
            cls._remove_pid_file()
            return False, None
        except PermissionError:
            # Running under another user, but process exists
            return True, pid

    @classmethod
    def start_simulation(cls, payload: dict) -> dict:
        """
        Asynchronously launches Data Blaster with validated inputs.
        Streams stdout/stderr to $SPLUNK_HOME/var/log/splunk/ta_datablaster_execution.log.
        Returns immediate status dictionary without blocking Splunk Web thread.
        """
        running, pid = cls.is_running()
        if running:
            return {
                "status": "already_running",
                "pid": pid,
                "message": f"DataBlaster is already actively running with PID {pid}.",
                "log_file": EXECUTION_LOG_PATH
            }

        # Validate inputs & locate binary
        sanitized = cls.sanitize_inputs(payload)
        binary_path = cls.get_platform_binary()
        cmd_args = cls.build_command_args(binary_path, sanitized)

        # Open dedicated execution log file for streaming
        log_file = open(EXECUTION_LOG_PATH, "a", encoding="utf-8")

        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        log_file.write(f"\n{'='*75}\n")
        log_file.write(f"[{timestamp}] [LAUNCH] Starting DataBlaster Simulation Engine\n")
        log_file.write(f"Platform   : {sys.platform}\n")
        log_file.write(f"Binary     : {binary_path}\n")
        log_file.write(f"Config     : {sanitized['config_file']}\n")
        log_file.write(f"Target HEC : {sanitized['hec_url']}\n")
        log_file.write(f"Target EPS : {sanitized['eps']}\n")
        log_file.write(f"Command    : {' '.join(cmd_args)}\n")
        log_file.write(f"{'='*75}\n")
        log_file.flush()

        # Launch Asynchronously with shell=False (MANDATORY for Splunk AppInspect)
        try:
            proc = subprocess.Popen(
                cmd_args,
                shell=False,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                cwd=APP_DIR,
                close_fds=True
            )

            # Store PID
            with open(PID_FILE_PATH, "w", encoding="utf-8") as f:
                f.write(str(proc.pid))

            logger.info("Spawned DataBlaster daemon process PID: %d", proc.pid)

            return {
                "status": "started",
                "pid": proc.pid,
                "platform": sys.platform,
                "binary": binary_path,
                "target_eps": sanitized["eps"],
                "target_hec": sanitized["hec_url"],
                "config_file": sanitized["config_file"],
                "log_file": EXECUTION_LOG_PATH,
                "message": f"DataBlaster successfully launched in background (PID: {proc.pid})."
            }
        except Exception as e:
            logger.error("Failed to start DataBlaster process: %s", str(e))
            log_file.write(f"[{timestamp}] [ERROR] Failed to start: {str(e)}\n")
            log_file.flush()
            log_file.close()
            raise

    @classmethod
    def stop_simulation(cls) -> dict:
        """
        Terminates the active Data Blaster background process.
        """
        running, pid = cls.is_running()
        if not running or not pid:
            return {
                "status": "not_running",
                "message": "No active DataBlaster process found to stop."
            }

        try:
            logger.info("Terminating DataBlaster PID: %d", pid)
            os.kill(pid, signal.SIGTERM)

            # Wait briefly for clean shutdown
            for _ in range(10):
                time.sleep(0.2)
                try:
                    os.kill(pid, 0)
                except ProcessLookupError:
                    break
            else:
                # Force kill if unresponsive
                os.kill(pid, signal.SIGKILL)

            cls._remove_pid_file()

            # Append to log
            with open(EXECUTION_LOG_PATH, "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}] [STOP] Process PID {pid} stopped by user.\n")

            return {
                "status": "stopped",
                "pid": pid,
                "message": f"DataBlaster process PID {pid} successfully stopped."
            }
        except Exception as e:
            cls._remove_pid_file()
            logger.error("Error while terminating PID %d: %s", pid, str(e))
            return {
                "status": "error",
                "pid": pid,
                "message": f"Error stopping process: {str(e)}"
            }

    @classmethod
    def get_logs(cls, tail_lines: int = 100) -> list:
        """
        Reads the most recent log lines from ta_datablaster_execution.log.
        Used dynamically by UI Tab 4 (Scenario Logs).
        """
        if not os.path.isfile(EXECUTION_LOG_PATH):
            return ["Log file not yet generated. Ready to start."]

        try:
            with open(EXECUTION_LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                return [line.rstrip() for line in lines[-tail_lines:]]
        except Exception as e:
            return [f"Error reading log file: {str(e)}"]

    @classmethod
    def get_status(cls) -> dict:
        """
        Returns full diagnostic status of the simulation engine.
        """
        running, pid = cls.is_running()
        binary_available = True
        detected_binary = ""
        error_msg = ""

        try:
            detected_binary = cls.get_platform_binary()
        except FileNotFoundError as e:
            binary_available = False
            error_msg = str(e)

        return {
            "is_running": running,
            "pid": pid,
            "platform": sys.platform,
            "binary_path": detected_binary,
            "binary_available": binary_available,
            "error": error_msg,
            "log_file": EXECUTION_LOG_PATH,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

    @classmethod
    def _remove_pid_file(cls):
        try:
            if os.path.isfile(PID_FILE_PATH):
                os.remove(PID_FILE_PATH)
        except OSError:
            pass


if __name__ == "__main__":
    # Test Harness / CLI Interface
    import argparse

    parser = argparse.ArgumentParser(description="TA-datablaster Backend CLI Test Harness")
    parser.add_argument("action", choices=["status", "start", "stop", "logs"], default="status", nargs="?")
    parser.add_argument("--eps", type=int, default=10, help="Target EPS")
    parser.add_argument("--url", default="", help="Splunk HEC URL")
    parser.add_argument("--token", default="", help="Splunk HEC Token")
    parser.add_argument("--scenario", default="normal", help="Simulation scenario alias")
    parser.add_argument("--tail", type=int, default=30, help="Log lines to tail")

    args = parser.parse_args()

    if args.action == "status":
        print(json.dumps(DataBlasterExecutor.get_status(), indent=2))
    elif args.action == "start":
        payload = {
            "eps": args.eps,
            "hec_url": args.url,
            "hec_token": args.token,
            "scenario": args.scenario
        }
        res = DataBlasterExecutor.start_simulation(payload)
        print(json.dumps(res, indent=2))
    elif args.action == "stop":
        print(json.dumps(DataBlasterExecutor.stop_simulation(), indent=2))
    elif args.action == "logs":
        for line in DataBlasterExecutor.get_logs(tail_lines=args.tail):
            print(line)
