# NetSpout — Product Roadmap (Post-1.0)

This roadmap outlines strategic enhancements planned for future releases of NetSpout following the 1.0.0 General Availability release.

---

## 🗺️ Release Timeline & Focus Areas

### NetSpout 1.1 — Protocol Expansion
- **SNMPv3 USM / VACM Support**:
  - SHA-256 / AES-128 cryptographic authentication and encryption for SNMPv3 Inform and Get operations.
  - User-based Security Model configuration profiles.
- **sFlow v5 Support**:
  - Sampled packet header and flow counter telemetry generation over UDP port 6343.
- **J-Flow (Juniper Flow)**:
  - Junos-native flow record template extensions.

---

### NetSpout 1.2 — Cloud-Native Observability & OTLP
- **Native OTLP Exporter**:
  - Direct OpenTelemetry Protocol export (OTLP/gRPC and OTLP/HTTP) for Splunk Observability Cloud and OpenTelemetry Collector.
  - Streaming metric counters, gauges, and distributed trace spans correlated with network failure events.
- **Kafka & Event Hub Streaming**:
  - Direct pipeline streaming to Apache Kafka topics for enterprise event meshes.

---

### NetSpout 1.3 — Advanced AI Fabrics & Data Center Topologies
- **RoCEv2 & InfiniBand Telemetry Simulation**:
  - PFC (Priority Flow Control) deadlocks and pauses.
  - ECN (Explicit Congestion Notification) marking and microburst modeling in GPU cluster fabrics.
  - High-bandwidth leaf-spine optical monitoring.

---

### NetSpout 1.4 — Automated Remediation & Closed-Loop Validation
- **Closed-Loop Testing Engine**:
  - Automated validation asserting that Splunk SOAR / Ansible playbooks successfully triggered remediation actions during a simulated fault.
  - Pre-incident vs post-remediation health diff assertions.

---

## 💡 Suggesting Features
To suggest features or contribute to the roadmap, open a discussion in [NetSpout GitHub Discussions](https://github.com/machowdhury/NetSpout/discussions).
