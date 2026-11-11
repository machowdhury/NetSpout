# NetSpout PulseForge 2.1.0 (draft release notes, not published)

**What's new.** One `netspout.spl`, installed from Splunk Web, runs on Splunk Enterprise with no separate engine: Splunk starts and supervises the bundled engine (Unix socket, no port), enforces access with Splunk capabilities, and keeps the HEC token and search credential in its encrypted credential store. First-run setup is in the app. Streaming is capped at 200 events/s and 3,600 s. Non-lab destinations need an explicit authorization tick before data is sent.

**Upgrading from v2.0.1.** Install the new package with "Upgrade app". Your `local/` configuration is kept; the Engine URL setting is ignored. Tested on 10.6.1 and 10.2.7. The v2.0.1 release itself is unchanged.

**Tested on.** Splunk Enterprise 10.6.1.1 (primary) and 10.2.7, Linux x86_64 image under emulation on an arm64 host. See the support statement.

**Not supported.** Splunk Cloud, distributed Splunk, non-x86_64 or non-Linux hosts, native-hardware performance claims.

**Known issues.** 9 AppInspect failures (not Splunkbase-submittable); credential saving needs the admin role; uninstall leaves `var/lib/netspout`; sustained streaming measured 200.0 events/s for 3,600 s on native x86_64 Splunk 10.6.1.1 (720,025 of 720,025 indexed, none lost); the supported scope is Linux x86_64 on 10.6.1.1, and 10.2.7 was tested on an earlier candidate under emulation only.
