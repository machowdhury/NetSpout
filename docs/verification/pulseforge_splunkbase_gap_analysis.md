# Splunkbase add-on coverage gap analysis (2026-10-30)

Machine-readable: `docs/verification/evidence/splunkbase/crossref.json` (444 app rows + 2,644 declared-sourcetype rows), `pulseforge_splunkbase_crossref.csv` (apps),
`pulseforge_splunkbase_crossref_sourcetypes.csv` (sourcetypes). Built offline by `scripts/build_splunkbase_crossref.py` (`snapshot` fetches metadata, `crossref` joins it to the registry).

## Inputs and what they are
| Input | Finding |
|---|---|
| `~/Downloads/addon.csv` | **Not a CSV: an Excel workbook (xlsx zip) with a .csv extension.** One column ("Add-on Name"), 444 unique rows, no IDs. sha256 and workbook save time (2026-10-30T16:31Z) recorded in `addon_snapshot.json`. **Export date: unknown** (the workbook records only its own save time). Treated as a filtered snapshot. |
| `~/Downloads/splunkbase_addons.csv` | Name -> Splunkbase UID join (exact title). 444 of 444 joined. |
| Splunkbase public API v1 (2026-10-30) | Title/version/supported Splunk versions/CIM versions/license/docs for all 444 (no login). |
| Pinned Splunkbase snapshot (`catalog/vendor_universe/`, fetched 2026-10-26) | The only source of **declared sourcetypes** (`rel_tags_st`). 438 of 444 apps are in it; the 6 newer apps have no declared-sourcetype evidence (INSUFFICIENT_EVIDENCE). |
| Package contents (props/transforms/inputs/README) | **Not inspected**: package downloads need a Splunkbase login. Role labels (collector/parser/protocol) are keyword heuristics on name and description, stated as such in the data. |

## 1-3. Rows, vendors, existing coverage
- Rows examined: 444; verified against the API: 444; 356 apps declare sourcetypes (5,686 declarations, 2,644 unique spellings).
- Vendor/product keys discovered: 230 (the rest are publisher-only or Splunk platform apps). PulseForge has a catalog vendor for 134 apps (64 distinct vendors).
- App classification (app-level; one label per app, strongest present tier wins): PRESENT_NATIVE_VERIFIED 40, PRESENT_NATIVE_UNVERIFIED 5, PRESENT_SAMPLE_REPLAY 7, PRESENT_NO_GENERATOR 4, MISSING_SOURCETYPE 60, MISSING_VENDOR_PRODUCT 214, INSUFFICIENT_EVIDENCE 54, OUT_OF_SCOPE 60.
- Splunk-built "Add-on for <third-party product>" apps (NGINX, Office 365, AWS ...) are in scope; other Splunk platform apps are OUT_OF_SCOPE. (A first pass wrongly put the NGINX add-on in OUT_OF_SCOPE; fixed.)

## 4-5. Confirmed missing vs candidates (do not read the large numbers as gaps)
- **Vendor/product gaps are separate from sourcetype gaps.** 214 apps (198 distinct vendor/product keys) have no PulseForge vendor. These are *candidates*: no authentic sample or documented format was checked for them, and none were added.
- 1,227 declared sourcetypes are MISSING_SOURCETYPE under an existing vendor. **Only 3 have authentic bytes in the pinned corpus** (the rest, 1,224, have none and stay backlog): `nginx:plus:access` (12 datasets; **implemented**), `o365:graph:api` (1 dataset, API collector), `stream:tcp` (1 dataset, Splunk Stream wire-data protocol collector). `XmlWinEventLog` in that count is a spelling of channels PulseForge already emits as `XmlWinEventLog:<channel>`, not a gap.
- Confirmed missing sourcetype with evidence: `nginx:plus:access` (now closed). Open with evidence but blocked: `o365:graph:api`, `stream:tcp`.

## 6. Mis-mapped TAs (verified only)
- 100 Cisco rows had `required_ta` nulled earlier (previous value "Splunk Add-on for Unix and Linux" was wrong). **37 are now filled** because Splunkbase declares that exact sourcetype for a named app (`required_ta_review.status = VERIFIED_DECLARED_BY_SPLUNKBASE`, with `splunkbase_ids`; 7538 Cisco Enterprise Networking Add-on for 26, 7828 for 10, 4221 for 1). This is a declaration, not parsing validation. **63 stay UNVERIFIED** (no app declares the exact spelling).
- `vendors.json` IDs that resolve to an unrelated Splunkbase app (checked by API title, **not applied**): netskope 4774 (the exact-title listing "Netskope Add-on For Splunk" is **3808**), cisco_duo 4768, citrix_netscaler 2748, huawei_vrp 5262, netscout 4920, nutanix 3148, vmware_nsx 3110; f5_bigip 2680 is the right app but is named "Splunk Add-on for F5 BIG-IP" on Splunkbase. Only netskope has a verified replacement (3808). **None was changed**: `tests/test_fortinet_checkpoint_fidelity.py` requires every vendor row except palo_alto/fortinet/checkpoint to equal HEAD, and `vendors.json` rows are projected from `telemetry_catalog.json`, so a correction needs a coordinated change to the contract test, the telemetry catalog and the generated vendor catalog. Left as a recorded finding.
- 21 rows still list "Splunk Add-on for Unix and Linux" (linux_infrastructure/splunk/sc4snmp), not shown wrong.

## 7. API-collector and protocol-collector gaps (heuristic, name/description based)
- API-collector candidates: 81 apps whose text says API/modular input/webhook and whose vendor or sourcetype PulseForge does not generate natively. These need documented API responses to implement; none are claimed.
- Protocol collectors: Splunk Add-on for Stream Wire Data (5234) and Stream Forwarders (5238) are wire-capture collectors with no PulseForge protocol path. Technology Add-on for NetFlow (1838) matched the text rule but PulseForge already emits native NetFlow v9/IPFIX templates; it needs review, not a new generator.

## 8-9. Implemented
- **`nginx:plus:access`**: native generator (`universe_batch7_engine.py`, registry `catalog/universe_batch7.json`), 5 verbatim records from 3 `splunk/attack_data` NGINX Plus key=value datasets. Authenticity: the three dataset files were fetched from the repo's pinned commit (4389fa7a) and are byte-equal to the local copy; sourcetype declared by the Splunk Add-on for NGINX (3258). Only the record's own `time_local` is re-stamped; no other field varies. Catalog row added (vendor `nginx_f5`, required_ta Splunk Add-on for NGINX).
- The existing `nginx:plus:kv` generator emits a combined-log line plus a synthetic key=value trail and does **not** match these authentic records; it is left untouched and stays NATIVE_UNVERIFIED.
- **New scenarios made runnable: 0.** No scenario names `nginx:plus:access`.

## 10. Independent validation (isolated lab, Splunk 10.2.7, `tests/lab/ta_validation`)
`scripts/verify_batch7_live.py`: 5 events over HEC, read back by independent search: 5 indexed, 5 indexed `_raw` byte-equal to submitted, 5 sourcetype-equal. Evidence: `catalog/universe_batch7_live_raw_equality_results.json`. **TA parsing not validated**: no NGINX add-on is installed (package requires a Splunkbase login). Time-field parsing and CIM mapping are unchecked.

## 11. Before / after
| Measure | Before | After |
|---|---|---|
| Cataloged sourcetypes | 348 | 349 |
| Vendor-native generator | 158 | 159 |
| Byte-verified (native) | 128 | 129 |
| Independently indexed | 136 | 137 |
| Sample replay / no generator | 143 / 47 | 143 / 47 |
| TA-parsing validated in a lab | 6 (Windows/Sysmon channels) | 6 |
| Cisco rows with verified required_ta | 0 of 100 | 37 of 100 |

## Scenario blockers (CONTRACTED scenarios that are not runnable-native)
Eight sourcetypes in CONTRACTED scenarios lack a native generator: `cisco:catalyst:networkhealth`, `meraki:accesspoints`, `arista:telemetry:json` (sample replay); `cisco:ise:trustsec:sgt`, `cisco:ise:nac:8021x`, `netapp:ontap:nas`, `pan:ble:iot:sensor`, `cisco:mds:san:fc` (no generator). Only `cisco:catalyst:networkhealth` (app 7538) and `meraki:accesspoints` (5580) are declared by an app in the 444; neither has authentic bytes in the pinned corpus. The other six are declared by none of the 444 add-ons. **This audit unblocks none of them**; the blocker is authentic samples, not Splunkbase coverage. The missing original 100 financial / 100 telecom use-case files were not fabricated.

## 12. Remaining blockers
No authentic bytes for 1,224 declared sourcetypes; add-on packages (login) for props/transforms and TA parsing checks; documented API payloads for 81 API-collector candidates; a Splunk Stream wire-data collector path (`stream:tcp`); a Graph API payload corpus (`o365:graph:api`, 1 dataset).
