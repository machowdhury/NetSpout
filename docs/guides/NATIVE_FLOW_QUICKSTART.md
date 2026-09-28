# NetSpout Native Flow Quickstart Guide

Welcome to NetSpout Native Flow Telemetry! This guide explains how to operate the standards-compliant NetFlow v9 and IPFIX export pipeline from start to finish.

---

## 1. What is "Native Flow" Telemetry?

In standard mode (Mode A), NetSpout sends modeled JSON event payloads directly to Splunk HTTP Event Collector (HEC).

In **Native Flow Mode (Mode B)**, NetSpout behaves exactly like a real hardware network switch or router exporter:
- Encodes flow records into standard binary datagrams (`RFC 3954` for NetFlow v9, `RFC 7011` for IPFIX).
- Transmits raw binary UDP datagrams over the network.
- Requires an external flow collector to ingest UDP packets, decode templates and flow records, and forward structured events into Splunk.

> **Semantic Distinction:**
> - `Fidelity: NATIVE TRANSPORT` — Standards-compliant binary wire serialization and UDP transmission.
> - `Fidelity: MODELED PAYLOAD` — Simulated telemetry schema without hardware ASICs.

---

## 2. Why is an External Collector Required?

Splunk Enterprise cannot natively bind to raw UDP ports and decode complex binary NetFlow v9 templates or IPFIX information elements directly into index fields. In real networks, an external collector (such as Splunk Stream, GoFlow2, or nProbe) receives UDP traffic, parses flow records, and forwards them to Splunk HEC.

NetSpout provides a containerized, production-grade **GoFlow2** collector stack in `deploy/collector/`.

---

## 3. Starting the Collector Stack

Start the collector stack using the lifecycle manager (which automatically discovers `docker` across `PATH` and standard macOS Docker Desktop locations such as `/usr/local/bin/docker`, `/opt/homebrew/bin/docker`, `/Applications/Docker.app/Contents/Resources/bin/docker`, and `~/.docker/bin/docker`):

```bash
python3 deploy/collector/manage_collector.py start
```

Or directly via Docker Compose (if `docker` is in your shell `PATH`):

```bash
docker compose -f deploy/collector/docker-compose.collector.yml up -d
```

Verify that the stack is healthy:

```bash
python3 deploy/collector/manage_collector.py status
```

Expected output:
```text
  [PASS] GoFlow2 collector metrics (127.0.0.1:8080/metrics) is UP
  [PASS] Forwarder status (127.0.0.1:8082/status): HEALTHY
         Flows Read: 0, Forwarded: 0, Failures: 0
```

Run a pre-flight readiness audit from the repository root (no `PYTHONPATH` environment variable required):

```bash
python3 deploy/collector/manage_collector.py preflight
```

---

## 4. Configuring NetSpout

NetSpout can be configured via environment variables, the web UI, or Python configuration.

### Environment Variables:
```bash
export NETSPOUT_FLOW_PROTOCOL=IPFIX          # IPFIX, NETFLOW_V9, or BOTH
export NETSPOUT_COLLECTOR_HOST=127.0.0.1     # Collector IP
export NETSPOUT_IPFIX_PORT=4739              # Default IPFIX UDP port
export NETSPOUT_NETFLOW_PORT=2055            # Default NetFlow v9 UDP port
export NETSPOUT_RATE_LIMIT_PPS=100           # Token-bucket rate limit (pps)
```

---

## 5. Running a Scenario

Run a scenario using the CLI or automated verification tools:

```bash
# Verify end-to-end flow delivery for mixed_backbone_optical:
PYTHONPATH=src python3 scripts/verify_gate11c_e2e.py
```

Or execute via Python:
```python
from netspout_core.transport_native_flow import NativeFlowTransport
from netspout_core.exporter_session import ExporterSession
from netspout_core.models import FlowRecord

transport = NativeFlowTransport(protocol="IPFIX", destination_port=4739)
session = ExporterSession(node_id="core-switch-01", observation_domain_id=101)

record = FlowRecord(
    src_ip="10.100.1.10",
    dest_ip="10.200.1.20",
    src_port=443,
    dest_port=52100,
    protocol=6,
    bytes_count=8420950,
    packets_count=5614
)

result = transport.send_batch([record], session=session, force_template=True)
print(f"Datagrams Sent: {result.datagrams_sent}, Bytes: {result.bytes_sent}")
```

---

## 6. Finding Flow Evidence in Splunk & Canonical Field Schema

GoFlow2 decodes binary NetFlow v9 and IPFIX packets into structured JSON records indexed in Splunk under `index=idx_network_ops` and `sourcetype=netflow:collector`.

### Canonical Collector JSON Field Schema (`snake_case`):
| Field Name | Description | Example Value |
| :--- | :--- | :--- |
| `type` | Decoded protocol type | `"NETFLOW_V9"` or `"IPFIX"` |
| `observation_domain_id` | Exporter Source ID / Observation Domain ID | `101` |
| `sampler_address` | Exporter source IP address | `"127.0.0.1"` |
| `src_addr` | Source IPv4/IPv6 address | `"10.100.1.10"` |
| `dst_addr` | Destination IPv4/IPv6 address | `"10.200.1.20"` |
| `src_port` | Layer 4 source port | `443` |
| `dst_port` | Layer 4 destination port | `52100` |
| `proto` | IP protocol number (`6`=TCP, `17`=UDP) | `6` |
| `bytes` | Octet delta count (`IN_BYTES`) | `8420950` |
| `packets` | Packet delta count (`IN_PKTS`) | `5614` |
| `in_if` / `out_if` | Ingress / Egress SNMP interface index | `10` / `22` |
| `src_as` / `dst_as` | Source / Destination BGP Autonomous System | `65001` / `65002` |

Open Splunk Web (`http://localhost:8800` or `8000`) and search using the canonical `snake_case` fields:

```spl
search index=idx_network_ops sourcetype=netflow:collector
| spath
| search observation_domain_id=101
| table _time src_addr dst_addr src_port dst_port proto bytes packets in_if out_if observation_domain_id
```

For flow volume aggregation:

```spl
search index=idx_network_ops sourcetype=netflow:collector
| spath
| search observation_domain_id=101
| stats count as total_flows sum(bytes) as total_bytes sum(packets) as total_packets by src_addr dst_addr src_port dst_port proto
```

---

## 7. Troubleshooting Pipeline Failures

If evidence does not appear in Splunk, check the specific pipeline stage:

| Symptom | Probable Cause | Action |
| :--- | :--- | :--- |
| `NetSpout send error` | Target IP is not private (RFC 1918) | NetSpout blocks public IPs by default. Use private loopback or set `NETSPOUT_ALLOW_PUBLIC_EXPORT=1`. |
| `No collector evidence` | GoFlow2 container offline or wrong port | Run `python3 deploy/collector/manage_collector.py status`. |
| `Collector decode failure` | Template not yet received | Restart session or set `NETSPOUT_TEMPLATE_REFRESH_POLICY=EVERY_BURST`. |
| `Forwarder failure` | Splunk HEC unreachable | Verify Splunk container is running on port 8888 (`curl -k https://127.0.0.1:8888/services/collector/health`). |
| `Splunk search returns 0` | Mismatched observation domain | Verify `observation_domain_id` in companion manifest matches query filter. |

---

## 8. Stopping and Cleaning the Environment

To stop services:
```bash
python3 deploy/collector/manage_collector.py stop
```

To reset flow files and in-memory buffers:
```bash
python3 deploy/collector/manage_collector.py cleanup
```

To completely tear down containers and volumes:
```bash
python3 deploy/collector/manage_collector.py down
```
