# Security Event Source Coverage

Catalog version: `2026.10-phase13-rc`. Sources: **33**.

This human-readable matrix is generated from the canonical machine-readable catalog. Maturity describes source-contract/runtime evidence and is independent of scenario maturity.

## Cisco — Secure Firewall / FTD

- Coverage ID: `secsrc-cisco-ftd`
- Status: **RESEARCH_REQUIRED**; runtime: `RESEARCH_REQUIRED`; Splunk: `NOT_OBSERVED`
- Scope: Not established
- Domain / event family: Network security / Firewall and intrusion events
- Native format: Vendor format not established
- Transport: Syslog
- Sourcetype: Not established
- Technology Add-on: Research required; CIM: `NOT_ESTABLISHED`
- Required fields: Not established
- Related scenarios: None
- Distribution: SPLUNK_APP, DOCKER_LAB
- Sample generation: Blocked — No authoritative FTD event contract is implemented.
- Provenance: Not established
- Validation evidence: None
- Limitations: Static legacy samples do not establish a supported runtime contract.

## Cisco — Adaptive Security Appliance

- Coverage ID: `secsrc-cisco-asa`
- Status: **IMPLEMENTED_AND_VALIDATED**; runtime: `GOLDEN`; Splunk: `OBSERVED`
- Scope: ASA syslog connection lifecycle subset
- Domain / event family: Network security / Firewall connection events
- Native format: Cisco ASA syslog subset
- Transport: Syslog, HEC
- Sourcetype: `cisco:asa`
- Technology Add-on: Cisco Security Cloud Technology Add-on for Splunk; CIM: `NOT_ESTABLISHED`
- Required fields: `host`, `action`, `src`, `dest`
- Related scenarios: `C100-SEC-001`
- Distribution: SPLUNK_APP, DOCKER_LAB
- Sample generation: Runnable
- Provenance: phase8c-cisco-asa-reference
- Validation evidence: Phase 8C and dashboard regression
- Limitations: Coverage is bounded; CIM compatibility is not established.

## Palo Alto Networks — PAN-OS NGFW

- Coverage ID: `secsrc-palo-alto-ngfw`
- Status: **NOT_IMPLEMENTED**; runtime: `NOT_IMPLEMENTED`; Splunk: `NOT_OBSERVED`
- Scope: Not established
- Domain / event family: Network security / Traffic and threat logs
- Native format: Vendor format not established
- Transport: Syslog
- Sourcetype: Not established
- Technology Add-on: Research required; CIM: `NOT_ESTABLISHED`
- Required fields: Not established
- Related scenarios: None
- Distribution: Unavailable
- Sample generation: Blocked — No validated PAN-OS runtime source contract exists.
- Provenance: Not established
- Validation evidence: None
- Limitations: None recorded

## Fortinet — FortiGate

- Coverage ID: `secsrc-fortigate`
- Status: **NOT_IMPLEMENTED**; runtime: `NOT_IMPLEMENTED`; Splunk: `NOT_OBSERVED`
- Scope: Not established
- Domain / event family: Network security / Firewall and UTM events
- Native format: Vendor format not established
- Transport: Syslog
- Sourcetype: Not established
- Technology Add-on: Research required; CIM: `NOT_ESTABLISHED`
- Required fields: Not established
- Related scenarios: None
- Distribution: Unavailable
- Sample generation: Blocked — No validated FortiGate runtime source contract exists.
- Provenance: Not established
- Validation evidence: None
- Limitations: None recorded

## Cisco — Umbrella

- Coverage ID: `secsrc-umbrella`
- Status: **PARTIAL**; runtime: `PARTIAL`; Splunk: `OBSERVED_AS_NETSPOUT_DNS`
- Scope: Not established
- Domain / event family: Network security / DNS security
- Native format: RFC 1035 modeled DNS observations, not Umbrella logs
- Transport: DNS, HEC
- Sourcetype: `netspout:dns`
- Technology Add-on: None for NetSpout-defined source; CIM: `NOT_ESTABLISHED`
- Required fields: `query`, `response_code`
- Related scenarios: `SEC-P9-B-DNS-ANOMALY`, `SEC-P9-E-DNS-TUNNEL`
- Distribution: SPLUNK_APP, DOCKER_LAB
- Sample generation: Blocked — Generic DNS evidence must not be represented as native Umbrella telemetry.
- Provenance: RFC 1035
- Validation evidence: Phase 9 Splunk validation
- Limitations: No Cisco Umbrella vendor-log contract is claimed.

## Unselected — IDS/IPS

- Coverage ID: `secsrc-ids-ips`
- Status: **RESEARCH_REQUIRED**; runtime: `RESEARCH_REQUIRED`; Splunk: `NOT_OBSERVED`
- Scope: Not established
- Domain / event family: Network security / Intrusion alerts
- Native format: Not selected
- Transport: None established
- Sourcetype: Not established
- Technology Add-on: Not selected; CIM: `NOT_ESTABLISHED`
- Required fields: Not established
- Related scenarios: None
- Distribution: Unavailable
- Sample generation: Blocked — A vendor and authoritative contract must be selected.
- Provenance: Not established
- Validation evidence: None
- Limitations: None recorded

## IETF / NetSpout — DNS security observations

- Coverage ID: `secsrc-dns`
- Status: **IMPLEMENTED_AND_VALIDATED**; runtime: `SPLUNK_VALIDATED`; Splunk: `OBSERVED`
- Scope: RFC 1035 bounded subset
- Domain / event family: Network security / DNS query and response
- Native format: DNS wire plus normalized NetSpout fields
- Transport: DNS, HEC
- Sourcetype: `netspout:dns`
- Technology Add-on: None; CIM: `NOT_ESTABLISHED`
- Required fields: `query`, `response_code`
- Related scenarios: `SEC-P9-B-DNS-ANOMALY`, `SEC-P9-C-BEACONING`, `SEC-P9-E-DNS-TUNNEL`, `SEC-P9-F-CROSS-SOURCE`
- Distribution: SPLUNK_APP, DOCKER_LAB
- Sample generation: Runnable
- Provenance: RFC 1035
- Validation evidence: Phase 9 Splunk validation
- Limitations: CIM compatibility is not established.

## Unselected — Proxy / SWG

- Coverage ID: `secsrc-proxy-swg`
- Status: **NOT_IMPLEMENTED**; runtime: `NOT_IMPLEMENTED`; Splunk: `NOT_OBSERVED`
- Scope: Not established
- Domain / event family: Network security / Web access
- Native format: Not selected
- Transport: None established
- Sourcetype: Not established
- Technology Add-on: Not selected; CIM: `NOT_ESTABLISHED`
- Required fields: Not established
- Related scenarios: None
- Distribution: Unavailable
- Sample generation: Blocked — No proxy/SWG contract is implemented.
- Provenance: Not established
- Validation evidence: None
- Limitations: None recorded

## Cisco / NetSpout — ASA VPN modeled subset

- Coverage ID: `secsrc-vpn-ztna`
- Status: **PARTIAL**; runtime: `PARTIAL`; Splunk: `NOT_RELEASE_VALIDATED`
- Scope: Synthetic remote-access lifecycle
- Domain / event family: Network security / VPN authentication and assignment
- Native format: Modeled ASA syslog
- Transport: Syslog, HEC
- Sourcetype: `cisco:asa`
- Technology Add-on: Cisco Security Cloud Technology Add-on for Splunk; CIM: `NOT_ESTABLISHED`
- Required fields: `user`, `src`, `assigned_ip`
- Related scenarios: `arch_vpn_remote_workforce`
- Distribution: SPLUNK_APP, DOCKER_LAB
- Sample generation: Blocked — The legacy modeled scenario lacks Phase 13 source-level validation.
- Provenance: Not established
- Validation evidence: None
- Limitations: Not a generic ZTNA source.

## Microsoft — Windows Security Event Log

- Coverage ID: `secsrc-windows-security`
- Status: **RESEARCH_REQUIRED**; runtime: `RESEARCH_REQUIRED`; Splunk: `NOT_OBSERVED`
- Scope: Not established
- Domain / event family: Endpoint security / Operating-system security audit
- Native format: Windows Event Log
- Transport: Windows Event Log
- Sourcetype: Not established
- Technology Add-on: Splunk Add-on for Microsoft Windows; CIM: `NOT_ESTABLISHED`
- Required fields: Not established
- Related scenarios: None
- Distribution: SPLUNK_APP, DOCKER_LAB
- Sample generation: Blocked — The canonical catalog intentionally blocks this source.
- Provenance: Not established
- Validation evidence: None
- Limitations: None recorded

## Microsoft Sysinternals — Sysmon

- Coverage ID: `secsrc-sysmon`
- Status: **NOT_IMPLEMENTED**; runtime: `NOT_IMPLEMENTED`; Splunk: `NOT_OBSERVED`
- Scope: Not established
- Domain / event family: Endpoint security / Endpoint process and network activity
- Native format: Windows Event Log
- Transport: Windows Event Log
- Sourcetype: Not established
- Technology Add-on: Research required; CIM: `NOT_ESTABLISHED`
- Required fields: Not established
- Related scenarios: None
- Distribution: Unavailable
- Sample generation: Blocked — No Sysmon contract is implemented.
- Provenance: Not established
- Validation evidence: None
- Limitations: None recorded

## Linux — auditd

- Coverage ID: `secsrc-linux-audit`
- Status: **NOT_IMPLEMENTED**; runtime: `NOT_IMPLEMENTED`; Splunk: `NOT_OBSERVED`
- Scope: Not established
- Domain / event family: Endpoint security / Linux audit
- Native format: auditd
- Transport: None established
- Sourcetype: Not established
- Technology Add-on: Research required; CIM: `NOT_ESTABLISHED`
- Required fields: Not established
- Related scenarios: None
- Distribution: Unavailable
- Sample generation: Blocked — No Linux audit contract is implemented.
- Provenance: Not established
- Validation evidence: None
- Limitations: None recorded

## Unselected — EDR / XDR

- Coverage ID: `secsrc-edr-xdr`
- Status: **RESEARCH_REQUIRED**; runtime: `RESEARCH_REQUIRED`; Splunk: `NOT_OBSERVED`
- Scope: Not established
- Domain / event family: Endpoint security / Endpoint detection
- Native format: Not selected
- Transport: None established
- Sourcetype: Not established
- Technology Add-on: Not selected; CIM: `NOT_ESTABLISHED`
- Required fields: Not established
- Related scenarios: None
- Distribution: Unavailable
- Sample generation: Blocked — A vendor and authoritative contract must be selected.
- Provenance: Not established
- Validation evidence: None
- Limitations: None recorded

## Microsoft — Active Directory

- Coverage ID: `secsrc-active-directory`
- Status: **NOT_IMPLEMENTED**; runtime: `NOT_IMPLEMENTED`; Splunk: `NOT_OBSERVED`
- Scope: Not established
- Domain / event family: Identity security / Directory authentication and administration
- Native format: Windows Event Log
- Transport: None established
- Sourcetype: Not established
- Technology Add-on: Splunk Add-on for Microsoft Windows; CIM: `NOT_ESTABLISHED`
- Required fields: Not established
- Related scenarios: None
- Distribution: Unavailable
- Sample generation: Blocked — No Active Directory contract is implemented.
- Provenance: Not established
- Validation evidence: None
- Limitations: None recorded

## Microsoft — Entra ID

- Coverage ID: `secsrc-entra-id`
- Status: **NOT_IMPLEMENTED**; runtime: `NOT_IMPLEMENTED`; Splunk: `NOT_OBSERVED`
- Scope: Not established
- Domain / event family: Identity security / Cloud identity audit
- Native format: Vendor API schema not established
- Transport: None established
- Sourcetype: Not established
- Technology Add-on: Research required; CIM: `NOT_ESTABLISHED`
- Required fields: Not established
- Related scenarios: None
- Distribution: Unavailable
- Sample generation: Blocked — No Entra ID contract is implemented.
- Provenance: Not established
- Validation evidence: None
- Limitations: None recorded

## Okta — System Log

- Coverage ID: `secsrc-okta`
- Status: **NOT_IMPLEMENTED**; runtime: `NOT_IMPLEMENTED`; Splunk: `NOT_OBSERVED`
- Scope: Not established
- Domain / event family: Identity security / Identity audit
- Native format: Vendor API schema not established
- Transport: None established
- Sourcetype: Not established
- Technology Add-on: Research required; CIM: `NOT_ESTABLISHED`
- Required fields: Not established
- Related scenarios: None
- Distribution: Unavailable
- Sample generation: Blocked — No Okta contract is implemented.
- Provenance: Not established
- Validation evidence: None
- Limitations: None recorded

## Unselected — Privileged access management

- Coverage ID: `secsrc-privileged-access`
- Status: **RESEARCH_REQUIRED**; runtime: `RESEARCH_REQUIRED`; Splunk: `NOT_OBSERVED`
- Scope: Not established
- Domain / event family: Identity security / Privileged session and credential access
- Native format: Not selected
- Transport: None established
- Sourcetype: Not established
- Technology Add-on: Not selected; CIM: `NOT_ESTABLISHED`
- Required fields: Not established
- Related scenarios: None
- Distribution: Unavailable
- Sample generation: Blocked — A vendor and authoritative contract must be selected.
- Provenance: Not established
- Validation evidence: None
- Limitations: None recorded

## Amazon Web Services — CloudTrail

- Coverage ID: `secsrc-aws-cloudtrail`
- Status: **NOT_IMPLEMENTED**; runtime: `NOT_IMPLEMENTED`; Splunk: `NOT_OBSERVED`
- Scope: Not established
- Domain / event family: Cloud security / Cloud control-plane audit
- Native format: AWS schema not established
- Transport: None established
- Sourcetype: Not established
- Technology Add-on: Splunk Add-on for AWS; CIM: `NOT_ESTABLISHED`
- Required fields: Not established
- Related scenarios: None
- Distribution: Unavailable
- Sample generation: Blocked — No CloudTrail contract is implemented.
- Provenance: Not established
- Validation evidence: None
- Limitations: None recorded

## Microsoft Azure — Azure Activity Log

- Coverage ID: `secsrc-azure-activity`
- Status: **NOT_IMPLEMENTED**; runtime: `NOT_IMPLEMENTED`; Splunk: `NOT_OBSERVED`
- Scope: Not established
- Domain / event family: Cloud security / Cloud control-plane audit
- Native format: Azure schema not established
- Transport: None established
- Sourcetype: Not established
- Technology Add-on: Splunk Add-on for Microsoft Cloud Services; CIM: `NOT_ESTABLISHED`
- Required fields: Not established
- Related scenarios: None
- Distribution: Unavailable
- Sample generation: Blocked — No Azure Activity contract is implemented.
- Provenance: Not established
- Validation evidence: None
- Limitations: None recorded

## Google Cloud — Cloud Audit Logs

- Coverage ID: `secsrc-gcp-audit`
- Status: **NOT_IMPLEMENTED**; runtime: `NOT_IMPLEMENTED`; Splunk: `NOT_OBSERVED`
- Scope: Not established
- Domain / event family: Cloud security / Cloud control-plane audit
- Native format: GCP schema not established
- Transport: None established
- Sourcetype: Not established
- Technology Add-on: Splunk Add-on for Google Cloud Platform; CIM: `NOT_ESTABLISHED`
- Required fields: Not established
- Related scenarios: None
- Distribution: Unavailable
- Sample generation: Blocked — No GCP audit contract is implemented.
- Provenance: Not established
- Validation evidence: None
- Limitations: None recorded

## Kubernetes — Kubernetes Audit

- Coverage ID: `secsrc-kubernetes-audit`
- Status: **NOT_IMPLEMENTED**; runtime: `NOT_IMPLEMENTED`; Splunk: `NOT_OBSERVED`
- Scope: Not established
- Domain / event family: Cloud security / Cluster API audit
- Native format: Kubernetes audit schema not established
- Transport: None established
- Sourcetype: Not established
- Technology Add-on: Research required; CIM: `NOT_ESTABLISHED`
- Required fields: Not established
- Related scenarios: None
- Distribution: Unavailable
- Sample generation: Blocked — No Kubernetes audit contract is implemented.
- Provenance: Not established
- Validation evidence: None
- Limitations: None recorded

## Unselected — Web application firewall

- Coverage ID: `secsrc-waf`
- Status: **RESEARCH_REQUIRED**; runtime: `RESEARCH_REQUIRED`; Splunk: `NOT_OBSERVED`
- Scope: Not established
- Domain / event family: Application security / WAF events
- Native format: Not selected
- Transport: None established
- Sourcetype: Not established
- Technology Add-on: Not selected; CIM: `NOT_ESTABLISHED`
- Required fields: Not established
- Related scenarios: None
- Distribution: Unavailable
- Sample generation: Blocked — A vendor and authoritative contract must be selected.
- Provenance: Not established
- Validation evidence: None
- Limitations: None recorded

## Unselected — API gateway

- Coverage ID: `secsrc-api-gateway`
- Status: **NOT_IMPLEMENTED**; runtime: `NOT_IMPLEMENTED`; Splunk: `NOT_OBSERVED`
- Scope: Not established
- Domain / event family: Application security / API access and policy events
- Native format: Not selected
- Transport: None established
- Sourcetype: Not established
- Technology Add-on: Not selected; CIM: `NOT_ESTABLISHED`
- Required fields: Not established
- Related scenarios: None
- Distribution: Unavailable
- Sample generation: Blocked — No API gateway contract is implemented.
- Provenance: Not established
- Validation evidence: None
- Limitations: None recorded

## NetSpout — Synthetic application authentication

- Coverage ID: `secsrc-application-auth`
- Status: **PARTIAL**; runtime: `PARTIAL`; Splunk: `NOT_SOURCE_VALIDATED`
- Scope: Modeled only
- Domain / event family: Application security / Authentication
- Native format: NetSpout modeled event
- Transport: HEC
- Sourcetype: Not established
- Technology Add-on: None; CIM: `NOT_ESTABLISHED`
- Required fields: Not established
- Related scenarios: None
- Distribution: SPLUNK_APP, DOCKER_LAB
- Sample generation: Blocked — No independent source contract exists.
- Provenance: Not established
- Validation evidence: None
- Limitations: Modeled application behavior is not a vendor audit source.

## Unselected — Application audit

- Coverage ID: `secsrc-application-audit`
- Status: **NOT_IMPLEMENTED**; runtime: `NOT_IMPLEMENTED`; Splunk: `NOT_OBSERVED`
- Scope: Not established
- Domain / event family: Application security / Application audit
- Native format: Not selected
- Transport: None established
- Sourcetype: Not established
- Technology Add-on: Not selected; CIM: `NOT_ESTABLISHED`
- Required fields: Not established
- Related scenarios: None
- Distribution: Unavailable
- Sample generation: Blocked — No application audit contract is implemented.
- Provenance: Not established
- Validation evidence: None
- Limitations: None recorded

## NetSpout — Agent runtime audit

- Coverage ID: `secsrc-agent-runtime`
- Status: **IMPLEMENTED_AND_VALIDATED**; runtime: `SPLUNK_VALIDATED`; Splunk: `OBSERVED`
- Scope: Phase 12 synthetic instrumentation v1
- Domain / event family: AI and software supply chain / Agent activity and prompt trust
- Native format: NetSpout-defined JSON audit
- Transport: HEC
- Sourcetype: `netspout:phase12:agentic`
- Technology Add-on: None; CIM: `NOT_ESTABLISHED`
- Required fields: `netspout_run_id`, `event_type`, `action`, `outcome`
- Related scenarios: `AI-001`, `AI-004`, `AI-006`
- Distribution: SPLUNK_APP, DOCKER_LAB
- Sample generation: Runnable
- Provenance: OWASP Agentic AI guidance
- Validation evidence: Phase 12 live validation
- Limitations: Instrumentation audit, not native model-provider telemetry.

## Model Context Protocol / NetSpout — MCP instrumentation

- Coverage ID: `secsrc-mcp`
- Status: **IMPLEMENTED_AND_VALIDATED**; runtime: `SPLUNK_VALIDATED`; Splunk: `OBSERVED`
- Scope: MCP 2025-11-25 bounded structures
- Domain / event family: AI and software supply chain / MCP tool and resource activity
- Native format: Protocol-shaped fields plus separate NetSpout audit
- Transport: HEC
- Sourcetype: `netspout:phase12:agentic`
- Technology Add-on: None; CIM: `NOT_ESTABLISHED`
- Required fields: `protocol_family`, `protocol_method`, `outcome`
- Related scenarios: `AI-001`, `AI-002`, `AI-003`, `AI-004`, `AI-006`, `P12-XD-001`
- Distribution: SPLUNK_APP, DOCKER_LAB
- Sample generation: Runnable
- Provenance: MCP 2025-11-25
- Validation evidence: Phase 12 live validation
- Limitations: Not a live external MCP wire capture.

## Agent2Agent Protocol / NetSpout — A2A instrumentation

- Coverage ID: `secsrc-a2a`
- Status: **IMPLEMENTED_AND_VALIDATED**; runtime: `SPLUNK_VALIDATED`; Splunk: `OBSERVED`
- Scope: A2A 1.0.0 bounded structures
- Domain / event family: AI and software supply chain / Agent task and delegation
- Native format: Protocol-shaped fields plus separate NetSpout audit
- Transport: HEC
- Sourcetype: `netspout:phase12:agentic`
- Technology Add-on: None; CIM: `NOT_ESTABLISHED`
- Required fields: `protocol_family`, `correlation_id`, `outcome`
- Related scenarios: `AI-005`, `AI-006`
- Distribution: SPLUNK_APP, DOCKER_LAB
- Sample generation: Runnable
- Provenance: A2A 1.0.0
- Validation evidence: Phase 12 live validation
- Limitations: Not a live external A2A wire capture.

## NetSpout — Agent tool authorization audit

- Coverage ID: `secsrc-tool-authorization`
- Status: **IMPLEMENTED_AND_VALIDATED**; runtime: `SPLUNK_VALIDATED`; Splunk: `OBSERVED`
- Scope: Phase 12 instrumentation v1
- Domain / event family: AI and software supply chain / Tool policy decisions
- Native format: NetSpout-defined JSON audit
- Transport: HEC
- Sourcetype: `netspout:phase12:agentic`
- Technology Add-on: None; CIM: `NOT_ESTABLISHED`
- Required fields: `action`, `outcome`, `correlation_id`
- Related scenarios: `AI-002`, `AI-004`, `P12-XD-001`
- Distribution: SPLUNK_APP, DOCKER_LAB
- Sample generation: Runnable
- Provenance: NetSpout audit schema
- Validation evidence: Phase 12 live validation
- Limitations: Authorization is instrumentation, not a universal MCP/A2A field.

## NetSpout — Repository audit

- Coverage ID: `secsrc-repository-audit`
- Status: **IMPLEMENTED_AND_VALIDATED**; runtime: `SPLUNK_VALIDATED`; Splunk: `OBSERVED`
- Scope: Phase 12 synthetic v1
- Domain / event family: AI and software supply chain / Repository and automation actions
- Native format: NetSpout-defined JSON audit
- Transport: HEC
- Sourcetype: `netspout:phase12:supply_chain`
- Technology Add-on: None; CIM: `NOT_ESTABLISHED`
- Required fields: `event_type`, `action`, `outcome`
- Related scenarios: `SC-001`, `SC-004`, `SC-005`
- Distribution: SPLUNK_APP, DOCKER_LAB
- Sample generation: Runnable
- Provenance: NetSpout audit schema
- Validation evidence: Phase 12 live validation
- Limitations: Not native GitHub or GitLab audit telemetry.

## NetSpout — CI/CD audit

- Coverage ID: `secsrc-cicd-audit`
- Status: **IMPLEMENTED_AND_VALIDATED**; runtime: `SPLUNK_VALIDATED`; Splunk: `OBSERVED`
- Scope: Phase 12 synthetic v1
- Domain / event family: AI and software supply chain / Workflow and build policy
- Native format: NetSpout-defined JSON audit
- Transport: HEC
- Sourcetype: `netspout:phase12:supply_chain`
- Technology Add-on: None; CIM: `NOT_ESTABLISHED`
- Required fields: `action`, `outcome`, `correlation_id`
- Related scenarios: `SC-002`, `SC-005`
- Distribution: SPLUNK_APP, DOCKER_LAB
- Sample generation: Runnable
- Provenance: NetSpout audit schema
- Validation evidence: Phase 12 live validation
- Limitations: Not native hosted-CI audit telemetry.

## SLSA / NetSpout — Build provenance

- Coverage ID: `secsrc-build-provenance`
- Status: **IMPLEMENTED_AND_VALIDATED**; runtime: `SPLUNK_VALIDATED`; Splunk: `OBSERVED`
- Scope: SLSA v1.1 modeled predicate subset
- Domain / event family: AI and software supply chain / Provenance validation
- Native format: SLSA-shaped statement plus NetSpout audit
- Transport: HEC
- Sourcetype: `netspout:phase12:supply_chain`
- Technology Add-on: None; CIM: `NOT_ESTABLISHED`
- Required fields: `outcome`, `correlation_id`
- Related scenarios: `SC-003`, `SC-005`, `P12-XD-002`
- Distribution: SPLUNK_APP, DOCKER_LAB
- Sample generation: Runnable
- Provenance: SLSA v1.1
- Validation evidence: Phase 12 live validation
- Limitations: No external attestation signature is generated.

## NetSpout — Artifact attestation validation

- Coverage ID: `secsrc-artifact-attestation`
- Status: **PARTIAL**; runtime: `PARTIAL`; Splunk: `OBSERVED_MODELED_GAP`
- Scope: Modeled presence/absence only
- Domain / event family: AI and software supply chain / Artifact attestation
- Native format: NetSpout-defined audit
- Transport: HEC
- Sourcetype: `netspout:phase12:supply_chain`
- Technology Add-on: None; CIM: `NOT_ESTABLISHED`
- Required fields: `outcome`, `correlation_id`
- Related scenarios: `SC-003`, `P12-XD-002`
- Distribution: SPLUNK_APP, DOCKER_LAB
- Sample generation: Blocked — No signed external attestation contract is implemented.
- Provenance: SLSA v1.1
- Validation evidence: Phase 12 live validation
- Limitations: Missing provenance is not malicious evidence.
