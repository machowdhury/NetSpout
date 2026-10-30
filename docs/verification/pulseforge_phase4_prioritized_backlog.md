# PulseForge Phase 4 Prioritized Backlog

## Ranking Criteria

1. **SE demo impact**: Value for Solution Engineer demonstrations
2. **Authentic telemetry availability**: Realistic, vendor-accurate telemetry
3. **Reuse across industries and vendors**: Breadth of applicability  
4. **Metrics and sourcetypes coverage improvement**: Quantitative coverage gains
5. **Engineering effort**: Implementation complexity and time
6. **Verification feasibility**: Ability to test and validate

## Top 15 Prioritized Tasks

| ID | Title | Impact | Authenticity | Reuse | Coverage | Effort | Verification | Priority |
|----|-------|--------|--------------|-------|----------|--------|--------------|----------|
| P4-001 | Increase supported sourcetypes to 70% | SE demo impact: HIGH | Authentic telemetry: HIGH | Cross-industry reuse: HIGH | Sourcetype coverage: +40% | Engineering effort: MEDIUM | Verification feasibility: HIGH | 95 |
| P4-002 | Complete Cisco IOS XE/XR telemetry coverage | SE demo impact: HIGH | Authentic telemetry: HIGH | Cross-industry reuse: MEDIUM | Vendor coverage: Cisco complete | Engineering effort: MEDIUM | Verification feasibility: HIGH | 90 |
| P4-003 | Implement AI/LLM observability scenarios | SE demo impact: HIGH | Authentic telemetry: MEDIUM | Cross-industry reuse: HIGH | AI scenario coverage: New category | Engineering effort: HIGH | Verification feasibility: MEDIUM | 88 |
| P4-004 | Expand financial services industry scenarios | SE demo impact: HIGH | Authentic telemetry: HIGH | Cross-industry reuse: MEDIUM | Industry coverage: Finance complete | Engineering effort: MEDIUM | Verification feasibility: HIGH | 85 |
| P4-005 | Add cloud metrics (AWS, Azure, GCP) | SE demo impact: HIGH | Authentic telemetry: HIGH | Cross-industry reuse: HIGH | Cloud metrics coverage: New area | Engineering effort: HIGH | Verification feasibility: MEDIUM | 83 |
| P4-006 | Implement metric-index support for all numeric telemetry | SE demo impact: MEDIUM | Authentic telemetry: HIGH | Cross-industry reuse: HIGH | Metrics capability: Complete | Engineering effort: MEDIUM | Verification feasibility: HIGH | 80 |
| P4-007 | Create dashboard library for all executable scenarios | SE demo impact: HIGH | Authentic telemetry: MEDIUM | Cross-industry reuse: HIGH | Dashboard readiness: 100% | Engineering effort: HIGH | Verification feasibility: HIGH | 78 |
| P4-008 | Add Kubernetes and container observability | SE demo impact: HIGH | Authentic telemetry: HIGH | Cross-industry reuse: HIGH | Platform engineering: New area | Engineering effort: MEDIUM | Verification feasibility: MEDIUM | 75 |
| P4-009 | Implement healthcare industry scenarios | SE demo impact: MEDIUM | Authentic telemetry: HIGH | Cross-industry reuse: MEDIUM | Industry coverage: Healthcare | Engineering effort: MEDIUM | Verification feasibility: MEDIUM | 72 |
| P4-010 | Add telecommunications network scenarios | SE demo impact: MEDIUM | Authentic telemetry: HIGH | Cross-industry reuse: MEDIUM | Industry coverage: Telecom | Engineering effort: HIGH | Verification feasibility: MEDIUM | 70 |
| P4-011 | Create validation test suite | SE demo impact: LOW | Authentic telemetry: HIGH | Cross-industry reuse: HIGH | Quality assurance: Complete | Engineering effort: MEDIUM | Verification feasibility: HIGH | 68 |
| P4-012 | Implement OT/IoT industrial scenarios | SE demo impact: MEDIUM | Authentic telemetry: HIGH | Cross-industry reuse: MEDIUM | OT coverage: New area | Engineering effort: HIGH | Verification feasibility: LOW | 65 |
| P4-013 | Add retail/e-commerce scenarios | SE demo impact: MEDIUM | Authentic telemetry: HIGH | Cross-industry reuse: MEDIUM | Industry coverage: Retail | Engineering effort: MEDIUM | Verification feasibility: HIGH | 63 |
| P4-014 | Implement multi-vendor correlation scenarios | SE demo impact: HIGH | Authentic telemetry: HIGH | Cross-industry reuse: HIGH | Advanced use cases: New | Engineering effort: HIGH | Verification feasibility: MEDIUM | 60 |
| P4-015 | Add education sector scenarios | SE demo impact: LOW | Authentic telemetry: HIGH | Cross-industry reuse: MEDIUM | Industry coverage: Education | Engineering effort: MEDIUM | Verification feasibility: HIGH | 58 |

## Implementation Recommendations

### Immediate (Sprint 1-2)
- **P4-001**: Increase supported sourcetypes (foundational)
- **P4-002**: Complete Cisco coverage (high-demand vendor)
- **P4-006**: Metric-index support (technical foundation)

### Short-term (Sprint 3-4)  
- **P4-003**: AI/LLM scenarios (emerging market)
- **P4-004**: Financial services (high-value industry)
- **P4-007**: Dashboard library (demo readiness)

### Medium-term (Sprint 5-6)
- **P4-005**: Cloud metrics (broad applicability)
- **P4-008**: Kubernetes observability (platform engineering)
- **P4-011**: Validation test suite (quality)

### Long-term (Sprint 7+)
- **P4-009**: Healthcare scenarios (specialized)
- **P4-010**: Telecommunications (complex)
- **P4-012**: OT/IoT (niche but valuable)

## Success Metrics for Phase 4

1. **Sourcetype coverage**: 70%+ SUPPORTED_AND_VERIFIED
2. **Scenario maturity**: 80%+ EXECUTABLE scenarios
3. **Industry coverage**: 5+ major industries with complete scenarios
4. **Metrics capability**: Full metric-index support for numeric telemetry
5. **Dashboard readiness**: 100% of EXECUTABLE scenarios have dashboards
6. **Validation coverage**: Automated tests for all core functionality

## Execution status (updated 2026-10-30)

Coverage is now computed from repository evidence by `scripts/generate_coverage_report.py`
(see `pulseforge_sourcetype_coverage.md` / `pulseforge_scenario_coverage.md`; the earlier all-UNKNOWN reports came from scanner bugs).

| Item | Status |
|---|---|
| P4-001 Sourcetype coverage | Native generators 112 → **142** of 348 (Batch 5, +31 Cisco IOS-XE change/fault/health sourcetypes); byte-verified in Splunk 87 → **118**; independently indexed 64 → **95**. The 70% target is **not** met (142/348 = 41%). |
| P4-002 Cisco IOS XE telemetry | Partial: IOS-XE change/fault/health syslog done (Batch 5). Catalyst Center / DNAC, Meraki, Intersight, Duo and ISE API-style sourcetypes remain sample-replay only. |
| Network change/fault scenarios | +3 executable packs (`ub5_*`): change-induced outage, platform health degradation, NAC RADIUS outage. Maturity stays CONTRACTED. |
| Financial / telecom scenario libraries | **Not integrated; inputs missing.** Needed: the 100 financial-services and 100 telecom use-case library files (scenario definitions, any sample payloads, and their original IDs so they can be ingested with stable IDs, provenance, dedup and maturity labels). Checked only the repository (`docs/`, `catalog/`, `tests/`) and the usual local folders (`~/Projects`, `~/Downloads`, `~/Documents`, `~/Desktop`); found only unrelated Splunk marketing PDFs. Nothing was invented in their place. |
| TA validation | Unchanged (1 partial: ISE). Batch 5 proves delivery and byte fidelity only; no Cisco TA parsing is claimed. |

### Batch 5 live evidence (Splunk 10.2.7 lab, index `idx_network_ops`)

* Byte equality: 38/38 families (31 sourcetypes) indexed `_raw` identical to submitted bytes (`catalog/universe_batch5_live_raw_equality_results.json`).
* Product path: `POST /api/generate/scenario-pack` dispatched 20 / 10 / 8 events for the three `ub5_*` packs; independent per-phase counts matched exactly; no correlation metadata in `_raw`.
* Explorer (inside Splunk Web): `Cisco Change-Induced Outage` Select, Configure, Generate (20), Ingest (HEC accepted 20 of 20), Verify (Splunk indexed 20 of 20); independent search by phase 3/4/8/5.
* Not claimed: Cisco TA parsing of these sourcetypes, detections, dashboards for these packs, or maturity above CONTRACTED.

### Batch 6 and counting reconciliation (2026-10-30)

| Item | Result |
|---|---|
| Batch 5 "31 added, 30 counted" | `cisco:sdwan:BGP-5-ADJCHANGE` already had a native formatter, so it now has two generators. Not a counting defect. |
| Real counting defect found | The scanner missed generators declared as default arguments or in dedicated generator modules: `pan:system`, `cisco:duo:remote:vpn`, `cisco:catalyst:clienthealth`, `meraki:assurancealerts`, `netspout:snmp:poll`, `netspout:snmp:trap` (+6, fixed in `scripts/generate_coverage_report.py`). |
| Batch 6 (+10 native) | 10 captured Cisco records promoted (ACI class, Nexus power, Catalyst rogue/threat/profile, SD-WAN SSE tunnels, UTD logs and health, MX flow) with declared time fields; 2 correlated scenarios (`ub6_*`). Live: 18/18 byte-equal; both scenarios counted exactly per phase in Splunk. |
| Deliberately not promoted | 10 Catalyst rows whose captured text is an empty-poller status string, a bare number or a heartbeat; ~136 demo-authored samples (dated 2026, invented names); fault-injection templates without a format reference. |
| FortiGate (7 rows) | Official FortiOS 7.4.0 Log Message Reference pages print field tables but **no sample log lines**, so no native generator was built; keep as sample replay until a pinned authentic log or the PDF samples are supplied. |
| 70% target (244/348) | **Not reachable on current evidence**: 158 native. Remaining 190 need authentic captures or documented sample lines per source. Exact blocker list: Aruba, Arista, Cisco ASA/FTD/NX-OS syslog, F5, Juniper, Sophos, Zscaler, Radware, Check Point, Nokia, A10, Huawei, Extreme, Dell, Netskope, Forcepoint, SonicWall, WatchGuard, VMware NSX, Cloudflare, NetApp, Nutanix, Meraki API, Intersight, Duo, remaining Catalyst/DNAC API types. |
