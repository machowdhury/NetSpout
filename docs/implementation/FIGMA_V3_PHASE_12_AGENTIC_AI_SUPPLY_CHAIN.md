# NetSpout Phase 12 — Agentic AI, MCP/A2A Observability, and Supply Chain

## 1. Executive outcome

Phase 12 is **PASS**. NetSpout now has reusable Agentic AI Security,
Software Supply Chain Security, and cross-domain packs integrated through the
existing pack registry, shared deterministic runtime, Splunk pipeline,
Dashboard Recipe Engine, Dashboard Gallery, and Scenario Studio.

Thirteen bounded references were implemented and observed through fresh
authenticated Splunk searches. Their investigation SPL and detection SPL
executed successfully, expected incident evidence matched, and baseline
false-positive behavior was tested. Thirteen new dashboards independently
reached `DASHBOARD_READY`; the 14 previously accepted dashboards remain
eligible and operational.

No external MCP server, A2A peer, model provider, repository, package registry,
CI system, or deployment environment was contacted. No real attack, untrusted
repository code, package installation, production deployment, or customer data
was involved.

## 2. Starting HEAD

- Branch: `feature/figma-v3-unified-telemetry-lab`
- Starting local HEAD: `0b427a8054753e59cf9f9545203b83c27370847d`
- Starting remote HEAD: `0b427a8054753e59cf9f9545203b83c27370847d`
- Starting tree: clean
- Reported Phase 11B results were treated as claims and revalidated where
  Phase 12 could affect them.

## 3. Architecture changes

Phase 12 extends, rather than replaces, the existing architecture:

- three new `PackKind` values: `AGENTIC_AI`,
  `SOFTWARE_SUPPLY_CHAIN`, and `CROSS_DOMAIN`;
- three pack definitions and 13 existing-contract compositions;
- three `NETSPOUT_DEFINED` JSON audit sources transported through the existing
  local HEC destination;
- allow-listed in-process generators and validators;
- one immutable `SimulationClock` and one deterministic causal graph per run;
- existing `GuidedScenarioManifest`, Investigation Pack, Detection Pack,
  composition, source binding, and replay contracts;
- 11 reusable Phase 12 dashboard recipes merged into the existing Dashboard
  Recipe Engine;
- safe Scenario Studio cloning and parameter editing using the existing private
  pack lifecycle.

No parallel simulator, dashboard framework, clock, or identity system was
created.

## 4. MCP specification evidence

Authoritative contract references:

- MCP Tools, version `2025-11-25`:
  `https://modelcontextprotocol.io/specification/2025-11-25/server/tools`
- MCP Resources, version `2025-11-25`:
  `https://modelcontextprotocol.io/specification/2025-11-25/server/resources`
- MCP Authorization, version `2025-11-25`:
  `https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization`

Verified structures used by the fixtures include `tools/list`, `tools/call`,
JSON-RPC request identity, parameters, results/errors, and resource-oriented
context where relevant. OAuth 2.1 authorization, Protected Resource Metadata,
resource indicators, PKCE, and audience validation support the authorization
model but are not fabricated as tool-call fields.

Every generated record has three explicit namespaces:

1. `protocol`: cited MCP/A2A/SLSA-shaped structures;
2. `audit`: instrumentation-generated authorization, provenance, trust, and
   downstream-action evidence;
3. `scenario`: NetSpout run, phase, correlation, causal-parent, and synthetic
   evidence classification.

MCP traffic is not represented as a complete security audit trail.

## 5. A2A specification evidence

Authoritative reference:

- Agent2Agent Protocol Specification v1.0.0:
  `https://a2a-protocol.org/v1.0.0/specification/`

Modeled protocol structures include Agent Card context, `Task`, `Message`,
`Part`, `Artifact`, `taskId`, `contextId`, status, and task update semantics.
Authorization is represented as implementation instrumentation after
authentication, not as a universal A2A field. An A2A exchange is never treated
as proof of malicious behavior.

## 6. Agentic AI Pack

The pack models synthetic agents, operators, runtimes, sessions, model
providers, tools, MCP clients/servers, A2A peers, resources, prompt/input
artifacts, invocations, authorization decisions, credential references,
downstream actions, policy evaluations, and audit events.

Stable IDs are derived from scenario ID and deterministic seed. Credential
references are synthetic labels; generated records reject secret-like keys,
external endpoints, and executable payload syntax.

## 7. Supply Chain Pack

The pack models repositories, branches, commits, pull requests, developer and
automation identities, CI workflows/jobs, dependencies, packages, artifacts,
registries, modeled deployment environments, provenance statements, policies,
and approval decisions.

SLSA v1.1 provenance uses the documented in-toto predicate type,
`buildDefinition`, `runDetails`, `builder.id`, subjects, and SHA-256 digests.
Missing provenance is a validation gap and is not labeled malicious.

## 8. Scenario inventory and maturity

| Scenario | Reference | Protocol/contract | Final scenario maturity | Splunk | Detection |
|---|---|---|---|---|---|
| AI-001 | Indirect Prompt Injection | MCP + audit | SPLUNK_VALIDATED | observed | matched |
| AI-002 | Unauthorized Tool Invocation | MCP + audit | SPLUNK_VALIDATED | observed | matched |
| AI-003 | MCP Tool Output Manipulation | MCP + audit | SPLUNK_VALIDATED | observed | matched |
| AI-004 | Agent Identity and Privilege Drift | MCP + audit | SPLUNK_VALIDATED | observed | matched |
| AI-005 | A2A Delegation Abuse | A2A + audit | SPLUNK_VALIDATED | observed | matched |
| AI-006 | Multi-Agent Incident | MCP + A2A + audit | SPLUNK_VALIDATED | observed | matched |
| SC-001 | Suspicious Dependency Change | SLSA + audit | SPLUNK_VALIDATED | observed | matched |
| SC-002 | CI Workflow Permission Escalation | SLSA + audit | SPLUNK_VALIDATED | observed | matched |
| SC-003 | Build Artifact Provenance Gap | SLSA + audit | SPLUNK_VALIDATED | observed | matched |
| SC-004 | Repository Automation Abuse | SLSA + audit | SPLUNK_VALIDATED | observed | matched |
| SC-005 | Supply Chain to Runtime Correlation | SLSA + audit | SPLUNK_VALIDATED | observed | matched |
| P12-XD-001 | AI Agent to Infrastructure | MCP + shared graph | SPLUNK_VALIDATED | observed | matched |
| P12-XD-002 | Supply Chain to Application | SLSA + shared graph | SPLUNK_VALIDATED | observed | matched |

Scenario, detection, and dashboard maturity remain independent. Protocol
structures are specification-backed, but the execution is synthetic
instrumentation rather than a live external protocol implementation.

## 9. Entity graph and causal model

Each run creates one state plan containing:

- one immutable `SimulationClock`;
- synthetic actor, resource, policy, and analytics entities;
- request, evaluation, and observation relationships;
- one correlation ID;
- causal-parent links between sequential events;
- one run/scenario identity and deterministic seed.

Cross-domain references use this same graph. `DENIED`, `BLOCKED`, `REJECTED`,
and `VALIDATION_FAILED` events always have
`downstream_action_executed=false`. `MODELED_DEPLOYMENT` is explicitly labeled
modeled rather than independently observed production deployment.

## 10. Protocol contracts

Sources:

- `phase12-agentic-audit` / `netspout:phase12:agentic`
- `phase12-supply-chain-audit` / `netspout:phase12:supply_chain`
- `phase12-cross-domain-audit` / `netspout:phase12:cross_domain`

All sourcetypes have authority `NETSPOUT_DEFINED`. CIM is `NOT_ESTABLISHED`.
Production field names and portability remain implementation-specific.

## 11. Telemetry validation

Current-run evidence:

- 13/13 scenarios generated deterministic events;
- 13/13 HEC dispatches were acknowledged;
- 13/13 had fresh authenticated indexed Splunk observations;
- 13/13 passed required-field observation;
- receiver observation remains `NOT_AVAILABLE` for the direct HEC path;
- HEC acceptance was not used as indexed-data evidence.

Durable ignored manifest:

`.artifacts/phase12-current/phase12/phase12-live-validation.json`

## 12. Detection validation

Each scenario has a run/time/source-bounded detection contract with required
fields, hypothesis, expected result, false-positive controls, blind spots, and
explicit `NETSPOUT_SPECIFIC` portability.

- Generated: 13/13
- Executed: 13/13
- Expected evidence matched: 13/13
- Baseline false-positive behavior tested: 13/13
- Production portability assessed: not established; requires environment field
  mapping and independent production validation

Synthetic execution does not establish real-world efficacy.

## 13. Splunk investigations

All 13 investigation recipes executed against fresh run-scoped indexed data.
They order event phase, protocol family/method, action, policy outcome,
correlation ID, and causal parent while preserving the distinction between
modeled causality and observed records.

## 14. Dashboard integration

- Reusable recipes before/after: 19 / 30
- New recipes: 11
- Phase 12 dashboard packs generated: 13
- SPL/data/export validated: 13/13
- Browser visually validated: 13/13
- New Dashboard Ready: 13
- Total Dashboard Ready: 27
- Existing Dashboard Ready regression: 14/14

The recipes cover agent activity, MCP tools, A2A tasks/delegation, agent
identity/authorization, prompt injection, policy timelines, repository
activity, CI changes, dependency risk, artifact provenance, and cross-domain
causal correlation. Gallery, NOC/Engineer/Evidence perspectives, topology,
Inspector, drilldowns, and Dashboard Studio export remain shared.

## 15. Scenario Studio integration

The packaged Docker API/browser journey proved:

- clone AI-002;
- modify bounded `intensity` and `policy_mode` parameters;
- validate;
- save;
- reload;
- run using the existing source/composition path;
- reject an external endpoint through `execution-containment`.

Execution policy is offline-only, non-executable, max 100 events, and bounded
to 300 seconds. Only `fixture` and `memory` endpoint schemes are allowed.

## 16. Guided learning experience

Every reference includes Simple and Advanced material covering:

- the threat and detection difficulty;
- crossed trust boundary;
- expected versus available evidence;
- Splunk investigation;
- what detection proves and does not prove;
- least privilege, external authorization, provenance, bounded tools, and
  logging controls;
- production adaptation guidance.

## 17. Cross-domain correlation

- P12-XD-001 links agent request, policy denial, unchanged modeled
  infrastructure state, and observation evidence.
- P12-XD-002 links repository/build identity, provenance, artifact digest,
  modeled application deployment, and runtime observation.

Correlation comes from one shared state plan and causal graph, not disconnected
logs.

## 18. Docker journeys

Packaged Docker result: **9/9 PASS**.

- A — Indirect Prompt Injection: PASS
- B — MCP Tool Misuse: PASS
- C — A2A Delegation: PASS
- D — Supply Chain: PASS
- E — Cross-Domain: PASS
- F — Dashboard perspectives/Inspector/export: PASS
- G — Scenario Studio clone/modify/save/reload/run: PASS
- H — External endpoint fail closed: PASS
- I — Existing 14-dashboard regression: PASS

Manifest:

`.artifacts/phase12-current/phase12/phase12-docker-journeys.json`

## 19. Security controls

Tests passed for denial semantics, external endpoint rejection, executable
payload rejection, secret-like key rejection, synthetic identity separation,
determinism, bounded event/time limits, replay consistency, contract
validation, and fail-closed Studio behavior.

Credentials remained environment/container-config only and were not serialized.
The existing insecure-TLS exception was used only for loopback Splunk lab
endpoints. A persistent local-lab admin mismatch surfaced after container
recreation; the indexed volume was preserved and only the local user seed was
reset to its already configured container value.

No certificate material was added. Therefore certificate expiry, validity
start, key strength, signature algorithm, issuer/subject, self-signed intent,
and chain checks were not applicable to new artifacts. No deprecated or custom
cryptographic algorithm was introduced; SHA-256 is used only for deterministic
synthetic identities and artifact digests.

## 20. Resource efficiency

Research and architecture inspection were batched. Fixtures are local and
deterministic. Focused tests ran before broad tests. No paid LLM/API,
infrastructure purchase, unbounded process, external agent, package execution,
or untrusted repository clone was used.

## 21. Regression results

- Phase 12 focused + dashboard + Studio: 39 passed, 19 subtests
- Expanded registry regression: 51 passed, 10 subtests
- Final focused catalog integration: 70 passed, 10 subtests
- Backend: 625 passed, 1 skipped, 2,322 inherited warnings, 77 subtests
- Gate 12F: 13/13 passed
- Gate 13E: 6/6 passed
- Combined gates: 19 passed, 57 inherited warnings
- Frontend build: PASS; inherited bundle-size warning
- Frontend lint: PASS; 13 inherited warnings
- Full Playwright: 30 passed, 16 conditional skips
- Phase 12 live Playwright: 3/3 passed
- Docker journeys: 9/9 passed

The skip is inherited. Warnings remain existing FastAPI/Pydantic/datetime
deprecations, frontend lint findings, npm `devdir`, and bundle-size warnings.

## 22. Browser evidence

The real packaged Docker browser run captured 39 Phase 12 screenshots:
13 dashboards × NOC/Engineer/Evidence. It also exercised Inspector SPL and
dependency views, export preview, five anchor journeys, legacy eligibility,
Studio save/reload/run, and fail-closed validation.

Evidence root:

`.artifacts/phase12-current/`

## 23. Protected artifacts

- Before: 634
- After: 644
- New protected artifacts: 10 (two canonical Phase 12 catalog extensions and
  four runtime mirrors each)
- Existing protected modifications/deletions: 0
- Historical Phase 8–11B evidence and implementation images: unchanged

## 24. Provenance and licensing

Protocol and security claims use official MCP, A2A, OWASP, and SLSA sources
recorded with publisher, URL, version/date, supported claim, validation state,
and limitation. No blog post is used as normative protocol evidence.

No third-party source, package, Splunkbase visualization, model output, or
license-restricted asset was copied. Existing React/lucide and project
licensing remain unchanged.

## 25. Known limitations

- Events are instrumentation audit fixtures, not live external MCP/A2A wire
  validation.
- No universal MCP/A2A authorization schema is claimed.
- Missing provenance is not malicious evidence.
- Direct HEC lacks an independent receiver-observation stage.
- CIM remains `NOT_ESTABLISHED`.
- Production field mappings, false-positive rates, scale, and efficacy require
  deployment-specific validation.
- No external repository, CI, registry, model, tool server, agent, or
  infrastructure action was executed.

## 26. Phase 13 readiness

**READY**, subject to explicit authorization. Phase 12 acceptance is complete;
no Phase 13 work was started.
