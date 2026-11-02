#!/bin/bash
set -e

echo "=========================================================================="
echo "⚡ NetSpout Standalone: Booting Splunk Enterprise + Fast Simulation Engine"
echo "=========================================================================="

: "${SPLUNK_HEC_TOKEN:?Set SPLUNK_HEC_TOKEN before starting NetSpout}"
umask 077

# Ensure all default Splunk apps and configurations are synchronized
if [ ! -d "/opt/splunk/etc/apps/splunk_httpinput" ] && [ -d "/opt/splunk-etc/apps" ]; then
    echo ">> Synchronizing default Splunk apps from /opt/splunk-etc to /opt/splunk/etc..."
    sudo cp -rn /opt/splunk-etc/* /opt/splunk/etc/ 2>/dev/null || true
fi

# Render lab-only HEC configuration from the runtime secret. The secret is
# never committed to an image layer, application default, log, or browser URL.
HEC_CONFIG="$(mktemp)"
trap 'rm -f "${HEC_CONFIG}"' EXIT
cat > "${HEC_CONFIG}" <<EOF
[http]
disabled = 0
port = 8088
enableSSL = 1

[http://netspout_events]
disabled = 0
token = ${SPLUNK_HEC_TOKEN}
index = idx_network_ops
indexes = idx_network_ops,idx_security_fw,idx_wireless_ops,idx_performance_metrics,cisco_mdt_metrics,cisco_duo,netops_logs,main

[udp://514]
connection_host = dns
index = idx_network_ops
sourcetype = syslog
no_priority_stripping = true

[tcp://514]
connection_host = dns
index = idx_network_ops
sourcetype = syslog
EOF
sudo install -d -o splunk -g splunk /opt/splunk/etc/apps/netspout/local
sudo install -m 600 -o splunk -g splunk "${HEC_CONFIG}" /opt/splunk/etc/apps/netspout/local/inputs.conf
sudo install -d -o splunk -g splunk /opt/splunk-etc/apps/netspout/local
sudo install -m 600 -o splunk -g splunk "${HEC_CONFIG}" /opt/splunk-etc/apps/netspout/local/inputs.conf
rm -f "${HEC_CONFIG}"
trap - EXIT
if [ ! -f "/opt/splunk/etc/apps/netspout/local/indexes.conf" ] && [ -f "/opt/splunk/etc/apps/netspout/default/indexes.conf" ]; then
    sudo install -m 600 -o splunk -g splunk \
        /opt/splunk/etc/apps/netspout/default/indexes.conf \
        /opt/splunk/etc/apps/netspout/local/indexes.conf
fi

# Start the external engine only after the upstream bootstrap has initialized
# persistent volume ownership and the Splunk management service is reachable.
start_backend() {
    if [ ! -d "/opt/netspout-backend" ]; then
        return
    fi
    for _ in $(seq 1 180); do
        # An unauthenticated management request returns HTTP 401 when the TLS
        # listener is ready; curl without --fail still proves reachability.
        if curl -kSs https://127.0.0.1:8089/services/server/info >/dev/null 2>&1; then
            sudo install -d -o splunk -g splunk \
                "${NETSPOUT_CONFIG_DIR:-/opt/splunk/var/lib/netspout/config}" \
                "${NETSPOUT_STUDIO_DIR:-/opt/splunk/var/lib/netspout/studio}"
            echo ">> Starting NetSpout Fast Simulation Engine on port ${FAST_SIMULATION_PORT:-8081}..."
            cd /opt/netspout-backend
            exec sudo -E -u splunk python3 run.py \
                --host 0.0.0.0 --port "${FAST_SIMULATION_PORT:-8081}"
        fi
        sleep 1
    done
    echo ">> NetSpout engine did not start: Splunk management readiness timed out." >&2
}
start_backend &

# Delegate to standard Splunk entrypoint to start Splunk Enterprise service
echo ">> Starting Splunk Enterprise 10.2 (Web: 8000, HEC: 8088, REST: 8089)..."
exec /sbin/entrypoint.sh "$@"
