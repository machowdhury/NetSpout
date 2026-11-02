# NetSpout PulseForge naming and compatibility

The product is NetSpout PulseForge; the Splunk app ID remains `netspout`.

| Class | Names / locations | Decision and trace |
|---|---|---|
| 1 — visible branding | Native onboarding probe labels; legacy React engine label/default app path; runtime descriptions; JS/CSS headers | PulseForge display names. Probe option values stay unchanged. Current dashboard links and manifest lookup target netspout. Existing historical app-path detection remains. |
| 2 — migrated implementation | `netspout/bin/pulseforge_executor.py`, `PulseForgeExecutor` | Actual executor implementation moved here. `datablaster_executor.py` delegates CLI unchanged and aliases normal imports to the same module; both class spellings reference one class. Caller patches and logger state remain shared. No second process, handler or lock. |
| 3 — persistent REST identity | `datablaster_rest.py`, `DataBlasterRestHandler`, `[script:datablaster_execution]`, `/services/datablaster/execute`, web.conf exposure | Retain: restmap loads this handler under a Splunk-generated name; native_run_monitor binds by exact file and rejects duplicate ordinary imports. Runner, incident producer and executor import its helpers. Renaming here requires a dedicated persistent-loader migration and live validation; a naive import wrapper creates conflicting state. |
| 3 — view and JS identity | `datablaster_console.xml`, `datablaster_dashboard.xml`, `datablaster_console.js`, `datablaster_react_app.js`, CSS filename | Retain existing view IDs, bookmarks, navigation and script entry points. Visible titles are PulseForge. No duplicate view or initializer added. |
| 3 — saved state / browser API | datablaster_config.json, datablaster_status.json, datablaster.pid, datablaster.lock; ta_datablaster log/PID names; localStorage keys, datablaster-app-root, DataBlasterApp, window.datablaster* | Retain so saved settings, run history, controls and integrations do not split. Internal spelling is not product branding. |
| 3 — source/executable contracts | datablaster:probe, datablaster:preflight, datablaster:ssl; data-blaster binary names; DATABLASTER_TARGET_EPS | Retain ingestion identities, external binary lookup and environment compatibility. Display labels are PulseForge; no format or behavior migration. |
| 3 — historical paths / evidence | TA-network-data-blaster catalog/sample fallbacks; historical Docker names, acceptance reports, source quotations, old command paths | Preserve factual evidence and old-installation compatibility. Historical documents are not rewritten to imply a different tested deployment. Current UI paths use netspout. |

Only ordinary executor imports migrate in this batch. `DataBlasterExecutor` is a
legacy class spelling retained alongside `PulseForgeExecutor`. The REST handler
is intentionally not wrapped or registered twice. No new endpoint or app ID.

No transports, saved-state formats, credential mechanisms, scenarios or delivery
semantics change. No frontend rebuild or edits to generated dist bundles are
performed. The committed bundle contains neither DataBlaster nor Data Blaster
branding strings. Existing native/legacy display assets are edited directly.

Validation is offline. Installed Splunk loader behavior and rendered links still
require a separately approved deployment; this batch does not resolve or retry
the prior native get_config HTTP 400 smoke-test blocker.
