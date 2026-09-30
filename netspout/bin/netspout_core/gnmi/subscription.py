"""
NetSpout Gate 13B — gNMI Notification Builder & Subscription State Machine Support.

Handles:
  - Prefix compression (Notification.prefix + relative Update.path)
  - Snapshot Notification construction for Get, Subscribe ONCE, Subscribe POLL, and initial STREAM sync
  - Redundancy suppression (suppress_redundant) and heartbeat_interval tracking
"""

from dataclasses import dataclass, field
import json
import time
from typing import Any, Dict, List, Optional, Tuple

from .encoding import build_updates_for_payload
from .path_parser import ParsedGnmiPath, ParsedPathElem
from .proto import gnmi_pb2
from .sensor_registry import ResolvedSensorSample


def split_prefix_and_relative(
    prefix_elems: Tuple[ParsedPathElem, ...],
    concrete_elems: Tuple[ParsedPathElem, ...],
) -> Tuple[Tuple[ParsedPathElem, ...], Tuple[ParsedPathElem, ...]]:
    """
    If prefix_elems is a valid prefix of concrete_elems, splits concrete_elems into
    (matched_concrete_prefix, relative_tail) to support gNMI prefix compression (T13B-09).
    """
    if not prefix_elems or len(prefix_elems) >= len(concrete_elems):
        return (), concrete_elems

    for idx, p_elem in enumerate(prefix_elems):
        c_elem = concrete_elems[idx]
        if p_elem.name != c_elem.name:
            return (), concrete_elems
        for k, v in p_elem.keys.items():
            if v != "*" and c_elem.keys.get(k) != v:
                return (), concrete_elems

    return concrete_elems[: len(prefix_elems)], concrete_elems[len(prefix_elems) :]


def build_notification_from_sample(
    sample: ResolvedSensorSample,
    timestamp_ns: int,
    encoding: int,
    request_prefix_elems: Tuple[ParsedPathElem, ...] = (),
) -> gnmi_pb2.Notification:
    """
    Constructs a canonical gnmi_pb2.Notification from a ResolvedSensorSample,
    preserving target, origin, and optional prefix compression.
    """
    matched_prefix, rel_elems = split_prefix_and_relative(
        request_prefix_elems, sample.concrete_path.elems
    )

    notif_prefix = gnmi_pb2.Path()
    notif_prefix.target = sample.concrete_path.target
    notif_prefix.origin = sample.concrete_path.origin
    for pe in matched_prefix:
        elem_proto = notif_prefix.elem.add()
        elem_proto.name = pe.name
        for k, v in pe.keys.items():
            elem_proto.key[k] = str(v)

    updates = build_updates_for_payload(
        relative_elems=rel_elems,
        payload=sample.payload,
        encoding=encoding,
        yang_module=sample.yang_module,
        leaf_yang_type=sample.leaf_yang_type,
    )

    return gnmi_pb2.Notification(
        timestamp=int(timestamp_ns),
        prefix=notif_prefix,
        update=updates,
        atomic=False,
    )


def canonical_payload_fingerprint(payload: Any) -> str:
    """Deterministic string fingerprint of a resolved sensor payload for ON_CHANGE and suppress_redundant."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


@dataclass
class SubscriptionItemTracker:
    """Tracks per-Subscription state for STREAM (SAMPLE / ON_CHANGE), suppress_redundant, and heartbeat."""
    parsed_path: ParsedGnmiPath
    request_prefix_elems: Tuple[ParsedPathElem, ...]
    mode: int  # gnmi_pb2.SubscriptionMode
    sample_interval_ns: int
    suppress_redundant: bool
    heartbeat_interval_ns: int
    last_fingerprints: Dict[str, str] = field(default_factory=dict)
    last_emit_time_ns: Dict[str, int] = field(default_factory=dict)
    next_sample_due_ns: int = 0

    def should_emit_sample(
        self,
        concrete_xpath: str,
        fingerprint: str,
        now_ns: int,
    ) -> bool:
        prev_fp = self.last_fingerprints.get(concrete_xpath)
        prev_ts = self.last_emit_time_ns.get(concrete_xpath, 0)

        if self.suppress_redundant and prev_fp == fingerprint:
            if self.heartbeat_interval_ns > 0 and (now_ns - prev_ts) >= self.heartbeat_interval_ns:
                self.last_emit_time_ns[concrete_xpath] = now_ns
                return True
            return False

        self.last_fingerprints[concrete_xpath] = fingerprint
        self.last_emit_time_ns[concrete_xpath] = now_ns
        return True

    def should_emit_on_change(
        self,
        concrete_xpath: str,
        fingerprint: str,
        now_ns: int,
        is_heartbeat_check: bool = False,
    ) -> bool:
        prev_fp = self.last_fingerprints.get(concrete_xpath)
        prev_ts = self.last_emit_time_ns.get(concrete_xpath, 0)

        if prev_fp != fingerprint:
            self.last_fingerprints[concrete_xpath] = fingerprint
            self.last_emit_time_ns[concrete_xpath] = now_ns
            return True

        if (
            is_heartbeat_check
            and self.heartbeat_interval_ns > 0
            and (now_ns - prev_ts) >= self.heartbeat_interval_ns
        ):
            self.last_emit_time_ns[concrete_xpath] = now_ns
            return True

        return False
