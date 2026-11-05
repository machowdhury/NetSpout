# Timestamp semantics (validated integrations)

Three different clocks exist for a NetSpout event; they must not be confused.

| clock | where it lives | who sets it |
|---|---|---|
| text time | the timestamp inside the raw event (`Nov 03 14:05:09`, `date=… time=…`, PAN `generated_time`) | the generator / sample (rendered from the UTC clock at generation time) |
| HEC `time` | the `time` field of the HEC JSON event | NetSpout's dispatcher: the send time (`time.time()`) |
| Splunk `_time` | the event's index time stamp | HEC event endpoint: the HEC `time`. HEC raw endpoint / syslog / file input: the add-on's `TIME_PREFIX`/`TIME_FORMAT` (or Splunk's auto-detection) applied to the text |

## Strategy per validated integration
| sourcetype (add-on) | product path (HEC JSON event) | raw-text path (add-on timestamp rule) | evidence |
|---|---|---|---|
| `cisco:asa` (Splunk Add-on for Cisco ASA 6.1.2) | `_time` = send time | parsed from the text with `TIME_PREFIX=^`, `TIME_FORMAT=%b %d %H:%M:%S`: **verified**, skew 0 s | `cisco_asa_ta_compat_phase4_revalidation.json` |
| `fortigate_traffic` (Fortinet FortiGate 1.6.10) | `_time` = send time | the add-on defines no `TIME_FORMAT`; Splunk auto-detected `date=… time=…`: **verified**, skew 0 s | `fortigate_traffic_after_fix.json` |
| `pan:traffic` (Palo Alto 4.0.0) | `_time` = send time | `TIME_PREFIX=^(?:[^,]*,){6}`, `TIME_FORMAT=%Y/%m/%d %H:%M:%S` (CSV column 7): **verified**, skew 0 s | `pan_traffic_after_fix.json` |
| `cisco:ios` (Cisco Enterprise Networking 4.0.60) | `_time` = send time | auto-detect: **verified after a sample fix** (see below) | `cisco_ios_before_fix.json` (fail) and `cisco_ios_after_fix.json` (pass) |

## Decisions
- **Product ingestion stays HEC JSON events** (not switched to HEC raw). `_time` is the send time, which equals the text time for freshly generated events. The add-on timestamp rules are therefore not exercised on the product path; they are verified separately through the HEC raw endpoint so that anyone who sends the same text through syslog or a file input gets correct times.
- **Time zone:** text times are rendered in UTC with no year (syslog style) or with a `UTC` label. The lab indexer runs in UTC; an indexer in another zone would shift text-parsed times unless the input sets `TZ`. Not tested.
- **Ordering and scenario timing:** scenario phases set `netspout_phase` and send time follows generation order. Text timestamps within one generation batch are identical (one clock reading per render). Event ordering inside a second is therefore carried by HEC `time` (sub-second) and not by the text.
- **Proven defect fixed:** NetSpout's `cisco-ios` sample rendered a header time but kept a hard-coded device time (`2026 Feb 28 19:00:01 EST`). Through the raw path Splunk combined the two: `_time` = 2026-03-26 13:53:50 for an event generated on 2026-11-03. The sample now renders the device time too (`$DEVTS$`). `tests/test_timestamp_semantics.py` fails if any shipped sample renders a timestamp token and also contains a literal full timestamp (one documented exception, `cisco-dc-aci-class`, a recorded object field).
