import statistics
from collections import Counter, defaultdict

import pytest

from netspout_core import netflow_solution as nf

NOW = 1_800_000_000.0


def gen(sid, **kw):
    return nf.generate(sid, "run-test", now=NOW, **kw)


def test_ten_unique_scenarios_with_documentation_addresses():
    assert len(nf.IDS) == len(set(nf.IDS)) == 10
    assert sum(c["kind"] == "operational" for c in nf.CATALOG) == 5
    for sid in nf.IDS:
        for r in gen(sid):
            rec = r["record"]
            for ip in (rec.src_ip, rec.dest_ip, r["exporter_ip"]):
                assert ip.startswith(("192.0.2.", "198.51.100.", "203.0.113.")), (sid, ip)


@pytest.mark.parametrize("sid", nf.IDS)
def test_deterministic_and_bounded(sid):
    a, b = gen(sid), gen(sid)
    assert [r["record"].model_dump() for r in a] == [r["record"].model_dump() for r in b]
    assert [r["record"].model_dump() for r in a] != [r["record"].model_dump() for r in gen(sid, seed=7)]
    t1 = int(NOW * 1000)
    assert all(t1 - 181_000 <= r["record"].start_time_ms <= r["record"].end_time_ms <= t1 for r in a)
    assert 40 < len(a) <= 20000
    ends = [r["record"].end_time_ms for r in a]
    assert ends == sorted(ends)


def test_normalized_event_semantics():
    r = gen("NF-SEC-06-DDOS")[0]
    ev = nf.normalize(r["record"], r["exporter_ip"], r["label_meta"], r["phase"])
    assert ev["duration_ms"] == ev["flowEndMilliseconds"] - ev["flowStartMilliseconds"] >= 0
    assert ev["timestamp_epoch"] == ev["flowEndMilliseconds"] / 1000.0
    assert ev["flow_end_iso"].endswith("Z")
    assert ev["bytes_in"] is ev["bytes_out"] is ev["packets_in"] is ev["packets_out"] is None   # unidirectional records: never fabricated
    assert ev["flow_end_reason"] is None
    assert ev["dscp"] == ev["tos"] >> 2
    assert ev["native"]["octetDeltaCount"] == ev["bytes"] and "label_meta" not in ev["native"]
    assert set(ev["label_meta"]) >= {"scenario_id", "is_malicious", "threat_technique"}
    assert ev["app"] is None or ev["app_basis"] == "port_heuristic"


def test_hec_payload_carries_run_binding_and_time_in_past():
    rows = gen("NF-NOC-05-BASELINE-DRIFT")
    pl = nf.hec_payloads(rows, "dev_test_replay")
    assert len(pl) == len(rows) and pl[0]["sourcetype"] == nf.DEFAULT_SOURCETYPE and pl[0]["index"] == "dev_test_replay"
    assert all(p["fields"]["netspout_run_id"] == "run-test" and p["time"] < NOW for p in pl)


def test_elephants_dominate_bytes():
    rows = gen("NF-NOC-01-ELEPHANT")
    big = sum(r["record"].bytes_count for r in rows if r["phase"] == "elephant")
    assert big > 0.9 * sum(r["record"].bytes_count for r in rows)


def test_dscp_noncompliance_is_concentrated():
    bad = Counter()
    for r in gen("NF-NOC-02-DSCP"):
        rec = r["record"]
        if r["phase"] == "voice-video":
            want = 46 if r["label_meta"]["role"] == "voice" else 34
            bad[rec.src_ip] += (rec.tos_dscp >> 2) != want
    offenders = [ip for ip, n in bad.items() if n > 5]
    assert 0 < len(offenders) < len(bad)


def test_asymmetry_has_all_three_pair_outcomes():
    rows = gen("NF-NOC-04-ASYMMETRY")
    ph = Counter(r["phase"] for r in rows)
    assert ph["paired"] > 0 and ph["reverse-elsewhere"] > 0
    fwd = sum(r["label_meta"]["role"] == "forward" for r in rows)
    rev = sum(r["label_meta"]["role"] == "reverse" for r in rows)
    assert rev < fwd                      # some reverse flows are never observed


def test_ddos_ramps_and_syn_only():
    rows = [r for r in gen("NF-SEC-06-DDOS") if r["phase"] == "syn-flood"]
    assert all(r["record"].tcp_flags == nf.SYN and r["record"].packets_count == 1 for r in rows)
    mid = (rows[0]["record"].end_time_ms + rows[-1]["record"].end_time_ms) / 2
    assert sum(r["record"].end_time_ms > mid for r in rows) > len(rows) / 2


def test_scan_footprint():
    by = defaultdict(lambda: (set(), set()))
    for r in gen("NF-SEC-07-PORTSCAN"):
        rec = r["record"]
        by[rec.src_ip][0].add(rec.dest_port)
        by[rec.src_ip][1].add(rec.dest_ip)
    assert len(by["198.51.100.77"][0]) > 30 and len(by["198.51.100.77"][1]) > 30
    assert all(len(p) < 10 for ip, (p, h) in by.items() if ip != "198.51.100.77" and len(h) < 5)


def test_exfil_volume_concentrated_on_one_internal_host():
    out = Counter()
    for r in gen("NF-SEC-08-EXFIL"):
        rec = r["record"]
        if nf.is_internal(rec.src_ip) and not nf.is_internal(rec.dest_ip):
            out[rec.src_ip] += rec.bytes_count
    top, n = out.most_common(1)[0]
    assert top == "192.0.2.120" and n > 0.8 * sum(out.values())


def test_beacon_interval_regular_vs_irregular():
    def cv(src):
        ts = sorted(r["record"].start_time_ms for r in gen("NF-SEC-09-BEACON") if r["record"].src_ip == src)
        gaps = [(b - a) / 1000 for a, b in zip(ts, ts[1:])]
        return statistics.pstdev(gaps) / statistics.mean(gaps), len(gaps)
    c, n = cv("198.51.100.140")
    assert n >= 5 and c < 0.2
    assert cv("198.51.100.150")[0] > 0.5


def test_dns_has_paired_reverse_flows_and_imbalance():
    rows = gen("NF-SEC-10-DNS-FLOW")
    req = Counter(); resp = Counter()
    for r in rows:
        rec = r["record"]
        if rec.dest_port == 53:
            req[rec.src_ip] += rec.bytes_count
        elif rec.src_port == 53:
            resp[rec.dest_ip] += rec.bytes_count
    assert req["198.51.100.200"] / req["198.51.100.10"] > 0 and resp["198.51.100.200"] > 0
    assert all(c["label_meta"]["is_malicious"] for c in rows if c["phase"] == "dns-heavy")


def test_parameter_validation():
    with pytest.raises(ValueError):
        gen("NF-SEC-06-DDOS", params={"nope": 1})
    with pytest.raises(ValueError):
        gen("NF-SEC-06-DDOS", scale=50)
    with pytest.raises(ValueError):
        gen("NF-SEC-06-DDOS", duration_s=1)
    with pytest.raises(ValueError):
        nf.get("NF-NOPE")


def test_normalized_layer_from_decoded_row_equals_source():
    r = gen("NF-NOC-02-DSCP")[5]
    rec = r["record"]
    row = {"src_addr": rec.src_ip, "dst_addr": rec.dest_ip, "src_port": rec.src_port, "dst_port": rec.dest_port, "proto": nf.PROTO_NAME[rec.protocol].upper(), "tcp_flags": rec.tcp_flags,
           "ip_tos": rec.tos_dscp, "src_as": rec.src_as, "dst_as": rec.dest_as, "in_if": rec.input_snmp, "out_if": rec.output_snmp, "bytes": rec.bytes_count, "packets": rec.packets_count,
           "time_flow_start_ns": rec.start_time_ms * 1_000_000, "time_flow_end_ns": rec.end_time_ms * 1_000_000, "sampler_address": "172.21.0.1"}
    assert nf.normalize_goflow(row, r["exporter_ip"]) == nf.normalize(rec, r["exporter_ip"])


def test_ndjson_lines_are_valid_json_with_run_binding():
    import json
    lines = nf.ndjson_lines(gen("NF-SEC-08-EXFIL"))
    ev = json.loads(lines[0])
    assert ev["netspout_run_id"] == "run-test" and ev["netspout_scenario_id"] == "NF-SEC-08-EXFIL" and "\n" not in lines[0]


def test_explorer_exposes_ten_runnable_netflow_entries():
    from netspout_core.use_case_explorer import UseCaseExplorer  # noqa: F401  (import check); entries are built in the engine
    from app import main
    entries = [e for e in main._explorer().all_entries() if e.get("engine") == "netflow_solution" or "netflow" in str(e.get("entry_id"))]
    assert len(entries) == 10
    assert len({e["scenario_id"] for e in entries}) == 10
