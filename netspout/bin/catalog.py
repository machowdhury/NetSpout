# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/catalog.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""
NetSpout Canonical Metadata Catalog & Identity Registry
Authoritative source for:
- Vendors (36 enterprise vendors, categories, CIM mappings)
- Sourcetypes (263 unified sourcetypes, metadata, indices, TAs)
- Scenarios (29 baseline, enterprise, architecture scenarios)
- Device Types (17 node types, hardware profiles, protocols)
- Topologies (28 topologies & architecture presets)
- Samples (213 sample datasets, mappings, paths)
- Protocols (Syslog RFC5424/3164, HEC, SC4SNMP, gNMI MDT, OTLP, Telegraf)
- Aliases & Deprecation mappings (cisco-sdwan-sytem-logs -> system-logs)
"""

import os
import json
import re
from typing import Dict, List, Any, Optional, Tuple, Set


def _find_catalog_dir() -> str:
    """Locate the canonical catalog directory across development and Splunk runtimes."""
    module_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.abspath(os.path.join(module_dir, "..", "..", "catalog")),
        os.path.join(module_dir, "catalog_data"),
        os.path.join(os.path.dirname(module_dir), "catalog"),
        os.path.join(os.path.dirname(module_dir), "catalog_data"),
        os.path.join(module_dir, "catalog"),
        "/opt/splunk/etc/apps/netspout/catalog",
        "/opt/splunk/etc/apps/netspout/bin/catalog_data",
        "/opt/splunk/etc/apps/netspout/bin/netspout_core/catalog_data",
        "/opt/splunk/etc/apps/TA-network-data-blaster/catalog",
        "/opt/splunk/etc/apps/TA-network-data-blaster/bin/catalog_data"
    ]
    for cand in candidates:
        if os.path.isdir(cand) and os.path.exists(os.path.join(cand, "vendors.json")):
            return cand
    return os.path.abspath(os.path.join(module_dir, "..", "..", "catalog"))


class NetSpoutCatalog:
    """
    Authoritative single catalog interface for all NetSpout metadata,
    schemas, identifiers, and compatibility aliases.
    """
    def __init__(self, catalog_dir: Optional[str] = None):
        self.catalog_dir = catalog_dir or _find_catalog_dir()
        self._vendors: List[Dict[str, Any]] = []
        self._sourcetypes: List[Dict[str, Any]] = []
        self._scenarios: List[Dict[str, Any]] = []
        self._device_types: List[Dict[str, Any]] = []
        self._topologies: List[Dict[str, Any]] = []
        self._samples: List[Dict[str, Any]] = []
        self._protocols: List[Dict[str, Any]] = []
        self._aliases: Dict[str, Dict[str, Any]] = {}

        self._vendors_by_id: Dict[str, Dict[str, Any]] = {}
        self._sourcetypes_by_st: Dict[str, Dict[str, Any]] = {}
        self._sourcetypes_by_id: Dict[str, Dict[str, Any]] = {}
        self._scenarios_by_id: Dict[str, Dict[str, Any]] = {}
        self._device_types_by_id: Dict[str, Dict[str, Any]] = {}
        self._topologies_by_id: Dict[str, Dict[str, Any]] = {}
        self._samples_by_id: Dict[str, Dict[str, Any]] = {}
        self._protocols_by_id: Dict[str, Dict[str, Any]] = {}

        self._load()

    def _load(self):
        def _read_json(fname: str) -> Any:
            p = os.path.join(self.catalog_dir, fname)
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as fp:
                    return json.load(fp)
            return [] if not fname.endswith("aliases.json") else {}

        self._vendors = _read_json("vendors.json")
        self._sourcetypes = _read_json("sourcetypes.json")
        self._scenarios = _read_json("scenarios.json")
        self._device_types = _read_json("device_types.json")
        self._topologies = _read_json("topologies.json")
        self._samples = _read_json("samples.json")
        self._protocols = _read_json("telemetry_protocols.json")
        self._aliases = _read_json("aliases.json")

        # Build fast lookup indexes
        for v in self._vendors:
            self._vendors_by_id[v["id"]] = v
            if v.get("legacy_id"):
                self._vendors_by_id[v["legacy_id"]] = v
            if v.get("slug"):
                self._vendors_by_id[v["slug"]] = v

        for st in self._sourcetypes:
            st["sourcetype"] = st.get("splunk_sourcetype") or st.get("sourcetype")
            self._sourcetypes_by_st[st["splunk_sourcetype"]] = st
            self._sourcetypes_by_id[st["id"]] = st
            for a in st.get("aliases", []):
                self._sourcetypes_by_st[a] = st

        for sc in self._scenarios:
            self._scenarios_by_id[sc["id"]] = sc

        for dt in self._device_types:
            self._device_types_by_id[dt["id"]] = dt

        for top in self._topologies:
            self._topologies_by_id[top["id"]] = top

        for sm in self._samples:
            self._samples_by_id[sm["id"]] = sm

        for pr in self._protocols:
            self._protocols_by_id[pr["id"]] = pr

    # -------------------------------------------------------------------------
    # Vendors API
    # -------------------------------------------------------------------------
    def get_vendor(self, vendor_id: str) -> Optional[Dict[str, Any]]:
        vid_clean = vendor_id.lower().replace("-", "_")
        if vid_clean in self._vendors_by_id:
            return self._vendors_by_id[vid_clean]
        # Check aliases
        if vendor_id in self._aliases:
            target = self._aliases[vendor_id].get("canonical_id")
            if target in self._vendors_by_id:
                return self._vendors_by_id[target]
        # Loose match
        for v in self._vendors:
            if (v["id"] == vid_clean or 
                v.get("slug") == vid_clean or 
                v.get("legacy_id") == vendor_id):
                return v
        return None

    def list_vendors(self) -> List[Dict[str, Any]]:
        return list(self._vendors)

    def get_legacy_vendor_catalog(self) -> List[Dict[str, Any]]:
        """
        Returns VENDOR_CATALOG list in format matching legacy vendor_catalog.py
        for complete backwards compatibility with tests and Splunk views.
        """
        legacy_list = []
        for v in self._vendors:
            legacy_item = {
                "id": v.get("legacy_id") or v["id"],
                "vendor": v["name"],
                "vendor_slug": v.get("slug") or v["id"],
                "category": v.get("category"),
                "name": v.get("splunk_app_name"),
                "splunkbase_id": v.get("splunkbase_id"),
                "splunkbase_url": v.get("splunkbase_url"),
                "doc_url": v.get("doc_url"),
                "sourcetypes": v.get("primary_sourcetypes", []),
                "header_type": v.get("header_type"),
                "delimiter": v.get("delimiter"),
                "timestamp_format": v.get("timestamp_format"),
                "cim_models": v.get("cim_models", []),
                "field_mappings": v.get("field_mappings", {}),
                "sample_events": v.get("sample_events", {})
            }
            if "sample_event" in v:
                legacy_item["sample_event"] = v["sample_event"]
            if "cim_datamodels" in v:
                legacy_item["cim_datamodels"] = v["cim_datamodels"]
            if "cim_fields" in v:
                legacy_item["cim_fields"] = v["cim_fields"]
            legacy_list.append(legacy_item)
        return legacy_list

    # -------------------------------------------------------------------------
    # Sourcetypes & Alias Resolution API
    # -------------------------------------------------------------------------
    def get_sourcetype(self, sourcetype_or_alias: str, resolve_deprecated: bool = True) -> Optional[Dict[str, Any]]:
        st = None
        if sourcetype_or_alias in self._sourcetypes_by_st:
            st = self._sourcetypes_by_st[sourcetype_or_alias]
        elif sourcetype_or_alias in self._sourcetypes_by_id:
            st = self._sourcetypes_by_id[sourcetype_or_alias]
        elif sourcetype_or_alias in self._aliases:
            can_st = self._aliases[sourcetype_or_alias].get("canonical_sourcetype")
            if can_st in self._sourcetypes_by_st:
                return self._sourcetypes_by_st[can_st]

        if st and resolve_deprecated and st.get("status") == "deprecated" and st.get("canonical_sourcetype"):
            can = self._sourcetypes_by_st.get(st["canonical_sourcetype"])
            if can:
                return can
        return st

    def resolve_sourcetype(self, sourcetype_or_alias: str) -> Tuple[str, bool, str]:
        """
        Resolves any sourcetype string or alias to:
        (canonical_splunk_sourcetype, is_deprecated, canonical_id)
        """
        # 1. Direct alias table check
        if sourcetype_or_alias in self._aliases:
            alias_info = self._aliases[sourcetype_or_alias]
            can_st = alias_info.get("canonical_sourcetype")
            can_id = alias_info.get("canonical_id")
            is_dep = (alias_info.get("type") == "DEPRECATED_ALIAS")
            if can_st:
                return can_st, is_dep, can_id or can_st

        # 2. Sourcetype catalog lookup
        st_obj = self.get_sourcetype(sourcetype_or_alias)
        if not st_obj:
            return sourcetype_or_alias, False, sourcetype_or_alias

        # 3. Check if entry itself is deprecated and points to canonical
        if st_obj.get("status") == "deprecated" and st_obj.get("canonical_sourcetype"):
            return st_obj["canonical_sourcetype"], True, st_obj.get("canonical_id", st_obj["id"])

        is_deprecated = (
            st_obj.get("status") == "deprecated" or 
            sourcetype_or_alias in st_obj.get("deprecated_aliases", [])
        )
        return st_obj["splunk_sourcetype"], is_deprecated, st_obj["id"]

    def list_sourcetypes(
        self,
        vendor_id: Optional[str] = None,
        category: Optional[str] = None,
        include_deprecated: bool = True
    ) -> List[Dict[str, Any]]:
        results = self._sourcetypes
        if not include_deprecated:
            results = [s for s in results if s.get("status") != "deprecated"]
        if vendor_id:
            v = self.get_vendor(vendor_id)
            vid = v["id"] if v else vendor_id
            results = [s for s in results if s.get("vendor_id") == vid]
        if category:
            results = [s for s in results if s.get("category") == category]
        return list(results)

    # -------------------------------------------------------------------------
    # Scenarios API
    # -------------------------------------------------------------------------
    def get_scenario(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        return self._scenarios_by_id.get(scenario_id)

    def get_scenario_contract(self, scenario_id: str) -> Optional[Any]:
        sc = self.get_scenario(scenario_id)
        if not sc:
            return None
        try:
            from netspout_core.models import ScenarioContract
            return ScenarioContract(**sc)
        except Exception:
            try:
                from app.models import ScenarioContract
                return ScenarioContract(**sc)
            except Exception:
                try:
                    from models import ScenarioContract
                    return ScenarioContract(**sc)
                except Exception:
                    return sc

    def get_use_case(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        sc = self.get_scenario(scenario_id)
        if sc and sc.get("use_case"):
            return sc["use_case"]
        return None

    def list_scenarios(
        self,
        category: Optional[str] = None,
        ecosystem: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        results = self._scenarios
        if category:
            results = [s for s in results if s.get("category") == category]
        if ecosystem and ecosystem != "both":
            results = [s for s in results if s.get("ecosystem") in (ecosystem, "both")]
        return list(results)

    # -------------------------------------------------------------------------
    # Device Types API
    # -------------------------------------------------------------------------
    def get_device_type(self, dt_id: str) -> Optional[Dict[str, Any]]:
        return self._device_types_by_id.get(dt_id)

    def list_device_types(self) -> List[Dict[str, Any]]:
        return list(self._device_types)

    # -------------------------------------------------------------------------
    # Topologies API
    # -------------------------------------------------------------------------
    def get_topology(self, topology_id: str) -> Optional[Dict[str, Any]]:
        if topology_id in self._topologies_by_id:
            return self._topologies_by_id[topology_id]
        if topology_id in self._aliases:
            can_id = self._aliases[topology_id].get("canonical_id")
            if can_id in self._topologies_by_id:
                return self._topologies_by_id[can_id]
        return None

    def list_topologies(self) -> List[Dict[str, Any]]:
        return list(self._topologies)

    # -------------------------------------------------------------------------
    # Samples API
    # -------------------------------------------------------------------------
    def get_sample(self, sample_id: str) -> Optional[Dict[str, Any]]:
        return self._samples_by_id.get(sample_id)

    def list_samples(
        self,
        vendor_id: Optional[str] = None,
        sourcetype: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        results = self._samples
        if vendor_id:
            results = [s for s in results if s.get("vendor_id") == vendor_id]
        if sourcetype:
            results = [s for s in results if s.get("sourcetype") == sourcetype]
        return list(results)

    # -------------------------------------------------------------------------
    # Protocols API
    # -------------------------------------------------------------------------
    def get_protocol(self, proto_id: str) -> Optional[Dict[str, Any]]:
        return self._protocols_by_id.get(proto_id)

    def list_protocols(self) -> List[Dict[str, Any]]:
        return list(self._protocols)

    # -------------------------------------------------------------------------
    # Aliases API
    # -------------------------------------------------------------------------
    def resolve_alias(self, alias_key: str) -> Optional[Dict[str, Any]]:
        return self._aliases.get(alias_key)

    def list_aliases(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._aliases)

    # -------------------------------------------------------------------------
    # Generation Mode Classification
    # -------------------------------------------------------------------------
    def get_generation_mode(self, identifier: str) -> str:
        """
        Determines telemetry generation mode:
        REPLAY | SYNTHETIC | STATEFUL | SCENARIO_DERIVED
        """
        sc = self.get_scenario(identifier)
        if sc:
            return sc.get("generation_mode", "SCENARIO_DERIVED")
        st = self.get_sourcetype(identifier)
        if st:
            return st.get("generation_mode", "SYNTHETIC")
        sm = self.get_sample(identifier)
        if sm:
            return sm.get("generation_mode", "REPLAY")
        return "SYNTHETIC"


# Global singleton instance
catalog = NetSpoutCatalog()
catalog_instance = catalog

