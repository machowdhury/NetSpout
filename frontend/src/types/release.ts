export type SecuritySourceStatus =
  | 'IMPLEMENTED_AND_VALIDATED'
  | 'IMPLEMENTED_NOT_VALIDATED'
  | 'PARTIAL'
  | 'RESEARCH_REQUIRED'
  | 'NOT_IMPLEMENTED'
  | 'UNSUPPORTED';

export interface SecuritySource {
  coverage_id: string;
  vendor: string;
  product: string;
  product_version_scope: string;
  domain: string;
  event_family: string;
  native_format: string;
  transports: string[];
  splunk_sourcetypes: string[];
  technology_add_on: string;
  cim_status: string;
  required_fields: string[];
  scenario_ids: string[];
  catalog_source_ids: string[];
  contract_provenance: string[];
  validation_evidence: string[];
  runtime_maturity: string;
  splunk_observation: string;
  distribution_availability: string[];
  status: SecuritySourceStatus;
  sample_generation: {
    runnable: boolean;
    mode?: string;
    reason?: string;
  };
  known_limitations: string[];
}

export interface SecuritySourceResponse {
  summary: {
    schema_version: string;
    catalog_version: string;
    source_count: number;
    runnable_count: number;
    status_counts: Record<string, number>;
    domain_counts: Record<string, number>;
  };
  sources: SecuritySource[];
}

export interface SetupConfiguration {
  configured: boolean;
  deployment_mode: string | null;
  splunk_deployment_type?: string;
  hec_url?: string;
  search_url?: string;
  auth_method?: string;
  search_username?: string | null;
  indexes?: string[];
  collectors?: string[];
  guided_sample?: boolean;
  allow_insecure_tls?: boolean;
  secret_state: {
    hec_token_configured: boolean;
    search_secret_configured: boolean;
  };
}

export interface SetupValidation {
  status: 'PASS' | 'BLOCKED';
  checks: Array<{
    id: string;
    status: 'PASS' | 'FAIL' | 'NOT_TESTED';
    detail: string;
  }>;
}
