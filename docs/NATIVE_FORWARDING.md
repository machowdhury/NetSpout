# NetSpout PulseForge — Splunk-managed forwarding

PulseForge does not implement Splunk-to-Splunk packets. Its Python scenario runner
atomically publishes JSON envelopes into the private
`$SPLUNK_HOME/var/run/netspout/forwarding` spool. Splunk launches the app's
`pulseforge_spool` modular input, which emits supported streaming XML into Splunk's
input pipeline. Splunk owns subsequent routing, queues, TLS and S2S communication.

## Operator setup

1. Arrange an authorized, existing `tcpout` group and receiving event index through
   your normal Splunk administration process. PulseForge never creates or changes
   customer output groups or system `outputs.conf`.
2. In native configuration, save that group and event index. Select forwarding for
   future scenarios. Configuration save does not activate a Splunk input.
3. Enable only the dedicated input in `netspout/local/inputs.conf`:

   ```ini
   [pulseforge_spool://native]
   disabled = 0
   _TCP_ROUTING = your_existing_group
   ```

   Apply this through your supported Splunk configuration lifecycle. Existing inputs
   and forwarding groups remain operator-owned. Check the actual installed app's
   effective routing before running synthetic traffic.
4. Use Check readiness. It reads selected effective `inputs` and `outputs` stanzas
   with bounded `splunk btool` commands. READY confirms an enabled input with matching
   routing and a configured enabled group, not network connectivity, queue health,
   existence of the receiving index, ingestion or downstream forwarding.
5. Launch a log scenario at 10 EPS. Metrics are rejected. Independently inspect
   indexed events using the recorded index/time and `| spath` correlation fields;
   no native forwarding verification or downstream acknowledgement is claimed.

## Data and evidence

XML preserves generation timestamp, host, source, sourcetype and the selected event
index. Data is a JSON envelope with `original_event`, `netspout_run_id`,
`netspout_scenario_id`, `netspout_device_id` and `netspout_phase=BASELINE`.
Original text remains inside the envelope; this is not original vendor raw-wire
format. Vendor TAs may require explicit mappings. No `props.conf` changes impose
new parsing rules on customer sourcetypes.

Published counts prove atomic local publication only. Pipe handoff receipts are
internal cleanup markers, not ingestion or forwarding acknowledgement. Public
accepted/indexed/forwarded counts remain unavailable. Crashing after stdout flush
but before recording a receipt can cause duplicate delivery on later input runs.
Do not interpret a successful process exit as proof of downstream delivery.

## Bounds and cleanup

At most 100 pending files, 64 KiB/event and 10 MiB total. Storage pressure stops new
publication; unread events never expire automatically. Orphaned staging files count
against limits and require operator investigation rather than automatic deletion.
Only successfully flushed files with private receipts are removed. Receipts retain
no payload, are capped at 100, and expire after 24 hours during spool operations.
Group changes are rejected while pending files exist. Stop producers and drain the
spool before reconfiguring routing. Avoid manual routing changes while files are
pending. Receiver/index reconfiguration and stale/orphan cleanup are operator tasks.

Offline tests use mocked Splunk configuration, pipes and filesystem failures.
Installed-app recognition, queue behavior, vendor parsing and real forwarding need
separately approved integration validation.
