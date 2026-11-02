#!/usr/bin/env bash
# Usage: lab.sh up|down|env   (down keeps volumes; "destroy" removes only this lab's volumes)
set -euo pipefail
cd "$(dirname "$0")"
ENVF=.env.lab
case "${1:-}" in
  up)
    if [ ! -f "$ENVF" ]; then
      umask 077
      { echo "LAB_SPLUNK_PASSWORD=Ns$(openssl rand -hex 12)!A"
        echo "LAB_HEC_TOKEN=$(uuidgen | tr 'A-Z' 'a-z')"
        echo "LAB_WEB_PORT=18000"; echo "LAB_MGMT_PORT=18191"; echo "LAB_HEC_PORT=18088"; } > "$ENVF"
    fi
    docker compose --env-file "$ENVF" up -d ;;
  down) docker compose --env-file "$ENVF" down ;;
  destroy) docker compose --env-file "$ENVF" down -v ;;
  *) echo "usage: $0 up|down|destroy"; exit 2 ;;
esac
