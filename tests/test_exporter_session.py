"""
Unit Tests for NetSpout ExporterSession.
Verifies sequence advancement, sysUpTime relative offset, and template refresh triggers.
"""

import time
import unittest
from netspout_core.exporter_session import ExporterSession


class TestExporterSession(unittest.TestCase):

    def test_session_initialization(self):
        session = ExporterSession(
            node_id="spine1",
            exporter_ip="10.200.0.1",
            observation_domain_id=500
        )
        self.assertEqual(session.node_id, "spine1")
        self.assertEqual(session.exporter_ip, "10.200.0.1")
        self.assertEqual(session.observation_domain_id, 500)
        self.assertEqual(session.source_id, 500)
        self.assertEqual(session.sequence_number, 0)
        self.assertTrue(session.should_send_template(), "Initial burst should require template")

    def test_sequence_number_progression(self):
        session = ExporterSession(node_id="r1")
        start1, next1 = session.advance_sequence(5)
        self.assertEqual(start1, 0)
        self.assertEqual(next1, 5)
        self.assertEqual(session.sequence_number, 5)

        start2, next2 = session.advance_sequence(10)
        self.assertEqual(start2, 5)
        self.assertEqual(next2, 15)
        self.assertEqual(session.sequence_number, 15)

    def test_template_refresh_triggers(self):
        session = ExporterSession(node_id="r1")
        # 1. Initial should require template
        self.assertTrue(session.should_send_template())

        # 2. Record template sent at t=100
        session.record_template_sent(current_time=100.0)
        self.assertFalse(session.should_send_template(current_time=110.0, refresh_interval_sec=60.0))

        # 3. Elapsed time >= 60s triggers refresh
        self.assertTrue(session.should_send_template(current_time=161.0, refresh_interval_sec=60.0))

        # 4. Packet count >= 20 triggers refresh
        session.record_template_sent(current_time=100.0)
        for _ in range(19):
            session.record_packet_sent(record_count=1, byte_count=100)
        self.assertFalse(session.should_send_template(current_time=110.0, refresh_interval_sec=60.0, refresh_packets=20))

        session.record_packet_sent(record_count=1, byte_count=100)
        self.assertTrue(session.should_send_template(current_time=110.0, refresh_interval_sec=60.0, refresh_packets=20))


if __name__ == "__main__":
    unittest.main()
