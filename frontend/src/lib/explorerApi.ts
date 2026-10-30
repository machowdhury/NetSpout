import { apiUrl } from './api';

export type StepName =
  | 'SELECT' | 'CONFIGURE' | 'GENERATE' | 'INGEST' | 'VERIFY' | 'DASHBOARD'
  | 'PREREQUISITES' | 'ENABLE_DETECTION';

export interface WorkflowStep {
  step: StepName;
  endpoint: { method: string; path: string; body?: unknown } | null;
  available: boolean;
  blocked_reason: string | null;
  success_criterion: string;
}

export interface IndustryTag { id: string; basis: string; subdomain?: string; source_subindustry?: string }

export interface ReplayDataset { dataset_path: string; sourcetype: string | null }

export interface DetectionRow {
  content_id: string;
  name: string;
  detection_type: string | null;
  mitre_attack_ids: string[];
  has_attack_data: boolean;
  compatibility: string;
  runtime_approved: boolean;
  verified: boolean;
  replay_datasets: ReplayDataset[];
}

export interface ExplorerEntry {
  entry_id: string;
  kind: 'operational' | 'security';
  title: string;
  summary: string;
  industries: IndustryTag[];
  vendors: string[];
  demo_ready: boolean;
  workflow: WorkflowStep[];
  // operational
  engine?: 'unified_generation' | 'scenario_runner' | 'scenario_pack' | 'incident_pack';
  scenario_id?: string;
  domain?: string;
  runnable?: boolean;
  blocked_reason?: string | null;
  maturity?: { tier: string; raw: string; basis: string };
  provenance?: { source_id: string; source_ref?: string | null; url?: string | null; upstream_industry?: string | null; criticality?: string | null };
  live_verified?: boolean;
  dashboard_verified?: boolean;
  dashboard?: { dashboard_id: string; eligibility: string; dashboard_maturity: string; reasons: string[]; splunk_view?: string | null } | null;
  // security
  story_id?: string;
  narrative?: string;
  mitre_attack_ids?: string[];
  data_sources?: string[];
  detections?: DetectionRow[];
  readiness?: {
    level: string;
    label: string;
    detections_total: number;
    detections_with_replay_data: number;
    detections_runtime_approved: number;
    detections_verified: number;
    production_detection_efficacy: string;
  };
}

export interface IndustrySummary {
  id: string; name: string; subdomains?: Array<{ id: string; name: string }>; scenarios_total: number; scenarios_demo_ready: number; bases: string[];
  scenarios_runnable?: number; scenarios_cataloged_only?: number; scenarios_live_verified?: number; scenarios_dashboard_verified?: number; subdomains_with_scenarios?: string[];
}

export interface ExplorerSummary {
  operational: { total: number; demo_ready: number; by_tier: Record<string, number>; vendors: string[] };
  security: { total: number; demo_ready: number; by_readiness: Record<string, number> };
  taxonomy: { status: string; version: string; note: string };
  industries: IndustrySummary[];
}

export interface SearchResult { total: number; offset: number; limit: number; items: ExplorerEntry[] }

export interface SearchParams {
  q?: string; kind?: string; industry?: string; tier?: string; readiness?: string; demoReady?: boolean; limit?: number;
}

export interface PrereqCheck { check_id: string; label: string; state: 'PASS' | 'FAIL'; detail: string }
export interface Prerequisites { checks: PrereqCheck[]; ready: boolean; live_reachability: string }

export class ApiError extends Error {}

async function call<T>(method: 'GET' | 'POST', path: string, body?: unknown, timeoutMs = 20_000): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(apiUrl(path), {
      method,
      signal: controller.signal,
      headers: { Accept: 'application/json', ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (!response.ok) {
      // Surface the server's reason (e.g. "Complete Connection Center setup first") instead of a bare status.
      const detail = await response.json().then((j) => (typeof j?.detail === 'string' ? j.detail : null), () => null);
      throw new ApiError(detail ? `${detail} (HTTP ${response.status})` : `HTTP ${response.status}`);
    }
    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError(error instanceof DOMException && error.name === 'AbortError' ? 'Request timed out' : 'Backend unreachable');
  } finally {
    window.clearTimeout(timer);
  }
}

const e = encodeURIComponent;

export const explorerApi = {
  summary: () => call<ExplorerSummary>('GET', '/api/explorer/summary'),
  search: (p: SearchParams) => {
    const qs = new URLSearchParams();
    if (p.q) qs.set('q', p.q);
    if (p.kind) qs.set('kind', p.kind);
    if (p.industry) qs.set('industry', p.industry);
    if (p.tier) qs.set('tier', p.tier);
    if (p.readiness) qs.set('readiness', p.readiness);
    if (p.demoReady !== undefined) qs.set('demo_ready', String(p.demoReady));
    qs.set('limit', String(p.limit ?? 60));
    return call<SearchResult>('GET', `/api/explorer/entries?${qs}`);
  },
  entry: (id: string) => call<ExplorerEntry>('GET', `/api/explorer/entries/${e(id)}`),
  prerequisites: (id: string, index?: string) =>
    call<Prerequisites>('GET', `/api/explorer/entries/${e(id)}/prerequisites${index ? `?index=${e(index)}` : ''}`),
  setup: () => call<{ configured: boolean; indexes?: string[] }>('GET', '/api/setup'),
  // operational, unified generation
  preflight: (selectionId: string, count: number) =>
    call<{ state: string; checks: Array<{ check_id: string; label: string; state: string; detail: string }> }>(
      'POST', '/api/generation/preflight', { mode: 'SCENARIO', selection_id: selectionId, count }),
  generate: (selectionId: string, count: number) =>
    call<{ run_id: string; status: string; evidence: Array<{ stage: string; state: string; detail?: string }>; limitations: string[] }>(
      'POST', '/api/generation/runs', { mode: 'SCENARIO', selection_id: selectionId, count }, 60_000),
  observe: (runId: string) =>
    call<{
      run_id: string; status: string; evidence: Array<{ stage: string; state: string; detail?: string }>;
      channel_results: Array<{ source_id: string; required: boolean; evidence: Array<{ stage: string; state: string; count?: number }> }>;
    }>(
      'POST', `/api/generation/runs/${e(runId)}/observe`, undefined, 30_000),
  // operational, authentic observation packs
  generatePack: (scenarioId: string, index: string) =>
    call<{ run_id: string; count_generated: number; event_count?: number; metric_datapoints_expected?: number; indexes?: { events?: string; metrics?: string };
           dispatch_results: Array<{ hec?: { success?: boolean } }> }>(
      'POST', '/api/generate/scenario-pack', { scenario_id: scenarioId, dispatch: true, index }, 120_000),
  // operational, ScenarioRunner
  runScenario: (scenarioId: string) =>
    call<{ run_id: string; dispatch_attempted: number; dispatch_succeeded: number; dispatch_failed: number; errors: string[] }>(
      'POST', `/api/scenarios/${e(scenarioId)}/run`, { dispatch_telemetry: true }, 90_000),
  runObservation: (runId: string) =>
    call<{ observation_status: string; required_evidence_satisfied: boolean; observation_completeness_pct: number;
           event_observed_count: number; metric_observed_count: number; destination_validation: string; schema_version: string | null }>(
      'GET', `/api/scenarios/runs/${e(runId)}/observation`, undefined, 60_000),
  dashboard: (dashboardId: string, runId: string, index: string) =>
    call<{ title: string; maturity: string; panels: unknown[] }>(
      'GET', `/api/dashboards/${e(dashboardId)}?run_id=${e(runId)}&index=${e(index)}`),
  validateDashboard: (dashboardId: string, runId: string, index: string) =>
    call<{ maturity: string; failures: string[]; data_validated: boolean }>(
      'POST', `/api/dashboards/${e(dashboardId)}/validate`, { run_id: runId, index }, 60_000),
  // security
  retrieveDataset: (datasetPath: string) =>
    call<{ local_id: string; size_bytes: number; sha256: string; repository_commit: string }>(
      'POST', '/api/security-content/datasets/retrieve', { dataset_path: datasetPath }, 60_000),
  replay: (localId: string, datasetPath: string, index: string) =>
    call<{ run_id: string; status: string; events_read: number; events_sent: number; errors: string[] }>(
      'POST', '/api/security-content/replays', { local_id: localId, dataset_path: datasetPath, index }, 120_000),
  observeReplay: (index: string, runId: string, metricIndex?: string) =>
    call<{ status: string; indexed_event_count: number | null; error: string | null; indexed_metric_datapoints?: number | null; metric_error?: string | null }>(
      'POST', '/api/explorer/security/observe', { index, run_id: runId, ...(metricIndex ? { metric_index: metricIndex } : {}) }, 30_000),
  enableDetection: (detectionId: string, index: string) =>
    call<{ status: string; enabled: boolean; saved_search?: string; error?: string; limitations: string[] }>(
      'POST', `/api/explorer/detections/${e(detectionId)}/enable`, { index }, 30_000),
  validateDetection: (p: { detection_id: string; run_id: string; index: string; dataset_or_scenario_id: string; indexed_event_count: number }) =>
    call<{ status: string; matched_event_count: number; error: string | null; limitations: string[] }>(
      'POST', '/api/security-content/validations', { ...p, expected_min_matches: 1, control: 'POSITIVE' }, 60_000),
};
