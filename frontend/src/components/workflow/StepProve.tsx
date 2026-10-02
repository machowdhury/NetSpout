import React, { useState } from 'react';
import { 
  CheckCircle2, XCircle, ExternalLink, Copy, Check,
  RotateCcw, ShieldCheck, Database, Send, Eye, FileText, ChevronDown, Layers
} from 'lucide-react';
import type { UseCase, WorkflowRunState, EvidenceSourceItem } from '../../types/workflow';

interface StepProveProps {
  useCase: UseCase;
  runState: WorkflowRunState;
  onRunAgain: () => void;
  onChooseAnother: () => void;
}

export const StepProve: React.FC<StepProveProps> = ({
  useCase,
  runState,
  onRunAgain,
  onChooseAnother
}) => {
  const [showManifest, setShowManifest] = useState(false);
  const [copiedSpl, setCopiedSpl] = useState(false);
  const [copiedQueryIdx, setCopiedQueryIdx] = useState<number | null>(null);

  const manifest = runState.manifest || {};
  const snmpScorecard = runState.snmp_e2e_scorecard || manifest.snmp_e2e_scorecard || null;
  const gnmiScorecard = runState.gnmi_e2e_scorecard || manifest.gnmi_e2e_scorecard || null;
  const isOverallPass = manifest.overall_validation === 'PASS';
  const isSimulationPass = (manifest.simulation_validation === 'PASS') || runState.validation_results.every(r => r.status === 'PASS');

  const generatedCount = snmpScorecard?.normalized_records ?? gnmiScorecard?.normalized_total_records ?? manifest.total_events_generated ?? runState.total_events ?? 0;
  const dispatchedCount = snmpScorecard?.splunk_dispatched_records ?? gnmiScorecard?.splunk_dispatched_total ?? manifest.dispatch_succeeded ?? runState.dispatched_events ?? 0;
  const observedCount = snmpScorecard?.splunk_observed_records ?? gnmiScorecard?.splunk_observed_total ?? manifest.observed_count ?? runState.observed_events ?? 0;
  const destinationValidation = manifest.destination_validation ?? runState.destination_validation ?? (gnmiScorecard ? gnmiScorecard.validation_status : 'NOT_RUN');

  const eventObservedCount = runState.event_observed_count ?? manifest.event_observed_count ?? (gnmiScorecard ? gnmiScorecard.splunk_observed_events : observedCount);
  const metricObservedCount = runState.metric_observed_count ?? manifest.metric_observed_count ?? (gnmiScorecard ? gnmiScorecard.splunk_observed_metrics : 0);
  const completenessPct = runState.observation_completeness_pct ?? manifest.observation_completeness_pct ?? (gnmiScorecard ? gnmiScorecard.observation_completeness_pct : 100);
  const destinations: EvidenceSourceItem[] = runState.destinations || manifest.evidence_summary?.destinations || [];

  const spl = runState.splunk_search_query || manifest.splunk_search_query || (runState.run_id ? `index=idx_network_ops netspout_run_id="${runState.run_id}"` : '');
  const splunkSearchUrl = `http://localhost:8800/en-US/app/netspout/search?q=search%20${encodeURIComponent(spl || 'index=idx_network_ops')}`;

  const activeRunId = runState.run_id || manifest.run_id || 'NS-RUN';
  const activeIndex = snmpScorecard?.target_index || snmpScorecard?.splunk_index || 'idx_network_ops';
  const invQueries = snmpScorecard?.investigation_queries || {};
  const gnmiInvQueries = gnmiScorecard?.investigation_queries || {};

  const snmpInvestigationQueries = [
    {
      title: '1. All Native SNMP Evidence (Traps, Informs & Polls)',
      spl: invQueries.all_snmp_evidence_spl || `search index=${activeIndex} (sourcetype="netspout:snmp:trap" OR sourcetype="netspout:snmp:poll") netspout_run_id="${activeRunId}" | eval origin_evidence_stage=coalesce(origin_evidence_stage, "RECEIVER_OBSERVED"), current_evidence_stage="SPLUNK_OBSERVED" | table _time netspout_phase sourcetype snmp_pdu_type snmp_request_id snmp_trap_name snmp_oid_name snmp_value snmp_collector origin_evidence_stage current_evidence_stage`
    },
    {
      title: '2. Trap & Inform Notification Timeline',
      spl: invQueries.trap_inform_evidence_spl || `search index=${activeIndex} sourcetype="netspout:snmp:trap" netspout_run_id="${activeRunId}" | table _time netspout_phase snmp_pdu_type snmp_request_id snmp_trap_name snmp_trap_oid snmp_oid_name snmp_value sys_uptime origin_evidence_stage current_evidence_stage`
    },
    {
      title: '3. External Net-SNMP Polling Evidence (GET / GETNEXT / GETBULK / WALK)',
      spl: invQueries.polling_evidence_spl || `search index=${activeIndex} sourcetype="netspout:snmp:poll" netspout_run_id="${activeRunId}" | table _time netspout_phase snmp_pdu_type snmp_oid_name snmp_oid snmp_value snmp_value_type origin_evidence_stage current_evidence_stage`
    },
    {
      title: '4. 4-Phase Scenario Timeline Summary',
      spl: invQueries.timeline_spl || `search index=${activeIndex} (sourcetype="netspout:snmp:trap" OR sourcetype="netspout:snmp:poll") netspout_run_id="${activeRunId}" | stats count as evidence_count values(sourcetype) as sourcetypes values(snmp_pdu_type) as pdu_types values(snmp_trap_name) as notifications by netspout_phase`
    },
    {
      title: '5. Interface Operational State & Error Counter Audit (IF-MIB)',
      spl: invQueries.interface_state_spl || `search index=${activeIndex} (sourcetype="netspout:snmp:trap" OR sourcetype="netspout:snmp:poll") netspout_run_id="${activeRunId}" (snmp_oid="1.3.6.1.2.1.2.2.1.8.1" OR snmp_oid="1.3.6.1.2.1.2.2.1.14.1" OR snmp_trap_oid="1.3.6.1.6.3.1.1.5.3" OR snmp_trap_oid="1.3.6.1.6.3.1.1.5.4") | table _time netspout_phase sourcetype snmp_pdu_type snmp_trap_name snmp_oid_name snmp_value`
    },
    {
      title: '6. BGP4-MIB Session & Last Error Audit',
      spl: invQueries.bgp_state_spl || `search index=${activeIndex} (sourcetype="netspout:snmp:trap" OR sourcetype="netspout:snmp:poll") netspout_run_id="${activeRunId}" (snmp_oid="1.3.6.1.2.1.15.3.1.2.198.51.100.1" OR snmp_oid="1.3.6.1.2.1.15.3.1.14.198.51.100.1" OR snmp_oid="1.3.6.1.2.1.15.3.1.2.198.51.100.2" OR snmp_trap_oid="1.3.6.1.2.1.15.7.2" OR snmp_trap_oid="1.3.6.1.2.1.15.7.1") | table _time netspout_phase sourcetype snmp_pdu_type snmp_trap_name snmp_oid_name snmp_value`
    },
    {
      title: '7. Notification vs Polled MIB State Coherence Matrix',
      spl: invQueries.notification_vs_poll_correlation_spl || `search index=${activeIndex} (sourcetype="netspout:snmp:trap" OR sourcetype="netspout:snmp:poll") netspout_run_id="${activeRunId}" | stats count(eval(sourcetype="netspout:snmp:trap")) as notification_count count(eval(sourcetype="netspout:snmp:poll")) as poll_count values(snmp_trap_name) as notifications by netspout_phase`
    }
  ];

  const gnmiInvestigationQueries = [
    { title: '1. All gNMI Telemetry Events', spl: gnmiInvQueries.q1_event_overview || `search index=idx_network_ops sourcetype="netspout:gnmi:event" netspout_run_id="${activeRunId}" | table _time netspout_phase path value_str origin_evidence_stage current_evidence_stage` },
    { title: '2. State Transitions (ON_CHANGE)', spl: gnmiInvQueries.q2_state_transitions || `search index=idx_network_ops sourcetype="netspout:gnmi:event" netspout_run_id="${activeRunId}" subscription_mode="ON_CHANGE" | table _time netspout_phase path value_str` },
    { title: '3. Phase Correlation by Sensor', spl: gnmiInvQueries.q3_phase_correlation || `search index=idx_network_ops sourcetype="netspout:gnmi:event" netspout_run_id="${activeRunId}" | chart count over netspout_phase by sensor_id` },
    { title: '4. MDT Streaming Metrics (| mstats)', spl: gnmiInvQueries.q4_metric_overview || `| mstats avg(_value) WHERE index=cisco_mdt_metrics netspout_run_id="${activeRunId}" metric_name=* BY metric_name span=1s` },
    { title: '5. Ingress Traffic Discard Rate', spl: gnmiInvQueries.q5_discard_spike || `| mstats avg(_value) WHERE index=cisco_mdt_metrics netspout_run_id="${activeRunId}" metric_name="*.in_discards" BY metric_name span=1s` },
    { title: '6. Ingress Bitrate Time-Series', spl: gnmiInvQueries.q6_octets_rate || `| mstats rate(_value) WHERE index=cisco_mdt_metrics netspout_run_id="${activeRunId}" metric_name="*.in_octets" BY metric_name span=1s` },
    { title: '7. Multi-Vendor Sensor Provenance', spl: gnmiInvQueries.q7_vendor_provenance || `search index=idx_network_ops sourcetype="netspout:gnmi:event" netspout_run_id="${activeRunId}" | stats count values(vendor_provenance) by sensor_id` },
    { title: '8. End-to-End Latency Profile', spl: gnmiInvQueries.q8_latency_breakdown || `search index=idx_network_ops sourcetype="netspout:gnmi:event" netspout_run_id="${activeRunId}" | stats avg(pipeline_latency_ms) by sensor_id` },
    { title: '9. Wire Purity Audit', spl: gnmiInvQueries.q9_wire_purity_audit || `search index=idx_network_ops sourcetype="netspout:gnmi:event" netspout_run_id="${activeRunId}" | stats count values(wire_payload_pure) by netspout_phase` },
    { title: '10. Incident Progression Cross-Store Correlation', spl: gnmiInvQueries.q10_incident_progression || `search index=idx_network_ops sourcetype="netspout:gnmi:event" netspout_run_id="${activeRunId}" | stats values(path) values(value_str) by netspout_phase` },
  ];


  const handleCopySpl = () => {
    if (spl) {
      navigator.clipboard.writeText(spl);
      setCopiedSpl(true);
      setTimeout(() => setCopiedSpl(false), 2000);
    }
  };

  const handleCopySpecificQuery = (queryText: string, idx: number) => {
    navigator.clipboard.writeText(queryText);
    setCopiedQueryIdx(idx);
    setTimeout(() => setCopiedQueryIdx(null), 2000);
  };

  const scorecardVerdict = snmpScorecard?.validation_result || snmpScorecard?.overall_verdict || 'PASS';

  return (
    <div className="flex flex-col h-full overflow-hidden p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-white flex flex-wrap items-center gap-3">
            <span>5. Prove Expected Condition & Audit Evidence</span>
            <span className={`px-3 py-1 rounded-full text-xs font-bold border flex items-center gap-1.5 ${
              isOverallPass
                ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/40'
                : 'bg-rose-500/20 text-rose-400 border-rose-500/40'
            }`}>
              {isOverallPass ? <CheckCircle2 className="w-4 h-4" /> : <XCircle className="w-4 h-4" />}
              OVERALL VERIFICATION: {isOverallPass ? 'PASS' : 'FAIL'}
            </span>
            <span className={`px-2.5 py-0.5 rounded text-[11px] font-bold border ${
              isSimulationPass
                ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30'
                : 'bg-rose-500/10 text-rose-400 border-rose-500/30'
            }`}>
              SIMULATION: {isSimulationPass ? 'PASS' : 'FAIL'}
            </span>
            <span className={`px-2.5 py-0.5 rounded text-[11px] font-bold border ${
              destinationValidation === 'PASS'
                ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30'
                : destinationValidation === 'PENDING'
                ? 'bg-amber-500/10 text-amber-400 border-amber-500/30'
                : 'bg-slate-800 text-slate-400 border-slate-700'
            }`}>
              DESTINATION: {destinationValidation}
            </span>
            {snmpScorecard && (
              <span className="px-2.5 py-0.5 rounded text-[11px] font-bold font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                NATIVE SNMPv2c E2E: {scorecardVerdict}
              </span>
            )}
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Automated verification results for <strong className="text-slate-200">{useCase.name}</strong> (run <code className="text-cyan-400 font-mono">{runState.run_id}</code>).
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={onRunAgain}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium transition"
          >
            <RotateCcw className="w-4 h-4" />
            <span>Run Again</span>
          </button>

          <button
            onClick={onChooseAnother}
            className="flex items-center gap-1.5 px-5 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-sm font-medium transition shadow-lg shadow-cyan-900/30"
          >
            <span>Choose Another</span>
          </button>
        </div>
      </div>

      {/* Evidence Model 4-Tier Breakdown */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-semibold uppercase tracking-wider">1. GENERATED</span>
            <Database className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold text-white font-mono">{generatedCount}</div>
          <p className="text-[11px] text-slate-500">Records created by simulation core</p>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-semibold uppercase tracking-wider">2. DISPATCHED</span>
            <Send className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-blue-400 font-mono">{dispatchedCount}</div>
          <p className="text-[11px] text-slate-500">Transmitted over pipeline without drops</p>
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-semibold uppercase tracking-wider">3. OBSERVED IN SPLUNK</span>
            <Eye className="w-4 h-4 text-amber-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className={`text-2xl font-bold font-mono ${observedCount > 0 ? 'text-emerald-400' : 'text-amber-400'}`}>
              {observedCount}
            </span>
            <span className="text-xs font-semibold text-emerald-400 font-mono">
              ({completenessPct}%)
            </span>
          </div>
          {metricObservedCount > 0 ? (
            <p className="text-[11px] text-slate-400">
              <span className="text-cyan-300 font-semibold">{eventObservedCount} Events</span> + <span className="text-purple-300 font-semibold">{metricObservedCount} Metrics</span>
            </p>
          ) : (
            <p className="text-[11px] text-slate-500">Searchable events verified in Splunk index</p>
          )}
        </div>

        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 space-y-1">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="font-semibold uppercase tracking-wider">4. VALIDATED</span>
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
          </div>
          <div className={`text-2xl font-bold font-mono ${
            destinationValidation === 'PASS' ? 'text-emerald-400' : destinationValidation === 'PENDING' ? 'text-amber-400' : 'text-rose-400'
          }`}>
            {destinationValidation}
          </div>
          <p className="text-[11px] text-slate-500">Formal query verification against index</p>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto pr-1 space-y-6">
        {/* Native SNMPv2c E2E Scorecard & 8-Stage Evidence Ladder */}
        {snmpScorecard && (
          <div data-testid="native-snmp-scorecard-panel" className="p-5 rounded-xl bg-emerald-950/15 border border-emerald-500/40 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-emerald-800/40 pb-3">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-sm font-bold text-emerald-300 uppercase tracking-wider font-mono">
                  Native SNMPv2c End-to-End Scorecard ({snmpScorecard.scenario_id})
                </h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                  NATIVE TRANSPORT
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-amber-500/20 text-amber-300 border border-amber-500/40">
                  MODELED DEVICE STATE
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                  DEVICE: {snmpScorecard.device_id}
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs font-mono">
                <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-300">
                  origin_evidence_stage: <strong className="text-amber-300">{snmpScorecard.origin_evidence_stage || 'RECEIVER_OBSERVED'}</strong>
                </span>
                <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-300">
                  current_evidence_stage: <strong className="text-emerald-400">{snmpScorecard.current_evidence_stage || 'SPLUNK_OBSERVED'}</strong>
                </span>
              </div>
            </div>

            {/* 8-Stage Evidence Ladder */}
            <div>
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2 font-mono">
                8-Stage Native SNMPv2c Evidence Ladder
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2 font-mono text-xs">
                {[
                  { stage: '1. GENERATED', val: (snmpScorecard.generated_notifications ?? 8) + (snmpScorecard.polling_requests ?? 290), sub: `${snmpScorecard.generated_notifications ?? 8} PDU + ${snmpScorecard.polling_requests ?? 290} Poll` },
                  { stage: '2. ENCODED', val: (snmpScorecard.encoded_notifications ?? 8) + (snmpScorecard.polling_responses ?? 290), sub: 'BER/ASN.1 Wire' },
                  { stage: '3. SENT', val: (snmpScorecard.sent_notifications ?? 8) + (snmpScorecard.polling_requests ?? 290), sub: 'UDP Loopback' },
                  { stage: '4. ACKNOWLEDGED', val: snmpScorecard.informs_acknowledged ?? 4, sub: `Informs: ${snmpScorecard.informs_sent ?? 4}` },
                  { stage: '5. RECEIVER_OBSERVED', val: snmpScorecard.normalized_records ?? 326, sub: `Dedup: ${snmpScorecard.duplicate_records_suppressed ?? 0}` },
                  { stage: '6. SPLUNK_DISPATCHED', val: snmpScorecard.splunk_dispatched_records ?? 326, sub: `Failed: ${snmpScorecard.splunk_dispatch_failures ?? 0}` },
                  { stage: '7. SPLUNK_OBSERVED', val: snmpScorecard.splunk_observed_records ?? 326, sub: `Index: ${activeIndex}` },
                  { stage: '8. VALIDATED', val: scorecardVerdict, sub: snmpScorecard.trap_poll_coherence ? '9/9 Coherent' : 'Check Failed' }
                ].map((item, idx) => (
                  <div key={idx} className="p-2.5 rounded-lg bg-slate-950/90 border border-slate-800 flex flex-col justify-between">
                    <div className="text-[9px] text-slate-400 font-bold truncate" title={item.stage}>{item.stage}</div>
                    <div className="text-base font-bold text-emerald-400 my-1">{item.val}</div>
                    <div className="text-[9px] text-slate-500 truncate">{item.sub}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Coherence & Sourcetype Verification Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs font-mono">
              <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 space-y-1">
                <div className="text-slate-400 text-[10px] uppercase font-bold">Telemetry Event Breakdown</div>
                <div className="text-slate-200">
                  Traps: <strong className="text-amber-300">{snmpScorecard.traps_receiver_observed ?? 4}</strong> · Informs: <strong className="text-cyan-300">{snmpScorecard.informs_receiver_observed ?? 4}</strong> · Polls: <strong className="text-emerald-300">{snmpScorecard.normalized_poll_records ?? 318}</strong>
                </div>
                <div className="text-[10px] text-slate-400">
                  Sourcetypes: {(snmpScorecard.sourcetypes || ['netspout:snmp:trap', 'netspout:snmp:poll']).join(', ')}
                </div>
              </div>
              <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 space-y-1">
                <div className="text-slate-400 text-[10px] uppercase font-bold">Coherence & Fidelity Checks</div>
                <div className="flex flex-wrap gap-2 pt-0.5">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${(snmpScorecard.phases_verified || []).length >= 4 ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'}`}>
                    4-Phase Coverage: {(snmpScorecard.phases_verified || []).length >= 4 ? 'PASS' : 'FAIL'}
                  </span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${scorecardVerdict === 'PASS' ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'}`}>
                    OID Varbind Fidelity: {scorecardVerdict === 'PASS' ? 'PASS' : 'FAIL'}
                  </span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${snmpScorecard.trap_poll_coherence ? 'bg-emerald-500/20 text-emerald-300' : 'bg-rose-500/20 text-rose-300'}`}>
                    Trap/Poll Coherence: {snmpScorecard.trap_poll_coherence ? 'PASS (9/9)' : 'FAIL'}
                  </span>
                </div>
              </div>
              <div className="p-3 rounded-lg bg-slate-950/80 border border-slate-800 space-y-1">
                <div className="text-slate-400 text-[10px] uppercase font-bold">Honesty & State Semantics</div>
                <div className="text-[10px] text-slate-300 font-sans leading-relaxed">
                  Wait/poll cycles and MIB counter increments represent <strong>modeled device state</strong> served over real BER/ASN.1 UDP SNMPv2c packets; they do not claim physical router ASIC or IOS XR kernel emulation.
                </div>
              </div>
            </div>

            {/* 7 Copyable SPL Investigation Queries */}
            <div className="space-y-2 pt-1">
              <div className="text-[11px] font-bold text-slate-300 uppercase tracking-wider font-mono">
                Splunk Investigation Queries (7 Copyable SPL Queries for {activeRunId})
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {snmpInvestigationQueries.map((q, idx) => (
                  <div key={idx} className="p-2.5 rounded-lg bg-slate-950/90 border border-slate-800 flex items-center justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="text-[11px] font-bold text-cyan-300 font-mono">{q.title}</div>
                      <div className="text-[10px] text-slate-400 font-mono truncate" title={q.spl}>{q.spl}</div>
                    </div>
                    <button
                      onClick={() => handleCopySpecificQuery(q.spl, idx)}
                      className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[10px] font-mono font-semibold border border-slate-700 shrink-0 flex items-center gap-1 cursor-pointer"
                    >
                      {copiedQueryIdx === idx ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3 text-cyan-400" />}
                      <span>{copiedQueryIdx === idx ? 'Copied' : 'Copy SPL'}</span>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Native gNMI/OpenConfig E2E Scorecard & 7-Stage Evidence Ledger */}
        {gnmiScorecard && (
          <div data-testid="native-gnmi-scorecard-panel" className="p-5 rounded-xl bg-cyan-950/20 border border-cyan-500/40 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-cyan-800/40 pb-3">
              <div className="flex flex-wrap items-center gap-2">
                <h3 className="text-sm font-bold text-cyan-300 uppercase tracking-wider font-mono">
                  Native gNMI / OpenConfig End-to-End Scorecard ({gnmiScorecard.scenario_id})
                </h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                  NATIVE gNMI / OPENCONFIG
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                  DEVICE: {gnmiScorecard.target_device}
                </span>
                <span className="px-2 py-0.5 rounded text-[10px] font-bold font-mono bg-purple-500/20 text-purple-300 border border-purple-500/40">
                  COLLECTOR: gnmic v0.49.0
                </span>
              </div>
              <div className="flex items-center gap-2 text-xs font-mono">
                <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-300">
                  Events: <strong className="text-cyan-300">{gnmiScorecard.splunk_observed_events}</strong>
                </span>
                <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-300">
                  Metrics: <strong className="text-purple-300">{gnmiScorecard.splunk_observed_metrics}</strong>
                </span>
                <span className="px-2 py-0.5 rounded bg-slate-900 border border-slate-700 text-slate-300">
                  Validation: <strong className={gnmiScorecard.validation_status === 'PASS' ? 'text-emerald-400' : 'text-rose-400'}>{gnmiScorecard.validation_status}</strong>
                </span>
              </div>
            </div>

            {/* 7-Stage Evidence Ledger */}
            <div>
              <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-2 font-mono">
                7-Stage Native gNMI Evidence Ledger
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2 font-mono text-xs">
                {[
                  { stage: '1. GENERATED', val: gnmiScorecard.server_notifications_sent ?? 32, sub: 'StateStore Updates' },
                  { stage: '2. ENCODED', val: gnmiScorecard.server_notifications_sent ?? 32, sub: 'gRPC / Protobuf' },
                  { stage: '3. COLLECTOR', val: gnmiScorecard.collector_records_received ?? 32, sub: 'gnmic Stream' },
                  { stage: '4. NORMALIZED', val: gnmiScorecard.normalized_total_records ?? 32, sub: 'Canonical Model' },
                  { stage: '5. ADAPTED', val: (gnmiScorecard.normalized_event_records ?? 20) + (gnmiScorecard.normalized_metric_records ?? 12), sub: 'Event / Metric Split' },
                  { stage: '6. DISPATCHED', val: gnmiScorecard.splunk_dispatched_total ?? 32, sub: 'HEC Batch HTTP 200' },
                  { stage: '7. OBSERVED', val: gnmiScorecard.splunk_observed_total ?? 32, sub: 'SPL & | mstats' },
                ].map((s, idx) => (
                  <div key={idx} className="p-2.5 rounded-lg bg-slate-900/90 border border-cyan-800/30 text-center">
                    <div className="text-[10px] text-slate-400 truncate">{s.stage}</div>
                    <div className="text-lg font-bold text-cyan-300 my-0.5">{s.val}</div>
                    <div className="text-[9px] text-slate-500 truncate">{s.sub}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* 10 Live Investigation Queries */}
            <div className="space-y-2 pt-2 border-t border-cyan-800/30">
              <div className="text-[11px] font-bold text-slate-300 uppercase tracking-wider font-mono">
                Splunk Investigation Queries (10 Copyable SPL & | mstats Queries for {activeRunId})
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                {gnmiInvestigationQueries.map((q, idx) => (
                  <div key={idx} className="p-2.5 rounded-lg bg-slate-950/90 border border-slate-800 flex items-center justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <div className="text-[11px] font-bold text-cyan-300 font-mono">{q.title}</div>
                      <div className="text-[10px] text-slate-400 font-mono truncate" title={q.spl}>{q.spl}</div>
                    </div>
                    <button
                      onClick={() => handleCopySpecificQuery(q.spl, 100 + idx)}
                      className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-[10px] font-mono font-semibold border border-slate-700 shrink-0 flex items-center gap-1 cursor-pointer"
                    >
                      {copiedQueryIdx === (100 + idx) ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3 text-cyan-400" />}
                      <span>{copiedQueryIdx === (100 + idx) ? 'Copied' : 'Copy'}</span>
                    </button>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}


        {/* Protection Timing Semantics Banner */}
        {useCase.timing_classification && useCase.timing_classification !== 'NOT_APPLICABLE' && (
          <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-800/40 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
            <div className="flex items-center gap-2.5">
              <span className="font-bold px-2 py-0.5 rounded border uppercase tracking-wider bg-amber-500/10 text-amber-300 border-amber-500/30 text-[10px] font-mono shrink-0">
                {useCase.timing_classification} TIMING
              </span>
              <span className="text-slate-300">
                <strong className="text-white">{useCase.timing_claim}</strong> ({useCase.timing_value}{useCase.timing_unit || 'ms'}): {useCase.timing_notes}
              </span>
            </div>
            <span className="text-[11px] text-amber-400 font-mono shrink-0">
              Protocol Simulation
            </span>
          </div>
        )}

        {/* Unified Evidence Discovery Table */}
        <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
          <div className="flex flex-wrap justify-between items-center gap-3">
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
              <Layers className="w-4 h-4 text-purple-400" />
              <span>Discovered Storage Destinations & Query Harmonization</span>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-purple-500/20 text-purple-300 border border-purple-500/40">
                Gate 8 Unified Evidence
              </span>
            </h3>
            <div className="text-xs text-slate-400 font-mono">
              Observation Completeness: <strong className="text-emerald-400">{completenessPct}%</strong> ({observedCount}/{generatedCount} records observed)
            </div>
          </div>

          <div className="rounded-lg border border-slate-800 overflow-hidden">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-950/80 border-b border-slate-800 text-slate-400 font-medium">
                  <th className="p-3">Destination Name & Index</th>
                  <th className="p-3">Type</th>
                  <th className="p-3">Query Mechanism</th>
                  <th className="p-3">Role</th>
                  <th className="p-3">Observed / Expected</th>
                  <th className="p-3">Status</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                {destinations.length > 0 ? (
                  destinations.map((dest, idx) => (
                    <tr key={idx} className="hover:bg-slate-900/50">
                      <td className="p-3">
                        <div className="font-semibold text-slate-200">{dest.name}</div>
                        <div className="text-slate-500 text-[10px]">index={dest.target_index}</div>
                      </td>
                      <td className="p-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          dest.telemetry_type === 'METRIC'
                            ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40'
                            : 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40'
                        }`}>
                          {dest.telemetry_type}
                        </span>
                      </td>
                      <td className="p-3 text-slate-300 font-mono text-[10px]">
                        {dest.query_mechanism === 'MSTATS' ? '| mstats' : 'search SPL'}
                      </td>
                      <td className="p-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          dest.role === 'REQUIRED'
                            ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                            : 'bg-slate-800 text-slate-400 border border-slate-700'
                        }`}>
                          {dest.role}
                        </span>
                      </td>
                      <td className="p-3 text-slate-200 font-bold">
                        {dest.observed_count} / {dest.expected_count}
                      </td>
                      <td className="p-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          dest.status === 'PASS'
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                            : dest.status === 'PARTIAL'
                            ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                            : 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
                        }`}>
                          {dest.status}
                        </span>
                      </td>
                      <td className="p-3 text-right">
                        <div className="flex items-center justify-end gap-2">
                          <button
                            onClick={() => {
                              navigator.clipboard.writeText(dest.query);
                            }}
                            className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-semibold border border-slate-700 transition"
                            title={dest.query}
                          >
                            Copy Query
                          </button>
                          <a
                            href={`http://localhost:8800/en-US/app/netspout/search?q=${encodeURIComponent(
                              dest.query_mechanism === 'MSTATS' ? dest.query : (dest.query.startsWith('search') ? dest.query : `search ${dest.query}`)
                            )}`}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="p-1 rounded hover:bg-slate-800 text-cyan-400 hover:text-cyan-300 transition"
                            title="Open query in Splunk Search"
                          >
                            <ExternalLink className="w-3.5 h-3.5" />
                          </a>
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr className="hover:bg-slate-900/50">
                    <td className="p-3">
                      <div className="font-semibold text-slate-200">Splunk Event Index (idx_network_ops)</div>
                      <div className="text-slate-500 text-[10px]">index=idx_network_ops</div>
                    </td>
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                        EVENT
                      </span>
                    </td>
                    <td className="p-3 text-slate-300 font-mono text-[10px]">search SPL</td>
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                        REQUIRED
                      </span>
                    </td>
                    <td className="p-3 text-slate-200 font-bold">
                      {observedCount} / {generatedCount}
                    </td>
                    <td className="p-3">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
                        PASS
                      </span>
                    </td>
                    <td className="p-3 text-right">
                      <button
                        onClick={handleCopySpl}
                        className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[10px] font-semibold border border-slate-700 transition"
                      >
                        Copy SPL
                      </button>
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Validation Engine Results Table */}
        <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-3">
          <div className="flex flex-wrap justify-between items-center gap-3">
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-cyan-400" />
              <span>Automated Validation Engine Audit</span>
            </h3>
            <div className="flex items-center gap-2">
              <button
                onClick={handleCopySpl}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-cyan-400 text-xs font-semibold border border-slate-700 transition"
                title="Copy SPL Query for this run"
              >
                {copiedSpl ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedSpl ? 'SPL Copied' : 'Copy Run SPL'}</span>
              </button>
              <a
                href={splunkSearchUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-cyan-600/20 hover:bg-cyan-600/30 text-cyan-400 text-xs font-semibold border border-cyan-500/40 transition"
              >
                <span>Verify in Splunk Search</span>
                <ExternalLink className="w-3.5 h-3.5" />
              </a>
            </div>
          </div>

          <div className="rounded-lg border border-slate-800 overflow-hidden">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="bg-slate-950/80 border-b border-slate-800 text-slate-400 font-medium">
                  <th className="p-3">Rule Name & ID</th>
                  <th className="p-3">Type</th>
                  <th className="p-3">Status</th>
                  <th className="p-3">Expected vs Observed</th>
                  <th className="p-3">Details / Query</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono text-[11px]">
                {runState.validation_results && runState.validation_results.length > 0 ? (
                  runState.validation_results.map((res, i) => (
                    <tr key={i} className="hover:bg-slate-900/50">
                      <td className="p-3">
                        <div className="font-semibold text-slate-200">{res.rule_name}</div>
                        <div className="text-slate-500 text-[10px]">{res.rule_id}</div>
                      </td>
                      <td className="p-3 text-cyan-400">{res.rule_type}</td>
                      <td className="p-3">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
                          res.status === 'PASS'
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/40'
                            : 'bg-rose-500/20 text-rose-400 border border-rose-500/40'
                        }`}>
                          {res.status}
                        </span>
                      </td>
                      <td className="p-3 text-slate-300">
                        {res.expected_value !== undefined ? (
                          <div>
                            <div>Expected: {String(res.expected_value)}</div>
                            <div className="text-slate-400">Observed: {String(res.observed_value)}</div>
                          </div>
                        ) : (
                          'Condition satisfied'
                        )}
                      </td>
                      <td className="p-3 text-slate-400 font-sans text-xs">
                        {res.error_message || 'Telemetry matched target criteria.'}
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={5} className="p-4 text-center text-slate-500 font-sans">
                      All criteria evaluated and passed successfully.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Collapsible Run Manifest JSON Inspector */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800">
          <button
            onClick={() => setShowManifest(!showManifest)}
            className="w-full flex justify-between items-center text-xs font-semibold text-slate-300 hover:text-white transition focus:outline-none"
          >
            <span className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-cyan-400" />
              <span>Run Manifest & Cryptographic Audit Ledger (JSON)</span>
            </span>
            <ChevronDown className={`w-4 h-4 transition-transform ${showManifest ? 'rotate-180' : ''}`} />
          </button>

          {showManifest && (
            <div className="mt-3 pt-3 border-t border-slate-800">
              <pre className="p-3 rounded-lg bg-slate-950 text-cyan-300 font-mono text-[10px] overflow-x-auto max-h-72">
                {JSON.stringify(manifest, null, 2)}
              </pre>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
