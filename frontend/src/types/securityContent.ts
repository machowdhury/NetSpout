export type CompatibilityStatus =
  | 'VALIDATED_COMPATIBLE'
  | 'STRUCTURALLY_COMPATIBLE'
  | 'PARTIALLY_COMPATIBLE'
  | 'REQUIRES_TRANSFORMATION'
  | 'MISSING_SOURCE'
  | 'MISSING_REQUIRED_FIELDS'
  | 'MISSING_TA'
  | 'MISSING_MACRO'
  | 'MISSING_LOOKUP'
  | 'MISSING_DATA_MODEL'
  | 'RESEARCH_REQUIRED'
  | 'NOT_EVALUATED';

export interface CompatibilityAssessment {
  status: CompatibilityStatus;
  matched_netspout_sources: string[];
  missing_macros: string[];
  missing_lookups: string[];
  reasons: string[];
  structural_compatibility: boolean;
  runtime_compatibility: string;
  splunk_compatibility: string;
  detection_validation: string;
  production_detection_efficacy: 'NOT_ESTABLISHED';
}

export interface SecurityDetectionSummary {
  catalog_key: string;
  content_id: string;
  name: string;
  description: string;
  category: string;
  security_domain: string;
  detection_type: string;
  status: string;
  version: number;
  analytic_stories: string[];
  mitre_attack_ids: string[];
  data_source_names: string[];
  products: string[];
  repository_commit: string;
  file_path: string;
  compatibility: CompatibilityAssessment;
  has_attack_data: boolean;
}

export interface SecurityDetectionDetail extends SecurityDetectionSummary {
  author: string;
  how_to_implement: string;
  known_false_positives: string;
  spl: string;
  dependencies: {
    resolution: string;
    indexes: string[];
    sourcetypes: string[];
    required_fields: string[];
    data_models: string[];
    macros: string[];
    lookups: string[];
    technology_add_ons: string[];
    search_commands: string[];
    unresolved_reasons: string[];
    parser_scope: string;
  };
  attack_data: Array<{
    url: string;
    source?: string;
    sourcetype?: string;
    test_name?: string;
  }>;
  validation_evidence?: {
    status: string;
    run_id: string;
    indexed_event_count: number;
    matched_event_count: number;
  } | null;
  production_detection_efficacy: 'NOT_ESTABLISHED';
}

export interface AttackDataset {
  catalog_key: string;
  dataset_id: string;
  name: string;
  description: string;
  author: string;
  environment: string;
  mitre_techniques: string[];
  repository_commit: string;
  redistribution_decision: string;
  files: Array<{
    name: string;
    path: string;
    format: string;
    source?: string;
    sourcetype?: string;
    size_bytes?: number;
    sha256?: string;
  }>;
}
