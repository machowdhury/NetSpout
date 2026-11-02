export type Cisco100Maturity =
  | 'CANDIDATE'
  | 'RESEARCHED'
  | 'CONTRACTED'
  | 'FORMAT_VALIDATED'
  | 'RUNTIME_VALIDATED'
  | 'SPLUNK_VALIDATED'
  | 'GOLDEN'
  | 'RESEARCH_REQUIRED'
  | 'UNSUPPORTED'
  | 'BLOCKED';

export interface Cisco100Scenario {
  scenario_id: string;
  title: string;
  domain: string;
  category: string;
  difficulty: string;
  story: string;
  technical_objective: string;
  business_impact: string;
  technologies: string[];
  entities: string[];
  relationships: string[];
  zones: string[];
  failure_or_attack_vector: string;
  enterprise_state: Record<string, string>;
  timeline: Array<{
    stage: string;
    offset_seconds: number;
    state_changes: Record<string, string>;
    expected_observation: string;
  }>;
  state_transitions: string[];
  telemetry_sources: string[];
  native_transports: string[];
  source_contracts: string[];
  product_packs: string[];
  splunk_integrations: string[];
  sourcetypes: string[];
  cim_relationships: Record<string, string>;
  evidence_references: string[];
  investigation_pack: {
    status: string;
    recipe_ids: string[];
    questions: string[];
    expected_findings: string[];
    spl_classifications: string[];
  };
  troubleshooting_pack: {
    status: string;
    operation_ids: string[];
    research_required: string[];
  };
  production_portability: {
    status: string;
    guide_id: string | null;
    production_portable_spl: string[];
    netspout_specific_spl: string[];
    requirements: string[];
    known_gaps: string[];
  };
  maturity: Cisco100Maturity;
  validation_state: string;
  research_gaps: string[];
  limitations: string[];
  runtime_scenario_id: string | null;
  execution_enabled: boolean;
  shared_state: boolean;
  guided_experience: boolean;
  topology_available: boolean;
  replay_supported: boolean;
  format_validation: string[];
  runtime_validation: string[];
  splunk_validation: string[];
}

export interface Cisco100Catalog {
  schema_version: string;
  catalog_version: string;
  vendor_id: string;
  independence_notice: string;
  summary: {
    scenario_definitions: number;
    domains: Record<string, number>;
    maturity: Record<Cisco100Maturity, number>;
    products_represented: number;
    source_contracts: number;
    native_protocols: number;
    verified_splunk_integrations: number;
  };
  evidence_debt: Record<string, number>;
  scenarios: Cisco100Scenario[];
  research_queue: Array<{
    research_id: string;
    scenario_id: string;
    product: string;
    source: string;
    missing_claim: string;
    required_evidence_type: string;
    blocking_gate: string;
    priority: string;
    status: string;
  }>;
  shared_assets: Array<{
    asset_id: string;
    asset_type: string;
    scenario_ids: string[];
    evidence_ids: string[];
  }>;
  filter_result_count: number;
  query_ms: number;
}
