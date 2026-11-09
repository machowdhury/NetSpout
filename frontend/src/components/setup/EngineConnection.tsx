import { useEffect, useState } from 'react';
import { engineStatus, insideSplunk, saveEngine, type EngineStatus } from '../../lib/engineApi';

// Where the PulseForge Engine runs. The Splunk app talks to exactly this address; nothing is guessed when it is empty.
export function EngineConnection() {
  const [status, setStatus] = useState<EngineStatus | null>(null);
  const [url, setUrl] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [loaded, setLoaded] = useState(false);   // the first status can take seconds when the engine is unreachable; the form stays disabled until the saved URL is known, so it can never act on, or overwrite, an unloaded value
  useEffect(() => { if (insideSplunk()) engineStatus().then((s) => { setStatus(s); setUrl(s.url); setLoaded(true); }, (e) => { setError(e instanceof Error ? e.message : String(e)); setLoaded(true); }); }, []);
  if (!insideSplunk()) return null;
  const save = async () => {
    setBusy(true); setError('');
    try { const s = await saveEngine(url.trim()); setStatus(s); setUrl(s.url); } catch (e) { setError(e instanceof Error ? e.message : String(e)); } finally { setBusy(false); }
  };
  if (status?.managed) return (
    <section className="sx-box" data-testid="engine-connection" aria-label="PulseForge Engine">
      <span className="sx-step">PulseForge Engine</span>
      <p data-testid="engine-status" data-state={status.connected ? 'connected' : 'not-connected'} className={status.connected ? 'sx-ok' : 'sx-bad'}>
        {status.message}{status.restarts ? ` Restarts: ${status.restarts}.` : ''}{status.last_error ? ` Last error: ${status.last_error}.` : ''}
      </p>
      <p className="sx-muted" data-testid="engine-managed-note">Splunk starts and supervises the engine; there is nothing to install or configure. It listens on a private socket, not a network port.</p>
    </section>
  );
  return (
    <section className="sx-box" data-testid="engine-connection" aria-label="PulseForge Engine">
      <span className="sx-step">PulseForge Engine</span>
      <p data-testid="engine-status" data-state={!status ? 'unknown' : !status.configured ? 'not-configured' : status.connected ? 'connected' : 'not-connected'} className={status?.connected ? 'sx-ok' : 'sx-bad'}>
        {status ? `${status.message}${status.connected && status.version ? ` Version ${status.version}.` : ''}` : 'Checking the engine…'}
      </p>
      <div className="sx-row">
        <label>Engine URL<input type="url" data-testid="engine-url" value={url} placeholder="http://engine-host:8081" disabled={!loaded} onChange={(e) => setUrl(e.target.value)} /></label>
        <button type="button" data-testid="save-engine" disabled={busy || !loaded} onClick={() => void save()}>Save engine</button>
      </div>
      <p className="sx-muted">The engine runs in Docker on a host you control. Enter the address this Splunk server can reach it at.</p>
      {error && <p className="sx-bad" role="alert" data-testid="engine-error">{error}</p>}
    </section>
  );
}
