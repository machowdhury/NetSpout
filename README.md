# NetSpout PulseForge

PulseForge is a Splunk app that generates realistic, **bounded** network, security and infrastructure telemetry so you can test dashboards, detections and investigations without touching production. Pick a scenario, preview it, send it to an authorized Splunk destination, confirm the events were indexed, and open the matching dashboard.

You sign in with your normal **Splunk** login. PulseForge has no accounts of its own.

## What you get
- **372 runnable scenarios** (372 defined): incident packs, NetFlow/IPFIX, replayed recordings, security and operational scenarios. Every defined scenario runs; the table says which telemetry is vendor-native, mixed or modeled, and what has been independently indexed. See [SCENARIOS](docs/SCENARIOS.md).
- **349 sourcetypes from 88 vendors** in the catalog, with the evidence for each kept separate. Catalog presence is not proof it works. See [TELEMETRY_COVERAGE](docs/TELEMETRY_COVERAGE.md).
- **372 Dashboard Studio dashboards**, one per runnable scenario: 372 validated against indexed data (31 of those also visually verified) and 0 implemented but not yet validated against data.
- Delivery through **HEC** (events and metrics), with indexed counts confirmed by an independent Splunk search, not by HEC acknowledgement. Of the 224 scenarios added most recently, 224 were independently indexed in a lab Splunk and 224 have Splunk-parser-validated dashboards; their telemetry is vendor-native, mixed or **modeled** as labeled in [SCENARIOS](docs/SCENARIOS.md).

## Install (two choices)

| | Docker | Splunk Enterprise app |
|---|---|---|
| Best for | Trying it quickly: includes an evaluation Splunk | Adding PulseForge to a Splunk you already run |
| You install | Docker | `netspout.spl` (a versioned release artifact, not stored in Git: [how to get it](docs/RELEASE_ARTIFACTS.md)) from Splunk Web, **plus** the PulseForge engine on a host Splunk can reach |
| Open | `http://localhost:8000` | Apps → NetSpout PulseForge |
| Status | Compose file validated; a one-command clean-checkout run is **not yet repeated** for this release | Verified end to end on Splunk Enterprise 10.2.7 in an isolated Docker lab |

Steps are in **[docs/INSTALL.md](docs/INSTALL.md)**. First run: **[docs/QUICKSTART.md](docs/QUICKSTART.md)**.

A single-package install, where Splunk runs the engine for you, is in development and is **not part of this release**.

**Splunk Cloud** is different: only the dashboards can be installed there, and generation runs in an engine you host. Read [the Cloud guide](docs/guides/04_SPLUNK_CLOUD_GUIDE.md) first. Nothing here is Splunk Cloud certified.

## Supported platforms

| Platform | State |
|---|---|
| Splunk Enterprise 10.2.7 (Docker lab) | Verified |
| Other Splunk Enterprise versions, VM installs | Not tested |
| Docker (Compose v2, `linux/amd64` image) | Supported; see status above |
| Splunk Cloud | Dashboards only; customer-hosted engine; not certified |

## Known limitations
- AppInspect reports failures on the Enterprise package; it is not Splunk-vetted. See [LIMITATIONS](docs/LIMITATIONS.md).
- A HEC or search secret entered in the UI is held by the engine in memory and has to be entered again after the engine restarts.
- Detection content (Enterprise Security, CIM) is not claimed.

## More
[Install](docs/INSTALL.md) · [Quickstart](docs/QUICKSTART.md) · [Scenarios](docs/SCENARIOS.md) · [Telemetry coverage](docs/TELEMETRY_COVERAGE.md) · [Security](docs/SECURITY.md) · [Troubleshooting](docs/TROUBLESHOOTING.md) · [Limitations](docs/LIMITATIONS.md)

PulseForge only sends to destinations you authorize, in bounded runs. Use it with test data and test indexes. Licensed under the terms in [LICENSE](LICENSE).
