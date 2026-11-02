#!/usr/bin/env bash
# Start the PulseForge engine against an isolated Docker Splunk lab (default: tests/lab/phase4e).
# Usage: scripts/start_lab_engine.sh [lab-dir] [port] [index]     Secrets come from <lab-dir>/.env.lab (git-ignored) and are never printed.
# Writes a Connection Center destination for the lab into a throwaway config dir; PulseForge never creates indexes.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LAB="${1:-$ROOT/tests/lab/phase4e}"; PORT="${2:-8091}"; IDX="${3:-idx_network_ops}"
PY="${PULSEFORGE_PYTHON:-$ROOT/.venv/bin/python}"
set -a; . "$LAB/.env.lab"; set +a
export NETSPOUT_HEC_TOKEN="$LAB_HEC_TOKEN" NETSPOUT_SPLUNK_PASSWORD="$LAB_SPLUNK_PASSWORD"
export NETSPOUT_CONFIG_DIR="${NETSPOUT_CONFIG_DIR:-$ROOT/.lab_engine_cfg}"
export NETSPOUT_REPLAY_STATE="$NETSPOUT_CONFIG_DIR/replay_sessions.json"
mkdir -p "$NETSPOUT_CONFIG_DIR"
"$PY" - <<PYEOF
import json, os
json.dump({"schema_version": "1.0.0", "deployment_mode": "DOCKER_LAB", "splunk_deployment_type": "DOCKER_LAB", "auth_method": "HEC_TOKEN_AND_BASIC_SEARCH", "allow_insecure_tls": True,
           "hec_url": "https://127.0.0.1:%s/services/collector" % os.environ["LAB_HEC_PORT"], "search_url": "https://127.0.0.1:%s/services/search/jobs/export" % os.environ["LAB_MGMT_PORT"],
           "search_username": "admin", "indexes": ["$IDX"], "collectors": [], "guided_sample": True}, open(os.path.join(os.environ["NETSPOUT_CONFIG_DIR"], "connection.json"), "w"), indent=1)
PYEOF
cd "$ROOT/backend"
exec env PYTHONPATH=../src:. "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port "$PORT" --log-level warning
