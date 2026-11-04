#!/usr/bin/env bash
# Usage: lab.sh up RC_DIR | down | destroy   (RC_DIR holds the candidate's pulseforge-engine.tar.gz; "destroy" removes only this lab's volumes)
set -euo pipefail
cd "$(dirname "$0")"
ENVF=.env.lab
case "${1:-}" in
  up)
    RC_DIR="$(cd "${2:?usage: lab.sh up RC_DIR}" && pwd)"
    [ -f "$RC_DIR/pulseforge-engine.tar.gz" ] || { echo "no pulseforge-engine.tar.gz in $RC_DIR"; exit 2; }
    if [ ! -f "$ENVF" ]; then
      umask 077
      { echo "LAB_SPLUNK_PASSWORD=Ns$(openssl rand -hex 12)!A"
        echo "LAB_HEC_TOKEN=$(uuidgen | tr 'A-Z' 'a-z')"
        echo "LAB_WEB_PORT=39000"; echo "LAB_MGMT_PORT=39191"; echo "LAB_HEC_PORT=39088"; echo "RC_ENGINE_PORT=38081"; } > "$ENVF"
    fi
    RC_DIR="$RC_DIR" docker compose --env-file "$ENVF" up -d --build ;;
  down) RC_DIR=. docker compose --env-file "$ENVF" down ;;
  destroy) RC_DIR=. docker compose --env-file "$ENVF" down -v ;;
  *) echo "usage: $0 up RC_DIR|down|destroy"; exit 2 ;;
esac
