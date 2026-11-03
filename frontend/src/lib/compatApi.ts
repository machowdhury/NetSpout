import { apiUrl } from './api';

export type CapabilityStatus = 'VERIFIED' | 'FORMAT_CHECKED' | 'GENERATOR_UNVERIFIED' | 'UNSUPPORTED';

export interface SourcetypeEntry {
  sourcetype: string;
  kind: 'event' | 'metric';
  status: CapabilityStatus;
  status_label: string;
  notes: string[];
  block: { code: string; message: string } | null;
  ta: { app: string; version: string; canonical_sourcetype: string | null; match: string } | null;
  generator: string | null;
  evidence?: { add_on: string; live_checks: Record<string, number>; file: string };
}
export interface ProductNode { name: string; best: number; sourcetypes: SourcetypeEntry[] }
export interface VendorNode { id: string; name: string; best: number; products: ProductNode[] }
export interface CompatCatalog { labels: Record<CapabilityStatus, string>; vendors: VendorNode[] }

export interface PreviewEvent { raw: string | null; sourcetype: string; index: string; host: string; source: string; kind: 'event' | 'metric'; metrics: Record<string, number> | null }
export interface Preview { sourcetype: string; vendor_id: string; generator_mode: string | null; provenance: string | null; status: CapabilityStatus | null; status_label: string | null; notes: string[]; events: PreviewEvent[]; disclaimer: string }

export interface ScenarioRequirement { sourcetype: string; status: CapabilityStatus; status_label: string; note?: string; block?: { code: string; message: string } | null }
export interface ScenarioCompat {
  id: string; title: string; category: string | null; summary: string | null; engine: string | null; dashboard: string | null; required: ScenarioRequirement[];
  runnable: boolean; verified: boolean; run_state: 'VERIFIED_IN_SPLUNK' | 'RUNNABLE_UNVERIFIED' | 'NOT_RUNNABLE'; reasons: string[]; warnings: string[];
}

// Unlike fetchJson, the server's own explanation (for example why a selection cannot run) is kept: it is shown to the user verbatim.
async function call<T>(method: 'GET' | 'POST', path: string, body?: unknown, timeoutMs = 20_000): Promise<T> {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(apiUrl(path), { method, signal: controller.signal, headers: { Accept: 'application/json', ...(body === undefined ? {} : { 'Content-Type': 'application/json' }) }, body: body === undefined ? undefined : JSON.stringify(body) });
    if (!response.ok) {
      const detail = await response.json().then((j) => (typeof j?.detail === 'string' ? j.detail : null), () => null);
      throw new Error(detail ?? `HTTP ${response.status}`);
    }
    return (await response.json()) as T;
  } catch (e) {
    if (e instanceof DOMException && e.name === 'AbortError') throw new Error(`No answer from the engine within ${timeoutMs / 1000}s`);
    throw e;
  } finally {
    window.clearTimeout(timer);
  }
}

export const compatApi = {
  catalog: () => call<CompatCatalog>('GET', '/api/compat/catalog'),
  scenarios: () => call<{ labels: Record<string, string>; scenarios: ScenarioCompat[] }>('GET', '/api/compat/scenarios'),
  preview: (vendor_id: string, sourcetype: string, count = 3, index?: string) => call<Preview>('POST', '/api/generate/preview', { vendor_id, sourcetype, count, index }),
  dashboards: () => call<{ recipes: Array<{ dashboard_id: string; scenario_id: string }> }>('GET', '/api/dashboards'),
};
