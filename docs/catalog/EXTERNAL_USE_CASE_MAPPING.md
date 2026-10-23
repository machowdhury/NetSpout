# External use-case mapping and next scenario batch

C4 checkpoint: `5065073f90fa522675d67a5054fd1f5d41de3d2b` (8 files).
Review date: 2026-10-22. Planning only; no new scenarios implemented here.

## Attribution, scope and evidence limits

Reference: [fenre/splunk-monitoring-use-cases](https://github.com/fenre/splunk-monitoring-use-cases),
by Fredrik Lima Sudmann and contributors. [MIT license](https://github.com/fenre/splunk-monitoring-use-cases/blob/main/LICENSE),
copyright 2026 Fredrik Lima Sudmann. Preserve its copyright/permission notice if
substantial source content is reused later. This document records short IDs,
objectives and our own implementation analysis; it copies no SPL or runbooks.

Read the [category metadata](https://github.com/fenre/splunk-monitoring-use-cases/blob/main/content/INDEX.md)
and 36 selected per-use-case JSON records (linked below), not the full catalog.
The dashboard could not be loaded through the web tool; selected JSON was read
directly. Upstream main is mutable and was not pinned to a commit. Titles below
come from per-UC JSON: industry quick-start titles disagree with those records
(e.g. 21.1.1, 21.2.1, 21.3.1). Do not use the quick-start title as schema evidence.
Upstream TA IDs, sourcetypes and CIM claims are discovery hints, not authority:
several records associate generic UF/617 or Cisco Security/1352 with unrelated
collection paths. None are imported into PulseForge catalogs or promoted.
No SOAR/Phantom cases, dependencies, actions or workflows are selected.

E = already executable at incident-objective level using owned PulseForge schemas;
P = partial assets, missing correlated scenario/schema work; M = missing scoped
telemetry/scenario; B = vendor-native implementation blocked on exact format
reference. E never means selected TA compatibility. P may also have native-format
gates listed explicitly. Priorities P1/P2 are proposed product sequence, not
security severities. All rows require selected-version parser and field tests
before any integration_verified claim. No installed-TA/CIM/dashboard verification
was performed. Missing fields remain unknown in C1 profiles.

## Existing assets and integration expectations

- N01–N15: `netspout/bin/network_incidents.py`, descriptors
  `netspout/appserver/static/scenarios/scenario_network_*.yml`; 15 finite packs.
- T01–T10: `netspout/bin/telecom_incidents.py`, `scenario_telco_*.yml`; 10 finite packs.
  Both use custom `netspout:*` telemetry, not native equipment contracts.
- Named samples below resolve to `netspout/appserver/static/samples/NAME/NAME.yml`.
- Named formatter functions reside in `src/netspout_core/log_engine.py`;
  existing correlated legacy paths in `src/netspout_core/scenario_runner.py`.
- C4 fixtures and C2B/C3B repaired functions have structural test evidence only.
  Generic SNMP encoding does not establish a vendor MIB or polling implementation.
- TA codes below are candidate targets, versions to select in existing
  `catalog/telemetry_catalog.json` integration profiles, not a new registry:
  NET = per-product Cisco/Juniper/Arista TA/SC4S; ISE = 1915/5.0.0;
  FW = ASA 1620/6.1.2, Fortinet 2846/1.6.10, Check Point 4293/1.1.6;
  F5 = 2680/7.0.1 (all candidate versions, not parser validated).
  WEB = selected NGINX/Apache/IIS extraction contract; DB = DB Connect or
  per-engine file/API extraction; AWS = Splunk_TA_aws; AZURE = Microsoft cloud
  collection; WINDOWS = Windows TA; OKTA = selected Okta add-on;
  K8S = selected OTel/Kubernetes collection; KAFKA = selected JMX/offset input;
  VMWARE = selected vCenter/VMware add-on; STORAGE = array-specific TA;
  ACI/UCS = product-specific add-ons, keeping API and syslog contracts separate;
  OT/POWER = chosen vendor/Edge Hub/SNMP extraction contract; TELCO/CUSTOM =
  no universal native TA. These last targets require an owned schema or a
  separately evidenced vendor profile. HEC/UF alone supplies no extraction schema.
- CIM values in the matrix are upstream claims unless explicitly proposed;
  `none` means no model established, not a guarantee that none applies.

## Candidate matrix (36)

| UC source / title | Domain / industry | Objective | Products / event families | Existing PulseForge asset | Missing authentic contract | TA / CIM expectation | Coverage / priority | Deterministic behavior and KPI |
|---|---|---|---|---|---|---|---|---|
| [UC-5.1.1](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-05-network-infrastructure/UC-5.1.1.json) — Interface Up/Down Events | Network / all industries | Correlate uplink transitions with user outage | Cisco/Arista interface syslog; service probes | N01; C4 Arista/MAC fixtures | Junos link-state grammar; full IOS release/parser selection | NET / none | E / P1 | Seed fixed flaps, then stable up; count transitions and outage seconds |
| [UC-5.1.4](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-05-network-infrastructure/UC-5.1.4.json) — BGP Peer State Changes | Routing / telecom, finance | Bound route withdrawal impact | BGP neighbor and prefix events, flow/probe KPIs | N06; IOS XR BGP formatter | Per-release BGP native grammar/parser | NET / none | E / P1 | Peer flaps then withdraws; prefix deficit and reconvergence time |
| [UC-5.1.5](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-05-network-infrastructure/UC-5.1.5.json) — OSPF Neighbor Adjacency | Routing / enterprise | Measure adjacency loss and convergence | OSPF adjacency; interface events | N07 | Native OSPF message IDs per vendor | NET / none | E / P1 | Neighbor FULL to DOWN to FULL; impacted clients and recovery time |
| [UC-5.1.11](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-05-network-infrastructure/UC-5.1.11.json) — Power Supply / Fan Failures | Hardware / DC, retail | Detect redundancy loss before service outage | PSU/fan alarms and sensor KPIs | N15; generic SNMP helpers | Exact PSU MIB/OIDs and device message references | NET / none | B / P2 | One PSU fails, load rises, replacement restores redundancy |
| [UC-5.2.2](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-05-network-infrastructure/UC-5.2.2.json) — Policy Change Audit | Security / finance, retail | Link policy change to blocked transactions | Firewall config audit plus allow/deny sessions | N08; ASA and Check Point fixtures | Authenticated config-audit schemas not covered by connection fixtures | FW / Change proposed, upstream empty | P / P1 | Bad rule causes denies; rollback restores transaction success |
| [UC-3.2.7](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-03-containers-orchestration/UC-3.2.7.json) — Kubernetes Control Plane Health (apiserver, etcd, scheduler, controller-manager) | Kubernetes / cloud, digital services | Detect control-plane loss before app outage | apiserver/etcd/scheduler metrics; audit JSON | kube-events, kube-object-pods samples | Versioned control-plane metric names and audit schema | K8S / Application_State, Performance claimed upstream | P / P2 | etcd latency rises, API errors follow; restore quorum |
| [UC-3.2.1](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-03-containers-orchestration/UC-3.2.1.json) — Kubernetes Pod Container Restart Churn and Rolling Restart-Rate Anomalies | Kubernetes / all digital services | Correlate restarts with service errors | Kubernetes events, pod objects, restart counters | kube-events, kube-object-pods, container samples | kube-state-metrics version and UID/counter reset contract | K8S / Application_State, Performance claimed upstream | P / P1 | OOM loop, backoff, rollout recovery; restart delta and unavailable replicas |
| [UC-4.1.7](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-04-cloud-infrastructure/UC-4.1.7.json) — S3 Bucket Policy Changes | Cloud security / finance, healthcare | Detect public exposure caused by policy drift | AWS CloudTrail policy-change JSON | Shared runner/OTLP only; no scoped AWS raw proof | Release/API CloudTrail record; validated AWS TA mapping | AWS / Change claimed upstream | M / P2 | Policy opens bucket, access increases, synthetic rollback closes it |
| [UC-4.1.8](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-04-cloud-infrastructure/UC-4.1.8.json) — GuardDuty Finding Ingestion | Cloud security / all industries | Correlate finding with affected workload | GuardDuty findings and CloudTrail/VPC context | Shared transport only | Finding schema/version and collector-specific sourcetype | AWS / Intrusion_Detection, Alerts claimed upstream | M / P2 | Synthetic finding progresses, affected host isolated in model only |
| [UC-4.2.9](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-04-cloud-infrastructure/UC-4.2.9.json) — Defender for Cloud Alerts | Cloud security / enterprise | Track cloud alert impact | Defender alert/API JSON and resource inventory | Shared transport only | Microsoft API/export contract; collector-specific fields | AZURE / none | M / P2 | Alert on one resource, correlate app errors, modeled recovery |
| [UC-7.1.2](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-07-database-data-platforms/UC-7.1.2.json) — Deadlock Monitoring | Database / banking, retail | Explain transaction failure from lock contention | PostgreSQL/SQL Server lock/deadlock events | format_postgres_db_log | Native deadlock grammar, SQL Server graph schema; current KV trail not certified | DB / none | B / P1 | Two transactions deadlock; victim aborts; retries restore throughput |
| [UC-7.1.3](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-07-database-data-platforms/UC-7.1.3.json) — Connection Pool Exhaustion | Database / retail, healthcare | Detect saturated application connections | Pool gauges, DB sessions, HTTP errors | Postgres and NGINX formatters; F5 fixtures | Versioned pool/DB metrics; NGINX/Postgres raw repairs | DB+WEB / none | P / P1 | Pool reaches capacity, requests queue, release restores service |
| [UC-8.1.1](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-08-application-infrastructure/UC-8.1.1.json) — HTTP Error Rate Monitoring | Application / retail, finance | Correlate HTTP errors with backend health | NGINX/Apache/IIS access logs; F5 monitors | format_nginx_web_log; C4 F5 fixtures | Combined log versus custom nginx:plus:kv contract; no native TA claim | WEB+F5 / Web claimed upstream | P / P1 | One pool member fails, 503s rise, member recovery reduces errors |
| [UC-8.1.5](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-08-application-infrastructure/UC-8.1.5.json) — SSL Certificate Monitoring | Application / healthcare, finance | Detect certificate expiry impact | Certificate inventory/probe results; TLS errors | Generic service simulation; no validated certificate producer | Selected TLS/probe contract; no generic UF schema | WEB / none | M / P2 | Days-to-expiry falls to zero; modeled renew restores handshake success |
| [UC-8.3.1](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-08-application-infrastructure/UC-8.3.1.json) — Consumer Lag Monitoring | Streaming / telecom, finance | Detect delayed event processing | Kafka offsets/JMX, producer rates | kube-container samples only, no Kafka lag producer | Kafka/JMX/Burrow version and offset semantics | KAFKA / none | M / P2 | Consumer stalls; offset gap and oldest-event age rise then drain |
| [UC-9.1.3](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-09-identity-access-management/UC-9.1.3.json) — Privileged Group Membership Changes | Identity / all industries | Correlate privileged membership with access | Windows 4728/4732/4756 XML/events | Shared runner; no inspected Windows raw fixture | Windows event version/XML and member identity fields | WINDOWS / Change claimed upstream | M / P2 | Member added then accesses restricted service; modeled removal |
| [UC-9.3.5](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-09-identity-access-management/UC-9.3.5.json) — IdP Availability Monitoring | Identity / healthcare, workforce | Detect IdP outage across relying services | Okta System Log/status API and auth probes | ISE auth formatter as adjacent asset only | Okta API/version; ISE cannot impersonate Okta schema | OKTA / none | M / P2 | SSO latency then failures; recover IdP and compare auth success ratio |
| [UC-17.1.2](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-17-network-security-zero-trust/UC-17.1.2.json) — Endpoint Posture Failures | NAC / campus, healthcare | Measure posture failures and service impact | ISE posture, auth, CoA lifecycle; client reachability | ISE auth/CoA; legacy scenario_runner FAILOVER | Posture event grammar and enforcement evidence; CoA is not enforcement | ISE / none | P / P1 | Auth success then posture failure; simulate restricted access externally |
| [UC-17.1.8](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-17-network-security-zero-trust/UC-17.1.8.json) — NAC Policy Change Audit | NAC / finance, campus | Explain authentication failures after policy edit | ISE admin audit plus RADIUS success/failure | ISE YAML and auth formatter | Admin policy-audit record schema and causal policy ID | ISE / Change claimed upstream | P / P1 | Policy change increases auth failure ratio; modeled rollback restores baseline |
| [UC-14.2.1](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-14-iot-operational-technology-ot/UC-14.2.1.json) — PLC/RTU Health Monitoring | OT / manufacturing, utilities | Detect controller health loss | OPC-UA/Modbus values and controller alarms | Generic metric envelope only | Selected controller/register map and quality flags; no new protocol implied | OT / none | B / P2 | CPU/scan time rises, watchdog alarms; simulated reset restores cycle |
| [UC-14.2.2](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-14-iot-operational-technology-ot/UC-14.2.2.json) — Process Variable Anomalies | OT / energy, manufacturing | Detect process drift before downtime | Historian/OPC-UA tags and quality | Generic gauge generation only | Vendor tag export schema, engineering units and quality semantics | OT / none | B / P2 | Temperature ramps out of bounds; modeled correction returns to band |
| [UC-15.1.1](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-15-data-center-physical-infrastructure/UC-15.1.1.json) — UPS Battery Health | DC physical / all industries | Detect loss of battery autonomy | UPS-MIB polls, battery state and runtime | SNMP wire engine only; not UPS data model | Exact OIDs, units, polling/export schema; traps are not polling | POWER / none | B / P2 | Charge/runtime drop under load; restore mains and recharge |
| [UC-15.2.1](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-15-data-center-physical-infrastructure/UC-15.2.1.json) — Temperature Monitoring per Zone | DC physical / telecom, AI | Correlate hot zone with workload impact | Environmental sensors; cooling alarms | Generic gauges; N15 resource incident | Sensor vendor schema/OIDs, zone and units contract | POWER / none | P / P2 | Cooling loss raises temperature before modeled throttling |
| [UC-21.1.1](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-21-industry-verticals/UC-21.1.1.json) — SCADA Alarm Rate Monitoring and Alarm Flooding Detection | Energy / utilities | Detect alarm flood and operator overload | SCADA alarms with priority, shelving, asset | Runner only; not authentic SCADA fixture | Vendor historian/alarm export contract | OT / none | B / P2 | One feeder fault produces bounded cascade; rate and unique asset KPIs |
| [UC-21.2.1](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-21-industry-verticals/UC-21.2.1.json) — Overall Equipment Effectiveness (OEE) Calculation | Manufacturing | Quantify production availability and yield loss | MES production counters and downtime | Runner metric envelopes only | MES vendor contract, count reset and unit rules | OT / none | M / P2 | Line stops, scrap rises, restarts; compute availability/performance/quality separately |
| [UC-21.3.1](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-21-industry-verticals/UC-21.3.1.json) — EHR System Response Time Monitoring | Healthcare | Link EHR latency to clinical workflow delay | EHR transaction latency; DB/pool/network context | WAN incident; Postgres/NGINX adjacent generators | EHR vendor schema and synthetic non-PHI transaction contract | CUSTOM / none | B / P2 | DB saturation delays synthetic patient-free requests; p95 and timeout ratio |
| [UC-21.4.1](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-21-industry-verticals/UC-21.4.1.json) — Fleet Vehicle GPS Tracking and Geofence Alerting | Transport / logistics | Detect location loss/geofence breach | Synthetic GPS positions and heartbeat | Runner only | Telematics vendor schema; coordinates synthetic, no real location data | CUSTOM / none | M / P2 | Vehicle heartbeat gap followed by geofence transition; missing interval KPI |
| [UC-21.10.1](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-21-industry-verticals/UC-21.10.1.json) — Claims Processing Cycle Time Monitoring | Insurance | Measure claims processing delay | Claims lifecycle and queue timing | Runner only | Selected application lifecycle contract; synthetic claim IDs | CUSTOM / none | M / P2 | Queue backlog delays settlement; cycle-time and SLA-breach ratio |
| [UC-2.1.7](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-02-virtualization/UC-2.1.7.json) — vSphere HA Host Failure and VM Restart Events | Virtualization / enterprise DC | Explain VM restart and app downtime | vCenter HA events, ESXi host state | vmware-esx-perf sample | vCenter event XML/API version; perf sample does not prove HA event grammar | VMWARE / none | P / P2 | Host fails, VM restart lag, service returns; recovery duration |
| [UC-6.1.2](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-06-storage-backup/UC-6.1.2.json) — Storage Latency Monitoring | Storage / finance, healthcare | Explain I/O latency impact on apps | Array latency/IOPS/queue metrics | Generic metric generation only | Selected NetApp/array API and unit/counter contract | STORAGE / none | M / P2 | Queue depth rises before DB waits; drain after simulated failover |
| [UC-18.1.2](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-18-data-center-fabric-sdn/UC-18.1.2.json) — Cisco ACI Fault Trending by Severity, Type, Lifecycle State, and Acknowledgement Workflow | Fabric / DC | Correlate APIC faults with service impact | ACI faultInst/faultRecord lifecycle; audit | cisco-dc-aci-events/health samples; ACI formatter | Actual APIC schema/version and fault lifecycle; custom health JSON not proof | ACI / Alerts, Inventory claimed upstream | P / P2 | Leaf fault raised/retained/cleared; affected endpoints and duration |
| [UC-19.1.1](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-19-compute-infrastructure-hci-converged/UC-19.1.1.json) — Blade/Rack Server Health (Cisco UCS) | Compute / DC, AI | Detect blade health failures | UCS faultInst XML/API; Intersight inventory | cisco-intersight-alarms/compute samples | UCS versus Intersight collection/source distinction; field extraction tests | UCS / none | P / P2 | Blade fault affects attached services; modeled recovery clears health |
| [UC-21.8.1](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-21-industry-verticals/UC-21.8.1.json) — RAN Cell Site Availability | Telecom / mobile | Measure cell availability and cohort impact | RAN state/KPIs, transport and user-plane probes | T01 RAN; T05 transport | Vendor EMS export contract absent; custom telco schema remains custom | TELCO / none | E / P1 | Cell degrades then recovers; availability and affected synthetic cohort |
| [UC-21.8.2](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-21-industry-verticals/UC-21.8.2.json) — Core Network Element Health (MME, SGW, PGW) | Telecom / core | Detect core element saturation | EPC/5GC health, sessions and alarms | T09 user plane; T02 registration | Native MME/SGW/PGW/5GC vendor schema absent | TELCO / none | P / P2 | Core saturation increases session failures; recover resource capacity |
| [UC-21.8.3](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-21-industry-verticals/UC-21.8.3.json) — Subscriber Provisioning Workflow Completion Rate | Telecom / OSS-BSS | Detect provisioning workflow failures | Synthetic provisioning step/status/duration | T02 auth adjacent only; no provisioning lifecycle | OSS/BSS native contract; use synthetic cohort ID, not MSISDN | TELCO / none | M / P2 | One workflow step stalls; completion ratio and latency recover |
| [UC-21.11.1](https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/main/content/cat-21-industry-verticals/UC-21.11.1.json) — Consumer credit card transaction monitoring | Finance / banking | Explain card transaction failures | Synthetic authorization events plus network/backend health | ASA/F5 fixtures; N08 impact model | Processor/card transaction schema; no real PAN/account data | CUSTOM / none | M / P1 | Policy denies payment path; declines rise; synthetic rollback restores approvals |

## Recommended next batch: 12 NEW cross-vendor incident compositions

These are proposals, not aliases for existing N/T packs. The new work is explicit
causal joins across entities, native fixture streams and modeled service impact.
Use one run/incident ID in external metadata, native endpoint/connection IDs where
available, and an owned `netspout:*` KPI stream. Do not append correlation fields
to vendor bodies or label the KPI stream with a vendor sourcetype. Fixture replay
must schedule transitions explicitly rather than inherit randomized sample order.

Readiness: **R** = bounded implementation can begin using structurally tested
assets plus custom KPIs, without claiming native parser compatibility;
**G** = a specific additional native schema must be established first. All need
new deterministic scenario tests. R does not mean integration_verified.

| Order / new scenario | Source objectives | Reused native assets / vendors | New causal sequence and measurable acceptance | Readiness / guardrail |
|---|---|---|---|---|
| 1. Retail branch uplink flap and checkout interruption | 5.1.1, 21.11.1 | C4 Arista interface fixtures; C2B ASA connections | Arista down precedes ASA session loss and owned checkout failures; up precedes new builds; assert outage duration and success ratio | R; payments are custom synthetic records, not a processor export |
| 2. Hospital access MAC instability and login retries | 5.1.1, 17.1.2 | Cisco MAC-flap + ISE auth | Fixed MAC alternates two ports; auth retries rise; stable port ends churn; assert flap count and auth success ratio | R; no invented posture verdict and no PHI |
| 3. Campus authentication retry storm at perimeter | 17.1.2, 9.3.5 | ISE success/failure + ASA build/teardown | Seeded client cohort retries; auth failures correlate to short-lived sessions; recovery restores session duration | R; model ISE service impact, not Okta-native availability |
| 4. Simulated NAC containment request and service-access change | 17.1.2 | Existing ISE CoA path + ASA deny | Known CoA lifecycle message, followed by separately labeled modeled policy/access effects; compare request time to synthetic reachability change | R; never infer enforced quarantine or CoA acknowledgement from request emission |
| 5. Perimeter deny burst and payment availability loss | 5.2.2, 21.11.1 | ASA deny + Check Point CEF | Two firewall observation points share native endpoint tuple; a modeled policy change increases denies; rollback restores synthetic approvals | R; config-change event is owned simulation, not fabricated vendor audit |
| 6. IPS attack burst and legitimate-session degradation | 5.2.2, 8.1.1 | Repaired Fortinet IPS + ASA sessions | Attack event rate rises while modeled legitimate-session success drops; filter intervention reduces attack observations and recovers service | R; no real attack, no invented Fortinet mitigation acknowledgement |
| 7. Multi-firewall path-policy disagreement | 5.2.2 | ASA build/deny + Check Point CEF | Upstream permit coexists with downstream deny for same flow; resolve modeled mismatch; assert conflicting-flow count and end-to-end success | R; correct source/destination mappings, not arbitrary timestamp joins |
| 8. Distribution-link loss and backend monitor failure | 5.1.1, 8.1.1 | Arista interface + F5 monitor up/down | Down on modeled backend path precedes monitor down; up and monitor recovery precede owned service recovery; assert causal delay and affected member count | R; local syslog send does not confirm receiver or indexing |
| 9. Partial load-balancer pool outage with perimeter demand | 8.1.1 | F5 monitor fixtures + ASA builds | One of two modeled members goes down under fixed offered load; remaining capacity increases modeled errors; restore member; assert healthy fraction and error rate | R; traffic/HTTP KPIs are custom; do not reuse uncertified F5 connection formatter |
| 10. Primary MPLS path-change observation and branch SLA recovery | 5.1.4, 21.8.2 | Junos LSP-change + Arista interface | Seed route-change observation and independent modeled branch latency; recovery sequence ties to declared topology; assert SLA breach duration | R; do not assert Junos event proves FRR enforcement or full path |
| 11. Planned maintenance versus unplanned service outage | 5.1.1, 8.1.1 | Arista transitions + F5 monitor fixtures | Two deterministic variants have same transitions but distinct owned maintenance scope; only unplanned impact contributes incident KPI | R; maintenance markers external to vendor raw; test negative controls |
| 12. Authentication recovery with stale perimeter sessions | 17.1.8, 5.2.2 | ISE auth + ASA correlated build/teardown | Auth success resumes before old sessions are removed; teardown/build native IDs track recovery; assert auth versus service recovery lag separately | R; policy edit remains modeled until ISE admin-audit grammar is evidenced |

Implement first in a small runner extension reusing
`netspout/bin/network_incidents.py`, existing descriptors/manifest and native
selector. Resolve Destination Manager's immutable server snapshot unchanged.
Likely files: that producer, 12 bounded descriptors under
`netspout/appserver/static/scenarios/`, `scenarios_manifest.json`, existing
`netspout/default/data/ui/views/datablaster_console.xml`, and a focused scenario
test module. Change canonical `log_engine.py` only if reuse requires a proven,
evidence-backed formatting correction; sync generated copies through the existing
script. Do not add routing, transport or credential machinery. Record reviewed
native-format evidence in existing C1 profiles only when prerequisites are met.

Acceptance for each new incident: identical seed/start/run produces identical
ordered output; fixed event/duration caps; stable site/device/endpoint identities;
explicit failure, impact and recovery; assert causal ordering and KPI arithmetic;
unchanged vendor body/sourcetype; separate custom KPIs; unrelated-flow negative
control; fail-closed missing/disabled destination; one immutable destination ID in
subprocess and history. Test existing log-only versus metric-capable behavior.
Use mocked transport boundaries. No live integration claims from these tests.

## Later waves and explicit unknowns

1. **Native app/database and Kubernetes wave:** repair the existing NGINX custom
   suffix and PostgreSQL native-format ambiguity under separate approval; then
   compose pool exhaustion, deadlocks and pod restart incidents using versioned
   schemas. This unlocks more credible healthcare/retail latency scenarios than
   inventing EHR raw events.
2. **Cloud/identity wave:** CloudTrail, GuardDuty, Defender, Windows and Okta need
   selected API/event versions, authentic fixtures and field-level TA validation.
   External sourcetype strings in this matrix are not automatically canonical.
3. **OT/industry wave:** select a concrete historian/MES/EHR/UPS contract before
   vendor-native output. Owned, clearly labeled simulations can model OEE, alarm
   floods, claims or card workflows without claiming vendor compatibility.
4. **Telecom wave:** existing ten custom service-assurance incidents already cover
   RAN, core and cross-layer modeled KPIs. New provisioning workflow needs its own
   synthetic schema first; use synthetic cohort identifiers instead of copying
   the external MSISDN requirement. Native EMS/OSS exports remain vendor-specific.
5. **AI/GPU extension:** no external GPU UC ID was established in this bounded
   selection, and inspected PulseForge assets do not establish a GPU-native
   generator. Proposed future cooling-to-throttling-to-job-delay correlation can
   reuse DC/compute/Kubernetes concepts (15.2.1, 19.1.1, 3.2.1), but needs a selected
   NVIDIA DCGM or AMD metric contract, units, labels and job telemetry evidence.
   Do not present generic CPU gauges as GPU metrics or claim native GPU support.

No source catalog was bulk-downloaded, no external SPL copied, no apps installed,
and no scenarios, transports or integrations were implemented by this planning
review. External content's own quality labels do not replace PulseForge's fidelity
standard or selected-version TA/installed-app/CIM evidence gates.
