import type { ExplorerEntry } from '../../lib/explorerApi';

export interface NetflowRunConfig { scale: number; duration_s: number; eps: number; sourcetype: string; wire: boolean; params: Record<string, number> }
export const defaultNetflowConfig = (entry: ExplorerEntry): NetflowRunConfig => ({
  scale: 1, duration_s: 180, eps: 50, sourcetype: 'netflow:collector', wire: true, params: { ...((entry as ExplorerEntry & { netflow?: { params?: Record<string, number> } }).netflow?.params ?? {}) },
});

// Configure step for the NetFlow/IPFIX scenarios: volume, time window, rate and the two delivery stages. Only values the generator validates are offered.
export function NetflowConfig({ entry, value, onChange }: { entry: ExplorerEntry; value: NetflowRunConfig; onChange: (v: NetflowRunConfig) => void }) {
  const nf = (entry as ExplorerEntry & { netflow?: { code: string; question: string; limits: string; extends?: string | null; mitre: string[]; params: Record<string, number> } }).netflow;
  if (!nf) return null;
  const set = (patch: Partial<NetflowRunConfig>) => onChange({ ...value, ...patch });
  return (
    <section className="ux-preview" data-testid="netflow-config" aria-label="NetFlow scenario configuration">
      <h3>Configure {nf.code}</h3>
      <p className="ux-note"><b>Limits:</b> {nf.limits}</p>
      {nf.extends && <p className="ux-note">Configurable, labelled flow profile related to the fixed pack <code>{nf.extends}</code>, which is unchanged.</p>}
      <div className="ux-config" style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
        <label>Volume scale<input type="number" min={0.1} max={10} step={0.1} value={value.scale} onChange={(e) => set({ scale: Math.max(0.1, Math.min(10, Number(e.target.value) || 1)) })} /></label>
        <label>Window (s)<input type="number" min={10} max={3600} value={value.duration_s} onChange={(e) => set({ duration_s: Math.max(10, Math.min(3600, Number(e.target.value) || 180)) })} /></label>
        <label>Delivery EPS<input type="number" min={1} max={2000} value={value.eps} onChange={(e) => set({ eps: Math.max(1, Math.min(2000, Number(e.target.value) || 50)) })} /></label>
        <label>Sourcetype
          <select value={value.sourcetype} onChange={(e) => set({ sourcetype: e.target.value })}>
            <option value="netflow:collector">netflow:collector (catalog sourcetype)</option>
            <option value="cisco:ios:ipfix">cisco:ios:ipfix (not in catalog; same field mapping)</option>
          </select>
        </label>
        {Object.entries(value.params).map(([k, v]) => (
          <label key={k}>{k.replace(/_/g, ' ')}<input type="number" value={v} onChange={(e) => set({ params: { ...value.params, [k]: Number(e.target.value) } })} /></label>))}
        <label><input type="checkbox" checked={value.wire} onChange={(e) => set({ wire: e.target.checked })} /> Also export IPFIX over UDP to the GoFlow2 collector</label>
      </div>
      <p className="ux-foot">Flows use RFC 5737 documentation addresses. HEC delivery of normalized flow events is what the monitor counts; the UDP export is reported separately and never counted as accepted.</p>
    </section>
  );
}
