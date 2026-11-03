# Next 10 generator corrections, ranked (Phase 7)

Ranked by (real-data evidence strength) x (events or scenarios affected) / effort. None implemented.

| # | Correction | Evidence | Effort |
|---|---|---|---|
| 1 | IOS XR MDT metrics: emit `cisco_metrics` schema (names, dims, source, sourcetype httpevent), see metric gap report | 330 real metric names; mcatalog/mstats | L |
| 2 | `meraki:securityappliances`: stop emitting AMP-style `eventType` events (belong to `meraki:organizationsecurity`) | real fieldsummary of 100 events, 49 fields, none AMP | S |
| 3 | `vmware:perf:*`: add a TSV event generator for `vmware-perf` event index (11 sourcetypes at about 8.3M events each in real data, 12 with clusterServices); unblock `vmware:perf:cpu` | raw TSV sample, empty `vmware-perf-metrics` | M |
| 4 | Duo `ctime`: recompute weekday after date rewrite; space-pad day (`Tue Nov  3`) | side-by-side real vs generated; `wave3_authentic_engine.py:1578` uses `%d` | S |
| 5 | Syslog day padding: RFC 3164 uses space-padded day (`Feb  2`), real SD-WAN events do; check every BSD-syslog generator | real sample vs generated `Nov 03` | S |
| 6 | `cisco:sdwan:<FAC-SEV-MNEM>`: locate the add-on routing rule, then generate per-mnemonic sourcetypes | 75 real sourcetypes, 114,869 events | M |
| 7 | eStreamer: emit compact JSON (`", "`, `":"`) and include `LastPacketSecond`, `ConnectionDuration` | raw sample comparison | S |
| 8 | `cisco:ios` / `cisco:ise:syslog`: offer an SC4S-shaped variant (no header; no `<PRI>`) and verify the add-on parses it | raw samples; 11 `sc4s_*` fields on real events | M |
| 9 | `stream:netflow`: decode `netflow_elements`, add `app`, align `observation_domain_id` | raw sample (truncated at 700 chars) | M |
| 10 | `cisco:thousandeyes:metric`: replace with `cisco:thousandeyes:test` event generation (7.55M real events) instead of a metric payload | real sourcetype counts; raw of `...:metric` is only `metric` | M |

Not ranked because no real data exists to compare: `cisco:asa:syslog` and every vendor outside Cisco/Meraki/VMware/ThousandEyes/Duo/Stream.
