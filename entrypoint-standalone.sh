#!/bin/bash
set -e

echo "=========================================================================="
echo "⚡ NetSpout Standalone: Booting Splunk Enterprise + Fast Simulation Engine"
echo "=========================================================================="

# Start the Fast Simulation Companion Service in the background
if [ -d "/opt/netspout-backend" ]; then
    echo ">> Starting NetSpout Fast Simulation Engine on port ${FAST_SIMULATION_PORT:-8081}..."
    cd /opt/netspout-backend
    python3 run.py --host 0.0.0.0 --port ${FAST_SIMULATION_PORT:-8081} &
    BACKEND_PID=$!
    echo ">> Fast Simulation Engine started (PID: $BACKEND_PID)"
fi

# Delegate to standard Splunk entrypoint to start Splunk Enterprise service
echo ">> Starting Splunk Enterprise 10.2 (Web: 8000, HEC: 8088, REST: 8089)..."
exec /sbin/entrypoint.sh "$@"
