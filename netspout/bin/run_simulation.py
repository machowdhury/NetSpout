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
import contextlib
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
from datablaster_rest import resolve_run_dir, resolve_hec_urls, get_stored_config, hec_request, resolve_scenario_path, cleanup_stale_run_files, get_orchestration_log_path, validate_syslog_settings

# App root directory
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLES_DIR = os.path.join(APP_DIR, "samples")
STATIC_SAMPLES_DIR = os.path.join(APP_DIR, "appserver", "static", "samples")
RUN_DIR = ""
_PRIVATE_FILES = set()

_RUNTIME_CONFIG = None


def runtime_config():
    return get_stored_config() if _RUNTIME_CONFIG is None else _RUNTIME_CONFIG


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
    resolve_hec_urls(hec_url, runtime_config())
    with open(scenario_path, "r", encoding="utf-8") as stream:
        scenario = yaml.safe_load(stream)
    if not isinstance(scenario, dict):
        raise ValueError("Scenario must be a mapping")
    if "pulseforge_incident" in scenario:
        import network_incidents
        incident = network_incidents.descriptor(scenario_path)
        if incident is None:
            raise ValueError("Invalid network incident descriptor")
        # The legacy samples interface carries logs. Native incident execution
        # retains its own supported metric path and server-owned run identity.
        events = network_incidents.select_events(network_incidents.generate(
            incident["pulseforge_incident"], incident["seed"], eps=eps), "syslog", {})
        scenario = {"samples": [
            {"name": incident["pulseforge_incident"] + "_" + str(position),
             "count": 1, "randomizeEvents": False,
             "lines": [{"index": event["index"], "source": event["source"],
                        "sourcetype": event["sourcetype"], "host": event["host"],
                        "_time": event["time"], "_raw": event["raw"]}]}
            for position, event in enumerate(events)]}
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


def validate_and_stream_mv_scenario(scenario_path, hec_url=None, hec_token=None, target_eps=None, run_id=None):
    """
    Asynchronously coordinates the execution of cross-vendor streaming scenarios
    ensuring that numeric metrics scale realistically via a temporal degradation curve.
    """
    cfg = runtime_config()
    hec_url = resolve_hec_urls(hec_url or cfg["hec_url"], cfg)[0]
    if not hec_token:
        raise ValueError("HEC credential is required")
    target_eps = int(target_eps or 1000)
    cmd = [sys.executable, os.path.abspath(__file__), "--scenario", scenario_path,
           "--hec", hec_url, "--eps", str(target_eps)]
    log_path = get_orchestration_log_path()
    with open(log_path, "a", encoding="utf-8") as log_handle:   # closed in the parent on success and on error
        log_handle.write(f"\n=======================================================\n")
        log_handle.write(f"SESSION START: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n")
        log_handle.write(f"INVOCATION: {' '.join(cmd[:4])} [HEC credentials redacted]\n")
        log_handle.write(f"=======================================================\n")
        log_handle.flush()
        process = subprocess.Popen(cmd, shell=False, stdin=subprocess.PIPE,
                                   stdout=log_handle, stderr=subprocess.STDOUT,
                                   text=True, cwd=APP_DIR, start_new_session=True)
    process.stdin.write(json.dumps({"credential": hec_token, "run_id": run_id}))
    process.stdin.close()
    return process.pid


def blast_single_device(device_info: dict, hec_url: str, hec_token: str, count: int = 1, ssl_verify: bool = True, run_id=None) -> dict:
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

    if run_id:
        from native_run_monitor import attach
        payload = attach(payload, run_id)
    data = json.dumps(payload).encode("utf-8")

    candidate_urls = resolve_hec_urls(hec_url, runtime_config())
    ctx = ssl.create_default_context()
    if not ssl_verify:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    last_err = None
    for target_url in candidate_urls:
        try:
            req = hec_request(target_url, configuration=runtime_config(), data=data, method="POST")
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



def load_python_scenario_events(scenario_file, strict=False):
    def decode_value(value):
        value = value.strip()
        if value.startswith('"'):
            return json.loads(value)
        return value.strip("'")

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
            if strict:
                raise ValueError("Invalid syslog scenario template") from None
            sys.stderr.write(f"[BLASTER-PY] Scenario parse warning: Operation failed\n")

    if not events_to_stream:
        basename = os.path.basename(scenario_file)
        raise NoStreamableEventsError(f"Scenario '{basename}' has no streamable events")

    return events_to_stream


def run_python_streamer(scenario_file: str, hec_url: str, hec_token: str, eps: int, run_id=None):
    """Pure-Python synthetic generator fallback when no native compiled binary is present."""
    import urllib.request
    import urllib.error
    import ssl
    import random

    resolve_hec_urls(hec_url, runtime_config())
    events_to_stream = load_python_scenario_events(scenario_file)

    ctx = ssl.create_default_context()
    if runtime_config().get("ssl_verify", True) is False:
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

        if run_id:
            from native_run_monitor import attach, update
            batch = [json.dumps(attach(json.loads(e), run_id)) for e in batch]
            indexes = sorted({json.loads(e)["index"] for e in batch})
            kinds = {"METRIC" if json.loads(e)["event"] == "metric" else "LOG" for e in batch}
            def record_scope(r):
                r["indexes"] = sorted(set(r["indexes"]) | set(indexes))
                r["counters"]["generated"] = (r["counters"]["generated"] or 0) + len(batch)
                new = next(iter(kinds)) if len(kinds) == 1 else "MIXED"
                r["classification"] = new if r["classification"] in ("UNKNOWN", new) else "MIXED"
            update(run_id, record_scope)
        payload = "\n".join(batch).encode("utf-8")
        req = hec_request(
            hec_url,
            configuration=runtime_config(),
            data=payload,
            headers={
                "Authorization": f"Splunk {hec_token}",
                "Content-Type": "application/json"
            }
        )
        if run_id:
            def attempted(r):
                r["counters"]["attempted"] = (r["counters"]["attempted"] or 0) + len(batch)
            update(run_id, attempted)
        outcome = "unknown"
        try:
            with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
                if run_id:
                    try:
                        acknowledgement = json.loads(resp.read())
                        if (200 <= resp.status < 300 and isinstance(acknowledgement, dict)
                                and type(acknowledgement.get("code")) is int and acknowledgement["code"] == 0):
                            outcome = "accepted"
                    except (ValueError, UnicodeError):
                        pass
                print(f"[BLASTER] Streamed batch of {batch_size} events to {hec_url} (HTTP {resp.status})")
                sys.stdout.flush()
        except Exception as e:
            if isinstance(e, urllib.error.HTTPError) and 400 <= e.code < 500:
                outcome = "failed"
            sys.stderr.write(f"[BLASTER-PY-WARN] HEC Send Error: Operation failed\n")
            sys.stderr.flush()

        if run_id:
            def record_delivery(r):
                for key in ("accepted", "failed", "unknown"):
                    r["counters"][key] = (r["counters"][key] or 0) + (len(batch) if key == outcome else 0)
            update(run_id, record_delivery)
        time.sleep(sleep_time)


def validate_syslog_scenario(scenario_file):
    events = load_python_scenario_events(scenario_file, strict=True)
    for event in events:
        if ("metric" in event["index"].lower() or "metric" in event["sourcetype"].lower()
                or event["sourcetype"] == "cisco:ios:mdt"):
            raise ValueError("Syslog supports log scenarios only")
        if any(c in event["raw"] or c in event["host"] for c in ("\r", "\n")):
            raise ValueError("Syslog requires single-line log records")
    return events


def send_native_syslog(dispatcher, config, raw, hostname="netspout-native"):
    """Use the existing adapter; a socket send is never receiver/index proof."""
    ok, _ = dispatcher.emit_syslog(raw_message=raw, host=config["syslog_host"],
        port=config["syslog_port"], protocol=config["syslog_protocol"],
        facility=config["syslog_facility"], severity=config["syslog_severity"],
        hostname=hostname, app_name="netspout", syslog_format=config["syslog_format"])
    return {"status": "success" if ok else "error", "delivery_state": "SENT" if ok else "UNKNOWN",
            "message": "Local socket send completed; receiver delivery and indexing unverified" if ok else
                       "Syslog send failed; delivery outcome unknown",
            "attempted": 1, "sent": int(ok), "failed": 0, "unknown": int(not ok),
            "receiver_observed": None, "indexed": None, "indexing_verified": False}


def native_syslog_diagnostic(config):
    from netspout_core.telemetry_dispatcher import TelemetryDispatcher
    return send_native_syslog(TelemetryDispatcher(), config, "NETSPOUT synthetic syslog diagnostic")


def run_python_syslog_streamer(scenario_file, config, eps, run_id=None):
    import random
    from netspout_core.telemetry_dispatcher import TelemetryDispatcher
    config = validate_syslog_settings(config)
    events = validate_syslog_scenario(scenario_file)
    dispatcher = TelemetryDispatcher()
    print("[SYSLOG] Python log scenario started; receiver delivery and indexing are unverified", flush=True)
    while True:
        event = random.choice(events)
        raw = event["raw"].replace("$SYSLOG_TS$", time.strftime("%b %d %H:%M:%S", time.localtime())).replace(
            "$ISO_TS$", time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())).replace("$FLOW_ID$", str(random.randint(10000, 99999)))
        if run_id:
            from native_run_monitor import update
            def generated(r):
                r["classification"] = "LOG"
                r["counters"]["generated"] = (r["counters"]["generated"] or 0) + 1
                r["correlation"] = "UNSUPPORTED"  # Never change vendor wire data for run proof.
            update(run_id, generated)
        # Record intent before the socket call; process interruption leaves an
        # unknown local-send outcome rather than an invented completed send.
        if run_id:
            def attempting(r):
                evidence = {key: ((r.get("syslog_delivery") or {}).get(key) or 0)
                            for key in ("attempted", "sent", "failed", "unknown")}
                evidence["attempted"] += 1
                evidence["unknown"] += 1
                r["syslog_delivery"] = evidence
                r["counters"]["attempted"] = evidence["attempted"]
            update(run_id, attempting)
        result = send_native_syslog(dispatcher, config, raw, event["host"])
        if run_id:
            def delivered(r):
                if result["sent"]:
                    r["syslog_delivery"]["sent"] += 1
                    r["syslog_delivery"]["unknown"] -= 1
            update(run_id, delivered)
        time.sleep(1.0 / eps)


def otlp_is_metric(event):
    return ("metric" in event["index"].lower() or "metric" in event["sourcetype"].lower()
            or event["sourcetype"] == "cisco:ios:mdt")


def validate_otlp_scenario(path, config):
    events = load_python_scenario_events(path, strict=True)
    for event in events:
        signal = "metrics" if otlp_is_metric(event) else "logs"
        if config["otlp_signal"] not in (signal, "both"):
            raise ValueError("Scenario signal is not enabled")
    return events


def build_native_otlp(event, raw, run_id, scenario_id, now=None):
    """Preserve vendor log bodies; metric templates use native synthetic gauges."""
    import random
    now = time.time() if now is None else now
    attributes = [{"key": key, "value": {"stringValue": str(value)}} for key, value in (
        ("host.name", event["host"]), ("service.name", "netspout-native"),
        ("netspout_run_id", run_id or "diagnostic"), ("netspout_scenario_id", scenario_id),
        ("netspout_device_id", event["host"]), ("netspout_phase", "BASELINE"),
        ("sourcetype", event["sourcetype"]), ("source", event["source"]))]
    resource = {"attributes": attributes}
    stamp = str(int(now * 1e9))
    if not otlp_is_metric(event):
        return {"resourceLogs":[{"resource":resource, "scopeLogs":[{
            "scope":{"name":"netspout.native", "version":"2.0.0"},
            "logRecords":[{"timeUnixNano":stamp, "body":{"stringValue":raw}, "attributes":attributes}]}]}]}, False, 1
    # Same generated gauges as the existing native HEC Python streamer; raw
    # metric templates are not interpreted as measured device values.
    values = {"cpu.utilization":round(random.uniform(15,85),2),
              "memory.utilization":round(random.uniform(30,75),2),
              "interface.octets.in":float(random.randint(1000000,50000000)),
              "interface.octets.out":float(random.randint(1000000,50000000)),
              "interface.errors.in":0.0}
    metrics = [{"name":name,"gauge":{"dataPoints":[{"asDouble":value,
                "timeUnixNano":stamp,"attributes":attributes}]}} for name,value in values.items()]
    return {"resourceMetrics":[{"resource":resource,"scopeMetrics":[{
        "scope":{"name":"netspout.native", "version":"2.0.0"},"metrics":metrics}]}]}, True, len(metrics)


def send_native_otlp(dispatcher, config, payload, is_metric, count):
    result = dispatcher.emit_otel_result(payload, config["otlp_endpoint"], is_metric,
                                        config.get("headers", {}), record_count=count)
    return dict(result, status="success" if result["acknowledged"] == count else "error",
                indexed=None, indexing_verified=False,
                counter_unit="metric_data_points" if is_metric else "log_records")


def native_otlp_diagnostic(config):
    from netspout_core.telemetry_dispatcher import TelemetryDispatcher
    metric = config["otlp_signal"] == "metrics"
    event = dict(host="netspout-diagnostic",source="netspout",sourcetype="netspout:metric" if metric else "netspout:log",index="metrics" if metric else "logs")
    payload, is_metric, count = build_native_otlp(event, "NETSPOUT synthetic OTLP diagnostic", None, "diagnostic")
    return send_native_otlp(TelemetryDispatcher(),config,payload,is_metric,count)


def run_python_otlp_streamer(path, config, eps, run_id=None):
    import random
    from netspout_core.telemetry_dispatcher import TelemetryDispatcher
    events = validate_otlp_scenario(path, config)
    dispatcher = TelemetryDispatcher()
    print("[OTLP] Python scenario started; collector acknowledgement is not indexing proof", flush=True)
    while True:
        event = random.choice(events)
        raw = event["raw"].replace("$SYSLOG_TS$",time.strftime("%b %d %H:%M:%S",time.localtime())).replace(
            "$ISO_TS$",time.strftime("%Y-%m-%dT%H:%M:%S.000Z",time.gmtime())).replace("$FLOW_ID$",str(random.randint(10000,99999)))
        payload, metric, count = build_native_otlp(event,raw,run_id,os.path.basename(path))
        if run_id:
            from native_run_monitor import update
            def attempting(r):
                delivery = {k:((r.get("otlp_delivery") or {}).get(k) or 0) for k in ("attempted","acknowledged","rejected","failed","unknown")}
                delivery["attempted"] += count
                delivery["unknown"] += count
                r["otlp_delivery"] = delivery
                r["classification"] = "MIXED" if config["otlp_signal"] == "both" else "METRIC" if metric else "LOG"
                r["counters"]["generated"] = (r["counters"]["generated"] or 0) + count
                r["counters"]["attempted"] = delivery["attempted"]
            update(run_id,attempting)
        result = send_native_otlp(dispatcher,config,payload,metric,count)
        if run_id:
            def delivered(r):
                r["otlp_delivery"]["unknown"] -= count
                for k in ("acknowledged","rejected","failed","unknown"):
                    r["otlp_delivery"][k] += result[k]
                r["counters"]["accepted"] = r["otlp_delivery"]["acknowledged"]
                r["counters"]["failed"] = r["otlp_delivery"]["rejected"] + r["otlp_delivery"]["failed"]
                r["counters"]["unknown"] = r["otlp_delivery"]["unknown"]
            update(run_id,delivered)
        time.sleep(1.0 / eps)


# Explicitly synthetic OIDs, using the repository's existing 59999 namespace.
# No claim of a registered vendor MIB or vendor notification fidelity.
NATIVE_SNMP_OID = "1.3.6.1.4.1.59999.101"


def build_native_snmp(event, raw, config, run_id, scenario_id, phase="BASELINE", request_id=1):
    from netspout_core.models import SnmpTrap, SnmpInform, SnmpVarBind
    cls = SnmpInform if config["snmp_message_type"] == "inform" else SnmpTrap
    values = (run_id or "diagnostic", scenario_id, event["host"], phase, raw, event["sourcetype"], event["source"])
    return cls(community=config["community"], request_id=request_id, sys_uptime=0,
               trap_oid=NATIVE_SNMP_OID + ".0", source_device_id=event["host"],
               scenario_id=scenario_id, phase=phase,
               varbinds=[SnmpVarBind(oid=NATIVE_SNMP_OID + "." + str(i) + ".0",
                         asn1_type="OctetString", value=value, fidelity="SYNTHETIC")
                         for i,value in enumerate(values,1)])


def validate_snmp_scenario(path, config, run_id=None):
    from netspout_core.snmp_ber import SnmpBerEncoder
    events = load_python_scenario_events(path,strict=True)
    for event in events:
        if otlp_is_metric(event):
            raise ValueError("SNMP metric mapping is unsupported")
        # Bound before startup using the largest timestamp/flow substitutions.
        raw = event["raw"].replace("$SYSLOG_TS$","Sep 30 23:59:59").replace("$ISO_TS$","2026-12-31T23:59:59.000Z").replace("$FLOW_ID$","99999")
        SnmpBerEncoder.encode_message(build_native_snmp(event,raw,config,run_id or "0"*36,os.path.basename(path),request_id=2147483647))
    return events


def native_snmp_transport(config):
    from netspout_core.transport_native_snmp import NativeSnmpTransport
    # Never fall back to netspout-lab; no implicit retries, even for informs.
    if not isinstance(config.get("community"),str) or not config["community"]:
        raise ValueError("SNMP community unavailable")
    return NativeSnmpTransport(destination_host=config["snmp_host"],destination_port=config["snmp_port"],
        community=config["community"],trap_rate_pps=50,inform_rate_pps=25,packet_cap=1000,
        inform_timeout_ms=500,inform_max_retries=0)


def send_native_snmp(transport, message, config):
    from netspout_core.snmp_ber import SnmpBerEncoder
    result = dict(status="error",attempted=1,sent=0,failed=0,unknown=1,
                  acknowledged=0 if config["snmp_message_type"] == "inform" else None,
                  message="SNMP delivery outcome unknown",indexed=None,indexing_verified=False,
                  receiver_observed=None)
    try:
        size = len(SnmpBerEncoder.encode_message(message))
    except Exception:
        result.update(failed=1,unknown=0,message="SNMP message could not be encoded")
        return result
    try:
        outcome = transport.send_batch([message])
        sent = outcome.datagrams_sent == 1 and outcome.bytes_sent == size
        result["sent"] = int(sent)
        if outcome.datagrams_attempted == 0:
            result.update(failed=1,unknown=0,message="SNMP message was not sent")
        elif config["snmp_message_type"] == "inform":
            acknowledged = sent and outcome.informs_acknowledged == 1
            result.update(acknowledged=int(acknowledged),unknown=0 if acknowledged else 1,
                          status="success" if acknowledged else "error",
                          message="SNMP inform response matched; indexing unverified" if acknowledged else "SNMP inform acknowledgement unconfirmed")
        elif sent:
            result.update(status="success",unknown=0,message="SNMP datagram locally sent; receiver delivery unverified")
    except Exception:
        pass  # Adapter errors can contain credentials/bytes; never expose them.
    return result


def native_snmp_diagnostic(config):
    event = dict(host="netspout-diagnostic",source="pulseforge",sourcetype="netspout:synthetic:snmp")
    message = build_native_snmp(event,"PulseForge synthetic SNMP diagnostic",config,None,"diagnostic")
    return send_native_snmp(native_snmp_transport(config),message,config)


def run_python_snmp_streamer(path, config, eps, run_id=None):
    import random
    events = validate_snmp_scenario(path,config,run_id)
    transport = native_snmp_transport(config)
    print("[PulseForge SNMP] Synthetic notifications; indexing verification unsupported",flush=True)
    for sequence in range(1,1001):
        event = random.choice(events)
        raw = event["raw"].replace("$SYSLOG_TS$",time.strftime("%b %d %H:%M:%S",time.localtime())).replace(
            "$ISO_TS$",time.strftime("%Y-%m-%dT%H:%M:%S.000Z",time.gmtime())).replace("$FLOW_ID$",str(random.randint(10000,99999)))
        message = build_native_snmp(event,raw,config,run_id,os.path.basename(path),request_id=sequence)
        if run_id:
            from native_run_monitor import update
            def attempting(r):
                delivery = {k:((r.get("snmp_delivery") or {}).get(k) or 0) for k in ("attempted","sent","failed","unknown")}
                delivery.update(attempted=delivery["attempted"]+1,unknown=delivery["unknown"]+1,
                                acknowledged=((r.get("snmp_delivery") or {}).get("acknowledged") or 0) if config["snmp_message_type"] == "inform" else None)
                r["snmp_delivery"] = delivery
                r["counters"]["generated"] = (r["counters"]["generated"] or 0)+1
                r["counters"]["attempted"] = delivery["attempted"]
            update(run_id,attempting)
        evidence = send_native_snmp(transport,message,config)
        if run_id:
            def delivered(r):
                r["snmp_delivery"]["unknown"] -= 1
                for key in ("sent","failed","unknown"):
                    r["snmp_delivery"][key] += evidence[key]
                if evidence["acknowledged"] is not None:
                    r["snmp_delivery"]["acknowledged"] += evidence["acknowledged"]
                r["counters"]["accepted"] = r["snmp_delivery"]["acknowledged"]
                r["counters"]["failed"] = r["snmp_delivery"]["failed"]
                r["counters"]["unknown"] = r["snmp_delivery"]["unknown"]
            update(run_id,delivered)
        time.sleep(1.0/eps)


def validate_forwarding_scenario(path, config):
    import pulseforge_forwarding as forwarding
    events = load_python_scenario_events(path,strict=True)
    for event in events:
        if otlp_is_metric(event):
            raise ValueError("Forwarding metrics are unsupported")
        record = forwarding.event_record(event,event["raw"],"00000000-0000-0000-0000-000000000000",os.path.basename(path),config["forwarding_index"],time.time())
        if len(json.dumps(record).encode()) > forwarding.MAX_EVENT_BYTES:
            raise ValueError("Forwarding event is oversized")
    return events


def run_python_forwarding_streamer(path, config, eps, run_id):
    import random
    import pulseforge_forwarding as forwarding
    from native_run_monitor import update
    events = validate_forwarding_scenario(path,config)
    for _ in range(1000):
        event = random.choice(events)
        raw = event["raw"].replace("$SYSLOG_TS$",time.strftime("%b %d %H:%M:%S",time.localtime())).replace(
            "$ISO_TS$",time.strftime("%Y-%m-%dT%H:%M:%S.000Z",time.gmtime())).replace("$FLOW_ID$",str(random.randint(10000,99999)))
        record = forwarding.event_record(event,raw,run_id,os.path.basename(path),config["forwarding_index"],time.time())
        def attempting(r):
            r["counters"]["generated"] = (r["counters"]["generated"] or 0)+1
            r["counters"]["attempted"] = (r["counters"]["attempted"] or 0)+1
            values = {k:((r.get("forwarding_delivery") or {}).get(k) or 0) for k in ("published","failed","unknown")}
            values["unknown"] += 1
            r["forwarding_delivery"] = values
        update(run_id,attempting)
        try:
            forwarding.publish(record)
        except Exception:
            # A filesystem failure can occur after replacement; don't infer loss.
            print("[PulseForge] Spool publication unconfirmed; run stopped",flush=True)
            return
        def published(r):
            r["forwarding_delivery"]["published"] += 1
            r["forwarding_delivery"]["unknown"] -= 1
        update(run_id,published)
        time.sleep(1.0/eps)


def _main():
    global _RUNTIME_CONFIG
    parser = argparse.ArgumentParser(description="NetSpout PulseForge Secure Simulation Runner")
    parser.add_argument("--scenario", required=False, help="Path to scenario YAML file")
    parser.add_argument("--eps", type=int, default=int(os.environ.get("DATABLASTER_TARGET_EPS", 1000)), help="Target Events Per Second (integer)")
    parser.add_argument("--hec", default=os.environ.get("SPLUNK_HEC_URL", "https://127.0.0.1:8088/services/collector"), help="Target Splunk HEC URL")
    parser.add_argument("--ssl-verify", default="true", choices=["true", "false"])
    parser.add_argument("--sample", required=False, default=None, help="Optional sample filter")
    parser.add_argument("--async-exec", action="store_true", help="Launch asynchronously and return PID immediately")
    parser.add_argument("--python-stream", action="store_true", help="Run using native Python streaming engine")

    syslog_mode = parser.add_mutually_exclusive_group()
    syslog_mode.add_argument("--native-syslog", action="store_true")
    syslog_mode.add_argument("--syslog-diagnostic", action="store_true")
    syslog_mode.add_argument("--syslog-preflight", action="store_true")
    syslog_mode.add_argument("--native-otlp", action="store_true")
    syslog_mode.add_argument("--otlp-diagnostic", action="store_true")
    syslog_mode.add_argument("--otlp-preflight", action="store_true")
    syslog_mode.add_argument("--native-snmp",action="store_true")
    syslog_mode.add_argument("--snmp-preflight",action="store_true")
    syslog_mode.add_argument("--snmp-diagnostic",action="store_true")
    syslog_mode.add_argument("--native-forwarding",action="store_true")
    syslog_mode.add_argument("--forwarding-preflight",action="store_true")
    syslog_mode.add_argument("--named-hec-diagnostic",action="store_true")
    args = parser.parse_args()

    def stop_runner(signum, frame):
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGTERM, stop_runner)
    signal.signal(signal.SIGINT, stop_runner)
    if not (args.syslog_diagnostic or args.otlp_diagnostic or args.snmp_diagnostic or args.named_hec_diagnostic):
        args.scenario = resolve_scenario_path(args.scenario or "", APP_DIR)
    private_input = json.loads(sys.stdin.read())
    _RUNTIME_CONFIG = private_input.get("runtime_config")
    if _RUNTIME_CONFIG is not None and not isinstance(_RUNTIME_CONFIG,dict):
        raise ValueError("Invalid runtime snapshot")
    args.token = private_input.get("credential", "")
    args.run_id = private_input.get("run_id")
    if args.run_id:
        import uuid
        if str(uuid.UUID(args.run_id)) != args.run_id:
            raise ValueError("Invalid native run identity")
    if args.scenario:
        import network_incidents
        incident = network_incidents.descriptor(args.scenario)
        if incident is not None:
            network_incidents.execute(sys.modules[__name__], args, private_input, incident)
            return
    if args.named_hec_diagnostic:
        from netspout_core.telemetry_dispatcher import TelemetryDispatcher, hec_outcome_fields
        config=runtime_config()
        endpoint=resolve_hec_urls(config['hec_url'],config)[0]
        outcome=TelemetryDispatcher().emit_hec({'event':'PulseForge synthetic destination diagnostic',
            'sourcetype':'netspout:diagnostic','index':config['idx_network_ops']},endpoint,args.token,
            ssl_verify=config['ssl_verify'],allow_insecure_tls=not config['ssl_verify'])
        fields=hec_outcome_fields(outcome)
        print(json.dumps(dict(fields,status='success' if fields['state']=='ACCEPTED' else 'error',message=outcome[1],indexed=None,indexing_verified=False)))
        return
    if args.native_forwarding or args.forwarding_preflight:
        import pulseforge_forwarding as forwarding
        config = forwarding.validate(private_input.get("forwarding",{}))
        events = validate_forwarding_scenario(args.scenario,config)
        if args.forwarding_preflight:
            print(json.dumps({"status":"success","templates":len(events)}))
            return
        if not args.run_id or not 1 <= args.eps <= 100:
            raise ValueError("Invalid forwarding run scope")
        run_python_forwarding_streamer(args.scenario,config,args.eps,args.run_id)
        return
    if args.snmp_diagnostic or args.snmp_preflight or args.native_snmp:
        from datablaster_rest import validate_snmp_settings
        supplied = private_input.get("snmp", {})
        config = dict(validate_snmp_settings(supplied),community=supplied.get("community"))
        native_snmp_transport(config)  # Require explicit runtime credentials.
        if args.snmp_diagnostic:
            print(json.dumps(native_snmp_diagnostic(config)))
            return
        events = validate_snmp_scenario(args.scenario,config,args.run_id)
        if args.snmp_preflight:
            print(json.dumps({"status":"success","templates":len(events)}))
            return
        if not 1 <= args.eps <= (25 if config["snmp_message_type"] == "inform" else 50):
            raise ValueError("Unsupported SNMP rate")
        run_python_snmp_streamer(args.scenario,config,args.eps,args.run_id)
        return
    if args.otlp_diagnostic or args.otlp_preflight or args.native_otlp:
        from datablaster_rest import validate_otlp_settings
        supplied = private_input.get("otlp", {})
        config = dict(validate_otlp_settings(supplied), headers=supplied.get("headers", {}))
        if args.otlp_diagnostic:
            print(json.dumps(native_otlp_diagnostic(config)))
            return
        events = validate_otlp_scenario(args.scenario, config)
        if args.otlp_preflight:
            print(json.dumps({"status":"success", "templates":len(events)}))
            return
        if not 1 <= args.eps <= 500000:
            raise ValueError("Invalid OTLP EPS")
        run_python_otlp_streamer(args.scenario,config,args.eps,args.run_id)
        return
    if args.syslog_diagnostic or args.syslog_preflight or args.native_syslog:
        config = validate_syslog_settings(private_input.get("syslog", {}))
        if args.syslog_diagnostic:
            print(json.dumps(native_syslog_diagnostic(config)))
            return
        args.scenario = resolve_scenario_path(args.scenario or "", APP_DIR)
        events = validate_syslog_scenario(args.scenario)
        if args.syslog_preflight:
            print(json.dumps({"status": "success", "log_templates": len(events)}))
            return
        if not 1 <= args.eps <= 500000:
            raise ValueError("Invalid syslog EPS")
        run_python_syslog_streamer(args.scenario, config, args.eps, args.run_id)
        return
    args.scenario = resolve_scenario_path(args.scenario, APP_DIR)
    if (os.path.basename(args.scenario).startswith("canvas_custom_")
            and os.path.dirname(args.scenario) == os.path.realpath(resolve_run_dir())):
        _PRIVATE_FILES.add(args.scenario)
    resolve_hec_urls(args.hec, runtime_config())
    if not args.token:
        raise ValueError("HEC credential is required")

    if args.python_stream:
        try:
            run_python_streamer(args.scenario, args.hec, args.token, args.eps, args.run_id)
        except NoStreamableEventsError as e:
            sys.stderr.write(f"{str(e)}\n")
            sys.exit(2)
        finally:
            if os.path.basename(args.scenario).startswith("canvas_custom_") and os.path.dirname(args.scenario) == resolve_run_dir():
                with contextlib.suppress(FileNotFoundError):
                    os.unlink(args.scenario)
        sys.exit(0)

    # 1. Input sanitization
    if args.eps <= 0 or args.eps > 500000:
        sys.stderr.write(f"[ERROR] Invalid EPS value: {args.eps}. Must be between 1 and 500,000.\n")
        sys.exit(1)

    scenario_file = args.scenario

    if args.async_exec:
        pid = validate_and_stream_mv_scenario(scenario_file, args.hec, args.token, args.eps, args.run_id)
        print(f"[PulseForge] Launched process asynchronously with PID: {pid}")
        sys.exit(0)

    # 2. Multi-Platform Binary Selection
    try:
        binary_path = resolve_binary()
    except Exception as e:
        sys.stderr.write(f"[ERROR] Operation failed\n")
        sys.exit(1)

    print(f"[PulseForge] Host OS: {sys.platform}")
    print(f"[PulseForge] Using Execution Engine: {binary_path}")
    print(f"[PulseForge] Scenario: {scenario_file}")
    print(f"[PulseForge] Target EPS: {args.eps}")
    print(f"[PulseForge] HEC Endpoint: {args.hec} (Token: {mask_secret(args.token)})")

    # Native engines do not expose a verified TLS configuration contract.
    # Use the Python engine while certificate verification is enabled.
    if binary_path == "python_engine" or runtime_config().get("ssl_verify", True) is not False:
        try:
            run_python_streamer(scenario_file, args.hec, args.token, args.eps, args.run_id)
        except NoStreamableEventsError as e:
            sys.stderr.write(f"{str(e)}\n")
            sys.exit(2)
        finally:
            if os.path.basename(scenario_file).startswith("canvas_custom_") and os.path.dirname(scenario_file) == resolve_run_dir():
                with contextlib.suppress(FileNotFoundError):
                    os.unlink(scenario_file)
        sys.exit(0)

    if args.run_id:
        from native_run_monitor import update
        update(args.run_id, lambda r: r.update(correlation="UNSUPPORTED"))

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

    print(f"[PulseForge] Spawning process (shell=False): {' '.join(cmd[:3])}...")
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
        print(f"[PulseForge] Simulation finished with return code {proc.returncode}")
        sys.exit(proc.returncode)

    except Exception as e:
        sys.stderr.write(f"[ERROR] Process execution failed: Operation failed\n")
        sys.exit(1)
    finally:
        if os.path.basename(scenario_file).startswith("canvas_custom_") and os.path.dirname(scenario_file) == resolve_run_dir():
            with contextlib.suppress(FileNotFoundError):
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
