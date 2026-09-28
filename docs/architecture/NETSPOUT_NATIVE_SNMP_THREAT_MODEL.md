# NetSpout Native SNMP Threat Model & Security Architecture

**Author:** Mahamudul Chowdhury (`machowdhury@yahoo.com`)  
**Gate:** 12 (Native SNMP Architecture & Protocol Definition)  
**Scope:** Threat Analysis, Attack Surface Mitigation, Privileged Port Hardening, and Secret Governance

---

## 1. Executive Summary & Security Posture

SNMP over UDP (`RFC 3416` / `RFC 3414`) presents unique network and parser security risks—including `GetBulkRequest` reflection/amplification, unauthenticated trap flooding, ASN.1 BER length-overflow parser vulnerabilities, cleartext community string exposure, and privileged port (`UDP/161`, `UDP/162`) requirements.

NetSpout's Native SNMP security architecture applies **defense-in-depth**:
1. **Default Loopback Isolation (`127.0.0.1`):** All receiver and simulated agent sockets bind strictly to `127.0.0.1` by default, and outbound trap/inform sockets enforce RFC 1918 / loopback destination validation via `transport_safety.py`.
2. **Zero Root Privilege:** Uses unprivileged ports (`1162/udp` for trap/inform receiver, `1161/udp` for simulated agent) and non-root container UIDs with `cap_drop: [ALL]` and `no-new-privileges:true`.
3. **Definite-Length Bounded ASN.1 BER Parser:** Rejects indefinite-length BER (`0x80`), enforces a hard `1,472-byte` packet ceiling, caps recursion depth to `4` levels (`Message -> PDU -> VarBindList -> VarBind`), and limits `GetBulkRequest` `max-repetitions` to `<= 50`.
4. **Non-Production Community & Ephemeral Secrets:** Uses `netspout-lab` as the default lab community string (never `private` or production strings) and prohibits committing SNMPv3 USM secrets to git.

---

## 2. Comprehensive 15-Threat SNMP Security Matrix (Section 36)

| # | Threat | Target Asset | Attack Path | Impact | Mitigation in NetSpout Architecture | Residual Risk |
| :-: | :--- | :--- | :--- | :--- | :--- | :---: |
| **T-01** | **Packet Amplification (`GetBulkRequest` Reflection)** | Simulated SNMP Agent (`:1161/udp`) & Local Network | Attacker sends a small spoofed `GetBulkRequest (0xA5)` with `max-repetitions = 65535` to trigger a massive multi-kilobyte `Response-PDU`. | **High** — Bandwidth exhaustion and UDP reflection DoS. | 1) Bind simulated agent strictly to `127.0.0.1:1161`.<br>2) Clamp `max-repetitions` to hard ceiling `50`.<br>3) Enforce `1,472-byte` response payload cap. | **LOW** |
| **T-02** | **Trap Flooding / UDP DoS** | Trap Receiver (`:1162/udp`), Forwarder, and Host CPU | Scenario misconfiguration or runaway loop emits thousands of UDP traps per second. | **Medium** — Receiver queue saturation and Splunk HEC flooding. | 1) Enforce token-bucket rate limiter (`50 traps/sec` default, `250/sec` max).<br>2) Enforce per-run packet cap (`1,000 packets` default). | **LOW** |
| **T-03** | **Credential Leakage in Repo / Logs** | Git Repository, Run Manifests, UI Logs | Developer commits HEC tokens, community strings, or SNMPv3 passphrases into `catalog/` or `RunManifest`. | **High** — Credential compromise. | 1) Exclude `community`, `auth_key`, `priv_key`, and `hec_token` from `RunManifest` and serialized configs.<br>2) Inject secrets strictly via runtime env vars. | **LOW** |
| **T-04** | **Community String Leakage on Wire** | Network Transit / Packet Captures | SNMPv2c sends community string in cleartext (`OCTET STRING`); using `public` or a real enterprise community string risks accidental reuse. | **Medium** — Cleartext exposure in PCAPs or local LAN. | 1) Mandate clearly synthetic default community `"netspout-lab"`.<br>2) Restrict default transport to `127.0.0.1`. | **LOW** |
| **T-05** | **SNMPv3 Secret / Key Leakage** | USM User Table (`Gate 12E`) | Plaintext passphrases stored in configuration files or container image layers. | **High** — Compromise of SNMPv3 `authPriv` sessions. | 1) Never store passphrases in Dockerfiles or git.<br>2) Perform RFC 3414 Key Localization ($Ku \rightarrow Kul$) in memory from env/secret mounts. | **LOW** |
| **T-06** | **OID Injection** | BER Encoder, `snmptrapd`, & Splunk Forwarder | Malicious or malformed string (e.g., `"1.3.6.1; rm -rf /"` or negative arcs) passed as an OID into varbind builder or CLI. | **High** — Command injection if passed to shell, or encoder crash. | 1) Strictly validate OID regex `^[0-2](\.(0|[1-9][0-9]*))+$` and integer range `0..4294967295` per arc.<br>2) Never invoke shell string interpolation with OIDs. | **LOW** |
| **T-07** | **Malformed ASN.1 BER Payload** | NetSpout BER Decoder (`INFORM` ACK & Agent Request Parser) | Truncated TLV, negative length, indefinite length (`0x80`), or length exceeding remaining buffer (`L > len(buf)`). | **High** — Unhandled exception, infinite loop, or memory over-read. | 1) Pure-Python bounds-checked parser.<br>2) Reject indefinite length (`0x80`).<br>3) Verify `offset + length <= len(packet)` before every slice. | **LOW** |
| **T-08** | **ASN.1 Parser Exploitation (Deep Recursion / Billion Laughs)** | NetSpout BER Decoder & External `snmptrapd` | Deeply nested `SEQUENCE (0x30)` inside `SEQUENCE` (e.g., 1,000 levels deep) designed to trigger Python `RecursionError` or C stack overflow. | **High** — Process crash / DoS. | Enforce strict iterative or depth-bounded parsing: SNMPv2c has a fixed maximum nesting depth of **4** (`Message -> PDU -> VarBindList -> VarBind`). Any depth $> 5$ is immediately rejected. | **LOW** |
| **T-09** | **External Collector / Receiver Compromise** | Containerized `snmptrapd` & Forwarder | Vulnerability in `snmptrapd` or forwarder exploited to gain host access. | **High** — Container breakout or privilege escalation. | 1) Run containers as non-root (`UID 10001`).<br>2) Set `cap_drop: [ALL]` and `security_opt: ["no-new-privileges:true"]`.<br>3) Bind ports to `127.0.0.1` only. | **LOW** |
| **T-10** | **Unauthorized Public Network Export** | External Internet / Production Routers | User enters a public IP (`8.8.8.8` or customer WAN IP) as trap destination, leaking synthetic fault alerts to external networks. | **High** — Unintended external traffic & false production alarms. | Enforce `transport_safety.py` RFC 1918 / loopback allowlist (`DestinationSecurityException`), blocking public, multicast (`224.0.0.0/4`), and broadcast (`255.255.255.255`) IPs by default. | **LOW** |
| **T-11** | **Spoofed Source Identity** | UDP Socket / Network Stack | Raw socket IP header spoofing used to forge device source IPs. | **High** — Requires `CAP_NET_RAW` / root and triggers OS/firewall alarms. | **Never use raw sockets (`SOCK_RAW`).** Always use standard unprivileged `SOCK_DGRAM` UDP sockets; represent simulated node identity via varbinds (`sysName.0`) or companion manifest. | **LOW** |
| **T-12** | **Packet Replay Attacks** | Trap Receiver / Simulated Agent | Captured `TRAPv2`, `INFORM`, or `SET` packet replayed to re-trigger alerts or alter agent state. | **Medium** — Duplicate alerts or state corruption. | 1) Reject all `SetRequest-PDU (0xA3)` messages (`read-only` agent).<br>2) Deduplicate `INFORM` retries by `request-id`.<br>3) Enforce RFC 3414 `150s` timeliness window in Gate 12E SNMPv3. | **LOW** |
| **T-13** | **`INFORM` Retry Storms** | NetSpout Transport & Receiver | Unreachable receiver causes dozens of concurrent `INFORM` senders to retry endlessly, exhausting sockets and threads. | **Medium** — Thread/socket starvation. | 1) Cap `max_retries <= 2` and `timeout_ms <= 2000`.<br>2) Cap concurrent pending `INFORM` requests at `8`.<br>3) Trip circuit-breaker to `RECEIVER_UNAVAILABLE` after 3 consecutive timeouts. | **LOW** |
| **T-14** | **MIB Poisoning** | OID Dictionary / Symbol Resolution | Maliciously crafted `.mib` file uploaded or loaded at runtime overwrites standard OID mappings or exploits SMI parser. | **Medium** — False telemetry interpretation or parser crash. | Use a **precompiled, immutable JSON/Python OID registry** validated by `validate_catalog.py`; disable runtime SMI text compilation in core engine. | **LOW** |
| **T-15** | **Disk & Memory Resource Exhaustion** | Shared Volume (`/traps/traps.json`) & Forwarder Buffer | Continuous trap emission fills disk volume or forwarder RAM when Splunk HEC is down. | **Medium** — Disk full or container OOM. | 1) Bound forwarder in-memory ring buffer (`maxlen = 1000`).<br>2) Enforce 10 MB file rotation (`traps.json` $\rightarrow$ `traps.json.1`) in forwarder, identical to Gate 11D flow rotation. | **LOW** |

---

## 3. Privileged Port & Container Hardening Specification (Section 35)

| Component | Default Bind Address & Port | Container User (`UID:GID`) | Capabilities | Privilege Escalation |
| :--- | :--- | :---: | :---: | :---: |
| **NetSpout Trap/Inform Sender** | Ephemeral local UDP port $\rightarrow$ `127.0.0.1:1162` | Host user (non-root) | Standard user | None |
| **NetSpout Simulated Polling Agent (Gate 12D)** | `127.0.0.1:1161/udp` | Host user (non-root) | Standard user | None |
| **`netspout-snmp-receiver` (`snmptrapd`, Gate 12C)** | `127.0.0.1:1162->1162/udp` | `10001:10001` | `cap_drop: [ALL]` | `no-new-privileges:true` |
| **`netspout-snmp-forwarder` (HEC Forwarder, Gate 12C)** | `127.0.0.1:8084->8084/tcp` | `10001:10001` | `cap_drop: [ALL]` | `no-new-privileges:true` |
