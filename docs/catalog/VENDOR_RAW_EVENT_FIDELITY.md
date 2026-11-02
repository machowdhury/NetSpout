# Platform-wide vendor raw-event fidelity standard

This is mandatory for all existing and future vendor-native telemetry across
networking, security, identity, ITOps, cloud, AI infrastructure, telecommunications
and industry scenarios. Scope excludes SOAR and Phantom. Existing assets are not
retroactively certified by this standard.

## One catalog and evidence chain

Use `SplunkIntegration.profiles` in `catalog/telemetry_catalog.json`, following
[the C1 contract](INTEGRATION_PROFILES.md). Reuse `catalog/vendors.json`,
`sourcetypes.json`, `samples.json`, `telemetry_sources.json` and
`vendor_coverage.json`; do not create a parallel registry or duplicate a schema
for every dashboard consuming it.

For each vendor/product/device or API version and collection method:

1. Record an official raw example or published schema in existing catalog evidence.
   Preserve its URL, publisher, release applicability, document revision/date and
   limitations. Prefer official vendor examples when Splunkbase supplies no data.
2. Record intended integration ID/version and its collection/parser documentation.
   Separate the currently listed version from the version actually validated.
3. Link a synthetic fixture that preserves the selected native format. Preserve
   required identifiers, field order/types, delimiters, nesting and timestamp
   semantics. Substitute documented variable values only. Keep simulation/run
   metadata outside the raw body unless the native schema defines that field.
4. Add deterministic structural, field and timestamp checks, including malformed
   inputs and lifecycle relationships. Preserve vendor-native payloads through
   existing adapters; local delivery or HEC acceptance does not prove parsing.
5. Validate selected-version TA parsing configurations against expected fields,
   sourcetype routing, timestamps, multiline behavior and type conversions.
6. Separately record installed-TA extraction results for the selected Splunk
   platform/version. Successful event indexing alone is insufficient.
7. Validate CIM datasets, eventtypes/tags and dashboard/search requirements only
   when claimed; parser success does not establish consumer compatibility.

Use optional/null values for unknowns. C1 profile `requirements` records source,
timestamp, signal, CIM, eventtype/tag and dashboard/search dependencies;
`fields` records typed required/optional fields. `validations` records the kind,
result, selected integration version/platform and evidence references. Evidence
records can point to reviewed fixtures/reports. No profile may reach
`integration_verified` based on sample/generator tests alone. C1 does not encode
an independent installed-TA validation kind: document that distinction in the
referenced validation report and profile notes rather than inventing a field or
silently conflating offline parser checks with live installed verification.

## Explicit format and evidence labels

- **Vendor-native:** source-backed structure for a specific version/method; no
  unsupported grammar or sourcetype is inferred from a vendor name.
- **Custom PulseForge:** modeled schema with explicit custom authority; useful
  simulation output, not an assertion of a vendor device's raw output.
- **Legacy:** retained compatibility interface with unresolved provenance or
  schema claims. Do not promote it by renaming its sourcetype.

Levels A (reference), B (structural fixture), C (selected parser), D (installed
extraction), E (CIM/dashboard) describe separate evidence. Unknown remains unknown.
A TA's documented capabilities are not proof that a PulseForge fixture passes it.

## Reusable format-aware test pattern

| Format | Required checks |
|---|---|
| Syslog | Selected BSD/RFC5424/vendor envelope; priority/facility/severity; timestamps/timezone; exact message ID/body; delimiter/escaping; multiline/segmentation; original raw bytes at adapter boundary |
| JSON / API | Parse complete records; nested shape and field types; nullability; epoch units/timezone; API response envelope versus individual collected event; collection enrichment separately documented |
| Webhook | Vendor payload/event version, nesting, identifiers and timestamp; distinguish transport envelope/signature metadata from event data |
| CSV | Vendor-specific field order/count, quoting/escaping, empty columns, embedded delimiters and release-dependent fields; parse with CSV rules, not naive split |
| Key/value | Vendor-specific separators, repeated keys, quoting, escaped separators and nested attribute sets; avoid a universal KV grammar |
| Metrics | Documented names, units, types, timestamps, resource/dimension semantics and signal format; no event-parser compatibility claim from a metric name |
| Other | Published format/encoding and independent structural decoder where available; do not coerce into syslog |

For ASA/ISE, the existing `tests/test_cisco_raw_events.py` fixture helpers use a
fixed clock and explicit raw assertions. They cover IDs, native-field pairing,
ISE authentication versus CoA semantics, nested attributes, token rejection and
metadata separation. They are not a universal parser and do not run live sends.

## Existing inventory and rollout priorities

Inspection of the canonical catalog finds 36 vendor IDs and 213 sample dataset
entries (not 213 individual records). Existing legacy `required_ta`, CIM and
vendor mappings require assessment; their presence does not establish evidence.
The C1 Cisco profiles remain `not_assessed`; this batch makes no catalog promotion.
No corpus-wide sample rewrite or other vendor implementation is performed.

| Priority / family | Reusable existing assets | Evidence and parser work before promotion |
|---|---|---|
| 1 Cisco | ASA/ISE repairs; IOS/XE/XR, SD-WAN, Meraki samples; XR structural template; ACI, Duo, Intersight catalog entries | Complete ASA/ISE selected-version parser checks first; then pin networking formats and API/syslog/webhook profiles independently. Existing XR source-backed structure does not certify a TA. |
| 2 Security | `palo_alto`, `fortinet`, `checkpoint`, `zscaler_zia`, `netskope`, `sonicwall`, `sophos`, `watchguard`, `forcepoint` | Compare existing CSV/KV/JSON bodies with official release-specific log references; resolve intended integration/version and actual parser expressions before rewriting. |
| 3 Networking | `juniper_junos`, `arista_eos`, `aruba_cx`, `f5_bigip`, `a10_networks`, `dell_os10`, `extreme_networks`, `huawei_vrp`, `nokia_sr` | Separate native syslog, structured logs, flow and API formats. Reuse documented schemas across consuming apps. Versioned integration and parser evidence remain unassessed here. |
| 4 Identity | Cisco ISE/Duo; inspect Microsoft/Okta assets outside the 36-vendor legacy projection before claiming coverage | Pin Windows event XML/channel semantics, API JSON/webhook versions and intended TAs; do not fabricate provider IDs or identity lifecycle events. |
| 5 Cloud | Assess AWS/Azure/GCP sample families beyond the legacy vendor projection | Separate each service's audit, flow, platform and metric schemas; use official examples and corresponding ingestion integrations. Asset and parser coverage unknown in this batch. |
| 6 Infrastructure | `nutanix`, `vmware_nsx`, `splunk`; existing database/ITOps generators require separate inventory | Distinguish ESXi/vCenter/NSX, storage, database, Kubernetes audit/container logs and metrics; pin the relevant integration for each schema. |
| 7 AI infrastructure | C1 can represent NVIDIA/AMD profiles; no implementation added | Inventory assets first; validate supported GPU exporter/management metrics, units and resource dimensions against authoritative schemas. Avoid labeling modeled metrics as native device output. |
| 8 Telecom / industry | Ten committed telecom incident scenarios and `nokia_sr` remain reusable simulation assets | Incident correlation is not equipment-format proof. Establish vendor/version contracts for telecom and financial, healthcare, manufacturing, energy, retail and transportation systems before vendor-native claims. |

For every row, structural coverage must be linked to actual assertions, not
inferred from a passing scenario. Selected-version parser, installed-TA and
consumer validation remain unknown unless a specific report establishes them.
Broader family inventory is incremental; this table is a rollout plan, not a
claim that all listed vendors or industry formats are implemented or compatible.
