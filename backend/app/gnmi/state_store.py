"""
NetSpout Gate 13B — Shared Deterministic ScenarioStateStore.

Provides a single deterministic operational state source across:
  - Native gNMI / OpenConfig & Vendor-Native Telemetry
  - Native SNMPv2c MIB Polling & Trap/Inform Notifications
  - Syslog Control-Plane Events (LINK-3-UPDOWN, BGP-5-ADJCHANGE, RPD_BGP_NEIGHBOR_STATE_CHANGED)
  - Native NetFlow v9 / IPFIX Data-Plane Flow Summaries

Guarantees that for any (run_id, scenario_id, device_id, phase, tick, seed) tuple,
all telemetry transports observe mathematically and semantically identical state.
"""

from dataclasses import dataclass, field
import threading
import time
from typing import Any, Callable, Dict, List, Optional, Tuple

from .vendor_profiles import (
    CANONICAL_DEVICE_TARGETS,
    DeviceTargetConfig,
    VendorProfileId,
    resolve_target_device,
)

CANONICAL_PHASES = ("BASELINE", "DEGRADE", "FAILOVER", "RECOVERY")
PHASE_ALIASES = {
    "BASELINE": "BASELINE",
    "NORMAL": "BASELINE",
    "DEGRADE": "DEGRADE",
    "FAULT": "DEGRADE",
    "PROPAGATE": "DEGRADE",
    "FAILOVER": "FAILOVER",
    "MITIGATE": "FAILOVER",
    "RECOVERY": "RECOVERY",
    "RECOVER": "RECOVERY",
    "VALIDATE": "RECOVERY",
}


def normalize_phase(phase: str) -> str:
    norm = (phase or "BASELINE").strip().upper()
    if norm not in PHASE_ALIASES:
        raise ValueError(
            f"Unsupported scenario phase {phase!r}; expected one of {CANONICAL_PHASES}"
        )
    return PHASE_ALIASES[norm]


@dataclass(frozen=True)
class InterfaceCountersSnapshot:
    in_octets: int
    out_octets: int
    in_unicast_pkts: int
    out_unicast_pkts: int
    in_errors: int
    out_errors: int
    in_fcs_errors: int
    in_discards: int
    out_discards: int
    carrier_transitions: int


@dataclass(frozen=True)
class InterfaceSnapshot:
    name: str
    if_index: int
    description: str
    admin_status: str  # "UP" | "DOWN"
    oper_status: str   # "UP" | "DOWN"
    snmp_admin_status: int  # 1=up, 2=down
    snmp_oper_status: int   # 1=up, 2=down
    mtu: int
    high_speed_mbps: int
    ipv4_address: str
    ipv4_prefix_length: int
    counters: InterfaceCountersSnapshot


@dataclass(frozen=True)
class BgpNeighborSnapshot:
    neighbor_address: str
    peer_as: int
    description: str
    session_state: str  # "ESTABLISHED" | "IDLE" | "ACTIVE"
    snmp_peer_state: int  # 6=established, 1=idle, 3=active
    established_transitions: int
    last_established: int
    prefixes_received: int
    prefixes_installed: int
    prefixes_sent: int
    messages_sent_update: int
    messages_received_update: int


@dataclass(frozen=True)
class LldpNeighborSnapshot:
    local_interface: str
    neighbor_id: str
    system_name: str
    port_id: str
    port_description: str
    management_address: str


@dataclass(frozen=True)
class LacpMemberSnapshot:
    lag_interface: str
    member_interface: str
    aggregatable: bool
    collecting: bool
    distributing: bool
    activity: str  # "ACTIVE" | "PASSIVE"
    oper_key: int
    partner_id: str


@dataclass(frozen=True)
class QosQueueSnapshot:
    interface_id: str
    queue_name: str
    transmit_pkts: int
    transmit_octets: int
    dropped_pkts: int
    dropped_octets: int
    max_queue_len: int


@dataclass(frozen=True)
class PlatformComponentSnapshot:
    name: str
    component_type: str
    oper_status: str
    temperature_instant: float
    used_power_watts: int


@dataclass(frozen=True)
class OpticsSnapshot:
    component_name: str
    interface_name: str
    rx_power_dbm: float
    tx_power_dbm: float
    laser_bias_ma: float
    pre_fec_ber: float
    osnr_db: float


@dataclass(frozen=True)
class SystemSnapshot:
    hostname: str
    domain_name: str
    boot_time_ns: int
    current_datetime: str
    sys_uptime_centisec: int
    cpu_total_pct: int
    cpu_user_pct: int
    cpu_kernel_pct: int
    memory_physical_bytes: int
    memory_reserved_bytes: int


@dataclass(frozen=True)
class AftEntrySnapshot:
    prefix: str
    next_hop_group: int
    next_hop_ip: str
    egress_interface: str
    ecmp_paths: int
    packets_forwarded: int
    octets_forwarded: int
    route_metric: int


@dataclass(frozen=True)
class EvpnVxlanSnapshot:
    supported: bool
    vtep_status: str
    vni_id: int
    type2_mac_ip_routes: int
    type5_ip_prefix_routes: int


@dataclass(frozen=True)
class DeviceStateSnapshot:
    run_id: str
    scenario_id: str
    device_id: str
    hostname: str
    vendor_profile: VendorProfileId
    phase: str
    tick: int
    seed: int
    timestamp_ns: int
    interfaces: Dict[str, InterfaceSnapshot]
    bgp_neighbors: Dict[str, BgpNeighborSnapshot]
    lldp_neighbors: Tuple[LldpNeighborSnapshot, ...]
    lacp_members: Tuple[LacpMemberSnapshot, ...]
    qos_queues: Dict[str, QosQueueSnapshot]
    platform_components: Dict[str, PlatformComponentSnapshot]
    optics: Dict[str, OpticsSnapshot]
    system: SystemSnapshot
    aft_entries: Dict[str, AftEntrySnapshot]
    evpn: EvpnVxlanSnapshot

    def to_syslog_events(self) -> List[Dict[str, Any]]:
        """Projects phase state transitions into vendor-authentic Syslog messages."""
        events: List[Dict[str, Any]] = []
        primary_if = next(iter(self.interfaces.values()))
        primary_bgp = next(iter(self.bgp_neighbors.values()))

        if self.phase in ("DEGRADE", "FAILOVER"):
            if self.vendor_profile == VendorProfileId.JUNIPER_JUNOS:
                events.append({
                    "device_id": self.device_id,
                    "phase": self.phase,
                    "mnemonic": "SNMP_TRAP_LINK_DOWN",
                    "interface": primary_if.name,
                    "oper_status": primary_if.oper_status,
                    "message": f"SNMP_TRAP_LINK_DOWN: ifIndex {primary_if.if_index}, ifAdminStatus up(1), ifOperStatus down(2), ifName {primary_if.name}",
                })
                events.append({
                    "device_id": self.device_id,
                    "phase": self.phase,
                    "mnemonic": "RPD_BGP_NEIGHBOR_STATE_CHANGED",
                    "neighbor": primary_bgp.neighbor_address,
                    "session_state": primary_bgp.session_state,
                    "message": f"RPD_BGP_NEIGHBOR_STATE_CHANGED: BGP peer {primary_bgp.neighbor_address} (External AS {primary_bgp.peer_as}) changed state from Established to Idle",
                })
            else:
                events.append({
                    "device_id": self.device_id,
                    "phase": self.phase,
                    "mnemonic": "LINK-3-UPDOWN",
                    "interface": primary_if.name,
                    "oper_status": primary_if.oper_status,
                    "message": f"%LINK-3-UPDOWN: Interface {primary_if.name}, changed state to down",
                })
                events.append({
                    "device_id": self.device_id,
                    "phase": self.phase,
                    "mnemonic": "BGP-5-ADJCHANGE",
                    "neighbor": primary_bgp.neighbor_address,
                    "session_state": primary_bgp.session_state,
                    "message": f"%BGP-5-ADJCHANGE: neighbor {primary_bgp.neighbor_address} Down Hold Timer Expired",
                })
        else:
            events.append({
                "device_id": self.device_id,
                "phase": self.phase,
                "mnemonic": "LINK-3-UPDOWN",
                "interface": primary_if.name,
                "oper_status": primary_if.oper_status,
                "message": f"%LINK-3-UPDOWN: Interface {primary_if.name}, changed state to up",
            })
            events.append({
                "device_id": self.device_id,
                "phase": self.phase,
                "mnemonic": "BGP-5-ADJCHANGE",
                "neighbor": primary_bgp.neighbor_address,
                "session_state": primary_bgp.session_state,
                "message": f"%BGP-5-ADJCHANGE: neighbor {primary_bgp.neighbor_address} Up",
            })
        return events

    def to_snmp_coherence_summary(self) -> Dict[str, Any]:
        """Returns the exact SNMP IF-MIB and BGP4-MIB OID values matching this snapshot."""
        primary_if = next(iter(self.interfaces.values()))
        primary_bgp = next(iter(self.bgp_neighbors.values()))
        return {
            "sysUpTime.0": self.system.sys_uptime_centisec,
            "ifAdminStatus.1": primary_if.snmp_admin_status,
            "ifOperStatus.1": primary_if.snmp_oper_status,
            "ifHCInOctets.1": primary_if.counters.in_octets,
            "ifHCOutOctets.1": primary_if.counters.out_octets,
            "ifHCInUcastPkts.1": primary_if.counters.in_unicast_pkts,
            "ifHCOutUcastPkts.1": primary_if.counters.out_unicast_pkts,
            "ifInErrors.1": primary_if.counters.in_errors,
            "ifOutErrors.1": primary_if.counters.out_errors,
            "bgpPeerState": primary_bgp.snmp_peer_state,
        }

    def to_netflow_coherence_summary(self) -> Dict[str, Any]:
        """Returns NetFlow v9 / IPFIX flow volume coherent with the primary/active interface counters."""
        primary_if = next(iter(self.interfaces.values()))
        aft_default = self.aft_entries["0.0.0.0/0"]
        return {
            "exporter_device_id": self.device_id,
            "phase": self.phase,
            "input_snmp": primary_if.if_index,
            "in_bytes_total": primary_if.counters.in_octets,
            "in_pkts_total": primary_if.counters.in_unicast_pkts,
            "out_bytes_total": primary_if.counters.out_octets,
            "out_pkts_total": primary_if.counters.out_unicast_pkts,
            "active_next_hop": aft_default.next_hop_ip,
            "forwarded_packets": aft_default.packets_forwarded,
            "forwarded_octets": aft_default.octets_forwarded,
        }


class ScenarioStateStore:
    """
    Thread-safe shared scenario state store driving gNMI, SNMP, Syslog, and NetFlow/IPFIX.
    Supports deterministic snapshot generation and phase transition listeners for ON_CHANGE streams.
    """

    BASE_EPOCH_NS = 1_727_640_000_000_000_000  # Deterministic base timestamp in ns

    def __init__(
        self,
        run_id: str = "NS-GATE13B-RUN",
        scenario_id: str = "openconfig_mdt_streaming",
        seed: int = 42,
        initial_phase: str = "BASELINE",
    ):
        self._lock = threading.RLock()
        self.run_id = run_id
        self.scenario_id = scenario_id
        self.seed = int(seed)
        self._phase = normalize_phase(initial_phase)
        self._tick = 0
        self._listeners: List[Callable[[str, int], None]] = []

    @property
    def phase(self) -> str:
        with self._lock:
            return self._phase

    @property
    def tick(self) -> int:
        with self._lock:
            return self._tick

    def register_listener(self, callback: Callable[[str, int], None]) -> None:
        with self._lock:
            if callback not in self._listeners:
                self._listeners.append(callback)

    def unregister_listener(self, callback: Callable[[str, int], None]) -> None:
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)

    def set_phase(self, new_phase: str, advance_tick: bool = True) -> Tuple[str, int]:
        norm = normalize_phase(new_phase)
        with self._lock:
            self._phase = norm
            if advance_tick:
                self._tick += 1
            current_phase = self._phase
            current_tick = self._tick
            listeners = list(self._listeners)

        for cb in listeners:
            try:
                cb(current_phase, current_tick)
            except Exception:
                pass
        return current_phase, current_tick

    def advance_tick(self, delta: int = 1) -> int:
        with self._lock:
            self._tick += max(1, int(delta))
            return self._tick

    def get_snapshot(
        self,
        device_id: str,
        phase: Optional[str] = None,
        tick: Optional[int] = None,
        seed: Optional[int] = None,
    ) -> DeviceStateSnapshot:
        with self._lock:
            eff_phase = normalize_phase(phase if phase is not None else self._phase)
            eff_tick = int(tick if tick is not None else self._tick)
            eff_seed = int(seed if seed is not None else self.seed)

        target_cfg = resolve_target_device(device_id)
        if target_cfg is None:
            raise KeyError(f"Unknown target device: {device_id}")

        return self._build_snapshot(target_cfg, eff_phase, eff_tick, eff_seed)

    def _build_snapshot(
        self,
        cfg: DeviceTargetConfig,
        phase: str,
        tick: int,
        seed: int,
    ) -> DeviceStateSnapshot:
        seed_offset = (abs(int(seed)) % 997) * 100
        tick_step = max(0, int(tick))

        # Exact phase coherence with Gate 12C/12D/12F build_service_provider_cisco_oid_store
        if phase == "BASELINE":
            sys_uptime = 8639000 + (tick_step * 100)
            if1_oper_str, if1_oper_snmp = "UP", 1
            if1_hc_in = 98500000000 + (seed_offset * 1000) + (tick_step * 12500000)
            if1_hc_out = 91200000000 + (seed_offset * 1000) + (tick_step * 11800000)
            if1_pkts_in = 950000 + seed_offset + (tick_step * 9500)
            if1_pkts_out = 910000 + seed_offset + (tick_step * 9100)
            if1_in_err = 0
            if1_out_err = 0
            if1_fcs_err = 0
            if1_discards = 0
            if1_transitions = 1

            if2_hc_in = 4200000000 + (seed_offset * 100) + (tick_step * 1500000)
            if2_hc_out = 4100000000 + (seed_offset * 100) + (tick_step * 1400000)
            if2_pkts_in = 120000 + seed_offset + (tick_step * 1200)
            if2_pkts_out = 115000 + seed_offset + (tick_step * 1150)

            peer1_state_str, peer1_state_snmp = "ESTABLISHED", 6
            peer1_transitions = 1
            peer1_prefixes_rx = 1420 + (seed % 50)
            peer1_prefixes_inst = 1420 + (seed % 50)
            peer1_prefixes_tx = 850 + (seed % 30)
            peer1_updates_tx = 1380 + (seed % 50) + (tick_step * 2)
            peer1_updates_rx = 1420 + (seed % 50) + (tick_step * 2)

            q_drop_pkts = 0
            q_drop_octets = 0
            q_max_len = 64000
            cpu_total, cpu_user, cpu_kernel = 18, 12, 6
            mem_reserved = 6_871_947_673  # ~6.4 GB of 32 GB
            temp_c = 41.2
            rx_dbm, tx_dbm, bias_ma, ber, osnr = -6.2, 1.4, 38.5, 1.0e-9, 28.5
            active_nh_ip = cfg.bgp_neighbors[0][0]
            active_nh_group = 100
            ecmp_paths = 2
            route_metric = 10

        elif phase == "DEGRADE":
            sys_uptime = 8640000 + (tick_step * 100)
            if1_oper_str, if1_oper_snmp = "DOWN", 2
            if1_hc_in = 98650000000 + (seed_offset * 1000) + (tick_step * 500000)
            if1_hc_out = 91320000000 + (seed_offset * 1000) + (tick_step * 450000)
            if1_pkts_in = 962000 + seed_offset + (tick_step * 400)
            if1_pkts_out = 921000 + seed_offset + (tick_step * 380)
            if1_in_err = 485 + (seed % 25) + (tick_step * 12)
            if1_out_err = 19 + (seed % 7) + (tick_step * 2)
            if1_fcs_err = 312 + (seed % 15) + (tick_step * 8)
            if1_discards = 4820 + (tick_step * 150)
            if1_transitions = 2

            if2_hc_in = 6800000000 + (seed_offset * 100) + (tick_step * 8500000)
            if2_hc_out = 6600000000 + (seed_offset * 100) + (tick_step * 8100000)
            if2_pkts_in = 230000 + seed_offset + (tick_step * 6800)
            if2_pkts_out = 220000 + seed_offset + (tick_step * 6500)

            peer1_state_str, peer1_state_snmp = "IDLE", 1
            peer1_transitions = 2
            peer1_prefixes_rx = 0
            peer1_prefixes_inst = 0
            peer1_prefixes_tx = 0
            peer1_updates_tx = 1385 + (seed % 50)
            peer1_updates_rx = 1425 + (seed % 50)

            q_drop_pkts = 4820 + (tick_step * 150)
            q_drop_octets = q_drop_pkts * 1024
            q_max_len = 14850000
            cpu_total, cpu_user, cpu_kernel = 88, 64, 24
            mem_reserved = 21_474_836_480  # 20 GB
            temp_c = 63.8
            rx_dbm, tx_dbm, bias_ma, ber, osnr = -24.8, -4.1, 68.2, 1.4e-3, 11.2
            active_nh_ip = cfg.bgp_neighbors[-1][0]
            active_nh_group = 200
            ecmp_paths = 1
            route_metric = 20

        elif phase == "FAILOVER":
            sys_uptime = 8640500 + (tick_step * 100)
            if1_oper_str, if1_oper_snmp = "DOWN", 2
            if1_hc_in = 98650000000 + (seed_offset * 1000)
            if1_hc_out = 91320000000 + (seed_offset * 1000)
            if1_pkts_in = 962000 + seed_offset
            if1_pkts_out = 921000 + seed_offset
            if1_in_err = 485 + (seed % 25)
            if1_out_err = 19 + (seed % 7)
            if1_fcs_err = 312 + (seed % 15)
            if1_discards = 4820
            if1_transitions = 2

            if2_hc_in = 42800000000 + (seed_offset * 1000) + (tick_step * 14000000)
            if2_hc_out = 40600000000 + (seed_offset * 1000) + (tick_step * 13200000)
            if2_pkts_in = 780000 + seed_offset + (tick_step * 11000)
            if2_pkts_out = 755000 + seed_offset + (tick_step * 10500)

            peer1_state_str, peer1_state_snmp = "IDLE", 1
            peer1_transitions = 2
            peer1_prefixes_rx = 0
            peer1_prefixes_inst = 0
            peer1_prefixes_tx = 0
            peer1_updates_tx = 1385 + (seed % 50)
            peer1_updates_rx = 1425 + (seed % 50)

            q_drop_pkts = 4820
            q_drop_octets = q_drop_pkts * 1024
            q_max_len = 420000
            cpu_total, cpu_user, cpu_kernel = 46, 32, 14
            mem_reserved = 11_811_160_064  # 11 GB
            temp_c = 49.5
            rx_dbm, tx_dbm, bias_ma, ber, osnr = -25.1, -4.2, 69.0, 1.8e-3, 10.8
            active_nh_ip = cfg.bgp_neighbors[-1][0]
            active_nh_group = 200
            ecmp_paths = 1
            route_metric = 20

        else:  # RECOVERY
            sys_uptime = 8643500 + (tick_step * 100)
            if1_oper_str, if1_oper_snmp = "UP", 1
            if1_hc_in = 124500000000 + (seed_offset * 1000) + (tick_step * 12500000)
            if1_hc_out = 116800000000 + (seed_offset * 1000) + (tick_step * 11800000)
            if1_pkts_in = 1290000 + seed_offset + (tick_step * 9500)
            if1_pkts_out = 1240000 + seed_offset + (tick_step * 9100)
            if1_in_err = 485 + (seed % 25)
            if1_out_err = 19 + (seed % 7)
            if1_fcs_err = 312 + (seed % 15)
            if1_discards = 4820
            if1_transitions = 3

            if2_hc_in = 46500000000 + (seed_offset * 1000) + (tick_step * 2000000)
            if2_hc_out = 44100000000 + (seed_offset * 1000) + (tick_step * 1900000)
            if2_pkts_in = 840000 + seed_offset + (tick_step * 1500)
            if2_pkts_out = 810000 + seed_offset + (tick_step * 1400)

            peer1_state_str, peer1_state_snmp = "ESTABLISHED", 6
            peer1_transitions = 3
            peer1_prefixes_rx = 1420 + (seed % 50)
            peer1_prefixes_inst = 1420 + (seed % 50)
            peer1_prefixes_tx = 850 + (seed % 30)
            peer1_updates_tx = 1920 + (seed % 50) + (tick_step * 2)
            peer1_updates_rx = 1980 + (seed % 50) + (tick_step * 2)

            q_drop_pkts = 4820
            q_drop_octets = q_drop_pkts * 1024
            q_max_len = 68000
            cpu_total, cpu_user, cpu_kernel = 21, 14, 7
            mem_reserved = 7_516_192_768  # 7 GB
            temp_c = 42.0
            rx_dbm, tx_dbm, bias_ma, ber, osnr = -6.1, 1.5, 38.2, 1.0e-9, 28.6
            active_nh_ip = cfg.bgp_neighbors[0][0]
            active_nh_group = 100
            ecmp_paths = 2
            route_metric = 10

        timestamp_ns = self.BASE_EPOCH_NS + (sys_uptime * 10_000_000)

        # Build Interface Snapshots
        interfaces: Dict[str, InterfaceSnapshot] = {}
        for idx, if_name in enumerate(cfg.interfaces, start=1):
            if idx == 1:
                cnt = InterfaceCountersSnapshot(
                    in_octets=if1_hc_in,
                    out_octets=if1_hc_out,
                    in_unicast_pkts=if1_pkts_in,
                    out_unicast_pkts=if1_pkts_out,
                    in_errors=if1_in_err,
                    out_errors=if1_out_err,
                    in_fcs_errors=if1_fcs_err,
                    in_discards=if1_discards,
                    out_discards=if1_discards // 2,
                    carrier_transitions=if1_transitions,
                )
                oper_s, oper_i = if1_oper_str, if1_oper_snmp
                speed = 100000
            else:
                scale = idx
                cnt = InterfaceCountersSnapshot(
                    in_octets=if2_hc_in * scale,
                    out_octets=if2_hc_out * scale,
                    in_unicast_pkts=if2_pkts_in * scale,
                    out_unicast_pkts=if2_pkts_out * scale,
                    in_errors=0,
                    out_errors=0,
                    in_fcs_errors=0,
                    in_discards=0,
                    out_discards=0,
                    carrier_transitions=1,
                )
                oper_s, oper_i = "UP", 1
                speed = 40000 if "Forty" in if_name else 10000

            interfaces[if_name] = InterfaceSnapshot(
                name=if_name,
                if_index=idx,
                description=f"{cfg.hostname} {if_name} Core Link",
                admin_status="UP",
                oper_status=oper_s,
                snmp_admin_status=1,
                snmp_oper_status=oper_i,
                mtu=9192 if idx <= 2 else 1500,
                high_speed_mbps=speed,
                ipv4_address=f"10.100.{idx}.{cfg.mgmt_ip.split('.')[-1]}",
                ipv4_prefix_length=30,
                counters=cnt,
            )

        # Build BGP Neighbor Snapshots
        bgp_neighbors: Dict[str, BgpNeighborSnapshot] = {}
        for idx, (peer_ip, peer_as, desc) in enumerate(cfg.bgp_neighbors):
            if idx == 0:
                bgp_neighbors[peer_ip] = BgpNeighborSnapshot(
                    neighbor_address=peer_ip,
                    peer_as=peer_as,
                    description=desc,
                    session_state=peer1_state_str,
                    snmp_peer_state=peer1_state_snmp,
                    established_transitions=peer1_transitions,
                    last_established=timestamp_ns - 60_000_000_000,
                    prefixes_received=peer1_prefixes_rx,
                    prefixes_installed=peer1_prefixes_inst,
                    prefixes_sent=peer1_prefixes_tx,
                    messages_sent_update=peer1_updates_tx,
                    messages_received_update=peer1_updates_rx,
                )
            else:
                bgp_neighbors[peer_ip] = BgpNeighborSnapshot(
                    neighbor_address=peer_ip,
                    peer_as=peer_as,
                    description=desc,
                    session_state="ESTABLISHED",
                    snmp_peer_state=6,
                    established_transitions=1,
                    last_established=timestamp_ns - 86400_000_000_000,
                    prefixes_received=1420 + (seed % 50),
                    prefixes_installed=1420 + (seed % 50),
                    prefixes_sent=850 + (seed % 30),
                    messages_sent_update=940 + (tick_step * 2),
                    messages_received_update=980 + (tick_step * 2),
                )

        # Build LLDP Neighbors
        lldp_list: List[LldpNeighborSnapshot] = []
        for idx, (loc_if, rem_sys, rem_port, rem_ip) in enumerate(cfg.lldp_neighbors, start=1):
            lldp_list.append(
                LldpNeighborSnapshot(
                    local_interface=loc_if,
                    neighbor_id=f"nbr-{idx}",
                    system_name=rem_sys,
                    port_id=rem_port,
                    port_description=f"Link to {rem_sys} ({rem_port})",
                    management_address=rem_ip,
                )
            )

        # Build LACP Members
        lacp_members = (
            LacpMemberSnapshot(
                lag_interface=cfg.lag_interface,
                member_interface=cfg.primary_uplink,
                aggregatable=True,
                collecting=(if1_oper_str == "UP"),
                distributing=(if1_oper_str == "UP"),
                activity="ACTIVE",
                oper_key=10,
                partner_id="00:1c:73:aa:bb:cc",
            ),
        )

        # Build QoS Queues
        qos_queues: Dict[str, QosQueueSnapshot] = {}
        for if_name, intf in interfaces.items():
            key = f"{if_name}:BE-0"
            qos_queues[key] = QosQueueSnapshot(
                interface_id=if_name,
                queue_name="BE-0",
                transmit_pkts=intf.counters.out_unicast_pkts,
                transmit_octets=intf.counters.out_octets,
                dropped_pkts=q_drop_pkts if if_name == cfg.primary_uplink else 0,
                dropped_octets=q_drop_octets if if_name == cfg.primary_uplink else 0,
                max_queue_len=q_max_len if if_name == cfg.primary_uplink else 32000,
            )

        # Build Platform Components & Optics
        platform_components = {
            "Chassis-0": PlatformComponentSnapshot(
                name="Chassis-0",
                component_type="CHASSIS",
                oper_status="ACTIVE",
                temperature_instant=temp_c,
                used_power_watts=840 if phase != "DEGRADE" else 1120,
            ),
            "Linecard0": PlatformComponentSnapshot(
                name="Linecard0",
                component_type="LINECARD",
                oper_status="ACTIVE",
                temperature_instant=temp_c + 4.5,
                used_power_watts=420,
            ),
            f"Transceiver-{cfg.primary_uplink}": PlatformComponentSnapshot(
                name=f"Transceiver-{cfg.primary_uplink}",
                component_type="TRANSCEIVER",
                oper_status="ACTIVE" if if1_oper_str == "UP" else "DEGRADED",
                temperature_instant=temp_c + 6.0,
                used_power_watts=18,
            ),
        }

        optics = {
            cfg.primary_uplink: OpticsSnapshot(
                component_name=f"Transceiver-{cfg.primary_uplink}",
                interface_name=cfg.primary_uplink,
                rx_power_dbm=rx_dbm,
                tx_power_dbm=tx_dbm,
                laser_bias_ma=bias_ma,
                pre_fec_ber=ber,
                osnr_db=osnr,
            )
        }

        # System Snapshot
        system = SystemSnapshot(
            hostname=cfg.hostname,
            domain_name="netspout.lab.internal",
            boot_time_ns=self.BASE_EPOCH_NS - 86_400_000_000_000,
            current_datetime="2026-09-29T18:00:00Z",
            sys_uptime_centisec=sys_uptime,
            cpu_total_pct=cpu_total,
            cpu_user_pct=cpu_user,
            cpu_kernel_pct=cpu_kernel,
            memory_physical_bytes=34_359_738_368,  # 32 GiB
            memory_reserved_bytes=mem_reserved,
        )

        # AFT / Routing Snapshot
        egress_if = cfg.primary_uplink if if1_oper_str == "UP" else cfg.interfaces[min(1, len(cfg.interfaces) - 1)]
        aft_entries = {
            "0.0.0.0/0": AftEntrySnapshot(
                prefix="0.0.0.0/0",
                next_hop_group=active_nh_group,
                next_hop_ip=active_nh_ip,
                egress_interface=egress_if,
                ecmp_paths=ecmp_paths,
                packets_forwarded=if1_pkts_in + if2_pkts_in,
                octets_forwarded=if1_hc_in + if2_hc_in,
                route_metric=route_metric,
            ),
            "10.100.0.0/16": AftEntrySnapshot(
                prefix="10.100.0.0/16",
                next_hop_group=active_nh_group + 1,
                next_hop_ip=active_nh_ip,
                egress_interface=egress_if,
                ecmp_paths=ecmp_paths,
                packets_forwarded=if1_pkts_in,
                octets_forwarded=if1_hc_in,
                route_metric=route_metric,
            ),
        }

        evpn = EvpnVxlanSnapshot(
            supported=cfg.evpn_supported,
            vtep_status="UP" if cfg.evpn_supported and phase != "DEGRADE" else ("DEGRADED" if cfg.evpn_supported else "NOT_SUPPORTED"),
            vni_id=10100 if cfg.evpn_supported else 0,
            type2_mac_ip_routes=480 if cfg.evpn_supported else 0,
            type5_ip_prefix_routes=120 if cfg.evpn_supported else 0,
        )

        return DeviceStateSnapshot(
            run_id=self.run_id,
            scenario_id=self.scenario_id,
            device_id=cfg.device_id,
            hostname=cfg.hostname,
            vendor_profile=cfg.vendor_profile,
            phase=phase,
            tick=tick_step,
            seed=seed,
            timestamp_ns=timestamp_ns,
            interfaces=interfaces,
            bgp_neighbors=bgp_neighbors,
            lldp_neighbors=tuple(lldp_list),
            lacp_members=lacp_members,
            qos_queues=qos_queues,
            platform_components=platform_components,
            optics=optics,
            system=system,
            aft_entries=aft_entries,
            evpn=evpn,
        )
