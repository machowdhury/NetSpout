import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { CheckCircle2, CircleAlert, RefreshCw, ShieldCheck } from 'lucide-react';
import { fetchJson } from '../../lib/api';
import { testConnection } from '../../lib/runsApi';
import type { SetupConfiguration, SetupValidation } from '../../types/release';

type FormState = {
  deployment_mode: string;
  splunk_deployment_type: string;
  hec_url: string;
  search_url: string;
  auth_method: string;
  search_username: string;
  hec_token: string;
  search_secret: string;
  event_index: string;
  metric_index: string;
  collectors: string[];
  guided_sample: boolean;
  allow_insecure_tls: boolean;
};

const initialForm: FormState = {
  deployment_mode: 'DOCKER_LAB',
  splunk_deployment_type: 'DOCKER_BUNDLED_ENTERPRISE',
  hec_url: 'https://127.0.0.1:8088/services/collector',
  search_url: 'https://127.0.0.1:8089/services/search/jobs/export',
  auth_method: 'HEC_TOKEN_AND_BASIC_SEARCH',
  search_username: 'admin',
  hec_token: '',
  search_secret: '',
  event_index: 'idx_network_ops',
  metric_index: 'cisco_mdt_metrics',
  collectors: ['HEC'],
  guided_sample: true,
  allow_insecure_tls: true,
};

export function SetupWizard() {
  const [configuration, setConfiguration] = useState<SetupConfiguration | null>(null);
  const [form, setForm] = useState<FormState>(initialForm);
  const [validation, setValidation] = useState<SetupValidation | null>(null);
  const [busy, setBusy] = useState(false);
  const [testIndex, setTestIndex] = useState('');
  const effectiveTestIndex = testIndex.trim() || form.event_index.split(',')[0].trim();
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<Record<string, unknown> | null>(null);
  const [testError, setTestError] = useState<string | null>(null);
  const runConnectionTest = async () => {
    setTesting(true); setTestError(null); setTestResult(null);
    try { setTestResult(await testConnection({ test_index: effectiveTestIndex })); } catch (e) { setTestError(e instanceof Error ? e.message : String(e)); } finally { setTesting(false); }
  };
  const [error, setError] = useState('');

  const load = () => fetchJson<SetupConfiguration>('/api/setup')
    .then((response) => {
      setConfiguration(response);
      if (response.configured) {
        setForm((current) => ({
          ...current,
          deployment_mode: response.deployment_mode ?? current.deployment_mode,
          splunk_deployment_type: response.splunk_deployment_type ?? current.splunk_deployment_type,
          hec_url: response.hec_url ?? current.hec_url,
          search_url: response.search_url ?? current.search_url,
          auth_method: response.auth_method ?? current.auth_method,
          search_username: response.search_username ?? '',
          event_index: (response.indexes ?? []).filter((item) => !/metric/i.test(item)).join(', ') || current.event_index,
          metric_index: (response.indexes ?? []).filter((item) => /metric/i.test(item)).join(', ') || current.metric_index,
          collectors: response.collectors ?? current.collectors,
          guided_sample: response.guided_sample ?? current.guided_sample,
          allow_insecure_tls: response.allow_insecure_tls ?? false,
          hec_token: '',
          search_secret: '',
        }));
      }
    })
    .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : 'Setup service unavailable'));

  useEffect(() => { void load(); }, []);

  const save = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    setValidation(null);
    try {
      const { event_index, metric_index, ...rest } = form;
      const response = await fetchJson<SetupConfiguration>('/api/setup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...rest,
          indexes: [event_index, metric_index].flatMap((value) => value.split(',')).map((item) => item.trim()).filter(Boolean),
        }),
      });
      setConfiguration(response);
      setForm((current) => ({ ...current, hec_token: '', search_secret: '' }));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Configuration was rejected');
    } finally {
      setBusy(false);
    }
  };

  const validate = async () => {
    setBusy(true);
    setError('');
    try {
      setValidation(await fetchJson<SetupValidation>('/api/setup/validate', { method: 'POST' }, 15000));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Connectivity validation failed');
    } finally {
      setBusy(false);
    }
  };

  const useDockerDefaults = form.deployment_mode === 'DOCKER_LAB';
  return (
    <div className="sx setup-wizard" data-testid="setup-wizard">
      <header>
        <h2>Connections</h2>
        <p data-testid="connection-status"><strong>{configuration?.configured ? 'A Splunk destination is saved.' : 'No Splunk destination is saved yet.'}</strong> {configuration?.secret_state.hec_token_configured ? 'The HEC token is stored on the server and is never shown again.' : 'No HEC token is stored.'}</p>
      </header>

      <div className="setup-security-note"><ShieldCheck /><div><strong>Secrets stay server-side and in memory.</strong><span>They are never returned by this API, persisted to the browser, written to the metadata file, or placed in a URL. Use environment-backed secret injection for durable deployments.</span></div></div>
      {error && <div className="sx-box sx-blocked" role="alert"><CircleAlert /> {error}</div>}

      <form className="sx-box setup-form" onSubmit={save}>
        <fieldset><legend>1. Splunk endpoint and credentials</legend>
          <label>HEC endpoint<input type="url" required value={form.hec_url} onChange={(event) => setForm({ ...form, hec_url: event.target.value })} /></label>
          <label>Search API endpoint<input type="url" required value={form.search_url} onChange={(event) => setForm({ ...form, search_url: event.target.value })} /></label>
          <label>Authentication<select value={form.auth_method} onChange={(event) => setForm({ ...form, auth_method: event.target.value })}>
            <option value="HEC_TOKEN_AND_BASIC_SEARCH">HEC token + least-privilege search user</option>
            <option value="HEC_TOKEN_AND_SPLUNK_TOKEN">HEC token + Splunk bearer token</option>
          </select></label>
          {form.auth_method === 'HEC_TOKEN_AND_BASIC_SEARCH' && <label>Search username<input autoComplete="username" value={form.search_username} onChange={(event) => setForm({ ...form, search_username: event.target.value })} /></label>}
          <label>HEC token<input type="password" autoComplete="off" required={!configuration?.secret_state.hec_token_configured} value={form.hec_token} onChange={(event) => setForm({ ...form, hec_token: event.target.value })} placeholder={configuration?.secret_state.hec_token_configured ? 'Configured — leave blank to retain' : 'Required'} /></label>
          <label>Search credential<input type="password" autoComplete="off" required={!configuration?.secret_state.search_secret_configured} value={form.search_secret} onChange={(event) => setForm({ ...form, search_secret: event.target.value })} placeholder={configuration?.secret_state.search_secret_configured ? 'Configured — leave blank to retain' : 'Required'} /></label>
          <label className="setup-checkbox"><input type="checkbox" disabled={!useDockerDefaults} checked={form.allow_insecure_tls} onChange={(event) => setForm({ ...form, allow_insecure_tls: event.target.checked })} /> Allow the documented loopback-only lab certificate exception</label>
        </fieldset>
        <fieldset><legend>2. Where the data goes</legend>
          <label>Event index<input required data-testid="event-index" value={form.event_index} onChange={(event) => setForm({ ...form, event_index: event.target.value })} /><small>Logs and events go here. NetSpout will not create indexes silently.</small></label>
          <label>Metric index<input data-testid="metric-index" value={form.metric_index} onChange={(event) => setForm({ ...form, metric_index: event.target.value })} /><small>Metrics go here. The name must contain &quot;metric&quot;, and the index must be a metrics index in Splunk.</small></label>
        </fieldset>
        <details className="setup-advanced"><summary>Advanced settings</summary>
        <fieldset><legend>1. Deployment</legend>
          <label>Mode<select value={form.deployment_mode} onChange={(event) => setForm({ ...form, deployment_mode: event.target.value, splunk_deployment_type: event.target.value })}>
            <option value="DOCKER_LAB">Self-contained Docker lab</option>
            <option value="SPLUNK_ENTERPRISE">Existing Splunk Enterprise</option>
            <option value="SPLUNK_CLOUD">Splunk Cloud architecture target</option>
          </select></label>
          <label>Splunk deployment type<input value={form.splunk_deployment_type} onChange={(event) => setForm({ ...form, splunk_deployment_type: event.target.value })} /></label>
        </fieldset>
          <label>Collectors<select multiple value={form.collectors} onChange={(event) => setForm({ ...form, collectors: [...event.target.selectedOptions].map((item) => item.value) })}>
            <option value="HEC">HEC</option><option value="SYSLOG">Syslog</option><option value="OTEL">OpenTelemetry</option><option value="GOFLOW2">GoFlow2</option>
          </select></label>
          <label className="setup-checkbox"><input type="checkbox" checked={form.guided_sample} onChange={(event) => setForm({ ...form, guided_sample: event.target.checked })} /> Offer a guided security sample after validation</label>
        </details>
        <div className="sx-row"><span /><button type="submit" className="sx-primary" disabled={busy}>{busy ? 'Saving…' : 'Save secure configuration'}</button></div>
      </form>

      <section className="sx-box">
        <div className="sx-row"><div><h3>Connection health</h3><span>HEC reachability and authenticated search are tested independently.</span></div><button type="button"  disabled={busy || !configuration?.configured} onClick={validate}><RefreshCw /> Validate</button></div>
        {!validation && <div className="sx-muted">Save configuration, then validate before running telemetry.</div>}
        {validation?.checks.map((check) => <article className="setup-check" key={check.id}>{check.status === 'PASS' ? <CheckCircle2 /> : <CircleAlert />}<div><strong>{check.id.replaceAll('_', ' ')}</strong><span>{check.detail}</span></div><span className={badgeForCheck(check.status)}>{check.status}</span></article>)}
        {validation?.status === 'PASS' && form.guided_sample && <a className="sx-primary source-run-link" href="#/generate/scenarios">Run guided security scenario</a>}
      </section>

      <section className="sx-box" aria-label="External HEC connection test">
        <div className="sx-row"><div><h3>HEC connection test</h3><span>Sends one marked synthetic event to the named test index of the saved destination, then searches for it. Connection, acceptance and indexing are reported separately.</span></div></div>
        <div className="sx-row">
          <label>Test index<input value={testIndex} placeholder={form.event_index.split(',')[0].trim() || 'an allowed index'} onChange={(event) => setTestIndex(event.target.value)} /></label>
          <button type="button"  disabled={testing || !configuration?.configured || !effectiveTestIndex} onClick={runConnectionTest}>{testing ? 'Testing…' : 'Test connection'}</button>
        </div>
        {testError && <div className="sx-muted">{testError}</div>}
        {testResult && (
          <>
            <p><strong>Overall: {String(testResult.overall)}</strong> {testResult.overall === 'ACCEPTED_NOT_VERIFIED' && '— Splunk acknowledged the event but indexing was not independently confirmed.'}</p>
            <p>{Object.entries((testResult.statuses ?? {}) as Record<string, string>).map(([k, v]) => `${k}: ${v}`).join(' · ')}</p>
            {((testResult.steps ?? []) as Array<{ id: string; status: string; detail: string }>).map((step) => <article className="setup-check" key={step.id}><div><strong>{step.id.replaceAll('_', ' ')}</strong><span>{step.detail}</span></div><span className={badgeForCheck(step.status)}>{step.status}</span></article>)}
            {testResult.error && <div className="sx-muted">{(testResult.error as { category: string; message: string }).category}: {(testResult.error as { message: string }).message}</div>}
          </>
        )}
      </section>
    </div>
  );
}

function badgeForCheck(status: string) {
  return `source-status source-status--${status.toLowerCase().replaceAll('_', '-')}`;
}
