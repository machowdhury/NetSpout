import React, { useState, useEffect } from 'react';
import { 
  X, Activity, Gauge, TrendingUp, RefreshCw, 
  Shield, Server, Zap, Radio
} from 'lucide-react';

interface NocMetrics {
  throughput_mbps: number;
  goodput_mbps: number;
  flow_efficiency_pct: number;
  tcp_retrans_pct: number;
  rtt_ms: number;
  jitter_ms: number;
  packet_loss_pct: number;
  mos_score: number;
  bgp_convergence_ms: number;
  optical_rx_dbm: number;
  thermal_chassis_c: number;
  thermal_asic_c: number;
  mtbf_hours: number;
  hardware_failure_prob_pct: number;
  config_drift_detected: boolean;
  dns_latency_ms: number;
  dns_failure_rate_pct: number;
  dhcp_pool_exhaustion_pct: number;
  ntp_stratum: number;
  ntp_offset_us: number;
  firewall_session_utilization_pct: number;
  deep_packet_inspection_bypass_pct: number;
  shadow_rules_count: number;
  micro_segmentation_quarantines: number;
  c2_beacon_threat_score: number;
  timestamp: string;
}

interface NocSocMetricsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const NocSocMetricsModal: React.FC<NocSocMetricsModalProps> = ({ isOpen, onClose }) => {
  const [metrics, setMetrics] = useState<NocMetrics | null>(null);
  const [activeTab, setActiveTab] = useState<'data_plane' | 'hardware' | 'ddi' | 'soc_firewall' | 'blueprints'>('data_plane');
  const [isDegraded, setIsDegraded] = useState<boolean>(false);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);

  // Fetch or simulate live NOC & SOC Metrics
  useEffect(() => {
    if (!isOpen) return;

    const fetchMetrics = () => {
      const url = typeof window !== 'undefined' && window.location.port === '8081'
        ? `${window.location.origin}/api/metrics/noc_soc?degraded=${isDegraded}`
        : `http://localhost:8081/api/metrics/noc_soc?degraded=${isDegraded}`;

      fetch(url)
        .then(res => res.json())
        .then(data => {
          if (data && data.metrics) {
            setMetrics(data.metrics);
          }
        })
        .catch(() => {
          // Fallback simulation
          const throughput = isDegraded ? 1240.0 : 6420.0;
          const goodput = isDegraded ? 980.0 : 6180.0;
          setMetrics({
            throughput_mbps: throughput,
            goodput_mbps: goodput,
            flow_efficiency_pct: isDegraded ? 79.0 : 96.2,
            tcp_retrans_pct: isDegraded ? 5.8 : 0.02,
            rtt_ms: isDegraded ? 84.5 : 2.4,
            jitter_ms: isDegraded ? 18.2 : 0.6,
            packet_loss_pct: isDegraded ? 4.8 : 0.01,
            mos_score: isDegraded ? 2.15 : 4.38,
            bgp_convergence_ms: isDegraded ? 4200.0 : 110.0,
            optical_rx_dbm: isDegraded ? -24.5 : -10.2,
            thermal_chassis_c: isDegraded ? 72.4 : 34.2,
            thermal_asic_c: isDegraded ? 87.1 : 42.8,
            mtbf_hours: 48200,
            hardware_failure_prob_pct: isDegraded ? 14.8 : 0.04,
            config_drift_detected: isDegraded,
            dns_latency_ms: isDegraded ? 94.2 : 2.4,
            dns_failure_rate_pct: isDegraded ? 14.5 : 0.02,
            dhcp_pool_exhaustion_pct: isDegraded ? 98.4 : 42.1,
            ntp_stratum: 1,
            ntp_offset_us: isDegraded ? 8400.0 : 12.4,
            firewall_session_utilization_pct: isDegraded ? 94.6 : 38.2,
            deep_packet_inspection_bypass_pct: isDegraded ? 18.4 : 0.4,
            shadow_rules_count: 14,
            micro_segmentation_quarantines: isDegraded ? 7 : 0,
            c2_beacon_threat_score: isDegraded ? 88.5 : 12.0,
            timestamp: new Date().toISOString()
          });
        });
    };

    fetchMetrics();
    let interval: any;
    if (autoRefresh) {
      interval = setInterval(fetchMetrics, 2000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isOpen, isDegraded, autoRefresh]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="bg-[#0B0F19] border border-[#374151] rounded-xl w-full max-w-5xl max-h-[92vh] flex flex-col shadow-2xl overflow-hidden font-sans">
        
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#374151] bg-[#1F2937]">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-cyan-500/10 border border-cyan-500/30 text-cyan-400">
              <Activity className="w-5 h-5 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-slate-100 font-mono">
                  NOC & SOC Metric Telemetry Matrix
                </h2>
                <span className="text-xs bg-cyan-950 text-cyan-300 border border-cyan-700/60 px-2 py-0.5 rounded font-mono font-bold">
                  HIGH DENSITY NOC
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-0.5">
                Real-time data plane, optical link dBm, ITU-T G.107 MOS, DDI, and firewall threat defense
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {/* Degraded State Toggle */}
            <button
              onClick={() => setIsDegraded(!isDegraded)}
              className={`px-3 py-1.5 rounded-lg border text-xs font-mono font-bold flex items-center gap-1.5 transition-colors cursor-pointer ${
                isDegraded
                  ? 'bg-rose-950/80 text-rose-300 border-rose-600 shadow-[0_0_12px_rgba(239,68,68,0.3)]'
                  : 'bg-slate-900 text-slate-400 border-slate-700 hover:text-slate-200'
              }`}
            >
              <Zap className="w-3.5 h-3.5 text-rose-400" />
              <span>{isDegraded ? 'Anomaly Injected' : 'Inject Anomaly'}</span>
            </button>

            {/* Auto refresh */}
            <button
              onClick={() => setAutoRefresh(!autoRefresh)}
              className={`p-1.5 rounded-lg border text-xs font-mono transition-colors cursor-pointer ${
                autoRefresh ? 'bg-cyan-950 text-cyan-300 border-cyan-700' : 'bg-slate-900 text-slate-400 border-slate-700'
              }`}
              title="Toggle 2s Auto Refresh"
            >
              <RefreshCw className={`w-4 h-4 ${autoRefresh ? 'animate-spin' : ''}`} />
            </button>

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="flex items-center px-6 bg-[#111827] border-b border-[#1F2937] gap-2 overflow-x-auto">
          {[
            { id: 'data_plane', label: 'Data Plane & VoIP MOS', icon: Gauge },
            { id: 'hardware', label: 'Optical & Physical Health', icon: Server },
            { id: 'ddi', label: 'DDI Infrastructure', icon: Radio },
            { id: 'soc_firewall', label: 'SOC Firewall & Threat', icon: Shield },
            { id: 'blueprints', label: 'Operational Blueprints', icon: TrendingUp }
          ].map(tab => {
            const Icon = tab.icon;
            const active = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id as any)}
                className={`py-3 px-3.5 text-xs font-mono font-bold flex items-center gap-2 border-b-2 transition-colors cursor-pointer whitespace-nowrap ${
                  active
                    ? 'border-cyan-400 text-cyan-400 bg-cyan-950/20'
                    : 'border-transparent text-slate-400 hover:text-slate-200 hover:border-slate-700'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {metrics && (
            <>
              {/* Tab 1: Data Plane */}
              {activeTab === 'data_plane' && (
                <div className="space-y-6">
                  {/* Top Highlight: MOS Rating & Flow Efficiency */}
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-[#1F2937] border border-[#374151] rounded-xl p-4 flex flex-col justify-between">
                      <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                        <span>ITU-T G.107 MOS Score</span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          metrics.mos_score >= 4.0 ? 'bg-emerald-950 text-emerald-300' :
                          metrics.mos_score >= 3.0 ? 'bg-amber-950 text-amber-300' :
                          'bg-rose-950 text-rose-300'
                        }`}>
                          {metrics.mos_score >= 4.0 ? 'EXCELLENT' : metrics.mos_score >= 3.0 ? 'FAIR' : 'POOR'}
                        </span>
                      </div>
                      <div className="my-3 flex items-baseline gap-2">
                        <span className="text-4xl font-black font-mono text-slate-100">
                          {metrics.mos_score.toFixed(2)}
                        </span>
                        <span className="text-xs text-slate-400 font-mono">/ 4.50</span>
                      </div>
                      <p className="text-[11px] text-slate-400">
                        Voice quality E-Model rating calculated from RTT ({metrics.rtt_ms}ms) & Jitter ({metrics.jitter_ms}ms)
                      </p>
                    </div>

                    <div className="bg-[#1F2937] border border-[#374151] rounded-xl p-4 flex flex-col justify-between">
                      <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                        <span>Goodput Efficiency</span>
                        <span className="text-cyan-400 font-bold">{metrics.flow_efficiency_pct.toFixed(1)}%</span>
                      </div>
                      <div className="my-3 flex items-baseline gap-2">
                        <span className="text-4xl font-black font-mono text-cyan-300">
                          {metrics.goodput_mbps.toFixed(0)}
                        </span>
                        <span className="text-xs text-slate-400 font-mono">Mbps</span>
                      </div>
                      <div className="w-full bg-slate-800 rounded-full h-2 overflow-hidden">
                        <div 
                          className="bg-cyan-500 h-full rounded-full transition-all"
                          style={{ width: `${Math.min(100, metrics.flow_efficiency_pct)}%` }}
                        />
                      </div>
                    </div>

                    <div className="bg-[#1F2937] border border-[#374151] rounded-xl p-4 flex flex-col justify-between">
                      <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                        <span>BGP Convergence Time</span>
                        <span className="text-amber-400 font-bold">{metrics.bgp_convergence_ms}ms</span>
                      </div>
                      <div className="my-3 flex items-baseline gap-2">
                        <span className="text-4xl font-black font-mono text-slate-100">
                          {metrics.bgp_convergence_ms < 1000 ? `${metrics.bgp_convergence_ms}ms` : `${(metrics.bgp_convergence_ms/1000).toFixed(1)}s`}
                        </span>
                      </div>
                      <p className="text-[11px] text-slate-400">
                        Sub-second convergence target: &lt; 200ms
                      </p>
                    </div>
                  </div>

                  {/* Latency & Loss Details */}
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-[#111827] border border-[#1F2937] rounded-lg p-3">
                      <span className="text-[10px] font-mono text-slate-400 block mb-1">ROUND TRIP TIME</span>
                      <span className="text-xl font-bold font-mono text-slate-200">{metrics.rtt_ms} ms</span>
                    </div>
                    <div className="bg-[#111827] border border-[#1F2937] rounded-lg p-3">
                      <span className="text-[10px] font-mono text-slate-400 block mb-1">JITTER</span>
                      <span className="text-xl font-bold font-mono text-slate-200">{metrics.jitter_ms} ms</span>
                    </div>
                    <div className="bg-[#111827] border border-[#1F2937] rounded-lg p-3">
                      <span className="text-[10px] font-mono text-slate-400 block mb-1">PACKET LOSS</span>
                      <span className={`text-xl font-bold font-mono ${metrics.packet_loss_pct > 1 ? 'text-rose-400' : 'text-emerald-400'}`}>
                        {metrics.packet_loss_pct}%
                      </span>
                    </div>
                    <div className="bg-[#111827] border border-[#1F2937] rounded-lg p-3">
                      <span className="text-[10px] font-mono text-slate-400 block mb-1">TCP RETRANSMITS</span>
                      <span className={`text-xl font-bold font-mono ${metrics.tcp_retrans_pct > 1 ? 'text-rose-400' : 'text-slate-200'}`}>
                        {metrics.tcp_retrans_pct}%
                      </span>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 2: Optical & Hardware */}
              {activeTab === 'hardware' && (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-[#1F2937] border border-[#374151] rounded-xl p-4">
                      <div className="flex items-center justify-between text-xs text-slate-400 font-mono mb-2">
                        <span>Optical Transceiver Power</span>
                        <span className={`font-bold ${metrics.optical_rx_dbm < -20 ? 'text-rose-400' : 'text-emerald-400'}`}>
                          {metrics.optical_rx_dbm < -20 ? 'SIGNAL DEGRADED' : 'OPTIMAL'}
                        </span>
                      </div>
                      <div className="my-2 flex items-baseline gap-2">
                        <span className="text-3xl font-black font-mono text-slate-100">{metrics.optical_rx_dbm}</span>
                        <span className="text-xs text-slate-400 font-mono">dBm</span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-2">
                        Safe operating range: -18.0 dBm to -8.0 dBm
                      </p>
                    </div>

                    <div className="bg-[#1F2937] border border-[#374151] rounded-xl p-4">
                      <div className="flex items-center justify-between text-xs text-slate-400 font-mono mb-2">
                        <span>ASIC Temperature</span>
                        <span className={`font-bold ${metrics.thermal_asic_c > 75 ? 'text-rose-400' : 'text-slate-300'}`}>
                          {metrics.thermal_asic_c}°C
                        </span>
                      </div>
                      <div className="my-2 flex items-baseline gap-2">
                        <span className="text-3xl font-black font-mono text-amber-300">{metrics.thermal_asic_c}</span>
                        <span className="text-xs text-slate-400 font-mono">°C</span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-2">
                        Chassis thermal: {metrics.thermal_chassis_c}°C (Warning &gt; 65°C)
                      </p>
                    </div>

                    <div className="bg-[#1F2937] border border-[#374151] rounded-xl p-4">
                      <div className="flex items-center justify-between text-xs text-slate-400 font-mono mb-2">
                        <span>MTBF & Failure Risk</span>
                        <span className="text-cyan-400 font-bold">{metrics.mtbf_hours.toLocaleString()} hrs</span>
                      </div>
                      <div className="my-2 flex items-baseline gap-2">
                        <span className={`text-3xl font-black font-mono ${metrics.hardware_failure_prob_pct > 5 ? 'text-rose-400' : 'text-slate-100'}`}>
                          {metrics.hardware_failure_prob_pct}%
                        </span>
                        <span className="text-xs text-slate-400 font-mono">failure prob</span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-2">
                        Config drift state: {metrics.config_drift_detected ? 'MODIFIED (DRIFT)' : 'IN SYNC'}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 3: DDI Infrastructure */}
              {activeTab === 'ddi' && (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-[#1F2937] border border-[#374151] rounded-xl p-4">
                      <div className="flex items-center justify-between text-xs text-slate-400 font-mono mb-2">
                        <span>DNS Query Latency</span>
                        <span className="text-cyan-400 font-bold">{metrics.dns_latency_ms} ms</span>
                      </div>
                      <div className="my-2 flex items-baseline gap-2">
                        <span className="text-3xl font-black font-mono text-slate-100">{metrics.dns_latency_ms}</span>
                        <span className="text-xs text-slate-400 font-mono">ms</span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-2">
                        Failure rate: {metrics.dns_failure_rate_pct}%
                      </p>
                    </div>

                    <div className="bg-[#1F2937] border border-[#374151] rounded-xl p-4">
                      <div className="flex items-center justify-between text-xs text-slate-400 font-mono mb-2">
                        <span>DHCP Pool Exhaustion</span>
                        <span className={`font-bold ${metrics.dhcp_pool_exhaustion_pct > 90 ? 'text-rose-400' : 'text-emerald-400'}`}>
                          {metrics.dhcp_pool_exhaustion_pct}%
                        </span>
                      </div>
                      <div className="my-2 flex items-baseline gap-2">
                        <span className="text-3xl font-black font-mono text-slate-100">{metrics.dhcp_pool_exhaustion_pct}</span>
                        <span className="text-xs text-slate-400 font-mono">%</span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-2">
                        Lease starvation threshold: 95%
                      </p>
                    </div>

                    <div className="bg-[#1F2937] border border-[#374151] rounded-xl p-4">
                      <div className="flex items-center justify-between text-xs text-slate-400 font-mono mb-2">
                        <span>NTP Clock Stratum</span>
                        <span className="text-violet-400 font-bold">Stratum {metrics.ntp_stratum}</span>
                      </div>
                      <div className="my-2 flex items-baseline gap-2">
                        <span className="text-3xl font-black font-mono text-slate-100">{metrics.ntp_offset_us}</span>
                        <span className="text-xs text-slate-400 font-mono">µs offset</span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-2">
                        Atomic clock source reference
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 4: SOC Firewall */}
              {activeTab === 'soc_firewall' && (
                <div className="space-y-6">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-[#1F2937] border border-[#374151] rounded-xl p-4">
                      <div className="flex items-center justify-between text-xs text-slate-400 font-mono mb-2">
                        <span>Firewall Session Utilization</span>
                        <span className={`font-bold ${metrics.firewall_session_utilization_pct > 80 ? 'text-rose-400' : 'text-emerald-400'}`}>
                          {metrics.firewall_session_utilization_pct}%
                        </span>
                      </div>
                      <div className="my-2 flex items-baseline gap-2">
                        <span className="text-3xl font-black font-mono text-slate-100">{metrics.firewall_session_utilization_pct}</span>
                        <span className="text-xs text-slate-400 font-mono">%</span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-2">
                        State table capacity: 1,000,000 active flows
                      </p>
                    </div>

                    <div className="bg-[#1F2937] border border-[#374151] rounded-xl p-4">
                      <div className="flex items-center justify-between text-xs text-slate-400 font-mono mb-2">
                        <span>Shadow Rules Audited</span>
                        <span className="text-amber-400 font-bold">{metrics.shadow_rules_count} detected</span>
                      </div>
                      <div className="my-2 flex items-baseline gap-2">
                        <span className="text-3xl font-black font-mono text-amber-300">{metrics.shadow_rules_count}</span>
                        <span className="text-xs text-slate-400 font-mono">rules</span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-2">
                        DPI bypass percentage: {metrics.deep_packet_inspection_bypass_pct}%
                      </p>
                    </div>

                    <div className="bg-[#1F2937] border border-[#374151] rounded-xl p-4">
                      <div className="flex items-center justify-between text-xs text-slate-400 font-mono mb-2">
                        <span>C2 Beacon Threat Score</span>
                        <span className={`font-bold ${metrics.c2_beacon_threat_score > 70 ? 'text-rose-400' : 'text-slate-300'}`}>
                          {metrics.c2_beacon_threat_score > 70 ? 'ACTIVE THREAT' : 'LOW RISK'}
                        </span>
                      </div>
                      <div className="my-2 flex items-baseline gap-2">
                        <span className={`text-3xl font-black font-mono ${metrics.c2_beacon_threat_score > 70 ? 'text-rose-400' : 'text-slate-100'}`}>
                          {metrics.c2_beacon_threat_score}
                        </span>
                        <span className="text-xs text-slate-400 font-mono">/ 100</span>
                      </div>
                      <p className="text-[11px] text-slate-400 mt-2">
                        Micro-segmentation quarantines: {metrics.micro_segmentation_quarantines}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Tab 5: Blueprints */}
              {activeTab === 'blueprints' && (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div className="bg-[#1F2937] border border-[#374151] rounded-xl p-5">
                      <div className="flex items-center gap-2 mb-3">
                        <Radio className="w-4 h-4 text-cyan-400" />
                        <h4 className="text-xs font-bold text-slate-100 font-mono uppercase">
                          Tier 1: Real-Time Tactical
                        </h4>
                      </div>
                      <p className="text-xs text-slate-300 mb-3 leading-relaxed">
                        Continuous sub-second streaming for automated remediation, link flap dampening, and firewall drop alarms.
                      </p>
                      <div className="text-[11px] font-mono text-cyan-300 bg-[#111827] p-2.5 rounded border border-[#374151]">
                        Cadence: 1s – 5s fast polling<br/>
                        Target: Splunk ITSI / ES Real-time
                      </div>
                    </div>

                    <div className="bg-[#1F2937] border border-[#374151] rounded-xl p-5">
                      <div className="flex items-center gap-2 mb-3">
                        <TrendingUp className="w-4 h-4 text-violet-400" />
                        <h4 className="text-xs font-bold text-slate-100 font-mono uppercase">
                          Tier 2: Weekly Trends
                        </h4>
                      </div>
                      <p className="text-xs text-slate-300 mb-3 leading-relaxed">
                        Capacity forecasting, MTBF degradation rate, jitter trends, and bandwidth growth analysis.
                      </p>
                      <div className="text-[11px] font-mono text-violet-300 bg-[#111827] p-2.5 rounded border border-[#374151]">
                        Cadence: 1h summary rollups<br/>
                        Target: NOC Capacity Planning
                      </div>
                    </div>

                    <div className="bg-[#1F2937] border border-[#374151] rounded-xl p-5">
                      <div className="flex items-center gap-2 mb-3">
                        <Shield className="w-4 h-4 text-emerald-400" />
                        <h4 className="text-xs font-bold text-slate-100 font-mono uppercase">
                          Tier 3: Annual Strategic
                        </h4>
                      </div>
                      <p className="text-xs text-slate-300 mb-3 leading-relaxed">
                        Regulatory compliance (NIST 800-53, CIS Controls), vendor lifecycle refresh, and executive SLA attainment.
                      </p>
                      <div className="text-[11px] font-mono text-emerald-300 bg-[#111827] p-2.5 rounded border border-[#374151]">
                        Cadence: Monthly / Quarterly audits<br/>
                        Target: Executive & Audit Reports
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-[#374151] bg-[#1F2937] flex items-center justify-between text-xs text-slate-400 font-mono">
          <span>NetSpout NOC & SOC Telemetry Engine</span>
          <span>Author: Mahamudul Chowdhury (machowdhury@yahoo.com)</span>
        </div>
      </div>
    </div>
  );
};
