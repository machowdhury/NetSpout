#!/usr/bin/env python3
"""Build the curated Cisco 100 definition catalog.

Scenario concepts are intentionally separate from telemetry implementation.
Only the accepted Phase 7 scenario receives executable/GOLDEN claims.
"""

from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "catalog" / "cisco_100_scenarios.json"

DOMAINS = {
    "Enterprise Networking": [
        ("Campus Access Link Degradation", "INTERFACE_HEALTH", ["IOS XE", "Catalyst Switching"], "Rising errors and loss on a campus access link", "User access to local and cloud applications becomes intermittent."),
        ("Distribution Uplink Failure", "INTERFACE_FAILURE", ["IOS XE", "Catalyst Switching"], "A distribution uplink transitions out of service", "A campus building loses resilient upstream connectivity."),
        ("Campus Oversubscription Congestion", "CONGESTION", ["Catalyst Switching"], "Sustained demand exceeds an aggregation path", "Interactive and voice traffic experience delay and loss."),
        ("Branch WAN Packet Loss", "WAN_DEGRADATION", ["IOS XE", "Cisco SD-WAN"], "A branch WAN path develops progressive packet loss", "Branch users experience unstable access to shared services."),
        ("SD-WAN Preferred-Path Change", "PATH_CHANGE", ["Cisco SD-WAN"], "Policy or path health causes a preferred-path transition", "Applications may move to a higher-latency or lower-capacity circuit."),
        ("SD-WAN Brownout Before Failover", "WAN_DEGRADATION", ["Cisco SD-WAN"], "A transport degrades before the failover threshold is crossed", "Application quality falls before redundancy restores service."),
        ("Campus Routing Adjacency Instability", "ROUTING_INSTABILITY", ["IOS XE", "Catalyst Switching"], "A routed campus adjacency repeatedly changes state", "Route convergence disrupts access across campus segments."),
        ("Branch Route Withdrawal", "ROUTING_CHANGE", ["IOS XE"], "A branch prefix is withdrawn from the enterprise routing domain", "Central services lose reachability to a remote site."),
        ("Wireless Client Roaming Failure", "WIRELESS", ["Cisco Wireless"], "A client transition between access points does not preserve service", "Mobile users lose sessions while moving through the campus."),
        ("Wireless Capacity Saturation", "WIRELESS_CONGESTION", ["Cisco Wireless"], "Client density drives airtime contention", "High-density users experience low throughput and latency."),
        ("Campus DHCP Dependency Failure", "DEPENDENCY_FAILURE", ["Catalyst Switching", "IOS XE"], "Address assignment becomes unavailable to a campus segment", "New clients cannot establish usable network service."),
        ("Campus DNS Path Degradation", "APPLICATION_PATH", ["IOS XE", "Catalyst Switching"], "The network path to enterprise DNS degrades", "Name resolution delays appear as broad application failures."),
        ("Network Access Authentication Delay", "ACCESS_CONTROL", ["Cisco ISE", "Catalyst Switching"], "Network access decisions exceed expected latency", "Users and devices experience delayed or failed onboarding."),
        ("Network Access Authorization Drift", "CONFIGURATION_DRIFT", ["Cisco ISE", "Catalyst Switching"], "Enforcement state diverges from intended authorization", "Devices receive incorrect access or segmentation policy."),
        ("Campus Path Asymmetry", "PATH_ASYMMETRY", ["IOS XE", "Catalyst Switching"], "Forward and return traffic take materially different paths", "Stateful services and troubleshooting become unreliable."),
        ("Catalyst Configuration Drift", "CONFIGURATION_DRIFT", ["Catalyst Switching", "Catalyst Center"], "Observed device state diverges from approved intent", "Operational consistency and change assurance are reduced."),
        ("Catalyst Center Assurance Data Gap", "TELEMETRY_DEGRADATION", ["Catalyst Center"], "Assurance observations become delayed or incomplete", "Operations teams lose timely campus health visibility."),
        ("Meraki Multi-Site Reachability Degradation", "MULTI_SITE", ["Cisco Meraki"], "Multiple managed sites show correlated reachability loss", "Distributed business locations lose access to central services."),
        ("Branch Application Path Regression", "APPLICATION_PATH", ["IOS XE", "Cisco SD-WAN"], "A path change raises application latency without total outage", "Transaction response times breach user expectations."),
        ("Enterprise Telemetry Blind Spot", "TELEMETRY_DEGRADATION", ["IOS XE", "Catalyst Switching"], "Expected network telemetry stops while forwarding continues", "Operators cannot distinguish healthy service from lost observability."),
    ],
    "Service Provider & Carrier": [
        ("IOS XR Interface Degradation", "INTERFACE_HEALTH", ["IOS XR", "Cisco 8000"], "A provider-edge interface degrades and recovers", "A customer-facing service experiences bounded degradation before recovery."),
        ("Carrier Interface Error Burst", "INTERFACE_HEALTH", ["IOS XR", "Cisco 8000"], "A carrier interface develops a burst of errors", "Packet loss affects services sharing the physical path."),
        ("BGP Peer Session Instability", "BGP", ["IOS XR"], "A peering session repeatedly changes state", "Route availability and convergence become unstable."),
        ("BGP Route Withdrawal Propagation", "BGP", ["IOS XR"], "A reachable prefix is withdrawn across provider edges", "Customers lose reachability until an alternate route converges."),
        ("Provider Edge Access Link Failure", "PE_CE", ["IOS XR", "Cisco 8000"], "A PE-to-CE access link fails", "One customer site loses primary provider connectivity."),
        ("BGP Path Preference Shift", "BGP", ["IOS XR"], "Routing policy selects a different available path", "Traffic moves to a path with different latency or capacity."),
        ("Route Reflector Propagation Delay", "CONTROL_PLANE", ["IOS XR"], "Route distribution is delayed through reflection topology", "Convergence extends beyond operational objectives."),
        ("MPLS Label-Switched Path Degradation", "MPLS", ["IOS XR"], "An MPLS forwarding path degrades without total loss", "Multiple services experience partial transport impairment."),
        ("MPLS VPN Reachability Loss", "MPLS_VPN", ["IOS XR"], "A VPN route or forwarding dependency becomes unavailable", "A tenant loses connectivity between sites."),
        ("Segment Routing Policy Path Change", "SEGMENT_ROUTING", ["IOS XR"], "A segment-routing policy selects an alternate path", "Traffic engineering intent changes service latency and capacity."),
        ("SR-MPLS Constraint Violation", "SEGMENT_ROUTING", ["IOS XR"], "Available paths cannot satisfy an SR-MPLS policy constraint", "Engineered service objectives cannot be maintained."),
        ("SRv6 Service Path Interruption", "SRV6", ["IOS XR"], "An SRv6 service path loses a required segment", "Traffic using the policy cannot complete its intended path."),
        ("Carrier Core Congestion", "CONGESTION", ["IOS XR", "Cisco 8000"], "Core demand exceeds an engineered link or queue", "Multiple downstream services experience latency and loss."),
        ("Provider Traffic Engineering Imbalance", "TRAFFIC_ENGINEERING", ["IOS XR"], "Traffic distribution diverges from engineering intent", "One path saturates while alternate capacity remains unused."),
        ("Optical Transport Dependency Degradation", "TRANSPORT_DEPENDENCY", ["IOS XR", "Cisco 8000"], "A lower-layer transport dependency degrades", "Packet-layer services inherit instability from the transport layer."),
        ("IOS XR Model-Driven Telemetry Loss", "TELEMETRY_DEGRADATION", ["IOS XR"], "A model-driven telemetry stream becomes incomplete", "Operations lose timely state while forwarding may continue."),
        ("Inter-AS Routing Leak Candidate", "ROUTING_POLICY", ["IOS XR"], "Unexpected route propagation crosses an administrative boundary", "Traffic may follow unauthorized or unstable inter-domain paths."),
        ("Carrier Control-Plane Resource Pressure", "CONTROL_PLANE", ["IOS XR"], "Control-plane workload rises beyond expected bounds", "Protocol processing and convergence may be delayed."),
        ("Multi-Domain Path Failover", "MULTI_DOMAIN_ROUTING", ["IOS XR"], "A service fails over across multiple routing domains", "Customer traffic experiences a cross-domain path transition."),
        ("PE-CE Policy Mismatch", "PE_CE", ["IOS XR"], "Provider-edge and customer-edge routing policies disagree", "Expected customer routes are rejected or preferred incorrectly."),
    ],
    "Data Center & AI Cloud": [
        ("Nexus Fabric Uplink Degradation", "INTERFACE_HEALTH", ["NX-OS", "Cisco Nexus"], "A data-center fabric uplink degrades", "East-west application traffic experiences loss and latency."),
        ("Nexus vPC Member Failure", "FABRIC_REDUNDANCY", ["NX-OS", "Cisco Nexus"], "A virtual port-channel member becomes unavailable", "Redundancy and available fabric capacity are reduced."),
        ("EVPN Route Withdrawal", "EVPN_VXLAN", ["NX-OS", "Cisco Nexus"], "An EVPN route is withdrawn from the overlay", "Remote endpoints become unreachable through the fabric."),
        ("VXLAN Tunnel Endpoint Reachability Loss", "EVPN_VXLAN", ["NX-OS", "Cisco Nexus"], "A tunnel endpoint loses underlay reachability", "Overlay segments lose connectivity across the fabric."),
        ("ACI Leaf-Spine Link Failure", "ACI_FABRIC", ["Cisco ACI"], "A leaf-to-spine path fails", "Fabric convergence may affect tenant application paths."),
        ("ACI Endpoint Movement Anomaly", "ACI_ENDPOINT", ["Cisco ACI"], "An endpoint moves unexpectedly between attachment points", "Policy and forwarding convergence can disrupt application access."),
        ("ACI Contract Policy Denial", "ACI_POLICY", ["Cisco ACI"], "Fabric policy denies an expected application flow", "An application tier loses required east-west communication."),
        ("Data Center East-West Congestion", "CONGESTION", ["Cisco Nexus", "Cisco ACI"], "East-west demand exceeds a fabric path", "Distributed application latency and retransmission increase."),
        ("Underlay Routing Instability", "UNDERLAY_ROUTING", ["NX-OS", "Cisco Nexus"], "Fabric underlay adjacencies become unstable", "Overlay reachability fluctuates across multiple tenants."),
        ("Overlay-Underlay Correlation Gap", "TELEMETRY_DEGRADATION", ["NX-OS", "Cisco ACI"], "Overlay symptoms cannot be correlated with underlay state", "Root-cause isolation is delayed."),
        ("UCS Fabric Interconnect Degradation", "COMPUTE_NETWORK", ["Cisco UCS"], "A compute fabric interconnect path degrades", "Server connectivity and storage access may be impaired."),
        ("UCS Service Profile Drift", "CONFIGURATION_DRIFT", ["Cisco UCS"], "Applied compute/network policy diverges from intended profile", "Workload placement and connectivity become inconsistent."),
        ("Intersight Managed-System Visibility Gap", "TELEMETRY_DEGRADATION", ["Cisco Intersight"], "Managed infrastructure observations become incomplete", "Cloud operations lose reliable health and inventory context."),
        ("Hybrid Cloud Data Path Degradation", "HYBRID_CLOUD", ["Cisco Nexus", "Cisco Intersight"], "The data-center-to-cloud path develops latency or loss", "Hybrid workloads miss response-time objectives."),
        ("Storage Network Dependency Congestion", "STORAGE_NETWORK", ["Cisco Nexus"], "Storage traffic contends for constrained network capacity", "Application I/O latency and recovery times increase."),
        ("Application Tier Fabric Isolation", "APPLICATION_DEPENDENCY", ["Cisco ACI"], "A fabric or policy condition isolates one application tier", "Transactions fail despite healthy compute instances."),
        ("GPU Fabric East-West Congestion Candidate", "AI_FABRIC", ["Cisco Nexus"], "Distributed accelerator traffic encounters fabric congestion", "Training or inference jobs lose throughput and predictability."),
        ("Lossless Ethernet Pause Propagation Candidate", "LOSSLESS_ETHERNET", ["Cisco Nexus"], "Flow-control pressure propagates across a lossless fabric", "High-performance workloads experience head-of-line blocking."),
        ("AI Cluster Network Telemetry Gap", "TELEMETRY_DEGRADATION", ["Cisco Nexus"], "Required high-performance fabric observations are absent", "Operators cannot distinguish workload bottlenecks from network loss."),
        ("Multi-Fabric Data Center Service Impact", "MULTI_FABRIC", ["Cisco ACI", "Cisco Nexus"], "A dependency spanning fabrics degrades", "A distributed service experiences failures across data-center boundaries."),
    ],
    "Security & SASE": [
        ("Secure Firewall Suspicious Connection Burst", "FIREWALL_ACTIVITY", ["Cisco Secure Firewall"], "A burst of suspicious outbound connections appears", "Security teams must distinguish attack behavior from workload change."),
        ("FTD Access-Control Policy Denial", "POLICY_VIOLATION", ["Cisco FTD", "Cisco FMC"], "An access-control rule denies a required flow", "A business service becomes unavailable due to enforcement."),
        ("ASA Remote Access Failure", "REMOTE_ACCESS", ["Cisco ASA"], "Remote access sessions fail to establish", "Remote workers lose access to protected applications."),
        ("Firewall Rulebase Drift", "CONFIGURATION_DRIFT", ["Cisco Secure Firewall", "Cisco FMC"], "Deployed firewall policy diverges from approved intent", "Security posture and application reachability become uncertain."),
        ("ISE Authentication Failure Spike", "IDENTITY_ACCESS", ["Cisco ISE"], "Network authentication failures rise sharply", "Users and devices cannot obtain expected access."),
        ("ISE Policy Authorization Mismatch", "IDENTITY_ACCESS", ["Cisco ISE"], "Authorization outcomes diverge from intended policy", "Devices receive inappropriate or insufficient access."),
        ("Secure Access Policy Block", "SASE_POLICY", ["Cisco Secure Access"], "A cloud-delivered access policy blocks a required application", "Users lose access while network transport remains healthy."),
        ("Umbrella DNS Abuse Indicator", "DNS_SECURITY", ["Cisco Umbrella"], "DNS behavior indicates possible abuse", "Potential malicious infrastructure or policy evasion requires investigation."),
        ("Umbrella DNS Tunneling Candidate", "DNS_SECURITY", ["Cisco Umbrella"], "DNS request patterns resemble covert data transport", "Sensitive data may leave through an allowed protocol."),
        ("Secure Endpoint Malware Activity Candidate", "ENDPOINT_SECURITY", ["Cisco Secure Endpoint"], "Endpoint behavior indicates possible malware execution", "A compromised host may affect users and adjacent systems."),
        ("Secure Endpoint Isolation Impact", "ENDPOINT_RESPONSE", ["Cisco Secure Endpoint"], "An endpoint containment action changes network reachability", "Business access is intentionally restricted during response."),
        ("Secure Network Analytics Beaconing Candidate", "NETWORK_ANALYTICS", ["Cisco Secure Network Analytics"], "Periodic connection behavior resembles command-and-control beaconing", "A persistent compromise may be communicating externally."),
        ("Secure Network Analytics Lateral Movement Candidate", "LATERAL_MOVEMENT", ["Cisco Secure Network Analytics"], "Internal connection behavior suggests lateral movement", "Additional systems may be exposed after initial compromise."),
        ("Secure Client Posture Failure", "REMOTE_ACCESS", ["Cisco Secure Client"], "Endpoint posture does not satisfy access policy", "A user cannot establish or retain remote access."),
        ("Duo Authentication Anomaly", "IDENTITY_SECURITY", ["Cisco Duo"], "Authentication behavior deviates from the expected user pattern", "Credential misuse or account compromise may be present."),
        ("Cisco XDR Cross-Signal Incident Candidate", "XDR_CORRELATION", ["Cisco XDR"], "Multiple security signals appear related to one incident", "Analysts need a coherent cross-product timeline."),
        ("Secure Workload Policy Violation Candidate", "WORKLOAD_SECURITY", ["Cisco Secure Workload"], "Workload communication violates intended segmentation", "East-west exposure increases within the data center."),
        ("Cyber Vision OT Asset Anomaly Candidate", "OT_SECURITY", ["Cisco Cyber Vision"], "Observed industrial asset behavior changes unexpectedly", "Operational technology safety and availability require review."),
        ("Reconnaissance and Firewall Correlation", "RECONNAISSANCE", ["Cisco Secure Firewall"], "Connection attempts span many targets or services", "Reconnaissance may precede exploitation."),
        ("Potential Exfiltration Path Correlation", "EXFILTRATION", ["Cisco Secure Firewall", "Cisco Umbrella"], "Outbound volume and destination behavior suggest possible staging or exfiltration", "Sensitive information may be leaving the environment."),
    ],
    "Sovereign Critical Infrastructure & Mixed Cross-Domain": [
        ("Financial Trading Campus-to-Data-Center Latency", "FINANCIAL_SERVICES", ["IOS XE", "Cisco Nexus"], "Latency rises across campus and data-center dependencies", "Time-sensitive trading workflows miss execution objectives."),
        ("Telecom Operations Network Degradation", "TELECOMMUNICATIONS", ["IOS XR", "Catalyst Switching"], "Operations connectivity degrades alongside carrier infrastructure", "Network operations lose reliable control and visibility."),
        ("Utility Substation WAN Loss", "UTILITIES", ["IOS XE", "Cisco Industrial Networking"], "A remote substation WAN path loses reliability", "Monitoring and control communications become impaired."),
        ("Energy Pipeline Remote-Site Isolation", "ENERGY", ["Cisco Industrial Networking", "IOS XE"], "A remote energy site loses upstream connectivity", "Operational telemetry and remote support become unavailable."),
        ("Manufacturing Cell Network Congestion", "MANUFACTURING", ["Cisco Industrial Networking", "Catalyst Switching"], "Production-cell traffic contends for constrained capacity", "Automation timing and production throughput degrade."),
        ("Healthcare Clinical Application Path Failure", "HEALTHCARE", ["IOS XE", "Cisco Wireless"], "A clinical application path fails across wired or wireless access", "Care teams lose timely access to clinical systems."),
        ("Transportation Control-Site Failover", "TRANSPORTATION", ["IOS XE", "Cisco SD-WAN"], "A control site transitions to backup connectivity", "Operational communications continue with reduced capacity."),
        ("Public Sector Identity and Network Access Failure", "PUBLIC_SECTOR", ["Cisco ISE", "Catalyst Switching"], "Identity and network enforcement fail to establish access", "Staff cannot reach protected public-sector services."),
        ("Remote Infrastructure Telemetry Blackout", "REMOTE_INFRASTRUCTURE", ["IOS XE", "Cisco Industrial Networking"], "Remote telemetry disappears while service state is uncertain", "Operators cannot distinguish communications loss from site failure."),
        ("OT/IT Segmentation Policy Drift", "OT_ICS", ["Cisco Cyber Vision", "Cisco Secure Firewall"], "Segmentation intent diverges between industrial and enterprise zones", "Critical assets may gain unintended exposure or lose required access."),
        ("Sovereign Cloud Interconnect Degradation", "SOVEREIGN_CLOUD", ["Cisco Nexus", "IOS XR"], "A regulated cloud interconnect develops latency or loss", "Data-residency workloads lose predictable connectivity."),
        ("Critical Communications Path Congestion", "CRITICAL_COMMUNICATIONS", ["IOS XR", "IOS XE"], "Priority communications share a congested path", "Emergency or operational communications may be delayed."),
        ("Distributed Government Site Outage", "PUBLIC_SECTOR", ["Cisco SD-WAN", "IOS XE"], "Multiple government sites lose a common dependency", "Citizen and internal services become unavailable across regions."),
        ("Mixed-Vendor Application Delivery Degradation", "MIXED_VENDOR", ["Cisco Campus", "Palo Alto Networks", "F5", "AWS"], "A multi-vendor application path degrades", "Users experience service impact spanning ownership boundaries."),
        ("Cisco Network and Microsoft Identity Correlation", "MIXED_VENDOR_IDENTITY", ["Cisco Network", "Microsoft Identity"], "Network-access symptoms coincide with identity anomalies", "Investigators need cross-domain evidence without inferred wire formats."),
        ("Hybrid Hospital Wireless and Cloud Dependency", "HEALTHCARE", ["Cisco Wireless", "Microsoft Azure"], "Wireless access and cloud dependency symptoms overlap", "Clinical workflows become slow or unavailable."),
        ("Industrial Site Security and Availability Incident", "OT_ICS", ["Cisco Cyber Vision", "Cisco Secure Firewall", "Cisco Industrial Networking"], "Security indicators coincide with an industrial connectivity impact", "Response must preserve both safety and service continuity."),
        ("Cross-Domain DNS Dependency Failure", "SHARED_SERVICE", ["Cisco Umbrella", "IOS XE", "AWS"], "A shared DNS dependency affects sites and cloud services", "Multiple domains present application failures simultaneously."),
        ("Sovereign Multi-Region Routing Instability", "SOVEREIGN_NETWORK", ["IOS XR", "Cisco SD-WAN"], "Routing instability spans regulated geographic regions", "Critical services experience intermittent cross-region reachability."),
        ("National Critical Infrastructure Evidence Gap", "EVIDENCE_DEBT", ["Cisco Industrial Networking", "Cisco Security"], "Required authoritative telemetry evidence is incomplete across domains", "Simulation must remain blocked until trust and provenance are established."),
    ],
}

PREFIX = {
    "Enterprise Networking": "ENT",
    "Service Provider & Carrier": "SP",
    "Data Center & AI Cloud": "DC",
    "Security & SASE": "SEC",
    "Sovereign Critical Infrastructure & Mixed Cross-Domain": "CRI",
}

DOMAIN_STATE = {
    "Enterprise Networking": "path.health",
    "Service Provider & Carrier": "service.path_health",
    "Data Center & AI Cloud": "fabric.health",
    "Security & SASE": "security.investigation_state",
    "Sovereign Critical Infrastructure & Mixed Cross-Domain": "cross_domain.service_health",
}

IOS_XR_REUSE = {"C100-SP-001", "C100-SP-002", "C100-SP-005"}


def base_scenario(domain, index, spec):
    title, category, technologies, vector, impact = spec
    scenario_id = f"C100-{PREFIX[domain]}-{index:03d}"
    state_key = DOMAIN_STATE[domain]
    research_required = index >= 16 and scenario_id != "C100-SP-001"
    maturity = "RESEARCH_REQUIRED" if research_required else "CANDIDATE"
    validation = "RESEARCH_BLOCKED" if research_required else "DEFINITION_VALIDATED"
    reuse = scenario_id in IOS_XR_REUSE

    scenario = {
        "scenario_id": scenario_id,
        "title": title,
        "domain": domain,
        "category": category,
        "difficulty": "INTERMEDIATE",
        "story": (
            f"A fictional test enterprise experiences {title.lower()}. "
            "Operators must establish a coherent timeline without inferring unsupported telemetry."
        ),
        "technical_objective": (
            f"Model the state progression for {title.lower()}, identify affected "
            "entities, and determine which evidence is required for defensible investigation."
        ),
        "business_impact": impact,
        "technologies": technologies,
        "entities": [f"{PREFIX[domain].lower()}-site.example", "affected-service.example"],
        "relationships": ["site depends on affected service path"],
        "zones": ["Reserved Test Environment", domain],
        "failure_or_attack_vector": vector,
        "enterprise_state": {state_key: "HEALTHY"},
        "timeline": [
            {
                "stage": "BASELINE",
                "offset_seconds": 0,
                "state_changes": {state_key: "HEALTHY"},
                "expected_observation": "The modeled service begins within healthy bounds.",
            },
            {
                "stage": "INCIDENT",
                "offset_seconds": 300,
                "state_changes": {state_key: "IMPAIRED"},
                "expected_observation": f"The modeled state reflects {vector.lower()}.",
            },
            {
                "stage": "RECOVERY",
                "offset_seconds": 600,
                "state_changes": {state_key: "HEALTHY"},
                "expected_observation": "The modeled service returns to healthy bounds.",
            },
        ],
        "state_transitions": ["HEALTHY", "IMPAIRED", "HEALTHY"],
        "telemetry_sources": [],
        "native_transports": [],
        "source_contracts": [],
        "product_packs": [],
        "splunk_integrations": [],
        "sourcetypes": [],
        "cim_relationships": {},
        "evidence_references": [],
        "investigation_pack": {
            "status": "RESEARCH_REQUIRED",
            "recipe_ids": [],
            "questions": [
                "Which entity changed first?",
                "Which dependency explains the modeled impact?",
            ],
            "expected_findings": [],
            "spl_classifications": [],
        },
        "troubleshooting_pack": {
            "status": "RESEARCH_REQUIRED",
            "operation_ids": [],
            "research_required": [
                "Authoritative platform operation and version applicability"
            ],
        },
        "production_portability": {
            "status": "NOT_ESTABLISHED",
            "guide_id": None,
            "production_portable_spl": [],
            "netspout_specific_spl": [],
            "requirements": [],
            "known_gaps": ["Collection and normalization requirements are not established."],
        },
        "maturity": maturity,
        "validation_state": validation,
        "research_gaps": (
            [
                "Authoritative native telemetry contract",
                "Verified transport and product-version applicability",
                "Evidence-backed Splunk integration and sourcetype relationship",
            ]
            if research_required
            else [
                "Scenario has not entered authoritative telemetry research.",
                "Execution remains disabled until maturity gates are satisfied.",
            ]
        ),
        "limitations": [
            "Scenario definition does not imply telemetry or product support.",
            "No fallback telemetry, sourcetype, integration, or CIM mapping is generated.",
        ],
        "runtime_scenario_id": None,
        "execution_enabled": False,
        "shared_state": True,
        "guided_experience": False,
        "topology_available": True,
        "replay_supported": False,
        "format_validation": [],
        "runtime_validation": [],
        "splunk_validation": [],
    }

    if reuse:
        scenario.update(
            {
                "telemetry_sources": [
                    "cisco-ios-xr-interface-syslog",
                    "ietf-snmpv2c-ifmib",
                    "openconfig-gnmi-interfaces",
                ],
                "native_transports": [
                    "transport-native-gnmi-grpc",
                    "transport-native-snmp-udp",
                    "transport-native-syslog-udp",
                ],
                "source_contracts": [
                    "native-cisco-ios-xr-interface-syslog",
                    "netspout-ietf-snmpv2c-ifmib",
                    "netspout-openconfig-gnmi-interfaces",
                ],
                "product_packs": ["cisco-ios-xr-coverage"],
                "splunk_integrations": [
                    "splunkbase-cisco-enterprise-networking-7538"
                ],
                "sourcetypes": [
                    "netspout:cisco:iosxr:syslog",
                    "openconfig:gnmi:telemetry",
                ],
                "cim_relationships": {
                    "netspout:cisco:iosxr:syslog": "NOT_ESTABLISHED",
                    "openconfig:gnmi:telemetry": "NOT_ESTABLISHED",
                },
                "evidence_references": [
                    "COV-CISCO-IOSXR-SYSLOG-FORMAT",
                    "COV-CISCO-IOSXR-LINK-UPDOWN",
                    "COV-CISCO-IOSXR-GNMI",
                    "COV-CISCO-IOSXR-SNMP",
                    "COV-SPLUNK-CISCO-7538",
                ],
            }
        )

    if scenario_id == "C100-SP-001":
        scenario.update(
            {
                "entities": [
                    "cisco-asr9k-pe1",
                    "HundredGigE0/0/0/1",
                    "bundled-syslog-receiver",
                    "bundled-snmp-receiver",
                    "bundled-gnmi-subscriber",
                    "test-local-splunk.invalid",
                ],
                "relationships": [
                    "Cisco 8000 edge contains the affected interface",
                    "affected interface emits documented IOS XR syslog",
                    "affected interface exposes IF-MIB state",
                    "affected interface publishes OpenConfig state",
                    "post-receipt records are delivered to the local test destination",
                ],
                "zones": [
                    "Reserved Test Enterprise",
                    "Bundled Native Receivers",
                    "Local Test Destination",
                ],
                "enterprise_state": {
                    "interface.status": "UP",
                    "interface.loss": "0",
                    "interface.utilization": "25",
                    "path.health": "HEALTHY",
                },
                "timeline": [
                    {
                        "stage": "BASELINE",
                        "offset_seconds": 0,
                        "state_changes": {
                            "interface.status": "UP",
                            "interface.loss": "0",
                            "path.health": "HEALTHY",
                        },
                        "expected_observation": "All three native channels establish the healthy test interface baseline.",
                    },
                    {
                        "stage": "DEGRADE",
                        "offset_seconds": 60,
                        "state_changes": {
                            "interface.status": "DEGRADED",
                            "interface.loss": "8",
                            "path.health": "IMPAIRED",
                        },
                        "expected_observation": "The shared state projects one bounded degradation through each native channel.",
                    },
                    {
                        "stage": "FAILOVER",
                        "offset_seconds": 120,
                        "state_changes": {
                            "interface.status": "DOWN",
                            "interface.loss": "100",
                            "path.health": "FAILED_OVER",
                        },
                        "expected_observation": "Receiver evidence preserves one entity and interface identity during failover.",
                    },
                    {
                        "stage": "RECOVERY",
                        "offset_seconds": 180,
                        "state_changes": {
                            "interface.status": "UP",
                            "interface.loss": "0",
                            "path.health": "HEALTHY",
                        },
                        "expected_observation": "All native channels and Splunk observations complete the same recovery lifecycle.",
                    },
                ],
                "state_transitions": [
                    "BASELINE",
                    "DEGRADE",
                    "FAILOVER",
                    "RECOVERY",
                ],
                "maturity": "GOLDEN",
                "validation_state": "LIVE_VALIDATED",
                "runtime_scenario_id": "test-correlated-interface-degradation",
                "execution_enabled": True,
                "guided_experience": True,
                "replay_supported": True,
                "format_validation": [
                    "IOS XR syslog structure validated separately from modeled values",
                    "IF-MIB and OpenConfig structures validated by reusable protocol Packs",
                ],
                "runtime_validation": [
                    "Syslog UDP receiver observed",
                    "SNMP receiver observed",
                    "gNMI collector observed",
                ],
                "splunk_validation": [
                    "Fresh Phase 7 observation proved raw, sourcetype, and fields"
                ],
                "investigation_pack": {
                    "status": "AVAILABLE",
                    "recipe_ids": ["investigate-correlated-interface-degradation"],
                    "questions": [
                        "Do three native channels describe the same interface lifecycle?"
                    ],
                    "expected_findings": [
                        "The reserved test interface degrades and recovers in causal order."
                    ],
                    "spl_classifications": ["NETSPOUT_SPECIFIC"],
                },
                "troubleshooting_pack": {
                    "status": "AVAILABLE",
                    "operation_ids": ["cisco-ios-xr-show-interfaces"],
                    "research_required": [],
                },
                "production_portability": {
                    "status": "AVAILABLE",
                    "guide_id": "guide-cisco-ios-xr-interface-degradation",
                    "production_portable_spl": [
                        "index=<network_index> (host=<router> OR device_id=<router>) | stats values(*) by sourcetype"
                    ],
                    "netspout_specific_spl": [
                        'search index=idx_network_ops netspout_scenario_id="test-correlated-interface-degradation" netspout_run_id="$run_id$"'
                    ],
                    "requirements": [
                        "Real IOS XR sources and vendor-supported collection",
                        "Installed integrations validated against deployed releases",
                    ],
                    "known_gaps": [
                        "Official app 7538 IOS XR sourcetype and CIM behavior",
                        "Production sizing and security configuration",
                    ],
                },
                "research_gaps": [
                    "Official app 7538 IOS XR sourcetype",
                    "Runtime CIM mapping",
                ],
            }
        )
    if scenario_id == "C100-CRI-014":
        scenario.update(
            {
                "entities": [
                    "cisco-campus-cri.example",
                    "palo-alto-edge-cri.example",
                    "f5-app-delivery-cri.example",
                    "aws-workload-cri.example",
                    "affected-service.example",
                ],
                "relationships": [
                    "Cisco campus forwards to the external security edge",
                    "external security edge forwards to application delivery",
                    "application delivery forwards to the cloud workload",
                    "cloud workload provides the affected service",
                ],
                "zones": [
                    "Reserved Test Campus",
                    "Mixed-Vendor Security Edge",
                    "Cloud Application Zone",
                ],
            }
        )
    return scenario


def build_catalog():
    scenarios = [
        base_scenario(domain, index, spec)
        for domain, specs in DOMAINS.items()
        for index, spec in enumerate(specs, start=1)
    ]
    research_queue = []
    for scenario in scenarios:
        for gap_index, gap in enumerate(scenario["research_gaps"], start=1):
            lower_gap = gap.lower()
            if "cim" in lower_gap:
                evidence_type = "Fresh Splunk CIM runtime validation"
                blocking_gate = "CIM_RUNTIME_VALIDATED"
            elif "splunk" in lower_gap or "sourcetype" in lower_gap:
                evidence_type = "Splunk integration and parsing documentation"
                blocking_gate = (
                    "PRODUCTION_PORTABILITY"
                    if scenario["maturity"] == "GOLDEN"
                    else "CONTRACTED"
                )
            else:
                evidence_type = "Authoritative vendor or standards documentation"
                blocking_gate = (
                    "CONTRACTED"
                    if scenario["maturity"] == "RESEARCH_REQUIRED"
                    else "RESEARCHED"
                )
            research_queue.append(
                {
                    "research_id": f"RQ-{scenario['scenario_id']}-{gap_index:02d}",
                    "scenario_id": scenario["scenario_id"],
                    "product": scenario["technologies"][0],
                    "source": (
                        scenario["telemetry_sources"][0]
                        if scenario["telemetry_sources"]
                        else "UNESTABLISHED"
                    ),
                    "missing_claim": gap,
                    "required_evidence_type": evidence_type,
                    "blocking_gate": blocking_gate,
                    "priority": (
                        "HIGH"
                        if scenario["maturity"] == "RESEARCH_REQUIRED"
                        else "LOW"
                        if scenario["maturity"] == "GOLDEN"
                        else "MEDIUM"
                    ),
                    "status": (
                        "RESEARCH_REQUIRED"
                        if scenario["maturity"] == "RESEARCH_REQUIRED"
                        else "OPEN"
                    ),
                }
            )
    return {
        "schema_version": "1.0.0",
        "catalog_version": "8.0.0",
        "vendor_id": "cisco",
        "independence_notice": (
            "NetSpout is an independent project and is not Cisco certified, "
            "Cisco approved, Splunk certified, or endorsed by either vendor."
        ),
        "domain_targets": {domain: 20 for domain in DOMAINS},
        "scenarios": scenarios,
        "research_queue": research_queue,
        "shared_assets": [
            {
                "asset_id": "cisco-ios-xr-interface-contract-set",
                "asset_type": "PRODUCT_SOURCE_CONTRACT_SET",
                "scenario_ids": sorted(IOS_XR_REUSE),
                "evidence_ids": [
                    "COV-CISCO-IOSXR-SYSLOG-FORMAT",
                    "COV-CISCO-IOSXR-LINK-UPDOWN",
                    "COV-CISCO-IOSXR-GNMI",
                    "COV-CISCO-IOSXR-SNMP",
                ],
            },
            {
                "asset_id": "cisco-ios-xr-interface-investigation",
                "asset_type": "INVESTIGATION_RECIPE",
                "scenario_ids": ["C100-SP-001", "C100-SP-002"],
                "evidence_ids": ["COV-CISCO-IOSXR-SYSLOG-FORMAT"],
            },
        ],
    }


if __name__ == "__main__":
    OUTPUT.write_text(json.dumps(build_catalog(), indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")
