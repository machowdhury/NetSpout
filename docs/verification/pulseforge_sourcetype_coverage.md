# PulseForge Sourcetype Coverage

Generated 2026-10-30 by `scripts/generate_coverage_report.py` from repository evidence (replaces the Phase 3 scanner output).

| Measure | Count | Of catalog |
|---|---|---|
| Cataloged sourcetypes | 348 | 100.0% |
| Vendor-native generator | 142 | 40.8% |
| Sample replay only | 156 | 44.8% |
| No generator | 50 | 14.4% |
| Format verified (byte-equal raw in Splunk) | 118 | 33.9% |
| Vendor TA validated (full or partial) | 1 | 0.3% |
| Independently indexed (live evidence) | 95 | 27.3% |

Tier definitions are in the script header. `TA validated` counts only a parser that was installed and exercised; mapping-only assessments are not counted. `Sample replay only` is recorded-event replay, not a vendor-native formatter.

## Vendors with the most uncovered sourcetypes

| Vendor | Cataloged | Native generator |
|---|---|---|
| cisco_catalyst | 34 | 2 |
| splunk | 21 | 2 |
| cisco_meraki | 17 | 1 |
| nutanix | 16 | 0 |
| cisco_ios | 26 | 11 |
| cisco_intersight | 11 | 0 |
| cisco_duo | 10 | 1 |
| cisco_sdwan | 41 | 34 |
| fortinet | 8 | 1 |
| aruba_cx | 6 | 0 |
| cisco_aci | 8 | 2 |
| cisco_ise | 7 | 1 |
| netskope | 4 | 0 |
| radware | 4 | 0 |
| zscaler_zia | 6 | 2 |
