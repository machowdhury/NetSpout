"""
NetSpout Gate 11 Golden Binary Flow Fixtures.
Authoritative known-good byte fixtures conforming to RFC 3954 and RFC 7011/7012.
"""

# NetFlow v9 Golden Hex Fixture (140 bytes total)
# 20-byte header + 72-byte Template FlowSet + 48-byte Data FlowSet
GOLDEN_HEX_NETFLOW_V9 = (
    "000900020001e84869c3c8000000000100000065"  # Header (20 bytes)
    "0000004801000010"                          # Template FlowSet Header (ID 0, Len 72, Tmpl 256, 16 fields)
    "00080004000c000400120004000a0002000e0002"  # Fields 1-5 (src_ip, dst_ip, nexthop, in_if, out_if)
    "0002000400010004001600040015000400070002"  # Fields 6-10 (pkts, bytes, first_sw, last_sw, src_port)
    "000b000200060001000400010005000100100002"  # Fields 11-15 (dst_port, tcp_flags, proto, tos, src_as)
    "00110002"                                  # Field 16 (dst_as)
    "01000030"                                  # Data FlowSet Header (ID 256, Len 48)
    "0a00010a0a0002140a00010100030005"          # 10.0.1.10 -> 10.0.2.20 via 10.0.1.1, ifIn=3, ifOut=5
    "0000040000080000"                          # pkts=1024, bytes=524288
    "0001d4c00001e848"                          # first_sw=120000ms, last_sw=125000ms
    "c00101bb180600"                            # src_p=49153, dst_p=443, tcp_flags=0x18, proto=6, tos=0
    "fffff000"                                  # src_as=65535, dst_as=61440
    "00"                                        # 1 padding byte to 4-byte boundary
)

GOLDEN_BYTES_NETFLOW_V9 = bytes.fromhex(GOLDEN_HEX_NETFLOW_V9)

# IPFIX Golden Hex Fixture (152 bytes total)
# 16-byte header + 68-byte Template Set + 68-byte Data Set
GOLDEN_HEX_IPFIX = (
    "000a009869c3c8000000000100000065"          # Header (16 bytes, version 10, len 152, seq 1, domain 101)
    "000200440100000f"                          # Template Set Header (Set 2, Len 68, Tmpl 256, 15 fields)
    "00080004000c000400070002000b000200040001"  # Fields 1-5 (src_ip, dst_ip, src_p, dst_p, proto)
    "0005000100060002000a0004000e000400020008"  # Fields 6-10 (tos, tcp_flags(2B), in_if, out_if, pkts(8B))
    "0001000800980008009900080010000400110004"  # Fields 11-15 (bytes(8B), start_ms(8B), end_ms(8B), src_as, dst_as)
    "01000044"                                  # Data Set Header (Set 256, Len 68)
    "0a00010a0a000214c00101bb06000018"          # src=10.0.1.10, dst=10.0.2.20, sp=49153, dp=443, proto=6, tos=0, flags=0x0018
    "0000000300000005"                          # ifIn=3, ifOut=5
    "0000000000000400"                          # pkts=1024 (uint64)
    "0000000000080000"                          # bytes=524288 (uint64)
    "0000019d24c54000"                          # flowStartMilliseconds = 1774438400000 ms
    "0000019d24c60738"                          # flowEndMilliseconds = 1774438451000 ms
    "0000ffff"                                  # src_as = 65535
    "0000f000"                                  # dst_as = 61440
)

GOLDEN_BYTES_IPFIX = bytes.fromhex(GOLDEN_HEX_IPFIX)
