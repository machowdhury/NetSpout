import type { StudioScenarioPack } from './studio';

export type IndustryEvidenceState =
  | 'OBSERVED'
  | 'MODELED'
  | 'INFERRED'
  | 'NOT_ESTABLISHED';

export interface IndustryEntity {
  entity_id: string;
  label: string;
  entity_kind: string;
  zone_id: string;
  description: string;
  attributes: Record<string, string>;
}

export interface IndustryDependency {
  dependency_id: string;
  source_entity_id: string;
  target_entity_id: string;
  relationship_type: string;
  criticality: string;
  assumption: string;
}

export interface IndustryEnvironment {
  environment_id: string;
  name: string;
  description: string;
  infrastructure_archetype: string;
  entity_ids: string[];
  dependency_ids: string[];
  scenario_ids: string[];
  default_scenario_id: string;
  telemetry_source_ids: string[];
  investigation_objectives: string[];
}

export interface IndustryImpact {
  impact_id: string;
  title: string;
  statement: string;
  classification: IndustryEvidenceState;
  trigger_entity_ids: string[];
  impacted_entity_ids: string[];
  dependency_ids: string[];
  assumptions: string[];
  exclusions: string[];
}

export interface IndustryScenarioReference {
  scenario_id: string;
  title: string;
  source_ids: string[];
  investigation_recipe_ids: string[];
  scenario_maturity: string | null;
}

export interface IndustryPack {
  pack_id: string;
  industry_id: string;
  pack_version: string;
  name: string;
  description: string;
  implemented_scope: string;
  maturity: string;
  business_capabilities: Array<{
    capability_id: string;
    name: string;
    description: string;
    objective: string;
    entity_id: string;
  }>;
  environments: IndustryEnvironment[];
  entities: IndustryEntity[];
  dependencies: IndustryDependency[];
  operational_objectives: Array<{
    objective_id: string;
    name: string;
    statement: string;
    measurement_status: IndustryEvidenceState;
  }>;
  business_impacts: IndustryImpact[];
  telemetry_requirements: Array<{
    source_id: string;
    role: string;
    required: boolean;
    evidence_classification: IndustryEvidenceState;
    notes: string;
  }>;
  provenance_evidence_ids: string[];
  validation_requirements: string[];
  scenario_references: IndustryScenarioReference[];
}

export interface IndustryCatalog {
  schema_version: string;
  registry_version: string;
  industries: IndustryPack[];
  future_categories: string[];
}

export interface IndustryComposition {
  industry_id: string;
  environment_id: string;
  scenario_id: string;
  seed: number;
  source_ids: string[];
  investigation_recipe_ids: string[];
  technical_evidence_classification: IndustryEvidenceState;
  business_impact_classification: IndustryEvidenceState;
  generation_request: {
    mode: 'SCENARIO';
    selection_id: string;
    transport_id: string;
    destination_id: string;
    count: number;
    rate_eps: number;
    scenario_parameters: Record<string, string | number | boolean>;
  };
  impact_preview: {
    propagated_entity_ids: string[];
    dependency_ids: string[];
    technical_evidence: { status: IndustryEvidenceState; detail: string };
    business_impacts: Array<IndustryImpact & { status: IndustryEvidenceState }>;
  };
}

export type IndustryStudioDraft = StudioScenarioPack;
