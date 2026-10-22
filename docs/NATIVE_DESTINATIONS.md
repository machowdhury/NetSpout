# NetSpout PulseForge — Named Destination Manager

The configuration view provides named destinations without replacing the existing
transport adapters, REST route, Splunk authorization, credential store or runtime
file. The registry is stored in `datablaster_config.json` beside legacy settings.
It is limited to 100 profiles and 256 KiB of registry JSON.

## Native REST operations

Use the existing `/services/datablaster/execute` handler with `netspout_admin`:

- `list_destinations`: lists profiles, non-secret settings/references, signals and
  `selected_id`. No token/community is returned.
- `create_destination`: `name`, `protocol`, `target_class`, optional `enabled`,
  `settings`, and optional explicit replacement `credential`. IDs are server UUIDs.
- `update_destination`: `destination_id` plus changed metadata/settings. Protocol
  is immutable. Omitted credentials preserve their references. A credential and
  explicit credential-reference update together are rejected.
- `disable_destination`: blocks selection, diagnostics and execution for that ID.
  Re-enable through an explicit update. No delete or automatic credential cleanup.
- `select_destination`: saves the default and corresponding flat settings atomically.
- `diagnose_destination`: one explicit collector request using existing adapters;
  forwarding performs read-only configuration readiness checks instead of sending.

Protocol names are `hec`, `syslog`, `otlp`, `snmp`, `forwarding`. Target classes
`local_splunk`, `remote_splunk`, `external_platform` are descriptive. They neither
relax nor tighten existing authorization, HEC allowlists, TLS or SNMP safety policy.
Compatible local and remote receivers are valid within those existing boundaries.

## Scenario routing and evidence

The native onboarding/console scenario selector sends only `destination_id`.
The server resolves its stored settings and credentials, validates the scenario's
signals, and records profile ID/name/protocol/class in native run history. Missing,
disabled or inconsistent selections fail closed. The Python runner receives a
private settings snapshot so later profile/selection edits cannot change that
run's HEC TLS or allowlist configuration. Browser credential/endpoint fields are
not used as execution configuration.

Named selection applies to Python scenario start/run_scenario paths. Existing
one-off HEC onboarding/sample operations retain their compatibility behavior and
do not silently turn into another protocol. External-binary correlation remains
unsupported. No universal acknowledgement or indexing semantics are introduced:
HEC ACCEPTED, OTLP acknowledgement/partial rejection, syslog local send, SNMP
local send/inform response, and forwarding publication/readiness remain distinct.

HEC supports log and metric templates; OTLP supports HTTP/JSON logs and generated
metric gauges; syslog supports logs; SNMP supports synthetic v2c trap/inform events;
forwarding supports log envelopes. Existing unsupported signals/transports remain
unsupported. Collector acceptance and local publication never establish indexing.

## Migration and compatibility

Before a registry exists, a read-only deterministic legacy view exposes the five
flat protocol profiles with stable IDs. Legacy defaults can still require initial
configuration/credentials; list visibility is not readiness evidence. First manager
mutation atomically persists that view plus the change. Existing fixed HEC entries
remain readable through legacy profiles; new HEC profiles require explicit versioned
credentials/references. Historical/staged credentials are never deleted automatically.

Legacy configuration actions remain supported. Writes to the active protocol update
its active profile. An explicit legacy protocol switch selects its stable legacy ID.
Disabling the active profile blocks runs until an explicit selection/re-enable action;
unrelated writes do not enable it. Separate inactive named profiles are retained.

Splunk-managed forwarding retains its dedicated operator-configured input and group.
A different group must be explicitly selected as default and configured by the
operator, with no pending spool files, before scenario use. Multiple profiles can
share that group and use different indexes. PulseForge never writes outputs.conf
or generates custom S2S packets. Existing envelope/vendor parsing and duplicate-on-
crash limitations continue to apply.

Offline tests use dummy credentials, mocked collectors and network denial. Installed
Splunk Web behavior and local/remote receiver integration require separate approval.
