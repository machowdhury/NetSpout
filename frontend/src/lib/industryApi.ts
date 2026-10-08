import { fetchJson } from './api';
import type {
  IndustryCatalog,
  IndustryComposition,
  IndustryStudioDraft,
} from '../types/industry';

const post = (body: unknown): RequestInit => ({
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
});

const selection = (
  industryId: string,
  environmentId: string,
  scenarioId?: string,
  seed = 1010,
) => ({
  industry_id: industryId,
  environment_id: environmentId,
  scenario_id: scenarioId,
  seed,
  modeled_parameters: {},
});

export const industryApi = {
  catalog: () => fetchJson<IndustryCatalog>('/api/industries'),
  compose: (
    industryId: string,
    environmentId: string,
    scenarioId?: string,
    seed = 1010,
  ) =>
    fetchJson<IndustryComposition>(
      '/api/industries/compose',
      post(selection(industryId, environmentId, scenarioId, seed)),
    ),
  cloneToStudio: (
    industryId: string,
    environmentId: string,
    scenarioId?: string,
  ) =>
    fetchJson<IndustryStudioDraft>(
      `/api/industries/${encodeURIComponent(industryId)}/studio-draft`,
      post(selection(industryId, environmentId, scenarioId)),
    ),
};
