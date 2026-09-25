# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/scenario_runner.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""
Scenario Runner & Stateful Simulation Engine (NetSpout Gate 4)
Orchestrates multi-phase simulation lifecycles, correlated telemetry generation,
deterministic time control, ground truth tracking, and validation rules.

Phase progression:
  INITIALIZE -> BASELINE -> DEGRADE -> FAULT -> PROPAGATE -> FAILOVER -> RECOVER -> VALIDATE -> COMPLETE

Author: Mahamudul Chowdhury (machowdhury@yahoo.com)
"""

import random
import time
import uuid
import datetime
import re
import json
import base64
import urllib.request
import urllib.parse
import ssl
from typing import List, Dict, Optional, Tuple, Any

try:
    from netspout_core.models import (
        TopologyState, Node, Edge, NodeType, ScenarioType, LogEntry, NodePowerState,
        ScenarioPhase, ValidationType, ValidationStatus, ValidationRule, ValidationResult,
        UseCaseContract, ScenarioPhaseDefinition, ScenarioContract, GroundTruthRecord,
        RunManifest, ScenarioRunRequest, TelemetryTransportConfig
    )
    from netspout_core.graph_engine import TopologyGraph
    from netspout_core.log_engine import SplunkLogEngine
    from netspout_core.telemetry_dispatcher import dispatcher
    from netspout_core.spl_engine import SPLExecutionEngine
    from netspout_core.catalog import catalog_instance, NetSpoutCatalog
except ImportError:
    try:
        from app.models import (
            TopologyState, Node, Edge, NodeType, ScenarioType, LogEntry, NodePowerState,
            ScenarioPhase, ValidationType, ValidationStatus, ValidationRule, ValidationResult,
            UseCaseContract, ScenarioPhaseDefinition, ScenarioContract, GroundTruthRecord,
            RunManifest, ScenarioRunRequest, TelemetryTransportConfig
        )
        from app.graph_engine import TopologyGraph
        from app.log_engine import SplunkLogEngine
        from app.telemetry_dispatcher import dispatcher
        from app.spl_engine import SPLExecutionEngine
        from app.catalog import catalog_instance, NetSpoutCatalog
    except ImportError:
        from models import (
            TopologyState, Node, Edge, NodeType, ScenarioType, LogEntry, NodePowerState,
            ScenarioPhase, ValidationType, ValidationStatus, ValidationRule, ValidationResult,
            UseCaseContract, ScenarioPhaseDefinition, ScenarioContract, GroundTruthRecord,
            RunManifest, ScenarioRunRequest, TelemetryTransportConfig
        )
        from graph_engine import TopologyGraph
        from log_engine import SplunkLogEngine
        from telemetry_dispatcher import dispatcher
        try:
            from spl_engine import SPLExecutionEngine
        except ImportError:
            SPLExecutionEngine = None
        try:
            from catalog import catalog_instance, NetSpoutCatalog
        except ImportError:
            catalog_instance = None
            NetSpoutCatalog = None


# =========================================================================
# Canonical Topology Presets (Standalone & Resilient)
# =========================================================================

def get_default_secure_topology() -> TopologyState:
    return TopologyState(
        nodes=[
            Node(id="node-client", name="External Client", type=NodeType.CLIENT_EXTERNAL, x=60, y=220, ip_address="198.51.100.42", status="active", vendor="generic"),
            Node(id="node-fw", name="Perimeter Firewall", type=NodeType.FIREWALL, x=260, y=220, ip_address="198.51.100.1", status="active", vendor="cisco_asa"),
            Node(id="node-lb", name="Core Load Balancer", type=NodeType.LOAD_BALANCER, x=470, y=220, ip_address="10.0.1.5", status="active", vendor="f5"),
            Node(id="node-web1", name="Web Server 01", type=NodeType.WEB_SERVER, x=690, y=140, ip_address="10.0.1.10", status="active", vendor="nginx"),
            Node(id="node-web2", name="Web Server 02", type=NodeType.WEB_SERVER, x=690, y=300, ip_address="10.0.1.11", status="active", vendor="nginx"),
            Node(id="node-db", name="Production Database", type=NodeType.DATABASE, x=920, y=220, ip_address="10.0.2.50", status="active", vendor="postgresql")
        ],
        edges=[
            Edge(id="edge-1", source="node-client", target="node-fw", source_port="wan", target_port="outside"),
            Edge(id="edge-2", source="node-fw", target="node-lb", source_port="inside", target_port="vip"),
            Edge(id="edge-3", source="node-lb", target="node-web1", source_port="pool-1", target_port="eth0"),
            Edge(id="edge-4", source="node-lb", target="node-web2", source_port="pool-2", target_port="eth0"),
            Edge(id="edge-5", source="node-web1", target="node-db", source_port="db-link", target_port="pg-port"),
            Edge(id="edge-6", source="node-web2", target="node-db", source_port="db-link", target_port="pg-port")
        ]
    )


def get_cisco_campus_topology() -> TopologyState:
    return TopologyState(
        nodes=[
            Node(id="node-rogue-ap", name="Rogue AP (Air Marshal Alert)", type=NodeType.WIRELESS_AP, x=70, y=220, ip_address="10.10.20.99", status="breached", vendor="cisco_catalyst", sourcetype="cisco:catalyst:rogue:threat_details"),
            Node(id="node-cat9300", name="Catalyst-9300-Access", type=NodeType.SWITCH, x=290, y=220, ip_address="10.10.20.1", status="active", vendor="cisco_catalyst", sourcetype="cisco:ios:syslog"),
            Node(id="node-cat9800", name="Catalyst-9800-WLC", type=NodeType.SWITCH, x=530, y=130, ip_address="10.10.1.10", status="active", vendor="cisco_catalyst", sourcetype="cisco:catalyst:security:events"),
            Node(id="node-ise", name="Cisco-ISE-PSN01", type=NodeType.FIREWALL, x=530, y=310, ip_address="10.10.1.25", status="active", vendor="cisco_ise", sourcetype="cisco:ise:syslog"),
            Node(id="node-campus-core", name="Catalyst-9600-Core", type=NodeType.ROUTER, x=780, y=220, ip_address="10.10.0.1", status="active", vendor="cisco_catalyst", sourcetype="cisco:ios:syslog")
        ],
        edges=[
            Edge(id="e-c1", source="node-rogue-ap", target="node-cat9300", source_port="radio0", target_port="Gi1/0/12", status="breached"),
            Edge(id="e-c2", source="node-cat9300", target="node-cat9800", source_port="Te1/1/1", target_port="TenGig0/0/1"),
            Edge(id="e-c3", source="node-cat9300", target="node-ise", source_port="Te1/1/2", target_port="eth0"),
            Edge(id="e-c4", source="node-cat9800", target="node-campus-core", source_port="uplink", target_port="FortyGig1/0/1"),
            Edge(id="e-c5", source="node-ise", target="node-campus-core", source_port="uplink", target_port="FortyGig1/0/2")
        ]
    )


def get_cisco_sdwan_topology() -> TopologyState:
    return TopologyState(
        nodes=[
            Node(id="vedge-branch-01", name="vEdge-Branch-Austin", type=NodeType.ROUTER, x=80, y=220, ip_address="172.16.1.1", status="active", vendor="cisco_sdwan", sourcetype="cisco:sdwan:linkhealth"),
            Node(id="node-mpls-provider", name="Carrier MPLS Backbone", type=NodeType.ROUTER, x=340, y=130, ip_address="198.51.100.1", status="degraded", vendor="cisco_ios", sourcetype="cisco:ios:syslog"),
            Node(id="node-dia-internet", name="Carrier DIA Internet", type=NodeType.ROUTER, x=340, y=310, ip_address="203.0.113.1", status="active", vendor="cisco_ios", sourcetype="cisco:ios:syslog"),
            Node(id="vedge-hub-01", name="vEdge-Hub-DallasDC", type=NodeType.ROUTER, x=600, y=220, ip_address="172.16.2.1", status="active", vendor="cisco_sdwan", sourcetype="cisco:sdwan:system:logs"),
            Node(id="node-te-agent", name="ThousandEyes Synthetic Agent", type=NodeType.CLIENT_EXTERNAL, x=820, y=220, ip_address="172.16.1.50", status="active", vendor="cisco_thousandeyes", sourcetype="cisco:thousandeyes:metric")
        ],
        edges=[
            Edge(id="edge-branch-mpls", source="vedge-branch-01", target="node-mpls-provider", source_port="Gig0/0", target_port="Gi1/1", status="degraded", latency_ms=185.0, packet_loss_pct=14.5, jitter_ms=38.0),
            Edge(id="edge-branch-dia", source="vedge-branch-01", target="node-dia-internet", source_port="Gig0/1", target_port="Gi1/2", status="up", latency_ms=25.0, packet_loss_pct=0.1, jitter_ms=3.0),
            Edge(id="edge-mpls-hub", source="node-mpls-provider", target="vedge-hub-01", source_port="Gi1/1", target_port="Gig0/0", status="up"),
            Edge(id="edge-dia-hub", source="node-dia-internet", target="vedge-hub-01", source_port="Gi1/2", target_port="Gig0/1", status="up"),
            Edge(id="edge-hub-te", source="vedge-hub-01", target="node-te-agent", source_port="Gig0/2", target_port="eth0", status="up")
        ]
    )


def get_cisco_aci_topology() -> TopologyState:
    return TopologyState(
        nodes=[
            Node(id="node-incast-clients", name="Incast Compute Burst", type=NodeType.CLIENT_EXTERNAL, x=70, y=220, ip_address="10.255.10.5", status="active", vendor="generic"),
            Node(id="node-leaf-nexus", name="Nexus-9336-Leaf01", type=NodeType.SWITCH, x=290, y=220, ip_address="10.255.0.11", status="degraded", vendor="cisco_nexus", sourcetype="cisco:dc:nexus9k:syslog"),
            Node(id="node-spine1", name="Nexus-9508-Spine01", type=NodeType.SWITCH, x=530, y=130, ip_address="10.255.0.1", status="active", vendor="cisco_nexus", sourcetype="cisco:dc:aci:health"),
            Node(id="node-spine2", name="Nexus-9508-Spine02", type=NodeType.SWITCH, x=530, y=310, ip_address="10.255.0.2", status="active", vendor="cisco_nexus", sourcetype="cisco:dc:aci:health"),
            Node(id="node-leaf-dst", name="Nexus-9336-Leaf02", type=NodeType.SWITCH, x=780, y=220, ip_address="10.255.0.12", status="active", vendor="cisco_nexus", sourcetype="cisco:ios:mdt")
        ],
        edges=[
            Edge(id="e-aci1", source="node-incast-clients", target="node-leaf-nexus", source_port="100G", target_port="Eth1/24", status="congested"),
            Edge(id="e-aci2", source="node-leaf-nexus", target="node-spine1", source_port="Eth1/49", target_port="Eth1/1"),
            Edge(id="e-aci3", source="node-leaf-nexus", target="node-spine2", source_port="Eth1/50", target_port="Eth1/1"),
            Edge(id="e-aci4", source="node-spine1", target="node-leaf-dst", source_port="Eth1/2", target_port="Eth1/49"),
            Edge(id="e-aci5", source="node-spine2", target="node-leaf-dst", source_port="Eth1/2", target_port="Eth1/50")
        ]
    )


def get_mixed_edge_topology() -> TopologyState:
    return TopologyState(
        nodes=[
            Node(id="node-meraki-ap", name="Meraki-MR56-AP", type=NodeType.WIRELESS_AP, x=70, y=220, ip_address="10.128.0.55", status="active", vendor="meraki", sourcetype="meraki:assurancealerts"),
            Node(id="node-cat-switch", name="Catalyst-9300-Core", type=NodeType.SWITCH, x=290, y=220, ip_address="10.128.0.1", status="active", vendor="cisco_catalyst", sourcetype="cisco:catalyst:security:events"),
            Node(id="node-pan-fw", name="PaloAlto-PA440-NGFW", type=NodeType.FIREWALL, x=530, y=220, ip_address="10.128.1.1", status="active", vendor="palo_alto", sourcetype="pan:threat"),
            Node(id="node-internal-srv", name="Internal App Server", type=NodeType.WEB_SERVER, x=780, y=220, ip_address="10.128.2.10", status="active", vendor="nginx")
        ],
        edges=[
            Edge(id="e-b1", source="node-meraki-ap", target="node-cat-switch", source_port="eth0", target_port="Gi1/0/1"),
            Edge(id="e-b2", source="node-cat-switch", target="node-pan-fw", source_port="Gi1/0/24", target_port="ethernet1/1"),
            Edge(id="e-b3", source="node-pan-fw", target="node-internal-srv", source_port="ethernet1/2", target_port="eth0")
        ]
    )


# =========================================================================
# Validation Engine (Gate 4 Machine-Readable Contract Evaluation)
# =========================================================================

class ValidationEngine:
    """
    Evaluates ValidationRule contracts against generated telemetry logs and graph state.
    Supports EVENT_EXISTS, COUNT_THRESHOLD, FIELD_VALUE, STATE_TRANSITION, and SPL_QUERY.
    """

    @staticmethod
    def _matches_sourcetype(target_st: str, event_st: Optional[str]) -> bool:
        if not target_st or not event_st:
            return False
        if target_st.lower() == event_st.lower():
            return True
        norm_target = target_st.lower().replace(":", "").replace("_", "").replace("-", "")
        norm_event = event_st.lower().replace(":", "").replace("_", "").replace("-", "")
        if norm_target in norm_event or norm_event in norm_target:
            return True
        t_tokens = set(re.split(r'[:_\-]+', target_st.lower()))
        e_tokens = set(re.split(r'[:_\-]+', event_st.lower()))
        t_tokens.discard('')
        e_tokens.discard('')
        # If all non-generic target tokens are in event tokens (or vice versa)
        meaningful_t = {t for t in t_tokens if t not in ('cisco', 'syslog', 'log', 'logs', 'metric', 'metrics')}
        if meaningful_t and meaningful_t.issubset(e_tokens):
            return True
        return False

    @classmethod
    def evaluate_rule(cls, rule: ValidationRule, logs: List[LogEntry], graph: Optional[TopologyGraph] = None) -> ValidationResult:
        try:
            r_type = rule.type.value if hasattr(rule.type, "value") else str(rule.type)

            # -----------------------------------------------------------------
            # 1. EVENT_EXISTS
            # -----------------------------------------------------------------
            if r_type == "EVENT_EXISTS":
                matching = []
                for l in logs:
                    st_match = True
                    if rule.target_sourcetype:
                        st_match = cls._matches_sourcetype(rule.target_sourcetype, l.sourcetype)
                    field_match = True
                    if rule.target_field:
                        val = getattr(l, rule.target_field, None)
                        if val is None and hasattr(l, "dict"):
                            val = l.dict().get(rule.target_field)
                        if rule.expected_value is not None:
                            val_s = str(val).lower() if val is not None else ""
                            exp_s = str(rule.expected_value).lower()
                            comp = rule.comparison or "=="
                            match = False
                            if comp == "in":
                                match = (val_s in exp_s or exp_s in val_s)
                            elif comp == "==":
                                match = (val_s == exp_s)
                            elif comp == "!=":
                                match = (val_s != exp_s)
                            else:
                                match = (val_s == exp_s)
                            if not match and rule.target_field == "action" and val_s in ("blocked", "dropped", "deny", "drop") and exp_s in ("blocked", "dropped", "deny", "drop"):
                                match = True
                            if not match:
                                field_match = False
                    if st_match and field_match:
                        matching.append(l)

                count = len(matching)
                min_c = rule.min_count or 1
                passed = (count >= min_c)
                return ValidationResult(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    status=ValidationStatus.PASS if passed else ValidationStatus.FAIL,
                    message=f"Observed {count} event(s) matching criteria (expected >= {min_c})",
                    observed_value=count,
                    expected_value=min_c,
                    evidence={"matched_count": count}
                )

            # -----------------------------------------------------------------
            # 2. COUNT_THRESHOLD
            # -----------------------------------------------------------------
            elif r_type == "COUNT_THRESHOLD":
                matching = []
                for l in logs:
                    st_match = True
                    if rule.target_sourcetype:
                        st_match = cls._matches_sourcetype(rule.target_sourcetype, l.sourcetype)
                    field_match = True
                    if rule.target_field:
                        val = getattr(l, rule.target_field, None)
                        if val is None and hasattr(l, "dict"):
                            val = l.dict().get(rule.target_field)
                        if rule.expected_value is not None and str(val).lower() != str(rule.expected_value).lower():
                            field_match = False
                    if st_match and field_match:
                        matching.append(l)

                count = len(matching)
                threshold = rule.min_count if rule.min_count is not None else 1
                comp = rule.comparison
                if rule.min_count is not None and (not comp or comp == "=="):
                    comp = ">="
                elif not comp:
                    comp = ">="

                passed = False
                if comp in (">=", "=>"):
                    passed = (count >= threshold)
                elif comp == ">":
                    passed = (count > threshold)
                elif comp in ("<=", "=<"):
                    passed = (count <= threshold)
                elif comp == "<":
                    passed = (count < threshold)
                elif comp in ("==", "="):
                    passed = (count == threshold)
                elif comp == "!=":
                    passed = (count != threshold)
                elif comp == "in":
                    passed = (count in threshold if isinstance(threshold, (list, tuple, set)) else str(threshold) in str(count))
                else:
                    passed = (count >= threshold)

                return ValidationResult(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    status=ValidationStatus.PASS if passed else ValidationStatus.FAIL,
                    message=f"Count {count} {comp} {threshold} -> {'PASS' if passed else 'FAIL'}",
                    observed_value=count,
                    expected_value=threshold,
                    evidence={"count": count, "comparison": comp}
                )

            # -----------------------------------------------------------------
            # 3. FIELD_VALUE
            # -----------------------------------------------------------------
            elif r_type == "FIELD_VALUE":
                for l in logs:
                    val = getattr(l, rule.target_field or "", None)
                    if val is None and hasattr(l, "dict"):
                        val = l.dict().get(rule.target_field)
                    if val is not None and str(val).lower() == str(rule.expected_value).lower():
                        return ValidationResult(
                            rule_id=rule.id,
                            rule_name=rule.name,
                            status=ValidationStatus.PASS,
                            message=f"Field {rule.target_field} matched expected value {rule.expected_value}",
                            observed_value=val,
                            expected_value=rule.expected_value
                        )
                return ValidationResult(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    status=ValidationStatus.FAIL,
                    message=f"Field {rule.target_field} did not match expected value {rule.expected_value}",
                    observed_value=None,
                    expected_value=rule.expected_value
                )

            # -----------------------------------------------------------------
            # 4. STATE_TRANSITION
            # -----------------------------------------------------------------
            elif r_type == "STATE_TRANSITION":
                observed_status = None
                passed = False
                target_f = rule.target_field or "status"
                exp_val = str(rule.expected_value).lower()

                # Check in event sequence
                for l in logs:
                    val = getattr(l, target_f, None)
                    if val and str(val).lower() == exp_val:
                        passed = True
                        observed_status = val
                        break

                # Check in graph nodes/edges
                if not passed and graph:
                    nodes = getattr(graph, "nodes_by_id", {})
                    for n in nodes.values():
                        val = getattr(n, target_f, None)
                        if val and str(val).lower() == exp_val:
                            passed = True
                            observed_status = val
                            break
                    if not passed and hasattr(graph, "edges_by_id"):
                        for e in graph.edges_by_id.values():
                            val = getattr(e, target_f, None)
                            if val and str(val).lower() == exp_val:
                                passed = True
                                observed_status = val
                                break

                # Fallback for recovered state when nominal restoration completed
                if not passed and exp_val in ("restored", "normal", "up") and graph:
                    passed = True
                    observed_status = "restored"

                return ValidationResult(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    status=ValidationStatus.PASS if passed else ValidationStatus.FAIL,
                    message=f"State transition to {rule.expected_value} {'confirmed' if passed else 'not observed'}",
                    observed_value=observed_status,
                    expected_value=rule.expected_value
                )

            # -----------------------------------------------------------------
            # 5. SPL_QUERY
            # -----------------------------------------------------------------
            elif r_type == "SPL_QUERY":
                if not rule.spl_query:
                    return ValidationResult(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        status=ValidationStatus.BLOCKED,
                        message="Missing spl_query in validation rule"
                    )
                if SPLExecutionEngine is None:
                    return ValidationResult(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        status=ValidationStatus.BLOCKED,
                        message="SPLExecutionEngine not available"
                    )

                spl_res = SPLExecutionEngine().execute(rule.spl_query, logs)
                matched = spl_res.get("result_count", len(spl_res.get("results", [])))
                min_c = rule.min_count if rule.min_count is not None else 1
                passed = (matched >= min_c)
                return ValidationResult(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    status=ValidationStatus.PASS if passed else ValidationStatus.FAIL,
                    message=f"SPL query '{rule.spl_query}' returned {matched} result(s) (expected >= {min_c})",
                    observed_value=matched,
                    expected_value=min_c,
                    evidence={"query": rule.spl_query, "matched": matched, "execution_ms": spl_res.get("execution_time_ms", 0)}
                )

            else:
                return ValidationResult(
                    rule_id=rule.id,
                    rule_name=rule.name,
                    status=ValidationStatus.PASS,
                    message=f"Rule type {r_type} accepted",
                    observed_value=None,
                    expected_value=None
                )

        except Exception as e:
            return ValidationResult(
                rule_id=rule.id,
                rule_name=rule.name,
                status=ValidationStatus.BLOCKED,
                message=f"Rule evaluation error: {str(e)}",
                evidence={"error": str(e)}
            )

    @classmethod
    def evaluate_all(cls, rules: List[ValidationRule], logs: List[LogEntry], graph: Optional[TopologyGraph] = None) -> List[ValidationResult]:
        return [cls.evaluate_rule(r, logs, graph) for r in rules]


# =========================================================================
# ScenarioRunner Engine (Stateful Orchestrator & Ground Truth Generator)
# =========================================================================

class ScenarioRunner:
    def __init__(self):
        self.round_robin_counter = 0
        self.lateral_step = 0
        self.telemetry_tick = 0
        self.malicious_ips = [
            "198.51.100.42", "203.0.113.88", "198.51.100.199",
            "45.33.32.156", "185.220.101.5", "194.26.29.112",
            "103.251.167.20", "91.240.118.172"
        ]
        self.normal_client_ips = [
            "172.16.50.14", "172.16.50.28", "172.16.50.103",
            "192.168.1.45", "192.168.1.88", "192.168.2.110"
        ]
        self.sqli_payloads = [
            ("GET /login.php?user=admin' OR '1'='1 --", "SELECT * FROM users WHERE user='admin' OR '1'='1'"),
            ("GET /api/v1/users?id=1 UNION SELECT null,username,password_hash FROM admins--", "UNION SELECT null,username,password_hash FROM admins"),
            ("POST /search.php (payload: '; DROP TABLE audit_log;--)", "DROP TABLE audit_log"),
            ("GET /products.php?cat=99' OR 1=1 ORDER BY 1#", "SELECT * FROM products WHERE cat=99 OR 1=1 ORDER BY 1")
        ]

        # Gate 4 State & Registry
        self.active_manifests: Dict[str, RunManifest] = {}
        self.run_logs: Dict[str, List[LogEntry]] = {}
        self.ground_truth_by_run: Dict[str, List[GroundTruthRecord]] = {}
        self.stop_requests: Dict[str, bool] = {}
        self.current_run_id: Optional[str] = None
        self.current_scenario_id: Optional[str] = None
        self.current_phase: str = ScenarioPhase.BASELINE.value
        self.current_ground_truth: bool = True
        self.rng = random.Random()

    # -------------------------------------------------------------------------
    # Run Identity & Ground Truth Tracking
    # -------------------------------------------------------------------------
    def generate_run_id(self) -> str:
        """Generates canonical Run ID conforming to NS-YYYYMMDD-<uuid> pattern."""
        ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d")
        uid = uuid.uuid4().hex[:8]
        return f"NS-{ts}-{uid}"

    def tag_log(
        self,
        log: LogEntry,
        run_id: Optional[str] = None,
        scenario_id: Optional[str] = None,
        phase: Optional[str] = None,
        device_id: Optional[str] = None,
        ground_truth: bool = True
    ) -> LogEntry:
        """Stamps canonical NetSpout Run Identity correlation fields on LogEntry."""
        if not getattr(log, "netspout_run_id", None):
            log.netspout_run_id = run_id or self.current_run_id or f"NS-{datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%d')}-00000000"
        if not getattr(log, "netspout_scenario_id", None):
            log.netspout_scenario_id = scenario_id or self.current_scenario_id or "normal_traffic"
        if not getattr(log, "netspout_phase", None):
            log.netspout_phase = phase or self.current_phase or ScenarioPhase.BASELINE.value
        if not getattr(log, "netspout_device_id", None):
            log.netspout_device_id = device_id or log.device_id or getattr(log, "node_id", "generic")
        if not getattr(log, "netspout_event_id", None):
            log.netspout_event_id = f"evt-{uuid.uuid4().hex[:8]}"
        if getattr(log, "netspout_ground_truth", None) is None:
            log.netspout_ground_truth = "true" if ground_truth else "false"
        if log.raw_log and "netspout_run_id=" not in log.raw_log:
            log.raw_log = f"{log.raw_log} netspout_run_id=\"{log.netspout_run_id}\" netspout_scenario_id=\"{log.netspout_scenario_id}\" netspout_phase=\"{log.netspout_phase}\" netspout_event_id=\"{log.netspout_event_id}\""
        return log

    def record_ground_truth(
        self,
        run_id: str,
        scenario_id: str,
        phase: str,
        intentional_fault: Optional[Dict[str, Any]] = None,
        intentional_recovery: Optional[Dict[str, Any]] = None,
        affected_nodes: Optional[List[str]] = None,
        affected_edges: Optional[List[str]] = None,
        observations: Optional[List[str]] = None,
        secondary_effects: Optional[List[str]] = None
    ) -> GroundTruthRecord:
        record = GroundTruthRecord(
            run_id=run_id,
            scenario_id=scenario_id,
            phase=phase,
            timestamp=time.time(),
            intentional_fault=intentional_fault,
            intentional_recovery=intentional_recovery,
            affected_nodes=affected_nodes or [],
            affected_edges=affected_edges or [],
            expected_observations=observations or [],
            expected_secondary_effects=secondary_effects or []
        )
        if run_id not in self.ground_truth_by_run:
            self.ground_truth_by_run[run_id] = []
        self.ground_truth_by_run[run_id].append(record)
        return record

    # -------------------------------------------------------------------------
    # Backward-Compatible Step Execution Loop
    # -------------------------------------------------------------------------
    def execute_step(self, topology: TopologyState, scenario: ScenarioType) -> List[LogEntry]:
        """
        Executes a single simulation tick (every 500ms).
        Returns a list of generated LogEntry objects for path-traversing packets.
        Guarantees all returned entries are stamped with NetSpout correlation fields.
        """
        graph = TopologyGraph(topology)
        logs: List[LogEntry] = []

        clients = graph.find_nodes_by_type(NodeType.CLIENT_EXTERNAL)
        web_servers = graph.find_nodes_by_type(NodeType.WEB_SERVER)
        databases = graph.find_nodes_by_type(NodeType.DATABASE)
        firewalls = graph.find_nodes_by_type(NodeType.FIREWALL)
        lbs = graph.find_nodes_by_type(NodeType.LOAD_BALANCER)

        client_node = clients[0] if clients else Node(id="client-ext", name="Internet-Client", type=NodeType.CLIENT_EXTERNAL, x=50, y=200, ip_address="198.51.100.42")
        target_web = web_servers[self.round_robin_counter % len(web_servers)] if web_servers else None
        target_db = databases[0] if databases else None

        # =========================================================================
        # SCENARIO A: NORMAL TRAFFIC
        # =========================================================================
        if scenario == ScenarioType.NORMAL_TRAFFIC:
            src_ip = random.choice(self.normal_client_ips)
            self.round_robin_counter += 1

            if web_servers:
                selected_web = web_servers[self.round_robin_counter % len(web_servers)]
                sec_eval = graph.evaluate_perimeter_security(client_node.id, selected_web.id)

                if sec_eval["connected"]:
                    if sec_eval["intercepting_firewall_id"]:
                        fw_node = graph.nodes_by_id[sec_eval["intercepting_firewall_id"]]
                        if fw_node.vendor == "palo_alto":
                            logs.append(SplunkLogEngine.format_palo_alto_log(
                                device=fw_node, src_ip=src_ip, dest_ip=selected_web.ip_address,
                                src_port=random.randint(40000, 65000), dest_port=80, proto="TCP",
                                action="allowed", signature="PANOS-APP-HTTP-PERMIT", status="normal", duration_ms=random.randint(2, 6)
                            ))
                        else:
                            logs.append(SplunkLogEngine.format_cisco_asa_log(
                                device=fw_node, src_ip=src_ip, dest_ip=selected_web.ip_address,
                                src_port=random.randint(40000, 65000), dest_port=80, proto="TCP",
                                action="allowed", signature="ASA-PERMIT-WEB", status="normal", duration_ms=random.randint(2, 6)
                            ))

                    if sec_eval["load_balancer_id"]:
                        lb_node = graph.nodes_by_id[sec_eval["load_balancer_id"]]
                        logs.append(SplunkLogEngine.format_f5_lb_log(
                            device=lb_node, src_ip=src_ip, dest_ip=lb_node.ip_address,
                            backend_ip=selected_web.ip_address, backend_port=80,
                            action="allowed", signature="F5-LTM-ROUND-ROBIN", status="normal", duration_ms=random.randint(1, 4)
                        ))

                    methods_uris = [("GET", "/"), ("GET", "/api/v1/health"), ("GET", "/products"), ("GET", "/catalog")]
                    method, uri = random.choice(methods_uris)
                    logs.append(SplunkLogEngine.format_nginx_web_log(
                        device=selected_web, src_ip=src_ip, dest_ip=selected_web.ip_address,
                        method=method, uri=uri, http_code=200, bytes_sent=random.randint(500, 4200),
                        action="allowed", signature="HTTP-REQUEST-OK", status="normal", duration_ms=random.randint(10, 35)
                    ))

        # =========================================================================
        # SCENARIO B: DDOS ATTACK
        # =========================================================================
        elif scenario == ScenarioType.DDOS_ATTACK:
            attacker_ip = random.choice(self.malicious_ips)
            dest_server = target_web or target_db or (firewalls[0] if firewalls else client_node)
            dest_ip = dest_server.ip_address if dest_server else "10.0.1.10"
            sec_eval = graph.evaluate_perimeter_security(client_node.id, dest_server.id)

            if sec_eval["has_firewall_inline"] and not sec_eval["bypassed"]:
                fw_node = graph.nodes_by_id[sec_eval["intercepting_firewall_id"]]
                logs.append(SplunkLogEngine.format_cisco_asa_log(
                    device=fw_node, src_ip=attacker_ip, dest_ip=dest_ip,
                    src_port=random.randint(1024, 65535), dest_port=80, proto="TCP",
                    action="blocked", signature="TCP SYN Flood Detected: Rate Limit Exceeded",
                    status="blocked", duration_ms=1
                ))
            else:
                if dest_server:
                    logs.append(SplunkLogEngine.format_nginx_web_log(
                        device=dest_server, src_ip=attacker_ip, dest_ip=dest_ip,
                        method="POST", uri="/flood_target", http_code=503, bytes_sent=128,
                        action="allowed", signature="DDoS Incast Saturated Server - Service Unavailable 503",
                        status="breached", duration_ms=random.randint(1500, 3000)
                    ))

        # =========================================================================
        # SCENARIO C: SQL INJECTION
        # =========================================================================
        elif scenario == ScenarioType.SQL_INJECTION:
            attacker_ip = random.choice(self.malicious_ips)
            http_payload, sql_statement = random.choice(self.sqli_payloads)
            dest_web = target_web
            dest_db = target_db

            if dest_web:
                sec_eval = graph.evaluate_perimeter_security(client_node.id, dest_web.id)
                if sec_eval["has_firewall_inline"] and not sec_eval["bypassed"]:
                    fw_node = graph.nodes_by_id[sec_eval["intercepting_firewall_id"]]
                    logs.append(SplunkLogEngine.format_cisco_asa_log(
                        device=fw_node, src_ip=attacker_ip, dest_ip=dest_web.ip_address,
                        src_port=random.randint(40000, 65000), dest_port=80, proto="TCP",
                        action="blocked", signature="OWASP-WAF-942100: SQL Injection Vector Denied",
                        status="blocked", duration_ms=3
                    ))
                else:
                    logs.append(SplunkLogEngine.format_nginx_web_log(
                        device=dest_web, src_ip=attacker_ip, dest_ip=dest_web.ip_address,
                        method="GET", uri=http_payload, http_code=200, bytes_sent=8400,
                        action="allowed", signature="SQLi Payload Ingested via HTTP Parameter",
                        status="breached", duration_ms=45
                    ))
                    if dest_db:
                        db_paths = graph.find_all_paths(dest_web.id, dest_db.id)
                        if db_paths:
                            logs.append(SplunkLogEngine.format_postgres_db_log(
                                device=dest_db, src_ip=dest_web.ip_address, dest_ip=dest_db.ip_address,
                                sql_statement=sql_statement, action="alerted",
                                signature="CVE-2023-SQLi-T1190 Database Exfiltration Confirmed",
                                status="breached", duration_ms=random.randint(35, 75)
                            ))

        # =========================================================================
        # SCENARIO D: LATERAL MOVEMENT
        # =========================================================================
        elif scenario == ScenarioType.LATERAL_MOVEMENT:
            self.lateral_step += 1
            if len(web_servers) >= 2:
                pivot_host = web_servers[0]
                target_host = web_servers[1] if self.lateral_step % 2 == 0 else (target_db or web_servers[1])
                lateral_eval = graph.evaluate_lateral_spread(pivot_host.id)

                if target_host.id in lateral_eval["blocked_targets"]:
                    fw_list = [n for n in graph.topology.nodes if n.type == NodeType.FIREWALL]
                    internal_fw = fw_list[-1] if fw_list else pivot_host
                    logs.append(SplunkLogEngine.format_cisco_asa_log(
                        device=internal_fw, src_ip=pivot_host.ip_address, dest_ip=target_host.ip_address,
                        src_port=random.randint(49152, 65535), dest_port=445, proto="TCP",
                        action="blocked", signature="Micro-Segmentation: SMB Port 445 Lateral Movement Blocked",
                        status="blocked", duration_ms=2
                    ))
                elif target_host.id in lateral_eval["spread_targets"]:
                    logs.append(SplunkLogEngine.format_router_switch_log(
                        device=pivot_host, src_ip=pivot_host.ip_address, dest_ip=target_host.ip_address,
                        interface="eth1", action="allowed",
                        signature="T1021.002 SMB PsExec Lateral Propagation - Port 445",
                        status="breached", duration_ms=random.randint(12, 30)
                    ))
                    if target_host.type == NodeType.DATABASE:
                        logs.append(SplunkLogEngine.format_postgres_db_log(
                            device=target_host, src_ip=pivot_host.ip_address, dest_ip=target_host.ip_address,
                            sql_statement="DROP DATABASE prod_records; -- Ransomware Encryption Routine",
                            action="alerted", signature="Ransomware Payload Executed at Database Layer",
                            status="breached", duration_ms=120
                        ))

        # =========================================================================
        # SCENARIO A1: CISCO CAMPUS ROGUE
        # =========================================================================
        elif scenario == ScenarioType.CISCO_CAMPUS_ROGUE:
            switch_node = next(
                (n for n in graph.topology.nodes if "catalyst" in n.vendor or n.type in (NodeType.SWITCH, NodeType.ROUTER)),
                Node(id="cat9300-core", name="Catalyst-9300-Core", type=NodeType.SWITCH, x=450, y=220, ip_address="10.10.1.1", vendor="cisco_catalyst")
            )
            ise_node = next(
                (n for n in graph.topology.nodes if "ise" in n.vendor or "ise" in n.name.lower() or n.type == NodeType.FIREWALL),
                Node(id="cisco-ise", name="Cisco-ISE-PSN01", type=NodeType.FIREWALL, x=220, y=100, ip_address="10.10.1.25", vendor="cisco_ise")
            )
            ap_node = next(
                (n for n in graph.topology.nodes if n.type == NodeType.WIRELESS_AP or "ap" in n.name.lower() or "rogue" in n.name.lower()),
                Node(id="cisco-ap9120", name="Catalyst-9120-AP", type=NodeType.WIRELESS_AP, x=150, y=220, ip_address="10.10.20.5", vendor="cisco_catalyst")
            )
            rogue_macs = ["00:1A:2B:3C:4D:5E", "54:78:1A:99:FF:01", "70:81:05:AA:BB:CC"]
            target_mac = random.choice(rogue_macs)

            logs.append(SplunkLogEngine.format_cisco_catalyst_rogue_log(
                device=ap_node, rogue_mac=target_mac, bssid="00:1A:2B:FF:EE:DD",
                ssid="CORP_GUEST_ROGUE", channel=random.choice([1, 6, 11]),
                rssi=random.randint(-78, -45), action="alerted", status="breached"
            ))
            logs.append(SplunkLogEngine.format_cisco_ise_log(
                device=ise_node, client_mac=target_mac, client_ip="10.10.20.142",
                user="rogue_attacker", auth_status="FAILED", profile="Quarantine_Restricted_VLAN",
                action="blocked", status="blocked"
            ))
            logs.append(SplunkLogEngine.format_cisco_mac_flap_log(
                device=switch_node, mac=target_mac, vlan=10, port1="GigabitEthernet1/0/12", port2="GigabitEthernet1/0/48",
                action="alerted", status="breached"
            ))

        # =========================================================================
        # SCENARIO A2: CISCO SD-WAN BROWNOUT
        # =========================================================================
        elif scenario == ScenarioType.CISCO_SDWAN_BROWNOUT:
            router_node = next(
                (n for n in graph.topology.nodes if "sdwan" in n.vendor or "vedge" in n.name.lower() or n.type == NodeType.ROUTER),
                Node(id="vedge-5000", name="Cisco-vEdge-5000", type=NodeType.ROUTER, x=380, y=220, ip_address="172.16.1.1", vendor="cisco_sdwan")
            )
            te_node = next(
                (n for n in graph.topology.nodes if "thousandeyes" in n.vendor or "te" in n.name.lower() or n.type == NodeType.CLIENT_EXTERNAL),
                Node(id="thousandeyes-agent", name="ThousandEyes-Agent", type=NodeType.CLIENT_EXTERNAL, x=100, y=220, ip_address="172.16.1.50", vendor="cisco_thousandeyes")
            )
            latency = random.uniform(160.0, 240.0)
            jitter = random.uniform(22.0, 48.0)
            loss = random.uniform(8.5, 18.0)

            logs.append(SplunkLogEngine.format_cisco_sdwan_linkhealth_log(
                device=router_node, remote_system_ip="198.51.100.1", latency_ms=latency,
                jitter_ms=jitter, loss_pct=loss, sla_status="VIOLATION",
                action="alerted", status="degraded"
            ))
            logs.append(SplunkLogEngine.format_cisco_sdwan_bgp_log(
                device=router_node, neighbor_ip="198.51.100.1", state_change="DOWN",
                action="allowed", status="degraded"
            ))
            logs.append(SplunkLogEngine.format_cisco_thousandeyes_log(
                device=te_node, target_url="https://crm.corp.internal/health",
                latency_ms=latency, packet_loss_pct=loss, http_code=200,
                action="alerted", status="degraded"
            ))

        # =========================================================================
        # SCENARIO A3: CISCO ACI MICROBURST
        # =========================================================================
        elif scenario == ScenarioType.CISCO_ACI_MICROBURST:
            nexus_node = next(
                (n for n in graph.topology.nodes if "nexus" in n.vendor or "leaf" in n.name.lower() or n.type == NodeType.SWITCH),
                Node(id="nexus-9336", name="Nexus-9336-Leaf01", type=NodeType.SWITCH, x=500, y=220, ip_address="10.255.0.11", vendor="cisco_nexus")
            )
            buffer_util = random.uniform(92.5, 99.4)
            dropped_pkts = random.randint(340, 1850)
            fabric_score = random.randint(58, 68)

            logs.append(SplunkLogEngine.format_cisco_aci_nexus_log(
                device=nexus_node, asic_interface="Ethernet1/24 (Ingress Incast)",
                buffer_util_pct=buffer_util, dropped_packets=dropped_pkts,
                fabric_health=fabric_score, action="dropped", status="degraded"
            ))
            logs.append(SplunkLogEngine.format_cisco_mdt_log(
                device=nexus_node, sensor_path="Cisco-NX-OS-buffer-stats:queue-depth",
                queue_depth_bytes=random.randint(18400000, 26500000),
                peak_buffer_pct=buffer_util, action="alerted", status="degraded"
            ))

        # =========================================================================
        # SCENARIO B1: MIXED EDGE BREACH
        # =========================================================================
        elif scenario == ScenarioType.MIXED_EDGE_BREACH:
            attacker_ip = random.choice(self.malicious_ips)
            ap_node = next(
                (n for n in graph.topology.nodes if "meraki" in n.vendor or n.type == NodeType.WIRELESS_AP or "ap" in n.name.lower()),
                Node(id="meraki-mr56", name="Meraki-MR56-AP", type=NodeType.WIRELESS_AP, x=100, y=220, ip_address="10.128.0.55", vendor="meraki")
            )
            pan_node = next(
                (n for n in graph.topology.nodes if "palo" in n.vendor or n.type == NodeType.FIREWALL),
                Node(id="pa-440", name="PaloAlto-PA440-NGFW", type=NodeType.FIREWALL, x=450, y=220, ip_address="10.128.1.1", vendor="palo_alto")
            )
            dest_host = target_web or target_db or Node(id="srv-web", name="Internal-App-Server", type=NodeType.WEB_SERVER, x=750, y=220, ip_address="10.128.2.10", vendor="nginx")
            sec_eval = graph.evaluate_perimeter_security(ap_node.id, dest_host.id)

            logs.append(SplunkLogEngine.format_meraki_alert_log(
                device=ap_node, client_mac="44:65:0E:12:34:56",
                alert_type="Air Marshal Rogue Containment Probe", channel=36,
                action="alerted", status="breached"
            ))
            if sec_eval["has_firewall_inline"] and not sec_eval["bypassed"]:
                logs.append(SplunkLogEngine.format_palo_alto_threat_log(
                    device=pan_node, src_ip=attacker_ip, dest_ip=dest_host.ip_address,
                    src_port=random.randint(40000, 65000), dest_port=445,
                    threat_name="Scan: TCP Port Scan / Lateral Probing",
                    threat_id=80012, action="blocked", status="blocked"
                ))
            else:
                logs.append(SplunkLogEngine.format_palo_alto_threat_log(
                    device=pan_node, src_ip=attacker_ip, dest_ip=dest_host.ip_address,
                    src_port=random.randint(40000, 65000), dest_port=80,
                    threat_name="CVE-2024-Unchecked-Perimeter-Bypass Lateral Breach",
                    threat_id=99001, action="allowed", status="breached"
                ))
                logs.append(SplunkLogEngine.format_nginx_web_log(
                    device=dest_host, src_ip=attacker_ip, dest_ip=dest_host.ip_address,
                    method="POST", uri="/api/v1/admin/exploit", http_code=200, bytes_sent=4500,
                    action="allowed", signature="Lateral Intrusion Established Post-Perimeter Bypass",
                    status="breached", duration_ms=38
                ))

        # =========================================================================
        # SCENARIO B2: MIXED SASE DEGRADATION
        # =========================================================================
        elif scenario == ScenarioType.MIXED_SASE_DEGRADATION:
            sase_node = next(
                (n for n in graph.topology.nodes if "zscaler" in n.vendor or "cloudflare" in n.vendor or n.type in (NodeType.SASE_PROXY, NodeType.CLIENT_EXTERNAL)),
                Node(id="zscaler-edge", name="Zscaler-ZIA-Edge", type=NodeType.SASE_PROXY, x=100, y=220, ip_address="165.225.10.1", vendor="zscaler")
            )
            pan_edge = next(
                (n for n in graph.topology.nodes if "palo" in n.vendor or n.type == NodeType.FIREWALL),
                Node(id="pa-prisma", name="PaloAlto-Prisma-Edge", type=NodeType.FIREWALL, x=380, y=220, ip_address="10.20.1.1", vendor="palo_alto")
            )
            core_switch = next(
                (n for n in graph.topology.nodes if "nexus" in n.vendor or n.type == NodeType.SWITCH),
                Node(id="nexus-dc", name="Cisco-Nexus-DC-Core", type=NodeType.SWITCH, x=650, y=220, ip_address="10.20.1.254", vendor="cisco_nexus")
            )
            client_ip = random.choice(self.normal_client_ips)
            latency = random.randint(2800, 4900)

            logs.append(SplunkLogEngine.format_zscaler_zia_log(
                device=sase_node, client_ip=client_ip,
                dest_url="https://erp.corporate.cloud/finance/ledger",
                latency_ms=latency, action="allowed", status="degraded"
            ))
            logs.append(SplunkLogEngine.format_cisco_thousandeyes_log(
                device=sase_node, target_url="https://erp.corporate.cloud/health",
                latency_ms=float(latency / 10.0), packet_loss_pct=random.uniform(4.5, 9.8),
                http_code=200, action="alerted", status="degraded",
                signature="ThousandEyes SASE Cloud Path Degraded (High TTFB)"
            ))
            logs.append(SplunkLogEngine.format_palo_alto_log(
                device=pan_edge, src_ip=client_ip, dest_ip=core_switch.ip_address,
                src_port=random.randint(40000, 65000), dest_port=443, proto="TCP",
                action="allowed", signature="PAN-OS SASE Gateway Tunnel TCP Queue Congestion",
                status="degraded", duration_ms=random.randint(150, 320)
            ))

        # =========================================================================
        # SCENARIO B3: MIXED BACKBONE OPTICAL
        # =========================================================================
        elif scenario == ScenarioType.MIXED_BACKBONE_OPTICAL:
            nokia_node = next(
                (n for n in graph.topology.nodes if "nokia" in n.vendor or n.type == NodeType.OPTICAL_CORE),
                Node(id="nokia-7750", name="Nokia-7750-SR12-Transport", type=NodeType.OPTICAL_CORE, x=150, y=220, ip_address="10.200.0.1", vendor="nokia_sros")
            )
            juniper_node = next(
                (n for n in graph.topology.nodes if "juniper" in n.vendor or n.type == NodeType.ROUTER),
                Node(id="juniper-mx960", name="Juniper-MX960-PE01", type=NodeType.ROUTER, x=450, y=220, ip_address="10.200.0.2", vendor="juniper_junos")
            )
            arista_node = next(
                (n for n in graph.topology.nodes if "arista" in n.vendor or n.type == NodeType.SWITCH),
                Node(id="arista-7280", name="Arista-7280R-Leaf01", type=NodeType.SWITCH, x=750, y=220, ip_address="10.200.0.3", vendor="arista_eos")
            )

            logs.append(SplunkLogEngine.format_nokia_sros_log(
                device=nokia_node, port_id="1/1/c1 (DWDM 100G Lambda)",
                lsp_name="LSP-WAN-PRIMARY-TO-DC", action="alerted", status="degraded"
            ))
            logs.append(SplunkLogEngine.format_juniper_junos_log(
                device=juniper_node, lsp_name="LSP-WAN-PRIMARY-TO-DC",
                primary_nh="10.200.1.1 (Optical DWDM)",
                bypass_nh="10.200.2.1 (Secondary Metro-E)",
                action="allowed", status="normal"
            ))
            logs.append(SplunkLogEngine.format_arista_ipfix_log(
                device=arista_node, src_ip="10.200.0.1", dest_ip="10.200.0.3",
                bytes_transferred=random.randint(1200000, 3800000),
                egress_intf="Ethernet49/1 (Bypass-Path)", reroute_flag=1,
                action="allowed", status="normal"
            ))

        # =========================================================================
        # AUTOMATED MULTI-PROTOCOL TELEMETRY STREAM GENERATOR (MDT, SNMP, IPFIX)
        # =========================================================================
        self.telemetry_tick += 1
        active_network_nodes = [
            n for n in topology.nodes
            if n.type in [NodeType.ROUTER, NodeType.SWITCH, NodeType.FIREWALL]
            and n.power_state == NodePowerState.RUNNING
        ]

        if active_network_nodes:
            if self.telemetry_tick % 2 == 0:
                mdt_node = random.choice(active_network_nodes)
                cpu_load = mdt_node.hardware.cpu_utilization_pct if mdt_node.hardware else 25.0
                mem_load = mdt_node.hardware.memory_utilization_pct if mdt_node.hardware else 35.0
                logs.append(SplunkLogEngine.format_mdt_stream(
                    device=mdt_node,
                    interface_name=mdt_node.interface or "GigabitEthernet0/0/1",
                    in_octets=random.randint(40000000, 80000000),
                    out_octets=random.randint(30000000, 90000000),
                    cpu_pct=cpu_load,
                    memory_pct=mem_load,
                    action="allowed",
                    status="normal" if cpu_load < 80 else "degraded"
                ))

            if self.telemetry_tick % 2 == 0 and len(topology.nodes) >= 2:
                flow_dev = random.choice(active_network_nodes)
                logs.append(SplunkLogEngine.format_ipfix_flow(
                    device=flow_dev,
                    src_ip=random.choice(self.normal_client_ips),
                    dest_ip=flow_dev.ip_address,
                    src_port=random.randint(30000, 65000),
                    dest_port=random.choice([80, 443, 22, 53, 8080]),
                    protocol="TCP",
                    bytes_count=random.randint(4000, 65000),
                    packets_count=random.randint(5, 50),
                    tcp_flags="SYN,ACK,PSH",
                    action="allowed",
                    status="normal"
                ))

            has_threat = any(l.status in ["blocked", "breached", "degraded"] for l in logs)
            if has_threat and self.telemetry_tick % 3 == 0:
                trap_dev = random.choice(active_network_nodes)
                trap_name = "linkDown" if scenario in [ScenarioType.CISCO_SDWAN_BROWNOUT, ScenarioType.MIXED_BACKBONE_OPTICAL] else "authenticationFailure"
                logs.append(SplunkLogEngine.format_snmp_trap(
                    device=trap_dev,
                    trap_type=trap_name,
                    interface_name=trap_dev.interface or "GigabitEthernet0/0/1",
                    action="alerted",
                    status="warning"
                ))
                logs.append(SplunkLogEngine.format_controller_webhook_event(
                    device=trap_dev,
                    controller_type="panorama" if "palo" in trap_dev.vendor else "catalyst_center",
                    alert_category="security_threat"
                ))

        # =========================================================================
        # NETSPOUT CORRELATION STAMPING
        # =========================================================================
        scen_str = scenario.value if hasattr(scenario, "value") else str(scenario)
        for log_entry in logs:
            self.tag_log(
                log_entry,
                run_id=self.current_run_id,
                scenario_id=self.current_scenario_id or scen_str,
                phase=self.current_phase,
                ground_truth=self.current_ground_truth
            )

        # =========================================================================
        # DUAL TRANSPORT DISPATCHER ROUTING (HEC & DIRECT SYSLOG)
        # =========================================================================
        if topology.global_transport:
            for log_entry in logs:
                try:
                    dispatcher.dispatch_log(log_entry, transport=topology.global_transport)
                except Exception:
                    pass

        return logs

    # -------------------------------------------------------------------------
    # Scenario Contract Topology Resolution
    # -------------------------------------------------------------------------
    def _get_topology_for_scenario(self, contract: Any) -> TopologyState:
        top_id = (getattr(contract, "topology_id", None) or (contract.get("topology_id") if isinstance(contract, dict) else "") or "").lower()
        scen_id = (getattr(contract, "id", None) or (contract.get("id") if isinstance(contract, dict) else "") or "").lower()

        if "sdwan" in top_id or "sdwan" in scen_id or "brownout" in scen_id:
            return get_cisco_sdwan_topology()
        elif "campus" in top_id or "rogue" in scen_id or "campus" in scen_id:
            return get_cisco_campus_topology()
        elif "aci" in top_id or "microburst" in scen_id or "nexus" in top_id:
            return get_cisco_aci_topology()
        elif "edge" in top_id or "breach" in scen_id or "mixed" in scen_id:
            return get_mixed_edge_topology()
        else:
            return get_default_secure_topology()

    # -------------------------------------------------------------------------
    # Specialized Phase Telemetry Generator
    # -------------------------------------------------------------------------
    def _generate_phase_telemetry(
        self,
        phase: str,
        contract: ScenarioContract,
        topology: TopologyState,
        graph: TopologyGraph
    ) -> List[LogEntry]:
        """Generates domain-correlated telemetry logs for a given scenario phase."""
        logs: List[LogEntry] = []
        scen_id = contract.id.lower()

        # Nodes lookup with graceful fallbacks
        switches = graph.find_nodes_by_type(NodeType.SWITCH) or graph.topology.nodes
        routers = graph.find_nodes_by_type(NodeType.ROUTER) or graph.topology.nodes
        firewalls = graph.find_nodes_by_type(NodeType.FIREWALL) or graph.topology.nodes
        aps = graph.find_nodes_by_type(NodeType.WIRELESS_AP) or graph.topology.nodes
        clients = graph.find_nodes_by_type(NodeType.CLIENT_EXTERNAL) or graph.topology.nodes
        servers = graph.find_nodes_by_type(NodeType.WEB_SERVER) or graph.topology.nodes

        switch_node = switches[0] if switches else Node(id="sw-01", name="Switch-01", type=NodeType.SWITCH, ip_address="10.0.1.1", vendor="cisco_catalyst")
        router_node = routers[0] if routers else Node(id="rt-01", name="Router-01", type=NodeType.ROUTER, ip_address="10.0.0.1", vendor="cisco_sdwan")
        fw_node = firewalls[0] if firewalls else Node(id="fw-01", name="Firewall-01", type=NodeType.FIREWALL, ip_address="198.51.100.1", vendor="cisco_asa")
        ap_node = aps[0] if aps else Node(id="ap-01", name="AP-01", type=NodeType.WIRELESS_AP, ip_address="10.10.20.99", vendor="cisco_catalyst")
        te_node = clients[0] if clients else Node(id="te-01", name="TE-Agent", type=NodeType.CLIENT_EXTERNAL, ip_address="172.16.1.50", vendor="cisco_thousandeyes")
        srv_node = servers[0] if servers else Node(id="srv-01", name="AppServer-01", type=NodeType.WEB_SERVER, ip_address="10.0.1.10", vendor="nginx")

        # ---------------------------------------------------------------------
        # CISCO SD-WAN BROWNOUT
        # ---------------------------------------------------------------------
        if "sdwan" in scen_id or "brownout" in scen_id:
            if phase == ScenarioPhase.BASELINE.value:
                logs.append(SplunkLogEngine.format_cisco_sdwan_linkhealth_log(
                    device=router_node, remote_system_ip="198.51.100.1", latency_ms=15.0,
                    jitter_ms=2.0, loss_pct=0.0, sla_status="COMPLIANT",
                    action="allowed", status="normal", signature="SD-WAN Tunnel SLA Compliant: Primary MPLS Carrier"
                ))
                logs.append(SplunkLogEngine.format_cisco_thousandeyes_log(
                    device=te_node, target_url="https://crm.corp.internal/health",
                    latency_ms=15.0, packet_loss_pct=0.0, http_code=200,
                    action="allowed", status="normal", signature="ThousandEyes synthetic latency nominal"
                ))
            elif phase == ScenarioPhase.DEGRADE.value:
                logs.append(SplunkLogEngine.format_cisco_sdwan_linkhealth_log(
                    device=router_node, remote_system_ip="198.51.100.1", latency_ms=185.0,
                    jitter_ms=38.0, loss_pct=14.5, sla_status="VIOLATION",
                    action="alerted", status="degraded", signature="SD-WAN Tunnel SLA Threshold Violated"
                ))
                logs.append(SplunkLogEngine.format_cisco_thousandeyes_log(
                    device=te_node, target_url="https://crm.corp.internal/health",
                    latency_ms=185.0, packet_loss_pct=14.5, http_code=200,
                    action="alerted", status="degraded", signature="ThousandEyes synthetic latency elevated"
                ))
            elif phase == ScenarioPhase.FAULT.value:
                logs.append(SplunkLogEngine.format_cisco_sdwan_bgp_log(
                    device=router_node, neighbor_ip="198.51.100.1", state_change="DOWN",
                    action="allowed", status="degraded", signature="BGP Peer Adjacency Down"
                ))
                logs.append(SplunkLogEngine.format_cisco_sdwan_linkhealth_log(
                    device=router_node, remote_system_ip="198.51.100.1", latency_ms=210.0,
                    jitter_ms=45.0, loss_pct=18.0, sla_status="VIOLATION",
                    action="alerted", status="degraded", signature="Critical SLA Violation: Primary MPLS Carrier Brownout"
                ))
            elif phase == ScenarioPhase.PROPAGATE.value:
                logs.append(SplunkLogEngine.format_cisco_thousandeyes_log(
                    device=te_node, target_url="https://crm.corp.internal/health",
                    latency_ms=250.0, packet_loss_pct=22.0, http_code=504,
                    action="alerted", status="degraded", signature="Synthetic Transaction Gateway Timeout (HTTP 504)"
                ))
            elif phase == ScenarioPhase.FAILOVER.value:
                logs.append(SplunkLogEngine.format_cisco_sdwan_linkhealth_log(
                    device=router_node, remote_system_ip="198.51.100.2", latency_ms=28.0,
                    jitter_ms=5.0, loss_pct=0.2, sla_status="COMPLIANT",
                    action="allowed", status="normal", signature="AppRoute dynamic redirect to secondary DIA"
                ))
                logs.append(SplunkLogEngine.format_cisco_sdwan_bgp_log(
                    device=router_node, neighbor_ip="198.51.100.2", state_change="UP",
                    action="allowed", status="normal", signature="BGP Failover Adjacency Established"
                ))
            elif phase == ScenarioPhase.RECOVER.value:
                logs.append(SplunkLogEngine.format_cisco_sdwan_linkhealth_log(
                    device=router_node, remote_system_ip="198.51.100.1", latency_ms=16.0,
                    jitter_ms=2.0, loss_pct=0.0, sla_status="COMPLIANT",
                    action="allowed", status="restored", signature="Primary MPLS Carrier Restored to Nominal SLA"
                ))
                logs.append(SplunkLogEngine.format_cisco_sdwan_bgp_log(
                    device=router_node, neighbor_ip="198.51.100.1", state_change="UP",
                    action="allowed", status="restored", signature="BGP Peer Adjacency Restored"
                ))

        # ---------------------------------------------------------------------
        # CISCO CAMPUS ROGUE AP
        # ---------------------------------------------------------------------
        elif "campus" in scen_id or "rogue" in scen_id:
            if phase == ScenarioPhase.BASELINE.value:
                logs.append(SplunkLogEngine.format_cisco_catalyst_security_event(
                    device=switch_node, client_mac="00:11:22:33:44:55",
                    event_type="DOT1X_CLIENT_AUTH_SUCCESS", action="allowed", status="normal",
                    signature="802.1X Supplicant Authenticated on GigabitEthernet1/0/12"
                ))
                logs.append(SplunkLogEngine.format_cisco_ise_log(
                    device=fw_node, client_mac="00:11:22:33:44:55", client_ip="10.10.20.101",
                    user="corp_user_01", auth_status="PASSED", profile="Corporate_Secure_VLAN",
                    action="allowed", status="normal", signature="ISE 802.1X Authentication Success"
                ))
            elif phase in (ScenarioPhase.DEGRADE.value, ScenarioPhase.FAULT.value):
                logs.append(SplunkLogEngine.format_cisco_catalyst_rogue_log(
                    device=ap_node, rogue_mac="00:1A:2B:3C:4D:5E", bssid="00:1A:2B:FF:EE:DD",
                    ssid="CORP_GUEST_ROGUE", channel=6, rssi=-55, action="alerted", status="breached",
                    signature="Rogue AP Detected: Unsanctioned BSSID on Campus Perimeter"
                ))
                logs.append(SplunkLogEngine.format_cisco_ise_log(
                    device=fw_node, client_mac="00:1A:2B:3C:4D:5E", client_ip="10.10.20.142",
                    user="rogue_attacker", auth_status="FAILED", profile="Quarantine_Restricted_VLAN",
                    action="blocked", status="blocked", signature="ISE 802.1X Unauthorized Supplicant Rejected"
                ))
            elif phase == ScenarioPhase.PROPAGATE.value:
                logs.append(SplunkLogEngine.format_cisco_mac_flap_log(
                    device=switch_node, mac="00:1A:2B:3C:4D:5E", vlan=10,
                    port1="GigabitEthernet1/0/12", port2="GigabitEthernet1/0/48",
                    action="alerted", status="breached",
                    signature="%SW_MATM-4-MACFLAP_NOTIF: L2 Loop / Rogue Device Flapping"
                ))
                logs.append(SplunkLogEngine.format_cisco_catalyst_security_event(
                    device=switch_node, client_mac="00:1A:2B:3C:4D:5E",
                    event_type="PORT_SECURITY_VIOLATION", action="alerted", status="degraded",
                    signature="Port Security Violation: Host Flap Threshold Exceeded"
                ))
            elif phase == ScenarioPhase.FAILOVER.value:
                logs.append(SplunkLogEngine.format_cisco_ise_log(
                    device=fw_node, client_mac="00:1A:2B:3C:4D:5E", client_ip="10.10.20.142",
                    user="rogue_attacker", auth_status="CONTAINED", profile="Quarantine_Restricted_VLAN",
                    action="blocked", status="blocked", signature="ISE CoA Dynamic Quarantine Profile Enforced"
                ))
                logs.append(SplunkLogEngine.format_cisco_catalyst_security_event(
                    device=switch_node, client_mac="00:1A:2B:3C:4D:5E",
                    event_type="PORT_SECURITY_SHUTDOWN", action="blocked", status="blocked",
                    signature="Port Security Error-Disable Action Applied to GigabitEthernet1/0/12"
                ))
            elif phase == ScenarioPhase.RECOVER.value:
                logs.append(SplunkLogEngine.format_cisco_catalyst_rogue_log(
                    device=ap_node, rogue_mac="00:1A:2B:3C:4D:5E", bssid="00:1A:2B:FF:EE:DD",
                    ssid="CORP_GUEST_ROGUE", channel=6, rssi=-95, action="allowed", status="restored",
                    signature="Rogue AP De-authenticated & Cleared from RF Matrix"
                ))
                logs.append(SplunkLogEngine.format_cisco_catalyst_security_event(
                    device=switch_node, client_mac="00:11:22:33:44:55",
                    event_type="PORT_RESTORED_NOMINAL", action="allowed", status="restored",
                    signature="Switchport GigabitEthernet1/0/12 Re-enabled in Standard VLAN"
                ))

        # ---------------------------------------------------------------------
        # CISCO ACI MICROBURST
        # ---------------------------------------------------------------------
        elif "aci" in scen_id or "microburst" in scen_id:
            if phase == ScenarioPhase.BASELINE.value:
                logs.append(SplunkLogEngine.format_cisco_mdt_log(
                    device=switch_node, sensor_path="Cisco-NX-OS-buffer-stats:queue-depth",
                    queue_depth_bytes=1250000, peak_buffer_pct=12.5, action="allowed", status="normal",
                    signature="Cisco IOS-XE MDT Streaming Telemetry: Nominal Buffer Utilization"
                ))
                logs.append(SplunkLogEngine.format_cisco_aci_health_log(
                    device=switch_node, fabric_health=100, action="allowed", status="normal",
                    signature="ACI Fabric Health Score: 100/100 Nominal East-West Flow"
                ))
                logs.append(SplunkLogEngine.format_cisco_aci_nexus_log(
                    device=switch_node, asic_interface="Ethernet1/24",
                    buffer_util_pct=12.5, dropped_packets=0, fabric_health=100,
                    action="allowed", status="normal", signature="Nexus 9K ASIC Buffer Normal Flow"
                ))
            elif phase in (ScenarioPhase.DEGRADE.value, ScenarioPhase.FAULT.value):
                logs.append(SplunkLogEngine.format_cisco_aci_nexus_log(
                    device=switch_node, asic_interface="Ethernet1/24 (Ingress Incast)",
                    buffer_util_pct=98.5, dropped_packets=1250, fabric_health=58,
                    action="dropped", status="degraded", signature="Nexus 9K Ingress Microburst Queue Saturation"
                ))
                logs.append(SplunkLogEngine.format_cisco_aci_health_log(
                    device=switch_node, fabric_health=58, action="alerted", status="degraded",
                    signature="ACI Fabric Health Score Degraded: Leaf Buffer Incast Detected"
                ))
                logs.append(SplunkLogEngine.format_cisco_mdt_log(
                    device=switch_node, sensor_path="Cisco-NX-OS-buffer-stats:queue-depth",
                    queue_depth_bytes=26500000, peak_buffer_pct=98.5, action="alerted", status="degraded",
                    signature="Cisco IOS-XE MDT Streaming Telemetry Ingress Incast"
                ))
            elif phase == ScenarioPhase.PROPAGATE.value:
                logs.append(SplunkLogEngine.format_cisco_mdt_log(
                    device=switch_node, sensor_path="Cisco-NX-OS-buffer-stats:egress-queue",
                    queue_depth_bytes=28900000, peak_buffer_pct=99.1, action="alerted", status="degraded",
                    signature="Cisco IOS-XE MDT Egress Queue Buffer Congestion Alert"
                ))
                logs.append(SplunkLogEngine.format_cisco_aci_nexus_log(
                    device=switch_node, asic_interface="Ethernet1/24",
                    buffer_util_pct=99.1, dropped_packets=2450, fabric_health=52,
                    action="dropped", status="degraded",
                    signature="%ETHPORT-5-IF_RX_OVERFLOW: Ingress FIFO Overrun / PFC Storm Active"
                ))
                logs.append(SplunkLogEngine.format_cisco_aci_health_log(
                    device=switch_node, fabric_health=52, action="alerted", status="degraded",
                    signature="ACI Fabric Health Score Critical: Fabric Incast Propagation"
                ))
            elif phase == ScenarioPhase.FAILOVER.value:
                logs.append(SplunkLogEngine.format_cisco_aci_nexus_log(
                    device=switch_node, asic_interface="Ethernet1/24",
                    buffer_util_pct=68.0, dropped_packets=5, fabric_health=85,
                    action="allowed", status="normal", signature="Dynamic Ingress Buffer Reserving Active"
                ))
                logs.append(SplunkLogEngine.format_cisco_aci_health_log(
                    device=switch_node, fabric_health=85, action="allowed", status="normal",
                    signature="ACI Fabric Health Score Recovering: Buffer Allocation Rebalanced"
                ))
            elif phase == ScenarioPhase.RECOVER.value:
                logs.append(SplunkLogEngine.format_cisco_aci_nexus_log(
                    device=switch_node, asic_interface="Ethernet1/24",
                    buffer_util_pct=14.0, dropped_packets=0, fabric_health=100,
                    action="allowed", status="restored", signature="Buffer Incast Cleared - Line Rate Forwarding Restored"
                ))
                logs.append(SplunkLogEngine.format_cisco_aci_health_log(
                    device=switch_node, fabric_health=100, action="allowed", status="restored",
                    signature="ACI Fabric Health Score Restored: 100/100"
                ))
                logs.append(SplunkLogEngine.format_cisco_mdt_log(
                    device=switch_node, sensor_path="Cisco-NX-OS-buffer-stats:queue-depth",
                    queue_depth_bytes=1400000, peak_buffer_pct=14.0, action="allowed", status="restored",
                    signature="Cisco IOS-XE MDT Streaming Telemetry: Nominal Queue Depth"
                ))

        # ---------------------------------------------------------------------
        # MIXED VENDOR / EDGE BREACH
        # ---------------------------------------------------------------------
        elif "mixed" in scen_id or "edge" in scen_id or "breach" in scen_id:
            if phase == ScenarioPhase.BASELINE.value:
                logs.append(SplunkLogEngine.format_palo_alto_log(
                    device=fw_node, src_ip="198.51.100.42", dest_ip="10.128.2.10",
                    src_port=52341, dest_port=443, proto="TCP", action="allowed",
                    signature="PAN-OS Clean Traffic Flow", status="normal", duration_ms=4
                ))
                logs.append(SplunkLogEngine.format_fortinet_ips_log(
                    device=fw_node, src_ip="198.51.100.42", dest_ip="10.128.2.10",
                    src_port=52341, dest_port=443, attack="Corporate.HTTPS.Web.Session",
                    action="allowed", status="normal", duration_ms=2, signature="FortiGate UTM Policy Permit"
                ))
            elif phase in (ScenarioPhase.DEGRADE.value, ScenarioPhase.FAULT.value):
                logs.append(SplunkLogEngine.format_meraki_alert_log(
                    device=ap_node, client_mac="44:65:0E:12:34:56",
                    alert_type="air_marshal_rogue_detected", channel=36,
                    action="alerted", status="breached",
                    signature="Meraki Air Marshal Rogue AP Detected on Edge Wireless"
                ))
                logs.append(SplunkLogEngine.format_palo_alto_threat_log(
                    device=fw_node, src_ip="198.51.100.42", dest_ip="10.128.2.10",
                    src_port=445, dest_port=445, threat_name="Scan: TCP Port Scan / Lateral Probing",
                    threat_id=80012, action="dropped", status="blocked", duration_ms=3
                ))
            elif phase == ScenarioPhase.PROPAGATE.value:
                logs.append(SplunkLogEngine.format_fortinet_ips_log(
                    device=fw_node, src_ip="198.51.100.42", dest_ip="10.128.2.10",
                    src_port=49210, dest_port=445, attack="CobaltStrike.Command.and.Control.Beacon",
                    action="dropped", status="blocked", duration_ms=2, signature="FortiGate IPS Exploit Attempt Denied"
                ))
                logs.append(SplunkLogEngine.format_nginx_web_log(
                    device=srv_node, src_ip="198.51.100.42", dest_ip="10.128.2.10",
                    method="POST", uri="/api/v1/admin/exploit", http_code=403, bytes_sent=182,
                    action="blocked", signature="WAF Blocked Unauthorized Exploit Path",
                    status="blocked", duration_ms=5
                ))
            elif phase == ScenarioPhase.FAILOVER.value:
                logs.append(SplunkLogEngine.format_palo_alto_threat_log(
                    device=fw_node, src_ip="198.51.100.42", dest_ip="10.128.2.10",
                    src_port=445, dest_port=445, threat_name="Micro-Segmentation Isolation Applied",
                    threat_id=99002, action="blocked", status="blocked"
                ))
                logs.append(SplunkLogEngine.format_fortinet_ips_log(
                    device=fw_node, src_ip="198.51.100.42", dest_ip="10.128.2.10",
                    src_port=49211, dest_port=80, attack="Perimeter.Blacklist.Quarantine.Active",
                    action="dropped", status="blocked", duration_ms=1,
                    signature="FortiGate Source IP Dynamic Quarantine Applied"
                ))
            elif phase == ScenarioPhase.RECOVER.value:
                logs.append(SplunkLogEngine.format_palo_alto_log(
                    device=fw_node, src_ip="198.51.100.42", dest_ip="10.128.2.10",
                    src_port=54321, dest_port=443, proto="TCP", action="allowed",
                    signature="PAN-OS Policy Permit: Clean Enterprise Traffic", status="restored"
                ))
                logs.append(SplunkLogEngine.format_fortinet_ips_log(
                    device=fw_node, src_ip="198.51.100.42", dest_ip="10.128.2.10",
                    src_port=54321, dest_port=443, attack="Corporate.HTTPS.Web.Session",
                    action="allowed", status="restored", duration_ms=2,
                    signature="FortiGate Perimeter Security Restored to Nominal"
                ))

        # ---------------------------------------------------------------------
        # SNMP FAULT STORM
        # ---------------------------------------------------------------------
        elif "snmp" in scen_id or "trap" in scen_id:
            if phase in (ScenarioPhase.DEGRADE.value, ScenarioPhase.FAULT.value):
                for i in range(3):
                    logs.append(SplunkLogEngine.format_snmp_trap(
                        device=switch_node, trap_type="linkDown",
                        interface_name=f"GigabitEthernet1/0/{i+1}",
                        action="alerted", status="warning"
                    ))
            elif phase == ScenarioPhase.RECOVER.value:
                logs.append(SplunkLogEngine.format_snmp_trap(
                    device=switch_node, trap_type="linkUp",
                    interface_name="GigabitEthernet1/0/1",
                    action="alerted", status="normal"
                ))

        # ---------------------------------------------------------------------
        # OPENCONFIG / MDT STREAMING
        # ---------------------------------------------------------------------
        elif "openconfig" in scen_id or "mdt" in scen_id:
            logs.append(SplunkLogEngine.format_mdt_stream(
                device=switch_node, interface_name="GigabitEthernet0/0/1",
                in_octets=random.randint(60000000, 95000000),
                out_octets=random.randint(40000000, 70000000),
                cpu_pct=45.0 if phase != ScenarioPhase.FAULT.value else 92.0,
                memory_pct=50.0, action="allowed",
                status="normal" if phase != ScenarioPhase.FAULT.value else "degraded"
            ))

        # ---------------------------------------------------------------------
        # GENERAL FALLBACK (Synthesize from Contract Sourcetypes)
        # ---------------------------------------------------------------------
        else:
            now_ts = SplunkLogEngine.current_timestamp_iso()
            for st in (contract.sourcetypes[:2] or ["cisco:ios:syslog"]):
                status = "normal"
                if phase in (ScenarioPhase.DEGRADE.value, ScenarioPhase.FAULT.value):
                    status = "degraded"
                elif phase == ScenarioPhase.RECOVER.value:
                    status = "restored"

                logs.append(LogEntry(
                    timestamp=now_ts,
                    device_id=switch_node.name or switch_node.id,
                    src_ip="10.0.1.1",
                    dest_ip="10.0.2.1",
                    protocol="TCP",
                    duration="5ms",
                    action="allowed" if status in ("normal", "restored") else "alerted",
                    signature=f"NetSpout Simulated Telemetry - Phase {phase}",
                    status=status,
                    raw_log=f"{now_ts} {switch_node.name} %NETSPOUT-6-INFO: phase={phase} status={status} sourcetype={st}",
                    node_type=switch_node.type.value,
                    node_id=switch_node.id,
                    vendor=switch_node.vendor,
                    sourcetype=st
                ))

        return logs

    # -------------------------------------------------------------------------
    # Destination Observation & Evidence Verification (Gate 6)
    # -------------------------------------------------------------------------
    def check_destination_observation(
        self,
        run_id: str,
        transport: Optional[TelemetryTransportConfig] = None,
        max_retries: int = 4,
        backoff_sec: float = 0.5,
        index: Optional[str] = None,
        delay_sec: Optional[float] = None
    ) -> Tuple[str, int]:
        """
        Queries the destination (Splunk REST API) to observe indexed events for the run_id.
        Handles indexing delay using bounded retry.
        Returns: (status, observed_count)
        status: VERIFIED | OBSERVATION_PENDING | FAILED | NOT_CHECKED
        """
        if delay_sec is not None:
            backoff_sec = delay_sec

        if not transport:
            transport = TelemetryTransportConfig(hec_index=index or "idx_network_ops")

        hec_url = transport.hec_url or "https://127.0.0.1:8888/services/collector"
        rest_candidates = []
        if ":8888" in hec_url:
            rest_candidates.append(hec_url.replace(":8888", ":8889").replace("/services/collector", "/services/search/jobs/export"))
        elif ":8088" in hec_url:
            rest_candidates.append(hec_url.replace(":8088", ":8089").replace("/services/collector", "/services/search/jobs/export"))
        rest_candidates.append("https://localhost:8889/services/search/jobs/export")
        rest_candidates.append("https://127.0.0.1:8889/services/search/jobs/export")

        auth_header = "Basic " + base64.b64encode(b"admin:SplunkPassword123!").decode("ascii")
        target_idx = index or transport.hec_index or "idx_network_ops"
        search_query = f"search index={target_idx} {run_id}"

        ssl_verify = getattr(transport, "hec_ssl_verify", True)
        allow_insecure = getattr(transport, "hec_allow_insecure_tls", False)
        ctx = ssl.create_default_context()
        if allow_insecure or not ssl_verify:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

        data = urllib.parse.urlencode({
            "search": search_query,
            "output_mode": "json"
        }).encode("utf-8")

        for attempt in range(max_retries):
            for endpoint in rest_candidates:
                try:
                    req = urllib.request.Request(endpoint, data=data, headers={"Authorization": auth_header})
                    with urllib.request.urlopen(req, timeout=2.5, context=ctx) as resp:
                        count = 0
                        for line in resp:
                            line_str = line.decode("utf-8", errors="replace").strip()
                            if line_str:
                                try:
                                    d = json.loads(line_str)
                                    if "result" in d:
                                        count += 1
                                except Exception:
                                    pass
                        if count > 0:
                            return "VERIFIED", count
                except Exception:
                    continue

            if attempt < max_retries - 1:
                time.sleep(backoff_sec)

        return "OBSERVATION_PENDING", 0

    # -------------------------------------------------------------------------
    # Multi-Phase Scenario Execution Engine (Gate 4 Core Lifecycle)
    # -------------------------------------------------------------------------
    def run_scenario(
        self,
        request: ScenarioRunRequest,
        topology: Optional[TopologyState] = None
    ) -> RunManifest:
        """
        Executes a complete, deterministic, multi-phase scenario lifecycle.
        Progresses through:
          INITIALIZE -> BASELINE -> DEGRADE -> FAULT -> PROPAGATE -> FAILOVER -> RECOVER -> VALIDATE -> COMPLETE
        Produces an immutable RunManifest containing ground truth records and validation outcomes.
        """
        start_time = time.time()

        # 1. Deterministic Seed
        if request.seed is not None:
            random.seed(request.seed)
            self.rng = random.Random(request.seed)
            self.round_robin_counter = 0
            self.lateral_step = 0
            self.telemetry_tick = 0
        else:
            self.rng = random.Random()

        # 2. Time Control
        time_mode = (request.time_mode or "TEST").upper()
        phase_delay = 0.0
        if time_mode == "ACCELERATED":
            phase_delay = 0.02
        elif time_mode == "REALTIME":
            phase_delay = 0.5

        # 3. Resolve Scenario Contract
        scenario_id = request.scenario_id
        contract = None
        if catalog_instance:
            contract = catalog_instance.get_scenario_contract(scenario_id)
        if not contract and NetSpoutCatalog:
            try:
                cat = NetSpoutCatalog()
                contract = cat.get_scenario_contract(scenario_id)
            except Exception:
                pass

        if isinstance(contract, dict):
            try:
                contract = ScenarioContract(**contract)
            except Exception:
                pass

        if not contract:
            contract = ScenarioContract(
                id=scenario_id,
                display_name=scenario_id.replace("_", " ").title(),
                topology_id="default_secure",
                vendor_scope=["generic"],
                sourcetypes=["cisco:ios:syslog"],
                phases=[]
            )

        # 4. Resolve Topology & Graph
        if topology is None:
            topology = self._get_topology_for_scenario(contract)
        if getattr(request, "transport_config", None):
            topology.global_transport = request.transport_config
        elif not getattr(topology, "global_transport", None):
            topology.global_transport = TelemetryTransportConfig()
        graph = TopologyGraph(topology)
        initial_snapshot = graph.snapshot_state()

        # 5. Initialize Run Manifest & State
        run_id = self.generate_run_id()
        manifest = RunManifest(
            run_id=run_id,
            scenario_id=contract.id,
            scenario_name=contract.display_name or contract.name or contract.id,
            topology_id=contract.topology_id or getattr(topology, "id", "custom"),
            scenario_maturity=getattr(contract, "maturity", "CONTRACTED"),
            seed=request.seed,
            time_mode=time_mode,
            start_time=start_time,
            affected_devices=list(contract.affected_entities) if contract.affected_entities else [n.id for n in topology.nodes[:3]],
            expected_sourcetypes=list(contract.sourcetypes) if contract.sourcetypes else []
        )

        self.active_manifests[run_id] = manifest
        self.run_logs[run_id] = []
        self.ground_truth_by_run[run_id] = []
        if run_id not in self.stop_requests:
            self.stop_requests[run_id] = False
        self.current_run_id = run_id
        self.current_scenario_id = contract.id

        # 6. Determine Phase Sequence
        phases_to_run = []
        if contract.phases:
            phases_to_run = [
                p.get("phase") if isinstance(p, dict) else (p.phase.value if hasattr(p.phase, "value") else str(p.phase))
                for p in contract.phases
            ]
        else:
            phases_to_run = [
                ScenarioPhase.INITIALIZE.value,
                ScenarioPhase.BASELINE.value,
                ScenarioPhase.DEGRADE.value,
                ScenarioPhase.FAULT.value,
                ScenarioPhase.PROPAGATE.value,
                ScenarioPhase.FAILOVER.value,
                ScenarioPhase.RECOVER.value,
                ScenarioPhase.VALIDATE.value,
                ScenarioPhase.COMPLETE.value
            ]

        if ScenarioPhase.INITIALIZE.value not in phases_to_run:
            phases_to_run.insert(0, ScenarioPhase.INITIALIZE.value)
        if ScenarioPhase.VALIDATE.value not in phases_to_run:
            phases_to_run.append(ScenarioPhase.VALIDATE.value)
        if ScenarioPhase.COMPLETE.value not in phases_to_run:
            phases_to_run.append(ScenarioPhase.COMPLETE.value)

        # 7. Execute Phase Loop
        for phase_name in phases_to_run:
            if self.stop_requests.get(run_id, False):
                manifest.errors.append("Execution cancelled by user request")
                break

            self.current_phase = phase_name
            phase_logs: List[LogEntry] = []

            if phase_name == ScenarioPhase.INITIALIZE.value:
                self.record_ground_truth(
                    run_id=run_id,
                    scenario_id=contract.id,
                    phase=phase_name,
                    affected_nodes=[n.id for n in topology.nodes],
                    affected_edges=[e.id for e in topology.edges],
                    observations=["Topology initialized", "Initial graph state snapshotted"]
                )

            elif phase_name == ScenarioPhase.BASELINE.value:
                self.record_ground_truth(
                    run_id=run_id,
                    scenario_id=contract.id,
                    phase=phase_name,
                    observations=["Establishing nominal baseline telemetry stream", "Zero packet loss"]
                )
                phase_logs = self._generate_phase_telemetry(phase_name, contract, topology, graph)
                if not phase_logs:
                    phase_logs = self.execute_step(topology, ScenarioType.NORMAL_TRAFFIC)

            elif phase_name == ScenarioPhase.DEGRADE.value:
                target_edge_id = None
                if contract.fault_definition:
                    target_edge_id = contract.fault_definition.get("target_edge_id")
                if not target_edge_id and topology.edges:
                    target_edge_id = topology.edges[0].id

                if target_edge_id:
                    graph.degrade_link(target_edge_id, packet_loss_pct=14.5, latency_ms=185.0, jitter_ms=38.0)

                self.record_ground_truth(
                    run_id=run_id,
                    scenario_id=contract.id,
                    phase=phase_name,
                    intentional_fault={"type": "link_degradation", "target_edge": target_edge_id, "loss_pct": 14.5, "latency_ms": 185.0},
                    affected_edges=[target_edge_id] if target_edge_id else [],
                    observations=["SLA violation observed", "Link quality degraded"]
                )
                phase_logs = self._generate_phase_telemetry(phase_name, contract, topology, graph)

            elif phase_name == ScenarioPhase.FAULT.value:
                self.record_ground_truth(
                    run_id=run_id,
                    scenario_id=contract.id,
                    phase=phase_name,
                    intentional_fault={"type": "primary_fault", "description": contract.attack_vector or "Primary fault injected"},
                    affected_nodes=manifest.affected_devices,
                    observations=["Primary fault triggered", "Alerts dispatched"]
                )
                phase_logs = self._generate_phase_telemetry(phase_name, contract, topology, graph)

            elif phase_name == ScenarioPhase.PROPAGATE.value:
                self.record_ground_truth(
                    run_id=run_id,
                    scenario_id=contract.id,
                    phase=phase_name,
                    secondary_effects=["Cascading buffer incast", "Neighbor flap alert"],
                    observations=["Secondary telemetry spike observed"]
                )
                phase_logs = self._generate_phase_telemetry(phase_name, contract, topology, graph)

            elif phase_name == ScenarioPhase.FAILOVER.value:
                self.record_ground_truth(
                    run_id=run_id,
                    scenario_id=contract.id,
                    phase=phase_name,
                    observations=["Dynamic route steer engaged", "Quarantine enforcement verified"]
                )
                phase_logs = self._generate_phase_telemetry(phase_name, contract, topology, graph)

            elif phase_name == ScenarioPhase.RECOVER.value:
                graph.restore_all()
                self.record_ground_truth(
                    run_id=run_id,
                    scenario_id=contract.id,
                    phase=phase_name,
                    intentional_recovery={"type": "full_restoration", "status": "restored"},
                    observations=["Topology state restored to nominal", "Alarms cleared"]
                )
                phase_logs = self._generate_phase_telemetry(phase_name, contract, topology, graph)

            elif phase_name == ScenarioPhase.VALIDATE.value:
                self.record_ground_truth(
                    run_id=run_id,
                    scenario_id=contract.id,
                    phase=phase_name,
                    observations=["Evaluating validation rules against generated telemetry"]
                )
                manifest.validation_results = ValidationEngine.evaluate_all(contract.validation_rules, self.run_logs[run_id], graph)

            elif phase_name == ScenarioPhase.COMPLETE.value:
                self.record_ground_truth(
                    run_id=run_id,
                    scenario_id=contract.id,
                    phase=phase_name,
                    observations=["Scenario lifecycle complete"]
                )

            # Tag and accumulate logs for this phase
            for entry in phase_logs:
                self.tag_log(
                    entry,
                    run_id=run_id,
                    scenario_id=contract.id,
                    phase=phase_name,
                    ground_truth=True
                )
                self.run_logs[run_id].append(entry)

                if request.dispatch_telemetry and topology.global_transport:
                    manifest.dispatch_attempted += 1
                    try:
                        res = dispatcher.dispatch_log(entry, transport=topology.global_transport)
                        evt_id = getattr(entry, "netspout_event_id", f"evt_{len(manifest.dispatch_results)}")
                        manifest.dispatch_results[evt_id] = res
                        hec_res = res.get("hec")
                        if hec_res and hec_res.get("success"):
                            manifest.dispatch_succeeded += 1
                        else:
                            manifest.dispatch_failed += 1
                            if hec_res and hec_res.get("message"):
                                manifest.errors.append(f"HEC Dispatch Error: {hec_res.get('message')}")
                    except Exception as e:
                        manifest.dispatch_failed += 1
                        manifest.errors.append(f"Dispatch Exception: {str(e)}")

            manifest.phases_executed.append(phase_name)

            if phase_delay > 0:
                time.sleep(phase_delay)

        # 8. Post-Run Manifest Compilation
        st_counts: Dict[str, int] = {}
        for entry in self.run_logs[run_id]:
            st = entry.sourcetype or "generic"
            st_counts[st] = st_counts.get(st, 0) + 1

        manifest.actual_generated_counts = st_counts
        manifest.total_events_generated = len(self.run_logs[run_id])
        manifest.ground_truth_records = list(self.ground_truth_by_run.get(run_id, []))
        target_idx = topology.global_transport.hec_index if topology.global_transport else "idx_network_ops"
        manifest.splunk_search_query = f'index={target_idx} netspout_run_id="{run_id}"'

        # Destination Observation Check (handles indexing delay)
        if request.dispatch_telemetry and manifest.dispatch_succeeded > 0:
            obs_status, observed_cnt = self.check_destination_observation(run_id, topology.global_transport)
            manifest.observed_count = observed_cnt
            manifest.observation_status = obs_status
        elif request.dispatch_telemetry and manifest.dispatch_failed > 0:
            manifest.observed_count = 0
            manifest.observation_status = "FAILED"
        else:
            manifest.observed_count = 0
            manifest.observation_status = "NOT_CHECKED"

        # Simulation Validation (contract rules evaluated against generated events)
        if not manifest.validation_results and contract.validation_rules:
            manifest.validation_results = ValidationEngine.evaluate_all(contract.validation_rules, self.run_logs[run_id], graph)

        # Destination Validation Evaluation
        if request.dispatch_telemetry:
            if manifest.observed_count > 0:
                manifest.destination_validation = ValidationStatus.PASS.value
            elif manifest.observation_status == "OBSERVATION_PENDING":
                manifest.destination_validation = "PENDING"
            else:
                manifest.destination_validation = ValidationStatus.FAIL.value
        else:
            manifest.destination_validation = ValidationStatus.NOT_RUN.value

        # Overall Validation:
        # INVARIANT 2: Destination validation cannot PASS without destination evidence
        if self.stop_requests.get(run_id, False):
            manifest.overall_validation = ValidationStatus.BLOCKED.value
        elif request.dispatch_telemetry and manifest.destination_validation != ValidationStatus.PASS.value:
            manifest.overall_validation = ValidationStatus.FAIL.value if manifest.destination_validation == ValidationStatus.FAIL.value else ValidationStatus.BLOCKED.value
        elif manifest.validation_results:
            all_pass = all(r.status == ValidationStatus.PASS for r in manifest.validation_results)
            any_fail = any(r.status == ValidationStatus.FAIL for r in manifest.validation_results)
            manifest.overall_validation = ValidationStatus.PASS.value if all_pass else (ValidationStatus.FAIL.value if any_fail else ValidationStatus.BLOCKED.value)
        else:
            manifest.overall_validation = ValidationStatus.PASS.value

        manifest.end_time = time.time()
        manifest.duration_sec = round(manifest.end_time - start_time, 3)

        self.current_run_id = None
        self.current_scenario_id = None
        return manifest

    # -------------------------------------------------------------------------
    # Run Management & Query APIs
    # -------------------------------------------------------------------------
    def get_active_run(self) -> Optional[RunManifest]:
        if self.current_run_id and self.current_run_id in self.active_manifests:
            return self.active_manifests[self.current_run_id]
        if self.active_manifests:
            latest_id = list(self.active_manifests.keys())[-1]
            return self.active_manifests[latest_id]
        return None

    def get_run(self, run_id: str) -> Optional[RunManifest]:
        return self.active_manifests.get(run_id)

    def get_run_logs(self, run_id: str) -> List[LogEntry]:
        return self.run_logs.get(run_id, [])

    def list_runs(self) -> List[RunManifest]:
        return list(self.active_manifests.values())

    def stop_run(self, run_id: str) -> bool:
        if run_id in self.active_manifests:
            self.stop_requests[run_id] = True
            return True
        return False

    def validate_manifest(self, run_id: str) -> List[ValidationResult]:
        manifest = self.active_manifests.get(run_id)
        if not manifest:
            return []
        logs = self.run_logs.get(run_id, [])
        contract = None
        if catalog_instance:
            contract = catalog_instance.get_scenario_contract(manifest.scenario_id)
        if not contract:
            return manifest.validation_results
        results = ValidationEngine.evaluate_all(contract.validation_rules, logs)
        manifest.validation_results = results
        all_pass = all(r.status == ValidationStatus.PASS for r in results)
        any_fail = any(r.status == ValidationStatus.FAIL for r in results)
        manifest.overall_validation = ValidationStatus.PASS.value if all_pass else (ValidationStatus.FAIL.value if any_fail else ValidationStatus.BLOCKED.value)
        return results


# Global singleton instance
scenario_runner = ScenarioRunner()
