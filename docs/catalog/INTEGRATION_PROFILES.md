# Multivendor integration profiles (C1)

Profiles extend `SplunkIntegration.profiles` in the existing
`catalog/telemetry_catalog.json` registry. Schema version 1.1.0 adds optional
profiles; pre-1.1 integration records remain valid. No separate registry,
transport, generator or runtime routing is introduced.

## Contract

Each globally unique `profile_id` identifies one product/version/collection/format
contract. Use separate profiles for incompatible versions or methods, even when
Splunkbase app ID and product are the same. Parent and profile app identities
must agree. Changing profile order never changes a legacy vendor's default.

| Metadata | Representation |
|---|---|
| Vendor/product/domain | `vendor`, `product`, optional stable `vendor_id`, `domains` |
| Integration identity | `splunkbase_id`, matching HTTPS `splunkbase_url`, `publisher`, `integration_type` |
| Version/applicability | `app_version`, `documentation_version`, `documentation_date`, `platforms` |
| Collection/schema | `collection_method`, `wire_format`, `schema_known`, `sourcetypes`, typed `fields` |
| Sources/timestamps | `requirements` with kind `source` or `timestamp`; exact value and documented details |
| Search/CIM/dashboard dependencies | Requirement kinds `cim_dataset`, `eventtype`, `tag`, `dashboard`, `search`, `signal` |
| Trust/coverage | `evidence_ids`, `verification_state`, `coverage`, `validations`, `notes` |

Field types are string, integer, number, boolean, object or array; `required`
identifies required versus optional fields. A timestamp requirement's details
should record field, format, timezone and epoch unit where documented. Signal
requirements distinguish events from metrics. Dependency records describe
requirements, not satisfied compatibility. References must resolve to existing
catalog evidence; inferred/research-only evidence cannot establish field or
requirement claims. Existing sourcetype authority rules still apply.

Unknown means null or an empty list. An empty platform list does not assert
Enterprise or Cloud support. `schema_known=false` means the complete schema has
not been established; a documented source or sourcetype can still be recorded.
No source, sourcetype, field, CIM dataset or dashboard requirement is inferred
from a product name. Scope excludes SOAR and Phantom.

## Coverage and validation

- `not_assessed`: no schema/sample assessment completed.
- `missing`: assessed telemetry has no implementation.
- `partial`: incomplete coverage, explicitly described in notes.
- `sample_ready`: established schema, collection and format, with passed sample-schema evidence.
- `scenario_ready`: sample-ready prerequisites plus passed generator evidence.
- `integration_verified`: sample prerequisites plus passed parser AND field-extraction
  validation for the exact selected app version and declared Splunk platform.

Integration checks require VERIFIED DATASET_VERIFIED references. Documentation,
sample tests and generator tests cannot establish integration verification.
Passed CIM/dashboard checks independently require the same version/platform
binding and dataset evidence; passing a parser does not imply CIM or dashboard
compatibility. A validation for Enterprise does not prove Cloud compatibility.
These rules validate reviewed metadata, not the truth of an external test report;
maintainers must review the underlying evidence before adding a successful result.

Illustrative future profile shape (not an asserted vendor schema):

```json
{
  "profile_id": "example-product-2-api-json",
  "vendor": "Example vendor",
  "product": "Example product",
  "integration_type": "add_on",
  "app_version": "2.0",
  "collection_method": "API",
  "wire_format": "JSON",
  "coverage": "not_assessed",
  "schema_known": false
}
```

Palo Alto, Fortinet, Juniper, AWS, Azure, VMware, NVIDIA, healthcare and industrial
profiles use these same fields and evidence gates. Vendor-native and custom
PulseForge schemas use distinct profiles and sourcetype authorities. C1 adds no
telemetry or compatibility claims for these future products.

## Cisco seed records and unknowns

C1 preserves the preceding research's source URLs without fetching or refreshing
Splunkbase. Catalog identity evidence is not selected-version schema evidence.
All six seed profiles remain **not_assessed** with no successful validations.

| Profile family | App | Established scope / unresolved work |
|---|---|---|
| Enterprise Networking / SD-WAN | [7538](https://splunkbase.splunk.com/app/7538) | Correct app identity; selected version, formats, fields, timestamp/CIM/parser unknown |
| Meraki API | [5580](https://splunkbase.splunk.com/app/5580) | Correct Meraki identity; API, syslog and webhooks must not share an assumed schema |
| Security Cloud 3.x and 4.x research tracks | [7404](https://splunkbase.splunk.com/app/7404) | Separate placeholders; exact app/document versions and FTD routing unconfirmed |
| Secure Access S3 | [7569](https://splunkbase.splunk.com/app/7569) | Separate S3 contract; API JSON, DNS/proxy/firewall headers and sourcetypes unassessed |
| UCS source contract | [2731](https://splunkbase.splunk.com/app/2731) | `cisco:ucs` sourcetype versus `cisco:ucs:faultInst`, `cisco:ucs:computeBlade`, `cisco:ucs:processorEnvStats` source values; version alignment remains open |

UCS schema evidence: [published add-on documentation](https://splunk.github.io/splunk-add-on-for-cisco-ucs/print_page/).
The records deliberately omit exact release numbers where no selected-release
schema has been established. None links existing samples/scenarios to a vendor
parser without validation. Existing source contracts and older integration IDs
remain unchanged.

## Identity correction and generation

Legacy `cisco_sdwan` pointed at Meraki app 5580, while `cisco_meraki` pointed at
2786 rather than the researched Meraki add-on 5580. This was an incorrect
product-to-catalog identity association, not a runtime transport defect.
C1 maps SD-WAN to Enterprise Networking 7538 and Meraki to 5580, preserving
stable vendor IDs, aliases, sourcetypes, samples and field mappings. Other
suspected identity problems remain uncorrected without established evidence.

Only profiles explicitly marked `legacy_catalog_default=true` project identity
into vendors.json. There may be only one default per stable vendor ID; unknown
vendor IDs fail rather than creating vendors. Projection copies records and
changes only app name, ID and URL. Both full and scoped generation use the same
projection, preventing the old association from returning.

```sh
PYTHONDONTWRITEBYTECODE=1 ../ns-d6-hec-lifecycle/.venv/bin/python scripts/build_canonical_catalog.py --integration-profiles-only
PYTHONDONTWRITEBYTECODE=1 ../ns-d6-hec-lifecycle/.venv/bin/python scripts/sync_core.py
```

The scoped command intentionally leaves unrelated legacy catalogs untouched.
Sync propagates core contracts, catalog mirrors and the static legacy vendor
catalog through the existing mechanism. Do not edit generated copies manually.
`telemetry_sources.json`, `sourcetypes.json` and `vendor_coverage.json` need no
changes: no source schema, telemetry family or readiness is promoted in C1.
