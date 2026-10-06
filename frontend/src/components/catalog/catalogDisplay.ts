import type { VerificationState } from '../../types/catalog';

export const integrationTypeLabels = {
  NATIVE_INPUT: 'Native input',
  COLLECTOR: 'Collector',
  SPLUNKBASE_ADD_ON: 'Splunkbase add-on',
  DIRECT_STRUCTURED_INGESTION: 'Lab-only direct ingestion',
} as const;

export const sourcetypeAuthorityLabels = {
  SPLUNK_DOCUMENTED: 'SPLUNK-DOCUMENTED',
  NETSPOUT_DEFINED: 'NETSPOUT-DEFINED',
} as const;

export function missingLabel(state: VerificationState, configured = false): string {
  if (state === 'UNSUPPORTED') return 'UNSUPPORTED';
  if (state === 'RESEARCH_REQUIRED') return 'RESEARCH REQUIRED';
  return configured ? 'NO EVIDENCE' : 'NOT CONFIGURED';
}
