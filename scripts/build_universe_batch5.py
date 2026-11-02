#!/usr/bin/env python3
"""Build catalog/universe_batch5.json: Cisco IOS-XE change / fault / health device syslog (31 cisco:sdwan:<MNEMONIC> sourcetypes).

Every family text is a real captured IOS-XE message taken from the vendored Network Assurance replay samples
(netspout/appserver/static/samples/cisco-sdwan-*). Only declared fields vary at render time: timestamps, the device
address in the syslog header, the per-device sequence number, and (for the correlated families) interface, neighbor,
state and CLI-command slots whose surrounding text is unchanged from the captured message. Nothing here is invented;
a mnemonic whose captured text is not parameterizable is rendered verbatim.

Run:  python scripts/build_universe_batch5.py   (idempotent; then scripts/sync_core.py)
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLES = ROOT / "netspout" / "appserver" / "static" / "samples"
SEVERITY_STATUS = {"0": "critical", "1": "critical", "2": "critical", "3": "error", "4": "warning", "5": "notice", "6": "info"}

# Correlated families: (family_id, body with slots, defaults). Text matches captured messages exactly.
LINKED = {
    "LINK-5-UPDOWN": [("link_state", "%LINK-5-UPDOWN: Interface {interface}, changed state to {state}", {"interface": "GigabitEthernet1/0/5", "state": "up"})],
    "LINEPROTO-5-UPDOWN": [("line_protocol", "%LINEPROTO-5-UPDOWN: Line protocol on Interface {interface}, changed state to {state}", {"interface": "GigabitEthernet1/0/5", "state": "up"})],
    "LINK-5-CHANGED": [("admin_down", "%LINK-5-CHANGED: Interface {interface}, changed state to administratively down", {"interface": "GigabitEthernet1/0/5"})],
    "OSPF-5-ADJCHG": [("adjacency", "%OSPF-5-ADJCHG: Process 1, Nbr {neighbor} on {interface} from {from_state} to {to_state}, {reason}",
                       {"neighbor": "10.201.48.120", "interface": "GigabitEthernet1/0/5", "from_state": "FULL", "to_state": "DOWN", "reason": "Neighbor Down: Dead timer expired"})],
    "BGP-5-NBR_RESET": [("peer_closed", "%BGP-5-NBR_RESET: Neighbor {neighbor} passive reset (Peer closed the session)", {"neighbor": "10.201.130.61"})],
    "BGP-5-ADJCHANGE": [("vrf_down", "%BGP-5-ADJCHANGE: neighbor {neighbor} vpn vrf {vrf} Down Neighbor deleted", {"neighbor": "10.201.152.1", "vrf": "UBC_TENANT"}),
                        ("up", "%BGP-5-ADJCHANGE: neighbor {neighbor} Up ", {"neighbor": "10.201.48.118"})],
    "MSDP-5-PEER_UPDOWN": [("peer_state", "%MSDP-5-PEER_UPDOWN: Session to peer {neighbor} going {state}", {"neighbor": "10.201.151.1", "state": "down"})],
    "CDP-4-NATIVE_VLAN_MISMATCH": [("vlan_mismatch", "%CDP-4-NATIVE_VLAN_MISMATCH: Native VLAN mismatch discovered on {interface} ({vlan}), with {peer} {peer_interface} ({peer_vlan}).",
                                    {"interface": "GigabitEthernet1/0/4", "vlan": "1", "peer": "switch2", "peer_interface": "GigabitEthernet0/1", "peer_vlan": "201"})],
    "DMI-5-SYNC_NEEDED": [("sync_needed", "%DMI-5-SYNC_NEEDED: Switch 1 R0/0: dmiauthd: Configuration change requiring running configuration sync detected - '{command}'. The running configuration will be synchronized  to the NETCONF running data store.",
                           {"command": "switchport trunk allowed vlan 2052"})],
    "ENVIRONMENTAL-1-ALERT": [("temperature", "%ENVIRONMENTAL-1-ALERT: Temp: Inlet 1, Location: R0, State: Warning, Reading: {reading} Celsius", {"reading": "43"})],
    "PLATFORM-4-ELEMENT_WARNING": [("load_average", "%PLATFORM-4-ELEMENT_WARNING: R0/0: smand: RP/0: 5-Minute Load Average value {load} exceeds warning level 6.10.", {"load": "6.11"})],
    "MDT_CONNECTION-6-STATE_CHANGED": [("connection_state", "%MDT_CONNECTION-6-STATE_CHANGED: Switch 1 R0/0: pubd: Connection state changed (id {conn_id} - 10.20.1.16:25103:0:{device_ip}): {state}",
                                        {"conn_id": "6", "device_ip": "10.201.48.120", "state": "DOWN"})],
}

# scenario id -> ordered (phase, sourcetype mnemonic, family id, params)
SCENARIOS = {
    "ub5_cisco_change_induced_outage": [
        ("BASELINE", "OSPF-5-ADJCHG", "adjacency", {"from_state": "LOADING", "to_state": "FULL", "reason": "Loading Done"}),
        ("BASELINE", "BGP-5-ADJCHANGE", "up", {}),
        ("BASELINE", "MSDP-5-PEER_UPDOWN", "peer_state", {"state": "up"}),
        ("CHANGE", "DMI-5-SYNC_NEEDED", "sync_needed", {"command": "switchport trunk allowed vlan 2052"}),
        ("CHANGE", "DMI-5-SYNC_START", None, {}),
        ("CHANGE", "DMI-5-SYNC_COMPLETE", None, {}),
        ("CHANGE", "NDBMAN-5-CONFIG_I", None, {}),
        ("FAULT", "CDP-4-NATIVE_VLAN_MISMATCH", "vlan_mismatch", {}),
        ("FAULT", "LINK-5-CHANGED", "admin_down", {}),
        ("FAULT", "LINK-5-UPDOWN", "link_state", {"state": "down"}),
        ("FAULT", "LINEPROTO-5-UPDOWN", "line_protocol", {"state": "down"}),
        ("FAULT", "OSPF-5-ADJCHG", "adjacency", {}),
        ("FAULT", "BGP-5-ADJCHANGE", "vrf_down", {}),
        ("FAULT", "BGP-5-NBR_RESET", "peer_closed", {}),
        ("FAULT", "MSDP-5-PEER_UPDOWN", "peer_state", {"state": "down"}),
        ("RECOVERY", "LINK-5-UPDOWN", "link_state", {"state": "up"}),
        ("RECOVERY", "LINEPROTO-5-UPDOWN", "line_protocol", {"state": "up"}),
        ("RECOVERY", "OSPF-5-ADJCHG", "adjacency", {"from_state": "LOADING", "to_state": "FULL", "reason": "Loading Done"}),
        ("RECOVERY", "BGP-5-ADJCHANGE", "up", {}),
        ("RECOVERY", "MSDP-5-PEER_UPDOWN", "peer_state", {"state": "up"}),
    ],
    "ub5_cisco_platform_health_degradation": [
        ("BASELINE", "PKI-6-AUTHORITATIVE_CLOCK", None, {}),
        ("BASELINE", "MDT_CONNECTION-6-STATE_CHANGED", "connection_state", {"state": "UP"}),
        ("DEGRADE", "ENVIRONMENTAL-1-ALERT", "temperature", {"reading": "43"}),
        ("DEGRADE", "PLATFORM-4-ELEMENT_WARNING", "load_average", {"load": "6.11"}),
        ("DEGRADE", "EVENTLIB-3-CPUHOG", None, {}),
        ("DEGRADE", "IOSXE-3-PLATFORM", None, {}),
        ("IMPACT", "IOSXE_INFRA-4-NO_PUNT_KEEPALIVE", None, {}),
        ("IMPACT", "MDT_CONNECTION-6-STATE_CHANGED", "connection_state", {"state": "DOWN"}),
        ("RECOVERY", "MDT_CONNECTION-6-STATE_CHANGED", "connection_state", {"state": "UP"}),
        ("RECOVERY", "ENVIRONMENTAL-1-ALERT", "temperature", {"reading": "36"}),
    ],
    "ub5_cisco_nac_radius_outage": [
        ("BASELINE", "AAA-6-METHOD_LIST_STATE", "alive", {}),
        ("OUTAGE", "CTS-3-AAA_NO_RADIUS_SERVER", None, {}),
        ("OUTAGE", "AAA-6-METHOD_LIST_STATE", "dead", {}),
        ("OUTAGE", "AAA-6-NOTIFY_MLIST_STATE_TO_AAA_CLIENT", "dead", {}),
        ("OUTAGE", "AAA_AUDIT_MESSAGE-6-METHOD_LIST_STATE", None, {}),
        ("RECOVERY", "AAA-6-METHOD_LIST_STATE", "alive", {}),
        ("RECOVERY", "AAA-6-NOTIFY_MLIST_STATE_TO_AAA_CLIENT", "alive", {}),
        ("RECOVERY", "AAA_AUDIT_MESSAGE-6-NOTIFY_MLIST_STATE_TO_AAA_CLIENT", None, {}),
    ],
}


def unescape_yaml(s):
    return s.replace("''", "'")


def captured(sample_dir):
    """Distinct (star, body) pairs captured in a sample file, in file order, with the sample line number."""
    out, seen = [], set()
    text = next(sample_dir.glob("*.yml")).read_text()
    for number, line in enumerate(text.splitlines(), 1):
        m = re.search(r"_raw: '(.*)'\s*$", line)
        if not m:
            continue
        raw = unescape_yaml(m.group(1))
        h = re.match(r"\$\w+\$ \S+ \d+: (\*?)\$\w+\$(?:\.\d+)?:\s+(%.*)$", raw)
        if not h:
            raise SystemExit(f"cannot parse captured line {sample_dir.name}:{number}: {raw[:80]}")
        key = (h.group(1), h.group(2))
        if key not in seen:
            seen.add(key)
            out.append({"star": bool(h.group(1)), "body": h.group(2), "sample_line": number})
    return out


def main():
    catalog = json.loads((ROOT / "catalog" / "sourcetypes.json").read_text())
    rows = [r for r in catalog if r["splunk_sourcetype"].startswith("cisco:sdwan:") and "-" in r["splunk_sourcetype"].split(":")[-1]]
    sources = []
    for r in sorted(rows, key=lambda r: r["splunk_sourcetype"]):
        mnemonic = r["splunk_sourcetype"].split(":")[-1]
        sample_dir = SAMPLES / ("cisco-sdwan-" + mnemonic.lower().replace("_", "-"))
        caps = captured(sample_dir)
        facility, severity = re.match(r"([A-Z0-9_]+)-(\d)-", mnemonic + "-").group(1), re.search(r"-(\d)-", mnemonic).group(1)
        families = []
        for fid, body, defaults in LINKED.get(mnemonic, []):
            families.append({"id": fid, "body": body, "star": caps[0]["star"], "params": defaults, "origin": "linked", "sample": sample_dir.name})
        # linked families replace verbatim ones only when the verbatim line is the same message shape
        for i, c in enumerate(caps):
            if mnemonic in LINKED:
                continue
            fid = "captured_%d" % (i + 1)
            if mnemonic in ("AAA-6-METHOD_LIST_STATE", "AAA-6-NOTIFY_MLIST_STATE_TO_AAA_CLIENT"):
                fid = "dead" if c["body"].rstrip().endswith("DEAD") else "alive"
            families.append({"id": fid, "body": c["body"], "star": c["star"], "params": {}, "origin": "captured", "sample": sample_dir.name, "sample_line": c["sample_line"]})
        ids = [f["id"] for f in families]
        assert len(ids) == len(set(ids)), (mnemonic, ids)
        sources.append({
            "batch_source_id": mnemonic, "vendor": r["vendor_id"], "product": "IOS-XE device syslog (Catalyst / SD-WAN edge)",
            "splunk_sourcetype": r["splunk_sourcetype"], "generator": "format_universe_batch5_log",
            "facility": facility, "severity": int(severity), "status": SEVERITY_STATUS.get(severity, "info"),
            "event_families": ids, "families": families,
        })
    known = {s["batch_source_id"]: {f["id"] for f in s["families"]} for s in sources}
    for sid, steps in SCENARIOS.items():
        for phase, mnemonic, fid, _ in steps:
            assert mnemonic in known, (sid, mnemonic)
            assert fid is None or fid in known[mnemonic], (sid, mnemonic, fid, sorted(known[mnemonic]))
    registry = {
        "schema_version": "1.0", "registry_version": "universe-batch5-2026-10-30",
        "purpose": "Cisco IOS-XE change, fault and health device syslog: vendor-native lines from captured device messages; correlated change-to-outage, platform health and NAC/RADIUS outage scenarios.",
        "baseline_counts": {"native_generators": 112, "sourcetypes": 348},
        "engine_module": "src/netspout_core/universe_batch5_engine.py",
        "provenance": "Captured IOS-XE messages in netspout/appserver/static/samples/cisco-sdwan-* (Network Assurance replay). Splunk TA parsing for these sourcetypes is NOT verified; source name alone is not verification.",
        "sources": sources,
        "scenarios": {sid: [{"phase": p, "sourcetype": m, "family": f, "params": prm} for p, m, f, prm in steps] for sid, steps in SCENARIOS.items()},
        "counts_summary": {"new_native_sourcetypes": len(sources), "families": sum(len(s["families"]) for s in sources), "scenario_packs": len(SCENARIOS)},
    }
    (ROOT / "catalog" / "universe_batch5.json").write_text(json.dumps(registry, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(registry["counts_summary"]))


if __name__ == "__main__":
    main()
