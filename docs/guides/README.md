# PulseForge documentation

| Guide | Audience | Content |
|---|---|---|
| [01 Product overview](01_PRODUCT_OVERVIEW.md) | everyone | What PulseForge is, capabilities, boundaries, honesty rules |
| [02 Architecture and deployment](02_ARCHITECTURE_AND_DEPLOYMENT.md) | architects, admins | Components, data flow, deployment models (Docker, VM, Splunk Cloud) |
| [03 Installation](03_INSTALLATION.md) | admins | Tested Docker procedure, VM procedure, upgrade, uninstall |
| [04 Splunk Cloud guide](04_SPLUNK_CLOUD_GUIDE.md) | admins (user-run validation) | Cloud edition, AppInspect results, checklist; **validation pending** |
| [05 User guide](05_USER_GUIDE.md) | solution engineers, operators | Command Center, Explorer, replay, verification, dashboards |
| [06 Network telemetry guide](06_NETWORK_TELEMETRY_GUIDE.md) | network engineers | SNMP, gNMI/OpenConfig, NetFlow/IPFIX, metrics: what exists, what is verified |
| [07 Dashboard guide](07_DASHBOARD_GUIDE.md) | engineers | Dashboard families, tabs, tokens, maturity, regeneration |
| [08 Security, TA and CIM guide](08_SECURITY_TA_CIM_GUIDE.md) | security engineers | Detections, analytic stories, TA and CIM status |
| [09 Troubleshooting](09_TROUBLESHOOTING.md) | everyone | Symptoms, causes, fixes |
| [10 Limitations and status](10_LIMITATIONS_AND_STATUS.md) | evaluators | Maturity matrix: implemented / tested / indexed / interoperability / release |
| [11 Live Delivery Monitor and HEC test](11_LIVE_DELIVERY_MONITOR_AND_HEC_TEST.md) | operators | Counter definitions, controls per family, external HEC connection test, engine restart |
| [Sourcetype reference](../reference/SOURCETYPE_REFERENCE.md) | everyone | Generated from the registry; JSON/CSV exports alongside |
| [Scenario reference](../reference/SCENARIO_REFERENCE.md) | everyone | Generated from the deduplicated scenario registry |

Reference documents under `docs/reference/` are generated (`scripts/generate_reference_docs.py`); do not edit them by hand. Evidence behind every claim is under `docs/verification/`.
