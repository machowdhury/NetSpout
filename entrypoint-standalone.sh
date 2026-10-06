#!/bin/bash
set -e

echo "=========================================================================="
echo "⚡ NetSpout Standalone: Booting Splunk Enterprise + Fast Simulation Engine"
echo "=========================================================================="

# Ensure all default Splunk apps and configurations are synchronized
if [ ! -d "/opt/splunk/etc/apps/splunk_httpinput" ] && [ -d "/opt/splunk-etc/apps" ]; then
    echo ">> Synchronizing default Splunk apps from /opt/splunk-etc to /opt/splunk/etc..."
    cp -rn /opt/splunk-etc/* /opt/splunk/etc/ 2>/dev/null || true
fi

# Ensure HEC & Indexes local configuration is present in app directory
mkdir -p /opt/splunk/etc/apps/netspout/local
if [ ! -f "/opt/splunk/etc/apps/netspout/local/inputs.conf" ] && [ -f "/opt/splunk/etc/apps/netspout/default/inputs.conf" ]; then
    cp /opt/splunk/etc/apps/netspout/default/inputs.conf /opt/splunk/etc/apps/netspout/local/inputs.conf
fi
if [ ! -f "/opt/splunk/etc/apps/netspout/local/indexes.conf" ] && [ -f "/opt/splunk/etc/apps/netspout/default/indexes.conf" ]; then
    cp /opt/splunk/etc/apps/netspout/default/indexes.conf /opt/splunk/etc/apps/netspout/local/indexes.conf
fi

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
