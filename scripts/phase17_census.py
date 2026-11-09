#!/usr/bin/env python3
"""Install census for the disposable Splunk container: which processes and listening ports the single package added.
  python scripts/phase17_census.py <container> <target-dir-name> <ports-before-file> <artifact-sha256> <host-arch-label>"""
import json
import re
import subprocess
import sys
from pathlib import Path

container, target, before_file, sha, arch = sys.argv[1:6]


def sh(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()


procs = sh("docker exec -u root %s ps -eo pid,ppid,user,args | grep -E 'pulseforge|engine_main' | grep -v grep | sed 's#/run/rosetta/rosetta /opt/splunk/bin/python3.13 /opt/splunk/bin/python3.13##'" % container).splitlines()
apps = sh("docker exec %s ls /opt/splunk/etc/apps" % container).split()
out = sh("docker exec -u root %s sh -c 'cat /proc/net/tcp /proc/net/tcp6' | awk '$4==\"0A\"{print $2}' | sed 's/.*://' | sort -u" % container)
after = sorted(int(h, 16) for h in out.split() if int(h, 16) < 32000)
before = [int(x) for x in re.findall(r"\d+", open(before_file).read().split(":")[1]) if int(x) < 32000]
res = {"name": "single_package_install_census", "artifact_sha256": sha, "host": arch,
       "install_method": "Splunk Web > Apps > Manage Apps > Install app from file (Playwright upload), then Splunk restart",
       "installed_apps_with_engine_or_pulse_in_name": [a for a in apps if re.search("engine|pulse", a, re.I)], "netspout_app_present": "netspout" in apps,
       "launcher_and_engine_processes": procs, "engine_state_dir_listing": sh("docker exec -u root %s ls -l /opt/splunk/var/lib/netspout" % container).splitlines(),
       "listening_tcp_ports_below_32000_before_install": before, "listening_tcp_ports_below_32000_after_install": after,
       "note": "the Docker host also runs an unrelated evaluation container with its own engine on host port 8081; this package never uses a TCP engine URL (MANAGED_ENGINE marker)",
       "ok": len(procs) == 2 and after == before and "netspout" in apps}
d = Path(__file__).resolve().parents[1] / "docs/verification/evidence/phase17" / target
d.mkdir(parents=True, exist_ok=True)
(d / "install_census.json").write_text(json.dumps({"results": [res]}, indent=1))
print("census ok" if res["ok"] else "census FAILED", len(procs), after == before)
