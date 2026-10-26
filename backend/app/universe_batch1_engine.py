# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/universe_batch1_engine.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""Universal Vendor Coverage — evidence-backed generator batch 1
==============================================================
First bounded multi-vendor generator batch of the Universal Vendor Coverage
phase (registry catalog/vendor_universe.json -> batches.batch_1). Every
format is modelled on vendor-native RAW samples pinned to
catalog/raw_reference/universe_batch1/ (sha256 recorded in
catalog/raw_reference/provenance.json, tag universe:batch1):

  docker_events                     -> pinned docs.docker.com docker events
                                       RFC3339Nano event lines
  bluecoat:proxysg:access:file      -> pinned Symantec/Broadcom ProxySG
                                       'main' format access-log record
                                       (official Splunkbase TA declares the
                                       bluecoat:proxysg:access:* family)
  wazuh:alerts                      -> pinned Wazuh manager alerts.log
                                       Rootcheck alert blocks (three examples)
  nozomi:universal_alert            -> pinned Nozomi Networks vendor-native
                                       alert JSON (official vendor
                                       Universal Add-on declares
                                       nozomi:universal_alert)

Guarantees (enforced by tests)
  * RAW is pure vendor-native: no NetSpout correlation tails inside RAW
  * correlation metadata (netspout_run_id etc.) lives ONLY on LogEntry fields
  * deterministic identifiers (crc32-derived) for reproducible episodes
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

try:
    from netspout_core.models import LogEntry, Node
    from netspout_core.wave1_authentic_engine import (
        _hex8,
        _reg,
    )
except ImportError:  # pragma: no cover - packaging fallback
    try:
        from app.models import LogEntry, Node
    except ImportError:
        from models import LogEntry, Node
    import zlib

    def _reg(seed: str) -> str:
        return f"{zlib.crc32(seed.encode('utf-8')) & 0x7fffffff:08x}"

    def _hex8(name: str) -> str:
        return f"{zlib.crc32(name.encode('utf-8')) & 0xffffffff:08x}"


# ---------------------------------------------------------------------------
# Sourcetype constants
# ---------------------------------------------------------------------------
SOURCETYPE_DOCKER_EVENTS = "docker_events"
SOURCETYPE_PROXYSG_FILE = "bluecoat:proxysg:access:file"
SOURCETYPE_WAZUH_ALERTS = "wazuh:alerts"
SOURCETYPE_NOZOMI_ALERT = "nozomi:universal_alert"


class UniverseBatch1Engine:
    """Static vendor-native formatters for Universal-Vendor-Coverage batch 1."""

    # ------------------------------------------------------------------
    # Docker engine events (docker_events)
    # ------------------------------------------------------------------
    DOCKER_EVENTS_FAMILIES = ["container_lifecycle", "network_connect"]

    @classmethod
    def format_docker_events_log(cls, device: Node, family: str,
                                 image: str = "alpine:latest",
                                 workload: str = "test",
                                 src_ip: str = "172.17.0.3",
                                 action: str = "allowed",
                                 status: str = "normal",
                                 signature: str = "docker-events") -> LogEntry:
        """docker events line: RFC3339Nano ts, object type, action, id, attrs."""
        if family not in cls.DOCKER_EVENTS_FAMILIES:
            raise ValueError(f"Unsupported docker_events family: {family}")
        now = datetime.now(timezone.utc)
        container_id = _hex8("docker|c1") + _hex8("docker|c2") + _hex8("docker|c3") + _hex8("docker|c4") \
            + _hex8("docker|c5") + _hex8("docker|c6") + _hex8("docker|c7") + _hex8("docker|c8")
        network_id = _hex8("docker|n1") + _hex8("docker|n2") + _hex8("docker|n3") + _hex8("docker|n4") \
            + _hex8("docker|n5") + _hex8("docker|n6") + _hex8("docker|n7") + _hex8("docker|n8")
        cs = "(container=%s, name=bridge, type=bridge)" % (container_id[:4] + "..." + container_id[-4:])
        if family == "container_lifecycle":
            ev_type = "container"
            obj_id = container_id
            attrs = "(image=%s, name=%s)" % (image, workload)
            ev = "create"
        elif family == "network_connect":
            ev_type = "network"
            obj_id = network_id
            attrs = cs
            ev = "connect"
        raw = "%s %s %s %s %s" % (
            now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond * 1000:09d}" + "+00:00",
            ev_type, ev, obj_id, attrs)
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=src_ip,
            protocol="TCP", duration="0ms", action=action, signature=signature,
            status=status, raw_log=raw, node_type=device.type.value,
            node_id=device.id, vendor="docker",
            sourcetype=SOURCETYPE_DOCKER_EVENTS)

    # ------------------------------------------------------------------
    # Symantec/Broadcom ProxySG 'main' access log (bluecoat:proxysg:access:file)
    # ------------------------------------------------------------------
    PROXYSG_FAMILIES = ["proxy_observed", "proxy_denied"]

    @classmethod
    def format_proxysg_access_log(cls, device: Node, family: str,
                                       src_ip: str, dest_ip: str = "34.111.113.62",
                                       dest_host: str = "pixel.tapad.com",
                                       dest_port: int = 443,
                                       http_get_URI: Optional[str] = None,
                                       user_name: str = "aeinstein",
                                       action: str = "observed",
                                       status: str = "normal",
                                       signature: str = "proxysg",
                                       user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                                       categories: str = "FastwebRes_CallCntr;Web Ads/Analytics",
                                       cipher: str = "sha256WithRSAEncryption",
                                       content_type: str = "text/html") -> LogEntry:
        """ProxySG 'main' (space-delimited positional) access-log record."""
        if family not in cls.PROXYSG_FAMILIES:
            raise ValueError(f"Unsupported proxysg family: {family}")
        now = datetime.now(timezone.utc)
        scheme = "https" if dest_port == 443 else "http"
        if http_get_URI is None:
            rid = _hex8("sg|rid")
            http_get_URI = "/api/v1/stream/%s?session=%s" % (rid[:8], _hex8("sg|session"))
        status_code = 302
        srv_act = "TCP_NC_MISS"
        filter_result = "OBSERVED"
        s_bytes, cs_bytes = 1242, 969
        if family == "proxy_denied":
            status_code = 403
            srv_act = "TCP_DENIED"
            filter_result = "DENIED"
            s_bytes, cs_bytes = 520, 1043
        if user_agent == "-":
            user_agent_note = '"-"'
        else:
            user_agent_note = '"%s"' % user_agent
        if categories:
            cat_note = '"%s"' % categories
        else:
            cat_note = '"-"'
        positional = [
            now.strftime("%Y-%m-%d %H:%M:%S"), "48", src_ip,
            str(status_code), srv_act, str(s_bytes), str(cs_bytes),
            "GET", scheme, dest_host, str(dest_port), http_get_URI.split("?")[0],
            ("?" + http_get_URI.split("?", 1)[1]) if "?" in http_get_URI else "-",
            user_name if user_name != "-" else "-", "-", "-", dest_host, "-",
            "https://vid.vidoomy.com/", filter_result, cat_note, "-",
            "142.182.19.21", dest_ip, user_agent_note, cipher,
        ]
        raw = " ".join(positional)
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
            protocol="TCP", duration="48ms", action=action.lower() if action else "allowed",
            signature=signature, status=status, raw_log=raw,
            node_type=device.type.value, node_id=device.id,
            vendor="broadcom_symantec", sourcetype=SOURCETYPE_PROXYSG_FILE)

    # ------------------------------------------------------------------
    # Wazuh manager alerts.log block (wazuh:alerts)
    # ------------------------------------------------------------------
    WAZUH_FAMILIES = ["rootcheck_hidden_process", "rootcheck_hidden_file"]

    @classmethod
    def format_wazuh_alert_log(cls, device: Node, family: str,
                               agent_name: str = "Ubuntu",
                               alert_day: Optional[str] = None,
                               secret_file: str = "/dev/.hidden",
                               process_id: int = 659,
                               user_name: Optional[str] = None,
                               action: str = "blocked",
                               status: str = "normal",
                               signature: str = "wazuh-rootcheck") -> LogEntry:
        """Wazuh alerts.log Rootcheck alert block (pinned three examples)."""
        if family not in cls.WAZUH_FAMILIES:
            raise ValueError(f"Unsupported wazuh family: {family}")
        now = datetime.now(timezone.utc)
        base_epoch = int(now.timestamp())
        alert_micro = int(_reg("wz|us|" + family), 16) % 900000 + 123456
        alert_ts = "%s %02d:%02d:%02d" % (alert_day or now.strftime("%Y %b %d"), now.hour, now.minute, now.second)
        groups = ("ossec,rootcheck," if family == "rootcheck_hidden_process"
                  else "ossec,rootcheck,pci_dss_10.6.1,gdpr_IV_35.7.d,")
        lines: List[str] = ["** Alert %s.%s: - %s" % (base_epoch, alert_micro, groups),
                            "%s (%s) any->rootcheck" % (alert_ts, agent_name)]
        if family == "rootcheck_hidden_process":
            # Pinned sample 1: hidden kernel process
            lines.append("Rule: 521 (level 11) -> 'Possible kernel level rootkit'")
            body = "Process '%s' hidden from /proc. Possible kernel level rootkit." % process_id
            title = "Process '%s' hidden from /proc." % process_id
            lines.extend([body, "title: %s" % title])
        else:
            # Pinned sample 3: hidden file on /dev (sample-3 grammar)
            lines.append("Rule: 510 (level 7) -> 'Host-based anomaly detection event (rootcheck).'")
            body = "File '%s' present on /dev. Possible hidden file." % secret_file
            lines.extend([body, "title: File present on /dev.", "file: %s" % secret_file])
        raw = "\n".join(lines)
        return LogEntry(
            timestamp=_wazuh_epoch_to_iso(base_epoch),
            device_id=device.id, src_ip=device.ip_address, dest_ip=device.ip_address,
            protocol="TCP", duration="0ms", action=action, signature=signature,
            status=status, raw_log=raw, node_type=device.type.value,
            node_id=device.id, vendor="wazuh",
            sourcetype=SOURCETYPE_WAZUH_ALERTS)

    # ------------------------------------------------------------------
    # Nozomi Networks alert JSON (nozomi:universal_alert)
    # ------------------------------------------------------------------
    NOZOMI_FAMILIES = ["ot_ids_program_change"]

    @classmethod
    def format_nozomi_alert_log(cls, device: Node, family: str,
                                src_ip: str = "81.2.69.192",
                                dest_ip: str = "89.160.20.112",
                                src_mac: str = "00:0c:29:01:98:be",
                                dest_mac: str = "f4:54:33:9f:22:3d",
                                appliance_host: str = "Sandbox-TAE-Guardian3",
                                protocol: str = "ethernetip",
                                src_port: int = 58679,
                                dest_port: int = 44818,
                                risk: int = 6,
                                severity: int = 10,
                                status: str = "normal",
                                signature: str = "nozomi",
                                action: str = "threat" ) -> LogEntry:
        """Nozomi Networks vendor-native alert JSON line (Universal Add-on)."""
        if family not in cls.NOZOMI_FAMILIES:
            raise ValueError(f"Unsupported nozomi family: {family}")
        now = datetime.now(timezone.utc)
        epoch_ms = int(now.timestamp() * 1000)
        alert_id = "%08x-cfd0-4ae2-9f22-886d86b83398" % int(_hex8("nm|id"), 16)

        if family == "ot_ids_program_change":
            type_id = "SIGN:PROGRAM:CHANGE"
            type_name = "Program change"
            threat_name = "Grizzly Steppe Threat Actor"
            trigger_type = "stix_indicators"
            trigger_id = "indicator--fb15c96c-eb73-48ac-a48a-15bcab2f0fe3"
            description = ("Online edits have been made on the PLC with IP 1.128.0.0. "
                           "The following steps were executed:\n"
                           "[1]- Downloaded project [ PLC_LOGIC_CHALLENGE2\\challenge2changed.ACD ] to [ \\AB_ETHIP-1\\1.128.0.0\\C1_1756 ]\n"
                           "[2]- Changed Controller [ C1_1756 ] to Run Mode\n"
                           "[3]- Changed Controller [ C1_1756 ] to Program Mode")
            src_roles = "consumer, engineering_station"

        alert = {
            "ack": False,
            "appliance_host": appliance_host,
            "appliance_id": "d5ab7eaa-9a4b-4b4b-9a4b-4b4b9a4b4b4b",
            "appliance_ip": "1.128.0.0",
            "appliance_site": "Sandbox",
            "bpf_filter": "(ip host %s and ip host %s and tcp port %d and tcp port %d) or (vlan and ip host %s and ip host %s and tcp port %d and tcp port %d)" % (src_ip, dest_ip, src_port, dest_port, src_ip, dest_ip, src_port, dest_port),
            "capture_device": "base.pcap",
            "close_option": None,
            "closed_time": 0,
            "created_time": epoch_ms,
            "custom_fields_dst": {},
            "custom_fields_src": {},
            "description": description,
            "dst_roles": "producer",
            "grouped_visible": True,
            "id": alert_id,
            "id_dst": dest_ip,
            "id_src": src_ip,
            "ip_src": src_ip,
            "ip_dst": dest_ip,
            "incident_keys": [],
            "is_incident": False,
            "is_security": True,
            "label_dst": "private.default",
            "label_src": "private.default",
            "mac_dst": dest_mac,
            "mac_src": src_mac,
            "name": type_name,
            "note": "User Defined Note",
            "parents": [],
            "playbook_contents": None,
            "port_dst": dest_port,
            "port_src": src_port,
            "properties": {
                "base_risk": risk,
                "from_id": src_ip,
                "is_dst_node_learned": True,
                "is_dst_public": False,
                "is_dst_reputation_bad": False,
                "is_src_node_learned": True,
                "is_src_public": False,
                "is_src_reputation_bad": False,
                "mitre_attack_for_ics": {"destination": {"levels": ["2"], "types": ["Field Controller/RTU/PLC/IED"]},
                                         "source": {"levels": ["2"], "types": ["Engineering Workstation"]}},
                "n2os_version": "25.0.0-03042016_D5AB7",
                "raised_by": "n2os_ids",
                "to_id": dest_ip},
            "protocol": protocol,
            "record_created_at": epoch_ms,
            "replicated": True,
            "risk": risk,
            "sec_profile_visible": True,
            "session_id": "12eszcd-223cds34",
            "severity": severity,
            "src_roles": src_roles,
            "status": "open",
            "synchronized": True,
            "threat_name": threat_name,
            "ti_source": "",
            "time": epoch_ms,
            "trace_sha1": None,
            "trace_status": "state_unavailable_for_alert_type",
            "transport_protocol": "tcp",
            "trigger_id": trigger_id,
            "trigger_type": trigger_type,
            "type_id": type_id,
            "type_name": type_name,
            "zone_dst": "Production_A",
            "zone_src": "Production_A",
        }
        raw = json.dumps(alert) + "\n"
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
            protocol=protocol.upper(), duration="0ms", action=action,
            signature=signature, status=status, raw_log=raw,
            node_type=device.type.value, node_id=device.id,
            vendor="nozomi_networks", sourcetype=SOURCETYPE_NOZOMI_ALERT)


def _wazuh_epoch_to_iso(epoch: int) -> str:
    from datetime import datetime as _dt
    return _dt.fromtimestamp(epoch, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S.000")


UNIVERSE_BATCH1_SOURCE_SOURCETYPES = {
    SOURCETYPE_DOCKER_EVENTS: "format_docker_events_log",
    SOURCETYPE_PROXYSG_FILE: "format_proxysg_access_log",
    SOURCETYPE_WAZUH_ALERTS: "format_wazuh_alert_log",
    SOURCETYPE_NOZOMI_ALERT: "format_nozomi_alert_log",
}
