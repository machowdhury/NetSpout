# Security

## Who signs in and who may act
PulseForge uses **Splunk** for sign-in, sessions and password rules. It has no login of its own and stores no user accounts. Requests from the app pass through a Splunk REST handler that checks the Splunk session and the user's roles:

| Roles | Allows |
|---|---|
| `admin`, `sc_admin`, `power` | Start and stop runs, change settings |
| any other role | Read-only |

A failed or missing check is a refusal.

## The engine
In both install choices the engine is a separate process that the Splunk handler calls. By default it listens on `127.0.0.1:8081`. Keep it on loopback or a firewalled interface, and use PulseForge through Splunk Web. The engine API has no separate user login, so anyone who can reach its port can use it: do not expose it.

## Credentials
- Your Splunk login belongs to Splunk. Do not reuse a production password for the evaluation Docker environment.
- HEC tokens and search credentials are optional integration settings, separate from your Splunk login. The engine takes them from its environment or from the Connection Center, holds them in memory, and does not write them to its settings files or return them from the API. Enter them again after the engine restarts.
- Docker: you choose the initial `admin` password in `.env` (git-ignored). Change it after first login ([INSTALL](INSTALL.md#a-docker)).
- No credential is shipped in the packages or this repository.

## Ports (Docker defaults, all on `127.0.0.1`)
Splunk Web 8000, HEC 8088, Splunk management 8089, engine 8081, syslog 514, OTLP 4317/4318, collector metrics 8889 and 13133, flow collectors 2055 and 4739, 8080.

## What is not covered
- The Enterprise package has not passed Splunk AppInspect and is not vetted for Splunk Cloud.
- No third-party penetration test has been done.

## Reporting
Please report a vulnerability privately: on GitHub, *Security → Report a vulnerability* for this repository. If that option is not available to you, open an issue asking for a private contact and include no details.
