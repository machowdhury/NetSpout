"""
Performance Characterization Test for NetSpout Flow Encoding & Transport.
Measures records encoded/sec, packets encoded/sec, and resource usage under safe bounded load.
Conforms to Gate 11B Phase 28.
"""

import os
import resource
import time
import unittest
from netspout_core.models import FlowRecord
from netspout_core.exporter_session import ExporterSession
from netspout_core.netflow_v9_encoder import NetFlowV9Encoder
from netspout_core.ipfix_encoder import IPFIXEncoder


class TestFlowPerformance(unittest.TestCase):

    def test_performance_characterization(self):
        """Measures encoding throughput for both NetFlow v9 and IPFIX under safe load."""
        batch_size = 1000
        records = [
            FlowRecord(
                src_ip=f"10.0.{(i // 254) % 254 + 1}.{i % 254 + 1}",
                dest_ip="10.200.0.1",
                src_port=10000 + (i % 50000),
                dest_port=443,
                protocol=6,
                packets_count=100,
                bytes_count=50000,
                start_time_ms=1000,
                end_time_ms=2000
            )
            for i in range(batch_size)
        ]

        # 1. NetFlow v9 Benchmark
        session_v9 = ExporterSession(node_id="perf1", source_id=1)
        t0 = time.perf_counter()
        packets_v9 = NetFlowV9Encoder.encode_batch(records, session_v9, include_template=True)
        t1 = time.perf_counter()
        dur_v9 = t1 - t0
        rec_sec_v9 = batch_size / dur_v9
        pkt_sec_v9 = len(packets_v9) / dur_v9

        # 2. IPFIX Benchmark
        session_ipfix = ExporterSession(node_id="perf2", observation_domain_id=1)
        t2 = time.perf_counter()
        packets_ipfix = IPFIXEncoder.encode_batch(records, session_ipfix, include_template=True)
        t3 = time.perf_counter()
        dur_ipfix = t3 - t2
        rec_sec_ipfix = batch_size / dur_ipfix
        pkt_sec_ipfix = len(packets_ipfix) / dur_ipfix

        # Measure peak memory
        rusage = resource.getrusage(resource.RUSAGE_SELF)
        # On macOS, maxrss is in bytes; on Linux, in KB
        peak_rss_mb = rusage.ru_maxrss / (1024 * 1024)

        print("\n--- NetSpout Gate 11B Performance Characterization ---")
        print(f"Batch Size:             {batch_size} FlowRecords")
        print(f"NetFlow v9 Encoded:     {len(packets_v9)} datagrams in {dur_v9*1000:.2f} ms")
        print(f"NetFlow v9 Throughput:  {rec_sec_v9:.0f} records/sec ({pkt_sec_v9:.0f} packets/sec)")
        print(f"IPFIX Encoded:          {len(packets_ipfix)} datagrams in {dur_ipfix*1000:.2f} ms")
        print(f"IPFIX Throughput:       {rec_sec_ipfix:.0f} records/sec ({pkt_sec_ipfix:.0f} packets/sec)")
        print(f"Process Peak RSS:       {peak_rss_mb:.2f} MB")
        print("------------------------------------------------------")

        self.assertGreater(rec_sec_v9, 10000, "NetFlow v9 encoding throughput must exceed 10,000 rec/sec")
        self.assertGreater(rec_sec_ipfix, 10000, "IPFIX encoding throughput must exceed 10,000 rec/sec")


if __name__ == "__main__":
    unittest.main()
