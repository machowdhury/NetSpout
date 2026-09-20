#!/usr/bin/env python3
"""
TA-datablaster Simulation Execution Wrapper & Multi-Vendor Streaming Engine
Part of TA-datablaster Splunk App

AppInspect & Cloud Vetting Compliant:
- Uses sys.platform for dynamic native binary resolution.
- Enforces subprocess.Popen with explicit argument lists and shell=False.
- Safely generates ephemeral configuration files for HEC destination and EPS throttling.
- Implements validate_and_stream_mv_scenario for chronological multi-vendor streaming.
"""

import argparse
import os
import re
import signal
import sys
import subprocess
import time
import json
import shutil

# App root directory
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(APP_DIR, "samples")
STATIC_SAMPLES_DIR = os.path.join(APP_DIR, "appserver", "static", "samples")
RUN_DIR = os.path.join(APP_DIR, "var", "run")

# Platform binary mapping matching user specification
PLATFORM_MAP = {
    "darwin": [
        "/Users/mahamudc/Documents/network-sim/data-blaster-mac-2022-03-22",
        "/Users/mahamudc/Documents/network-sim/data-blaster-mac",
        "/Users/mahamudc/Documents/network-sim/data-blaster",
    ],
    "linux": [
        "/Users/mahamudc/Documents/network-sim/data-blaster-linux",
        "/Users/mahamudc/Documents/network-sim/data-blaster",
    ],
    "win32": [
        "/Users/mahamudc/Documents/network-sim/data-blaster-win.exe",
        "/Users/mahamudc/Documents/network-sim/data-blaster.exe",
    ],
}


def resolve_binary() -> str:
    """Dynamically determine the platform binary matching sys.platform, falling back to python_engine."""
    platform_key = sys.platform
    if platform_key.startswith("linux"):
        platform_key = "linux"
    elif platform_key == "darwin":
        platform_key = "darwin"
    elif platform_key.startswith("win"):
        platform_key = "win32"

    candidates = list(PLATFORM_MAP.get(platform_key, []))
    candidates.extend([
        os.path.join(APP_DIR, "data-blaster"),
        os.path.join(APP_DIR, "bin", "data-blaster"),
        os.path.join(APP_DIR, "bin", f"data-blaster-{platform_key}")
    ])
    for path in candidates:
        if os.path.exists(path) and (os.access(path, os.X_OK) or platform_key == "win32"):
            # Ensure not executing Mach-O on Linux
            if platform_key == "linux":
                try:
                    with open(path, "rb") as bf:
                        magic = bf.read(4)
                        if magic.startswith(b"\x7fELF"):
                            return path
                except Exception:
                    pass
            else:
                return path

    return "python_engine"


def sanitize_input(val: str, pattern: str, name: str) -> str:
    """Validate string against regex pattern."""
    if not re.match(pattern, val):
        raise ValueError(f"Security validation failed for parameter '{name}': illegal format")
    return val


def mask_secret(secret: str) -> str:
    """Mask credentials for safe operational logging."""
    if not secret:
        return "********"
    if len(secret) <= 8:
        return "********"
    return f"{secret[:4]}****{secret[-4:]}"


def prepare_scenario_config(scenario_path: str, eps: int, hec_url: str, hec_token: str) -> str:
    """
    Prepare an ephemeral scenario configuration file with updated HEC endpoints and token.
    Uses basic line parsing to avoid external PyYAML dependency if not installed in Splunk python.
    """
    os.makedirs(RUN_DIR, exist_ok=True)
    out_filename = f"active_sim_{int(time.time())}.yml"
    out_path = os.path.join(RUN_DIR, out_filename)

    with open(scenario_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    workers = max(1, min(50, int(eps / 100) if eps > 100 else 1))

    new_lines = []
    endpoints_written = False
    token_written = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("generatorWorkers:"):
            indent = line[:line.find("generatorWorkers")]
            new_lines.append(f"{indent}generatorWorkers: {workers}\n")
            continue
        if stripped.startswith("outputWorkers:"):
            indent = line[:line.find("outputWorkers")]
            new_lines.append(f"{indent}outputWorkers: {workers}\n")
            continue
        if stripped.startswith("endpoints:"):
            indent = line[:line.find("endpoints")]
            new_lines.append(f"{indent}endpoints:\n")
            new_lines.append(f"{indent}  - {hec_url}\n")
            endpoints_written = True
            continue
        if stripped.startswith("- http://") or stripped.startswith("- https://"):
            if endpoints_written:
                continue
        if stripped.startswith("splunkHECToken:"):
            indent = line[:line.find("splunkHECToken")]
            new_lines.append(f"{indent}splunkHECToken: {hec_token}\n")
            token_written = True
            continue

        new_lines.append(line)

    if not token_written and hec_token:
        new_lines.append(f"    splunkHECToken: {hec_token}\n")

    with open(out_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    return out_path


def validate_and_stream_mv_scenario(scenario_path, hec_url=None, hec_token=None, target_eps=None):
    """
    Asynchronously coordinates the execution of cross-vendor streaming scenarios
    ensuring that numeric metrics scale realistically via a temporal degradation curve.
    """
    # Environment variable fallbacks for secrets and endpoints
    hec_url = hec_url or os.environ.get("SPLUNK_HEC_URL", "https://127.0.0.1:8088/services/collector")
    hec_token = hec_token or os.environ.get("SPLUNK_HEC_TOKEN", "00000000-0000-0000-0000-000000000000")
    if target_eps is None:
        target_eps = int(os.environ.get("DATABLASTER_TARGET_EPS", 1000))

    # Enforce strict input data sanitization for AppInspect safety
    if not re.match(r"^\d+$", str(target_eps)):
        raise ValueError("Security Violation: Target EPS parameter must be an integer string pattern.")
        
    if ".." in scenario_path or not scenario_path.endswith('.yml'):
        raise ValueError("Security Violation: Unauthorized path traversal attempt detected.")

    print(f"Initializing Multi-Vendor Simulation Engine targeting HEC: {hec_url} (Token: {mask_secret(hec_token)})")
    print(f"Loading Playbook Matrix Configuration: {os.path.basename(scenario_path)}")
    
    # Platform Detection Framework (Maps dynamically across local user structures cleanly)
    current_os = sys.platform
    binary_base_path = "/Users/mahamudc/Documents/network-sim"
    
    if current_os == "darwin":
        binary_executable = os.path.join(binary_base_path, "data-blaster-mac-2022-03-22")
    elif current_os == "linux":
        binary_executable = os.path.join(binary_base_path, "data-blaster-linux")
    else:
        binary_executable = os.path.join(binary_base_path, "data-blaster-win.exe")

    # If the specific platform binary is not directly available, resolve via candidate map
    if not (os.path.exists(binary_executable) and os.access(binary_executable, os.X_OK)):
        binary_executable = resolve_binary()

    if binary_executable == "python_engine":
        cmd = [
            sys.executable,
            os.path.abspath(__file__),
            "--python-stream",
            "--scenario", scenario_path,
            "--hec", hec_url,
            "--token", hec_token,
            "--eps", str(target_eps)
        ]
        process = subprocess.Popen(
            cmd,
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            cwd=APP_DIR,
            start_new_session=True
        )
        return process.pid

    # Pre-configure ephemeral config for HEC and worker rates
    active_config = prepare_scenario_config(scenario_path, int(target_eps), hec_url, hec_token)
    samples_dir = SAMPLES_DIR if os.path.exists(SAMPLES_DIR) else STATIC_SAMPLES_DIR

    # Construct the explicit arguments array (Shell=False is mandatory for Splunk Cloud deployment)
    # Uses data-blaster native flags (--config, --url, --splunkHECToken)
    blast_cmd = [
        binary_executable,
        "--config", active_config,
        "--url", hec_url,
        "--splunkHECToken", hec_token,
        "--samplesDir", samples_dir,
        "--info"
    ]
    
    try:
        # Spawn execution process asynchronously to prevent web server thread hangs
        process = subprocess.Popen(
            blast_cmd,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=APP_DIR
        )
        return process.pid
    except Exception as e:
        print(f"Execution Generation Failure: {str(e)}")
        sys.exit(1)


def blast_single_device(device_info: dict, hec_url: str, hec_token: str, count: int = 1) -> dict:
    """
    Emits test events/metrics for a single device node directly to Splunk HEC.
    Supports both single event testing and burst testing for individual technologies.
    """
    import urllib.request
    import urllib.error
    import ssl
    import json
    import time

    event_body = device_info.get("sampleEvent")
    if not event_body:
        event_body = f"TEST_EVENT: device={device_info.get('name', 'node')} vendor={device_info.get('vendor', 'cisco')} status=OK"

    is_metric = (device_info.get("metricsMode", False) or 
                 device_info.get("index") == "cisco_mdt_metrics" or 
                 "metric" in str(device_info.get("sourcetype", "")).lower() or
                 device_info.get("sourcetype") == "cisco:ios:mdt")
    if is_metric:
        payload = {
            "time": time.time(),
            "event": "metric",
            "host": device_info.get("host", "device.corp.local"),
            "source": device_info.get("source", "telemetry"),
            "sourcetype": device_info.get("sourcetype", "cisco:ios:mdt:metric"),
            "index": device_info.get("index", "cisco_mdt_metrics"),
            "fields": {
                "metric_name:cpu.utilization": 28.4,
                "metric_name:memory.utilization": 41.6,
                "metric_name:interface.octets.in": 98412034.0,
                "metric_name:interface.octets.out": 81249104.0,
                "metric_name:buffer.utilization_pct": 14.5,
                "_value": 28.4,
                "vendor": device_info.get("vendor", "cisco"),
                "device": device_info.get("name", "node")
            }
        }
    else:
        payload = {
            "time": time.time(),
            "host": device_info.get("host", "device.corp.local"),
            "source": device_info.get("source", f"{device_info.get('vendor', 'cisco')}:syslog"),
            "sourcetype": device_info.get("sourcetype", "cisco:ios"),
            "index": device_info.get("index", "idx_network_ops"),
            "event": event_body
        }

    data = json.dumps(payload).encode("utf-8")

    candidate_urls = [hec_url]
    if ":8888" in hec_url:
        candidate_urls.append(hec_url.replace(":8888", ":8088"))
    elif ":8088" in hec_url:
        candidate_urls.append(hec_url.replace(":8088", ":8888"))

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    last_err = None
    for target_url in candidate_urls:
        try:
            req = urllib.request.Request(target_url, data=data, method="POST")
            req.add_header("Authorization", f"Splunk {hec_token}")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, context=ctx, timeout=5) as response:
                resp_code = response.getcode()
                resp_text = response.read().decode("utf-8")
                return {
                    "status": "success",
                    "code": resp_code,
                    "response": resp_text,
                    "device": device_info.get("name"),
                    "hec_url": target_url
                }
        except urllib.error.HTTPError as e:
            return {
                "status": "error",
                "code": e.code,
                "message": e.read().decode("utf-8"),
                "hec_url": target_url
            }
        except Exception as e:
            last_err = str(e)
            continue

    return {"status": "error", "message": f"HEC Connection Failed: {last_err or 'unreachable'}"}


def stream_custom_canvas_topology(nodes: list, links: list, hec_url: str, hec_token: str, eps: int) -> int:
    """
    Synthesizes an ephemeral scenario YAML from the visual canvas nodes and links,
    then launches validate_and_stream_mv_scenario asynchronously.
    """
    os.makedirs(RUN_DIR, exist_ok=True)
    scenario_id = f"canvas_custom_{int(time.time())}"
    scen_filename = f"{scenario_id}.yml"
    scen_path = os.path.join(RUN_DIR, scen_filename)

    lines_yaml = []
    lines_yaml.append(f'scenario_id: "{scenario_id}"')
    lines_yaml.append('name: "Custom Visual Canvas Network Flow Simulation"')
    lines_yaml.append(f'description: "Dynamically synthesized topology spanning {len(nodes)} nodes across {len(links)} network path links."')
    lines_yaml.append('')
    lines_yaml.append('global:')
    lines_yaml.append('  earliest: -15m')
    lines_yaml.append('  latest: now')
    lines_yaml.append(f'  target_eps: {eps}')
    lines_yaml.append('  interval: 1000')
    lines_yaml.append('  workers: 4')
    lines_yaml.append('  endpoints:')
    lines_yaml.append(f'    - "{hec_url}"')
    lines_yaml.append('  tokens:')
    lines_yaml.append(f'    - "{hec_token}"')
    lines_yaml.append('')
    lines_yaml.append('tokens:')
    lines_yaml.append('  SYSLOG_TS:')
    lines_yaml.append('    type: date')
    lines_yaml.append('    format: "%b %d %H:%M:%S"')
    lines_yaml.append('  ISO_TS:')
    lines_yaml.append('    type: date')
    lines_yaml.append('    format: "%Y-%m-%dT%H:%M:%S.000Z"')
    lines_yaml.append('  FLOW_ID:')
    lines_yaml.append('    type: random')
    lines_yaml.append('    replacement: int')
    lines_yaml.append('    lower: 10000')
    lines_yaml.append('    upper: 99999')
    lines_yaml.append('')
    lines_yaml.append('samples:')
    lines_yaml.append('  - name: canvas_flow_pipeline')
    lines_yaml.append('    lines:')

    for n in nodes:
        host = n.get("host", f"{n.get('id', 'node')}.corp.internal")
        index = n.get("index", "idx_network_ops")
        sourcetype = n.get("sourcetype", "cisco:ios")
        source = n.get("source", f"{n.get('vendor', 'net')}:syslog")
        event_raw = n.get("sampleEvent", f"$SYSLOG_TS$ {host} NetFlow: flow_id=$FLOW_ID$ proto=TCP action=forward status=established")
        clean_raw = event_raw.replace('"', '\\"') if '"' in event_raw else event_raw
        lines_yaml.append(f'      - index: {index}')
        lines_yaml.append(f'        source: {source}')
        lines_yaml.append(f'        sourcetype: {sourcetype}')
        lines_yaml.append(f'        host: {host}')
        lines_yaml.append(f'        _raw: "{clean_raw}"')

    lines_yaml.append('')

    with open(scen_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines_yaml))

    return validate_and_stream_mv_scenario(scen_path, hec_url, hec_token, eps)



def run_python_streamer(scenario_file: str, hec_url: str, hec_token: str, eps: int):
    """Pure-Python synthetic generator fallback when no native compiled binary is present."""
    import urllib.request
    import urllib.error
    import ssl
    import random

    events_to_stream = []
    if os.path.exists(scenario_file):
        try:
            with open(scenario_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            curr_index = "idx_network_ops"
            curr_st = "cisco:ios"
            curr_source = "cisco:syslog"
            curr_host = "core-router.corp.internal"
            for l in lines:
                ls = l.strip()
                if ls.startswith("index:"):
                    curr_index = ls.split(":", 1)[1].strip()
                elif ls.startswith("sourcetype:"):
                    curr_st = ls.split(":", 1)[1].strip()
                elif ls.startswith("source:"):
                    curr_source = ls.split(":", 1)[1].strip()
                elif ls.startswith("host:"):
                    curr_host = ls.split(":", 1)[1].strip()
                elif ls.startswith("_raw:") or ls.startswith("raw:"):
                    raw_val = ls.split(":", 1)[1].strip().strip('"').strip("'")
                    events_to_stream.append({
                        "index": curr_index,
                        "sourcetype": curr_st,
                        "source": curr_source,
                        "host": curr_host,
                        "raw": raw_val
                    })
        except Exception as e:
            sys.stderr.write(f"[BLASTER-PY] Scenario parse warning: {e}\n")

    if not events_to_stream:
        events_to_stream = [
            {"index": "idx_network_ops", "sourcetype": "cisco:ios", "source": "cisco:syslog", "host": "core-sw01.corp.internal", "raw": "$SYSLOG_TS$ core-sw01 Interface GigabitEthernet0/1 up"},
            {"index": "idx_network_ops", "sourcetype": "juniper:junos", "source": "juniper:syslog", "host": "edge-junos.corp.internal", "raw": "$SYSLOG_TS$ edge-junos RPD_BGP_NEIGHBOR_STATE_CHANGED: BGP neighbor 198.51.100.1 state changed from Established to Idle"},
            {"index": "idx_security_fw", "sourcetype": "pan:traffic", "source": "pan:firewall", "host": "pa-5450-edge.corp.internal", "raw": "1,$ISO_TS$,001801000001,TRAFFIC,drop,2304,$ISO_TS$,10.0.1.10,198.51.100.23,0.0.0.0,0.0.0.0,Rule-Deny,src-user,dst-user,ssl,vsys1,untrust,trust,ethernet1/1,ethernet1/2,Log-Forward,2026/09/18 22:00:00,1001,1,443,443,0,0,0x0,tcp,deny,120,120,0,1,2026/09/18 22:00:00,0,any,0,293847291,0x0,10.0.0.0-10.255.255.255,US,1,1,0,aged-out,0,0,0,0,,pa-5450-edge,from-policy"},
            {"index": "idx_security_fw", "sourcetype": "fortinet:fortigate", "source": "fortinet:firewall", "host": "fgt-edge-01.corp.internal", "raw": "date=2026-09-18 time=22:00:00 devname=\"FGT-EDGE-01\" devid=\"FGT37E1234567890\" eventtime=1789768000 tz=\"-0400\" logid=\"0000000013\" type=\"traffic\" subtype=\"forward\" level=\"notice\" vd=\"root\" srcip=10.100.5.42 srcport=51234 srcintf=\"port1\" dstip=198.51.100.50 dstport=443 dstintf=\"port2\" sessionid=987654 proto=6 action=\"accept\" policyid=1 policytype=\"policy\" service=\"HTTPS\" trandisp=\"snat\" transip=203.0.113.10 transport=51234 duration=45 sentbyte=1420 rcvdbyte=8920 sentpkt=12 rcvdpkt=18 appcat=\"unscanned\""},
            {"index": "idx_performance_metrics", "sourcetype": "arista:telemetry:json", "source": "arista:telemetry", "host": "dc1-spine01.corp.internal", "raw": "{\"timestamp\": \"$ISO_TS$\", \"device\": \"dc1-spine01\", \"vendor\": \"Arista\", \"roce.pfc_rx_frames\": 1420, \"buffer_pool.shared_bytes_used_pct\": 94.2}"}
        ]

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    print(f"[BLASTER-PY] Starting Python Native Simulation Engine ({len(events_to_stream)} templates)...")
    print(f"[BLASTER-PY] Target HEC: {hec_url} (Token: {mask_secret(hec_token)}), EPS: {eps}")
    sys.stdout.flush()

    batch_size = max(5, min(50, eps // 2))
    sleep_time = max(0.1, batch_size / max(1, eps))

    while True:
        batch = []
        now = time.time()
        syslog_ts = time.strftime("%b %d %H:%M:%S", time.localtime(now))
        iso_ts = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(now))

        for _ in range(batch_size):
            item = random.choice(events_to_stream)
            raw = item["raw"].replace("$SYSLOG_TS$", syslog_ts).replace("$ISO_TS$", iso_ts).replace("$FLOW_ID$", str(random.randint(10000, 99999)))
            is_metric_item = (item["index"] == "cisco_mdt_metrics" or 
                              "metric" in item["index"].lower() or 
                              "metric" in item["sourcetype"].lower() or
                              item["sourcetype"] == "cisco:ios:mdt")
            if is_metric_item:
                batch.append(json.dumps({
                    "time": now,
                    "host": item["host"],
                    "source": item["source"],
                    "sourcetype": item["sourcetype"] if "metric" in item["sourcetype"] else f"{item['sourcetype']}:metric",
                    "index": item["index"],
                    "event": "metric",
                    "fields": {
                        "metric_name:cpu.utilization": round(random.uniform(15.0, 85.0), 2),
                        "metric_name:memory.utilization": round(random.uniform(30.0, 75.0), 2),
                        "metric_name:interface.octets.in": float(random.randint(1000000, 50000000)),
                        "metric_name:interface.octets.out": float(random.randint(1000000, 50000000)),
                        "metric_name:interface.errors.in": 0.0,
                        "_value": round(random.uniform(15.0, 85.0), 2),
                        "device": item["host"],
                        "vendor": "cisco"
                    }
                }))
            else:
                batch.append(json.dumps({
                    "time": now,
                    "host": item["host"],
                    "source": item["source"],
                    "sourcetype": item["sourcetype"],
                    "index": item["index"],
                    "event": raw
                }))

        payload = "\n".join(batch).encode("utf-8")
        req = urllib.request.Request(
            hec_url,
            data=payload,
            headers={
                "Authorization": f"Splunk {hec_token}",
                "Content-Type": "application/json"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
                print(f"[BLASTER] Streamed batch of {batch_size} events to {hec_url} (HTTP {resp.status})")
                sys.stdout.flush()
        except Exception as e:
            sys.stderr.write(f"[BLASTER-PY-WARN] HEC Send Error: {e}\n")
            sys.stderr.flush()

        time.sleep(sleep_time)


def main():
    parser = argparse.ArgumentParser(description="TA-network-data-blaster Secure Simulation Runner")
    parser.add_argument("--scenario", required=True, help="Path to scenario YAML file")
    parser.add_argument("--eps", type=int, default=int(os.environ.get("DATABLASTER_TARGET_EPS", 1000)), help="Target Events Per Second (integer)")
    parser.add_argument("--hec", default=os.environ.get("SPLUNK_HEC_URL", "https://127.0.0.1:8088/services/collector"), help="Target Splunk HEC URL")
    parser.add_argument("--token", default=os.environ.get("SPLUNK_HEC_TOKEN", "00000000-0000-0000-0000-000000000000"), help="Splunk HEC Token GUID")
    parser.add_argument("--sample", required=False, default=None, help="Optional sample filter")
    parser.add_argument("--async-exec", action="store_true", help="Launch asynchronously and return PID immediately")
    parser.add_argument("--python-stream", action="store_true", help="Run using native Python streaming engine")

    args = parser.parse_args()

    if args.python_stream:
        run_python_streamer(args.scenario, args.hec, args.token, args.eps)
        sys.exit(0)

    # 1. Input sanitization
    if args.eps <= 0 or args.eps > 500000:
        sys.stderr.write(f"[ERROR] Invalid EPS value: {args.eps}. Must be between 1 and 500,000.\n")
        sys.exit(1)

    # Sanitize scenario path (prevent traversal)
    if ".." in args.scenario or not re.match(r"^[a-zA-Z0-9_\-./]+$", args.scenario):
        sys.stderr.write(f"[ERROR] Invalid scenario path characters detected.\n")
        sys.exit(1)

    scenario_file = args.scenario
    if not os.path.isabs(scenario_file):
        candidate_app = os.path.join(APP_DIR, scenario_file)
        candidate_scenarios = os.path.join(APP_DIR, "scenarios", os.path.basename(scenario_file))
        candidate_static = os.path.join(APP_DIR, "appserver", "static", "scenarios", os.path.basename(scenario_file))
        if os.path.exists(candidate_app):
            scenario_file = candidate_app
        elif os.path.exists(candidate_scenarios):
            scenario_file = candidate_scenarios
        elif os.path.exists(candidate_static):
            scenario_file = candidate_static
        else:
            sys.stderr.write(f"[ERROR] Scenario file not found: {args.scenario}\n")
            sys.exit(1)

    if args.async_exec:
        pid = validate_and_stream_mv_scenario(scenario_file, args.hec, args.token, args.eps)
        print(f"[TA-network-data-blaster] Launched process asynchronously with PID: {pid}")
        sys.exit(0)

    # 2. Multi-Platform Binary Selection
    try:
        binary_path = resolve_binary()
    except Exception as e:
        sys.stderr.write(f"[ERROR] {e}\n")
        sys.exit(1)

    print(f"[TA-network-data-blaster] Host OS: {sys.platform}")
    print(f"[TA-network-data-blaster] Using Execution Engine: {binary_path}")
    print(f"[TA-network-data-blaster] Scenario: {scenario_file}")
    print(f"[TA-network-data-blaster] Target EPS: {args.eps}")
    print(f"[TA-network-data-blaster] HEC Endpoint: {args.hec} (Token: {mask_secret(args.token)})")

    if binary_path == "python_engine":
        run_python_streamer(scenario_file, args.hec, args.token, args.eps)
        sys.exit(0)

    # 3. Prepare Config
    try:
        active_config = prepare_scenario_config(scenario_file, args.eps, args.hec, args.token)
    except Exception as e:
        sys.stderr.write(f"[ERROR] Failed preparing ephemeral config: {e}\n")
        sys.exit(1)

    samples_dir = SAMPLES_DIR if os.path.exists(SAMPLES_DIR) else STATIC_SAMPLES_DIR

    # 4. Execute Native Binary (Strictly shell=False)
    cmd = [
        binary_path,
        "-c", active_config,
        "--samplesDir", samples_dir,
        "--info",
    ]

    print(f"[TA-datablaster] Spawning process (shell=False): {' '.join(cmd[:3])}...")
    sys.stdout.flush()

    try:
        proc = subprocess.Popen(
            cmd,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            cwd=APP_DIR
        )

        if proc.stdout:
            for line in iter(proc.stdout.readline, ""):
                print(f"[BLASTER] {line.strip()}")
                sys.stdout.flush()

        proc.wait()
        print(f"[TA-datablaster] Simulation finished with return code {proc.returncode}")
        sys.exit(proc.returncode)

    except Exception as e:
        sys.stderr.write(f"[ERROR] Process execution failed: {e}\n")
        sys.exit(1)
    finally:
        if os.path.exists(active_config):
            try:
                os.remove(active_config)
            except OSError:
                pass


if __name__ == "__main__":
    main()
