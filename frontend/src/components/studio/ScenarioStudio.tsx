import { useEffect, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import {
  AlertTriangle,
  BadgeCheck,
  Boxes,
  ChevronLeft,
  ChevronRight,
  Copy,
  FileSearch,
  FlaskConical,
  GitBranch,
  LockKeyhole,
  Play,
  Plus,
  Save,
  ShieldCheck,
  Sparkles,
} from 'lucide-react';
import { studioApi } from '../../lib/studioApi';
import type { GenerationScenario } from '../../types/generation';
import type {
  CreationPath,
  CustomSourceDraft,
  FieldClassification,
  SampleAnalysis,
  SampleProvenance,
  StudioHome,
  StudioRun,
  StudioScenarioPack,
  StudioValidation,
} from '../../types/studio';
import type { ExperienceMode } from '../../app/navigation';
import { TopologyPreview } from '../generation/TopologyPreview';
import { StatusBadge } from '../ui/SystemPrimitives';

const EDITOR_STEPS = [
  'ENVIRONMENT',
  'TOPOLOGY',
  'STATE',
  'TIMELINE',
  'TELEMETRY',
  'PARAMETERS',
  'INVESTIGATION',
  'PREVIEW',
  'VALIDATE',
  'SAVE & RUN',
] as const;

type EditorStep = (typeof EDITOR_STEPS)[number];
type StudioScreen = 'HOME' | 'SOURCES' | 'CLONE' | 'IMPORT' | 'FIELDS' | EditorStep;

const classifications: FieldClassification[] = [
  'STRUCTURAL',
  'MODELED',
  'CORRELATION',
  'DERIVED',
  'SENSITIVE',
  'UNKNOWN',
];

const emptyValidation = (): StudioValidation => ({
  valid: false,
  maturity_ceiling: 'DRAFT',
  checks: [],
  errors: [],
  warnings: [],
});

function toScenario(pack: StudioScenarioPack): GenerationScenario {
  const observerId = 'studio-splunk';
  const producerId = pack.entities[0]?.entity_id ?? 'studio-source';
  const nodes = pack.entities.map((entity) => ({
    node_id: entity.entity_id,
    technology_id: `studio-${entity.entity_type}`,
    zone_id: entity.zone_id,
    role: entity.entity_type,
    source_ids: pack.correlation_mappings
      .filter((item) => item.entity_id === entity.entity_id)
      .map((item) => item.source_id),
    label: entity.label,
    entity_id: entity.entity_id,
    description: 'Scenario Studio modeled entity',
  }));
  if (!nodes.some((item) => item.node_id === observerId)) {
    nodes.push({
      node_id: observerId,
      technology_id: 'splunk-enterprise',
      zone_id: pack.zones[0]?.zone_id ?? 'lab',
      role: 'splunk',
      source_ids: [],
      label: 'Splunk',
      entity_id: observerId,
      description: 'Configured destination',
    });
  }
  return {
    scenario_id: pack.scenario_id,
    title: pack.title,
    description: pack.description,
    story: pack.story,
    domain: 'netops',
    category: 'PRIVATE_STUDIO',
    technical_description: 'Private deterministic Scenario Studio draft.',
    difficulty: 'CUSTOM',
    expected_duration_minutes: Math.max(
      1,
      Math.ceil(Math.max(...pack.timeline.map((item) => item.offset_seconds), 60) / 60),
    ),
    learning_objectives: ['Validate a locally authored telemetry scenario.'],
    business_impact: 'Modeled private lab impact.',
    prerequisites: ['Configured local runtime'],
    technology_ids: [...new Set(pack.entities.map((item) => `studio-${item.entity_type}`))],
    source_ids: pack.source_ids,
    entities: [...pack.entities.map((item) => item.entity_id), observerId],
    zones: pack.zones,
    nodes,
    relationships: pack.relationships.map((item) => ({
      relationship_id: item.relationship_id,
      source_node_id: item.source_entity_id,
      target_node_id: item.target_entity_id,
      relationship_type: item.relationship_type,
      protocol: item.protocol,
      telemetry_source_ids: pack.source_ids,
    })),
    telemetry_paths: pack.source_ids.map((sourceId) => ({
      path_id: `path-${sourceId}`,
      source_id: sourceId,
      producer_node_id: producerId,
      observer_node_id: observerId,
      label: sourceId,
      protocol: 'DECLARED CONTRACT',
    })),
    incident_path: [producerId, observerId],
    runtime_state_keys: [
      ...new Set(
        pack.timeline.flatMap((transition) =>
          transition.state_changes.map((item) => item.state_key),
        ),
      ),
    ],
    timeline: pack.timeline.map((item) => ({
      step_id: item.transition_id,
      stage: item.stage,
      description: item.title,
      state_changes: Object.fromEntries(
        item.state_changes.map((change) => [change.state_key, String(change.value)]),
      ),
      entity_state_changes: Object.fromEntries(
        item.state_changes.map((change) => [
          change.entity_id,
          `${change.state_key}=${String(change.value)}`,
        ]),
      ),
      incident_ids: item.stage === 'INCIDENT' ? ['studio-incident'] : [],
      evidence_source_ids: item.source_ids,
    })),
    expected_evidence: ['GENERATED', 'SPLUNK_DISPATCHED', 'SPLUNK_OBSERVED'],
    investigation_recipe_ids: pack.investigations.map((item) => item.investigation_id),
    integration_recommendation_ids: [],
    production_replication_guidance: ['Private Studio packs are local lab artifacts.'],
    visualization: {
      mode: 'AUTOMATIC',
      direction: 'LEFT_TO_RIGHT',
      curated_layout_ref: null,
    },
    composition_id: `compose-${pack.scenario_id}`,
    verification_state: 'PARTIALLY_VERIFIED',
    maturity: pack.maturity,
    source_count: pack.source_ids.length,
    integration_count: 0,
    runnable: true,
  };
}

export function ScenarioStudio({ experienceMode }: { experienceMode: ExperienceMode }) {
  const [home, setHome] = useState<StudioHome | null>(null);
  const [screen, setScreen] = useState<StudioScreen>('HOME');
  const [selectedSources, setSelectedSources] = useState<string[]>([]);
  const [draft, setDraft] = useState<StudioScenarioPack | null>(null);
  const [analysis, setAnalysis] = useState<SampleAnalysis | null>(null);
  const [authorizationAck, setAuthorizationAck] = useState(false);
  const [provenance, setProvenance] = useState<SampleProvenance>('LAB SAMPLE — SANITIZED');
  const [customSourceId, setCustomSourceId] = useState('private-synthetic-source');
  const [customSourcetype, setCustomSourcetype] = useState('netspout:custom:synthetic');
  const [validation, setValidation] = useState<StudioValidation>(emptyValidation);
  const [saved, setSaved] = useState<StudioScenarioPack | null>(null);
  const [run, setRun] = useState<StudioRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const sampleRef = useRef<HTMLTextAreaElement | null>(null);
  const approvedSampleRef = useRef('');

  const refresh = async () => {
    const result = await studioApi.home();
    setHome(result);
  };

  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect -- synchronizes local UI with the local Studio API
    refresh().catch((reason) => setError(String(reason)));
  }, []);

  useEffect(() => {
    document.getElementById('main-content')?.scrollTo({ top: 0, behavior: 'auto' });
  }, [screen]);

  const sourceById = useMemo(
    () => new Map((home?.sources ?? []).map((item) => [item.source_id, item])),
    [home],
  );
  const scenario = useMemo(() => (draft ? toScenario(draft) : null), [draft]);

  const begin = (path: CreationPath) => {
    setDraft(null);
    setAnalysis(null);
    setValidation(emptyValidation());
    setSaved(null);
    setRun(null);
    setError('');
    if (path === 'EXISTING_SOURCES') setScreen('SOURCES');
    if (path === 'CLONE_SCENARIO') setScreen('CLONE');
    if (path === 'IMPORT_SANITIZED_SAMPLE') setScreen('IMPORT');
  };

  const createExisting = async () => {
    setBusy(true);
    setError('');
    try {
      const next = await studioApi.createDraft(
        'EXISTING_SOURCES',
        selectedSources,
        'Private Interface Degradation',
      );
      setDraft(next);
      setScreen('ENVIRONMENT');
    } catch (reason) {
      setError(String(reason));
    } finally {
      setBusy(false);
    }
  };

  const clone = async (scenarioId: string) => {
    setBusy(true);
    setError('');
    try {
      const next = await studioApi.createDraft(
        'CLONE_SCENARIO',
        [],
        'Private Clone',
        scenarioId,
      );
      setDraft(next);
      setScreen('ENVIRONMENT');
    } catch (reason) {
      setError(String(reason));
    } finally {
      setBusy(false);
    }
  };

  const analyze = async () => {
    const sample = sampleRef.current?.value ?? '';
    setBusy(true);
    setError('');
    try {
      const result = await studioApi.analyze(sample, authorizationAck);
      setAnalysis(result);
      if (result.blocked) {
        approvedSampleRef.current = '';
        if (sampleRef.current) sampleRef.current.value = '';
      } else {
        approvedSampleRef.current = sample;
        setScreen('FIELDS');
      }
    } catch (reason) {
      setError(String(reason));
    } finally {
      setBusy(false);
    }
  };

  const createCustomDraft = async () => {
    if (!analysis || analysis.blocked || !approvedSampleRef.current) return;
    const custom: CustomSourceDraft = {
      source_id: customSourceId,
      display_name: 'Private Synthetic Source',
      sanitized_sample: approvedSampleRef.current,
      analyzed_fingerprint: analysis.sample_fingerprint,
      privacy_status: 'SANITIZED',
      provenance,
      redistribution: 'PRIVATE',
      fields: analysis.fields.map((item) => ({ ...item, authority: 'USER_PROVIDED' })),
      format: analysis.format,
      source_description: 'User-reviewed local private telemetry contract.',
      netspout_sourcetype: customSourcetype || null,
      netspout_sourcetype_acknowledged: Boolean(customSourcetype),
    };
    setBusy(true);
    setError('');
    try {
      const contract = await studioApi.validateCustomSource(custom);
      if (!contract.valid) throw new Error(contract.errors.join('; '));
      const next = await studioApi.createDraft(
        'IMPORT_SANITIZED_SAMPLE',
        [],
        'Private Custom Telemetry',
      );
      const entityId = next.entities[0].entity_id;
      const modeled = custom.fields.find((item) => item.classification === 'MODELED');
      next.source_ids = [custom.source_id];
      next.custom_sources = [custom];
      next.provenance = provenance;
      next.timeline = next.timeline.map((transition) => ({
        ...transition,
        source_ids: [custom.source_id],
        state_changes: modeled
          ? [{
              state_key: modeled.name,
              entity_id: entityId,
              value: transition.stage === 'INCIDENT' ? (modeled.numeric_max ?? 8) : (modeled.numeric_min ?? 0),
              unit: null,
            }]
          : [],
      }));
      next.correlation_mappings = [{
        source_id: custom.source_id,
        source_field: custom.fields.find((item) => item.classification === 'CORRELATION')?.name
          ?? custom.fields.find((item) => item.classification === 'MODELED')?.name
          ?? custom.fields[0].name,
        entity_id: entityId,
        identity_type: 'device',
      }];
      approvedSampleRef.current = '';
      setDraft(next);
      if (sampleRef.current) sampleRef.current.value = '';
      setScreen('ENVIRONMENT');
    } catch (reason) {
      setError(String(reason));
    } finally {
      setBusy(false);
    }
  };

  const changeStep = (direction: -1 | 1) => {
    const current = EDITOR_STEPS.indexOf(screen as EditorStep);
    const next = current + direction;
    if (next >= 0 && next < EDITOR_STEPS.length) setScreen(EDITOR_STEPS[next]);
  };

  const validate = async () => {
    if (!draft) return;
    setBusy(true);
    setError('');
    try {
      const result = await studioApi.validate(draft);
      setValidation(result);
      setScreen('VALIDATE');
    } catch (reason) {
      setError(String(reason));
    } finally {
      setBusy(false);
    }
  };

  const save = async () => {
    if (!draft) return;
    setBusy(true);
    setError('');
    try {
      const result = await studioApi.save(draft);
      setDraft(result);
      setSaved(result);
      await refresh();
      setScreen('SAVE & RUN');
    } catch (reason) {
      setError(String(reason));
    } finally {
      setBusy(false);
    }
  };

  const runSaved = async () => {
    if (!saved) return;
    setBusy(true);
    setError('');
    try {
      setRun(await studioApi.run(saved.pack_id));
    } catch (reason) {
      setError(String(reason));
    } finally {
      setBusy(false);
    }
  };

  const renderHome = () => (
    <div className="studio-home" data-testid="studio-home">
      <section className="studio-hero">
        <div>
          <div className="generation-eyebrow">SCENARIO STUDIO · PRIVATE BY DEFAULT</div>
          <h2>Create a deterministic telemetry scenario</h2>
          <p>
            Compose verified contracts or build a reviewed private source without editing
            NetSpout Core. Structural telemetry stays protected; modeled state remains editable.
          </p>
        </div>
        <div className="studio-hero__boundary">
          <ShieldCheck />
          <strong>Safety boundary</strong>
          <span>Local analysis only. Unknown fields remain unknown.</span>
        </div>
      </section>
      <div className="studio-choice-grid">
        {(home?.creation_paths ?? []).map((item, index) => {
          const Icon = index === 0 ? Boxes : index === 1 ? FileSearch : Copy;
          return (
            <button
              type="button"
              key={item.id}
              className="studio-choice"
              onClick={() => begin(item.id)}
              data-testid={`studio-path-${item.id.toLowerCase()}`}
            >
              <Icon />
              <strong>{item.title}</strong>
              <span>{item.description}</span>
              <em>{index === 1 ? 'PRIVATE / LOCAL ONLY' : 'PACK ARCHITECTURE'}</em>
            </button>
          );
        })}
      </div>
      <section className="studio-private-packs">
        <div className="studio-section-title">
          <LockKeyhole />
          <div><strong>Private packs</strong><span>Stored outside the repository</span></div>
        </div>
        {(home?.private_packs ?? []).length === 0 ? (
          <p className="generation-muted">No private packs saved yet.</p>
        ) : (
          <div className="studio-pack-list">
            {home?.private_packs.map((item) => (
              <button
                type="button"
                key={item.pack_id}
                onClick={async () => {
                  const loaded = await studioApi.load(item.pack_id);
                  setDraft(loaded);
                  setSaved(loaded);
                  setScreen('PREVIEW');
                }}
              >
                <strong>{item.title}</strong>
                <span>{item.maturity} · {item.redistribution}</span>
              </button>
            ))}
          </div>
        )}
      </section>
    </div>
  );

  const renderSourceSelection = () => (
    <div className="studio-panel" data-testid="studio-source-selection">
      <StudioHeading
        eyebrow="PATH A · EXISTING VERIFIED SOURCES"
        title="Choose catalog sources"
        detail="Only sources with executable runtime bindings are selectable."
      />
      <div className="studio-source-grid">
        {(home?.sources ?? []).map((source) => {
          const selected = selectedSources.includes(source.source_id);
          return (
            <label
              key={source.source_id}
              className={`studio-source-card ${selected ? 'is-selected' : ''}`}
            >
              <input
                type="checkbox"
                checked={selected}
                disabled={!source.generation.runnable}
                onChange={() =>
                  setSelectedSources((current) =>
                    selected
                      ? current.filter((item) => item !== source.source_id)
                      : [...current, source.source_id],
                  )
                }
              />
              <div>
                <strong>{source.product}</strong>
                <span>{source.telemetry_source}</span>
              </div>
              <StatusBadge status={source.generation.runnable ? 'READY' : source.generation.state} />
            </label>
          );
        })}
      </div>
      <div className="studio-callout">
        Recommended correlation proof: SNMP + gNMI. Both consume one Phase 5 state plan.
      </div>
      <button
        type="button"
        className="button-primary"
        disabled={selectedSources.length === 0 || busy}
        onClick={createExisting}
      >
        Build Environment <ChevronRight />
      </button>
    </div>
  );

  const renderClone = () => (
    <div className="studio-panel" data-testid="studio-clone-scenario">
      <StudioHeading
        eyebrow="PATH C · CLONE"
        title="Clone a golden scenario"
        detail="Contracts remain immutable. Entities, timing and modeled state become editable."
      />
      <div className="studio-source-grid">
        {(home?.scenarios ?? []).filter((item) => item.runnable).map((item) => (
          <button
            type="button"
            className="studio-source-card"
            key={item.scenario_id}
            onClick={() => clone(item.scenario_id)}
          >
            <GitBranch />
            <div><strong>{item.title}</strong><span>{item.source_count} sources · {item.maturity}</span></div>
            <StatusBadge status={item.verification_state} />
          </button>
        ))}
      </div>
    </div>
  );

  const renderImport = () => (
    <div className="studio-panel" data-testid="studio-import-sample">
      <StudioHeading
        eyebrow="PATH B · CUSTOM SOURCE"
        title="Import an authorized, sanitized sample"
        detail="The browser sends this sample only to the local NetSpout API. It is not persisted during analysis."
      />
      <div className="studio-warning">
        <AlertTriangle />
        <p>{home?.import_notice}</p>
      </div>
      <textarea
        ref={sampleRef}
        className="studio-sample-input"
        aria-label="Sanitized telemetry sample"
        placeholder='{"event_type":"interface_health","device":"router-01.example","src_ip":"192.0.2.10","loss_pct":8}'
      />
      <label className="studio-ack">
        <input
          type="checkbox"
          checked={authorizationAck}
          onChange={(event) => setAuthorizationAck(event.target.checked)}
        />
        I am authorized to use this telemetry and reviewed it for credentials, customer
        identifiers and personal information.
      </label>
      <button type="button" className="button-primary" disabled={!authorizationAck || busy} onClick={analyze}>
        Analyze Locally <FileSearch />
      </button>
      {analysis?.blocked && (
        <section className="studio-findings" data-testid="studio-sensitive-warning">
          <div className="studio-section-title">
            <AlertTriangle />
            <div>
              <strong>IMPORT BLOCKED</strong>
              <span>{analysis.findings.length} values require review</span>
            </div>
          </div>
          {analysis.findings.map((finding) => (
            <div className="studio-finding" key={finding.fingerprint}>
              <StatusBadge status={finding.severity} />
              <strong>{finding.category}</strong>
              <span>{finding.location}</span>
              <code>{finding.redacted_preview}</code>
            </div>
          ))}
          <p>Replace the identified values, then analyze the sanitized sample again.</p>
        </section>
      )}
    </div>
  );

  const renderFields = () => (
    <div className="studio-panel" data-testid="studio-field-classification">
      <StudioHeading
        eyebrow="LOCAL STRUCTURE ANALYSIS"
        title="Review field classifications"
        detail="Suggestions are inferred. User descriptions are USER PROVIDED, never vendor verified."
      />
      <div className="studio-contract-grid">
        <ContractCard title="Native Contract" status="SAMPLE STRUCTURE">
          {analysis?.format} · {analysis?.record_boundary}
        </ContractCard>
        <ContractCard title="Splunk Contract" status={customSourcetype ? 'NETSPOUT-DEFINED' : 'RESEARCH REQUIRED'}>
          No TA or CIM relationship is inferred.
        </ContractCard>
        <ContractCard title="NetSpout Contract" status="DRAFT">
          Only MODELED fields may be changed by scenario state.
        </ContractCard>
      </div>
      <div className="studio-field-table">
        <div className="studio-field-row studio-field-row--header">
          <span>Field</span><span>Type</span><span>Classification</span><span>Authority</span>
        </div>
        {analysis?.fields.map((field, index) => (
          <div className="studio-field-row" key={field.name}>
            <code>{field.name}</code>
            <span>{field.data_type}</span>
            <select
              value={field.classification}
              onChange={(event) =>
                setAnalysis((current) => current && ({
                  ...current,
                  fields: current.fields.map((item, itemIndex) =>
                    itemIndex === index
                      ? { ...item, classification: event.target.value as FieldClassification }
                      : item,
                  ),
                }))
              }
            >
              {classifications.map((item) => <option key={item}>{item}</option>)}
            </select>
            <span>USER REVIEW</span>
          </div>
        ))}
      </div>
      <div className="studio-form-grid">
        <label>Source ID<input value={customSourceId} onChange={(event) => setCustomSourceId(event.target.value)} /></label>
        <label>
          Provenance
          <select value={provenance} onChange={(event) => setProvenance(event.target.value as SampleProvenance)}>
            <option>LAB SAMPLE — SANITIZED</option>
            <option>CUSTOMER SAMPLE — SANITIZED</option>
            <option>PUBLIC SAMPLE</option>
            <option>UNKNOWN ORIGIN</option>
          </select>
        </label>
        <label>
          Custom sourcetype
          <input value={customSourcetype} onChange={(event) => setCustomSourcetype(event.target.value)} />
          <small>Explicitly NETSPOUT-DEFINED; never an official Splunk claim.</small>
        </label>
      </div>
      <button type="button" className="button-primary" onClick={createCustomDraft} disabled={busy}>
        Approve Sanitized Contract <ShieldCheck />
      </button>
    </div>
  );

  const renderEditor = () => {
    if (!draft || !scenario) return null;
    if (screen === 'ENVIRONMENT') {
      return (
        <StudioEditorShell screen={screen} onStep={setScreen}>
          <div data-testid="studio-environment-builder">
            <StudioHeading eyebrow="ENVIRONMENT" title="Define modeled entities" detail="Addresses and labels are modeled values; contracts remain immutable." />
            <div className="studio-entity-grid">
              {draft.entities.map((entity, index) => (
                <article className="studio-entity-card" key={entity.entity_id}>
                  <Boxes />
                  <label>Label<input value={entity.label} onChange={(event) => setDraft({
                    ...draft,
                    entities: draft.entities.map((item, itemIndex) => itemIndex === index ? { ...item, label: event.target.value } : item),
                  })} /></label>
                  <label>Entity identity<input value={entity.entity_id} readOnly /></label>
                  <label>Type<input value={entity.entity_type} readOnly /></label>
                </article>
              ))}
              <button type="button" className="studio-add-card" onClick={() => {
                const id = `endpoint-${draft.entities.length + 1}.example`;
                setDraft({
                  ...draft,
                  entities: [...draft.entities, {
                    entity_id: id,
                    label: `Endpoint ${draft.entities.length + 1}`,
                    entity_type: 'endpoint',
                    zone_id: draft.zones[0].zone_id,
                    attributes: { address: '198.51.100.20' },
                    x: null,
                    y: null,
                  }],
                });
              }}><Plus /> Add Entity</button>
            </div>
          </div>
        </StudioEditorShell>
      );
    }
    if (screen === 'TOPOLOGY') {
      return (
        <StudioEditorShell screen={screen} onStep={setScreen}>
          <div data-testid="studio-topology-builder">
            <StudioHeading eyebrow="TOPOLOGY" title="Automatic semantic layout" detail="Relationships are saved declaratively; layout hints are optional." />
            <TopologyPreview scenario={scenario} sources={home?.sources ?? []} />
            <button type="button" className="button-secondary" onClick={() => {
              if (draft.entities.length < 2) return;
              setDraft({
                ...draft,
                relationships: [{
                  relationship_id: 'studio-link-1',
                  source_entity_id: draft.entities[0].entity_id,
                  target_entity_id: draft.entities[1].entity_id,
                  relationship_type: 'CONNECTED_TO',
                  protocol: null,
                }],
              });
            }}>Connect first two entities</button>
          </div>
        </StudioEditorShell>
      );
    }
    if (screen === 'STATE') {
      return (
        <StudioEditorShell screen={screen} onStep={setScreen}>
          <div data-testid="studio-state-builder">
            <StudioHeading eyebrow="ENTERPRISE STATE" title="Set baseline modeled state" detail="State keys must be supported by every selected generator that consumes them." />
            <div className="studio-state-list">
              {draft.baseline.map((state, index) => (
                <div className="studio-state-row" key={`${state.entity_id}-${state.state_key}`}>
                  <code>{state.state_key}</code><span>{state.entity_id}</span>
                  <input value={String(state.value)} onChange={(event) => setDraft({
                    ...draft,
                    baseline: draft.baseline.map((item, itemIndex) => itemIndex === index ? { ...item, value: event.target.value } : item),
                  })} />
                  <span>{state.unit ?? 'state'}</span>
                </div>
              ))}
            </div>
            <div className="studio-callout">Baseline values are MODELED, not vendor-documented constants.</div>
          </div>
        </StudioEditorShell>
      );
    }
    if (screen === 'TIMELINE') {
      return (
        <StudioEditorShell screen={screen} onStep={setScreen}>
          <div data-testid="studio-timeline-builder">
            <StudioHeading eyebrow="TIMELINE" title="Drive telemetry with transitions" detail="Authors change state; verified generators derive protocol-correct telemetry." />
            <div className="studio-timeline">
              {draft.timeline.map((transition) => (
                <article key={transition.transition_id}>
                  <div className="studio-timeline__time">{String(Math.floor(transition.offset_seconds / 60)).padStart(2, '0')}:00</div>
                  <div>
                    <StatusBadge status={transition.stage} />
                    <strong>{transition.title}</strong>
                    {transition.state_changes.map((change) => (
                      <span key={change.state_key}>{change.state_key} → {String(change.value)} {change.unit}</span>
                    ))}
                  </div>
                </article>
              ))}
            </div>
          </div>
        </StudioEditorShell>
      );
    }
    if (screen === 'TELEMETRY') {
      return (
        <StudioEditorShell screen={screen} onStep={setScreen}>
          <div data-testid="studio-telemetry-configuration">
            <StudioHeading eyebrow="TELEMETRY" title="Review source contracts and paths" detail="Native transport and destination delivery remain separate." />
            <div className="studio-source-grid">
              {draft.source_ids.map((sourceId) => {
                const source = sourceById.get(sourceId);
                const custom = draft.custom_sources.find((item) => item.source_id === sourceId);
                return (
                  <article className="studio-source-card" key={sourceId}>
                    <FlaskConical />
                    <div>
                      <strong>{source?.product ?? custom?.display_name ?? sourceId}</strong>
                      <span>{source?.native_contract.format ?? custom?.format ?? 'Declared contract'}</span>
                      <small>{custom ? 'PRIVATE · NETSPOUT-DEFINED HEC PATH' : 'PHASE 5 NATIVE PATH → HEC → SPLUNK'}</small>
                    </div>
                    <StatusBadge status={custom ? 'DRAFT' : source?.generation.state ?? 'UNKNOWN'} />
                  </article>
                );
              })}
            </div>
            <button type="button" className="button-secondary" onClick={() => setDraft({
              ...draft,
              correlation_mappings: draft.source_ids.map((sourceId) => ({
                source_id: sourceId,
                source_field: sourceId.includes('snmp') ? 'ifIndex' : sourceId.includes('gnmi') ? 'interface[name]' : 'device',
                entity_id: draft.entities[0].entity_id,
                identity_type: 'interface',
              })),
            })}>Map all sources to {draft.entities[0].entity_id}</button>
            <div className="studio-correlation-map">
              {draft.correlation_mappings.map((item) => (
                <div key={item.source_id}><code>{item.source_id}</code><span>{item.source_field}</span><b>→</b><strong>{item.entity_id}</strong></div>
              ))}
            </div>
          </div>
        </StudioEditorShell>
      );
    }
    if (screen === 'PARAMETERS') {
      return (
        <StudioEditorShell screen={screen} onStep={setScreen}>
          <div data-testid="studio-parameters">
            <StudioHeading eyebrow="RUNTIME CONTROLS" title="Expose constrained modeled values" detail="Parameters cannot alter structural telemetry fields." />
            {draft.parameters.map((parameter) => (
              <div className="studio-state-row" key={parameter.parameter_id}>
                <code>{parameter.parameter_id}</code><span>{parameter.state_key}</span><b>{String(parameter.default)} {parameter.unit}</b>
              </div>
            ))}
            <button type="button" className="button-secondary" onClick={() => {
              const stateKey = draft.timeline.flatMap((item) => item.state_changes)[0]?.state_key ?? 'interface.loss';
              setDraft({
                ...draft,
                parameters: [{
                  parameter_id: 'incident-intensity',
                  state_key: stateKey,
                  value_type: 'number',
                  default: 8,
                  minimum: 0,
                  maximum: 100,
                  enum_values: [],
                  unit: 'percent',
                  description: 'Modeled incident intensity.',
                }],
              });
            }}><Plus /> Add constrained parameter</button>
          </div>
        </StudioEditorShell>
      );
    }
    if (screen === 'INVESTIGATION') {
      return (
        <StudioEditorShell screen={screen} onStep={setScreen}>
          <div data-testid="studio-investigation-builder">
            <StudioHeading eyebrow="INVESTIGATION PACK" title="Author evidence-backed SPL steps" detail="Syntax alone does not validate a search; runtime results must match the expected finding." />
            {draft.investigations.map((item) => (
              <article className="studio-investigation" key={item.investigation_id}>
                <StatusBadge status={item.portability} />
                <strong>{item.title}</strong>
                <code>{item.spl}</code>
                <span>Expected: {item.expected_finding}</span>
              </article>
            ))}
            <button type="button" className="button-secondary" onClick={() => setDraft({
              ...draft,
              investigations: [{
                investigation_id: 'studio-check-observation',
                title: 'Confirm selected sources',
                objective: 'Verify indexed evidence for this private run.',
                question: 'Did Splunk observe every selected source?',
                spl: 'index=idx_network_ops netspout_run_id="$run_id$" | stats count by sourcetype',
                expected_finding: 'At least one indexed event for every selected source.',
                explanation: 'The query is NetSpout-specific because it uses run correlation metadata.',
                portability: 'NETSPOUT_SPECIFIC',
                evidence_source_ids: draft.source_ids,
                netspout_only_fields: ['netspout_run_id'],
              }],
            })}><Plus /> Add investigation step</button>
          </div>
        </StudioEditorShell>
      );
    }
    if (screen === 'PREVIEW') {
      return (
        <StudioEditorShell screen={screen} onStep={setScreen}>
          <div data-testid="studio-preview">
            <StudioHeading eyebrow="PREVIEW" title={draft.title} detail={draft.story} />
            <div className="studio-preview-grid">
              <section><h3>Story Preview</h3><p>{draft.description}</p></section>
              <section><h3>Provenance Preview</h3><p>{draft.provenance}</p><StatusBadge status={draft.redistribution} /></section>
              <section><h3>Timeline Preview</h3><p>{draft.timeline.length} ordered transitions</p></section>
              <section><h3>Splunk Preview</h3><p>{draft.custom_sources.length ? 'NETSPOUT-DEFINED custom sourcetype' : 'Catalog relationship preserved'}</p></section>
            </div>
            <TopologyPreview scenario={scenario} sources={home?.sources ?? []} />
            <section className="studio-raw-preview">
              <h3>Raw Event Preview</h3>
              <pre>{draft.custom_sources[0]?.sanitized_sample ?? 'Generated at run time from the selected verified native contracts.'}</pre>
              <span>Structural fields are protected. Highlighting does not mutate raw telemetry.</span>
            </section>
            <section className="studio-guided-preview" data-testid="studio-guided-preview">
              <h3>Guided Lab Preview</h3>
              <div>{['Understand', 'Prepare', 'Run', 'Observe', 'Investigate', 'Validate'].map((item, index) => <span key={item}>{index + 1}. {item}</span>)}</div>
            </section>
            <button type="button" className="button-primary" onClick={validate}>Validate Draft <BadgeCheck /></button>
          </div>
        </StudioEditorShell>
      );
    }
    if (screen === 'VALIDATE') {
      return (
        <StudioEditorShell screen={screen} onStep={setScreen}>
          <div data-testid="studio-validation">
            <StudioHeading eyebrow="FAIL-CLOSED VALIDATION" title={validation.valid ? 'Structure validated' : 'Draft blocked'} detail={`Maturity ceiling: ${validation.maturity_ceiling}`} />
            <div className="studio-validation-list">
              {validation.checks.map((check) => (
                <div key={check.check_id} className={check.state === 'PASS' ? 'is-pass' : 'is-fail'}>
                  <StatusBadge status={check.state} /><strong>{check.check_id}</strong><span>{check.detail}</span>
                </div>
              ))}
            </div>
            {validation.warnings.map((item) => <div className="studio-callout" key={item}>{item}</div>)}
            <button type="button" className="button-primary" disabled={!validation.valid || busy} onClick={save}>
              Save as Private Pack <Save />
            </button>
          </div>
        </StudioEditorShell>
      );
    }
    return (
      <StudioEditorShell screen={screen as EditorStep} onStep={setScreen}>
        <div data-testid="studio-save-private-pack">
          <StudioHeading eyebrow="PRIVATE PACK" title={saved ? 'Saved locally' : 'Ready to save'} detail="The pack is outside Git and defaults to PRIVATE / LOCAL ONLY." />
          {saved && (
            <div className="studio-save-card">
              <LockKeyhole />
              <div><strong>{saved.title}</strong><span>{saved.pack_id}</span></div>
              <StatusBadge status={saved.maturity} />
              <StatusBadge status={saved.redistribution} />
            </div>
          )}
          <button type="button" className="button-primary" disabled={!saved || busy} onClick={runSaved}>
            Run Draft Scenario <Play />
          </button>
          {run && (
            <section className="studio-live-result" data-testid="studio-live-run">
              <div className="studio-section-title"><Sparkles /><div><strong>Live Run</strong><span>{run.run_id}</span></div></div>
              <StatusBadge status={run.status} />
              <div className="studio-evidence-grid">
                {run.evidence.map((item) => (
                  <div key={item.stage}><strong>{item.stage}</strong><b>{item.count}</b><StatusBadge status={item.state} /></div>
                ))}
              </div>
              <h3>Splunk validation</h3>
              <p>Run observation remains distinct from HEC acceptance. Use Observe after indexing to promote evidence.</p>
            </section>
          )}
        </div>
      </StudioEditorShell>
    );
  };

  return (
    <div className={`scenario-studio scenario-studio--${experienceMode}`}>
      <div className="studio-toolbar">
        <button type="button" onClick={() => setScreen('HOME')}><ChevronLeft /> Studio Home</button>
        <span>Scenario Studio</span>
        <StatusBadge status={draft?.maturity ?? 'DRAFT'} />
      </div>
      {error && <div className="generation-error">{error}</div>}
      {screen === 'HOME' && renderHome()}
      {screen === 'SOURCES' && renderSourceSelection()}
      {screen === 'CLONE' && renderClone()}
      {screen === 'IMPORT' && renderImport()}
      {screen === 'FIELDS' && renderFields()}
      {EDITOR_STEPS.includes(screen as EditorStep) && renderEditor()}
      {EDITOR_STEPS.includes(screen as EditorStep) && (
        <div className="studio-step-actions">
          <button type="button" className="button-secondary" onClick={() => changeStep(-1)} disabled={EDITOR_STEPS.indexOf(screen as EditorStep) === 0}><ChevronLeft /> Previous</button>
          <button type="button" className="button-secondary" onClick={() => changeStep(1)} disabled={EDITOR_STEPS.indexOf(screen as EditorStep) === EDITOR_STEPS.length - 1}>Next <ChevronRight /></button>
        </div>
      )}
    </div>
  );
}

function StudioEditorShell({
  screen,
  onStep,
  children,
}: {
  screen: EditorStep;
  onStep: (step: StudioScreen) => void;
  children: ReactNode;
}) {
  return (
    <div className="studio-editor">
      <aside className="studio-steps" aria-label="Scenario Studio steps">
        {EDITOR_STEPS.map((item, index) => (
          <button
            type="button"
            key={item}
            className={item === screen ? 'is-active' : ''}
            onClick={() => onStep(item)}
          >
            <span>{String(index + 1).padStart(2, '0')}</span>{item}
          </button>
        ))}
      </aside>
      <section className="studio-editor__content">{children}</section>
    </div>
  );
}

function StudioHeading({ eyebrow, title, detail }: { eyebrow: string; title: string; detail: string }) {
  return (
    <header className="studio-heading">
      <div className="generation-eyebrow">{eyebrow}</div>
      <h2>{title}</h2>
      <p>{detail}</p>
    </header>
  );
}

function ContractCard({ title, status, children }: { title: string; status: string; children: ReactNode }) {
  return (
    <article className="studio-contract-card">
      <span>{title}</span>
      <StatusBadge status={status} />
      <p>{children}</p>
    </article>
  );
}
