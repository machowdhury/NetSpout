#!/usr/bin/env python3
"""Idle-telemetry check against a disposable Splunk lab (Phase 16, defect B1): does an installed, idle NetSpout write any synthetic event?

  python scripts/phase16_idle_check.py --env LABENV --container NAME measure OUT.json [--label TEXT]
  python scripts/phase16_idle_check.py --env LABENV --container NAME canary          (writes 5 events to the control index; proves the measurement can see events)
  python scripts/phase16_idle_check.py --env LABENV --container NAME observe OUT.json MINUTES [--label TEXT]   (measure, wait, measure again, compare)
  python scripts/phase16_idle_check.py --env LABENV --container NAME legacy on|off|status   (writes / removes local/inputs.conf that enables the legacy streamer; restart Splunk afterwards)

LABENV is a lab env file with LAB_MGMT_PORT, LAB_HEC_PORT, LAB_HEC_TOKEN and LAB_SPLUNK_PASSWORD (never printed). The container must be a disposable lab (name starts with nsp).

Attribution: an event is NetSpout-generated when its source starts with "netspout:" or "pulseforge", or it has a netspout_run_id field, in ANY index (search over index=* from the beginning of time), plus the totals of the app-defined indexes and metric datapoints. The control index ns16_idle_control receives 5 canary events (source "idle_check:canary") so a zero is known to be a real zero and not a broken search; canary events are excluded from the attribution count. Splunk's own internal indexes are not touched by the attribution because they never carry those sources.
"""
import json
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CTX = __import__("ssl")._create_unverified_context()
APP_INDEXES = ("idx_network_ops", "idx_security_fw", "idx_wireless_ops")
METRIC_INDEX = "cisco_mdt_metrics"
CONTROL = "ns16_idle_control"
LEGACY = "[netspout_streamer://default]\ndisabled = 0\ninterval = 5\n"


def parse(argv):
    a, env, cont = list(argv), None, None
    for flag in ("--env", "--container", "--label"):
        if flag in a:
            i = a.index(flag)
            val = a[i + 1]
            del a[i:i + 2]
            if flag == "--env":
                env = val
            elif flag == "--container":
                cont = val
            else:
                parse.label = val
    return a, env, cont


parse.label = ""
ARGS, ENV, CONTAINER = parse(sys.argv[1:])
if not ENV or not CONTAINER or not CONTAINER.startswith("nsp"):
    raise SystemExit(__doc__)
E = dict(l.strip().split("=", 1) for l in Path(ENV).read_text().splitlines() if "=" in l)
MGMT = "https://127.0.0.1:%s" % E["LAB_MGMT_PORT"]
AUTH = "Basic " + __import__("base64").b64encode(("admin:" + E["LAB_SPLUNK_PASSWORD"]).encode()).decode()


def rest(path, data=None):
    r = urllib.request.Request(MGMT + path, data=urllib.parse.urlencode(data).encode() if data is not None else None, headers={"Authorization": AUTH})
    return json.loads(urllib.request.urlopen(r, context=CTX, timeout=180).read() or b"{}")


def search(spl):
    q = urllib.parse.urlencode({"search": spl if spl.startswith(("search", "|")) else "search " + spl, "output_mode": "json", "earliest_time": "0"}).encode()
    req = urllib.request.Request(MGMT + "/services/search/jobs/export", data=q, headers={"Authorization": AUTH})
    rows = []
    for line in urllib.request.urlopen(req, context=CTX, timeout=300).read().decode().splitlines():
        if line.strip():
            o = json.loads(line)
            if "result" in o:
                rows.append(o["result"])
    return rows


def n(spl):
    r = search(spl)
    return int(r[0].get("count", 0)) if r else 0


def dexec(*cmd, user="root"):
    return subprocess.run(["docker", "exec", "-u", user, CONTAINER, *cmd], capture_output=True, text=True)


def measure(label=""):
    try:
        indexes = {x["name"] for x in rest("/services/data/indexes?output_mode=json&count=0&datatype=all")["entry"]}
    except Exception as e:
        raise SystemExit("cannot read the lab Splunk: %s" % type(e).__name__)
    attributed = n('index=* (source="netspout:*" OR source="pulseforge*" OR netspout_run_id=*) NOT source="idle_check:canary" | stats count')
    by_sourcetype = search('index=* (source="netspout:*" OR source="pulseforge*" OR netspout_run_id=*) NOT source="idle_check:canary" | stats count by index, source, sourcetype | head 20')
    per_index = {i: n("index=%s | stats count" % i) for i in APP_INDEXES if i in indexes}
    metric = int((search("| mstats count(_value) as count WHERE index=%s" % METRIC_INDEX) or [{"count": 0}])[0].get("count") or 0) if METRIC_INDEX in indexes else None
    ps = dexec("sh", "-c", "ps -eo pid,args | grep -E 'netspout_streamer|pulseforge_spool' | grep -v grep").stdout.strip()
    log = dexec("sh", "-c", "grep -hE 'New scheduled exec process.*(netspout_streamer|pulseforge_spool)' /opt/splunk/var/log/splunk/splunkd.log | wc -l").stdout.strip()
    ver = ""
    try:
        ver = rest("/services/apps/local/netspout?output_mode=json")["entry"][0]["content"].get("version", "")
    except Exception:
        ver = "(not installed)"
    return {"label": label or parse.label, "time_utc": time.strftime("%FT%TZ", time.gmtime()), "app_version": ver, "app_indexes_defined": sorted(i for i in indexes if i in APP_INDEXES + (METRIC_INDEX,)),
            "netspout_attributed_events": attributed, "attributed_by_index_source_sourcetype": by_sourcetype, "events_in_app_indexes": per_index, "metric_datapoints_in_metric_index": metric,
            "control_index_events": n("index=%s | stats count" % CONTROL) if CONTROL in indexes else None,
            "generator_processes_running": ps.splitlines(), "splunkd_log_generator_launches": int(log or 0)}


def canary():
    try:
        rest("/services/data/indexes?output_mode=json", {"name": CONTROL, "datatype": "event"})
    except urllib.error.HTTPError:
        pass
    now = int(time.time())
    body = "".join(json.dumps({"time": now - i, "host": "idle-check", "source": "idle_check:canary", "sourcetype": "idle_check", "index": CONTROL, "event": "canary %d" % i}) for i in range(5)).encode()
    for attempt in range(18):
        try:
            urllib.request.urlopen(urllib.request.Request("https://127.0.0.1:%s/services/collector" % E["LAB_HEC_PORT"], data=body, headers={"Authorization": "Splunk " + E["LAB_HEC_TOKEN"]}), context=CTX, timeout=60).read()
            break
        except urllib.error.URLError:
            time.sleep(10)
    for _ in range(36):
        if n("index=%s | stats count" % CONTROL) >= 5:
            print("canary visible: 5 events in %s" % CONTROL)
            return
        time.sleep(5)
    raise SystemExit("canary events never became searchable; the measurement cannot be trusted")


def main():
    cmd = ARGS[:1]
    if cmd == ["measure"]:
        m = measure()
        Path(ARGS[1]).write_text(json.dumps(m, indent=1) + "\n")
        print(json.dumps({k: m[k] for k in ("label", "app_version", "netspout_attributed_events", "events_in_app_indexes", "metric_datapoints_in_metric_index", "control_index_events", "generator_processes_running", "splunkd_log_generator_launches")}, indent=1))
    elif cmd == ["canary"]:
        canary()
    elif cmd == ["observe"]:
        a = measure("start")
        time.sleep(float(ARGS[2]) * 60)
        b = measure("end")
        res = {"label": parse.label, "window_minutes": float(ARGS[2]), "start": a, "end": b,
               "new_netspout_events_in_window": b["netspout_attributed_events"] - a["netspout_attributed_events"],
               "new_events_in_app_indexes": {i: b["events_in_app_indexes"].get(i, 0) - a["events_in_app_indexes"].get(i, 0) for i in b["events_in_app_indexes"]}}
        Path(ARGS[1]).write_text(json.dumps(res, indent=1) + "\n")
        print(json.dumps({k: v for k, v in res.items() if k not in ("start", "end")}, indent=1))
        sys.exit(0 if res["new_netspout_events_in_window"] == 0 and b["netspout_attributed_events"] == 0 else 1)
    elif cmd == ["legacy"]:
        f = "/opt/splunk/etc/apps/netspout/local/inputs.conf"
        if ARGS[1] == "on":
            r = dexec("sh", "-c", "mkdir -p /opt/splunk/etc/apps/netspout/local && printf '%s' '" + LEGACY + "' > " + f + " && chown splunk:splunk " + f)
            print("legacy streamer enabled in local/inputs.conf" if r.returncode == 0 else r.stderr)
        elif ARGS[1] == "off":
            dexec("rm", "-f", f)
            print("local/inputs.conf removed")
        else:
            print(dexec("sh", "-c", "cat %s 2>&1 || echo '(no local/inputs.conf)'" % f).stdout)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main()
