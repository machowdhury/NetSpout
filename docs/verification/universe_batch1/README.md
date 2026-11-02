# Universal Vendor Coverage Batch 1 recovery — 2026-10-26

Recovered in place from uncommitted work on `oc/ise-ta-1915-record`, baseline
`10aa4342ac34eac5fe282d04ef3613fc7ddd9802`. No reset, branch switch, package
installation, paid API, Splunk configuration change, PAN contract change or push.

## Delivered scope

Canonical vendor rows: 53 → 57; sourcetypes: 313 → 317; scenarios: 40 → 41.
Four product integrations: Docker Engine events, Symantec/Broadcom ProxySG,
Wazuh manager alerts.log and Nozomi Networks Universal alerts. There is no
separate canonical product table; these four integrations must not be described
as four newly discovered technology vendors or products in the ecosystem.

Seven supported family instances (156 → 163 across the source-expansion registries):

| Sourcetype | Supported families |
| --- | --- |
| docker_events | container_lifecycle, network_connect |
| bluecoat:proxysg:access:file | proxy_observed, proxy_denied |
| wazuh:alerts | rootcheck_hidden_process, rootcheck_hidden_file |
| nozomi:universal_alert | ot_ids_program_change |

`ub1_ot_proxy_host_hunt` executes seven events across four phases and all four
sourcetypes. Correlation fields remain outside RAW. This is a synthetic sequence;
it does not prove a real intrusion, causality or detection efficacy.

Recovered gaps: engine omitted from runtime synchronization; broken backend
scenario imports; stale scenario/count metadata; incomplete live-evidence file
list; truncated product projection; unaudited per-app classifications; wrong
Docker network container reference; Wazuh header date inconsistent with epoch;
Nozomi endpoint fields/filter inconsistent. TAs 2758 (Splunk LLC publisher) and
6905 (Nozomi Networks publisher) are now linked to their existing pinned metadata.
The undocumented Docker volume and Nozomi THREAT:COMMAND families are deferred,
not counted or executed. The original RAW fixtures and live summary are retained.

## Inventory and discovery denominator

The existing public Splunkbase metadata snapshot contains 1,871 unique app rows,
matching its declared API denominator: 915 add-ons and 956 applications. Snapshot
hash, all per-app classification bases and all product candidates are retained.
853 raw publisher names normalize to 848. Publisher identities are distinct from
technology vendor identities.

The registry contains 57 canonical vendor keys, 66 additional recognized vendor
keys and 583 title-derived product candidates. Canonical keys include product
families (for example individual Cisco platforms), so 57 + 66 is a registry-key
count, not a count of independent vendor corporations. Product candidates include
utilities and noisy labels and require review. Splunk-published third-party TAs
can be classified in the platform bucket by the existing first-match rule.

Recovery fixed a classifier error that interpreted generic “for Splunk” text as
technology vendor identity. This reclassified many unresolved rows and changes
discovery counts; it is not newly performed ecosystem discovery.

Coverage is complete only against this snapshot's declared denominator. Private,
removed, unlisted, non-Splunkbase integrations and vendors not recognized by the
curated lexicon remain outside verified discovery. No global exhaustive claim.

The complete machine-readable queue is `catalog/vendor_universe.json` →
`uncovered_vendor_queue` (66 keys). Highest app-count entries include Cisco other,
Proofpoint, IBM QRadar, PAVO Metrics, Trellix/McAfee, Akamai, Atlassian and Oracle.
Preserved RAW-evidence deferrals: Trellix ePO, Illumio, Veeam VBR and Proofpoint
PDS. Queue keys are discovery candidates, not proof that every product under an
already canonical vendor is covered. Remaining products/TAs must also be reviewed
through `classified_apps` and the full pinned snapshot.

## Separate evidence categories

* Offline verification: **158 passed, 1 skipped; 148 subtests passed**, exit 0.
  Format grammar, fixture hashes, endpoint consistency, supported-family bounds,
  scenario metadata, fresh runtime imports, discovery and catalog regressions.
  Source and catalog gates both exit 0. Catalog reports 42 unreferenced sourcetypes,
  zero orphan vendors and zero orphan topologies; all four new sources are linked.
* Live RAW equality: preserved pre-recovery summary reports **9/9 PASS over four
  sourcetypes**, run `pf-ub1-rawfidelity-1793041105`. Original summary lacks submitted
  and indexed payload hashes. It demonstrates the prior reported transport check,
  not revised-byte validation, authenticity, TA parsing or detection. No re-ingestion.
  The historical all-wave RAW-equality union is 56 sourcetypes; current recovered
  Batch 1 bytes have not been live revalidated.
* TA parser verification: **0 new; 1 existing overall** (`cisco:ise:syslog`). No
  controlled installed-parser checks for Batch 1. Docker monitoringdocker identity
  and Wazuh alerts.log parser/sourcetype compatibility remain unestablished by the
  snapshot. ProxySG and Nozomi declarations are metadata evidence only. No TAs installed.
* Detection validation: **0 new**. No CIM/ESCU or detection execution claim.

The genuine-family counter records registry family instances, not a globally
unique semantic event taxonomy. The generator-source counter follows canonical
registration; these tests do not exhaustively execute all 317 canonical sources.

## Failure comparison and reproducibility

`validation.json` records exact commands, exit statuses and the focused summary.
`gate-*.txt` retain outputs. `wave3_baseline_failure_identities.txt` preserves the
actual 69 failure identities from the existing broad run (69 failed, 1,025 passed,
10 skipped); the baseline log hash is recorded. The cache named
`wave3_baseline_lastfailed.json` held 109 accumulated identities and was unsuitable
as the actual baseline. Six old count-test identities and the new universe count
test needed Batch 1 assertions updated; none belongs to the actual 69 baseline
failures. Final focused failures: none. Broad suite not rerun; no full-suite clean
claim. Tests completed in bounded subprocesses with a 120-second command deadline.

Rebuild offline, in order:

```sh
.venv-test/bin/python scripts/build_universe_batch1_catalog.py
.venv-test/bin/python scripts/build_universe_batch1_registry.py
.venv-test/bin/python scripts/build_vendor_universe.py
.venv-test/bin/python scripts/sync_core.py
.venv-test/bin/python scripts/verify_sources.py
.venv-test/bin/python scripts/validate_catalog.py
```

Focused pytest command is recorded in `validation.json`; set `PYTHONPATH=src`.
No full ecosystem refetch is needed. If rollback is later requested, revert the
local Batch 1 commit after checking for subsequent work; do not reset or clean.
