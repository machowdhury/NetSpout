import { apiUrl } from './api';

export interface RunSnapshot {
  run_id: string;
  kind: string;
  target?: string;
  title?: string;
  state: string;
  error?: string | null;
  destination?: { name?: string; index?: string; metric_index?: string | null };
  mode?: string;
  elapsed_s?: number;
  progress?: { total: number | null; done: number; pct: number | null };
  counters: { generated: number; attempts: number; accepted: number; rejected: number; unknown: number; pending: number; indexed: number | null };
  rate?: { current_eps: number; average_eps: number; limit_eps: number | null };
  eta_s?: number | null;
  by_sourcetype?: Record<string, Record<string, number>>;
  by_phase?: Array<Record<string, number | string>>;
  throughput?: Array<{ t: number; eps: number }>;
  recent_errors?: Array<{ at: string; sourcetype?: string; outcome?: string; message: string }>;
  controls: { pause: boolean; resume: boolean; stop: boolean };
  verification?: { status: string; indexed?: number | null; accepted?: number; error?: string | null; note?: string } | null;
  links?: Record<string, string>;
  interrupted_note?: string | null;
  accounting_note?: string;
}

async function call<T>(method: 'GET' | 'POST', path: string, body?: unknown): Promise<T> {
  const response = await fetch(apiUrl(path), {
    method,
    headers: { Accept: 'application/json', ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const detail = await response.json().then((j) => (typeof j?.detail === 'string' ? j.detail : null), () => null);
    throw new Error(detail ? `${detail} (HTTP ${response.status})` : `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const startRun = (body: Record<string, unknown>) => call<RunSnapshot>('POST', '/api/runs', body);
export const getRun = (id: string) => call<RunSnapshot>('GET', `/api/runs/${encodeURIComponent(id)}`);
export const controlRun = (id: string, action: 'pause' | 'resume' | 'stop') => call<RunSnapshot>('POST', `/api/runs/${encodeURIComponent(id)}/${action}`);
export const verifyRun = (id: string) => call<NonNullable<RunSnapshot['verification']>>('POST', `/api/runs/${encodeURIComponent(id)}/verify`);
export const testConnection = (body: Record<string, unknown>) => call<Record<string, unknown>>('POST', '/api/setup/test-connection', body);
