# Cisco ASA and ISE raw-event repair (C2B)

This batch establishes vendor-source-backed synthetic structures, not TA parser
compatibility. Candidate validation targets are Splunk Add-on for Cisco ASA,
Splunkbase **1620 / 6.1.2**, and Splunk Add-on for Cisco Identity Services,
Splunkbase **1915 / 5.0.0**. Their selected-version parsing configurations have
not been validated here. No installed-TA, CIM or dashboard verification is claimed.

## Pinned format evidence

- ASA connection IDs **302013/302014** (TCP) and **302015/302016** (UDP):
  https://www.cisco.com/c/en/us/td/docs/security/asa/syslog/asa-syslog/syslog-messages-302003-to-342008.html
- ASA deny **106023** and command **111008**:
  https://www.cisco.com/c/en/us/td/docs/security/asa/syslog/asa-syslog/syslog-messages-101001-to-199021.html
- ASA **725001**, SSL handshake (not PING):
  https://www.cisco.com/c/en/us/td/docs/security/asa/syslog/b_syslog/syslogs-sev-level.html
- ASA **605005**, login permitted (not IPsec proxy host):
  https://www.cisco.com/c/en/us/td/docs/security/asa/syslog/asa-syslog/syslog-messages-602101-to-622102.html
- ISE remote/local header, comma-separated attributes and nested Response syntax:
  https://www.cisco.com/c/en/us/td/docs/security/ise/syslog/Cisco_ISE_Syslogs/m_IntrotoSyslogs.html
- ISE **5200** authentication success and **5400** authentication failure:
  https://www.cisco.com/c/en/us/td/docs/security/ise/syslog/Cisco_ISE_Syslogs/m_SyslogsList.html
- ISE TA sourcetype `cisco:ise:syslog`:
  https://splunk.github.io/splunk-add-on-for-cisco-identity-services/Sourcetypes/
- Candidate TA listings: https://splunkbase.splunk.com/app/1620 and
  https://splunkbase.splunk.com/app/1915

Cisco documentation is maintained independently of these TA releases. These
references pin message definitions, not tested TA extraction expressions or a
universal device-release contract. Optional identity/firewall features are not
modeled. The unrelated ASA VPN/failover/checksum records retained in the fixtures
are outside this batch's structural assertions and remain unverified.

## Changes and synthetic examples

ASA formatter used to emit `302013: Permit tcp src ... dst ...` with appended
PulseForge key/value fields. It now emits connection-build grammar:

```text
Oct 20 12:00:00 fw-lab-01 %ASA-6-302013: Built inbound TCP connection 42 for outside:198.51.100.20/52140 (198.51.100.20/52140) to inside:192.0.2.30/443 (192.0.2.30/443)
Oct 20 12:02:14 fw-lab-01 %ASA-6-302014: Teardown TCP connection 42 for outside:198.51.100.20/52140 to inside:192.0.2.30/443 duration 0:02:14 bytes 148920 TCP FINs
Oct 20 12:02:15 fw-lab-01 %ASA-4-106023: Deny tcp src outside:198.51.100.20/52140 dst inside:192.0.2.30/443 by access-group "OUTSIDE_IN" [0x0, 0x0]
```

The formatter models outside-to-inside inbound TCP/UDP. Identity translation is
explicit by default; optional mapped socket values allow NAT examples. An
explicit connection ID pairs a build and teardown; otherwise a deterministic
CRC32 of device/flow identity supplies a synthetic ID. This is not a live ASA
connection allocator and does not distinguish repeated concurrent identical
flows. Duration is rendered as H:MM:SS; TCP teardown uses the modeled FIN reason.
Non-TCP/UDP connection formats are rejected rather than mislabeled as TCP.

ISE previously always emitted a failed-authentication-style body, including for
success calls. It now selects the documented category, code and message class:

```text
<181>Oct 20 12:00:00 ise-lab-01 CISE_Passed_Authentications 0000000001 1 0 2026-10-20 12:00:00.125 +00:00 0000000001 5200 NOTICE Passed-Authentication: Authentication succeeded, User-Name=lab_user, Calling-Station-ID=02:00:00:00:00:01, Framed-IP-Address=192.0.2.30, NAS-IP-Address=192.0.2.20, Protocol=Radius, Response={RadiusPacketType=AccessAccept;}
```

Failure uses `CISE_Failed_Attempts`, `5400 NOTICE Failed-Attempt`,
`Authentication failed` and `AccessReject`. Explicit authentication status wins;
when omitted, blocked/dropped actions imply failure and other actions imply
success. Single-segment headers use `1 0`; sequence counters are bounded integers.
The formatter's default sequence is a synthetic placeholder; callers may supply
`sequence_num`. Existing custom sourcetype overrides and LogEntry metadata remain
available. PulseForge annotations are not appended to the vendor raw body.

The three existing ISE YAML phases retain their names: healthy baseline now
succeeds, degraded/failure reject authentication. Truncated nested Response
attributes were replaced with complete synthetic Responses. The bundled
`netspout/samples/cisco_ise_syslog.sample` was inspected but left unchanged: no
incomplete nested Response was found in its 5200/5400 authentication records.
Other captured event classes are not recast as authentication events.

## Bounded native token support

Only `cisco:asa`, legacy `cisco:asa:syslog`, and `cisco:ise:syslog` use the added
loader boundary. It renders `$TS$`, `$HOST$`, `$SYSLOG_TIMESTAMP$` and the required
ISE local timestamp `$ISE_TIMESTAMP$`. UTC is explicit, milliseconds are retained,
and tests supply a fixed clock. HOST uses the event's explicit host, not a new
weighted-choice engine. Remaining unsupported tokens fail the complete load;
partial records are not returned. Existing `$SYSLOG_TS$`, `$ISO_TS$` and
`$FLOW_ID$` remain for their existing downstream renderer. Other schemas retain
their token semantics.

The native loader materializes these new tokens when loading the fixture; it does
not implement a general token language or continuously refresh loaded timestamps.
YAML build/teardown records retain ordered definitions and disable fixture
randomization. Legacy Python streaming still randomly chooses loaded records;
this batch does not claim stateful build/teardown delivery ordering or live flow
lifetimes. The explicit formatter parameters and fixture assertions establish
native-field pairing, not receiver observation.

Canonical `cisco:asa` and `cisco:ise:syslog` are preserved. The legacy
`cisco:asa:syslog` alias is retained without claiming TA support. No catalog
coverage promotion or incident/transport/destination change occurs.

## Verification boundary

Focused checks cover synthetic message grammars, native-field correlation,
timestamps, Response balance, token rejection, metadata separation and mirrors.
These are evidence levels A/B only. C requires selected-version TA parser
configuration validation; D requires installed-TA tests; E requires independent
CIM/dashboard consumer checks. None is inferred from a passing generator test.

## Legacy compatibility and non-authentication CoA completion

`PASSED` is a legacy alias of `SUCCESS`, with identical successful-authentication
semantics. `CONTAINED` is deliberately rejected by the authentication formatter.
Only the campus rogue scenario's former CONTAINED call routes to the separate
`format_cisco_ise_coa_log` method; other authentication callers stay unchanged.

Authoritative source: Cisco ISE Syslogs, last modified 2026-08-12, printed pages
491-492 (PDF pages 493-494):
https://www.cisco.com/c/en/us/td/docs/security/ise/syslog/Cisco_ISE_Syslogs.pdf#page=493

Message **5205**, severity NOTICE, class **Dynamic-Authorization**, represents
successful dynamic authorization. It is listed in the Passed Authentications
logging category, but is not authentication code 5200. Cisco's lifecycle example
also distinguishes confirmed CoA from subsequent reauthentication:
https://www.cisco.com/c/en/us/support/docs/security/identity-services-engine/216330-ise-self-registered-guest-portal-configu.pdf

This is not merely a request-issued event. It does not independently establish
quarantine enforcement or data-plane isolation. The existing scenario containment
meaning remains a simulated state; action/status, run/phase/device correlation,
and original signature text remain, with an external signature qualification:
`SIMULATED CoA success; profile=...; quarantine enforcement unverified`.
No request, receiver or real enforcement is invoked. No AccessAccept/AccessReject
is invented for CoA; the raw body uses the documented dynamic-authorization text
and standard ISE user/endpoint attribute names. No PulseForge/profile annotations
are inserted into it. Selected-version TA extraction of 5205 remains unvalidated.

See [the platform-wide standard](VENDOR_RAW_EVENT_FIDELITY.md) for the evidence
chain and prioritized multivendor rollout. No profile coverage state is promoted.
