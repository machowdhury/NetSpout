# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/graph_engine.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""
Graph Engine for Network Topology Analysis
Traverses custom network topologies, computes shortest paths (BFS),
detects in-line security nodes (Firewall/Load Balancer), and evaluates
whether attack vectors reach internal targets or are intercepted.
"""

from collections import deque
from typing import List, Dict, Set, Optional, Tuple, Any
try:
    from netspout_core.models import TopologyState, Node, Edge, NodeType, NodeHardware, NodePowerState
except ImportError:
    try:
        from app.models import TopologyState, Node, Edge, NodeType, NodeHardware, NodePowerState
    except ImportError:
        from models import TopologyState, Node, Edge, NodeType, NodeHardware, NodePowerState


def _get_yang_store():
    try:
        from netspout_core.gnmi_engine import yang_store
        return yang_store
    except ImportError:
        try:
            from app.gnmi_engine import yang_store
            return yang_store
        except ImportError:
            try:
                from gnmi_engine import yang_store
                return yang_store
            except ImportError:
                return None


class TopologyGraph:
    def __init__(self, topology: TopologyState):
        self.topology = topology
        self.nodes_by_id: Dict[str, Node] = {n.id: n for n in topology.nodes}
        self.adj: Dict[str, List[str]] = {n.id: [] for n in topology.nodes}
        self._build_graph()

    def _build_graph(self):
        self.adj = {n.id: [] for n in self.topology.nodes}
        for edge in self.topology.edges:
            # Only up edges route traffic
            if edge.status == "down":
                continue
            if edge.source in self.adj and edge.target in self.adj:
                node_a = self.nodes_by_id.get(edge.source)
                node_b = self.nodes_by_id.get(edge.target)
                if node_a and getattr(node_a, "power_state", "running") == "stopped":
                    continue
                if node_b and getattr(node_b, "power_state", "running") == "stopped":
                    continue
                if edge.target not in self.adj[edge.source]:
                    self.adj[edge.source].append(edge.target)
                if edge.source not in self.adj[edge.target]:
                    self.adj[edge.target].append(edge.source)

    def get_node(self, node_id: str) -> Optional[Node]:
        return self.nodes_by_id.get(node_id)

    def get_edge(self, edge_id: str) -> Optional[Edge]:
        return next((e for e in self.topology.edges if e.id == edge_id), None)

    def get_neighbors(self, node_id: str) -> List[str]:
        return list(self.adj.get(node_id, []))

    def get_affected_neighbors(self, node_id: str, hops: int = 2) -> List[str]:
        """Discovers all nodes within N hops of node_id."""
        if node_id not in self.adj:
            return []
        visited = {node_id}
        queue = deque([(node_id, 0)])
        neighbors = []
        while queue:
            curr, dist = queue.popleft()
            if 0 < dist <= hops:
                neighbors.append(curr)
            if dist < hops:
                for nxt in self.adj.get(curr, []):
                    if nxt not in visited:
                        visited.add(nxt)
                        queue.append((nxt, dist + 1))
        return neighbors

    def find_nodes_by_type(self, node_type: NodeType) -> List[Node]:
        return [n for n in self.topology.nodes if n.type == node_type]

    def find_all_paths(self, start_id: str, end_id: str, max_depth: int = 12) -> List[List[str]]:
        """Finds all simple paths from start_id to end_id using DFS with depth cutoff."""
        if start_id not in self.adj or end_id not in self.adj:
            return []
        
        results: List[List[str]] = []
        
        def dfs(current: str, target: str, visited: Set[str], path: List[str]):
            if len(path) > max_depth:
                return
            if current == target:
                results.append(list(path))
                return
            for neighbor in self.adj.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    path.append(neighbor)
                    dfs(neighbor, target, visited, path)
                    path.pop()
                    visited.remove(neighbor)

        dfs(start_id, end_id, {start_id}, [start_id])
        return results

    def shortest_path(self, start_id: str, end_id: str) -> Optional[List[str]]:
        """Computes shortest hop path using BFS."""
        if start_id not in self.adj or end_id not in self.adj:
            return None
        if start_id == end_id:
            return [start_id]
        
        queue = deque([[start_id]])
        visited = {start_id}
        
        while queue:
            path = queue.popleft()
            node = path[-1]
            for neighbor in self.adj.get(node, []):
                if neighbor == end_id:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])
        return None

    def evaluate_perimeter_security(self, client_id: str, target_id: str) -> Dict[str, any]:
        """
        Evaluates the routing path from client to target.
        Detects whether an active Firewall intercepts the path.
        Returns security posture:
          - connected: bool
          - has_firewall_inline: bool (ALL paths must pass through a firewall)
          - bypassed: bool (at least one path reaches target WITHOUT a firewall)
          - intercepting_firewall_id: Optional[str]
          - load_balancer_id: Optional[str]
          - active_path: List[str]
        """
        paths = self.find_all_paths(client_id, target_id)
        if not paths:
            return {
                "connected": False,
                "has_firewall_inline": False,
                "bypassed": False,
                "intercepting_firewall_id": None,
                "load_balancer_id": None,
                "active_path": []
            }

        # Sort paths by length (prefer shortest natural routing)
        paths.sort(key=len)
        primary_path = paths[0]

        # Check if ANY path exists that bypasses the firewall
        bypassed_path = None
        protected_path = None
        intercepting_fw = None
        lb_node = None

        for path in paths:
            firewalls = [nid for nid in path if self.nodes_by_id[nid].type == NodeType.FIREWALL]
            lbs = [nid for nid in path if self.nodes_by_id[nid].type == NodeType.LOAD_BALANCER]
            if lbs and not lb_node:
                lb_node = lbs[0]

            if not firewalls:
                bypassed_path = path
            else:
                if not protected_path:
                    protected_path = path
                    intercepting_fw = firewalls[0]

        # If a bypass path exists, traffic naturally follows it or attacker leverages it
        has_firewall_inline = (bypassed_path is None and protected_path is not None)
        is_bypassed = (bypassed_path is not None and len([n for n in self.topology.nodes if n.type == NodeType.FIREWALL]) > 0)
        chosen_path = bypassed_path if is_bypassed else primary_path

        return {
            "connected": True,
            "has_firewall_inline": has_firewall_inline,
            "bypassed": is_bypassed,
            "intercepting_firewall_id": intercepting_fw,
            "load_balancer_id": lb_node,
            "active_path": chosen_path
        }

    def evaluate_lateral_spread(self, infected_server_id: str) -> Dict[str, any]:
        """
        Evaluates whether an infection on infected_server can spread laterally to other internal servers/DB.
        Checks if internal subnets have micro-segmentation / internal firewalls.
        """
        internal_targets = [n.id for n in self.topology.nodes if n.type in (NodeType.WEB_SERVER, NodeType.DATABASE) and n.id != infected_server_id]
        if not internal_targets:
            return {"can_spread": False, "spread_targets": [], "blocked_targets": []}

        spreadable: List[str] = []
        blocked: List[str] = []

        for target_id in internal_targets:
            paths = self.find_all_paths(infected_server_id, target_id)
            if not paths:
                continue
            
            # Check if any path between these two internal nodes passes through an internal firewall
            is_segmented = False
            for path in paths:
                fws = [nid for nid in path if self.nodes_by_id[nid].type == NodeType.FIREWALL]
                if fws:
                    is_segmented = True
                    break
            
            if is_segmented:
                blocked.append(target_id)
            else:
                spreadable.append(target_id)

        return {
            "can_spread": len(spreadable) > 0,
            "spread_targets": spreadable,
            "blocked_targets": blocked
        }

    def propagate_link_failure(self, edge_id: str) -> Dict[str, Any]:
        """
        Cross-device state propagation for link failures:
        1. Drops edge status to 'down'.
        2. Toggles connected interfaces to 'down'.
        3. Updates OpenConfig operational state.
        4. Drops BGP sessions traversing this link.
        5. Rebuilds active graph routing table.
        """
        edge = next((e for e in self.topology.edges if e.id == edge_id), None)
        if not edge:
            return {"success": False, "error": f"Edge {edge_id} not found"}

        edge.status = "down"
        node_a = self.nodes_by_id.get(edge.source)
        node_b = self.nodes_by_id.get(edge.target)

        # Update interface oper status on both ends
        if node_a and node_a.hardware:
            for intf in node_a.hardware.interfaces:
                if intf.name == edge.source_port:
                    intf.oper_status = "down"
        if node_b and node_b.hardware:
            for intf in node_b.hardware.interfaces:
                if intf.name == edge.target_port:
                    intf.oper_status = "down"

        # Update OpenConfig YANG state
        yang_store = _get_yang_store()
        if yang_store:
            try:
                if node_a:
                    yang_store.update_interface_oper_status(node_a.id, edge.source_port, "DOWN")
                    yang_store.update_bgp_session_state(node_a.id, node_b.ip_address if node_b else "*", "IDLE")
                if node_b:
                    yang_store.update_interface_oper_status(node_b.id, edge.target_port, "DOWN")
                    yang_store.update_bgp_session_state(node_b.id, node_a.ip_address if node_a else "*", "IDLE")
            except Exception:
                pass

        self._build_graph()

        return {
            "success": True,
            "edge_id": edge_id,
            "affected_nodes": [edge.source, edge.target],
            "cascades": [
                f"Physical carrier loss on {edge.source}:{edge.source_port} and {edge.target}:{edge.target_port}",
                f"OpenConfig /interfaces/interface/state/oper-status set to DOWN",
                f"SNMP IF-MIB::linkDown trap emitted for both ports",
                f"BGP neighbor adjacency transitioned from ESTABLISHED to IDLE",
                f"Graph routing table rebuilt: shortest path diverted"
            ]
        }

    def propagate_node_exhaustion(self, node_id: str, cpu_pct: float = 98.0, mem_pct: float = 94.0) -> Dict[str, Any]:
        """
        Cross-device state propagation for resource exhaustion:
        1. Pushes CPU and RAM past saturation thresholds.
        2. Triples latency on all adjacent links due to buffering delays.
        3. Updates OpenConfig platform component state.
        """
        node = self.nodes_by_id.get(node_id)
        if not node:
            return {"success": False, "error": f"Node {node_id} not found"}

        node.status = "degraded"
        if not node.hardware:
            node.hardware = NodeHardware()
        node.hardware.cpu_utilization_pct = cpu_pct
        node.hardware.memory_utilization_pct = mem_pct

        # Affect connected edges with elevated latency & jitter
        affected_edges = []
        for e in self.topology.edges:
            if e.source == node_id or e.target == node_id:
                e.latency_ms = round(e.latency_ms * 3.5, 1)
                affected_edges.append(e.id)

        yang_store = _get_yang_store()
        if yang_store:
            try:
                yang_store.update_platform_utilization(node_id, cpu_pct, mem_pct)
            except Exception:
                pass

        return {
            "success": True,
            "node_id": node_id,
            "cpu_utilization_pct": cpu_pct,
            "memory_utilization_pct": mem_pct,
            "affected_edges": affected_edges,
            "cascades": [
                f"CPU utilization spiked to {cpu_pct}%, Memory to {mem_pct}%",
                f"Transit latency tripled across {len(affected_edges)} adjacent links",
                f"OpenConfig /components/component[CPU]/state/cpu-utilization alarm triggered",
                f"PFC buffer watermark exceeded, generating queue congestion"
            ]
        }

    def restore_link(self, edge_id: str) -> Dict[str, Any]:
        edge = next((e for e in self.topology.edges if e.id == edge_id), None)
        if not edge:
            return {"success": False, "error": f"Edge {edge_id} not found"}
        edge.status = "up"
        node_a = self.nodes_by_id.get(edge.source)
        node_b = self.nodes_by_id.get(edge.target)

        if node_a and node_a.hardware:
            for intf in node_a.hardware.interfaces:
                if intf.name == edge.source_port:
                    intf.oper_status = "up"
        if node_b and node_b.hardware:
            for intf in node_b.hardware.interfaces:
                if intf.name == edge.target_port:
                    intf.oper_status = "up"

        yang_store = _get_yang_store()
        if yang_store:
            try:
                if node_a:
                    yang_store.update_interface_oper_status(node_a.id, edge.source_port, "UP")
                    yang_store.update_bgp_session_state(node_a.id, node_b.ip_address if node_b else "*", "ESTABLISHED")
                if node_b:
                    yang_store.update_interface_oper_status(node_b.id, edge.target_port, "UP")
                    yang_store.update_bgp_session_state(node_b.id, node_a.ip_address if node_a else "*", "ESTABLISHED")
            except Exception:
                pass

        self._build_graph()
        return {"success": True, "edge_id": edge_id, "status": "restored"}

    def restore_node(self, node_id: str) -> Dict[str, Any]:
        node = self.nodes_by_id.get(node_id)
        if not node:
            return {"success": False, "error": f"Node {node_id} not found"}
        node.status = "active"
        if node.hardware:
            node.hardware.cpu_utilization_pct = 18.5
            node.hardware.memory_utilization_pct = 34.0
        for e in self.topology.edges:
            if e.source == node_id or e.target == node_id:
                e.latency_ms = 1.0

        yang_store = _get_yang_store()
        if yang_store:
            try:
                yang_store.update_platform_utilization(node_id, 18.5, 34.0)
            except Exception:
                pass

        return {"success": True, "node_id": node_id, "status": "restored"}

    def degrade_link(
        self,
        edge_id: str,
        packet_loss_pct: float = 12.0,
        latency_ms: float = 150.0,
        jitter_ms: float = 35.0
    ) -> Dict[str, Any]:
        """
        Degrades link quality (brownout simulation):
        - Raises packet loss and latency without tearing down physical layer.
        - Triggers BFD degradation and SD-WAN App-Route path switching.
        """
        edge = next((e for e in self.topology.edges if e.id == edge_id), None)
        if not edge:
            return {"success": False, "error": f"Edge {edge_id} not found"}

        edge.status = "degraded"
        edge.packet_loss_pct = packet_loss_pct
        edge.latency_ms = latency_ms
        edge.jitter_ms = jitter_ms

        node_a = self.nodes_by_id.get(edge.source)
        node_b = self.nodes_by_id.get(edge.target)
        if node_a and node_a.hardware:
            for intf in node_a.hardware.interfaces:
                if intf.name == edge.source_port:
                    intf.out_errors += int(packet_loss_pct * 10)
        if node_b and node_b.hardware:
            for intf in node_b.hardware.interfaces:
                if intf.name == edge.target_port:
                    intf.in_errors += int(packet_loss_pct * 10)

        return {
            "success": True,
            "edge_id": edge_id,
            "status": "degraded",
            "packet_loss_pct": packet_loss_pct,
            "latency_ms": latency_ms,
            "jitter_ms": jitter_ms,
            "cascades": [
                f"Link {edge_id} degraded: {packet_loss_pct}% loss, {latency_ms}ms latency",
                f"SLA threshold violation detected across {edge.source} <-> {edge.target}",
                f"BFD path quality score dropped below acceptance criteria"
            ]
        }

    def restore_all(self) -> Dict[str, Any]:
        """Restores entire topology graph to clean, healthy baseline."""
        restored_edges = 0
        restored_nodes = 0
        for edge in self.topology.edges:
            edge.status = "up"
            edge.packet_loss_pct = 0.0
            edge.latency_ms = 1.0
            edge.jitter_ms = 0.0
            restored_edges += 1

        for node in self.topology.nodes:
            node.status = "active"
            if getattr(node, "power_state", None) != NodePowerState.RUNNING:
                node.power_state = NodePowerState.RUNNING
            if node.hardware:
                node.hardware.cpu_utilization_pct = 18.5
                node.hardware.memory_utilization_pct = 34.0
                for intf in node.hardware.interfaces:
                    intf.oper_status = "up"
                    intf.in_errors = 0
                    intf.out_errors = 0
            restored_nodes += 1

        self._build_graph()
        return {
            "success": True,
            "restored_nodes": restored_nodes,
            "restored_edges": restored_edges
        }

    def snapshot_state(self) -> Dict[str, Any]:
        """Captures current mutable runtime state for rollback/restoration."""
        return {
            "nodes": [
                {
                    "id": n.id,
                    "status": n.status,
                    "power_state": str(n.power_state.value if hasattr(n.power_state, "value") else n.power_state),
                    "cpu_pct": n.hardware.cpu_utilization_pct if n.hardware else 0.0,
                    "mem_pct": n.hardware.memory_utilization_pct if n.hardware else 0.0,
                    "interfaces": [
                        {
                            "name": i.name,
                            "oper_status": i.oper_status,
                            "in_errors": i.in_errors,
                            "out_errors": i.out_errors
                        }
                        for i in (n.hardware.interfaces if n.hardware else [])
                    ]
                }
                for n in self.topology.nodes
            ],
            "edges": [
                {
                    "id": e.id,
                    "status": e.status,
                    "latency_ms": e.latency_ms,
                    "packet_loss_pct": getattr(e, "packet_loss_pct", 0.0),
                    "jitter_ms": getattr(e, "jitter_ms", 0.0)
                }
                for e in self.topology.edges
            ]
        }

    def restore_snapshot(self, snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Restores exact mutable runtime state from snapshot."""
        node_map = {n["id"]: n for n in snapshot.get("nodes", [])}
        edge_map = {e["id"]: e for e in snapshot.get("edges", [])}

        for node in self.topology.nodes:
            if node.id in node_map:
                s = node_map[node.id]
                node.status = s["status"]
                if hasattr(NodePowerState, s.get("power_state", "RUNNING")):
                    node.power_state = NodePowerState(s["power_state"])
                if node.hardware:
                    node.hardware.cpu_utilization_pct = s.get("cpu_pct", 18.5)
                    node.hardware.memory_utilization_pct = s.get("mem_pct", 34.0)
                    intf_map = {i["name"]: i for i in s.get("interfaces", [])}
                    for intf in node.hardware.interfaces:
                        if intf.name in intf_map:
                            intf.oper_status = intf_map[intf.name].get("oper_status", "up")
                            intf.in_errors = intf_map[intf.name].get("in_errors", 0)
                            intf.out_errors = intf_map[intf.name].get("out_errors", 0)

        for edge in self.topology.edges:
            if edge.id in edge_map:
                s = edge_map[edge.id]
                edge.status = s["status"]
                edge.latency_ms = s.get("latency_ms", 1.0)
                edge.packet_loss_pct = s.get("packet_loss_pct", 0.0)
                edge.jitter_ms = s.get("jitter_ms", 0.0)

        self._build_graph()
        return {"success": True, "restored_from_snapshot": True}

    def find_target_nodes(
        self,
        node_types: Optional[List[NodeType]] = None,
        vendor: Optional[str] = None
    ) -> List[Node]:
        """Finds target nodes matching node types or vendor criteria."""
        results = self.topology.nodes
        if node_types:
            results = [n for n in results if n.type in node_types]
        if vendor:
            v_clean = vendor.lower()
            results = [n for n in results if v_clean in getattr(n, "vendor", "").lower() or v_clean in n.name.lower()]
        return results

    def find_target_edges(
        self,
        link_type: Optional[str] = None
    ) -> List[Edge]:
        """Finds target edges matching link type criteria."""
        if link_type:
            return [e for e in self.topology.edges if e.link_type == link_type]
        return list(self.topology.edges)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes topology graph to clean dictionary for UI/API consumption."""
        return {
            "nodes": [n.dict() if hasattr(n, "dict") else dict(n) for n in self.topology.nodes],
            "edges": [e.dict() if hasattr(e, "dict") else dict(e) for e in self.topology.edges],
            "zones": [z.dict() if hasattr(z, "dict") else dict(z) for z in getattr(self.topology, "zones", [])]
        }

