"""Cisco ASA event generator for sourcetype ``cisco:asa`` (Splunk Add-on for Cisco ASA, Splunkbase 1620).

Emits the documented ASA connection messages (302013/302014 TCP, 302015/302016 UDP, 106023 deny) through
SplunkLogEngine.format_cisco_asa_log, so the raw text keeps one vendor format. A build is always followed by its
teardown with the same connection id. Output is a pure function of (count, seed, now): a preview and a delivery
built from the same arguments are identical.
"""
import random
import time
from datetime import datetime, timezone
from typing import List, Optional

from netspout_core.log_engine import SplunkLogEngine
from netspout_core.models import LogEntry, Node, NodeType

SOURCETYPE = "cisco:asa"
HOST = "asa-fw-01"
_INTERNAL = [f"10.20.10.{n}" for n in (45, 46, 52, 60, 71)]
_EXTERNAL = ["198.51.100.80", "198.51.100.81", "203.0.113.88", "192.0.2.14"]
_SERVICES = [("TCP", 443), ("TCP", 80), ("TCP", 22), ("UDP", 53), ("UDP", 123)]


def _firewall() -> Node:
    return Node(id=HOST, name=HOST, type=NodeType.FIREWALL, x=0, y=0, ip_address="10.20.0.1", vendor="cisco_asa", sourcetype=SOURCETYPE)


def generate_asa_entries(count: int, seed: Optional[int] = None, now: Optional[float] = None) -> List[LogEntry]:
    """``count`` events: connection build/teardown pairs plus occasional 106023 denies. ``now`` is epoch seconds (default: current time)."""
    rng = random.Random(seed)
    fw = _firewall()
    fixed = datetime.fromtimestamp(now if now is not None else time.time(), tz=timezone.utc)
    entries: List[LogEntry] = []
    cid = rng.randint(100000, 900000)
    while len(entries) < count:
        proto, port = rng.choice(_SERVICES)
        client, server = rng.choice(_INTERNAL), rng.choice(_EXTERNAL)
        sport = rng.randint(1025, 65000)
        # the formatter reads the clock; pin it so output depends only on (count, seed, now)
        common = dict(device=fw, src_ip=server, dest_ip=client, src_port=port, dest_port=sport, proto=proto, signature="ASA_CONNECTION",
                      src_interface="outside", dest_interface="inside")
        if rng.random() < 0.2:
            deny = rng.choice(_EXTERNAL)
            entries.append(SplunkLogEngine.format_cisco_asa_log(**{**common, "src_ip": deny, "src_port": sport, "dest_port": port, "proto": proto}, action="blocked", status="denied"))
            continue
        cid += rng.randint(1, 40)
        build = SplunkLogEngine.format_cisco_asa_log(**common, action="allowed", status="success", connection_id=cid, event_type="build", direction="outbound")
        tear = SplunkLogEngine.format_cisco_asa_log(**common, action="allowed", status="success", connection_id=cid, event_type="teardown",
                                                    duration_ms=rng.randint(1, 600) * 1000, bytes_count=rng.randint(200, 2_000_000))
        entries += [build, tear]
    entries = entries[:count]
    header = f"{fixed.strftime('%b')} {fixed.day:2d} {fixed.strftime('%H:%M:%S')}"
    for e in entries:
        # replace the formatter's wall-clock header with the pinned one
        e.raw_log = _repin(e.raw_log, header)
        e.timestamp = fixed.strftime("%Y-%m-%d %H:%M:%S.000 UTC")
    return entries


def _repin(raw: str, header: str) -> str:
    """The formatter writes '<Mon dd HH:MM:SS> <host> %ASA-...': keep everything from the host onward."""
    return header + raw[raw.index(" " + HOST + " "):]
