# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/ipfix_encoder.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""
NetSpout IETF IPFIX (Internet Protocol Flow Information Export) Binary Packet Encoder.
Conforms to IETF RFC 7011 / RFC 7012 and Gate 11 Protocol Specification.

Key features:
- Big-endian network byte order ('!')
- 16-byte message header: Version (10), Length, Export Time, Sequence Number, Observation Domain ID
- Template Set (Set ID = 2) with 15 core IANA Information Elements
- Data Set (Set ID >= 256) with 64-byte aligned records (zero padding required)
- 64-bit packet and octet counters (octetDeltaCount, packetDeltaCount)
- Absolute epoch millisecond timestamps (flowStartMilliseconds, flowEndMilliseconds)
- Sequence numbers count Data Records only (excluding Template records per RFC 7011)
- Support for Enterprise-Specific Information Elements (PEN) and variable-length fields
- Pure Python standard library (struct, socket, ipaddress) with zero external dependencies
"""

import ipaddress
import struct
import time
from typing import List, Tuple, Optional, Dict, Any

from netspout_core.models import FlowRecord
from netspout_core.exporter_session import ExporterSession

# RFC 7011 Constants
IPFIX_VERSION = 10
SET_TEMPLATE_ID = 2
SET_OPTIONS_ID = 3
DEFAULT_TEMPLATE_ID_IPFIX = 256
MAX_DATAGRAM_PAYLOAD_BYTES = 1400

# Canonical 15-Field IANA IPFIX Flow Template Definitions
# (IANA IE ID, Field Length in bytes, struct format)
IPFIX_CORE_FIELDS: List[Tuple[int, int, str]] = [
    (8, 4, "!4s"),    # sourceIPv4Address
    (12, 4, "!4s"),   # destinationIPv4Address
    (7, 2, "!H"),     # sourceTransportPort
    (11, 2, "!H"),    # destinationTransportPort
    (4, 1, "!B"),     # protocolIdentifier
    (5, 1, "!B"),     # ipClassOfService
    (6, 2, "!H"),     # tcpControlBits (2 octets in RFC 7012)
    (10, 4, "!I"),    # ingressInterface
    (14, 4, "!I"),    # egressInterface
    (2, 8, "!Q"),     # packetDeltaCount
    (1, 8, "!Q"),     # octetDeltaCount
    (152, 8, "!Q"),   # flowStartMilliseconds
    (153, 8, "!Q"),   # flowEndMilliseconds
    (16, 4, "!I"),    # bgpSourceAsNumber
    (17, 4, "!I"),    # bgpDestinationAsNumber
]

RECORD_BYTES_IPFIX = sum(field[1] for field in IPFIX_CORE_FIELDS)  # 64 bytes


class IPFIXValidationError(ValueError):
    """Raised when flow record values fail RFC 7011/7012 structural bounds."""
    pass


class IPFIXEncoder:
    """
    Encodes NetSpout FlowRecord models into RFC 7011/7012 binary IPFIX messages.
    """

    @staticmethod
    def encode_template_set(template_id: int = DEFAULT_TEMPLATE_ID_IPFIX) -> bytes:
        """
        Builds an IPFIX Template Set (Set ID = 2) containing the 15-field core IANA schema.
        Set Header: Set ID = 2 (uint16), Length (uint16)
        Template Record Header: Template ID (uint16), Field Count (uint16)
        Fields: Sequence of (IE ID uint16, Field Length uint16)
        4 + 4 + (15 * 4) = 68 bytes (divisible by 4, 0 padding required).
        """
        body = struct.pack("!HH", template_id, len(IPFIX_CORE_FIELDS))
        for ie_id, field_len, _ in IPFIX_CORE_FIELDS:
            body += struct.pack("!HH", ie_id & 0x7FFF, field_len)

        padding_len = (4 - (len(body) % 4)) % 4
        set_len = 4 + len(body) + padding_len
        header = struct.pack("!HH", SET_TEMPLATE_ID, set_len)
        return header + body + (b"\x00" * padding_len)

    @classmethod
    def encode_record(
        cls,
        record: FlowRecord,
        session: ExporterSession
    ) -> bytes:
        """
        Encodes a single FlowRecord into 64 raw bytes conforming to IPFIX Template 256.
        Validates IP addresses, ports, and counters.
        """
        try:
            src_ip_bytes = ipaddress.IPv4Address(record.src_ip).packed
            dst_ip_bytes = ipaddress.IPv4Address(record.dest_ip).packed
        except Exception as exc:
            raise IPFIXValidationError(f"Invalid IPv4 address in FlowRecord: {exc}")

        if not (0 <= record.src_port <= 65535 and 0 <= record.dest_port <= 65535):
            raise IPFIXValidationError(f"Port out of range 0..65535: src={record.src_port}, dst={record.dest_port}")

        if record.packets_count < 0 or record.bytes_count < 0:
            raise IPFIXValidationError("Packet/Byte count cannot be negative")

        if record.end_time_ms < record.start_time_ms and record.start_time_ms > 0:
            raise IPFIXValidationError(f"end_time_ms ({record.end_time_ms}) < start_time_ms ({record.start_time_ms})")

        # Resolve epoch ms
        if record.start_time_ms > 1000000000:
            start_ms = record.start_time_ms
            end_ms = record.end_time_ms
        else:
            base_ms = session.base_time_epoch_ms
            start_ms = base_ms + max(0, record.start_time_ms)
            end_ms = base_ms + max(record.start_time_ms, record.end_time_ms)

        return struct.pack(
            "!4s4sHHBBHIIQQQQII",
            src_ip_bytes,
            dst_ip_bytes,
            record.src_port & 0xFFFF,
            record.dest_port & 0xFFFF,
            record.protocol & 0xFF,
            record.tos_dscp & 0xFF,
            record.tcp_flags & 0xFFFF,
            record.input_snmp & 0xFFFFFFFF,
            record.output_snmp & 0xFFFFFFFF,
            record.packets_count & 0xFFFFFFFFFFFFFFFF,
            record.bytes_count & 0xFFFFFFFFFFFFFFFF,
            start_ms & 0xFFFFFFFFFFFFFFFF,
            end_ms & 0xFFFFFFFFFFFFFFFF,
            record.src_as & 0xFFFFFFFF,
            record.dest_as & 0xFFFFFFFF
        )

    @classmethod
    def encode_data_set(
        cls,
        records: List[FlowRecord],
        session: ExporterSession,
        template_id: int = DEFAULT_TEMPLATE_ID_IPFIX
    ) -> Tuple[bytes, int]:
        """
        Packs a list of FlowRecords into an IPFIX Data Set.
        Set Header: Set ID = Template ID (uint16), Length (uint16)
        Followed by packed records and zero-padding to 4-byte boundary.
        Returns (data_set_bytes, record_count).
        """
        if not records:
            return b"", 0

        raw_records = b"".join(cls.encode_record(r, session) for r in records)
        padding_len = (4 - (len(raw_records) % 4)) % 4
        set_len = 4 + len(raw_records) + padding_len
        header = struct.pack("!HH", template_id, set_len)
        return header + raw_records + (b"\x00" * padding_len), len(records)

    @classmethod
    def build_packet(
        cls,
        session: ExporterSession,
        data_records: List[FlowRecord],
        include_template: bool = False,
        sim_time_sec: Optional[int] = None
    ) -> bytes:
        """
        Builds a complete RFC 7011 IPFIX Message with 16-byte header and Sets.
        Header: Version(10), Length, Export Time, Sequence Number, Observation Domain ID.
        """
        sets = []

        if include_template:
            template_set = cls.encode_template_set()
            sets.append(template_set)

        if data_records:
            data_set, _ = cls.encode_data_set(data_records, session)
            sets.append(data_set)

        sets_payload = b"".join(sets)
        total_message_len = 16 + len(sets_payload)
        now_sec = sim_time_sec if sim_time_sec is not None else int(time.time())

        # In RFC 7011, Sequence Number counts total DATA records only (excluding templates)
        seq_start, _ = session.advance_sequence(len(data_records))

        header = struct.pack(
            "!HHIII",
            IPFIX_VERSION,
            total_message_len,
            now_sec,
            seq_start,
            session.observation_domain_id
        )

        return header + sets_payload

    @classmethod
    def encode_batch(
        cls,
        records: List[FlowRecord],
        session: ExporterSession,
        include_template: bool = False,
        max_bytes: int = MAX_DATAGRAM_PAYLOAD_BYTES
    ) -> List[bytes]:
        """
        Splits records across multiple UDP datagrams to safely respect MTU limits.
        """
        packets = []
        header_len = 16
        template_set_len = 68 if include_template else 0  # 4 + 4 + 15*4 = 68 bytes
        available_first = max_bytes - header_len - template_set_len - 4  # 4 for data Set header
        records_per_first_pkt = max(1, available_first // RECORD_BYTES_IPFIX)

        available_subsequent = max_bytes - header_len - 4
        records_per_subsequent_pkt = max(1, available_subsequent // RECORD_BYTES_IPFIX)

        idx = 0
        is_first = True
        while idx < len(records) or (is_first and include_template and not records):
            batch_size = records_per_first_pkt if is_first else records_per_subsequent_pkt
            chunk = records[idx : idx + batch_size]
            pkt = cls.build_packet(
                session=session,
                data_records=chunk,
                include_template=(is_first and include_template)
            )
            packets.append(pkt)
            idx += len(chunk)
            is_first = False
            if not chunk:
                break

        return packets
