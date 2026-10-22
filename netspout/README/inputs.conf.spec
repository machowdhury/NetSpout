[netspout_streamer://<name>]
* NetSpout multi-vendor network telemetry and metrics streaming modular input

ecosystem_mode = <value>
* Ecosystem mode (pure_cisco or mixed_vendor)

scenario = <value>
* Active simulation scenario name

target_hec_url = <value>
* Splunk HEC URL destination endpoint

metric_index = <value>
* Splunk metric index (default: cisco_mdt_metrics)

event_index = <value>
* Splunk event index (default: idx_network_ops)

interval = <value>
* Polling and stream generation interval in seconds

[pulseforge_spool://native]
* App-owned bounded spool; disabled until the operator configures forwarding.
spool_mode = native
* Only the dedicated native spool is supported; arbitrary paths are not accepted.
_TCP_ROUTING = <existing-tcpout-group>
* Operator-selected existing group. PulseForge does not create outputs.conf.
