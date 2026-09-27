"""
Exporter Session State for NetSpout Native Flow Transport.
Maintains stateful sequence numbers, sysUpTime reference, active templates,
and transmission counters scoped to (run_id, node_id).
Conforms to Gate 11 Architecture Section 7 and RFC 3954 / RFC 7011 requirements.
"""

import time
from typing import Dict, Any, Optional, Tuple


class ExporterSession:
    """
    Maintains session state for an exporter device.
    Scoped per (run_id, node_id) to avoid global state cross-talk.
    """
    def __init__(
        self,
        node_id: str,
        exporter_ip: str = "127.0.0.1",
        observation_domain_id: int = 1,
        source_id: Optional[int] = None,
        base_time_epoch_ms: Optional[int] = None,
        template_refresh_policy: str = "PERIODIC"
    ):
        self.node_id = node_id
        self.exporter_ip = exporter_ip
        self.observation_domain_id = observation_domain_id & 0xFFFFFFFF
        self.source_id = (source_id if source_id is not None else observation_domain_id) & 0xFFFFFFFF
        self.template_refresh_policy = template_refresh_policy.upper()
        
        now_ms = int(time.time() * 1000)
        self.base_time_epoch_ms = base_time_epoch_ms if base_time_epoch_ms is not None else now_ms
        self.sequence_number = 0
        self.active_templates: Dict[int, Any] = {}
        self.template_last_sent_time = 0.0
        self.template_packets_sent_count = 0
        self.total_packets_sent = 0
        self.total_records_sent = 0
        self.total_bytes_sent = 0

    def get_sys_uptime_ms(self, current_time_epoch_ms: Optional[int] = None) -> int:
        """
        Returns relative sysUpTime in milliseconds since exporter boot/session start.
        """
        now_ms = current_time_epoch_ms if current_time_epoch_ms is not None else int(time.time() * 1000)
        elapsed = now_ms - self.base_time_epoch_ms
        return max(0, elapsed) & 0xFFFFFFFF

    def force_template_refresh(self) -> None:
        """Forces the next transmission to include templates (e.g. after collector restart)."""
        self.template_last_sent_time = 0.0

    def should_send_template(
        self,
        current_time: Optional[float] = None,
        refresh_interval_sec: float = 60.0,
        refresh_packets: int = 20,
        policy: Optional[str] = None
    ) -> bool:
        """
        Evaluates whether templates must be transmitted:
        1. Never sent yet (initial burst)
        2. Policy is EVERY_BURST
        3. Elapsed time exceeds refresh_interval_sec
        4. Packets sent since last template exceeds refresh_packets
        """
        effective_policy = (policy or self.template_refresh_policy).upper()
        if effective_policy == "EVERY_BURST":
            return True
        if self.template_last_sent_time == 0.0:
            return True
        now = current_time if current_time is not None else time.time()
        if (now - self.template_last_sent_time) >= refresh_interval_sec:
            return True
        if self.template_packets_sent_count >= refresh_packets:
            return True
        return False

    def record_template_sent(self, current_time: Optional[float] = None) -> None:
        """Updates template transmission timestamp and resets packet counter."""
        self.template_last_sent_time = current_time if current_time is not None else time.time()
        self.template_packets_sent_count = 0

    def advance_sequence(self, count: int) -> Tuple[int, int]:
        """
        Advances the sequence number by the specified count (records or packets depending on protocol).
        Returns (start_seq, next_seq).
        """
        start_seq = self.sequence_number
        self.sequence_number = (self.sequence_number + count) & 0xFFFFFFFF
        return start_seq, self.sequence_number

    def record_packet_sent(self, record_count: int, byte_count: int) -> None:
        """Records transmission of a single datagram."""
        self.total_packets_sent += 1
        self.template_packets_sent_count += 1
        self.total_records_sent += record_count
        self.total_bytes_sent += byte_count

    def reset(self) -> None:
        """Resets counters and sequence number for a fresh run."""
        self.sequence_number = 0
        self.template_last_sent_time = 0.0
        self.template_packets_sent_count = 0
        self.total_packets_sent = 0
        self.total_records_sent = 0
        self.total_bytes_sent = 0
