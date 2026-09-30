"""
NetSpout Gate 13B — Centralized Telemetry Sensor Registry & Multi-Vendor Extractor Engine.

Implements explicit sensor definitions with:
  - sensor_id, vendor_profile, origin, path, telemetry_domain
  - encoding_support, subscription_support
  - fidelity_classification (VERIFIED | MODELED | NOT_SUPPORTED)
  - state_source, units, description, yang_module

Enforces strict vendor origin isolation and never silently transforms NOT_SUPPORTED into MODELED.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from .path_parser import ParsedGnmiPath, ParsedPathElem, parse_xpath_string
from .state_store import DeviceStateSnapshot
from .vendor_profiles import VendorProfileId, get_vendor_profile


class GnmiOriginNotSupportedError(PermissionError):
    """Raised when a client queries an origin not supported by the target vendor profile."""


GnmiForeignOriginError = GnmiOriginNotSupportedError


class GnmiPathNotFoundError(KeyError):
    """Raised when a requested gNMI path or key does not exist or is NOT_SUPPORTED."""


@dataclass(frozen=True)
class SensorDefinition:
    sensor_id: str
    vendor_profile: str  # "ALL" or VendorProfileId value
    origin: str
    path: str
    telemetry_domain: str
    yang_module: str
    encoding_support: Tuple[str, ...]
    subscription_support: Tuple[str, ...]
    fidelity_classification: str  # "VERIFIED" | "MODELED" | "NOT_SUPPORTED"
    state_source: str
    units: str
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sensor_id": self.sensor_id,
            "vendor_profile": self.vendor_profile,
            "origin": self.origin,
            "path": self.path,
            "telemetry_domain": self.telemetry_domain,
            "yang_module": self.yang_module,
            "encoding_support": list(self.encoding_support),
            "subscription_support": list(self.subscription_support),
            "fidelity_classification": self.fidelity_classification,
            "state_source": self.state_source,
            "units": self.units,
            "description": self.description,
        }


@dataclass(frozen=True)
class ResolvedSensorSample:
    sensor_id: str
    concrete_path: ParsedGnmiPath
    payload: Any
    yang_module: str
    leaf_yang_type: str = ""


# =========================================================================
# Canonical Sensor Definitions (OpenConfig + 4 Vendor-Native Profiles)
# =========================================================================
CANONICAL_SENSORS: Tuple[SensorDefinition, ...] = (
    # --- 1. OpenConfig Universal Sensors (origin="openconfig") ---
    SensorDefinition(
        sensor_id="oc_if_state",
        vendor_profile="ALL",
        origin="openconfig",
        path="/interfaces/interface[name=*]/state",
        telemetry_domain="interfaces",
        yang_module="openconfig-interfaces",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE", "ON_CHANGE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.interfaces[*]",
        units="state/counters",
        description="OpenConfig interface operational state, admin status, MTU, speed, and counters.",
    ),
    SensorDefinition(
        sensor_id="oc_if_counters",
        vendor_profile="ALL",
        origin="openconfig",
        path="/interfaces/interface[name=*]/state/counters",
        telemetry_domain="interfaces",
        yang_module="openconfig-interfaces",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.interfaces[*].counters",
        units="bytes/packets/transitions",
        description="OpenConfig 64-bit interface packet, octet, error, discard, and transition counters.",
    ),
    SensorDefinition(
        sensor_id="oc_subif_ipv4",
        vendor_profile="ALL",
        origin="openconfig",
        path="/interfaces/interface[name=*]/subinterfaces/subinterface[index=*]/ipv4/addresses/address[ip=*]/state",
        telemetry_domain="subinterfaces",
        yang_module="openconfig-if-ip",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "ON_CHANGE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.interfaces[*].ipv4_address",
        units="ipv4-prefix",
        description="OpenConfig subinterface IPv4 address and prefix-length state.",
    ),
    SensorDefinition(
        sensor_id="oc_lldp_nbr",
        vendor_profile="ALL",
        origin="openconfig",
        path="/lldp/interfaces/interface[name=*]/neighbors/neighbor[id=*]/state",
        telemetry_domain="lldp",
        yang_module="openconfig-lldp",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE", "ON_CHANGE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.lldp_neighbors[*]",
        units="adjacency",
        description="OpenConfig LLDP neighbor discovery state (system-name, port-id, management-address).",
    ),
    SensorDefinition(
        sensor_id="oc_lacp_mbr",
        vendor_profile="ALL",
        origin="openconfig",
        path="/lacp/interfaces/interface[name=*]/members/member[interface=*]/state",
        telemetry_domain="lacp",
        yang_module="openconfig-lacp",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE", "ON_CHANGE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.lacp_members[*]",
        units="bundle-state",
        description="OpenConfig LACP LAG member collecting, distributing, activity, and oper-key state.",
    ),
    SensorDefinition(
        sensor_id="oc_bgp_nbr",
        vendor_profile="ALL",
        origin="openconfig",
        path="/network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=*]/bgp/neighbors/neighbor[neighbor-address=*]/state",
        telemetry_domain="bgp",
        yang_module="openconfig-bgp",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE", "ON_CHANGE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.bgp_neighbors[*]",
        units="session/prefixes/messages",
        description="OpenConfig BGP neighbor session-state, transitions, prefixes, and update messages.",
    ),
    SensorDefinition(
        sensor_id="oc_bgp_afi",
        vendor_profile="ALL",
        origin="openconfig",
        path="/network-instances/network-instance[name=*]/protocols/protocol[identifier=BGP][name=*]/bgp/neighbors/neighbor[neighbor-address=*]/afi-safis/afi-safi[afi-safi-name=*]/state/prefixes",
        telemetry_domain="bgp",
        yang_module="openconfig-bgp",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE", "ON_CHANGE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.bgp_neighbors[*].prefixes",
        units="prefixes",
        description="OpenConfig BGP per-AFI/SAFI received, installed, and sent prefix counters.",
    ),
    SensorDefinition(
        sensor_id="oc_aft_ipv4",
        vendor_profile="ALL",
        origin="openconfig",
        path="/network-instances/network-instance[name=*]/afts/ipv4-unicast/ipv4-entries/ipv4-entry[prefix=*]/state",
        telemetry_domain="routing_aft",
        yang_module="openconfig-aft",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE", "ON_CHANGE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.aft_entries[*]",
        units="routes/packets/octets",
        description="OpenConfig Abstract Forwarding Table (AFT) IPv4 unicast next-hop group and forwarding counters.",
    ),
    SensorDefinition(
        sensor_id="oc_qos_queue",
        vendor_profile="ALL",
        origin="openconfig",
        path="/qos/interfaces/interface[interface-id=*]/output/queues/queue[name=*]/state",
        telemetry_domain="qos",
        yang_module="openconfig-qos",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.qos_queues[*]",
        units="packets/bytes",
        description="OpenConfig QoS egress queue transmit packets/octets, tail-drops, and max queue depth.",
    ),
    SensorDefinition(
        sensor_id="oc_platform_comp",
        vendor_profile="ALL",
        origin="openconfig",
        path="/components/component[name=*]/state",
        telemetry_domain="platform",
        yang_module="openconfig-platform",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE", "ON_CHANGE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.platform_components[*]",
        units="celsius/watts",
        description="OpenConfig platform component operational status, temperature, and power draw.",
    ),
    SensorDefinition(
        sensor_id="oc_platform_optics",
        vendor_profile="ALL",
        origin="openconfig",
        path="/components/component[name=*]/transceiver/state",
        telemetry_domain="optics",
        yang_module="openconfig-platform-transceiver",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.optics[*]",
        units="dBm/mA",
        description="OpenConfig optical transceiver Rx/Tx optical power (dBm) and laser bias current (mA).",
    ),
    SensorDefinition(
        sensor_id="oc_system_state",
        vendor_profile="ALL",
        origin="openconfig",
        path="/system/state",
        telemetry_domain="system",
        yang_module="openconfig-system",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE", "ON_CHANGE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.system",
        units="ns/string",
        description="OpenConfig system hostname, domain-name, boot-time, and current-datetime.",
    ),
    SensorDefinition(
        sensor_id="oc_system_cpu",
        vendor_profile="ALL",
        origin="openconfig",
        path="/system/cpus/cpu[index=*]/state",
        telemetry_domain="system",
        yang_module="openconfig-system",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.system.cpu",
        units="percent",
        description="OpenConfig system CPU utilization (total, user, kernel percentages).",
    ),
    SensorDefinition(
        sensor_id="oc_system_memory",
        vendor_profile="ALL",
        origin="openconfig",
        path="/system/memory/state",
        telemetry_domain="system",
        yang_module="openconfig-system",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.system.memory",
        units="bytes",
        description="OpenConfig system physical and reserved memory counters in bytes.",
    ),
    SensorDefinition(
        sensor_id="oc_evpn_vxlan",
        vendor_profile="ARISTA_EOS",
        origin="openconfig",
        path="/network-instances/network-instance[name=*]/evpn/state",
        telemetry_domain="evpn_vxlan",
        yang_module="openconfig-evpn",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE", "ON_CHANGE"),
        fidelity_classification="MODELED",
        state_source="DeviceStateSnapshot.evpn",
        units="routes",
        description="Modeled EVPN VXLAN state on EVPN-capable spine/leaf nodes (NOT_SUPPORTED on pure L3 nodes).",
    ),

    # --- 2. Cisco IOS XR Native Sensors ---
    SensorDefinition(
        sensor_id="xr_native_if_counters",
        vendor_profile="CISCO_IOS_XR",
        origin="Cisco-IOS-XR-infra-statsd-oper",
        path="/infra-statistics/interfaces/interface[interface-name=*]/latest/generic-counters",
        telemetry_domain="interfaces",
        yang_module="Cisco-IOS-XR-infra-statsd-oper",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.interfaces[*].counters",
        units="bytes/packets",
        description="Cisco IOS XR native statsd generic interface counters.",
    ),
    SensorDefinition(
        sensor_id="xr_native_if_state",
        vendor_profile="CISCO_IOS_XR",
        origin="Cisco-IOS-XR-pfi-im-cmd-oper",
        path="/interfaces/interface-xr/interface[interface-name=*]",
        telemetry_domain="interfaces",
        yang_module="Cisco-IOS-XR-pfi-im-cmd-oper",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE", "ON_CHANGE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.interfaces[*]",
        units="state",
        description="Cisco IOS XR native pfi-im-cmd-oper interface operational state.",
    ),
    SensorDefinition(
        sensor_id="xr_native_bgp",
        vendor_profile="CISCO_IOS_XR",
        origin="Cisco-IOS-XR-ipv4-bgp-oper",
        path="/bgp/instances/instance[instance-name=*]/instance-active/default-vrf/neighbors/neighbor[neighbor-address=*]",
        telemetry_domain="bgp",
        yang_module="Cisco-IOS-XR-ipv4-bgp-oper",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE", "ON_CHANGE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.bgp_neighbors[*]",
        units="session/prefixes",
        description="Cisco IOS XR native ipv4-bgp-oper neighbor state.",
    ),
    SensorDefinition(
        sensor_id="xr_native_qos",
        vendor_profile="CISCO_IOS_XR",
        origin="Cisco-IOS-XR-qos-ma-oper",
        path="/qos/interface-table/interface[interface-name=*]/output/service-policy-names/service-policy-instance/statistics",
        telemetry_domain="qos",
        yang_module="Cisco-IOS-XR-qos-ma-oper",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.qos_queues[*]",
        units="bytes/packets",
        description="Cisco IOS XR native qos-ma-oper policy-map queue statistics.",
    ),
    SensorDefinition(
        sensor_id="xr_native_optics",
        vendor_profile="CISCO_IOS_XR",
        origin="Cisco-IOS-XR-controller-optics-oper",
        path="/optics-oper/optics-ports/optics-port[name=*]/optics-info",
        telemetry_domain="optics",
        yang_module="Cisco-IOS-XR-controller-optics-oper",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.optics[*]",
        units="0.01-dBm/mA",
        description="Cisco IOS XR native controller-optics-oper optical power and bias telemetry.",
    ),
    SensorDefinition(
        sensor_id="xr_native_cpu",
        vendor_profile="CISCO_IOS_XR",
        origin="Cisco-IOS-XR-wdsysmon-fd-oper",
        path="/system-monitoring/cpu-utilization[node-name=*]",
        telemetry_domain="system",
        yang_module="Cisco-IOS-XR-wdsysmon-fd-oper",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.system.cpu",
        units="percent",
        description="Cisco IOS XR native wdsysmon CPU utilization sensor.",
    ),

    # --- 3. Cisco IOS XE Native Sensors ---
    SensorDefinition(
        sensor_id="xe_native_if_stats",
        vendor_profile="CISCO_IOS_XE",
        origin="Cisco-IOS-XE-interfaces-oper",
        path="/interfaces/interface[name=*]/statistics",
        telemetry_domain="interfaces",
        yang_module="Cisco-IOS-XE-interfaces-oper",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE", "ON_CHANGE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.interfaces[*]",
        units="bytes/packets",
        description="Cisco IOS XE native interfaces-oper statistics and oper-status.",
    ),
    SensorDefinition(
        sensor_id="xe_native_bgp",
        vendor_profile="CISCO_IOS_XE",
        origin="Cisco-IOS-XE-bgp-oper",
        path="/bgp-state-data/neighbors/neighbor[neighbor-id=*]",
        telemetry_domain="bgp",
        yang_module="Cisco-IOS-XE-bgp-oper",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE", "ON_CHANGE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.bgp_neighbors[*]",
        units="session/prefixes",
        description="Cisco IOS XE native bgp-oper neighbor state.",
    ),
    SensorDefinition(
        sensor_id="xe_native_env",
        vendor_profile="CISCO_IOS_XE",
        origin="Cisco-IOS-XE-environment-oper",
        path="/environment-sensors/environment-sensor[name=*]",
        telemetry_domain="platform",
        yang_module="Cisco-IOS-XE-environment-oper",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.platform_components[*]",
        units="celsius",
        description="Cisco IOS XE native environment-oper thermal sensor.",
    ),
    SensorDefinition(
        sensor_id="xe_native_xcvr",
        vendor_profile="CISCO_IOS_XE",
        origin="Cisco-IOS-XE-transceiver-oper",
        path="/transceiver-oper-data/transceiver[name=*]",
        telemetry_domain="optics",
        yang_module="Cisco-IOS-XE-transceiver-oper",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.optics[*]",
        units="dBm/mA",
        description="Cisco IOS XE native transceiver-oper optical DOM sensor.",
    ),
    SensorDefinition(
        sensor_id="xe_native_cpu",
        vendor_profile="CISCO_IOS_XE",
        origin="Cisco-IOS-XE-process-cpu-oper",
        path="/cpu-usage/cpu-utilization",
        telemetry_domain="system",
        yang_module="Cisco-IOS-XE-process-cpu-oper",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.system.cpu",
        units="percent",
        description="Cisco IOS XE native process-cpu-oper CPU utilization.",
    ),

    # --- 4. Arista EOS Native Sensors (origin="eos_native") ---
    SensorDefinition(
        sensor_id="eos_native_if_counters",
        vendor_profile="ARISTA_EOS",
        origin="eos_native",
        path="/Sysdb/interface/counter/eth/slice/phy/[intf=*]/currentStatistics",
        telemetry_domain="interfaces",
        yang_module="eos_native",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.interfaces[*].counters",
        units="bytes/packets",
        description="Arista EOS native Sysdb Ethernet interface counter statistics.",
    ),
    SensorDefinition(
        sensor_id="eos_native_lanz",
        vendor_profile="ARISTA_EOS",
        origin="eos_native",
        path="/Sysdb/hardware/counter/Lanz/[intf=*]/queueStatus",
        telemetry_domain="qos",
        yang_module="eos_native",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.qos_queues[*]",
        units="bytes/packets",
        description="Arista EOS native LANZ microburst queue length and discard status.",
    ),
    SensorDefinition(
        sensor_id="eos_native_bgp",
        vendor_profile="ARISTA_EOS",
        origin="eos_native",
        path="/Smash/routing/bgp/bgpPeerInfoStatus/[vrf=*]/bgpPeerStatusEntry[peerAddr=*]",
        telemetry_domain="bgp",
        yang_module="eos_native",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE", "ON_CHANGE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.bgp_neighbors[*]",
        units="session/prefixes",
        description="Arista EOS native Smash BGP peer status table.",
    ),
    SensorDefinition(
        sensor_id="eos_native_vxlan",
        vendor_profile="ARISTA_EOS",
        origin="eos_native",
        path="/Smash/vxlan/vtepStatus",
        telemetry_domain="evpn_vxlan",
        yang_module="eos_native",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE", "ON_CHANGE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.evpn",
        units="state",
        description="Arista EOS native Smash VXLAN VTEP status.",
    ),

    # --- 5. Juniper Junos Native JTI Sensors (origin="junos") ---
    SensorDefinition(
        sensor_id="junos_native_if_stats",
        vendor_profile="JUNIPER_JUNOS",
        origin="junos",
        path="/junos/system/linecard/interface[name=*]/statistics",
        telemetry_domain="interfaces",
        yang_module="junos-telemetry-interface",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.interfaces[*].counters",
        units="bytes/packets",
        description="Juniper Junos JTI linecard interface statistics.",
    ),
    SensorDefinition(
        sensor_id="junos_native_optics",
        vendor_profile="JUNIPER_JUNOS",
        origin="junos",
        path="/junos/system/linecard/optics[name=*]",
        telemetry_domain="optics",
        yang_module="junos-telemetry-interface",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.optics[*]",
        units="dBm/mA",
        description="Juniper Junos JTI linecard optical transceiver telemetry.",
    ),
    SensorDefinition(
        sensor_id="junos_native_qmon",
        vendor_profile="JUNIPER_JUNOS",
        origin="junos",
        path="/junos/system/linecard/qmon[interface=*]",
        telemetry_domain="qos",
        yang_module="junos-telemetry-interface",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.qos_queues[*]",
        units="bytes/packets",
        description="Juniper Junos JTI queue monitoring (qmon) buffer and tail-drop telemetry.",
    ),
    SensorDefinition(
        sensor_id="junos_native_bgp",
        vendor_profile="JUNIPER_JUNOS",
        origin="junos",
        path="/junos/services/bgp/neighbors/neighbor[neighbor-address=*]",
        telemetry_domain="bgp",
        yang_module="junos-telemetry-interface",
        encoding_support=("JSON_IETF", "JSON", "PROTO"),
        subscription_support=("ONCE", "POLL", "SAMPLE", "ON_CHANGE"),
        fidelity_classification="VERIFIED",
        state_source="DeviceStateSnapshot.bgp_neighbors[*]",
        units="session/prefixes",
        description="Juniper Junos JTI BGP neighbor state and prefix telemetry.",
    ),
)


class TelemetrySensorRegistry:
    """
    Centralized registry for resolving gNMI Paths to DeviceStateSnapshot extractors.
    """

    def __init__(self) -> None:
        self._sensors: Dict[str, SensorDefinition] = {s.sensor_id: s for s in CANONICAL_SENSORS}

    def list_sensors(self, vendor_profile: Optional[VendorProfileId] = None) -> List[SensorDefinition]:
        if vendor_profile is None:
            return list(CANONICAL_SENSORS)
        return [
            s
            for s in CANONICAL_SENSORS
            if s.vendor_profile in ("ALL", vendor_profile.value)
        ]

    def resolve(
        self,
        snap: DeviceStateSnapshot,
        path: ParsedGnmiPath,
        data_type: str = "ALL",
    ) -> List[ResolvedSensorSample]:
        return self.resolve_and_extract(snapshot=snap, parsed_path=path, data_type=data_type)

    def resolve_and_extract(
        self,
        snapshot: DeviceStateSnapshot,
        parsed_path: ParsedGnmiPath,
        data_type: str = "ALL",
    ) -> List[ResolvedSensorSample]:
        """
        Validates origin against the target's VendorProfile, matches the path (including wildcard
        expansion or leaf drill-down), and extracts deterministic values from DeviceStateSnapshot.
        """
        vprof = get_vendor_profile(snapshot.vendor_profile)
        origin = parsed_path.origin or "openconfig"
        if not vprof.supports_origin(origin):
            raise GnmiOriginNotSupportedError(
                f"FOREIGN_VENDOR_ORIGIN / MODEL_NOT_SUPPORTED: Origin {origin!r} is not supported by target "
                f"{snapshot.device_id!r} ({snapshot.vendor_profile.value}). "
                f"Supported origins: {list(vprof.supported_origins)}"
            )

        if origin == "openconfig":
            return self._extract_openconfig(snapshot, parsed_path, data_type=data_type)
        return self._extract_vendor_native(snapshot, parsed_path)

    # =====================================================================
    # OpenConfig Path Extraction
    # =====================================================================
    def _extract_openconfig(
        self,
        snap: DeviceStateSnapshot,
        path: ParsedGnmiPath,
        data_type: str = "ALL",
    ) -> List[ResolvedSensorSample]:
        elems = path.elems
        if not elems:
            raise GnmiPathNotFoundError("UNSUPPORTED_PATH: Root '/' query is not permitted; specify a domain subtree.")

        root = elems[0].name
        results: List[ResolvedSensorSample] = []

        # 1. /interfaces/interface[name=...]/...
        if root == "interfaces":
            if len(elems) < 2 or elems[1].name != "interface":
                raise GnmiPathNotFoundError(f"UNSUPPORTED_PATH: {path.canonical_xpath}")
            req_if = elems[1].keys.get("name", "*")
            matched_ifs = (
                list(snap.interfaces.values())
                if req_if == "*"
                else ([snap.interfaces[req_if]] if req_if in snap.interfaces else [])
            )
            if not matched_ifs:
                raise GnmiPathNotFoundError(
                    f"UNSUPPORTED_PATH: Interface {req_if!r} not found on {snap.device_id}"
                )

            tail = elems[2:]
            for intf in matched_ifs:
                base_elems = (
                    ParsedPathElem("interfaces", {}),
                    ParsedPathElem("interface", {"name": intf.name}),
                )
                # Subinterfaces check
                if tail and tail[0].name == "subinterfaces":
                    sub_payload = {
                        "ip": intf.ipv4_address,
                        "prefix-length": intf.ipv4_prefix_length,
                    }
                    c_elems = base_elems + (
                        ParsedPathElem("subinterfaces", {}),
                        ParsedPathElem("subinterface", {"index": "0"}),
                        ParsedPathElem("ipv4", {}),
                        ParsedPathElem("addresses", {}),
                        ParsedPathElem("address", {"ip": intf.ipv4_address}),
                        ParsedPathElem("state", {}),
                    )
                    results.append(
                        ResolvedSensorSample(
                            sensor_id="oc_subif_ipv4",
                            concrete_path=ParsedGnmiPath("openconfig", snap.device_id, c_elems),
                            payload=sub_payload,
                            yang_module="openconfig-if-ip",
                        )
                    )
                    continue

                counters_dict = {
                    "in-octets": intf.counters.in_octets,
                    "out-octets": intf.counters.out_octets,
                    "in-unicast-pkts": intf.counters.in_unicast_pkts,
                    "out-unicast-pkts": intf.counters.out_unicast_pkts,
                    "in-errors": intf.counters.in_errors,
                    "out-errors": intf.counters.out_errors,
                    "in-fcs-errors": intf.counters.in_fcs_errors,
                    "in-discards": intf.counters.in_discards,
                    "out-discards": intf.counters.out_discards,
                    "carrier-transitions": intf.counters.carrier_transitions,
                }
                config_dict = {
                    "name": intf.name,
                    "description": intf.description,
                    "enabled": intf.admin_status == "UP",
                    "mtu": intf.mtu,
                }
                state_dict = {
                    "name": intf.name,
                    "description": intf.description,
                    "admin-status": intf.admin_status,
                    "oper-status": intf.oper_status,
                    "mtu": intf.mtu,
                    "high-speed": intf.high_speed_mbps,
                    "counters": counters_dict,
                }
                if not tail:
                    dt = (data_type or "ALL").upper()
                    if dt == "CONFIG":
                        if_payload = {"openconfig-interfaces:config": config_dict}
                    elif dt in ("STATE", "OPERATIONAL"):
                        if_payload = {"openconfig-interfaces:state": state_dict}
                    else:
                        if_payload = {
                            "openconfig-interfaces:config": config_dict,
                            "openconfig-interfaces:state": state_dict,
                        }
                    results.append(
                        ResolvedSensorSample(
                            sensor_id="oc_if_state",
                            concrete_path=ParsedGnmiPath("openconfig", snap.device_id, base_elems),
                            payload=if_payload,
                            yang_module="openconfig-interfaces",
                        )
                    )
                elif len(tail) == 1 and tail[0].name == "config":
                    c_elems = base_elems + (ParsedPathElem("config", {}),)
                    results.append(
                        ResolvedSensorSample(
                            sensor_id="oc_if_state",
                            concrete_path=ParsedGnmiPath("openconfig", snap.device_id, c_elems),
                            payload=config_dict,
                            yang_module="openconfig-interfaces",
                        )
                    )
                elif len(tail) == 1 and tail[0].name == "state":
                    c_elems = base_elems + (ParsedPathElem("state", {}),)
                    results.append(
                        ResolvedSensorSample(
                            sensor_id="oc_if_state",
                            concrete_path=ParsedGnmiPath("openconfig", snap.device_id, c_elems),
                            payload=state_dict,
                            yang_module="openconfig-interfaces",
                        )
                    )
                elif len(tail) == 2 and tail[0].name == "state":
                    leaf = tail[1].name
                    if leaf == "counters":
                        c_elems = base_elems + (
                            ParsedPathElem("state", {}),
                            ParsedPathElem("counters", {}),
                        )
                        results.append(
                            ResolvedSensorSample(
                                sensor_id="oc_if_counters",
                                concrete_path=ParsedGnmiPath("openconfig", snap.device_id, c_elems),
                                payload=counters_dict,
                                yang_module="openconfig-interfaces",
                            )
                        )
                    elif leaf in state_dict:
                        c_elems = base_elems + (
                            ParsedPathElem("state", {}),
                            ParsedPathElem(leaf, {}),
                        )
                        results.append(
                            ResolvedSensorSample(
                                sensor_id="oc_if_state",
                                concrete_path=ParsedGnmiPath("openconfig", snap.device_id, c_elems),
                                payload=state_dict[leaf],
                                yang_module="openconfig-interfaces",
                            )
                        )
                    else:
                        raise GnmiPathNotFoundError(f"UNSUPPORTED_PATH: Unknown interface state leaf {leaf!r}")
                elif len(tail) == 3 and tail[0].name == "state" and tail[1].name == "counters":
                    c_leaf = tail[2].name
                    if c_leaf not in counters_dict:
                        raise GnmiPathNotFoundError(f"UNSUPPORTED_PATH: Unknown counter leaf {c_leaf!r}")
                    c_elems = base_elems + (
                        ParsedPathElem("state", {}),
                        ParsedPathElem("counters", {}),
                        ParsedPathElem(c_leaf, {}),
                    )
                    results.append(
                        ResolvedSensorSample(
                            sensor_id="oc_if_counters",
                            concrete_path=ParsedGnmiPath("openconfig", snap.device_id, c_elems),
                            payload=counters_dict[c_leaf],
                            yang_module="openconfig-interfaces",
                            leaf_yang_type="uint64",
                        )
                    )
                else:
                    raise GnmiPathNotFoundError(f"UNSUPPORTED_PATH: {path.canonical_xpath}")
            return results

        # 2. /lldp/...
        if root == "lldp":
            for nbr in snap.lldp_neighbors:
                c_elems = (
                    ParsedPathElem("lldp", {}),
                    ParsedPathElem("interfaces", {}),
                    ParsedPathElem("interface", {"name": nbr.local_interface}),
                    ParsedPathElem("neighbors", {}),
                    ParsedPathElem("neighbor", {"id": nbr.neighbor_id}),
                    ParsedPathElem("state", {}),
                )
                payload = {
                    "id": nbr.neighbor_id,
                    "system-name": nbr.system_name,
                    "port-id": nbr.port_id,
                    "port-description": nbr.port_description,
                    "management-address": nbr.management_address,
                }
                results.append(
                    ResolvedSensorSample(
                        sensor_id="oc_lldp_nbr",
                        concrete_path=ParsedGnmiPath("openconfig", snap.device_id, c_elems),
                        payload=payload,
                        yang_module="openconfig-lldp",
                    )
                )
            return results

        # 3. /lacp/...
        if root == "lacp":
            for mbr in snap.lacp_members:
                c_elems = (
                    ParsedPathElem("lacp", {}),
                    ParsedPathElem("interfaces", {}),
                    ParsedPathElem("interface", {"name": mbr.lag_interface}),
                    ParsedPathElem("members", {}),
                    ParsedPathElem("member", {"interface": mbr.member_interface}),
                    ParsedPathElem("state", {}),
                )
                payload = {
                    "interface": mbr.member_interface,
                    "aggregatable": mbr.aggregatable,
                    "collecting": mbr.collecting,
                    "distributing": mbr.distributing,
                    "activity": mbr.activity,
                    "oper-key": mbr.oper_key,
                    "partner-id": mbr.partner_id,
                }
                results.append(
                    ResolvedSensorSample(
                        sensor_id="oc_lacp_mbr",
                        concrete_path=ParsedGnmiPath("openconfig", snap.device_id, c_elems),
                        payload=payload,
                        yang_module="openconfig-lacp",
                    )
                )
            return results

        # 4. /network-instances/network-instance[name=...]/...
        if root == "network-instances":
            names = [e.name for e in elems]
            if "bgp" in names:
                nbr_elem = next((e for e in elems if e.name == "neighbor"), None)
                req_peer = nbr_elem.keys.get("neighbor-address", "*") if nbr_elem else "*"
                matched_peers = (
                    list(snap.bgp_neighbors.values())
                    if req_peer == "*"
                    else ([snap.bgp_neighbors[req_peer]] if req_peer in snap.bgp_neighbors else [])
                )
                if not matched_peers:
                    raise GnmiPathNotFoundError(f"UNSUPPORTED_PATH: BGP neighbor {req_peer!r} not found")

                for peer in matched_peers:
                    base_bgp_elems = (
                        ParsedPathElem("network-instances", {}),
                        ParsedPathElem("network-instance", {"name": "default"}),
                        ParsedPathElem("protocols", {}),
                        ParsedPathElem("protocol", {"identifier": "BGP", "name": "BGP"}),
                        ParsedPathElem("bgp", {}),
                        ParsedPathElem("neighbors", {}),
                        ParsedPathElem("neighbor", {"neighbor-address": peer.neighbor_address}),
                    )
                    if "prefixes" in names:
                        c_elems = base_bgp_elems + (
                            ParsedPathElem("afi-safis", {}),
                            ParsedPathElem("afi-safi", {"afi-safi-name": "IPV4_UNICAST"}),
                            ParsedPathElem("state", {}),
                            ParsedPathElem("prefixes", {}),
                        )
                        payload = {
                            "received": peer.prefixes_received,
                            "installed": peer.prefixes_installed,
                            "sent": peer.prefixes_sent,
                        }
                        results.append(
                            ResolvedSensorSample(
                                sensor_id="oc_bgp_afi",
                                concrete_path=ParsedGnmiPath("openconfig", snap.device_id, c_elems),
                                payload=payload,
                                yang_module="openconfig-bgp",
                            )
                        )
                    elif names[-1] == "session-state":
                        c_elems = base_bgp_elems + (
                            ParsedPathElem("state", {}),
                            ParsedPathElem("session-state", {}),
                        )
                        results.append(
                            ResolvedSensorSample(
                                sensor_id="oc_bgp_nbr",
                                concrete_path=ParsedGnmiPath("openconfig", snap.device_id, c_elems),
                                payload=peer.session_state,
                                yang_module="openconfig-bgp",
                                leaf_yang_type="string",
                            )
                        )
                    else:
                        c_elems = base_bgp_elems + (ParsedPathElem("state", {}),)
                        payload = {
                            "neighbor-address": peer.neighbor_address,
                            "peer-as": peer.peer_as,
                            "description": peer.description,
                            "session-state": peer.session_state,
                            "established-transitions": peer.established_transitions,
                            "last-established": peer.last_established,
                            "prefixes": {
                                "received": peer.prefixes_received,
                                "installed": peer.prefixes_installed,
                                "sent": peer.prefixes_sent,
                            },
                            "messages": {
                                "sent": {"update": peer.messages_sent_update},
                                "received": {"update": peer.messages_received_update},
                            },
                        }
                        results.append(
                            ResolvedSensorSample(
                                sensor_id="oc_bgp_nbr",
                                concrete_path=ParsedGnmiPath("openconfig", snap.device_id, c_elems),
                                payload=payload,
                                yang_module="openconfig-bgp",
                            )
                        )
                return results

            if "afts" in names:
                entry_elem = next((e for e in elems if e.name == "ipv4-entry"), None)
                req_pfx = entry_elem.keys.get("prefix", "*") if entry_elem else "*"
                matched_aft = (
                    list(snap.aft_entries.values())
                    if req_pfx == "*"
                    else ([snap.aft_entries[req_pfx]] if req_pfx in snap.aft_entries else [])
                )
                if not matched_aft:
                    raise GnmiPathNotFoundError(f"UNSUPPORTED_PATH: AFT prefix {req_pfx!r} not found")
                for aft in matched_aft:
                    c_elems = (
                        ParsedPathElem("network-instances", {}),
                        ParsedPathElem("network-instance", {"name": "default"}),
                        ParsedPathElem("afts", {}),
                        ParsedPathElem("ipv4-unicast", {}),
                        ParsedPathElem("ipv4-entries", {}),
                        ParsedPathElem("ipv4-entry", {"prefix": aft.prefix}),
                        ParsedPathElem("state", {}),
                    )
                    payload = {
                        "prefix": aft.prefix,
                        "next-hop-group": aft.next_hop_group,
                        "next-hop": aft.next_hop_ip,
                        "egress-interface": aft.egress_interface,
                        "ecmp-paths": aft.ecmp_paths,
                        "packets-forwarded": aft.packets_forwarded,
                        "octets-forwarded": aft.octets_forwarded,
                    }
                    results.append(
                        ResolvedSensorSample(
                            sensor_id="oc_aft_ipv4",
                            concrete_path=ParsedGnmiPath("openconfig", snap.device_id, c_elems),
                            payload=payload,
                            yang_module="openconfig-aft",
                        )
                    )
                return results

            if "evpn" in names:
                if not snap.evpn.supported:
                    raise GnmiPathNotFoundError(
                        f"NOT_SUPPORTED: EVPN/VXLAN sensor is NOT_SUPPORTED on target {snap.device_id!r}"
                    )
                c_elems = (
                    ParsedPathElem("network-instances", {}),
                    ParsedPathElem("network-instance", {"name": "default"}),
                    ParsedPathElem("evpn", {}),
                    ParsedPathElem("state", {}),
                )
                payload = {
                    "vtep-status": snap.evpn.vtep_status,
                    "vni-id": snap.evpn.vni_id,
                    "type2-mac-ip-routes": snap.evpn.type2_mac_ip_routes,
                    "type5-ip-prefix-routes": snap.evpn.type5_ip_prefix_routes,
                }
                return [
                    ResolvedSensorSample(
                        sensor_id="oc_evpn_vxlan",
                        concrete_path=ParsedGnmiPath("openconfig", snap.device_id, c_elems),
                        payload=payload,
                        yang_module="openconfig-evpn",
                    )
                ]

        # 5. /qos/...
        if root == "qos":
            if_elem = next((e for e in elems if e.name == "interface"), None)
            req_if = if_elem.keys.get("interface-id", "*") if if_elem else "*"
            matched_q = [
                q
                for q in snap.qos_queues.values()
                if req_if in ("*", q.interface_id)
            ]
            if not matched_q:
                raise GnmiPathNotFoundError(f"UNSUPPORTED_PATH: QoS interface {req_if!r} not found")
            for q in matched_q:
                c_elems = (
                    ParsedPathElem("qos", {}),
                    ParsedPathElem("interfaces", {}),
                    ParsedPathElem("interface", {"interface-id": q.interface_id}),
                    ParsedPathElem("output", {}),
                    ParsedPathElem("queues", {}),
                    ParsedPathElem("queue", {"name": q.queue_name}),
                    ParsedPathElem("state", {}),
                )
                q_dict = {
                    "name": q.queue_name,
                    "transmit-pkts": q.transmit_pkts,
                    "transmit-octets": q.transmit_octets,
                    "dropped-pkts": q.dropped_pkts,
                    "dropped-octets": q.dropped_octets,
                    "max-queue-len": q.max_queue_len,
                }
                if elems[-1].name in q_dict and elems[-2].name == "state":
                    leaf = elems[-1].name
                    results.append(
                        ResolvedSensorSample(
                            sensor_id="oc_qos_queue",
                            concrete_path=ParsedGnmiPath("openconfig", snap.device_id, c_elems + (ParsedPathElem(leaf, {}),)),
                            payload=q_dict[leaf],
                            yang_module="openconfig-qos",
                            leaf_yang_type="uint64",
                        )
                    )
                else:
                    results.append(
                        ResolvedSensorSample(
                            sensor_id="oc_qos_queue",
                            concrete_path=ParsedGnmiPath("openconfig", snap.device_id, c_elems),
                            payload=q_dict,
                            yang_module="openconfig-qos",
                        )
                    )
            return results

        # 6. /components/...
        if root == "components":
            names = [e.name for e in elems]
            if "transceiver" in names:
                for opt in snap.optics.values():
                    c_elems = (
                        ParsedPathElem("components", {}),
                        ParsedPathElem("component", {"name": opt.component_name}),
                        ParsedPathElem("transceiver", {}),
                        ParsedPathElem("state", {}),
                    )
                    payload = {
                        "interface": opt.interface_name,
                        "input-power": {"instant": opt.rx_power_dbm},
                        "output-power": {"instant": opt.tx_power_dbm},
                        "laser-bias-current": {"instant": opt.laser_bias_ma},
                        "pre-fec-ber": {"instant": opt.pre_fec_ber},
                        "osnr": {"instant": opt.osnr_db},
                    }
                    results.append(
                        ResolvedSensorSample(
                            sensor_id="oc_platform_optics",
                            concrete_path=ParsedGnmiPath("openconfig", snap.device_id, c_elems),
                            payload=payload,
                            yang_module="openconfig-platform-transceiver",
                        )
                    )
                return results

            comp_elem = next((e for e in elems if e.name == "component"), None)
            req_comp = comp_elem.keys.get("name", "*") if comp_elem else "*"
            matched_comps = (
                list(snap.platform_components.values())
                if req_comp == "*"
                else ([snap.platform_components[req_comp]] if req_comp in snap.platform_components else [])
            )
            if not matched_comps:
                raise GnmiPathNotFoundError(f"UNSUPPORTED_PATH: Component {req_comp!r} not found")
            for comp in matched_comps:
                c_elems = (
                    ParsedPathElem("components", {}),
                    ParsedPathElem("component", {"name": comp.name}),
                    ParsedPathElem("state", {}),
                )
                payload = {
                    "name": comp.name,
                    "type": comp.component_type,
                    "oper-status": comp.oper_status,
                    "temperature": {"instant": comp.temperature_instant},
                    "used-power": comp.used_power_watts,
                }
                results.append(
                    ResolvedSensorSample(
                        sensor_id="oc_platform_comp",
                        concrete_path=ParsedGnmiPath("openconfig", snap.device_id, c_elems),
                        payload=payload,
                        yang_module="openconfig-platform",
                    )
                )
            return results

        # 7. /system/...
        if root == "system":
            names = [e.name for e in elems]
            if "cpus" in names:
                c_elems = (
                    ParsedPathElem("system", {}),
                    ParsedPathElem("cpus", {}),
                    ParsedPathElem("cpu", {"index": "0"}),
                    ParsedPathElem("state", {}),
                )
                payload = {
                    "index": 0,
                    "total": {"instant": snap.system.cpu_total_pct},
                    "user": {"instant": snap.system.cpu_user_pct},
                    "kernel": {"instant": snap.system.cpu_kernel_pct},
                }
                return [
                    ResolvedSensorSample(
                        sensor_id="oc_system_cpu",
                        concrete_path=ParsedGnmiPath("openconfig", snap.device_id, c_elems),
                        payload=payload,
                        yang_module="openconfig-system",
                    )
                ]
            if "memory" in names:
                c_elems = (
                    ParsedPathElem("system", {}),
                    ParsedPathElem("memory", {}),
                    ParsedPathElem("state", {}),
                )
                payload = {
                    "physical": snap.system.memory_physical_bytes,
                    "reserved": snap.system.memory_reserved_bytes,
                }
                return [
                    ResolvedSensorSample(
                        sensor_id="oc_system_memory",
                        concrete_path=ParsedGnmiPath("openconfig", snap.device_id, c_elems),
                        payload=payload,
                        yang_module="openconfig-system",
                    )
                ]
            if len(elems) >= 2 and elems[1].name in ("state", "config"):
                sys_dict = {
                    "hostname": snap.system.hostname,
                    "domain-name": snap.system.domain_name,
                    "boot-time": snap.system.boot_time_ns,
                    "current-datetime": snap.system.current_datetime,
                }
                if len(elems) == 3 and elems[2].name in sys_dict:
                    leaf = elems[2].name
                    c_elems = (
                        ParsedPathElem("system", {}),
                        ParsedPathElem("state", {}),
                        ParsedPathElem(leaf, {}),
                    )
                    return [
                        ResolvedSensorSample(
                            sensor_id="oc_system_state",
                            concrete_path=ParsedGnmiPath("openconfig", snap.device_id, c_elems),
                            payload=sys_dict[leaf],
                            yang_module="openconfig-system",
                        )
                    ]
                c_elems = (
                    ParsedPathElem("system", {}),
                    ParsedPathElem("state", {}),
                )
                return [
                    ResolvedSensorSample(
                        sensor_id="oc_system_state",
                        concrete_path=ParsedGnmiPath("openconfig", snap.device_id, c_elems),
                        payload=sys_dict,
                        yang_module="openconfig-system",
                    )
                ]

        raise GnmiPathNotFoundError(f"UNSUPPORTED_PATH: OpenConfig path {path.canonical_xpath!r} is not supported")

    # =====================================================================
    # Vendor-Native Path Extraction
    # =====================================================================
    def _extract_vendor_native(
        self,
        snap: DeviceStateSnapshot,
        path: ParsedGnmiPath,
    ) -> List[ResolvedSensorSample]:
        origin = path.origin
        elems = path.elems
        names = [e.name for e in elems]
        primary_if = next(iter(snap.interfaces.values()))
        primary_bgp = next(iter(snap.bgp_neighbors.values()))
        primary_q = next(iter(snap.qos_queues.values()))
        primary_opt = next(iter(snap.optics.values()))

        # 1. Cisco IOS XR Native
        if origin == "Cisco-IOS-XR-infra-statsd-oper":
            c_elems = (
                ParsedPathElem("infra-statistics", {}),
                ParsedPathElem("interfaces", {}),
                ParsedPathElem("interface", {"interface-name": primary_if.name}),
                ParsedPathElem("latest", {}),
                ParsedPathElem("generic-counters", {}),
            )
            payload = {
                "bytes-received": primary_if.counters.in_octets,
                "bytes-sent": primary_if.counters.out_octets,
                "packets-received": primary_if.counters.in_unicast_pkts,
                "packets-sent": primary_if.counters.out_unicast_pkts,
                "input-errors": primary_if.counters.in_errors,
                "input-drops": primary_if.counters.in_discards,
                "carrier-transitions": primary_if.counters.carrier_transitions,
            }
            return [
                ResolvedSensorSample(
                    sensor_id="xr_native_if_counters",
                    concrete_path=ParsedGnmiPath(origin, snap.device_id, c_elems),
                    payload=payload,
                    yang_module=origin,
                )
            ]

        if origin == "Cisco-IOS-XR-pfi-im-cmd-oper":
            c_elems = (
                ParsedPathElem("interfaces", {}),
                ParsedPathElem("interface-xr", {}),
                ParsedPathElem("interface", {"interface-name": primary_if.name}),
            )
            payload = {
                "interface-name": primary_if.name,
                "state": "im-state-up" if primary_if.oper_status == "UP" else "im-state-down",
                "line-state": "im-state-up" if primary_if.oper_status == "UP" else "im-state-down",
                "mtu": primary_if.mtu,
            }
            return [
                ResolvedSensorSample(
                    sensor_id="xr_native_if_state",
                    concrete_path=ParsedGnmiPath(origin, snap.device_id, c_elems),
                    payload=payload,
                    yang_module=origin,
                )
            ]

        if origin == "Cisco-IOS-XR-ipv4-bgp-oper":
            c_elems = (
                ParsedPathElem("bgp", {}),
                ParsedPathElem("instances", {}),
                ParsedPathElem("instance", {"instance-name": "default"}),
                ParsedPathElem("instance-active", {}),
                ParsedPathElem("default-vrf", {}),
                ParsedPathElem("neighbors", {}),
                ParsedPathElem("neighbor", {"neighbor-address": primary_bgp.neighbor_address}),
            )
            payload = {
                "neighbor-address": primary_bgp.neighbor_address,
                "connection-state": "bgp-st-estab" if primary_bgp.session_state == "ESTABLISHED" else "bgp-st-idle",
                "prefixes-accepted": primary_bgp.prefixes_installed,
            }
            return [
                ResolvedSensorSample(
                    sensor_id="xr_native_bgp",
                    concrete_path=ParsedGnmiPath(origin, snap.device_id, c_elems),
                    payload=payload,
                    yang_module=origin,
                )
            ]

        if origin == "Cisco-IOS-XR-qos-ma-oper":
            c_elems = (
                ParsedPathElem("qos", {}),
                ParsedPathElem("interface-table", {}),
                ParsedPathElem("interface", {"interface-name": primary_q.interface_id}),
                ParsedPathElem("output", {}),
                ParsedPathElem("service-policy-names", {}),
                ParsedPathElem("service-policy-instance", {}),
                ParsedPathElem("statistics", {}),
            )
            payload = {
                "tail-drop-packets": primary_q.dropped_pkts,
                "queue-current-size-bytes": primary_q.max_queue_len,
                "transmit-bytes": primary_q.transmit_octets,
            }
            return [
                ResolvedSensorSample(
                    sensor_id="xr_native_qos",
                    concrete_path=ParsedGnmiPath(origin, snap.device_id, c_elems),
                    payload=payload,
                    yang_module=origin,
                )
            ]

        if origin == "Cisco-IOS-XR-controller-optics-oper":
            c_elems = (
                ParsedPathElem("optics-oper", {}),
                ParsedPathElem("optics-ports", {}),
                ParsedPathElem("optics-port", {"name": primary_opt.interface_name}),
                ParsedPathElem("optics-info", {}),
            )
            payload = {
                "receive-power": int(primary_opt.rx_power_dbm * 100),
                "transmit-power": int(primary_opt.tx_power_dbm * 100),
                "laser-bias-current": primary_opt.laser_bias_ma,
            }
            return [
                ResolvedSensorSample(
                    sensor_id="xr_native_optics",
                    concrete_path=ParsedGnmiPath(origin, snap.device_id, c_elems),
                    payload=payload,
                    yang_module=origin,
                )
            ]

        if origin == "Cisco-IOS-XR-wdsysmon-fd-oper":
            c_elems = (
                ParsedPathElem("system-monitoring", {}),
                ParsedPathElem("cpu-utilization", {"node-name": "0/RP0/CPU0"}),
            )
            payload = {
                "total-cpu-one-minute": snap.system.cpu_total_pct,
                "total-cpu-five-minute": snap.system.cpu_total_pct,
            }
            return [
                ResolvedSensorSample(
                    sensor_id="xr_native_cpu",
                    concrete_path=ParsedGnmiPath(origin, snap.device_id, c_elems),
                    payload=payload,
                    yang_module=origin,
                )
            ]

        # 2. Cisco IOS XE Native
        if origin == "Cisco-IOS-XE-interfaces-oper":
            c_elems = (
                ParsedPathElem("interfaces", {}),
                ParsedPathElem("interface", {"name": primary_if.name}),
                ParsedPathElem("statistics", {}),
            )
            payload = {
                "name": primary_if.name,
                "oper-status": "if-oper-state-ready" if primary_if.oper_status == "UP" else "if-oper-state-no-pass",
                "in-octets": primary_if.counters.in_octets,
                "out-octets": primary_if.counters.out_octets,
                "in-errors": primary_if.counters.in_errors,
            }
            return [
                ResolvedSensorSample(
                    sensor_id="xe_native_if_stats",
                    concrete_path=ParsedGnmiPath(origin, snap.device_id, c_elems),
                    payload=payload,
                    yang_module=origin,
                )
            ]

        if origin == "Cisco-IOS-XE-bgp-oper":
            c_elems = (
                ParsedPathElem("bgp-state-data", {}),
                ParsedPathElem("neighbors", {}),
                ParsedPathElem("neighbor", {"neighbor-id": primary_bgp.neighbor_address}),
            )
            payload = {
                "neighbor-id": primary_bgp.neighbor_address,
                "session-state": "fsm-established" if primary_bgp.session_state == "ESTABLISHED" else "fsm-idle",
                "prefix-activity": {"received": primary_bgp.prefixes_received},
            }
            return [
                ResolvedSensorSample(
                    sensor_id="xe_native_bgp",
                    concrete_path=ParsedGnmiPath(origin, snap.device_id, c_elems),
                    payload=payload,
                    yang_module=origin,
                )
            ]

        if origin == "Cisco-IOS-XE-environment-oper":
            comp = next(iter(snap.platform_components.values()))
            c_elems = (
                ParsedPathElem("environment-sensors", {}),
                ParsedPathElem("environment-sensor", {"name": comp.name}),
            )
            payload = {
                "name": comp.name,
                "current-reading": int(comp.temperature_instant),
                "state": comp.oper_status,
            }
            return [
                ResolvedSensorSample(
                    sensor_id="xe_native_env",
                    concrete_path=ParsedGnmiPath(origin, snap.device_id, c_elems),
                    payload=payload,
                    yang_module=origin,
                )
            ]

        if origin == "Cisco-IOS-XE-transceiver-oper":
            c_elems = (
                ParsedPathElem("transceiver-oper-data", {}),
                ParsedPathElem("transceiver", {"name": primary_opt.interface_name}),
            )
            payload = {
                "name": primary_opt.interface_name,
                "input-power": primary_opt.rx_power_dbm,
                "output-power": primary_opt.tx_power_dbm,
                "laser-bias-current": primary_opt.laser_bias_ma,
            }
            return [
                ResolvedSensorSample(
                    sensor_id="xe_native_xcvr",
                    concrete_path=ParsedGnmiPath(origin, snap.device_id, c_elems),
                    payload=payload,
                    yang_module=origin,
                )
            ]

        if origin == "Cisco-IOS-XE-process-cpu-oper":
            c_elems = (
                ParsedPathElem("cpu-usage", {}),
                ParsedPathElem("cpu-utilization", {}),
            )
            payload = {
                "five-seconds": snap.system.cpu_total_pct,
                "one-minute": snap.system.cpu_total_pct,
            }
            return [
                ResolvedSensorSample(
                    sensor_id="xe_native_cpu",
                    concrete_path=ParsedGnmiPath(origin, snap.device_id, c_elems),
                    payload=payload,
                    yang_module=origin,
                )
            ]

        # 3. Arista EOS Native (origin="eos_native")
        if origin == "eos_native":
            if "Lanz" in names or "lanz" in names:
                c_elems = (
                    ParsedPathElem("Sysdb", {}),
                    ParsedPathElem("hardware", {}),
                    ParsedPathElem("counter", {}),
                    ParsedPathElem("Lanz", {"intf": primary_q.interface_id}),
                    ParsedPathElem("queueStatus", {}),
                )
                payload = {
                    "intfName": primary_q.interface_id,
                    "queueLengthBytes": primary_q.max_queue_len,
                    "outDiscards": primary_q.dropped_pkts,
                }
                return [
                    ResolvedSensorSample(
                        sensor_id="eos_native_lanz",
                        concrete_path=ParsedGnmiPath(origin, snap.device_id, c_elems),
                        payload=payload,
                        yang_module="eos_native",
                    )
                ]
            if "bgp" in names:
                c_elems = (
                    ParsedPathElem("Smash", {}),
                    ParsedPathElem("routing", {}),
                    ParsedPathElem("bgp", {}),
                    ParsedPathElem("bgpPeerInfoStatus", {"vrf": "default"}),
                    ParsedPathElem("bgpPeerStatusEntry", {"peerAddr": primary_bgp.neighbor_address}),
                )
                payload = {
                    "peerAddr": primary_bgp.neighbor_address,
                    "bgpState": primary_bgp.session_state,
                    "prefixesReceived": primary_bgp.prefixes_received,
                }
                return [
                    ResolvedSensorSample(
                        sensor_id="eos_native_bgp",
                        concrete_path=ParsedGnmiPath(origin, snap.device_id, c_elems),
                        payload=payload,
                        yang_module="eos_native",
                    )
                ]
            if "vxlan" in names or "vtepStatus" in names:
                c_elems = (
                    ParsedPathElem("Smash", {}),
                    ParsedPathElem("vxlan", {}),
                    ParsedPathElem("vtepStatus", {}),
                )
                payload = {
                    "vtepStatus": snap.evpn.vtep_status,
                    "vni": snap.evpn.vni_id,
                    "type2MacIpRoutes": snap.evpn.type2_mac_ip_routes,
                }
                return [
                    ResolvedSensorSample(
                        sensor_id="eos_native_vxlan",
                        concrete_path=ParsedGnmiPath(origin, snap.device_id, c_elems),
                        payload=payload,
                        yang_module="eos_native",
                    )
                ]
            if "Sysdb" in names and "interface" in names:
                c_elems = (
                    ParsedPathElem("Sysdb", {}),
                    ParsedPathElem("interface", {}),
                    ParsedPathElem("counter", {}),
                    ParsedPathElem("eth", {}),
                    ParsedPathElem("slice", {}),
                    ParsedPathElem("phy", {"intf": primary_if.name}),
                    ParsedPathElem("currentStatistics", {}),
                )
                payload = {
                    "intfId": primary_if.name,
                    "operStatus": primary_if.oper_status,
                    "inOctets": primary_if.counters.in_octets,
                    "outOctets": primary_if.counters.out_octets,
                    "inUcastPkts": primary_if.counters.in_unicast_pkts,
                    "outDiscards": primary_if.counters.out_discards,
                }
                return [
                    ResolvedSensorSample(
                        sensor_id="eos_native_if_counters",
                        concrete_path=ParsedGnmiPath(origin, snap.device_id, c_elems),
                        payload=payload,
                        yang_module="eos_native",
                    )
                ]

        # 4. Juniper Junos Native (origin="junos")
        if origin == "junos":
            if "optics" in names:
                c_elems = (
                    ParsedPathElem("junos", {}),
                    ParsedPathElem("system", {}),
                    ParsedPathElem("linecard", {}),
                    ParsedPathElem("optics", {"name": primary_opt.interface_name}),
                )
                payload = {
                    "name": primary_opt.interface_name,
                    "laser-rx-optical-power-dbm": primary_opt.rx_power_dbm,
                    "laser-output-power-dbm": primary_opt.tx_power_dbm,
                    "laser-bias-current": primary_opt.laser_bias_ma,
                }
                return [
                    ResolvedSensorSample(
                        sensor_id="junos_native_optics",
                        concrete_path=ParsedGnmiPath(origin, snap.device_id, c_elems),
                        payload=payload,
                        yang_module="junos-telemetry-interface",
                    )
                ]
            if "qmon" in names:
                c_elems = (
                    ParsedPathElem("junos", {}),
                    ParsedPathElem("system", {}),
                    ParsedPathElem("linecard", {}),
                    ParsedPathElem("qmon", {"interface": primary_q.interface_id}),
                )
                payload = {
                    "interface": primary_q.interface_id,
                    "allocated-buffer-size": primary_q.max_queue_len,
                    "tail-drop-packets": primary_q.dropped_pkts,
                }
                return [
                    ResolvedSensorSample(
                        sensor_id="junos_native_qmon",
                        concrete_path=ParsedGnmiPath(origin, snap.device_id, c_elems),
                        payload=payload,
                        yang_module="junos-telemetry-interface",
                    )
                ]
            if "bgp" in names:
                c_elems = (
                    ParsedPathElem("junos", {}),
                    ParsedPathElem("services", {}),
                    ParsedPathElem("bgp", {}),
                    ParsedPathElem("neighbors", {}),
                    ParsedPathElem("neighbor", {"neighbor-address": primary_bgp.neighbor_address}),
                )
                payload = {
                    "neighbor-address": primary_bgp.neighbor_address,
                    "session-state": primary_bgp.session_state,
                    "active-prefix-count": primary_bgp.prefixes_installed,
                }
                return [
                    ResolvedSensorSample(
                        sensor_id="junos_native_bgp",
                        concrete_path=ParsedGnmiPath(origin, snap.device_id, c_elems),
                        payload=payload,
                        yang_module="junos-telemetry-interface",
                    )
                ]
            if "interface" in names:
                c_elems = (
                    ParsedPathElem("junos", {}),
                    ParsedPathElem("system", {}),
                    ParsedPathElem("linecard", {}),
                    ParsedPathElem("interface", {"name": primary_if.name}),
                    ParsedPathElem("statistics", {}),
                )
                payload = {
                    "name": primary_if.name,
                    "oper-status": primary_if.oper_status,
                    "ibytes": primary_if.counters.in_octets,
                    "obytes": primary_if.counters.out_octets,
                    "ipackets": primary_if.counters.in_unicast_pkts,
                    "opackets": primary_if.counters.out_unicast_pkts,
                }
                return [
                    ResolvedSensorSample(
                        sensor_id="junos_native_if_stats",
                        concrete_path=ParsedGnmiPath(origin, snap.device_id, c_elems),
                        payload=payload,
                        yang_module="junos-telemetry-interface",
                    )
                ]

        raise GnmiPathNotFoundError(
            f"UNSUPPORTED_PATH: Native path {path.canonical_xpath!r} for origin {origin!r} not found"
        )
