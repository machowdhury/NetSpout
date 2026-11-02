#!/usr/bin/env python3
"""Build netspout_cloud.spl: the Splunk Cloud EDITION of the PulseForge app (dashboards and navigation only).

Why a separate edition: AppInspect (cloud tags) rejects the engine code shipped in the Enterprise app (UDP communications in the SNMP/syslog/flow modules,
persistent REST handlers, a modular input, index definitions). Splunk Cloud cannot run a collector either. The Cloud edition therefore carries only
Dashboard Studio views, navigation and metadata; the PulseForge engine runs as a separate, customer-hosted service that sends events to the Cloud HEC endpoint.
No Python, no inputs, no indexes, no custom conf, no setup.  Run: python scripts/build_splunk_cloud_package.py
"""
import hashlib
import io
import json
import os
import re
import shutil
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "netspout"
OUT = ROOT / "netspout_cloud.spl"
APP_CONF = """[launcher]
author = Mahamudul Chowdhury
description = PulseForge scenario dashboards for Splunk: Dashboard Studio views over telemetry produced by a customer-hosted PulseForge engine
version = 2.0.0

[id]
name = netspout
version = 2.0.0

[package]
id = netspout
check_for_updates = 0

[ui]
is_visible = 1
label = PulseForge Scenario Dashboards
show_in_nav = 1
"""
NAV = """<nav search_view="search">
{collections}
  <view name="search" label="Search"/>
</nav>
"""


def build():
    views = sorted((SRC / "default/data/ui/views").glob("pf_*.xml"))
    nav_src = (SRC / "default/data/ui/nav/default.xml").read_text(encoding="utf-8")
    block = re.search(r'  <collection label="Scenario Dashboards">.*?</collection>\s*</collection>', nav_src, re.S).group(0)
    stage = ROOT / ".cloud_stage" / "netspout"
    shutil.rmtree(stage.parent, ignore_errors=True)
    (stage / "default/data/ui/views").mkdir(parents=True)
    (stage / "default/data/ui/nav").mkdir(parents=True)
    (stage / "metadata").mkdir()
    for v in views:
        shutil.copyfile(v, stage / "default/data/ui/views" / v.name)
    (stage / "default/app.conf").write_text(APP_CONF, encoding="utf-8")
    (stage / "default/data/ui/nav/default.xml").write_text(NAV.format(collections=block), encoding="utf-8")
    meta = (SRC / "metadata/default.meta").read_text(encoding="utf-8")
    meta = re.sub(r"\badmin\b(?!,\s*sc_admin)", "admin, sc_admin", meta)   # Splunk Cloud customer administrators hold sc_admin
    (stage / "metadata/default.meta").write_text(meta, encoding="utf-8")
    shutil.copyfile(SRC / "app.manifest", stage / "app.manifest")
    (stage / "README").write_text("PulseForge scenario dashboards (Splunk Cloud edition). Dashboards only: the PulseForge engine runs outside Splunk. See docs/guides/SPLUNK_CLOUD_GUIDE.md.\n", encoding="utf-8")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for p in sorted(stage.rglob("*")):
            info = tar.gettarinfo(str(p), arcname=str(Path("netspout") / p.relative_to(stage)))
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            if p.is_file():
                with open(p, "rb") as fh:
                    tar.addfile(info, fh)
            else:
                tar.addfile(info)
    OUT.write_bytes(buf.getvalue())
    shutil.rmtree(stage.parent)
    digest = hashlib.sha256(OUT.read_bytes()).hexdigest()
    (ROOT / "netspout_cloud.spl.manifest.json").write_text(json.dumps({"artifact": OUT.name, "sha256": digest, "views": len(views), "edition": "splunk-cloud-dashboards-only"}, indent=1) + "\n")
    print(json.dumps({"artifact": OUT.name, "bytes": OUT.stat().st_size, "views": len(views), "sha256": digest}))


if __name__ == "__main__":
    build()
