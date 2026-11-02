# Security

## Who signs in and who may act
PulseForge uses **Splunk** for sign-in, sessions and password rules. It has no login of its own and stores no user accounts. Every request from the app passes through a Splunk REST handler that checks the Splunk session and then a capability:

| Capability | Allows |
|---|---|
| `netspout_view` | Read-only use (default: the `user` role) |
| `netspout_admin` | Start and stop runs, change settings (default: `admin`, `sc_admin`, `power`) |

Any error while checking is a refusal. After a role change, access can take about 30 seconds to update.

## The engine is not a second front door
- **Splunk Enterprise package:** Splunk starts the engine. It listens only on a private Unix socket (owner-only permissions), not on a TCP port. Requests need an internal key that the Splunk handler adds; requests to the engine without it, including WebSocket requests, are refused. The key is service-to-service protection, not user authentication. Anyone who can run commands as the Splunk operating-system user could read it, which is the same trust level as Splunk itself.
- **Docker:** the engine runs inside the container and is not published. Published ports are bound to `127.0.0.1`.
- You never need port 8081.

## Credentials
- Your Splunk login belongs to Splunk. Do not reuse a production password for the evaluation Docker environment.
- HEC tokens and search credentials you enter for PulseForge are optional integration settings, separate from your Splunk login. They are held by the engine in memory, never written to its settings files or logs, and never returned by the API. Enter them again after the engine restarts. In Docker they come from `.env`.
- Docker: you choose the initial `admin` password in `.env` (git-ignored). Change it after first login ([INSTALL](INSTALL.md#a-docker)).
- No credential is shipped in the packages or this repository.

## Ports (Docker defaults, all on `127.0.0.1`)
Splunk Web 8000, HEC 8088, syslog 514, OTLP 4317/4318, collector metrics 8889 and 13133, flow collectors 2055 and 4739, 8080. The engine (8081) and Splunk management (8089) are not published.

## What is not covered
- The Enterprise package has not passed Splunk AppInspect; it is not vetted for Splunk Cloud.
- Parameterized GET endpoints, log contents and WebSocket frames were not exhaustively scanned for secrets; the parameterless GET endpoints were.
- No third-party penetration test has been done. Dependencies bundled in the package were checked against known-vulnerability data on the build date, with none found.

## Reporting
Please report a vulnerability privately: on GitHub, *Security → Report a vulnerability* for this repository. If that option is not available to you, open an issue asking for a private contact and include no details.
