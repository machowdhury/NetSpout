import { useEffect, useMemo, useState } from 'react';
import { BookOpen, ExternalLink, Network, ShieldCheck } from 'lucide-react';
import { coverageApi } from '../../lib/coverageApi';
import type {
  CiscoCoverageCatalog,
  CoverageProduct,
  ProductSourceCoverage,
} from '../../types/coverage';
import { Panel, StatePanel, StatusBadge } from '../ui/SystemPrimitives';

type CoverageTab = 'coverage' | 'contracts' | 'scenario' | 'production';

function List({ values, empty = 'RESEARCH REQUIRED' }: { values: string[]; empty?: string }) {
  return values.length ? (
    <ul className="coverage-list">{values.map((value) => <li key={value}>{value}</li>)}</ul>
  ) : <span className="catalog-empty">{empty}</span>;
}

function SourceCard({
  source,
  selected,
  onSelect,
}: {
  source: ProductSourceCoverage;
  selected: boolean;
  onSelect: () => void;
}) {
  return (
    <button
      type="button"
      className={`coverage-source-card${selected ? ' coverage-source-card--selected' : ''}`}
      onClick={onSelect}
    >
      <span>{source.name}</span>
      <StatusBadge status={source.maturity.replaceAll('_', ' ')} />
      <small>{source.native_format ?? 'NATIVE CONTRACT RESEARCH REQUIRED'}</small>
    </button>
  );
}

function ContractView({
  source,
  evidence,
}: {
  source: ProductSourceCoverage;
  evidence: CiscoCoverageCatalog['evidence'];
}) {
  const claims = evidence.filter((item) => source.evidence_ids.includes(item.claim_id));
  return (
    <div className="coverage-contract-grid" data-testid="cisco-contracts">
      <article>
        <h3>Native Contract</h3>
        <StatusBadge status={source.maturity.replaceAll('_', ' ')} />
        <dl>
          <div><dt>Format</dt><dd>{source.native_format ?? 'RESEARCH REQUIRED'}</dd></div>
          <div><dt>Transport</dt><dd><List values={source.transport_ids} /></dd></div>
          <div><dt>Schema</dt><dd><List values={source.schema_references} /></dd></div>
        </dl>
      </article>
      <article>
        <h3>Splunk Contract</h3>
        <StatusBadge status={source.splunk.requirement.replaceAll('_', ' ')} />
        <dl>
          <div><dt>Integration</dt><dd><List values={source.splunk.integration_ids} /></dd></div>
          <div><dt>Sourcetype</dt><dd><List values={source.splunk.sourcetypes} /></dd></div>
          <div><dt>CIM</dt><dd>{source.splunk.cim_status.replaceAll('_', ' ')}</dd></div>
        </dl>
      </article>
      <article>
        <h3>NetSpout Contract</h3>
        <StatusBadge status={source.generator_status} />
        <dl>
          <div><dt>Contract</dt><dd><code>{source.netspout_contract_id ?? 'NOT ESTABLISHED'}</code></dd></div>
          <div><dt>Generator</dt><dd>{source.generator_status}</dd></div>
          <div><dt>Limitations</dt><dd><List values={source.limitations} empty="NONE RECORDED" /></dd></div>
        </dl>
      </article>
      <article className="coverage-contract-evidence">
        <h3>Why trust this claim</h3>
        {claims.length ? claims.map((claim) => (
          <div className="coverage-evidence" key={claim.claim_id}>
            <strong>{claim.source_title}</strong>
            <span>{claim.publisher} · {claim.confidence} · verified {claim.verified_date}</span>
            <p>{claim.claim}</p>
            <a href={claim.reference} target="_blank" rel="noreferrer">
              Open authoritative reference <ExternalLink size={13} />
            </a>
          </div>
        )) : <StatePanel kind="empty" title="Research required" message="No authoritative source has established this contract." />}
      </article>
    </div>
  );
}

function ProductList({
  catalog,
  selected,
  onSelect,
}: {
  catalog: CiscoCoverageCatalog;
  selected: string;
  onSelect: (id: string) => void;
}) {
  return (
    <aside className="coverage-products">
      {catalog.families.map((family) => (
        <section key={family.family_id}>
          <h3>{family.name}</h3>
          {family.product_ids.map((id) => {
            const product = catalog.products.find((item) => item.product_id === id);
            if (!product) return null;
            return (
              <button
                type="button"
                key={id}
                className={selected === id ? 'is-selected' : ''}
                onClick={() => onSelect(id)}
              >
                <span>{product.current_name}</span>
                <small>{product.maturity.replaceAll('_', ' ')}</small>
              </button>
            );
          })}
        </section>
      ))}
    </aside>
  );
}

function GoldenScenario({
  catalog,
  product,
}: {
  catalog: CiscoCoverageCatalog;
  product: CoverageProduct;
}) {
  const scenario = catalog.golden_scenarios.find((item) =>
    item.product_ids.includes(product.product_id));
  if (!scenario) {
    return <StatePanel kind="empty" title="No Golden Scenario" message="Coverage discovery does not imply a runnable scenario." />;
  }
  return (
    <div className="coverage-golden" data-testid="golden-scenario">
      <article className="coverage-hero-card">
        <span className="eyebrow">Golden Scenario Program</span>
        <h2>{scenario.title}</h2>
        <p>{scenario.description}</p>
        <div className="catalog-badge-row">
          <StatusBadge status={scenario.maturity.replaceAll('_', ' ')} />
          <StatusBadge status="SHARED STATE" />
          <StatusBadge status="NATIVE RUNTIME" />
        </div>
      </article>
      <div className="coverage-flow" aria-label="Golden Scenario evidence chain">
        {['Enterprise State', 'Incident', '3 Native Sources', 'Splunk', 'Investigation', 'Validation', 'Replay'].map((item) => (
          <div key={item}>{item}</div>
        ))}
      </div>
      <Panel title="Multi-channel runtime">
        <div className="coverage-channel-grid">
          {scenario.source_ids.map((sourceId) => {
            const source = product.sources.find((item) => item.source_id === sourceId);
            return (
              <article key={sourceId}>
                <Network size={18} />
                <strong>{source?.name ?? sourceId}</strong>
                <span>{source?.maturity.replaceAll('_', ' ')}</span>
              </article>
            );
          })}
        </div>
      </Panel>
      <Panel title="Guided investigation">
        <p>Find the incident → identify the interface → establish the timeline → correlate all three sources → validate recovery.</p>
        <p><strong>SPL portability:</strong> NETSPOUT SPECIFIC. A separate production guide removes run and phase metadata assumptions.</p>
      </Panel>
      <div className="coverage-actions">
        <a className="button button--primary" href="#/generate/scenarios">Open Guided Scenario</a>
        <a className="button button--quiet" href="#/build/studio">Clone in Scenario Studio</a>
      </div>
    </div>
  );
}

function ProductionView({
  catalog,
  product,
}: {
  catalog: CiscoCoverageCatalog;
  product: CoverageProduct;
}) {
  const scenario = catalog.golden_scenarios.find((item) => item.product_ids.includes(product.product_id));
  const guide = catalog.production_guides.find((item) => item.guide_id === scenario?.production_guide_id);
  const operations = catalog.troubleshooting.filter((item) => item.product_ids.includes(product.product_id));
  return (
    <div className="coverage-production" data-testid="production-guidance">
      <Panel title="Platform-correct troubleshooting">
        {operations.length ? operations.map((operation) => (
          <article key={operation.operation_id}>
            <StatusBadge status={operation.operation_type.replaceAll('_', ' ')} />
            <code>{operation.operation}</code>
            <p>{operation.purpose}</p>
            <small>Expected scenario result: {operation.expected_result_model}</small>
          </article>
        )) : <StatePanel kind="empty" title="Research required" message="No command or API is shown without authoritative evidence." />}
      </Panel>
      <Panel title="Take This to Production">
        {guide ? (
          <div className="coverage-guide-grid">
            <section><h3>Real sources required</h3><List values={guide.real_sources} /></section>
            <section><h3>Collection</h3><List values={guide.collection_mechanisms} /></section>
            <section><h3>Splunk integration</h3><List values={guide.integration_requirements} /></section>
            <section><h3>Sourcetype and CIM</h3><List values={[...guide.sourcetypes, ...guide.cim_requirements]} /></section>
            <section><h3>Production prerequisites</h3><List values={guide.prerequisites} /></section>
            <section><h3>Known gaps</h3><List values={[...guide.known_gaps, ...guide.unvalidated_assumptions]} /></section>
          </div>
        ) : <StatePanel kind="empty" title="Not established" message="Production guidance requires a Golden Scenario." />}
      </Panel>
    </div>
  );
}

export function CiscoCoverageView() {
  const [catalog, setCatalog] = useState<CiscoCoverageCatalog | null>(null);
  const [error, setError] = useState('');
  const [selectedId, setSelectedId] = useState('cisco-ios-xr');
  const [sourceId, setSourceId] = useState('cisco-ios-xr-interface-syslog');
  const [tab, setTab] = useState<CoverageTab>('coverage');

  useEffect(() => {
    coverageApi.cisco().then(setCatalog).catch((reason) => setError(String(reason)));
  }, []);

  const product = useMemo(
    () => catalog?.products.find((item) => item.product_id === selectedId) ?? null,
    [catalog, selectedId],
  );
  const source = product?.sources.find((item) => item.coverage_id === sourceId) ?? product?.sources[0] ?? null;

  if (error) return <StatePanel kind="error" title="Coverage unavailable" message={error} />;
  if (!catalog || !product) return <StatePanel kind="loading" message="Loading evidence-backed Cisco coverage." />;

  const chooseProduct = (id: string) => {
    const next = catalog.products.find((item) => item.product_id === id);
    setSelectedId(id);
    setSourceId(next?.sources[0]?.coverage_id ?? '');
    setTab('coverage');
  };

  return (
    <div className="coverage-workspace">
      <header className="coverage-header">
        <div>
          <span className="eyebrow">Cisco Coverage Foundation</span>
          <h1>Evidence before generation</h1>
          <p>{catalog.independence_notice}</p>
        </div>
        <div className="coverage-summary">
          {Object.entries(catalog.summary).filter(([key]) => key !== 'vendor_id').map(([key, value]) => (
            <div key={key}><strong>{value}</strong><span>{key.replaceAll('_', ' ')}</span></div>
          ))}
        </div>
      </header>
      <div className="coverage-layout">
        <ProductList catalog={catalog} selected={selectedId} onSelect={chooseProduct} />
        <main>
          <header className="coverage-product-header">
            <div>
              <span>{catalog.families.find((item) => item.family_id === product.family_id)?.name}</span>
              <h2>{product.current_name}</h2>
              <p>{product.pack_id ? `Product Pack: ${product.pack_id}` : 'No Product Pack — generation is not implied.'}</p>
            </div>
            <StatusBadge status={product.maturity.replaceAll('_', ' ')} />
          </header>
          <nav className="coverage-tabs" aria-label="Cisco coverage views">
            {(['coverage', 'contracts', 'scenario', 'production'] as CoverageTab[]).map((item) => (
              <button type="button" key={item} className={tab === item ? 'is-active' : ''} onClick={() => setTab(item)}>
                {item === 'scenario' ? 'Golden Scenario' : item}
              </button>
            ))}
          </nav>
          {tab === 'coverage' && (
            <div className="coverage-overview">
              {product.sources.length ? (
                <>
                  <section className="coverage-source-list">
                    <h3>Source maturity</h3>
                    {product.sources.map((item) => (
                      <SourceCard key={item.coverage_id} source={item} selected={source?.coverage_id === item.coverage_id} onSelect={() => setSourceId(item.coverage_id)} />
                    ))}
                  </section>
                  {source && <ContractView source={source} evidence={catalog.evidence} />}
                </>
              ) : (
                <StatePanel kind="empty" title={product.maturity.replaceAll('_', ' ')} message="This product is represented in the taxonomy, but authoritative source contracts have not been established." />
              )}
              {product.research_gaps.length > 0 && (
                <Panel title="Research gaps"><List values={product.research_gaps} /></Panel>
              )}
            </div>
          )}
          {tab === 'contracts' && source && <ContractView source={source} evidence={catalog.evidence} />}
          {tab === 'scenario' && <GoldenScenario catalog={catalog} product={product} />}
          {tab === 'production' && <ProductionView catalog={catalog} product={product} />}
          {!source && tab === 'contracts' && <StatePanel kind="empty" title="Research required" message="No native, Splunk, or NetSpout contract is available." />}
        </main>
      </div>
      <footer className="coverage-trust"><ShieldCheck size={18} /><span>Unknown remains unknown. No generic Cisco-looking fallback is generated.</span><BookOpen size={18} /></footer>
    </div>
  );
}
