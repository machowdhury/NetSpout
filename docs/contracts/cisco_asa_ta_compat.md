# Compatibility contract: Cisco ASA (`cisco:asa`)

Status: **format VERIFIED against documented message templates; Splunk TA compatibility UNVERIFIED** (TA package not available in the lab).

| Item | Value | Evidence |
|---|---|---|
| Technology Add-on | Splunk Add-on for Cisco ASA, Splunkbase **1620** | `docs/reference/sourcetype_coverage.json` (`splunkbase_declared_by: ["1620"]`); Splunk docs "Integrated Enterprise Value for Cisco data" lists the add-on with source type `cisco:asa` |
| TA version | **Not recorded.** The package is not on disk and Splunkbase download needs a login | `docs/verification/pulseforge_ta_validation_matrix.md` row 1: `BLOCKED_PACKAGE` |
| Canonical sourcetype | `cisco:asa` | Splunk docs (above). `cisco:asa:syslog` is **not** listed there and is not declared by any TA; the product now refuses it (`NON_CANONICAL_SOURCETYPE`) |
| Raw format | BSD-style syslog line: `<Mon dd HH:MM:SS> <host> %ASA-<sev>-<id>: <message>` | Cisco Secure Firewall ASA syslog messages guide; templates in `tests/fixtures/cisco_asa/message_formats.json` |
| Messages generated | 302013/302015 Built outbound TCP/UDP connection; 302014/302016 Teardown (same connection id, `duration hh:mm:ss bytes N`, TCP reason); 106023 Deny by access-group | Cisco guide; Cisco ASA FAQ 116149 (build/teardown share the connection id) |
| Required HEC metadata | `sourcetype=cisco:asa`, `host` (firewall name), `index`, `time`, `event` = the raw line as a string. The product sets `source=network-topology-simulator`; the TA does not key on `source` (not verified from the TA) | `telemetry_dispatcher.py` HEC payload |
| Expected extractions | From the TA, **not verified**: `action`, `src`/`dest`, `src_port`/`dest_port`, `transport`, `bytes`, `duration`, `connection_id`-style fields, `vendor_product`. Listed as targets for the lab check, not as claims | TA `props.conf`/`transforms.conf` not read |
| Generator | `src/netspout_core/asa_generator.py` (`generate_asa_entries`) using `SplunkLogEngine.format_cisco_asa_log` (`log_engine.py`); wired in `generator_modes.py` (`_NATIVE`) for batch, single event and monitored run | tests below |
| Tests | `tests/test_cisco_asa_ta_contract.py` (8 tests): every event matches a documented template; teardown follows its build; outbound/inbound consistent; no YAML metadata or `$TOKEN$`; deterministic for a seed; preview equals what is dispatched; native path used; non-TA name refused | pytest |

## Splunk verification searches (NOT RUN: needs the lab credentials and the TA)
```
index=<idx> sourcetype=cisco:asa netspout_run_id=<run> | stats count by sourcetype
index=<idx> sourcetype=cisco:asa netspout_run_id=<run> | rex "%ASA-\d-(?<msgid>\d{6})" | stats count by msgid
index=<idx> sourcetype=cisco:asa netspout_run_id=<run> | table _time host action src dest src_port dest_port transport bytes duration   # empty columns = TA not installed or extraction differs
| rest /services/apps/local | search title="Splunk_TA_cisco-asa" | table title version
```

## What is not claimed
No TA field extraction, CIM mapping or TA-version compatibility is claimed. The lab Splunk has no Cisco ASA add-on installed.
