"""
NetSpout Companion Control Manifest.
Emits ground-truth control metadata to Splunk HEC for Step 5 ("Prove") verification
without corrupting binary flow records.
Conforms to Gate 11 Architecture Section 8 and Section 9.
"""

import json
import time
from typing import Dict, Any, List, Optional

from netspout_core.models import CompanionControlManifest, FlowRecord, TransportResult


class CompanionManifestBuilder:
    """
    Constructs companion control manifests linking simulated scenarios
    to external collector flow indexing.
    """

    @staticmethod
    def build_manifest(
        run_id: str,
        scenario_id: str,
        protocol: str,
        destination_host: str,
        destination_port: int,
        exporter_ip: str,
        observation_domain_id: int,
        template_ids: List[int],
        records_generated: int,
        records_encoded: int,
        datagrams_sent: int,
        bytes_sent: int,
        start_time_epoch_ms: int,
        end_time_epoch_ms: int,
        collector_sourcetype: str = "stream:netflow"
    ) -> CompanionControlManifest:
        """
        Creates a structured CompanionControlManifest with pre-constructed copyable SPL queries.
        """
        raw_spl = (
            f'search index=idx_network_ops sourcetype=netflow:collector '
            f'| spath '
            f'| search (observation_domain_id={observation_domain_id} OR ObservationDomainID={observation_domain_id} OR ObservationDomainId={observation_domain_id})'
        )
        table_spl = (
            f'{raw_spl} '
            f'| table _time src_addr dst_addr src_port dst_port proto bytes packets in_if out_if observation_domain_id'
        )
        stats_spl = (
            f'{raw_spl} '
            f'| stats count as total_flows sum(bytes) as total_bytes sum(packets) as total_packets by src_addr dst_addr src_port dst_port proto'
        )

        spl_query = (
            f'index=* sourcetype="{collector_sourcetype}" '
            f'earliest={int(start_time_epoch_ms / 1000) - 10} '
            f'latest={int(end_time_epoch_ms / 1000) + 10} '
            f'| stats count as observed_flows, sum(bytes) as total_bytes by src_addr, dst_addr, dst_port'
        )

        return CompanionControlManifest(
            run_id=run_id,
            scenario_id=scenario_id,
            protocol=protocol,
            destination_host=destination_host,
            destination_port=destination_port,
            observation_domain_id=observation_domain_id,
            exporter_ip=exporter_ip,
            template_ids=template_ids,
            records_generated=records_generated,
            records_encoded=records_encoded,
            datagrams_sent=datagrams_sent,
            bytes_sent=bytes_sent,
            start_time_epoch_ms=start_time_epoch_ms,
            end_time_epoch_ms=end_time_epoch_ms,
            fidelity_badge="NATIVE TRANSPORT",
            splunk_suggested_spl=spl_query,
            splunk_raw_events_spl=raw_spl,
            splunk_stats_spl=stats_spl,
            pipeline_stage="SENT"
        )

    @staticmethod
    def build_snmp_manifest(
        run_id: str,
        scenario_id: str,
        pdu_mode: str,
        destination_host: str,
        destination_port: int,
        exporter_ip: str,
        request_ids: List[int],
        acknowledged_request_ids: List[int],
        trap_oids: List[str],
        pdus_generated: int,
        pdus_encoded: int,
        datagrams_sent: int,
        bytes_sent: int,
        informs_acknowledged: int,
        inform_retries: int,
        inform_timeouts: int,
        receiver_observed_count: int,
        evidence_stage: str,
        start_time_epoch_ms: int,
        end_time_epoch_ms: int,
        collector_sourcetype: str = "sc4snmp:traps",
    ) -> CompanionControlManifest:
        """
        Constructs an out-of-band CompanionControlManifest for Native SNMPv2c Trap/Inform runs
        correlating wire PDUs via deterministic 31-bit request-id values without polluting wire varbinds.
        """
        req_filter = " OR ".join(f"request_id={rid}" for rid in request_ids) if request_ids else "request_id=*"
        raw_spl = (
            f'search index=idx_network_ops (sourcetype="{collector_sourcetype}" OR sourcetype="snmptrapd:collector") '
            f'| spath | search ({req_filter})'
        )
        stats_spl = (
            f'{raw_spl} '
            f'| stats count as total_notifications values(snmpTrapOID) as trap_oids by host request_id pdu_type'
        )
        protocol_label = f"SNMPV2C_{pdu_mode.upper()}" if pdu_mode.upper() in ("TRAP", "INFORM") else "SNMPV2C"

        return CompanionControlManifest(
            run_id=run_id,
            scenario_id=scenario_id,
            protocol=protocol_label,
            destination_host=destination_host,
            destination_port=destination_port,
            observation_domain_id=1,
            exporter_ip=exporter_ip,
            template_ids=[],
            records_generated=pdus_generated,
            records_encoded=pdus_encoded,
            datagrams_sent=datagrams_sent,
            bytes_sent=bytes_sent,
            start_time_epoch_ms=start_time_epoch_ms,
            end_time_epoch_ms=end_time_epoch_ms,
            fidelity_badge="NATIVE TRANSPORT",
            splunk_suggested_spl=raw_spl,
            splunk_raw_events_spl=raw_spl,
            splunk_stats_spl=stats_spl,
            pipeline_stage=evidence_stage,
            pdu_mode=pdu_mode.upper(),
            request_ids=list(request_ids),
            acknowledged_request_ids=list(acknowledged_request_ids),
            trap_oids=list(trap_oids),
            informs_acknowledged=informs_acknowledged,
            inform_retries=inform_retries,
            inform_timeouts=inform_timeouts,
            receiver_observed_count=receiver_observed_count,
        )

    @staticmethod
    def build_snmp_polling_manifest(
        run_id: str,
        scenario_id: str,
        bind_host: str,
        bind_port: int,
        exporter_ip: str,
        simulated_device_ids: List[str],
        exposed_oid_count: int,
        mib_families: List[str],
        requests_received: int,
        get_requests: int,
        getnext_requests: int,
        getbulk_requests: int,
        responses_sent: int,
        malformed_requests: int,
        set_rejected: int,
        evidence_stage: str,
        start_time_epoch_ms: int,
        end_time_epoch_ms: int,
    ) -> CompanionControlManifest:
        """
        Constructs an out-of-band CompanionControlManifest for Native SNMPv2c Polling Agent runs
        without injecting any proprietary NetSpout correlation OIDs into the MIB tree.
        """
        dev_filter = (
            " OR ".join(f'device_id="{d}"' for d in simulated_device_ids)
            if simulated_device_ids
            else 'device_id="*"'
        )
        raw_spl = (
            f'search index=idx_network_ops sourcetype="netspout:control:manifest" run_id="{run_id}" '
            f'| spath | search ({dev_filter})'
        )
        stats_spl = (
            f'{raw_spl} '
            f'| table _time run_id scenario_id snmp_agent_bind_host snmp_agent_port exposed_oid_count '
            f'snmp_get_requests snmp_getnext_requests snmp_getbulk_requests snmp_responses_sent pipeline_stage'
        )
        return CompanionControlManifest(
            run_id=run_id,
            scenario_id=scenario_id,
            protocol="SNMPV2C_POLL",
            destination_host=bind_host,
            destination_port=bind_port,
            observation_domain_id=1,
            exporter_ip=exporter_ip,
            template_ids=[],
            records_generated=exposed_oid_count,
            records_encoded=responses_sent,
            datagrams_sent=responses_sent,
            bytes_sent=0,
            start_time_epoch_ms=start_time_epoch_ms,
            end_time_epoch_ms=end_time_epoch_ms,
            fidelity_badge="NATIVE TRANSPORT",
            splunk_suggested_spl=raw_spl,
            splunk_raw_events_spl=raw_spl,
            splunk_stats_spl=stats_spl,
            pipeline_stage=evidence_stage,
            pdu_mode="POLL",
            snmp_agent_bind_host=bind_host,
            snmp_agent_port=bind_port,
            exposed_oid_count=exposed_oid_count,
            mib_families=list(mib_families),
            snmp_requests_received=requests_received,
            snmp_get_requests=get_requests,
            snmp_getnext_requests=getnext_requests,
            snmp_getbulk_requests=getbulk_requests,
            snmp_responses_sent=responses_sent,
            snmp_malformed_requests=malformed_requests,
            snmp_set_rejected=set_rejected,
            simulated_device_ids=list(simulated_device_ids),
        )

    @staticmethod
    def to_hec_event(manifest: CompanionControlManifest) -> Dict[str, Any]:
        """
        Formats the manifest as a Splunk HEC event for index idx_network_ops.
        """
        return {
            "time": time.time(),
            "host": manifest.exporter_ip,
            "source": "netspout:native_transport:manifest",
            "sourcetype": "netspout:control:manifest",
            "index": "idx_network_ops",
            "event": manifest.model_dump() if hasattr(manifest, "model_dump") else manifest.dict()
        }
