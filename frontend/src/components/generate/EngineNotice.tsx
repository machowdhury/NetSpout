import { useEngineStatus } from '../../lib/engineApi';

/** Shown on Generate Data and Scenarios whenever the Splunk app cannot use its PulseForge Engine. */
export function EngineNotice({ status }: { status: ReturnType<typeof useEngineStatus> }) {
  if (!status || status.connected) return null;
  return (
    <div className="sx-box sx-blocked" role="alert" data-testid="engine-notice" data-state={status.configured ? 'not-connected' : 'not-configured'}>
      <b>{status.message}</b>
      <p>{status.configured ? `The engine at ${status.url} did not answer. Start it, or correct the address in Connections.` : 'Nothing can be generated until the engine address is set.'} <a href="#/system/connections">Open Connections</a></p>
    </div>
  );
}
