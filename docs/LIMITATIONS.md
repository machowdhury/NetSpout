# NetSpout — Known Limitations & Scope Boundaries

To maintain fidelity and strict engineering honesty, NetSpout explicitly defines what is modeled, what is supported natively, and what is currently outside the release scope.

---

## 1. Telemetry Honesty Principle

NetSpout models realistic network device state without fabricating vendor telemetry contracts.
- **`NATIVE TRANSPORT`**: Real protocol serialization matching industry RFCs and vendor specs transmitted over standard network sockets (gNMI/Protobuf/HTTP2, SNMPv2c BER/UDP, NetFlow v9 / IPFIX binary UDP).
- **`MODELED DEVICE STATE`**: Software simulation of device internal state (CPU, optics, interface counters, BGP states).
- **`UNSUPPORTED_TELEMETRY`**: When a requested vendor object has no standard public OpenConfig or YANG equivalent, NetSpout explicitly declares it unsupported rather than synthesizing fake paths.

---

## 2. Unsupported Telemetry Scope (By Design)

### Cisco ACI APIC DME Managed Objects
- **Status:** Explicitly classified as `UNSUPPORTED_TELEMETRY`.
- **Rationale:** Cisco ACI uses proprietary object-model endpoints (Management Information Tree - MIT) exposed via APIC REST API / WebSockets (`uni/tn-*`, `sys/eqpt/...`). It does not expose standard OpenConfig gNMI schemas. NetSpout refuses to invent counterfeit OpenConfig paths for ACI DME MOs.

### Protocols Deferred from v1.0 Release
The following protocols are intentionally not included in the 1.0 release:
1. **NETCONF / RESTCONF**: Configuration protocols. NetSpout is a telemetry and observation generator, not a configuration manager.
2. **SNMPv3 (USM / VACM)**: NetSpout currently implements standard SNMPv2c Community-based transport. Encrypted SNMPv3 is planned for future releases.
3. **OpenTelemetry Protocol (OTLP)**: Native gRPC/HTTP OTLP exporter is planned for Wave 3.
4. **sFlow / J-Flow**: Flow generation currently focuses on standard NetFlow v9 (RFC 3954) and IPFIX (RFC 7011).

---

## 3. Network & Security Boundaries

1. **Loopback Only by Default:** All native listeners and simulated device ports bind exclusively to `127.0.0.1` to prevent unauthorized network exposure.
2. **Read-Only / State Simulation Only:** gNMI `SetRequest` and SNMP `SetRequest` modifications from external collectors are disabled or rejected with access violations. NetSpout is designed to test observability, not act as a live programmable router.
3. **Ephemeral Ports:** When running tests or simulations in multi-tenant environments, dynamic ephemeral ports are allocated to prevent TCP/UDP port collision.

---

## 4. Performance & Scalability Boundaries

- **Single Host Rate Guardrails:** Rate limiters bound packet emission (e.g. max 250 pps for SNMP, max 1000 pps for flow) to avoid exhausting local socket buffers or overwhelming local Splunk test instances.
- **HEC Batching:** Ingestion batches are capped at 100 records per HTTP request to ensure minimal latency and predictable heap usage.
