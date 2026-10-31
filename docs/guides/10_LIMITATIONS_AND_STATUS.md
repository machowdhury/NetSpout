# 10 Limitations and status

Statuses are separate: **IMPLEMENTED** (code exists), **TESTED** (automated tests), **INDEXED** (events or metrics found by an independent Splunk search), **INTEROP** (verified against an independent third-party tool), **RELEASE** (installed from the built package and exercised end to end). Evidence paths are under `docs/verification/`.

| Capability | Implemented | Tested | Indexed | Interop | Release (installed package) |
|---|---|---|---|---|---|
| Native generators (159 of 349 sourcetypes) | yes | yes | 137 sourcetypes indexed (evidence-derived) | n/a | partly (packs through the gateway) |
| Continuous replay (10 recordings, 33 packs) | yes | yes (unit, API, 41+ live checks) | yes | n/a | yes (installed-app run, 12/12) |
| Scenarios (362 definitions, 138 runnable) | yes | yes | 76 scenarios indexed | n/a | sampled (replay, native pack, incident pack) |
| Dashboards (133) | yes | yes | data-validated 133 | n/a | opened in Splunk Web from the real app (2 checked in the installed app) |
| SNMPv2c | yes | yes (75) | yes | Net-SNMP tools | not exercised through the app UI |
| gNMI / OpenConfig + vendor-native paths | yes | yes (27 + more) | yes (events and mstats) | gnmic 0.49.0 | not exercised through the app UI |
| NetFlow v9 / IPFIX | yes | yes | yes | GoFlow2 2.2.5, tshark 4.6.9 | not exercised through the app UI |
| sFlow, SNMPv3, gRPC dial-out MDT, J-Flow-specific | **no** | - | - | - | - |
| Detections | stored for one story only | - | - | - | **not verified** |
| TA parsing | Windows, Sysmon | yes | yes | those two add-ons | - |
| CIM | **no** | - | - | - | - |
| Docker Splunk install | yes | yes | yes | - | **yes** (`docs/verification/evidence/installed_app/`) |
| Splunk Enterprise on a VM | packaging only | - | - | - | **not run** |
| Splunk Cloud | Cloud edition built | AppInspect clean | - | - | **USER VALIDATION PENDING** |

## Known limitations
- The engine is a separate service; it is not packaged inside the app and is not deployable inside Splunk Cloud.
- 5 unified scenarios (SEC-P9 flow-based) need the repository's GoFlow2 collector and forwarder; not run here.
- Recorded replay: year-less syslog timestamps assume a leap year; microsecond precision; mixed-format logs (Ollama) excluded; independent recordings are time-aligned only.
- Original 100 financial and 100 telecom libraries were not supplied and are not integrated.
- 30+ scenarios have no industry mapping; the UI says so instead of inventing one.
- `vendors.json` Splunkbase IDs for seven vendors resolve to unrelated apps (netskope's verified replacement is 3808); not changed because a contract test pins them.
- Dashboard Studio cannot load IBM Plex Mono; markdown link contrast is Splunk's.
