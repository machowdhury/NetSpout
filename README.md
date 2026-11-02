# NetSpout PulseForge

PulseForge is a Splunk app that generates realistic, **bounded** network, security and infrastructure telemetry so you can test dashboards, detections and investigations without touching production. Pick a scenario, preview it, send it to an authorized Splunk destination, confirm the events were indexed, and open the matching dashboard.

You sign in with your normal **Splunk** login. PulseForge has no accounts of its own.

## What you get
- **148 runnable scenarios** (372 defined): incident packs, NetFlow/IPFIX, replayed recordings, security and operational scenarios. See [SCENARIOS](docs/SCENARIOS.md).
- **349 sourcetypes from 88 vendors** in the catalog, with the evidence for each kept separate. Catalog presence is not proof it works. See [TELEMETRY_COVERAGE](docs/TELEMETRY_COVERAGE.md).
- **148 Dashboard Studio dashboards**, one per runnable scenario.
- Delivery through **HEC** (events and metrics), with indexed counts confirmed by an independent Splunk search, not by HEC acknowledgement.

## Install (two choices)

| | Docker | Splunk Enterprise app |
|---|---|---|
| Best for | Trying it quickly: includes an evaluation Splunk | Adding PulseForge to a Splunk you already run |
| You install | Docker | One `.spl` file, from Splunk Web |
| Open | `http://localhost:8000` | Apps → NetSpout PulseForge |
| Status | Compose file validated; one-command clean-checkout run **not yet repeated** for this revision | Validated on Splunk Enterprise 10.6.1.1, Linux x86_64 (one host) |

Steps are in **[docs/INSTALL.md](docs/INSTALL.md)**. First run: **[docs/QUICKSTART.md](docs/QUICKSTART.md)**.

**Splunk Cloud** is different: only the dashboards can be installed there, and generation runs in an engine you host. Read [the Cloud guide](docs/guides/04_SPLUNK_CLOUD_GUIDE.md) before planning. Nothing here is Splunk Cloud certified.

## Supported platforms

| Platform | State |
|---|---|
| Splunk Enterprise 10.6.1.1, Linux x86_64 | Validated (single host, Ubuntu 24.04) |
| Other Splunk Enterprise versions, ARM64, Windows | Not tested |
| Docker (Compose v2, `linux/amd64` image) | Supported; see status above |
| Splunk Cloud | Dashboards only; customer-hosted engine; not certified |

## Known limitations
- AppInspect still reports failures on the Enterprise package; it is not Splunk-vetted. Details in [LIMITATIONS](docs/LIMITATIONS.md).
- The Enterprise single package needs Splunk's bundled Python 3.13. gNMI streaming is not validated there.
- A separately entered HEC or search secret is held by the engine in memory and has to be entered again after the engine restarts.
- Detection content (Enterprise Security, CIM) is not claimed.

## More
[Install](docs/INSTALL.md) · [Quickstart](docs/QUICKSTART.md) · [Scenarios](docs/SCENARIOS.md) · [Telemetry coverage](docs/TELEMETRY_COVERAGE.md) · [Security](docs/SECURITY.md) · [Troubleshooting](docs/TROUBLESHOOTING.md) · [Limitations](docs/LIMITATIONS.md) · [Engineering notes](docs/architecture/PULSEFORGE_INSTALL_ARCHITECTURE_DECISION.md)

PulseForge only sends to destinations you authorize, in bounded runs. Use it with test data and test indexes. Licensed under the terms in [LICENSE](LICENSE).
