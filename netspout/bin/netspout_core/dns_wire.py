"""Minimal RFC 1035 DNS wire codec and bounded loopback exchange runtime."""

from __future__ import annotations

import ipaddress
import socket
import struct
from dataclasses import dataclass
from typing import Dict, Optional, Tuple


DNS_CLASS_IN = 1
DNS_TYPE_A = 1
DNS_RCODE_NOERROR = 0
DNS_RCODE_NXDOMAIN = 3
MAX_DNS_MESSAGE_BYTES = 512


class DnsWireError(ValueError):
    pass


@dataclass(frozen=True)
class DnsMessage:
    transaction_id: int
    is_response: bool
    qname: str
    qtype: int
    rcode: int
    answer_ip: Optional[str]


@dataclass(frozen=True)
class DnsExchange:
    query_wire: bytes
    response_wire: bytes
    receiver_query: DnsMessage
    client_response: DnsMessage


def encode_name(name: str) -> bytes:
    normalized = name.rstrip(".").lower()
    if not normalized or len(normalized.encode("ascii", "strict")) > 253:
        raise DnsWireError("DNS name must contain 1..253 ASCII octets")
    output = bytearray()
    for label in normalized.split("."):
        encoded = label.encode("ascii", "strict")
        if not encoded or len(encoded) > 63:
            raise DnsWireError("DNS labels must contain 1..63 ASCII octets")
        output.append(len(encoded))
        output.extend(encoded)
    output.append(0)
    return bytes(output)


def decode_name(payload: bytes, offset: int) -> Tuple[str, int]:
    labels = []
    cursor = offset
    next_offset = None
    visited = set()
    while True:
        if cursor >= len(payload):
            raise DnsWireError("truncated DNS name")
        length = payload[cursor]
        if length & 0xC0 == 0xC0:
            if cursor + 1 >= len(payload):
                raise DnsWireError("truncated DNS compression pointer")
            pointer = ((length & 0x3F) << 8) | payload[cursor + 1]
            if pointer >= len(payload) or pointer in visited:
                raise DnsWireError("invalid DNS compression pointer")
            visited.add(pointer)
            if next_offset is None:
                next_offset = cursor + 2
            cursor = pointer
            continue
        if length & 0xC0:
            raise DnsWireError("unsupported DNS label encoding")
        cursor += 1
        if length == 0:
            break
        if length > 63 or cursor + length > len(payload):
            raise DnsWireError("invalid DNS label length")
        try:
            labels.append(payload[cursor : cursor + length].decode("ascii"))
        except UnicodeDecodeError as exc:
            raise DnsWireError("DNS label is not ASCII") from exc
        cursor += length
    return ".".join(labels), next_offset if next_offset is not None else cursor


def build_query(transaction_id: int, qname: str, qtype: int = DNS_TYPE_A) -> bytes:
    if not (0 <= transaction_id <= 0xFFFF):
        raise DnsWireError("transaction ID is outside uint16")
    question = encode_name(qname) + struct.pack("!HH", qtype, DNS_CLASS_IN)
    payload = struct.pack("!HHHHHH", transaction_id, 0x0100, 1, 0, 0, 0) + question
    if len(payload) > MAX_DNS_MESSAGE_BYTES:
        raise DnsWireError("DNS query exceeds the bounded UDP message size")
    return payload


def build_response(
    query: bytes,
    *,
    rcode: int = DNS_RCODE_NOERROR,
    answer_ip: Optional[str] = None,
) -> bytes:
    parsed = parse_message(query)
    if parsed.is_response:
        raise DnsWireError("cannot answer a DNS response")
    if not (0 <= rcode <= 15):
        raise DnsWireError("DNS response code must fit the RFC 1035 header")
    question_end = _question_end(query)
    answer = b""
    answer_count = 0
    if rcode == DNS_RCODE_NOERROR and answer_ip is not None:
        packed_ip = ipaddress.IPv4Address(answer_ip).packed
        answer = b"\xc0\x0c" + struct.pack(
            "!HHIH", DNS_TYPE_A, DNS_CLASS_IN, 60, len(packed_ip)
        ) + packed_ip
        answer_count = 1
    flags = 0x8180 | rcode
    payload = (
        struct.pack("!HHHHHH", parsed.transaction_id, flags, 1, answer_count, 0, 0)
        + query[12:question_end]
        + answer
    )
    if len(payload) > MAX_DNS_MESSAGE_BYTES:
        raise DnsWireError("DNS response exceeds the bounded UDP message size")
    return payload


def parse_message(payload: bytes) -> DnsMessage:
    if len(payload) < 12:
        raise DnsWireError("DNS message is shorter than its header")
    transaction_id, flags, qdcount, ancount, _, _ = struct.unpack(
        "!HHHHHH", payload[:12]
    )
    if qdcount != 1:
        raise DnsWireError("bounded DNS runtime requires exactly one question")
    qname, cursor = decode_name(payload, 12)
    if cursor + 4 > len(payload):
        raise DnsWireError("truncated DNS question")
    qtype, qclass = struct.unpack("!HH", payload[cursor : cursor + 4])
    if qclass != DNS_CLASS_IN:
        raise DnsWireError("bounded DNS runtime supports IN class only")
    cursor += 4
    answer_ip = None
    if ancount:
        _, cursor = decode_name(payload, cursor)
        if cursor + 10 > len(payload):
            raise DnsWireError("truncated DNS answer")
        answer_type, answer_class, _, rdlength = struct.unpack(
            "!HHIH", payload[cursor : cursor + 10]
        )
        cursor += 10
        if cursor + rdlength > len(payload):
            raise DnsWireError("truncated DNS answer data")
        if (
            answer_type == DNS_TYPE_A
            and answer_class == DNS_CLASS_IN
            and rdlength == 4
        ):
            answer_ip = str(ipaddress.IPv4Address(payload[cursor : cursor + 4]))
    return DnsMessage(
        transaction_id=transaction_id,
        is_response=bool(flags & 0x8000),
        qname=qname,
        qtype=qtype,
        rcode=flags & 0x000F,
        answer_ip=answer_ip,
    )


def execute_loopback_exchange(
    *,
    transaction_id: int,
    qname: str,
    qtype: int = DNS_TYPE_A,
    rcode: int = DNS_RCODE_NOERROR,
    answer_ip: Optional[str] = None,
    timeout: float = 1.0,
) -> DnsExchange:
    """Send a real DNS query and response through two ephemeral loopback sockets."""

    query = build_query(transaction_id, qname, qtype)
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        server.bind(("127.0.0.1", 0))
        client.bind(("127.0.0.1", 0))
        server.settimeout(timeout)
        client.settimeout(timeout)
        client.sendto(query, server.getsockname())
        received_query, client_address = server.recvfrom(MAX_DNS_MESSAGE_BYTES)
        receiver_observation = parse_message(received_query)
        response = build_response(
            received_query, rcode=rcode, answer_ip=answer_ip
        )
        server.sendto(response, client_address)
        received_response, _ = client.recvfrom(MAX_DNS_MESSAGE_BYTES)
        client_observation = parse_message(received_response)
        if client_observation.transaction_id != transaction_id:
            raise DnsWireError("DNS response transaction ID does not match")
        return DnsExchange(
            query_wire=query,
            response_wire=response,
            receiver_query=receiver_observation,
            client_response=client_observation,
        )
    finally:
        client.close()
        server.close()


def message_view(message: DnsMessage) -> Dict[str, object]:
    return {
        "transaction_id": message.transaction_id,
        "is_response": message.is_response,
        "query": message.qname,
        "query_type": message.qtype,
        "response_code": message.rcode,
        "answer": message.answer_ip,
    }


def _question_end(payload: bytes) -> int:
    _, cursor = decode_name(payload, 12)
    if cursor + 4 > len(payload):
        raise DnsWireError("truncated DNS question")
    return cursor + 4


__all__ = [
    "DNS_RCODE_NOERROR",
    "DNS_RCODE_NXDOMAIN",
    "DNS_TYPE_A",
    "DnsExchange",
    "DnsMessage",
    "DnsWireError",
    "build_query",
    "build_response",
    "decode_name",
    "encode_name",
    "execute_loopback_exchange",
    "message_view",
    "parse_message",
]
