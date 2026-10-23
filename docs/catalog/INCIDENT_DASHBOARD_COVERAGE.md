# C6 executable incident dashboard coverage

25 existing incidents, four reused dashboards, 34 recipe IDs retained. No new
scenario, transport, registry or vendor-native claim. The builder reads the
committed descriptors and generates bounded preview events without dispatching;
this establishes output-field provenance, not live data availability.

| Stable scenario ID | Domain / industry | Primary dashboard | Related dashboard | KPI names from producer |
|---|---|---|---|---|
| network_01_campus_link | Network / infrastructure / Cross-industry | discovery-network |  | interface.errors.rate, interface.input.errors, interface.operational.up, network.latency.ms, network.packet_loss.percent |
| network_02_vlan_trunk | Network / infrastructure / Cross-industry | discovery-network |  | network.latency.ms, network.packet_loss.percent, vlan.discard.rate |
| network_03_stp_storm | Network / infrastructure / Cross-industry | discovery-network |  | broadcast.packets.rate, network.latency.ms, network.packet_loss.percent |
| network_04_wan_brownout | Network / infrastructure / Cross-industry | discovery-network |  | network.latency.ms, network.packet_loss.percent, wan.latency.ms |
| network_05_dual_isp | Network / infrastructure / Cross-industry | discovery-network |  | network.latency.ms, network.packet_loss.percent, wan.packet_loss.percent |
| network_06_bgp_flap | Network / infrastructure / Cross-industry | discovery-network |  | bgp.withdrawn.prefixes, network.latency.ms, network.packet_loss.percent |
| network_07_ospf_adjacency | Network / infrastructure / Cross-industry | discovery-network |  | network.latency.ms, network.packet_loss.percent, ospf.adjacency.down |
| network_08_firewall_policy | Security / Cross-industry | discovery-security | discovery-network | firewall.denied.sessions.rate, network.latency.ms, network.packet_loss.percent |
| network_09_ddos_flood | Security / Cross-industry | discovery-security | discovery-network | network.latency.ms, network.packet_loss.percent, security.flood.packets.rate |
| network_10_dns_failure | Cloud / application / Cross-industry | discovery-application | discovery-network | dns.query.failure.percent, network.latency.ms, network.packet_loss.percent |
| network_11_dhcp_exhaustion | Network / infrastructure / Cross-industry | discovery-network |  | dhcp.pool.utilization.percent, network.latency.ms, network.packet_loss.percent |
| network_12_dc_congestion | Network / infrastructure / Cross-industry | discovery-network |  | interface.queue.drops.rate, network.latency.ms, network.packet_loss.percent |
| network_13_mtu_pmtud | Network / infrastructure / Cross-industry | discovery-network |  | network.large_probe.failure.percent, network.latency.ms, network.packet_loss.percent |
| network_14_wireless_outage | Network / infrastructure / Cross-industry | discovery-network |  | network.latency.ms, network.packet_loss.percent, wireless.ap.unreachable |
| network_15_device_resources | Cloud / application / Cross-industry | discovery-application | discovery-network | device.cpu.percent, device.memory.utilization.percent, network.latency.ms, network.packet_loss.percent |
| telco_01_ran_cell | Telecom / Telecommunications | discovery-telecom |  | ran.downlink.bler.percent, ran.prb.utilization.percent, ran.user.throughput.mbps |
| telco_02_registration_auth | Telecom / Telecommunications | discovery-telecom |  | authentication.latency.ms, registration.failure.percent, registration.success.percent |
| telco_03_slice_sla | Telecom / Telecommunications | discovery-telecom |  | slice.latency.ms, slice.packet_loss.percent, slice.throughput.mbps |
| telco_04_ims_volte | Telecom / Telecommunications | discovery-telecom |  | voice.estimated_mos, voice.rtp.jitter.ms, voice.rtp.loss.percent |
| telco_05_mobile_transport | Telecom / Telecommunications | discovery-telecom |  | fronthaul.one_way_latency.ms, fronthaul.packet_loss.percent, fronthaul.queue.utilization.percent |
| telco_06_broadband_cpe | Telecom / Telecommunications | discovery-telecom |  | broadband.active_sessions, broadband.probe.failure.percent, broadband.service.availability.percent |
| telco_07_sdwan_service | Telecom / Telecommunications | discovery-telecom |  | sdwan.application.jitter.ms, sdwan.application.latency.ms, sdwan.application.loss.percent |
| telco_08_roaming_mobility | Telecom / Telecommunications | discovery-telecom |  | mobility.handover.failure.percent, mobility.interruption.ms, mobility.session.drop.percent |
| telco_09_core_user_plane | Telecom / Telecommunications | discovery-telecom |  | upf.data.latency.ms, upf.forwarding.packets_per_second, upf.packet_drop.percent |
| telco_10_cross_layer | Telecom / Telecommunications | discovery-telecom |  | telecom.affected.cohort.percent, telecom.service.availability.percent, telecom.service.latency.ms |

## Telemetry and field prerequisites

Network incidents emit custom `netspout:network:syslog` and
`netspout:network:metric`; telecom emits custom `netspout:telecom:log` and
`netspout:telecom:metric`. These are PulseForge contracts, not authentic equipment
or selected-version TA profiles. No vendor source is inferred from an incident
name. C1 integration statuses are unchanged; research cases are not executable.

Required common structured log fields: netspout_run_id, netspout_scenario_id,
netspout_phase, netspout_device_id, netspout_incident_id, netspout_site_id, severity.
Telecom also requires netspout_service_id, affected_synthetic_subscribers and
evidence_kind. Provenance is `generate()` in `netspout/bin/network_incidents.py`
or `telecom_incidents.py`; recipe field_provenance records each source. `_time`
comes from event.time in the HEC envelope. Metric names/values come from
`generate().metrics`, serialized as HEC metric_name:<name> fields. The metric
index must preserve run/scenario/device/phase dimensions. Local configured indexes
are inputs; nothing assumes default indexes are deployed. Read access is required.

Log-only destinations cannot supply KPI panels. Syslog extraction, SNMP receiver
mapping, forwarding metric conversion and OTLP-to-local-Splunk ingestion are not
established by these dashboards. Remote destinations are not searched. Log data
readiness does not establish metric availability. Empty metrics are unavailable,
never zero. Missing fields are counted per record; extraction failures or search
permission/index errors remain distinct from missing data.

## Investigation and safe filters

Panels show first observation/failure, observed span, observed devices, phase
severity (lower numeric syslog severity is worse), ordered KPI averages and up to
500 supporting raw observations. Observed devices include witnesses/probes;
that count is not a count of damaged devices. Telecom cohort counts use max,
not a sum across duplicate observers. All figures are synthetic. Averages are
per metric/device/phase/one-second bin; phase grouping retains compressed incident
order even when phases share an index timestamp. No expected value substitutes
for missing records. Recovery/VERIFIED_HEALTHY means a simulated producer phase,
not independently verified indexing or real remediation.

Filters: event index, metric index, run UUID, emitted scenario ID, device ID,
log sourcetype and bounded relative window (15m, 1h, 24h, 7d). Free-text search
values use Splunk's `|s` string escaping; fixed recipe scenario/source clauses
restrict each dashboard family. The entity/scenario `*` choice means all matching
values. There is no vendor filter: these streams are custom and have no reliable
vendor dimension. Discovery links preselect the producer scenario ID; dashboard
back-links return to source-scoped discovery. No execution is triggered.

## Evidence limits

[Splunk mstats reference](https://help.splunk.com/en/splunk-cloud-platform/spl-search-reference/9.3.2408/search-commands/mstats)
requires a metric_name predicate for avg(_value); generated KPI panels include it.
[Simple XML reference](https://help.splunk.com/en/splunk-enterprise/create-dashboards-and-reports/simple-xml-dashboards/10.6/simple-xml-reference/simple-xml-reference)
documents string token escaping and token-driven time bounds. These references
support structure, not a live SPL parser or successful installed-app execution.

Dashboard definitions, generated relationships and producer fields can be checked
offline. Required data presence, metric dimension retention, search performance,
rendering, TA extraction and CIM/dashboard-consumer compatibility still require
separately authorized running-Splunk validation. No such validation occurred.
