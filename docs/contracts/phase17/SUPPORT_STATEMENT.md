# NetSpout PulseForge 2.1.0 single-package Enterprise — support statement (DRAFT, for review; nothing is published)

Lists only what was actually tested. Details and limits: `PHASE17_VALIDATION_MATRIX.md`.

**Tested.** Splunk Enterprise **10.6.1.1** (primary) and **10.2.7** (compatibility), single instance, Docker, Linux x86_64 image **running under emulation on an arm64 host** (not native hardware). Python 3.13 embedded in Splunk. Install, upgrade from the released v2.0.1 and uninstall through Splunk Web; generation of Cisco ASA, Cisco IOS, Fortinet FortiGate and Palo Alto events, IOS XR metrics, the Palo Alto threat-investigation scenario, bounded streaming, access control, credential persistence, crash/restart recovery, and zero idle telemetry.

**Behaviour you can rely on (as tested).** Nothing is generated on install, restart, upgrade or while idle. A run needs an authorized user and, outside the Docker lab, an explicit confirmation of the destination. The engine is started and supervised by Splunk and has no network port.

**Not tested or not supported.** Splunk Cloud (not supported; AppInspect Cloud checks fail); distributed deployments; Windows, macOS, aarch64 hosts; other Splunk versions; Python 3.9; gNMI, SNMP, syslog and IPFIX wire listeners; the 200 events/s streaming ceiling (measured 124.5 events/s sustained for 3,600 s on native x86_64 m6i.2xlarge; supported rate is about 120 events/s per engine); browsers other than headless Chromium.

**Known limits.** AppInspect: 9 failures (8 shared with v2.0.1, plus x86_64-only binaries), so the package is self-distributed, not for Splunkbase. Saving credentials needs the admin role. A killed launcher is restarted by Splunk's next start or by Restart engine. Uninstall leaves `var/lib/netspout`. 9 known unit-test failures carried over from v2.0.1.
