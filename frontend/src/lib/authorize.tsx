import { useEffect, useState } from 'react';
import { fetchJson } from './api';

// Outside the self-contained Docker lab the engine refuses to send synthetic data until the user has confirmed the destination (confirm_destination). The confirmation is per page load and is never remembered.
let confirmed = false;
export const destinationConfirmed = () => confirmed;

export function useDestinationAuthorization() {
  const [mode, setMode] = useState<string | null>(null);
  const [ok, setOk] = useState(confirmed);
  useEffect(() => {
    fetchJson<{ configured?: boolean; deployment_mode?: string | null }>('/api/setup').then((c) => setMode(c.configured ? c.deployment_mode ?? null : null), () => setMode(null));
  }, []);
  const needed = mode !== null && mode !== 'DOCKER_LAB';
  return { needed, confirmed: ok, blocked: needed && !ok, set: (v: boolean) => { confirmed = v; setOk(v); } };
}

export function AuthorizeDestination({ auth, index }: { auth: ReturnType<typeof useDestinationAuthorization>; index?: string }) {
  if (!auth.needed) return null;
  return (
    <label className="sx-check" data-testid="authorize-label">
      <input type="checkbox" data-testid="authorize-destination" checked={auth.confirmed} onChange={(e) => auth.set(e.target.checked)} />
      {' '}I authorize sending synthetic test data to {index ? <code>{index}</code> : 'the saved Splunk destination'}. Nothing is sent until I do.
    </label>
  );
}
