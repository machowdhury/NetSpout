# NetSpout PulseForge — Phase 4D Implementation Plan

**Status:** Design, backlog and acceptance criteria only. No Phase 4D code is
included in the Phase 4C recovery branch.
**Written:** 2026-10-29
**Depends on:** Phase 4C recovery (§1–§9 report), which establishes the
integration pattern Phase 4D extends rather than reinvents.

---

## 1. Why Phase 4D exists

Phase 4C proved a repeatable path for a vendor source:

```
typed generator  ->  canonical catalog contract  ->  ScenarioRunner branch
                 ->  TelemetryDispatcher         ->  HEC
                 ->  index/mstats                ->  counted, value-checked evidence
```

What Phase 4C could *not* do is let a customer add a source that the project has
not hand-built. Every sourcetype in `catalog/sourcetypes.json` was authored by a
human against a vendor document and pinned with a frozen sample. That is correct
for the golden path and hopeless as a growth model — it does not scale past the
vendors the team already knows.

Phase 4D replaces "file a request and wait for a release" with a governed
in-product authoring flow, without letting that flow become a remote-code
execution surface.

## 2. Goals

1. A user can define a **custom data source profile** (source, sourcetype,
   field extractions, index routing, entity model) without editing `props.conf`
   or shipping an app.
2. A user can upload a **small sample of events** and immediately see how the
   platform parsed them, before anything is saved.
3. A user can **inspect** an installed add-on's knowledge objects read-only and
   reuse its extraction logic as a starting point.
4. Profiles are usable by the existing generators and scenarios: a custom source
   becomes eligible for the same runner→HEC→Splunk verification that governs
   built-in sources.
5. Optional AI assistance for extraction suggestion — strictly advisory, never
   auto-applied, never auto-saved.

## 3. Non-goals (deliberate)

- **No execution of uploaded or user-authored code.** No `import`, no `eval`, no
  subprocess against uploaded content, no "custom command" plugin that runs in
  the search head. This is the defining constraint of the phase; see §5
  invariant 1.
- **No PulseForge-owned identity.** No application login screen, no default
  admin account, no product password, no session store of its own. Splunk owns
  authentication, account lifecycle and RBAC (§4.3). A builder feature that
  needed "the PulseForge password" would be a design defect, not a setting.
- No bulk event storage in the KV Store. Samples are exemplars, not data.
- No secrets in the KV Store (see §5 invariant 3 — this already has a precedent
  to fix).
- No replacement of App Cert / `splunk add-on` packaging. The builder produces
  *platform configuration*, not a shippable TA.
- No claim that a custom profile is "verified" on the strength of existing
  events in the index. Verification means the §7 evidence contract.

## 4. Architecture

### 4.1 Components

| # | Component | Responsibility | Lives in |
|---|---|---|---|
| 1 | `source_profile_store` | CRUD for profiles, `enforceTypes` schema, size caps | KV Store collection |
| 2 | `sample_ingest` | Validate + parse an uploaded sample in-memory, return extraction results | backend FastAPI route |
| 3 | `ta_inspector` | Read-only enumeration of installed TA knowledge objects | REST `configs/props`/`configs/transforms` reads |
| 4 | `profile_translator` | Profile → props/transforms-shaped dict the engine already understands | `src/netspout_core/` |
| 5 | `custom_sourcetype_bridge` | Register a profile into the catalog *as a distinct, labelled kind* | `catalog/` + runtime |
| 6 | `ai_extract_advisor` (optional) | Suggest extractions from a sample; output is a proposal object | backend, feature-flagged off by default |

Nothing in the list runs user code. Component 4 emits **declarative**
structures only: regex, delimiter lists, field aliases, lookups. If a proposed
profile cannot be expressed declaratively, the builder rejects it with an
explanation rather than escalating to executable code.

### 4.2 Profile schema (`netspout_source_profiles`)

```ini
[netspout_source_profiles]
enforceTypes = true
field.profile_id        = string
field.display_name      = string
field.vendor            = string
field.sourcetype        = string
field.data_kind         = string        # event | metric
field.category          = string
field.status            = string        # DRAFT | VALIDATED | VERIFIED
field.extract_sha       = string        # checksum of the declared extraction set
field.field_names       = string        # JSON array, bounded
field.sample_ref        = string        # id into the *bounded* sample store
field.created_at        = time
field.updated_at        = time
field.created_by        = string
field.evidence_run_id   = string        # empty until a live run proves it
replicate = true
```

`status` is the load-bearing field. A profile **starts** at `DRAFT` and cannot be
promoted by the user typing. `VERIFIED` is only written by the verification
runner after it observes the events in Splunk. This makes §7 mechanically
enforced rather than a policy document.

### 4.3 Platform and identity boundary

PulseForge is a **Splunk-native application**. This is the frame the Custom Data
Source Builder is built inside, and it decides several design questions before
any code is written:

| Question | Answer that binds Phase 4D |
|---|---|
| Who authenticates the user? | Splunk. The builder runs in the **authenticated Splunk user's context** and never collects a username or password of its own |
| Who creates admin accounts / changes passwords? | Splunk, through its own accounts and RBAC. PulseForge has no admin account, no default credential, no product password |
| How is access to builder endpoints controlled? | Splunk roles and capabilities. A profile write needs an explicit capability; reads follow `power` (§5 invariant 7, story D-3) |
| Where do persisted secrets live? | Splunk's supported secure storage (`storage/passwords`), referenced **by name**. KV Store holds `credential_ref`, never a value (§5 invariant 3, story D-1) |
| Where do profiles and generation metadata live? | KV Store collections (`netspout_source_profiles`, plus the metadata fields in §4.2) — configuration and metadata only, no bulk events, no secrets |
| How does a user point PulseForge at their own HEC endpoint? | As a **user-configured destination** inside Splunk, with the token taken from secure storage. No hardcoded token in source, catalog or app defaults |
| Is Docker part of the product? | No. Docker is a development and testing harness. The lab's initial Splunk password is disposable lab configuration; nothing may read it as application configuration, and no feature may require a container, a second login or a PulseForge-specific password |
| What about credentials already leaked in Git history? | A housekeeping/security item, closed by rotation and invalidated in the live lab. It is **not** a reason to redesign product authentication (see the recovery report §10) |

Two failure modes this boundary is meant to prevent, both observed during
Phase 4C:

1. A validation helper scraped `SPLUNK_PASSWORD` out of the **running container**,
   which is the build-time value and stays stale after a rotation — treating the
   dev harness as the source of truth for who can log in (recovery report §3.6).
2. A destination read its token from the process environment **once at import**,
   so a long-lived server kept reporting `enabled=True` while every dispatch was
   rejected with a dead token (recovery report §3.5).

The product answer to both is the same: secrets are user-configured inside
Splunk and resolved per use from supported storage, so there is no ambient
credential to go stale.

## 5. Security invariants

These are acceptance criteria, not guidelines. Each needs a test.

1. **No execution.** Uploaded files are never written to a path on `bin/`,
   `lib/`, `appserver/` or any directory on `sys.path`. The upload handler keeps
   bytes in memory, parses, discards. A test asserts that no uploaded byte is
   ever reachable by the interpreter (see A-4).
2. **Read-only TA inspection.** Only `GET` against
   `/servicesNS/-/-/configs/conf-props`, `/configs/conf-transforms`,
   `/services/saved/searches`. No POST, no reload, no restart, no `btool`
   subprocess. A test asserts zero mutating calls.
3. **No secrets in KV Store.** **Existing defect to respect and not repeat:**
   `netspout/default/collections.conf` currently declares
   `netspout_config.hec_token = string`, i.e. the KV Store is designed to hold a
   live collector token. Phase 4D must not extend that pattern. Remediation
   story D-1 moves credential material to `storage/passwords` (Splunk's
   encrypted credential store) and leaves only a *reference name* in KV Store.
   The builder stores `field.credential_ref = string`, never a value.
4. **Sample volume cap.** Hard cap 100 events and 256 KB per upload, enforced
   server-side *before* parsing. Rejection returns a machine-readable reason.
5. **No PII retention.** Samples are retained only while a profile is `DRAFT`
   and are deleted on promotion to `VALIDATED` or on a 24-hour TTL. Redaction is
   applied to any sample surfaced in a preview.
6. **Injection surface.** Every user-authored regex is bounded (length cap,
   no nested quantifier patterns that risk catastrophic backtracking) and is
   executed against a *sample*, never against indexed data, under a wall-clock
   timeout. Timeout exhaustion is a validation failure, not a retry.
7. **Authorization.** Profile create/update requires an explicit capability;
   read is available to `power`. No anonymous writes. Authorization is checked
   against the **Splunk** role of the calling user — the app never consults its
   own notion of a user.
8. **No application-owned credential.** No endpoint, setting, config file,
   catalog entry or default accepts a PulseForge username/password, and nothing
   in the product reads a lab container's environment variable as configuration
   (§4.3). Development credentials stay in the environment of a disposable lab
   and are named explicitly in code (`os.getenv`), never embedded. Story D-5
   proves it.

### 5.1 AI is optional and cannot write

If enabled, `ai_extract_advisor` returns `List[ExtractionProposal]`. Each
proposal must be individually previewed against the sample by the user and
individually accepted. There is no `apply_all`. Prompt content is treated as
untrusted input; the advisor never receives a full event stream, only the
already-redacted sample within the §5 invariant 4 caps. Output is validated by the same
declarative-only parser as a human-authored profile, so a malicious or malformed
model response cannot smuggle executable intent.

## 6. Reuse of existing machinery

Phase 4D should feel like configuration, not a new subsystem. Concretely:

- `catalog/sourcetypes.json` gains a `provenance` field: `VENDOR_DOCUMENTED`
  (today's hand-authored entries) vs `USER_DEFINED`. UI and reporting must show
  the difference; a user-defined entry is never rendered with the same badge as a
  vendor-documented one.
- `scripts/sync_core.py` propagates canonical catalog changes to the mirrors —
  custom profiles must **not** be merged into the tracked catalog (they are
  environment state, not source). They load from KV Store at runtime and are
  merged in memory only.
- The `data_kind` classification introduced as the dispatcher's routing rule in
  Phase 4C (`is_metric_sourcetype`) is what makes a custom *metric* source work
  with zero new routing code. A profile declaring `data_kind = metric` routes to
  `hec_metric_index` automatically.
- `TelemetryTransportConfig` and `DestinationManager` handle destination
  selection already; profiles reference an index name, never a URL or token.

## 7. Verification contract (what "verified" is allowed to mean)

Borrowed verbatim from the Phase 4C recovery lesson, and stricter:

A profile reaches `VERIFIED` only when all are true for one recorded run:

1. It was generated through `ScenarioRunner` (or a companion `ProfileRunner`),
   not a standalone script.
2. `dispatch_succeeded == dispatch_attempted`, with HEC rejections listed.
3. Observed event count in Splunk equals expected per-sourcetype count
   (`stats count by sourcetype, index`), reported as *observed*, never as
   "generated".
4. For metric profiles, expected-vs-observed **values** round-trip within
   tolerance — names alone are insufficient (a wrong number with the right
   name is the failure mode that hid the Phase 4C defects).
5. `evidence_run_id` is written to the profile, and historical counts may never
   be reused as evidence for a later claim.
6. Credential resolution is explicit: the run takes its destination from
   user-configured storage (`storage/passwords`, by reference) or from a named
   environment variable in a disposable lab — never from a scraped container
   value, and never from a credential retained in a long-lived process after a
   rotation (recovery report §3.5, §3.6). A verification run whose transport
   secret cannot be traced to one of those two sources is not a verification run.

Catalog presence, UI listing, passing unit tests, or a `200` from HEC are each
explicitly **not** verification.

## 8. Backlog

Sizes: S ≤ 2 days, M ≤ 1 week, L ≤ 2 weeks.

### Stage A — Safe foundation (must land first)

| ID | Story | Size | Acceptance criteria |
|---|---|---|---|
| A-1 | Add `netspout_source_profiles` collection + `provenance` field on catalog entries | S | `collections.conf` with `enforceTypes`; existing 100+ sourcetypes still resolve; new lookups return `VENDOR_DOCUMENTED` |
| A-2 | `profile_translator`: profile → declarative props/transforms dict | M | Round-trip test: authored profile equals re-parsed translation; unsupported constructs raise, never fall back to code |
| A-3 | Read-only `ta_inspector` | M | Enumerates props/transforms of an installed TA; test asserts no mutating REST verb is issued; works with no TA installed |
| A-4 | Upload path with no execution | M | Sample parsed in memory; test proves upload bytes are never on `sys.path`, never written under `bin/`/`lib/`; file is discarded after parse |
| A-5 | Caps + redaction before any parse | S | 101st event rejected with reason; 257 KB rejected; preview shows redacted identifiers |

### Stage B — Builder UX

| ID | Story | Size | Acceptance criteria |
|---|---|---|---|
| B-1 | Profile create/edit form in PulseForge Command Center | M | Saves as `DRAFT`; no index writes occur from the form |
| B-2 | Live extraction preview against uploaded sample | M | Shows per-field parsed values; regex timeout surfaces as inline validation error |
| B-3 | "Start from an installed TA" flow | M | Copies declarative extractions only; executable helpers are listed but not copied, with a note explaining why |
| B-4 | Event vs metric profile selection driving routing | S | Metric profile lands in the metrics index with zero new dispatcher code (proves the Phase 4C `data_kind` rule) |

### Stage C — Verification integration

| ID | Story | Size | Acceptance criteria |
|---|---|---|---|
| C-1 | `ProfileRunner` executing a profile through the real dispatcher | L | Produces a `run_id`-stamped artifact equivalent to `phase4c_control_run.py` output |
| C-2 | Value round-trip check generalized from `verify_metric_value_roundtrip.py` | M | Expected from offline replay through the production payload builder; observed from `mstats`; exit non-zero on any mismatch |
| C-3 | Promotion `DRAFT → VALIDATED → VERIFIED` written only by the runner | M | UI cannot set `VERIFIED`; test asserts a forged write is rejected |
| C-4 | Show custom profiles in coverage reporting, separated by provenance | S | Scorecard distinguishes vendor-documented, user-defined, and verified-user-defined |

### Stage D — Cleanup and hardening

| ID | Story | Size | Acceptance criteria |
|---|---|---|---|
| D-1 | Remove `hec_token` from `netspout_config` KV Store design; use `storage/passwords` + `credential_ref` | M | No secret-valued field remains in any collection; `btool`/REST read of the collection returns only a reference |
| D-2 | Sample TTL deletion + explicit purge endpoint | S | Draft samples gone after 24 h; promotion deletes samples |
| D-3 | Capability + ACL review for new endpoints | S | Unauthenticated write returns 401; non-privileged write returns 403 |
| D-4 | Threat-model walkthrough document reviewed by security owner | S | OWASP-style entry per endpoint with mitigation + test id |
| D-5 | Identity-boundary conformance sweep (§4.3, §5 invariant 8) | S | No login route, no app-owned user/password setting, no default admin credential anywhere in app or catalog; HEC destination token resolves from `storage/passwords` by reference; grep for container-scraped credentials (`printenv`, `docker exec … printenv`) returns zero in `src/`, `backend/`, `scripts/`; each claim is a named test, not a review note |
| D-6 | Discovery-projection readiness made evidence-aware (recovery report §3.3) | M | `readiness` derives from catalog `maturity` **and** incident-pack membership, never from an id naming prefix; each of the 17 rows the catalog calls certified either links to a dashboard recipe or is explicitly marked as having no primary surface; `test_native_discovery` stays cohort-defined by `incident_contracts()`; no row may claim `Executable custom simulation` without the evidence reference C-3 writes |

### Stage E — Optional (feature-flagged, off by default)

| ID | Story | Size | Acceptance criteria |
|---|---|---|---|
| E-1 | `ai_extract_advisor` proposals | L | Proposals are advisory only; user must accept each; no `apply_all`; advisor sees only redacted capped sample |
| E-2 | Suggest CIM field mapping for a profile | M | Mapping proposed, not applied; unverified mapping renders distinctly from vendor-documented |

**Recommended sequencing:** A-1 → A-4 → A-5 → A-2 → A-3 → B-1 → B-2 → B-4 →
C-1 → C-2 → C-3 → D-1 → B-3 → C-4 → D-2 → D-3 → D-4 → D-5 → D-6 → E-*. Stage A is a
hard gate: B and C must not ship before A-4 and A-5 prove the execution and
volume boundaries. D-6 sits after C-3 deliberately — a readiness label that
points at verified execution needs the runner-written evidence reference to point
at, or the change just swaps one unverified label for another.

## 9. Finite v1.0 completion scorecard

The point of this section is that "done" has to be a countable number that stops
moving. Catalog growth is not a finish line — entries are declarations.

| # | Gate | Measure | Target for v1.0 | Counts as met only if |
|---|---|---|---|---|
| 1 | Vendor-documented sources | `status=active` **and** live-verified in one release | 12 | Each has a stored `run_id` + observed count matching expected |
| 2 | Native PAN-OS formats | generators on canonical `pan:*` | 3 (traffic, threat, system) | Delivered through `ScenarioRunner`, not a standalone script |
| 3 | SNMP verified OIDs | typed, value-round-tripped | 12 | Counter/gauge/enum classes proven, incl. one forced wrap and one reset |
| 4 | E2E-validated scenarios | `maturity=E2E_VALIDATED` | 8 | §7 contract satisfied for that scenario |
| 5 | Custom profiles verified | profiles at `VERIFIED` | 3 | Created via builder by a non-author, then verified by C-1 |
| 6 | Credential hygiene | secret values in tracked files | 0 | Fresh scan of tracked files **and** the staged diff |
| 7 | Metric value fidelity | mismatched metric names in a round-trip | 0 | `verify_metric_value_roundtrip.py` exit 0 |
| 8 | Execution boundary | uploaded-bytes-reachable-by-interpreter | 0 | A-4 test present and passing |
| 9 | Regression guardrail | Cisco control run | GREEN each release | Fresh run, fresh counts; historical numbers never reused |
| 10 | UI truthfulness | sources shown as verified without evidence | 0 | Provenance and `evidence_run_id` rendered in Command Center |
| 11 | Identity boundary | product surfaces that own a credential (login route, app admin account, embedded/default password, container-scraped secret) | 0 | D-5 conformance tests present and passing; every lab credential resolves from the environment by name |

v1.0 is **complete** when all eleven gates are met simultaneously. Gates 1–5 rise
with the codebase and are the only ones that can be "in progress"; gates 6–11
are floors that must never be non-zero. A scorecard that reports only totals,
without per-item evidence ids, is not acceptable for publication.

## 10. Explicitly deferred past v1.0

- Custom sources as alert/notable triggers.
- Distribution of user profiles between environments (export/import) — needs a
  trust model first, because an imported profile is someone else's regex.
- Any streaming or real-time capture for custom sources.
- Auto-remediation or active-response driven by custom profiles.
- Multi-tenant isolation of the builder.

## 11. Risks

| Risk | Consequence | Mitigation |
|---|---|---|
| Builder becomes an RCE foothold | Full host compromise on the search head | §5 invariant 1 (no execution) + A-4 test + Stage A hard gate |
| KV Store accumulates real event data | Licensing, retention, privacy exposure | §5 invariant 4 caps + D-2 TTL + samples never indexed |
| Secrets creep into profiles | Token exposure in a replicated collection | D-1 + `credential_ref` only, enforced by schema |
| Product grows its own login/default admin | Second identity store to secure, breaks Splunk RBAC, duplicates what Splunk already owns | §4.3 boundary + §5 invariant 8 + D-5 conformance sweep |
| Transport secret goes stale inside a running instance | `enabled=True` with 100% dispatch rejection — the Phase 4C §3.5/§3.6 incident | resolve per use from `storage/passwords` by reference; destination health probe (D-3 adjacent); never read the lab container's environment |
| "Verified" inflates quietly | Reports overstate readiness; the exact Phase 4C failure | `status` written only by the runner; §7 contract; gate 10 |
| User regex stalls the search head | Availability incident | bounded patterns + timeout + sample-only execution |
| Custom and vendor sources blur in UI | Reviewers credit hand-built work to config | mandatory `provenance` badge, C-4 |
