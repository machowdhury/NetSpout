import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { CheckCircle2, CircleAlert, RefreshCw, ShieldCheck } from 'lucide-react';
import { fetchJson } from '../../lib/api';
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
  indexes: string;
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
  indexes: 'idx_network_ops',
  collectors: ['HEC'],
  guided_sample: true,
  allow_insecure_tls: true,
};

export function SetupWizard() {
  const [configuration, setConfiguration] = useState<SetupConfiguration | null>(null);
  const [form, setForm] = useState<FormState>(initialForm);
  const [validation, setValidation] = useState<SetupValidation | null>(null);
  const [busy, setBusy] = useState(false);
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
          indexes: response.indexes?.join(', ') ?? current.indexes,
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
      const response = await fetchJson<SetupConfiguration>('/api/setup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...form,
          indexes: form.indexes.split(',').map((item) => item.trim()).filter(Boolean),
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
    <div className="workspace-stack setup-wizard" data-testid="setup-wizard">
      <header className="generation-hero">
        <div><span className="generation-eyebrow">First-run onboarding</span><h2>Setup Wizard &amp; Connection Center</h2><p>Connect the external NetSpout engine to an authorized Splunk destination without editing source code.</p></div>
        <div className="generation-hero__summary">
          <span><strong>{configuration?.configured ? 'Configured' : 'Setup required'}</strong> connection</span>
          <span><strong>{configuration?.secret_state.hec_token_configured ? 'Present' : 'Missing'}</strong> ingestion credential</span>
        </div>
      </header>

      <div className="setup-security-note"><ShieldCheck /><div><strong>Secrets stay server-side and in memory.</strong><span>They are never returned by this API, persisted to the browser, written to the metadata file, or placed in a URL. Use environment-backed secret injection for durable deployments.</span></div></div>
      {error && <div className="generation-alert generation-alert--error" role="alert"><CircleAlert /> {error}</div>}

      <form className="setup-form" onSubmit={save}>
        <fieldset><legend>1. Deployment</legend>
          <label>Mode<select value={form.deployment_mode} onChange={(event) => setForm({ ...form, deployment_mode: event.target.value, splunk_deployment_type: event.target.value })}>
            <option value="DOCKER_LAB">Self-contained Docker lab</option>
            <option value="SPLUNK_ENTERPRISE">Existing Splunk Enterprise</option>
            <option value="SPLUNK_CLOUD">Splunk Cloud architecture target</option>
          </select></label>
          <label>Splunk deployment type<input value={form.splunk_deployment_type} onChange={(event) => setForm({ ...form, splunk_deployment_type: event.target.value })} /></label>
        </fieldset>
        <fieldset><legend>2. Endpoints and authentication</legend>
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
        <fieldset><legend>3. Authorized data and collectors</legend>
          <label>Allowed indexes<input required value={form.indexes} onChange={(event) => setForm({ ...form, indexes: event.target.value })} /><small>Comma-separated. NetSpout will not create indexes silently.</small></label>
          <label>Collectors<select multiple value={form.collectors} onChange={(event) => setForm({ ...form, collectors: [...event.target.selectedOptions].map((item) => item.value) })}>
            <option value="HEC">HEC</option><option value="SYSLOG">Syslog</option><option value="OTEL">OpenTelemetry</option><option value="GOFLOW2">GoFlow2</option>
          </select></label>
          <label className="setup-checkbox"><input type="checkbox" checked={form.guided_sample} onChange={(event) => setForm({ ...form, guided_sample: event.target.checked })} /> Offer a guided security sample after validation</label>
        </fieldset>
        <div className="generation-actions"><span /><button type="submit" className="generation-primary" disabled={busy}>{busy ? 'Saving…' : 'Save secure configuration'}</button></div>
      </form>

      <section className="generation-panel">
        <div className="generation-panel__header"><div><h3>Connection health</h3><span>HEC reachability and authenticated search are tested independently.</span></div><button type="button" className="generation-secondary" disabled={busy || !configuration?.configured} onClick={validate}><RefreshCw /> Validate</button></div>
        {!validation && <div className="generation-empty">Save configuration, then validate before running telemetry.</div>}
        {validation?.checks.map((check) => <article className="setup-check" key={check.id}>{check.status === 'PASS' ? <CheckCircle2 /> : <CircleAlert />}<div><strong>{check.id.replaceAll('_', ' ')}</strong><span>{check.detail}</span></div><span className={badgeForCheck(check.status)}>{check.status}</span></article>)}
        {validation?.status === 'PASS' && form.guided_sample && <a className="generation-primary source-run-link" href="#/generate/scenarios">Run guided security scenario</a>}
      </section>
    </div>
  );
}

function badgeForCheck(status: string) {
  return `source-status source-status--${status.toLowerCase().replaceAll('_', '-')}`;
}
