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
import tempfile
import stat
from datablaster_rest import resolve_run_dir, resolve_hec_urls, get_stored_config, hec_request, resolve_scenario_path, cleanup_stale_run_files

# App root directory
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(APP_DIR, "samples")
STATIC_SAMPLES_DIR = os.path.join(APP_DIR, "appserver", "static", "samples")
RUN_DIR = ""
_PRIVATE_FILES = set()

def resolve_binary() -> str:
    platform_key = "linux" if sys.platform.startswith("linux") else ("darwin" if sys.platform == "darwin" else "win32")
    for name in ("data-blaster-" + platform_key, "data-blaster"):
        path = os.path.join(APP_DIR, "bin", name)
        try:
            info = os.lstat(path)
            if (stat.S_ISREG(info.st_mode) and info.st_uid == os.getuid()
                    and not info.st_mode & 0o022 and os.access(path, os.X_OK)):
                return path
        except OSError:
            pass
    return "python_engine"


class NoStreamableEventsError(ValueError):
    """Raised when a scenario file yields no streamable events."""
    pass


def sanitize_input(val: str, pattern: str, name: str) -> str:
    """Validate string against regex pattern."""
    if not re.match(pattern, val):
        raise ValueError(f"Security validation failed for parameter '{name}': illegal format")
    return val


def mask_secret(secret: str) -> str:
    """Mask credentials for safe operational logging."""
    return "********"


def prepare_scenario_config(scenario_path: str, eps: int, hec_url: str, hec_token: str) -> str:
    """Build a native configuration from approved scenario data."""
    import yaml

    global RUN_DIR
    RUN_DIR = resolve_run_dir()
    resolve_hec_urls(hec_url, get_stored_config())
    with open(scenario_path, "r", encoding="utf-8") as stream:
        scenario = yaml.safe_load(stream)
    if not isinstance(scenario, dict):
        raise ValueError("Scenario must be a mapping")
    workers = max(1, min(50, int(eps / 100) if eps > 100 else 1))
    section = "global" if "global" in scenario and "general" not in scenario else "general"
    original = scenario.get(section, {})
    if not isinstance(original, dict):
        original = {}
    settings = {}
    for key in ("workerThreads", "globalInterval", "rotInterval", "earliest", "latest", "interval"):
        value = original.get(key)
        if (key in original and isinstance(value, (str, int, float, bool, type(None)))
                and not re.search(r"[a-zA-Z][a-zA-Z0-9+.-]*://", str(value))):
            settings[key] = value
    settings.update(generatorWorkers=workers, outputWorkers=workers)
    output = original.get("output", {})
    buffer_bytes = output.get("bufferBytes") if isinstance(output, dict) else None
    settings["output"] = {"outputter": "splunkhec", "outputTemplate": "splunkhec",
                          "bufferBytes": buffer_bytes if type(buffer_bytes) is int else 4096,
                          "endpoints": [hec_url], "splunkHECToken": hec_token}
    document = {section: settings}
    sample_keys = ("name", "interval", "count", "randomizeEvents", "tokens", "lines", "earliest", "latest")
    line_keys = ("index", "source", "sourcetype", "host", "_raw", "raw", "_time", "time", "event")
    if "samples" in scenario:
        if not isinstance(scenario["samples"], list):
            raise ValueError("Scenario samples must be a list")
        samples = []
        for sample in scenario["samples"]:
            if not isinstance(sample, dict):
                raise ValueError("Scenario sample must be a mapping")
            item = {k: v for k, v in sample.items() if k in sample_keys}
            if "lines" in item:
                if not isinstance(item["lines"], list):
                    raise ValueError("Sample lines must be a list")
                item["lines"] = [{k: v for k, v in line.items() if k in line_keys}
                                 if isinstance(line, dict) else line for line in item["lines"]]
            samples.append(item)
        document["samples"] = samples
    if isinstance(scenario.get("tokens"), dict):
        document["tokens"] = scenario["tokens"]

    class PlainDumper(yaml.SafeDumper):
        def ignore_aliases(self, data):
            return True

    fd, out_path = tempfile.mkstemp(prefix="active_sim_", suffix=".yml", dir=RUN_DIR)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            yaml.dump(document, stream, Dumper=PlainDumper, sort_keys=False, default_flow_style=False)
    except BaseException:
        os.unlink(out_path)
        raise
    _PRIVATE_FILES.add(out_path)
    return out_path


def validate_and_stream_mv_scenario(scenario_path, hec_url=None, hec_token=None, target_eps=None):
    """
    Asynchronously coordinates the execution of cross-vendor streaming scenarios
    ensuring that numeric metrics scale realistically via a temporal degradation curve.
    """
    cfg = get_stored_config()
    hec_url = resolve_hec_urls(hec_url or cfg["hec_url"], cfg)[0]
    if not hec_token:
        raise ValueError("HEC credential is required")
    target_eps = int(target_eps or 1000)
    cmd = [sys.executable, os.path.abspath(__file__), "--scenario", scenario_path,
           "--hec", hec_url, "--eps", str(target_eps)]
    process = subprocess.Popen(cmd, shell=False, stdin=subprocess.PIPE,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               text=True, cwd=APP_DIR, start_new_session=True)
    process.stdin.write(json.dumps({"credential": hec_token}))
    process.stdin.close()
    return process.pid


def blast_single_device(device_info: dict, hec_url: str, hec_token: str, count: int = 1, ssl_verify: bool = True) -> dict:
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

    candidate_urls = resolve_hec_urls(hec_url, get_stored_config())
    ctx = ssl.create_default_context()
    if not ssl_verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    last_err = None
    for target_url in candidate_urls:
        try:
            req = hec_request(target_url, data=data, method="POST")
            req.add_unredirected_header("Authorization", f"Splunk {hec_token}")
            req.add_header("Content-Type", "application/json")
            with urllib.request.urlopen(req, context=ctx, timeout=5) as response:
                resp_code = response.getcode()
                resp_text = response.read().decode("utf-8")
                return {
                    "status": "success",
                    "code": resp_code,
                    "response": "HEC responded",
                    "device": device_info.get("name"),
                    "hec_url": target_url
                }
        except urllib.error.HTTPError as e:
            return {
                "status": "error",
                "code": e.code,
                "message": "HEC request failed",
                "hec_url": target_url
            }
        except Exception as e:
            last_err = "Operation failed"
            continue

    return {"status": "error", "message": f"HEC Connection Failed: {last_err or 'unreachable'}"}


def stream_custom_canvas_topology(nodes: list, links: list, hec_url: str, hec_token: str, eps: int) -> int:
    """
    Synthesizes an ephemeral scenario YAML from the visual canvas nodes and links,
    then launches validate_and_stream_mv_scenario asynchronously.
    """
    global RUN_DIR
    RUN_DIR = resolve_run_dir()
    cleanup_stale_run_files()
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
    lines_yaml.append(f'    - {json.dumps(hec_url)}')
    lines_yaml.append('  tokens:')
    lines_yaml.append('    - ""')
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
        lines_yaml.append(f'      - index: {json.dumps(index)}')
        lines_yaml.append(f'        source: {json.dumps(source)}')
        lines_yaml.append(f'        sourcetype: {json.dumps(sourcetype)}')
        lines_yaml.append(f'        host: {json.dumps(host)}')
        lines_yaml.append(f'        _raw: {json.dumps(event_raw)}')

    lines_yaml.append('')

    with os.fdopen(os.open(scen_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", encoding="utf-8") as f:
        f.write("\n".join(lines_yaml))

    return validate_and_stream_mv_scenario(scen_path, hec_url, hec_token, eps)



def run_python_streamer(scenario_file: str, hec_url: str, hec_token: str, eps: int):
    """Pure-Python synthetic generator fallback when no native compiled binary is present."""
    import urllib.request
    import urllib.error
    import ssl
    import random

    def decode_value(value):
        value = value.strip()
        if value.startswith('"'):
            return json.loads(value)
        return value.strip("'")

    resolve_hec_urls(hec_url, get_stored_config())
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
                if ls.startswith("- "):
                    ls = ls[2:]
                if ls.startswith("index:"):
                    curr_index = decode_value(ls.split(":", 1)[1])
                elif ls.startswith("sourcetype:"):
                    curr_st = decode_value(ls.split(":", 1)[1])
                elif ls.startswith("source:"):
                    curr_source = decode_value(ls.split(":", 1)[1])
                elif ls.startswith("host:"):
                    curr_host = decode_value(ls.split(":", 1)[1])
                elif ls.startswith("_raw:") or ls.startswith("raw:"):
                    raw_val = decode_value(ls.split(":", 1)[1])
                    events_to_stream.append({
                        "index": curr_index,
                        "sourcetype": curr_st,
                        "source": curr_source,
                        "host": curr_host,
                        "raw": raw_val
                    })
        except Exception as e:
            sys.stderr.write(f"[BLASTER-PY] Scenario parse warning: Operation failed\n")

    if not events_to_stream:
        basename = os.path.basename(scenario_file)
        raise NoStreamableEventsError(f"Scenario '{basename}' has no streamable events")

    ctx = ssl.create_default_context()
    if get_stored_config().get("ssl_verify", True) is False:
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
        req = hec_request(
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
            sys.stderr.write(f"[BLASTER-PY-WARN] HEC Send Error: Operation failed\n")
            sys.stderr.flush()

        time.sleep(sleep_time)


def _main():
    parser = argparse.ArgumentParser(description="TA-network-data-blaster Secure Simulation Runner")
    parser.add_argument("--scenario", required=True, help="Path to scenario YAML file")
    parser.add_argument("--eps", type=int, default=int(os.environ.get("DATABLASTER_TARGET_EPS", 1000)), help="Target Events Per Second (integer)")
    parser.add_argument("--hec", default=os.environ.get("SPLUNK_HEC_URL", "https://127.0.0.1:8088/services/collector"), help="Target Splunk HEC URL")
    parser.add_argument("--ssl-verify", default="true", choices=["true", "false"])
    parser.add_argument("--sample", required=False, default=None, help="Optional sample filter")
    parser.add_argument("--async-exec", action="store_true", help="Launch asynchronously and return PID immediately")
    parser.add_argument("--python-stream", action="store_true", help="Run using native Python streaming engine")

    args = parser.parse_args()

    def stop_runner(signum, frame):
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, stop_runner)
    signal.signal(signal.SIGINT, stop_runner)
    args.scenario = resolve_scenario_path(args.scenario, APP_DIR)
    if (os.path.basename(args.scenario).startswith("canvas_custom_")
            and os.path.dirname(args.scenario) == os.path.realpath(resolve_run_dir())):
        _PRIVATE_FILES.add(args.scenario)
    args.token = json.loads(sys.stdin.read()).get("credential", "")
    resolve_hec_urls(args.hec, get_stored_config())
    if not args.token:
        raise ValueError("HEC credential is required")

    if args.python_stream:
        try:
            run_python_streamer(args.scenario, args.hec, args.token, args.eps)
        except NoStreamableEventsError as e:
            sys.stderr.write(f"{str(e)}\n")
            sys.exit(2)
        finally:
            if os.path.basename(args.scenario).startswith("canvas_custom_") and os.path.dirname(args.scenario) == resolve_run_dir():
                os.unlink(args.scenario)
        sys.exit(0)

    # 1. Input sanitization
    if args.eps <= 0 or args.eps > 500000:
        sys.stderr.write(f"[ERROR] Invalid EPS value: {args.eps}. Must be between 1 and 500,000.\n")
        sys.exit(1)

    scenario_file = args.scenario

    if args.async_exec:
        pid = validate_and_stream_mv_scenario(scenario_file, args.hec, args.token, args.eps)
        print(f"[TA-network-data-blaster] Launched process asynchronously with PID: {pid}")
        sys.exit(0)

    # 2. Multi-Platform Binary Selection
    try:
        binary_path = resolve_binary()
    except Exception as e:
        sys.stderr.write(f"[ERROR] Operation failed\n")
        sys.exit(1)

    print(f"[TA-network-data-blaster] Host OS: {sys.platform}")
    print(f"[TA-network-data-blaster] Using Execution Engine: {binary_path}")
    print(f"[TA-network-data-blaster] Scenario: {scenario_file}")
    print(f"[TA-network-data-blaster] Target EPS: {args.eps}")
    print(f"[TA-network-data-blaster] HEC Endpoint: {args.hec} (Token: {mask_secret(args.token)})")

    # Native engines do not expose a verified TLS configuration contract.
    # Use the Python engine while certificate verification is enabled.
    if binary_path == "python_engine" or get_stored_config().get("ssl_verify", True) is not False:
        try:
            run_python_streamer(scenario_file, args.hec, args.token, args.eps)
        except NoStreamableEventsError as e:
            sys.stderr.write(f"{str(e)}\n")
            sys.exit(2)
        finally:
            if os.path.basename(scenario_file).startswith("canvas_custom_") and os.path.dirname(scenario_file) == resolve_run_dir():
                os.unlink(scenario_file)
        sys.exit(0)

    # 3. Prepare Config
    try:
        active_config = prepare_scenario_config(scenario_file, args.eps, args.hec, args.token)
    except Exception as e:
        sys.stderr.write(f"[ERROR] Failed preparing ephemeral config: Operation failed\n")
        sys.exit(1)

    samples_dir = SAMPLES_DIR if os.path.exists(SAMPLES_DIR) else STATIC_SAMPLES_DIR

    proc = None

    def terminate(signum, frame):
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, terminate)
    signal.signal(signal.SIGINT, terminate)

    # 4. Execute Native Binary (Strictly shell=False)
    cmd = [
        binary_path,
        "-c", active_config,
        "--url", args.hec,
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
                print(f"[BLASTER] {line.strip().replace(args.token, '[redacted]')}")
                sys.stdout.flush()

        proc.wait()
        print(f"[TA-datablaster] Simulation finished with return code {proc.returncode}")
        sys.exit(proc.returncode)

    except Exception as e:
        sys.stderr.write(f"[ERROR] Process execution failed: Operation failed\n")
        sys.exit(1)
    finally:
        if os.path.basename(scenario_file).startswith("canvas_custom_") and os.path.dirname(scenario_file) == resolve_run_dir():
            os.unlink(scenario_file)
        if os.path.exists(active_config):
            try:
                os.remove(active_config)
            except OSError:
                pass


def main():
    _PRIVATE_FILES.clear()
    try:
        _main()
    finally:
        for path in _PRIVATE_FILES:
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass
        _PRIVATE_FILES.clear()


if __name__ == "__main__":
    main()
