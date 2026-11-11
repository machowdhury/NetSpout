# NetSpout PulseForge 2.1.0 single-package Enterprise — support statement (nothing is published as a release)

Lists only what was actually tested. Details and limits: `PHASE17_VALIDATION_MATRIX.md`.

**Supported validation scope: Linux x86_64, Splunk Enterprise 10.6.1.1.** Tested natively (AWS m6i.2xlarge, Ubuntu 24.04, single instance, Docker-hosted Splunk, Python 3.13 embedded in Splunk) on the exact candidate `bdc4084`: install, restart, upgrade from the released v2.0.1 and uninstall through Splunk Web; generation of Cisco ASA, Cisco IOS, Fortinet FortiGate and Palo Alto events, IOS XR metrics, the Palo Alto threat-investigation scenario, bounded streaming, access control, credential persistence, crash/restart recovery, and zero idle telemetry; and a 3,600 s stream at 200 events/s (720,025 of 720,025 events independently indexed, none rejected, unknown or dropped; at most 201 events in any second). Evidence: `docs/verification/evidence/phase17/aws-native-x86_64/run2-bdc4084/`; provenance: `FINAL_CANDIDATE.md` and `RELEASE_REVIEW.md`.

**Splunk 10.2.7: compatibility tested on an earlier candidate (`91af353`) under amd64 emulation on an arm64 host only.** It was not re-run on the final candidate and never ran natively; it is not part of the supported scope.

**Behaviour you can rely on (as tested).** Nothing is generated on install, restart, upgrade or while idle. A run needs an authorized user and, outside the Docker lab, an explicit confirmation of the destination. The engine is started and supervised by Splunk and has no network port.

**Not tested or not supported.** Splunk Cloud (not supported; AppInspect Cloud checks fail); distributed deployments; Windows, macOS, aarch64 hosts; other Splunk versions (10.2.7 as above); Python 3.9; gNMI, SNMP, syslog and IPFIX wire listeners; rates above the 200 events/s cap (enforced); the earlier 124.5 events/s result (run 1) was superseded by the performance fix; browsers other than headless Chromium.

**Known limits.** AppInspect: 9 failures (8 shared with v2.0.1, plus x86_64-only binaries), so the package is self-distributed, not for Splunkbase. Saving credentials needs the admin role. A killed launcher is restarted by Splunk's next start or by Restart engine. Uninstall leaves `var/lib/netspout`. Known unit-test failures carried over from v2.0.1 (the same set locally on baseline and candidate). Follow-ups: `docs/contracts/phase17/FOLLOW_UPS.md`.
