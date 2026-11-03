# Evidence limitations and missing access (Phase 7)

## Access
- `mpreview` is denied for the role (missing capability). Raw metric events were not inspected; schema comes from `mcatalog`/`mstats`. `mcatalog` supports only `values()`.
- `mstats` needs a `metric_name` filter, and listing a dimension a metric does not have silently returns no rows. Early empty results were this effect, not missing data.
- Search timeout is 60 s. The all-index `tstats` timed out and was split by index group.
- The role is `sc_admin`. All queries were read-only searches and REST GETs. Nothing was written, installed or created.

## Coverage
- Event `tstats` covered 11 indexes with data in the window. ITSI/summary indexes (`itsi_*`, `summary*`, `em_metrics`) were not queried; they are not NetSpout targets.
- `em_logs` (18 `kube:*` names) and Meraki (23 names) are collapsed in the inventory file.
- Real extracted fields were pulled for 4 sourcetypes (`cisco:ios`, `cisco:ftd:syslog`, `cisco:dnac:devicehealth`, `meraki:securityappliances`) from 100-event samples, which can miss rare message families.
- Raw samples were truncated at 450-900 characters, so field lists for long events (Duo, netflow, link health) are incomplete.
- Only one `cisco:ftd:syslog` message family (805002) exists in the window.
- No sample was taken for most Meraki, ACI, `cisco:dnac:*` (other than devicehealth), `cisco:duo:*` (other than auth v2), `cisco:sdwan:tunnelhealth/sitehealth/ssetunnels`, `nix:syslog`, `kube:*`, per-mnemonic SD-WAN, `cisco:catalyst:*`.
- Add-on configuration was read only for `cisco:sdwan:sytem:logs` and `cisco:sdwan:system:logs` (props). Transforms and routing rules for per-mnemonic sourcetypes were not read.

## Time
- Server timezone America/New_York. The window `2026-02-01T00:00:00` to `2026-03-31T00:00:00` was passed to the MCP tool as local times: 2026-02-01 00:00 EST to 2026-03-31 00:00 EDT (DST began 2026-03-08), upper bound exclusive. All-time (`earliest=0`) was used only for nine indexes whose data fell outside the window.
- Several sources have no data in the window: VMware, ThousandEyes, Webex devices (2025), Duo user/authentication_v2 (all-time only). Their samples come from outside the primary window.
- `cisco_metrics` data in the window spans only 2026-03-10..03-26.

## Unexplained
- `main` and `netflow` both report exactly 40,719,386 `stream:netflow` events in the window.
- `cisco:dnac:devicehealth` raw carries `cisco_dnac_host`, indexed fields show `cisco_catalyst_host`.
- Real `cisco:thousandeyes:metric` raw is the string `metric`.

## Not claimed
No NetSpout integration was upgraded. A real indexed sample proves the source exists, not that NetSpout output ingests and parses correctly. Real data is from a lab instance; the shipped NetSpout samples appear to come from the same lab (identical Meraki network and org ids appear in generated output), so format agreement for those is partly circular.
