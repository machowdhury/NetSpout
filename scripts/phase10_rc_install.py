#!/usr/bin/env python3
"""Install and check a release candidate in the RC install lab (tests/lab/rc_install: containers netspout_rc_splunk and netspout_rc_engine ONLY).

  python scripts/phase10_rc_install.py wait                       wait until the fresh Splunk answers on its management port
  python scripts/phase10_rc_install.py install RC_DIR            install RC_DIR/netspout.spl with Splunk's own app endpoint, then restart Splunk and wait
  python scripts/phase10_rc_install.py install-ta PACKAGE       install ONE vendor add-on (any .spl/.tgz/.tar.gz) into the RC Splunk; remove-ta APP removes it; apps lists non-built-in apps
  python scripts/phase10_rc_install.py create-index NAME TYPE  create a test index (event|metric) in the RC lab only (used for the wrong-index failure tests)
  python scripts/phase10_rc_install.py check RC_DIR OUT.json     installed-app and engine checks (versions, packaged files byte-equal to the archive, indexes, gateway, engine reachability)

The engine in the lab was built from RC_DIR/pulseforge-engine.tar.gz. Credentials are read from the git-ignored tests/lab/rc_install/.env.lab and never printed. Refuses any other container.
"""
import base64
import hashlib
import json
import ssl
import subprocess
import sys
import tarfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / "tests/lab/rc_install/.env.lab"
SPLUNK, ENGINE = "netspout_rc_splunk", "netspout_rc_engine"
CTX = ssl._create_unverified_context()
e = dict(l.strip().split("=", 1) for l in ENV.read_text().splitlines() if "=" in l)
MGMT = "https://127.0.0.1:%s" % e["LAB_MGMT_PORT"]
AUTH = "Basic " + base64.b64encode(("admin:" + e["LAB_SPLUNK_PASSWORD"]).encode()).decode()
assert e["LAB_MGMT_PORT"] == "39191" and e["LAB_WEB_PORT"] == "39000", "this script only talks to the RC install lab (mgmt 39191, web 39000)"


def rest(path, data=None, method=None):
    r = urllib.request.Request(MGMT + path, data=urllib.parse.urlencode(data).encode() if data is not None else None, headers={"Authorization": AUTH}, method=method)
    return json.loads(urllib.request.urlopen(r, context=CTX, timeout=180).read() or b"{}")


def wait(timeout=900):
    end = time.time() + timeout
    while time.time() < end:
        try:
            rest("/services/server/info?output_mode=json")
            return True
        except Exception:
            time.sleep(10)
    raise SystemExit("Splunk did not come up")


def dexec(c, *cmd):
    assert c in (SPLUNK, ENGINE)
    return subprocess.run(["docker", "exec", c] + list(cmd), capture_output=True, text=True)


def install(rc):
    wait()
    pkg = Path(rc) / "netspout.spl"
    subprocess.run(["docker", "cp", str(pkg), "%s:/tmp/rc_netspout.spl" % SPLUNK], check=True)
    out = rest("/services/apps/local?output_mode=json", {"name": "/tmp/rc_netspout.spl", "filename": "true", "update": "true"})
    c = out["entry"][0]["content"]
    print(json.dumps({"installed": out["entry"][0]["name"], "version": c.get("version"), "label": c.get("label"), "disabled": c.get("disabled")}))
    # splunkd does not hand the container's environment to REST handler processes; splunk-launch.conf is the supported place, and without it the gateway falls back to the host demo port 8081.
    subprocess.run(["docker", "exec", "-u", "root", SPLUNK, "bash", "-c", "grep -q '^NETSPOUT_BACKEND_URL=' /opt/splunk/etc/splunk-launch.conf || printf '\\nNETSPOUT_BACKEND_URL=http://engine:8081\\n' >> /opt/splunk/etc/splunk-launch.conf"], check=True)
    try:
        rest("/services/server/control/restart?output_mode=json", {}, "POST")
    except Exception:
        pass
    time.sleep(25)
    wait()


def check(rc, out_path):
    rc = Path(rc)
    checks = []

    def add(name, ok, detail=""):
        checks.append({"check": name, "status": "PASS" if ok else "FAIL", "detail": str(detail)[:300]})
        print("%-4s %s  %s" % ("PASS" if ok else "FAIL", name, str(detail)[:160]))
    with tarfile.open(rc / "netspout.spl") as tf:
        members = {m.name: m for m in tf.getmembers() if m.isfile()}
        arc = lambda n: hashlib.sha256(tf.extractfile(members[n]).read()).hexdigest()
        app = rest("/services/apps/local/netspout?output_mode=json")["entry"][0]["content"]
        add("app.installed_and_enabled", not app.get("disabled") and app.get("version") == "2.0.0", "%s %s" % (app.get("label"), app.get("version")))
        conf_ver = [l.split("=")[1].strip() for l in tf.extractfile(members["netspout/default/app.conf"]).read().decode().splitlines() if l.startswith("version")][0]
        manifest = json.loads(tf.extractfile(members["netspout/app.manifest"]).read())
        pkg = json.loads((ROOT / "frontend/package.json").read_text())
        eng = json.loads(urllib.request.urlopen("http://127.0.0.1:38081/openapi.json", timeout=10).read())["info"]["version"]
        versions = {"app.conf": conf_ver, "app.manifest": manifest["info"]["id"]["version"] if "id" in manifest.get("info", {}) else manifest["schemaVersion"], "frontend/package.json": pkg["version"], "engine(openapi)": eng, "installed app": app.get("version")}
        add("versions.match", len(set(versions.values())) == 1, versions)
        for n in ("netspout/appserver/static/dist/index.html", "netspout/bin/netspout_gateway.py", "netspout/default/indexes.conf", "netspout/bin/netspout_core/catalog_data/capability_status.json", "netspout/bin/netspout_core/real_format_generators.py"):
            r = dexec(SPLUNK, "sha256sum", "/opt/splunk/etc/apps/" + n)
            add("installed_file_equals_archive[%s]" % n.split("/")[-1], r.returncode == 0 and r.stdout.split()[0] == arc(n), n)
        dist = [n for n in members if n.startswith("netspout/appserver/static/dist/assets/") and n.endswith(".js")]
        add("ui.bundle_present_and_referenced", bool(dist) and any(d.split("/")[-1] in tf.extractfile(members["netspout/appserver/static/dist/index.html"]).read().decode() for d in dist), [d.split("/")[-1] for d in dist])
        cap = json.loads(tf.extractfile(members["netspout/bin/netspout_core/catalog_data/capability_status.json"]).read())["sourcetypes"]
        ver = sorted(k for k, v in cap.items() if v["status"] == "VERIFIED")
        add("capability.verified_set", ver == sorted(["cisco:asa", "cisco:ios", "fortigate_traffic", "pan:traffic", "pan:threat", "pan:system"]), ver)
        live = json.loads((ROOT / "docs/contracts/ta_live_results.json").read_text())
        add("capability.verified_equals_live_evidence", set(ver) == {k for k, v in live.items() if v["passed"]}, "evidence file docs/contracts/ta_live_results.json")
    idx = {x["name"]: x["content"].get("datatype") for x in rest("/services/data/indexes?output_mode=json&count=0&datatype=all")["entry"]}
    for name, dt in (("idx_network_ops", "event"), ("idx_security_fw", "event"), ("idx_wireless_ops", "event"), ("cisco_mdt_metrics", "metric")):
        add("indexes.defined_by_the_app[%s]" % name, idx.get(name) == dt, idx.get(name))
    views = rest("/servicesNS/nobody/netspout/data/ui/views?output_mode=json&count=0")["entry"]
    add("dashboards.installed", len(views) >= 372, "%d views" % len(views))
    r = dexec(SPLUNK, "curl", "-s", "-m", "8", "http://engine:8081/health")
    add("engine.reachable_from_splunk_over_the_private_network", '"status":"ok"' in r.stdout.replace(" ", ""), r.stdout[:80])
    gw = dexec(SPLUNK, "curl", "-sk", "-m", "20", "-u", "admin:" + e["LAB_SPLUNK_PASSWORD"], "https://127.0.0.1:8089/services/netspout_gateway/health?output_mode=json")
    add("gateway.forwards_to_the_engine", "netspout-simulation-engine" in gw.stdout or '"ok"' in gw.stdout, gw.stdout[:120].replace(e["LAB_SPLUNK_PASSWORD"], "***"))
    codes = {r: dexec(SPLUNK, "curl", "-sk", "-m", "30", "-o", "/dev/null", "-w", "%{http_code}", "-u", "admin:" + e["LAB_SPLUNK_PASSWORD"], "https://127.0.0.1:8089/services/netspout_gateway" + r).stdout for r in ("/api/runs", "/api/replay/sources", "/api/compat/catalog", "/api/compat/scenarios", "/api/catalog/sourcetypes")}
    add("gateway.routes_reach_this_engine_build", set(codes.values()) == {"200"}, codes)
    env_in = dexec(SPLUNK, "printenv", "NETSPOUT_BACKEND_URL").stdout.strip()
    add("no_development_services_required", env_in == "http://engine:8081" and "8081" in env_in and not subprocess.run(["lsof", "-nP", "-iTCP:5173", "-sTCP:LISTEN"], capture_output=True).stdout, "gateway uses the engine container; no Vite server is listening on 5173")
    Path(out_path).write_text(json.dumps({"release_candidate": rc.name, "checks": checks, "passed": all(c["status"] == "PASS" for c in checks)}, indent=1) + "\n")
    return 0 if all(c["status"] == "PASS" for c in checks) else 1


BUILTIN = ("splunk", "SplunkForwarder", "SplunkLightForwarder", "SplunkDeploymentServerConfig", "alert", "appsbrowser", "audit_trail", "introspection", "journald", "launcher", "learned", "legacy",
           "python_upgrade", "sample_app", "search", "user-prefs", "framework", "gettingstarted", "netspout")


def install_ta(pkg):
    dest = "/tmp/rc_ta_" + Path(pkg).name
    subprocess.run(["docker", "cp", str(Path(pkg).expanduser()), "%s:%s" % (SPLUNK, dest)], check=True)
    c = rest("/services/apps/local?output_mode=json", {"name": dest, "filename": "true", "update": "true"})["entry"][0]
    print(json.dumps({"installed": c["name"], "version": c["content"].get("version")}))


def remove_ta(app):
    assert app != "netspout", "refusing to remove the app under test"
    urllib.request.urlopen(urllib.request.Request(MGMT + "/services/apps/local/%s?output_mode=json" % urllib.parse.quote(app), method="DELETE", headers={"Authorization": AUTH}), context=CTX, timeout=300).read()
    print("removed", app)


def apps():
    return sorted((x["name"], x["content"].get("version")) for x in rest("/services/apps/local?output_mode=json&count=0")["entry"] if not x["name"].startswith(BUILTIN))


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["wait"]:
        wait(); print("ready")
    elif a[:1] == ["install"]:
        install(a[1])
    elif a[:1] == ["install-ta"]:
        install_ta(a[1])
    elif a[:1] == ["remove-ta"]:
        remove_ta(a[1])
    elif a[:1] == ["create-index"]:
        rest("/services/data/indexes?output_mode=json", {"name": a[1], "datatype": a[2]}); print("created", a[1], a[2])
    elif a[:1] == ["apps"]:
        print(json.dumps(apps()))
    elif a[:1] == ["check"]:
        sys.exit(check(a[1], a[2]))
    else:
        raise SystemExit(__doc__)
