# C4 network raw-event repairs

These synthetic structures follow the references below. They are not validated
against a selected TA parser, installed TA, CIM dataset or dashboard. Existing
sourcetypes/source values are retained, not newly certified. C1 profiles and
VENDOR_RAW_EVENT_FIDELITY.md remain the coverage contracts; no registry is added.

| Family | Evidence and bounded change | Limitations |
|---|---|---|
| Cisco IOS/IOS XE MAC movement | [Cisco MAC-flap reference](https://www.cisco.com/c/en/us/support/docs/ip/syslog/221140-troubleshoot-mac-address-flap-notificati.html): SW_MATM-4-MACFLAP_NOTIF, dotted MAC, native body; simulation attributes remain in LogEntry metadata. | Catalyst example, not all IOS/XE releases. Movement does not itself prove a loop. Invalid MACs now reject. |
| Junos MPLS | [Juniper MPLS system logs](https://www.juniper.net/documentation/us/en/software/junos/mpls/topics/concept/mpls-configuring-system-log-messages-and-snmp-traps-for-lsps.html): RPD_MPLS_LSP_CHANGE native primary(any) Route structure. Emit only the supplied primary hop, stripping legacy display label. | Documentation does not pin a release. No invented concatenation of old/new next hops into one route. Does not establish FRR enforcement, timing or full path. Existing backup metadata retained externally. |
| Arista EOS interface | [7100 management guide, June 2013](https://www.aristanetworks.com/docs/Manuals/QuickStart-Managing7100Series.pdf): Ebra LINEPROTO-5-UPDOWN down/up examples. Replace two unverified BGP/OSPF fixture records with this documented representative family. | Historical platform example, no all-release applicability. Existing generic forwarded-packet generator unchanged. |
| BIG-IP LTM monitors | [F5 K01054050](https://my.f5.com/manage/s/article/K01054050): mcpd 01070727:5 up / 01070638:5 down. Three representative monitor transitions replace mismatched monitor IDs and unverified connection record. | Candidate TA 2680/7.0.1 remains research metadata only. Connection generator is not converted to a monitor event; that would change its meaning. |

Fixtures retain counts, source, sourcetype and routing settings. Their replay
randomization remains unchanged: file order is illustrative, not a guaranteed
live lifecycle. Raw timestamps are synthetic fixed examples. No transports,
destinations, catalog identities or custom PulseForge contracts change.

## Deferred evidence gaps

- Nokia SR OS optical LOS/RSVP FRR formatter and SYSTEM/CHASSIS fixture IDs:
  exact authoritative event-ID/body/release linkage not established. General
  [22.10 event format](https://documentation.nokia.com/sr/22-10/books/log-events/about-log-events.html)
  is insufficient to certify these specific events. Unchanged.
- Cisco NX-OS queue-drop generator and existing routing/vPC fixtures need exact
  family-specific reference validation; interface examples cannot justify
  relabeling queue drops. Unchanged.
- F5 connection formatter and generic router forwarding messages require their
  own message-family evidence; monitor/interface references are not substitutes.
- One bounded PAN-OS documentation search did not establish a pinned traffic CSV
  field contract. PAN-OS raw samples and generator remain unchanged; positional
  repair remains blocked. No additional search was performed during recovery.
- Candidate integration versions for Junos, Arista and IOS/NX-OS are not selected
  by this repair. Existing catalog claims are not promoted. Structural tests are
  evidence level B only; no C/D/E parser, installed-app or consumer verification.
