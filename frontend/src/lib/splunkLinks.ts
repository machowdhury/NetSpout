import type { RunSnapshot } from './runsApi';

// The app runs in an iframe on the Splunk origin, so Splunk Web pages are same-origin links that must open in the top window.
export function splunkLocale(): string | null {
  const m = typeof window === 'undefined' ? null : window.location.pathname.match(/^\/([a-zA-Z]{2}-[a-zA-Z]{2})\/static\/app\/netspout\//);
  return m ? m[1] : null;
}

const quote = (value: string) => `"${value.replace(/"/g, '')}"`;

/** Search that returns exactly the events of one run, in the index the run was delivered to. */
export function runSearchSpl(run: Pick<RunSnapshot, 'run_id' | 'destination' | 'key_field'> & { sourcetype?: string }, tail = ''): string {
  const index = run.destination?.index;
  const field = (run as { key_field?: string }).key_field || 'netspout_run_id';
  const parts = [index ? `index=${quote(index)}` : null, run.sourcetype ? `sourcetype=${quote(run.sourcetype)}` : null, `${field}=${quote(run.run_id)}`].filter(Boolean);
  return `search ${parts.join(' ')}${tail ? ` ${tail}` : ''}`;
}

/** Splunk Web link that opens the search with a time range that covers the run (five minutes before it started until now). */
export function splunkSearchHref(spl: string, startedAt?: string | null): string | null {
  const locale = splunkLocale();
  if (!locale) return null;
  const start = startedAt ? Date.parse(startedAt) : NaN;
  const earliest = Number.isFinite(start) ? String(Math.floor(start / 1000) - 300) : '-24h@h';
  return `/${locale}/app/search/search?q=${encodeURIComponent(spl)}&earliest=${earliest}&latest=now`;
}

export function dashboardHref(view: string, tokens: Record<string, string | number>): string | null {
  const locale = splunkLocale();
  if (!locale) return null;
  const qs = Object.entries(tokens).map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`).join('&');
  return `/${locale}/app/netspout/${view}?${qs}`;
}
