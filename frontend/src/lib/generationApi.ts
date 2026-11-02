import { fetchJson } from './api';
import type {
  GenerationCapabilities,
  GenerationPreflight,
  GenerationPreview,
  GenerationRequest,
  GenerationRun,
  InvestigationResult,
} from '../types/generation';

const jsonRequest = (method: 'POST', body?: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: body === undefined ? undefined : JSON.stringify(body),
});

export const generationApi = {
  capabilities: () => fetchJson<GenerationCapabilities>('/api/generation/capabilities'),
  preview: (request: GenerationRequest) =>
    fetchJson<GenerationPreview>('/api/generation/preview', jsonRequest('POST', request)),
  preflight: (request: GenerationRequest) =>
    fetchJson<GenerationPreflight>('/api/generation/preflight', jsonRequest('POST', request)),
  run: (request: GenerationRequest) =>
    fetchJson<GenerationRun>('/api/generation/runs', jsonRequest('POST', request), 30_000),
  observe: (runId: string) =>
    fetchJson<GenerationRun>(`/api/generation/runs/${encodeURIComponent(runId)}/observe`, jsonRequest('POST'), 15_000),
  investigate: (runId: string, recipeId: string) =>
    fetchJson<InvestigationResult>(
      `/api/generation/runs/${encodeURIComponent(runId)}/investigate/${encodeURIComponent(recipeId)}`,
      jsonRequest('POST'),
      15_000,
    ),
};
