# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/companion_manifest.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
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
        Creates a structured CompanionControlManifest with a pre-constructed SPL search query.
        """
        spl_query = (
            f'index=* sourcetype="{collector_sourcetype}" '
            f'earliest={int(start_time_epoch_ms / 1000) - 10} '
            f'latest={int(end_time_epoch_ms / 1000) + 10} '
            f'| stats count as observed_flows, sum(bytes) as total_bytes by src_ip, dest_ip, dest_port'
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
            splunk_suggested_spl=spl_query
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
