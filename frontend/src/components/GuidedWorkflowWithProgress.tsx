import { useEffect, useState, useRef } from 'react';

type Choice = { id: string; title?: string; name?: string };
type Manifest = { 
  run_id: string; 
  total_events_generated: number; 
  dispatch_succeeded: number; 
  dispatch_failed: number; 
  observed_count: number; 
  observation_status: string; 
  errors: string[] 
};

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
  const response = await fetch(url, body === undefined ? undefined : { 
    method: 'POST', 
    headers: { 'Content-Type': 'application/json' }, 
    body: JSON.stringify(body) 
  });
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
  return data;
}

export function GuidedWorkflowWithProgress() {
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

  // WebSocket connection for progress updates
  useEffect(() => {
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
        const result = await request('/api/scenarios/run-with-progress', { 
          scenario_id: scenario, 
          destination_id: destination, 
          seed: 42 
        });
        setResult(result);
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
      <h2>Guided Workflow with Progress Tracking</h2>
      <p>WebSocket status: {wsConnected ? 'Connected ✓' : 'Disconnected ✗'}</p>
      
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
          Execute Scenario with Progress
        </button>
        
        {busy && (
          <button onClick={cancelRun}>
            Cancel Run
          </button>
        )}
      </p>
      
      {busy && (
        <div role="status">
          <h3>Run Progress</h3>
          {currentProgress && (
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
          )}
          <p>Waiting for actual backend results...</p>
        </div>
      )}
      
      {error && <p role="alert">{error}</p>}
      
      {preview && (
        <pre style={{ maxHeight: 350, overflow: 'auto' }}>
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
            <p>
              <a href={dashboard} target="_blank" rel="noreferrer">
                Open Dashboard in Splunk
              </a>
            </p>
          )}
        </div>
      )}
      
      {progress.length > 0 && (
        <div>
          <h3>Progress History</h3>
          <ul style={{ maxHeight: 200, overflow: 'auto' }}>
            {progress.map((p, i) => (
              <li key={i}>
                {new Date(p.timestamp).toLocaleTimeString()}: {p.state} - {p.message}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}