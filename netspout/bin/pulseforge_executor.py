#!/usr/bin/env python3
"""
NetSpout PulseForge Backend Execution Engine
Cross-Platform PulseForge Process Management & Input Sanitization
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
SCENARIOS_DIR = os.path.join(APP_DIR, "appserver", "static", "scenarios")
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

    # Allowed Scenario Aliases to Local Files
    SCENARIO_MAP = {
        "normal": os.path.join(SCENARIOS_DIR, "scenario_acme_full_network_topology.yml"),
        "global": os.path.join(SCENARIOS_DIR, "scenario_acme_full_network_topology.yml"),
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
        import run_simulation
        previous = run_simulation.APP_DIR
        try:
            run_simulation.APP_DIR = APP_DIR
            return run_simulation.resolve_binary()
        finally:
            run_simulation.APP_DIR = previous

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

        from datablaster_rest import get_stored_config, resolve_hec_urls
        cfg = get_stored_config(payload.get("session_key", ""))
        sanitized["hec_url"] = resolve_hec_urls(cfg["hec_url"], cfg)[0]

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
        from datablaster_rest import resolve_scenario_path
        sanitized["config_file"] = resolve_scenario_path(config_file, APP_DIR)
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
                "--url", sanitized["hec_url"]
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
        Checks if a PulseForge simulation process is currently running.
        Returns: (bool is_running, int pid or None)
        """
        from datablaster_rest import get_active_run_dir
        if not os.path.isfile(os.path.join(get_active_run_dir(), "datablaster.pid")):
            return False, None

        try:
            from datablaster_rest import get_active_run_dir, _read_private_file
            pid_str = _read_private_file(os.path.join(get_active_run_dir(), "datablaster.pid")).strip()
            if not pid_str:
                return False, None
            pid = int(pid_str)

            # Check if process is alive (signal 0 does not kill process)
            from datablaster_rest import is_process_running
            if not is_process_running(pid):
                cls._remove_pid_file()
                return False, None
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
        from datablaster_rest import simulation_start_lock
        with simulation_start_lock():
            return cls._start_simulation_locked(payload)

    @classmethod
    def _start_simulation_locked(cls, payload: dict) -> dict:
        """
        Asynchronously launches PulseForge with validated inputs.
        Streams stdout/stderr to $SPLUNK_HOME/var/log/splunk/ta_datablaster_execution.log.
        Returns immediate status dictionary without blocking Splunk Web thread.
        """
        from datablaster_rest import has_netspout_admin
        if not has_netspout_admin(payload.get("session_key", "")):
            raise PermissionError("netspout_admin capability required")
        running, pid = cls.is_running()
        if running:
            return {
                "status": "already_running",
                "pid": pid,
                "message": f"PulseForge is already actively running with PID {pid}.",
                "log_file": EXECUTION_LOG_PATH
            }

        from datablaster_rest import cleanup_stale_run_files
        cleanup_stale_run_files()
        # Validate inputs & locate binary
        sanitized = cls.sanitize_inputs(payload)
        from datablaster_rest import HECCredentialStore, has_netspout_admin
        session_key = payload.get("session_key", "")
        if not has_netspout_admin(session_key):
            raise PermissionError("netspout_admin capability required")
        credential = None
        if sanitized["output"] == "splunkhec":
            credential = HECCredentialStore(session_key).read()
            binary_path = sys.executable
            cmd_args = [binary_path, os.path.join(APP_DIR, "bin", "run_simulation.py"),
                        "--scenario", sanitized["config_file"], "--hec", sanitized["hec_url"],
                        "--eps", str(sanitized["eps"])]
        else:
            binary_path = cls.get_platform_binary()
            cmd_args = cls.build_command_args(binary_path, sanitized)

        # Open dedicated execution log file for streaming
        log_file = open(EXECUTION_LOG_PATH, "a", encoding="utf-8")

        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        log_file.write(f"\n{'='*75}\n")
        log_file.write(f"[{timestamp}] [LAUNCH] Starting PulseForge Simulation Engine\n")
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
                stdin=subprocess.PIPE, text=True, close_fds=True, start_new_session=True
            )

            if credential is not None:
                proc.stdin.write(json.dumps({"credential": credential}))
            proc.stdin.close()

            # Store PID
            from datablaster_rest import get_active_run_dir, write_private_file
            write_private_file(os.path.join(get_active_run_dir(), "datablaster.pid"), str(proc.pid))

            logger.info("Spawned PulseForge daemon process PID: %d", proc.pid)

            return {
                "status": "started",
                "pid": proc.pid,
                "platform": sys.platform,
                "binary": binary_path,
                "target_eps": sanitized["eps"],
                "target_hec": sanitized["hec_url"],
                "config_file": sanitized["config_file"],
                "log_file": EXECUTION_LOG_PATH,
                "message": f"PulseForge successfully launched in background (PID: {proc.pid})."
            }
        except Exception as e:
            logger.error("Failed to start PulseForge process")
            log_file.write(f"[{timestamp}] [ERROR] Failed to start process\n")
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
                "message": "No active PulseForge process found to stop."
            }

        from datablaster_rest import stop_simulation
        return stop_simulation()

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
            from datablaster_rest import get_active_run_dir
            os.unlink(os.path.join(get_active_run_dir(), "datablaster.pid"))
        except OSError:
            pass


# Preferred public spelling; the historical class remains the same object.
PulseForgeExecutor = DataBlasterExecutor


if __name__ == "__main__":
    # Test Harness / CLI Interface
    import argparse

    parser = argparse.ArgumentParser(description="NetSpout PulseForge Backend CLI Test Harness")
    parser.add_argument("action", choices=["status", "start", "stop", "logs"], default="status", nargs="?")
    parser.add_argument("--eps", type=int, default=10, help="Target EPS")
    parser.add_argument("--url", default="", help="Splunk HEC URL")
    parser.add_argument("--session-key", default="")
    parser.add_argument("--scenario", default="normal", help="Simulation scenario alias")
    parser.add_argument("--tail", type=int, default=30, help="Log lines to tail")

    args = parser.parse_args()

    if args.action == "status":
        print(json.dumps(DataBlasterExecutor.get_status(), indent=2))
    elif args.action == "start":
        payload = {
            "eps": args.eps,
            "hec_url": args.url,
            "session_key": args.session_key,
            "scenario": args.scenario
        }
        res = DataBlasterExecutor.start_simulation(payload)
        print(json.dumps(res, indent=2))
    elif args.action == "stop":
        print(json.dumps(DataBlasterExecutor.stop_simulation(), indent=2))
    elif args.action == "logs":
        for line in DataBlasterExecutor.get_logs(tail_lines=args.tail):
            print(line)
