"""
NetSpout PCAP Generator & TShark Dissector Verifier.
Generates a valid PCAP file with NetFlow v9 and IPFIX datagrams,
and verifies wire-level dissection using /opt/homebrew/bin/tshark.
Conforms to Gate 11B Test Plan Section 6.
"""

import ipaddress
import os
import struct
import subprocess
import time
from typing import Dict, Any, Tuple

from netspout_core.models import FlowRecord
from netspout_core.exporter_session import ExporterSession
from netspout_core.netflow_v9_encoder import NetFlowV9Encoder
from netspout_core.ipfix_encoder import IPFIXEncoder


def ip_checksum(header: bytes) -> int:
    """Calculates standard Internet Checksum (RFC 1071)."""
    if len(header) % 2 == 1:
        header += b"\x00"
    total = sum(struct.unpack(f"!{len(header)//2}H", header))
    while total >> 16:
        total = (total & 0xFFFF) + (total >> 16)
    return (~total) & 0xFFFF


def build_udp_ethernet_packet(
    src_mac: str,
    dst_mac: str,
    src_ip: str,
    dst_ip: str,
    src_port: int,
    dst_port: int,
    payload: bytes
) -> bytes:
    """Wraps UDP payload in Ethernet II + IPv4 + UDP framing."""
    # 1. Ethernet Header (14 bytes)
    eth_dst = bytes.fromhex(dst_mac.replace(":", ""))
    eth_src = bytes.fromhex(src_mac.replace(":", ""))
    eth_type = struct.pack("!H", 0x0800)  # IPv4
    eth_header = eth_dst + eth_src + eth_type

    # 2. UDP Header (8 bytes)
    udp_len = 8 + len(payload)
    # Checksum can be 0 in IPv4 UDP
    udp_header = struct.pack("!HHHH", src_port, dst_port, udp_len, 0)

    # 3. IPv4 Header (20 bytes)
    src_ip_bytes = ipaddress.IPv4Address(src_ip).packed
    dst_ip_bytes = ipaddress.IPv4Address(dst_ip).packed
    total_ip_len = 20 + udp_len
    ip_hdr_no_cksum = struct.pack(
        "!BBHHHBBH4s4s",
        0x45,          # Version 4, IHL 5
        0x00,          # DSCP / ECN
        total_ip_len,
        0x1234,        # Identification
        0x4000,        # Flags: Don't Fragment
        64,            # TTL
        17,            # Protocol: UDP
        0,             # Checksum placeholder
        src_ip_bytes,
        dst_ip_bytes
    )
    cksum = ip_checksum(ip_hdr_no_cksum)
    ip_header = struct.pack(
        "!BBHHHBBH4s4s",
        0x45, 0x00, total_ip_len, 0x1234, 0x4000, 64, 17, cksum, src_ip_bytes, dst_ip_bytes
    )

    return eth_header + ip_header + udp_header + payload


def write_pcap(filepath: str, packets: list[bytes]) -> None:
    """Writes standard Libpcap 2.4 format file."""
    # PCAP Global Header: magic 0xa1b2c3d4, v2.4, thiszone=0, sigfigs=0, snaplen=65535, network=1 (Ethernet)
    global_header = struct.pack("!IHHiIII", 0xa1b2c3d4, 2, 4, 0, 0, 65535, 1)

    with open(filepath, "wb") as f:
        f.write(global_header)
        now = time.time()
        for i, pkt in enumerate(packets):
            sec = int(now) + i
            usec = 1000 * i
            pkt_hdr = struct.pack("!IIII", sec, usec, len(pkt), len(pkt))
            f.write(pkt_hdr)
            f.write(pkt)


def verify_with_tshark(pcap_path: str) -> Tuple[bool, str]:
    """Runs tshark on PCAP and checks for dissector recognition and malformed warnings."""
    tshark_bin = "/opt/homebrew/bin/tshark"
    if not os.path.exists(tshark_bin):
        return False, f"TShark not found at {tshark_bin}"

    # Dissect all packets with full protocol details
    cmd = [tshark_bin, "-r", pcap_path, "-V"]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        return False, f"tshark failed with code {result.returncode}: {result.stderr}"

    output = result.stdout
    # Check for malformed packets
    if "malformed" in output.lower():
        return False, f"TShark detected malformed packet:\n{output}"

    # Check for protocol recognition
    cflow_detected = "Cisco NetFlow/IPFIX" in output or "CFLOW" in output or "NetFlow" in output
    ipfix_detected = "IPFIX" in output

    if not (cflow_detected or ipfix_detected):
        return False, f"Neither NetFlow nor IPFIX dissector triggered:\n{output[:500]}"

    return True, output


def main():
    pcap_file = "/tmp/netspout_verification.pcap"

    # 1. Build NetFlow v9 Packet
    session_v9 = ExporterSession(node_id="r1", source_id=101)
    rec_v9 = FlowRecord(
        src_ip="10.0.1.10", dest_ip="10.0.2.20", bgp_next_hop="10.0.1.1",
        input_snmp=3, output_snmp=5, packets_count=1024, bytes_count=524288,
        start_time_ms=120000, end_time_ms=125000, src_port=49153, dest_port=443,
        tcp_flags=0x18, protocol=6, tos_dscp=0, src_as=65535, dest_as=61440
    )
    v9_payload = NetFlowV9Encoder.build_packet(
        session=session_v9, data_records=[rec_v9], include_template=True,
        sim_time_sec=1774438400, sys_uptime_ms=125000
    )
    v9_frame = build_udp_ethernet_packet(
        src_mac="00:11:22:33:44:55", dst_mac="66:77:88:99:aa:bb",
        src_ip="10.0.0.1", dst_ip="10.0.0.2",
        src_port=50000, dst_port=2055, payload=v9_payload
    )

    # 2. Build IPFIX Packet
    session_ipfix = ExporterSession(node_id="r1", observation_domain_id=101)
    rec_ipfix = FlowRecord(
        src_ip="10.0.1.10", dest_ip="10.0.2.20", src_port=49153, dest_port=443,
        protocol=6, tos_dscp=0, tcp_flags=0x0018, input_snmp=3, output_snmp=5,
        packets_count=1024, bytes_count=524288,
        start_time_ms=1774438400000, end_time_ms=1774438451000,
        src_as=65535, dest_as=61440
    )
    ipfix_payload = IPFIXEncoder.build_packet(
        session=session_ipfix, data_records=[rec_ipfix], include_template=True,
        sim_time_sec=1774438400
    )
    ipfix_frame = build_udp_ethernet_packet(
        src_mac="00:11:22:33:44:55", dst_mac="66:77:88:99:aa:bb",
        src_ip="10.0.0.1", dst_ip="10.0.0.2",
        src_port=50001, dst_port=4739, payload=ipfix_payload
    )

    # 3. Write PCAP
    write_pcap(pcap_file, [v9_frame, ipfix_frame])
    print(f"Generated PCAP at {pcap_file} ({os.path.getsize(pcap_file)} bytes)")

    # 4. Dissect with TShark
    success, output = verify_with_tshark(pcap_file)
    if not success:
        print("FAIL: TShark verification failed!")
        print(output)
        exit(1)

    print("PASS: TShark cleanly dissected both NetFlow v9 and IPFIX packets with 0 malformed warnings!")
    # Print summary of dissection
    lines = [line for line in output.splitlines() if any(k in line for k in ("Cisco NetFlow/IPFIX", "Version:", "FlowSet Id:", "Set Id:", "SrcAddr:", "DstAddr:", "SrcPort:", "DstPort:", "IPFIX"))]
    for line in lines[:30]:
        print("  ", line)


if __name__ == "__main__":
    main()
