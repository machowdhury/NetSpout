#!/usr/bin/env bash
# Usage: lab.sh up LAB_NAME PORT_BASE RC_DIR | down LAB_NAME | destroy LAB_NAME     (LAB_NAME: nsp15* or nsp16*; RC_DIR holds pulseforge-engine.tar.gz)
# PORT_BASE 45000 -> web 45000, HEC 45088, mgmt 45191, engine 45081, tap 45990. "destroy" removes only this instance's own volumes.
set -euo pipefail
cd "$(dirname "$0")"
N="${2:?usage: lab.sh up|down|destroy LAB_NAME ...}"
case "$N" in nsp15|nsp15u|nsp15r|nsp16|nsp16u|nsp16r|nsp16l) ;; *) echo "LAB_NAME must be nsp15, nsp15u, nsp15r, nsp16, nsp16u, nsp16r or nsp16l"; exit 2 ;; esac
ENVF=".env.$N"
case "${1:-}" in
  up)
    B="${3:?PORT_BASE}"; RC_DIR="$(cd "${4:?RC_DIR}" && pwd)"
    [ -f "$RC_DIR/pulseforge-engine.tar.gz" ] || { echo "no pulseforge-engine.tar.gz in $RC_DIR"; exit 2; }
    if [ ! -f "$ENVF" ]; then
      umask 077
      { echo "LAB_NAME=$N"; echo "LAB_SPLUNK_PASSWORD=Ns$(openssl rand -hex 12)!A"; echo "LAB_HEC_TOKEN=$(uuidgen | tr 'A-Z' 'a-z')"
        echo "LAB_WEB_PORT=$B"; echo "LAB_HEC_PORT=$((B+88))"; echo "LAB_MGMT_PORT=$((B+191))"; echo "RC_ENGINE_PORT=$((B+81))"; echo "LAB_TAP_PORT=$((B+990))"; } > "$ENVF"
    fi
    RC_DIR="$RC_DIR" docker compose --env-file "$ENVF" up -d --build ;;
  down) RC_DIR=. docker compose --env-file "$ENVF" down ;;
  destroy) RC_DIR=. docker compose --env-file "$ENVF" down -v ;;
  *) echo "usage"; exit 2 ;;
esac
