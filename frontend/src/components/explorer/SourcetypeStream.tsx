import { useEffect, useState } from 'react';
import { startRun } from '../../lib/runsApi';
import { explorerApi } from '../../lib/explorerApi';
import { LiveDeliveryMonitor, rememberRun, rememberedRun } from '../monitor/LiveDeliveryMonitor';

type Mode = 'continuous' | 'finite' | 'duration';

// One supported sourcetype, streamed until stopped (or by count / duration). The run lives on the engine, so the monitor reattaches after a refresh.
export function SourcetypeStream({ sourcetype, vendor }: { sourcetype: string; vendor?: string | null }) {
  const [mode, setMode] = useState<Mode>('continuous');
  const [eps, setEps] = useState(5);
  const [count, setCount] = useState(100);
  const [cap, setCap] = useState(0);
  const [duration, setDuration] = useState(60);
  const [indexes, setIndexes] = useState<string[]>([]);
  const [index, setIndex] = useState('');
  const [runId, setRunId] = useState<string | null>(rememberedRun('st:' + sourcetype));
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    explorerApi.setup().then((s) => {
      const list = s.indexes ?? [];
      setIndexes(list);
      setIndex((cur) => cur || list.find((i) => !/metric/i.test(i)) || list[0] || '');
    }, () => undefined);
  }, []);

  const start = () => startRun({
    kind: 'sourcetype', target: sourcetype, vendor_id: vendor ?? '', index: index || undefined, eps,
    mode: mode === 'finite' ? 'finite' : mode, count: mode === 'finite' ? count : mode === 'continuous' ? cap : undefined, duration_s: mode === 'duration' ? duration : undefined,
  }).then((r) => { rememberRun(r.run_id, 'st:' + sourcetype); setRunId(r.run_id); setErr(null); }, (e) => setErr(String(e.message || e)));

  return (
    <div className="ux-stream" data-testid="sourcetype-stream">
      <div className="ux-filters">
        <select value={mode} onChange={(e) => setMode(e.target.value as Mode)} aria-label="Stream mode">
          <option value="continuous">Continuous (until stopped)</option>
          <option value="finite">Finite: event count</option>
          <option value="duration">Finite: duration</option>
        </select>
        <label>EPS <input type="number" min={0.1} max={2000} step={0.5} value={eps} onChange={(e) => setEps(Number(e.target.value))} aria-label="Events per second" /></label>
        {mode === 'finite' && <label>Events <input type="number" min={1} max={1000} value={count} onChange={(e) => setCount(Number(e.target.value))} aria-label="Event count" /></label>}
        {mode === 'continuous' && <label>Safety cap <input type="number" min={0} value={cap} onChange={(e) => setCap(Number(e.target.value))} aria-label="Optional event cap" title="0 = no cap" /></label>}
        {mode === 'duration' && <label>Seconds <input type="number" min={1} max={86400} value={duration} onChange={(e) => setDuration(Number(e.target.value))} aria-label="Duration seconds" /></label>}
        <select value={index} onChange={(e) => setIndex(e.target.value)} aria-label="Index">{indexes.map((i) => <option key={i}>{i}</option>)}</select>
        <button type="button" className="ux-run-btn" data-testid="start-streaming" onClick={start}>Start Streaming</button>
      </div>
      {err && <p className="ux-error" role="alert">{err}</p>}
      {runId && <LiveDeliveryMonitor key={runId} runId={runId} onClose={() => setRunId(null)} />}
    </div>
  );
}
