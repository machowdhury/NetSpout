"""
Comprehensive NOC & SOC Metric Emulation Engine (NetSpout)
Emulates:
  - Network Operations (NOC): Flow efficiency, MOS (VoIP), goodput, optical power dBm, MTBF, DDI (DNS/DHCP/NTP).
  - Security Architecture (SOC): Firewall session utilization, DPI, shadow rules, micro-segmentation, C2 beaconing.
  - Multi-Frequency Operational Blueprints: Real-time, Weekly trends, Strategic annual compliance.

Author: Mahamudul Chowdhury (machowdhury@yahoo.com)
"""

import time
import math
import random
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


class NocSocMetricEngine:
    """
    Generates deterministic, highly authentic NOC and SOC metrics across all tiers.
    """
    def __init__(self):
        self.start_time = time.time()
        self.tick_counter = 0

    def calculate_mos(self, rtt_ms: float, jitter_ms: float, loss_pct: float) -> float:
        """
        Calculates Mean Opinion Score (MOS) using simplified ITU-T G.107 E-model.
        Returns MOS rating between 1.0 (unusable) and 4.5 (toll quality).
        """
        effective_latency = rtt_ms + (jitter_ms * 2.0)
        r = 93.2
        if effective_latency > 100:
            r -= (effective_latency - 100) / 10.0
        r -= (loss_pct * 8.5)
        r = max(0.0, min(100.0, r))
        if r < 0:
            return 1.0
        elif r > 100:
            return 4.5
        else:
            mos = 1.0 + (0.035 * r) + (r * (r - 60) * (100 - r) * 0.000007)
            return round(max(1.0, min(4.5, mos)), 2)

    def generate_noc_metrics(self, is_degraded: bool = False) -> Dict[str, Any]:
        """Generates comprehensive Network Operations Center telemetry."""
        now = time.time()
        uptime_hrs = (now - self.start_time) / 3600.0 + 842.0  # realistic long-running uptime

        # 1. Data Plane & Flow Efficiency
        if not is_degraded:
            throughput_mbps = round(random.uniform(4200.0, 7800.0), 2)
            goodput_mbps = round(throughput_mbps * random.uniform(0.95, 0.98), 2)
            retrans_pct = round(random.uniform(0.01, 0.04), 3)
            rtt_ms = round(random.uniform(1.2, 4.8), 2)
            jitter_ms = round(random.uniform(0.2, 1.1), 2)
            loss_pct = round(random.uniform(0.00, 0.02), 3)
            bgp_convergence_ms = 110.0
            optical_rx_dbm = round(random.uniform(-10.8, -9.8), 2)
            thermal_chassis_c = round(random.uniform(33.0, 36.5), 1)
            thermal_asic_c = round(random.uniform(41.0, 45.0), 1)
            dns_latency_ms = round(random.uniform(1.8, 3.2), 2)
            dns_fail_pct = round(random.uniform(0.01, 0.03), 3)
            dhcp_pool_pct = round(random.uniform(41.0, 46.0), 1)
            ntp_offset_us = round(random.uniform(8.0, 18.0), 1)
        else:
            throughput_mbps = round(random.uniform(850.0, 1900.0), 2)
            goodput_mbps = round(throughput_mbps * random.uniform(0.75, 0.85), 2)
            retrans_pct = round(random.uniform(4.5, 8.2), 3)
            rtt_ms = round(random.uniform(45.0, 110.0), 2)
            jitter_ms = round(random.uniform(14.0, 28.0), 2)
            loss_pct = round(random.uniform(3.2, 7.5), 3)
            bgp_convergence_ms = 4200.0
            optical_rx_dbm = -24.50
            thermal_chassis_c = round(random.uniform(68.0, 74.5), 1)
            thermal_asic_c = round(random.uniform(84.0, 89.0), 1)
            dns_latency_ms = round(random.uniform(65.0, 120.0), 2)
            dns_fail_pct = round(random.uniform(12.5, 18.0), 2)
            dhcp_pool_pct = 98.4
            ntp_offset_us = round(random.uniform(4500.0, 12500.0), 1)

        mos = self.calculate_mos(rtt_ms, jitter_ms, loss_pct)

        return {
            "throughput_mbps": throughput_mbps,
            "goodput_mbps": goodput_mbps,
            "flow_efficiency_pct": round((goodput_mbps / throughput_mbps) * 100.0, 1),
            "retransmission_rate_pct": retrans_pct,
            "tcp_retrans_pct": retrans_pct,
            "rtt_ms": rtt_ms,
            "jitter_ms": jitter_ms,
            "packet_loss_pct": loss_pct,
            "mos_score": mos,
            "bgp_convergence_ms": bgp_convergence_ms,
            "optical_rx_dbm": optical_rx_dbm,
            "optical_tx_power_dbm": -2.40,
            "mtbf_hours": 185000,
            "thermal_chassis_c": thermal_chassis_c,
            "thermal_asic_c": thermal_asic_c,
            "dns_latency_ms": dns_latency_ms,
            "dns_failure_rate_pct": dns_fail_pct,
            "dhcp_pool_exhaustion_pct": dhcp_pool_pct,
            "ntp_offset_us": ntp_offset_us,
            "firewall_session_utilization_pct": 94.6 if is_degraded else 38.2,
            "c2_beacon_threat_score": 88.5 if is_degraded else 12.0,
            "dataplane_efficiency": {
                "throughput_mbps": throughput_mbps,
                "goodput_mbps": goodput_mbps,
                "retransmission_rate_pct": retrans_pct,
                "rtt_ms": rtt_ms,
                "jitter_ms": jitter_ms,
                "packet_loss_pct": loss_pct,
                "mos_voice_score": mos,
                "bgp_convergence_ms": bgp_convergence_ms
            },
            "infrastructure_health": {
                "optical_rx_power_dbm": optical_rx_dbm,
                "optical_tx_power_dbm": -2.40,
                "device_uptime_hours": round(uptime_hrs, 1),
                "mtbf_hours": 185000,
                "thermal_chassis_celsius": thermal_chassis_c,
                "thermal_asic_celsius": thermal_asic_c,
                "fan_speed_rpm": 4800 if not is_degraded else 11500,
                "psu_redundancy_active": True,
                "config_drift_rate_pct": 0.0 if not is_degraded else 4.2
            },
            "core_ddi_services": {
                "dns_latency_ms": dns_latency_ms,
                "dns_failure_rate_pct": dns_fail_pct,
                "dhcp_pool_exhaustion_pct": dhcp_pool_pct,
                "ntp_stratum_offset_us": ntp_offset_us,
                "ntp_active_stratum": 1
            }
        }

    def generate_soc_metrics(self, is_under_attack: bool = False) -> Dict[str, Any]:
        """Generates comprehensive Security Operations Center telemetry."""
        if not is_under_attack:
            session_util = round(random.uniform(21.0, 28.5), 1)
            dpi_throughput_gbps = round(random.uniform(18.5, 24.0), 2)
            rule_hits = random.randint(120000, 185000)
            shadow_rules = 4
            vpn_tunnels = 48
            vpn_flaps = 0
            any_to_any_rules = 1
            quarantine_rate_pct = 0.4
            microsegmentation_violations = 0
            mac_spoofing_count = 0
            threat_sig_count = 2
            inspect_to_block_ratio_pct = 0.08
            encrypted_inspection_pct = 82.5
            exfiltration_kbps = 0.0
            lateral_hops_per_min = 0.0
            c2_regularity_score = 0.04
            ddos_mitigation_ms = 0.0
        else:
            session_util = 96.8
            dpi_throughput_gbps = 48.5
            rule_hits = random.randint(4500000, 6800000)
            shadow_rules = 12
            vpn_tunnels = 34
            vpn_flaps = 14
            any_to_any_rules = 3
            quarantine_rate_pct = 18.5
            microsegmentation_violations = 48
            mac_spoofing_count = 12
            threat_sig_count = 42
            inspect_to_block_ratio_pct = 34.2
            encrypted_inspection_pct = 45.0
            exfiltration_kbps = 4250.0
            lateral_hops_per_min = 8.5
            c2_regularity_score = 0.94
            ddos_mitigation_ms = 1850.0

        return {
            "perimeter_firewall_state": {
                "session_utilization_pct": session_util,
                "dpi_throughput_gbps": dpi_throughput_gbps,
                "active_rule_hits": rule_hits,
                "unused_shadow_rules_count": shadow_rules,
                "vpn_tunnels_active": vpn_tunnels,
                "vpn_tunnel_flaps": vpn_flaps,
                "any_to_any_permissive_rules": any_to_any_rules
            },
            "nac_microsegmentation": {
                "unauth_quarantine_rate_pct": quarantine_rate_pct,
                "microsegmentation_violations": microsegmentation_violations,
                "mac_spoofing_events": mac_spoofing_count
            },
            "threat_prevention_inspection": {
                "active_threat_signatures": threat_sig_count,
                "inspect_to_block_ratio_pct": inspect_to_block_ratio_pct,
                "encrypted_traffic_inspection_pct": encrypted_inspection_pct
            },
            "ndr_traffic_anomalies": {
                "data_exfiltration_rate_kbps": exfiltration_kbps,
                "lateral_movement_velocity_hops_per_min": lateral_hops_per_min,
                "c2_beacon_regularity_score": c2_regularity_score,
                "ddos_mitigation_time_ms": ddos_mitigation_ms
            }
        }

    def get_frequency_blueprints(self) -> Dict[str, Any]:
        """
        Returns structured multi-frequency operational metrics:
          1. Real-time stream (1-5s intervals for NOC wallboard)
          2. Weekly / Monthly engineering trend rollups
          3. Annual strategic C-suite & auditor metrics
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        return {
            "realtime_blueprint": {
                "frequency": "realtime_5s",
                "timestamp": now_iso,
                "noc": self.generate_noc_metrics(is_degraded=False),
                "soc": self.generate_soc_metrics(is_under_attack=False)
            },
            "weekly_monthly_blueprint": {
                "frequency": "weekly_trend",
                "timestamp": now_iso,
                "average_availability_sla_pct": 99.982,
                "mttr_minutes": 8.4,
                "bgp_flaps_7d": 3,
                "dhcp_exhaustion_peak_pct": 68.2,
                "shadow_rule_reduction_pct": 45.0,
                "dpi_utilization_growth_pct": 12.4,
                "capacity_forecast_days_remaining": 142
            },
            "strategic_annual_blueprint": {
                "frequency": "annual_strategic",
                "timestamp": now_iso,
                "zero_trust_architecture_compliance_pct": 94.2,
                "pci_dss_network_segmentation_audit_score": 100.0,
                "cis_benchmark_pass_rate_pct": 98.6,
                "annual_mtbf_hours_achieved": 182500,
                "unplanned_downtime_minutes_total": 4.2,
                "csuite_security_confidence_index": 92.5
            }
        }


    def get_operational_blueprints(self) -> Dict[str, Any]:
        """Provides 3-frequency operational blueprints."""
        return {
            "realtime_tactical": {
                "polling_frequency_seconds": 5,
                "target_use": "Live triage, dynamic alerting, and automated incident creation",
                "recommended_index": "idx_network_ops"
            },
            "weekly_capacity_forecast": {
                "polling_frequency_hours": 1,
                "target_use": "Growth trend analysis, MTBF degradation rate, and link saturation projection",
                "recommended_index": "cisco_mdt_metrics"
            },
            "annual_strategic_compliance": {
                "polling_frequency_days": 30,
                "target_use": "Executive SLA attainment, NIST 800-53 / CIS compliance, and vendor refresh planning",
                "recommended_index": "netspout_reports"
            }
        }


# Global singleton metric engine
metric_engine = NocSocMetricEngine()
