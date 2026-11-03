# Compatibility contract: Cisco ASA (`cisco:asa`)

**Status: PARTIAL.** Verified against the installed add-on for the message types listed under "Scope". Not verified: the other ASA message ids, CIM data models, and the add-on's timestamp parsing on the product's own HEC event path (see "Limitations").

| Item | Value |
|---|---|
| Add-on | Splunk Add-on for Cisco ASA (`Splunk_TA_cisco-asa`), Splunkbase 1620, **version 6.1.2** (build 1), published 2026-07-29 |
| Package | `splunk-add-on-for-cisco-asa_612.spl`, 71,033 bytes (equals Splunkbase's published size), sha256 `dbe93977b84b05c6…`; kept outside the repository |
| Lab | isolated TA-validation lab (`tests/lab/ta_validation`, Splunk 10.2.7), index `ta_validation` (event index); the demo environment was not touched |
| Canonical sourcetype | `cisco:asa` (props.conf `[cisco:asa]`; `transforms.conf [force_sourcetype_for_cisco_asa]`: `REGEX = %(?:ASA)-\d+-\d{6}` → `sourcetype::cisco:asa`) |
| Not an add-on sourcetype | `cisco:asa:syslog` (no stanza in props.conf); the product refuses it (`NON_CANONICAL_SOURCETYPE`) |

## What the add-on expects (read from the package)
- **Timestamp:** `TIME_PREFIX = ^`, `TIME_FORMAT = %b %d %H:%M:%S`, `MAX_TIMESTAMP_LOOKAHEAD = 30`, `SHOULD_LINEMERGE = false`: the line must start with the BSD syslog timestamp.
- **Marker:** `%ASA-<severity>-<6-digit id>` anywhere in the line; the id drives about 180 search-time `REPORT` extractions.
- **Extractions used here** (transforms.conf): `-30201[35]:` Built (action, direction, transport, session_id, src/dest interface, ip, port, translated ip/port); `-30201[46]:` Teardown (session_id, interfaces, ips, ports, `duration_*`, `bytes`, `reason`); `-106023:` Deny (action, transport, interfaces, ips, ports, `rule`, `access_group`); `-111008:` (user, action, command).
- **Derived by the add-on:** `action` through `cisco_asa_action_lookup_600.csv` (`built→allowed`, `deny→blocked`, `teardown→teardown`, `executed→executed`), `vendor_action`, `duration` in seconds, `src`/`dest`, `vendor_product = Cisco ASA`.
- **Event types and tags:** `cisco_connection` (ids incl. 302013–302016, 106023; tags `network`, `communicate`), `cisco_authentication`, others.

## Sample provenance
- Replay: `netspout/appserver/static/samples/cisco-asa/cisco-asa.yml` through `src/netspout_core/yaml_sample_replay.py` (8 `_raw` templates, tokens rendered at emit time). Vendored NetSpout sample; messages follow the Cisco ASA syslog guide formats.
- Native: `src/netspout_core/asa_generator.py` (build/teardown pairs sharing a connection id, 106023 denies).
- Format fixtures: `tests/fixtures/cisco_asa/message_formats.json` (shape fixtures from the Cisco guide, not captures).

## Defect found and fixed in this phase
Delivered through the product's HEC dispatcher, the first live run failed 16 of 85 checks (`cisco_asa_ta_compat_before_fix.json`). The add-on extracted ports, transport, session id, bytes, duration and rule correctly, but NetSpout's own indexed fields `action`, `src_ip`, `dest_ip`, `signature` and `protocol` shadowed the add-on's: `src_ip=192.0.2.1` instead of `198.51.100.80`, `vendor_action=streamed` instead of `built`, and `action` missing. Cause proven by resending the identical raw events with only `netspout_*` fields (the add-on then returned the right values). Fix (Phase 3): for sourcetypes in `TA_PARSED_SOURCETYPES` those five fields were sent as `netspout_<name>`. **Phase 4 extends the policy** (live evidence from FortiGate, Palo Alto and IOS showed NetSpout `status`, `vendor` and `node_type` polluting CIM fields too): every event carries `netspout_<name>` copies of action, signature, status, src_ip, dest_ip, protocol, vendor and node_type, and verified sourcetypes (now `cisco:asa`, `cisco:ios`, `fortigate_traffic`, `pan:traffic`) send none of the bare names. Raw event text, sourcetype and index routing were never the cause.

## Results (installed add-on 6.1.2)
`scripts/ta_compat.py tests/ta_specs/cisco_asa.json --live …` after the fix: **85 PASS, 0 FAIL, 0 NOT_RUN** (`cisco_asa_ta_compat_after_fix.json`): version, props stanza, 182 REPORT transforms present, force-sourcetype regex matches the events and rejects the negatives, HEC accepted 7/7, indexed 7/7, sourcetype `cisco:asa`, event-index datatype, every expected field, event type and tags, absent fields for payloads the add-on does not parse, independent search, timestamp parsed from the event text (skew 0 s).

`scripts/verify_asa_generated_live.py` (`cisco_asa_generated_run.json`), values from the raw text compared with what Splunk returned:

| run | generated | HEC accepted | indexed | events fully matching | fields compared | mismatches |
|---|---|---|---|---|---|---|
| YAML replay (3 passes of 8 templates) | 24 | 24 | 24 | 24 | 126 | 0 |
| native generator | 30 | 30 | 30 | 30 | 335 | 0 |

Expected versus observed for the Built event (`302013`, session 984210): `src_ip 198.51.100.80`, `src_port 443`, `dest_ip 10.20.10.45`, `dest_port 52140`, `transport tcp`, `direction outbound`, `vendor_action built`, `action allowed`, `message_id 302013`, `log_level 6`, event type `cisco_connection`, tags `network`/`communicate`: all returned by Splunk.

Example events (as indexed): `Nov 03 16:20:44 fw-cisco-asa-01 %ASA-6-302014: Teardown TCP connection 984210 for outside:198.51.100.80/443 to inside:10.20.10.45/52140 duration 0:02:14 bytes 148920 TCP FINs` → `duration=134`, `bytes=148920`, `action=teardown`.

## Verification queries
```
index=ta_validation sourcetype=cisco:asa netspout_run_id=<run> | stats count
index=ta_validation sourcetype=cisco:asa netspout_run_id=<run> | stats count by message_id
index=ta_validation sourcetype=cisco:asa netspout_run_id=<run> message_id=302013 | table _time host src_ip src_port dest_ip dest_port transport direction vendor_action action eventtype tag
index=ta_validation sourcetype=cisco:asa netspout_run_id=<run> eventtype=cisco_connection | stats count by action
| rest /services/apps/local/Splunk_TA_cisco-asa | table label version disabled
```

## Scope
Fully verified (all fields): 302013, 302014, 302015, 302016, 106023; 111008 (user, action). `message_id`/`log_level`/event type only: 305011, 500003, 605005, 710003 (replay sample messages).

## Limitations
- The remaining ~180 ASA message ids were not tested.
- **CIM data models are NOT verified**: the Common Information Model add-on is not installed in the lab; only CIM field names and tags were observed.
- **Timestamp:** the add-on's `TIME_FORMAT` is applied by Splunk only when the event is parsed from text (verified through the HEC `raw` endpoint). The product sends HEC JSON events, where `_time` is the send time; the add-on's timestamp parsing is therefore not exercised on the product path. The raw text timestamps are UTC and carry no year.
- The bare-name removal applies only to verified sourcetypes; other sourcetypes keep the bare names plus `netspout_*` copies until each is verified.
- The two ASA-containing contracts (`lateral_movement`, `normal_traffic`) were re-run in Phase 4 (`asa_contract_dashboards.json`): all searches run without error. Their phase-story panels read `coalesce(netspout_x, x)`; the previous bare-field searches returned zero ASA events once the add-on owned those fields.

## Phase 4 revalidation
The unchanged spec passed 131 of 131 live checks on the Phase 4 dispatcher (`cisco_asa_ta_compat_phase4_revalidation.json`); 54 generated events, 461 field comparisons, 0 mismatches (`cisco_asa_generated_run_phase4.json`). Status remains **PARTIAL** (scope as above; CIM data models not verified).
