#!/usr/bin/env python3
"""Phase 15 upgrade / persistence / rollback evidence for ONE Phase 15 Docker lab (NS_LAB=nsp15|nsp15u|nsp15r).

  NS_LAB=nsp15u python scripts/phase15_upgrade_check.py seed            create indexes, a saved search, a dashboard and a local setting; ingest known events and metric datapoints over HEC
  NS_LAB=nsp15u python scripts/phase15_upgrade_check.py record OUT.json  record counts, index definitions, app version, app local files (sha256), saved objects
  NS_LAB=nsp15u python scripts/phase15_upgrade_check.py compare BEFORE.json AFTER.json   every recorded data/config item must be unchanged (app version may differ); exit 1 otherwise

Known data: 120 events (sourcetype ns15:upgrade, index idx_network_ops), 40 events in the user-created index ns15_keep, 30 metric datapoints in cisco_mdt_metrics (metric ns15.upgrade.value).
Credentials come from the lab's git-ignored env file and are never printed.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

sys.argv, argv = sys.argv[:1], sys.argv[1:]
sys.path.insert(0, os.path.dirname(__file__))
import phase10_rc_install as L   # noqa: E402  (reads NS_LAB)

APP = "/opt/splunk/etc/apps/netspout"
HEC = "https://127.0.0.1:%s/services/collector" % L.e["LAB_HEC_PORT"]
TOKEN = L.e["LAB_HEC_TOKEN"]


def hec(payload):
    r = urllib.request.Request(HEC, data=payload.encode(), headers={"Authorization": "Splunk " + TOKEN})
    for attempt in range(18):   # HEC comes up a little after the management port after a restart
        try:
            return json.loads(urllib.request.urlopen(r, context=L.CTX, timeout=60).read())
        except urllib.error.URLError:
            if attempt == 17:
                raise
            time.sleep(10)


def search(spl, timeout=120):
    q = urllib.parse.urlencode({"search": spl if spl.startswith(("search", "|")) else "search " + spl, "output_mode": "json", "earliest_time": "-30d"}).encode()
    req = urllib.request.Request(L.MGMT + "/services/search/jobs/export", data=q, headers={"Authorization": L.AUTH})
    rows = []
    for line in urllib.request.urlopen(req, context=L.CTX, timeout=timeout).read().decode().splitlines():
        if line.strip():
            o = json.loads(line)
            if "result" in o:
                rows.append(o["result"])
    return rows


def count(spl):
    r = search(spl + " | stats count")
    return int(r[0]["count"]) if r else 0


def seed():
    for name, dt in (("ns15_keep", "event"),):
        try:
            L.rest("/servicesNS/nobody/netspout/data/indexes?output_mode=json", {"name": name, "datatype": dt})
        except Exception as ex:
            print("index", name, ex)
    now = int(time.time())
    ev = "".join(json.dumps({"time": now - i, "host": "ns15-upgrade", "sourcetype": "ns15:upgrade", "index": "idx_network_ops", "event": "ns15 upgrade marker %03d" % i}) for i in range(120))
    ev += "".join(json.dumps({"time": now - i, "host": "ns15-upgrade", "sourcetype": "ns15:keep", "index": "ns15_keep", "event": "ns15 keep marker %03d" % i}) for i in range(40))
    print(hec(ev))
    mt = "".join(json.dumps({"time": now - i, "event": "metric", "source": "ns15", "host": "ns15-upgrade", "index": "cisco_mdt_metrics", "fields": {"metric_name:ns15.upgrade.value": i + 1, "dim": "ns15"}}) for i in range(30))
    print(hec(mt))
    L.rest("/servicesNS/nobody/netspout/saved/searches?output_mode=json", {"name": "ns15_saved_search", "search": "index=idx_network_ops sourcetype=ns15:upgrade | stats count", "description": "phase15 upgrade marker"})
    L.rest("/servicesNS/nobody/netspout/data/ui/views?output_mode=json", {"name": "ns15_custom_view", "eai:data": '<dashboard version="1.1"><label>ns15 custom view</label><row><panel><table><search><query>index=idx_network_ops sourcetype=ns15:upgrade | stats count</query><earliest>-30d</earliest><latest>now</latest></search></table></panel></row></dashboard>'})
    L.rest("/servicesNS/nobody/netspout/configs/conf-ns15_custom?output_mode=json", {"name": "settings"})
    L.rest("/servicesNS/nobody/netspout/configs/conf-ns15_custom/settings?output_mode=json", {"owner_note": "kept across upgrade", "retention_days": "7"})
    for _ in range(36):   # a new index can take a while to show its first events; a baseline recorded early would be wrong
        if (count("index=idx_network_ops sourcetype=ns15:upgrade"), count("index=ns15_keep sourcetype=ns15:keep")) == (120, 40):
            break
        time.sleep(5)
    print("seeded")


def record(out):
    r = __import__("subprocess").run(["docker", "exec", "-u", "root", L.SPLUNK, "sh", "-c", "cd %s/local && find . -type f | sort | xargs sha256sum" % APP], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr   # an unreadable local/ must fail the record, not look like "no files"
    local = r.stdout.strip().splitlines()
    app = L.rest("/services/apps/local/netspout?output_mode=json")["entry"][0]["content"]
    idx = {x["name"]: {"datatype": x["content"].get("datatype"), "totalEventCount": int(x["content"].get("totalEventCount") or 0)} for x in L.rest("/services/data/indexes?output_mode=json&count=0&datatype=all")["entry"] if x["name"] in ("idx_network_ops", "idx_security_fw", "idx_wireless_ops", "cisco_mdt_metrics", "ns15_keep")}
    views = {x["name"] for x in L.rest("/servicesNS/nobody/netspout/data/ui/views?output_mode=json&count=0")["entry"]}
    ss = L.rest("/servicesNS/nobody/netspout/saved/searches/ns15_saved_search?output_mode=json")["entry"][0]["content"]["search"]
    st = L.rest("/servicesNS/nobody/netspout/configs/conf-ns15_custom/settings?output_mode=json")["entry"][0]["content"]
    rec = {"app_version": app.get("version"), "events_ns15_upgrade": count("index=idx_network_ops sourcetype=ns15:upgrade"), "events_ns15_keep": count("index=ns15_keep sourcetype=ns15:keep"),
           "metric_datapoints": int((search("| mstats count(ns15.upgrade.value) as count WHERE index=cisco_mdt_metrics") or [{"count": 0}])[0].get("count") or 0),
           "indexes": idx, "app_local_files_sha256": local, "ns15_custom_view_present": "ns15_custom_view" in views, "saved_search": ss, "custom_conf": {"owner_note": st.get("owner_note"), "retention_days": st.get("retention_days")}, "dashboards_installed": len(views)}
    json.dump(rec, open(out, "w"), indent=1)
    print(json.dumps({k: v for k, v in rec.items() if k != "app_local_files_sha256"}, indent=1))


def compare(a, b):
    A, B = json.load(open(a)), json.load(open(b))
    bad = []
    for k in ("events_ns15_upgrade", "events_ns15_keep", "metric_datapoints", "ns15_custom_view_present", "saved_search", "custom_conf"):
        ok = A[k] == B[k]
        print("PASS" if ok else "FAIL", k, A[k] if ok else (A[k], B[k]))
        if not ok:
            bad.append(k)
    for n, v in A["indexes"].items():
        ok = n in B["indexes"] and B["indexes"][n]["datatype"] == v["datatype"] and B["indexes"][n]["totalEventCount"] >= v["totalEventCount"]
        print("PASS" if ok else "FAIL", "index", n, v, B["indexes"].get(n))
        if not ok:
            bad.append("index " + n)
    gone = sorted(set(A["app_local_files_sha256"]) - set(B["app_local_files_sha256"]))
    print("PASS" if not gone else "FAIL", "app local files unchanged (%d recorded)" % len(A["app_local_files_sha256"]), gone)
    bad += gone
    print("INFO app version %s -> %s; dashboards %s -> %s" % (A["app_version"], B["app_version"], A["dashboards_installed"], B["dashboards_installed"]))
    return 1 if bad else 0


if __name__ == "__main__":
    c = argv[:1]
    if c == ["seed"]:
        seed()
    elif c == ["record"]:
        record(argv[1])
    elif c == ["compare"]:
        sys.exit(compare(argv[1], argv[2]))
    else:
        raise SystemExit(__doc__)
