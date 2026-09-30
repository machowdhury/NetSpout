"""
NetSpout Gate 13B — Multi-Vendor gNMI / OpenConfig Target Profiles.

Defines the four canonical NOS telemetry profiles:
  - CISCO_IOS_XR
  - CISCO_IOS_XE
  - ARISTA_EOS
  - JUNIPER_JUNOS

Includes target resolution for canonical topology nodes (e.g. openconfig_core
and service_provider_cisco), supported YANG models for CapabilitiesResponse,
supported origins, and representative interface inventories.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Tuple


class VendorProfileId(str, Enum):
    CISCO_IOS_XR = "CISCO_IOS_XR"
    CISCO_IOS_XE = "CISCO_IOS_XE"
    ARISTA_EOS = "ARISTA_EOS"
    JUNIPER_JUNOS = "JUNIPER_JUNOS"


@dataclass(frozen=True)
class ModelDataSpec:
    name: str
    organization: str
    version: str


@dataclass(frozen=True)
class DeviceTargetConfig:
    device_id: str
    hostname: str
    mgmt_ip: str
    vendor_profile: VendorProfileId
    interfaces: Tuple[str, ...]
    lag_interface: str
    bgp_neighbors: Tuple[Tuple[str, int, str], ...]  # (peer_ip, peer_as, description)
    lldp_neighbors: Tuple[Tuple[str, str, str, str], ...]  # (local_if, remote_sys, remote_port, remote_mgmt_ip)
    primary_uplink: str
    evpn_supported: bool = False


@dataclass(frozen=True)
class VendorProfile:
    profile_id: VendorProfileId
    vendor_name: str
    nos_name: str
    default_gnmi_port: int
    gnmi_version: str
    supported_encodings: Tuple[str, ...]
    supported_origins: Tuple[str, ...]
    representative_interfaces: Tuple[str, ...]
    supported_models: Tuple[ModelDataSpec, ...]

    def supports_origin(self, origin: str) -> bool:
        norm = (origin or "openconfig").strip()
        if norm == "":
            norm = "openconfig"
        return norm in self.supported_origins


GNMI_SEMVER = "0.10.0"
SUPPORTED_ENCODINGS: Tuple[str, ...] = ("JSON", "PROTO", "JSON_IETF")

COMMON_OPENCONFIG_MODELS: Tuple[ModelDataSpec, ...] = (
    ModelDataSpec("openconfig-interfaces", "OpenConfig working group", "2022-10-25"),
    ModelDataSpec("openconfig-if-ip", "OpenConfig working group", "2022-05-10"),
    ModelDataSpec("openconfig-if-aggregate", "OpenConfig working group", "2022-06-28"),
    ModelDataSpec("openconfig-lacp", "OpenConfig working group", "2022-06-28"),
    ModelDataSpec("openconfig-lldp", "OpenConfig working group", "2022-05-10"),
    ModelDataSpec("openconfig-network-instance", "OpenConfig working group", "2022-09-15"),
    ModelDataSpec("openconfig-bgp", "OpenConfig working group", "2022-09-20"),
    ModelDataSpec("openconfig-aft", "OpenConfig working group", "2022-06-16"),
    ModelDataSpec("openconfig-qos", "OpenConfig working group", "2022-09-13"),
    ModelDataSpec("openconfig-platform", "OpenConfig working group", "2022-12-20"),
    ModelDataSpec("openconfig-platform-transceiver", "OpenConfig working group", "2022-07-28"),
    ModelDataSpec("openconfig-terminal-device", "OpenConfig working group", "2022-07-28"),
    ModelDataSpec("openconfig-system", "OpenConfig working group", "2022-10-19"),
)

VENDOR_PROFILES: Dict[VendorProfileId, VendorProfile] = {
    VendorProfileId.CISCO_IOS_XR: VendorProfile(
        profile_id=VendorProfileId.CISCO_IOS_XR,
        vendor_name="Cisco Systems, Inc.",
        nos_name="Cisco IOS XR",
        default_gnmi_port=57400,
        gnmi_version="0.10.0",
        supported_encodings=("JSON_IETF", "JSON", "PROTO"),
        supported_origins=(
            "openconfig",
            "Cisco-IOS-XR-infra-statsd-oper",
            "Cisco-IOS-XR-pfi-im-cmd-oper",
            "Cisco-IOS-XR-ipv4-bgp-oper",
            "Cisco-IOS-XR-qos-ma-oper",
            "Cisco-IOS-XR-controller-optics-oper",
            "Cisco-IOS-XR-wdsysmon-fd-oper",
            "Cisco-IOS-XR-plat-chas-invmgr-oper",
            "Cisco-IOS-XR-ethernet-lldp-oper",
            "Cisco-IOS-XR-bundlemgr-oper",
            "Cisco-IOS-XR-fib-common-oper",
        ),
        representative_interfaces=(
            "HundredGigE0/0/0/0",
            "Bundle-Ether10",
            "Loopback0",
            "MgmtEth0/RP0/CPU0/0",
        ),
        supported_models=COMMON_OPENCONFIG_MODELS + (
            ModelDataSpec("Cisco-IOS-XR-infra-statsd-oper", "Cisco Systems, Inc.", "7.9.1"),
            ModelDataSpec("Cisco-IOS-XR-pfi-im-cmd-oper", "Cisco Systems, Inc.", "7.9.1"),
            ModelDataSpec("Cisco-IOS-XR-ipv4-bgp-oper", "Cisco Systems, Inc.", "7.9.1"),
            ModelDataSpec("Cisco-IOS-XR-qos-ma-oper", "Cisco Systems, Inc.", "7.9.1"),
            ModelDataSpec("Cisco-IOS-XR-controller-optics-oper", "Cisco Systems, Inc.", "7.9.1"),
            ModelDataSpec("Cisco-IOS-XR-wdsysmon-fd-oper", "Cisco Systems, Inc.", "7.9.1"),
            ModelDataSpec("Cisco-IOS-XR-plat-chas-invmgr-oper", "Cisco Systems, Inc.", "7.9.1"),
            ModelDataSpec("Cisco-IOS-XR-ethernet-lldp-oper", "Cisco Systems, Inc.", "7.9.1"),
            ModelDataSpec("Cisco-IOS-XR-bundlemgr-oper", "Cisco Systems, Inc.", "7.9.1"),
            ModelDataSpec("Cisco-IOS-XR-fib-common-oper", "Cisco Systems, Inc.", "7.9.1"),
        ),
    ),
    VendorProfileId.CISCO_IOS_XE: VendorProfile(
        profile_id=VendorProfileId.CISCO_IOS_XE,
        vendor_name="Cisco Systems, Inc.",
        nos_name="Cisco IOS XE",
        default_gnmi_port=57400,
        gnmi_version="0.10.0",
        supported_encodings=("JSON_IETF", "JSON", "PROTO"),
        supported_origins=(
            "openconfig",
            "Cisco-IOS-XE-interfaces-oper",
            "Cisco-IOS-XE-bgp-oper",
            "Cisco-IOS-XE-ospf-oper",
            "Cisco-IOS-XE-environment-oper",
            "Cisco-IOS-XE-transceiver-oper",
            "Cisco-IOS-XE-process-cpu-oper",
            "Cisco-IOS-XE-memory-oper",
            "Cisco-IOS-XE-lldp-oper",
            "Cisco-IOS-XE-lacp-oper",
            "Cisco-IOS-XE-fib-oper",
        ),
        representative_interfaces=(
            "FortyGigE1/0/1",
            "TenGigabitEthernet1/0/1",
            "Port-channel1",
            "Vlan100",
        ),
        supported_models=COMMON_OPENCONFIG_MODELS + (
            ModelDataSpec("Cisco-IOS-XE-interfaces-oper", "Cisco Systems, Inc.", "17.12.1"),
            ModelDataSpec("Cisco-IOS-XE-bgp-oper", "Cisco Systems, Inc.", "17.12.1"),
            ModelDataSpec("Cisco-IOS-XE-ospf-oper", "Cisco Systems, Inc.", "17.12.1"),
            ModelDataSpec("Cisco-IOS-XE-environment-oper", "Cisco Systems, Inc.", "17.12.1"),
            ModelDataSpec("Cisco-IOS-XE-transceiver-oper", "Cisco Systems, Inc.", "17.12.1"),
            ModelDataSpec("Cisco-IOS-XE-process-cpu-oper", "Cisco Systems, Inc.", "17.12.1"),
            ModelDataSpec("Cisco-IOS-XE-memory-oper", "Cisco Systems, Inc.", "17.12.1"),
            ModelDataSpec("Cisco-IOS-XE-lldp-oper", "Cisco Systems, Inc.", "17.12.1"),
            ModelDataSpec("Cisco-IOS-XE-lacp-oper", "Cisco Systems, Inc.", "17.12.1"),
            ModelDataSpec("Cisco-IOS-XE-fib-oper", "Cisco Systems, Inc.", "17.12.1"),
        ),
    ),
    VendorProfileId.ARISTA_EOS: VendorProfile(
        profile_id=VendorProfileId.ARISTA_EOS,
        vendor_name="Arista Networks, Inc.",
        nos_name="Arista EOS",
        default_gnmi_port=6030,
        gnmi_version="0.10.0",
        supported_encodings=("JSON_IETF", "JSON", "PROTO"),
        supported_origins=("openconfig", "eos_native"),
        representative_interfaces=(
            "Ethernet1/1",
            "Ethernet2/1",
            "Port-Channel10",
            "Vxlan1",
            "Management1",
        ),
        supported_models=COMMON_OPENCONFIG_MODELS + (
            ModelDataSpec("arista-exp-eos-lanz", "Arista Networks, Inc.", "4.31.2F"),
            ModelDataSpec("eos_native", "Arista Networks, Inc.", "4.31.2F"),
        ),
    ),
    VendorProfileId.JUNIPER_JUNOS: VendorProfile(
        profile_id=VendorProfileId.JUNIPER_JUNOS,
        vendor_name="Juniper Networks, Inc.",
        nos_name="Juniper Junos",
        default_gnmi_port=32767,
        gnmi_version="0.10.0",
        supported_encodings=("JSON_IETF", "JSON", "PROTO"),
        supported_origins=("openconfig", "junos"),
        representative_interfaces=(
            "et-0/0/0",
            "et-0/0/1",
            "xe-0/0/1",
            "ae0",
            "lo0.0",
        ),
        supported_models=COMMON_OPENCONFIG_MODELS + (
            ModelDataSpec("junos-telemetry-interface", "Juniper Networks, Inc.", "23.4R1"),
        ),
    ),
}


CANONICAL_DEVICE_TARGETS: Dict[str, DeviceTargetConfig] = {
    "node-cisco8k": DeviceTargetConfig(
        device_id="node-cisco8k",
        hostname="Cisco-8000-Core01",
        mgmt_ip="10.100.1.1",
        vendor_profile=VendorProfileId.CISCO_IOS_XR,
        interfaces=(
            "HundredGigE0/0/0/0",
            "Bundle-Ether10",
            "Loopback0",
            "MgmtEth0/RP0/CPU0/0",
        ),
        lag_interface="Bundle-Ether10",
        bgp_neighbors=(
            ("10.100.1.2", 65002, "Juniper-PTX10K-PE01"),
            ("10.100.2.1", 65003, "Arista-7280R-Spine"),
        ),
        lldp_neighbors=(
            ("HundredGigE0/0/0/0", "Juniper-PTX10K-PE01", "et-0/0/0", "10.100.1.2"),
        ),
        primary_uplink="HundredGigE0/0/0/0",
        evpn_supported=False,
    ),
    "cisco-asr9k-pe1": DeviceTargetConfig(
        device_id="cisco-asr9k-pe1",
        hostname="cisco-asr9k-pe1",
        mgmt_ip="10.255.0.11",
        vendor_profile=VendorProfileId.CISCO_IOS_XR,
        interfaces=(
            "HundredGigE0/0/0/0",
            "HundredGigE0/0/0/1",
            "Bundle-Ether10",
            "Loopback0",
            "MgmtEth0/RP0/CPU0/0",
        ),
        lag_interface="Bundle-Ether10",
        bgp_neighbors=(
            ("10.255.0.2", 65000, "node-ncs5500-spine01"),
            ("10.255.0.3", 65000, "node-ncs5500-spine02"),
        ),
        lldp_neighbors=(
            ("HundredGigE0/0/0/0", "node-ncs5500-spine01", "HundredGigE0/1/0/0", "10.255.0.2"),
            ("HundredGigE0/0/0/1", "node-ncs5500-spine02", "HundredGigE0/1/0/0", "10.255.0.3"),
        ),
        primary_uplink="HundredGigE0/0/0/0",
        evpn_supported=False,
    ),
    "node-juniper-ptx": DeviceTargetConfig(
        device_id="node-juniper-ptx",
        hostname="Juniper-PTX10K-PE01",
        mgmt_ip="10.100.1.2",
        vendor_profile=VendorProfileId.JUNIPER_JUNOS,
        interfaces=(
            "et-0/0/0",
            "et-0/0/1",
            "xe-0/0/1",
            "ae0",
            "lo0.0",
        ),
        lag_interface="ae0",
        bgp_neighbors=(
            ("10.100.1.1", 65001, "Cisco-8000-Core01"),
            ("10.100.2.1", 65003, "Arista-7280R-Spine"),
        ),
        lldp_neighbors=(
            ("et-0/0/0", "Cisco-8000-Core01", "HundredGigE0/0/0/0", "10.100.1.1"),
            ("et-0/0/1", "Arista-7280R-Spine", "Ethernet1/1", "10.100.2.1"),
        ),
        primary_uplink="et-0/0/0",
        evpn_supported=False,
    ),
    "node-arista-spine": DeviceTargetConfig(
        device_id="node-arista-spine",
        hostname="Arista-7280R-Spine",
        mgmt_ip="10.100.2.1",
        vendor_profile=VendorProfileId.ARISTA_EOS,
        interfaces=(
            "Ethernet1/1",
            "Ethernet2/1",
            "Port-Channel10",
            "Vxlan1",
            "Management1",
        ),
        lag_interface="Port-Channel10",
        bgp_neighbors=(
            ("10.100.1.2", 65002, "Juniper-PTX10K-PE01"),
            ("10.100.2.2", 65004, "Catalyst-9600-Leaf"),
        ),
        lldp_neighbors=(
            ("Ethernet1/1", "Juniper-PTX10K-PE01", "et-0/0/1", "10.100.1.2"),
            ("Ethernet2/1", "Catalyst-9600-Leaf", "FortyGigE1/0/1", "10.100.2.2"),
        ),
        primary_uplink="Ethernet1/1",
        evpn_supported=True,
    ),
    "node-cat-leaf": DeviceTargetConfig(
        device_id="node-cat-leaf",
        hostname="Catalyst-9600-Leaf",
        mgmt_ip="10.100.2.2",
        vendor_profile=VendorProfileId.CISCO_IOS_XE,
        interfaces=(
            "FortyGigE1/0/1",
            "TenGigabitEthernet1/0/1",
            "Port-channel1",
            "Vlan100",
        ),
        lag_interface="Port-channel1",
        bgp_neighbors=(
            ("10.100.2.1", 65003, "Arista-7280R-Spine"),
        ),
        lldp_neighbors=(
            ("FortyGigE1/0/1", "Arista-7280R-Spine", "Ethernet2/1", "10.100.2.1"),
        ),
        primary_uplink="FortyGigE1/0/1",
        evpn_supported=False,
    ),
}

TARGET_ALIASES: Dict[str, str] = {
    "node-cisco8k": "node-cisco8k",
    "Cisco-8000-Core01": "node-cisco8k",
    "cisco-8000-core01": "node-cisco8k",
    "CISCO_IOS_XR": "node-cisco8k",
    "cisco-asr9k-pe1": "cisco-asr9k-pe1",
    "node-juniper-ptx": "node-juniper-ptx",
    "Juniper-PTX10K-PE01": "node-juniper-ptx",
    "juniper-ptx10k-pe01": "node-juniper-ptx",
    "JUNIPER_JUNOS": "node-juniper-ptx",
    "node-arista-spine": "node-arista-spine",
    "Arista-7280R-Spine": "node-arista-spine",
    "arista-7280r-spine": "node-arista-spine",
    "ARISTA_EOS": "node-arista-spine",
    "node-cat-leaf": "node-cat-leaf",
    "Catalyst-9600-Leaf": "node-cat-leaf",
    "catalyst-9600-leaf": "node-cat-leaf",
    "CISCO_IOS_XE": "node-cat-leaf",
}


def resolve_target_device(target: Optional[str]) -> Optional[DeviceTargetConfig]:
    """Resolves a gNMI Path.target or metadata target string to a canonical DeviceTargetConfig."""
    if not target or target.strip() == "":
        return CANONICAL_DEVICE_TARGETS["node-cisco8k"]
    cleaned = target.strip()
    canonical_id = TARGET_ALIASES.get(cleaned)
    if canonical_id and canonical_id in CANONICAL_DEVICE_TARGETS:
        return CANONICAL_DEVICE_TARGETS[canonical_id]
    return None


OPENCONFIG_CORE_DEVICES = CANONICAL_DEVICE_TARGETS
get_device_target = resolve_target_device


def list_scenario_devices() -> List[DeviceTargetConfig]:
    return list(CANONICAL_DEVICE_TARGETS.values())


def get_vendor_profile(profile_id: Any) -> VendorProfile:
    if isinstance(profile_id, VendorProfileId):
        return VENDOR_PROFILES[profile_id]
    return VENDOR_PROFILES[VendorProfileId(str(profile_id))]

