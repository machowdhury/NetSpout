#!/usr/bin/env python3
"""Host and Splunk facts for the evidence: python phase17_hostinfo.py <container> <image> <hostlabel>  (prints JSON)."""
import json
import os
import subprocess
import sys

c, image, label = sys.argv[1:4]
sh = lambda cmd: subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()
print(json.dumps({
    "host_label": label, "image": image, "uname": sh("uname -srm"), "cpu_model": sh("lscpu | sed -n 's/^Model name: *//p'"), "vcpus": os.cpu_count(),
    "mem_gb": round(int(sh("awk '/MemTotal/{print $2}' /proc/meminfo") or 0) / 1048576, 1), "docker": sh("docker --version"),
    "kernel_page_size": sh("getconf PAGESIZE"), "splunk_version": sh("docker exec %s /opt/splunk/bin/splunk version 2>/dev/null | tail -1" % c),
    "splunk_python": sh("docker exec -e LD_LIBRARY_PATH=/opt/splunk/lib %s /opt/splunk/bin/python3.13 -V" % c), "root_fs": sh("df -h / | tail -1"),
}, indent=1))
