"""NetFlow/IPFIX solution pack: ten deterministic flow-pattern scenarios (5 network operations, 5 security) over the existing flow pipeline.

Pipeline reuse (nothing here re-implements wire encoding or collection):
  FlowRecord -> IPFIXEncoder/UDP (transport_native_flow) -> GoFlow2 -> repo forwarder   = the WIRE path, already verified;
  FlowRecord -> normalize() -> NDJSON event -> HEC                                       = the NORMALIZED path added here, counted by the run monitor.
The two paths are reported separately. UDP-exported records are never counted as HEC-accepted.

Honesty rules baked into the data model:
  * direction counters (bytes_in/out, packets_in/out) are None: a NetFlow/IPFIX record from this template is unidirectional, so they are not fabricated.
    Dashboards pair forward and reverse flows with SPL where a use case needs direction.
  * flow_end_reason is None: the IPFIX template used by the encoder does not carry flowEndReason (IE 136).
  * `app` is a port heuristic, flagged by app_basis; it is not application identification.
  * label_meta is synthetic scenario truth, kept apart from observed fields. It is not exporter data.
  * addresses come from RFC 5737 documentation ranges only.
"""
import ipaddress
import random
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from netspout_core.models import FlowRecord

SOLUTION_VERSION = "1.0"
SOURCE = "netspout:netflow:normalized"
DEFAULT_SOURCETYPE = "netflow:collector"          # canonical decoded-flow sourcetype (forwarder + SEC-P9); cisco:ios:ipfix is NOT in the catalog
REQUESTED_SOURCETYPE = "cisco:ios:ipfix"
INTERNAL_NETS = ("192.0.2.0/24", "198.51.100.0/24")   # RFC 5737 TEST-NET-1 / TEST-NET-2: servers / clients
EXTERNAL_NET = "203.0.113.0/24"                        # TEST-NET-3: synthetic "internet"
EXPORTERS = {"core": "192.0.2.1", "edge": "192.0.2.2"}
PROTO_NAME = {1: "icmp", 6: "tcp", 17: "udp"}
# Port-to-application names are a convenience label only (app_basis=port_heuristic).
PORT_APP = {22: "ssh", 53: "dns", 80: "http", 123: "ntp", 443: "https", 445: "smb", 873: "rsync", 3306: "mysql", 3389: "rdp", 5060: "sip", 5004: "rtp-video", 8443: "https-alt"}
TCP_BITS = [(1, "FIN"), (2, "SYN"), (4, "RST"), (8, "PSH"), (16, "ACK"), (32, "URG")]
SYN, ACK, SYN_ACK, PSH_ACK, FIN_ACK = 2, 16, 18, 24, 17
EF, AF41, CS0 = 46, 34, 0

CATALOG: List[Dict[str, Any]] = [
    {"scenario_id": "NF-NOC-01-ELEPHANT", "code": "NOC-01", "kind": "operational", "title": "NetFlow: bandwidth saturation and elephant flows",
     "question": "Which few flows carry most of the bytes, who sends them, and how long do they last?", "extends": None, "mitre": [],
     "limits": "Utilization is shown only when you enter a link capacity; NetFlow carries no interface speed.",
     "params": {"elephants": 4, "elephant_gb": 3.0}},
    {"scenario_id": "NF-NOC-02-DSCP", "code": "NOC-02", "kind": "operational", "title": "NetFlow: QoS and DSCP marking validation",
     "question": "Is voice and video traffic marked with the DSCP the policy expects, and which endpoints are not?", "extends": None, "mitre": [],
     "limits": "Voice/video class comes from UDP port ranges (a heuristic); the policy (EF=46 voice, AF41=34 video) is the lab default, not discovered.",
     "params": {"noncompliant_pct": 25}},
    {"scenario_id": "NF-NOC-03-ROUTING-LOOP", "code": "NOC-03", "kind": "operational", "title": "NetFlow: routing-loop indicators (flow-only)",
     "question": "Are the same source/destination pairs being observed repeatedly across exporters and interfaces in a pattern a forwarding loop would produce?", "extends": None, "mitre": [],
     "limits": "Indicator only. NetFlow has no TTL, so TTL depletion and loop drops cannot be shown; ICMP time-exceeded or router counters would be needed to confirm.",
     "params": {"looping_pairs": 3}},
    {"scenario_id": "NF-NOC-04-ASYMMETRY", "code": "NOC-04", "kind": "operational", "title": "NetFlow: asymmetric-routing indicators",
     "question": "For which endpoint pairs is the reverse direction seen at a different exporter, or not seen at all?", "extends": None, "mitre": [],
     "limits": "A missing reverse flow is not proof of asymmetry: sampling, observation coverage and collection gaps look the same. Pairs are classified as indicators.",
     "params": {"pairs": 60}},
    {"scenario_id": "NF-NOC-05-BASELINE-DRIFT", "code": "NOC-05", "kind": "operational", "title": "NetFlow: application baseline and duration drift",
     "question": "Did flow duration or volume to a destination drift away from its earlier baseline?", "extends": None, "mitre": [],
     "limits": "Flow duration is not application latency; it also depends on session length and exporter timeouts.",
     "params": {"drift_factor": 3.0}},
    {"scenario_id": "NF-SEC-06-DDOS", "code": "SEC-06", "kind": "security", "title": "NetFlow: volumetric DDoS indicators (SYN flood and UDP)",
     "question": "Where is the packet rate peaking, which protocols and TCP flags dominate, and which assets are targeted?", "extends": "SEC-P9-A-TRAFFIC-FLOOD", "mitre": ["T1498.001"],
     "limits": "Synthetic flood patterns. Flow export may be sampled in production and cannot prove loss of availability.",
     "params": {"syn_sources": 180}},
    {"scenario_id": "NF-SEC-07-PORTSCAN", "code": "SEC-07", "kind": "security", "title": "NetFlow: network reconnaissance and port scanning",
     "question": "Which hosts touch many ports or many destinations with tiny flows, and how does the footprint grow?", "extends": "SEC-P9-D-INTERNAL-RECON", "mitre": ["T1046"],
     "limits": "Connection attempts do not prove access. Approved vulnerability scanners produce the same pattern.",
     "params": {"scan_hosts": 60, "scan_ports": 40}},
    {"scenario_id": "NF-SEC-08-EXFIL", "code": "SEC-08", "kind": "security", "title": "NetFlow: outbound data-exfiltration indicators",
     "question": "Which internal host sends unusual byte volume to external destinations, and over what ports and times?", "extends": None, "mitre": ["T1048"],
     "limits": "Volume alone does not establish data theft. Backups, updates and uploads look identical in flow data.",
     "params": {"exfil_mb": 900}},
    {"scenario_id": "NF-SEC-09-BEACON", "code": "SEC-09", "kind": "security", "title": "NetFlow: command-and-control beaconing indicators",
     "question": "Which source/destination pairs reconnect on a regular interval, and how regular is it?", "extends": "SEC-P9-C-BEACONING", "mitre": ["T1071"],
     "limits": "Periodicity is a weak indicator on its own: agents, monitoring and update checks beacon too. Encrypted payloads are not visible.",
     "params": {"interval_s": 20, "jitter_pct": 10}},
    {"scenario_id": "NF-SEC-10-DNS-FLOW", "code": "SEC-10", "kind": "security", "title": "NetFlow: DNS-tunneling indicators (flow-only, limited evidence)",
     "question": "Which clients send unusually many or unusually large DNS flows, and is request/response volume imbalanced?", "extends": "SEC-P9-E-DNS-TUNNEL", "mitre": ["T1071.004", "T1048.003"],
     "limits": "Limited evidence: flow data has no query names, lengths or entropy, so encoded labels cannot be detected here. Correlate with DNS logs for that.",
     "params": {"tunnel_clients": 1}},
]
IDS = [c["scenario_id"] for c in CATALOG]


def catalog() -> List[Dict[str, Any]]:
    return [dict(c) for c in CATALOG]


def get(scenario_id: str) -> Dict[str, Any]:
    for c in CATALOG:
        if c["scenario_id"] == scenario_id:
            return c
    raise ValueError("Unknown NetFlow scenario: " + str(scenario_id))


def is_internal(ip: str) -> bool:
    a = ipaddress.ip_address(ip)
    return any(a in ipaddress.ip_network(n) for n in INTERNAL_NETS)


# ----------------------------------------------------------------------------------------------------------------- generation
class _G:
    """Small deterministic builder: every call is seeded, every flow lands inside [t0, t1]."""
    def __init__(self, seed: int, t0_ms: int, t1_ms: int, scenario_id: str):
        self.r, self.t0, self.t1, self.sid = random.Random(seed), t0_ms, t1_ms, scenario_id
        self.rows: List[Dict[str, Any]] = []
        self.span = max(1000, t1_ms - t0_ms)

    def at(self, frac_lo=0.0, frac_hi=1.0) -> int:
        return int(self.t0 + self.span * (frac_lo + self.r.random() * (frac_hi - frac_lo)))

    def add(self, src, dst, sport, dport, proto, flags, tos, nbytes, npkts, start, dur_ms, exporter="core", sin=1, sout=2, phase="traffic", malicious=False, technique=None, role=None, note=None):
        dur_ms = max(0, int(dur_ms))
        if start + dur_ms > self.t1:        # slide the flow earlier instead of clipping its end: clipping would pile many flow ends onto the last instant
            start = max(self.t0, self.t1 - dur_ms)
        end = min(self.t1, start + dur_ms)
        start = min(start, end)
        rec = FlowRecord(src_ip=src, dest_ip=dst, src_port=sport, dest_port=dport, protocol=proto, tcp_flags=flags, tos_dscp=tos, src_as=64500 if is_internal(src) else 64510,
                         dest_as=64500 if is_internal(dst) else 64510, input_snmp=sin, output_snmp=sout, bytes_count=int(nbytes), packets_count=max(1, int(npkts)),
                         start_time_ms=int(start), end_time_ms=int(end), netspout_scenario_id=self.sid, netspout_phase=phase, anomaly_type="malicious" if malicious else "normal")
        self.rows.append({"record": rec, "exporter_ip": EXPORTERS[exporter], "phase": phase,
                          "label_meta": {"scenario_id": self.sid, "is_malicious": bool(malicious), "threat_technique": technique, "role": role, "note": note}})
        return rec

    def client(self, n=60):
        return "198.51.100.%d" % (10 + self.r.randrange(n))

    def server(self, n=20):
        return "192.0.2.%d" % (10 + self.r.randrange(n))


def _background(g: _G, n: int, services=((443, 6, 0.7), (80, 6, 0.1), (53, 17, 0.2)), tos=0, **kw):
    """Ordinary client-to-server traffic used as the comparison population in every scenario."""
    for _ in range(n):
        p = g.r.random()
        acc = 0.0
        for port, proto, w in services:
            acc += w
            if p <= acc:
                break
        small = proto == 17
        g.add(g.client(), g.server(), 32768 + g.r.randrange(28000), port, proto, 0 if small else PSH_ACK, tos, g.r.randint(90, 240) if small else g.r.randint(2000, 90000),
              g.r.randint(1, 3) if small else g.r.randint(8, 80), g.at(), g.r.randint(20, 400) if small else g.r.randint(200, 9000), exporter=g.r.choice(["core", "edge"]), **kw)


def _gen_elephant(g: _G, scale: float, p: Dict[str, Any]):
    _background(g, int(220 * scale))
    n = max(1, int(p.get("elephants", 4)))
    for i in range(n):
        gb = float(p.get("elephant_gb", 3.0)) * (0.7 + 0.6 * g.r.random())
        start = g.at(0.05, 0.4)
        dur = int(g.span * (0.35 + 0.4 * g.r.random()))
        nb = int(gb * 1e9)
        g.add("192.0.2.%d" % (50 + i), "192.0.2.%d" % (200 + i % 3), 40000 + i, 873, 6, PSH_ACK, 0, nb, nb // 1448, start, dur, phase="elephant", role="backup-replication",
              note="large scheduled transfer; not malicious")


def _gen_dscp(g: _G, scale: float, p: Dict[str, Any]):
    _background(g, int(80 * scale))
    bad_pct = max(0, min(100, int(p.get("noncompliant_pct", 25)))) / 100.0
    endpoints = ["198.51.100.%d" % (120 + i) for i in range(12)]
    bad = set(endpoints[:max(1, round(len(endpoints) * bad_pct * 1.6))]) if bad_pct else set()     # noncompliance concentrates on a few endpoints
    for _ in range(int(260 * scale)):
        ep = g.r.choice(endpoints)
        voice = g.r.random() < 0.6
        t = g.at()
        marked_wrong = ep in bad and g.r.random() < 0.9
        want = EF if voice else AF41
        dscp = CS0 if marked_wrong else want
        port = (16384 + g.r.randrange(16000)) if voice else 5004
        pk = g.r.randint(40, 120)
        g.add(ep, "192.0.2.%d" % (90 + g.r.randrange(3)), 20000 + g.r.randrange(10000), port, 17, 0, dscp << 2, pk * (172 if voice else 900), pk, t, g.r.randint(800, 6000),
              exporter=g.r.choice(["core", "edge"]), sin=3, sout=4, phase="voice-video", role="voice" if voice else "video", note="marked DSCP %d, policy expects %d" % (dscp, want))


def _gen_loop(g: _G, scale: float, p: Dict[str, Any]):
    _background(g, int(160 * scale))
    pairs = [("198.51.100.%d" % (100 + i), "192.0.2.%d" % (130 + i)) for i in range(max(1, int(p.get("looping_pairs", 3))))]
    for i, (s, d) in enumerate(pairs):
        reps = int(40 * scale)
        for k in range(reps):                        # same pair, both exporters, ingress/egress interfaces swapping, tiny packet counts, growing over time
            t = g.at(0.25 + 0.6 * k / reps, 0.30 + 0.65 * k / reps)
            ex = "core" if k % 2 == 0 else "edge"
            g.add(s, d, 41000 + i, 443, 6, ACK, 0, g.r.randint(40, 160), g.r.randint(1, 3), t, g.r.randint(5, 60), exporter=ex, sin=1 if ex == "core" else 2, sout=2 if ex == "core" else 1,
                  phase="repeat-observation", role="loop-candidate", note="same pair seen alternately at core and edge with swapped interfaces")


def _gen_asym(g: _G, scale: float, p: Dict[str, Any]):
    n = max(6, int(p.get("pairs", 60) * scale))
    for i in range(n):
        c, s = "198.51.100.%d" % (20 + i % 200), "192.0.2.%d" % (10 + i % 40)
        sport = 30000 + i
        t = g.at(0.0, 0.85)
        dur = g.r.randint(300, 5000)
        fwd_b, rev_b = g.r.randint(4000, 30000), g.r.randint(40000, 400000)
        g.add(c, s, sport, 443, 6, PSH_ACK, 0, fwd_b, fwd_b // 900 + 1, t, dur, exporter="core", sin=1, sout=2, phase="paired", role="forward")
        bucket = i % 10
        if bucket < 7:      # reverse seen at the same exporter
            g.add(s, c, 443, sport, 6, PSH_ACK, 0, rev_b, rev_b // 1200 + 1, t, dur, exporter="core", sin=2, sout=1, phase="paired", role="reverse", note="symmetric: reverse at same exporter")
        elif bucket < 9:    # reverse seen at a different exporter
            g.add(s, c, 443, sport, 6, PSH_ACK, 0, rev_b, rev_b // 1200 + 1, t, dur, exporter="edge", sin=7, sout=8, phase="reverse-elsewhere", role="reverse",
                  note="reverse path observed at the edge exporter, not the core exporter: path-asymmetry indicator")
        # bucket 9: reverse not observed at all (asymmetric path, sampling, or coverage gap: not distinguishable from flow data)


def _gen_drift(g: _G, scale: float, p: Dict[str, Any]):
    factor = float(p.get("drift_factor", 3.0))
    dests = ["192.0.2.80", "192.0.2.81", "192.0.2.82"]
    for _ in range(int(420 * scale)):
        f = g.r.random()
        d = g.r.choice(dests)
        drift = d == "192.0.2.80" and f > 0.55
        base_dur = g.r.randint(300, 900)
        base_b = g.r.randint(8000, 24000)
        g.add(g.client(), d, 33000 + g.r.randrange(20000), 443, 6, PSH_ACK, 0, int(base_b * (1.8 if drift else 1.0)), g.r.randint(10, 40),
              int(g.t0 + g.span * f), int(base_dur * (factor if drift else 1.0)), exporter="core", phase="drift" if drift else "baseline", role="web-app",
              note="duration/volume scaled x%.1f from the baseline period" % factor if drift else None)


def _gen_ddos(g: _G, scale: float, p: Dict[str, Any]):
    _background(g, int(100 * scale))
    target, udp_target = "192.0.2.80", "192.0.2.53"
    for _ in range(int(560 * scale)):
        f = g.r.random() ** 0.6                       # density rises toward the end of the window: attack progression
        s = "203.0.113.%d" % (1 + g.r.randrange(max(2, int(p.get("syn_sources", 180)))) % 250)
        g.add(s, target, 1024 + g.r.randrange(60000), 443, 6, SYN, 0, g.r.choice([40, 44, 60]), 1, int(g.t0 + g.span * (0.2 + 0.78 * f)), g.r.randint(0, 20), phase="syn-flood",
              malicious=True, technique="T1498.001", role="syn-flood", exporter="edge", sin=5, sout=6)
    for _ in range(int(160 * scale)):
        f = g.r.random() ** 0.7
        g.add("203.0.113.%d" % (1 + g.r.randrange(250)), udp_target, 1024 + g.r.randrange(60000), 53 if g.r.random() < 0.5 else 11211, 17, 0, 0, 1400 * g.r.randint(1, 3), g.r.randint(1, 3),
              int(g.t0 + g.span * (0.35 + 0.63 * f)), g.r.randint(0, 40), phase="udp-flood", malicious=True, technique="T1498.001", role="udp-volumetric", exporter="edge", sin=5, sout=6)


def _gen_scan(g: _G, scale: float, p: Dict[str, Any]):
    _background(g, int(150 * scale))
    scanner = "198.51.100.77"
    hosts = int(p.get("scan_hosts", 60) * scale)
    for i in range(hosts):         # horizontal: a few ports across many hosts, growing over time
        port = g.r.choice([22, 445, 3389])
        g.add(scanner, "192.0.2.%d" % (10 + i % 240), 50000 + g.r.randrange(10000), port, 6, SYN, 0, 44, 1, int(g.t0 + g.span * (0.2 + 0.4 * i / max(1, hosts))), g.r.randint(0, 5),
              phase="horizontal-scan", malicious=True, technique="T1046", role="scanner", exporter="core")
    for i in range(int(p.get("scan_ports", 40) * scale)):       # vertical: many ports on one host
        g.add(scanner, "192.0.2.25", 50000 + g.r.randrange(10000), 1 + i * 37 % 10000, 6, SYN, 0, 44, 1, int(g.t0 + g.span * (0.6 + 0.35 * i / max(1, p.get("scan_ports", 40)))), g.r.randint(0, 5),
              phase="vertical-scan", malicious=True, technique="T1046", role="scanner", exporter="core")
    for i in range(int(12 * scale)):   # a benign monitoring host touches several hosts on one port: contrast
        g.add("198.51.100.5", "192.0.2.%d" % (10 + i), 51000 + i, 443, 6, PSH_ACK, 0, 4200, 12, g.at(), 400, phase="traffic", role="monitor", note="approved health checks")


def _gen_exfil(g: _G, scale: float, p: Dict[str, Any]):
    _background(g, int(140 * scale))
    for _ in range(int(60 * scale)):          # normal outbound browsing from many clients
        g.add(g.client(), "203.0.113.%d" % (100 + g.r.randrange(30)), 40000 + g.r.randrange(20000), 443, 6, PSH_ACK, 0, g.r.randint(2000, 90000), g.r.randint(10, 80), g.at(), g.r.randint(200, 4000),
              exporter="edge", sin=5, sout=6)
    total = int(float(p.get("exfil_mb", 900)) * 1e6 * scale)
    chunks = max(3, int(12 * scale))
    for k in range(chunks):
        port = 443 if k % 4 else 22
        g.add("192.0.2.120", "203.0.113.50", 44000 + k, port, 6, PSH_ACK, 0, total // chunks, (total // chunks) // 1448, int(g.t0 + g.span * (0.45 + 0.5 * k / chunks)), int(g.span * 0.08),
              phase="outbound-transfer", malicious=True, technique="T1048", role="exfil-candidate", exporter="edge", sin=5, sout=6, note="large outbound transfer to one external host")


def _gen_beacon(g: _G, scale: float, p: Dict[str, Any]):
    _background(g, int(100 * scale))
    interval = max(2.0, float(p.get("interval_s", 20)))
    jitter = max(0.0, float(p.get("jitter_pct", 10))) / 100.0
    t = g.t0 + 3000
    k = 0
    while t < g.t1 - 2000:
        g.add("198.51.100.140", "203.0.113.66", 45000 + k % 3000, 443, 6, PSH_ACK, 0, g.r.randint(280, 520), g.r.randint(4, 8), int(t), g.r.randint(60, 300), phase="beacon", malicious=True,
              technique="T1071", role="periodic-contact", exporter="edge", sin=5, sout=6)
        t += interval * 1000 * (1 + g.r.uniform(-jitter, jitter))
        k += 1
    for i in range(max(3, int(8 * scale))):        # irregular small-flow hosts for contrast (random gaps)
        for _ in range(int(14 * scale)):
            g.add("198.51.100.%d" % (150 + i), "203.0.113.%d" % (10 + i), 46000 + g.r.randrange(5000), 443, 6, PSH_ACK, 0, g.r.randint(280, 900), g.r.randint(4, 12), g.at(), g.r.randint(60, 600),
                  exporter="edge", sin=5, sout=6, role="irregular-client")


def _gen_dns(g: _G, scale: float, p: Dict[str, Any]):
    resolver = "192.0.2.53"

    def query(client, req_b, resp_b, t, phase="dns", malicious=False):
        sport = 30000 + g.r.randrange(30000)
        g.add(client, resolver, sport, 53, 17, 0, 0, req_b, max(1, req_b // 90), t, 20, exporter="core", sin=3, sout=4, phase=phase, malicious=malicious,
              technique="T1071.004" if malicious else None, role="dns-request")
        g.add(resolver, client, 53, sport, 17, 0, 0, resp_b, max(1, resp_b // 150), t + 20, 20, exporter="core", sin=4, sout=3, phase=phase, malicious=malicious,
              technique="T1071.004" if malicious else None, role="dns-response")
    for _ in range(int(220 * scale)):
        query(g.client(30), g.r.randint(60, 90), g.r.randint(90, 220), g.at())
    for c in range(max(1, int(p.get("tunnel_clients", 1)))):
        for k in range(int(140 * scale)):
            query("198.51.100.%d" % (200 + c), g.r.randint(200, 380), g.r.randint(500, 1000), g.at(0.15, 0.98), phase="dns-heavy", malicious=True)


GENERATORS = {"NF-NOC-01-ELEPHANT": _gen_elephant, "NF-NOC-02-DSCP": _gen_dscp, "NF-NOC-03-ROUTING-LOOP": _gen_loop, "NF-NOC-04-ASYMMETRY": _gen_asym,
              "NF-NOC-05-BASELINE-DRIFT": _gen_drift, "NF-SEC-06-DDOS": _gen_ddos, "NF-SEC-07-PORTSCAN": _gen_scan, "NF-SEC-08-EXFIL": _gen_exfil,
              "NF-SEC-09-BEACON": _gen_beacon, "NF-SEC-10-DNS-FLOW": _gen_dns}


def generate(scenario_id: str, run_id: str, seed: int = 42, duration_s: int = 180, scale: float = 1.0, params: Optional[Dict[str, Any]] = None, now: Optional[float] = None) -> List[Dict[str, Any]]:
    """Deterministic for a given (seed, duration_s, scale, params, now). Flows lie in [now - duration_s, now] so their event time is already in the past when sent."""
    meta = get(scenario_id)
    if not 10 <= duration_s <= 3600:
        raise ValueError("duration_s must be between 10 and 3600")
    if not 0.1 <= scale <= 10:
        raise ValueError("scale must be between 0.1 and 10")
    merged = dict(meta["params"], **(params or {}))
    unknown = set(merged) - set(meta["params"])
    if unknown:
        raise ValueError("unknown parameter(s) for %s: %s" % (scenario_id, ", ".join(sorted(unknown))))
    t1 = int((now if now is not None else time.time()) * 1000) - 1000
    g = _G(seed, t1 - duration_s * 1000, t1, scenario_id)
    GENERATORS[scenario_id](g, scale, merged)
    rows = sorted(g.rows, key=lambda r: (r["record"].end_time_ms, r["record"].start_time_ms, r["record"].src_ip, r["record"].src_port))
    if len(rows) > 20000:
        raise ValueError("configuration would generate %d flows; the cap is 20000" % len(rows))
    for i, r in enumerate(rows):
        r["record"].netspout_run_id = run_id
        r["seq"] = i
    return rows


# ------------------------------------------------------------------------------------------------------------- normalization
def _iso(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000.0, tz=timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _flags_text(flags: int) -> str:
    return "|".join(n for b, n in TCP_BITS if flags & b) or ""


def normalize(rec: FlowRecord, exporter_ip: str, label_meta: Optional[Dict[str, Any]] = None, phase: Optional[str] = None) -> Dict[str, Any]:
    """Normalized decoded-flow event. `native` holds the IPFIX information elements as exported; the rest is the normalized layer.
    CIM names (src, dest, transport, ...) are produced at search time from these fields by the app's props.conf, so the stored event never claims to be CIM data."""
    dur = max(0, rec.end_time_ms - rec.start_time_ms)
    tos = rec.tos_dscp & 0xFF
    sport_app = PORT_APP.get(rec.dest_port) if rec.protocol in (6, 17) else None
    ev = {
        "timestamp_epoch": rec.end_time_ms / 1000.0,
        "flowStartMilliseconds": rec.start_time_ms, "flowEndMilliseconds": rec.end_time_ms,
        "flow_start_iso": _iso(rec.start_time_ms), "flow_end_iso": _iso(rec.end_time_ms), "duration_ms": dur,
        "exporter_ip": exporter_ip, "src_ip": rec.src_ip, "src_port": rec.src_port, "dest_ip": rec.dest_ip, "dest_port": rec.dest_port,
        "protocol": PROTO_NAME.get(rec.protocol, str(rec.protocol)), "protocol_number": rec.protocol,
        "app": sport_app, "app_basis": "port_heuristic" if sport_app else None,
        "tcp_flags": rec.tcp_flags if rec.protocol == 6 else None, "tcp_flags_text": _flags_text(rec.tcp_flags) if rec.protocol == 6 else None,
        "bytes_in": None, "bytes_out": None, "packets_in": None, "packets_out": None,
        "bytes": rec.bytes_count, "packets": rec.packets_count, "tos": tos, "dscp": tos >> 2,
        "snmp_in": rec.input_snmp, "snmp_out": rec.output_snmp, "src_as": rec.src_as, "dest_as": rec.dest_as, "flow_end_reason": None,
        "native": {"sourceIPv4Address": rec.src_ip, "destinationIPv4Address": rec.dest_ip, "sourceTransportPort": rec.src_port, "destinationTransportPort": rec.dest_port,
                   "protocolIdentifier": rec.protocol, "tcpControlBits": rec.tcp_flags, "ipClassOfService": tos, "octetDeltaCount": rec.bytes_count, "packetDeltaCount": rec.packets_count,
                   "ingressInterface": rec.input_snmp, "egressInterface": rec.output_snmp, "bgpSourceAsNumber": rec.src_as, "bgpDestinationAsNumber": rec.dest_as,
                   "flowStartMilliseconds": rec.start_time_ms, "flowEndMilliseconds": rec.end_time_ms},
        "label_meta": dict(label_meta or {}), "label_note": "synthetic scenario truth; not exporter telemetry",
    }
    return ev


PROTO_NUMBER = {"ICMP": 1, "TCP": 6, "UDP": 17}


def record_from_goflow(row: Dict[str, Any]) -> FlowRecord:
    """Rebuild a FlowRecord from one GoFlow2 JSON row (the collector's decode of our IPFIX), so the normalized layer can be produced from DECODED data too.
    Exporter identity is not in the row (sampler_address is the UDP source); callers pass exporter_ip separately."""
    proto = row.get("proto")
    return FlowRecord(src_ip=row["src_addr"], dest_ip=row["dst_addr"], src_port=int(row.get("src_port", 0)), dest_port=int(row.get("dst_port", 0)),
                      protocol=PROTO_NUMBER.get(str(proto).upper(), proto if isinstance(proto, int) else 0), tcp_flags=int(row.get("tcp_flags", 0)), tos_dscp=int(row.get("ip_tos", 0)),
                      src_as=int(row.get("src_as", 0)), dest_as=int(row.get("dst_as", 0)), input_snmp=int(row.get("in_if", 0)), output_snmp=int(row.get("out_if", 0)),
                      bytes_count=int(row.get("bytes", 0)), packets_count=int(row.get("packets", 0)),
                      start_time_ms=int(row["time_flow_start_ns"]) // 1_000_000, end_time_ms=int(row["time_flow_end_ns"]) // 1_000_000)


def normalize_goflow(row: Dict[str, Any], exporter_ip: Optional[str] = None, label_meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Normalized event from a decoded collector row. exporter_ip defaults to sampler_address (the UDP source), which is NOT the synthetic exporter address."""
    return normalize(record_from_goflow(row), exporter_ip or row.get("sampler_address") or "", label_meta)


def hec_payloads(rows: List[Dict[str, Any]], index: str, sourcetype: str = DEFAULT_SOURCETYPE, host: str = "netspout-flow-normalizer") -> List[Dict[str, Any]]:
    """One HEC event per flow. Run/phase/scenario are also sent as indexed fields so run-bound verification and readiness work like every other pack."""
    out = []
    for r in rows:
        ev = normalize(r["record"], r["exporter_ip"], r["label_meta"], r["phase"])
        out.append({"time": ev["timestamp_epoch"], "host": host, "source": SOURCE, "sourcetype": sourcetype, "index": index, "event": ev,
                    "fields": {"netspout_run_id": r["record"].netspout_run_id, "netspout_scenario_id": r["record"].netspout_scenario_id, "netspout_phase": r["phase"]}})
    return out


def ndjson_lines(rows: List[Dict[str, Any]]) -> List[str]:
    """The same normalized events as newline-delimited JSON for file or forwarder ingestion. Run binding is added at the top level here (over HEC it travels as indexed fields instead)."""
    import json
    out = []
    for r in rows:
        ev = normalize(r["record"], r["exporter_ip"], r["label_meta"], r["phase"])
        ev.update(netspout_run_id=r["record"].netspout_run_id, netspout_scenario_id=r["record"].netspout_scenario_id, netspout_phase=r["phase"])
        out.append(json.dumps(ev, separators=(",", ":")))
    return out


def summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    ph: Dict[str, int] = {}
    for r in rows:
        ph[r["phase"]] = ph.get(r["phase"], 0) + 1
    return {"flows": len(rows), "phases": ph, "exporters": sorted({r["exporter_ip"] for r in rows}), "malicious_labeled": sum(r["label_meta"]["is_malicious"] for r in rows),
            "bytes": sum(r["record"].bytes_count for r in rows), "packets": sum(r["record"].packets_count for r in rows)}
