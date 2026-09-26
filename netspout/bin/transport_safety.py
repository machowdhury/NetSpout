# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/transport_safety.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""
NetSpout Native Transport Safety Controls & Destination Validation.
Enforces RFC 1918 / Loopback safe-by-default export policy, public destination blocking,
and privileged port controls.
Conforms to Gate 11 Threat Model and Safety Specification.
"""

import ipaddress
import logging
import os
import socket
from typing import List

logger = logging.getLogger("netspout.security")

# Permitted Safe Destination Ranges
SAFE_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fe80::/10"),
]

# Standard allowed native flow ports
RECOMMENDED_FLOW_PORTS = {2055, 4739, 9995, 9996, 6343, 514}


class DestinationSecurityException(PermissionError):
    """
    Raised when an unapproved, public, or privileged destination is targeted
    for native flow telemetry export without explicit authorization.
    """
    pass


class RateLimitExceededException(RuntimeError):
    """Raised when simulation attempts to exceed maximum configured packet ceiling."""
    pass


def is_safe_ip(ip_addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Checks whether an IP address belongs to RFC 1918, Loopback, or Link-Local."""
    return any(ip_addr in network for network in SAFE_NETWORKS)


def validate_destination_target(
    host: str,
    port: int,
    allow_privileged_ports: bool = False
) -> str:
    """
    Validates that the target host resolves strictly to a permitted private or loopback IP.
    Blocks public routable IPs unless explicit environment override is provided.
    Blocks privileged ports (< 1024) unless explicitly authorized.

    Returns the resolved canonical IP string.
    Raises DestinationSecurityException on security violations.
    """
    # 1. Port bounds check
    if not (1 <= port <= 65535):
        raise DestinationSecurityException(f"Destination port out of range 1..65535: {port}")

    if port < 1024 and not allow_privileged_ports and port != 514:
        raise DestinationSecurityException(
            f"Privileged destination port {port} (< 1024) is blocked by default. "
            f"NetFlow/IPFIX should target high collector ports (e.g. 2055, 4739, 9995)."
        )

    # 2. Host resolution
    try:
        # Check if already a valid IP string
        try:
            target_ip = ipaddress.ip_address(host)
            resolved_ip_str = str(target_ip)
        except ValueError:
            # Resolve DNS hostname
            resolved_ip_str = socket.gethostbyname(host)
            target_ip = ipaddress.ip_address(resolved_ip_str)
    except Exception as exc:
        raise DestinationSecurityException(f"Failed to resolve target destination host '{host}': {exc}")

    # 3. Check against safe private / loopback networks
    if is_safe_ip(target_ip):
        return resolved_ip_str

    # 4. Check for explicit environment override
    allow_public = os.environ.get("NETSPOUT_ALLOW_PUBLIC_EXPORT", "").lower() in ("true", "1", "yes")
    if allow_public:
        logger.warning(
            "SECURITY AUDIT: Outbound native flow transmission to PUBLIC IP %s:%d explicitly permitted via NETSPOUT_ALLOW_PUBLIC_EXPORT.",
            resolved_ip_str, port
        )
        return resolved_ip_str

    raise DestinationSecurityException(
        f"SECURITY VIOLATION: Native flow transmission to public IP '{resolved_ip_str}' is forbidden by default. "
        f"NetSpout only permits export to RFC 1918 private networks and loopback addresses. "
        f"To override for designated lab environments, set environment variable NETSPOUT_ALLOW_PUBLIC_EXPORT=true."
    )
