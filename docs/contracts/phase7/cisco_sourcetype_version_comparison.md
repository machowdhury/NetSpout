# Cisco sourcetype and add-on version comparison (Phase 7)

Evidence: read-only REST on the remote instance (`/services/apps/local`, `configs/conf-props`), `tstats` (index-time names), `search` (search-time names), and the Phase 5 matrix (local package versions). Server timezone America/New_York.

## Installed add-ons versus local packages

| Add-on (installed id) | Installed | Local package (Phase 5) | Note |
|---|---|---|---|
| TA_cisco_catalyst | 4.0.60 | 4.0.60 | identical |
| CiscoSecurityCloud | 4.1.2 | 3.7.3 | installed is newer; FTD/Duo/eStreamer verification used 3.7.3 |
| Splunk_TA_cisco_meraki | 3.2.0 | 3.5.0 | installed is OLDER than local |
| Splunk_TA_vmware | 4.1.0 | 4.2.1 | installed is older |
| TA-cisco-thousand-eyes | 5.0.15 | ta_cisco_thousandeyes 0.9.0 | different app lineage |
| Splunk_TA_cisco-ise / Splunk_CiscoISE | 5.0.0 / 2.1.4 | listed as TA_cisco_catalyst 4.0.60 | two ISE add-ons installed |
| TA-cisco_ios / cisco_ios | 2.7.6 / 2.8.1 | - | also installed |
| splunk_app_stream_ipfix_cisco_hsl | 2.1.0 | Splunk_TA_stream_wire_data 8.1.7 | no wire-data TA seen on remote |
| cisco_dc_networking_app_for_splunk | 1.0.2 | none | no local package |

## Classified differences

| # | Observation | Class | Evidence |
|---|---|---|---|
| 1 | `tstats` shows `cisco:sdwan:sytem:logs`; `search` shows `cisco:sdwan:system:logs`. `TA_cisco_catalyst` 4.0.60 props stanza `[cisco:sdwan:sytem:logs]` has `rename = cisco:sdwan:system:logs`. Real content is Meraki MX syslog, which NetSpout also generates. | Same raw format, different sourcetype convention | REST conf-props read; Phase 5 called this a naming "conflict" |
| 2 | Real `cisco:ios` raw has no syslog header (SC4S strips it); NetSpout emits the full header | Same raw format, different delivery convention | raw samples; 11 `sc4s_*` indexed fields on real events |
| 3 | Real ISE raw has no `<PRI>`; NetSpout adds `<181>` | Same raw format, different delivery convention | raw samples |
| 4 | Real eStreamer JSON is compact (`", "`, `":"`); NetSpout uses `": "` | Same raw format, different delivery convention | raw samples |
| 5 | `meraki:securityappliances` real = network events only; NetSpout also emits `eventType/File Scanned` AMP-style events | Different product or event family | raw samples, real fieldsummary (49 fields, none of `eventType`, `fileHash`) |
| 6 | `vmware:perf:cpu` real = TSV event in event index; NetSpout catalog treats it as metric | Actual incompatible payload | raw sample, `vmware-perf-metrics` empty |
| 7 | `cisco:thousandeyes:metric` real raw = `metric` (6 bytes) in event index | Unknown pending further evidence | raw sample |
| 8 | `stream:netflow`: NetSpout leaves `netflow_elements` as `UNKNOWN : hex`; real decoded event carries `app`, `app_tag` | Different parser or extraction expectations | raw samples; sample truncated at 700 chars |
| 9 | Real `cisco:sdwan:<FAC-SEV-MNEM>` (75 sourcetypes) has no NetSpout counterpart | Unknown pending further evidence | tstats; routing rule not read |
| 10 | `cisco:ftd:syslog`, `cisco:sdwan:utd:logs`, `cisco:dnac:devicehealth` structure matches | no difference found at structure level | raw samples |
| 11 | `cisco:asa:syslog` (NetSpout) vs real `cisco:ftd:syslog` | Different product (no ASA data exists on the remote) | tstats shows no cisco:asa* |

No sourcetype was renamed. The `sytem` spelling in the catalog is correct for index-time use.
