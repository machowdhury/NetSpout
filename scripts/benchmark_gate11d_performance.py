#!/usr/bin/env python3
"""
NetSpout Gate 11D Performance & Latency Benchmark.
Evaluates end-to-end telemetry pipeline latency and resource utilization
at 10, 100, 500, and 1000 PPS controlled export rates.
"""

import json
import os
import ssl
import time
import urllib.parse
import urllib.request
from typing import Dict, Any, List

from artifact_isolation import artifact_dir
from netspout_core.models import FlowRecord
from netspout_core.exporter_session import ExporterSession
from netspout_core.collector_evidence import CollectorEvidenceAdapter
from netspout_core.transport_native_flow import NativeFlowTransport


def query_splunk_record(obs_id: int, max_wait: float = 6.0) -> Tuple[bool, float]:
    """Polls Splunk for the observation domain and measures time until searchable."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    auth_header = "Basic YWRtaW46U3BsdW5rUGFzc3dvcmQxMjMh"
    search_url = "https://localhost:8889/services/search/jobs/export"
    query = f"search index=idx_network_ops sourcetype=netflow:collector (ObservationDomainID={obs_id} OR observation_domain_id={obs_id} OR ObservationDomainId={obs_id}) | head 1"
    
    data = urllib.parse.urlencode({
        "search": query,
        "output_mode": "json",
        "earliest_time": "-5m",
        "latest_time": "now"
    }).encode("utf-8")
    
    start_poll = time.time()
    while time.time() - start_poll < max_wait:
        req = urllib.request.Request(search_url, data=data, headers={"Authorization": auth_header})
        try:
            with urllib.request.urlopen(req, timeout=3.0, context=ctx) as resp:
                for line in resp:
                    text = line.decode().strip()
                    if text:
                        d = json.loads(text)
                        if "result" in d:
                            return True, time.time() - start_poll
        except Exception:
            pass
        time.sleep(0.2)
    return False, time.time() - start_poll


def run_benchmark_rate(rate_pps: int, record_count: int = 10) -> Dict[str, Any]:
    print(f"\n>> Benchmarking rate: {rate_pps} PPS (batch size={record_count})...")
    adapter = CollectorEvidenceAdapter()
    adapter.clear_buffer()

    obs_id = 95000 + int(time.time() % 3000) + rate_pps
    session = ExporterSession(
        node_id=f"bench-{rate_pps}",
        exporter_ip="10.200.0.5",
        observation_domain_id=obs_id,
        template_refresh_policy="EVERY_BURST"
    )

    transport = NativeFlowTransport(
        destination_host="127.0.0.1",
        destination_port=4739,
        protocol="IPFIX",
        rate_pps=rate_pps,
        max_packets_per_run=10000,
        test_mode=True
    )

    # 1. Generation Latency
    t0 = time.time()
    records = [
        FlowRecord(
            src_ip="10.100.1.10",
            dest_ip="10.200.1.20",
            src_port=443,
            dest_port=50000 + i,
            protocol=6,
            bytes_count=5000 + i * 100,
            packets_count=50 + i,
            input_snmp=1,
            output_snmp=1
        )
        for i in range(record_count)
    ]
    gen_lat = time.time() - t0

    # 2. Encoding & Send Latency
    t1 = time.time()
    res = transport.send_batch(records, session=session, force_template=True)
    send_lat = time.time() - t1

    # 3. Collector Decode Latency
    t2 = time.time()
    found_flow = None
    while time.time() - t2 < 3.0:
        found_flow = adapter.find_matching_flow(observation_domain_id=obs_id)
        if found_flow:
            break
        time.sleep(0.05)
    collector_lat = time.time() - t2
    collector_observed = found_flow is not None

    # 4. Splunk Indexing Latency
    t3 = time.time()
    splunk_found, splunk_lat = query_splunk_record(obs_id=obs_id, max_wait=6.0)

    total_time = gen_lat + send_lat + collector_lat + splunk_lat

    result = {
        "rate_pps": rate_pps,
        "record_count": record_count,
        "datagrams_sent": res.datagrams_sent,
        "datagrams_attempted": res.datagrams_attempted,
        "generation_latency_sec": round(gen_lat, 5),
        "encoding_and_send_latency_sec": round(send_lat, 5),
        "collector_decode_latency_sec": round(collector_lat, 5),
        "splunk_indexing_latency_sec": round(splunk_lat, 5),
        "total_time_to_validated_evidence_sec": round(total_time, 4),
        "collector_observed": collector_observed,
        "splunk_observed": splunk_found,
        "packet_loss_pct": 0.0 if res.datagrams_sent == res.datagrams_attempted else 100.0 * (1 - res.datagrams_sent / res.datagrams_attempted),
        "decode_errors": 0 if collector_observed else 1
    }
    print(f"   Gen Latency: {result['generation_latency_sec']}s")
    print(f"   Send Latency: {result['encoding_and_send_latency_sec']}s")
    print(f"   Collector Latency: {result['collector_decode_latency_sec']}s")
    print(f"   Splunk Latency: {result['splunk_indexing_latency_sec']}s")
    print(f"   Total Time-to-Evidence: {result['total_time_to_validated_evidence_sec']}s")
    return result


def main():
    print("=" * 65)
    print("⚡ NetSpout Gate 11D Performance & Latency Benchmark Suite")
    print("=" * 65)

    rates = [10, 100, 500, 1000]
    bench_results = []

    for r in rates:
        res = run_benchmark_rate(rate_pps=r, record_count=10)
        bench_results.append(res)
        time.sleep(0.5)

    out_file = artifact_dir("gate11d", "evidence") / "gate11d_performance_benchmark.json"
    with open(out_file, "w") as f:
        json.dump({
            "timestamp": time.time(),
            "environment": "macOS / Docker Localhost Collector",
            "results": bench_results
        }, f, indent=2)

    print("\n" + "=" * 65)
    print(f"🎉 Benchmark Complete. Results written to: {out_file}")
    print("=" * 65)


if __name__ == "__main__":
    main()
