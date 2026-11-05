# Phase 7 report: real Splunk data discovery (read-only)

Branch `recovery/phase1-ta-compat`, from `96c4e13`. Remote: Splunk 10.4.2 `show-itsi-i-0bc8a6095f4375910` via the configured `splunk-mcp-server`. Role `sc_admin`. Only searches and REST GETs were issued.

## Results
- MCP connectivity: succeeded. `mpreview` is denied for the role.
- Time ranges: primary 2026-02-01 00:00 EST to 2026-03-31 00:00 EDT (upper bound exclusive; server tz America/New_York). All-time only for nine indexes whose data fell outside the window. `cisco_metrics` data in the window spans 2026-03-10..03-26.
- Indexes: 56 on the server (12 disabled internal). 11 event indexes with data in the primary window were enumerated. 185 index x sourcetype pairs in the window, plus 34 pairs found only over all time. 9 metric indexes exist; 3 hold data; 1 (`cisco_metrics`) was inspected.
- Metrics: 330 metric names in `cisco_metrics`; 1 metric index inspected.
- Raw-event formats sampled: 16 (sanitized fixtures).
- Cisco sourcetype changes observed: `cisco:sdwan:sytem:logs` is renamed to `cisco:sdwan:system:logs` by `TA_cisco_catalyst` 4.0.60; 75 per-mnemonic `cisco:sdwan:<FAC-SEV-MNEM>` sourcetypes; installed add-on versions differ from local packages for CiscoSecurityCloud (4.1.2 vs 3.7.3), Meraki (3.2.0 vs 3.5.0), VMware (4.1.0 vs 4.2.1).
- Matches and incompatibilities (17 matrix rows): structure matches for `cisco:ftd:syslog`, `cisco:sdwan:utd:logs`, `cisco:dnac:devicehealth`, `cisco:sdwan:sytem:logs` content; delivery-convention differences for `cisco:ios`, ISE, eStreamer, Duo; event-family mismatch for `meraki:securityappliances`; incompatible payload for `vmware:perf:cpu` and IOS XR metrics; no ASA data on the remote.
- Metric generator gaps: index name, metric names, dimensions, source, sourcetype and YANG family all differ (see `metric_schema_gap_report.md`).
- Nothing was upgraded to VERIFIED. No generated data was ingested into the remote.

## Deliverables (`docs/contracts/phase7/` unless noted)
1. `real_sourcetype_inventory.json`
2. `real_metric_inventory.json`
3. `tests/fixtures/phase7_real_samples/sanitized_real_samples.json`
4. `cisco_sourcetype_version_comparison.md`
5. `netspout_vs_real_matrix.json`, `netspout_vs_real_matrix.csv`
6. `metric_schema_gap_report.md`
7. `top10_generator_corrections.md`
8. `evidence_limitations.md`

## Safety
Samples were redacted by hand (users, hosts, serials, MACs, org/network ids, IPs). No token, credential or unredacted raw event is in the repo. The bearer token was never read or printed by this session; the MCP client holds it. The earlier chat exposure still means it should be rotated. Generated NetSpout output already carries real lab identifiers (Meraki org/network ids) from shipped samples; that predates this phase and was not changed.
