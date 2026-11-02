#!/usr/bin/env python3
"""
Build a TEST-ONLY single-package netspout.spl (Phase 2 candidate): the app plus the managed engine, so one package is installed.
It never touches the released artifacts (netspout.spl, netspout_cloud.spl, pulseforge-engine.tar.gz); output goes to
build/single_package_test/ (git-ignored). Run offline checks on the result with --verify.

  python scripts/build_single_package_test.py [--variants py313-linux-x86_64,py39-linux-x86_64,...] [--verify]

Contents added to a copy of netspout/: bin/engine/app (the engine API), bin/lib/<variant>/ (vendored wheels: fastapi, pydantic,
pydantic_core, uvicorn, httpx, websockets and their dependencies), bin/lib/MANIFEST.json, and a launcher stanza in default/inputs.conf.
grpcio, protobuf and cryptography are NOT vendored: Splunk's bundled Python provides them (checked on Splunk 10.2.7).
"""
import argparse
import ast
import gzip
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build" / "single_package_test"
REQ = ["fastapi==0.143.0", "uvicorn==0.54.0", "pydantic==2.14.0", "websockets==17.2", "httpx==0.28.1"]
DEFAULT_VARIANTS = ["py313-linux-x86_64", "py313-linux-aarch64", "py39-linux-x86_64", "py39-linux-aarch64"]
PLAT = {"x86_64": ["manylinux2014_x86_64", "manylinux_2_17_x86_64", "manylinux_2_28_x86_64"], "aarch64": ["manylinux2014_aarch64", "manylinux_2_17_aarch64", "manylinux_2_28_aarch64"]}
OPTIONAL = {"pygnmi", "gnmi"}  # pygnmi: guarded by try/except in the gNMI protobuf stubs; gnmi: last fallback in an import chain after netspout_core.gnmi
SPLUNK_PROVIDES = {"grpc", "google", "cryptography", "cffi", "pycparser"}  # present in Splunk 10.2.7's bundled Python
LAUNCHER_STANZA = """
[pulseforge_engine_launcher]
python.version = python3
python.required = 3.13

[pulseforge_engine_launcher://default]
engine_mode = managed
disabled = 0
interval = 0
"""


def download(variant, cache):
    py, _, arch = variant.split("-", 2)
    dest = cache / variant
    dest.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "pip", "download", "-q", "-d", str(dest), "--python-version", py[2:], "--only-binary=:all:"]
    for p in PLAT[arch]:
        cmd += ["--platform", p]
    r = subprocess.run(cmd + REQ, capture_output=True, text=True)
    return r.returncode == 0, (r.stderr or "").strip().splitlines()[-1:] or [""]


def third_party_imports(engine_dir, bin_dir):
    """Top-level third-party module names imported by the engine and core sources (stdlib and in-package modules excluded)."""
    local = {p.stem for p in bin_dir.glob("*.py")} | {p.name for p in bin_dir.iterdir() if p.is_dir()} | {"app", "netspout_core"}
    found = set()
    for base in (engine_dir, bin_dir / "netspout_core"):
        for f in base.rglob("*.py"):
            try:
                tree = ast.parse(f.read_text(encoding="utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for n in ast.walk(tree):
                names = [a.name for a in n.names] if isinstance(n, ast.Import) else [n.module] if isinstance(n, ast.ImportFrom) and n.level == 0 and n.module else []
                found |= {x.split(".")[0] for x in names}
    return sorted(m for m in found if m not in sys.stdlib_module_names and m not in local)


def build(variants):
    cache = ROOT / "build" / "wheel_cache"
    stage = Path(tempfile.mkdtemp(prefix="pfsp"))
    app = stage / "netspout"
    shutil.copytree(ROOT / "netspout", app, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "local"))
    shutil.copytree(ROOT / "backend" / "app", app / "bin" / "engine" / "app", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    manifest = {"variants": {}, "requirements": REQ}
    for v in variants:
        ok, note = download(v, cache)
        if not ok:
            manifest["variants"][v] = {"status": "UNAVAILABLE", "reason": note[0][:200]}
            continue
        target = app / "bin" / "lib" / v
        target.mkdir(parents=True)
        wheels = sorted((cache / v).glob("*.whl"))
        for w in wheels:
            zipfile.ZipFile(w).extractall(target)
        manifest["variants"][v] = {"status": "BUNDLED", "wheels": [{"name": w.name, "sha256": hashlib.sha256(w.read_bytes()).hexdigest()} for w in wheels],
                                   "compiled": sorted({p.name for p in target.rglob("*.so")})[:12]}
    (app / "bin" / "lib").mkdir(exist_ok=True)
    (app / "bin" / "lib" / "MANIFEST.json").write_text(json.dumps(manifest, indent=1))
    (app / "bin" / "MANAGED_ENGINE").write_text("This build runs the engine under splunkd; the gateway never falls back to a TCP engine.\n")
    inputs = app / "default" / "inputs.conf"
    inputs.write_text(inputs.read_text() + LAUNCHER_STANZA)
    OUT.mkdir(parents=True, exist_ok=True)
    spl = OUT / "netspout_single_test.spl"
    with open(spl, "wb") as raw, gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz, tarfile.open(fileobj=gz, mode="w") as tar:
        tar.add(app, arcname="netspout")
    shutil.rmtree(stage)
    return spl


def verify(spl):
    """Offline completeness checks on the built package; returns a result dict (no Splunk involved)."""
    names, res = None, {"package": str(spl.relative_to(ROOT)), "bytes": spl.stat().st_size, "sha256": hashlib.sha256(spl.read_bytes()).hexdigest()}
    with tarfile.open(spl, "r:gz") as t:
        names = set(t.getnames())
        manifest = json.loads(t.extractfile("netspout/bin/lib/MANIFEST.json").read())
        inputs = t.extractfile("netspout/default/inputs.conf").read().decode()
    need = ["netspout/bin/pulseforge_engine_launcher.py", "netspout/bin/pulseforge_engine_main.py", "netspout/bin/pulseforge_ipc.py", "netspout/bin/netspout_gateway.py",
            "netspout/bin/engine/app/main.py", "netspout/bin/engine/app/gateway_auth.py", "netspout/bin/netspout_core/models.py", "netspout/default/restmap.conf",
            "netspout/default/authorize.conf", "netspout/default/data/ui/nav/default.xml", "netspout/app.manifest"]
    res["required_files_missing"] = [n for n in need if n not in names]
    res["launcher_stanza_enabled"] = "[pulseforge_engine_launcher://default]" in inputs and "disabled = 0" in inputs and "python.required = 3.13" in inputs
    res["variants"] = {k: v["status"] for k, v in manifest["variants"].items()}
    work = Path(tempfile.mkdtemp(prefix="pfv"))
    with tarfile.open(spl, "r:gz") as t:
        t.extractall(work, filter="data")
    app = work / "netspout"
    needed = [m for m in third_party_imports(app / "bin" / "engine", app / "bin") if m not in SPLUNK_PROVIDES]
    res["third_party_imports"] = needed
    res["optional_unresolved_ok"] = sorted(set(needed) & OPTIONAL)
    needed = [m for m in needed if m not in OPTIONAL]
    res["dependency_gaps"] = {}
    for v, info in manifest["variants"].items():
        if info["status"] != "BUNDLED":
            continue
        lib = app / "bin" / "lib" / v
        missing = [m for m in needed if not ((lib / m).is_dir() or (lib / (m + ".py")).is_file() or list(lib.glob(m + ".*.so")))]
        res["dependency_gaps"][v] = missing
    # no environment credential value or private key material in the package
    secret_hits = []
    for p in app.rglob("*"):
        if p.is_file() and p.stat().st_size < 3_000_000:
            b = p.read_bytes()
            if b"-----BEGIN PRIVATE KEY-----" in b or b"-----BEGIN RSA PRIVATE KEY-----" in b:
                secret_hits.append(str(p.relative_to(app)))
    res["private_key_files"] = secret_hits
    shutil.rmtree(work)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--variants", default=",".join(DEFAULT_VARIANTS))
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    out = build([v for v in a.variants.split(",") if v])
    print("built", out, out.stat().st_size, "bytes")
    if a.verify:
        r = verify(out)
        (OUT / "verify.json").write_text(json.dumps(r, indent=1))
        print(json.dumps(r, indent=1))
