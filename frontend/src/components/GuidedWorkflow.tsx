import { useEffect, useState } from 'react';

type Choice = { id: string; title?: string; name?: string };
type Manifest = { run_id: string; total_events_generated: number; dispatch_succeeded: number; dispatch_failed: number; observed_count: number; observation_status: string; errors: string[] };
async function request(url: string, body?: unknown) {
  const response = await fetch(url, body === undefined ? undefined : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
  return data;
}
export function GuidedWorkflow() {
  const [scenarios, setScenarios] = useState<Choice[]>([]);
  const [destinations, setDestinations] = useState<Choice[]>([]);
  const [scenario, setScenario] = useState('');
  const [destination, setDestination] = useState('');
  const [preview, setPreview] = useState('');
  const [result, setResult] = useState<Manifest>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [dashboard, setDashboard] = useState('');
  useEffect(() => { Promise.all([request('/api/acceptance/scenarios'), request('/api/destinations/')]).then(([s, d]) => { setScenarios(s); setDestinations(d); }).catch(e => setError(e.message)); }, []);
  async function execute(previewOnly: boolean) {
    setBusy(true); setError(''); setDashboard('');
    try {
      if (previewOnly) { const data = await request(`/api/acceptance/preview/${scenario}`, {}); setPreview(JSON.stringify(data.events, null, 2)); }
      else { setResult(undefined); setResult(await request('/api/scenarios/run-with-destination', { scenario_id: scenario, destination_id: destination, seed: 42 })); }
    } catch (e) { setError(String(e)); } finally { setBusy(false); }
  }
  return <section className="panel" style={{ padding: 24 }}>
    <h2>Guided Workflow</h2>
    <label>Scenario <select aria-label="Scenario" value={scenario} onChange={e => {setScenario(e.target.value); setResult(undefined); setPreview('');}}><option value="">Select executable scenario</option>{scenarios.map(s => <option key={s.id} value={s.id}>{s.title}</option>)}</select></label>
    <label>Destination <select aria-label="Destination" value={destination} onChange={e => {setDestination(e.target.value); setResult(undefined);}}><option value="">Select destination</option>{destinations.map(d => <option key={d.id} value={d.id}>{d.name}</option>)}</select></label>
    <p><button disabled={!scenario || busy} onClick={() => execute(true)}>Preview Telemetry</button> <button disabled={!scenario || !destination || busy} onClick={() => execute(false)}>Execute Scenario</button></p>
    {busy && <p role="status">Request in progress. Waiting for actual backend results.</p>}
    {error && <p role="alert">{error}</p>}
    {preview && <pre style={{ maxHeight: 350, overflow: 'auto' }}>{preview}</pre>}
    {result && <div><h3>Run {result.run_id}</h3><p>Generated: {result.total_events_generated}; HEC accepted: {result.dispatch_succeeded}; failed: {result.dispatch_failed}</p><p>Backend observation: {result.observation_status}; count: {result.observed_count}. HEC acceptance alone does not prove indexing.</p>{result.errors.map((e, i) => <p role="alert" key={i}>{e}</p>)}<button onClick={async () => {try {setError(''); const data = await request(`/api/acceptance/dashboards/${result.run_id}`, {destination_id: destination}); setDashboard(data.url);} catch(e) {setError(String(e));}}}>Deploy Run Dashboard</button>{dashboard && <p><a href={dashboard} target="_blank" rel="noreferrer">Open Dashboard in Splunk</a></p>}</div>}
  </section>;
}
