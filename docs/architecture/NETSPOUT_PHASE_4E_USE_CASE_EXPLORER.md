# Phase 4E: Use Case Explorer

Route: `#/explore` (Explore → Use Case Explorer). Backend: `src/netspout_core/use_case_explorer.py`.
The Explorer is a front door onto existing engines. It does not generate, ingest or validate anything itself.

## What it indexes

| Kind | Source | Count (this snapshot) |
|---|---|---|
| Operational, `engine=unified_generation` | `/api/generation/capabilities` scenarios | 25 |
| Operational, `engine=scenario_runner` | `catalog/scenarios.json` | 53 |
| Security analytic stories | `catalog/phase13a_splunk_security_content.json` | 365 |

Counts are computed at request time; nothing is hardcoded.

## Truthfulness rules

1. **Maturity is never upgraded.** Operational maturity is the catalog value (or the dashboard service's scenario maturity),
   normalised to `CERTIFIED / VALIDATED / FORMAT_VALIDATED / CONTRACTED / NOT_ESTABLISHED` with the raw value kept.
   34 of 53 runner scenarios are only `CONTRACTED`; they are listed, labelled, and excluded by the default *Demo-ready only* filter.
2. **Demo-ready** = runnable and tier `CERTIFIED` or `VALIDATED` (operational), or a story whose workflow can actually run (security).
   It reflects recorded catalog maturity, not a live run in the current session.
3. **Security readiness**, strongest first: `DETECTION_VERIFIED` (stored `POSITIVE_CASE_VALIDATED` evidence) >
   `RUNTIME_APPROVED` (a detection in `SUPPORTED_RUNTIME_DETECTIONS` with a replay dataset the catalog can serve) >
   `REPLAY_ONLY` > `CONTENT_ONLY` > `NO_DETECTIONS`. Today exactly one story (React2Shell) is `RUNTIME_APPROVED`; 313 are `REPLAY_ONLY`.
   `production_detection_efficacy` is always `NOT_ESTABLISHED`.
4. **Industry mappings carry a basis**: `industry_pack` (a catalog pack/dashboard binds the scenario) or `editorial`
   (maintainer judgement, shown with `*`). Industries with no mapped scenario show 0 and are not padded.
   Security stories carry no industry claim.
5. **Dashboards** are shown with the dashboard service's eligibility and maturity (currently `NOT_STARTED` for all 29).
   A dashboard is never presented as ready by the Explorer; only `POST /api/dashboards/{id}/validate` changes that.
6. **Blocked steps say why** (`blocked_reason`), e.g. a replay-only story blocks Enable Detection and Verify because its SPL is
   not approved for bounded runtime execution.

## Taxonomy

`catalog/explorer_taxonomy.json` holds the 18 industries and the scenario mappings. `taxonomy_status` is `PROPOSED_DEFAULT`
and the UI says so. **Replace the `industries` list with the approved taxonomy if it differs**; `load_taxonomy()` rejects
mappings that reference unknown industry ids. Editing this one file is sufficient (it is mirrored by `scripts/sync_core.py`).

## Workflows

Operational: **Select → Configure → Generate → Ingest → Verify → Dashboard**

| Step | `unified_generation` | `scenario_runner` |
|---|---|---|
| Configure | `POST /api/generation/preflight` | uses Connection Center destination (no call) |
| Generate | `POST /api/generation/runs` | `POST /api/scenarios/{id}/run` |
| Ingest | `SPLUNK_DISPATCHED` evidence stage `PROVEN` | observed event/metric counts (Gate 8 evidence) |
| Verify | `SPLUNK_OBSERVED` `PROVEN` | `required_evidence_satisfied` (Gate 8 contract v1.0) |
| Dashboard | generate + validate; reports the maturity the service returns | not available (no binding) |

Security: **Select → Prerequisites → Generate → Ingest → Enable Detection → Verify** (no dashboard step)

| Step | Call | Success means |
|---|---|---|
| Prerequisites | `GET /api/explorer/entries/{id}/prerequisites` | Local config checks pass; live reachability is reported `NOT_TESTED` |
| Generate | `POST /api/security-content/datasets/retrieve` | Pinned upstream dataset retrieved, SHA-256 verified |
| Ingest | `POST /api/security-content/replays`, then `POST /api/explorer/security/observe` | Splunk shows a run-scoped event count > 0 ("sent" alone is not enough) |
| Enable Detection | `POST /api/explorer/detections/{id}/enable` | Saved search exists, is scheduled and not disabled **on Splunk read-back** |
| Verify | `POST /api/security-content/validations` | `POSITIVE_CASE_VALIDATED`: the detection SPL matched run-scoped replayed events |

`Verify` does not prove that the scheduled search has fired or that the detection is effective in production.

## Security and access

* Mutating routes (`enable`, `observe`, replay, validation) require Connection Center to be configured and the index to be
  in its authorized list; otherwise 409/403. No Splunk call is made before those checks.
* Splunk RBAC applies because the configured Splunk credential performs saved-search creation; a forbidden call is
  reported as `FAILED` with the HTTP status. Secrets are never returned; `prerequisites` reports presence only.
* Saved searches use `servicesNS/nobody/<app>/saved/searches` (app `netspout`, override `NETSPOUT_SPLUNK_APP`), 15-minute
  schedule, **no alert actions**. Only SPL from `SUPPORTED_RUNTIME_DETECTIONS` is ever expanded, and it passes the same
  read-only SPL validation as bounded validation.

## Verification status

* Hermetic: `tests/test_phase4e_use_case_explorer.py` (24 tests, local Splunk REST stub), `tests/test_gate8_unified_evidence.py` (26).
* Browser: `frontend/tests/phase4e-use-case-explorer.spec.ts` (5) against the real backend with an unconfigured Connection Center.
* **Live:** operational and security workflows were run against a real Splunk 10.2.7 lab and independently verified; see
  `docs/verification/pulseforge_phase4e_live_splunk_acceptance.md` (including what remains unverified: ES, visual dashboard
  validation, collector-dependent gNMI E2E).
