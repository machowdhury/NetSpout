"""
NetSpout Gate 12B — Safe Native SNMPv2c UDP Transport & Loopback Test Receiver.
Implements:
  - Strict destination validation via transport_safety.py (default 127.0.0.1:1162; blocks public, multicast, broadcast)
  - Token-bucket rate limiting (Traps: 50 pps default / 250 pps max; Informs: 25 pps default / 100 pps max)
  - Per-run packet caps (1,000 default / 5,000 hard max)
  - 1,472-byte UDP payload ceiling (zero silent IP fragmentation)
  - Honest TRAP evidence progression: GENERATED -> ENCODED -> SENT -> RECEIVER_OBSERVED (SENT != RECEIVER_OBSERVED)
  - Honest INFORM acknowledgement & retry state machine: GENERATED -> ENCODED -> SENT -> ACKNOWLEDGED -> RECEIVER_OBSERVED
  - Bounded 127.0.0.1 Loopback Test Receiver with ACK delay, ACK drop, wrong request-id, malformed response injection,
    and standard libpcap export for independent TShark/Wireshark verification.
"""

import ipaddress
import socket
import struct
import threading
import time
from typing import Any, Dict, List, Optional, Set, Tuple, Union

try:
    from netspout_core.models import (
        SnmpEvidenceStage,
        SnmpInform,
        SnmpMessage,
        SnmpPduType,
        SnmpResponse,
        SnmpTransportResult,
        SnmpTrap,
        TransportErrorType,
    )
    from netspout_core.rate_limiter import TokenBucketRateLimiter
    from netspout_core.snmp_ber import (
        MAX_SNMP_UDP_PAYLOAD_BYTES,
        SnmpBerDecodeError,
        SnmpBerDecoder,
        SnmpBerEncodeError,
        SnmpBerEncoder,
        SnmpCommunityMismatchError,
        SnmpPayloadSizeError,
        UnsupportedSnmpVersionError,
    )
    from netspout_core.transport_safety import (
        DestinationSecurityException,
        validate_destination_target,
    )
except ImportError:
    try:
        from app.models import (
            SnmpEvidenceStage,
            SnmpInform,
            SnmpMessage,
            SnmpPduType,
            SnmpResponse,
            SnmpTransportResult,
            SnmpTrap,
            TransportErrorType,
        )
        from app.rate_limiter import TokenBucketRateLimiter
        from app.snmp_ber import (
            MAX_SNMP_UDP_PAYLOAD_BYTES,
            SnmpBerDecodeError,
            SnmpBerDecoder,
            SnmpBerEncodeError,
            SnmpBerEncoder,
            SnmpCommunityMismatchError,
            SnmpPayloadSizeError,
            UnsupportedSnmpVersionError,
        )
        from app.transport_safety import (
            DestinationSecurityException,
            validate_destination_target,
        )
    except ImportError:
        from models import (
            SnmpEvidenceStage,
            SnmpInform,
            SnmpMessage,
            SnmpPduType,
            SnmpResponse,
            SnmpTransportResult,
            SnmpTrap,
            TransportErrorType,
        )
        from rate_limiter import TokenBucketRateLimiter
        from snmp_ber import (
            MAX_SNMP_UDP_PAYLOAD_BYTES,
            SnmpBerDecodeError,
            SnmpBerDecoder,
            SnmpBerEncodeError,
            SnmpBerEncoder,
            SnmpCommunityMismatchError,
            SnmpPayloadSizeError,
            UnsupportedSnmpVersionError,
        )
        from transport_safety import (
            DestinationSecurityException,
            validate_destination_target,
        )

# Gate 12 / 12B Hard Safety Ceilings
DEFAULT_SNMP_HOST = "127.0.0.1"
DEFAULT_SNMP_TRAP_PORT = 1162

DEFAULT_TRAP_RATE_PPS = 50
MAX_TRAP_RATE_PPS = 250

DEFAULT_INFORM_RATE_PPS = 25
MAX_INFORM_RATE_PPS = 100

DEFAULT_SNMP_PACKET_CAP = 1000
MAX_SNMP_PACKET_CAP = 5000

DEFAULT_INFORM_TIMEOUT_MS = 1500
DEFAULT_INFORM_MAX_RETRIES = 2


def _ipv4_checksum(header: bytes) -> int:
    if len(header) % 2 == 1:
        header += b"\x00"
    total = 0
    for i in range(0, len(header), 2):
        word = (header[i] << 8) + header[i + 1]
        total += word
        total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF


def write_snmp_pcap(
    filepath: str,
    packets: List[Union[bytes, Dict[str, Any]]],
    default_src_ip: str = "127.0.0.1",
    default_dst_ip: str = "127.0.0.1",
    default_src_port: int = 54161,
    default_dst_port: int = DEFAULT_SNMP_TRAP_PORT,
) -> str:
    """
    Writes a list of raw SNMP UDP payloads (or packet dicts with src_ip, dst_ip, src_port, dst_port, payload, timestamp)
    to a standard libpcap (DLT_EN10MB = 1) file for independent TShark / Wireshark protocol verification.
    """
    # Global PCAP header: magic=0xa1b2c3d4, v_major=2, v_minor=4, thiszone=0, sigfigs=0, snaplen=65535, network=1 (Ethernet)
    global_hdr = struct.pack("<IHHiIII", 0xA1B2C3D4, 2, 4, 0, 0, 65535, 1)

    with open(filepath, "wb") as f:
        f.write(global_hdr)
        base_ts = time.time()

        for idx, item in enumerate(packets):
            if isinstance(item, (bytes, bytearray)):
                payload = bytes(item)
                src_ip = default_src_ip
                dst_ip = default_dst_ip
                src_port = default_src_port
                dst_port = default_dst_port
                pkt_ts = base_ts + (idx * 0.001)
            else:
                payload = bytes(item["payload"])
                src_ip = item.get("src_ip", default_src_ip)
                dst_ip = item.get("dst_ip", default_dst_ip)
                src_port = int(item.get("src_port", default_src_port))
                dst_port = int(item.get("dst_port", default_dst_port))
                pkt_ts = float(item.get("timestamp", base_ts + (idx * 0.001)))

            # 1. Ethernet II header (14 bytes: dst_mac, src_mac, ethertype=0x0800 IPv4)
            eth_hdr = b"\x00\x00\x5e\x00\x53\x02\x00\x00\x5e\x00\x53\x01\x08\x00"

            # 2. UDP header (8 bytes: src_port, dst_port, udp_len, checksum=0)
            udp_len = 8 + len(payload)
            udp_hdr = struct.pack("!HHHH", src_port, dst_port, udp_len, 0)

            # 3. IPv4 header (20 bytes)
            ip_total_len = 20 + udp_len
            src_ip_bytes = socket.inet_aton(src_ip)
            dst_ip_bytes = socket.inet_aton(dst_ip)
            ip_hdr_no_csum = struct.pack(
                "!BBHHHBBH4s4s",
                0x45,           # Version=4, IHL=5
                0x00,           # DSCP/ECN
                ip_total_len,   # Total Length
                (1000 + idx) & 0xFFFF,
                0x4000,         # Don't Fragment
                64,             # TTL
                17,             # Protocol = UDP (17)
                0,              # Checksum placeholder
                src_ip_bytes,
                dst_ip_bytes,
            )
            ip_csum = _ipv4_checksum(ip_hdr_no_csum)
            ip_hdr = struct.pack(
                "!BBHHHBBH4s4s",
                0x45,
                0x00,
                ip_total_len,
                (1000 + idx) & 0xFFFF,
                0x4000,
                64,
                17,
                ip_csum,
                src_ip_bytes,
                dst_ip_bytes,
            )

            frame = eth_hdr + ip_hdr + udp_hdr + payload
            ts_sec = int(pkt_ts)
            ts_usec = int((pkt_ts - ts_sec) * 1_000_000) & 0xFFFFFFFF
            pkt_hdr = struct.pack("<IIII", ts_sec, ts_usec, len(frame), len(frame))
            f.write(pkt_hdr)
            f.write(frame)

    return filepath


class LoopbackSnmpTestReceiver:
    """
    Bounded Gate 12B Local Loopback SNMPv2c Test Receiver (127.0.0.1 only).
    Supports:
      - Trapv2 (0xA7) reception and decoding
      - InformRequest (0xA6) reception, deduplication, and Response-PDU (0xA2) acknowledgement
      - Controlled ACK delay (ack_delay_ms)
      - Controlled dropped ACKs (drop_acks_count / drop_all_acks)
      - Wrong request-id injection (inject_wrong_request_id)
      - Malformed response injection (inject_malformed_response)
      - Duplicate ACK simulation (duplicate_ack_count)
      - Wire PCAP capture for independent TShark verification
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 0,
        expected_community: str = "netspout-lab",
        ack_delay_ms: float = 0.0,
        drop_acks_count: int = 0,
        drop_all_acks: bool = False,
        inject_wrong_request_id: Optional[int] = None,
        inject_malformed_response: Optional[bytes] = None,
        duplicate_ack_count: int = 0,
    ):
        if host != "127.0.0.1":
            raise DestinationSecurityException(
                f"LoopbackSnmpTestReceiver may only bind to 127.0.0.1, got {host!r}"
            )
        self.host = host
        self.requested_port = port
        self.bound_port: int = 0
        self.expected_community = expected_community
        self.ack_delay_ms = ack_delay_ms
        self.drop_acks_count = drop_acks_count
        self.drop_all_acks = drop_all_acks
        self.inject_wrong_request_id = inject_wrong_request_id
        self.inject_malformed_response = inject_malformed_response
        self.duplicate_ack_count = duplicate_ack_count

        self._sock: Optional[socket.socket] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()

        # Receiver telemetry & evidence state
        self.packets_received: int = 0
        self.traps_received: int = 0
        self.informs_received: int = 0
        self.duplicate_informs_received: int = 0
        self.responses_sent: int = 0
        self.acks_dropped: int = 0
        self.decode_errors: int = 0
        self.bad_community_count: int = 0
        self.bad_version_count: int = 0
        self.decoded_messages: List[SnmpMessage] = []
        self.deduplicated_messages: List[SnmpMessage] = []
        self.observed_request_ids: List[int] = []
        self._seen_inform_keys: Set[Tuple[str, int]] = set()
        self.captured_frames: List[Dict[str, Any]] = []

    def start(self) -> int:
        if self._running:
            return self.bound_port
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((self.host, self.requested_port))
        sock.settimeout(0.05)
        self.bound_port = sock.getsockname()[1]
        self._sock = sock
        self._running = True
        self._thread = threading.Thread(target=self._serve_loop, daemon=True)
        self._thread.start()
        return self.bound_port

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    def __enter__(self) -> "LoopbackSnmpTestReceiver":
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.stop()

    def _serve_loop(self) -> None:
        while self._running and self._sock:
            try:
                data, addr = self._sock.recvfrom(65535)
            except socket.timeout:
                continue
            except OSError:
                break

            recv_ts = time.time()
            src_ip, src_port = addr[0], addr[1]

            with self._lock:
                self.packets_received += 1
                self.captured_frames.append(
                    {
                        "direction": "IN",
                        "src_ip": src_ip,
                        "dst_ip": self.host,
                        "src_port": src_port,
                        "dst_port": self.bound_port,
                        "payload": bytes(data),
                        "timestamp": recv_ts,
                    }
                )

            try:
                msg = SnmpBerDecoder.decode_message(
                    data, expected_community=self.expected_community
                )
            except SnmpCommunityMismatchError:
                with self._lock:
                    self.bad_community_count += 1
                    self.decode_errors += 1
                continue
            except UnsupportedSnmpVersionError:
                with self._lock:
                    self.bad_version_count += 1
                    self.decode_errors += 1
                continue
            except SnmpBerDecodeError:
                with self._lock:
                    self.decode_errors += 1
                continue

            with self._lock:
                self.decoded_messages.append(msg)
                if msg.request_id not in self.observed_request_ids:
                    self.observed_request_ids.append(msg.request_id)

                if msg.pdu_type == SnmpPduType.SNMPV2_TRAP.value:
                    self.traps_received += 1
                    self.deduplicated_messages.append(msg)
                    continue

                if msg.pdu_type == SnmpPduType.INFORM_REQUEST.value:
                    self.informs_received += 1
                    inform_key = (src_ip, msg.request_id)
                    if inform_key in self._seen_inform_keys:
                        self.duplicate_informs_received += 1
                    else:
                        self._seen_inform_keys.add(inform_key)
                        self.deduplicated_messages.append(msg)

                    # Check fault injection controls for INFORM acknowledgement
                    if self.drop_all_acks:
                        self.acks_dropped += 1
                        continue
                    if self.drop_acks_count > 0:
                        self.drop_acks_count -= 1
                        self.acks_dropped += 1
                        continue

            if self.ack_delay_ms > 0:
                time.sleep(self.ack_delay_ms / 1000.0)

            # Build and send Response-PDU (0xA2) or injected fault response
            if self.inject_malformed_response is not None:
                resp_bytes = bytes(self.inject_malformed_response)
            else:
                resp_msg = SnmpResponse.from_inform(msg)
                if self.inject_wrong_request_id is not None:
                    resp_msg.request_id = int(self.inject_wrong_request_id)
                resp_bytes = SnmpBerEncoder.encode_message(resp_msg)

            send_count = 1 + max(0, int(self.duplicate_ack_count))
            for _ in range(send_count):
                if not self._running or not self._sock:
                    break
                try:
                    self._sock.sendto(resp_bytes, addr)
                    with self._lock:
                        self.responses_sent += 1
                        self.captured_frames.append(
                            {
                                "direction": "OUT",
                                "src_ip": self.host,
                                "dst_ip": src_ip,
                                "src_port": self.bound_port,
                                "dst_port": src_port,
                                "payload": resp_bytes,
                                "timestamp": time.time(),
                            }
                        )
                except OSError:
                    break

    def wait_for_packets(self, count: int, timeout_sec: float = 2.0) -> bool:
        deadline = time.monotonic() + timeout_sec
        while time.monotonic() < deadline:
            with self._lock:
                if self.packets_received >= count:
                    return True
            time.sleep(0.01)
        with self._lock:
            return self.packets_received >= count

    def export_pcap(self, filepath: str) -> str:
        with self._lock:
            frames = list(self.captured_frames)
        return write_snmp_pcap(filepath, frames)

    def get_evidence_snapshot(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "host": self.host,
                "port": self.bound_port,
                "packets_received": self.packets_received,
                "traps_received": self.traps_received,
                "informs_received": self.informs_received,
                "duplicate_informs_received": self.duplicate_informs_received,
                "responses_sent": self.responses_sent,
                "acks_dropped": self.acks_dropped,
                "decode_errors": self.decode_errors,
                "bad_community_count": self.bad_community_count,
                "bad_version_count": self.bad_version_count,
                "observed_request_ids": list(self.observed_request_ids),
                "deduplicated_count": len(self.deduplicated_messages),
            }


class NativeSnmpTransport:
    """
    Safe UDP Exporter for Native SNMPv2c Traps (0xA7) and Informs (0xA6).
    Reuses NetSpout transport safety guardrails and token-bucket rate limiters.
    """

    def __init__(
        self,
        destination_host: str = DEFAULT_SNMP_HOST,
        destination_port: int = DEFAULT_SNMP_TRAP_PORT,
        community: str = "netspout-lab",
        trap_rate_pps: int = DEFAULT_TRAP_RATE_PPS,
        inform_rate_pps: int = DEFAULT_INFORM_RATE_PPS,
        packet_cap: int = DEFAULT_SNMP_PACKET_CAP,
        inform_timeout_ms: int = DEFAULT_INFORM_TIMEOUT_MS,
        inform_max_retries: int = DEFAULT_INFORM_MAX_RETRIES,
        allow_public: bool = False,
        test_mode: bool = False,
        receiver: Optional[LoopbackSnmpTestReceiver] = None,
    ):
        self.destination_host = destination_host
        self.destination_port = int(destination_port)
        self.community = community
        self.allow_public = allow_public
        self.test_mode = test_mode
        self.receiver = receiver

        if trap_rate_pps <= 0 or trap_rate_pps > MAX_TRAP_RATE_PPS:
            raise ValueError(
                f"SNMP Trap rate limit must be in 1..{MAX_TRAP_RATE_PPS} pps, got {trap_rate_pps}"
            )
        if inform_rate_pps <= 0 or inform_rate_pps > MAX_INFORM_RATE_PPS:
            raise ValueError(
                f"SNMP Inform rate limit must be in 1..{MAX_INFORM_RATE_PPS} pps, got {inform_rate_pps}"
            )
        if packet_cap <= 0 or packet_cap > MAX_SNMP_PACKET_CAP:
            raise ValueError(
                f"SNMP packet cap must be in 1..{MAX_SNMP_PACKET_CAP}, got {packet_cap}"
            )

        self.trap_rate_pps = trap_rate_pps
        self.inform_rate_pps = inform_rate_pps
        self.packet_cap = packet_cap
        self.inform_timeout_ms = max(20, int(inform_timeout_ms))
        self.inform_max_retries = max(0, int(inform_max_retries))

        self.trap_limiter = TokenBucketRateLimiter(
            rate_pps=self.trap_rate_pps, max_packets_per_run=self.packet_cap
        )
        self.inform_limiter = TokenBucketRateLimiter(
            rate_pps=self.inform_rate_pps, max_packets_per_run=self.packet_cap
        )

    def validate_target(self) -> Tuple[str, int]:
        """
        Validates destination target via transport_safety.py and explicitly rejects
        public Internet IPs (unless allow_public=True), multicast, and broadcast.
        """
        # Explicitly check for multicast/broadcast first so even allow_public cannot bypass it
        try:
            ip_obj = ipaddress.ip_address(self.destination_host)
            if ip_obj.is_multicast or str(ip_obj) == "255.255.255.255" or ip_obj.is_unspecified:
                raise DestinationSecurityException(
                    f"SNMP export to multicast/broadcast/unspecified address {self.destination_host} is strictly prohibited"
                )
        except ValueError:
            pass

        ip_str = validate_destination_target(
            self.destination_host,
            int(self.destination_port),
            allow_privileged_ports=False,
        )
        ip_obj = ipaddress.ip_address(ip_str)
        if ip_obj.is_multicast or ip_str == "255.255.255.255":
            raise DestinationSecurityException(
                f"SNMP export to multicast/broadcast address {ip_str} is strictly prohibited"
            )
        return ip_str, int(self.destination_port)

    def send_trap(self, trap: SnmpTrap) -> SnmpTransportResult:
        return self.send_batch([trap])

    def send_inform(self, inform: SnmpInform) -> SnmpTransportResult:
        return self.send_batch([inform])

    def send_batch(
        self,
        messages: List[SnmpMessage],
        receiver: Optional[LoopbackSnmpTestReceiver] = None,
    ) -> SnmpTransportResult:
        """
        Transmits a batch of SnmpTrap and/or SnmpInform messages over UDP with
        strict rate limiting, packet caps, and honest evidence state tracking.
        """
        start_time = time.monotonic()
        active_receiver = receiver or self.receiver

        pdu_types = {int(m.pdu_type) for m in messages}
        if pdu_types == {SnmpPduType.SNMPV2_TRAP.value}:
            pdu_mode = "TRAP"
        elif pdu_types == {SnmpPduType.INFORM_REQUEST.value}:
            pdu_mode = "INFORM"
        else:
            pdu_mode = "MIXED"

        res = SnmpTransportResult(
            transport_type="SNMPV2C_UDP",
            pdu_mode=pdu_mode,
            destination_host=self.destination_host,
            destination_port=self.destination_port,
            pdus_generated=len(messages),
            evidence_stage=SnmpEvidenceStage.GENERATED.value,
            stage_history=[SnmpEvidenceStage.GENERATED.value],
        )

        if not messages:
            return res

        # 1. Validate Target Safety
        try:
            target_ip, target_port = self.validate_target()
            res.destination_host = target_ip
            res.destination_port = target_port
        except DestinationSecurityException as e:
            err_str = str(e)
            err_type = (
                TransportErrorType.DESTINATION_INVALID.value
                if "Invalid" in err_str or "Resolve" in err_str or "Port" in err_str
                else TransportErrorType.DESTINATION_BLOCKED.value
            )
            res.errors.append(err_str)
            res.error_types.append(err_type)
            res.elapsed_ms = round((time.monotonic() - start_time) * 1000.0, 2)
            return res

        # 2. Open UDP Socket
        sock: Optional[socket.socket] = None
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        except Exception as e:
            res.errors.append(f"Socket creation failed: {e}")
            res.error_types.append(TransportErrorType.SOCKET_CREATE_FAILED.value)
            res.elapsed_ms = round((time.monotonic() - start_time) * 1000.0, 2)
            return res

        try:
            for msg in messages:
                if res.datagrams_sent >= self.packet_cap:
                    res.packet_cap_exceeded = True
                    res.errors.append(
                        f"SNMP packet cap ({self.packet_cap}) reached; halting transmission"
                    )
                    res.error_types.append(TransportErrorType.RATE_LIMIT_EXCEEDED.value)
                    break

                # Encode ASN.1 BER wire payload (enforces <= 1,472 bytes)
                try:
                    wire_bytes = SnmpBerEncoder.encode_message(
                        msg, max_payload_bytes=MAX_SNMP_UDP_PAYLOAD_BYTES
                    )
                    res.pdus_encoded += 1
                    res.request_ids.append(msg.request_id)
                    if SnmpEvidenceStage.ENCODED.value not in res.stage_history:
                        res.stage_history.append(SnmpEvidenceStage.ENCODED.value)
                    if res.evidence_stage == SnmpEvidenceStage.GENERATED.value:
                        res.evidence_stage = SnmpEvidenceStage.ENCODED.value
                except SnmpPayloadSizeError as e:
                    res.encoding_failures += 1
                    res.errors.append(str(e))
                    res.error_types.append(TransportErrorType.PACKET_TOO_LARGE.value)
                    continue
                except Exception as e:
                    res.encoding_failures += 1
                    res.errors.append(f"ASN.1 BER encoding failed: {e}")
                    res.error_types.append(TransportErrorType.ENCODING_FAILED.value)
                    continue

                if int(msg.pdu_type) == SnmpPduType.SNMPV2_TRAP.value:
                    # Unacknowledged TRAPv2 (0xA7)
                    self.trap_limiter.acquire(1, test_mode=self.test_mode)
                    res.datagrams_attempted += 1
                    try:
                        sent_len = sock.sendto(wire_bytes, (target_ip, target_port))
                        res.datagrams_sent += 1
                        res.bytes_sent += sent_len
                        if SnmpEvidenceStage.SENT.value not in res.stage_history:
                            res.stage_history.append(SnmpEvidenceStage.SENT.value)
                        res.evidence_stage = SnmpEvidenceStage.SENT.value
                    except Exception as e:
                        res.send_failures += 1
                        res.errors.append(f"UDP trap sendto failed: {e}")
                        res.error_types.append(TransportErrorType.SEND_FAILED.value)

                elif int(msg.pdu_type) == SnmpPduType.INFORM_REQUEST.value:
                    # Acknowledged InformRequest-PDU (0xA6) -> expects Response-PDU (0xA2)
                    res.informs_sent += 1
                    ack_received = False
                    total_attempts = 1 + self.inform_max_retries

                    for attempt in range(total_attempts):
                        if res.datagrams_sent >= self.packet_cap:
                            res.packet_cap_exceeded = True
                            res.errors.append(
                                f"SNMP packet cap ({self.packet_cap}) reached during Inform retry"
                            )
                            res.error_types.append(TransportErrorType.RATE_LIMIT_EXCEEDED.value)
                            break

                        if attempt > 0:
                            res.inform_retries += 1

                        self.inform_limiter.acquire(1, test_mode=self.test_mode)
                        res.datagrams_attempted += 1
                        attempt_start = time.monotonic()

                        try:
                            sent_len = sock.sendto(wire_bytes, (target_ip, target_port))
                            res.datagrams_sent += 1
                            res.bytes_sent += sent_len
                            if SnmpEvidenceStage.SENT.value not in res.stage_history:
                                res.stage_history.append(SnmpEvidenceStage.SENT.value)
                            if res.evidence_stage in (
                                SnmpEvidenceStage.GENERATED.value,
                                SnmpEvidenceStage.ENCODED.value,
                            ):
                                res.evidence_stage = SnmpEvidenceStage.SENT.value
                        except Exception as e:
                            res.send_failures += 1
                            res.errors.append(f"UDP inform sendto failed: {e}")
                            res.error_types.append(TransportErrorType.SEND_FAILED.value)
                            continue

                        # Wait for matching Response-PDU (0xA2) within inform_timeout_ms
                        deadline = attempt_start + (self.inform_timeout_ms / 1000.0)
                        while True:
                            remaining = deadline - time.monotonic()
                            if remaining <= 0:
                                break
                            sock.settimeout(remaining)
                            try:
                                resp_data, _ = sock.recvfrom(65535)
                            except socket.timeout:
                                break
                            except OSError:
                                # e.g., ICMP Port Unreachable on connected/loopback UDP socket
                                # Wait out remaining timeout window before next retry
                                sleep_rem = deadline - time.monotonic()
                                if sleep_rem > 0 and not self.test_mode:
                                    time.sleep(min(sleep_rem, 0.05))
                                break

                            try:
                                resp_msg = SnmpBerDecoder.decode_message(
                                    resp_data, expected_community=msg.community
                                )
                            except Exception as e:
                                res.late_or_mismatched_acks += 1
                                res.errors.append(f"Invalid Inform Response-PDU ignored: {e}")
                                continue

                            if (
                                int(resp_msg.pdu_type) == SnmpPduType.RESPONSE.value
                                and resp_msg.request_id == msg.request_id
                                and resp_msg.error_status == 0
                            ):
                                rtt_ms = round((time.monotonic() - attempt_start) * 1000.0, 3)
                                res.rtt_ms_samples.append(max(0.001, rtt_ms))
                                ack_received = True
                                res.informs_acknowledged += 1
                                if msg.request_id not in res.acknowledged_request_ids:
                                    res.acknowledged_request_ids.append(msg.request_id)
                                if SnmpEvidenceStage.ACKNOWLEDGED.value not in res.stage_history:
                                    res.stage_history.append(SnmpEvidenceStage.ACKNOWLEDGED.value)
                                res.evidence_stage = SnmpEvidenceStage.ACKNOWLEDGED.value
                                break
                            else:
                                res.late_or_mismatched_acks += 1
                                res.errors.append(
                                    f"Mismatched Response-PDU request-id={resp_msg.request_id} "
                                    f"(expected {msg.request_id}) or error_status={resp_msg.error_status}"
                                )

                        if ack_received:
                            break

                    if not ack_received:
                        res.inform_timeouts += 1
                        res.errors.append(
                            f"INFORM request_id={msg.request_id} timed out after {total_attempts} attempt(s)"
                        )
                        if TransportErrorType.COLLECTOR_TIMEOUT.value not in res.error_types:
                            res.error_types.append(TransportErrorType.COLLECTOR_TIMEOUT.value)

            # Drain any duplicate trailing ACKs sitting in socket receive buffer
            sock.settimeout(0.005)
            while True:
                try:
                    dup_data, _ = sock.recvfrom(65535)
                    try:
                        dup_msg = SnmpBerDecoder.decode_message(dup_data)
                        if dup_msg.request_id in res.acknowledged_request_ids:
                            res.late_or_mismatched_acks += 1
                    except Exception:
                        res.late_or_mismatched_acks += 1
                except Exception:
                    break

        finally:
            if sock:
                try:
                    sock.close()
                except Exception:
                    pass

        # 3. Optional Receiver Observation Verification (ONLY when a real receiver is attached and observed the PDUs)
        if active_receiver is not None:
            # Allow brief moment for loopback receiver thread to finish processing final packet
            for _ in range(10):
                snap = active_receiver.get_evidence_snapshot()
                observed_ids = [
                    rid for rid in res.request_ids if rid in snap["observed_request_ids"]
                ]
                if len(observed_ids) >= len(res.request_ids):
                    break
                time.sleep(0.005)

            snap = active_receiver.get_evidence_snapshot()
            observed_ids = [
                rid for rid in res.request_ids if rid in snap["observed_request_ids"]
            ]
            res.receiver_observed_request_ids = observed_ids
            res.receiver_observed_count = len(observed_ids)
            if res.receiver_observed_count > 0:
                if pdu_mode == "INFORM" and res.informs_acknowledged == 0:
                    # Receiver observed the Inform, but sender never received ACK (e.g. dropped ACK)
                    pass
                else:
                    if SnmpEvidenceStage.RECEIVER_OBSERVED.value not in res.stage_history:
                        res.stage_history.append(SnmpEvidenceStage.RECEIVER_OBSERVED.value)
                    res.evidence_stage = SnmpEvidenceStage.RECEIVER_OBSERVED.value

        res.elapsed_ms = round((time.monotonic() - start_time) * 1000.0, 2)
        return res
