import { useEffect, useState } from 'react';
import { apiUrl } from './api';

export interface EngineStatus { configured: boolean; connected: boolean; url: string; message: string; version?: string | null; managed?: boolean; state?: string; restarts?: number; last_error?: string | null }

// The engine setting exists only where the app runs inside Splunk (the gateway owns it); in a plain browser the page talks to the engine directly.
export const insideSplunk = () => typeof window !== 'undefined' && /^\/[a-zA-Z]{2}-[a-zA-Z]{2}\/static\/app\/netspout\//.test(window.location.pathname);

async function call(method: 'GET' | 'POST', body?: unknown): Promise<EngineStatus> {
  const r = await fetch(apiUrl('/engine'), { method, headers: { Accept: 'application/json', ...(body ? { 'Content-Type': 'application/json' } : {}) }, body: body ? JSON.stringify(body) : undefined });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof j?.detail === 'string' ? j.detail : `HTTP ${r.status}`);
  return j as EngineStatus;
}
export const engineStatus = () => call('GET');
export const saveEngine = (url: string) => call('POST', { url });

/** null outside Splunk or while unknown; otherwise what the gateway says about the configured engine. */
export function useEngineStatus(): EngineStatus | null {
  const [s, setS] = useState<EngineStatus | null>(null);
  useEffect(() => {
    if (!insideSplunk()) return undefined;
    let alive = true;
    const tick = () => engineStatus().then((v) => alive && setS(v), () => undefined);
    tick();
    const t = window.setInterval(tick, 10_000);
    return () => { alive = false; window.clearInterval(t); };
  }, []);
  return s;
}

/** Managed install only: ask Splunk to stop and start the engine input again (admin). */
export async function restartEngine(): Promise<string> {
  const r = await fetch(apiUrl('/engine/restart'), { method: 'POST', headers: { Accept: 'application/json' } });
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(typeof j?.detail === 'string' ? j.detail : `HTTP ${r.status}`);
  return String(j.detail ?? 'Restart requested');
}
