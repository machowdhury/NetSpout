export type CoverageMaturity =
  | 'DISCOVERED'
  | 'RESEARCHED'
  | 'CONTRACTED'
  | 'FORMAT_VALIDATED'
  | 'RUNTIME_VALIDATED'
  | 'SPLUNK_VALIDATED'
  | 'GOLDEN'
  | 'RESEARCH_REQUIRED'
  | 'UNSUPPORTED';

export interface CoverageEvidence {
  claim_id: string;
  claim: string;
  evidence_type: string;
  source_title: string;
  publisher: string;
  reference: string;
  product_applicability: string[];
  software_version_applicability: string[];
  verified_date: string;
  confidence: string;
  status: string;
  notes: string;
}

export interface ProductSourceCoverage {
  coverage_id: string;
  source_id: string | null;
  name: string;
  native_format: string | null;
  transport_ids: string[];
  schema_references: string[];
  evidence_ids: string[];
  netspout_contract_id: string | null;
  generator_status: string;
  maturity: CoverageMaturity;
  splunk: {
    requirement: string;
    integration_ids: string[];
    sourcetypes: string[];
    cim_status: string;
    evidence_ids: string[];
  };
  limitations: string[];
}

export interface CoverageProduct {
  product_id: string;
  family_id: string;
  current_name: string;
  aliases: Array<{ name: string; relationship: string; evidence_ids: string[] }>;
  lifecycle_status: string;
  version_applicability: string[];
  evidence_ids: string[];
  pack_id: string | null;
  sources: ProductSourceCoverage[];
  investigation_ids: string[];
  scenario_ids: string[];
  maturity: CoverageMaturity;
  limitations: string[];
  research_gaps: string[];
}

export interface CiscoCoverageCatalog {
  catalog_version: string;
  vendor_name: string;
  independence_notice: string;
  summary: Record<string, number | string>;
  evidence: CoverageEvidence[];
  families: Array<{ family_id: string; name: string; product_ids: string[] }>;
  products: CoverageProduct[];
  troubleshooting: Array<{
    operation_id: string;
    product_ids: string[];
    operation_type: string;
    operation: string;
    purpose: string;
    expected_result_model: string;
    platform_applicability: string[];
    software_version_applicability: string[];
    evidence_ids: string[];
  }>;
  production_guides: Array<{
    guide_id: string;
    scenario_id: string;
    real_sources: string[];
    collection_mechanisms: string[];
    integration_requirements: string[];
    sourcetypes: string[];
    cim_requirements: string[];
    production_portable_spl: string[];
    prerequisites: string[];
    netspout_differences: string[];
    known_gaps: string[];
    unvalidated_assumptions: string[];
  }>;
  golden_scenarios: Array<{
    scenario_id: string;
    title: string;
    description: string;
    product_ids: string[];
    source_ids: string[];
    shared_state: boolean;
    native_runtime: boolean;
    studio_pack: boolean;
    investigation_ids: string[];
    troubleshooting_operation_ids: string[];
    production_guide_id: string;
    spl_portability: Record<string, string>;
    maturity: CoverageMaturity;
  }>;
}
