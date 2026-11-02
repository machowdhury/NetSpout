# Fortinet and Check Point raw-event repair (C3B)

This is a bounded application of [the platform fidelity standard](VENDOR_RAW_EVENT_FIDELITY.md).
It adds no transports, changes no destination routing, and does not certify any TA
parser, installed extraction, CIM dataset or dashboard.

## Integration identities and scope

Existing C1 integration profiles in `catalog/telemetry_catalog.json` record these
candidate versions, all `not_assessed` / `RESEARCH_REQUIRED`, with no validation
results or asserted official sourcetype mappings:

| Stable vendor ID | Candidate integration | Previous association |
|---|---|---|
| `palo_alto` | Splunk Add-on for Palo Alto Networks, 7523 / 4.0.0 | Archived Palo Alto-owned 2757 / 8.1.3 |
| `fortinet` | Fortinet FortiGate Add-On for Splunk, 2846 / 1.6.10 | Incorrect add-on association 2800 |
| `checkpoint` | Check Point App for Splunk, 4293 / 1.1.6 | Unrelated Departures Board Viz 4292 |

Authoritative listings: https://splunkbase.splunk.com/app/7523,
https://splunkbase.splunk.com/app/2757,
https://splunkbase.splunk.com/app/2846,
https://splunkbase.splunk.com/app/4293,
https://splunkbase.splunk.com/app/4292.

The app name/ID/URL projection uses explicit profile defaults through
`scripts/build_canonical_catalog.py --integration-profiles-only`; both scoped and
full generation use that projection. `scripts/sync_core.py` propagates core and
catalog mirrors and the static vendor projection. Stable vendor IDs, aliases,
sourcetypes, sample associations and execution settings are unchanged.

## FortiGate IPS: FortiOS 7.2.0 subset

Official release-specific references:

- https://docs.fortinet.com/document/fortigate/7.2.0/administration-guide/535363/ips-signature-filter-options
- https://docs.fortinet.com/document/fortigate/7.2.0/new-features/395172/http-transaction-log-fields
- https://docs.fortinet.com/document/fortigate/7.2.0/administration-guide/876272/security-events-log-page

Indexed official examples establish logid `0419016384`, type `utm`, subtype `ips`,
eventtype `signature` and `dropped`/`detected` actions. Direct retrieval of the HTTP
transaction page returned 403; no access restriction was bypassed. References and
limitations are retained in catalog evidence. This is a synthetic subset, not a
complete device capture or a claim about every Fortinet product/release.

The existing IPS formatter now emits one action key and removes the appended
PulseForge `timestamp`, `device_id`, `duration`, second `action`, `signature` and
`status` attributes. Those simulation values remain in LogEntry metadata. Native
date/time has an explicit UTC offset. Nonblocking IPS observations use `detected`;
this does not prove session forwarding or authentication success. Blocking maps
to `dropped`. The existing `fortinet:fortigate:utm` routing label is preserved;
its compatibility with the selected TA is unverified.

Quoted device/attack values preserve spaces. Quotes, backslashes and CR/LF are
rejected because this bounded formatter has no source-backed codec for those
inputs. No generic escaping engine is invented. Other Fortinet samples and
scenario callers remain unchanged; synthetic attack names are modeled values,
not assertions that those exact signatures exist in a FortiGuard database.

## Check Point CEF fixture

The existing fixture is explicitly named/sourcetyped `checkpoint-cef` /
`checkpoint:cef`, but its old pipe-separated KV record was not CEF. C3B repairs
its two synthetic firewall records as CEF instead of relabeling the old data.

Sources:

- Log Exporter Administration Guide, document dated 2026-09-07, page 85:
  https://sc1.checkpoint.com/documents/Log_Exporter/EN/CP_Log_Exporter_AdminGuide.pdf
- Vendor-hosted field mapping and sample:
  https://community.checkpoint.com/t5/AI-Network-Firewall/Log-Exporter-CEF-Field-Mappings/m-p/41060

The header uses CEF version 0, Check Point vendor/product/version conventions,
`Log` event class, service name and `Unknown` severity from the documented export
example. Extension fields are the demonstrated `act`, `rt`, `src`, `dst`, `spt`,
`dpt`, `proto`, `cs2Label=Rule Name` and `cs2`. Timestamps use epoch milliseconds;
ports/protocol use numeric values. Unmapped old fields are not invented as CEF
extensions. The fixture's literal header values contain no pipe/backslash and
extension values need no equals/backslash/control-character escaping. The space
in `Rule Name` is a CEF extension value, not a new field. Focused assertions check
the complete bounded record; they do not implement a general CEF codec.

The existing source `syslog:udp:514`, host, index and sourcetype stay unchanged.
App 4293's Splunk export format and CEF export are separate contracts: correcting
the catalog identity does not establish that app's parsing support for CEF or
`checkpoint:cef`. That remains a selected-version parser-validation task.

## PAN-OS evidence gate

No PAN-OS raw generator or sample is changed. The known traffic CSV defects
(subtype/action position, missing generated time, appended simulation KV) remain
blocked. Vendor 10.2 and 11.0 field-reference URLs redirect to an unversioned
current reference; the attempted release-specific PDF was inaccessible. A pinned
release-specific field order/count is required before native CSV repair.

## Offline validation boundary

`tests/test_fortinet_checkpoint_fidelity.py` contains small, format-specific
assertions for unique quoted KV keys and literal CEF records. Tests cover candidate
identity projection, metadata separation, deterministic clocks, no unresolved
fixture tokens, preserved routing labels and byte/AST preservation of PAN assets.
Existing C1 tests exercise canonical generation in an isolated temporary catalog.
Passing these checks is structural evidence only, not integration verification.
