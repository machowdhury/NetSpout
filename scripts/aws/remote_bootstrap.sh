#!/usr/bin/env bash
# Runs ON the instance as root. remote_bootstrap.sh <deadman_minutes> <image-ref> [<image-ref>...]
# Installs Docker, Python venv (psutil), Node 22 (copied out of the repo's own digest-pinned node image, no curl|bash), Playwright Chromium; pulls the Splunk images by digest.
set -eu
DEADMAN=$1; shift
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq docker.io python3-venv python3-pip git curl jq unzip sysstat libmagic1 >/dev/null
systemctl enable --now docker
mkdir -p /opt/p17/secrets /opt/p17/logs /opt/p17/status /opt/p17/build; chmod 700 /opt/p17/secrets
python3 -m venv /opt/p17/venv && /opt/p17/venv/bin/pip install -q psutil
NODE_IMG=node:22-bookworm-slim@sha256:c3de60bf2f9dd0ac6370e6117950ff62d6e339527e7472301c9c78a017978392   # the digest Dockerfile.standalone pins
docker pull -q $NODE_IMG >/dev/null; id=$(docker create $NODE_IMG); mkdir -p /opt/node; docker cp $id:/usr/local/. /opt/node/; docker rm $id >/dev/null
ln -sf /opt/node/bin/node /usr/local/bin/node; ln -sf /opt/node/bin/npm /usr/local/bin/npm; ln -sf /opt/node/bin/npx /usr/local/bin/npx
node --version
mkdir -p /opt/p17/harness && tar -xzf /opt/p17/harness.tar.gz -C /opt/p17/harness
( cd /opt/p17/harness/frontend && npm ci --silent && npx playwright install --with-deps chromium >/dev/null )
for img in "$@"; do docker pull -q "$img" >/dev/null; echo "pulled $img"; done
shutdown -h +$DEADMAN "p17 deadman: instance stops itself (behaviour: terminate)" >/dev/null 2>&1 || true
echo "bootstrap done; deadman in $DEADMAN minutes"
