# NetSpout v1.0.0-rc1 Release Report

**Product**: NetSpout Network Telemetry Laboratory & Splunk Generator  
**Release Type**: Pre-release (Release Candidate 1)  
**Publication Timestamp**: `2026-10-02T21:28:37-04:00`  
**Independent Acceptance Status**: **PENDING**

---

## 1. Release Identity & Artifact Ledger

| Attribute | Certified Value |
| :--- | :--- |
| **Tag** | `v1.0.0-rc1` |
| **Commit SHA** | `a006dde3a4330a0dff0d5c4dd27ff46e127fe843` |
| **Branch** | `main` |
| **GitHub Release URL** | [https://github.com/machowdhury/NetSpout/releases/tag/v1.0.0-rc1](https://github.com/machowdhury/NetSpout/releases/tag/v1.0.0-rc1) |
| **Attached Artifact** | `netspout.spl` |
| **Artifact Size** | `1,786,138 bytes` (1.70 MB) |
| **Artifact SHA-256** | `c0e9e02fe6433cac455d6a6467c44d7f6ff367933f04edb99e867a81a4a27a72` |
| **Build Command** | `python3 scripts/build_splunk_package.py` |
| **Build Timestamp** | `2026-10-02T20:25:45-04:00` |

---

## 2. Release Verification Results

Prior to tagging and publication, bounded release verification was performed against the clean-room environment:

1. **Clean Docker Startup**: Standalone container (`splunk-netspout-standalone`) and companion services booted and reported `HEALTHY` within certified thresholds.
2. **App Isolation Installation**: `netspout.spl` installed into standard Splunk Enterprise 10.2 without external dependencies or prior configuration.
3. **Operational Mode A**: Scenario simulation (`service_provider_cisco`) initialized, executed, and completed cleanly (`run_id: NS-20261003-a7c732cc`).
4. **Operational Mode C (Exact-10)**: 10 events generated, dispatched to HEC, indexed in `idx_network_ops`, and verified via Splunk search (10/10 observed, 0 duplicates).
5. **Operational Mode D (Exact-1)**: 1 precision event generated, dispatched to HEC, indexed in `idx_network_ops`, and verified via Splunk search (1/1 observed, 0 duplicates).
6. **HEC Ingestion & Search Query**: Dual-store routing verified across event (`idx_network_ops`) and metric (`cisco_mdt_metrics`) indexes.
7. **Splunk Configuration Validation (`btool check`)**: `splunk btool check --app=netspout` returned return code `0` with 0 errors and 0 warnings.
8. **Comprehensive Regression Suite**: 484/484 tests passing across unit, functional, and Gate 14B certification suites.

---

## 3. Operational Endpoints

- **NetSpout Fast Simulation Engine UI**: `http://127.0.0.1:8081`
- **Splunk Enterprise Web UI**: `http://127.0.0.1:8000` (Credentials: `admin` / `NetSpout123!`)
- **Splunk HTTP Event Collector (HEC)**: `https://127.0.0.1:8088/services/collector` (Token: `00000000-0000-0000-0000-000000000000`)
- **Splunk REST API**: `https://127.0.0.1:8089`
- **OpenTelemetry HTTP Receiver**: `http://127.0.0.1:4318`
- **Syslog Receiver**: `127.0.0.1:514` (UDP/TCP)

---

## 4. Acceptance Status

- **Internal Gate Certification**: **GATE 14B PASSED**
- **Independent Acceptance Status**: **PENDING** (Ready for independent third-party black-box validation)
- **General Availability (GA)**: **NOT GA** (Release Candidate 1)
