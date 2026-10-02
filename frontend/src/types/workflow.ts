import type { LogEntry } from './topology';

export type WorkflowStep = 'CHOOSE' | 'PREVIEW' | 'CONNECT' | 'RUN' | 'PROVE';

export type AppViewMode = 'workflow' | 'advanced' | 'operations' | 'generator' | 'catalog';

export type PipelineType = 'splunk_hec' | 'syslog' | 'otlp' | 'telegraf';

export type ConnectionHealth = 'CONFIGURED' | 'REACHABLE' | 'VERIFIED' | 'DISCONNECTED';

export interface ValidationRule {
  id: string;
  name: string;
  type: 'EVENT_EXISTS' | 'COUNT_THRESHOLD' | 'FIELD_VALUE' | 'STATE_TRANSITION' | 'SPL_QUERY';
  target_sourcetype?: string;
  min_count?: number;
  target_field?: string;
  expected_value?: any;
  spl_query?: string;
  description: string;
}

export interface ScenarioPhaseDef {
  phase: string;
  name: string;
  duration_ticks: number;
  description: string;
  expected_observations: string[];
}

export interface NativeSnmpCapabilities {
  protocol: string;
  pdu_types: string[];
  notifications: string[];
  polling_operations: string[];
  mibs: string[];
  external_tooling: string[];
  splunk_sourcetypes: string[];
  splunk_index: string;
  canonical_device_id: string;
  transport_fidelity: string;
  device_state_fidelity: string;
  semantic_statement: string;
}

export interface NativeGnmiCapabilities {
  protocol: string;
  subscription_modes: string[];
  encoding: string;
  yang_models: string[];
  external_tooling: string[];
  splunk_sourcetypes: string[];
  event_index: string;
  metric_index: string;
  canonical_device_id: string;
  transport_fidelity: string;
  device_state_fidelity: string;
  semantic_statement: string;
}

export interface UseCase {
  id: string;
  scenario_id: string;
  name: string;
  category: string;
  domain: string;
  difficulty: 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED';
  estimated_runtime_sec: number;
  vendors: string[];
  sourcetypes: string[];
  description: string;
  objective: string;
  expected_observations: string[];
  validation_rules: ValidationRule[];
  default_topology_id: string;
  phases: ScenarioPhaseDef[];
  source: 'SCENARIO_BOUND' | 'PRE_BUILT_REPO';
  maturity?: 'GOLDEN_PATH_CERTIFIED' | 'E2E_VALIDATED' | 'FORMAT_VALIDATED' | 'CONTRACTED';
  telemetry_model?: string;
  transport_protocol?: string;
  splunk_storage?: string;
  fidelity_badge?: 'NATIVE TRANSPORT' | 'MODELED PAYLOAD' | 'SYNTHETIC';
  telemetry_notes?: string;
  native_snmp_supported?: boolean;
  native_snmp_capabilities?: NativeSnmpCapabilities | null;
  native_gnmi_supported?: boolean;
  native_gnmi_capabilities?: NativeGnmiCapabilities | null;
  telemetry_requirements?: string[];
  affected_entities?: string[];
  timing_claim?: string;
  timing_value?: number;
  timing_unit?: string;
  timing_classification?: 'MEASURED' | 'MODELED' | 'DECLARED_ONLY' | 'NOT_APPLICABLE';
  timing_notes?: string;
}

export interface PipelineConnection {
  type: PipelineType;
  name: string;
  endpoint: string;
  token?: string;
  index?: string;
  port?: number;
  protocol?: string;
  status: ConnectionHealth;
  latency_ms?: number;
  last_verified?: string;
  allow_insecure_tls?: boolean;
  transport_mode?: 'DIRECT_TO_SPLUNK' | 'NATIVE_TRANSPORT';
  native_protocol?: string;
  native_snmp_e2e?: boolean;
  native_snmp_pdu_mode?: 'TRAP' | 'INFORM' | 'MIXED';
  native_snmp_community?: string;
  native_gnmi_e2e?: boolean;
}

export interface ValidationResultItem {
  rule_id: string;
  rule_name: string;
  status: 'PASS' | 'FAIL' | 'ERROR' | 'SKIPPED';
  rule_type: string;
  observed_value?: any;
  expected_value?: any;
  error_message?: string;
  details?: Record<string, any>;
}

export interface EvidenceBreakdown {
  generated_count: number;
  dispatched_count: number;
  observed_count: number;
  validation_passed: boolean;
  validation_total: number;
  validation_passed_count: number;
}

export interface EvidenceSourceItem {
  destination_id: string;
  name: string;
  telemetry_type: 'EVENT' | 'METRIC' | 'FLOW' | 'TRACE';
  target_index: string;
  query_mechanism: 'SPL_SEARCH' | 'MSTATS';
  query: string;
  observed_count: number;
  expected_count: number;
  status: 'PASS' | 'FAIL' | 'PENDING' | 'ERROR' | 'PARTIAL';
  role: 'REQUIRED' | 'SUPPORTING' | 'OPTIONAL';
  errors?: string[];
}

export interface UnifiedEvidenceSummary {
  run_id: string;
  scenario_id: string;
  destinations: EvidenceSourceItem[];
  total_generated: number;
  total_dispatched: number;
  total_observed: number;
  event_observed_count: number;
  event_expected_count: number;
  metric_observed_count: number;
  metric_expected_count: number;
  observation_completeness_pct: number;
  observation_status: string;
  contract_validation: string;
  required_evidence_satisfied: boolean;
  errors?: string[];
}

export interface WorkflowRunState {
  run_id: string | null;
  scenario_id: string | null;
  scenario_name: string;
  phase: string;
  status: 'idle' | 'running' | 'completed' | 'stopped' | 'failed';
  start_time?: number;
  elapsed_sec: number;
  total_events: number;
  dispatched_events: number;
  observed_events: number;
  destination_validation: string;
  observation_status: string;
  splunk_search_query?: string;
  splunk_metric_query?: string;
  event_observed_count?: number;
  metric_observed_count?: number;
  observation_completeness_pct?: number;
  destinations?: EvidenceSourceItem[];
  evidence_summary?: UnifiedEvidenceSummary;
  eps: number;
  affected_devices: string[];
  manifest: any | null;
  snmp_e2e_scorecard?: any | null;
  native_snmp_result?: any | null;
  gnmi_e2e_scorecard?: any | null;
  transport_mode?: string;
  native_protocol?: string;
  validation_results: ValidationResultItem[];
  recent_logs: LogEntry[];
  error: string | null;
}
