"""
NetSpout Gate 12B — Native SNMPv2c ASN.1 BER Encoder & Reference Decoder.
Conforms to:
  - ITU-T X.690 (ASN.1 Basic Encoding Rules, definite-length subset)
  - RFC 1901 (Community-Based SNMPv2c)
  - RFC 2578 (Structure of Management Information Version 2 - SMIv2)
  - RFC 3416 (Version 2 of the Protocol Operations for SNMP)
  - RFC 3418 (Management Information Base for SNMP)
"""

import hashlib
import socket
from typing import Any, Dict, List, Optional, Tuple, Union

try:
    from netspout_core.models import (
        ASN1_TAG_TO_CANONICAL_NAME,
        OidFidelityClass,
        SNMP_TRAP_OID,
        SYSUPTIME_OID,
        SnmpAsn1Type,
        SnmpInform,
        SnmpMessage,
        SnmpPduType,
        SnmpResponse,
        SnmpTrap,
        SnmpVarBind,
        SnmpVersion,
        resolve_asn1_tag,
        validate_notification_varbind_order,
    )
except ImportError:
    try:
        from app.models import (
            ASN1_TAG_TO_CANONICAL_NAME,
            OidFidelityClass,
            SNMP_TRAP_OID,
            SYSUPTIME_OID,
            SnmpAsn1Type,
            SnmpInform,
            SnmpMessage,
            SnmpPduType,
            SnmpResponse,
            SnmpTrap,
            SnmpVarBind,
            SnmpVersion,
            resolve_asn1_tag,
            validate_notification_varbind_order,
        )
    except ImportError:
        from models import (
            ASN1_TAG_TO_CANONICAL_NAME,
            OidFidelityClass,
            SNMP_TRAP_OID,
            SYSUPTIME_OID,
            SnmpAsn1Type,
            SnmpInform,
            SnmpMessage,
            SnmpPduType,
            SnmpResponse,
            SnmpTrap,
            SnmpVarBind,
            SnmpVersion,
            resolve_asn1_tag,
            validate_notification_varbind_order,
        )

MAX_SNMP_UDP_PAYLOAD_BYTES = 1472
MAX_ASN1_RECURSION_DEPTH = 5
MAX_OID_ARCS = 128
MAX_COMMUNITY_OCTETS = 255

VALID_PDU_TAGS = {
    SnmpPduType.GET_REQUEST.value,
    SnmpPduType.GET_NEXT_REQUEST.value,
    SnmpPduType.RESPONSE.value,
    SnmpPduType.SET_REQUEST.value,
    SnmpPduType.GET_BULK_REQUEST.value,
    SnmpPduType.INFORM_REQUEST.value,
    SnmpPduType.SNMPV2_TRAP.value,
}


class SnmpBerError(ValueError):
    """Base exception for SNMP ASN.1 BER encoding and decoding errors."""


class SnmpBerEncodeError(SnmpBerError):
    """Raised when an SNMP message or TLV cannot be encoded into valid ASN.1 BER."""


class SnmpBerDecodeError(SnmpBerError):
    """Raised when incoming wire bytes violate SNMPv2c ASN.1 BER rules."""


class InvalidSnmpOidError(SnmpBerEncodeError):
    """Raised when an OID string violates RFC 2578 / X.690 syntax or arc rules."""


class SnmpValueTypeError(SnmpBerEncodeError):
    """Raised when a VarBind value does not match its declared SMIv2 ASN.1 syntax."""


class SnmpPayloadSizeError(SnmpBerEncodeError):
    """Raised when an encoded SNMP PDU exceeds the 1,472-byte safe UDP payload ceiling."""


class UnsupportedSnmpVersionError(SnmpBerDecodeError):
    """Raised when an SNMP message carries a version other than SNMPv2c (version=1)."""


class SnmpCommunityMismatchError(SnmpBerDecodeError):
    """Raised when an incoming SNMP message community does not match the expected community."""


# =========================================================================
# Authoritative Gate 12 / 12B Golden Hex Fixtures
# =========================================================================
GOLDEN_HEX_FIXTURES: Dict[str, Dict[str, Any]] = {
    "fixture_1_linkdown_trap": {
        "name": "Fixture 1: SNMPv2c linkDown TRAP (0xA7)",
        "expected_hex": (
            "307d020101040c6e657473706f75742d6c6162a76a020203e9020100020100"
            "305e301006082b0601020101030043040083d600"
            "3017060a2b06010603010104010006092b0601060301010503"
            "300f060a2b060102010202010101020101"
            "300f060a2b060102010202010701020101"
            "300f060a2b060102010202010801020102"
        ),
        "expected_length": 127,
    },
    "fixture_2_linkup_trap": {
        "name": "Fixture 2: SNMPv2c linkUp TRAP (0xA7)",
        "expected_hex": (
            "307d020101040c6e657473706f75742d6c6162a76a020203ea020100020100"
            "305e301006082b0601020101030043040083e1b8"
            "3017060a2b06010603010104010006092b0601060301010504"
            "300f060a2b060102010202010101020101"
            "300f060a2b060102010202010701020101"
            "300f060a2b060102010202010801020101"
        ),
        "expected_length": 127,
    },
    "fixture_3_bgp_backward_transition_inform": {
        "name": "Fixture 3: SNMPv2c bgpBackwardTransition INFORM (0xA6)",
        "expected_hex": (
            "305e020101040c6e657473706f75742d6c6162a64b020207d1020100020100"
            "303f301006082b0601020101030043040083d7f4"
            "3016060a2b06010603010104010006082b060102010f0702"
            "3013060e2b060102010f0301020a817f0002020101"
        ),
        "expected_length": 96,
        "expected_response_hex": (
            "305e020101040c6e657473706f75742d6c6162a24b020207d1020100020100"
            "303f301006082b0601020101030043040083d7f4"
            "3016060a2b06010603010104010006082b060102010f0702"
            "3013060e2b060102010f0301020a817f0002020101"
        ),
    },
    "fixture_4_get_request": {
        "name": "Fixture 4: SNMPv2c GET Request (0xA0) for ifOperStatus.1",
        "expected_hex": (
            "302f020101040c6e657473706f75742d6c6162a01c02020bb9020100020100"
            "3010300e060a2b0601020102020108010500"
        ),
        "expected_length": 49,
    },
    "fixture_5_get_response": {
        "name": "Fixture 5: SNMPv2c GET RESPONSE (0xA2) for ifOperStatus.1 = 1",
        "expected_hex": (
            "3030020101040c6e657473706f75742d6c6162a21d02020bb9020100020100"
            "3011300f060a2b060102010202010801020101"
        ),
        "expected_length": 50,
    },
}


class SnmpBerEncoder:
    """
    Deterministic ASN.1 BER Definite-Length Encoder for SNMPv2c PDUs.
    """

    @staticmethod
    def encode_length(length: int) -> bytes:
        if not isinstance(length, int) or isinstance(length, bool) or length < 0:
            raise SnmpBerEncodeError(f"Invalid BER length: {length!r}")
        if length <= 0x7F:
            return bytes([length])
        if length > 0xFFFFFFFF:
            raise SnmpBerEncodeError(f"BER length {length} exceeds 4-octet definite length limit")
        n_bytes = (length.bit_length() + 7) // 8
        return bytes([0x80 | n_bytes]) + length.to_bytes(n_bytes, byteorder="big", signed=False)

    @classmethod
    def encode_tlv(cls, tag: int, value_bytes: bytes) -> bytes:
        if not isinstance(tag, int) or not (0 <= tag <= 0xFF):
            raise SnmpBerEncodeError(f"Invalid BER tag byte: {tag!r}")
        return bytes([tag]) + cls.encode_length(len(value_bytes)) + value_bytes

    @staticmethod
    def encode_integer_bytes(val: Any, signed: bool = True, bits: int = 32) -> bytes:
        if isinstance(val, bool) or not isinstance(val, int):
            raise SnmpValueTypeError(f"Expected integer value, got {type(val).__name__}: {val!r}")

        if signed:
            min_val = -(1 << (bits - 1))
            max_val = (1 << (bits - 1)) - 1
            if not (min_val <= val <= max_val):
                raise SnmpValueTypeError(
                    f"Signed {bits}-bit integer {val} out of bounds [{min_val}, {max_val}]"
                )
            if val >= 0:
                n_bytes = (val.bit_length() + 8) // 8
            else:
                n_bytes = ((~val).bit_length() + 8) // 8
            return val.to_bytes(n_bytes, byteorder="big", signed=True)
        else:
            max_val = (1 << bits) - 1
            if not (0 <= val <= max_val):
                raise SnmpValueTypeError(
                    f"Unsigned {bits}-bit integer {val} out of bounds [0, {max_val}]"
                )
            # In ASN.1 BER, unsigned SMIv2 types (Counter32, Gauge32, TimeTicks, Counter64)
            # use two's-complement integer encoding where a leading 0x00 byte is prepended
            # whenever the most significant bit of the top byte is 1 (>= 0x80).
            n_bytes = (val.bit_length() + 8) // 8
            return val.to_bytes(n_bytes, byteorder="big", signed=True)

    @staticmethod
    def validate_oid(oid_str: Any) -> List[int]:
        if not isinstance(oid_str, str) or not oid_str:
            raise InvalidSnmpOidError(f"OID must be a non-empty dotted string, got {oid_str!r}")
        if oid_str.startswith(".") or oid_str.endswith(".") or ".." in oid_str:
            raise InvalidSnmpOidError(f"Malformed OID string (leading/trailing/double dot): {oid_str!r}")

        parts = oid_str.split(".")
        if len(parts) < 2:
            raise InvalidSnmpOidError(f"OID must contain at least 2 arcs, got {oid_str!r}")
        if len(parts) > MAX_OID_ARCS:
            raise InvalidSnmpOidError(f"OID exceeds maximum {MAX_OID_ARCS} sub-identifiers: {len(parts)}")

        arcs: List[int] = []
        for p in parts:
            if not p.isdigit():
                raise InvalidSnmpOidError(f"Non-numeric OID arc {p!r} in {oid_str!r}")
            arc_val = int(p)
            if arc_val < 0 or arc_val > 0xFFFFFFFF:
                raise InvalidSnmpOidError(f"OID arc {arc_val} out of 32-bit range in {oid_str!r}")
            arcs.append(arc_val)

        if arcs[0] not in (0, 1, 2):
            raise InvalidSnmpOidError(
                f"Invalid root OID arc {arcs[0]} in {oid_str!r} (must be 0, 1, or 2)"
            )
        if arcs[0] < 2 and arcs[1] > 39:
            raise InvalidSnmpOidError(
                f"Invalid second OID arc {arcs[1]} when first arc is {arcs[0]} in {oid_str!r} (must be 0..39)"
            )
        return arcs

    @staticmethod
    def _encode_vlq_subid(subid: int) -> bytes:
        if subid == 0:
            return b"\x00"
        chunks: List[int] = []
        val = subid
        while val > 0:
            chunks.append(val & 0x7F)
            val >>= 7
        chunks.reverse()
        for i in range(len(chunks) - 1):
            chunks[i] |= 0x80
        return bytes(chunks)

    @classmethod
    def encode_oid(cls, oid_str: str) -> bytes:
        arcs = cls.validate_oid(oid_str)
        first_subid = 40 * arcs[0] + arcs[1]
        body = bytearray(cls._encode_vlq_subid(first_subid))
        for arc in arcs[2:]:
            body.extend(cls._encode_vlq_subid(arc))
        return cls.encode_tlv(SnmpAsn1Type.OBJECT_IDENTIFIER.value, bytes(body))

    @classmethod
    def encode_ip_address(cls, ip_val: Any) -> bytes:
        if isinstance(ip_val, (bytes, bytearray)):
            if len(ip_val) != 4:
                raise SnmpValueTypeError(f"IpAddress bytes must be exactly 4 octets, got {len(ip_val)}")
            return cls.encode_tlv(SnmpAsn1Type.IP_ADDRESS.value, bytes(ip_val))
        if not isinstance(ip_val, str):
            raise SnmpValueTypeError(f"IpAddress must be dotted IPv4 string or 4 bytes, got {ip_val!r}")
        parts = ip_val.split(".")
        if len(parts) != 4:
            raise SnmpValueTypeError(f"Invalid IPv4 address for IpAddress SMIv2 type: {ip_val!r}")
        octets: List[int] = []
        for p in parts:
            if not p.isdigit():
                raise SnmpValueTypeError(f"Invalid IPv4 octet {p!r} in {ip_val!r}")
            v = int(p)
            if not (0 <= v <= 255):
                raise SnmpValueTypeError(f"IPv4 octet {v} out of range 0..255 in {ip_val!r}")
            octets.append(v)
        return cls.encode_tlv(SnmpAsn1Type.IP_ADDRESS.value, bytes(octets))

    @classmethod
    def encode_value(cls, asn1_type: Union[int, str, SnmpAsn1Type], value: Any) -> bytes:
        try:
            tag = resolve_asn1_tag(asn1_type)
        except ValueError as e:
            raise SnmpValueTypeError(str(e)) from e

        if tag == SnmpAsn1Type.INTEGER.value:
            return cls.encode_tlv(tag, cls.encode_integer_bytes(value, signed=True, bits=32))
        elif tag == SnmpAsn1Type.OCTET_STRING.value:
            if isinstance(value, str):
                raw = value.encode("utf-8")
            elif isinstance(value, (bytes, bytearray)):
                raw = bytes(value)
            else:
                raise SnmpValueTypeError(f"OctetString requires str or bytes, got {type(value).__name__}")
            return cls.encode_tlv(tag, raw)
        elif tag == SnmpAsn1Type.NULL.value:
            if value not in (None, b"", ""):
                raise SnmpValueTypeError(f"NULL ASN.1 type requires None or empty value, got {value!r}")
            return b"\x05\x00"
        elif tag == SnmpAsn1Type.OBJECT_IDENTIFIER.value:
            return cls.encode_oid(value)
        elif tag == SnmpAsn1Type.IP_ADDRESS.value:
            return cls.encode_ip_address(value)
        elif tag == SnmpAsn1Type.COUNTER32.value:
            return cls.encode_tlv(tag, cls.encode_integer_bytes(value, signed=False, bits=32))
        elif tag == SnmpAsn1Type.GAUGE32.value:
            return cls.encode_tlv(tag, cls.encode_integer_bytes(value, signed=False, bits=32))
        elif tag == SnmpAsn1Type.TIME_TICKS.value:
            return cls.encode_tlv(tag, cls.encode_integer_bytes(value, signed=False, bits=32))
        elif tag == SnmpAsn1Type.OPAQUE.value:
            if isinstance(value, (bytes, bytearray)):
                raw = bytes(value)
            elif isinstance(value, str):
                raw = value.encode("utf-8")
            else:
                raise SnmpValueTypeError(f"Opaque requires bytes or str, got {type(value).__name__}")
            return cls.encode_tlv(tag, raw)
        elif tag == SnmpAsn1Type.COUNTER64.value:
            return cls.encode_tlv(tag, cls.encode_integer_bytes(value, signed=False, bits=64))
        elif tag in (
            SnmpAsn1Type.NO_SUCH_OBJECT.value,
            SnmpAsn1Type.NO_SUCH_INSTANCE.value,
            SnmpAsn1Type.END_OF_MIB_VIEW.value,
        ):
            return bytes([tag, 0x00])
        else:
            raise SnmpValueTypeError(f"Unsupported ASN.1 tag for VarBind value: 0x{tag:02x}")

    @classmethod
    def encode_varbind(cls, vb: SnmpVarBind) -> bytes:
        oid_tlv = cls.encode_oid(vb.oid)
        val_tlv = cls.encode_value(vb.asn1_type, vb.value)
        return cls.encode_tlv(SnmpAsn1Type.SEQUENCE.value, oid_tlv + val_tlv)

    @classmethod
    def encode_message(
        cls,
        msg: SnmpMessage,
        max_payload_bytes: int = MAX_SNMP_UDP_PAYLOAD_BYTES,
    ) -> bytes:
        if msg.version != SnmpVersion.V2C.value:
            raise UnsupportedSnmpVersionError(
                f"Only SNMPv2c (version=1) is supported in Gate 12B, got version={msg.version!r}"
            )
        if not isinstance(msg.community, str) or not msg.community:
            raise SnmpBerEncodeError("SNMPv2c community string must be non-empty")
        comm_bytes = msg.community.encode("utf-8")
        if len(comm_bytes) > MAX_COMMUNITY_OCTETS:
            raise SnmpBerEncodeError(f"Community string exceeds {MAX_COMMUNITY_OCTETS} octets")

        pdu_tag = int(msg.pdu_type.value if isinstance(msg.pdu_type, SnmpPduType) else msg.pdu_type)
        if pdu_tag not in VALID_PDU_TAGS:
            raise SnmpBerEncodeError(f"Unsupported SNMPv2c PDU tag: 0x{pdu_tag:02x}")

        if pdu_tag in (SnmpPduType.SNMPV2_TRAP.value, SnmpPduType.INFORM_REQUEST.value):
            try:
                validate_notification_varbind_order(msg.varbinds)
            except ValueError as e:
                raise SnmpBerEncodeError(str(e)) from e

        # Encode VarBindList (SEQUENCE OF VarBind)
        vb_encoded = b"".join(cls.encode_varbind(vb) for vb in msg.varbinds)
        varbind_list_tlv = cls.encode_tlv(SnmpAsn1Type.SEQUENCE.value, vb_encoded)

        # Encode PDU fields: request-id, error-status (or non-repeaters), error-index (or max-repetitions)
        req_id_tlv = cls.encode_tlv(
            SnmpAsn1Type.INTEGER.value,
            cls.encode_integer_bytes(msg.request_id, signed=True, bits=32),
        )
        err_status_val = msg.non_repeaters if (pdu_tag == SnmpPduType.GET_BULK_REQUEST.value and msg.non_repeaters is not None) else msg.error_status
        err_index_val = msg.max_repetitions if (pdu_tag == SnmpPduType.GET_BULK_REQUEST.value and msg.max_repetitions is not None) else msg.error_index

        err_status_tlv = cls.encode_tlv(
            SnmpAsn1Type.INTEGER.value,
            cls.encode_integer_bytes(err_status_val, signed=True, bits=32),
        )
        err_index_tlv = cls.encode_tlv(
            SnmpAsn1Type.INTEGER.value,
            cls.encode_integer_bytes(err_index_val, signed=True, bits=32),
        )

        pdu_tlv = cls.encode_tlv(
            pdu_tag,
            req_id_tlv + err_status_tlv + err_index_tlv + varbind_list_tlv,
        )

        version_tlv = cls.encode_tlv(
            SnmpAsn1Type.INTEGER.value,
            cls.encode_integer_bytes(msg.version, signed=True, bits=32),
        )
        community_tlv = cls.encode_tlv(SnmpAsn1Type.OCTET_STRING.value, comm_bytes)

        wire_bytes = cls.encode_tlv(
            SnmpAsn1Type.SEQUENCE.value,
            version_tlv + community_tlv + pdu_tlv,
        )

        if max_payload_bytes and len(wire_bytes) > max_payload_bytes:
            raise SnmpPayloadSizeError(
                f"Encoded SNMPv2c message size {len(wire_bytes)} bytes exceeds safe UDP ceiling {max_payload_bytes} bytes"
            )
        return wire_bytes


class SnmpBerDecoder:
    """
    Defensive ASN.1 BER Reference Decoder for SNMPv2c PDUs.
    Enforces definite-length bounds, recursion depth limit (<= 5), and strict tag validation.
    """

    @staticmethod
    def decode_length(data: bytes, offset: int) -> Tuple[int, int]:
        if offset >= len(data):
            raise SnmpBerDecodeError("Truncated BER stream while reading length byte")

        first = data[offset]
        offset += 1

        if first == 0x80:
            raise SnmpBerDecodeError("Invalid or indefinite BER length (0x80 is prohibited in SNMP)")

        if first < 0x80:
            length = first
        else:
            num_octets = first & 0x7F
            if num_octets > 4:
                raise SnmpBerDecodeError(
                    f"Invalid or indefinite BER length: long-form octet count {num_octets} exceeds maximum 4"
                )
            if offset + num_octets > len(data):
                raise SnmpBerDecodeError("Truncated BER long-form length octets")
            length = int.from_bytes(data[offset : offset + num_octets], byteorder="big", signed=False)
            offset += num_octets

        if offset + length > len(data):
            raise SnmpBerDecodeError(
                f"Truncated TLV value: expected {length} bytes, got {len(data) - offset}"
            )
        return length, offset

    @classmethod
    def decode_tlv(
        cls,
        data: bytes,
        offset: int = 0,
        depth: int = 1,
        max_depth: int = MAX_ASN1_RECURSION_DEPTH,
    ) -> Tuple[int, bytes, int]:
        if depth > max_depth:
            raise SnmpBerDecodeError(
                f"ASN.1 BER nesting depth {depth} exceeds maximum recursion depth {max_depth}"
            )
        if offset >= len(data):
            raise SnmpBerDecodeError("Truncated BER stream while reading tag byte")

        tag = data[offset]
        length, val_offset = cls.decode_length(data, offset + 1)
        val_bytes = data[val_offset : val_offset + length]
        return tag, val_bytes, val_offset + length

    @staticmethod
    def decode_integer(val_bytes: bytes, signed: bool = True, bits: int = 32) -> int:
        if len(val_bytes) == 0:
            raise SnmpBerDecodeError("Empty ASN.1 INTEGER value bytes")
        if len(val_bytes) > 1:
            if val_bytes[0] == 0x00 and (val_bytes[1] & 0x80) == 0:
                raise SnmpBerDecodeError("Non-minimal ASN.1 INTEGER encoding (redundant leading 0x00)")
            if signed and val_bytes[0] == 0xFF and (val_bytes[1] & 0x80) != 0:
                raise SnmpBerDecodeError("Non-minimal ASN.1 INTEGER encoding (redundant leading 0xFF)")

        val = int.from_bytes(val_bytes, byteorder="big", signed=True)
        if signed:
            min_val = -(1 << (bits - 1))
            max_val = (1 << (bits - 1)) - 1
            if not (min_val <= val <= max_val):
                raise SnmpBerDecodeError(f"Decoded signed integer {val} exceeds {bits}-bit bounds")
        else:
            if val < 0:
                raise SnmpBerDecodeError(f"Negative value {val} in unsigned SMIv2 application integer")
            max_val = (1 << bits) - 1
            if val > max_val:
                raise SnmpBerDecodeError(f"Decoded unsigned integer {val} exceeds {bits}-bit bounds")
        return val

    @staticmethod
    def decode_oid(val_bytes: bytes) -> str:
        if len(val_bytes) == 0:
            raise SnmpBerDecodeError("Empty OBJECT IDENTIFIER value bytes")
        if (val_bytes[-1] & 0x80) != 0:
            raise SnmpBerDecodeError("Unterminated base-128 VLQ in OBJECT IDENTIFIER")

        subids: List[int] = []
        acc = 0
        in_subid = False
        for b in val_bytes:
            if not in_subid and b == 0x80:
                raise SnmpBerDecodeError("Non-minimal base-128 VLQ sub-identifier (leading 0x80)")
            in_subid = True
            acc = (acc << 7) | (b & 0x7F)
            if (b & 0x80) == 0:
                subids.append(acc)
                acc = 0
                in_subid = False

        if not subids:
            raise SnmpBerDecodeError("OBJECT IDENTIFIER contains no sub-identifiers")

        first = subids[0]
        if first < 40:
            arcs = [0, first] + subids[1:]
        elif first < 80:
            arcs = [1, first - 40] + subids[1:]
        else:
            arcs = [2, first - 80] + subids[1:]

        if len(arcs) > MAX_OID_ARCS:
            raise SnmpBerDecodeError(f"Decoded OID exceeds {MAX_OID_ARCS} arcs")

        return ".".join(str(a) for a in arcs)

    @classmethod
    def decode_value(
        cls,
        tag: int,
        val_bytes: bytes,
        depth: int = 5,
        max_depth: int = MAX_ASN1_RECURSION_DEPTH,
    ) -> Tuple[str, Any]:
        if depth > max_depth:
            raise SnmpBerDecodeError(
                f"ASN.1 BER nesting depth {depth} exceeds maximum recursion depth {max_depth}"
            )
        if tag == SnmpAsn1Type.SEQUENCE.value or (tag & 0x20) != 0:
            # Constructed tag inside a VarBind value -> recurse to check depth limit
            if len(val_bytes) > 0:
                cls.decode_tlv(val_bytes, 0, depth=depth + 1, max_depth=max_depth)
            raise SnmpBerDecodeError(f"Constructed tag 0x{tag:02x} is not a valid SMIv2 VarBind scalar value")

        if tag == SnmpAsn1Type.INTEGER.value:
            return "Integer32", cls.decode_integer(val_bytes, signed=True, bits=32)
        elif tag == SnmpAsn1Type.OCTET_STRING.value:
            try:
                return "OctetString", val_bytes.decode("utf-8")
            except UnicodeDecodeError:
                return "OctetString", val_bytes
        elif tag == SnmpAsn1Type.NULL.value:
            if len(val_bytes) != 0:
                raise SnmpBerDecodeError(f"ASN.1 NULL must have length 0, got {len(val_bytes)}")
            return "Null", None
        elif tag == SnmpAsn1Type.OBJECT_IDENTIFIER.value:
            return "ObjectIdentifier", cls.decode_oid(val_bytes)
        elif tag == SnmpAsn1Type.IP_ADDRESS.value:
            if len(val_bytes) != 4:
                raise SnmpBerDecodeError(f"SMIv2 IpAddress must be 4 octets, got {len(val_bytes)}")
            return "IpAddress", ".".join(str(b) for b in val_bytes)
        elif tag == SnmpAsn1Type.COUNTER32.value:
            return "Counter32", cls.decode_integer(val_bytes, signed=False, bits=32)
        elif tag == SnmpAsn1Type.GAUGE32.value:
            return "Gauge32", cls.decode_integer(val_bytes, signed=False, bits=32)
        elif tag == SnmpAsn1Type.TIME_TICKS.value:
            return "TimeTicks", cls.decode_integer(val_bytes, signed=False, bits=32)
        elif tag == SnmpAsn1Type.OPAQUE.value:
            return "Opaque", val_bytes
        elif tag == SnmpAsn1Type.COUNTER64.value:
            return "Counter64", cls.decode_integer(val_bytes, signed=False, bits=64)
        elif tag == SnmpAsn1Type.NO_SUCH_OBJECT.value:
            if len(val_bytes) != 0:
                raise SnmpBerDecodeError("noSuchObject (0x80) exception must have length 0")
            return "noSuchObject", None
        elif tag == SnmpAsn1Type.NO_SUCH_INSTANCE.value:
            if len(val_bytes) != 0:
                raise SnmpBerDecodeError("noSuchInstance (0x81) exception must have length 0")
            return "noSuchInstance", None
        elif tag == SnmpAsn1Type.END_OF_MIB_VIEW.value:
            if len(val_bytes) != 0:
                raise SnmpBerDecodeError("endOfMibView (0x82) exception must have length 0")
            return "endOfMibView", None
        else:
            raise SnmpBerDecodeError(f"Unsupported ASN.1 VarBind value tag: 0x{tag:02x}")

    @classmethod
    def decode_message(
        cls,
        data: bytes,
        expected_community: Optional[str] = None,
        max_depth: int = MAX_ASN1_RECURSION_DEPTH,
    ) -> SnmpMessage:
        if not isinstance(data, (bytes, bytearray)) or len(data) == 0:
            raise SnmpBerDecodeError("Empty SNMP packet buffer")
        raw = bytes(data)

        # Depth 1: Outer SNMPv2c Message SEQUENCE (0x30)
        outer_tag, msg_body, next_offset = cls.decode_tlv(raw, 0, depth=1, max_depth=max_depth)
        if outer_tag != SnmpAsn1Type.SEQUENCE.value:
            raise SnmpBerDecodeError(
                f"Expected outer SEQUENCE tag 0x30, got 0x{outer_tag:02x}"
            )
        if next_offset != len(raw):
            raise SnmpBerDecodeError(
                f"Trailing bytes after outer SNMP SEQUENCE: {len(raw) - next_offset} extra bytes"
            )

        # Depth 2: version (0x02), community (0x04), PDU (0xA0..0xA7)
        ver_tag, ver_bytes, off = cls.decode_tlv(msg_body, 0, depth=2, max_depth=max_depth)
        if ver_tag != SnmpAsn1Type.INTEGER.value:
            raise SnmpBerDecodeError(f"Expected INTEGER tag 0x02 for SNMP version, got 0x{ver_tag:02x}")
        version = cls.decode_integer(ver_bytes, signed=True, bits=32)
        if version != SnmpVersion.V2C.value:
            raise UnsupportedSnmpVersionError(
                f"Unsupported SNMP version {version} (only SNMPv2c version=1 is supported)"
            )

        comm_tag, comm_bytes, off = cls.decode_tlv(msg_body, off, depth=2, max_depth=max_depth)
        if comm_tag != SnmpAsn1Type.OCTET_STRING.value:
            raise SnmpBerDecodeError(f"Expected OCTET STRING tag 0x04 for community, got 0x{comm_tag:02x}")
        try:
            community = comm_bytes.decode("utf-8")
        except UnicodeDecodeError as e:
            raise SnmpBerDecodeError("Non-UTF8 community string") from e

        if expected_community is not None and community != expected_community:
            raise SnmpCommunityMismatchError(
                f"SNMP community mismatch: expected {expected_community!r}, got {community!r}"
            )

        pdu_tag, pdu_body, off = cls.decode_tlv(msg_body, off, depth=2, max_depth=max_depth)
        if off != len(msg_body):
            raise SnmpBerDecodeError("Trailing bytes after SNMP PDU inside Message SEQUENCE")
        if pdu_tag not in VALID_PDU_TAGS:
            raise SnmpBerDecodeError(f"Unsupported or unknown SNMP PDU tag: 0x{pdu_tag:02x}")

        # Depth 3: request-id, error-status, error-index, VarBindList SEQUENCE (0x30)
        req_tag, req_bytes, p_off = cls.decode_tlv(pdu_body, 0, depth=3, max_depth=max_depth)
        if req_tag != SnmpAsn1Type.INTEGER.value:
            raise SnmpBerDecodeError(f"Expected INTEGER tag 0x02 for request-id, got 0x{req_tag:02x}")
        request_id = cls.decode_integer(req_bytes, signed=True, bits=32)

        es_tag, es_bytes, p_off = cls.decode_tlv(pdu_body, p_off, depth=3, max_depth=max_depth)
        if es_tag != SnmpAsn1Type.INTEGER.value:
            raise SnmpBerDecodeError(f"Expected INTEGER tag 0x02 for error-status, got 0x{es_tag:02x}")
        error_status = cls.decode_integer(es_bytes, signed=True, bits=32)

        ei_tag, ei_bytes, p_off = cls.decode_tlv(pdu_body, p_off, depth=3, max_depth=max_depth)
        if ei_tag != SnmpAsn1Type.INTEGER.value:
            raise SnmpBerDecodeError(f"Expected INTEGER tag 0x02 for error-index, got 0x{ei_tag:02x}")
        error_index = cls.decode_integer(ei_bytes, signed=True, bits=32)

        vbl_tag, vbl_body, p_off = cls.decode_tlv(pdu_body, p_off, depth=3, max_depth=max_depth)
        if vbl_tag != SnmpAsn1Type.SEQUENCE.value:
            raise SnmpBerDecodeError(f"Expected SEQUENCE tag 0x30 for VarBindList, got 0x{vbl_tag:02x}")
        if p_off != len(pdu_body):
            raise SnmpBerDecodeError("Trailing bytes after VarBindList in SNMP PDU")

        # Depth 4: Individual VarBind SEQUENCEs
        varbinds: List[SnmpVarBind] = []
        vb_off = 0
        while vb_off < len(vbl_body):
            vb_tag, vb_body, vb_off = cls.decode_tlv(vbl_body, vb_off, depth=4, max_depth=max_depth)
            if vb_tag != SnmpAsn1Type.SEQUENCE.value:
                raise SnmpBerDecodeError(f"Expected SEQUENCE tag 0x30 for VarBind, got 0x{vb_tag:02x}")

            # Depth 5: OID (0x06) + Value
            oid_tag, oid_bytes, inner_off = cls.decode_tlv(vb_body, 0, depth=5, max_depth=max_depth)
            if oid_tag != SnmpAsn1Type.OBJECT_IDENTIFIER.value:
                raise SnmpBerDecodeError(f"Expected OID tag 0x06 in VarBind, got 0x{oid_tag:02x}")
            oid_str = cls.decode_oid(oid_bytes)

            val_tag, val_bytes, inner_off = cls.decode_tlv(vb_body, inner_off, depth=5, max_depth=max_depth)
            if inner_off != len(vb_body):
                raise SnmpBerDecodeError("Trailing bytes inside VarBind SEQUENCE")

            asn1_name, decoded_val = cls.decode_value(val_tag, val_bytes, depth=5, max_depth=max_depth)
            varbinds.append(
                SnmpVarBind(
                    oid=oid_str,
                    asn1_type=asn1_name,
                    value=decoded_val,
                )
            )

        if pdu_tag == SnmpPduType.SNMPV2_TRAP.value:
            try:
                return SnmpTrap(
                    version=version,
                    community=community,
                    request_id=request_id,
                    error_status=error_status,
                    error_index=error_index,
                    varbinds=varbinds,
                )
            except ValueError as e:
                raise SnmpBerDecodeError(str(e)) from e
        elif pdu_tag == SnmpPduType.INFORM_REQUEST.value:
            try:
                return SnmpInform(
                    version=version,
                    community=community,
                    request_id=request_id,
                    error_status=error_status,
                    error_index=error_index,
                    varbinds=varbinds,
                )
            except ValueError as e:
                raise SnmpBerDecodeError(str(e)) from e
        elif pdu_tag == SnmpPduType.RESPONSE.value:
            return SnmpResponse(
                version=version,
                community=community,
                request_id=request_id,
                error_status=error_status,
                error_index=error_index,
                varbinds=varbinds,
            )
        elif pdu_tag == SnmpPduType.GET_BULK_REQUEST.value:
            return SnmpMessage(
                version=version,
                community=community,
                pdu_type=pdu_tag,
                request_id=request_id,
                error_status=error_status,
                error_index=error_index,
                non_repeaters=error_status,
                max_repetitions=error_index,
                varbinds=varbinds,
            )
        else:
            return SnmpMessage(
                version=version,
                community=community,
                pdu_type=pdu_tag,
                request_id=request_id,
                error_status=error_status,
                error_index=error_index,
                varbinds=varbinds,
            )


def build_golden_fixture_messages() -> Dict[str, SnmpMessage]:
    """
    Constructs the canonical SnmpMessage objects corresponding to the 5 Gate 12 Golden Hex Fixtures.
    """
    f1 = SnmpTrap(
        community="netspout-lab",
        request_id=1001,
        sys_uptime=8640000,
        trap_oid="1.3.6.1.6.3.1.1.5.3",
        varbinds=[
            SnmpVarBind(oid="1.3.6.1.2.1.2.2.1.1.1", asn1_type="Integer32", value=1),
            SnmpVarBind(oid="1.3.6.1.2.1.2.2.1.7.1", asn1_type="Integer32", value=1),
            SnmpVarBind(oid="1.3.6.1.2.1.2.2.1.8.1", asn1_type="Integer32", value=2),
        ],
    )
    f2 = SnmpTrap(
        community="netspout-lab",
        request_id=1002,
        sys_uptime=8643000,
        trap_oid="1.3.6.1.6.3.1.1.5.4",
        varbinds=[
            SnmpVarBind(oid="1.3.6.1.2.1.2.2.1.1.1", asn1_type="Integer32", value=1),
            SnmpVarBind(oid="1.3.6.1.2.1.2.2.1.7.1", asn1_type="Integer32", value=1),
            SnmpVarBind(oid="1.3.6.1.2.1.2.2.1.8.1", asn1_type="Integer32", value=1),
        ],
    )
    f3 = SnmpInform(
        community="netspout-lab",
        request_id=2001,
        sys_uptime=8640500,
        trap_oid="1.3.6.1.2.1.15.7.2",
        varbinds=[
            SnmpVarBind(oid="1.3.6.1.2.1.15.3.1.2.10.255.0.2", asn1_type="Integer32", value=1),
        ],
    )
    f4 = SnmpMessage(
        community="netspout-lab",
        pdu_type=SnmpPduType.GET_REQUEST.value,
        request_id=3001,
        varbinds=[
            SnmpVarBind(oid="1.3.6.1.2.1.2.2.1.8.1", asn1_type="Null", value=None),
        ],
    )
    f5 = SnmpResponse(
        community="netspout-lab",
        request_id=3001,
        varbinds=[
            SnmpVarBind(oid="1.3.6.1.2.1.2.2.1.8.1", asn1_type="Integer32", value=1),
        ],
    )
    return {
        "fixture_1_linkdown_trap": f1,
        "fixture_2_linkup_trap": f2,
        "fixture_3_bgp_backward_transition_inform": f3,
        "fixture_4_get_request": f4,
        "fixture_5_get_response": f5,
    }


def verify_golden_fixtures() -> List[Dict[str, Any]]:
    """
    Encodes and decodes all 5 Gate 12 Golden Hex Fixtures and returns a detailed
    verification report with expected/actual length, expected/actual SHA-256, and PASS/FAIL.
    """
    messages = build_golden_fixture_messages()
    results: List[Dict[str, Any]] = []

    for key, spec in GOLDEN_HEX_FIXTURES.items():
        msg = messages[key]
        expected_bytes = bytes.fromhex(spec["expected_hex"])
        actual_bytes = SnmpBerEncoder.encode_message(msg)
        decoded_msg = SnmpBerDecoder.decode_message(actual_bytes, expected_community="netspout-lab")
        reencoded_bytes = SnmpBerEncoder.encode_message(decoded_msg)

        expected_sha256 = hashlib.sha256(expected_bytes).hexdigest()
        actual_sha256 = hashlib.sha256(actual_bytes).hexdigest()
        passed = (
            actual_bytes == expected_bytes
            and reencoded_bytes == expected_bytes
            and len(actual_bytes) == spec["expected_length"]
        )

        # For Fixture 3, also verify the matching Response-PDU (0xA2)
        if "expected_response_hex" in spec:
            resp_msg = SnmpResponse.from_inform(msg)
            resp_bytes = SnmpBerEncoder.encode_message(resp_msg)
            expected_resp_bytes = bytes.fromhex(spec["expected_response_hex"])
            passed = passed and (resp_bytes == expected_resp_bytes)

        results.append(
            {
                "fixture_id": key,
                "fixture_name": spec["name"],
                "expected_length": spec["expected_length"],
                "actual_length": len(actual_bytes),
                "expected_sha256": expected_sha256,
                "actual_sha256": actual_sha256,
                "expected_hex": spec["expected_hex"],
                "actual_hex": actual_bytes.hex(),
                "status": "PASS" if passed else "FAIL",
            }
        )
    return results
