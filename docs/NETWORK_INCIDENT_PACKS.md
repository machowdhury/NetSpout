# NetSpout PulseForge Network Incident Packs

Fifteen finite, seedable synthetic incidents. Launch from the Network Incident Packs section of the native Run Console after selecting a named destination. Existing start/stop, authorization, destination snapshots, credentials and run history are reused. The Python producer is selected for these descriptors even when an external binary is present.

## Execution contract

Each JSON-as-YAML descriptor in `netspout/appserver/static/scenarios/scenario_network_*.yml` names a pack and an unsigned 32-bit seed (default 42). Change the descriptor seed for a repeatable alternative, or use `network_incidents.generate(slug, seed, start, run_id, eps)` for offline previews. There is no browser-controlled run ID. Equal seed, start, run ID and EPS reproduce identical events; new server run IDs intentionally create new incident identities. No global random state is changed.

Ten phases run once: BASELINE, WARNING, DEGRADATION, FAILURE, NETWORK_IMPACT, USER_IMPACT, INTERVENTION, RECOVERY, RECONVERGENCE, VERIFIED_HEALTHY. These are synthetic incident/probe assertions, not actual network probes or indexing verification. Timelines are compressed to the selected rate: 40 scheduled positions at 10 EPS span 3.9 seconds; HTTP/receiver delays may make a run longer. Each phase contains primary-device, observer and client logs plus one metric envelope. Logs-only outputs omit the metrics rather than serializing them as logs. All counters are evidence from existing adapters; no indexing success is inferred.

## Topology

Site `campus-east`; client VLAN 110, subnet 10.20.110.0/24, gateway 10.20.110.1. Internal addresses are synthetic RFC1918; WAN peers and application/attack sources use documentation address ranges. No telemetry is sent to these modeled device addresses; delivery goes only to the selected destination.

| Device | Address | Role | Primary interface |
|---|---|---|---|
| core01 | 10.20.0.11 | core_switch | TenGigabitEthernet1/0/1 |
| core02 | 10.20.0.12 | core_switch | TenGigabitEthernet1/0/1 |
| dist01 | 10.20.0.21 | distribution_switch | TenGigabitEthernet1/1/1 |
| access01 | 10.20.0.31 | access_switch | GigabitEthernet1/0/24 |
| edge01 | 10.20.0.1 | firewall_router | GigabitEthernet0/0 |
| dns01 | 10.20.0.53 | dns_resolver | eth0 |
| dhcp01 | 10.20.0.67 | dhcp_server | eth0 |
| wlc01 | 10.20.0.41 | wireless_controller | GigabitEthernet0 |
| ap01 | 10.20.0.42 | access_point | GigabitEthernet0 |
| leaf01 | 10.20.0.51 | datacenter_leaf | Ethernet1/1 |
| client01 | 10.20.110.10 | client | eth0 |
| wifi01 | 10.20.110.30 | wireless_client | wlan0 |
| isp_a | 192.0.2.1 | synthetic_isp_router | Ethernet0 |
| isp_b | 192.0.2.5 | synthetic_isp_router | Ethernet0 |

Links:
- `core01:TenGigabitEthernet1/0/1` ↔ `dist01:TenGigabitEthernet1/1/1`
- `core02:TenGigabitEthernet1/0/1` ↔ `dist01:TenGigabitEthernet1/1/2`
- `dist01:GigabitEthernet1/0/1` ↔ `access01:GigabitEthernet1/0/24`
- `core01:TenGigabitEthernet1/0/2` ↔ `edge01:GigabitEthernet0/1`
- `core02:TenGigabitEthernet1/0/2` ↔ `leaf01:Ethernet1/1`
- `access01:GigabitEthernet1/0/10` ↔ `client01:eth0`
- `access01:GigabitEthernet1/0/11` ↔ `ap01:GigabitEthernet0`
- `core01:GigabitEthernet1/0/2` ↔ `dns01:eth0`
- `core02:GigabitEthernet1/0/2` ↔ `dhcp01:eth0`
- `dist01:GigabitEthernet1/0/2` ↔ `wlc01:GigabitEthernet0`
- `ap01:radio0` ↔ `wifi01:wlan0`
- `edge01:GigabitEthernet0/0` ↔ `isp_a:Ethernet0`
- `edge01:GigabitEthernet0/2` ↔ `isp_b:Ethernet0`

## Protocol and evidence limits

- HEC: 30 logs and 10 metric envelopes, preserving event time, host, source, custom sourcetype and searchable correlation fields. Uses saved log/metric indexes. Provision an event index and a metric index before running. Collector ACCEPTED is separate from independent search VERIFIED.
- OTLP HTTP/JSON: saved logs, metrics or both. Thirty log records and 30 gauge points (50 for campus link, including input errors and operational state; 40 for device resources, including memory utilization). Resource/data-point attributes preserve correlation. Existing partial-success handling counts rejected points separately. No native Splunk indexing verification.
- Syslog: 30 single-line logs using the selected RFC3164/RFC5424 and UDP/TCP adapter. Correlation is in the owned synthetic message. Local socket completion is not receiver or indexing proof; native indexing verification remains unsupported.
- SNMP: 30 existing synthetic v2c UDP trap/inform messages. Existing varbinds carry run/scenario/device/phase and original text; incident/site are inside that text. Preflight BER-encodes all messages against the existing size limit. Traps expose local sends; only matching inform responses are acknowledgements. No vendor MIB or indexing claim.
- Splunk-managed forwarding: 30 atomic spool envelopes preserving timestamps, metadata and all incident fields; forwarding group and index stay server-owned. Publication is not ingestion or downstream forwarding proof. Existing bounded spool/input rules apply.
- Missing/disabled destinations remain blocked by Destination Manager. Unsupported protocols or OTLP signals are rejected. No new transport, retries, destinations or credential settings are introduced.
- These are illustrative vendor-style event patterns, not device-specific command emulation or certified vendor TA profiles. Dedicated `netspout:network:syslog` and `netspout:network:metric` sourcetypes avoid implying Cisco/Palo Alto parsing fidelity. Metrics are scenario gauges, not live measurements.

## Incident library and independent SPL

Replace `RUN_UUID`, indexes and earliest/latest with the server-owned run record. Search success alone is not proof: require the exact selected run ID and expected scenario/device events inside its time bounds. The examples below use HEC indexed fields. For forwarding use `spath` on the envelope; for a syslog receiver validate its extraction separately. Metrics require a metrics index and `mstats`, not an event-count claim.

### Campus link failure/recovery

ID: `01_campus_link`. Primary device: `dist01`. Gauge: `interface.errors.rate`.

Fault: LINK-3-UPDOWN: Interface TenGigabitEthernet1/1/1 changed state to down Impact: OSPF-5-ADJCHG: Neighbor 10.20.0.11 on uplink changed FULL to DOWN; alternate core02 path active Intervention: Operator replaced damaged uplink optic and cleared error counters Recovery: LINK-5-UPDOWN: Interface TenGigabitEthernet1/1/1 changed state to up OSPF-5-ADJCHG: Neighbor 10.20.0.11 changed LOADING to FULL; primary path restored

Representative failure event (dummy run identity):

```text
dist01 %LINK-3-UPDOWN: Interface TenGigabitEthernet1/1/1 changed state to down netspout_incident_id=efc6ac89-537c-5819-90fb-01ec1f8cdc0e netspout_scenario_id=01_campus_link netspout_site_id=campus-east netspout_device_id=dist01 netspout_phase=FAILURE device_ip=10.20.0.21 device_role=distribution_switch interface=TenGigabitEthernet1/1/1 vlan=110 subnet=10.20.110.0/24 netspout_run_id=00000000-0000-0000-0000-000000000000
```

```spl
index=idx_network_ops netspout_run_id::"RUN_UUID" netspout_scenario_id::"01_campus_link" earliest=RUN_START latest=RUN_END
| sort 0 _time sequence
| table _time host netspout_incident_id netspout_site_id netspout_phase severity interface _raw
```

```spl
| mstats avg(interface.errors.rate) WHERE index=idx_performance_metrics netspout_run_id="RUN_UUID" netspout_scenario_id="01_campus_link" earliest=RUN_START latest=RUN_END BY netspout_phase netspout_device_id span=1s
```

### VLAN/trunk misconfiguration

ID: `02_vlan_trunk`. Primary device: `access01`. Gauge: `vlan.discard.rate`.

Fault: SW_VLAN-3-VLAN_DENIED: VLAN 110 traffic discarded on GigabitEthernet1/0/24 Impact: Connected SVI remains up but VLAN 110 client frames cannot reach gateway 10.20.110.1 Intervention: Operator restored VLAN 110 to allowed VLAN list on both trunk endpoints Recovery: SW_VLAN-5-VLAN_ALLOWED: VLAN 110 forwarding enabled on trunk MAC learning resumed for VLAN 110; gateway ARP and bidirectional probes succeed

Representative failure event (dummy run identity):

```text
access01 %SW_VLAN-3-VLAN_DENIED: VLAN 110 traffic discarded on GigabitEthernet1/0/24 netspout_incident_id=2c5ec07b-66da-56e6-ba2b-7ab33786d59b netspout_scenario_id=02_vlan_trunk netspout_site_id=campus-east netspout_device_id=access01 netspout_phase=FAILURE device_ip=10.20.0.31 device_role=access_switch interface=GigabitEthernet1/0/24 vlan=110 subnet=10.20.110.0/24 netspout_run_id=00000000-0000-0000-0000-000000000000
```

```spl
index=idx_network_ops netspout_run_id::"RUN_UUID" netspout_scenario_id::"02_vlan_trunk" earliest=RUN_START latest=RUN_END
| sort 0 _time sequence
| table _time host netspout_incident_id netspout_site_id netspout_phase severity interface _raw
```

```spl
| mstats avg(vlan.discard.rate) WHERE index=idx_performance_metrics netspout_run_id="RUN_UUID" netspout_scenario_id="02_vlan_trunk" earliest=RUN_START latest=RUN_END BY netspout_phase netspout_device_id span=1s
```

### STP loop/broadcast storm

ID: `03_stp_storm`. Primary device: `access01`. Gauge: `broadcast.packets.rate`.

Fault: STORM_CONTROL-3-FILTERED: Broadcast threshold exceeded in VLAN 110 Impact: MACFLAP-4-NOTIF: Client MAC moving between GigabitEthernet1/0/2 and GigabitEthernet1/0/3 Intervention: Operator shut down looped port GigabitEthernet1/0/3 and removed patch cable Recovery: SPANTREE-5-PORTSTATE: Loop isolated; root port stable toward dist01 Spanning tree converged; topology-change counter stable and broadcast rate normal

Representative failure event (dummy run identity):

```text
access01 %STORM_CONTROL-3-FILTERED: Broadcast threshold exceeded in VLAN 110 netspout_incident_id=3fa8d33f-18ae-5ab4-b78e-639f20c12ada netspout_scenario_id=03_stp_storm netspout_site_id=campus-east netspout_device_id=access01 netspout_phase=FAILURE device_ip=10.20.0.31 device_role=access_switch interface=GigabitEthernet1/0/24 vlan=110 subnet=10.20.110.0/24 netspout_run_id=00000000-0000-0000-0000-000000000000
```

```spl
index=idx_network_ops netspout_run_id::"RUN_UUID" netspout_scenario_id::"03_stp_storm" earliest=RUN_START latest=RUN_END
| sort 0 _time sequence
| table _time host netspout_incident_id netspout_site_id netspout_phase severity interface _raw
```

```spl
| mstats avg(broadcast.packets.rate) WHERE index=idx_performance_metrics netspout_run_id="RUN_UUID" netspout_scenario_id="03_stp_storm" earliest=RUN_START latest=RUN_END BY netspout_phase netspout_device_id span=1s
```

### WAN latency/jitter/packet-loss brownout

ID: `04_wan_brownout`. Primary device: `edge01`. Gauge: `wan.latency.ms`.

Fault: IP_SLA-3-TIMEOUT: WAN path loss 24 percent and jitter 85 ms; carrier remains up Impact: Application path to 198.51.100.80 impaired; routing adjacency remains established Intervention: Operator applied temporary traffic steering to ISP-B and opened carrier incident Recovery: IP_SLA-5-RECOVERY: ISP-A latency and packet loss returning to baseline Carrier repair confirmed; policy restored after stable probe hold-down

Representative failure event (dummy run identity):

```text
edge01 %IP_SLA-3-TIMEOUT: WAN path loss 24 percent and jitter 85 ms; carrier remains up netspout_incident_id=b15e772f-5702-59c6-8ad5-983e275fcab9 netspout_scenario_id=04_wan_brownout netspout_site_id=campus-east netspout_device_id=edge01 netspout_phase=FAILURE device_ip=10.20.0.1 device_role=firewall_router interface=GigabitEthernet0/0 vlan=110 subnet=10.20.110.0/24 netspout_run_id=00000000-0000-0000-0000-000000000000
```

```spl
index=idx_network_ops netspout_run_id::"RUN_UUID" netspout_scenario_id::"04_wan_brownout" earliest=RUN_START latest=RUN_END
| sort 0 _time sequence
| table _time host netspout_incident_id netspout_site_id netspout_phase severity interface _raw
```

```spl
| mstats avg(wan.latency.ms) WHERE index=idx_performance_metrics netspout_run_id="RUN_UUID" netspout_scenario_id="04_wan_brownout" earliest=RUN_START latest=RUN_END BY netspout_phase netspout_device_id span=1s
```

### Dual-ISP failover/recovery

ID: `05_dual_isp`. Primary device: `edge01`. Gauge: `wan.packet_loss.percent`.

Fault: TRACK-3-STATE: ISP-A tracked route down; primary default route removed Impact: ROUTING-5-FAILOVER: Default route installed via ISP-B 192.0.2.5; sessions re-establish Intervention: Operator confirmed backup egress and requested ISP-A circuit repair Recovery: TRACK-5-STATE: ISP-A next-hop reachable; restoration timer started Primary default restored after hold-down; ISP-B remains standby

Representative failure event (dummy run identity):

```text
edge01 %TRACK-3-STATE: ISP-A tracked route down; primary default route removed netspout_incident_id=c7c39fe9-4eb1-5c56-98a4-37c6a9f06a3c netspout_scenario_id=05_dual_isp netspout_site_id=campus-east netspout_device_id=edge01 netspout_phase=FAILURE device_ip=10.20.0.1 device_role=firewall_router interface=GigabitEthernet0/0 vlan=110 subnet=10.20.110.0/24 netspout_run_id=00000000-0000-0000-0000-000000000000
```

```spl
index=idx_network_ops netspout_run_id::"RUN_UUID" netspout_scenario_id::"05_dual_isp" earliest=RUN_START latest=RUN_END
| sort 0 _time sequence
| table _time host netspout_incident_id netspout_site_id netspout_phase severity interface _raw
```

```spl
| mstats avg(wan.packet_loss.percent) WHERE index=idx_performance_metrics netspout_run_id="RUN_UUID" netspout_scenario_id="05_dual_isp" earliest=RUN_START latest=RUN_END BY netspout_phase netspout_device_id span=1s
```

### BGP neighbor flap/route withdrawal

ID: `06_bgp_flap`. Primary device: `edge01`. Gauge: `bgp.withdrawn.prefixes`.

Fault: BGP-3-NOTIFICATION: Hold timer expired; peer 192.0.2.1 Established to Idle Impact: BGP-4-WITHDRAW: 240 prefixes withdrawn; alternate peer 192.0.2.5 AS 64502 selected Intervention: Operator corrected unstable WAN optics and reset only affected BGP neighbor Recovery: BGP-5-ADJCHANGE: Peer 192.0.2.1 OpenConfirm to Established BGP best-path selection complete; 240 prefixes restored without repeated flaps

Representative failure event (dummy run identity):

```text
edge01 %BGP-3-NOTIFICATION: Hold timer expired; peer 192.0.2.1 Established to Idle netspout_incident_id=42caf8a2-0825-550f-b381-f36b1b1aaa4d netspout_scenario_id=06_bgp_flap netspout_site_id=campus-east netspout_device_id=edge01 netspout_phase=FAILURE device_ip=10.20.0.1 device_role=firewall_router interface=GigabitEthernet0/0 vlan=110 subnet=10.20.110.0/24 netspout_run_id=00000000-0000-0000-0000-000000000000
```

```spl
index=idx_network_ops netspout_run_id::"RUN_UUID" netspout_scenario_id::"06_bgp_flap" earliest=RUN_START latest=RUN_END
| sort 0 _time sequence
| table _time host netspout_incident_id netspout_site_id netspout_phase severity interface _raw
```

```spl
| mstats avg(bgp.withdrawn.prefixes) WHERE index=idx_performance_metrics netspout_run_id="RUN_UUID" netspout_scenario_id="06_bgp_flap" earliest=RUN_START latest=RUN_END BY netspout_phase netspout_device_id span=1s
```

### OSPF adjacency failure/reconvergence

ID: `07_ospf_adjacency`. Primary device: `dist01`. Gauge: `ospf.adjacency.down`.

Fault: OSPF-3-ADJCHG: Neighbor 10.20.0.11 FULL to DOWN; dead timer expired Impact: OSPF-4-SPF: Topology LSA updated; VLAN 110 routed through core02 with higher cost Intervention: Operator corrected mismatched OSPF hello/dead timers to 10/40 seconds Recovery: OSPF-5-ADJCHG: Neighbor 10.20.0.11 EXSTART to EXCHANGE OSPF-5-ADJCHG: Neighbor FULL; LSDB synchronized and shortest path restored

Representative failure event (dummy run identity):

```text
dist01 %OSPF-3-ADJCHG: Neighbor 10.20.0.11 FULL to DOWN; dead timer expired netspout_incident_id=35e3145f-7ab6-5eff-88e9-f8f9c100b4c5 netspout_scenario_id=07_ospf_adjacency netspout_site_id=campus-east netspout_device_id=dist01 netspout_phase=FAILURE device_ip=10.20.0.21 device_role=distribution_switch interface=TenGigabitEthernet1/1/1 vlan=110 subnet=10.20.110.0/24 netspout_run_id=00000000-0000-0000-0000-000000000000
```

```spl
index=idx_network_ops netspout_run_id::"RUN_UUID" netspout_scenario_id::"07_ospf_adjacency" earliest=RUN_START latest=RUN_END
| sort 0 _time sequence
| table _time host netspout_incident_id netspout_site_id netspout_phase severity interface _raw
```

```spl
| mstats avg(ospf.adjacency.down) WHERE index=idx_performance_metrics netspout_run_id="RUN_UUID" netspout_scenario_id="07_ospf_adjacency" earliest=RUN_START latest=RUN_END BY netspout_phase netspout_device_id span=1s
```

### Firewall policy misconfiguration

ID: `08_firewall_policy`. Primary device: `edge01`. Gauge: `firewall.denied.sessions.rate`.

Fault: POLICY-3-DENY: Rule block-web denies tcp 10.20.110.10 to 198.51.100.80:443 Impact: TRAFFIC-4-DROP: Healthy routed path but new application sessions denied by policy Intervention: Operator reverted erroneous rule block-web to previous approved policy revision Recovery: POLICY-5-PERMIT: Approved outbound HTTPS policy restored New sessions established; synthetic HTTPS transaction and return traffic verified

Representative failure event (dummy run identity):

```text
edge01 %POLICY-3-DENY: Rule block-web denies tcp 10.20.110.10 to 198.51.100.80:443 netspout_incident_id=8fb10ea6-9bf5-56cc-a6cf-243fafbb4691 netspout_scenario_id=08_firewall_policy netspout_site_id=campus-east netspout_device_id=edge01 netspout_phase=FAILURE device_ip=10.20.0.1 device_role=firewall_router interface=GigabitEthernet0/0 vlan=110 subnet=10.20.110.0/24 netspout_run_id=00000000-0000-0000-0000-000000000000
```

```spl
index=idx_network_ops netspout_run_id::"RUN_UUID" netspout_scenario_id::"08_firewall_policy" earliest=RUN_START latest=RUN_END
| sort 0 _time sequence
| table _time host netspout_incident_id netspout_site_id netspout_phase severity interface _raw
```

```spl
| mstats avg(firewall.denied.sessions.rate) WHERE index=idx_performance_metrics netspout_run_id="RUN_UUID" netspout_scenario_id="08_firewall_policy" earliest=RUN_START latest=RUN_END BY netspout_phase netspout_device_id span=1s
```

### DDoS/traffic flood/mitigation

ID: `09_ddos_flood`. Primary device: `edge01`. Gauge: `security.flood.packets.rate`.

Fault: THREAT-2-FLOOD: SYN flood threshold exceeded; connection table under pressure Impact: TRAFFIC-3-DROP: Legitimate VLAN 110 sessions competing with flood traffic Intervention: Operator enabled bounded SYN protection and upstream synthetic source filter Recovery: THREAT-5-MITIGATED: Flood filtered; connection table pressure declining Legitimate transactions stable; mitigation retained pending observation

Representative failure event (dummy run identity):

```text
edge01 %THREAT-2-FLOOD: SYN flood threshold exceeded; connection table under pressure netspout_incident_id=60aa840f-2cca-52a8-b7b2-5eb9ba0e13a7 netspout_scenario_id=09_ddos_flood netspout_site_id=campus-east netspout_device_id=edge01 netspout_phase=FAILURE device_ip=10.20.0.1 device_role=firewall_router interface=GigabitEthernet0/0 vlan=110 subnet=10.20.110.0/24 netspout_run_id=00000000-0000-0000-0000-000000000000
```

```spl
index=idx_network_ops netspout_run_id::"RUN_UUID" netspout_scenario_id::"09_ddos_flood" earliest=RUN_START latest=RUN_END
| sort 0 _time sequence
| table _time host netspout_incident_id netspout_site_id netspout_phase severity interface _raw
```

```spl
| mstats avg(security.flood.packets.rate) WHERE index=idx_performance_metrics netspout_run_id="RUN_UUID" netspout_scenario_id="09_ddos_flood" earliest=RUN_START latest=RUN_END BY netspout_phase netspout_device_id span=1s
```

### DNS resolver failure/recovery

ID: `10_dns_failure`. Primary device: `dns01`. Gauge: `dns.query.failure.percent`.

Fault: DNS-3-SERVFAIL: Resolver cannot answer uncached queries for demo.example Impact: CLIENT-4-RESOLUTION: IP reachability healthy but name-based applications unavailable Intervention: Operator restored upstream resolver route and flushed failed query cache Recovery: DNS-5-ANSWER: Recursive answers restored for demo.example Positive and negative cache probes normal; synthetic client resolution verified

Representative failure event (dummy run identity):

```text
dns01 %DNS-3-SERVFAIL: Resolver cannot answer uncached queries for demo.example netspout_incident_id=717efdb7-310a-554a-92b2-d7d0adf0e789 netspout_scenario_id=10_dns_failure netspout_site_id=campus-east netspout_device_id=dns01 netspout_phase=FAILURE device_ip=10.20.0.53 device_role=dns_resolver interface=eth0 vlan=110 subnet=10.20.110.0/24 netspout_run_id=00000000-0000-0000-0000-000000000000
```

```spl
index=idx_network_ops netspout_run_id::"RUN_UUID" netspout_scenario_id::"10_dns_failure" earliest=RUN_START latest=RUN_END
| sort 0 _time sequence
| table _time host netspout_incident_id netspout_site_id netspout_phase severity interface _raw
```

```spl
| mstats avg(dns.query.failure.percent) WHERE index=idx_performance_metrics netspout_run_id="RUN_UUID" netspout_scenario_id="10_dns_failure" earliest=RUN_START latest=RUN_END BY netspout_phase netspout_device_id span=1s
```

### DHCP pool exhaustion/recovery

ID: `11_dhcp_exhaustion`. Primary device: `dhcp01`. Gauge: `dhcp.pool.utilization.percent`.

Fault: DHCP-3-POOL_EXHAUSTED: No free address for new VLAN 110 client Impact: CLIENT-4-LEASE: New clients cannot obtain address; existing leased clients unaffected Intervention: Operator reclaimed expired leases and corrected excessive lease duration Recovery: DHCP-5-OFFER: Free leases available; offer 10.20.110.20 to new synthetic client DHCP-5-ACK: Lease completed; gateway and DNS options verified by client

Representative failure event (dummy run identity):

```text
dhcp01 %DHCP-3-POOL_EXHAUSTED: No free address for new VLAN 110 client netspout_incident_id=c4bce44a-6130-5ee8-95c5-8bf5aaec80b7 netspout_scenario_id=11_dhcp_exhaustion netspout_site_id=campus-east netspout_device_id=dhcp01 netspout_phase=FAILURE device_ip=10.20.0.67 device_role=dhcp_server interface=eth0 vlan=110 subnet=10.20.110.0/24 netspout_run_id=00000000-0000-0000-0000-000000000000
```

```spl
index=idx_network_ops netspout_run_id::"RUN_UUID" netspout_scenario_id::"11_dhcp_exhaustion" earliest=RUN_START latest=RUN_END
| sort 0 _time sequence
| table _time host netspout_incident_id netspout_site_id netspout_phase severity interface _raw
```

```spl
| mstats avg(dhcp.pool.utilization.percent) WHERE index=idx_performance_metrics netspout_run_id="RUN_UUID" netspout_scenario_id="11_dhcp_exhaustion" earliest=RUN_START latest=RUN_END BY netspout_phase netspout_device_id span=1s
```

### Data-center congestion/queue drops

ID: `12_dc_congestion`. Primary device: `leaf01`. Gauge: `interface.queue.drops.rate`.

Fault: QOS-3-DROP: Microburst queue overflow; tail drops on Ethernet1/1 Impact: TCP-4-RETRANS: Application transfers to 198.51.100.80 retransmitting; link stays up Intervention: Operator paced bulk transfer and corrected QoS queue allocation Recovery: QOS-5-RECOVERY: Queue occupancy declining and drop rate reduced Application throughput restored; queue and retransmission probes stable

Representative failure event (dummy run identity):

```text
leaf01 %QOS-3-DROP: Microburst queue overflow; tail drops on Ethernet1/1 netspout_incident_id=4dee606f-2c91-5d8e-af74-79f53f5ef1b2 netspout_scenario_id=12_dc_congestion netspout_site_id=campus-east netspout_device_id=leaf01 netspout_phase=FAILURE device_ip=10.20.0.51 device_role=datacenter_leaf interface=Ethernet1/1 vlan=110 subnet=10.20.110.0/24 netspout_run_id=00000000-0000-0000-0000-000000000000
```

```spl
index=idx_network_ops netspout_run_id::"RUN_UUID" netspout_scenario_id::"12_dc_congestion" earliest=RUN_START latest=RUN_END
| sort 0 _time sequence
| table _time host netspout_incident_id netspout_site_id netspout_phase severity interface _raw
```

```spl
| mstats avg(interface.queue.drops.rate) WHERE index=idx_performance_metrics netspout_run_id="RUN_UUID" netspout_scenario_id="12_dc_congestion" earliest=RUN_START latest=RUN_END BY netspout_phase netspout_device_id span=1s
```

### MTU mismatch/PMTUD failure

ID: `13_mtu_pmtud`. Primary device: `edge01`. Gauge: `network.large_probe.failure.percent`.

Fault: IP-3-PMTUD: Path MTU 1400 smaller than sender 1500 and ICMP feedback filtered Impact: TCP-4-STALL: TLS handshake succeeds but large application transfer stalls Intervention: Operator permitted ICMP fragmentation-needed and aligned tunnel MTU/MSS Recovery: IP-5-PMTUD: Sender learned 1400-byte path MTU Large and small synthetic transfers complete; fragmentation-needed feedback confirmed

Representative failure event (dummy run identity):

```text
edge01 %IP-3-PMTUD: Path MTU 1400 smaller than sender 1500 and ICMP feedback filtered netspout_incident_id=bf9d2fa6-7398-58c7-ae00-3585136366cc netspout_scenario_id=13_mtu_pmtud netspout_site_id=campus-east netspout_device_id=edge01 netspout_phase=FAILURE device_ip=10.20.0.1 device_role=firewall_router interface=GigabitEthernet0/0 vlan=110 subnet=10.20.110.0/24 netspout_run_id=00000000-0000-0000-0000-000000000000
```

```spl
index=idx_network_ops netspout_run_id::"RUN_UUID" netspout_scenario_id::"13_mtu_pmtud" earliest=RUN_START latest=RUN_END
| sort 0 _time sequence
| table _time host netspout_incident_id netspout_site_id netspout_phase severity interface _raw
```

```spl
| mstats avg(network.large_probe.failure.percent) WHERE index=idx_performance_metrics netspout_run_id="RUN_UUID" netspout_scenario_id="13_mtu_pmtud" earliest=RUN_START latest=RUN_END BY netspout_phase netspout_device_id span=1s
```

### Wireless controller/AP outage

ID: `14_wireless_outage`. Primary device: `wlc01`. Gauge: `wireless.ap.unreachable`.

Fault: CAPWAP-3-AP_DOWN: AP ap01 lost controller reachability Impact: WLAN-4-CLIENT_LOSS: VLAN 110 wireless clients disconnected; wired clients unaffected Intervention: Operator restored AP switch power/uplink and verified controller reachability Recovery: CAPWAP-5-JOIN: AP ap01 authenticated and rejoined controller wlc01 WLAN-5-CLIENT_JOIN: SSID campus-demo available; client lease and application probe verified

Representative failure event (dummy run identity):

```text
wlc01 %CAPWAP-3-AP_DOWN: AP ap01 lost controller reachability netspout_incident_id=cd87143e-f895-5d6b-9df5-6a19c5e0f154 netspout_scenario_id=14_wireless_outage netspout_site_id=campus-east netspout_device_id=wlc01 netspout_phase=FAILURE device_ip=10.20.0.41 device_role=wireless_controller interface=GigabitEthernet0 vlan=110 subnet=10.20.110.0/24 netspout_run_id=00000000-0000-0000-0000-000000000000
```

```spl
index=idx_network_ops netspout_run_id::"RUN_UUID" netspout_scenario_id::"14_wireless_outage" earliest=RUN_START latest=RUN_END
| sort 0 _time sequence
| table _time host netspout_incident_id netspout_site_id netspout_phase severity interface _raw
```

```spl
| mstats avg(wireless.ap.unreachable) WHERE index=idx_performance_metrics netspout_run_id="RUN_UUID" netspout_scenario_id="14_wireless_outage" earliest=RUN_START latest=RUN_END BY netspout_phase netspout_device_id span=1s
```

### Device CPU/memory exhaustion

ID: `15_device_resources`. Primary device: `core01`. Gauge: `device.cpu.percent`.

Fault: SYS-3-RESOURCE: CPU 99 percent; free memory low and control-plane queue delayed Impact: ROUTING-4-DELAY: Adjacency hellos delayed; management response and client latency degraded Intervention: Operator stopped runaway synthetic process and reduced excessive collection frequency Recovery: SYS-5-RESOURCE: CPU and memory returning to safe operating range Control-plane queues drained; adjacency, management and client probes stable

Representative failure event (dummy run identity):

```text
core01 %SYS-3-RESOURCE: CPU 99 percent; free memory low and control-plane queue delayed netspout_incident_id=9cafed2a-4de4-5242-8f95-5f4fc07f28f8 netspout_scenario_id=15_device_resources netspout_site_id=campus-east netspout_device_id=core01 netspout_phase=FAILURE device_ip=10.20.0.11 device_role=core_switch interface=TenGigabitEthernet1/0/1 vlan=110 subnet=10.20.110.0/24 netspout_run_id=00000000-0000-0000-0000-000000000000
```

```spl
index=idx_network_ops netspout_run_id::"RUN_UUID" netspout_scenario_id::"15_device_resources" earliest=RUN_START latest=RUN_END
| sort 0 _time sequence
| table _time host netspout_incident_id netspout_site_id netspout_phase severity interface _raw
```

```spl
| mstats avg(device.cpu.percent) WHERE index=idx_performance_metrics netspout_run_id="RUN_UUID" netspout_scenario_id="15_device_resources" earliest=RUN_START latest=RUN_END BY netspout_phase netspout_device_id span=1s
```

## C7A correlated incident additions

These six packs use the existing custom network log/metric contracts. Products
are modeled system roles, not vendor-native raw output or TA compatibility.
All interventions and business probes are simulated; no real payment or patient data.

- 16_retail_uplink — Retail branch uplink flap and checkout interruption: proposal 1; UC 5.1.1, 21.11.1. KPI fields: uplink.down, checkout.failure.percent, session.failure.percent.
- 17_hospital_mac_auth — Hospital access MAC instability and login retries: proposal 2; UC 5.1.1, 17.1.2. KPI fields: mac.moves.per_minute, authentication.failure.percent, login.latency.ms.
- 18_payment_deny — Perimeter deny burst and payment availability loss: proposal 5; UC 5.2.2, 21.11.1. KPI fields: policy.denies.per_second, payment.failure.percent, payment.latency.ms.
- 19_ips_service — IPS attack burst and legitimate-session degradation: proposal 6; UC 5.2.2, 8.1.1. KPI fields: ips.detections.per_second, legitimate.session.failure.percent, service.latency.ms.
- 20_backend_link — Distribution-link loss and backend monitor failure: proposal 8; UC 5.1.1, 8.1.1. KPI fields: backend.link.down, pool.member.unavailable.percent, application.failure.percent.
- 21_partial_pool — Partial load-balancer pool outage with perimeter demand: proposal 9; UC 8.1.1. KPI fields: pool.member.unavailable.percent, application.failure.percent, application.latency.ms.

Remaining proposals: 3, 4, 7, 10, 11, 12. Native-message composition remains gated
by complete selected-family format and field evidence; repaired fixtures alone
do not establish a whole correlated vendor-native lifecycle. No raw formats are changed.

## C7B remaining correlated proposals

All twelve proposals are now executable in the owned custom contract. No native
TA/CIM extraction or actual enforcement is implied. C7A output is unchanged.

- 22_authentication_storm — Campus authentication retry storm at perimeter: proposal 3; UC 17.1.2, 9.3.5.
- 23_containment_request — Simulated NAC containment request and service-access change: proposal 4; UC 17.1.2.
- 24_policy_disagreement — Multi-firewall path-policy disagreement: proposal 7; UC 5.2.2.
- 25_mpls_recovery — Primary MPLS path-change observation and branch SLA recovery: proposal 10; UC 5.1.4, 21.8.2.
- 26_maintenance — Planned maintenance versus unplanned service outage: proposal 11; UC 5.1.1, 8.1.1.
- 27_stale_sessions — Authentication recovery with stale perimeter sessions: proposal 12; UC 17.1.8, 5.2.2.

Maintenance seed parity selects planned (odd) or unplanned (even): application
impact occurs in both, but planned scope has zero modeled unplanned-impact KPI.
Stale-session authentication failure reaches zero at intervention while service
failures persist until subsequent cleanup. Containment is modeled request and
restriction state only; acknowledgement/enforcement are not claimed.
