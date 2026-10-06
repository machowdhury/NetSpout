# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/transport_native_flow.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""
NetSpout Native Flow UDP Transport Engine.
Exports protocol-correct NetFlow v9 and IPFIX binary datagrams over UDP
to network flow collectors (Splunk Stream, ElastiFlow, nProbe).
Conforms to Gate 11 Architecture Section 4, 10, 11 and Threat Model.
"""

import logging
import socket
import time
from typing import Any, List, Optional, Tuple

from netspout_core.models import FlowRecord, TransportResult, TransportErrorType
from netspout_core.exporter_session import ExporterSession
from netspout_core.netflow_v9_encoder import NetFlowV9Encoder
from netspout_core.ipfix_encoder import IPFIXEncoder
from netspout_core.transport_safety import (
    validate_destination_target,
    DestinationSecurityException,
    RateLimitExceededException
)
from netspout_core.rate_limiter import TokenBucketRateLimiter

logger = logging.getLogger("netspout.transport.native")

CIRCUIT_BREAKER_THRESHOLD = 5


class NativeFlowTransport:
    """
    Manages bounded UDP export of binary NetFlow v9 and IPFIX datagrams.
    Enforces RFC 1918 safe-by-default destination rules, token-bucket pacing,
    and circuit breaking on repeated socket failures.
    """
    def __init__(
        self,
        destination_host: str = "127.0.0.1",
        destination_port: int = 4739,
        protocol: str = "IPFIX",
        rate_pps: int = 100,
        max_packets_per_run: int = 10000,
        allow_privileged_ports: bool = False,
        template_refresh_policy: str = "EVERY_BURST",
        test_mode: bool = False
    ):
        self.destination_host = destination_host
        self.destination_port = destination_port
        self.protocol = protocol.upper()
        self.template_refresh_policy = template_refresh_policy.upper()
        self.test_mode = test_mode
        self.allow_privileged_ports = allow_privileged_ports

        # Validate security boundaries before socket instantiation
        self.resolved_ip = validate_destination_target(
            host=destination_host,
            port=destination_port,
            allow_privileged_ports=allow_privileged_ports
        )

        self.rate_limiter = TokenBucketRateLimiter(
            rate_pps=rate_pps,
            max_packets_per_run=max_packets_per_run
        )

    @classmethod
    def from_config(cls, config: Any, test_mode: bool = False) -> "NativeFlowTransport":
        """Factory constructor from NativeFlowConfig model."""
        protocol_str = getattr(config.protocol, "value", str(config.protocol)).upper()
        port = config.netflow_port if protocol_str == "NETFLOW_V9" else config.ipfix_port
        policy_str = getattr(config.template_refresh_policy, "value", str(config.template_refresh_policy))
        return cls(
            destination_host=config.collector_host,
            destination_port=port,
            protocol=protocol_str,
            rate_pps=config.rate_limit_pps,
            max_packets_per_run=config.packet_cap,
            allow_privileged_ports=False,
            template_refresh_policy=policy_str,
            test_mode=test_mode
        )

    def test_connectivity(self) -> Tuple[bool, str]:
        """
        Tests if a UDP socket can be bound and targeted toward the destination.
        Note: Standard UDP is connectionless; socket creation proves OS capability,
        not collector receipt.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.0)
            sock.close()
            return True, f"UDP socket feasibility confirmed for {self.resolved_ip}:{self.destination_port}"
        except Exception as exc:
            return False, f"Failed to initialize UDP socket: {exc}"

    def send_batch(
        self,
        records: List[FlowRecord],
        session: ExporterSession,
        force_template: bool = False
    ) -> TransportResult:
        """
        Encodes and transmits a batch of FlowRecord objects over UDP.
        Guarantees strict MTU bound (<1400 bytes), sequence accounting, and rate limiting.
        """
        start_time = time.time()
        result = TransportResult(
            transport_type=f"{self.protocol}_UDP",
            destination_host=self.resolved_ip,
            destination_port=self.destination_port,
            records_received=len(records)
        )

        include_template = force_template or session.should_send_template(policy=self.template_refresh_policy)
        seq_start = session.sequence_number
        result.sequence_start = seq_start

        # 1. Encode records into MTU-safe datagram packets
        try:
            if self.protocol == "NETFLOW_V9":
                packets = NetFlowV9Encoder.encode_batch(
                    records=records,
                    session=session,
                    include_template=include_template
                )
            elif self.protocol == "IPFIX":
                packets = IPFIXEncoder.encode_batch(
                    records=records,
                    session=session,
                    include_template=include_template
                )
            else:
                result.encoding_failures += len(records)
                result.errors.append(f"Unsupported flow protocol: {self.protocol}")
                result.error_types.append(TransportErrorType.ENCODING_FAILED.value)
                return result

            result.records_encoded = len(records)
            if include_template:
                result.templates_sent = 1
                session.record_template_sent()

        except Exception as exc:
            result.encoding_failures = len(records)
            result.errors.append(f"Encoding failed: {exc}")
            result.error_types.append(TransportErrorType.ENCODING_FAILED.value)
            return result

        result.datagrams_attempted = len(packets)

        # 2. Transmit datagrams over UDP socket
        sock = None
        consecutive_errors = 0
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(2.0)

            for pkt in packets:
                # Rate limit pacing
                try:
                    self.rate_limiter.acquire(1, test_mode=self.test_mode)
                except RateLimitExceededException as rle:
                    result.errors.append(str(rle))
                    result.error_types.append(TransportErrorType.RATE_LIMIT_EXCEEDED.value)
                    break

                # Send datagram
                try:
                    bytes_sent = sock.sendto(pkt, (self.resolved_ip, self.destination_port))
                    result.datagrams_sent += 1
                    result.bytes_sent += bytes_sent
                    consecutive_errors = 0
                    session.record_packet_sent(
                        record_count=len(records) // max(1, len(packets)),
                        byte_count=bytes_sent
                    )
                except Exception as sock_err:
                    result.send_failures += 1
                    consecutive_errors += 1
                    result.errors.append(f"UDP sendto error: {sock_err}")
                    result.error_types.append(TransportErrorType.SEND_FAILED.value)

                    if consecutive_errors >= CIRCUIT_BREAKER_THRESHOLD:
                        circuit_msg = (
                            f"Circuit breaker tripped after {consecutive_errors} consecutive UDP send errors. "
                            f"Aborting transmission batch."
                        )
                        result.errors.append(circuit_msg)
                        result.error_types.append(TransportErrorType.CIRCUIT_BREAKER_TRIGGERED.value)
                        logger.error(circuit_msg)
                        break

        except Exception as net_exc:
            result.send_failures = len(packets) - result.datagrams_sent
            result.errors.append(f"Socket initialization/runtime error: {net_exc}")
            result.error_types.append(TransportErrorType.SOCKET_CREATE_FAILED.value)
        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

        result.sequence_end = session.sequence_number
        result.elapsed_ms = (time.time() - start_time) * 1000.0

        if result.datagrams_sent < result.datagrams_attempted and result.datagrams_sent > 0:
            result.error_types.append(TransportErrorType.PARTIAL_EXPORT.value)

        return result
