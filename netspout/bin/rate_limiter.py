# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/rate_limiter.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""
NetSpout Token-Bucket Rate Limiter & Transmission Pacer.
Guarantees bounded packet emission rates and total scenario packet caps.
Conforms to Gate 11 Threat Model Section 3.2.
"""

import time
from typing import Optional

from netspout_core.transport_safety import RateLimitExceededException

DEFAULT_RATE_PPS = 100
MAX_ALLOWED_RATE_PPS = 1000
DEFAULT_MAX_PACKETS_PER_RUN = 10000


class TokenBucketRateLimiter:
    """
    Token-bucket rate limiter for pacing UDP datagram transmission.
    Prevents microburst saturation of local interfaces and collector buffers.
    """
    def __init__(
        self,
        rate_pps: int = DEFAULT_RATE_PPS,
        burst_capacity: Optional[int] = None,
        max_packets_per_run: int = DEFAULT_MAX_PACKETS_PER_RUN
    ):
        self.rate_pps = min(max(1, rate_pps), MAX_ALLOWED_RATE_PPS)
        self.capacity = burst_capacity if burst_capacity is not None else self.rate_pps
        self.tokens = float(self.capacity)
        self.max_packets_per_run = max_packets_per_run
        
        self.last_update_time = time.time()
        self.total_packets_emitted = 0
        self.total_sleep_time_sec = 0.0

    def acquire(self, packets: int = 1, test_mode: bool = False) -> None:
        """
        Consumes tokens for the requested packet count.
        Enforces maximum packets per run ceiling.
        In real mode, sleeps if necessary to maintain target rate.
        In test mode (time_mode == 'TEST'), advances virtual accounting without sleeping.
        """
        # 1. Enforce run ceiling
        if (self.total_packets_emitted + packets) > self.max_packets_per_run:
            raise RateLimitExceededException(
                f"Rate ceiling exceeded: Attempted to emit {self.total_packets_emitted + packets} packets, "
                f"which exceeds the scenario maximum cap of {self.max_packets_per_run} packets."
            )

        now = time.time()
        elapsed = now - self.last_update_time
        self.last_update_time = now

        # Replenish tokens
        self.tokens = min(float(self.capacity), self.tokens + (elapsed * self.rate_pps))

        if self.tokens < packets:
            needed = packets - self.tokens
            sleep_duration = needed / self.rate_pps
            if not test_mode and sleep_duration > 0:
                time.sleep(sleep_duration)
                self.total_sleep_time_sec += sleep_duration
            self.tokens = 0.0
            self.last_update_time = time.time()
        else:
            self.tokens -= packets

        self.total_packets_emitted += packets

    def reset(self) -> None:
        """Resets the limiter state for a new run."""
        self.tokens = float(self.capacity)
        self.last_update_time = time.time()
        self.total_packets_emitted = 0
        self.total_sleep_time_sec = 0.0
