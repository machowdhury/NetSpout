import { useMemo } from 'react';
import type { ExperienceMode } from '../../app/navigation';
import { useCatalogData } from '../../hooks/useCatalogData';
import type { CatalogIntegration } from '../../types/catalog';
import { Panel, StatePanel, StatusBadge } from '../ui/SystemPrimitives';
import {
  CimMappingList,
  EvidenceList,
  SourcetypeList,
  ValueList,
} from './CatalogPrimitives';
import { integrationTypeLabels, missingLabel } from './catalogDisplay';

function IntegrationCard({
  integration,
  sourceNames,
  evidenceById,
  mode,
}: {
  integration: CatalogIntegration;
  sourceNames: Map<string, string>;
  evidenceById: Map<string, import('../../types/catalog').CatalogEvidence>;
  mode: ExperienceMode;
}) {
  const typeLabel = integrationTypeLabels[integration.integration_type];
  const sourceLabels = integration.supported_source_ids.map(
    (id) => sourceNames.get(id) ?? id,
  );

  return (
    <article className="integration-card">
      <header>
        <div>
          <span className="integration-card__type">{typeLabel}</span>
          <h3>{integration.name}</h3>
          <p>{integration.publisher}</p>
        </div>
        <div className="catalog-badge-row">
          <StatusBadge status={integration.support_state.replaceAll('_', ' ')} />
          <StatusBadge status={integration.verification_state.replaceAll('_', ' ')} />
        </div>
      </header>

      <div className="integration-card__facts">
        <div>
          <strong>Source relationships</strong>
          <ValueList values={sourceLabels} empty={missingLabel(integration.verification_state)} />
        </div>
        <div>
          <strong>Sourcetypes</strong>
          <SourcetypeList
            claims={integration.sourcetypes}
            empty={missingLabel(integration.verification_state, true)}
          />
        </div>
        {integration.splunkbase_id && (
          <div>
            <strong>Splunkbase ID</strong>
            <code>{integration.splunkbase_id}</code>
          </div>
        )}
      </div>

      <p className="integration-card__notes">{integration.notes}</p>

      {mode === 'advanced' && (
        <div className="integration-card__advanced">
          <div>
            <strong>Machine type</strong>
            <code>{integration.integration_type}</code>
          </div>
          <div>
            <strong>NetSpout coverage</strong>
            <StatusBadge status={integration.netspout_coverage.replaceAll('_', ' ')} />
          </div>
          <div>
            <strong>CIM mappings</strong>
            <CimMappingList
              mappings={integration.cim_mappings}
              empty={missingLabel(integration.verification_state, true)}
            />
          </div>
        </div>
      )}

      <div className="integration-card__evidence">
        <strong>Evidence</strong>
        <EvidenceList
          evidenceIds={integration.evidence_ids}
          evidenceById={evidenceById}
          state={integration.verification_state}
        />
      </div>
    </article>
  );
}

export function SplunkIntegrationsView({ mode }: { mode: ExperienceMode }) {
  const { data, loading, error, retry } = useCatalogData();
  const evidenceById = useMemo(
    () => new Map(data?.evidence.map((item) => [item.evidence_id, item]) ?? []),
    [data],
  );
  const sourceNames = useMemo(
    () => new Map(data?.sources.map((source) => [source.source_id, source.product]) ?? []),
    [data],
  );

  if (loading) return <StatePanel kind="loading" message="Loading backend integration records." />;
  if (error || !data) {
    return (
      <StatePanel
        kind="error"
        title="Integrations unavailable"
        message={`The backend catalog request failed${error ? `: ${error}` : '.'}`}
        action={<button type="button" className="button button--quiet" onClick={retry}>Retry</button>}
      />
    );
  }

  return (
    <div className="workspace-stack catalog-workspace">
      <Panel
        title="Splunk Integrations"
        description={`${data.summary.integration_count} backend catalog records. Native inputs, collectors, add-ons, and lab ingestion are classified separately.`}
      >
        <div className="integration-summary">
          <div><strong>{data.integrations.filter((item) => item.support_state === 'SUPPORTED').length}</strong><span>Supported</span></div>
          <div><strong>{data.integrations.filter((item) => item.support_state === 'DEPRECATED').length}</strong><span>Deprecated</span></div>
          <div><strong>{data.integrations.filter((item) => item.support_state === 'LAB_ONLY').length}</strong><span>Lab only</span></div>
        </div>
      </Panel>

      <div className="integration-grid">
        {data.integrations.map((integration) => (
          <IntegrationCard
            key={integration.integration_id}
            integration={integration}
            sourceNames={sourceNames}
            evidenceById={evidenceById}
            mode={mode}
          />
        ))}
      </div>
      {data.integrations.length === 0 && <StatePanel kind="empty" message="NO EVIDENCE" />}
    </div>
  );
}
