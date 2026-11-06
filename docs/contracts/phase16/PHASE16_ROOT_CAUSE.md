# Phase 16 — root cause of B1 (idle app generates synthetic telemetry)

Defect (Phase 15): a freshly installed NetSpout wrote about 78 synthetic events a minute into `idx_network_ops` with no run started. Evidence for the unfixed build in this phase: **3,231 NetSpout-attributed events 30 minutes after install, one generator process alive** (`evidence/phase16/live_0_unfixed_idle_after_install.json`); the archived 2.0.0 package does the same (342 events within a few minutes of its install, `live_4_…`).

## Exact entry point

`netspout/bin/netspout_streamer.py`, a Splunk **modular input** (scheme `netspout_streamer://`, declared by `README/inputs.conf.spec` and by the script's own `--scheme` output with `<use_single_instance>true</use_single_instance>`). The app ships `default/inputs.conf` with `[netspout_streamer://default] disabled = 1`.

## Why Splunk runs it although the stanza is disabled

For a *single-instance* modular input, Splunk starts the script once at every Splunk (re)start and every configuration reload, independent of which stanzas are enabled; `disabled = 1` only keeps the stanza out of the XML it writes to the script's stdin. `splunkd.log` shows it directly:

```
ModularInputs - No stanzas found for scheme "netspout_streamer" in inputs.conf at script (re)start.
ExecProcessor - New scheduled exec process: .../netspout_streamer.py
```

## Why it then generated events with nothing enabled

The original `run_input()` waited 0.2 s for stdin, and `parse_input_config()` returned built-in defaults (`mixed_vendor`, `mixed_edge_breach`, `event_index = idx_network_ops`, `interval = 5`) for an empty or stanza-less document. The default configuration was therefore treated as authorization, and the script looped forever, writing `<event>` XML to stdout, which Splunk indexes directly (no HEC involved) with `source = netspout:streamer`.

## What is affected

| item | value |
|---|---|
| index | `idx_network_ops` (the default `event_index`); `cisco_mdt_metrics` is the default `metric_index` but no metric datapoints were observed |
| sourcetypes seen | `pan:traffic`, `pan:threat`, `cisco:ios:syslog`, `cisco:ise:syslog`, `cisco:duo:auth`, `arista:eos:syslog`, `fortinet:fortigate:utm`, `juniper:junos:syslog` |
| source | `netspout:streamer` |
| rate | about 78 events per minute idle (Phase 15); about 108 per minute when the input is explicitly enabled |
| versions | 2.0.0 and the pre-fix 2.0.1 (the file is unchanged between them); an upgrade does not stop it |

## All invocation paths checked

| path | finding |
|---|---|
| `netspout_streamer` modular input | **the cause** (above) |
| `pulseforge_spool` modular input | `use_single_instance=false`, so Splunk starts it only for an enabled stanza; none enabled, no process ever observed |
| `default/eventgen.conf` plus `samples/` (34 stanzas, 35 sample files) | **latent second path**: no stanza had `disabled`, so a Splunk that has the *Splunk Eventgen* app installed would generate into `idx_network_ops` every 15 s per sample. Not present in the lab images, so it was fixed (every stanza now `disabled = true`) and unit-tested, but **not exercised live** |
| persistent REST handlers (`netspout_rest_handler`, `datablaster_rest`, `netspout_gateway`) | answer requests only; the idle measurement after the fix (all indexes, 10 minutes, plus restarts) shows none emits |
| scheduled searches, `[script://]`, `[monitor://]`, TCP/UDP/HTTP inputs, `app.conf` triggers | none shipped |
| Setup wizard or setup scripts | none that start generation; PulseForge runs are started only by a user through the engine |

## Dead end worth recording

Switching the scheme to `use_single_instance=false` (so Splunk would not start the script without an enabled stanza) was tried first and is **wrong**: Splunk then refuses to initialize the input (`Endpoint argument "interval" is an internal argument that is handled specially within Splunk, and it should not be defined via introspection`), so an explicitly enabled legacy input could never start. The scheme is left as it was; the authorization check lives in the script. A first fix also wrote a notice to stderr, which `splunkd` logs at ERROR on every restart; it now exits silently.
