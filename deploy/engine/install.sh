#!/usr/bin/env bash
# Creates the engine's virtualenv inside an extracted pulseforge-engine package (Python 3.11-3.13 recommended).
set -euo pipefail
home="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
"${PULSEFORGE_BOOTSTRAP_PYTHON:-python3}" -m venv "$home/venv"
"$home/venv/bin/pip" install --quiet -r "$home/backend/requirements.txt"
echo "Installed. Start with: $home/deploy/engine/pulseforge-engine   (config: deploy/engine/engine.env.example)"
