# 06 Network telemetry and protocol guide

Each protocol lists: what exists, how it was verified, and what is **not** claimed. Verification used the isolated Splunk 10.2.7 Docker lab and independent tools. Suites that need a Splunk destination read `NETSPOUT_HEC_URL`, `NETSPOUT_HEC_TOKEN`, `NETSPOUT_REST_SEARCH_URL`, `NETSPOUT_SPLUNK_USER`, `NETSPOUT_SPLUNK_PASSWORD` (set them to your lab; without them those suites fail as before).

## SNMP
| Item | Detail |
|---|---|
| Versions | **SNMPv2c only.** SNMPv3 is not implemented and not claimed |
| Operations | Polling (GET, GETNEXT, GETBULK) answered by a native agent; traps (0xA7) and informs (0xA6, with Response-PDU acknowledgement) sent to a receiver |
| MIB objects | Standard IF-MIB interface table (ifIndex, ifDescr, ifType, ifMtu, ifSpeed, ifAdminStatus, ifOperStatus, ifLastChange, ifInOctets and further counters with the correct types: Counter32, Gauge32, TimeTicks, OctetString) plus system and health objects; vendor MIBs only where defined |
| Encoding | ASN.1 BER implemented in `snmp_ber.py`; counters, gauges and discontinuities follow the scenario state |
| Splunk path | Normalized `netspout:snmp:poll` / `netspout:snmp:trap` events to HEC; fresh SPL observation |
| Evidence | 75 of 75 tests pass in `tests/test_gate12c/12d/12f` with a Splunk destination configured and the host's Net-SNMP tools (`snmpget`, `snmpwalk`, `snmptrapd`) as independent peers (`docs/verification/evidence/snmp/lab_run.json`) |
| Not claimed | SNMPv3 security interoperability; third-party SNMP managers other than Net-SNMP; vendor-specific MIB breadth |
| Fixed in this window | The SNMP preflight always probed 127.0.0.1:8088/8089 and could report on an unrelated Splunk; it now probes the configured destination |

## gNMI and OpenConfig
| Item | Detail |
|---|---|
| Transport | gNMI over gRPC/HTTP2 (native server, protobuf) |
| Encodings | JSON_IETF, JSON, PROTO; BYTES and ASCII are refused with UNIMPLEMENTED |
| Model-driven paths | OpenConfig: `/interfaces/interface[name=*]/state` (+counters), `/system/state`, `/system/memory/state`, `/system/cpus/cpu[index=*]/state`, `/lldp/...`, `/components/component[name=*]/state` and `/transceiver/state`, `/network-instances/.../evpn/state`. Vendor-native: Cisco IOS-XR (`/interfaces/interface-xr/...`, `/infra-statistics/...`, `/optics-oper/...`, `/system-monitoring/cpu-utilization`, `/bgp-state-data/...`), Juniper (`/junos/system/linecard/...`, `/junos/services/bgp/...`), Arista experimental LANZ |
| Devices modeled | Cisco IOS-XR (ASR 9000, 8000), Cisco IOS-XE, Arista EOS, Juniper Junos (PTX) with per-vendor profiles; each profile limits which models and encodings the device accepts |
| Collector | **gnmic 0.49.0** (OpenConfig) subscribes to the native server; output is normalized to `netspout:gnmi:event` and `netspout:gnmi:metric` |
| Splunk path | events through HEC, metrics through the metric index; `mstats` verification |
| Evidence | 27 of 27 gate13d tests pass against the isolated lab, covering interface/BGP/QoS/optics/CPU-memory state transitions on all four platforms, keyed paths and datatypes preserved, separation of dispatched and observed (`docs/verification/evidence/gnmi/lab_run.json`) |
| Not claimed | Interoperability with collectors other than gnmic; real device behavior; Cisco native YANG beyond the paths above; telemetry dial-out (gRPC dial-out MDT) |

## Cisco model-driven telemetry (native YANG)
Cisco native paths are modeled as separate profiles from OpenConfig (IOS-XR above; IOS-XE appears in the gate13d profile set). They are served through the same gNMI server and are verified only against gnmic. Cisco gRPC **dial-out** MDT and NX-OS-specific streaming are **not implemented**.

## NetFlow v9 and IPFIX
| Item | Detail |
|---|---|
| Encoders | RFC 3954 (NetFlow v9) and RFC 7011/7012 (IPFIX) binary export: headers, template and data sets, template IDs, source id / observation domain, sequence numbers, field types and lengths (IPv4) |
| Independent collector | **GoFlow2 v2.2.5** (pinned image) decoded the datagrams; fields compared with the records sent (type, addresses, ports, protocol, bytes, packets, interfaces): equal for both protocols |
| Splunk path | decoded flows through the repository forwarder to HEC as `netflow:collector`; found by an independent search |
| Dissector check | `tshark 4.6.9` dissects the encoder output with 0 malformed warnings |
| Evidence | `docs/verification/evidence/flow/flow_e2e.json` (5 of 5) and `scripts/verify_flow_pcap.py` |
| Not claimed | sFlow (**not implemented**), J-Flow beyond NetFlow v9 compatibility, IPv6 flows, Cisco Flexible NetFlow beyond the standard fields, Splunk Stream or vendor flow add-ons |
| Blocked scenarios | Five unified SEC-P9 scenarios need the bundled collector (GoFlow2 metrics on 8080, forwarder on 8082) from the repository compose; they were not run in the lab and have no dashboards |

## Metrics
Numerical telemetry (incident gauges, ScenarioRunner metrics, gNMI metrics) goes to a metric index with `metric_name` and dimensions (`netspout_scenario_id`, `netspout_run_id`, `netspout_phase`, device, site) and is verified with `mstats ... WHERE metric_name=*`. Events use HEC events; native protocols keep their own transport to their collector first.
