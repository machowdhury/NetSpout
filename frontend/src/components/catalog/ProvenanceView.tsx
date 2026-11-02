import { useMemo, useState } from 'react';
import { Search } from 'lucide-react';
import type { ExperienceMode } from '../../app/navigation';
import { useCatalogData } from '../../hooks/useCatalogData';
import type { CatalogEvidence, CatalogSource, VerificationState } from '../../types/catalog';
import {
  Panel,
  ProvenanceBadge,
  StatePanel,
  StatusBadge,
} from '../ui/SystemPrimitives';
import {
  CimMappingList,
  EvidenceList,
  SourcetypeList,
  ValueList,
} from './CatalogPrimitives';
import { missingLabel } from './catalogDisplay';

function sourceMissing(source: CatalogSource, configured = false) {
  return missingLabel(source.verification_state, configured);
}

function ContractHeader({
  title,
  state,
  contractId,
}: {
  title: string;
  state: VerificationState;
  contractId: string;
}) {
  return (
    <div className="contract-header">
      <div>
        <h3>{title}</h3>
        <code>{contractId}</code>
      </div>
      <StatusBadge status={state.replaceAll('_', ' ')} />
    </div>
  );
}

function SimpleProvenance({
  source,
  evidenceById,
}: {
  source: CatalogSource;
  evidenceById: Map<string, CatalogEvidence>;
}) {
  const nativeTransport = source.native_contract.transports.map((item) => {
    const port = item.default_port === null ? '' : `:${item.default_port}`;
    return `${item.protocol}${port}${item.encoding ? ` · ${item.encoding}` : ''}`;
  });
  const generationConfigured =
    Boolean(source.netspout_contract.generator) && source.netspout_contract.generation_modes.length > 0;
  const generationState =
    source.netspout_contract.verification_state === 'UNSUPPORTED'
      ? 'UNSUPPORTED'
      : source.netspout_contract.verification_state === 'RESEARCH_REQUIRED'
        ? 'RESEARCH REQUIRED'
        : generationConfigured &&
            source.netspout_contract.verification_state === 'VERIFIED' &&
            source.netspout_contract.runtime_status === 'AVAILABLE'
          ? 'READY'
          : generationConfigured
            ? 'PARTIAL'
            : 'NOT AVAILABLE';

  return (
    <div className="catalog-answer-grid">
      <article>
        <span>What is this</span>
        <h3>{source.telemetry_source}</h3>
        <p>{source.vendor} · {source.product_family}</p>
      </article>
      <article>
        <span>Where contract came from</span>
        <div className="catalog-badge-row">
          {source.provenance.map((state) => <ProvenanceBadge key={state} state={state} />)}
        </div>
        <p>{source.native_contract.schema ?? sourceMissing(source, true)}</p>
      </article>
      <article>
        <span>How it gets to Splunk</span>
        <ValueList
          values={source.splunk_contract.input_mechanisms}
          empty={missingLabel(source.splunk_contract.verification_state)}
        />
        {nativeTransport.length > 0 && <p>Native transport: {nativeTransport.join(', ')}</p>}
      </article>
      <article>
        <span>What Splunk calls it</span>
        <SourcetypeList
          claims={source.splunk_contract.sourcetypes}
          empty={missingLabel(source.splunk_contract.verification_state, true)}
        />
      </article>
      <article>
        <span>Can NetSpout generate it</span>
        <StatusBadge status={generationState} />
        <p>Runtime: {source.netspout_contract.runtime_status}</p>
        {generationConfigured && (
          <>
            <code>{source.netspout_contract.generator}</code>
            <ValueList values={source.netspout_contract.generation_modes} empty="NOT CONFIGURED" />
          </>
        )}
      </article>
      <article>
        <span>Why trust it</span>
        <EvidenceList evidenceIds={source.evidence_ids} evidenceById={evidenceById} state={source.verification_state} />
      </article>
    </div>
  );
}

function AdvancedProvenance({
  source,
  evidenceById,
}: {
  source: CatalogSource;
  evidenceById: Map<string, import('../../types/catalog').CatalogEvidence>;
}) {
  const native = source.native_contract;
  const splunk = source.splunk_contract;
  const netspout = source.netspout_contract;

  return (
    <div className="catalog-advanced">
      <section className="contract-card">
        <ContractHeader title="Native Contract" state={native.verification_state} contractId={native.contract_id} />
        <dl className="catalog-definition-list">
          <div><dt>Format</dt><dd>{native.format ?? missingLabel(native.verification_state)}</dd></div>
          <div><dt>Schema</dt><dd>{native.schema ?? missingLabel(native.verification_state, true)}</dd></div>
          <div>
            <dt>Transports</dt>
            <dd><ValueList values={native.transports.map((item) => `${item.protocol}${item.default_port === null ? '' : `:${item.default_port}`}${item.encoding ? ` · ${item.encoding}` : ''}`)} empty={missingLabel(native.verification_state)} /></dd>
          </div>
          <div><dt>Structural fields</dt><dd><ValueList values={native.structural_fields} empty={missingLabel(native.verification_state, true)} code /></dd></div>
        </dl>
        <EvidenceList evidenceIds={native.evidence_ids} evidenceById={evidenceById} state={native.verification_state} />
      </section>

      <section className="contract-card">
        <ContractHeader title="Splunk Contract" state={splunk.verification_state} contractId={splunk.contract_id} />
        <dl className="catalog-definition-list">
          <div><dt>Input mechanisms</dt><dd><ValueList values={splunk.input_mechanisms} empty={missingLabel(splunk.verification_state)} /></dd></div>
          <div><dt>Sourcetypes</dt><dd><SourcetypeList claims={splunk.sourcetypes} empty={missingLabel(splunk.verification_state, true)} /></dd></div>
          <div><dt>Integrations</dt><dd><ValueList values={splunk.integration_ids} empty={missingLabel(splunk.verification_state)} code /></dd></div>
          <div><dt>CIM mappings</dt><dd><CimMappingList mappings={splunk.cim_mappings} empty={missingLabel(splunk.verification_state, true)} /></dd></div>
        </dl>
        <EvidenceList evidenceIds={splunk.evidence_ids} evidenceById={evidenceById} state={splunk.verification_state} />
      </section>

      <section className="contract-card">
        <ContractHeader title="NetSpout Contract" state={netspout.verification_state} contractId={netspout.contract_id} />
        <dl className="catalog-definition-list">
          <div><dt>Schema classification</dt><dd><ProvenanceBadge state={netspout.schema_classification} /></dd></div>
          <div><dt>Generator</dt><dd><code>{netspout.generator ?? missingLabel(netspout.verification_state)}</code></dd></div>
          <div><dt>Validator</dt><dd><code>{netspout.validator ?? 'NOT CONFIGURED'}</code></dd></div>
          <div><dt>Runtime status</dt><dd><StatusBadge status={netspout.runtime_status} /></dd></div>
          <div><dt>Maturity</dt><dd><StatusBadge status={netspout.maturity} /></dd></div>
          <div><dt>Transports</dt><dd><ValueList values={netspout.transports} empty={missingLabel(netspout.verification_state)} /></dd></div>
          <div><dt>Generation modes</dt><dd><ValueList values={netspout.generation_modes} empty={missingLabel(netspout.verification_state)} /></dd></div>
          <div><dt>Modeled fields</dt><dd><ValueList values={netspout.modeled_fields} empty={missingLabel(netspout.verification_state, true)} code /></dd></div>
          <div><dt>Structural fields</dt><dd><ValueList values={netspout.structural_fields} empty={missingLabel(netspout.verification_state, true)} code /></dd></div>
          <div>
            <dt>Scenarios</dt>
            <dd>
              {netspout.scenario_ids.length > 0 ? (
                <div className="catalog-chip-list">
                  {netspout.scenario_ids.map((id) => <a key={id} href="#/generate/scenarios">{id}</a>)}
                </div>
              ) : <span className="catalog-empty">NOT CONFIGURED</span>}
            </dd>
          </div>
        </dl>
        <EvidenceList evidenceIds={netspout.evidence_ids} evidenceById={evidenceById} state={netspout.verification_state} />
      </section>

      <section className="contract-card contract-card--wide">
        <h3>SPL field scope</h3>
        <div className="field-scope-grid">
          <div>
            <strong>Production fields</strong>
            <ValueList values={source.spl_field_scope.production_fields} empty={missingLabel(source.spl_field_scope.portable_spl_status, true)} code />
          </div>
          <div>
            <strong>NetSpout-only fields</strong>
            <ValueList values={source.spl_field_scope.netspout_only_fields} empty={missingLabel(source.spl_field_scope.portable_spl_status)} code />
          </div>
        </div>
        <StatusBadge status={source.spl_field_scope.portable_spl_status.replaceAll('_', ' ')} />
      </section>

      <section className="contract-card contract-card--wide">
        <h3>Known limitations</h3>
        {source.known_limitations.length > 0 ? (
          <ul className="catalog-limitations">{source.known_limitations.map((item) => <li key={item}>{item}</li>)}</ul>
        ) : <span className="catalog-empty">NO EVIDENCE</span>}
      </section>
    </div>
  );
}

export function ProvenanceView({ mode }: { mode: ExperienceMode }) {
  const { data, loading, error, retry } = useCatalogData();
  const [query, setQuery] = useState('');
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const filteredSources = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    if (!data || !normalized) return data?.sources ?? [];
    return data.sources.filter((source) =>
      [source.product, source.vendor, source.telemetry_source, source.source_id, ...source.domains]
        .join(' ')
        .toLowerCase()
        .includes(normalized),
    );
  }, [data, query]);

  const selected =
    data?.sources.find((source) => source.source_id === selectedId) ??
    filteredSources[0] ??
    null;
  const evidenceById = useMemo(
    () => new Map(data?.evidence.map((item) => [item.evidence_id, item]) ?? []),
    [data],
  );

  if (loading) return <StatePanel kind="loading" message="Loading backend catalog contracts." />;
  if (error || !data) {
    return (
      <StatePanel
        kind="error"
        title="Catalog unavailable"
        message={`The backend catalog request failed${error ? `: ${error}` : '.'}`}
        action={<button type="button" className="button button--quiet" onClick={retry}>Retry</button>}
      />
    );
  }

  return (
    <div className="workspace-stack catalog-workspace">
      <Panel
        title="Telemetry Provenance"
        description={`Backend catalog ${data.summary.catalog_version} · ${data.summary.source_count} sources · ${data.summary.evidence_count} evidence records`}
      >
        <div className="catalog-browser">
          <label className="catalog-search">
            <Search />
            <span className="sr-only">Search sources</span>
            <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search source, vendor, domain…" />
          </label>
          <div className="catalog-source-list" role="listbox" aria-label="Catalog sources">
            {filteredSources.map((source) => (
              <button
                type="button"
                role="option"
                aria-selected={source.source_id === selected?.source_id}
                className={source.source_id === selected?.source_id ? 'catalog-source--selected' : ''}
                key={source.source_id}
                onClick={() => setSelectedId(source.source_id)}
              >
                <span><strong>{source.product}</strong><small>{source.vendor} · {source.telemetry_source}</small></span>
                <StatusBadge status={source.verification_state.replaceAll('_', ' ')} />
              </button>
            ))}
            {filteredSources.length === 0 && <span className="catalog-empty">NO EVIDENCE</span>}
          </div>
        </div>
      </Panel>

      {selected && (
        <Panel
          title={selected.product}
          description={`${selected.source_id} · ${selected.domains.join(', ') || 'NOT CONFIGURED'}`}
          actions={<StatusBadge status={selected.verification_state.replaceAll('_', ' ')} />}
        >
          {mode === 'simple' ? (
            <SimpleProvenance source={selected} evidenceById={evidenceById} />
          ) : (
            <AdvancedProvenance source={selected} evidenceById={evidenceById} />
          )}
        </Panel>
      )}
    </div>
  );
}
