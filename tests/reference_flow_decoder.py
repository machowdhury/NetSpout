"""
Independent Reference Protocol Decoder for NetFlow v9 and IPFIX.
Conforms strictly to RFC 3954 and RFC 7011/7012.
Provides independent, clean-room decoding of wire datagrams for protocol verification.
"""

import ipaddress
import struct
from typing import Dict, Any, List, Tuple, Optional


class ReferenceDecoderError(Exception):
    """Raised when an independent decoding assertion fails."""
    pass


class ReferenceNetFlowV9Decoder:
    """Independent RFC 3954 dissector."""

    @classmethod
    def decode_packet(cls, data: bytes) -> Dict[str, Any]:
        if len(data) < 20:
            raise ReferenceDecoderError(f"Datagram too short for NetFlow v9 header: {len(data)} bytes < 20")

        version, count, sys_uptime, unix_secs, seq_num, source_id = struct.unpack("!HHIIII", data[:20])
        if version != 9:
            raise ReferenceDecoderError(f"Invalid NetFlow version: expected 9, got {version}")

        offset = 20
        flowsets = []
        templates_learned: Dict[int, List[Tuple[int, int]]] = {}
        total_records_decoded = 0

        while offset + 4 <= len(data):
            flowset_id, flowset_len = struct.unpack("!HH", data[offset : offset + 4])
            if flowset_len < 4:
                raise ReferenceDecoderError(f"Invalid FlowSet length {flowset_len} < 4 at offset {offset}")
            if offset + flowset_len > len(data):
                raise ReferenceDecoderError(f"FlowSet length {flowset_len} exceeds packet boundary {len(data)}")

            flowset_body = data[offset + 4 : offset + flowset_len]

            if flowset_id == 0:
                # Template FlowSet
                tmpl_offset = 0
                while tmpl_offset + 4 <= len(flowset_body):
                    tmpl_id, field_count = struct.unpack("!HH", flowset_body[tmpl_offset : tmpl_offset + 4])
                    tmpl_offset += 4
                    fields = []
                    for _ in range(field_count):
                        if tmpl_offset + 4 > len(flowset_body):
                            break
                        f_type, f_len = struct.unpack("!HH", flowset_body[tmpl_offset : tmpl_offset + 4])
                        fields.append((f_type, f_len))
                        tmpl_offset += 4
                    templates_learned[tmpl_id] = fields
                    total_records_decoded += 1
                flowsets.append({
                    "type": "TEMPLATE",
                    "flowset_id": 0,
                    "length": flowset_len,
                    "templates": list(templates_learned.keys())
                })

            elif flowset_id >= 256:
                # Data FlowSet
                tmpl_fields = templates_learned.get(flowset_id)
                data_records = []
                if tmpl_fields:
                    rec_len = sum(f[1] for f in tmpl_fields)
                    body_len = len(flowset_body)
                    num_records = body_len // rec_len
                    for r_idx in range(num_records):
                        r_bytes = flowset_body[r_idx * rec_len : (r_idx + 1) * rec_len]
                        rec_dict = cls._dissect_record(r_bytes, tmpl_fields)
                        data_records.append(rec_dict)
                        total_records_decoded += 1

                flowsets.append({
                    "type": "DATA",
                    "template_id": flowset_id,
                    "length": flowset_len,
                    "records": data_records
                })
            else:
                flowsets.append({
                    "type": "UNKNOWN_OR_OPTIONS",
                    "flowset_id": flowset_id,
                    "length": flowset_len
                })

            offset += flowset_len

        return {
            "version": version,
            "count": count,
            "sys_uptime_ms": sys_uptime,
            "unix_secs": unix_secs,
            "sequence_number": seq_num,
            "source_id": source_id,
            "flowsets": flowsets,
            "templates_learned": templates_learned,
            "total_records_decoded": total_records_decoded
        }

    @staticmethod
    def _dissect_record(raw: bytes, fields: List[Tuple[int, int]]) -> Dict[str, Any]:
        result = {}
        offset = 0
        for f_type, f_len in fields:
            chunk = raw[offset : offset + f_len]
            offset += f_len
            if f_type in (8, 12, 18) and f_len == 4:  # IPV4_SRC_ADDR, IPV4_DST_ADDR, BGP_NEXT_HOP
                result[f"field_{f_type}"] = str(ipaddress.IPv4Address(chunk))
            elif f_len == 4:
                result[f"field_{f_type}"] = struct.unpack("!I", chunk)[0]
            elif f_len == 2:
                result[f"field_{f_type}"] = struct.unpack("!H", chunk)[0]
            elif f_len == 1:
                result[f"field_{f_type}"] = struct.unpack("!B", chunk)[0]
            else:
                result[f"field_{f_type}"] = chunk.hex()
        return result


class ReferenceIPFIXDecoder:
    """Independent RFC 7011 dissector."""

    @classmethod
    def decode_message(cls, data: bytes) -> Dict[str, Any]:
        if len(data) < 16:
            raise ReferenceDecoderError(f"Datagram too short for IPFIX header: {len(data)} bytes < 16")

        version, length, export_time, seq_num, domain_id = struct.unpack("!HHIII", data[:16])
        if version != 10:
            raise ReferenceDecoderError(f"Invalid IPFIX version: expected 10, got {version}")
        if length != len(data):
            raise ReferenceDecoderError(f"Header length mismatch: declared {length}, actual {len(data)}")

        offset = 16
        sets = []
        templates_learned: Dict[int, List[Tuple[int, int]]] = {}
        total_data_records = 0

        while offset + 4 <= len(data):
            set_id, set_len = struct.unpack("!HH", data[offset : offset + 4])
            if set_len < 4:
                raise ReferenceDecoderError(f"Invalid Set length {set_len} < 4 at offset {offset}")
            if offset + set_len > len(data):
                raise ReferenceDecoderError(f"Set length {set_len} exceeds message boundary {len(data)}")

            set_body = data[offset + 4 : offset + set_len]

            if set_id == 2:
                # Template Set
                tmpl_offset = 0
                while tmpl_offset + 4 <= len(set_body):
                    tmpl_id, field_count = struct.unpack("!HH", set_body[tmpl_offset : tmpl_offset + 4])
                    tmpl_offset += 4
                    fields = []
                    for _ in range(field_count):
                        if tmpl_offset + 4 > len(set_body):
                            break
                        ie_id, f_len = struct.unpack("!HH", set_body[tmpl_offset : tmpl_offset + 4])
                        tmpl_offset += 4
                        # Check enterprise bit
                        enterprise_num = None
                        if ie_id & 0x8000:
                            ie_id = ie_id & 0x7FFF
                            if tmpl_offset + 4 <= len(set_body):
                                enterprise_num = struct.unpack("!I", set_body[tmpl_offset : tmpl_offset + 4])[0]
                                tmpl_offset += 4
                        fields.append((ie_id, f_len))
                    templates_learned[tmpl_id] = fields
                sets.append({
                    "type": "TEMPLATE",
                    "set_id": 2,
                    "length": set_len,
                    "templates": list(templates_learned.keys())
                })

            elif set_id >= 256:
                # Data Set
                tmpl_fields = templates_learned.get(set_id)
                data_records = []
                if tmpl_fields:
                    rec_len = sum(f[1] for f in tmpl_fields)
                    body_len = len(set_body)
                    num_records = body_len // rec_len
                    for r_idx in range(num_records):
                        r_bytes = set_body[r_idx * rec_len : (r_idx + 1) * rec_len]
                        rec_dict = cls._dissect_record(r_bytes, tmpl_fields)
                        data_records.append(rec_dict)
                        total_data_records += 1

                sets.append({
                    "type": "DATA",
                    "template_id": set_id,
                    "length": set_len,
                    "records": data_records
                })
            else:
                sets.append({
                    "type": "OPTIONS_OR_RESERVED",
                    "set_id": set_id,
                    "length": set_len
                })

            offset += set_len

        return {
            "version": version,
            "length": length,
            "export_time": export_time,
            "sequence_number": seq_num,
            "observation_domain_id": domain_id,
            "sets": sets,
            "templates_learned": templates_learned,
            "total_data_records": total_data_records
        }

    @staticmethod
    def _dissect_record(raw: bytes, fields: List[Tuple[int, int]]) -> Dict[str, Any]:
        result = {}
        offset = 0
        for ie_id, f_len in fields:
            chunk = raw[offset : offset + f_len]
            offset += f_len
            if ie_id in (8, 12) and f_len == 4:  # sourceIPv4Address, destinationIPv4Address
                result[f"ie_{ie_id}"] = str(ipaddress.IPv4Address(chunk))
            elif f_len == 8:
                result[f"ie_{ie_id}"] = struct.unpack("!Q", chunk)[0]
            elif f_len == 4:
                result[f"ie_{ie_id}"] = struct.unpack("!I", chunk)[0]
            elif f_len == 2:
                result[f"ie_{ie_id}"] = struct.unpack("!H", chunk)[0]
            elif f_len == 1:
                result[f"ie_{ie_id}"] = struct.unpack("!B", chunk)[0]
            else:
                result[f"ie_{ie_id}"] = chunk.hex()
        return result
