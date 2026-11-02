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

Numeric telemetry is delivered as **Splunk metric events**: HEC JSON with `"event": "metric"` and one `metric_name:<name>` field per measurement, all other fields as dimensions. Logs and non-numeric records go to an **event** index as ordinary HEC events. A mixed run (incident packs, gNMI) needs both indexes authorized.

### Events versus metrics, models versus transports
| Concept | Meaning here |
|---|---|
| Event vs metric | Events are searched with `index=...`; metrics with `mstats` / `mcatalog` / `mpreview`. A metric index cannot be read with an event search, and PulseForge never falls back to an event index for metrics |
| YANG model vs transport | OpenConfig and vendor-native YANG define *what* a path means; gNMI, SNMP or HEC define *how* it moves. A path in the catalog is not a transport |
| gNMI vs HEC | gNMI is the device-facing protocol (served by the synthetic native server, dial-in only); HEC is how normalized events and metrics reach Splunk |
| Synthetic vs replay vs device | Everything here is synthetic generation or recorded-sample replay. **No real device is connected.** |

### Connection Center authorization
A destination's `indexes` list is the allow-list for both event and metric indexes. An index whose name contains `metric` is used as the destination's metrics index (for example `test_metrics`); otherwise the default `cisco_mdt_metrics` applies. If that index is not on the list, a metric-bearing run is refused with `Metric index is not authorized by Connection Center (HTTP 403)`. To authorize a remote metrics index, save the destination with both the event index and the metrics index listed. PulseForge does not create indexes, and the HEC token itself must be allowed to write to them.

### What is implemented (from the code; verified by reading, not by device tests)
| Family | OpenConfig | Vendor-native paths | Transport | Metrics delivery |
|---|---|---|---|---|
| Cisco IOS-XR | 14 shared OpenConfig sensors | 6 (`infra-statsd`, `pfi-im-cmd`, `ipv4-bgp`, `qos-ma`, `controller-optics`, `wdsysmon-fd`) | gNMI dial-in, synthetic | `gnmi.*` metrics with `gnmi_unit`; SNMP-typed metrics |
| Cisco IOS-XE | same 14 | 5 (`interfaces-oper`, `bgp-oper`, `environment-oper`, `transceiver-oper`, `process-cpu-oper`) | gNMI dial-in, synthetic; SNMPv2c | same |
| Arista EOS | 14 + EVPN/VXLAN (modeled) | 4 (`eos_native`: Sysdb counters, LANZ, Smash BGP, Smash VXLAN) | gNMI dial-in, synthetic | `gnmi.*` metrics; `arista:telemetry:json` is a recorded-sample replay |
| Juniper Junos | same 14 | 4 (`junos`: linecard interface, optics, qmon, BGP) | gNMI dial-in, synthetic | `gnmi.*` metrics |

Not implemented: gNMI **dial-out**, Cisco **MDT** as a protocol (MDT is only a log/metric *format* here), SNMPv3, NX-OS gNMI, gNMI `Set`. Native paths were not validated against vendor YANG; the registry's "VERIFIED" labels are the project's own, not an external check. Incident-pack gauges (27 network + 10 telecom packs, 10 gauge records per 40) are generic modeled KPIs such as `interface.errors.rate` or `upf.packet_drop.percent`; they carry **no vendor, YANG model or path**, and they are gauges only.

### Metric contract gaps (stated, not hidden)
- gNMI metrics carry `gnmi_unit`, `gnmi_path`, `gnmi_sensor_id`, vendor and platform, run id and phase, but **no counter-versus-gauge flag**. Only SNMP-typed metrics (`snmp_metrics.py`) distinguish counter32/counter64/gauge32. Treat interface octet and packet metrics as cumulative counters when querying.
- Equivalent measurements across vendors share a name only where the gNMI leaf name matches; interface naming, counter widths and reset behavior are not normalized.

### Searching metrics
Discover what a run produced, then rate a counter. `<metric>` and the index are yours to fill in; these two queries were **not executed**, because no metrics index was available to test against (see below):
```
| mcatalog values(metric_name) AS metrics values(gnmi_vendor) AS vendors WHERE index=test_metrics

| mstats latest(_value) AS v WHERE index=test_metrics AND metric_name="<metric>" AND netspout_run_id="<run id>" BY interface_name span=10s
| streamstats current=f last(v) AS prev BY interface_name
| eval bits_per_s=if(v>=prev, (v-prev)*8/10, null())
```
The `if` drops a negative step (a counter reset) instead of plotting it. Cumulative octets are never bits per second. Existing incident dashboards use `mstats avg(_value) ... span=1s` on gauges, with `fillnull value=0` for missing samples, so a gap shows as zero. Syntax reference: <https://docs.splunk.com/Documentation/Splunk/8.2.12/Metrics/Search>.

### Remote `test_metrics` status
Nov 2 2026, Splunk Cloud 10.4 (`docs/verification/evidence/metrics/remote_test_metrics_2026-11-02.json`):
- **Five-metric test: PASS.** 5 uniquely tagged synthetic metrics were accepted over HEC (0 rejected) and then found independently with `mstats` and `mcatalog`, with their run id and dimensions.
- **Incident pack, metrics side: PASS.** `telco_09_core_user_plane` gauges (10 records, 30 datapoints) were accepted and found by `mstats` with the expected counts. The four `mstats` searches of `pf_telco_09_core_user_plane` all return data for that run in Cloud.
- **Not tested:** the pack's 30 log records (the metrics HEC token is refused on event indexes: `Incorrect index`, so the mixed event-plus-metrics path was not exercised), the engine run path and Live Delivery Monitor against Cloud, a rendered dashboard (the app is not installed in Cloud), and any vendor/OpenConfig sample.
- `mstats` needs a `metric_name` predicate in its `WHERE` clause (for example `metric_name=*`); without one, one query returned no rows even though the data was present.

The isolated Docker lab has no metrics index (none was created), so metric-bearing runs are refused there. The Cloud result is a bounded check, not production certification.
