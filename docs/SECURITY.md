# NetSpout — Security & Deployment Profiles

NetSpout provides two distinct, explicitly separated deployment profiles to safeguard production enterprise environments while offering zero-friction local evaluations.

---

## 1. Profiles Overview

| Dimension | `DEMO` (Default for local lab) | `SECURE` / `EXTERNAL` (Production / Enterprise) |
| :--- | :--- | :--- |
| **Intended Target** | Local development, sandbox evaluation, quickstart Docker | Production networks, shared staging labs, remote Splunk Cloud |
| **UI Badge** | `DEMO / LOCAL LAB` (Prominently displayed in TopBar) | `SECURE / EXTERNAL` |
| **Credentials** | Disposable lab credentials accepted (`0000...`, `SplunkPassword123!`) | User-supplied/generated secrets **strictly required** |
| **Fallback Policy** | Allows automatic fallback to demo credentials if unspecified | **Fails fast with error** if demo secrets or empty tokens are passed |
| **Token Logging** | Strictly masked (`0000****0000`) | Strictly masked (`****`); secrets are never logged in cleartext |
| **Network Bind** | Local loopback / container network | Explicit target host/ports with TLS verification options |

---

## 2. Profile Activation

The active deployment profile is configured via the `NETSPOUT_PROFILE` environment variable.

### Activating the Demo Profile (Default)
```bash
export NETSPOUT_PROFILE="demo"
# or simply leave unset: defaults to demo
```

### Activating the Secure / External Profile
```bash
export NETSPOUT_PROFILE="secure"
# or: export NETSPOUT_PROFILE="external"
```

---

## 3. Configuration in Secure Mode

When `NETSPOUT_PROFILE=secure` or `NETSPOUT_PROFILE=external`:

1. **HEC Token Enforcement:**
   - Must be explicitly passed via `NETSPOUT_HEC_TOKEN` or configured in the connection UI.
   - NetSpout **rejects** the disposable demo token (`00000000-0000-0000-0000-000000000000`) with a fatal configuration error.

2. **Splunk Management Password Enforcement:**
   - Must be explicitly passed via `NETSPOUT_SPLUNK_PASSWORD`.
   - NetSpout **rejects** the default password (`SplunkPassword123!`).

3. **Example Secure Launch:**
   ```bash
   export NETSPOUT_PROFILE="secure"
   export NETSPOUT_HEC_URL="https://splunk.corp.internal:8088/services/collector/event"
   export NETSPOUT_HEC_TOKEN="e983fa2b-8a21-419b-a3d8-58319dfa9931"
   export NETSPOUT_SPLUNK_USER="svc_netspout"
   export NETSPOUT_SPLUNK_PASSWORD="SuperSecretCorpPassword2026!"
   export NETSPOUT_HEC_SSL_VERIFY="true"

   docker compose -f docker-compose.prod.yml up -d
   ```

---

## 4. Secret Masking & Redaction

NetSpout enforces strict secret masking across all logs, REST API payloads, UI state, and evidence records:
- Tokens and passwords longer than 8 characters are masked as `prefix****suffix` (e.g. `e983****9931`).
- Tokens 8 characters or fewer are completely obscured as `********`.
- HTTP authorization headers are never persisted into collector evidence ledgers or Splunk dispatch receipts.
