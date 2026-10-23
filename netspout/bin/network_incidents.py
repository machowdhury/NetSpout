"""Seeded, finite network incidents for the existing native runner/adapters.

Synthetic vendor-style messages, not device firmware emulation. No destinations
or credentials live in this pack. Event time follows the paced execution clock.
"""
import json
import math
import random
import time
import uuid
from pathlib import Path
import telecom_incidents

SITE = 'campus-east'
DEVICES = {
    'core01': ('10.20.0.11', 'core_switch', 'TenGigabitEthernet1/0/1'),
    'core02': ('10.20.0.12', 'core_switch', 'TenGigabitEthernet1/0/1'),
    'dist01': ('10.20.0.21', 'distribution_switch', 'TenGigabitEthernet1/1/1'),
    'access01': ('10.20.0.31', 'access_switch', 'GigabitEthernet1/0/24'),
    'edge01': ('10.20.0.1', 'firewall_router', 'GigabitEthernet0/0'),
    'dns01': ('10.20.0.53', 'dns_resolver', 'eth0'),
    'dhcp01': ('10.20.0.67', 'dhcp_server', 'eth0'),
    'wlc01': ('10.20.0.41', 'wireless_controller', 'GigabitEthernet0'),
    'ap01': ('10.20.0.42', 'access_point', 'GigabitEthernet0'),
    'leaf01': ('10.20.0.51', 'datacenter_leaf', 'Ethernet1/1'),
    'client01': ('10.20.110.10', 'client', 'eth0'),
    'wifi01': ('10.20.110.30', 'wireless_client', 'wlan0'),
    'isp_a': ('192.0.2.1', 'synthetic_isp_router', 'Ethernet0'),
    'isp_b': ('192.0.2.5', 'synthetic_isp_router', 'Ethernet0'),
}
DEVICES.update({
    'checkout01': ('10.20.110.50', 'synthetic_checkout_probe', 'eth0'),
    'ise01': ('10.20.0.60', 'modeled_authentication_service', 'eth0'),
    'login01': ('10.20.110.51', 'synthetic_login_probe', 'eth0'),
    'checkpoint01': ('10.20.0.61', 'modeled_downstream_firewall', 'eth0'),
    'fortigate01': ('10.20.0.62', 'modeled_ips', 'eth0'),
    'f5_01': ('10.20.0.63', 'modeled_load_balancer', 'eth0'),
    'app_probe01': ('10.20.110.52', 'synthetic_application_probe', 'eth0'),
})
LINKS = (
    ('core01','TenGigabitEthernet1/0/1','dist01','TenGigabitEthernet1/1/1'),
    ('core02','TenGigabitEthernet1/0/1','dist01','TenGigabitEthernet1/1/2'),
    ('dist01','GigabitEthernet1/0/1','access01','GigabitEthernet1/0/24'),
    ('core01','TenGigabitEthernet1/0/2','edge01','GigabitEthernet0/1'),
    ('core02','TenGigabitEthernet1/0/2','leaf01','Ethernet1/1'),
    ('access01','GigabitEthernet1/0/10','client01','eth0'),
    ('access01','GigabitEthernet1/0/11','ap01','GigabitEthernet0'),
    ('core01','GigabitEthernet1/0/2','dns01','eth0'),
    ('core02','GigabitEthernet1/0/2','dhcp01','eth0'),
    ('dist01','GigabitEthernet1/0/2','wlc01','GigabitEthernet0'),
    ('ap01','radio0','wifi01','wlan0'),
    ('edge01','GigabitEthernet0/0','isp_a','Ethernet0'),
    ('edge01','GigabitEthernet0/2','isp_b','Ethernet0'),
)
# slug, title, device, fault metric, healthy, degraded, peak, warning, failure,
# network impact, operator action, recovery, convergence. Explicit per-incident
# messages make each pack executable evidence rather than a category label.
DEFINITIONS = [
 ('01_campus_link','Campus link failure/recovery','dist01','interface.errors.rate',0,18,180,
  'CRC and input errors rising on uplink to core01 TenGigabitEthernet1/0/1',
  'LINK-3-UPDOWN: Interface TenGigabitEthernet1/1/1 changed state to down',
  'OSPF-5-ADJCHG: Neighbor 10.20.0.11 on uplink changed FULL to DOWN; alternate core02 path active',
  'Operator replaced damaged uplink optic and cleared error counters',
  'LINK-5-UPDOWN: Interface TenGigabitEthernet1/1/1 changed state to up',
  'OSPF-5-ADJCHG: Neighbor 10.20.0.11 changed LOADING to FULL; primary path restored'),
 ('02_vlan_trunk','VLAN/trunk misconfiguration','access01','vlan.discard.rate',0,40,240,
  'Trunk allowed VLAN list changed; VLAN 110 absent on uplink to dist01',
  'SW_VLAN-3-VLAN_DENIED: VLAN 110 traffic discarded on GigabitEthernet1/0/24',
  'Connected SVI remains up but VLAN 110 client frames cannot reach gateway 10.20.110.1',
  'Operator restored VLAN 110 to allowed VLAN list on both trunk endpoints',
  'SW_VLAN-5-VLAN_ALLOWED: VLAN 110 forwarding enabled on trunk',
  'MAC learning resumed for VLAN 110; gateway ARP and bidirectional probes succeed'),
 ('03_stp_storm','STP loop/broadcast storm','access01','broadcast.packets.rate',20,2000,18000,
  'SPANTREE-4-TOPO_CHG: Repeated topology changes following accidental access-port loop',
  'STORM_CONTROL-3-FILTERED: Broadcast threshold exceeded in VLAN 110',
  'MACFLAP-4-NOTIF: Client MAC moving between GigabitEthernet1/0/2 and GigabitEthernet1/0/3',
  'Operator shut down looped port GigabitEthernet1/0/3 and removed patch cable',
  'SPANTREE-5-PORTSTATE: Loop isolated; root port stable toward dist01',
  'Spanning tree converged; topology-change counter stable and broadcast rate normal'),
 ('04_wan_brownout','WAN latency/jitter/packet-loss brownout','edge01','wan.latency.ms',12,95,340,
  'IP_SLA-4-DEGRADED: WAN probe latency and jitter increasing on ISP-A',
  'IP_SLA-3-TIMEOUT: WAN path loss 24 percent and jitter 85 ms; carrier remains up',
  'Application path to 198.51.100.80 impaired; routing adjacency remains established',
  'Operator applied temporary traffic steering to ISP-B and opened carrier incident',
  'IP_SLA-5-RECOVERY: ISP-A latency and packet loss returning to baseline',
  'Carrier repair confirmed; policy restored after stable probe hold-down'),
 ('05_dual_isp','Dual-ISP failover/recovery','edge01','wan.packet_loss.percent',0,8,100,
  'TRACK-4-STATE: ISP-A next-hop 192.0.2.1 probes failing',
  'TRACK-3-STATE: ISP-A tracked route down; primary default route removed',
  'ROUTING-5-FAILOVER: Default route installed via ISP-B 192.0.2.5; sessions re-establish',
  'Operator confirmed backup egress and requested ISP-A circuit repair',
  'TRACK-5-STATE: ISP-A next-hop reachable; restoration timer started',
  'Primary default restored after hold-down; ISP-B remains standby'),
 ('06_bgp_flap','BGP neighbor flap/route withdrawal','edge01','bgp.withdrawn.prefixes',0,12,240,
  'BGP-4-ADJCHANGE: Peer 192.0.2.1 AS 64501 repeated keepalive delays',
  'BGP-3-NOTIFICATION: Hold timer expired; peer 192.0.2.1 Established to Idle',
  'BGP-4-WITHDRAW: 240 prefixes withdrawn; alternate peer 192.0.2.5 AS 64502 selected',
  'Operator corrected unstable WAN optics and reset only affected BGP neighbor',
  'BGP-5-ADJCHANGE: Peer 192.0.2.1 OpenConfirm to Established',
  'BGP best-path selection complete; 240 prefixes restored without repeated flaps'),
 ('07_ospf_adjacency','OSPF adjacency failure/reconvergence','dist01','ospf.adjacency.down',0,0,1,
  'OSPF-4-HELLO: Hello packets missing from neighbor 10.20.0.11 area 0',
  'OSPF-3-ADJCHG: Neighbor 10.20.0.11 FULL to DOWN; dead timer expired',
  'OSPF-4-SPF: Topology LSA updated; VLAN 110 routed through core02 with higher cost',
  'Operator corrected mismatched OSPF hello/dead timers to 10/40 seconds',
  'OSPF-5-ADJCHG: Neighbor 10.20.0.11 EXSTART to EXCHANGE',
  'OSPF-5-ADJCHG: Neighbor FULL; LSDB synchronized and shortest path restored'),
 ('08_firewall_policy','Firewall policy misconfiguration','edge01','firewall.denied.sessions.rate',0,30,180,
  'CONFIG-5-COMMIT: New outbound policy revision applied to VLAN 110',
  'POLICY-3-DENY: Rule block-web denies tcp 10.20.110.10 to 198.51.100.80:443',
  'TRAFFIC-4-DROP: Healthy routed path but new application sessions denied by policy',
  'Operator reverted erroneous rule block-web to previous approved policy revision',
  'POLICY-5-PERMIT: Approved outbound HTTPS policy restored',
  'New sessions established; synthetic HTTPS transaction and return traffic verified'),
 ('09_ddos_flood','DDoS/traffic flood/mitigation','edge01','security.flood.packets.rate',40,12000,90000,
  'THREAT-4-RATE: Rising SYN rate from synthetic source 203.0.113.77 toward 198.51.100.80',
  'THREAT-2-FLOOD: SYN flood threshold exceeded; connection table under pressure',
  'TRAFFIC-3-DROP: Legitimate VLAN 110 sessions competing with flood traffic',
  'Operator enabled bounded SYN protection and upstream synthetic source filter',
  'THREAT-5-MITIGATED: Flood filtered; connection table pressure declining',
  'Legitimate transactions stable; mitigation retained pending observation'),
 ('10_dns_failure','DNS resolver failure/recovery','dns01','dns.query.failure.percent',0,30,100,
  'DNS-4-UPSTREAM: Recursive resolver upstream timeouts increasing',
  'DNS-3-SERVFAIL: Resolver cannot answer uncached queries for demo.example',
  'CLIENT-4-RESOLUTION: IP reachability healthy but name-based applications unavailable',
  'Operator restored upstream resolver route and flushed failed query cache',
  'DNS-5-ANSWER: Recursive answers restored for demo.example',
  'Positive and negative cache probes normal; synthetic client resolution verified'),
 ('11_dhcp_exhaustion','DHCP pool exhaustion/recovery','dhcp01','dhcp.pool.utilization.percent',60,92,100,
  'DHCP-4-POOL_LOW: VLAN110 pool 10.20.110.0/24 has few free leases',
  'DHCP-3-POOL_EXHAUSTED: No free address for new VLAN 110 client',
  'CLIENT-4-LEASE: New clients cannot obtain address; existing leased clients unaffected',
  'Operator reclaimed expired leases and corrected excessive lease duration',
  'DHCP-5-OFFER: Free leases available; offer 10.20.110.20 to new synthetic client',
  'DHCP-5-ACK: Lease completed; gateway and DNS options verified by client'),
 ('12_dc_congestion','Data-center congestion/queue drops','leaf01','interface.queue.drops.rate',0,140,1800,
  'QOS-4-QUEUE: Egress queue occupancy increasing on Ethernet1/1',
  'QOS-3-DROP: Microburst queue overflow; tail drops on Ethernet1/1',
  'TCP-4-RETRANS: Application transfers to 198.51.100.80 retransmitting; link stays up',
  'Operator paced bulk transfer and corrected QoS queue allocation',
  'QOS-5-RECOVERY: Queue occupancy declining and drop rate reduced',
  'Application throughput restored; queue and retransmission probes stable'),
 ('13_mtu_pmtud','MTU mismatch/PMTUD failure','edge01','network.large_probe.failure.percent',0,50,100,
  'IP-4-MTU: Large DF probes failing across tunnel; small probes succeed',
  'IP-3-PMTUD: Path MTU 1400 smaller than sender 1500 and ICMP feedback filtered',
  'TCP-4-STALL: TLS handshake succeeds but large application transfer stalls',
  'Operator permitted ICMP fragmentation-needed and aligned tunnel MTU/MSS',
  'IP-5-PMTUD: Sender learned 1400-byte path MTU',
  'Large and small synthetic transfers complete; fragmentation-needed feedback confirmed'),
 ('14_wireless_outage','Wireless controller/AP outage','wlc01','wireless.ap.unreachable',0,0,1,
  'CAPWAP-4-KEEPALIVE: AP ap01 10.20.0.42 missed control keepalives',
  'CAPWAP-3-AP_DOWN: AP ap01 lost controller reachability',
  'WLAN-4-CLIENT_LOSS: VLAN 110 wireless clients disconnected; wired clients unaffected',
  'Operator restored AP switch power/uplink and verified controller reachability',
  'CAPWAP-5-JOIN: AP ap01 authenticated and rejoined controller wlc01',
  'WLAN-5-CLIENT_JOIN: SSID campus-demo available; client lease and application probe verified'),
 ('15_device_resources','Device CPU/memory exhaustion','core01','device.cpu.percent',18,78,99,
  'SYS-4-RESOURCE: CPU and memory pressure increasing from runaway telemetry process',
  'SYS-3-RESOURCE: CPU 99 percent; free memory low and control-plane queue delayed',
  'ROUTING-4-DELAY: Adjacency hellos delayed; management response and client latency degraded',
  'Operator stopped runaway synthetic process and reduced excessive collection frequency',
  'SYS-5-RESOURCE: CPU and memory returning to safe operating range',
  'Control-plane queues drained; adjacency, management and client probes stable'),
]
DEFINITIONS.extend([('16_retail_uplink',
  'Retail branch uplink flap and checkout interruption',
  'access01',
  'uplink.down',
  0,
  0.2,
  1,
  'Modeled Arista access uplink intermittently down; firewall sessions retry',
  'Modeled branch uplink down; perimeter sessions cannot carry checkout requests',
  'Synthetic retail checkout cohort sees unavailable payment path',
  'Simulated Operator restores modeled uplink; no device operation performed',
  'Modeled uplink up; new firewall sessions establish',
  'Synthetic checkout probes recover after transport stability',
  {'proposal': 1,
   'uc': ['5.1.1', '21.11.1'],
   'domain': 'Network / infrastructure',
   'industry': 'Retail',
   'observer': 'edge01',
   'client': 'checkout01',
   'service': 'retail-checkout',
   'products': ['Arista EOS', 'Cisco ASA'],
   'signals': ['uplink observation', 'perimeter session observation', 'checkout probe'],
   'kpis': [('checkout.failure.percent', 0, 70), ('session.failure.percent', 0, 80)]}),
 ('17_hospital_mac_auth',
  'Hospital access MAC instability and login retries',
  'access01',
  'mac.moves.per_minute',
  0,
  12,
  60,
  'Modeled Cisco access MAC movement between two declared ports increases',
  'Modeled port instability coincides with ISE authentication retries',
  'Synthetic staff login cohort delayed; no patient identities or clinical actions',
  'Simulated Operator stabilizes modeled port relationship',
  'Modeled MAC stable on one port; authentication retries decline',
  'Synthetic staff login probes return to baseline',
  {'proposal': 2,
   'uc': ['5.1.1', '17.1.2'],
   'domain': 'Security',
   'industry': 'Healthcare',
   'observer': 'ise01',
   'client': 'login01',
   'service': 'staff-login',
   'products': ['Cisco IOS XE', 'Cisco ISE'],
   'signals': ['MAC movement observation', 'authentication observation', 'staff login probe'],
   'kpis': [('authentication.failure.percent', 0, 65), ('login.latency.ms', 40, 1800)]}),
 ('18_payment_deny',
  'Perimeter deny burst and payment availability loss',
  'edge01',
  'policy.denies.per_second',
  0,
  30,
  200,
  'Modeled Cisco ASA deny rate rises on synthetic payment path',
  'Modeled downstream Check Point observation also denies selected payment flows',
  'Synthetic authorization probes fail; no real card or account data',
  'Simulated policy rollback in model only; no firewall change performed',
  'Modeled permits return; new synthetic payment sessions establish',
  'Synthetic authorization failure ratio returns to baseline',
  {'proposal': 5,
   'uc': ['5.2.2', '21.11.1'],
   'domain': 'Security',
   'industry': 'Financial services',
   'observer': 'checkpoint01',
   'client': 'checkout01',
   'service': 'payment-authorize',
   'products': ['Cisco ASA', 'Check Point'],
   'signals': ['upstream policy observation', 'downstream policy observation', 'payment probe'],
   'kpis': [('payment.failure.percent', 0, 85), ('payment.latency.ms', 25, 2200)]}),
 ('19_ips_service',
  'IPS attack burst and legitimate-session degradation',
  'fortigate01',
  'ips.detections.per_second',
  0,
  40,
  250,
  'Modeled Fortinet IPS detections increase for a bounded synthetic attack cohort',
  'Modeled perimeter demand coincides with legitimate session degradation',
  'Synthetic legitimate-client completion ratio drops; no attack packets emitted',
  'Simulated filtering intervention reduces modeled attack demand only',
  'Modeled detections and session failures decline',
  'Legitimate synthetic service probes stable after recovery',
  {'proposal': 6,
   'uc': ['5.2.2', '8.1.1'],
   'domain': 'Security',
   'industry': 'Cross-industry',
   'observer': 'edge01',
   'client': 'client01',
   'service': 'enterprise-service',
   'products': ['Fortinet FortiOS', 'Cisco ASA'],
   'signals': ['IPS observation', 'legitimate session observation', 'service probe'],
   'kpis': [('legitimate.session.failure.percent', 0, 45), ('service.latency.ms', 20, 850)]}),
 ('20_backend_link',
  'Distribution-link loss and backend monitor failure',
  'dist01',
  'backend.link.down',
  0,
  0.2,
  1,
  'Modeled Arista distribution path flaps before backend health checks fail',
  'Modeled backend path down; F5 pool member observation becomes unavailable',
  'Synthetic application dependency degraded; frontend reachability alone is insufficient',
  'Simulated Operator restores backend path in the dependency model',
  'Modeled path up; backend monitor recovers after link stability',
  'Synthetic application probe stable after backend recovery',
  {'proposal': 8,
   'uc': ['5.1.1', '8.1.1'],
   'domain': 'Cloud / application',
   'industry': 'Cross-industry',
   'observer': 'f5_01',
   'client': 'app_probe01',
   'service': 'application-backend',
   'products': ['Arista EOS', 'F5 BIG-IP'],
   'signals': ['backend path observation', 'pool member health observation', 'application probe'],
   'kpis': [('pool.member.unavailable.percent', 0, 50), ('application.failure.percent', 0, 60)]}),
 ('21_partial_pool',
  'Partial load-balancer pool outage with perimeter demand',
  'f5_01',
  'pool.member.unavailable.percent',
  0,
  10,
  50,
  'Modeled F5 pool loses one of two members under fixed synthetic offered load',
  'Modeled half-capacity pool cannot serve all synthetic perimeter demand',
  'Synthetic application errors rise while one member remains available',
  'Simulated Operator restores failed member; no real load balancer operation',
  'Modeled pool returns to two healthy members; application errors decline',
  'Synthetic application probes meet baseline with restored pool capacity',
  {'proposal': 9,
   'uc': ['8.1.1'],
   'domain': 'Cloud / application',
   'industry': 'Retail',
   'observer': 'edge01',
   'client': 'app_probe01',
   'service': 'retail-web',
   'products': ['F5 BIG-IP', 'Cisco ASA'],
   'signals': ['pool capacity observation', 'offered session demand', 'application probe'],
   'kpis': [('application.failure.percent', 0, 35), ('application.latency.ms', 25, 600)]})])
CATALOG = {row[0]: row for row in DEFINITIONS}
PHASES = ('BASELINE','WARNING','DEGRADATION','FAILURE','NETWORK_IMPACT',
          'USER_IMPACT','INTERVENTION','RECOVERY','RECONVERGENCE','VERIFIED_HEALTHY')


def descriptor(path):
    """Only explicitly marked JSON-as-YAML pack files use this execution path."""
    text = Path(path).read_text()
    if not text.lstrip().startswith('{'):
        return None
    data = json.loads(text)
    if 'pulseforge_incident' not in data:
        return None
    if (set(data) != {'pulseforge_incident','seed','version'} or data['version'] != 1
            or (data['pulseforge_incident'] not in CATALOG
                and data['pulseforge_incident'] not in telecom_incidents.CATALOG)
            or type(data['seed']) is not int or not 0 <= data['seed'] <= 2**32-1):
        raise ValueError('Invalid network incident descriptor')
    return data


def generate(slug, seed=42, start=1700000000.0, run_id=None, eps=10):
    """30 ordered logs and 10 gauges, at most 40 transport records per run.

    A supplied start/seed/run ID reproduces exact events. No global RNG is used.
    Timestamps span the actual paced run (not a future simulated wall clock).
    """
    if slug in telecom_incidents.CATALOG:
        return telecom_incidents.generate(slug, seed, start, run_id, eps, PHASES)
    row = CATALOG[slug]
    if type(seed) is not int or not 0 <= seed <= 2**32-1 or not math.isfinite(start) or not 1 <= eps <= 500000:
        raise ValueError('Invalid incident execution parameters')
    rng = random.Random(seed)
    incident = str(uuid.uuid5(uuid.NAMESPACE_URL, f'netspout:{slug}:{seed}:{run_id or "preview"}'))
    _, title, primary, metric, healthy, degraded, peak, warning, failure, impact, action, recovery, converge = row[:13]
    correlated = row[13] if len(row) > 13 else None
    messages = (f'HEALTH-6-OK: {title} baseline; VLAN 110 gateway and application reachable', warning,
                f'PROBE-4-DEGRADED: {warning}; loss and latency outside baseline', failure,
                impact, f'CLIENT-3-IMPACT: {impact}', action, recovery, converge,
                'HEALTH-6-OK: Post-recovery gateway, DNS and application probes passed; no active incident')
    levels = (6,4,4,3,4,3,5,5,5,6)
    values = (healthy,degraded,degraded,peak,peak,peak,degraded,degraded,healthy,healthy)
    events=[]
    for phase_index,phase in enumerate(PHASES):
        observations = ((primary,messages[phase_index]),('core02',f'PATH-5-OBSERVE: {messages[phase_index]}'),
                               ('wifi01' if slug=='14_wireless_outage' else 'client01',f'PROBE-5-RESULT: phase={phase}; '+
                                ('application reachable' if phase_index in (0,8,9) else
                                 'operator action in progress' if phase_index==6 else
                                 'application degraded; '+impact)))
        if correlated:
            observations = ((primary,messages[phase_index]),
                (correlated['observer'],correlated['signals'][1]+': '+messages[phase_index]),
                (correlated['client'],correlated['signals'][2]+': '+messages[phase_index]))
        for device,message in observations:
            address,role,interface=DEVICES[device]
            fields=dict(netspout_incident_id=incident,netspout_scenario_id=slug,netspout_site_id=SITE,
                        netspout_device_id=device,netspout_phase=phase,device_ip=address,
                        device_role=role,interface=interface,vlan=110,subnet='10.20.110.0/24',
                        sequence=len(events),severity=levels[phase_index])
            if correlated:
                fields.update(simulation='true',contract_kind='pulseforge_custom',
                    netspout_service_id=correlated['service'],
                    dependency_path=primary+'>'+correlated['observer']+'>'+correlated['client'],
                    modeled_products=','.join(correlated['products']),
                    evidence_kind='simulated_action' if phase_index==6 else 'simulated_observation')
                message=('SIMULATED Operator action: ' if phase_index==6 else 'SIMULATED ')+message
            if run_id: fields['netspout_run_id']=run_id
            stamp=start+len(events)/eps
            fields['event_time']=stamp
            raw=(f'{device} %{message} '+ ' '.join(f'{k}={v}' for k,v in fields.items() if k not in ('sequence','severity')))
            events.append(dict(time=stamp,host=device,source='netspout:network_incident',
                               sourcetype='netspout:network:syslog',index='idx_network_ops',raw=raw,fields=fields))
        # Preserve the incident progression; jitter affects only numeric evidence.
        value=float(values[phase_index])
        if phase_index in (1,2) and value > 0: value=round(value*rng.uniform(.95,1.05),3)
        fields=dict(events[-3]['fields'],sequence=len(events),event_time=start+len(events)/eps)
        events.append(dict(time=start+len(events)/eps,host=primary,source='netspout:network_incident',
                           sourcetype='netspout:network:metric',index='idx_performance_metrics',
                           raw='metric',fields=fields,metrics={metric:value,
                           'network.packet_loss.percent':float(0 if phase_index in (0,8,9) else 5 if phase_index in (1,6,7) else 35),
                           'network.latency.ms':float(3 if phase_index in (0,8,9) else 20 if phase_index in (1,6,7) else 160)}))
        if correlated:
            factor=(0,.2,.4,1,1,1,.6,.2,0,0)[phase_index]
            events[-1]['metrics']={metric:value, **{name:float(base+(peak-base)*factor)
                for name,base,peak in correlated['kpis']}}
        if slug=='01_campus_link':
            events[-1]['metrics'].update({'interface.operational.up':float(phase_index not in (3,4,5,6)),
                                         'interface.input.errors':float((0,18,40,180,180,180,0,0,0,0)[phase_index])})
        if slug=='15_device_resources':
            events[-1]['metrics']['device.memory.utilization.percent']=float((40,78,85,97,97,97,82,65,40,40)[phase_index])
    return events


def select_events(events, protocol, config):
    if protocol not in ('hec','syslog','otlp','snmp','forwarding'):
        raise ValueError('Unsupported incident destination')
    signal=config.get('otlp_signal','both') if protocol=='otlp' else 'both' if protocol=='hec' else 'logs'
    if signal not in ('logs','metrics','both'): raise ValueError('Unsupported incident signal')
    return [e for e in events if signal=='both' or ('metrics' if 'metrics' in e else 'logs')==signal]


def otlp_payload(runner,event,run_id,slug):
    # Reuse the native resource/body builder. Only the scenario's gauge data is
    # supplied here; HTTP, partial-success and authentication stay in the adapter.
    log=dict(event,index='logs',sourcetype='netspout:network:syslog')
    payload,_,_=runner.build_native_otlp(log,event['raw'],run_id,slug,now=event['time'])
    resource=payload['resourceLogs'][0]['resource']
    attrs={a['key']:a for a in resource['attributes']}
    attrs.update({k:{'key':k,'value':{'stringValue':str(v)}} for k,v in event['fields'].items()})
    attrs['sourcetype']={'key':'sourcetype','value':{'stringValue':event['sourcetype']}}
    resource['attributes']=list(attrs.values())
    if 'metrics' not in event:
        record=payload['resourceLogs'][0]['scopeLogs'][0]['logRecords'][0]
        record.update(attributes=list(attrs.values()),severityNumber={3:17,4:13,5:9,6:9}[event['fields']['severity']])
        return payload,False,1
    metrics=[{'name':name,'gauge':{'dataPoints':[{'asDouble':value,'timeUnixNano':str(int(event['time']*1e9)),
               'attributes':list(attrs.values())}]}} for name,value in event['metrics'].items()]
    return {'resourceMetrics':[{'resource':resource,'scopeMetrics':[{'scope':{'name':'netspout.native'},'metrics':metrics}]}]},True,len(metrics)


def execute(runner,args,private,data):
    """Finite producer only: all delivery uses the existing native adapters."""
    from netspout_core.telemetry_dispatcher import TelemetryDispatcher, hec_outcome_fields
    from native_run_monitor import update
    protocol=next((p for p in ('syslog','otlp','snmp','forwarding') if
        getattr(args,'native_'+p,False) or getattr(args,p+'_preflight',False)), 'hec')
    config=private.get(protocol,{}) if protocol!='hec' else runner.runtime_config()
    from datablaster_rest import validate_syslog_settings,validate_otlp_settings,validate_snmp_settings
    if protocol=='syslog': config=validate_syslog_settings(config)
    if protocol=='otlp': config=dict(validate_otlp_settings(config),headers=config.get('headers',{}))
    if protocol=='snmp': config=dict(validate_snmp_settings(config),community=config.get('community'))
    if protocol=='forwarding':
        import pulseforge_forwarding as forwarding
        config=forwarding.validate(config)
    limit=100 if protocol=='forwarding' else (25 if config.get('snmp_message_type')=='inform' else 50) if protocol=='snmp' else 500000
    if not 1 <= args.eps <= limit: raise ValueError('Unsupported incident rate')
    if protocol=='hec':
        endpoint=runner.resolve_hec_urls(args.hec,config)[0]
        if not args.token: raise ValueError('Missing incident credential')
    start=time.time()
    events=select_events(generate(data['pulseforge_incident'],data['seed'],start,args.run_id,args.eps),protocol,config)
    if protocol=='snmp':
        from netspout_core.snmp_ber import SnmpBerEncoder
        transport=runner.native_snmp_transport(config)
        for e in events:
            SnmpBerEncoder.encode_message(runner.build_native_snmp(e,e['raw'],config,args.run_id,data['pulseforge_incident'],e['fields']['netspout_phase']))
    if any(getattr(args,p+'_preflight',False) for p in ('syslog','otlp','snmp','forwarding')):
        print(json.dumps({'status':'success','templates':len(events)}));return
    if not args.run_id: raise ValueError('Incident requires native run identity')
    dispatcher=TelemetryDispatcher()
    for event in events:
        delay=event['time']-time.time()
        if delay>0: time.sleep(delay)
        payload_count=len(event.get('metrics',{})) if protocol=='otlp' and 'metrics' in event else 1
        def attempting(r):
            r['classification']='MIXED' if any('metrics' in e for e in events) and any('metrics' not in e for e in events) else 'METRIC' if 'metrics' in events[0] else 'LOG'
            r['correlation']='SUPPORTED' if protocol=='hec' else 'UNSUPPORTED'
            for key in ('generated','attempted','unknown'):
                r['counters'][key]=(r['counters'][key] or 0)+payload_count
            if protocol!='hec':
                delivery=r.setdefault(protocol+'_delivery',{})
                delivery['unknown']=(delivery.get('unknown') or 0)+payload_count
                if protocol!='forwarding':
                    delivery['attempted']=(delivery.get('attempted') or 0)+payload_count
            if protocol=='hec':
                index=config.get('idx_performance_metrics','idx_performance_metrics') if 'metrics' in event else config.get('idx_network_ops','idx_network_ops')
                r['indexes']=sorted(set(r['indexes'])|{index})
        update(args.run_id,attempting)
        evidence={k:0 for k in ('accepted','failed','unknown')}
        if protocol=='hec':
            fields=dict(event['fields'])
            if 'metrics' in event: fields.update({'metric_name:'+k:v for k,v in event['metrics'].items()})
            payload=dict(time=event['time'],host=event['host'],source=event['source'],sourcetype=event['sourcetype'],
                         index=config.get('idx_performance_metrics','idx_performance_metrics') if 'metrics' in event else config.get('idx_network_ops','idx_network_ops'),
                         event='metric' if 'metrics' in event else event['raw'],fields=fields)
            outcome=dispatcher.emit_hec(payload,endpoint,args.token,ssl_verify=config.get('ssl_verify',True),allow_insecure_tls=config.get('ssl_verify',True) is False)
            state=hec_outcome_fields(outcome)['state']
            evidence[{'ACCEPTED':'accepted','FAILED':'failed'}.get(state,'unknown')]=1
        elif protocol=='syslog':
            result=runner.send_native_syslog(dispatcher,config,event['raw'],event['host'])
            evidence.update(unknown=result['unknown'],failed=result['failed'])
        elif protocol=='otlp':
            payload,metric,count=otlp_payload(runner,event,args.run_id,data['pulseforge_incident'])
            result=runner.send_native_otlp(dispatcher,config,payload,metric,count)
            evidence.update(accepted=result['acknowledged'],failed=result['rejected']+result['failed'],unknown=result['unknown'])
        elif protocol=='snmp':
            message=runner.build_native_snmp(event,event['raw'],config,args.run_id,data['pulseforge_incident'],event['fields']['netspout_phase'],event['fields']['sequence']+1)
            result=runner.send_native_snmp(transport,message,config)
            evidence.update(accepted=result['acknowledged'] or 0,failed=result['failed'],unknown=result['unknown'])
        else:
            record=forwarding.event_record(event,event['raw'],args.run_id,data['pulseforge_incident'],config['forwarding_index'],event['time'])
            record['data'].update(event['fields'])
            try: forwarding.publish(record);result={'published':1,'failed':0,'unknown':0}
            except Exception:
                # Publication may have reached replacement; never retry it.
                raise RuntimeError('Incident spool publication unconfirmed') from None
        def delivered(r):
            r['counters']['unknown']-=payload_count
            for key,value in evidence.items(): r['counters'][key]=(r['counters'][key] or 0)+value
            if protocol in ('syslog','otlp','snmp','forwarding'):
                keys={'syslog':('attempted','sent','failed','unknown'),'otlp':('attempted','acknowledged','rejected','failed','unknown'),
                      'snmp':('attempted','sent','acknowledged','failed','unknown'),'forwarding':('published','failed','unknown')}[protocol]
                delivery=r.setdefault(protocol+'_delivery',{})
                delivery['unknown']-=payload_count
                for key in keys:
                    if key=='attempted': continue
                    value=result.get(key)
                    if value is not None: delivery[key]=(delivery.get(key) or 0)+value
                if protocol in ('syslog','forwarding') or protocol=='snmp' and config['snmp_message_type']=='trap':
                    r['counters']['accepted']=None
        update(args.run_id,delivered)
    update(args.run_id,lambda r:r.update(execution_state='COMPLETED',ended_at=time.time()))
