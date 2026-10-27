import { useEffect, useState, useRef } from 'react';

type Choice = { id: string; title?: string; name?: string };
type Manifest = { run_id: string; total_events_generated: number; dispatch_succeeded: number; dispatch_failed: number; observed_count: number; observation_status: string; errors: string[] };
type ProgressEvent = {
  type: string;
  run_id: string;
  state: string;
  timestamp: string;
  message: string;
  details: any;
  current_phase?: string;
  phases_total?: number;
  phases_completed?: number;
  generated_count?: number;
  accepted_count?: number;
  rejected_count?: number;
  indexed_count?: number;
  verified_count?: number;
  transport_target?: string;
  transport_protocol?: string;
  transport_status?: string;
};

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
  const [progress, setProgress] = useState<ProgressEvent[]>([]);
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const [useProgressEndpoint, setUseProgressEndpoint] = useState(true);

  // WebSocket connection for progress updates
  useEffect(() => {
    // Skip WebSocket connection during SSR
    if (typeof window === 'undefined') return;

    const connectWebSocket = () => {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/run-progress`;
      
      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          console.log('WebSocket connected for progress updates');
          setWsConnected(true);
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'run_progress') {
              setProgress(prev => [...prev, data]);
            } else if (data.type === 'run_cancelled') {
              setError(`Run ${data.run_id} cancelled: ${data.reason}`);
              setBusy(false);
            }
          } catch (e) {
            console.error('Failed to parse WebSocket message:', e);
          }
        };

        ws.onclose = () => {
          console.log('WebSocket disconnected');
          setWsConnected(false);
          // Attempt to reconnect after 5 seconds
          setTimeout(connectWebSocket, 5000);
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
        };
      } catch (e) {
        console.error('Failed to create WebSocket:', e);
      }
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  // Load scenarios and destinations
  useEffect(() => { 
    Promise.all([
      request('/api/acceptance/scenarios'), 
      request('/api/destinations/')
    ]).then(([s, d]) => { 
      setScenarios(s); 
      setDestinations(d); 
    }).catch(e => setError(e.message)); 
  }, []);

  async function execute(previewOnly: boolean) {
    setBusy(true); 
    setError(''); 
    setDashboard('');
    setProgress([]);
    
    try {
      if (previewOnly) { 
        const data = await request(`/api/acceptance/preview/${scenario}`, {}); 
        setPreview(JSON.stringify(data.events, null, 2)); 
      } else { 
        setResult(undefined);
        
        if (useProgressEndpoint) {
          // Use progress-enabled endpoint
          const result = await request('/api/scenarios/run-with-progress', { 
            scenario_id: scenario, 
            destination_id: destination, 
            seed: 42 
          });
          setResult(result);
        } else {
          // Use traditional endpoint (backward compatibility)
          const result = await request('/api/scenarios/run-with-destination', { 
            scenario_id: scenario, 
            destination_id: destination, 
            seed: 42 
          });
          setResult(result);
        }
      }
    } catch (e) { 
      setError(String(e)); 
    } finally { 
      setBusy(false); 
    }
  }

  function cancelRun() {
    if (progress.length > 0) {
      const lastRunId = progress[progress.length - 1].run_id;
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({
          action: 'cancel_run',
          run_id: lastRunId,
          reason: 'User cancelled'
        }));
      }
    }
  }

  const currentProgress = progress.length > 0 ? progress[progress.length - 1] : null;

  return (
    <section className="panel" style={{ padding: 24 }}>
      <h2>Guided Workflow</h2>
      <p>WebSocket status: {typeof window === 'undefined' ? 'Checking...' : (wsConnected ? 'Connected ✓' : 'Disconnected ✗')}</p>
      
      <div style={{ marginBottom: '16px', padding: '12px', backgroundColor: '#f5f5f5', borderRadius: '4px' }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <input 
            type="checkbox" 
            checked={useProgressEndpoint}
            onChange={(e) => setUseProgressEndpoint(e.target.checked)}
          />
          Use real-time progress tracking (WebSocket)
        </label>
        <small style={{ display: 'block', marginTop: '4px', color: '#666' }}>
          {useProgressEndpoint 
            ? 'Shows live progress during execution with WebSocket updates'
            : 'Traditional execution without live progress (backward compatible)'}
        </small>
      </div>
      
      <label>
        Scenario 
        <select 
          aria-label="Scenario" 
          value={scenario} 
          onChange={e => {
            setScenario(e.target.value); 
            setResult(undefined); 
            setPreview('');
            setProgress([]);
          }}
        >
          <option value="">Select executable scenario</option>
          {scenarios.map(s => (
            <option key={s.id} value={s.id}>{s.title}</option>
          ))}
        </select>
      </label>
      
      <label>
        Destination 
        <select 
          aria-label="Destination" 
          value={destination} 
          onChange={e => {
            setDestination(e.target.value); 
            setResult(undefined);
            setProgress([]);
          }}
        >
          <option value="">Select destination</option>
          {destinations.map(d => (
            <option key={d.id} value={d.id}>{d.name}</option>
          ))}
        </select>
      </label>
      
      <p>
        <button disabled={!scenario || busy} onClick={() => execute(true)}>
          Preview Telemetry
        </button>
        
        <button disabled={!scenario || !destination || busy} onClick={() => execute(false)}>
          {useProgressEndpoint ? 'Execute with Progress' : 'Execute Scenario'}
        </button>
        
        {busy && useProgressEndpoint && (
          <button onClick={cancelRun} style={{ marginLeft: '8px' }}>
            Cancel Run
          </button>
        )}
      </p>
      
      {busy && useProgressEndpoint && currentProgress && (
        <div role="status" style={{ margin: '16px 0', padding: '12px', backgroundColor: '#e8f4f8', borderRadius: '4px' }}>
          <h3 style={{ marginTop: 0 }}>Run Progress</h3>
          <div>
            <p><strong>State:</strong> {currentProgress.state}</p>
            <p><strong>Message:</strong> {currentProgress.message}</p>
            {currentProgress.current_phase && (
              <p><strong>Phase:</strong> {currentProgress.current_phase} 
                ({currentProgress.phases_completed || 0}/{currentProgress.phases_total || '?'})
              </p>
            )}
            {currentProgress.generated_count !== undefined && (
              <p><strong>Generated:</strong> {currentProgress.generated_count}</p>
            )}
            {currentProgress.accepted_count !== undefined && (
              <p><strong>Accepted:</strong> {currentProgress.accepted_count}</p>
            )}
            {currentProgress.indexed_count !== undefined && (
              <p><strong>Indexed:</strong> {currentProgress.indexed_count}</p>
            )}
          </div>
        </div>
      )}
      
      {busy && !useProgressEndpoint && (
        <p role="status">Request in progress. Waiting for actual backend results...</p>
      )}
      
      {error && <p role="alert" style={{ color: '#d32f2f' }}>{error}</p>}
      
      {preview && (
        <pre style={{ maxHeight: 350, overflow: 'auto', backgroundColor: '#f5f5f5', padding: '12px' }}>
          {preview}
        </pre>
      )}
      
      {result && (
        <div>
          <h3>Run {result.run_id}</h3>
          <p>Generated: {result.total_events_generated}; HEC accepted: {result.dispatch_succeeded}; failed: {result.dispatch_failed}</p>
          <p>Backend observation: {result.observation_status}; count: {result.observed_count}. HEC acceptance alone does not prove indexing.</p>
          {result.errors.map((e, i) => (
            <p role="alert" key={i}>{e}</p>
          ))}
          <button onClick={async () => {
            try {
              setError('');
              const data = await request(`/api/acceptance/dashboards/${result.run_id}`, {
                destination_id: destination
              });
              setDashboard(data.url);
            } catch(e) {
              setError(String(e));
            }
          }}>
            Deploy Run Dashboard
          </button>
          {dashboard && (
            <p style={{ marginTop: '8px' }}>
              <a href={dashboard} target="_blank" rel="noreferrer" style={{ color: '#1976d2' }}>
                Open Dashboard in Splunk
              </a>
            </p>
          )}
        </div>
      )}
      
      {progress.length > 0 && useProgressEndpoint && (
        <div style={{ marginTop: '24px' }}>
          <h3>Progress History</h3>
          <ul style={{ maxHeight: 200, overflow: 'auto', listStyle: 'none', padding: 0 }}>
            {progress.map((p, i) => (
              <li key={i} style={{ padding: '4px 0', borderBottom: '1px solid #eee' }}>
                <small>{new Date(p.timestamp).toLocaleTimeString()}</small>: {p.state} - {p.message}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}
