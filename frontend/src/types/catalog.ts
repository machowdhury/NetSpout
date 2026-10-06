export type VerificationState =
  | 'VERIFIED'
  | 'PARTIALLY_VERIFIED'
  | 'RESEARCH_REQUIRED'
  | 'UNSUPPORTED';

export type SourcetypeAuthority = 'SPLUNK_DOCUMENTED' | 'NETSPOUT_DEFINED';

export type ProvenanceValue =
  | 'VENDOR_DOCUMENTED'
  | 'STANDARD_DOCUMENTED'
  | 'VERIFIED_PUBLIC_SAMPLE'
  | 'SPLUNK_DOCUMENTED'
  | 'DATASET_VERIFIED'
  | 'NETSPOUT_SCHEMA'
  | 'MODELED_PAYLOAD'
  | 'MODELED_VALUE'
  | 'INFERRED'
  | 'RESEARCH_REQUIRED'
  | 'UNSUPPORTED_TELEMETRY';

export interface CatalogEvidence {
  evidence_id: string;
  title: string;
  publisher: string;
  reference: string;
  provenance: ProvenanceValue;
  verification_state: VerificationState;
  notes: string;
}

export interface SourcetypeClaim {
  name: string;
  authority: SourcetypeAuthority;
  evidence_ids: string[];
}

export interface NativeTransport {
  protocol: string;
  default_port: number | null;
  encoding: string | null;
}

export interface NativeContract {
  contract_id: string;
  verification_state: VerificationState;
  format: string | null;
  schema: string | null;
  transports: NativeTransport[];
  structural_fields: string[];
  evidence_ids: string[];
}

export interface SplunkContract {
  contract_id: string;
  verification_state: VerificationState;
  input_mechanisms: string[];
  integration_ids: string[];
  sourcetypes: SourcetypeClaim[];
  cim_mappings: CimMapping[];
  evidence_ids: string[];
}

export interface CimMapping {
  name: string;
  verification_state: VerificationState;
  evidence_ids: string[];
}

export interface NetSpoutContract {
  contract_id: string;
  verification_state: VerificationState;
  schema_classification: ProvenanceValue;
  generator: string | null;
  validator: string | null;
  transports: string[];
  modeled_fields: string[];
  structural_fields: string[];
  scenario_ids: string[];
  generation_modes: string[];
  runtime_status: string;
  maturity: string;
  evidence_ids: string[];
}

export interface SplFieldScope {
  production_fields: string[];
  netspout_only_fields: string[];
  portable_spl_status: VerificationState;
}

export interface CatalogSource {
  source_id: string;
  vendor: string;
  product: string;
  product_family: string;
  domains: string[];
  telemetry_source: string;
  applicable_industries: string[];
  verification_state: VerificationState;
  provenance: ProvenanceValue[];
  evidence_ids: string[];
  native_contract: NativeContract;
  splunk_contract: SplunkContract;
  netspout_contract: NetSpoutContract;
  spl_field_scope: SplFieldScope;
  known_limitations: string[];
}

export type IntegrationType =
  | 'NATIVE_INPUT'
  | 'COLLECTOR'
  | 'SPLUNKBASE_ADD_ON'
  | 'DIRECT_STRUCTURED_INGESTION';

export type IntegrationSupportState =
  | 'SUPPORTED'
  | 'DEPRECATED'
  | 'LAB_ONLY'
  | 'RESEARCH_REQUIRED'
  | 'UNSUPPORTED';

export interface CatalogIntegration {
  integration_id: string;
  name: string;
  publisher: string;
  integration_type: IntegrationType;
  supported_source_ids: string[];
  splunkbase_id: string | null;
  verification_state: VerificationState;
  support_state: IntegrationSupportState;
  sourcetypes: SourcetypeClaim[];
  cim_mappings: CimMapping[];
  netspout_coverage: VerificationState;
  evidence_ids: string[];
  notes: string;
}

export interface CatalogSummary {
  schema_version: string;
  catalog_version: string;
  source_count: number;
  integration_count: number;
  evidence_count: number;
  source_manifest_count: number;
  verification_counts: Record<string, number>;
  provenance_counts: Record<string, number>;
  domain_counts: Record<string, number>;
  sourcetype_counts: Partial<Record<SourcetypeAuthority, number>>;
}
