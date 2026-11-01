# NetFlow / IPFIX solution: ten flow-pattern scenarios and dashboards

Ten deterministic, configurable flow scenarios (five network operations, five security) built on the **existing** NetFlow v9/IPFIX encoders, GoFlow2 collector and forwarder. Each has a scenario-specific Dashboard Studio view, runs from the Use Case Explorer with the Live Delivery Monitor, and is bound to its run id.

Code: `src/netspout_core/netflow_solution.py` (generators, normalizer), `netflow_wire.py` (IPFIX/UDP stage). Dashboards: `scripts/build_netflow_dashboards.py` → `netspout/default/data/ui/views/pf_NF-*.xml`. Evidence: `docs/verification/evidence/netflow/`.

## 1. What already existed, and what was added

| Capability | Status before | Used / added |
|---|---|---|
| NetFlow v9 and IPFIX wire encoders, UDP transport, exporter sessions | EXISTS_AND_VERIFIED (Gate 11) | reused unchanged |
| GoFlow2 v2.2.5 collector + repo forwarder (`deploy/collector`) | EXISTS_AND_VERIFIED | reused unchanged; run separately as the *wire* path |
| Five SEC-P9 flow scenarios (flood, beaconing, recon, DNS tunnel, cross-source) | EXISTS_AND_VERIFIED, fixed 7–11 flow packs, template dashboards | kept unchanged; four of the ten new scenarios are configurable, labelled profiles that reference them (`extends`) |
| Normalized flow event, labels, directional semantics | MISSING | added (`normalize`, `label_meta`) |
| Canonical sourcetype for decoded flows | `netflow:collector` (forwarder, SEC-P9) | reused. **`cisco:ios:ipfix` is not in the catalog** (349 canonical sourcetypes); it is selectable per run with the same props, and is not counted as a registered sourcetype |
| CIM Network Traffic aliases | MISSING | search-time `EVAL-` aliases in `props.conf` |
| NOC-01…05 patterns, SEC-08 exfil indicators | MISSING | new (6 genuinely new scenarios) |
| SEC-06, 07, 09, 10 | EXISTS_NEEDS_EXTENSION | new configurable profiles + distinct dashboards; the SEC-P9 packs remain |
| Dashboards | template only | ten distinct Studio views |

No existing scenario id, catalog entry or dashboard was changed. Ten scenario entries and ten dashboards were added; see section 8 for how counts move.

## 2. Two delivery paths, reported separately

```
FlowRecord ──► IPFIX over UDP ──► GoFlow2 ──► flows.json ──► forwarder ──► HEC     WIRE path (existing, verified)
     └───────► normalize() ───────────────────────────────────────────────► HEC     NORMALIZED path (counted by the monitor)
```

The monitor's *HEC accepted* counter counts the normalized events only. The run panel shows four stages: **generated → UDP exported → collector decoded → HEC accepted**. UDP-exported and collector-decoded records are never counted as accepted or indexed. Indexed comes only from an independent search keyed by `netspout_run_id`.

The wire path registers no correlation with the forwarder, so the forwarder's own events (raw GoFlow2 shape, forwarder index) carry no run id and cannot double-count with the run. `collector_decoded` is the GoFlow2 data-record counter delta during the export. UDP can drop datagrams; when the collector decodes fewer records than were sent the state is `PARTIAL` and the numbers are shown as they are.

`scripts/validate_netflow_wire.py` proves the wire path: every record the collector decoded must equal its source record on all compared fields after `record_from_goflow`/`normalize`. Evidence: `evidence/netflow/wire_roundtrip.json`.

Exporter identity on the wire is the UDP source plus the observation domain id (300 + exporter index); GoFlow2 reports the UDP source (`sampler_address`), not the synthetic exporter IPs.

## 3. Index and sourcetype

* Sourcetype default: `netflow:collector`. Optional: `cisco:ios:ipfix` (same props; not a catalog sourcetype).
* Index: the destination's authorized index chosen in Connection Center. The requested `netflow` index was **not** created and does not exist in the validation lab; runs used the existing lab index `dev_test_replay`. Use `netflow` only if it exists and is authorized.
* Source: `netspout:netflow:normalized`. Raw GoFlow2 events use `goflow2:*`.

## 4. Normalized event (NDJSON schema)

One HEC event per flow (`netflow_solution.ndjson_lines()` writes the same events as NDJSON with run binding added at top level).

| Field | Meaning |
|---|---|
| `timestamp_epoch`, `flowStartMilliseconds`, `flowEndMilliseconds`, `duration_ms`, `flow_start_iso`, `flow_end_iso` | Flow times. Splunk `_time` = flow end (flows are exported when they end). `duration_ms` = end − start |
| `exporter_ip`, `src_ip`, `src_port`, `dest_ip`, `dest_port`, `protocol`, `protocol_number` | 5-tuple and observation point |
| `app`, `app_basis` | Port heuristic only (`app_basis=port_heuristic`), never application identification |
| `tcp_flags`, `tcp_flags_text` | TCP only, else null |
| `bytes`, `packets` | Totals as exported (`octetDeltaCount`, `packetDeltaCount`) |
| `bytes_in/out`, `packets_in/out` | **null always.** A unidirectional record has no verified direction. Dashboards pair forward and reverse flows with SPL where needed |
| `tos`, `dscp` | ToS byte and `tos >> 2` |
| `snmp_in`, `snmp_out`, `src_as`, `dest_as` | As exported |
| `flow_end_reason` | **null.** The IPFIX template used by the encoder does not carry flowEndReason |
| `native{}` | The IPFIX information elements as exported, kept apart from the normalized layer |
| `label_meta{scenario_id, is_malicious, threat_technique, role, note}`, `label_note` | Synthetic scenario truth. Not exporter data. Dashboards never use it as a detection input |
| indexed fields `netspout_run_id`, `netspout_scenario_id`, `netspout_phase` | Run binding (HEC `fields`) |

Addresses come from RFC 5737 documentation ranges only (192.0.2.0/24 servers and exporters, 198.51.100.0/24 clients, 203.0.113.0/24 "internet").

### CIM Network Traffic mapping (search time, `props.conf`)

`src`←`src_ip`/`src_addr`, `dest`←`dest_ip`/`dst_addr`, `dest_port`, `transport`←`protocol`/`lower(proto)`, `bytes`, `packets`, `app`, `vendor_product="NetFlow/IPFIX"`. `action` and `direction` are deliberately not set: a flow record does not say allowed/blocked and these records are unidirectional. The stored events are not CIM data; no data model acceleration is configured or assumed, and no dashboard uses `tstats`.

## 5. The ten scenarios

| Code | Scenario id | Dashboard (view) | Primary question | Reuse |
|---|---|---|---|---|
| NOC-01 | `NF-NOC-01-ELEPHANT` | `pf_NF-NOC-01-ELEPHANT` | Which few flows carry most bytes? | new |
| NOC-02 | `NF-NOC-02-DSCP` | `pf_NF-NOC-02-DSCP` | Is voice/video marked per policy? | new |
| NOC-03 | `NF-NOC-03-ROUTING-LOOP` | `pf_NF-NOC-03-ROUTING-LOOP` | Loop-like repeat observations (indicator only) | new |
| NOC-04 | `NF-NOC-04-ASYMMETRY` | `pf_NF-NOC-04-ASYMMETRY` | Reverse at another exporter or unseen? | new |
| NOC-05 | `NF-NOC-05-BASELINE-DRIFT` | `pf_NF-NOC-05-BASELINE-DRIFT` | Duration/volume drift vs baseline | new |
| SEC-06 | `NF-SEC-06-DDOS` | `pf_NF-SEC-06-DDOS` | Peak packet rate, flags, targets | extends `SEC-P9-A-TRAFFIC-FLOOD` |
| SEC-07 | `NF-SEC-07-PORTSCAN` | `pf_NF-SEC-07-PORTSCAN` | Ports vs hosts per source (T1046) | extends `SEC-P9-D-INTERNAL-RECON` |
| SEC-08 | `NF-SEC-08-EXFIL` | `pf_NF-SEC-08-EXFIL` | Outbound volume outliers (T1048) | new |
| SEC-09 | `NF-SEC-09-BEACON` | `pf_NF-SEC-09-BEACON` | Interval regularity (CV) (T1071) | extends `SEC-P9-C-BEACONING` |
| SEC-10 | `NF-SEC-10-DNS-FLOW` | `pf_NF-SEC-10-DNS-FLOW` | DNS volume and request/response imbalance, limited evidence (T1071.004, T1048.003) | extends `SEC-P9-E-DNS-TUNNEL` |

Each dashboard has its own layout and panel set (no shared template): throughput/talker/table layout (NOC-01), gauge + stacked compliance timeline (NOC-02), table-first evidence ledger (NOC-03), pair classification with forward/reverse bars (NOC-04), baseline-vs-observed comparison (NOC-05), full-width packet-rate hero (SEC-06), footprint scatter + cumulative curves (SEC-07), Sankey storyline (SEC-08), interval histogram + regularity ranking (SEC-09), split direction/outlier view (SEC-10). Common inputs: time range, scenario run, index, sourcetype, plus scenario inputs (thresholds, capacity, internal ranges, baseline percentage).

### What each scenario does *not* prove

* **NOC-01** Utilization appears only if you enter a link capacity. Throughput assumes a constant rate inside each flow.
* **NOC-02** Voice/video class is a UDP port heuristic; the policy (EF=46, AF41=34) is a lab default.
* **NOC-03** NetFlow has no TTL. Loops and TTL depletion are not shown. Confirmation needs ICMP time-exceeded or router counters, which this data does not have.
* **NOC-04** A missing reverse flow can be sampling, coverage or a collection gap, not asymmetry.
* **NOC-05** Flow duration is not application latency.
* **SEC-06** Production export is often sampled; flow data cannot show lost availability.
* **SEC-08** Volume is not theft. **SEC-09** Periodicity is a weak indicator. **SEC-10** Flow records have no query names, lengths or entropy: this is limited evidence and cannot detect encoded labels; correlate with DNS logs.

## 6. Run it

1. Start a lab: Splunk with the app installed (restart splunkd after install), the engine, and a destination in Connection Center. For the wire stage also start `deploy/collector` (`docker compose -f deploy/collector/docker-compose.collector.yml up -d`, needs `SPLUNK_HEC_TOKEN`, `SPLUNK_HEC_URL`, `SPLUNK_INDEX`; set `NETSPOUT_COLLECTOR_HOST`, `NETSPOUT_GOFLOW_METRICS_URL`, `NETSPOUT_FLOW_FORWARDER_STATUS_URL` for the engine). Without a collector the wire stage reports `COLLECTOR_UNREACHABLE` and HEC delivery proceeds.
2. Use Case Explorer → search `NetFlow` (or use universal search) → select → **Configure** (volume scale 0.1–10, window 10–3600 s, delivery EPS, sourcetype, scenario parameters, UDP export on/off) → preview → **Run scenario with live delivery monitor**.
3. Or by API: `POST /api/runs {"kind":"scenario","target":"NF-SEC-09-BEACON","index":"<authorized index>","scale":1,"duration_s":180,"eps":50,"params":{"interval_s":20},"wire":true}`. Flows lie in `[now − duration_s, now]`; the same seed, window and parameters reproduce the same flows.
4. Verify in Splunk (monitor button) and open the dashboard from the READY notification (`form.run_tok` is set).

Bounds: EPS 0.1–2000, at most 20000 flows per run, at most 4 concurrent runs.

## 7. Dashboard Studio versus XML

The deliverable is **Dashboard Studio (v2)** views (`<dashboard version="2">` wrapping the Studio JSON definition), consistent with the other PulseForge dashboards. Dashboard Studio JSON is not Simple XML and is not presented as such. No Classic Simple XML versions were produced.

## 8. Counts

| Item | Before | After |
|---|---|---|
| Canonical sourcetypes | 349 | 349 (`cisco:ios:ipfix` is optional, not registered) |
| Streamable single sourcetypes | 259 | 259 |
| Installed dashboards | 138 | 148 |
| Deduplicated scenario definitions | 362 | 372 |
| Runnable scenarios | 138 | 148 (6 are new capabilities: NOC-01…05 and SEC-08; 4 are configurable profiles that extend existing SEC-P9 packs) |
| Dashboards visually verified | 10 | 20 |

## 9. Verification

`scripts/validate_netflow_dashboards.py` (every data source and drilldown against real indexed data), `scripts/render_netflow_live.mjs` (rendered in Splunk Web), `scripts/render_netflow_flow.mjs` (search → configure → run → monitor → READY → dashboard), `scripts/validate_netflow_wire.py`. Results: `docs/verification/netflow_solution_verification.md`.

## Related scenario profiles (search and scenario detail)

Four NetFlow scenarios are configurable profiles of existing SEC-P9 packs. Both sides stay in search and both stay runnable; they are different executions with different dashboards:

| NetFlow profile (new dashboard) | Parent fixed pack (unchanged dashboard) |
|---|---|
| `NF-SEC-06-DDOS` → `pf_NF-SEC-06-DDOS` | `SEC-P9-A-TRAFFIC-FLOOD` → `pf_SEC-P9-A-TRAFFIC-FLOOD` |
| `NF-SEC-07-PORTSCAN` → `pf_NF-SEC-07-PORTSCAN` | `SEC-P9-D-INTERNAL-RECON` → `pf_SEC-P9-D-INTERNAL-RECON` |
| `NF-SEC-09-BEACON` → `pf_NF-SEC-09-BEACON` | `SEC-P9-C-BEACONING` → `pf_SEC-P9-C-BEACONING` |
| `NF-SEC-10-DNS-FLOW` → `pf_NF-SEC-10-DNS-FLOW` | `SEC-P9-E-DNS-TUNNEL` → `pf_SEC-P9-E-DNS-TUNNEL` |

Search rows carry a relation label ("NetFlow profile of …" / "Has NetFlow profile …"), and a scenario's detail page shows a **Related scenario profiles** panel with a link to the other side and its dashboard. The data comes from the `related` list on the Explorer entry (`GET /api/explorer/entries/{id}`) and `relation` on `GET /api/search` scenario rows. The other six NetFlow scenarios have no parent pack.

## Index in the lab

The target index is whichever authorized index your Connection Center allows. PulseForge never creates one. The earlier validation lab used `dev_test_replay`; the `phase4e` lab (ports 18000/18088/18191) has no `dev_test_replay` and no `netflow` index, so its runs used `idx_network_ops`. There is no `netflow` index in either lab.
