# PulseForge Phase 4C Recovery — Audit, Implementation and Evidence

**Date:** 2026‑10‑29
**Branch:** `oc/ise-ta-1915-record` (worktree `ns-sec2b-credential-updates`)
**Lab:** `pf-native-lab` — Splunk 10.2.7 (`c0bff5b0fac3`), Docker, local‑only
**Publication status:** credential blocker **CLEARED** (§10); held only for
outgoing-change review, not for an active exposed secret

## 0. What PulseForge is — and what this recovery must not become

PulseForge is a **Splunk-native application**. Splunk owns identity: user
authentication, admin account creation, password changes, sessions, and
role-based access control. PulseForge does not have, and must not grow, its own
default admin account, its own password, or its own login step.

That boundary changes how several findings in this report should be read:

- **Docker is a development and testing harness**, not the product's deployment
  unit. The container's initial Splunk password is lab configuration for a
  disposable environment. It must never be treated as application configuration,
  and no code may read it as if it were authoritative (§3.6 is exactly that bug).
- **The credential rotation in §10 is housekeeping about exposure**, not a
  redesign of product authentication. Nothing about PulseForge's auth model
  changed, because none needed to: the app is supposed to run in the
  authenticated Splunk user's context and respect that user's roles and
  capabilities.
- **User-configured HEC destinations must not carry hardcoded tokens** in source
  or in the catalog. Secrets that must be persisted belong in Splunk's supported
  secure storage (`storage/passwords`), referenced by name.
- **Custom data-source profiles and generation metadata belong in KV Store** —
  configuration and metadata, never bulk events and never secret values. That is
  Phase 4D's shape, restated in those terms in the plan.
- Environment-based configuration remains correct **for disposable development
  credentials only**, which is what `backend/.env` (untracked, mode 0600) holds.

So when this report says a defect was found in credential handling, the claim is
that PulseForge was reaching *around* Splunk for identity or secrets. The fix is
always to go back through Splunk's own layer, never to invent a second one.

This report has to answer two different questions, and they have different
answers. First: were the Phase 4C "complete" claims true? Second: what is true
now, after the recovery work? The claims were largely false (§1). The
subsystems they describe now genuinely work (§4–§7), verified end to end through
the real runner → HEC → Splunk path. Those are separate statements and are kept
separate throughout.

---

## 1. Claims vs Evidence (the Phase 4C commits)

Audited against commits `df5fd09`, `2e278ca`, `ce87042` and
`PHASE4C_FINAL_SUMMARY.md`.

| Claim | Evidence at audit | Verdict |
|---|---|---|
| "Exact match with historical evidence: 14 generated, 14 accepted, 10 indexed" | The referenced artifact had `metric_observed_count = 0`; the branch's own control run recorded **0 accepted**. | **False** — count reused from history, not re-measured |
| "Format verified: PAN‑OS fields correctly structured" | Generator emitted `LEEF:2.0`, not native PAN‑OS CSV | **False** |
| "`AuthenticPaloAltoGenerator` class verified working" | `generate_traffic_log(count=N)` returned **1** record for any N | **Broken** |
| "Catalog verified: 8 Palo Alto sourcetypes with correct vendor ID" | Catalog `pan:*` entries were correct; the generator emitted non‑canonical `paloalto:traffic` | **Partially true** — catalog right, generator wrong |
| "SNMP metrics foundation built" | `snmp_metrics_generator.py` existed but was imported by neither `TelemetryDispatcher` nor `ScenarioRunner` | **Disconnected** |
| "333 OIDs cataloged" | `snmp_mib_oid_inventory.json` genuinely held 333 rows | **True** (inventory only — see §5.2) |
| "Palo Alto live acceptance verified" | Driver used the pre-rotation token and the broken generator | **Invalid** |
| "All code pushed to GitHub" | Pushed, but **zero** files under `src/netspout_core/` or `catalog/` | **True, and not integrated** |
| "Fresh UI‑to‑runner‑to‑Splunk evidence" | UI path never exercised | **Untested** |

Two corrections to my own earlier baseline write-up, now that the root causes are
known:

- **Cisco "0 accepted" was not a token or index misconfiguration.** The cause was
  `DestinationManager` resolving `destinations.json` relative to the current
  working directory, so a run started from the repo root read a stale untracked
  file pointing at `cisco_mdt_metrics` — an index absent from the token
  allowlist, rejected with HTTP 400 `{"text":"Incorrect index","code":7}`. Fixed
  by anchoring to `backend/destinations.json` with
  `PULSEFORGE_DESTINATIONS_FILE` override (§3.1).
- **`sync_core.py` does propagate the catalog**, contrary to the earlier note. It
  writes to `netspout/bin/catalog_data/`, `backend/app/catalog_data/`,
  `netspout/catalog/` and `netspout/bin/netspout_core/`. The divergence was
  because Phase 4C never touched canonical files, not because sync was missing
  them.

## 2. Credential Cleanup (§1 of the mission, done first)

Completed and reported separately in
`docs/verification/pulseforge_phase4c_credential_cleanup.md`. Summary:

| Item | Result |
|---|---|
| Old HEC token `1379bbf9…` in 14 tracked files | **Invalidated** (HTTP 403) and replaced by `os.getenv('PULSEFORGE_LAB_HEC_TOKEN')` |
| Second stale token `86eafae9…` | **Invalidated** (HTTP 403) |
| New lab tokens (2) | Active, HTTP 200 |
| Base64 `YWRtaW46…` credential blob in 3 files incl. `origin/main` | Removed from working tree |
| Lab admin password in 8 tracked files | **Rotated and invalidated** — old credential now returns HTTP 401 (§10). The tracked-file copies were already removed from the working tree; the values left in Git history are a dead credential, and history was deliberately not rewritten |
| Working-tree sanitization | ~19 files changed: env-var reads in 10 scripts, `[REDACTED]` in 7 docs, untracked gitignored `backend/.env` |
| History rewrite / force-push | **Deliberately not done.** Exposure was neutralized by rotation, not scrubbing. |

Nothing was committed or pushed. All edited scripts pass `py_compile`.

## 3. Product Defects Fixed on the Way

### 3.1 `DestinationManager` CWD-relative default
Metric and event dispatch depended on which directory the process happened to
start in. Anchored to the package path with an explicit override.
`scripts/verify_destination_path_resolution.py` passes for all three working
directories (repo root, `backend/`, `/tmp`), each resolving `metric idx =
idx_performance_metrics`.

### 3.2 Dispatcher metric routing was Cisco-only
`dispatch_log` decided "is this a metric?" by hardcoded
`log.sourcetype in ("cisco:ios:mdt", "cisco:ios:mdt:metric")`, and then
**relabelled every metric payload as Cisco telemetry** — source
`cisco:ios:mdt`, sourcetype `cisco:ios:mdt:metric`. Any non-Cisco metric source
was therefore unroutable, and would have been misattributed if it arrived.
Routing is now catalog-driven via `is_metric_sourcetype()` (the canonical
catalog's `data_kind == "metric"`), and only Cisco keeps the historic labels.
Regression-tested both ways (`test_metric_payload_still_cisco_for_mdt_logs`,
`test_metric_payload_keeps_snmp_sourcetype_not_cisco`).

### 3.3 Defects found but deliberately **not** changed (flagged for a decision)
`cisco_mdt_metrics` survives as a *default* in several places:
`models.py` `TelemetryTransportConfig.hec_metric_index`, `models.py:~435`
`index`, `gnmi_engine`, `fault_injection_engine` (two hardcoded indices), the
dispatcher's `or "cisco_mdt_metrics"` fallback, and 8 descriptive
`splunk_storage` strings in `catalog/`. The live path overrides all of these with
the destination's value, so nothing breaks today — but any code path that
constructs a transport without a destination would silently target an index the
lab rejects. I left these alone rather than sweep ten files under a
"recovery" label; they need their own change with the frozen-count tests updated
deliberately.

A second finding I deliberately did **not** change, because the fix has
cross-cutting blast radius: the discovery projection's readiness label.
`scripts/build_discovery_catalog.py` derives `readiness='Executable custom
simulation'` **only** from membership in the incident producer pack
(`incident_contracts()` over `netspout/bin/network_incidents.py`) and attaches
`dashboard_ids` only from `catalog/dashboard_recipes.json` selectors. Catalog
`maturity` is never consulted. Measured consequence, not inferred:

| Observation | Count |
|---|---|
| Catalog rows at `GOLDEN_PATH_CERTIFIED` or `E2E_VALIDATED` | 17 |
| …of which are incident-pack members | **0** |
| …rendered `Legacy / verification pending` in the projection | **17** |
| …with an empty `dashboard_ids` | **17** |

So the discovery surface under-reports verified capability for *every* certified
scenario it holds, `ddos_attack` and the thirteen golden paths included — the
three Phase 4C scenarios are the newest members of a pre-existing class, each
carrying the gap text "Execution and parser compatibility require separate
validation." Making the rule evidence-aware relabels all 17 rows at once and
forces a decision about which dashboard each belongs to, so it is its own change
with its own frozen-count updates rather than something folded in here. Recorded
as Phase 4D story **D-6**, sequenced after C-3 so a readiness label can point at
runner-written evidence instead of a name.

### 3.4 The "8 Palo Alto sourcetypes" claim traced to a divergent mirror
The original audit marked that claim "partially true". It is now explained
precisely: `backend/app/catalog_data/sourcetypes.json` (committed) held **356**
entries, **8** of which existed nowhere in the canonical catalog —
`paloalto-config`, `-cortex`, `-globalprotect`, `-system`, `-threat`,
`-traffic`, `-userid`, `-wildfire`. Those are the non-canonical `paloalto:*`
forms the broken generator emitted. Canonical `catalog/sourcetypes.json` has
**348** entries with the correct `pan-traffic`/`pan-threat`/`pan-system` →
`pan:traffic|threat|system`, `vendor_id=palo_alto`.

So the "8 verified sourcetypes" were verified **against a stale mirror**, not
against the catalog that runtime reads. Running the project's own
`scripts/sync_core.py` (which byte-copies canonical to every mirror) removes
those 8 and leaves 348 everywhere. Nothing in the codebase still depends on them
except a self-test block in `backend/app/sourcetype_resolver.py`, which I updated
to assert canonical `pan:*` and which now passes against the 348-entry catalog.

**Counting rules, stated precisely** (what each number counts):

- **348 = the number of rows in the canonical `catalog/sourcetypes.json`**, one
  row per canonical sourcetype *identity*. Each row carries its own
  `splunk_sourcetype`, `aliases` and `deprecated_aliases` — so a single row can
  serve several Splunk-facing spellings. Cross-checks: every one of the 53
  catalog scenarios' declared `sourcetypes` resolves against exactly this
  union (`splunk_sourcetype` ∪ `aliases` ∪ `deprecated_aliases` ∪ `id`), zero
  unresolved. The pinned counter in `tests/test_wave2_authentic_expansion.py`
  asserts `len == 348` (the test's *name*, `test_sourcetype_rows_289`, is a
  stale label from an earlier epoch — the assertion is the authority).
- **356 = the stale committed mirror's row count**: 348 canonical rows + the 8
  invented `paloalto-*` rows that existed only in that mirror. Those 8 rows
  were a mirror-local artifact of the Phase 4C interim generator, never
  products of the canonical pipeline; deleting them changes no canonical
  identity — the correct `pan-*` aliases already cover the Splunk spellings
  (`pan:traffic|threat|system`, `vendor_id=palo_alto`).
- **Zero-drift rule:** mirrors are byte-copies of canonical by design
  (`sync_core.py`, `indent=1`), enforced by
  `tests/test_gate2_canonical.py::test_02_zero_drift_guardrail`. This is why
  re-formatting the mirror `json` files to "minimise the diff" is explicitly
  **not** done: it would re-introduce drift, make the guardrail fail, and the
  ~14k-line whitespace delta is what the byte-copy invariant looks like when a
  mirror is shown against `indent=4` history. The whitespace-insensitive diff
  of the two mirror files is 337/9 lines (`scenarios.json` — three new
  contracts) and 0/136 lines (`sourcetypes.json` — only the 8 non-canonical
  rows removed, canonical content untouched).

**Review note on diff size:** the committed `backend/app/catalog_data/*.json`
mirrors were formatted `indent=4` while canonical is `indent=1`. Because
`sync_core.py` copies bytes, syncing rewrites those two mirrors in full
(~29k lines of whitespace). My scenario-registration script originally inherited
the same problem and re-indented the canonical file too; that is fixed —
`catalog/scenarios.json` and its three mirrors now show **+334 lines each**,
which is exactly the three new scenario contracts. Reviewed semantically
(`git diff --ignore-all-space`), the whole change is **3,640 insertions / 352
deletions**, not the ~17k line figure a plain `--stat` shows.

### 3.5 Enabled destination + dead credential = silent total dispatch failure
Running scenario B through the **product API** returned HTTP 200 with
`dispatch_attempted: 51, dispatch_succeeded: 0` and every record marked
`{"state":"FAILED","http_status":403,"error_class":"auth_rejected"}`. The same
scenario through the acceptance driver, minutes earlier, had been 51/51 accepted.

Cause: `backend/destinations.json` stores **no** token (`hec_token` empty for both
`docker_local` and `external_default`); `to_transport_config()` fills it from the
**process environment**. The long-lived `uvicorn` (PID 75729, started ~1 d 17 h
earlier) had `PULSEFORGE_LAB_HEC_TOKEN` bound at start — proven by reading that
process's own environment: its token is **36 characters** (the revoked UUID form)
and compares unequal to the current 32-character lab token. Rotation invalidated
the token, the destination stayed `enabled=True`, and the API had no reason to
complain: the endpoint's guard only checks `dest.enabled` and
`transport.hec_token` truthiness, both of which a dead credential satisfies.

Restarting the backend with current credentials made the identical call succeed
51/51 (§7.1). Two things follow, and neither is code I should silently patch
under a recovery label:

1. **Credential freshness is unobserved.** An "enabled" destination can carry an
   expired secret with no health signal. A destination-level probe belongs in
   Phase 4D (D-3 adjacent), and the product-shaped answer — HEC destinations
   configured by the user inside Splunk, with the token held in
   `storage/passwords` and referenced by name (Phase 4D plan §4.3, §5 invariant 3,
   story D-1) — removes the "read once at import" failure mode entirely. Reading a
   token from the process environment is acceptable for a disposable Docker lab
   (§0); as an application mechanism it is what makes a stale secret invisible.
2. **Environment drift between two entry points is invisible in the manifest.**
   `dispatch_failed: 51` with a 200 response is the same shape as a genuine
   product outage. Reporting should surface `error_class` aggregates, not just
   totals — otherwise "the API ran" is mistaken for "the data arrived".

This also explains how the original Phase 4C "Palo Alto live acceptance verified"
claim could have been written honestly and still been wrong: the author's own
long-lived process was holding a stale credential.

### 3.6 A validation helper was scraping the container's build-time password

While re-running §6 after rotation, `scripts/phase4c_control_run.py` failed with
`SPL dispatch failed (401): Unauthorized` — even though the same shell
authenticated against `/services/server/health` with HTTP 200 moments earlier.
`scripts/pf_lab_query.py:spl_admin()` resolved credentials like this:

```python
pw = os.environ.get("NETSPOUT_SPLUNK_PASSWORD", "")
if not pw:
    pw = subprocess.run(["docker", "exec", "pf-native-lab", "sh", "-c",
                         "printenv SPLUNK_PASSWORD"], ...).stdout.strip()
```

Neither branch is correct after rotation, in two different ways:

- the env var name is the `NETSPOUT_*` convention from the docs, while the lab
  env file and every sanitized script use `SPLUNK_PASSWORD`, so the env branch
  returns `""`;
- the fallback then reads the **container's** `SPLUNK_PASSWORD`, which is the
  value the entrypoint consumed at first boot. Changing the Splunk account
  through Splunk's own authentication layer never updates that variable, so the
  scrape silently resurrects the retired credential.

That second failure mode is the dangerous one: it is invisible while nothing is
rotated, and it turns a supported security operation into a confusing 401 in
every tool that uses the helper. The fallback is also exactly the pattern §0
rules out — treating Docker as the source of truth for who can log in.

**Fixed** (environment-only, with a clear error instead of a silent bad
credential): resolve `NETSPOUT_SPLUNK_PASSWORD` then `SPLUNK_PASSWORD`, then
raise a message naming both variables. Repo-wide grep confirms no other
`printenv SPLUNK_PASSWORD` scrape remains; the only other `docker exec` use in
`scripts/verify_gate14b_certification.py` runs `splunk btool check` for a
different container and reads no credential. Verified behaviour:

| Case | Result |
|---|---|
| env configured | resolves to the live credential, `py_compile` clean |
| env absent | raises `Splunk management credentials are not configured: set NETSPOUT_SPLUNK_PASSWORD (or SPLUNK_PASSWORD)` |
| Cisco control after fix | HTTP 200, run `NS-20261029-f3f9d813` (§7) |

Unused `import subprocess` removed from the helper as part of the change.

## 4. PAN-OS Native Generator — now real

`src/netspout_core/panos_generator.py`, replacing the LEEF path (the old
`AuthenticPaloAltoGenerator` / `paloalto_live_acceptance.py` is superseded, not
reused).

| Requirement | Implementation | Evidence |
|---|---|---|
| Native CSV, not LEEF/CEF | PAN‑OS syslog CSV, `1,<ts>,<serial>,<TYPE>,…` | Stored events inspected in Splunk: no `LEEF`/`CEF` prefix (§7) |
| Field contract | traffic **54**, threat **45**, system **17** | Pinned to the repo's own byte-frozen YAML samples, not to doc order |
| Timestamp form | `YYYY/MM/DD HH:MM:SS` | Confirmed by ordinal: `47` at positions 4 and 7 (a slash). Note: date-looking strings render with dashes in several tool outputs — verify bytes, not appearance. An earlier "dash fix" was wrong and was reverted |
| `count=N` → exactly N | `generate(kind, N)` returns N or raises | Unit-tested; and in production run A the generated split (25/13/9) equalled the indexed split exactly |
| Seeded determinism | `random.Random(seed)`; stable string seeds per (scenario, phase) | `test_same_seed_is_reproducible`; values replay offline and match (§6) |
| Canonical sourcetypes | `pan:traffic` / `pan:threat` / `pan:system` | Zero `paloalto:*` in emitted records; catalog already canonical |
| LEEF/CEF as labelled alternates | Not generated at all here | Catalog `telemetry_notes` states LEEF/CEF are customer export templates and are not represented as native |
| Address hygiene | RFC 5737 documentation space + RFC 1918 only | Hygiene test present |
| Integrated into production | `to_log_entry()` bridge → `ScenarioRunner._generate_phase_telemetry` → `TelemetryDispatcher` → HEC | Live run, §7 |

**Tests:** `tests/test_pan_os_native_generator.py` — 47 passing.

## 5. SNMP Metrics — typed, integrated, honestly labelled

### 5.1 What was built
`src/netspout_core/snmp_metrics.py`: a typed OID registry plus a deterministic
generator, emitted through the existing HEC metric path.

- **Small and fully verified, not broad and unverified:** registry holds **12**
  OIDs — **10 `VERIFIED`** (each carrying its RFC citation and unit) and **2
  `INFERRED`** (usable, unit asserted rather than documented). **3** OIDs are
  explicitly held back as `UNRESOLVED` and the generator refuses to emit them.
  `registry_summary()` reports the split so coverage claims stay honest.
- **Syntax classes are real, not cosmetic:** `COUNTER32`, `COUNTER64`, `GAUGE32`,
  `UNSIGNED32`, `INTEGER32`, `ENUM`, `STRING`, with `CUMULATIVE` / `INSTANT`
  grouping. `counter_delta()` **raises** if asked to difference a Gauge32 —
  the single most common SNMP mistake, made structurally impossible here.
- **Counter resets and rollover:** `increase` / `wrap` / `reset` are distinguished
  by where the previous sample sat relative to the ceiling; the method used is
  published per-sample as `snmp_method:<name>` so a reviewer can audit it rather
  than trust it.
- **Enum handling:** `ifOperStatus` is decoded to its RFC 2863 label and is
  **excluded from the metric data map**. An earlier cut published it as a metric,
  where `mstats avg(ifOperStatus)` would have produced a meaningless number; the
  test that caught it is `test_metric_names_do_not_include_enumerations`, and a
  runtime invariant now raises if any ENUM/STRING ever reaches `values`.
- **Counter64 precision — a real bug, found by a test I wrote and then had to
  correct:** `float(2**64-1)` is not 2\*\*64-1; it rounds to 2\*\*64, and the
  spacing of representable doubles there is 4096, so a wrap near the ceiling was
  silently mis-cost. All cumulative arithmetic is now done in Python integers.
  `test_counter64_wrap_math_needs_integers_not_float64` pins the hazard.
- **Language discipline:** records are **modeled** measurements. No socket is
  opened and no device is polled; `action` is `"modeled"`, not `"polled"`, and
  `test_no_claim_of_polling_in_generated_output` fails if "polled" ever reaches
  the payload. This output must never be described as SNMP polling.

### 5.2 Relationship to the 333-OID inventory
The 333-row inventory is real and remains as an inventory artifact. It is **not**
a capability claim: 12 OIDs are generatable with verified semantics; the rest are
catalogued. Those are different numbers and are reported separately.

**Tests:** `tests/test_snmp_metric_typed_generation.py` — 88 passing.

## 6. Scenarios — registered, runnable, delivered, counted

Registered in canonical `catalog/scenarios.json` (53 entries now, was 50),
mirrored by `sync_core.py` to all four catalog locations, wired into
`SUPPORTED_SCENARIO_IDS`, `_get_topology_for_scenario` and
`_generate_phase_telemetry`. Authoring script:
`scripts/register_phase4c_scenarios.py`.

Maturity is **earned, not asserted**: the script defaults to `CONTRACTED` and
only writes `E2E_VALIDATED` when passed `--verified`, which was done *after* the
live runs in §7 produced matching counts.

| Scenario | Id | Telemetry |
|---|---|---|
| A — PAN threat investigation | `paloalto_threat_investigation` | `pan:traffic`/`threat`/`system`, threat→traffic correlation id so an analyst can pivot |
| B — Degradation + security correlation | `network_security_correlation` | PAN + Cisco `cisco:catalyst:security:events` + `sc4snmp:metric` in one window |
| C — Financial-services payment degradation | `payment_processing_degradation` | PAN + Cisco payment-edge evidence + SNMP metrics |

All three run on the existing `mixed_edge` topology, which already carries a Palo
Alto NGFW, a Catalyst switch and an internal app server — so no parallel topology
fixture was invented. Phase→PAN-OS mapping covers the engine's full
`ScenarioPhase` enum (INITIALIZE…COMPLETE), not just the five declared phases.

The fourth Phase 4C brief item, an AI/LLM inference-RAG degradation scenario, was
**not** built. It is carried into Phase 4D rather than half-implemented here.

## 7. Live Verification (fresh runs, rotated credentials, no reused counts)

Driver: `scripts/phase4c_control_run.py` — the real production `ScenarioRunner`
against the authorized lab. Each row below is this run's own measurement.

| Scenario | run_id | seed | generated | HEC accepted | rejected | indexed events | metric records | metric names |
|---|---|---|---|---|---|---|---|---|
| A `paloalto_threat_investigation` | `NS-20261029-12083179` | 51001 | 47 | 47 | 0 | 47 | 0 | — |
| B `network_security_correlation` | `NS-20261029-58818c7d` | 51002 | 51 | 51 | 0 | 37 | 14 | 9 |
| C `payment_processing_degradation` | `NS-20261029-fbe6249b` | 51003 | 66 | 66 | 0 | 52 | 14 | 9 |
| Control `cisco_aci_microburst` | `NS-20261029-070e812c` | 51010 | 14 | 14 | 0 | 10 | 4 | 3 |

Per-sourcetype **generated == indexed**, read back with
`index=* netspout_run_id="<run_id>" | stats count by sourcetype, index`:

- **A** — `pan:traffic` 25, `pan:threat` 13, `pan:system` 9 (47 total, all in
  `idx_network_ops`).
- **B** — `pan:traffic` 18, `pan:threat` 7, `pan:system` 7,
  `cisco:catalyst:security:events` 5 (37 events) plus 14 `sc4snmp:metric`
  records in `idx_performance_metrics`.
- **C** — `pan:traffic` 25, `pan:threat` 13, `pan:system` 9, Cisco 5 (52 events)
  plus 14 SNMP metric records.
- **Control** — `cisco:dc:aci:health` 5, `cisco:dc:nexus9k:syslog` 5, plus 4
  `cisco:ios:mdt` metric records. **Green after the dispatcher change**, which is
  the point of keeping a control.

### Metric value round-trip (names are not the bar; numbers are)
`scripts/verify_metric_value_roundtrip.py` replays the seeded scenario offline
**through the production payload builder** — so expected names already include
the dispatcher's own mapping, e.g. `queue_depth_bytes` → `queue_depth` — and
compares arithmetic means against `| mstats avg(*)` for that run_id.

| Run | metrics checked | all values match | worst relative error |
|---|---|---|---|
| B | 9 | **TRUE** | 2.6e‑16 |
| C | 9 | **TRUE** | 2.6e‑16 |
| Control | 3 | **TRUE** | 0.0 |

Observed metric names for B/C: `hrProcessorLoad`, `ifHCInOctets`,
`ifHCInOctetsRate`, `ifHCOutOctets`, `ifHCOutOctetsRate`, `ifInErrors`,
`ifOutErrors`, `ifSpeed`, `interface_utilization_percent`. No enumeration is
present, as intended.

### Raw format check on the indexed data
Splunk-side `_raw` for run A shows
`1,2026‑10‑29 13:08:01,001801000001,THREAT,spyware,…` — native CSV, 45
comma-separated threat fields, zero `LEEF`/`CEF` markers.

### Runs taken *after* the credential rotation

The four runs above were taken with the pre-rotation admin credential. Per the
no-reused-counts rule they are not treated as evidence that the current lab works
after §10. Two fresh runs close that gap, both with an environment that can only
supply the post-rotation credential (§3.6):

| Path | run_id | seed | generated | HEC accepted | Splunk read-back (independent query) |
|---|---|---|---|---|---|
| product API `POST /api/scenarios/run-with-destination` (A) | `NS-20261029-0ff65599` | 51031 | 47 | **47** (`state=ACCEPTED http=200` ×47) | **47 events** — `pan:traffic` 25, `pan:threat` 13, `pan:system` 9, all in `idx_network_ops` |
| driver, Cisco control (§6 guardrail) | `NS-20261029-f3f9d813` | 51040 | 14 | **14** | 10 events + 4 metric records, 3 names |

Product-API evidence: `pulseforge_phase4c_product_api_post_rotation.json`. Its
`dispatch_result_classes` field also records a small reporting trap worth naming:
this endpoint nests per-record transport status under `hec`, so aggregating the
top-level dict yields all-`None` — the same class of mistake as §3.5, one layer
deeper. Aggregations must read `dispatch_results[*].hec.state`.

Metric values for the post-rotation control run round-trip **exactly** (`buffer_utilization`
56.025, `egress_drops` 1420.0, `queue_depth` 14512500.0, worst relative error
`0.00e+00`, `n=4` per name) — `pulseforge_phase4c_cisco_metric_values.json`.

So neither the product's own run path nor the Cisco baseline depends on a
credential that no longer exists, which is the guardrail §10 was worth doing for.

### Regression methodology (four passes, one bad diagnosis of my own)
A first full-suite pass was killed mid-run: I re-registered the catalog and
re-synced mirrors *while pytest was executing*, so its fixtures changed
underneath it and ~20 failures appeared by 15% progress. Those results are
uninterpretable and were thrown away rather than explained.

A second pass (09:59) produced 88 failures in the after tree and I recorded it
as **invalid** on the theory that I had launched pytest without sourcing
`backend/.env`, so the live-lab tests were failing on missing credentials rather
than on code. That theory was testable, and it is wrong:

| Claim I made | What that log actually shows |
|---|---|
| "live-lab tests had no credentials → 401 / `RuntimeError` paths" | `401` × **0**, `Unauthorized` × **0**, `RuntimeError` × **0** |
| "the run is therefore contaminated" | its 88 failure ids are **set-identical** to the properly credentialled 10:23 rerun |

The credential helper raises a distinctive message when the lab password is
absent —

```
RuntimeError: Splunk management credentials are not configured: set
NETSPOUT_SPLUNK_PASSWORD (or SPLUNK_PASSWORD) in the environment
```

— so a genuinely credential-less run *would* leave a fingerprint, and this one
leaves none. What it does contain is 38 `gnmic` and 13 `tshark` mentions: binaries
that are simply not installed on this Mac.

Correcting the record, the four passes are:

| Pass | Log | Verdict |
|---|---|---|
| 1, 09:28 | `pf_suite.log` | **Invalid** — catalog re-registered and mirrors re-synced *while pytest was executing*; fixtures changed underneath it; stopped at ~18% |
| 2, 09:59 | `pf_suite_clean.log` | **Valid** — a repeat, not a contaminated run |
| 3, 10:23 | `pf_after2.log` | after tree, credentials exported |
| 4, 10:23 | `pf_base2.log` | baseline at `ce87042` in a detached worktree, `--rootdir` pinned there, same interpreter (`.venv-test`, pytest 9.1.1, no plugin autoload) and same credential environment |

Passes 2 and 3 agreeing exactly is worth keeping as a control rather than
discarding: **the after tree's failure set reproduces identically across two
independent 22-minute runs**, which is what makes a 13-id difference against the
baseline meaningful instead of noise.

Failure distribution in the after tree, by file — a map of where the
environment-dependent tests live: 25 `test_gate13d_gnmi_splunk_e2e`,
11 `test_gate13c_gnmi_collector`, 9 `test_gate12d_snmp_splunk_e2e`,
7 `test_gate8_unified_evidence`, 7 `test_gate9_5_telemetry_semantics`,
5 `test_gate13e_customer_acceptance`, 4 `test_gate12f_snmp_productization`,
2 each `test_gate4_contract`/`test_gate11f_governance_closure`/
`test_gate10_6_namespace_reconciliation`/`test_fallback_guard`, 1 each
`test_wave2_authentic_expansion`/`test_phase12_agentic_supply_chain`/
`test_native_discovery`/`test_gate13b_gnmi_core`/`test_gate12c_snmp_polling`/
`test_gate12b_native_snmp`.

### Regression result — failure-id diff, not counts

**Interim comparison (`pf_base2` vs `pf_after2`), taken before the five test
files were updated. It is superseded for the final verdict by the completed
`pf_after3` pass above (0 new ids); it is kept because its 13-id triage explains
the test updates the final pass then validated.**

Comparing the two **failure id sets** isolates regressions from pre-existing
breakage, which matters here because `ce87042` is 120 commits ahead of
`origin/main` on a public repo and nothing establishes that its suite was green
to begin with. Counts alone would be an unfair guardrail: the after tree adds
47 + 88 tests that HEAD cannot have. The claim this section supports is therefore
"no regression by failure-id comparison", not "the suite passes".

| Measure | Result |
|---|---|
| baseline (`pf_base2`) | 76 failed, 1,196 passed, 10 skipped, 2,114 subtests passed in 1,348.20 s → **76 ids** |
| after (`pf_after2`) | 88 failed, 1,278 passed, 10 skipped, 2,103 subtests passed in 1,347.37 s → **88 ids** |
| shared by both | 75 |
| **new in the after tree** | **13** |
| failing only at baseline | 1 |

One extraction trap worth recording: pytest prints subtest failures as
`SUBFAILED(scenario='…') tests/…`, not `FAILED …`. A first diff that matched only
`FAILED|ERROR` reported **7** new ids. Including the `SUBFAILED` lines — which are
the ones that say *which* scenario broke — gives the true **13**. Reading the
summary format instead of assuming it changed the answer.

All 13 trace to two deliberate product changes:

| Family | Ids | Why it moved |
|---|---|---|
| release availability guard | 7 — `test_fallback_guard`: `test_supported_generators`, `test_api_refusal` + 3 subtests, `test_refusal_precedes_run_creation` + 3 subtests | the test maintains a hand-written copy of `SUPPORTED_SCENARIO_IDS`; this work adds the three scenarios to the production frozenset (14 → 17), which is exactly what makes them runnable in the product |
| pinned maturity / catalog counters | 6 — `gate10_6` `test_03` and `test_05`, `gate11f` `test_01`, `wave2` `test_scenarios_37`, `native_discovery` cohort | "exactly 1 `E2E_VALIDATED`" is now 4; 50 catalog rows are now 53; the native cohort went 37 → 38 |

That last file needs its own paragraph, because bumping its number would have
**buried** a real finding. `test_native_discovery` selects scenarios whose id
starts with `network_`/`telco_` and asserts each has a dashboard and readiness
`Executable custom simulation`. `network_security_correlation` matches that prefix
by naming coincidence but is not a member of the executable incident pack, so it
has neither — the assertion after the count would have failed next. Instead of
changing the number I compared the prefix heuristic against the pack it stands in
for:

```
incident pack members  : 37
name-prefix cohort     : 38
pack - prefix          : []   (the heuristic had been a perfect proxy)
prefix - pack          : ['network_security_correlation']
every pack member has a dashboard and the expected readiness : True
```

The cohort is now defined by its authoritative source, `incident_contracts()`,
plus a new assertion that every pack incident actually appears in the projection.
Same guarantee for all 37 incidents, one false positive removed, and the
invariant left true rather than renegotiated.

**These are test edits that make my own changes pass, so they deserve suspicion.**
What keeps them honest: the availability guard still refuses the remaining 36
catalog scenarios (`test_refusal_precedes_run_creation` passes for every one of
them after the update); the maturity sets changed only by the three ids §6–§7
evidence; and each updated site names its evidence in a comment. In one such
comment I first wrote that the run ids are "recorded on the catalog rows
themselves" — checked, and **false**: those rows carry a `maturity` label and no
`evidence_run_id`. The comment now states where the evidence really lives, and
that gap is exactly Phase 4D story C-3.

The single baseline-only failure is a genuine **fix**: `test_gate2_canonical`
`::test_02_zero_drift_guardrail` fails at `ce87042` — the canonical catalog and
its mirrors had already drifted in committed history — and passes in this tree
after `scripts/sync_core.py` re-synced them (1 passed, run alone).

So that "environmental" is a measurement rather than a label, here is what the 75
shared failures actually are. None of them is credential-related:

| Signal | Mentions in the after log |
|---|---|
| `gnmic` — binary absent | 38 |
| `tshark` — binary absent | 13 |
| HTTP 401 / `Unauthorized` / credential-resolution `RuntimeError` | **0** |

Representative reason per shared file: `gate13d` `AssertionError: 'FAIL' !=
'PASS'` (gNMI end-to-end, needs `gnmic`); `gate4` `AttributeError: 'dict' object
has no attribute 'topology_id'`; `gate8` `KeyError: 'hec'` and `TypeError:
'NoneType' object is not subscriptable`; `gate9_5` `AssertionError:
'telemetry_model' not found in {…'ub1_ot_proxy_host_hunt'…}` — a pre-existing
completeness gap in the `ub*` universe scenarios, identical at HEAD and unrelated
to this work. No suite failure in any of the four passes is credential-related:
the only `401`s this task produced are the deliberate post-rotation probe proving
the old admin password dead, and the stale build-time password behind §3.6 — and
a bare `grep -c 401` returns 1–2 hits per log for exactly that reason (a test's
*line number* 401, a gRPC timestamp `10:01:21.401118`, a SHA fragment
`8c432f4016`), none of them an HTTP status.

The five test updates are verified directly in the final tree: re-running the 13
previously-new ids as standalone nodes gives **8 passed, 107 subtests passed**,
and re-running the five files together gives **54 passed, 129 subtests passed
and the single failure `test_gate11f::test_03_p2_manage_collector_preflight…`,
which fails identically in the baseline log** — it is one of the 75 shared
pre-existing ids, not a regression. (The earlier interim note of "28 passed,
116 subtests" counted a narrower subset and is superseded by the numbers above;
it is recorded here so the correction stays visible.)

### Final clean full-suite pass (`pf_after3.log`, 2026-10-29)

A completed after-tree run, same interpreter and environment as the baseline
(`.venv-test`, pytest 9.1.1, `python -m pytest`, `PYTHONPATH=src:backend`, no
plugin autoload, credentials from `backend/.env`), catalog untouched during the
run, **22 min 28.8 s**:

| Measure | Result |
|---|---|
| baseline (`pf_base2`, detached worktree at `ce87042`) | 76 failed, 1,196 passed, 10 skipped, 2,114 subtests passed, 1,348.20 s |
| **final after tree (`pf_after3`, this working tree)** | **75 failed, 1,285 passed, 10 skipped, 2,120 subtests passed, 1,348.84 s** |
| shared failure ids | 75 |
| **new failure ids in the after tree** | **0 — no regressions** |
| failing only at baseline | 1 (`test_gate2_canonical::test_02_zero_drift_guardrail` — the committed mirrors had already drifted in history; the re-synced tree **fixes** it, which is why it appears in the baseline set only) |

### 7.1 The product path (what the UI actually calls) — verified
The baseline finding was that the UI path had never been exercised. It now has
been, end to end, against the running FastAPI app rather than the driver script:

```
POST /api/scenarios/run-with-destination
     {"scenario_id":"network_security_correlation","seed":51021}
```

| Step | Observed |
|---|---|
| Endpoint | HTTP 200 in 1.8 s |
| `GET /api/scenarios` | 53 scenarios; all three new ids present with `maturity=E2E_VALIDATED`, 5 phases each — the catalog registration is visible **to the product**, not just to the file |
| Manifest | `run_id NS-20261029-a633f222`, generated 51, attempted 51, **succeeded 51**, failed 0, `hec states {ACCEPTED: 51}` |
| Splunk, events | `pan:traffic` 18, `pan:system` 7, `pan:threat` 7, `cisco:catalyst:security:events` 5 = **37** in `idx_network_ops` |
| Splunk, metrics | **9** `avg(*)` columns round-tripped from `idx_performance_metrics` |

Same per-sourcetype shape as the driver run for B (`NS-20261029-58818c7d`),
reached through different code: the API resolves the destination via
`DestinationManager`, dispatches, then observes. The two runs are counted
separately and neither number supports the other.

### What is *not* claimed
- Runner-internal `overall_validation` reports `BLOCKED` /
  `observation_status: OBSERVATION_PENDING` on these runs, because the contracts
  declare no `ValidationRule` objects. The counts above come from the driver's
  independent Splunk queries, not from the runner's self-assessment. Adding
  per-scenario validation rules is Phase 4D work (C-1/C-3), not something to
  paper over here.
- `run_id` cannot be injected (the engine stamps `NS-YYYYMMDD-<uuid8>`), so
  reproducibility holds for **telemetry values**, not for run identifiers.
- The **product API** path is verified (§7.1). The **browser** was never opened:
  no `PulseForge Command Center` rendering, layout or interaction was checked, so
  **no visual or "renders correctly" claim is made anywhere in this report** (§8).
  "The API the UI calls works" and "the UI displays it correctly" are different
  claims, and only the first is supported here.

## 8. UI

The Figma-derived **PulseForge Command Center** was left untouched — no
component changes, no rename, no "Mission Control". Scenario discoverability in
the UI was not browser-verified in this session; the three new scenarios are
registered in the canonical catalog and mirrored, which is a necessary condition
for listing, not proof of rendering.

## 9. Status Table

The first column is a section **in this report**, not the mission's item numbering
(the mission numbered the Phase 4D plan as §8 and this table as §9, so a shared
column would have been ambiguous).

| Report § | Item | Status |
|---|---|---|
| §1 | Truthful baseline of the Phase 4C claims | **DONE**, with two self-corrections recorded in §1 |
| §2 / §10 | Credential cleanup — HEC tokens | **DONE**, both exposed tokens return HTTP 403 |
| §2 / §10 | Lab admin password | **ROTATED AND INVALIDATED** — old credential HTTP 401, live value only in gitignored `backend/.env` |
| §3.1 | `DestinationManager` CWD defect | **FIXED**, 3-CWD test passing |
| §3.2 | Dispatcher metric routing (Cisco-only, relabelling) | **FIXED**, catalog-driven + regression tests |
| §3.3 | Stale `cisco_mdt_metrics` defaults across 6+ files | **FOUND, NOT CHANGED** — flagged for own decision |
| §3.4 | 8 non-canonical `paloalto:*` entries living only in a stale mirror | **RESOLVED** by `sync_core.py`; resolver self-test moved to canonical `pan:*` |
| §3.5 | Enabled destination carrying a revoked credential (stale process env) | **DIAGNOSED**, proven by process-env comparison; backend restarted; hardening deferred to Phase 4D |
| §3.6 | Validation helper scraping the container's build-time password | **FIXED** — environment-only resolution, clear error when unconfigured, no scrape left in the tree |
| §4 | PAN native CSV generator, 54/45/17, count-exact, deterministic, canonical | **DONE** — 47 unit tests |
| §4 | PAN wired into registry/dispatcher/runner | **DONE** — live run A |
| §5 | Typed SNMP OID set (12 generatable / 333 inventoried) | **DONE** — 88 unit tests |
| §5 | Counter/gauge/enum separation, wrap + reset | **DONE**, 2 real bugs found and fixed |
| §5 | SNMP through existing HEC metric path | **DONE** — runs B/C, values round-trip |
| §6 | Scenario A / B / C registered and runnable | **DONE** — `E2E_VALIDATED`, 4 mirrors |
| §6 | AI/LLM RAG degradation scenario | **NOT BUILT** → Phase 4D |
| §7 | Fresh Cisco control regression | **GREEN** — pre-rotation `NS-20261029-070e812c` and post-rotation `NS-20261029-f3f9d813` (14/14/10 + 3 metric names, values exact) |
| §7.1 | Product API path (UI's actual call) → runner → HEC → Splunk | **VERIFIED** — 51/51 accepted, 37 events + 9 metric columns observed |
| §7.2 | Product API path **after** rotation | **VERIFIED** — `NS-20261029-0ff65599`, 47/47 accepted, 47 indexed (25/13/9) |
| §7 | Full-suite regression, baseline vs after by failure id | **COMPLETE — 0 regressions.** Final pass `pf_after3`: 75 failed / 1,285 passed / 10 skipped / 2,120 subtests in 1,348.84 s; failure-id diff vs `pf_base2` (76 ids): 75 shared, **0 new**, 1 baseline-only (the drift guardrail this tree fixes). Interim `pf_after2` run (88 ids) was pre-test-update and is retained only as the repeat-control pair with `pf_suite_clean` |
| §8 | Command Center browser rendering | **NOT DONE** — no visual claims; API ≠ UI rendering |
| §10.1 | Secret state of the outgoing tree | **CLEAN — after a documented correction.** A re-verification with exact-value needles found 6 residues of the *retired* admin password in 5 files (prose/auth-header contexts invisible to the earlier assignment-pattern scan); all 6 are sanitised and the targeted re-test re-passed (§10.1). No credential anywhere in history, tree or docs authenticates today |
| §11 | Phase 4D plan + v1.0 scorecard (mission item 8) | **DONE** — `pulseforge_phase4d_implementation_plan.md` |
| §10.1 | Push / PR / merge | **NOT EXECUTED.** No longer blocked by an active exposed credential; still held for review of the outgoing changes and an explicit decision |

## 10. Credential Exposure — Handled, Not Redesigned

**Resolved 2026‑10‑29.** The lab admin password that was present in tracked files
is no longer a working credential.

Executed through Splunk's own authentication layer, which is the correct place
for it (§0) — PulseForge has no admin account of its own to rotate:

```
POST /services/authentication/users/admin
     password=<new>  oldpassword=<current>        -> HTTP 200
```

| Check | Result |
|---|---|
| Pre-condition: old credential authenticated | HTTP 200 |
| Pre-condition: `content.type` | `Splunk` — native scheme, required; password change is unsupported on non-native schemes |
| Rotation call | HTTP 200 |
| **Old (exposed) credential** on `/services/server/health` | **HTTP 401 — invalidated** |
| New credential | HTTP 200 |
| `roles` after change | `['admin']`, unchanged |
| `locked-out` | `False` |
| Persistence | new value written to untracked, gitignored `backend/.env`, key set preserved, mode `0600` |

Two details matter more than the outcome:

1. **The first attempt failed safely.** `POST` with only `password` returned
   `400 Missing old password.` — a self-change requires `oldpassword`. The script
   was written to abort before touching `backend/.env` unless rotation returned
   200 **and** the old credential stopped working, so a failed attempt left the
   lab and the env file byte-identical. That ordering is why this could be
   attempted at all.
2. **The four earlier "blockers" were never blockers for this path.** They were
   all CLI or file-ownership failures (`var/log/*`, `splunkd.pid`,
   `users.ini`, `splunk.secret`, the validation temp dir) caused by executing as
   a user other than the one splunkd runs as. splunkd writes those files itself.
   The mistake was generalising "we cannot write Splunk's files" into "we cannot
   rotate the password".

This is exposure housekeeping. It did **not** change PulseForge's authentication
design, and nothing in §3–§7 depends on it: the product still authenticates as
whatever Splunk user is in context, and gains nothing new in the way of
credentials.

### 10.1 Secret state of the outgoing tree

| Item | Status |
|---|---|
| Exposed lab admin password | **dead — re-verified today** (HTTP 401 on `/services/server/health` with the exact value recovered from history; current value HTTP 200) |
| Pre-rotation HEC token #1 (`1379bbf9…`) | **dead — re-verified today** (HTTP 403 on the collector with a token-validating request; current token passes auth with HTTP 400 on an empty payload) |
| Pre-rotation HEC token #2 (`86eafae9…`) | invalidated per the cleanup pass (403 claimed); its **full value is not recoverable from Git history or the tree** (it was never committed), so no historic live test is possible today — only the 8-character prefix remains, in 2 verification docs |
| Live admin password + current HEC token location | only `backend/.env`, gitignored (`.gitignore:41`), mode 0600 |
| Credential-shaped literals in tracked docs | 2 initially neutralised (`QUICKSTART.md`, `SECURITY.md` examples), **then 5 more files corrected 2026‑10‑29 ~13:10 after a re-verification found residuals** — see below |
| Remaining literals in tracked code | all fake fixtures — `correct-password` / `invalid-password` gRPC auth pairs, `netspout-lab` username, `dummy*` test secrets |
| Broad scan | 2,045 tracked files scanned for `password/secret/token/api_key/authorization` **assignments**; the only non-fake matches are SPL dashboard `$token$` definitions in `default/data/ui/views/*.xml`, which are not credentials. **Limitation: this assignment-pattern scan cannot see prose, table and auth-header contexts** — the correction below was found by an exact-value (known-needle) scan instead |
| Git history | **not** rewritten. History contains dead credentials only: the retired admin password and one full HEC token literal remain in published commits and **are verified inactive** (401 / 403) |

**Outgoing-tree correction (2026‑10‑29 ~13:10).** A re-verification that greps for
the *literal value* recovered from history — not an assignment regex — found 6
residual occurrences of the retired admin password in the outgoing tree, in prose
and auth-header contexts the earlier scan's pattern could not match:

| File | Location | Treatment |
|---|---|---|
| `docs/QUICKSTART.md` | line 23, "Login: `admin` / …" | placeholder `<your-splunk-admin-password>` |
| `docs/SECURITY.md` | lines 15 and 50 | placeholders |
| `docs/acceptance/GOLDEN_PATH_02_CAMPUS_ROGUE.md` | line 48, Basic Auth template | placeholder |
| `scripts/run_phase13_release_audit.py` | line 117 — the scanner's own needle embeds the literal | needle moved to `PF_LEGACY_LAB_SECRET_PATTERN` env; the committed pattern matches only the all-zero token |
| `tests/test_gate1_runtime.py` | lines 239–240, hard-coded Basic Auth | resolved from `NETSPOUT_SPLUNK_PASSWORD`/`SPLUNK_PASSWORD`, skips when unset (re-ran: 5 passed, 1 skipped — same shape as the full-suite snapshot) |

The §11.1 pre-rotation pass's "clean" table is correspondingly superseded: those
five files did contain the value, the earlier needle-set missed them, and the
current tree is clean only after this correction.

Publication is therefore no longer blocked by an active exposed credential —
**every credential that appears in published history or the outgoing tree is
verified dead** (401 / 403 today). It is still held for an outgoing-change
review, and pushing is a separate decision: the sanitisation above is staged
but uncommitted, and the branch is 120 commits ahead of `origin/main` on a
public repository.

## 11. Artifacts

| File | Contents |
|---|---|
| `pulseforge_phase4c_recovery.md` | this report |
| `pulseforge_phase4c_recovery.json` | machine-readable status + evidence index |
| `pulseforge_phase4c_credential_cleanup.md` | §2 credential pass |
| `pulseforge_phase4d_implementation_plan.md` | §9 Phase 4D design, backlog, scorecard |
| `pulseforge_phase4c_product_api_post_rotation.json` | post-rotation product-API run: 47/47 accepted, 47 indexed per sourcetype |
| `pulseforge_phase4c_cisco_control_regression.json` | Cisco control run — **now holds the post-rotation `NS-20261029-f3f9d813`**; the same filename previously held pre-rotation `NS-20261029-070e812c`, whose counts survive only in §7's table |
| `pulseforge_phase4c_cisco_metric_values.json` | post-rotation control value round-trip, `all_values_match: true` |
| `pulseforge_phase4c_pan_threat.json` | scenario A live evidence |
| `pulseforge_phase4c_xsrc_correlation.json` / `…_xsrc_metric_values.json` | scenario B events + value round-trip |
| `pulseforge_phase4c_payment_degradation.json` / `…_payment_metric_values.json` | scenario C events + value round-trip |
| `scripts/phase4c_control_run.py` | acceptance driver |
| `scripts/verify_metric_value_roundtrip.py` | expected-vs-observed metric value check |
| `scripts/verify_destination_path_resolution.py` | §3.1 fix proof |
| `scripts/register_phase4c_scenarios.py` | canonical scenario registration |
| `scripts/pf_lab_query.py` | read-only lab search/HEC helper; §3.6 credential-resolution fix |
| `tests/test_pan_os_native_generator.py` (47) · `tests/test_snmp_metric_typed_generation.py` (88) | contract tests |
| `scripts/build_recovery_status_json.py` | regenerates the recovery JSON from these artifacts; refuses to write credential values |
| `/var/tmp/pf_base2.log` · `/var/tmp/pf_after3.log` | baseline suite log and the **completed** after-tree full-suite pass (session scratch, not committed); `pf_after2.log` is the superseded pre-update interim run kept as the repeat-control pair with `pf_suite_clean.log` |

### 11.1 Known-value scan of the whole worktree (pre-rotation pass)

`§10.1` records the **current** secret state after rotation; this subsection is
the earlier pass kept for provenance, because it scanned values that no longer
exist anywhere but Git history.

Run over the whole worktree (tracked **and** untracked, excluding `.git`,
virtualenvs and `__pycache__`) for every known credential value — live admin
password, live HEC token, both revoked HEC token UUIDs, and the stale base64
`admin:<password>` blob:

| Needle | Hits outside `backend/.env` |
|---|---|
| live admin password | **clean** |
| live lab HEC token | **clean** |
| revoked token UUID #1 | **clean** |
| revoked token UUID #2 | **clean** |
| stale base64 credential pair | **clean** |

`git check-ignore -v` confirms `backend/.env` is ignored by `.gitignore:41`, so
it cannot enter a commit.

Two hits were found and fixed during this pass, both in my **own** reports: this
JSON initially carried the two revoked token UUIDs in full, and
`pulseforge_phase4c_credential_cleanup.md` carried the decoded base64 pair. A
revoked value is not a live secret, but publishing credential-shaped material in
a document headed for a public repository is the same habit that created this
problem, so both are now withheld — the cleanup report keeps truncated prefixes
only, and the JSON records `hec_old_tokens_invalidated: 2` with a note pointing
at the report. Tests use obviously fake tokens (`offline-replay-no-credential`,
`"x"`).

## 12. What changed the meaning of "Phase 4C complete"

The commits that claimed completion were not lying about *files existing*. Every
named artifact was present. What they got wrong is a distinction worth keeping
in the project's vocabulary, because it is what let the claim survive review:

- A **generator** that no runner calls produces nothing observable. Both the PAN
  and SNMP modules were importable, tested-looking, and unreachable.
- A **count** copied from an earlier artifact is not a measurement. The
  "exact match" line was evidence of the previous run, not this one.
- A **catalog entry** describes an intent. It is not proof of ingestion, and the
  "8 Palo Alto sourcetypes" were real rows in a stale mirror nobody searched.
- An **index name in a config** is not where the data landed. `splunk_storage`
  in the catalog is descriptive; only the dispatcher and destination manager
  decide routing, and both were wrong in ways §3 documents.
- A **credential in a source file is not configuration**, and a credential that
  happens to still work is not evidence that the design is sound. §3.5 and §3.6
  are the same mistake seen from two directions: an ambient secret bound once at
  import, and a secret scraped from a dev container that no longer owns it.
  Closing the exposure meant rotating one value through Splunk's own
  authentication API — it did **not** mean inventing application identity, which
  §0 says PulseForge must never own.
- A **reason I invent for a failing run is also a claim**, and it can be wrong in
  a way that costs me evidence. I labelled a full-suite pass invalid because I
  believed it had been launched without credentials; the log turned out to contain
  no 401 and no credential `RuntimeError`, and its 88 failure ids matched the
  properly credentialled rerun exactly. Only comparing the two logs caught it —
  quoting the first one would have left the story standing. The correction is in
  §7, and the accidental gain is a reproducibility control I had already decided
  to throw away.

Phase 4D's §7 verification contract exists specifically so those four failures
cannot be reported as success again, and its §4.3 identity boundary exists so the
fifth cannot come back as a "feature".

