#!/usr/bin/env python3
"""
NetSpout Gate 3 Test Suite: Canonical Catalog, Identifiers, and Metadata
Tests:
1. Authoritative Catalog Loading (vendors, sourcetypes, scenarios, device_types, topologies, samples, protocols, aliases)
2. Typo & Deprecation Resolution (cisco:sdwan:sytem:logs -> cisco:sdwan:system:logs)
3. Duplicate ID Disambiguation (nutanixpc-syslog / nutanixpc-syslog-colon)
4. Schema & Reference Validation (0 schema errors, 0 broken references)
5. Legacy Compatibility (vendor_catalog.py and vendor_catalog.json)
6. Telemetry Generation Mode Classification
7. Device Types & Topologies Consistency
8. Telemetry Protocols Completeness
"""

import os
import sys
import json
import unittest

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC_DIR = os.path.join(REPO_ROOT, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from netspout_core.catalog import NetSpoutCatalog, catalog
from netspout_core.vendor_catalog import (
    VENDOR_CATALOG,
    list_all_vendors,
    get_vendor_by_id,
    get_sourcetypes_by_vendor,
    get_all_sourcetypes
)


class TestGate3CanonicalCatalog(unittest.TestCase):

    def test_01_catalog_entity_counts(self):
        """Verify canonical catalog entity counts meet or exceed Gate 3 requirements."""
        vendors = catalog.list_vendors()
        self.assertEqual(len(vendors), 36, "Catalog must contain exactly 36 enterprise vendors")

        sourcetypes = catalog.list_sourcetypes(include_deprecated=True)
        self.assertGreaterEqual(len(sourcetypes), 260, "Catalog must contain >= 260 sourcetypes")

        scenarios = catalog.list_scenarios()
        self.assertEqual(len(scenarios), 29, "Catalog must contain 29 scenarios")

        device_types = catalog.list_device_types()
        self.assertEqual(len(device_types), 17, "Catalog must contain 17 device types")

        topologies = catalog.list_topologies()
        self.assertEqual(len(topologies), 28, "Catalog must contain 28 topologies")

        samples = catalog.list_samples()
        self.assertEqual(len(samples), 213, "Catalog must contain 213 sample datasets")

        protocols = catalog.list_protocols()
        self.assertEqual(len(protocols), 8, "Catalog must contain 8 telemetry protocols")

        aliases = catalog.list_aliases()
        self.assertGreaterEqual(len(aliases), 40, "Catalog must contain >= 40 alias mappings")

    def test_02_typo_sourcetype_resolution(self):
        """Verify cisco:sdwan:sytem:logs resolves cleanly to cisco:sdwan:system:logs."""
        # 1. Direct resolution
        can_st, is_dep, can_id = catalog.resolve_sourcetype("cisco:sdwan:sytem:logs")
        self.assertEqual(can_st, "cisco:sdwan:system:logs")
        self.assertTrue(is_dep, "Typo sourcetype must be marked deprecated")
        self.assertEqual(can_id, "cisco-sdwan-system-logs")

        # 2. Lookup via alias
        st_obj = catalog.get_sourcetype("cisco:sdwan:sytem:logs")
        self.assertIsNotNone(st_obj)
        self.assertEqual(st_obj["splunk_sourcetype"], "cisco:sdwan:system:logs")
        self.assertEqual(st_obj["sourcetype"], "cisco:sdwan:system:logs")

        # 3. Canonical sourcetype itself
        can_st2, is_dep2, can_id2 = catalog.resolve_sourcetype("cisco:sdwan:system:logs")
        self.assertEqual(can_st2, "cisco:sdwan:system:logs")
        self.assertFalse(is_dep2)

        # 4. Filter behavior
        active_sts = [s["sourcetype"] for s in catalog.list_sourcetypes(include_deprecated=False)]
        all_sts = [s["sourcetype"] for s in catalog.list_sourcetypes(include_deprecated=True)]
        self.assertIn("cisco:sdwan:system:logs", active_sts)
        self.assertNotIn("cisco:sdwan:sytem:logs", active_sts)
        self.assertIn("cisco:sdwan:sytem:logs", all_sts)

    def test_03_duplicate_id_resolution(self):
        """Verify DEF-04 duplicate IDs are disambiguated and resolvable."""
        sample_colon = catalog.get_sample("nutanixpc-syslog-colon")
        self.assertIsNotNone(sample_colon)
        self.assertEqual(sample_colon["sourcetype"], "nutanixpc:syslog")

        sample_legacy = catalog.get_sample("nutanixpc-syslog")
        self.assertIsNotNone(sample_legacy)
        self.assertEqual(sample_legacy["sourcetype"], "nutanixpc_syslog")

        sample_vms_colon = catalog.get_sample("nutanixpc-vms-colon")
        self.assertIsNotNone(sample_vms_colon)
        self.assertEqual(sample_vms_colon["sourcetype"], "nutanixpc:vms")

        sample_vms = catalog.get_sample("nutanixpc-vms")
        self.assertIsNotNone(sample_vms)
        self.assertEqual(sample_vms["sourcetype"], "nutanixpc_vms")

    def test_04_schema_and_reference_validation(self):
        """Verify validate_catalog() returns 0 errors."""
        scripts_dir = os.path.join(REPO_ROOT, "scripts")
        if scripts_dir not in sys.path:
            sys.path.insert(0, scripts_dir)
        from validate_catalog import validate_catalog

        is_valid, errors, orphans = validate_catalog()
        self.assertTrue(is_valid, f"Catalog validation failed with errors: {errors}")
        self.assertEqual(len(errors), 0)
        self.assertEqual(len(orphans["orphan_vendors"]), 0, "No orphan vendors allowed")
        self.assertEqual(len(orphans["orphan_topologies"]), 0, "No orphan topologies allowed")

    def test_05_legacy_vendor_catalog_compatibility(self):
        """Verify vendor_catalog.py wrapper and static vendor_catalog.json match catalog."""
        self.assertEqual(len(VENDOR_CATALOG), 36)
        self.assertEqual(len(list_all_vendors()), 36)

        cisco = get_vendor_by_id("cisco_sdwan")
        self.assertIsNotNone(cisco)
        self.assertEqual(cisco["vendor"], "Cisco Systems")

        palo = get_vendor_by_id("paloalto-panos")
        self.assertIsNotNone(palo)
        self.assertEqual(palo["vendor"], "Palo Alto Networks")

        all_sts = get_all_sourcetypes()
        self.assertGreaterEqual(len(all_sts), 200)

        # Check vendor_catalog.json mirror
        static_json = os.path.join(REPO_ROOT, "netspout", "appserver", "static", "vendor_catalog.json")
        self.assertTrue(os.path.exists(static_json))
        with open(static_json, "r", encoding="utf-8") as f:
            static_vendors = json.load(f)
        self.assertEqual(len(static_vendors), 36)
        self.assertEqual(len(static_vendors), len(VENDOR_CATALOG))

    def test_06_generation_mode_classification(self):
        """Verify generation mode classification logic."""
        # Scenario derived
        mode_sc = catalog.get_generation_mode("cisco_sdwan_brownout")
        self.assertIn(mode_sc, ("STATEFUL", "SCENARIO_DERIVED"))

        # Sample replay
        mode_sample = catalog.get_generation_mode("cisco-ios-syslog")
        self.assertEqual(mode_sample, "REPLAY")

        # Sourcetype with sample file -> REPLAY
        mode_pan = catalog.get_generation_mode("pan:traffic")
        self.assertEqual(mode_pan, "REPLAY")

        # Sourcetype synthetic
        mode_syn = catalog.get_generation_mode("arista:telemetry:json")
        self.assertEqual(mode_syn, "SYNTHETIC")

    def test_07_device_types_and_topologies(self):
        """Verify device types match NodeType enum and topologies have required fields."""
        from netspout_core.models import NodeType

        device_types = catalog.list_device_types()
        dt_ids = {dt["id"] for dt in device_types}
        enum_values = {nt.value for nt in NodeType}

        for val in enum_values:
            self.assertIn(val, dt_ids, f"NodeType.{val} must be in catalog device types")

        topologies = catalog.list_topologies()
        for top in topologies:
            self.assertIn("id", top)
            self.assertIn("name", top)
            self.assertIn("ecosystem", top)
            self.assertIn("node_count", top)
            self.assertIn("edge_count", top)

    def test_08_protocols(self):
        """Verify 8 telemetry protocols."""
        protocols = catalog.list_protocols()
        proto_ids = {p["id"] for p in protocols}
        expected_protocols = {
            "syslog_rfc5424",
            "syslog_rfc3164",
            "hec_event",
            "hec_metric",
            "snmp_sc4snmp",
            "gnmi_openconfig",
            "otlp_http",
            "telegraf_influx"
        }
        self.assertEqual(proto_ids, expected_protocols)


if __name__ == "__main__":
    unittest.main()
