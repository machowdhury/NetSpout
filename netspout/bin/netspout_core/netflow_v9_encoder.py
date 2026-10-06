"""
NetSpout Cisco NetFlow Version 9 Binary Packet Encoder.
Conforms to IETF RFC 3954 and Gate 11 Protocol Specification.

Key features:
- Big-endian network byte order ('!')
- 16-byte header: Version (9), Count, sysUpTime, UNIX secs, Sequence Number, Source ID
- Template FlowSet (ID 0) with 4-byte word boundary padding
- Data FlowSet (ID >= 256) with 4-byte word boundary padding
- Standard 16-field IPv4 Template (Template ID 256, 43 bytes/record)
- Strict sequence number accounting (tracks export packets per RFC 3954)
- Pure Python standard library (struct, socket, ipaddress) with zero external dependencies
"""

import ipaddress
import struct
import time
from typing import List, Tuple, Optional, Dict, Any

from netspout_core.models import FlowRecord
from netspout_core.exporter_session import ExporterSession

# RFC 3954 Constants
NETFLOW_V9_VERSION = 9
FLOWSET_TEMPLATE_ID = 0
FLOWSET_OPTIONS_ID = 1
DEFAULT_TEMPLATE_ID_V4 = 256
MAX_DATAGRAM_PAYLOAD_BYTES = 1400

# Canonical 16-Field IPv4 Flow Template Definitions
# (Field Type, Field Length, struct format)
IPV4_TEMPLATE_FIELDS: List[Tuple[int, int, str]] = [
    (8, 4, "!4s"),   # IPV4_SRC_ADDR
    (12, 4, "!4s"),  # IPV4_DST_ADDR
    (18, 4, "!4s"),  # BGP_IPV4_NEXT_HOP
    (10, 2, "!H"),   # INPUT_SNMP
    (14, 2, "!H"),   # OUTPUT_SNMP
    (2, 4, "!I"),    # IN_PKTS
    (1, 4, "!I"),    # IN_BYTES
    (22, 4, "!I"),   # FIRST_SWITCHED (sysUpTime ms)
    (21, 4, "!I"),   # LAST_SWITCHED (sysUpTime ms)
    (7, 2, "!H"),    # L4_SRC_PORT
    (11, 2, "!H"),   # L4_DST_PORT
    (6, 1, "!B"),    # TCP_FLAGS
    (4, 1, "!B"),    # PROTOCOL
    (5, 1, "!B"),    # SRC_TOS
    (16, 2, "!H"),   # SRC_AS
    (17, 2, "!H"),   # DST_AS
]

RECORD_BYTES_V4 = sum(field[1] for field in IPV4_TEMPLATE_FIELDS)  # 43 bytes


class NetFlowV9ValidationError(ValueError):
    """Raised when flow record values fail RFC 3954 structural bounds."""
    pass


class NetFlowV9Encoder:
    """
    Encodes NetSpout FlowRecord models into RFC 3954 binary NetFlow v9 datagrams.
    """

    @staticmethod
    def encode_template_flowset(template_id: int = DEFAULT_TEMPLATE_ID_V4) -> bytes:
        """
        Builds a Template FlowSet (FlowSet ID = 0) containing the 16-field IPv4 schema.
        FlowSet Header: FlowSet ID (uint16), Length (uint16)
        Template Header: Template ID (uint16), Field Count (uint16)
        Fields: Sequence of (Field Type uint16, Field Length uint16)
        Padded to 4-byte boundary.
        """
        body = struct.pack("!HH", template_id, len(IPV4_TEMPLATE_FIELDS))
        for field_type, field_len, _ in IPV4_TEMPLATE_FIELDS:
            body += struct.pack("!HH", field_type, field_len)

        padding_len = (4 - (len(body) % 4)) % 4
        flowset_len = 4 + len(body) + padding_len
        header = struct.pack("!HH", FLOWSET_TEMPLATE_ID, flowset_len)
        return header + body + (b"\x00" * padding_len)

    @classmethod
    def encode_record(
        cls,
        record: FlowRecord,
        session: ExporterSession
    ) -> bytes:
        """
        Encodes a single FlowRecord into 43 raw bytes conforming to Template 256.
        Validates IP addresses, ports, and counters.
        """
        try:
            src_ip_bytes = ipaddress.IPv4Address(record.src_ip).packed
            dst_ip_bytes = ipaddress.IPv4Address(record.dest_ip).packed
            next_hop = record.bgp_next_hop or "0.0.0.0"
            next_hop_bytes = ipaddress.IPv4Address(next_hop).packed
        except Exception as exc:
            raise NetFlowV9ValidationError(f"Invalid IPv4 address in FlowRecord: {exc}")

        if not (0 <= record.src_port <= 65535 and 0 <= record.dest_port <= 65535):
            raise NetFlowV9ValidationError(f"Port out of range 0..65535: src={record.src_port}, dst={record.dest_port}")

        if record.packets_count < 0 or record.bytes_count < 0:
            raise NetFlowV9ValidationError("Packet/Byte count cannot be negative")

        if record.end_time_ms < record.start_time_ms and record.start_time_ms > 0:
            raise NetFlowV9ValidationError(f"end_time_ms ({record.end_time_ms}) < start_time_ms ({record.start_time_ms})")

        # Convert epoch ms to relative sysUpTime ms if absolute epoch given
        if record.start_time_ms > 1000000000:
            first_switched = session.get_sys_uptime_ms(record.start_time_ms)
            last_switched = session.get_sys_uptime_ms(record.end_time_ms)
        else:
            first_switched = max(0, record.start_time_ms) & 0xFFFFFFFF
            last_switched = max(first_switched, record.end_time_ms) & 0xFFFFFFFF

        return struct.pack(
            "!4s4s4sHHIIIIHHBBBHH",
            src_ip_bytes,
            dst_ip_bytes,
            next_hop_bytes,
            record.input_snmp & 0xFFFF,
            record.output_snmp & 0xFFFF,
            record.packets_count & 0xFFFFFFFF,
            record.bytes_count & 0xFFFFFFFF,
            first_switched,
            last_switched,
            record.src_port & 0xFFFF,
            record.dest_port & 0xFFFF,
            record.tcp_flags & 0xFF,
            record.protocol & 0xFF,
            record.tos_dscp & 0xFF,
            record.src_as & 0xFFFF,
            record.dest_as & 0xFFFF
        )

    @classmethod
    def encode_data_flowset(
        cls,
        records: List[FlowRecord],
        session: ExporterSession,
        template_id: int = DEFAULT_TEMPLATE_ID_V4
    ) -> Tuple[bytes, int]:
        """
        Packs a list of FlowRecords into a Data FlowSet.
        FlowSet Header: FlowSet ID = Template ID (uint16), Length (uint16)
        Followed by packed records and zero-padding to 4-byte boundary.
        Returns (data_flowset_bytes, record_count).
        """
        if not records:
            return b"", 0

        raw_records = b"".join(cls.encode_record(r, session) for r in records)
        padding_len = (4 - (len(raw_records) % 4)) % 4
        flowset_len = 4 + len(raw_records) + padding_len
        header = struct.pack("!HH", template_id, flowset_len)
        return header + raw_records + (b"\x00" * padding_len), len(records)

    @classmethod
    def build_packet(
        cls,
        session: ExporterSession,
        data_records: List[FlowRecord],
        include_template: bool = False,
        sim_time_sec: Optional[int] = None,
        sys_uptime_ms: Optional[int] = None
    ) -> bytes:
        """
        Builds a complete RFC 3954 UDP datagram with 20-byte header and FlowSets.
        Header: Version(9), Count, sysUpTime, UNIX Secs, Sequence Number, Source ID.
        """
        flowsets = []
        record_count = 0

        if include_template:
            template_fs = cls.encode_template_flowset()
            flowsets.append(template_fs)
            record_count += 1  # Template counts as 1 record in header Count

        if data_records:
            data_fs, data_rec_count = cls.encode_data_flowset(data_records, session)
            flowsets.append(data_fs)
            record_count += data_rec_count

        now_sec = sim_time_sec if sim_time_sec is not None else int(time.time())
        uptime = sys_uptime_ms if sys_uptime_ms is not None else session.get_sys_uptime_ms()

        # RFC 3954 §5.1: this is the incremental sequence counter of export
        # packets sent by the exporting device, unlike IPFIX's data-record count.
        seq_start, _ = session.advance_sequence(1)

        header = struct.pack(
            "!HHIIII",
            NETFLOW_V9_VERSION,
            record_count,
            uptime,
            now_sec,
            seq_start,
            session.source_id
        )

        return header + b"".join(flowsets)

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
        template_fs_len = 72 if include_template else 0  # 4 + 4 + 16*4 = 72 bytes
        available_first = max_bytes - header_len - template_fs_len - 4  # 4 for data FS header
        records_per_first_pkt = max(1, available_first // RECORD_BYTES_V4)

        available_subsequent = max_bytes - header_len - 4
        records_per_subsequent_pkt = max(1, available_subsequent // RECORD_BYTES_V4)

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
