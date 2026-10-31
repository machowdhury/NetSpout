# 04 Splunk Cloud guide

**Status: USER VALIDATION PENDING.** The maintainers did not connect to, install into or test any Splunk Cloud stack, and nothing here is a certification.

## Why there is a separate Cloud edition
`netspout.spl` (Enterprise app) was inspected with Splunk AppInspect 4.4.0 using the Splunk Cloud ruleset (`--mode precert --included-tags cloud`), evidence `docs/verification/evidence/appinspect/cloud.json`: **0 errors, 8 failures, 11 warnings, 137 passed**. The failures: UDP network communications in the engine modules (25 findings: SNMP, syslog, flow), a modular input and REST handlers without the required `python.version`/`python.required` settings, illegal `indexes.conf` properties, `is_configured = 1`, and a missing `[triggers]` stanza. Splunk Cloud cannot run a customer collector and prohibits programmatic UDP, so the engine cannot live in the app.

`netspout_cloud.spl` (built by `scripts/build_splunk_cloud_package.py`) therefore contains **only** Dashboard Studio views (133), navigation, `app.conf`, `app.manifest`, metadata and a README: no Python, no inputs, no indexes, no REST handlers, no custom conf. AppInspect (cloud ruleset): **0 failures, 0 errors, 0 warnings, 87 passed** (`cloud_edition.json`). That is a pre-submission result, not Splunk Cloud approval; the official vetting and any manual review are yours to run.

## Supported architecture
```text
 Customer network                                           Splunk Cloud
 +---------------------------+   HEC (events, metrics)     +-------------------------------+
 | PulseForge engine         | --------------------------> | event + metric indexes (yours) |
 | (and optional collectors) |                             | netspout app: pf_* dashboards  |
 +---------------------------+ <-- search (REST token) --- | search head                    |
```
The Explorer/Command Center UI and the gateway are **not** part of the Cloud edition; the engine's own UI/API run on the customer side. Dashboards work with any run: open `/app/netspout/pf_<scenario id>?form.run_tok=<run or session id>`.

## Validation checklist (for you)
1. Confirm your stack's HEC endpoint, a token restricted to specific indexes, and your IP allow list (engine egress address).
2. Create the event and metric indexes you will allow (the product never creates indexes).
3. Run AppInspect on `netspout_cloud.spl` (`splunk-appinspect inspect netspout_cloud.spl --mode precert --included-tags cloud`) and submit through your normal Cloud app-vetting path ([official requirements](https://dev.splunk.com/enterprise/docs/releaseapps/cloudvetting)).
4. Install the vetted app; confirm the `Scenario Dashboards` nav collection and that your role can read the views.
5. Start the engine on your network with the Connection Center pointed at the Cloud HEC URL (real TLS; `allow_insecure_tls` false) and a search credential limited to the allowed indexes.
6. Run one replay pack and one incident pack; confirm indexed counts with your own search and open the matching dashboards with the returned run id.
7. Record: HEC acceptance, indexed counts, dashboards populated, any vetting findings.

## Known blockers and open questions
- Splunk Cloud outbound/inbound policies for the engine-to-Cloud path are customer-specific.
- The Explorer UI is not shipped to Cloud; run launching happens against the engine directly.
- Add-ons for vendor sourcetypes (parsing, CIM) must be installed through Splunk Cloud's own process; none were validated here.
