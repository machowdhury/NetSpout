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

async function call<T>(method: 'GET' | 'POST', path: string, body?: unknown, timeoutMs = 25_000): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);   // a hung gateway call must not leave the monitor controls disabled forever
  const response = await fetch(apiUrl(path), {
    method,
    signal: controller.signal,
    headers: { Accept: 'application/json', ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) },
    body: body === undefined ? undefined : JSON.stringify(body),
  }).catch((e: unknown) => {
    throw new Error(e instanceof DOMException && e.name === 'AbortError' ? `No answer from the engine within ${timeoutMs / 1000}s` : String(e));
  }).finally(() => window.clearTimeout(timer));
  if (!response.ok) {
    const detail = await response.json().then((j) => (typeof j?.detail === 'string' ? j.detail : null), () => null);
    throw new Error(detail ? `${detail} (HTTP ${response.status})` : `HTTP ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export const startRun = (body: Record<string, unknown>) => call<RunSnapshot>('POST', '/api/runs', body);
// Status polls answer in milliseconds (measured p50 4 ms, max 28 ms). A poll lost at the gateway connection never answers, so it is abandoned after 5 s and the next one goes out instead of the monitor waiting out the 25 s default.
export const getRun = (id: string) => call<RunSnapshot>('GET', `/api/runs/${encodeURIComponent(id)}`, undefined, 5_000);
const WANT: Record<'pause' | 'resume' | 'stop', string[]> = { pause: ['PAUSED'], resume: ['RUNNING'], stop: ['STOPPING', 'STOPPED', 'COMPLETED'] };
// The Splunk gateway sometimes drops a POST at the connection level. The control is retried once, and a failed or rejected retry still counts as done when the engine already reports the wanted state.
export async function controlRun(id: string, action: 'pause' | 'resume' | 'stop'): Promise<RunSnapshot> {
  const path = `/api/runs/${encodeURIComponent(id)}/${action}`;
  try { return await call<RunSnapshot>('POST', path); } catch (first) {
    await new Promise((r) => window.setTimeout(r, 500));
    const now = await getRun(id).catch(() => null);
    if (now && WANT[action].includes(now.state)) return now;
    try { return await call<RunSnapshot>('POST', path); } catch (second) {
      const after = await getRun(id).catch(() => null);
      if (after && WANT[action].includes(after.state)) return after;
      throw second instanceof Error ? second : first;
    }
  }
}
export const verifyRun = (id: string) => call<NonNullable<RunSnapshot['verification']>>('POST', `/api/runs/${encodeURIComponent(id)}/verify`);
export const testConnection = (body: Record<string, unknown>) => call<Record<string, unknown>>('POST', '/api/setup/test-connection', body);

export interface Readiness {
  state: 'NOT_STARTED' | 'GENERATING' | 'DELIVERING' | 'INDEXING' | 'PARTIALLY_READY' | 'READY' | 'DEGRADED' | 'FAILED' | 'UNKNOWN';
  run_id: string; title?: string; scenario?: string; notes: string[]; missing: string[]; elapsed_s?: number; elapsed_to_ready_s?: number | null;
  required?: { sourcetypes?: Record<string, number>; phases?: string[] }; present?: { sourcetypes?: Record<string, number>; phases?: Record<string, number>; events_indexed?: number };
  counters?: RunSnapshot['counters'];
  verification?: { status: string; indexed?: number; accepted?: number; metric_datapoints_indexed?: number; query?: string } | null;
  dashboard?: { view: string; tokens: Record<string, string | number>; openable: boolean; note: string } | null;
}
export const checkReadiness = (id: string) => call<Readiness>('POST', `/api/runs/${encodeURIComponent(id)}/readiness`, undefined, 60_000);
