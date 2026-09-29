# NetSpout Gate 13 — Native gNMI Security, Authentication & Threat Model

**Author:** Mahamudul Chowdhury (`machowdhury@yahoo.com`)  
**Gate:** 13 (Native gNMI Security & Threat Model)  
**Date:** 2026-09-29  
**Status:** SPECIFICATION COMPLETE (Zero Runtime Implementation in Gate 13)

---

## 1. Purpose & Security Posture

Native gNMI introduces a bidirectional HTTP/2 gRPC server capable of streaming high-rate telemetry (`Subscribe`) and answering state snapshots (`Capabilities`, `Get`). Unlike fire-and-forget UDP NetFlow or bounded UDP SNMPv2c polling, an unguarded gRPC streaming server can be abused for **resource exhaustion (subscription storms, sub-millisecond `SAMPLE` intervals, wildcard tree dumps), unauthenticated path enumeration, public listener exposure, or credential/certificate leakage**.

This document defines the mandatory security controls, TLS/mTLS and metadata authentication design, network binding policies, and hard subscription safety caps required before any gNMI listener is implemented in Gate 13B.

---

## 2. Network Binding & Public Listener Policy

Consistent with `TransportSafetyPolicy` in [`src/netspout_core/transport_safety.py`](file:///Users/mahamudc/Documents/NetSpout/src/netspout_core/transport_safety.py):
1. **Default Loopback-Only Binding (`127.0.0.1`):**
   - By default, the NetSpout gNMI server MUST bind exclusively to `127.0.0.1` (IPv4 loopback) on an ephemeral port (`0` $\rightarrow$ OS-assigned unprivileged port) or configured loopback port (`57400`).
   - Binding to `0.0.0.0` or `::` is **blocked by default** and permitted only inside an isolated Docker bridge network when `NETSPOUT_ALLOW_RFC1918_GNMI_BIND=1` is explicitly set and the bind IP is validated as loopback or RFC 1918 private space (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`).
2. **Public Internet IP Rejection:**
   - Any attempt to bind a gNMI listener to a public routable IP or initiate a dial-out connection to a non-loopback/non-RFC1918 collector IP is rejected by `TransportSafetyPolicy` with `TransportSafetyViolationError`.
3. **Ephemeral Lifecycle Binding:**
   - During bounded E2E scenario runs, the gNMI server starts only for the duration of the scenario run (`max_stream_duration_sec = 120s` default) and cleanly shuts down and releases its socket upon scenario completion.

---

## 3. TLS, mTLS, Credentials & Insecure Local Lab Mode (Section 37)

Real-world Cisco IOS XR, Arista EOS, and Juniper Junos gNMI deployments use TLS (or mTLS) with gRPC metadata credentials (`username` / `password`), while local developer labs often test with `--insecure` or self-signed ephemeral certificates. NetSpout supports three explicit security modes:

| Security Mode | Transport Encryption | Client Authentication | When Used |
| :--- | :--- | :--- | :--- |
| **Mode 1: `TLS_METADATA_AUTH` (Recommended Realistic Default)** | Ephemeral in-memory self-signed ECDSA P-256 / RSA-2048 server certificate (`SAN: localhost, 127.0.0.1`) generated at runtime or loaded from a git-ignored runtime path | gRPC per-RPC metadata headers `username` and `password` validated via constant-time `hmac.compare_digest` | Realistic collector validation (`gnmic --tls-ca ... -u netspout -p <lab-token>`, `Telegraf`, `pygnmi`). |
| **Mode 2: `MTLS_CLIENT_CERT`** | Server TLS 1.2/1.3 | Mutual TLS (`ssl_client_auth=REQUIRE_AND_VERIFY_CLIENT_CERT`) against an ephemeral lab CA | Enterprise security & zero-trust telemetry collector verification. |
| **Mode 3: `LOCAL_LAB_INSECURE` (Explicit Opt-In for Local Loopback Only)** | Cleartext HTTP/2 (`h2c`) | Optional metadata auth; **permitted ONLY when bound to `127.0.0.1`** | Frictionless local loopback debugging (`gnmic -a 127.0.0.1:<port> --insecure`). Refused if bind address is not `127.0.0.1`. |

### Secret & Certificate Hygiene Rules
- **Zero Committed Private Keys or Passwords:** No `.pem`, `.key`, `.crt`, or hardcoded production passwords may ever be committed to git.
- **In-Memory Ephemeral Cert Generation:** For automated E2E tests (`Gate 13B/13C`), test certificates are generated in a temporary directory (`tempfile.TemporaryDirectory`) with `0600` permissions and destroyed on test teardown.
- **Redacted Logging:** gRPC metadata headers `password`, `authorization`, and `x-api-key` MUST be redacted (`"***REDACTED***"`) in all NetSpout logs, preflight outputs, and Companion Manifests.

---

## 4. Subscription Safety Caps & Resource Exhaustion Controls (Section 39)

To guarantee that no misconfigured or malicious gNMI client can exhaust CPU, memory, or file descriptors in the NetSpout backend, the following hard safety caps are enforced by `GnmiSubscriptionLimiter`:

| Safety Limit Parameter | Default Cap | Hard Maximum | Enforcement Behavior |
| :--- | :--- | :--- | :--- |
| **`max_concurrent_clients`** | `4` | `8` | Rejects additional gRPC connections/streams with `StatusCode.RESOURCE_EXHAUSTED` (`SUBSCRIPTION_LIMIT_EXCEEDED`). |
| **`max_subscriptions_per_client`** | `8` | `16` | Rejects `SubscribeRequest` containing $> 16$ `Subscription` entries with `StatusCode.RESOURCE_EXHAUSTED`. |
| **`max_paths_per_subscription`** | `32` | `64` | Bounds wildcard expansion and `GetRequest.path` count to $\le 64$ resolved leaf/subtree paths per request. |
| **`min_sample_interval_ms`** | `500 ms` (`500,000,000 ns`) | `100 ms` (burst lab floor) | Any `SAMPLE` subscription with `0 < sample_interval < 500,000,000 ns` is rejected with `StatusCode.INVALID_ARGUMENT` (`SAMPLE_INTERVAL_TOO_LOW`). A value of `0` defaults to `5000 ms` (`5s`). |
| **`max_updates_per_second_per_stream`** | `200 updates/sec` | `500 updates/sec` | Token-bucket rate limiter (`rate_limiter.py`) caps outbound `Notification` emission rate per client stream. |
| **`max_grpc_message_size_bytes`** | `1 MiB` (`1,048,576 B`) | `4 MiB` | Applied to both `grpc.max_receive_message_length` and `grpc.max_send_message_length` to prevent oversized protobuf DoS. |
| **`max_simulated_devices_per_run`** | `8` | `16` | Caps the number of virtual device targets multiplexed on the gNMI server per scenario run. |
| **`max_stream_duration_sec`** | `120 s` | `600 s` | Automatically closes idle or runaway `STREAM` subscriptions after the scenario run window expires. |

---

## 5. Comprehensive Threat Matrix (Section 38)

| Threat ID | Threat Vector | Attack / Failure Scenario | Mitigating Control in Gate 13 Architecture | Residual Risk |
| :--- | :--- | :--- | :--- | :--- |
| **T-GNMI-01** | **Public Listener Exposure** | Operator binds gNMI server to `0.0.0.0` on a cloud VM, exposing simulated telemetry to the internet. | `TransportSafetyPolicy` enforces `127.0.0.1` default bind and blocks public IPv4/IPv6 addresses. | Low |
| **T-GNMI-02** | **Unauthenticated gRPC Access** | Local or container peer connects without credentials when auth mode is required. | Server interceptor enforces `TLS_METADATA_AUTH` or `MTLS_CLIENT_CERT` unless `LOCAL_LAB_INSECURE` is explicitly selected on `127.0.0.1`. | Low |
| **T-GNMI-03** | **High-Frequency `SAMPLE` Storm (`sample_interval = 1ns`)** | Client requests `1ns` or `1ms` sampling across all interfaces, pegging CPU at 100%. | `SAMPLE_INTERVAL_TOO_LOW` rejects any non-zero interval below `min_sample_interval_ms` (`500ms`) and enforces token-bucket rate limiting (`200 updates/sec`). | Low |
| **T-GNMI-04** | **Wildcard Path Explosion (`/`)** | Client subscribes to root path `/` or `/*/*/*` across 50 simulated nodes. | `max_paths_per_subscription` (`64`) and `max_simulated_devices_per_run` (`8`) bound root/wildcard expansion; excess paths return `SUBSCRIPTION_LIMIT_EXCEEDED`. | Low |
| **T-GNMI-05** | **Subscription / Connection Flood** | Client opens hundreds of concurrent `Subscribe` streams without closing them. | `max_concurrent_clients` (`8`), `max_subscriptions_per_client` (`16`), and `max_stream_duration_sec` (`120s`) bound active streams. | Low |
| **T-GNMI-06** | **Oversized / Malicious Protobuf Payload** | Client sends a 100 MB crafted `SubscribeRequest` or deeply nested `PathElem` map to crash protobuf parser. | `grpc.max_receive_message_length = 1 MiB`, max `PathElem` depth `16`, max key length `128` chars. | Low |
| **T-GNMI-07** | **Unauthorized State Mutation via `gNMI.Set`** | Client attempts to modify simulated router configuration or inject arbitrary strings into Splunk via `gNMI.Set`. | `gNMI.Set` is unconditionally disabled and returns `StatusCode.UNIMPLEMENTED` (`SET_NOT_SUPPORTED`). | Zero |
| **T-GNMI-08** | **Credential / Certificate Leakage** | Lab passwords or TLS private keys written to git, logs, or Splunk events. | Ephemeral temp-dir cert generation (`0600`), `hmac.compare_digest` verification, and mandatory metadata redaction in logs/manifests. | Low |
| **T-GNMI-09** | **Path Enumeration / Cross-Scenario Leakage** | Client probes arbitrary targets to discover internal host system paths. | NetSpout serves only the in-memory `TelemetryPathRegistry` for the active scenario's virtual nodes; zero host OS files or metrics are ever read. | Zero |
| **T-GNMI-10** | **Splunk Cloud / AppInspect Violation** | Bundling `grpcio` C-extensions or opening listening sockets inside the Splunk App (`netspout/`). | Native gNMI server lives strictly in the Companion Backend / Emulator Service (`Option D`), never inside `netspout/bin/`. | Zero |
