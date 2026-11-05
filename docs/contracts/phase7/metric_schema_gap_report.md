# cisco_metrics schema and routing gap report (Phase 7)

Nothing here was implemented. Evidence is from `mcatalog`, `mstats` and the REST index list on the remote instance. `mpreview` was denied (role lacks the capability), so raw metric events were not inspected; the schema below comes from `mcatalog`/`mstats` only.

## What the real index holds
- `cisco_metrics` is a metric index (`datatype=metric`), 15,997,060,265 events all time. Data in the primary window runs 2026-03-10 to 2026-03-26 (EDT).
- 330 metric names: 164 `Cisco-IOS-XR-*:<yang path>.<leaf>`, 128 `interface_status.*`, 20 `isis_neighbors.*`, 11 `interface_generic_counters.*`, 7 other flat (`bgp_status`, `fib_summary`, `rib_ipv4_status`, `rib_ipv6_status`).
- Dimensions: `interface_name`, `path`, `node_name`, `subscription`, `neighbor_address`, `identifier`, `name`, `vrf_name`, `system_id`, ... (31 in total). `path` carries the YANG sensor path.
- `source` = device management IP (10 devices) or router name; `sourcetype` = `httpevent`; `host` = the HEC front end. Delivery is HEC.
- Values are cumulative counters (for example 37,558,365 bytes on a 40GE port, 0 on idle ports).
- Eight other metric indexes exist. Only `em_metrics` and `itsi_summary_metrics` hold data (not inspected). `thousandeyes_metrics`, `vmware-perf-metrics`, `sdwan_metrics`, `cisco_xr`, `network_telemetry`, `itsi_im_metrics` are empty.

## What NetSpout emits (`cisco:ios:mdt:metric`, previewed locally, nothing sent)

| Aspect | Real `cisco_metrics` | NetSpout |
|---|---|---|
| Index | `cisco_metrics` | `cisco_mdt_metrics` (default `hec_metric_index`) |
| Sourcetype | `httpevent` | `cisco:ios:mdt:metric` |
| Source | device IP / router name | `cisco:ios:mdt` |
| Host | HEC front end | device id (`ncs-edge-01`) |
| Metric name | `interface_generic_counters.bytes_received`, or `<module>:<path>.<leaf>` | leaf only: `in_octets`, `cpu_utilization` (gNMI path uses `gnmi.<category>.<leaf>`) |
| Dimensions | `interface_name`, `path`, `node_name`, `subscription` | `device`, `host`, `vendor`, `status`, `action`, `node_id_str`, `sensor_path` |
| Payload family | IOS XR native YANG (`Cisco-IOS-XR-*`) | OpenConfig (`openconfig-interfaces:`, `openconfig-platform:`) |

Result: a dashboard or search written against real `cisco_metrics` would return nothing from NetSpout output. Metric names, dimension names, source, sourcetype, index and YANG family all differ.

## Classification of the observed streams
- Genuine metric-index streams: all 330 `cisco_metrics` names.
- JSON events containing measurements: none observed in this phase.
- Modular-input events: `vmware:perf:*` (TSV in `vmware-perf`), `cisco:dc:*`, `cisco:dnac:*`, `cisco:sdwan:linkhealth` are events, not metrics.
- Unsupported by NetSpout: all IOS XR native names; `vmware:perf:cpu` and `cisco:thousandeyes:metric` are events on the remote, which confirms the Phase 6 routing blocks.

## Proposed changes (not implemented)
1. Make the metric index name a setting with `cisco_metrics` as a documented option, not the default `cisco_mdt_metrics`.
2. Add an IOS XR native profile that emits `<module>:<path>.<leaf>` names and the dimensions `interface_name`, `path`, `node_name`, `subscription`, starting with the three highest-value families: `infra-statsd generic-counters` (about 50 names), `wdsysmon cpu-utilization`, `nto-misc memory-summary`.
3. Add the flat family (`interface_generic_counters.*`, `bgp_status.*`, `rib_ipv4_status.*`, `fib_summary.routes`) as a second profile; its path dimension equals the IOS XR sensor path.
4. For HEC metric events set `source` to the device IP and `sourcetype` to `httpevent`. Keep `netspout_run_id` as an extra dimension so runs stay identifiable.
5. Emit cumulative counters that increase monotonically per interface; keep idle ports at 0.
6. Keep `vmware:perf:*` and `cisco:thousandeyes:metric` blocked until an event generator (TSV for VMware) replaces the metric routing; do not push them to a metric index.
7. Verification still requires live ingestion into an authorized test index and an `mstats` query that returns the generated names.
