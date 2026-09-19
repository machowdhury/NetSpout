"""
Scenario Runner & Stateful Simulation Engine
Evaluates dynamic network topologies against 4 security scenarios:
- Scenario A: Normal Traffic (Balanced HTTP requests)
- Scenario B: DDoS Attack (TCP SYN Flood / Rate Exceeded)
- Scenario C: SQL Injection (OWASP SQLi payload hitting Database)
- Scenario D: Ransomware / Lateral Movement (Internal SMB/RDP propagation)
Dynamically adapts log outcomes (action=blocked vs action=allowed/status=breached)
based on active canvas wiring and node presence.
"""

import random
from typing import List, Dict, Optional, Tuple
from app.models import TopologyState, Node, NodeType, ScenarioType, LogEntry, NodePowerState
from app.graph_engine import TopologyGraph
from app.log_engine import SplunkLogEngine
from app.telemetry_dispatcher import dispatcher


class ScenarioRunner:
    def __init__(self):
        self.round_robin_counter = 0
        self.lateral_step = 0
        self.telemetry_tick = 0
        self.malicious_ips = [
            "198.51.100.42", "203.0.113.88", "198.51.100.199",
            "45.33.32.156", "185.220.101.5", "194.26.29.112",
            "103.251.167.20", "91.240.118.172"
        ]
        self.normal_client_ips = [
            "172.16.50.14", "172.16.50.28", "172.16.50.103",
            "192.168.1.45", "192.168.1.88", "192.168.2.110"
        ]
        self.sqli_payloads = [
            ("GET /login.php?user=admin' OR '1'='1 --", "SELECT * FROM users WHERE user='admin' OR '1'='1'"),
            ("GET /api/v1/users?id=1 UNION SELECT null,username,password_hash FROM admins--", "UNION SELECT null,username,password_hash FROM admins"),
            ("POST /search.php (payload: '; DROP TABLE audit_log;--)", "DROP TABLE audit_log"),
            ("GET /products.php?cat=99' OR 1=1 ORDER BY 1#", "SELECT * FROM products WHERE cat=99 OR 1=1 ORDER BY 1")
        ]

    def execute_step(self, topology: TopologyState, scenario: ScenarioType) -> List[LogEntry]:
        """
        Executes a single simulation tick (every 500ms).
        Returns a list of generated LogEntry objects for path-traversing packets.
        """
        graph = TopologyGraph(topology)
        logs: List[LogEntry] = []

        clients = graph.find_nodes_by_type(NodeType.CLIENT_EXTERNAL)
        web_servers = graph.find_nodes_by_type(NodeType.WEB_SERVER)
        databases = graph.find_nodes_by_type(NodeType.DATABASE)
        firewalls = graph.find_nodes_by_type(NodeType.FIREWALL)
        lbs = graph.find_nodes_by_type(NodeType.LOAD_BALANCER)

        # Fallback default source/targets if canvas is partially empty
        client_node = clients[0] if clients else Node(id="client-ext", name="Internet-Client", type=NodeType.CLIENT_EXTERNAL, x=50, y=200, ip_address="198.51.100.42")
        target_web = web_servers[self.round_robin_counter % len(web_servers)] if web_servers else None
        target_db = databases[0] if databases else None

        # =========================================================================
        # SCENARIO A: NORMAL TRAFFIC
        # =========================================================================
        if scenario == ScenarioType.NORMAL_TRAFFIC:
            src_ip = random.choice(self.normal_client_ips)
            self.round_robin_counter += 1

            if not web_servers:
                # No web servers to target
                return logs

            selected_web = web_servers[self.round_robin_counter % len(web_servers)]
            sec_eval = graph.evaluate_perimeter_security(client_node.id, selected_web.id)

            if not sec_eval["connected"]:
                # Isolated node / no wire
                return logs

            # If firewall is in-line, log normal inspection allow
            if sec_eval["intercepting_firewall_id"]:
                fw_node = graph.nodes_by_id[sec_eval["intercepting_firewall_id"]]
                if fw_node.vendor == "palo_alto":
                    logs.append(SplunkLogEngine.format_palo_alto_log(
                        device=fw_node, src_ip=src_ip, dest_ip=selected_web.ip_address,
                        src_port=random.randint(40000, 65000), dest_port=80, proto="TCP",
                        action="allowed", signature="PANOS-APP-HTTP-PERMIT", status="normal", duration_ms=random.randint(2, 6)
                    ))
                else:
                    logs.append(SplunkLogEngine.format_cisco_asa_log(
                        device=fw_node, src_ip=src_ip, dest_ip=selected_web.ip_address,
                        src_port=random.randint(40000, 65000), dest_port=80, proto="TCP",
                        action="allowed", signature="ASA-PERMIT-WEB", status="normal", duration_ms=random.randint(2, 6)
                    ))

            # If load balancer is in path, log session dispatch
            if sec_eval["load_balancer_id"]:
                lb_node = graph.nodes_by_id[sec_eval["load_balancer_id"]]
                logs.append(SplunkLogEngine.format_f5_lb_log(
                    device=lb_node, src_ip=src_ip, dest_ip=lb_node.ip_address,
                    backend_ip=selected_web.ip_address, backend_port=80,
                    action="allowed", signature="F5-LTM-ROUND-ROBIN", status="normal", duration_ms=random.randint(1, 4)
                ))

            # Web server log
            methods_uris = [("GET", "/"), ("GET", "/api/v1/health"), ("GET", "/products"), ("GET", "/catalog")]
            method, uri = random.choice(methods_uris)
            logs.append(SplunkLogEngine.format_nginx_web_log(
                device=selected_web, src_ip=src_ip, dest_ip=selected_web.ip_address,
                method=method, uri=uri, http_code=200, bytes_sent=random.randint(500, 4200),
                action="allowed", signature="HTTP-REQUEST-OK", status="normal", duration_ms=random.randint(10, 35)
            ))

        # =========================================================================
        # SCENARIO B: DDOS ATTACK
        # =========================================================================
        elif scenario == ScenarioType.DDOS_ATTACK:
            attacker_ip = random.choice(self.malicious_ips)
            dest_server = target_web or target_db or (firewalls[0] if firewalls else client_node)
            dest_ip = dest_server.ip_address if dest_server else "10.0.1.10"

            sec_eval = graph.evaluate_perimeter_security(client_node.id, dest_server.id)

            # CORE LOGIC: Path directly dictates outcome!
            # If Firewall is in-line and NOT bypassed:
            if sec_eval["has_firewall_inline"] and not sec_eval["bypassed"]:
                fw_node = graph.nodes_by_id[sec_eval["intercepting_firewall_id"]]
                logs.append(SplunkLogEngine.format_cisco_asa_log(
                    device=fw_node, src_ip=attacker_ip, dest_ip=dest_ip,
                    src_port=random.randint(1024, 65535), dest_port=80, proto="TCP",
                    action="blocked", signature="TCP SYN Flood Detected: Rate Limit Exceeded",
                    status="blocked", duration_ms=1
                ))
            else:
                # Firewall was bypassed with a wire OR deleted from canvas!
                # Result: Flooding attacks reach the server directly -> BREACHED!
                if dest_server:
                    logs.append(SplunkLogEngine.format_nginx_web_log(
                        device=dest_server, src_ip=attacker_ip, dest_ip=dest_ip,
                        method="POST", uri="/flood_target", http_code=503, bytes_sent=128,
                        action="allowed", signature="DDoS Incast Saturated Server - Service Unavailable 503",
                        status="breached", duration_ms=random.randint(1500, 3000)
                    ))

        # =========================================================================
        # SCENARIO C: SQL INJECTION / BREACH
        # =========================================================================
        elif scenario == ScenarioType.SQL_INJECTION:
            attacker_ip = random.choice(self.malicious_ips)
            http_payload, sql_statement = random.choice(self.sqli_payloads)
            
            # Destination is Database through Web Server
            dest_web = target_web
            dest_db = target_db

            if not dest_web:
                return logs

            sec_eval = graph.evaluate_perimeter_security(client_node.id, dest_web.id)

            # Check if Firewall intercepts before Web Server
            if sec_eval["has_firewall_inline"] and not sec_eval["bypassed"]:
                # Firewall / WAF inspects and drops the attack
                fw_node = graph.nodes_by_id[sec_eval["intercepting_firewall_id"]]
                logs.append(SplunkLogEngine.format_cisco_asa_log(
                    device=fw_node, src_ip=attacker_ip, dest_ip=dest_web.ip_address,
                    src_port=random.randint(40000, 65000), dest_port=80, proto="TCP",
                    action="blocked", signature="OWASP-WAF-942100: SQL Injection Vector Denied",
                    status="blocked", duration_ms=3
                ))
            else:
                # Firewall bypassed or absent! Attack hits Web Server
                logs.append(SplunkLogEngine.format_nginx_web_log(
                    device=dest_web, src_ip=attacker_ip, dest_ip=dest_web.ip_address,
                    method="GET", uri=http_payload, http_code=200, bytes_sent=8400,
                    action="allowed", signature="SQLi Payload Ingested via HTTP Parameter",
                    status="breached", duration_ms=45
                ))

                # If Database is wired to Web Server, payload penetrates to DB layer!
                if dest_db:
                    db_paths = graph.find_all_paths(dest_web.id, dest_db.id)
                    if db_paths:
                        logs.append(SplunkLogEngine.format_postgres_db_log(
                            device=dest_db, src_ip=dest_web.ip_address, dest_ip=dest_db.ip_address,
                            sql_statement=sql_statement, action="alerted",
                            signature="CVE-2023-SQLi-T1190 Database Exfiltration Confirmed",
                            status="breached", duration_ms=random.randint(35, 75)
                        ))

        # =========================================================================
        # SCENARIO D: RANSOMWARE / LATERAL MOVEMENT
        # =========================================================================
        elif scenario == ScenarioType.LATERAL_MOVEMENT:
            self.lateral_step += 1
            if len(web_servers) >= 2:
                pivot_host = web_servers[0]
                target_host = web_servers[1] if self.lateral_step % 2 == 0 else (target_db or web_servers[1])

                lateral_eval = graph.evaluate_lateral_spread(pivot_host.id)

                if target_host.id in lateral_eval["blocked_targets"]:
                    # An internal firewall protects this segment
                    fw_list = [n for n in graph.topology.nodes if n.type == NodeType.FIREWALL]
                    internal_fw = fw_list[-1] if fw_list else pivot_host
                    logs.append(SplunkLogEngine.format_cisco_asa_log(
                        device=internal_fw, src_ip=pivot_host.ip_address, dest_ip=target_host.ip_address,
                        src_port=random.randint(49152, 65535), dest_port=445, proto="TCP",
                        action="blocked", signature="Micro-Segmentation: SMB Port 445 Lateral Movement Blocked",
                        status="blocked", duration_ms=2
                    ))
                elif target_host.id in lateral_eval["spread_targets"]:
                    # Flat unsegmented subnet -> Lateral infection spreads!
                    logs.append(SplunkLogEngine.format_router_switch_log(
                        device=pivot_host, src_ip=pivot_host.ip_address, dest_ip=target_host.ip_address,
                        interface="eth1", action="allowed",
                        signature="T1021.002 SMB PsExec Lateral Propagation - Port 445",
                        status="breached", duration_ms=random.randint(12, 30)
                    ))
                    if target_host.type == NodeType.DATABASE:
                        logs.append(SplunkLogEngine.format_postgres_db_log(
                            device=target_host, src_ip=pivot_host.ip_address, dest_ip=target_host.ip_address,
                            sql_statement="DROP DATABASE prod_records; -- Ransomware Encryption Routine",
                            action="alerted", signature="Ransomware Payload Executed at Database Layer",
                            status="breached", duration_ms=120
                        ))

        # =========================================================================
        # SCENARIO A1: CAMPUS CORE L2/3 DISTURBANCE & ROGUE AP
        # =========================================================================
        elif scenario == ScenarioType.CISCO_CAMPUS_ROGUE:
            switch_node = next(
                (n for n in graph.topology.nodes if "catalyst" in n.vendor or n.type in (NodeType.SWITCH, NodeType.ROUTER)),
                Node(id="cat9300-core", name="Catalyst-9300-Core", type=NodeType.SWITCH, x=450, y=220, ip_address="10.10.1.1", vendor="cisco_catalyst")
            )
            ise_node = next(
                (n for n in graph.topology.nodes if "ise" in n.vendor or "ise" in n.name.lower() or n.type == NodeType.FIREWALL),
                Node(id="cisco-ise", name="Cisco-ISE-PSN01", type=NodeType.FIREWALL, x=220, y=100, ip_address="10.10.1.25", vendor="cisco_ise")
            )
            ap_node = next(
                (n for n in graph.topology.nodes if n.type == NodeType.WIRELESS_AP or "ap" in n.name.lower() or "rogue" in n.name.lower()),
                Node(id="cisco-ap9120", name="Catalyst-9120-AP", type=NodeType.WIRELESS_AP, x=150, y=220, ip_address="10.10.20.5", vendor="cisco_catalyst")
            )

            rogue_macs = ["00:1A:2B:3C:4D:5E", "54:78:1A:99:FF:01", "70:81:05:AA:BB:CC"]
            target_mac = random.choice(rogue_macs)
            
            # 1. Catalyst Rogue AP threat alert
            logs.append(SplunkLogEngine.format_cisco_catalyst_rogue_log(
                device=ap_node, rogue_mac=target_mac, bssid="00:1A:2B:FF:EE:DD",
                ssid="CORP_GUEST_ROGUE", channel=random.choice([1, 6, 11]),
                rssi=random.randint(-78, -45), action="alerted", status="breached"
            ))

            # 2. Cisco ISE 802.1X Quarantine / Auth Failure
            logs.append(SplunkLogEngine.format_cisco_ise_log(
                device=ise_node, client_mac=target_mac, client_ip="10.10.20.142",
                user="rogue_attacker", auth_status="FAILED", profile="Quarantine_Restricted_VLAN",
                action="blocked", status="blocked"
            ))

            # 3. Catalyst Switch MAC Flapping detection
            p1, p2 = "GigabitEthernet1/0/12", "GigabitEthernet1/0/48"
            logs.append(SplunkLogEngine.format_cisco_mac_flap_log(
                device=switch_node, mac=target_mac, vlan=10, port1=p1, port2=p2,
                action="alerted", status="breached"
            ))

        # =========================================================================
        # SCENARIO A2: ENTERPRISE WAN CIRCUIT BROWNOUT & ROUTE FAILOVER
        # =========================================================================
        elif scenario == ScenarioType.CISCO_SDWAN_BROWNOUT:
            router_node = next(
                (n for n in graph.topology.nodes if "sdwan" in n.vendor or "vedge" in n.name.lower() or n.type == NodeType.ROUTER),
                Node(id="vedge-5000", name="Cisco-vEdge-5000", type=NodeType.ROUTER, x=380, y=220, ip_address="172.16.1.1", vendor="cisco_sdwan")
            )
            te_node = next(
                (n for n in graph.topology.nodes if "thousandeyes" in n.vendor or "te" in n.name.lower() or n.type == NodeType.CLIENT_EXTERNAL),
                Node(id="thousandeyes-agent", name="ThousandEyes-Agent", type=NodeType.CLIENT_EXTERNAL, x=100, y=220, ip_address="172.16.1.50", vendor="cisco_thousandeyes")
            )

            latency = random.uniform(160.0, 240.0)
            jitter = random.uniform(22.0, 48.0)
            loss = random.uniform(8.5, 18.0)

            # 1. SD-WAN BFD Link Health Brownout
            logs.append(SplunkLogEngine.format_cisco_sdwan_linkhealth_log(
                device=router_node, remote_system_ip="198.51.100.1", latency_ms=latency,
                jitter_ms=jitter, loss_pct=loss, sla_status="VIOLATION",
                action="alerted", status="degraded"
            ))

            # 2. SD-WAN BGP Flap and Route Failover
            logs.append(SplunkLogEngine.format_cisco_sdwan_bgp_log(
                device=router_node, neighbor_ip="198.51.100.1", state_change="DOWN",
                action="allowed", status="degraded"
            ))

            # 3. ThousandEyes Synthetic Metric Verification
            logs.append(SplunkLogEngine.format_cisco_thousandeyes_log(
                device=te_node, target_url="https://crm.corp.internal/health",
                latency_ms=latency, packet_loss_pct=loss, http_code=200,
                action="alerted", status="degraded"
            ))

        # =========================================================================
        # SCENARIO A3: DATA CENTER FABRIC ACI INGRESS MICROBURST
        # =========================================================================
        elif scenario == ScenarioType.CISCO_ACI_MICROBURST:
            nexus_node = next(
                (n for n in graph.topology.nodes if "nexus" in n.vendor or "leaf" in n.name.lower() or n.type == NodeType.SWITCH),
                Node(id="nexus-9336", name="Nexus-9336-Leaf01", type=NodeType.SWITCH, x=500, y=220, ip_address="10.255.0.11", vendor="cisco_nexus")
            )

            buffer_util = random.uniform(92.5, 99.4)
            dropped_pkts = random.randint(340, 1850)
            fabric_score = random.randint(58, 68)

            # 1. Nexus 9K Buffer Ingress Drop alert
            logs.append(SplunkLogEngine.format_cisco_aci_nexus_log(
                device=nexus_node, asic_interface="Ethernet1/24 (Ingress Incast)",
                buffer_util_pct=buffer_util, dropped_packets=dropped_pkts,
                fabric_health=fabric_score, action="dropped", status="degraded"
            ))

            # 2. Cisco IOS-XE / NX-OS MDT Streaming Telemetry
            logs.append(SplunkLogEngine.format_cisco_mdt_log(
                device=nexus_node, sensor_path="Cisco-NX-OS-buffer-stats:queue-depth",
                queue_depth_bytes=random.randint(18400000, 26500000),
                peak_buffer_pct=buffer_util, action="alerted", status="degraded"
            ))

        # =========================================================================
        # SCENARIO B1: DISTRIBUTED EDGE BREACH & INTERNAL PROBING
        # =========================================================================
        elif scenario == ScenarioType.MIXED_EDGE_BREACH:
            attacker_ip = random.choice(self.malicious_ips)
            ap_node = next(
                (n for n in graph.topology.nodes if "meraki" in n.vendor or n.type == NodeType.WIRELESS_AP or "ap" in n.name.lower()),
                Node(id="meraki-mr56", name="Meraki-MR56-AP", type=NodeType.WIRELESS_AP, x=100, y=220, ip_address="10.128.0.55", vendor="meraki")
            )
            pan_node = next(
                (n for n in graph.topology.nodes if "palo" in n.vendor or n.type == NodeType.FIREWALL),
                Node(id="pa-440", name="PaloAlto-PA440-NGFW", type=NodeType.FIREWALL, x=450, y=220, ip_address="10.128.1.1", vendor="palo_alto")
            )
            dest_host = target_web or target_db or Node(id="srv-web", name="Internal-App-Server", type=NodeType.WEB_SERVER, x=750, y=220, ip_address="10.128.2.10", vendor="nginx")

            # Evaluate perimeter path between AP / Edge and destination
            sec_eval = graph.evaluate_perimeter_security(ap_node.id, dest_host.id)

            # 1. Meraki Rogue Client Assurance Alert
            logs.append(SplunkLogEngine.format_meraki_alert_log(
                device=ap_node, client_mac="44:65:0E:12:34:56",
                alert_type="Air Marshal Rogue Containment Probe", channel=36,
                action="alerted", status="breached"
            ))

            # 2. Path-Dependent Firewall Inspection:
            # If Palo Alto NGFW intercepts packet and is NOT bypassed:
            if sec_eval["has_firewall_inline"] and not sec_eval["bypassed"]:
                logs.append(SplunkLogEngine.format_palo_alto_threat_log(
                    device=pan_node, src_ip=attacker_ip, dest_ip=dest_host.ip_address,
                    src_port=random.randint(40000, 65000), dest_port=445,
                    threat_name="Scan: TCP Port Scan / Lateral Probing",
                    threat_id=80012, action="blocked", status="blocked"
                ))
            else:
                # Bypassed / Absent firewall -> Breaches interior host!
                logs.append(SplunkLogEngine.format_palo_alto_threat_log(
                    device=pan_node, src_ip=attacker_ip, dest_ip=dest_host.ip_address,
                    src_port=random.randint(40000, 65000), dest_port=80,
                    threat_name="CVE-2024-Unchecked-Perimeter-Bypass Lateral Breach",
                    threat_id=99001, action="allowed", status="breached"
                ))
                logs.append(SplunkLogEngine.format_nginx_web_log(
                    device=dest_host, src_ip=attacker_ip, dest_ip=dest_host.ip_address,
                    method="POST", uri="/api/v1/admin/exploit", http_code=200, bytes_sent=4500,
                    action="allowed", signature="Lateral Intrusion Established Post-Perimeter Bypass",
                    status="breached", duration_ms=38
                ))

        # =========================================================================
        # SCENARIO B2: SASE CLOUD INGRESS APP DEGRADATION
        # =========================================================================
        elif scenario == ScenarioType.MIXED_SASE_DEGRADATION:
            sase_node = next(
                (n for n in graph.topology.nodes if "zscaler" in n.vendor or "cloudflare" in n.vendor or n.type in (NodeType.SASE_PROXY, NodeType.CLIENT_EXTERNAL)),
                Node(id="zscaler-edge", name="Zscaler-ZIA-Edge", type=NodeType.SASE_PROXY, x=100, y=220, ip_address="165.225.10.1", vendor="zscaler")
            )
            pan_edge = next(
                (n for n in graph.topology.nodes if "palo" in n.vendor or n.type == NodeType.FIREWALL),
                Node(id="pa-prisma", name="PaloAlto-Prisma-Edge", type=NodeType.FIREWALL, x=380, y=220, ip_address="10.20.1.1", vendor="palo_alto")
            )
            core_switch = next(
                (n for n in graph.topology.nodes if "nexus" in n.vendor or n.type == NodeType.SWITCH),
                Node(id="nexus-dc", name="Cisco-Nexus-DC-Core", type=NodeType.SWITCH, x=650, y=220, ip_address="10.20.1.254", vendor="cisco_nexus")
            )

            client_ip = random.choice(self.normal_client_ips)
            latency = random.randint(2800, 4900)

            # 1. Zscaler ZIA Transaction Log (SSL Inspection Degradation)
            logs.append(SplunkLogEngine.format_zscaler_zia_log(
                device=sase_node, client_ip=client_ip,
                dest_url="https://erp.corporate.cloud/finance/ledger",
                latency_ms=latency, action="allowed", status="degraded"
            ))

            # 2. ThousandEyes Synthetic Probe Degradation
            logs.append(SplunkLogEngine.format_cisco_thousandeyes_log(
                device=sase_node, target_url="https://erp.corporate.cloud/health",
                latency_ms=float(latency / 10.0), packet_loss_pct=random.uniform(4.5, 9.8),
                http_code=200, action="alerted", status="degraded",
                signature="ThousandEyes SASE Cloud Path Degraded (High TTFB)"
            ))

            # 3. Palo Alto SD-WAN Session Saturation
            logs.append(SplunkLogEngine.format_palo_alto_log(
                device=pan_edge, src_ip=client_ip, dest_ip=core_switch.ip_address,
                src_port=random.randint(40000, 65000), dest_port=443, proto="TCP",
                action="allowed", signature="PAN-OS SASE Gateway Tunnel TCP Queue Congestion",
                status="degraded", duration_ms=random.randint(150, 320)
            ))

        # =========================================================================
        # SCENARIO B3: MULTICAST/MPLS BACKBONE OPTICAL CARRIER SHIFT
        # =========================================================================
        elif scenario == ScenarioType.MIXED_BACKBONE_OPTICAL:
            nokia_node = next(
                (n for n in graph.topology.nodes if "nokia" in n.vendor or n.type == NodeType.OPTICAL_CORE),
                Node(id="nokia-7750", name="Nokia-7750-SR12-Transport", type=NodeType.OPTICAL_CORE, x=150, y=220, ip_address="10.200.0.1", vendor="nokia_sros")
            )
            juniper_node = next(
                (n for n in graph.topology.nodes if "juniper" in n.vendor or n.type == NodeType.ROUTER),
                Node(id="juniper-mx960", name="Juniper-MX960-PE01", type=NodeType.ROUTER, x=450, y=220, ip_address="10.200.0.2", vendor="juniper_junos")
            )
            arista_node = next(
                (n for n in graph.topology.nodes if "arista" in n.vendor or n.type == NodeType.SWITCH),
                Node(id="arista-7280", name="Arista-7280R-Leaf01", type=NodeType.SWITCH, x=750, y=220, ip_address="10.200.0.3", vendor="arista_eos")
            )

            # 1. Nokia SR-OS DWDM Loss-of-Signal (LOS) Alarm
            logs.append(SplunkLogEngine.format_nokia_sros_log(
                device=nokia_node, port_id="1/1/c1 (DWDM 100G Lambda)",
                lsp_name="LSP-WAN-PRIMARY-TO-DC", action="alerted", status="degraded"
            ))

            # 2. Juniper Junos RSVP-TE Fast Reroute (FRR)
            logs.append(SplunkLogEngine.format_juniper_junos_log(
                device=juniper_node, lsp_name="LSP-WAN-PRIMARY-TO-DC",
                primary_nh="10.200.1.1 (Optical DWDM)",
                bypass_nh="10.200.2.1 (Secondary Metro-E)",
                action="allowed", status="normal"
            ))

            # 3. Arista EOS IPFIX Flow Telemetry Confirming Alternate Path Egress
            logs.append(SplunkLogEngine.format_arista_ipfix_log(
                device=arista_node, src_ip="10.200.0.1", dest_ip="10.200.0.3",
                bytes_transferred=random.randint(1200000, 3800000),
                egress_intf="Ethernet49/1 (Bypass-Path)", reroute_flag=1,
                action="allowed", status="normal"
            ))

        # =========================================================================
        # AUTOMATED MULTI-PROTOCOL TELEMETRY STREAM GENERATOR (MDT, SNMP, IPFIX)
        # =========================================================================
        self.telemetry_tick += 1
        active_network_nodes = [
            n for n in topology.nodes
            if n.type in [NodeType.ROUTER, NodeType.SWITCH, NodeType.FIREWALL]
            and n.power_state == NodePowerState.RUNNING
        ]

        if active_network_nodes:
            # 1. Model-Driven Telemetry (MDT) Stream (Every 2 ticks)
            if self.telemetry_tick % 2 == 0:
                mdt_node = random.choice(active_network_nodes)
                cpu_load = mdt_node.hardware.cpu_utilization_pct if mdt_node.hardware else 25.0
                mem_load = mdt_node.hardware.memory_utilization_pct if mdt_node.hardware else 35.0
                logs.append(SplunkLogEngine.format_mdt_stream(
                    device=mdt_node,
                    interface_name=mdt_node.interface or "GigabitEthernet0/0/1",
                    in_octets=random.randint(40000000, 80000000),
                    out_octets=random.randint(30000000, 90000000),
                    cpu_pct=cpu_load,
                    memory_pct=mem_load,
                    action="allowed",
                    status="normal" if cpu_load < 80 else "degraded"
                ))

            # 2. NetFlow v9 / IPFIX Flow Records (Every 2 ticks)
            if self.telemetry_tick % 2 == 0 and len(topology.nodes) >= 2:
                flow_dev = random.choice(active_network_nodes)
                logs.append(SplunkLogEngine.format_ipfix_flow(
                    device=flow_dev,
                    src_ip=random.choice(self.normal_client_ips),
                    dest_ip=flow_dev.ip_address,
                    src_port=random.randint(30000, 65000),
                    dest_port=random.choice([80, 443, 22, 53, 8080]),
                    protocol="TCP",
                    bytes_count=random.randint(4000, 65000),
                    packets_count=random.randint(5, 50),
                    tcp_flags="SYN,ACK,PSH",
                    action="allowed",
                    status="normal"
                ))

            # 3. SNMP Traps & Webhooks (on Security Incidents or periodic health checks)
            has_threat = any(l.status in ["blocked", "breached", "degraded"] for l in logs)
            if has_threat and self.telemetry_tick % 3 == 0:
                trap_dev = random.choice(active_network_nodes)
                trap_name = "linkDown" if scenario in [ScenarioType.CISCO_SDWAN_BROWNOUT, ScenarioType.MIXED_BACKBONE_OPTICAL] else "authenticationFailure"
                logs.append(SplunkLogEngine.format_snmp_trap(
                    device=trap_dev,
                    trap_type=trap_name,
                    interface_name=trap_dev.interface or "GigabitEthernet0/0/1",
                    action="alerted",
                    status="warning"
                ))
                logs.append(SplunkLogEngine.format_controller_webhook_event(
                    device=trap_dev,
                    controller_type="panorama" if "palo" in trap_dev.vendor else "catalyst_center",
                    alert_category="security_threat"
                ))

        # =========================================================================
        # DUAL TRANSPORT DISPATCHER ROUTING (HEC & DIRECT SYSLOG)
        # =========================================================================
        if topology.global_transport:
            for log_entry in logs:
                try:
                    dispatcher.dispatch_log(log_entry, transport=topology.global_transport)
                except Exception:
                    pass

        return logs


