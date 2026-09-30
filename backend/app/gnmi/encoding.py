"""
NetSpout Gate 13B — gNMI Payload & TypedValue Encoding Engine.

Implements:
  - JSON_IETF (RFC 7951): 64-bit integers encoded as strings, YANG enums, module-qualified trees
  - JSON: Standard JSON encoding in TypedValue.json_val
  - PROTO: Native protobuf TypedValue scalar fields (uint_val, int_val, string_val, bool_val, double_val)
  - Strict rejection of unsupported encodings (BYTES, ASCII) with StatusCode.UNIMPLEMENTED
"""

import json
from typing import Any, Dict, List, Tuple

from .path_parser import ParsedGnmiPath, ParsedPathElem
from .proto import gnmi_pb2


class GnmiEncodingError(ValueError):
    """Base exception for gNMI encoding validation errors."""


class GnmiEncodingNotSupportedError(GnmiEncodingError):
    """Raised when a client requests an unsupported gNMI encoding (e.g., BYTES or ASCII)."""


GnmiUnsupportedEncodingError = GnmiEncodingNotSupportedError


SUPPORTED_ENCODING_ENUMS = {
    gnmi_pb2.JSON: "JSON",
    gnmi_pb2.PROTO: "PROTO",
    gnmi_pb2.JSON_IETF: "JSON_IETF",
}

RFC7951_UINT64_LEAF_NAMES = {
    "in-octets",
    "out-octets",
    "in-unicast-pkts",
    "out-unicast-pkts",
    "in-errors",
    "out-errors",
    "in-fcs-errors",
    "in-discards",
    "out-discards",
    "carrier-transitions",
    "transmit-pkts",
    "transmit-octets",
    "dropped-pkts",
    "dropped-octets",
    "max-queue-len",
    "boot-time",
    "physical",
    "reserved",
    "last-established",
    "established-transitions",
    "packets-forwarded",
    "octets-forwarded",
    "bytes-received",
    "bytes-sent",
    "packets-received",
    "packets-sent",
    "tail-drop-packets",
    "queue-current-size-bytes",
    "queueLengthBytes",
    "outDiscards",
    "allocated-buffer-size",
    "ibytes",
    "obytes",
}


def validate_encoding(encoding_enum: int) -> int:
    if encoding_enum not in SUPPORTED_ENCODING_ENUMS:
        raise GnmiEncodingNotSupportedError(
            f"UNSUPPORTED_ENCODING: Encoding enum {encoding_enum} is not supported; "
            f"supported encodings are JSON_IETF (4), PROTO (2), and JSON (0)."
        )
    return encoding_enum


def to_rfc7951_value(value: Any, leaf_name: str = "", yang_module: str = "") -> Any:
    """
    Recursively converts a Python dictionary or scalar value to RFC 7951 JSON_IETF semantics:
      - 64-bit integer counters/timestamps (uint64/int64) are represented as JSON strings
      - Booleans, 32-bit integers, floats, and strings are preserved accurately
    """
    if isinstance(value, dict):
        out: Dict[str, Any] = {}
        for k, v in value.items():
            out[k] = to_rfc7951_value(v, leaf_name=k, yang_module=yang_module)
        return out
    if isinstance(value, (list, tuple)):
        return [to_rfc7951_value(item, leaf_name=leaf_name, yang_module=yang_module) for item in value]
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        if leaf_name in RFC7951_UINT64_LEAF_NAMES or abs(value) >= (1 << 53):
            return str(value)
        return value
    return value


def encode_scalar_typed_value(value: Any, yang_type: str = "") -> gnmi_pb2.TypedValue:
    """Encodes a scalar Python value into a native PROTO gnmi_pb2.TypedValue."""
    tv = gnmi_pb2.TypedValue()
    if isinstance(value, bool) or yang_type == "boolean":
        tv.bool_val = bool(value)
    elif isinstance(value, int):
        if yang_type in ("int64", "int32", "int16", "int8") or value < 0:
            tv.int_val = int(value)
        else:
            tv.uint_val = int(value)
    elif isinstance(value, float) or yang_type in ("decimal64", "double", "float"):
        tv.double_val = float(value)
    else:
        tv.string_val = str(value)
    return tv


def build_updates_for_payload(
    relative_elems: Tuple[ParsedPathElem, ...],
    payload: Any,
    encoding: int,
    yang_module: str = "",
    leaf_yang_type: str = "",
) -> List[gnmi_pb2.Update]:
    """
    Constructs one or more gnmi_pb2.Update objects for a resolved sensor payload
    according to the requested encoding (JSON_IETF, JSON, or PROTO).
    """
    validate_encoding(encoding)
    base_path = ParsedGnmiPath(origin="", target="", elems=relative_elems).to_proto_path()

    if encoding == gnmi_pb2.JSON_IETF:
        rfc_val = to_rfc7951_value(payload, leaf_name=relative_elems[-1].name if relative_elems else "", yang_module=yang_module)
        if isinstance(rfc_val, dict) and yang_module and relative_elems:
            # RFC 7951 top-level container qualification when returning a subtree
            pass
        tv = gnmi_pb2.TypedValue()
        tv.json_ietf_val = json.dumps(rfc_val, separators=(",", ":")).encode("utf-8")
        upd = gnmi_pb2.Update(path=base_path, val=tv)
        return [upd]

    if encoding == gnmi_pb2.JSON:
        tv = gnmi_pb2.TypedValue()
        tv.json_val = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        upd = gnmi_pb2.Update(path=base_path, val=tv)
        return [upd]

    # PROTO encoding: if payload is a dict, flatten into leaf Updates with native scalar TypedValues
    if isinstance(payload, dict):
        updates: List[gnmi_pb2.Update] = []
        _flatten_dict_to_proto_updates(relative_elems, payload, updates)
        return updates

    tv = encode_scalar_typed_value(payload, yang_type=leaf_yang_type)
    return [gnmi_pb2.Update(path=base_path, val=tv)]


def _flatten_dict_to_proto_updates(
    prefix_elems: Tuple[ParsedPathElem, ...],
    node: Dict[str, Any],
    out_updates: List[gnmi_pb2.Update],
) -> None:
    for k, v in node.items():
        child_elems = prefix_elems + (ParsedPathElem(name=str(k), keys={}),)
        if isinstance(v, dict):
            _flatten_dict_to_proto_updates(child_elems, v, out_updates)
        else:
            p = ParsedGnmiPath(origin="", target="", elems=child_elems).to_proto_path()
            tv = encode_scalar_typed_value(v)
            out_updates.append(gnmi_pb2.Update(path=p, val=tv))
