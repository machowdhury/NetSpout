import type { GenerationRun, GenerationScenario, GenerationSource } from './generation';

export type CreationPath =
  | 'EXISTING_SOURCES'
  | 'IMPORT_SANITIZED_SAMPLE'
  | 'CLONE_SCENARIO';

export type FieldClassification =
  | 'STRUCTURAL'
  | 'MODELED'
  | 'CORRELATION'
  | 'DERIVED'
  | 'SENSITIVE'
  | 'UNKNOWN';

export type PrivacyStatus =
  | 'UNREVIEWED'
  | 'FINDINGS_REQUIRE_REVIEW'
  | 'SANITIZED';

export type SampleProvenance =
  | 'CUSTOMER SAMPLE — SANITIZED'
  | 'LAB SAMPLE — SANITIZED'
  | 'PUBLIC SAMPLE'
  | 'VENDOR DOCUMENTED'
  | 'UNKNOWN ORIGIN'
  | 'NETSPOUT GENERATED';

export type RedistributionStatus =
  | 'PRIVATE'
  | 'LOCAL ONLY'
  | 'REDISTRIBUTION UNKNOWN'
  | 'REDISTRIBUTION PERMITTED';

export interface PrivacyFinding {
  category: string;
  location: string;
  redacted_preview: string;
  severity: string;
  fingerprint: string;
}

export interface SampleField {
  name: string;
  data_type: string;
  classification: FieldClassification;
  authority: 'INFERRED' | 'USER_PROVIDED' | 'CATALOG_VERIFIED';
  description: string;
  enum_values: string[];
  numeric_min: number | null;
  numeric_max: number | null;
}

export interface SampleAnalysis {
  sample_fingerprint: string;
  blocked: boolean;
  privacy_status: PrivacyStatus;
  findings: PrivacyFinding[];
  format: string;
  record_count: number;
  fields: SampleField[];
  record_boundary: string;
  notes: string[];
}

export interface CustomSourceDraft {
  source_id: string;
  display_name: string;
  sanitized_sample: string;
  analyzed_fingerprint: string;
  privacy_status: PrivacyStatus;
  provenance: SampleProvenance;
  redistribution: RedistributionStatus;
  fields: SampleField[];
  format: string;
  source_description: string;
  netspout_sourcetype: string | null;
  netspout_sourcetype_acknowledged: boolean;
}

export interface StudioEntity {
  entity_id: string;
  label: string;
  entity_type: string;
  zone_id: string;
  attributes: Record<string, string>;
  x: number | null;
  y: number | null;
}

export interface StudioStateValue {
  state_key: string;
  entity_id: string;
  value: unknown;
  unit: string | null;
}

export interface StudioTransition {
  transition_id: string;
  stage: string;
  offset_seconds: number;
  title: string;
  state_changes: StudioStateValue[];
  source_ids: string[];
}

export interface StudioParameter {
  parameter_id: string;
  state_key: string;
  value_type: string;
  default: unknown;
  minimum: number | null;
  maximum: number | null;
  enum_values: string[];
  unit: string | null;
  description: string;
}

export interface StudioInvestigation {
  investigation_id: string;
  title: string;
  objective: string;
  question: string;
  spl: string;
  expected_finding: string;
  explanation: string;
  portability: 'PRODUCTION_PORTABLE' | 'NETSPOUT_SPECIFIC';
  evidence_source_ids: string[];
  netspout_only_fields: string[];
}

export interface StudioScenarioPack {
  pack_id: string;
  scenario_id: string;
  title: string;
  description: string;
  story: string;
  creation_path: CreationPath;
  maturity: string;
  privacy_status: PrivacyStatus;
  provenance: SampleProvenance;
  redistribution: RedistributionStatus;
  source_ids: string[];
  custom_sources: CustomSourceDraft[];
  zones: Array<{ zone_id: string; label: string }>;
  entities: StudioEntity[];
  relationships: Array<{
    relationship_id: string;
    source_entity_id: string;
    target_entity_id: string;
    relationship_type: string;
    protocol: string | null;
  }>;
  baseline: StudioStateValue[];
  timeline: StudioTransition[];
  parameters: StudioParameter[];
  correlation_mappings: Array<{
    source_id: string;
    source_field: string;
    entity_id: string;
    identity_type: string;
  }>;
  investigations: StudioInvestigation[];
  contract_fingerprints: Record<string, string>;
  layout_hints: Record<string, Record<string, number>>;
  cloned_from_scenario_id: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface StudioValidation {
  valid: boolean;
  maturity_ceiling: string;
  checks: Array<{ check_id: string; state: 'PASS' | 'FAIL'; detail: string }>;
  errors: string[];
  warnings: string[];
}

export interface StudioHome {
  creation_paths: Array<{ id: CreationPath; title: string; description: string }>;
  import_notice: string;
  sources: GenerationSource[];
  scenarios: GenerationScenario[];
  private_packs: Array<{
    pack_id: string;
    scenario_id: string;
    title: string;
    maturity: string;
    privacy_status: string;
    provenance: string;
    redistribution: string;
    source_count: number;
    custom_source_count: number;
    updated_at: string | null;
  }>;
}

export type StudioRun = GenerationRun;
