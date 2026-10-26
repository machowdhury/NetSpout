"""
Wave 3 Authentic Splunkbase-Scale Expansion Engine
==================================================
Fourth batch of genuinely supported vendor-native RAW families
(Splunkbase-scale telemetry expansion). Every format is modelled on the
pinned upstream datasets committed to the RAW reference corpus
(catalog/raw_reference/wave3/ + provenance.json sha256 ledger, wave:3 tags)
plus official vendor schemas:

  vmw-syslog                                   -> pinned ESXi Hostd event
                                                  download + shell audit lines
  cisco:cloud_security:firewall                -> pinned CSV rows (C2S/TCP +
                                                  S2C/ICMP layouts)
  cisco:cloud_security:dns                     -> pinned 16-column CSV row
  cisco:cloud_security:proxy                   -> pinned 49-column CSV row
  cisco:isovalent (+ :processExec/:processConnect)
                                               -> pinned Tetragon process_exec
                                                  / process_connect records
  aws:cloudtrail:lake                          -> pinned OCSF CloudTrail Lake
                                                  record (complete fixture)
  linux_secure                                 -> pinned /var/log/secure su +
                                                  documented sshd grammar
  iis                                          -> pinned W3C WSUS access +
                                                  module-backdoor listing
  bro:conn:json                                -> pinned Zeek conn JSON
  MSExchange:Management                        -> pinned cmdlet event block +
                                                  pinned ECP client access row
  aws:cloudfront:accesslogs                    -> pinned 33-column
                                                  tab-delimited edge access row
  o365:reporting:messagetrace                  -> pinned message trace JSON
  o365:graph:messagetrace                      -> pinned Graph message trace JSON
  gsuite:gmail:bigquery                        -> pinned Gmail BigQuery row
  zscalernss-web                               -> pinned Zscaler NSS web JSON
                                                  (keys 0..43 of the ledger
                                                  record; later keys omitted)
  cisco:secure_access:security_events_ravpn    -> pinned OCSF AAA event
  cisco:sdwan:syslog / cisco:sdwan:access      -> pinned Viptela syslog +
                                                  envoy access row
  cisco:ios                                    -> pinned %SEC_LOGIN events
  XmlWinEventLog:System                        -> documented System channel
                                                  event XML
  cisco:meraki:syslog                          -> documented Meraki flows/urls
  dhcpd                                        -> documented ISC dhcpd grammar
  gcp:audit                                    -> documented audit record schema
  opentelemetry:otlp                           -> documented OTLP/JSON log +
                                                  span records
  cisco:duo:administrator (existing row)       -> pinned admin action + pinned
                                                  activity records

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
        _reg,
        _hex8,
        _utc7,
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

    def _utc7(now: datetime) -> str:
        return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 100:07d}" + "Z"


def _csv_q(value: Any) -> str:
    """Cloud security CSV dialect: everything quoted, embedded quotes doubled."""
    return '"%s"' % str(value).replace('"', '""')


def _iso_ms(now: datetime) -> str:
    return now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"


def _rfc3164_syslog_ts(now: datetime) -> str:
    """RFC3164 sender timestamp with space-padded day (e.g. 'May  7 17:17:50')."""
    return "%s %2d %02d:%02d:%02d" % (
        now.strftime("%b"), int(now.strftime("%d")),
        now.hour, now.minute, now.second)


def _nsec(now: datetime, offset_s: int = 0) -> str:
    """Nanosecond unix timestamp (OTLP), 19 digits."""
    return str((int(now.timestamp()) + offset_s) * 1_000_000_000
               + now.microsecond * 1000)


# ---------------------------------------------------------------------------
# Sourcetype constants (all new rows unless noted as an existing catalog row)
# ---------------------------------------------------------------------------
SOURCETYPE_VMW_SYSLOG = "vmw-syslog"
SOURCETYPE_CSL_FIREWALL = "cisco:cloud_security:firewall"
SOURCETYPE_CSL_DNS = "cisco:cloud_security:dns"
SOURCETYPE_CSL_PROXY = "cisco:cloud_security:proxy"
SOURCETYPE_ISOVALENT = "cisco:isovalent"
SOURCETYPE_ISOVALENT_PROCEXEC = "cisco:isovalent:processExec"
SOURCETYPE_ISOVALENT_PROCCONNECT = "cisco:isovalent:processConnect"
SOURCETYPE_CLOUDTRAIL_LAKE = "aws:cloudtrail:lake"
SOURCETYPE_LINUX_SECURE = "linux_secure"
SOURCETYPE_IIS = "iis"
SOURCETYPE_ZEEK_CONN = "bro:conn:json"
SOURCETYPE_MSEXCHANGE = "MSExchange:Management"
SOURCETYPE_CLOUDFRONT = "aws:cloudfront:accesslogs"
SOURCETYPE_O365_MESSAGETRACE = "o365:reporting:messagetrace"
SOURCETYPE_O365_GRAPH_MESSAGETRACE = "o365:graph:messagetrace"
SOURCETYPE_GMAIL_BIGQUERY = "gsuite:gmail:bigquery"
SOURCETYPE_ZSCALER_NSS_WEB = "zscalernss-web"
SOURCETYPE_RAVPN = "cisco:secure_access:security_events_ravpn"
SOURCETYPE_SDWAN_SYSLOG = "cisco:sdwan:syslog"
SOURCETYPE_SDWAN_ACCESS = "cisco:sdwan:access"
SOURCETYPE_CISCO_IOS = "cisco:ios"
SOURCETYPE_MERAKI_SYSLOG = "cisco:meraki:syslog"
SOURCETYPE_DHCPD = "dhcpd"
SOURCETYPE_GCP_AUDIT = "gcp:audit"
SOURCETYPE_OTEL = "opentelemetry:otlp"
SOURCETYPE_WINDOWS_SYSTEM = "XmlWinEventLog:System"
# Existing catalog row (generator-gap fill, no new row)
SOURCETYPE_DUO_ADMIN = "cisco:duo:administrator"


class Wave3AuthenticEngine:
    """Static vendor-native formatters for the Wave-3 source families."""

    # ------------------------------------------------------------------
    # VMware vSphere / ESXi syslog (vmw-syslog)
    # ------------------------------------------------------------------
    VMW_SYSLOG_FAMILIES = ["hostd_event", "shell_command"]

    @classmethod
    def format_vmw_syslog_log(cls, device: Node, family: str,
                              src_ip: str = "192.168.196.95",
                              dest_ip: str = "192.168.8.233",
                              host_ip: Optional[str] = None,
                              host_name: str = "localhost.localdomain",
                              datastore_path: str = "[Test]Test2/Test2.vmdk",
                              shell_command: str = "cat /etc/shadow",
                              user_name: str = "root",
                              status: str = "normal",
                              signature: str = "vmw-syslog",
                              action: str = "allowed") -> LogEntry:
        """ESXi Hostd event / shell audit line, pinned vmw-syslog grammar."""
        if family not in cls.VMW_SYSLOG_FAMILIES:
            raise ValueError(f"Unsupported vmw-syslog family: {family}")
        if host_ip is None:
            host_ip = dest_ip
        now = datetime.now(timezone.utc)
        iso = _iso_ms(now)
        sys_ts = _rfc3164_syslog_ts(now)
        pid = int(_reg("vmw|pid"), 16) % 900000 + 260000
        if family == "hostd_event":
            event_no = int(_reg("vmw|evno"), 16) % 900 + 100
            body = ("[Originator@6876 sub=Vimsvc.ha-eventmgr] "
                    "Event %d : File download from path '%s' was initiated "
                    "from 'govc/0.50.0@%s' and completed with status ''"
                    % (event_no, datastore_path, src_ip))
            proc = "Hostd"
        else:
            body = "[%s]: %s" % (user_name, shell_command)
            proc = "shell"
        raw = "%s %s %s %s %s[%d]: %s" % (
            sys_ts, host_ip, iso, host_name, proc, pid, body)
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=host_ip,
            protocol="TCP", duration="0ms", action=action, signature=signature,
            status=status, raw_log=raw, node_type=device.type.value,
            node_id=device.id, vendor="vmware_nsx",
            sourcetype=SOURCETYPE_VMW_SYSLOG)

    # ------------------------------------------------------------------
    # Cisco Cloud Security (Secure Firewall Cloud / DNS / Web proxy, CSV)
    # ------------------------------------------------------------------
    CSL_FIREWALL_FAMILIES = ["conn_c2s", "conn_s2c_icmp"]
    CSL_DNS_FAMILIES = ["dns_query"]
    CSL_PROXY_FAMILIES = ["proxy_http"]

    @staticmethod
    def _csl_ts(now: datetime) -> str:
        return now.strftime("%Y-%m-%d %H:%M:%S")

    @classmethod
    def format_cisco_cloud_security_firewall_log(
            cls, device: Node, family: str,
            src_ip: str, dest_ip: str, dest_port: int = 3389,
            user_name: str = "Joe Kehoe (joe.kehoe@d1.pseudoco.org)",
            user_group: str = "AD Users",
            zone: str = "prod_aws_us-west-2_1_0",
            action: str = "ALLOW", status: str = "normal",
            signature: str = "cisco-csl", action_status: str = "allowed",
            src_geo: str = "us") -> LogEntry:
        """Cisco Cloud Security firewall CSV row (C2S/TCP or S2C/ICMP layout)."""
        if family not in cls.CSL_FIREWALL_FAMILIES:
            raise ValueError(f"Unsupported csl firewall family: {family}")
        now = datetime.now(timezone.utc)
        ts = cls._csl_ts(now)
        epoch = int(now.timestamp())
        conn_id = "[15700%04d]" % (int(_reg("cfw|id"), 16) % 9999)
        sess = str(int(_reg("cfw|sess"), 16) % 900000 + 300000)
        if family == "conn_c2s":
            # Pinned 37-column C2S/TCP layout
            c = [
                ts, conn_id, user_name, user_group, "C2S", "6", "0", "", "",
                src_ip, str(dest_port), zone, sess, action, "", "[]",
                str(epoch), str(epoch + 26), "93", "82", "20847", "46067",
                _hex8("cfw|colhash"),
                "", "aws-us-west-2", "", "178937", "true", "1145001", "[]",
                "2", "[]", "[]", "8176184", "", "",
                _hex8("cfw|endhash"),
            ]
        else:
            # Pinned 37-column S2C/ICMP layout
            c = [
                ts, conn_id, user_name, user_group, "S2C", "1", "0",
                dest_ip, "", src_ip, "", zone, sess, action, "", "[]",
                str(epoch), str(epoch + 180), "0", "8", "0", "1504",
                "%s-1-%d-9640" % (_hex8("cfw|icmphash"), epoch),
                src_geo, "aws-us-west-2", "", "", "false", "", "[]",
                "1", "[]", "[]", "8176184", "", "",
                _hex8("cfw|endhash2"),
            ]
        raw = ",".join(_csv_q(v) for v in c)
        return LogEntry(
            timestamp=ts, device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
            protocol="ICMP" if family == "conn_s2c_icmp" else "TCP",
            duration="%dms" % (26 if family == "conn_c2s" else 180),
            action=action_status, signature=signature,
            status=status,
            raw_log=raw, node_type=device.type.value, node_id=device.id,
            vendor="cisco_asa", sourcetype=SOURCETYPE_CSL_FIREWALL)

    @classmethod
    def format_cisco_cloud_security_dns_log(
            cls, device: Node, family: str,
            src_ip: str, dest_ip: str,
            identity_host: str = "EC2AMAZ-J8G2CH1",
            domain: str = "www.proxysite.com.",
            categories: str = "Proxy/Anonymizer,Application",
            verdict: str = "Allowed",
            device_identity: str = "Anyconnect Roaming Client",
            req_type: str = "1 (A)", rcode: str = "NOERROR",
            status: str = "normal", signature: str = "cisco-csl-dns",
            action: str = "allowed") -> LogEntry:
        """Cisco Cloud Security DNS CSV row (16 columns, pinned layout)."""
        if family not in cls.CSL_DNS_FAMILIES:
            raise ValueError(f"Unsupported csl dns family: {family}")
        now = datetime.now(timezone.utc)
        ts = cls._csl_ts(now)
        c = [
            ts, identity_host, identity_host, src_ip, dest_ip, verdict,
            req_type, rcode, domain, categories, device_identity,
            device_identity, "", "139213", "", "8209150",
        ]
        raw = ",".join(_csv_q(v) for v in c)
        return LogEntry(
            timestamp=ts, device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
            protocol="UDP", duration="0ms", action=action, signature=signature,
            status=status, raw_log=raw, node_type=device.type.value,
            node_id=device.id, vendor="cisco_asa",
            sourcetype=SOURCETYPE_CSL_DNS)

    @classmethod
    def format_cisco_cloud_security_proxy_log(
            cls, device: Node, family: str,
            src_ip: str, dest_ip: str = "104.20.23.154",
            identity_host: str = "EC2AMAZ-J8G2CH1",
            user_agent: str = "gobuster/3.8.1",
            url: str = "http://example.com/css-3444",
            uri_suffix: str = "css-3444",
            http_status: str = "404", content_type: str = "text/html",
            categories: str = "Research/Reference,Reference",
            verdict: str = "ALLOWED",
            device_identity: str = "Anyconnect Roaming Client",
            status: str = "normal", signature: str = "cisco-csl-proxy",
            action: str = "allowed") -> LogEntry:
        """Cisco Cloud Security web proxy CSV row (49 columns, pinned layout)."""
        if family not in cls.CSL_PROXY_FAMILIES:
            raise ValueError(f"Unsupported csl proxy family: {family}")
        now = datetime.now(timezone.utc)
        ts = cls._csl_ts(now)
        c = [
            ts, identity_host, src_ip, dest_ip, dest_ip, content_type,
            verdict, url, "", user_agent, http_status, "", "790", "528",
            _hex8("csl|bodyhash"), categories, "", "", "", "", "",
            device_identity, "", identity_host, device_identity, "GET",
            verdict, "", uri_suffix, "14303105", "139213", "", "", "", "",
            "", "", "", "", "", "mps-7b95df5757-wmc2v.sigprox",
            "PROD_AWS_US-EAST-2_1_0N", "false", "", "false", "false", "",
            "", "8209150",
        ]
        assert len(c) == 49
        raw = ",".join(_csv_q(v) for v in c)
        return LogEntry(
            timestamp=ts, device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
            protocol="TCP", duration="0ms", action=action, signature=signature,
            status=status, raw_log=raw, node_type=device.type.value,
            node_id=device.id, vendor="cisco_asa",
            sourcetype=SOURCETYPE_CSL_PROXY)

    # ------------------------------------------------------------------
    # Cisco Isovalent (Tetragon eBPF, JSON) - 3 catalog rows share the
    # engine method (dispatch identical family grammar, distinct rows).
    # ------------------------------------------------------------------
    ISOVALENT_FAMILIES = ["process_exec", "process_connect"]

    @classmethod
    def format_cisco_isovalent_log(
            cls, device: Node, family: str,
            src_ip: str, dest_ip: str = "169.254.169.254",
            dest_port: int = 80,
            binary: str = "/usr/bin/curl",
            arguments: str = "-sS -m 2 -H \"Metadata: true\" "
                             "http://169.254.169.254/metadata/"
                             "instance?api-version=2021-02-01",
            pod_namespace: str = "kube-system",
            pod_name: str = "meta-probe",
            pod_image: str = "docker.io/curlimages/curl:8.10.1",
            pod_labels: Optional[Dict[str, str]] = None,
            user_name: str = "curl_user",
            node_name: str = "ip-10-0-10-253.us-west-2.compute.internal",
            cluster_name: str = "remote-dev-cluster",
            status: str = "normal", signature: str = "cisco-isovalent",
            action: str = "allowed",
            sourcetype: Optional[str] = None) -> LogEntry:
        """Tetragon process_exec / process_connect record, pinned key order."""
        if family not in cls.ISOVALENT_FAMILIES:
            raise ValueError(f"Unsupported cisco isovalent family: {family}")
        if sourcetype is None:
            sourcetype = SOURCETYPE_ISOVALENT
        now = datetime.now(timezone.utc)
        exec_id = ("%s:%s:%s" % ("aXAtMTAtMC0xMC0yNTMudXMtd2VzdC0yLmNvbXB1dGU"
                                 ".aW50ZXJuYWw",
                                 "1%d" % (int(_reg("iso|exec"), 16) % 99999
                                          + 46627100000),
                                 int(_reg("iso|pid"), 16) % 8000000 + 1200000))
        parent_exec_id = ("%s:%s:%s" % ("aXAtMTAtMC0xMC0yNTMudXMtd2VzdC0yLmNvbXB1dGU"
                                        ".aW50ZXJuYWw",
                                        "1%d" % (int(_reg("iso|pexec"), 16)
                                                 % 99999 + 46627100000),
                                        int(_reg("iso|ppid"), 16) % 8000000
                                        + 1200000))
        container_id = (_hex8("iso|contid") + _hex8("iso|contid2")
                        + _hex8("iso|contid3"))[:32]
        pid = int(_reg("iso|pid"), 16) % 8000000 + 1200000
        # Pod with pinned key order (namespace/name/container/labels/workload)
        pod = {
            "namespace": pod_namespace,
            "name": pod_name,
            "container": {
                "id": "containerd://containerd%s" % container_id,
                "name": pod_name,
                "image": {
                    "id": "%s@sha256:%s" % (
                        pod_image.replace("docker.io/", "docker.io/"),
                        _hex8("iso|img") + _hex8("iso|img2") + _hex8("iso|img3")),
                    "name": pod_image,
                },
                "start_time": _iso_ms(now)[:-1] + "Z",
                "pid": 1,
                "security_context": {},
            },
            "pod_labels": pod_labels or {"run": pod_name},
            "workload": pod_name,
            "workload_kind": "Pod",
        }
        process = {
            "exec_id": exec_id,
            "pid": pid,
            "uid": 100,
            "cwd": "/home/%s" % user_name,
            "binary": binary,
            "arguments": arguments,
            "flags": ("execve inInitTree" if family == "process_exec"
                      else "execve clone inInitTree"),
            "start_time": _utc7(now),
            "auid": 4294967295,
            "pod": pod,
            "docker": container_id,
            "parent_exec_id": parent_exec_id,
            "tid": pid,
            "in_init_tree": True,
        }
        parent = {
            "exec_id": parent_exec_id,
            "pid": int(_reg("iso|ppid"), 16) % 8000000 + 1200000,
            "uid": 100,
            "cwd": "/home/%s" % user_name,
            "binary": "/entrypoint.sh",
            "arguments": "/entrypoint.sh %s" % binary,
            "flags": "execve clone inInitTree",
            "start_time": _utc7(now),
            "auid": 4294967295,
        }
        if family == "process_exec":
            branch = {
                "process": process,
                "parent": parent,
                "ancestors": [{"exec_id": parent_exec_id}],
            }
        else:
            branch = {
                "process": process,
                "parent": parent,
                "source_ip": src_ip,
                "source_port": int(_reg("iso|sport"), 16) % 50000 + 1024,
                "destination_ip": dest_ip,
                "destination_port": dest_port,
                "sock_cookie": "1844646261%d" % (int(_reg("iso|cookie"), 16)
                                                 % 899999999),
                "protocol": "TCP",
            }
        envelope = {"process_exec" if family == "process_exec"
                    else "process_connect": branch}
        envelope.update({
            "node_name": node_name,
            "time": _utc7(now),
            "cluster_name": cluster_name,
            "node_labels": {},
        })
        raw = json.dumps(envelope, separators=(",", ":"))
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
            protocol="TCP", duration="0ms", action=action, signature=signature,
            status=status, raw_log=raw, node_type=device.type.value,
            node_id=device.id, vendor="cisco_ios", sourcetype=sourcetype)

    # ------------------------------------------------------------------
    # AWS CloudTrail Lake (OCSF JSON) - complete pinned record
    # ------------------------------------------------------------------
    CLOUDTRAIL_LAKE_FAMILIES = ["ocsf_api_activity"]

    @classmethod
    def format_aws_cloudtrail_lake_log(
            cls, device: Node, family: str,
            src_ip: str, dest_ip: str,
            api_operation: str = "CreatePolicy",
            api_service: str = "iam.amazonaws.com",
            request_data: str = '{"policyName":"test"}',
            response_data: str = '{"policy":{}}',
            activity: str = "Create",
            user_arn: str = "arn:aws:sts::222222222222:assumed-role/"
                            "7d40dd7e11854f8/test@test.com",
            user_type: str = "AssumedRole",
            region: str = "us-east-1",
            account_id: str = "222222222222",
            user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                              " AppleWebKit/537.36 (KHTML, like Gecko)"
                              " Chrome/131.0.0.0 Safari/537.36",
            status: str = "normal", signature: str = "aws-cloudtrail-lake",
            action: str = "allowed") -> LogEntry:
        """CloudTrail Lake OCSF API Activity record, pinned key order."""
        if family not in cls.CLOUDTRAIL_LAKE_FAMILIES:
            raise ValueError(f"Unsupported cloudtrail lake family: {family}")
        now = datetime.now(timezone.utc)
        epoch_ms = int(now.timestamp()) * 1000
        uid_prefix = user_arn.split("/")[-1]
        raw = json.dumps({
            "metadata": {
                "product": {
                    "version": "1.10",
                    "name": "CloudTrail",
                    "vendor_name": "AWS",
                    "feature": {"name": "Management"},
                },
                "event_code": "AwsApiCall",
                "uid": _hex8("ctlake|meta") + "-" + _reg("ctlake|m2")[:4]
                       + "-4" + _reg("ctlake|m3")[:3] + "-"
                       + _hex8("ctlake|m4")[:4] + "-"
                       + _hex8("ctlake|m5")[:12],
                "profiles": "datetime",
                "version": "1.1.0",
            },
            "time": epoch_ms,
            "time_dt": epoch_ms,  # fixture quirk preserved: numeric time_dt
            "cloud": {"region": region, "provider": "AWS"},
            "api": {
                "response": {"error": "", "message": "",
                             "data": response_data},
                "operation": api_operation,
                "version": "",
                "service": {"name": api_service},
                "request": {"data": request_data,
                            "uid": _hex8("ctlake|req") + "-"
                                   + _reg("ctlake|r2")[:4] + "-4"
                                   + _reg("ctlake|r3")[:3] + "-"
                                   + _hex8("ctlake|r4")[:4] + "-"
                                   + _hex8("ctlake|r5")[:12]},
            },
            "dst_endpoint": {"svc_name": ""},
            "actor": {
                "user": {
                    "type": user_type,
                    "name": "",
                    "uid_alt": "%s:%s" % (_reg("ctlake|principal"),
                                          user_arn.split("/")[-1]),
                    "uid": user_arn,
                    "account": {"uid": account_id},
                    "credential_uid": "ASIAW3MD6V2A%s" % _hex8("ctlake|cred"),
                },
                "session": {
                    "created_time_dt": epoch_ms - 11429000,
                    "is_mfa": False,
                    "issuer": "arn:aws:iam::%s:role/aws-reserved/"
                              "sso.amazonaws.com/us-west-2/7d40dd7e11854f8"
                              % account_id,
                },
                "invoked_by": "",
                "idp": {"name": ""},
            },
            "http_request": {"user_agent": user_agent},
            "src_endpoint": {"uid": "", "ip": src_ip, "domain": ""},
            "session": {"uid": "", "uid_alt": "", "credential_uid": "",
                        "issuer": ""},
            "policy": {"uid": ""},
            "resources": None,
            "class_name": "API Activity",
            "class_uid": 6003,
            "category_name": "Application Activity",
            "category_uid": 6,
            "severity_id": 1,
            "severity": "Informational",
            "user": {"uid_alt": "", "uid": "", "name": ""},
            "activity_name": activity,
            "activity_id": 1 if activity == "Create" else 2,
            "type_uid": 600301 if activity == "Create" else 600302,
            "type_name": "API Activity: %s" % activity,
            "status": "Success",
            "is_mfa": False,
            "unmapped": {
                "userIdentity.sessionContext.sessionIssuer.type": "Role",
                "sessionCredentialFromConsole": "true",
                "tlsDetails.clientProvidedHostHeader": api_service,
                "userIdentity.sessionContext.sessionIssuer.userName":
                    uid_prefix,
                "userIdentity.sessionContext.sessionIssuer.principalId":
                    _hex8("ctlake|principal2"),
                "recipientAccountId": account_id,
                "readOnly": "false",
                "tlsDetails.tlsVersion": "TLSv1.3",
                "managementEvent": "true",
                "userIdentity.sessionContext.sessionIssuer.accountId":
                    account_id,
                "tlsDetails.cipherSuite": "TLS_AES_128_GCM_SHA256",
            },
            "accountid": "",
            "region": "",
            "asl_version": "",
            "observables": {
                "name": "src_endpoint.ip",
                "value": src_ip,
                "type": "IP Address",
                "type_id": 2,
            },
        }, separators=(",", ":"))
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
            protocol="TCP", duration="0ms", action=action, signature=signature,
            status=status, raw_log=raw, node_type=device.type.value,
            node_id=device.id, vendor="amazon_aws",
            sourcetype=SOURCETYPE_CLOUDTRAIL_LAKE)

    # ------------------------------------------------------------------
    # linux_secure (classic /var/log/secure)
    # ------------------------------------------------------------------
    LINUX_SECURE_FAMILIES = ["su_message", "pam_session", "sshd_message"]

    @classmethod
    def format_linux_secure_log(
            cls, device: Node, family: str,
            src_ip: str, dest_ip: str = "10.0.9.9",
            host_name: str = "snapubuntu",
            daemon: str = "su",
            user_their: str = "snapattack",
            user_us: str = "secadmin",
            tty: str = "pts/2",
            message: Optional[str] = None,
            status: str = "normal", signature: str = "linux-secure",
            action: str = "allowed") -> LogEntry:
        """Classic /var/log/secure syslog line (su evidenced, sshd documented)."""
        if family not in cls.LINUX_SECURE_FAMILIES:
            raise ValueError(f"Unsupported linux_secure family: {family}")
        now = datetime.now(timezone.utc)
        sys_ts = _rfc3164_syslog_ts(now)
        if message is not None:
            tail = message
        elif family == "su_message":
            tail = "su: (to %s) %s on %s" % (user_their, user_us, tty)
        elif family == "pam_session":
            tail = ("su: pam_unix(su:session): session opened for user %s"
                    "(uid=0) by (uid=1000)" % user_their)
        else:
            pid = int(_reg("ls|sshd"), 16) % 55000 + 1000
            port = int(_reg("ls|port"), 16) % 50000 + 1024
            if action == "blocked":
                tail = ("sshd[%d]: Failed password for invalid user deploy "
                        "from %s port %d ssh2" % (pid, src_ip, port))
            else:
                tail = ("sshd[%d]: Accepted password for %s from %s port %d "
                        "ssh2" % (pid, user_their, src_ip, port))
        raw = "%s %s %s: %s" % (sys_ts, host_name, daemon, tail)
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
            protocol="TCP", duration="0ms", action=action, signature=signature,
            status=status, raw_log=raw, node_type=device.type.value,
            node_id=device.id, vendor="linux_infrastructure",
            sourcetype=SOURCETYPE_LINUX_SECURE)

    # ------------------------------------------------------------------
    # IIS (W3C access + module listing)
    # ------------------------------------------------------------------
    IIS_FAMILIES = ["w3c_access", "module_backdoor_listing"]

    @classmethod
    def format_iis_log(
            cls, device: Node, family: str,
            src_ip: str, dest_ip: str,
            dest_port: int = 8530,
            method: str = "POST",
            uri_stem: str = "/ReportingWebService/ReportingWebService.asmx",
            uri_query: str = "-",
            http_status: int = 200,
            time_taken: int = 1119,
            module_name: str = "IIS_Backdo1",
            module_image: str = r"c:\\temp\\IIS-Backdoor.dll",
            status: str = "normal", signature: str = "iis-access",
            action: str = "allowed") -> LogEntry:
        """IIS W3C access line / backdoor module listing (pinned)."""
        if family not in cls.IIS_FAMILIES:
            raise ValueError(f"Unsupported iis family: {family}")
        now = datetime.now(timezone.utc)
        if family == "w3c_access":
            raw = "%s %s %s %s %s %d - %s - - %d 0 0 %d" % (
                now.strftime("%Y-%m-%d %H:%M:%S"), dest_ip,
                method, uri_stem, uri_query, dest_port,
                src_ip, http_status, time_taken)
        else:
            raw = "name=\"%s\"\nimage=\"%s\"" % (module_name, module_image)
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
            protocol="TCP", duration="%dms" % time_taken, action=action,
            signature=signature, status=status, raw_log=raw,
            node_type=device.type.value, node_id=device.id,
            vendor="microsoft_windows", sourcetype=SOURCETYPE_IIS)

    # ------------------------------------------------------------------
    # Zeek conn (JSON)
    # ------------------------------------------------------------------
    ZEEK_CONN_FAMILIES = ["conn"]

    @classmethod
    def format_zeek_conn_json_log(
            cls, device: Node, family: str,
            src_ip: str, dest_ip: str,
            dest_port: int = 21,
            service: str = "ftp",
            conn_state: str = "SF",
            history: str = "ShAdDFaf",
            orig_bytes: int = 26,
            resp_bytes: int = 97,
            status: str = "normal", signature: str = "zeek-conn",
            action: str = "allowed") -> LogEntry:
        """Zeek conn JSON record, pinned conn-log key order."""
        if family not in cls.ZEEK_CONN_FAMILIES:
            raise ValueError(f"Unsupported zeek conn family: {family}")
        now = datetime.now(timezone.utc)
        uid = (_hex8("zeek|uid")[:10].upper() + _reg("zeek|uid2")[:9].upper())
        raw = json.dumps({
            "ts": _utc7(now)[:-1] + "Z",
            "uid": uid,
            "id.orig_h": src_ip,
            "id.orig_p": int(_reg("zeek|op"), 16) % 50000 + 1024,
            "id.resp_h": dest_ip,
            "id.resp_p": dest_port,
            "proto": "tcp",
            "service": service,
            "duration": 20.390862941741943,
            "orig_bytes": orig_bytes,
            "resp_bytes": resp_bytes,
            "conn_state": conn_state,
            "local_orig": False,
            "local_resp": True,
            "missed_bytes": 0,
            "history": history,
            "orig_pkts": 7,
            "orig_ip_bytes": 402,
            "resp_pkts": 5,
            "resp_ip_bytes": 365,
        }, separators=(",", ":"))
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
            protocol="TCP", duration="20390ms", action=action,
            signature=signature, status=status, raw_log=raw,
            node_type=device.type.value, node_id=device.id,
            vendor="zeek", sourcetype=SOURCETYPE_ZEEK_CONN)

    # ------------------------------------------------------------------
    # MSExchange:Management (Windows event block + ECP access line)
    # ------------------------------------------------------------------
    MSEXCHANGE_FAMILIES = ["cmdlet_event", "ecp_client_access"]

    @classmethod
    def format_msexchange_log(
            cls, device: Node, family: str,
            src_ip: str, dest_ip: str = "10.3.10.6",
            computer_name: str = "win-dc-exch01.attackrange.local",
            cmdlet: str = "Search-Mailbox",
            cmdlet_params: str = "-Identity \"Administrator@attackrange.local\""
                                 " -SearchQuery \"Subject:backup\""
                                 " -DeleteContent \"True\"",
            record: int = 1897,
            uri_stem: str = "/ecp/ReportingWebService/",
            http_status: int = 302,
            status: str = "normal", signature: str = "msexchange-mgmt",
            action: str = "allowed") -> LogEntry:
        """MSExchange Management cmdlet event block / ECP access row."""
        if family not in cls.MSEXCHANGE_FAMILIES:
            raise ValueError(f"Unsupported msexchange family: {family}")
        now = datetime.now(timezone.utc)
        if family == "cmdlet_event":
            echo = now.strftime("%m/%d/%Y %I:%M:%S %p")
            raw = "\n".join([
                echo,
                "LogName=MSExchange Management",
                "EventCode=1",
                "EventType=4",
                "ComputerName=%s" % computer_name,
                "SourceName=MSExchange CmdletLogs",
                "Type=Information",
                "RecordNumber=%d" % record,
                "Keywords=Classic",
                "TaskCategory=General",
                "OpCode=None",
                "Message=Cmdlet suceeded. Cmdlet %s, parameters %s."
                % (cmdlet, cmdlet_params),  # 'suceeded' preserved from fixture
            ])
        else:
            cafe_req = (_hex8("msex|cafe")[:8] + "-" + _reg("msex|c2")[:4]
                        + "-" + _reg("msex|c3")[:4] + "-"
                        + _reg("msex|c4")[:4] + "-"
                        + _reg("msex|c5")[:12]).lower()
            raw = ("%s %s GET %s &CorrelationID=<empty>;&cafeReqId=%s;"
                   "&LogoffReason=NoCookiesGetOrE14AuthPost 443 - %s "
                   "AMProbe/Local/ClientAccess - %d 0 0 2"
                   % (now.strftime("%Y-%m-%d %H:%M:%S"), dest_ip, uri_stem,
                      cafe_req, src_ip, http_status))
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
            protocol="TCP",
            duration="0ms" if family == "cmdlet_event" else "2ms",
            action=action, signature=signature, status=status, raw_log=raw,
            node_type=device.type.value, node_id=device.id,
            vendor="microsoft_365", sourcetype=SOURCETYPE_MSEXCHANGE)

    # ------------------------------------------------------------------
    # Amazon CloudFront access logs (33-column tab-delimited)
    # ------------------------------------------------------------------
    CLOUDFRONT_FAMILIES = ["edge_access"]

    @classmethod
    def format_aws_cloudfront_log(
            cls, device: Node, family: str,
            src_ip: str, dest_ip: str,
            host: str = "dabwhjbmhqkmp.cloudfront.net",
            origin_host: str = "test-open-bucket-1739301225.com",
            method: str = "GET",
            uri_stem: str = "/endpoint/1a93b7ea-7af7-11eb-adb5-acde48001122/",
            http_status: int = 200,
            user_agent: str = "Mozilla/5.0%20(Windows%20NT%2010.0;%20Win64;%20"
                              "x64)%20AppleWebKit/537.36%20(KHTML,%20like%20"
                              "Gecko)%20Chrome/132.0.0.0%20Safari/537.36",
            referer: str = "https://test-open-bucket-1739301225.com/",
            edge: str = "NRT12-P4", bytes_sent: int = 17361,
            sc_content_type: str = "text/html",
            status: str = "normal", signature: str = "aws-cloudfront",
            action: str = "allowed") -> LogEntry:
        """CloudFront access log row, pinned 33-column tab-delimited layout."""
        if family not in cls.CLOUDFRONT_FAMILIES:
            raise ValueError(f"Unsupported cloudfront family: {family}")
        now = datetime.now(timezone.utc)
        edge_req = _hex8("cf|req1") + _reg("cf|r2")[:14].upper()
        c = [
            now.strftime("%Y-%m-%d"), now.strftime("%H:%M:%S"), edge,
            str(bytes_sent), src_ip, method, host, uri_stem, str(http_status),
            referer, user_agent, "-", "-", "Hit", edge_req, origin_host,
            "https", "4704", "0.001", dest_ip, "TLSv1.3",
            "TLS_AES_128_GCM_SHA256", "Hit", "HTTP/1.1", "-", "-", "59766",
            "0.001", "Hit", sc_content_type, "-", "-", "-",
        ]
        assert len(c) == 33
        raw = "\t".join(c)
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
            protocol="TCP", duration="2ms", action=action, signature=signature,
            status=status, raw_log=raw, node_type=device.type.value,
            node_id=device.id, vendor="amazon_aws",
            sourcetype=SOURCETYPE_CLOUDFRONT)

    # ------------------------------------------------------------------
    # M365 message traces (reporting + Graph shapes)
    # ------------------------------------------------------------------
    O365_MESSAGETRACE_FAMILIES = ["message_trace"]
    O365_GRAPH_MESSAGETRACE_FAMILIES = ["graph_message_trace"]

    @classmethod
    def format_o365_messagetrace_log(
            cls, device: Node, family: str,
            src_ip: str, dest_ip: str,
            recipient: str = "victim_1@attack_range.lan",
            sender: str = "Password@attack_range.lan",
            message_id: str = "<beee425e-de47-490c-aae9-dae74de48442@"
                              "mailserver2001.attack_range.lan>",
            subject: str = "Password Manager",
            msg_status: str = "Delivered",
            org: str = "attackrange.onmicrosoft.com",
            size: int = 30869,
            status: str = "normal", signature: str = "o365-messagetrace",
            action: str = "allowed") -> LogEntry:
        """O365 reporting message trace JSON row, pinned key order."""
        if family not in cls.O365_MESSAGETRACE_FAMILIES:
            raise ValueError(f"Unsupported o365 messagetrace family: {family}")
        now = datetime.now(timezone.utc)
        raw = json.dumps({
            "Organization": org,
            "MessageId": message_id,
            "Received": now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3],
            "SenderAddress": sender,
            "RecipientAddress": recipient,
            "Subject": subject,
            "Status": msg_status,
            "ToIP": dest_ip,
            "FromIP": src_ip,
            "Size": size,
            "MessageTraceId": _hex8("mt|trace") + "-" + _reg("mt|t2")[:4]
                              + "-" + _reg("mt|t3")[:4] + "-"
                              + _reg("mt|t4")[:4] + "-"
                              + _hex8("mt|t5")[:12],
            "Index": int(_reg("mt|index"), 16) % 20000 + 10000,
        }, separators=(",", ":"))
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
            protocol="TCP", duration="0ms", action=action, signature=signature,
            status=status, raw_log=raw, node_type=device.type.value,
            node_id=device.id, vendor="microsoft_365",
            sourcetype=SOURCETYPE_O365_MESSAGETRACE)

    @classmethod
    def format_o365_graph_messagetrace_log(
            cls, device: Node, family: str,
            src_ip: str, dest_ip: str,
            recipient: str = "victim_1@attack_range.lan",
            sender: str = "Password@attack_range.lan",
            message_id: str = "<beee425e-de47-490c-aae9-dae74de48442@"
                              "mailserver2001.attack_range.lan>",
            subject: str = "Password Manager",
            msg_status: str = "Delivered",
            size: int = 30869,
            status: str = "normal", signature: str = "o365-graph-mt",
            action: str = "allowed") -> LogEntry:
        """O365 Graph message trace JSON row, pinned key order."""
        if family not in cls.O365_GRAPH_MESSAGETRACE_FAMILIES:
            raise ValueError(f"Unsupported o365 graph family: {family}")
        now = datetime.now(timezone.utc)
        raw = json.dumps({
            "id": "%s@%s" % (_hex8("gmt|id"), "attack_range.lan"),
            "messageId": message_id,
            "status": msg_status,
            "receivedDateTime": now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z",
            "recipientAddress": recipient,
            "senderAddress": sender,
            "subject": subject,
            "size": size,
            "fromIP": src_ip,
            "toIP": dest_ip,
        }, separators=(",", ":"))
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
            protocol="TCP", duration="0ms", action=action, signature=signature,
            status=status, raw_log=raw, node_type=device.type.value,
            node_id=device.id, vendor="microsoft_365",
            sourcetype=SOURCETYPE_O365_GRAPH_MESSAGETRACE)

    # ------------------------------------------------------------------
    # GSuite Gmail BigQuery export (JSON)
    # ------------------------------------------------------------------
    GMAIL_BIGQUERY_FAMILIES = ["gmail_message_event"]

    @classmethod
    def format_gmail_bigquery_log(
            cls, device: Node, family: str,
            src_ip: str, dest_ip: str,
            sender: str = "juan@internal_test_email.com",
            recipient: str = "juan@external_test_email.com",
            subject: str = "test email dev",
            payload_size: int = 43826,
            attachments: int = 0,
            source_service: str = "gmail-ui",
            action_type: int = 2,
            status: str = "normal", signature: str = "gmail-bigquery",
            action: str = "allowed") -> LogEntry:
        """Gmail BigQuery export JSON row, pinned key order."""
        if family not in cls.GMAIL_BIGQUERY_FAMILIES:
            raise ValueError(f"Unsupported gmail bigquery family: {family}")
        now = datetime.now(timezone.utc)
        raw = json.dumps({
            "action_type": action_type,
            "rfc2822_message_id": "<%s-QQQQQQ01@mail.gmail.com>"
                                  % _hex8("gmq|mid"),
            "subject": subject,
            "payload_size": payload_size,
            "source": {
                "address": sender,
                "service": source_service,
                "selector": "send",
                "from_header_address": sender,
                "from_header_displayname": "",
            },
            "destination": [{
                "address": recipient,
                "service": "gmail-ui",
                "selector": "",
                "smime_signature_verification_success": None,
                "smime_decryption_success": None,
                "smime_parsing_success": None,
                "smime_extraction_success": None,
                "rcpt_response": "2.0.0 OK",
            }],
            "flattened_destinations": recipient,
            "description": None,
            "connection_info": None,
            "is_spam": False,
            "is_policy_check_for_sender": True,
            "num_message_attachments": attachments,
            "message_set": None,
            "smtp_relay_error": None,
            "upload_error_category": None,
            "structured_policy_log_info": None,
            "triggered_rule_info": None,
            "flattened_triggered_rule_info": None,
            "smime_sign_message": False,
            "smime_encrypt_message": False,
            "smime_packaging_success": None,
            "smime_extraction_success": None,
            "smime_content_type": None,
            "link_domain": None,
            "attachment": None,
            "spam_info": None,
            "timestamp": _utc7(now),
        }, separators=(",", ":"))
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
            protocol="TCP", duration="0ms", action=action, signature=signature,
            status=status, raw_log=raw, node_type=device.type.value,
            node_id=device.id, vendor="google_workspace",
            sourcetype=SOURCETYPE_GMAIL_BIGQUERY)

    # ------------------------------------------------------------------
    # Zscaler NSS web (JSON) - keys 0..43 of the pinned record; keys 44+
    # were beyond the bounded evidence head and are omitted.
    # ------------------------------------------------------------------
    ZSCALER_NSS_FAMILIES = ["web_proxy_block", "web_proxy_allow"]

    @classmethod
    def format_zscaler_nss_web_log(
            cls, device: Node, family: str,
            src_ip: str, dest_ip: str,
            user: str = "jdoe@example.com",
            hostname: str = "example.com",
            url: str = "http://example.com/payload.exe",
            reason: str = "Malicious Bot",
            url_category: str = "Security Updates",
            app_name: str = "Web Proxy",
            dept: str = "Research and Development",
            location_name: str = "Head Office",
            file_type: str = "-",
            status: str = "normal", signature: str = "zscale-web",
            action: str = "blocked") -> LogEntry:
        """Zscaler NSS web JSON row, pinned key order (keys 0..43)."""
        if family not in cls.ZSCALER_NSS_FAMILIES:
            raise ValueError(f"Unsupported zscaler family: {family}")
        now = datetime.now(timezone.utc)
        blocked = family == "web_proxy_block"
        raw = json.dumps({
            "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
            "reason": reason if blocked else "",
            "event_id": _hex8("zs|event"),
            "protocol": "HTTPS",
            "action": "Blocked" if blocked else "Allowed",
            "zstenantid": "832736",
            "zstenantdomain": "example.com",
            "transactionsize": 30869,
            "responsesize": 24133,
            "requestsize": 6736,
            "urlcategory": url_category,
            "serverip": dest_ip,
            "clienttranstime": 79094,
            "requestmethod": "GET",
            "refererURL": "",
            "useragent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "product": app_name,
            "location": location_name,
            "ClientIP": src_ip,
            "status": "200",
            "user": user,
            "url": url,
            "vendor": "Zscaler NSS",
            "hostname": hostname,
            "clientpublicIP": src_ip,
            "threatcategory": reason if blocked else "None",
            "threatname": reason if blocked else "None",
            "filetype": file_type,
            "appname": app_name,
            "pagerisk": 0,
            "department": dept,
            "urlsupercategory": "Information Technology",
            "appclass": "Business Productivity",
            "dlpengine": "",
            "dlp_allow": False,
            "urlclass": "Business Use",
            "threatclass": reason if blocked else "None",
            "dlpdictionaries": "",
            "dlphitcount": 0,
            "fileclass": "",
            "servertranstime": 79094,
            "contenttype": "text/html",
            "unscannabletype": "",
            "deviceowner": "",
        }, separators=(",", ":"))
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
            protocol="TCP", duration="79ms", action=action, signature=signature,
            status=status, raw_log=raw, node_type=device.type.value,
            node_id=device.id, vendor="zscaler_zia",
            sourcetype=SOURCETYPE_ZSCALER_NSS_WEB)

    # ------------------------------------------------------------------
    # Cisco Secure Access RA-VPN OCSF events
    # ------------------------------------------------------------------
    RAVPN_FAMILIES = ["vpn_auth_reject", "vpn_auth_accept"]

    @classmethod
    def format_cisco_ravpn_log(
            cls, device: Node, family: str,
            src_ip: str, dest_ip: str,
            user_name: str = "vpn_user@example.com",
            device_name: str = "vpn-device",
            syslog_id: str = "ASA-6-113005",
            region: str = "us-east-2",
            org_id: str = "10002000",
            status: str = "normal", signature: str = "ravpn-auth",
            action: str = "blocked") -> LogEntry:
        """Cisco Secure Access RA-VPN OCSF AAA event (reject/accept)."""
        if family not in cls.RAVPN_FAMILIES:
            raise ValueError(f"Unsupported ravpn family: {family}")
        now = datetime.now(timezone.utc)
        descriptor = ("AAA_RESULT_REJECT" if family == "vpn_auth_reject"
                      else "AAA_RESULT_ACCEPT")
        raw = json.dumps({
            "activity_id": 5,
            "category_uid": 4,
            "cisco_asa": {
                "full_log_print_specifiers": '["","","",""]',
                "syslog_class": "INFORMATION",
                "syslog_descriptor": descriptor,
                "syslog_id": syslog_id,
                "syslog_id_with_version": syslog_id + "-0",
                "syslog_severity": "6",
            },
            "cisco_dtls_ipsec_tunnel": {},
            "cisco_endpoint_posture": {},
            "cisco_event_id": 1500000,
            "cisco_event_type": "AUTHENTICATION",
            "cisco_organization_id": org_id,
            "cisco_origin": "mgmt",
            "cisco_ravpn_metadata": {"device_name": device_name},
            "cisco_ravpn_session": {},
            "class_uid": 4002,
            "cloud": {"provider": "Cisco Secure Access", "region": region},
            "device": {"hostname": device_name},
            "metadata": {
                "product": {"version": "1.10", "name": "Secure Access",
                            "vendor_name": "Cisco"},
                "uid": _hex8("rv|meta"),
            },
            "policy": {},
            "severity_id": 2,
            "src_endpoint": {"ip": src_ip, "name": user_name},
            "time": int(now.timestamp()),
            "type_uid": 400205,
        }, separators=(",", ":"))
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
            protocol="UDP", duration="0ms", action=action, signature=signature,
            status=status if family == "vpn_auth_accept" else "breached",
            raw_log=raw, node_type=device.type.value, node_id=device.id,
            vendor="cisco_ios", sourcetype=SOURCETYPE_RAVPN)

    # ------------------------------------------------------------------
    # Cisco SD-WAN (Viptela) syslog + management access
    # ------------------------------------------------------------------
    SDWAN_SYSLOG_FAMILIES = ["vdaemon_control_change", "sshd_auth"]
    SDWAN_ACCESS_FAMILIES = ["mgmt_proxy_access"]

    @classmethod
    def format_cisco_sdwan_syslog_log(
            cls, device: Node, family: str,
            src_ip: str, dest_ip: str,
            host_name: str = "vSmart-01",
            peer_system_ip: str = "1.1.1.10",
            peer_public_ip: str = "192.168.3.20",
            new_state: str = "up", site_id: int = 1005,
            ssh_user: str = "admin", ssh_key: str = "RSA SHA256:KEY_1",
            status: str = "normal", signature: str = "viptela-syslog",
            action: str = "allowed") -> LogEntry:
        """Viptela syslog: vdaemon control change + sshd auth (pinned)."""
        if family not in cls.SDWAN_SYSLOG_FAMILIES:
            raise ValueError(f"Unsupported sdwan syslog family: {family}")
        now = datetime.now(timezone.utc)
        iso = now.strftime("%Y-%m-%dT%H:%M:%S") + "+00:00"
        if family == "vdaemon_control_change":
            raw = ("%s %s VDAEMON_0[2571]: %%Viptela-vSmart-VDAEMON_0-5-NTCE-"
                   "%d: control-connection-state-change new-state:%s "
                   "peer-type:vmanage peer-system-ip:%s public-ip:%s "
                   "public-port:12345 domain-id:1 site-id:%d"
                   % (iso, host_name, 1000001, new_state, peer_system_ip,
                      peer_public_ip, site_id))
        else:
            pid = int(_reg("sdw|sshd"), 16) % 9000 + 1000
            raw = ("%s %s <auth.info> sshd[%d]: Accepted publickey for %s "
                   "from %s port %d ssh2: %s"
                   % (iso, host_name, pid, ssh_user, src_ip,
                      int(_reg("sdw|port"), 16) % 50000 + 1024, ssh_key))
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
            protocol="TCP", duration="0ms", action=action, signature=signature,
            status=status, raw_log=raw, node_type=device.type.value,
            node_id=device.id, vendor="cisco_sdwan",
            sourcetype=SOURCETYPE_SDWAN_SYSLOG)

    @classmethod
    def format_cisco_sdwan_access_log(
            cls, device: Node, family: str,
            src_ip: str, dest_ip: str = "172.16.0.1",
            dest_svc: str = "172.16.0.1:8443",
            uri: str = "/reports/data/opt/data/containers/"
                       "config/data-collection-agent/.dca",
            method: str = "GET", http_status: int = 200,
            user_agent: str = "python-requests/2.31.0",
            upstream: str = "127.0.0.1:8080",
            mgmt_ip: str = "172.16.1.1",
            status: str = "normal", signature: str = "viptela-access",
            action: str = "allowed") -> LogEntry:
        """SD-WAN management access envoy row (pinned)."""
        if family not in cls.SDWAN_ACCESS_FAMILIES:
            raise ValueError(f"Unsupported sdwan access family: {family}")
        now = datetime.now(timezone.utc)
        iso = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
        trace = _hex8("sdwa|trace") + _hex8("sdwa|trace2") + _hex8("sdwa|t3")[:4]
        raw = ('[%s] "%s %s HTTP/1.1" %d - 0 32 4 - "%s" "%s" "%s" "%s" "%s"'
               % (iso, method, uri, http_status, mgmt_ip, user_agent, trace,
                  dest_svc, upstream))
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
            protocol="TCP", duration="4ms", action=action, signature=signature,
            status=status, raw_log=raw, node_type=device.type.value,
            node_id=device.id, vendor="cisco_sdwan",
            sourcetype=SOURCETYPE_SDWAN_ACCESS)

    # ------------------------------------------------------------------
    # Cisco IOS %SEC_LOGIN syslog
    # ------------------------------------------------------------------
    IOS_SYSLOG_FAMILIES = ["sec_login_success", "sec_login_failure"]

    @classmethod
    def format_cisco_ios_syslog_log(
            cls, device: Node, family: str,
            src_ip: str, dest_ip: str = "10.0.7.10",
            user_name: str = "admin", localport: int = 22,
            host_name: str = "ios-lab-rt01", reason: str = "BadPassword",
            status: str = "normal", signature: str = "ios-syslog",
            action: str = "allowed") -> LogEntry:
        """Cisco IOS %SEC_LOGIN-5/4 events, pinned grammar."""
        if family not in cls.IOS_SYSLOG_FAMILIES:
            raise ValueError(f"Unsupported cisco ios family: {family}")
        now = datetime.now(timezone.utc)
        ts = "%s: " % (now.strftime("%b %d %H:%M:%S.")
                       + ("%03d" % now.microsecond)[:3])
        close = now.strftime("%H:%M:%S UTC %a %b %d %Y")
        if family == "sec_login_success":
            raw = ("%s%%SEC_LOGIN-5-LOGIN_SUCCESS: Login Success "
                   "[user: %s] [Source: %s] [localport: %d] at %s"
                   % (ts, user_name, src_ip, localport, close))
        else:
            raw = ("%s%%SEC_LOGIN-4-LOGIN_FAILED: Login failed "
                   "[user: %s] [Source: %s] [localport: %d] "
                   "[Reason: Login Authentication Failed - %s] at %s"
                   % (ts, user_name, src_ip, localport, reason, close))
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
            protocol="TCP", duration="0ms",
            action="blocked" if family == "sec_login_failure" else action,
            signature=signature,
            status="breached" if family == "sec_login_failure" else status,
            raw_log=raw, node_type=device.type.value, node_id=device.id,
            vendor="cisco_ios", sourcetype=SOURCETYPE_CISCO_IOS)

    # ------------------------------------------------------------------
    # Cisco Meraki syslog (documented dashboard syslog grammar)
    # ------------------------------------------------------------------
    MERAKI_SYSLOG_FAMILIES = ["flows", "urls"]

    @classmethod
    def format_cisco_meraki_syslog_log(
            cls, device: Node, family: str,
            src_ip: str, dest_ip: str,
            mac: str = "aa:bb:cc:dd:ee:01",
            verdict: str = "allow",
            dport: int = 443, sport: int = 52620,
            pattern: str = "allow all",
            url: str = "http://example.com/",
            requests: int = 1,
            status: str = "normal", signature: str = "meraki-syslog",
            action: str = "allowed") -> LogEntry:
        """Meraki dashboard syslog flows/urls rows (documented grammar)."""
        if family not in cls.MERAKI_SYSLOG_FAMILIES:
            raise ValueError(f"Unsupported meraki family: {family}")
        now = datetime.now(timezone.utc)
        head = "%s %s " % (now.strftime("%b %d %H:%M:%S"), "mx-lab-01")
        if family == "flows":
            raw = "<%d>%s flows %s src=%s dst=%s mac=%s protocol=tcp " \
                  "sport=%d dport=%d patterns=1" % (
                      134, head, verdict, src_ip, dest_ip, mac, sport, dport)
        else:
            raw = "<%d>%s urls %s src=%s mac=%s pattern=%s url=%s " \
                  "requests=%d" % (138, head, verdict, src_ip, mac, pattern,
                                   url, requests)
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
            protocol="TCP", duration="0ms", action=action, signature=signature,
            status=status, raw_log=raw, node_type=device.type.value,
            node_id=device.id, vendor="cisco_meraki",
            sourcetype=SOURCETYPE_MERAKI_SYSLOG)

    # ------------------------------------------------------------------
    # ISC dhcpd (documented grammar)
    # ------------------------------------------------------------------
    DHCPD_FAMILIES = ["dhcpdiscover", "dhcprequest", "dhcpack", "dhcprelease"]

    @classmethod
    def format_dhcpd_log(
            cls, device: Node, family: str,
            src_ip: str, dest_ip: str = "10.0.9.9",
            mac: str = "aa:bb:cc:dd:ee:02",
            host_name: str = "dhcp-srv-01",
            interface: str = "eth0",
            lease_ip: str = "10.0.9.9",
            status: str = "normal", signature: str = "dhcpd",
            action: str = "allowed") -> LogEntry:
        """ISC dhcpd syslog lines (documented grammar)."""
        if family not in cls.DHCPD_FAMILIES:
            raise ValueError(f"Unsupported dhcpd family: {family}")
        now = datetime.now(timezone.utc)
        sys_ts = _rfc3164_syslog_ts(now)
        if family == "dhcpdiscover":
            tail = "DHCPDISCOVER from %s via %s" % (mac, interface)
        elif family == "dhcprequest":
            tail = ("DHCPREQUEST for %s from %s via %s"
                    % (lease_ip, mac, interface))
        elif family == "dhcpack":
            tail = ("DHCPACK on %s to %s (%s) via %s"
                    % (lease_ip, mac, host_name, interface))
        else:
            tail = ("DHCPRELEASE of %s from %s via %s"
                    % (lease_ip, mac, interface))
        raw = "%s %s dhcpd: %s" % (sys_ts, host_name, tail)
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
            protocol="UDP", duration="0ms", action=action, signature=signature,
            status=status, raw_log=raw, node_type=device.type.value,
            node_id=device.id, vendor="linux_infrastructure",
            sourcetype=SOURCETYPE_DHCPD)

    # ------------------------------------------------------------------
    # Google Cloud audit log (documented schema)
    # ------------------------------------------------------------------
    GCP_AUDIT_FAMILIES = ["admin_activity", "data_access"]

    @classmethod
    def format_gcp_audit_log(
            cls, device: Node, family: str,
            src_ip: str, dest_ip: str,
            project_id: str = "netops-prod",
            resource_type: str = "gce_instance",
            method_name: str = "v1.compute.instances.start",
            principal_email: str = "admin@netops-prod.iam.gserviceaccount.com",
            zone: str = "us-west1-b",
            instance: str = "inst-01",
            status: str = "normal", signature: str = "gcp-audit",
            action: str = "allowed") -> LogEntry:
        """GCP Cloud Audit Log record (documented JSON schema)."""
        if family not in cls.GCP_AUDIT_FAMILIES:
            raise ValueError(f"Unsupported gcp audit family: {family}")
        now = datetime.now(timezone.utc)
        log_name = ("projects/%s/logs/cloudaudit.googleapis.com%%2F%s"
                    % (project_id, "activity" if family == "admin_activity"
                       else "data_access"))
        raw = json.dumps({
            "insertId": _hex8("gcp|insert"),
            "logName": log_name,
            "receiveTimestamp": _utc7(now),
            "resource": {
                "type": resource_type,
                "labels": {"instance_id": instance, "project_id": project_id,
                           "zone": zone},
            },
            "protoPayload": {
                "@type": "type.googleapis.com/google.cloud.audit.AuditLog",
                "authenticationInfo": {"principalEmail": principal_email},
                "methodName": method_name,
                "request": {"@type": "type.googleapis.com/"
                                     "compute.instances.get"},
                "resourceName": ("projects/%s/zones/%s/instances/%s"
                                 % (project_id, zone, instance)),
                "requestMetadata": {
                    "callerIp": src_ip,
                    "callerSuppliedUserAgent": "google-cloud-sdk/468.0.0",
                },
                "serviceName": "compute.googleapis.com",
                "status": {"code": 0},
            },
            "severity": "NOTICE",
            "timestamp": _utc7(now),
        }, separators=(",", ":"))
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
            protocol="TCP", duration="0ms", action=action, signature=signature,
            status=status, raw_log=raw, node_type=device.type.value,
            node_id=device.id, vendor="google_cloud",
            sourcetype=SOURCETYPE_GCP_AUDIT)

    # ------------------------------------------------------------------
    # OpenTelemetry OTLP/JSON (documented schema)
    # ------------------------------------------------------------------
    OTEL_FAMILIES = ["log_record", "span_record"]

    @classmethod
    def format_opentelemetry_otlp_log(
            cls, device: Node, family: str,
            src_ip: str, dest_ip: str,
            service_name: str = "shop-api",
            body: str = "request completed",
            severity: str = "INFO",
            span_name: str = "GET /checkout",
            status: str = "normal", signature: str = "otel-otlp",
            action: str = "allowed") -> LogEntry:
        """OTLP/JSON resourceLogs / resourceSpans records (documented)."""
        if family not in cls.OTEL_FAMILIES:
            raise ValueError(f"Unsupported otel family: {family}")
        now = datetime.now(timezone.utc)
        resource = {
            "attributes": [
                {"key": "service.name",
                 "value": {"stringValue": service_name}},
                {"key": "host.name", "value": {"stringValue": device.name}},
                {"key": "deployment.environment",
                 "value": {"stringValue": "production"}},
            ],
        }
        if family == "log_record":
            record = {
                "resourceLogs": [{
                    "resource": resource,
                    "scopeLogs": [{
                        "scope": {"name": "netspout-otel", "version": "1.0"},
                        "logRecords": [{
                            "timeUnixNano": _nsec(now),
                            "severityText": severity,
                            "severityNumber": 9 if severity == "INFO" else 17,
                            "body": {"stringValue": body},
                            "traceId": _hex8("otel|trace") + _hex8("otel|t2"),
                            "spanId": _hex8("otel|span")[:16],
                            "attributes": [
                                {"key": "net.sock.peer.addr",
                                 "value": {"stringValue": src_ip}},
                            ],
                        }],
                    }],
                }],
            }
        else:
            record = {
                "resourceSpans": [{
                    "resource": resource,
                    "scopeSpans": [{
                        "spans": [{
                            "traceId": _hex8("otel|trace") + _hex8("otel|t2"),
                            "spanId": _hex8("otel|span")[:16],
                            "name": span_name,
                            "kind": "SPAN_KIND_SERVER",
                            "startTimeUnixNano": _nsec(now),
                            "endTimeUnixNano": _nsec(now, 2),
                            "attributes": [
                                {"key": "http.request.method",
                                 "value": {"stringValue": "GET"}},
                            ],
                            "status": {"code": "STATUS_CODE_OK"},
                        }],
                    }],
                }],
            }
        raw = json.dumps(record, separators=(",", ":"))
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
            protocol="TCP", duration="2ms", action=action, signature=signature,
            status=status, raw_log=raw, node_type=device.type.value,
            node_id=device.id, vendor="opentelemetry",
            sourcetype=SOURCETYPE_OTEL)

    # ------------------------------------------------------------------
    # XmlWinEventLog:System (documented System channel schema)
    # ------------------------------------------------------------------
    WINDOWS_SYSTEM_FAMILIES = ["system_service_event", "service_install_event"]

    @classmethod
    def format_windows_system_xml_log(
            cls, device: Node, family: str,
            src_ip: str, dest_ip: str,
            host_name: str = "WIN-DC-01",
            event_id: int = 6005,
            provider: str = "EventLog",
            message: str = "The Event log service was started.",
            channel: str = "System",
            user: str = "S-1-5-18",
            status: str = "normal", signature: str = "winsys-system",
            action: str = "allowed") -> LogEntry:
        """Windows System channel Event XML (documented base schema plus
        the pinned EventCode 7045 service-install record shape)."""
        if family not in cls.WINDOWS_SYSTEM_FAMILIES:
            raise ValueError(f"Unsupported windows system family: {family}")
        now = datetime.now(timezone.utc)
        if family == "service_install_event":
            service_name = message
            image_path = ("C:\\Users\\Administrator\\AppData\\Roaming\\"
                          "Bluetooth\\BluetoothService.exe")
            raw = (
                "<Event xmlns='http://schemas.microsoft.com/win/2004/08/"
                "events/event'><System><Provider Name='Service Control "
                "Manager' Guid='{555908d1-a6d7-4695-8e1e-26931d2012f4}' "
                "EventSourceName='Service Control Manager'/><EventID "
                "Qualifiers='16384'>7045</EventID><Version>0</Version>"
                "<Level>4</Level><Task>0</Task><Opcode>0</Opcode>"
                "<Keywords>0x8080000000000000</Keywords><TimeCreated "
                "SystemTime='%s'/><EventRecordID>%d</EventRecordID>"
                "<Correlation/><Execution ProcessID='%d' ThreadID='%d'/>"
                "<Channel>System</Channel>"
                "<Computer>%s</Computer><Security UserID='S-1-5-21-%s'/></"
                "System><EventData><Data Name='ServiceName'>%s</Data>"
                "<Data Name='ImagePath'>%s</Data>"
                "<Data Name='ServiceType'>user mode service</Data>"
                "<Data Name='StartType'>demand start</Data>"
                "<Data Name='AccountName'>LocalSystem</Data></EventData>"
                "</Event>"
            ) % (
                _utc7(now), int(_reg("winsys|svc"), 16) % 400000 + 30000,
                int(_reg("winsys|proc"), 16) % 3000 + 400,
                int(_reg("winsys|thr"), 16) % 8000 + 700,
                host_name, _hex8("winsys|sid")[:12], service_name, image_path,
            )
            return LogEntry(
                timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
                protocol="TCP", duration="0ms", action=action,
                signature=signature, status=status, raw_log=raw,
                node_type=device.type.value, node_id=device.id,
                vendor="microsoft_windows", sourcetype=SOURCETYPE_WINDOWS_SYSTEM)
        record_id = int(_reg("winsys|rec"), 16) % 90000 + 10000
        level = 4
        raw = (
            '<Event xmlns="http://schemas.microsoft.com/win/2004/08/events'
            '/event">'
            '<System>'
            '<Provider Name="%s"/>'
            '<EventID>%d</EventID>'
            '<Version>0</Version>'
            '<Level>%d</Level>'
            '<Task>0</Task>'
            '<Opcode>0</Opcode>'
            '<Keywords>0x80000000000000</Keywords>'
            '<TimeCreated SystemTime="%s"/>'
            '<EventRecordID>%d</EventRecordID>'
            '<Correlation/>'
            '<Execution ProcessID="%d" ThreadID="%d"/>'
            '<Channel>%s</Channel>'
            '<Computer>%s</Computer>'
            '<Security UserID="%s"/>'
            '</System>'
            '<EventData>'
            '<Data Name="param1">%s</Data>'
            '</EventData>'
            '</Event>'
        ) % (
            provider, event_id, level,
            _utc7(now), record_id,
            int(_reg("winsys|proc"), 16) % 5000 + 200,
            int(_reg("winsys|thr"), 16) % 9000 + 200,
            channel, host_name, user, message,
        )
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
            protocol="TCP", duration="0ms", action=action, signature=signature,
            status=status, raw_log=raw, node_type=device.type.value,
            node_id=device.id, vendor="microsoft_windows",
            sourcetype=SOURCETYPE_WINDOWS_SYSTEM)

    # ------------------------------------------------------------------
    # cisco:duo:administrator (existing row - generator gap fill)
    # ------------------------------------------------------------------
    DUO_FAMILIES = ["admin_action", "activity_event"]

    @classmethod
    def format_cisco_duo_admin_log(
            cls, device: Node, family: str,
            src_ip: str, dest_ip: str = "10.0.9.9",
            action_name: str = "policy_bulk_delete",
            description: Optional[Dict[str, Any]] = None,
            admin_key: str = "DEKXVXLFZBK5U0C9F1ST",
            admin_name: str = "Test Test",
            target_uname: str = "test2",
            browser: str = "Chrome",
            browser_version: str = "137.0.0.0",
            os_name: str = "Mac OS X",
            os_version: str = "10.15.7",
            location_country: str = "Germany",
            location_state: str = "Baden-Wurttemberg",
            status: str = "normal", signature: str = "duo-admin",
            action: str = "allowed") -> LogEntry:
        """Duo administrator log: pinned action / activity record shapes."""
        if family not in cls.DUO_FAMILIES:
            raise ValueError(f"Unsupported duo admin family: {family}")
        now = datetime.now(timezone.utc)
        # Duo ctime dialect: 'Thu Jul 10 07:24:12 2025'
        ctime = now.strftime("%a %b %d %H:%M:%S %Y")
        isotimestamp = now.strftime("%Y-%m-%dT%H:%M:%S+00:00")[:-1]
        isotimestamp = now.strftime("%Y-%m-%dT%H:%M:%S") + "+00:00"
        if family == "admin_action":
            desc = description if description is not None else {
                "admin_email": "test@test.com",
                "policies": "test2: PO9XV84OQJ5JXDBROM4O, "
                            "test3: PO6OTE8JJQBX2C19SK3X",
            }
            raw = json.dumps({
                "ctime": ctime,
                "action": action_name,
                "description": json.dumps(desc),
                "isotimestamp": isotimestamp,
                "object": None,
                "timestamp": int(now.timestamp()),
                "username": admin_name,
                "email": "test@test.com",
            }, separators=(",", ":"))
        else:
            raw = json.dumps({
                "ctime": ctime,
                "access_device": {
                    "browser": browser,
                    "browser_version": browser_version,
                    "ip": {"address": src_ip},
                    "location": {"city": "Unknown",
                                 "country": location_country,
                                 "state": location_state},
                    "os": os_name,
                    "os_version": os_version,
                },
                "action": {"details": None, "name": action_name},
                "activity_id": _hex8("duo|act") + "-"
                               + _reg("duo|a2")[:4] + "-4"
                               + _reg("duo|a3")[:3] + "-ef4"
                               + _reg("duo|a4")[:3] + "-"
                               + _hex8("duo|a5")[:12],
                "actor": {
                    "details": json.dumps({
                        "created": _iso_ms(now)[:-1],
                        "last_login": _iso_ms(now)[:-1],
                        "email": "test@test.com", "status": None,
                        "groups": None,
                    }),
                    "key": admin_key,
                    "name": admin_name,
                    "type": "admin",
                },
                "akey": _hex8("duo|akey")[:20],
                "application": None,
                "old_target": {
                    "details": json.dumps({
                        "uname": target_uname, "realname": "",
                        "status": "Active", "notes": "",
                        "email": "test@test.com",
                        "enable_auto_prompt": True,
                    }),
                    "key": _hex8("duo|otarget")[:20],
                    "name": target_uname,
                    "type": "user",
                },
            }, separators=(",", ":"))
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=dest_ip,
            protocol="TCP", duration="0ms", action=action, signature=signature,
            status=status, raw_log=raw, node_type=device.type.value,
            node_id=device.id, vendor="cisco_duo",
            sourcetype=SOURCETYPE_DUO_ADMIN)


WAVE3_SOURCE_SOURCETYPES = {
    SOURCETYPE_VMW_SYSLOG: "format_vmw_syslog_log",
    SOURCETYPE_CSL_FIREWALL: "format_cisco_cloud_security_firewall_log",
    SOURCETYPE_CSL_DNS: "format_cisco_cloud_security_dns_log",
    SOURCETYPE_CSL_PROXY: "format_cisco_cloud_security_proxy_log",
    SOURCETYPE_ISOVALENT: "format_cisco_isovalent_log",
    SOURCETYPE_ISOVALENT_PROCEXEC: "format_cisco_isovalent_log",
    SOURCETYPE_ISOVALENT_PROCCONNECT: "format_cisco_isovalent_log",
    SOURCETYPE_CLOUDTRAIL_LAKE: "format_aws_cloudtrail_lake_log",
    SOURCETYPE_LINUX_SECURE: "format_linux_secure_log",
    SOURCETYPE_IIS: "format_iis_log",
    SOURCETYPE_ZEEK_CONN: "format_zeek_conn_json_log",
    SOURCETYPE_MSEXCHANGE: "format_msexchange_log",
    SOURCETYPE_CLOUDFRONT: "format_aws_cloudfront_log",
    SOURCETYPE_O365_MESSAGETRACE: "format_o365_messagetrace_log",
    SOURCETYPE_O365_GRAPH_MESSAGETRACE: "format_o365_graph_messagetrace_log",
    SOURCETYPE_GMAIL_BIGQUERY: "format_gmail_bigquery_log",
    SOURCETYPE_ZSCALER_NSS_WEB: "format_zscaler_nss_web_log",
    SOURCETYPE_RAVPN: "format_cisco_ravpn_log",
    SOURCETYPE_SDWAN_SYSLOG: "format_cisco_sdwan_syslog_log",
    SOURCETYPE_SDWAN_ACCESS: "format_cisco_sdwan_access_log",
    SOURCETYPE_CISCO_IOS: "format_cisco_ios_syslog_log",
    SOURCETYPE_MERAKI_SYSLOG: "format_cisco_meraki_syslog_log",
    SOURCETYPE_DHCPD: "format_dhcpd_log",
    SOURCETYPE_GCP_AUDIT: "format_gcp_audit_log",
    SOURCETYPE_OTEL: "format_opentelemetry_otlp_log",
    SOURCETYPE_WINDOWS_SYSTEM: "format_windows_system_xml_log",
    SOURCETYPE_DUO_ADMIN: "format_cisco_duo_admin_log",
}
