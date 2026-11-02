# NetSpout Release Candidate Guide

NetSpout is an offline-first synthetic telemetry lab. It generates bounded
network, security, agentic-AI, and software-supply-chain evidence, sends that
evidence through supported transports, and verifies what Splunk actually
indexed. It does not attack external systems or claim that modeled activity is
production evidence.

## Choose a deployment

### Docker Lab

Use this mode for evaluation and learning. It runs the NetSpout web application,
simulation engine, Splunk Enterprise lab, and bounded collectors from the same
source tree.

1. Install Docker Desktop with Compose.
2. Copy `.env.example` to `.env`.
3. Generate unique local-lab values with a password manager or operating-system
   CSPRNG and set `SPLUNK_PASSWORD` and `SPLUNK_HEC_TOKEN` in `.env`.
4. Start with `docker compose up -d --build`.
5. Wait for `docker compose ps` to report healthy services.
6. Open NetSpout at `http://127.0.0.1:8081` and Splunk Web at
   `http://127.0.0.1:8000`.
7. Complete **System → Connections**. The loopback certificate exception is
   permitted only for this disposable lab.

Administrative services bind to loopback by default. The repository contains no
default password or HEC token. Docker retrieves the permitted Splunk image from
its publisher; NetSpout does not redistribute Splunk binaries.

Stop without deleting data:

```bash
docker compose down
```

Reset the disposable lab after confirming no needed evidence remains:

```bash
docker compose down --volumes
```

Upgrade by preserving `.env`, fetching the authorized branch or archive,
reviewing release notes, and running `docker compose up -d --build`. Back up
named volumes before an important upgrade.

### Splunk App plus external engine

`netspout.spl` uses a supported Splunk App layout. Install it through
**Apps → Manage Apps → Install app from file**, or unpack it under
`$SPLUNK_HOME/etc/apps` using standard administrator procedures.

The package supplies Splunk navigation, existing Splunk views, investigation
content, dashboards, and static client assets. The Phase 13 Security Source
Catalog, Scenario Gallery/Studio, Dashboard Studio, and Connection Center run
in the external NetSpout web UI served by the companion engine; they are not
native search-head views. The simulation engine is a separate service and is
not a privileged process embedded in the search head. Configure the engine and
open its UI using the documented deployment integration. Do not add secrets to
`default/`; use environment-backed engine configuration and Splunk `local/`
configuration under administrator control.

The app does not silently create indexes, HEC tokens, roles, or network
listeners. An administrator must provide:

- an authorized HEC endpoint and token;
- a least-privilege search user or Splunk bearer token;
- allowed event/metric indexes;
- required collectors and Technology Add-ons for selected native sources.

Upgrade by installing a newer package through Splunk's supported app upgrade
flow after backing up `local/`. Uninstall by stopping the external engine,
removing the app through supported Splunk administration, and separately
retiring credentials. Indexed data is not deleted automatically.

## First-run Setup Wizard

Open **System → Connections** and select Docker, Splunk Enterprise, or the
Splunk Cloud architecture target. Enter HEC and management/search endpoints,
authentication type, allowed indexes, and available collectors.

Secrets are submitted in the request body, retained in engine memory, and never
returned or written to the metadata file. For durable operation, inject secrets
through the deployment environment or a platform secret manager. The wizard
requires both credentials to be re-entered whenever either Splunk endpoint or
the authentication method changes. Redirects from validation endpoints are
rejected. The standalone engine binds to loopback by default; place any
explicit remote deployment behind an authenticated administrative access
boundary.
The wizard
validates an authorized bounded HEC probe, authenticated search, and index
search access independently. It does not equate HEC acceptance with indexed
events and does not create missing Splunk resources.

Common recovery:

- `HTTP 401/403`: verify least-privilege credential and HEC-token permissions.
- TLS failure: install the issuing CA. Disable verification only for the
  documented loopback Docker lab.
- Index search denied: ask a Splunk administrator to grant search access; do not
  broaden permissions automatically.
- Collector degraded: open **Observe → Pipeline Health** and verify that exact
  protocol component before running.

## First security scenario

1. Open **Catalog → Security Sources** and choose an
   `IMPLEMENTED_AND_VALIDATED` source.
2. Review format, transport, sourcetype, provenance, and limitations.
3. Select **Generate bounded sample**, or open **Generate → Scenarios**.
4. Preview the trust boundary and expected evidence.
5. Run preflight. Resolve every blocked requirement.
6. Run the scenario.
7. Open **Observe Evidence** and refresh Splunk observation.
8. Confirm `SPLUNK_OBSERVED`; an acknowledgment alone is insufficient.
9. Run the attached investigation.
10. Open **Observe → Dashboard Studio**, retain the run ID, inspect
    NOC/Engineer/Evidence perspectives, and export the supported Dashboard
    Studio definition.

The four generation modes remain Scenario, Data Source, Sourcetype/Event Family,
and Single Event. Research-required, unsupported, and incomplete source
families fail closed.

The complete source-by-source matrix is in
`docs/SECURITY_SOURCE_COVERAGE.md`; its canonical machine-readable source is
`catalog/phase13_security_source_coverage.json`.

## Splunk Cloud architecture

Splunk Cloud is an architectural target, not a certified compatibility claim.
Run the NetSpout engine outside the search head in an owner-authorized network.
The deployment requires approved HEC ingress, an approved search API path,
least-privilege credentials, allowed indexes, and any required app-vetting
process. Arbitrary server-side execution is not assumed. No Splunk Cloud,
Splunkbase, or AppInspect approval is claimed until independently obtained.

## Security and privacy model

The default runtime is synthetic, deterministic, bounded, and offline. External
MCP/A2A endpoints, repositories, packages, and arbitrary commands remain
blocked. Credentials are not committed, placed in URLs, or returned to the
browser. The Docker lab's certificate-verification exception is limited to
loopback and is not suitable for production.

Samples may still require human IP and redistribution review. Automated
sanitization or scanning does not establish employer approval, legal clearance,
or vendor redistribution rights. See the Phase 13 report and release-blocker
register before publication.

## Troubleshooting and support bundle

Capture only secret-free output:

```bash
docker compose ps
curl -fsS http://127.0.0.1:8081/api/health/pipelines
python3 scripts/verify_sources.py
```

Do not attach `.env`, Splunk `local/`, browser network exports containing
authorization headers, or raw customer events. Phase evidence is written below
`.artifacts/phase13-current/`, which is intentionally excluded from Git.

## Developer and contributor workflow

Use Python 3.11–3.14 and a dedicated environment:

```bash
python3 -m venv .venv-phase13
.venv-phase13/bin/pip install -r backend/requirements-test.txt
PYTHONPATH=backend:src .venv-phase13/bin/python -m pytest -p no:cacheprovider
cd frontend && npm ci && npm run build && npm run lint
```

Build the app package with `python3 scripts/build_splunk_package.py`. Run
`python3 scripts/verify_sources.py` before committing generated mirrors. Never
commit `.env`, `local/`, credentials, customer data, or generated evidence.
