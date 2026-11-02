#!/usr/bin/env bash
# Feasibility probe: does the engine import and answer /api/health and /api/search inside SPLUNK's bundled Python,
# using only vendored pure-Python packages plus two compiled wheels (pydantic_core, websockets)? Uses a throwaway
# container from the splunk/splunk:10.2 image WITHOUT starting Splunk. Usage: scripts/probe_splunk_python_engine.sh [workdir]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"; W="${1:-$(mktemp -d)}"; mkdir -p "$W/wheels" "$W/vend"
printf 'fastapi==0.143.0\nuvicorn==0.54.0\npydantic==2.14.0\nwebsockets==17.2\nhttpx==0.28.1\n' > "$W/req.txt"
python3 -m pip download -q -r "$W/req.txt" -d "$W/wheels" --platform manylinux2014_x86_64 --platform manylinux_2_17_x86_64 --platform manylinux_2_28_x86_64 --python-version 3.13 --only-binary=:all:
for w in "$W"/wheels/*.whl; do unzip -q -o "$w" -d "$W/vend"; done
cat > "$W/probe.py" <<'PY'
import sys
import grpc, google.protobuf, cryptography, pydantic, fastapi
print("python", sys.version.split()[0], "grpc", grpc.__version__, "protobuf", google.protobuf.__version__, "cryptography", cryptography.__version__, "pydantic", pydantic.VERSION, "fastapi", fastapi.__version__)
from fastapi.testclient import TestClient
from app import main
c = TestClient(main.app)
print("health", c.get("/api/health").json().get("status"), "| search total", c.get("/api/search", params={"q": "NF-SEC-06"}).json().get("total"))
from netspout_core.gnmi import server  # noqa: F401
print("gnmi server import ok")
PY
# CRYPTOGRAPHY_OPENSSL_NO_LEGACY: only because the interpreter is called directly, outside `splunk cmd`/splunkd, which set the OpenSSL provider paths
docker run --rm --platform linux/amd64 --entrypoint bash -v "$W/vend:/vend:ro" -v "$ROOT:/repo:ro" -v "$W/probe.py:/probe.py:ro" \
  -e CRYPTOGRAPHY_OPENSSL_NO_LEGACY=1 -e NETSPOUT_CONFIG_DIR=/tmp/cfg -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/vend:/repo/src:/repo/backend \
  splunk/splunk:10.2 -c 'mkdir -p /tmp/cfg; cd /repo/backend; SPLUNK_HOME=/opt/splunk LD_LIBRARY_PATH=/opt/splunk/lib /opt/splunk/bin/python3.13 /probe.py 2>&1 | grep -v Deprecat'
du -sh "$W/vend" "$W/wheels"
