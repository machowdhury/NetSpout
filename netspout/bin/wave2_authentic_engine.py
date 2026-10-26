# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/wave2_authentic_engine.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""
Wave 2 Authentic Source Expansion Engine
========================================
Second batch of genuinely supported vendor-native RAW families.
Every format is modelled on the pinned upstream datasets committed to
the RAW reference corpus (see catalog/raw_reference/ + provenance.json,
sha256 ledger) plus official vendor schemas:

  cisco:sfw:estreamer      -> pinned attack_data cisco_secure_firewall
                              react2shell + static_tundra (IntrusionEvent JSON)
  cisco:nvm:flowdata:v2    -> pinned nvzFlow_v11 record (short-key schema)
  ollama:server            -> pinned server logfmt stream (time=/level=/source=)
  mcp:jsonrpc              -> pinned research envelope (timestamp/host/source/
                              sourcetype/direction/method/id/jsonrpc/params/
                              result/error)
  gws:reports:login        -> pinned Reports login activity (kind/id/actor/
                              ipAddress/event{name,parameters})
  linux_messages_syslog    -> pinned /var/log/messages (syslog RFC 3164)
  crushftp:sessionlogs     -> pinned SESSION| pipe-delimited records
  azure:monitor:activity   -> pinned azure-activity.log record schema
                              (Administrative category)
  XmlWinEventLog:Microsoft-Windows-Windows Defender/Operational
                           -> official Microsoft Defender Operational schema
  XmlWinEventLog:Microsoft-Windows-NTLM/Operational
                           -> official Microsoft NTLM Operational schema
  aws:cloudwatchlogs:vpcflow -> official AWS VPC Flow Log default format
  kube:audit               -> official Kubernetes audit.k8s.io/v1 Event schema
  kube:container:falco     -> official Falco default text output + rule fields

Guarantees (enforced by tests)
  * RAW is pure vendor-native: no NetSpout correlation tails inside RAW
  * correlation metadata (netspout_run_id etc.) lives ONLY on LogEntry fields
  * deterministic identifiers (crc32-derived) for reproducible episodes
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

try:
    from netspout_core.models import LogEntry, Node
    from netspout_core.wave1_authentic_engine import (
        _reg,
        _hex8,
        _utc7,
        Wave1AuthenticEngine as _W1,
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


SOURCETYPE_CISCO_SFW_ESTREAMER = "cisco:sfw:estreamer"
SOURCETYPE_CISCO_NVM_V2 = "cisco:nvm:flowdata:v2"
SOURCETYPE_OLLAMA = "ollama:server"
SOURCETYPE_MCP = "mcp:jsonrpc"
SOURCETYPE_GWS_LOGIN = "gws:reports:login"
SOURCETYPE_AZURE_ACTIVITY = "azure:monitor:activity"
SOURCETYPE_AWS_VPCFLOW = "aws:cloudwatchlogs:vpcflow"
SOURCETYPE_LINUX_MESSAGES = "linux_messages_syslog"
SOURCETYPE_WINDOWS_DEFENDER = "XmlWinEventLog:Microsoft-Windows-Windows Defender/Operational"  # noqa
SOURCETYPE_WINDOWS_NTLM = "XmlWinEventLog:Microsoft-Windows-NTLM/Operational"
SOURCETYPE_KUBE_AUDIT = "kube:audit"
SOURCETYPE_FALCO = "kube:container:falco"
SOURCETYPE_CRUSHFTP = "crushftp:sessionlogs"


class Wave2AuthenticEngine:
    """Static vendor-native formatters for the Wave-2 source families."""

    # ------------------------------------------------------------------
    # Cisco Secure Firewall eStreamer (JSON) - existing catalog row
    # ------------------------------------------------------------------
    ESTREAMER_FAMILIES = ["intrusion_event"]

    @classmethod
    def format_cisco_sfw_estreamer_log(cls, device: Node, family: str,
                                       src_ip: str, dest_ip: str,
                                       dest_port: int = 51500,
                                       intrusion_message: str = "SERVER-OTHER Cisco Smart Install invalid init discovery message denial of service attempt",  # noqa
                                       classification: str = "A Network Trojan was Detected",
                                       priority: int = 1,
                                       impact: Any = "-", status: str = "normal",
                                       signature: str = "cisco-estreamer",
                                       action: str = "alerted") -> LogEntry:
        """Cisco SFR eStreamer IntrusionEvent, pinned react2shell/static_tundra field order."""
        if family not in cls.ESTREAMER_FAMILIES:
            raise ValueError(f"Unsupported cisco estreamer family: {family}")
        now = datetime.now(timezone.utc)
        epoch = int(now.timestamp())
        event_second = epoch + int(_reg("es|%d" % now.second), 16) % 59
        raw = json.dumps({
            "EventType": "IntrusionEvent",
            "EventSecond": event_second,
            "EventMicrosecond": int(now.microsecond),
            "DeviceUUID": "11bc8e94-f604-11ef-bcfe-eeb1de9c8a63",
            "InstanceID": 1,
            "FirstPacketSecond": event_second,
            "ConnectionID": int(_reg("connid|estreamer"), 16) % 9000 + 900,
            "InitiatorIP": src_ip,
            "ResponderIP": dest_ip,
            "InitiatorPort": 80,
            "ResponderPort": dest_port,
            "Protocol": "tcp",
            "IngressInterface": "outside",
            "EgressInterface": "inside",
            "IngressZone": "outside",
            "EgressZone": "inside",
            "PriorityID": priority,
            "GeneratorID": 1,
            "SignatureID": int(_reg("sig|estreamer"), 16) % 300000 + 10000,
            "SignatureRevision": 22,
            "Impact": impact,
            "IntrusionRuleMessage": intrusion_message,
            "Classification": classification,
            "WebApplication": "none",
        }, separators=(",", ":"))
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=dest_ip, protocol="TCP",
            duration="0ms", action=action, signature=signature, status=status,
            raw_log=raw, node_type=device.type.value, node_id=device.id,
            vendor="cisco_ios", sourcetype=SOURCETYPE_CISCO_SFW_ESTREAMER)

    # ------------------------------------------------------------------
    # Cisco Nexus NVM flowdata v2 (JSON nvzFlow_v11) - new catalog row
    # ------------------------------------------------------------------
    NVM_V2_FAMILIES = ["nvzflow_v11_record"]

    @classmethod
    def format_cisco_nvm_v2_log(cls, device: Node, family: str,
                                src_ip: str, dest_ip: str,
                                dest_port: int = 80,
                                dest_host: str = "www.example.com",
                                process_path: str = "/bin/zsh",
                                process_args: str = "-c zmodload zsh/net/tcp && ztcp www.example.com 80 && ztcp -c",  # noqa
                                parent_path: str = "/Users/ec2-user/safari-poc/safari",
                                status: str = "normal",
                                signature: str = "cisco-nvm-v2",
                                action: str = "allowed") -> LogEntry:
        """Cisco NVM v2 nvzFlow_v11 record with endpoint process identity context."""
        if family not in cls.NVM_V2_FAMILIES:
            raise ValueError(f"Unsupported cisco nvm v2 family: {family}")
        now = datetime.now(timezone.utc)
        epoch = int(now.timestamp())
        start_ms = epoch * 1000 + int(now.microsecond / 1000)
        stmt_time = now.strftime("%a %b %e %H:%M:%S %Y")
        raw = json.dumps({
            "fv": "nvzFlow_v11",
            "pr": "6",
            "sa": src_ip,
            "sp": "49304",
            "da": dest_ip,
            "dp": str(dest_port),
            "fd": "1",
            "fss": str(epoch),
            "fst": stmt_time,
            "fes": str(epoch),
            "fet": stmt_time,
            "hh": "",
            "hm": "",
            "ht": "",
            "udid": _hex8("nvm|udid") + _reg("nvm|udid2"),
            "liuid": "Mac mini\\ec2-user",
            "liuida": "Mac mini",
            "liuidp": "ec2-user",
            "liuat": "1",
            "pa": "Mac mini\\ec2-user",
            "paa": "Mac mini",
            "pap": "ec2-user",
            "puat": "1",
            "pn": "zsh",
            "ph": _hex8("nvm|ph"),
            "ppa": "Mac mini\\ec2-user",
            "ppuat": "1",
            "ppn": "safari",
            "pph": _hex8("nvm|pph"),
            "ibc": "0",
            "obc": "0",
            "ds": "Unknown",
            "dh": dest_host,
            "iid": "0",
            "mnl": "",
            "mhl": "",
            "fsms": str(start_ms),
            "fems": str(start_ms + 2),
            "pid": "25096",
            "ppath": process_path,
            "parg": process_args,
            "ppid": "25095",
            "pppath": parent_path,
            "aliul": "",
            "pil": "-1",
            "ppil": "-1",
            "fsg": "0",
            "puid": _hex8("nvm|puid"),
            "eveuuid": "00000000000000000000000000000000",
        }, separators=(",", ":"))
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=dest_ip, protocol="TCP",
            duration="2ms", action=action, signature=signature, status=status,
            raw_log=raw, node_type=device.type.value, node_id=device.id,
            vendor="cisco_ios", sourcetype=SOURCETYPE_CISCO_NVM_V2)

    # ------------------------------------------------------------------
    # Ollama server logfmt (pinned server.go/images.go/routes.go stream)
    # ------------------------------------------------------------------
    OLLAMA_FAMILIES = {
        "server_config": "routes.go:1475",
        "model_store": "images.go:518",
        "gpu_inventory": "gpu.go:217",
        "runner_wait": "server.go:1251",
    }

    @classmethod
    def format_ollama_server_log(cls, device: Node, family: str,
                                 src_ip: str = "127.0.0.1",
                                 model: str = "llama2",
                                 status: str = "normal",
                                 signature: str = "ollama",
                                 action: str = "allowed") -> LogEntry:
        """Ollama logfmt line (time=/level=/source=/msg=...), pinned shapes."""
        if family not in cls.OLLAMA_FAMILIES:
            raise ValueError(f"Unsupported ollama family: {family}")
        now = datetime.now(timezone.utc)
        ts = now.strftime("%Y-%m-%dT%H:%M:%S.") + "%03d" % (now.microsecond // 1000) \
            + now.strftime("%z")
        source = cls.OLLAMA_FAMILIES[family]
        if family == "server_config":
            core = ('msg="server config" env="map[OLLAMA_HOST:http://0.0.0.0:11434 '
                    'OLLAMA_CONTEXT_LENGTH:4096 OLLAMA_MAX_QUEUE:512 '
                    "OLLAMA_MODELS:/Users/research/.ollama/models "
                    'OLLAMA_NUM_PARALLEL:1 OLLAMA_FLASH_ATTENTION:false '
                    'OLLAMA_KEEP_ALIVE:5m0s OLLAMA_DEBUG:INFO]"')
        elif family == "model_store":
            core = 'msg="total blobs: 6"'
        elif family == "gpu_inventory":
            core = 'msg="looking for compatible GPUs"'
        else:
            core = 'msg="waiting for llama runner to start responding"'
        raw = f"time={ts} level=INFO source={source} {core}"
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip="127.0.0.1", protocol="HTTP",
            duration="0ms", action=action, signature=signature, status=status,
            raw_log=raw, node_type=device.type.value, node_id=device.id,
            vendor="ollama", sourcetype=SOURCETYPE_OLLAMA)

    # ------------------------------------------------------------------
    # Model Context Protocol JSON-RPC envelope (pinned research schema)
    # ------------------------------------------------------------------
    MCP_FAMILIES = ["server_lifecycle", "request", "response", "error"]

    @classmethod
    def format_mcp_jsonrpc_log(cls, device: Node, family: str,
                               src_ip: str,
                               mcp_server: str = "mcp_github_server",
                               host_name: str = "ar-win-1",
                               tool_name: str = "fs.read_file",
                               tool_args: Optional[Dict[str, Any]] = None,
                               status: str = "normal",
                               signature: str = "mcp-jsonrpc",
                               action: str = "allowed") -> LogEntry:
        """MCP JSON-RPC research envelope (direction/method/params/result/error)."""
        if family not in cls.MCP_FAMILIES:
            raise ValueError(f"Unsupported mcp family: {family}")
        now = datetime.now(timezone.utc)
        ts = now.strftime("%Y-%m-%dT%H:%M:%S.") + "%03d" % (now.microsecond // 1000) + "Z"
        body: Dict[str, Any] = {
            "timestamp": ts,
            "host": host_name,
            "source": mcp_server,
            "sourcetype": "mcp:jsonrpc",
        }
        req_id = int(_reg("mcprid"), 16) % 8000 + 40
        if family == "server_lifecycle":
            body.update({
                "direction": "server_start",
                "method": "server_lifecycle",
                "id": None, "jsonrpc": None,
                "params": {"action": "start",
                           "log_file": "C:\\ProgramData\\MCP\\logs\\mcp-github.log"},
                "result": None, "error": None,
            })
        elif family == "request":
            body.update({
                "direction": "request",
                "method": "tools/call",
                "id": req_id, "jsonrpc": "2.0",
                "params": {"name": tool_name,
                           "arguments": tool_args or {"path": "/etc/passwd"}},
                "result": None, "error": None,
            })
        elif family == "response":
            body.update({
                "direction": "response",
                "method": "tools/call",
                "id": req_id, "jsonrpc": "2.0", "params": None,
                "result": {"content": [{"type": "text", "text": "ok"}],
                           "isError": False},
                "error": None,
            })
        else:
            body.update({
                "direction": "response",
                "method": "tools/call",
                "id": req_id, "jsonrpc": "2.0", "params": None,
                "result": None,
                "error": {"code": -32001,
                          "message": "tool denied by policy allow-list"},
            })
        raw = json.dumps(body, separators=(",", ":"))
        return LogEntry(
            timestamp=ts,
            device_id=device.id, src_ip=src_ip, dest_ip="127.0.0.1", protocol="HTTP",
            duration="0ms", action=action, signature=signature, status=status,
            raw_log=raw, node_type=device.type.value, node_id=device.id,
            vendor="model_context_protocol", sourcetype=SOURCETYPE_MCP)

    # ------------------------------------------------------------------
    # Google Workspace login reports (pinned Reports schema)
    # ------------------------------------------------------------------
    GWS_LOGIN_FAMILIES = ["login_success", "login_failure", "login_2sv_challenge"]

    @classmethod
    def format_gws_login_log(cls, device: Node, family: str, src_ip: str,
                             actor_email: str = "user1@splunkresearch.com",
                             status: str = "normal",
                             signature: str = "gws-login",
                             action: str = "allowed") -> LogEntry:
        """Google Workspace Reports login activity, singular event object."""
        if family not in cls.GWS_LOGIN_FAMILIES:
            raise ValueError(f"Unsupported gws login family: {family}")
        now = datetime.now(timezone.utc)
        name = ("login_success" if family == "login_success"
                else "login_failure" if family == "login_failure"
                else "login_2sv_challenge")
        params: List[Dict[str, Any]] = [
            {"name": "login_type", "value": "google_password"},
        ]
        if family == "login_2sv_challenge":
            params.append({"name": "login_challenge_method",
                           "multiValue": ["password", "password", "password"]})
        elif family == "login_success":
            params.append({"name": "is_suspicious", "boolValue": False})
        else:
            params.append({"name": "login_failure_type", "boolValue": False})
        raw = json.dumps({
            "kind": "admin#reports#activity",
            "id": {"time": now.strftime("%Y-%m-%dT%H:%M:%S.") +
                        "%03d" % (now.microsecond // 1000) + "Z",
                   "uniqueQualifier": str(int(_reg("gwsuq"), 16) % 1000000000000),
                   "applicationName": "login",
                   "customerId": "C046r85ir"},
            "etag": "\"%s/NgAbD-Tz8hSD1vUJWw7NLiJ5SF4\"" % _reg("gwsetag"),
            "actor": {"email": actor_email,
                      "profileId": "112184723778873345717"},
            "ipAddress": src_ip,
            "event": {"type": "login", "name": name, "parameters": params},
        }, separators=(",", ":"))
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip="142.250.65.129",
            protocol="HTTPS",
            duration="0ms", action=action, signature=signature, status=status,
            raw_log=raw, node_type=device.type.value, node_id=device.id,
            vendor="google_workspace", sourcetype=SOURCETYPE_GWS_LOGIN)

    # ------------------------------------------------------------------
    # Azure Monitor Activity Log (pinned azure-activity.log schema)
    # ------------------------------------------------------------------
    AZURE_ACTIVITY_FAMILIES = ["admin_action", "alert_action", "service_health"]

    @classmethod
    def format_azure_activity_log(cls, device: Node, family: str, src_ip: str,
                                  subscription_id: str = "ad251139-d600-4f45-a8ba-9f6ca1e5a93d",  # noqa
                                  caller: str = "splunkresearch@splunkops.onmicrosoft.com",  # noqa
                                  operation_name: str = "Create or Update Virtual Machine",  # noqa
                                  status: str = "normal",
                                  signature: str = "azure-activity",
                                  action: str = "allowed") -> LogEntry:
        """Azure Activity Log record (Administrative / SecurityAlert / ServiceHealth)."""
        if family not in cls.AZURE_ACTIVITY_FAMILIES:
            raise ValueError(f"Unsupported azure activity family: {family}")
        now = datetime.now(timezone.utc)
        ts = now.strftime("%Y-%m-%dT%H:%M:%S.") + "%07d" % (now.microsecond * 10) + "Z"
        if family == "admin_action":
            body: Dict[str, Any] = {
                "time": ts,
                "resourceId": ("/subscriptions/%s/resourceGroups/netspout-rg/"
                               "providers/Microsoft.Compute/virtualMachines/"
                               "hunt-sandbox" % subscription_id),
                "category": "Administrative",
                "operationName": operation_name,
                "caller": caller,
                "resourceGroup": "netspout-rg",
                "httpRequest": {"clientIpAddress": src_ip, "method": "PUT"},
                "subscriptionId": subscription_id,
                "properties": {
                    "statusCode": "Created",
                    "serviceRequestId": _hex8("azreq") + "-" + _reg("azreq2"),
                    "message": "Microsoft.Compute/virtualMachines/write",
                },
                "tenantId": "ad251139-d600-4f45-a8ba-9f6ca1e5a93d",
            }
        elif family == "alert_action":
            body = {
                "time": ts,
                "resourceId": ("/subscriptions/%s/resourceGroups/netspout-rg/"
                               "providers/Microsoft.Compute/virtualMachines/"
                               "hunt-sandbox" % subscription_id),
                "category": "SecurityAlert",
                "operationName": "Create Security Alert",
                "properties": {
                    "alertDisplayName": "Suspicious PowerShell activity detected",
                    "severity": "High",
                    "alertUri": ("https://portal.azure.com/#blade/"
                                 "Microsoft_Azure_Security_Insights/AlertBlade/"
                                 + _reg("azalert")),
                    "userPrincipalName": caller,
                    "clientIpAddress": src_ip,
                },
                "tenantId": "ad251139-d600-4f45-a8ba-9f6ca1e5a93d",
            }
        else:
            body = {
                "time": ts,
                "resourceId": ("/subscriptions/%s/resourceGroups/netspout-rg/"
                               "providers/Microsoft.ServiceBus/namespaces/"
                               "netspout-bus" % subscription_id),
                "category": "ServiceHealth",
                "operationName": "Service Health Advisory",
                "properties": {
                    "incidentType": "ActionRequired",
                    "title": "Maintenance advisory for the region",
                    "communication": "Azure service maintenance window scheduled",
                },
                "tenantId": "ad251139-d600-4f45-a8ba-9f6ca1e5a93d",
            }
        raw = json.dumps(body, separators=(",", ":"))
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip="52.224.147.160",
            protocol="HTTPS",
            duration="0ms", action=action, signature=signature, status=status,
            raw_log=raw, node_type=device.type.value, node_id=device.id,
            vendor="microsoft_azure", sourcetype=SOURCETYPE_AZURE_ACTIVITY)

    # ------------------------------------------------------------------
    # AWS VPC Flow Logs (official default format, space delimited)
    # ------------------------------------------------------------------
    VPCFLOW_FAMILIES = ["flow_accept", "flow_reject", "flow_skipdata"]

    @classmethod
    def format_aws_vpcflow_log(cls, device: Node, family: str, src_ip: str,
                               dest_ip: str, dest_port: int = 22,
                               eni: str = "eni-1235b8ca123456789",
                               status: str = "normal",
                               signature: str = "aws-vpcflow",
                               action: str = "allowed") -> LogEntry:
        """AWS VPC Flow Log default v2 layout (official AWS field order)."""
        if family not in cls.VPCFLOW_FAMILIES:
            raise ValueError(f"Unsupported vpcflow family: {family}")
        now = datetime.now(timezone.utc)
        epoch = int(now.timestamp())
        if family == "flow_skipdata":
            raw = "2 %d %s - SKIPDATA" % (epoch, eni)
        else:
            log_action = "ACCEPT" if family == "flow_accept" else "REJECT"
            packets = int(_reg("vpfp|%d" % epoch), 16) % 40 + 8
            raw = ("2 %d %s %s %s 49304 %d 6 %d %d %d %d %s OK" % (
                epoch, eni, src_ip, dest_ip, dest_port, packets,
                packets * 1300, epoch, epoch + 4, log_action))
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=dest_ip, protocol="TCP",
            duration="4ms", action=action, signature=signature, status=status,
            raw_log=raw, node_type=device.type.value, node_id=device.id,
            vendor="amazon_aws", sourcetype=SOURCETYPE_AWS_VPCFLOW)

    # ------------------------------------------------------------------
    # Linux /var/log/messages (RFC 3164 style, pinned kernel sample)
    # ------------------------------------------------------------------
    LINUX_MESSAGES_FAMILIES = ["kernel_message", "sshd_message", "sudo_message",
                               "service_message"]

    @classmethod
    def format_linux_messages_log(cls, device: Node, family: str, src_ip: str,
                                  host_name: Optional[str] = None,
                                  message: Optional[str] = None,
                                  status: str = "normal",
                                  signature: str = "linux-messages",
                                  action: str = "allowed") -> LogEntry:
        """Classic /var/log/messages line: 'Mon DD hh:mm:ss host tag: msg'."""
        if family not in cls.LINUX_MESSAGES_FAMILIES:
            raise ValueError(f"Unsupported linux messages family: {family}")
        now = datetime.now(timezone.utc)
        host = host_name or (device.name or device.id)
        ts = "%s %2d %02d:%02d:%02d" % (now.strftime("%b"), now.day,
                                        now.hour, now.minute, now.second)
        if family == "kernel_message":
            tag = "kernel"
            body = message or ("[  %d.%06d] BOND: bond0: link status definitely "
                               "down for interface ens192, disabling it" % (
                                   int(_reg("lmbt"), 16) % 900 + 10,
                                   int(_reg("lmbt2"), 16) % 1000000))
            raw = f"{ts} {host} {tag}: {body}"
        elif family == "sshd_message":
            tag = "sshd"
            body = message or ("Failed publickey for invalid user admin from %s "
                               "port 49872 ssh2: RSA SHA256:%s" % (
                                   src_ip, _reg("smsig")))
            raw = (f"{ts} {host} {tag}["
                   f"{int(_reg('smpid'), 16) % 90000 + 1000}]: {body}")
        elif family == "sudo_message":
            tag = "sudo"
            user = "ec2-user"
            body = (f"   {user} : TTY=pts/0 ; PWD=/home/{user} ; USER=root ; "
                    f"COMMAND=/bin/systemctl restart falco")
            raw = f"{ts} {host} {tag}: {body}"
        else:
            tag = "systemd"
            body = message or "Starting Daily apt upgrade and clean activities..."
            raw = f"{ts} {host} {tag}[1]: {body}"
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=device.ip_address,
            protocol="syslog", duration="0ms", action=action, signature=signature,
            status=status, raw_log=raw, node_type=device.type.value,
            node_id=device.id, vendor="linux_infrastructure",
            sourcetype=SOURCETYPE_LINUX_MESSAGES)

    # ------------------------------------------------------------------
    # Windows Defender Operational XML (Microsoft-documented schema)
    # ------------------------------------------------------------------
    DEFENDER_FAMILIES = {
        "detection": (1116, "Malware detected"),
        "remediation": (1117, "Malware remediation executed"),
        "config_change": (5007, "Configuration change"),
    }

    @classmethod
    def format_windows_defender_xml_log(cls, device: Node, family: str,
                                        host_name: str, src_ip: str,
                                        threat_name: str = "Trojan:Win32/Wacatac.B!ml",  # noqa
                                        user: str = "nt authority\\system",
                                        status: str = "breached",
                                        signature: str = "windows-defender",
                                        action: str = "alerted",
                                        protocol: str = "WinEvent") -> LogEntry:
        """Defender Operational Event element, Microsoft-documented EventData names."""
        if family not in cls.DEFENDER_FAMILIES:
            raise ValueError(f"Unsupported defender family: {family}")
        event_id, _label = cls.DEFENDER_FAMILIES[family]
        now = datetime.now(timezone.utc)
        host = host_name or (device.name or device.id)
        record = int(_reg("def|%s" % family), 16) % 900000 + 10000
        if family == "detection":
            data_pairs = [
                ("Detection ID", _reg("defid")),
                ("Detection Name", threat_name),
                ("Detection Type", "FastPath"),
                ("Initial Detection Time", _utc7(now)),
                ("Threat Category ID", "3"),
                ("Threat Category Name", "Software/Trojan"),
                ("Threat Identifier", threat_name),
                ("Severity ID", "4"),
                ("Severity Name", "Severe"),
                ("Process Name",
                 "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe"),
                ("User", user),
                ("Action ID", "9"),
                ("Action Name", "Clean,Quarantine"),
            ]
        elif family == "remediation":
            data_pairs = [
                ("Threat Identifier", threat_name),
                ("Remediation Success", "true"),
                ("Execution Time", "1.9"),
                ("User", user),
                ("Path", "C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\"),
                ("Detection ID", _reg("defid")),
            ]
        else:
            data_pairs = [
                ("Operating System Version", "10.0.19041.0"),
                ("Configuration change description",
                 "MAPS reporting turn on - from off to on"),
            ]
        raw = ("<Event xmlns='http://schemas.microsoft.com/win/2004/08/events/event'>"
               + _W1._xml_system("Microsoft-Windows-Windows Defender", event_id,
                                 host, now, record, "1824", "2148",
                                 "Microsoft-Windows-Windows Defender/Operational",
                                 "0x8000000000000000")
               + _W1._xml_event_data(data_pairs) + "</Event>")
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=host, protocol=protocol,
            duration="0ms", action=action, signature=signature, status=status,
            raw_log=raw, node_type=device.type.value, node_id=device.id,
            vendor="microsoft_windows", sourcetype=SOURCETYPE_WINDOWS_DEFENDER)

    # ------------------------------------------------------------------
    # Windows NTLM Operational XML (Microsoft-documented schema)
    # ------------------------------------------------------------------
    NTLM_FAMILIES = {
        "client_request": (8001, "NTLM client logon request"),
        "credential_negotiate": (8002, "NTLM credentials used"),
        "audit_block": (8004, "NTLM blocked"),
    }

    @classmethod
    def format_windows_ntlm_xml_log(cls, device: Node, family: str,
                                    host_name: str, src_ip: str,
                                    user_name: str = "CORP\\netops-admin",
                                    process_name: str = "C:\\Windows\\System32\\cmd.exe",  # noqa
                                    status: str = "normal",
                                    signature: str = "windows-ntlm",
                                    action: str = "allowed",
                                    protocol: str = "WinEvent") -> LogEntry:
        """NTLM channel Event element (8001/8002/8004 documented)."""
        if family not in cls.NTLM_FAMILIES:
            raise ValueError(f"Unsupported ntlm family: {family}")
        event_id, _label = cls.NTLM_FAMILIES[family]
        now = datetime.now(timezone.utc)
        host = host_name or (device.name or device.id)
        record = int(_reg("ntlm|%s" % family), 16) % 900000 + 10000
        common = [("ProcessName", process_name),
                  ("ProcessId", "7400"),
                  ("ComputerName", host),
                  ("User", user_name.split("\\")[-1]),
                  ("DomainName", user_name.split("\\")[0])]
        if family == "client_request":
            data_pairs = common + [
                ("RequestId", _reg("ntlmid")),
                ("NegotiateFlags", "0xA1F5AB07"),
                ("TargetSpn", "TERMSRV/%s" % host),
                ("Realm", "-"),
                ("Held-GUIDs", "-"),
            ]
        elif family == "credential_negotiate":
            data_pairs = common + [
                ("StorageCredential", user_name),
                ("RequestId", _reg("ntlmid")),
                ("NegotiateFlags", "0xE288A233"),
                ("Realm", "CORP"),
                ("Held-GUIDs", "-"),
            ]
        else:
            data_pairs = common + [
                ("TargetSpn", "HTTP/%s.corp.local" % host),
                ("RequestId", _reg("ntlmid")),
                ("NegotiateFlags", "0xA1F5AB07"),
                ("Realm", "CORP"),
                ("Held-GUIDs", "-"),
                ("PolicyId", _reg("ntlm pol")),
                ("DenyReason", "PolicyDeny"),
            ]
        raw = ("<Event xmlns='http://schemas.microsoft.com/win/2004/08/events/event'>"
               + _W1._xml_system("Microsoft-Windows-NTLM", event_id, host, now,
                                 record, "620", "3124",
                                 "Microsoft-Windows-NTLM/Operational",
                                 "0x8020000000000000")
               + _W1._xml_event_data(data_pairs) + "</Event>")
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=host, protocol=protocol,
            duration="0ms", action=action, signature=signature, status=status,
            raw_log=raw, node_type=device.type.value, node_id=device.id,
            vendor="microsoft_windows", sourcetype=SOURCETYPE_WINDOWS_NTLM)

    # ------------------------------------------------------------------
    # Kubernetes audit (official audit.k8s.io/v1 Event schema)
    # ------------------------------------------------------------------
    KUBE_AUDIT_FAMILIES = {
        "pod_create": ("/api/v1/namespaces/netspout-prod/pods", "create", 201,
                       "pods", "nginx-web-6b7fc9f578-x8klp"),
        "secret_read": ("/api/v1/namespaces/netspout-prod/secrets/db-credentials",
                        "get", 200, "secrets", "db-credentials"),
        "exec_into_pod": ("/api/v1/namespaces/netspout-prod/pods/"
                          "nginx-web-6b7fc9f578-x8klp/exec",
                          "create", 200, "pods/exec",
                          "nginx-web-6b7fc9f578-x8klp"),
    }

    @classmethod
    def format_kube_audit_log(cls, device: Node, family: str, src_ip: str,
                              user_name: str = "kubernetes-admin",
                              status: str = "normal",
                              signature: str = "kube-audit",
                              action: str = "allowed") -> LogEntry:
        """audit.k8s.io/v1 JSON event (stage ResponseComplete)."""
        if family not in cls.KUBE_AUDIT_FAMILIES:
            raise ValueError(f"Unsupported kube audit family: {family}")
        request_uri, verb, code, resource, name = cls.KUBE_AUDIT_FAMILIES[family]
        now = datetime.now(timezone.utc)
        stage_ts = (now.strftime("%Y-%m-%dT%H:%M:%S.") +
                    "%04d" % (now.microsecond // 100) + "Z")
        raw = json.dumps({
            "kind": "Event",
            "apiVersion": "audit.k8s.io/v1",
            "level": "RequestResponse",
            "auditID": "%s-%s-%s-%s-%s" % (_hex8("ka1"), _hex8("ka2")[:4],
                                           "4" + _hex8("ka3")[:3],
                                           "9" + _hex8("ka4")[:3],
                                           _hex8("ka5")[:12]),
            "stage": "ResponseComplete",
            "requestURI": request_uri,
            "verb": verb,
            "user": {"username": user_name,
                     "groups": ["system:masters", "system:authenticated"]},
            "sourceIPs": [src_ip],
            "userAgent": "kubectl/v1.29.1 (linux/amd64) kubernetes/b20327d",
            "objectRef": {"resource": resource, "namespace": "netspout-prod",
                          "name": name, "apiVersion": "v1"},
            "responseStatus": {"metadata": {}, "code": code},
            "stageTimestamp": stage_ts,
        }, separators=(",", ":"))
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip="10.96.0.1", protocol="HTTPS",
            duration="0ms", action=action, signature=signature, status=status,
            raw_log=raw, node_type=device.type.value, node_id=device.id,
            vendor="kubernetes", sourcetype=SOURCETYPE_KUBE_AUDIT)

    # ------------------------------------------------------------------
    # Falco runtime events (default text output format)
    # ------------------------------------------------------------------
    FALCO_FAMILIES = [
        "terminal_shell",
        "sensitive_file_read",
        "write_below_etc",
    ]

    @classmethod
    def format_falco_log(cls, device: Node, family: str, src_ip: str,
                         container_id: str = "a4e1c9f2b7d1",
                         status: str = "breached",
                         signature: str = "falco",
                         action: str = "alerted") -> LogEntry:
        """Falco default output: `<HH:MM:SS.frac>: <severity> <rule>: <fields>`."""
        if family not in cls.FALCO_FAMILIES:
            raise ValueError(f"Unsupported falco family: {family}")
        now = datetime.now(timezone.utc)
        ts = now.strftime("%H:%M:%S.") + "%09d" % (now.microsecond * 1000)
        if family == "terminal_shell":
            body = ("Terminal shell in container (user=root user_loginuid=0 "
                    "event_type=execve user_uid=0 pid=%d parent_pid=%d "
                    "proc_exepath=/bin/bash parent_exepath=runc "
                    "evt_type=execve user_name=root command=bash "
                    "terminal=34819 evt-res=success res=success "
                    "container_id=%s container_image_repository=ubuntu "
                    "container_image_tag=latest k8s_ns=netspout-prod) " % (
                        int(_reg("fcp"), 16) % 60000 + 4000,
                        int(_reg("fpp"), 16) % 6000 + 900,
                        container_id))
            severity = "Critical"
        elif family == "sensitive_file_read":
            body = ("Sensitive file opened for reading for read/write by trusted "
                    "container (user=root user_loginuid=0 command=cat /etc/shadow "
                    "file=/etc/shadow parent_proc_name=bash user_uid=0 "
                    "container_id=%s container_image_repository=ubuntu "
                    "k8s_ns=netspout-prod)" % container_id)
            severity = "Warning"
        else:
            body = ("Write below etc (evt_type=openat user=root user_uid=0 "
                    "user_gid=0 process=bash pid=%d parent_pid=%d "
                    "proc_name=touch proc_exepath=/bin/touch category=change "
                    "filename=/etc/passwd parent=sh parent_exepath=/bin/sh "
                    "container_id=%s container_image_repository=ubuntu "
                    "k8s_ns=netspout-prod)" % (
                        int(_reg("fwp"), 16) % 60000 + 4000,
                        int(_reg("fpp2"), 16) % 6000 + 900,
                        container_id))
            severity = "Warning"
        raw = f"{ts}: {severity} {body}"
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip="127.0.0.1",
            protocol="syscall",
            duration="0ms", action=action, signature=signature, status=status,
            raw_log=raw, node_type=device.type.value, node_id=device.id,
            vendor="kubernetes", sourcetype=SOURCETYPE_FALCO)

    # ------------------------------------------------------------------
    # CrushFTP session logs (pinned SESSION pipe-delimited schema)
    # ------------------------------------------------------------------
    CRUSHFTP_FAMILIES = ["session_command_read", "session_login",
                         "session_transfer"]

    @classmethod
    def format_crushftp_log(cls, device: Node, family: str, src_ip: str,
                            user: str = "anonymous",
                            path: str = "/WebInterface/function",
                            status: str = "normal",
                            signature: str = "crushftp",
                            action: str = "allowed") -> LogEntry:
        """CrushFTP session_logs record: SESSION|MM/DD/YYYY hh:mm:ss.mmm|..."""
        if family not in cls.CRUSHFTP_FAMILIES:
            raise ValueError(f"Unsupported crushftp family: {family}")
        now = datetime.now(timezone.utc)
        ts = now.strftime("%m/%d/%Y %H:%M:%S.") + "%03d" % (now.microsecond // 1000)
        slot = int(_reg("cfs"), 16) % 900 + 100
        conn = int(_reg("cfc"), 16) % 40000 + 9000
        token = _reg("cft")
        session_head = "[HTTPS:%d_%d_%s:%s:%s]" % (slot, conn, token, user, src_ip)
        if family == "session_command_read":
            raw = ("%s|%s|%s READ: *POST %s/?c2f=%s&command=zip"
                   "&path=%%3CINCLUDE%%3EC:/Users/Administrator/Downloads/"
                   "CrushFTP10/CrushFTP10/sessions.obj%%3C/INCLUDE%%3E"
                   "&names=/a HTTP/1.1*" % (
                       "SESSION", ts, session_head, path, _reg("cfc2f")))
        elif family == "session_login":
            raw = "%s|%s|%s LOGIN: *%s*" % ("SESSION", ts, session_head, user)
        else:
            raw = ("%s|%s|%s READ: *GET /uploads/invoice_q1_reconciliation.csv "
                   "HTTP/1.1*" % ("SESSION", ts, session_head))
        return LogEntry(
            timestamp=now.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            device_id=device.id, src_ip=src_ip, dest_ip=device.ip_address,
            protocol="HTTPS", duration="0ms", action=action, signature=signature,
            status=status, raw_log=raw, node_type=device.type.value,
            node_id=device.id, vendor="crushftp", sourcetype=SOURCETYPE_CRUSHFTP)


# Registry consumed by SplunkLogEngine delegation (mirrors wave-1 pattern)
WAVE2_SOURCE_SOURCETYPES = {
    SOURCETYPE_CISCO_SFW_ESTREAMER: "format_cisco_sfw_estreamer_log",
    SOURCETYPE_CISCO_NVM_V2: "format_cisco_nvm_v2_log",
    SOURCETYPE_OLLAMA: "format_ollama_server_log",
    SOURCETYPE_MCP: "format_mcp_jsonrpc_log",
    SOURCETYPE_GWS_LOGIN: "format_gws_login_log",
    SOURCETYPE_AZURE_ACTIVITY: "format_azure_activity_log",
    SOURCETYPE_AWS_VPCFLOW: "format_aws_vpcflow_log",
    SOURCETYPE_LINUX_MESSAGES: "format_linux_messages_log",
    SOURCETYPE_WINDOWS_DEFENDER: "format_windows_defender_xml_log",
    SOURCETYPE_WINDOWS_NTLM: "format_windows_ntlm_xml_log",
    SOURCETYPE_KUBE_AUDIT: "format_kube_audit_log",
    SOURCETYPE_FALCO: "format_falco_log",
    SOURCETYPE_CRUSHFTP: "format_crushftp_log",
}
