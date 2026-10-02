# NetSpout — Troubleshooting & Diagnostics

This guide provides troubleshooting steps and diagnostics for common preflight, collector, network socket, and Splunk ingestion issues.

---

## 1. Preflight Check Diagnostic Matrix

| Check Name | Symptom / Failure | Root Cause | Remediation |
|---|---|---|---|
| **`splunk_hec_reachability`** | HTTP 404 or Connection Refused | HEC is disabled or port is incorrect in Splunk | In Splunk Web: **Settings → Data inputs → HTTP Event Collector → Global Settings**, ensure HEC is Enabled, SSL checked, and port is 8888 or 8088. |
| **`splunk_hec_reachability`** | HTTP 401 Unauthorized | Invalid or missing HEC token | Generate or copy an active HEC token in Splunk Web, and set `NETSPOUT_HEC_TOKEN="<your-token>"`. |
| **`splunk_rest_search`** | HTTP 401 Unauthorized | Incorrect admin credentials | Verify your Splunk credentials and export `NETSPOUT_SPLUNK_USER` and `NETSPOUT_SPLUNK_PASSWORD`. |
| **`event_index_availability`** | Index `idx_network_ops` not found | Index has not been created in Splunk | Create the event index in Splunk Web: **Settings → Indexes → New Index** (`idx_network_ops`, Events). |
| **`metric_index_availability`** | Index `cisco_mdt_metrics` not found | Metric index missing | Create the metric index in Splunk Web: **Settings → Indexes → New Index** (`cisco_mdt_metrics`, Metrics). |
| **`gnmic_binary`** | Missing `gnmic` binary in PATH | `gnmic` is not installed | Install via Homebrew: `brew install gnmic` or binary download from https://gnmic.openconfig.net. |
| **`local_tcp_bind`** | Permission denied or Port in use | Non-loopback interface or conflicting service | NetSpout binds to `127.0.0.1` ephemeral ports. Ensure no security tool blocks local loopback binds. |

---

## 2. Diagnosing Native gNMI Streaming

### Verifying the Native gNMI Server Manually
You can test the NetSpout gNMI server directly from the command line using `gnmic`:

```bash
# Capabilities query
gnmic -a 127.0.0.1:50051 --insecure capabilities

# Target device subscription
gnmic -a 127.0.0.1:50051 --insecure \
  --path "/interfaces/interface[name=HundredGigE0/0/0/0]/state/oper-status" \
  subscribe --mode once
```

### Checking Splunk Ingestion for gNMI Events
If `gnmic` receives data but events do not appear in Splunk:
1. Check the HEC token permissions: The token must have access to `idx_network_ops` and `cisco_mdt_metrics`.
2. Inspect the HEC endpoint log in Splunk:
   ```spl
   index=_internal sourcetype=splunkd component=HttpInputDataHandler
   | table _time log_level message
   ```

---

## 3. Diagnosing Native SNMPv2c Transport

### Verifying Local UDP Binds
NetSpout sends SNMP Traps and Informs over UDP loopback to port `1162` or ephemeral ports.
- Test if port 1162 is available:
  ```bash
  nc -z -v -u 127.0.0.1 1162
  ```
- If running unprivileged on macOS/Linux, ports above 1024 (e.g. 1162) do not require `sudo`.

---

## 4. Diagnosing Splunk Metric Ingestion (`| mstats`)

When querying `cisco_mdt_metrics`, Splunk Enterprise requires `metric_name=*` or explicit metric filter expressions in the `WHERE` clause:

```spl
# INCORRECT (may return 0 results depending on Splunk version)
| mstats avg(_value) WHERE index=cisco_mdt_metrics BY metric_name

# CORRECT
| mstats avg(_value) WHERE index=cisco_mdt_metrics metric_name=* BY metric_name span=1s
```

---

## 5. Collecting Debug Diagnostics for Support

If an unexpected behavior occurs, run the diagnostic collection command:

```bash
# Run backend health check
curl -s http://127.0.0.1:8080/api/native-gnmi/preflight | jq .

# Verify Python test harness
PYTHONPATH=src python3 -m unittest tests/test_gate13e_customer_acceptance.py
```
Include the output in any GitHub issue reported to [NetSpout Issues](https://github.com/machowdhury/NetSpout/issues).
