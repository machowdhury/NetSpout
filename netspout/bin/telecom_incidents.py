"""Synthetic telecom service assurance, using the shared finite incident runner.

No subscriber PII, standards-wire claims, network operations or remediation.
All observations and alarms below are generated simulation evidence.
"""
import math
import random
import uuid

SITE = 'synthetic-metro-01'
COHORT = 'synthetic-cohort-A'
# Management addresses and logical interfaces, never destination addresses.
DEVICES = {
    'gnb01': ('10.60.0.11','5g_ran','n2'),
    'du01': ('10.60.0.12','distributed_unit','fronthaul'),
    'transport01': ('10.60.0.21','mobile_transport','Ethernet1/1'),
    'amf01': ('10.60.0.31','access_mobility','n2'),
    'ausf01': ('10.60.0.32','authentication_service','nausf'),
    'udm01': ('10.60.0.33','subscriber_data_service','nudm'),
    'smf01': ('10.60.0.34','session_management','n4'),
    'upf01': ('10.60.0.35','user_plane','n3'),
    'enb01': ('10.60.0.41','lte_ran','s1'),
    'epc01': ('10.60.0.42','lte_packet_core','s1'),
    'ims01': ('10.60.0.43','ims_service','sip'),
    'cpe01': ('10.60.0.51','broadband_cpe','wan0'),
    'bng01': ('10.60.0.52','broadband_gateway','subscriber0'),
    'sdwan01': ('10.60.0.61','sdwan_edge','wan0'),
    'sdwan02': ('10.60.0.62','sdwan_hub','wan0'),
    'gnb02': ('10.60.0.71','target_5g_ran','n2'),
    'assurance01': ('10.60.0.81','synthetic_assurance','telemetry'),
    'probe01': ('10.60.0.82','synthetic_cohort_probe','service'),
}
# Logical dependencies; no claim these labels implement 3GPP signaling.
RELATIONSHIPS = (
    ('du01','transport01','fronthaul'),('gnb01','transport01','backhaul'),
    ('transport01','amf01','N2_control'),('transport01','upf01','N3_user'),
    ('amf01','ausf01','authentication'),('ausf01','udm01','synthetic_subscription'),
    ('amf01','smf01','session_control'),('smf01','upf01','N4_control'),
    ('enb01','epc01','LTE_access'),('epc01','ims01','voice_service'),
    ('cpe01','bng01','broadband_access'),('sdwan01','sdwan02','overlay'),
    ('gnb01','gnb02','mobility'),('gnb02','amf01','target_access'),
)
CELL_NODES={'synthetic-cell-A':'gnb01','synthetic-cell-B':'gnb02','synthetic-lte-cell-A':'enb01'}
SERVICE_PATHS={
    'telco_01_ran_cell':('du01','gnb01','transport01','upf01'),
    'telco_02_registration_auth':('gnb01','amf01','ausf01','udm01'),
    'telco_03_slice_sla':('gnb01','smf01','upf01'),
    'telco_04_ims_volte':('enb01','epc01','ims01'),
    'telco_05_mobile_transport':('du01','transport01','upf01'),
    'telco_06_broadband_cpe':('cpe01','bng01'),
    'telco_07_sdwan_service':('sdwan01','sdwan02'),
    'telco_08_roaming_mobility':('gnb01','gnb02','amf01','smf01'),
    'telco_09_core_user_plane':('gnb01','smf01','upf01'),
    'telco_10_cross_layer':('gnb01','transport01','amf01','upf01'),
}
# title, primary node, service, cell, warning, fault, impact, simulated action,
# recovery, convergence, (KPI name, healthy, peak) tuples.
CATALOG = {
 'telco_01_ran_cell': (
  '5G RAN cell degradation','gnb01','synthetic-mobile-data','synthetic-cell-A',
  'Radio interference rising; downlink block errors increasing',
  'Cell quality alarm; scheduler retransmissions high while carrier stays available',
  'Mobile data cohort experiences reduced throughput and higher retransmissions',
  'Simulated operator action: isolate interfering source and retune lab radio parameters',
  'Interference reduced in simulation; block error ratio falling',
  'Scheduler stable; synthetic cohort throughput returns toward baseline',
  (('ran.downlink.bler.percent',.5,18),('ran.user.throughput.mbps',150,8),('ran.prb.utilization.percent',35,95))),
 'telco_02_registration_auth': (
  '5G registration/authentication failure','ausf01','synthetic-registration','synthetic-cell-A',
  'AUSF to UDM synthetic authentication lookup latency increasing',
  'Registration rejects increasing after synthetic authentication-data mismatch',
  'New registrations fail; already established user-plane sessions remain active',
  'Simulated operator action: restore consistent synthetic authentication data and UDM reachability',
  'Authentication responses return; new registration probes retry successfully',
  'AMF registration success stable; established sessions unaffected',
  (('registration.failure.percent',.2,65),('authentication.latency.ms',30,1200),('registration.success.percent',99.8,35))),
 'telco_03_slice_sla': (
  '5G network slice SLA violation','upf01','synthetic-enterprise-slice','synthetic-cell-A',
  'Slice queue utilization rising above reserved capacity',
  'Synthetic slice latency budget exceeded; isolated service SLA alarm',
  'Enterprise slice cohort degraded; other modeled services remain outside incident scope',
  'Simulated operator action: restore slice resource reservation and reduce competing lab load',
  'Slice latency declining; reserved service capacity restored in simulation',
  'Synthetic latency and loss probes meet configured slice budget',
  (('slice.latency.ms',8,60),('slice.packet_loss.percent',.1,8),('slice.throughput.mbps',100,20))),
 'telco_04_ims_volte': (
  'IMS/VoLTE call-quality degradation','ims01','synthetic-volte','synthetic-lte-cell-A',
  'LTE/EPC voice bearer jitter rising; SIP registration remains available',
  'Synthetic RTP impairment alarm; packet loss and estimated MOS degraded',
  'Established VoLTE calls have poor audio; SIP signaling success is not media quality proof',
  'Simulated operator action: correct voice QoS queue and remove competing synthetic media load',
  'RTP jitter and loss decline; modeled voice quality improves',
  'LTE/EPC/IMS media probes stable; estimated MOS returns to baseline',
  (('voice.estimated_mos',4.3,2.1),('voice.rtp.jitter.ms',4,65),('voice.rtp.loss.percent',.1,12))),
 'telco_05_mobile_transport': (
  'Mobile transport/fronthaul congestion','transport01','synthetic-ran-transport','synthetic-cell-A',
  'Fronthaul egress queue occupancy rising on Ethernet1/1',
  'Transport queue drops and one-way delay exceed synthetic fronthaul budget',
  'DU radio scheduling and downstream mobile service degraded by transport loss',
  'Simulated operator action: pace competing lab traffic and restore fronthaul queue reservation',
  'Transport drops decline; fronthaul delay moves toward budget',
  'DU and transport synthetic probes stable; no persistent queue growth',
  (('fronthaul.queue.utilization.percent',10,96),('fronthaul.one_way_latency.ms',.1,3),('fronthaul.packet_loss.percent',0,15))),
 'telco_06_broadband_cpe': (
  'Broadband CPE service outage','cpe01','synthetic-broadband','not_applicable',
  'CPE WAN session keepalives missed at broadband gateway',
  'Synthetic access session down; CPE cannot reach broadband gateway',
  'Broadband service probes fail for affected cohort; mobile services outside incident scope',
  'Simulated operator action: restore lab access uplink and re-establish broadband session',
  'CPE WAN session restored; address and route provisioning return',
  'Synthetic DNS and application probes pass through BNG',
  (('broadband.service.availability.percent',100,0),('broadband.active_sessions',120,0),('broadband.probe.failure.percent',0,100))),
 'telco_07_sdwan_service': (
  'SD-WAN service degradation','sdwan01','synthetic-branch-service','not_applicable',
  'Primary overlay path latency and jitter increasing',
  'Synthetic application SLA threshold exceeded on primary underlay',
  'Branch application cohort degraded; tunnel-up status alone does not establish service health',
  'Simulated operator action: steer lab application traffic to healthy secondary underlay',
  'Application probes improve on secondary path; primary repair pending',
  'Primary restored and hold-down complete; overlay probes stable',
  (('sdwan.application.latency.ms',25,200),('sdwan.application.jitter.ms',5,80),('sdwan.application.loss.percent',.2,20))),
 'telco_08_roaming_mobility': (
  'Roaming/mobility failure','amf01','synthetic-mobility','synthetic-cell-A',
  'Synthetic inter-cell handover preparation delays toward target cell B',
  'Target access context rejected during modeled mobility transition',
  'Moving cohort sessions interrupted; stationary cohort is not modeled as affected',
  'Simulated operator action: correct target-cell access context and synthetic mobility policy',
  'Target cell accepts handover context; session continuity improves',
  'Repeated synthetic A-to-B mobility probes complete without session loss',
  (('mobility.handover.failure.percent',1,45),('mobility.interruption.ms',30,1200),('mobility.session.drop.percent',.1,18))),
 'telco_09_core_user_plane': (
  '5G core user-plane degradation','upf01','synthetic-mobile-data','synthetic-cell-A',
  'UPF processing queues growing on N3 user-plane path',
  'Synthetic GTP-U packet drops rising; control-plane registration remains available',
  'Established data sessions lose packets despite successful AMF registration',
  'Simulated operator action: remove synthetic UPF overload and restore modeled processing capacity',
  'UPF queue drains; user-plane packet delivery improves',
  'N3 data probes and session throughput stable; control plane remains separate',
  (('upf.packet_drop.percent',.1,25),('upf.forwarding.packets_per_second',50000,8000),('upf.data.latency.ms',8,250))),
 'telco_10_cross_layer': (
  'Cross-layer telecom service outage and SLA impact','transport01','synthetic-enterprise-mobile','synthetic-cell-A',
  'Shared transport loss affects RAN-to-core service dependency',
  'Synthetic transport outage creates RAN reachability and user-plane service alarms',
  'One correlated incident affects mobile enterprise cohort; SLA budget consumed',
  'Simulated operator action: restore shared lab transport and validate RAN/core dependencies',
  'Transport restored; RAN and user-plane service alarms begin clearing',
  'Cross-layer probes meet SLA; consumed outage budget remains recorded',
  (('telecom.service.availability.percent',99.9,40),('telecom.service.latency.ms',15,350),('telecom.affected.cohort.percent',0,70))),
}


def generate(slug,seed,start,run_id,eps,phases):
    """Same 40-record schedule as network packs; all KPIs are simulated gauges."""
    if type(seed) is not int or not 0 <= seed <= 2**32-1 or not math.isfinite(start) or not 1 <= eps <= 500000:
        raise ValueError('Invalid incident execution parameters')
    row=CATALOG[slug]
    title,primary,service,cell,warning,fault,impact,action,recovery,convergence,kpis=row
    rng=random.Random(seed)
    incident=str(uuid.uuid5(uuid.NAMESPACE_URL,f'netspout:{slug}:{seed}:{run_id or "preview"}'))
    messages=(f'Synthetic baseline: {service} probes healthy',warning,warning+'; service KPI trend degraded',
              fault,impact,impact+'; synthetic cohort probe confirms modeled impact',action,recovery,convergence,
              f'Synthetic recovery verification: {service} probes healthy; no real service tested')
    severity=(6,4,4,3,4,3,5,5,5,6)
    factors=(0,.2,.4,1,1,1,.65,.3,.05,0)
    affected=(0,20,100,450,650,700,350,150,20,0)
    events=[]
    dependent=next(node for node in SERVICE_PATHS[slug] if node!=primary)
    for n,phase in enumerate(phases):
        for host,message in ((primary,messages[n]),(dependent,messages[n]),
                             ('upf01' if slug=='telco_10_cross_layer' else 'probe01',messages[n])):
            ip,role,interface=DEVICES[host]
            kind='simulated_action' if n==6 else 'simulated_alarm' if host==primary and 1<=n<=5 else 'simulated_observation'
            fields=dict(netspout_run_id=run_id or 'preview',netspout_incident_id=incident,
                        netspout_scenario_id=slug,netspout_site_id=SITE,netspout_device_id=host,
                        netspout_phase=phase,netspout_cell_id=cell,netspout_service_id=service,
                        netspout_subscriber_cohort=COHORT,device_ip=ip,device_role=role,interface=interface,
                        evidence_kind=kind,simulation='true',sequence=len(events),severity=severity[n],
                        event_time=start+len(events)/eps,affected_synthetic_subscribers=affected[n])
            if slug=='telco_03_slice_sla': fields['slice_id']='synthetic-slice-01'
            if slug=='telco_08_roaming_mobility': fields['target_cell_id']='synthetic-cell-B'
            if slug=='telco_10_cross_layer': fields['consumed_sla_budget_seconds']=(0,0,0,.1,.2,.4,.6,.8,.8,.8)[n]
            if n==6: fields['remediation_executed']='false'
            # Full correlation stays in the owned synthetic body for log-only
            # transports. Numeric detail remains structured in HEC/OTLP fields.
            raw=('SIMULATED '+message+' '+ ' '.join(f'{key}={fields[key]}' for key in (
                 'netspout_run_id','netspout_incident_id','netspout_scenario_id','netspout_site_id',
                 'netspout_device_id','netspout_phase','netspout_cell_id','netspout_service_id',
                 'netspout_subscriber_cohort','evidence_kind','interface','device_ip')))
            for key in ('slice_id','target_cell_id','remediation_executed'):
                if key in fields: raw+=' '+key+'='+fields[key]
            events.append(dict(time=fields['event_time'],host=host,source='netspout:telecom_incident',
                               sourcetype='netspout:telecom:log',index='idx_network_ops',raw=raw,fields=fields))
        fields=dict(events[-3]['fields'],sequence=len(events),event_time=start+len(events)/eps,
                    evidence_kind='simulated_observation')
        metrics={name:round(healthy+(peak-healthy)*factors[n]*(rng.uniform(.97,1.03) if n in (1,2) else 1),4)
                 for name,healthy,peak in kpis}
        events.append(dict(time=fields['event_time'],host=primary,source='netspout:telecom_incident',
                           sourcetype='netspout:telecom:metric',index='idx_performance_metrics',raw='metric',fields=fields,metrics=metrics))
    return events
