export type DashboardPerspective = 'NOC' | 'ENGINEER' | 'EVIDENCE';

export type DashboardMaturity =
  | 'NOT_STARTED'
  | 'GENERATED'
  | 'SPL_VALIDATED'
  | 'DATA_VALIDATED'
  | 'VISUALLY_VALIDATED'
  | 'DASHBOARD_READY'
  | 'DEPENDENCY_BLOCKED'
  | 'VALIDATION_FAILED';

export interface DashboardEligibility {
  dashboard_id: string;
  title: string;
  scenario_id: string;
  runtime_scenario_id: string;
  domain: string;
  industry_id: string | null;
  scenario_maturity: string;
  dashboard_maturity: DashboardMaturity;
  state: 'ELIGIBLE' | 'RESEARCH_REQUIRED' | 'DEPENDENCY_BLOCKED';
  reasons: string[];
  source_ids: string[];
  investigation_recipe_ids: string[];
  recipe_ids: string[];
}

export interface DashboardCatalog {
  schema_version: string;
  registry_version: string;
  dashboards: DashboardEligibility[];
  eligible_count: number;
  recipes: Array<Record<string, unknown>>;
  visualizations: Array<Record<string, unknown>>;
}

export interface DashboardDrilldown {
  token: string;
  field: string;
  semantics: string;
}

export interface DashboardPanel {
  panel_id: string;
  recipe_id: string;
  title: string;
  purpose: string;
  perspective: DashboardPerspective;
  visualization_id: string;
  requested_visualization_id: string;
  dependency_state: string;
  query: string | null;
  required_fields: string[];
  optional_fields: string[];
  expected_shape: Record<string, string>;
  drilldowns: DashboardDrilldown[];
  evidence_requirements: string[];
  portability: 'PRODUCTION_PORTABLE' | 'NETSPOUT_SPECIFIC';
  executable: boolean;
}

export interface DashboardGraphNode {
  node_id?: string;
  entity_id?: string;
  label?: string;
  role?: string;
  entity_type?: string;
  zone_id?: string;
  x?: number | null;
  y?: number | null;
  attributes?: Record<string, unknown>;
}

export interface DashboardGraphRelationship {
  relationship_id: string;
  source_node_id?: string;
  target_node_id?: string;
  source_entity_id?: string;
  target_entity_id?: string;
  relationship_type: string;
  protocol?: string | null;
}

export interface DashboardPack {
  dashboard_id: string;
  schema_version: string;
  dashboard_version: string;
  title: string;
  description: string;
  scenario_id: string;
  scenario_version: string;
  runtime_scenario_id: string;
  run_id: string | null;
  domain: string;
  category: string;
  industry_id: string | null;
  source_contracts: Array<Record<string, unknown>>;
  splunk_contracts: Array<Record<string, unknown>>;
  investigation_recipe_ids: string[];
  detection_pack_ids: string[];
  entity_graph: {
    shared_with_scenario: boolean;
    nodes: DashboardGraphNode[];
    relationships: DashboardGraphRelationship[];
  };
  topology_ref: string;
  telemetry_manifest: Array<Record<string, unknown>>;
  observed_fields: string[];
  panels: DashboardPanel[];
  perspectives: Record<DashboardPerspective, string[]>;
  maturity: DashboardMaturity;
  validation_evidence: Array<Record<string, unknown>>;
  export_compatibility: string;
  cim_status: string;
  limitations: string[];
}

export interface DashboardStudioExport {
  format: 'SPLUNK_DASHBOARD_STUDIO_JSON';
  definition: Record<string, unknown>;
  validation: { valid: boolean; errors: string[] };
  deployment: {
    deployment_status: string;
    target: string;
    overwrite_allowed: boolean;
    required_permissions: string[];
    search_workload: Record<string, unknown>;
  };
}
