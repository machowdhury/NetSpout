"""
Unit Tests for NetSpout Transport Safety Controls and Rate Limiter.
Verifies RFC 1918 safe-by-default destination controls, public IP blocking,
and token-bucket rate limits.
"""

import os
import unittest
from netspout_core.transport_safety import (
    validate_destination_target,
    DestinationSecurityException,
    RateLimitExceededException
)
from netspout_core.rate_limiter import TokenBucketRateLimiter


class TestTransportSafety(unittest.TestCase):

    def test_allow_loopback_destinations(self):
        """Loopback destinations must be allowed by default."""
        ip = validate_destination_target("127.0.0.1", 2055)
        self.assertEqual(ip, "127.0.0.1")

    def test_allow_rfc1918_destinations(self):
        """RFC 1918 private networks must be allowed by default."""
        self.assertEqual(validate_destination_target("10.10.10.10", 2055), "10.10.10.10")
        self.assertEqual(validate_destination_target("172.20.1.5", 4739), "172.20.1.5")
        self.assertEqual(validate_destination_target("192.168.1.100", 9995), "192.168.1.100")

    def test_block_public_destination_by_default(self):
        """Public routable IP destinations must be blocked with DestinationSecurityException."""
        # Ensure env override is unset
        os.environ.pop("NETSPOUT_ALLOW_PUBLIC_EXPORT", None)
        with self.assertRaises(DestinationSecurityException):
            validate_destination_target("8.8.8.8", 2055)
        with self.assertRaises(DestinationSecurityException):
            validate_destination_target("1.1.1.1", 4739)

    def test_public_destination_override_env(self):
        """Public IP allowed only when explicit environment override is set."""
        try:
            os.environ["NETSPOUT_ALLOW_PUBLIC_EXPORT"] = "true"
            ip = validate_destination_target("8.8.8.8", 2055)
            self.assertEqual(ip, "8.8.8.8")
        finally:
            os.environ.pop("NETSPOUT_ALLOW_PUBLIC_EXPORT", None)

    def test_block_privileged_ports(self):
        """Privileged ports < 1024 (except 514) must be blocked without explicit flag."""
        with self.assertRaises(DestinationSecurityException):
            validate_destination_target("127.0.0.1", 80)
        # Port 514 (syslog) is permitted
        self.assertEqual(validate_destination_target("127.0.0.1", 514), "127.0.0.1")
        # Allowed with explicit authorization
        self.assertEqual(
            validate_destination_target("127.0.0.1", 80, allow_privileged_ports=True),
            "127.0.0.1"
        )

    def test_invalid_port_range(self):
        """Ports outside 1..65535 must be rejected."""
        with self.assertRaises(DestinationSecurityException):
            validate_destination_target("127.0.0.1", 0)
        with self.assertRaises(DestinationSecurityException):
            validate_destination_target("127.0.0.1", 70000)

    def test_rate_limiter_run_ceiling(self):
        """Rate limiter must enforce max packets per run ceiling."""
        limiter = TokenBucketRateLimiter(rate_pps=500, max_packets_per_run=10)
        # First 10 packets should succeed in test mode
        limiter.acquire(10, test_mode=True)
        # 11th packet must raise RateLimitExceededException
        with self.assertRaises(RateLimitExceededException):
            limiter.acquire(1, test_mode=True)


if __name__ == "__main__":
    unittest.main()
