import { useEffect, useMemo, useState } from 'react';
import { getApiBaseUrl } from '../../lib/api';
import type { ExperienceMode } from '../../app/navigation';
import type {
  AttackDataset,
  SecurityDetectionDetail,
  SecurityDetectionSummary,
} from '../../types/securityContent';

const API = getApiBaseUrl();
type LabTab =
  | 'overview'
  | 'detections'
  | 'stories'
  | 'datasets'
  | 'compatibility'
  | 'mitre'
  | 'runs'
  | 'research';

const TAB_LABELS: Record<LabTab, string> = {
  overview: 'Overview',
  detections: 'Detection Explorer',
  stories: 'Analytic Stories',
  datasets: 'Attack Datasets',
  compatibility: 'Compatibility Matrix',
  mitre: 'MITRE Coverage',
  runs: 'Validation Runs',
  research: 'Research Required',
};

interface Props {
  mode: ExperienceMode;
}

interface Summary {
  detections: number;
  analytic_stories: number;
  attack_dataset_manifests: number;
  attack_dataset_files: number;
  dependencies_resolved: number;
  duplicate_ids: number;
  parse_failures: number;
  compatibility_counts: Record<string, number>;
  upstreams: {
    security_content: { commit: string; branch: string };
    attack_data: { commit: string; branch: string };
  };
}

const statusClass = (status: string) =>
  `source-status source-status--${status.toLowerCase().replaceAll('_', '-')}`;

export function SecurityContentLab({ mode }: Props) {
  const [tab, setTab] = useState<LabTab>('detections');
  const [summary, setSummary] = useState<Summary | null>(null);
  const [detections, setDetections] = useState<SecurityDetectionSummary[]>([]);
  const [selected, setSelected] = useState<SecurityDetectionDetail | null>(null);
  const [datasets, setDatasets] = useState<AttackDataset[]>([]);
  const [stories, setStories] = useState<Array<{ content_id: string; name: string; description: string }>>([]);
  const [mitre, setMitre] = useState<Array<{
    technique: string;
    name?: string;
    tactics: string[];
    detections: number;
    telemetry_available: number;
    test_data_available: number;
    detection_validated: number;
  }>>([]);
  const [validations, setValidations] = useState<Array<{
    run_id: string;
    detection_id: string;
    status: string;
    matched_event_count: number;
  }>>([]);
  const [query, setQuery] = useState('');
  const [compatibility, setCompatibility] = useState('');
  const [detectionType, setDetectionType] = useState('');
  const [technique, setTechnique] = useState('');
  const [message, setMessage] = useState('Loading pinned upstream metadata…');
  const [busy, setBusy] = useState(false);
  const [retrieved, setRetrieved] = useState<Record<string, string>>({});
  const [targetIndex, setTargetIndex] = useState('idx_network_ops');

  useEffect(() => {
    Promise.all([
      fetch(`${API}/api/security-content/summary`).then((response) => response.json()),
      fetch(`${API}/api/security-content/datasets?limit=200`).then((response) => response.json()),
      fetch(`${API}/api/security-content/stories?limit=200`).then((response) => response.json()),
      fetch(`${API}/api/security-content/mitre`).then((response) => response.json()),
      fetch(`${API}/api/security-content/validations`).then((response) => response.json()),
    ])
      .then(([summaryPayload, datasetPayload, storyPayload, mitrePayload, validationPayload]) => {
        setSummary(summaryPayload);
        setDatasets(datasetPayload);
        setStories(storyPayload);
        setMitre(mitrePayload);
        setValidations(validationPayload);
        setMessage('Pinned metadata loaded. No datasets were downloaded automatically.');
      })
      .catch((error) => setMessage(`Catalog unavailable: ${String(error)}`));
  }, []);

  useEffect(() => {
    const params = new URLSearchParams({ limit: '200' });
    if (query) params.set('q', query);
    if (compatibility) params.set('compatibility', compatibility);
    if (detectionType) params.set('detection_type', detectionType);
    if (technique) params.set('technique', technique);
    fetch(`${API}/api/security-content/detections?${params}`)
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json();
      })
      .then((payload) => setDetections(payload.items ?? []))
      .catch((error) => setMessage(`Detection search failed: ${String(error)}`));
  }, [query, compatibility, detectionType, technique]);

  const detectionTypes = useMemo(
    () => [...new Set(detections.map((item) => item.detection_type).filter(Boolean))].sort(),
    [detections],
  );

  const openDetection = async (item: SecurityDetectionSummary) => {
    setBusy(true);
    try {
      const response = await fetch(
        `${API}/api/security-content/detections/${encodeURIComponent(item.catalog_key)}`,
      );
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      setSelected(await response.json());
    } catch (error) {
      setMessage(`Detection detail failed: ${String(error)}`);
    } finally {
      setBusy(false);
    }
  };

  const retrieveDataset = async (file: AttackDataset['files'][number]) => {
    setBusy(true);
    setMessage(`Retrieving ${file.path} from the pinned Attack Data revision…`);
    try {
      const response = await fetch(`${API}/api/security-content/datasets/retrieve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dataset_path: file.path }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? `HTTP ${response.status}`);
      setRetrieved((current) => ({ ...current, [file.path]: payload.local_id }));
      setMessage(`Integrity verified: ${payload.size_bytes} bytes, SHA-256 ${payload.sha256}.`);
    } catch (error) {
      setMessage(`Selective retrieval blocked: ${String(error)}`);
    } finally {
      setBusy(false);
    }
  };

  const replayDataset = async (file: AttackDataset['files'][number]) => {
    const localId = retrieved[file.path];
    if (!localId) return;
    setBusy(true);
    try {
      const response = await fetch(`${API}/api/security-content/replays`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          local_id: localId,
          dataset_path: file.path,
          index: targetIndex,
          timestamp_mode: 'CURRENT',
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? `HTTP ${response.status}`);
      setMessage(
        `Replay ${payload.run_id}: ${payload.events_sent}/${payload.events_read} events sent. HEC acceptance is not indexing proof.`,
      );
      setTab('runs');
    } catch (error) {
      setMessage(`Replay blocked: ${String(error)}`);
    } finally {
      setBusy(false);
    }
  };

  return (
    <main className="source-page security-content-lab" aria-labelledby="security-content-title">
      <header className="source-header">
        <div>
          <p className="source-eyebrow">SECURITY CONTENT LAB · METADATA-FIRST</p>
          <h1 id="security-content-title">Splunk Detection Compatibility</h1>
          <p>
            Discover what an upstream detection requires, compare it with NetSpout telemetry,
            and validate bounded evidence without claiming production efficacy.
          </p>
        </div>
        <div className="source-summary" aria-label="Security content inventory">
          <strong>{summary?.detections ?? '—'}</strong><span>detections</span>
          <strong>{summary?.analytic_stories ?? '—'}</strong><span>stories</span>
          <strong>{summary?.attack_dataset_manifests ?? '—'}</strong><span>dataset manifests</span>
        </div>
      </header>

      <div className="setup-security-note" role="status">
        <span aria-hidden="true">🛡</span>
        <div>
          <strong>{message}</strong>
          <span>
            Upstream SPL and datasets are untrusted. Downloads are explicit, pinned, size-limited,
            integrity-checked, and never execute bundled scripts or attack tooling.
          </span>
        </div>
      </div>

      <nav className="security-lab-tabs" aria-label="Security Content Lab sections">
        {(['overview', 'detections', 'stories', 'datasets', 'compatibility', 'mitre', 'runs', 'research'] as LabTab[]).map(
          (item) => (
            <button
              type="button"
              key={item}
              className={tab === item ? 'active' : ''}
              onClick={() => setTab(item)}
            >
              {TAB_LABELS[item]}
            </button>
          ),
        )}
      </nav>

      {tab === 'overview' && summary && (
        <section className="security-card-grid" aria-label="Security Content Lab overview">
          <article>
            <h2>Pinned upstream inventory</h2>
            <p>{summary.detections} detections · {summary.analytic_stories} stories</p>
            <small>{summary.upstreams.security_content.commit}</small>
          </article>
          <article>
            <h2>Metadata-only Attack Data</h2>
            <p>{summary.attack_dataset_manifests} manifests · {summary.attack_dataset_files} files</p>
            <small>{summary.upstreams.attack_data.commit}</small>
          </article>
          <article>
            <h2>Conservative dependency analysis</h2>
            <p>{summary.dependencies_resolved} detection dependencies resolved</p>
            <small>{summary.parse_failures} parse failures · {summary.duplicate_ids} duplicate IDs quarantined</small>
          </article>
        </section>
      )}

      {tab === 'detections' && (
        <>
          <section className="source-toolbar" aria-label="Detection filters">
            <label>
              Search
              <input
                aria-label="Search detections"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Detection, story, source, MITRE technique"
              />
            </label>
            <label>
              Compatibility
              <select value={compatibility} onChange={(event) => setCompatibility(event.target.value)}>
                <option value="">All statuses</option>
                {Object.keys(summary?.compatibility_counts ?? {}).sort().map((status) => (
                  <option value={status} key={status}>{status}</option>
                ))}
              </select>
            </label>
            <label>
              Detection type
              <select value={detectionType} onChange={(event) => setDetectionType(event.target.value)}>
                <option value="">All types</option>
                {detectionTypes.map((value) => <option value={value} key={value}>{value}</option>)}
              </select>
            </label>
            <label>
              MITRE technique
              <input
                aria-label="Filter by MITRE technique"
                value={technique}
                onChange={(event) => setTechnique(event.target.value)}
                placeholder="T1190"
              />
            </label>
          </section>

          <section className="source-layout">
            <div className="source-list" aria-label="Detection results">
              {detections.map((detection) => (
                <button
                  type="button"
                  key={detection.catalog_key}
                  className={selected?.catalog_key === detection.catalog_key ? 'active' : ''}
                  onClick={() => openDetection(detection)}
                >
                  <span>
                    <strong>{detection.name}</strong>
                    <small>{detection.data_source_names.join(' · ') || 'Dependency unresolved'}</small>
                  </span>
                  <span className={statusClass(detection.compatibility.status)}>
                    {detection.compatibility.status}
                  </span>
                </button>
              ))}
            </div>

            <article className="source-detail" aria-live="polite">
              {!selected ? (
                <div className="source-empty">
                  <h2>Select a detection</h2>
                  <p>Review telemetry, fields, macros, lookups, data models, replay data, and evidence.</p>
                </div>
              ) : (
                <>
                  <div className="source-detail-heading">
                    <div>
                      <p className="source-eyebrow">{selected.content_id} · v{selected.version}</p>
                      <h2>{selected.name}</h2>
                    </div>
                    <span className={statusClass(selected.compatibility.status)}>
                      {selected.compatibility.status}
                    </span>
                  </div>
                  <p>{selected.description}</p>
                  <dl className="source-facts">
                    <div><dt>Telemetry</dt><dd>{selected.data_source_names.join(', ') || 'Unresolved'}</dd></div>
                    <div><dt>Sourcetypes</dt><dd>{selected.dependencies.sourcetypes.join(', ') || 'Unresolved'}</dd></div>
                    <div><dt>Required fields</dt><dd>{selected.dependencies.required_fields.join(', ') || 'Unresolved'}</dd></div>
                    <div><dt>Macros</dt><dd>{selected.dependencies.macros.join(', ') || 'None identified'}</dd></div>
                    <div><dt>Lookups</dt><dd>{selected.dependencies.lookups.join(', ') || 'None identified'}</dd></div>
                    <div><dt>Data models</dt><dd>{selected.dependencies.data_models.join(', ') || 'None identified'}</dd></div>
                    <div><dt>Technology Add-ons</dt><dd>{selected.dependencies.technology_add_ons.join(', ') || 'None identified'}</dd></div>
                    <div><dt>MITRE</dt><dd>{selected.mitre_attack_ids.join(', ') || 'Not mapped'}</dd></div>
                  </dl>
                  <h3>What remains missing</h3>
                  <ul>
                    {(selected.compatibility.reasons.length
                      ? selected.compatibility.reasons
                      : ['No structural blocker identified; runtime validation remains separate.']
                    ).map((reason) => <li key={reason}>{reason}</li>)}
                  </ul>
                  <h3>Validation meaning</h3>
                  <p>
                    Detection validation: {selected.compatibility.detection_validation}. Production
                    efficacy: {selected.production_detection_efficacy}.
                  </p>
                  {selected.validation_evidence && (
                    <p>
                      Evidence {selected.validation_evidence.run_id}:{' '}
                      {selected.validation_evidence.indexed_event_count} indexed,{' '}
                      {selected.validation_evidence.matched_event_count} matched.
                    </p>
                  )}
                  {selected.attack_data.length > 0 && (
                    <p>{selected.attack_data.length} curated Attack Data reference(s) are associated.</p>
                  )}
                  {mode === 'advanced' && (
                    <>
                      <h3>Upstream SPL — review before execution</h3>
                      <pre className="security-spl-preview">{selected.spl}</pre>
                      <small>{selected.dependencies.parser_scope}</small>
                    </>
                  )}
                </>
              )}
            </article>
          </section>
        </>
      )}

      {tab === 'datasets' && (
        <section className="security-dataset-grid" aria-label="Attack datasets">
          <label className="security-index-field">
            Authorized destination index
            <input value={targetIndex} onChange={(event) => setTargetIndex(event.target.value)} />
          </label>
          {datasets.map((dataset) => (
            <article key={dataset.catalog_key}>
              <h2>{dataset.name}</h2>
              <p>{dataset.description}</p>
              <small>{dataset.mitre_techniques.join(', ')} · {dataset.environment}</small>
              {dataset.files.map((file) => (
                <div className="security-dataset-file" key={file.path}>
                  <code>{file.path}</code>
                  <span>{file.sourcetype || 'sourcetype unresolved'} · {file.size_bytes ?? 'unknown'} bytes</span>
                  <div>
                    <button type="button" disabled={busy} onClick={() => retrieveDataset(file)}>
                      Explicitly retrieve
                    </button>
                    <button
                      type="button"
                      disabled={busy || !retrieved[file.path]}
                      onClick={() => replayDataset(file)}
                    >
                      Replay to authorized lab
                    </button>
                  </div>
                </div>
              ))}
            </article>
          ))}
        </section>
      )}

      {tab === 'stories' && (
        <section className="security-card-grid" aria-label="Analytic stories">
          {stories.map((story) => (
            <article key={story.content_id}>
              <h2>{story.name}</h2>
              <p>{story.description}</p>
            </article>
          ))}
        </section>
      )}

      {tab === 'mitre' && (
        <section className="security-card-grid" aria-label="MITRE ATT&CK coverage">
          {mitre.map((row) => (
            <article key={row.technique}>
              <h2>{row.technique} · {row.name || 'Metadata unresolved'}</h2>
              <p>{row.tactics.join(', ') || 'Tactic unresolved'}</p>
              <small>
                {row.detections} content · {row.telemetry_available} telemetry ·{' '}
                {row.test_data_available} test data · {row.detection_validated} validated
              </small>
            </article>
          ))}
        </section>
      )}

      {tab === 'compatibility' && (
        <section className="security-card-grid" aria-label="Compatibility matrix">
          {Object.entries(summary?.compatibility_counts ?? {}).sort().map(([status, count]) => (
            <article key={status}>
              <span className={statusClass(status)}>{status}</span>
              <h2>{count} detections</h2>
              <p>Compatibility is structural evidence only; runtime, Splunk, and efficacy remain independent.</p>
            </article>
          ))}
        </section>
      )}

      {tab === 'runs' && (
        <section className="security-card-grid" aria-label="Validation runs">
          {validations.length === 0 ? (
            <article><h2>No persisted validation evidence</h2><p>A replay acceptance is not a detection validation.</p></article>
          ) : validations.map((run) => (
            <article key={run.run_id}>
              <h2>{run.run_id}</h2>
              <p>{run.detection_id}</p>
              <span className={statusClass(run.status)}>{run.status}</span>
              <small>{run.matched_event_count} matched events</small>
            </article>
          ))}
        </section>
      )}

      {tab === 'research' && (
        <section className="security-card-grid" aria-label="Research required">
          <article>
            <h2>{summary?.compatibility_counts.RESEARCH_REQUIRED ?? 0} unresolved detections</h2>
            <p>
              These detections lack authoritative dependency detail and are not promoted to
              compatibility. Filter Detection Explorer by RESEARCH_REQUIRED for review.
            </p>
          </article>
        </section>
      )}

    </main>
  );
}
