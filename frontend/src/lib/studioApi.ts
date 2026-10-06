import { fetchJson } from './api';
import type {
  CreationPath,
  CustomSourceDraft,
  SampleAnalysis,
  StudioHome,
  StudioRun,
  StudioScenarioPack,
  StudioValidation,
} from '../types/studio';

const request = (method: 'POST' | 'DELETE', body?: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const studioApi = {
  home: () => fetchJson<StudioHome>('/api/studio'),
  analyze: (sample: string, authorizationAcknowledged: boolean) =>
    fetchJson<SampleAnalysis>(
      '/api/studio/samples/analyze',
      request('POST', {
        sample,
        authorization_acknowledged: authorizationAcknowledged,
      }),
    ),
  validateCustomSource: (source: CustomSourceDraft) =>
    fetchJson<{
      valid: boolean;
      errors: string[];
      privacy_status: string;
      native_contract: Record<string, unknown>;
      splunk_contract: Record<string, unknown>;
      netspout_contract: Record<string, unknown>;
    }>('/api/studio/custom-sources/validate', request('POST', source)),
  createDraft: (
    creationPath: CreationPath,
    sourceIds: string[],
    title: string,
    cloneScenarioId?: string,
  ) =>
    fetchJson<StudioScenarioPack>(
      '/api/studio/drafts',
      request('POST', {
        creation_path: creationPath,
        source_ids: sourceIds,
        clone_scenario_id: cloneScenarioId,
        title,
      }),
    ),
  validate: (pack: StudioScenarioPack) =>
    fetchJson<StudioValidation>(
      '/api/studio/packs/validate',
      request('POST', pack),
    ),
  save: (pack: StudioScenarioPack) =>
    fetchJson<StudioScenarioPack>('/api/studio/packs', request('POST', pack)),
  load: (packId: string) =>
    fetchJson<StudioScenarioPack>(
      `/api/studio/packs/${encodeURIComponent(packId)}`,
    ),
  remove: (packId: string) =>
    fetchJson<{ deleted: boolean; pack_id: string }>(
      `/api/studio/packs/${encodeURIComponent(packId)}`,
      request('DELETE'),
    ),
  run: (packId: string, parameters: Record<string, unknown> = {}) =>
    fetchJson<StudioRun>(
      `/api/studio/packs/${encodeURIComponent(packId)}/run`,
      request('POST', { parameters, seed: 606 }),
      180_000,
    ),
  exportGate: (packId: string, publicExport = false) =>
    fetchJson<{ allowed: boolean; scope: string; blockers: string[] }>(
      `/api/studio/packs/${encodeURIComponent(packId)}/export-gate?public=${String(publicExport)}`,
    ),
};
