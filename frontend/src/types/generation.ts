import type { CatalogSource, VerificationState } from './catalog';

export type GenerationMode = 'SCENARIO' | 'DATA_SOURCE' | 'SOURCETYPE' | 'SINGLE_EVENT';
export type GenerationStep = 'CHOOSE' | 'PREVIEW' | 'CONFIGURE' | 'RUN' | 'OBSERVE' | 'INVESTIGATE';

export interface GenerationModeDefinition {
  id: GenerationMode;
  label: string;
  description: string;
}

export interface TopologyZone {
  zone_id: string;
  label: string;
}

export interface TopologyNode {
  node_id: string;
  technology_id: string;
  zone_id: string;
  role: string;
  source_ids: string[];
  label?: string | null;
  entity_id?: string | null;
  description?: string | null;
  vendor?: string | null;
  product?: string | null;
}

export interface TopologyRelationship {
  relationship_id: string;
  source_node_id: string;
  target_node_id: string;
  relationship_type: string;
  protocol?: string | null;
  purpose?: string | null;
  telemetry_source_ids?: string[];
  incident_relevance?: string | null;
}

export interface TelemetryPath {
  path_id: string;
  source_id: string;
  producer_node_id: string;
  observer_node_id: string | null;
  label?: string | null;
  protocol?: string | null;
}

export interface TimelineStep {
  step_id: string;
  stage: string;
  description: string;
  state_changes: Record<string, string>;
  entity_state_changes?: Record<string, string>;
  telemetry_state_changes?: Record<string, string>;
  expected_observations?: string[];
  evidence_source_ids?: string[];
  incident_ids: string[];
}

export interface GuidedInvestigationStep {
  step_id: string;
  recipe_id: string;
  title: string;
  question: string;
  expected_finding: string;
  explanation: string;
  hint: string | null;
  node_ids: string[];
  source_ids: string[];
}

export interface ScenarioValidationExpectation {
  validation_id: string;
  label: string;
  evidence_stage: string;
  expected_state: string;
  requirement: 'REQUIRED' | 'INFORMATIONAL';
  source_id: string | null;
}

export interface GuidedCompleteness {
  state: 'READY' | 'PARTIAL' | 'RESEARCH_REQUIRED' | 'UNSUPPORTED';
  passed: number;
  total: number;
  checks: Record<string, boolean>;
  production_guidance_available: boolean;
}

export interface GenerationScenario {
  scenario_id: string;
  title: string;
  description: string;
  story: string;
  domain?: string | null;
  category?: string | null;
  technical_description?: string | null;
  difficulty: string;
  expected_duration_minutes: number;
  learning_objectives: string[];
  skills_practiced?: string[];
  expected_outcome?: string | null;
  baseline_description?: string | null;
  incident_description?: string | null;
  discovery_prompt?: string | null;
  learning_hints?: string[];
  business_impact: string;
  prerequisites: string[];
  technology_ids: string[];
  source_ids: string[];
  entities: string[];
  zones: TopologyZone[];
  nodes: TopologyNode[];
  relationships: TopologyRelationship[];
  telemetry_paths: TelemetryPath[];
  incident_path: string[];
  incident_summary?: string | null;
  runtime_state_keys: string[];
  timeline: TimelineStep[];
  expected_evidence: string[];
  investigation_recipe_ids: string[];
  investigation_steps?: GuidedInvestigationStep[];
  validation_expectations?: ScenarioValidationExpectation[];
  visualization?: {
    mode: 'AUTOMATIC' | 'CURATED';
    direction: 'LEFT_TO_RIGHT' | 'TOP_TO_BOTTOM';
    curated_layout_ref: string | null;
  };
  replay_policy?: {
    creates_new_run_id: boolean;
    preserves_history: boolean;
    reset_to_step: string;
  } | null;
  integration_recommendation_ids: string[];
  production_replication_guidance: string[];
  composition_id: string | null;
  verification_state: VerificationState;
  maturity: string;
  source_count: number;
  integration_count: number;
  runnable: boolean;
  guided_completeness?: GuidedCompleteness;
}

export interface GenerationSource extends CatalogSource {
  generation: {
    runnable: boolean;
    state: string;
    reason: string;
  };
}

export interface GenerationSourcetype {
  name: string;
  authority: 'SPLUNK_DOCUMENTED' | 'NETSPOUT_DEFINED';
  source_id: string;
  vendor: string;
  product: string;
  source: string;
  verification_state: VerificationState;
  provenance: string[];
  integration_ids: string[];
  cim_mappings: Array<{ name: string; verification_state: VerificationState; evidence_ids: string[] }>;
  runnable: boolean;
  generation_controls: string[];
}

export interface EventFamily {
  event_family_id: string;
  label: string;
  source_id: string;
  sourcetype: string;
  runnable: boolean;
  count: number;
}

export interface GenerationTransport {
  transport_id: string;
  component: string;
  protocol: string;
  signals: string[];
  compatible_source_ids: string[];
  verification_state: VerificationState;
  implemented: boolean;
  evidence_ids: string[];
  notes: string;
}

export interface GenerationDestination {
  destination_id: string;
  destination_type: string;
  accepted_transport_ids: string[];
  verification_state: VerificationState;
  evidence_ids: string[];
  label: string;
  configured: boolean;
}

export interface IntegrationReadiness {
  recommendation_id: string;
  source_id: string;
  integration_id: string | null;
  requirement: 'REQUIRED' | 'RECOMMENDED' | 'NOT_REQUIRED' | 'RESEARCH_REQUIRED';
  evidence_ids: string[];
  notes: string;
  name: string;
  publisher: string | null;
  support_state: string;
  detected: boolean;
  evidence: Array<{ evidence_id: string; title: string; publisher: string; reference: string }>;
}

export interface InvestigationRecipe {
  recipe_id: string;
  title: string;
  objective?: string | null;
  question?: string | null;
  expected_finding?: string | null;
  explanation?: string | null;
  hint?: string | null;
  portability: 'PRODUCTION_PORTABLE' | 'NETSPOUT_SPECIFIC';
  spl: string;
  source_ids: string[];
  required_fields: string[];
  cim_requirements: string[];
  netspout_only_fields: string[];
  evidence_ids: string[];
}

export interface GenerationCapabilities {
  schema_version: string;
  workflow: GenerationStep[];
  guided_workflow?: Array<'UNDERSTAND' | 'PREPARE' | 'RUN' | 'OBSERVE' | 'INVESTIGATE' | 'VALIDATE'>;
  modes: GenerationModeDefinition[];
  sources: GenerationSource[];
  scenarios: GenerationScenario[];
  sourcetypes: GenerationSourcetype[];
  event_families: EventFamily[];
  transports: GenerationTransport[];
  destinations: GenerationDestination[];
  integration_recommendations: IntegrationReadiness[];
  investigations: InvestigationRecipe[];
  raw_preview_policy: string;
}

export interface GenerationRequest {
  mode: GenerationMode;
  selection_id: string;
  transport_id: string;
  destination_id: string;
  count: number;
  rate_eps: number;
  duration_seconds?: number;
  scenario_parameters: Record<string, string | number | boolean>;
}

export interface GeneratedEvent {
  event_id: string;
  source_id: string;
  contract_id: string;
  provenance: string[];
  transport_id: string;
  sourcetype: string;
  sourcetype_authority: string;
  phase: string;
  raw: string;
}

export interface GenerationPreview {
  mode: GenerationMode;
  selection_id: string;
  scenario: GenerationScenario | null;
  sources: GenerationSource[];
  bindings: Array<{
    source_id: string;
    generator_id: string;
    transport_id: string;
    destination_id: string;
    validator_ids: string[];
  }>;
  integration_readiness: IntegrationReadiness[];
  investigations: InvestigationRecipe[];
  raw_preview: GeneratedEvent[];
  preview_notice: string;
  native_contract: CatalogSource['native_contract'];
  splunk_contract: CatalogSource['splunk_contract'];
  netspout_contract: CatalogSource['netspout_contract'];
  known_limitations: string[];
}

export interface PreflightCheck {
  check_id: string;
  label: string;
  state: 'PASS' | 'WARN' | 'BLOCK';
  detail: string;
}

export interface GenerationPreflight {
  state: 'READY' | 'READY_WITH_WARNINGS' | 'BLOCKED';
  checks: PreflightCheck[];
  source_ids: string[];
  generator_ids: string[];
  transport_id: string;
  destination_id: string;
}

export interface EvidenceStage {
  stage: string;
  state: 'NOT_ATTEMPTED' | 'PROVEN' | 'PENDING' | 'NOT_AVAILABLE' | 'FAILED';
  count: number;
  detail: string;
}

export interface ScenarioValidationResult {
  validation_id: string;
  label: string;
  evidence_stage: string;
  requirement: 'REQUIRED' | 'INFORMATIONAL';
  state: 'NOT_ATTEMPTED' | 'PROVEN' | 'PENDING' | 'NOT_AVAILABLE' | 'FAILED';
  detail: string;
}

export interface GenerationRun {
  run_id: string;
  mode: GenerationMode;
  selection_id: string;
  scenario_id: string | null;
  source_ids: string[];
  generator_ids: string[];
  transport_id: string;
  destination_id: string;
  started_at: string;
  completed_at: string | null;
  current_phase: string;
  status: string;
  events: GeneratedEvent[];
  evidence: EvidenceStage[];
  validation?: ScenarioValidationResult[];
  integration_readiness: IntegrationReadiness[];
  investigations: InvestigationRecipe[];
  limitations: string[];
}

export interface InvestigationResult {
  run_id: string;
  recipe_id: string;
  portability: string;
  query: string;
  status: 'SUCCEEDED' | 'FAILED';
  result_count: number;
  detail: string;
}
