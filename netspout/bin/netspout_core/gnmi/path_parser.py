"""
NetSpout Gate 13B — Deterministic Structured gNMI Path Parser & Validator.

Supports:
  - Structured gnmi_pb2.Path (origin, target, elem[] with PathElem.name and PathElem.key)
  - String XPath parsing with origin prefix (e.g. "openconfig:/interfaces/interface[name=Ethernet1/1]/state")
  - Prefix + relative path composition
  - Wildcard key predicates ([name=*]) where permitted by sensor definitions
  - Strict validation of malformed brackets, predicates, and path depth bounds
"""

from dataclasses import dataclass, field
import re
from typing import Dict, List, Optional, Tuple

from .proto import gnmi_pb2

MAX_PATH_DEPTH = 16
MAX_KEY_LENGTH = 128
_VALID_IDENT_RE = re.compile(r"^[A-Za-z0-9_.\-:]+$")


class GnmiPathParseError(ValueError):
    """Raised when a gNMI Path or XPath string is syntactically malformed."""


@dataclass(frozen=True)
class ParsedPathElem:
    name: str
    keys: Dict[str, str] = field(default_factory=dict)

    def to_xpath_segment(self) -> str:
        if not self.keys:
            return self.name
        key_parts = "".join(f"[{k}={self.keys[k]}]" for k in sorted(self.keys.keys()))
        return f"{self.name}{key_parts}"


@dataclass(frozen=True)
class ParsedGnmiPath:
    origin: str
    target: str
    elems: Tuple[ParsedPathElem, ...]

    @property
    def canonical_xpath(self) -> str:
        if not self.elems:
            return "/"
        return "/" + "/".join(e.to_xpath_segment() for e in self.elems)

    @property
    def pattern_xpath(self) -> str:
        """Returns the path with all key values normalized to '*' for sensor registry lookup."""
        if not self.elems:
            return "/"
        parts: List[str] = []
        for e in self.elems:
            if not e.keys:
                parts.append(e.name)
            else:
                k_str = "".join(f"[{k}=*]" for k in sorted(e.keys.keys()))
                parts.append(f"{e.name}{k_str}")
        return "/" + "/".join(parts)

    def to_proto_path(self, include_target: bool = False, include_origin: bool = False) -> gnmi_pb2.Path:
        p = gnmi_pb2.Path()
        if include_origin and self.origin:
            p.origin = self.origin
        if include_target and self.target:
            p.target = self.target
        for e in self.elems:
            pe = p.elem.add()
            pe.name = e.name
            for k, v in e.keys.items():
                pe.key[k] = str(v)
        return p


def _validate_elem_name_and_keys(name: str, keys: Dict[str, str]) -> str:
    if not name or not name.strip():
        raise GnmiPathParseError("Empty PathElem name is invalid")
    if "[" in name or "]" in name:
        raise GnmiPathParseError(f"Malformed bracket in PathElem name: {name!r}")
    # Strip module prefix on individual element name if present (e.g. openconfig-interfaces:interfaces -> interfaces)
    clean_name = name.split(":", 1)[-1] if ":" in name else name
    if not _VALID_IDENT_RE.match(clean_name):
        raise GnmiPathParseError(f"Invalid characters in PathElem name: {name!r}")
    for k, v in keys.items():
        if not k or not _VALID_IDENT_RE.match(k):
            raise GnmiPathParseError(f"Invalid key name {k!r} in PathElem {name!r}")
        if v is None or v == "" or len(str(v)) > MAX_KEY_LENGTH:
            raise GnmiPathParseError(f"Invalid or oversized key value for {k!r} in PathElem {name!r}")
        if "[" in str(v) or "]" in str(v):
            raise GnmiPathParseError(f"Unclosed or nested bracket in key value {v!r} for {k!r}")
    return clean_name


def parse_xpath_string(xpath: str, default_origin: str = "openconfig", target: str = "") -> ParsedGnmiPath:
    """
    Parses a string XPath (with optional 'origin:/path') into a validated ParsedGnmiPath.
    Rejects unclosed brackets, empty segments, or malformed key predicates.
    """
    if xpath is None:
        raise GnmiPathParseError("XPath cannot be None")
    raw = xpath.strip()
    if not raw:
        raise GnmiPathParseError("Empty XPath is invalid")

    origin = default_origin or "openconfig"
    # Check for origin:/... prefix before the first slash
    if ":/" in raw and not raw.startswith("/"):
        orig_part, rest = raw.split(":/", 1)
        if "[" not in orig_part and "/" not in orig_part:
            origin = orig_part.strip() or origin
            raw = "/" + rest

    if not raw.startswith("/"):
        raw = "/" + raw

    # Split path into segments while respecting [...] brackets
    segments: List[str] = []
    buf: List[str] = []
    bracket_depth = 0
    for ch in raw[1:]:
        if ch == "[":
            bracket_depth += 1
            if bracket_depth > 1:
                raise GnmiPathParseError(f"Nested brackets are invalid in XPath: {xpath!r}")
            buf.append(ch)
        elif ch == "]":
            bracket_depth -= 1
            if bracket_depth < 0:
                raise GnmiPathParseError(f"Unmatched closing bracket in XPath: {xpath!r}")
            buf.append(ch)
        elif ch == "/" and bracket_depth == 0:
            seg = "".join(buf)
            if not seg:
                raise GnmiPathParseError(f"Empty path segment '//' in XPath: {xpath!r}")
            segments.append(seg)
            buf = []
        else:
            buf.append(ch)

    if bracket_depth != 0:
        raise GnmiPathParseError(f"Unclosed bracket in XPath: {xpath!r}")

    if buf:
        segments.append("".join(buf))

    if len(segments) > MAX_PATH_DEPTH:
        raise GnmiPathParseError(f"Path depth {len(segments)} exceeds maximum {MAX_PATH_DEPTH}")

    parsed_elems: List[ParsedPathElem] = []
    for seg in segments:
        if "[" not in seg:
            if "]" in seg:
                raise GnmiPathParseError(f"Unmatched bracket in segment {seg!r}")
            # Check if first segment has module prefix like Cisco-IOS-XR-infra-statsd-oper:infra-statistics
            if ":" in seg and not parsed_elems and origin == "openconfig":
                mod_prefix, elem_name = seg.split(":", 1)
                if mod_prefix.startswith("Cisco-IOS-"):
                    origin = mod_prefix
                seg = elem_name
            clean_name = _validate_elem_name_and_keys(seg, {})
            parsed_elems.append(ParsedPathElem(name=clean_name, keys={}))
        else:
            first_bracket = seg.index("[")
            elem_name = seg[:first_bracket]
            if ":" in elem_name and not parsed_elems and origin == "openconfig":
                mod_prefix, elem_name = elem_name.split(":", 1)
                if mod_prefix.startswith("Cisco-IOS-"):
                    origin = mod_prefix
            predicates_str = seg[first_bracket:]
            keys: Dict[str, str] = {}
            pos = 0
            while pos < len(predicates_str):
                if predicates_str[pos] != "[":
                    raise GnmiPathParseError(f"Malformed predicate in segment {seg!r}")
                end_idx = predicates_str.find("]", pos)
                if end_idx == -1:
                    raise GnmiPathParseError(f"Unclosed bracket in segment {seg!r}")
                inner = predicates_str[pos + 1 : end_idx]
                if "=" not in inner:
                    raise GnmiPathParseError(f"Missing '=' in key predicate [{inner}] in {seg!r}")
                k, v = inner.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'").strip('"')
                keys[k] = v
                pos = end_idx + 1
            clean_name = _validate_elem_name_and_keys(elem_name, keys)
            parsed_elems.append(ParsedPathElem(name=clean_name, keys=keys))

    return ParsedGnmiPath(origin=origin, target=target, elems=tuple(parsed_elems))


def parse_proto_path(
    path: Optional[gnmi_pb2.Path],
    prefix: Optional[gnmi_pb2.Path] = None,
    default_target: str = "",
) -> ParsedGnmiPath:
    """
    Merges an optional gnmi_pb2.Path prefix and relative gnmi_pb2.Path into a validated ParsedGnmiPath.
    Also handles clients that pass a raw XPath string in a single PathElem.name or legacy Path.element.
    """
    origin = ""
    target = default_target
    combined_elems: List[ParsedPathElem] = []

    for proto_p in (prefix, path):
        if proto_p is None:
            continue
        if proto_p.origin:
            origin = proto_p.origin.strip()
        if proto_p.target:
            target = proto_p.target.strip()

        if len(proto_p.elem) > 0:
            for pe in proto_p.elem:
                raw_name = pe.name
                # Handle case where client passed full XPath or bracketed segment inside pe.name
                if ("/" in raw_name or "[" in raw_name) and len(pe.key) == 0:
                    sub = parse_xpath_string(raw_name, default_origin=origin or "openconfig", target=target)
                    if sub.origin != "openconfig" and not origin:
                        origin = sub.origin
                    combined_elems.extend(sub.elems)
                else:
                    if ":" in raw_name and not combined_elems and not origin:
                        mod_prefix, rest_name = raw_name.split(":", 1)
                        if mod_prefix.startswith("Cisco-IOS-"):
                            origin = mod_prefix
                        raw_name = rest_name
                    keys_dict = {str(k): str(v) for k, v in pe.key.items()}
                    clean_name = _validate_elem_name_and_keys(raw_name, keys_dict)
                    combined_elems.append(ParsedPathElem(name=clean_name, keys=keys_dict))
        elif len(proto_p.element) > 0:
            joined = "/" + "/".join(proto_p.element)
            sub = parse_xpath_string(joined, default_origin=origin or "openconfig", target=target)
            combined_elems.extend(sub.elems)

    if len(combined_elems) > MAX_PATH_DEPTH:
        raise GnmiPathParseError(f"Combined path depth {len(combined_elems)} exceeds maximum {MAX_PATH_DEPTH}")

    if not origin:
        origin = "openconfig"

    return ParsedGnmiPath(origin=origin, target=target, elems=tuple(combined_elems))


def to_proto_path(
    parsed: ParsedGnmiPath,
    include_target: bool = True,
    include_origin: bool = True,
) -> gnmi_pb2.Path:
    """Converts a ParsedGnmiPath to a gnmi_pb2.Path."""
    return parsed.to_proto_path(include_target=include_target, include_origin=include_origin)

