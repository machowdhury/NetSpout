"""C1 profile contracts, evidence gates and canonical/mirror compatibility (offline)."""
import copy
import json
from pathlib import Path
import runpy
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

from pydantic import ValidationError
from netspout_core.catalog import NetSpoutCatalog
from netspout_core.catalog_contracts import (
    CoverageState, IntegrationProfile, TelemetryCatalog, project_integration_identities,
)

ROOT = Path(__file__).resolve().parents[1]


class IntegrationProfileTests(unittest.TestCase):
    def setUp(self):
        self.raw = json.loads((ROOT / 'catalog/telemetry_catalog.json').read_text())
        self.catalog = TelemetryCatalog.model_validate(self.raw)

    def validate_profile(self, **changes):
        value = dict(profile_id='example-v1', vendor='Example', product='Example device',
                     integration_type='add_on')
        value.update(changes)
        return IntegrationProfile.model_validate(value)

    def test_multivendor_same_contract_and_unknowns(self):
        for vendor in ('Palo Alto', 'Fortinet', 'Juniper', 'AWS', 'Azure', 'VMware',
                       'NVIDIA', 'Healthcare', 'Industrial'):
            profile = self.validate_profile(vendor=vendor)
            self.assertIsNone(profile.app_version)
            self.assertEqual(profile.fields, [])
            self.assertEqual(profile.coverage, CoverageState.NOT_ASSESSED)
        self.assertEqual({s.value for s in CoverageState}, {
            'not_assessed', 'missing', 'partial', 'sample_ready', 'scenario_ready',
            'integration_verified'})

    def test_multiple_versions_and_methods_one_product(self):
        integration = self.raw['integrations'][0]
        integration['profiles'] = [self.validate_profile(
            profile_id=pid, app_version=version, collection_method=method,
            wire_format=fmt).model_dump(mode='json')
            for pid, version, method, fmt in (
                ('example-v1-api', '1.0', 'API', 'JSON'),
                ('example-v2-api', '2.0', 'API', 'JSON'),
                ('example-v2-file', '2.0', 'file', 'CSV'))]
        parsed = TelemetryCatalog.model_validate(self.raw)
        self.assertEqual(len(parsed.integrations[0].profiles), 3)

    def test_missing_unknown_or_inferred_schema_evidence_rejected(self):
        with self.assertRaises(ValidationError):
            self.validate_profile(fields=[dict(name='src', data_type='string', evidence_ids=[])])
        integration = self.raw['integrations'][0]
        value = self.validate_profile(evidence_ids=['absent'], fields=[dict(
            name='src', data_type='string', evidence_ids=['absent'])]).model_dump(mode='json')
        integration['profiles'] = [value]
        with self.assertRaises(ValidationError):
            TelemetryCatalog.model_validate(self.raw)
        evidence = self.raw['evidence'][0]
        value['evidence_ids'] = [evidence['evidence_id']]
        value['fields'][0]['evidence_ids'] = [evidence['evidence_id']]
        evidence.update(provenance='INFERRED', verification_state='RESEARCH_REQUIRED')
        with self.assertRaises(ValidationError):
            TelemetryCatalog.model_validate(self.raw)
        with self.assertRaises(ValidationError):
            self.validate_profile(fields=[dict(name='src', data_type='invented', evidence_ids=['x'])])

    def test_sample_and_scenario_promotion_gates(self):
        for coverage in ('sample_ready', 'scenario_ready', 'integration_verified'):
            with self.assertRaises(ValidationError):
                self.validate_profile(coverage=coverage)
        value = dict(schema_known=True, wire_format='JSON', collection_method='API',
                     verification_state='PARTIALLY_VERIFIED', evidence_ids=['sample'],
                     validations=[dict(kind='sample_schema', outcome='passed', evidence_ids=['sample'])])
        self.assertEqual(self.validate_profile(coverage='sample_ready', **value).coverage.value,
                         'sample_ready')
        with self.assertRaises(ValidationError):
            self.validate_profile(coverage='scenario_ready', **value)
        value['validations'].append(dict(kind='generator', outcome='passed', evidence_ids=['sample']))
        self.assertEqual(self.validate_profile(coverage='scenario_ready', **value).coverage.value,
                         'scenario_ready')
        with self.assertRaises(ValidationError):
            self.validate_profile(coverage='integration_verified', **value)

    def verified_candidate(self):
        eid = 'C1-TEST-DATASET'
        self.raw['evidence'].append(dict(evidence_id=eid, title='Dummy parser fixture',
            publisher='Test', reference='fixture://dummy', provenance='DATASET_VERIFIED',
            verification_state='VERIFIED'))
        value = self.validate_profile(app_version='1.0', schema_known=True,
            coverage='integration_verified', verification_state='VERIFIED',
            collection_method='API', wire_format='JSON', platforms=['splunk_enterprise'],
            evidence_ids=[eid], validations=[dict(kind=kind, outcome='passed', app_version='1.0',
                platform='splunk_enterprise', evidence_ids=[eid])
                for kind in ('sample_schema', 'parser', 'field_extraction')]).model_dump(mode='json')
        self.raw['integrations'][0]['profiles'] = [value]
        return value, eid

    def test_integration_verification_requires_exact_version_platform_and_dataset(self):
        value, eid = self.verified_candidate()
        TelemetryCatalog.model_validate(self.raw)
        for mutation in ('version', 'platform', 'evidence', 'failure', 'missing'):
            candidate = copy.deepcopy(self.raw)
            profile = candidate['integrations'][0]['profiles'][0]
            validation = profile['validations'][1]
            if mutation == 'version':
                validation['app_version'] = '2.0'
            elif mutation == 'platform':
                validation['platform'] = 'splunk_cloud'
            elif mutation == 'evidence':
                candidate['evidence'][-1]['provenance'] = 'SPLUNK_DOCUMENTED'
            elif mutation == 'failure':
                validation['outcome'] = 'failed'
            else:
                profile['validations'].pop()
            with self.assertRaises(ValidationError, msg=mutation):
                TelemetryCatalog.model_validate(candidate)

    def test_cim_dashboard_results_need_separate_evidence(self):
        value, eid = self.verified_candidate()
        value['validations'].append(dict(kind='dashboard', outcome='passed',
            app_version='2.0', platform='splunk_enterprise', evidence_ids=[eid]))
        with self.assertRaises(ValidationError):
            TelemetryCatalog.model_validate(self.raw)
        value['validations'][-1]['app_version'] = '1.0'
        TelemetryCatalog.model_validate(self.raw)

    def test_profile_identity_conflicts_rejected(self):
        candidate = copy.deepcopy(self.raw)
        profiles = [p for i in candidate['integrations'] for p in i.get('profiles', [])]
        profiles[1]['profile_id'] = profiles[0]['profile_id']
        with self.assertRaises(ValidationError):
            TelemetryCatalog.model_validate(candidate)
        with self.assertRaises(ValidationError):
            self.validate_profile(splunkbase_id='5580', splunkbase_url='https://splunkbase.splunk.com/app/7538')
        candidate = copy.deepcopy(self.raw)
        for i in candidate['integrations']:
            if i['splunkbase_id'] == '5580':
                i['profiles'][0]['splunkbase_id'] = '7538'
                i['profiles'][0]['splunkbase_url'] = 'https://splunkbase.splunk.com/app/7538'
        with self.assertRaises(ValidationError):
            TelemetryCatalog.model_validate(candidate)

    def test_identity_projection_preserves_stable_ids_and_other_fields(self):
        vendors = json.loads((ROOT / 'catalog/vendors.json').read_text())
        before = copy.deepcopy(vendors)
        result = project_integration_identities(vendors, self.catalog)
        self.assertEqual(vendors, before)
        self.assertEqual(result, project_integration_identities(result, self.catalog))
        by_id = {v['id']: v for v in result}
        for vid, appid in [('cisco_meraki', '5580'), ('cisco_sdwan', '7538')]:
            self.assertEqual(by_id[vid]['splunkbase_id'], appid)
        for old, new in zip(vendors, result):
            for key in set(old) - {'splunk_app_name', 'splunkbase_id', 'splunkbase_url'}:
                self.assertEqual(old[key], new[key])
        with self.assertRaises(ValueError):
            project_integration_identities([], self.catalog)

    def test_duplicate_legacy_defaults_fail_closed(self):
        profiles = [p for i in self.raw['integrations'] for p in i.get('profiles', [])
                    if p.get('legacy_catalog_default')]
        profiles[1]['vendor_id'] = profiles[0]['vendor_id']
        with self.assertRaises(ValidationError):
            TelemetryCatalog.model_validate(self.raw)

    def test_ucs_source_is_not_a_sourcetype_and_cisco_not_verified(self):
        profiles = [p for i in self.catalog.integrations for p in i.profiles]
        self.assertTrue(profiles)
        self.assertTrue(all(p.coverage == CoverageState.NOT_ASSESSED for p in profiles))
        ucs = next(p for p in profiles if p.product == 'UCS')
        self.assertEqual([s.name for s in ucs.sourcetypes], ['cisco:ucs'])
        self.assertIn('cisco:ucs:faultInst', [r.value for r in ucs.requirements if r.kind == 'source'])
        self.assertFalse(any(p.validations for p in profiles))

    def test_legacy_catalog_without_profiles_still_valid_and_runtime_exposes_profiles(self):
        for integration in self.raw['integrations']:
            integration.pop('profiles', None)
        TelemetryCatalog.model_validate(self.raw)
        integration = NetSpoutCatalog().get_splunk_integration('splunkbase-cisco-meraki-5580')
        self.assertEqual(integration['profiles'][0]['vendor_id'], 'cisco_meraki')

    def test_generation_uses_same_projection_in_isolated_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'scripts').mkdir()
            (root / 'catalog').mkdir()
            script = root / 'scripts/build_canonical_catalog.py'
            shutil.copyfile(ROOT / 'scripts/build_canonical_catalog.py', script)
            for name in ('vendors.json', 'telemetry_catalog.json'):
                shutil.copyfile(ROOT / 'catalog' / name, root / 'catalog' / name)
            vendors = json.loads((root / 'catalog/vendors.json').read_text())
            for vendor in vendors:
                if vendor['id'] == 'cisco_sdwan':
                    vendor.update(splunkbase_id='5580', splunkbase_url='https://splunkbase.splunk.com/app/5580')
            (root / 'catalog/vendors.json').write_text(json.dumps(vendors))
            old_path = sys.path[:]
            try:
                with patch.object(sys, 'argv', [str(script), '--integration-profiles-only']):
                    with self.assertRaises(SystemExit) as stopped:
                        runpy.run_path(str(script), run_name='__main__')
                    self.assertEqual(stopped.exception.code, 0)
            finally:
                sys.path[:] = old_path
            self.assertEqual(json.loads((root / 'catalog/vendors.json').read_text()),
                             project_integration_identities(vendors, self.catalog))
            self.assertEqual(sorted(p.name for p in (root / 'catalog').iterdir()),
                             ['telemetry_catalog.json', 'vendors.json'])
        source = (ROOT / 'scripts/build_canonical_catalog.py').read_text()
        self.assertIn('canonical_vendors = project_profile_defaults(canonical_vendors, CATALOG_DIR)', source)

    def test_all_generated_copies_match(self):
        module = (ROOT / 'src/netspout_core/catalog_contracts.py').read_bytes()
        self.assertEqual(module, (ROOT / 'netspout/bin/netspout_core/catalog_contracts.py').read_bytes())
        for path in ('netspout/bin/catalog_contracts.py', 'backend/app/catalog_contracts.py'):
            self.assertTrue((ROOT / path).read_bytes().endswith(module))
        for name in ('vendors.json', 'telemetry_catalog.json'):
            canonical = (ROOT / 'catalog' / name).read_bytes()
            for mirror in ('netspout/bin/netspout_core/catalog_data', 'netspout/bin/catalog_data',
                           'backend/app/catalog_data', 'netspout/catalog'):
                self.assertEqual(canonical, (ROOT / mirror / name).read_bytes())
        runtime = NetSpoutCatalog().get_legacy_vendor_catalog()
        self.assertEqual(runtime, json.loads((ROOT / 'netspout/appserver/static/vendor_catalog.json').read_text()))
