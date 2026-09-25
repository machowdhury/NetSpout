import type { LogEntry } from './topology';

export type WorkflowStep = 'CHOOSE' | 'PREVIEW' | 'CONNECT' | 'RUN' | 'PROVE';

export type AppViewMode = 'workflow' | 'advanced' | 'operations';

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
  eps: number;
  affected_devices: string[];
  manifest: any | null;
  validation_results: ValidationResultItem[];
  recent_logs: LogEntry[];
  error: string | null;
}
