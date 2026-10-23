"""C6 checks derive expectations from actual finite producer outputs, not labels."""
import json
from pathlib import Path
import subprocess
import unittest
from xml.etree import ElementTree as ET
import test_native_discovery as c5
from netspout_core.catalog import NetSpoutCatalog

ROOT=Path(__file__).resolve().parents[1]

class IncidentDashboardCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=c5.build.build()
        cls.incidents=c5.build.incident_contracts()
        cls.recipes={r['recipe_id']:r for r in c5.build.read('catalog/dashboard_recipes.json')['recipes']}

    def test_all_25_descriptor_verified_incidents_have_primary(self):
        self.assertEqual(len(self.incidents),25)
        native=[r for r in self.data['entries'] if r.get('executable')]
        self.assertEqual(len(native),25)
        for row in native:
            with self.subTest(scenario=row['id']):
                self.assertIn(row['id'],self.incidents)
                self.assertEqual(row['primary_dashboard_id'],row['dashboard_ids'][0])
                recipe=self.recipes[row['primary_dashboard_id']]
                self.assertIn(row['id'],recipe['selectors'])
                self.assertTrue(set(recipe['required_sourcetypes'])<=set(row['incident_contract']['log_sourcetypes']))
                self.assertTrue(set(recipe['metric_sourcetypes'])<=set(row['incident_contract']['metric_sourcetypes']))
                self.assertTrue(set(recipe['required_fields'])<=set(row['incident_contract']['log_fields']))
                self.assertTrue(row['incident_contract']['metric_names'])
                self.assertEqual(row['telemetry_status'],'NOT_CHECKED')

    def test_no_research_or_vendor_native_promotion(self):
        for row in self.data['entries']:
            if row['kind']=='use_case': self.assertFalse(row.get('executable',False))
            if row.get('executable'):
                self.assertEqual(row['vendors'],['PulseForge'])
                self.assertIn('custom',row['readiness'])
                self.assertIn('not established',' '.join(row['gaps']))
                self.assertTrue(row['prerequisites'])

    def test_field_provenance_has_actual_producer_identifiers(self):
        for r in self.recipes.values():
            if not r.get('native_view'):continue
            for field in r['required_fields']:
                provenance=r['field_provenance'][field]
                file=provenance.split(':')[0]
                self.assertIn(field,(ROOT/file).read_text())
            self.assertIn('event.time',r['field_provenance']['_time'])
            self.assertIn('metric_name:',r['field_provenance']['metric_name'])
            self.assertIn('Numeric',r['field_provenance']['_value'])

    def test_recipe_inventory_preserved(self):
        service=NetSpoutCatalog(str(ROOT/'catalog')).get_dashboard_recipe_service()
        ids=[r.recipe_id for r in service.registry.recipes]
        self.assertEqual(len(ids),34);self.assertEqual(len(set(ids)),34)
        old=json.loads(subprocess.check_output(['git','show','HEAD:catalog/dashboard_recipes.json'],cwd=ROOT))
        self.assertEqual(set(self.recipes),{r['recipe_id'] for r in old['recipes']})
        for r in old['recipes']:
            if not r.get('native_view'):self.assertEqual(self.recipes[r['recipe_id']],r)
        subprocess.run(['git','diff','--exit-code','--','catalog/phase12_dashboard_recipes.json'],cwd=ROOT,check=True)

    def test_scenario_filters_match_emitted_ids_and_are_escaped(self):
        for r in self.recipes.values():
            if not r.get('native_view'):continue
            root=ET.fromstring(c5.build.dashboard_xml(r))
            inputs={e.attrib['token']:e for e in root.iter('input')}
            choices={e.attrib['value'] for e in inputs['scenario_id'].iter('choice')}
            expected={self.incidents[s]['runtime_scenario_id'] for s in r['selectors']}
            self.assertEqual(choices,expected|{'*'})
            self.assertEqual({e.attrib['value'] for e in inputs['window'].iter('choice')},{'-15m','-1h','-24h','-7d'})
            for q in root.iter('query'):
                for token in ('run_id','scenario_id','entity'):
                    self.assertIn('$'+token+'|s$',q.text)
                    self.assertNotIn('$'+token+'$',q.text)
                self.assertTrue(all('netspout_scenario_id="'+s+'"' in q.text for s in expected))
            self.assertTrue(all(e.text=='$window$' for e in root.iter('earliest')))
            self.assertTrue(all(e.text=='now' for e in root.iter('latest')))

    def test_panels_have_onset_impact_entities_kpis_and_support(self):
        for r in self.recipes.values():
            if not r.get('native_view'):continue
            root=ET.fromstring(c5.build.dashboard_xml(r))
            spl='\n'.join(q.text for q in root.iter('query'))
            self.assertIn('first_failure',spl);self.assertIn('observed_span_seconds',spl)
            self.assertIn('min(severity)',spl);self.assertIn('dc(netspout_device_id)',spl)
            self.assertIn('mstats avg(_value)',spl);self.assertIn('BY metric_name',spl);self.assertIn('WHERE metric_name=*',spl)
            self.assertIn('phase_order=case(',spl);self.assertIn('severity _raw',spl)
            self.assertIn('MISSING_FIELDS',spl);self.assertIn('MISSING_DATA',spl)
            self.assertTrue(any(a.attrib.get('href','').startswith('pulseforge_discovery?q=') for a in root.iter('a')))
            if r['recipe_id']=='discovery-telecom':
                self.assertIn('max(affected_synthetic_subscribers)',spl)
                self.assertNotIn('sum(affected_synthetic_subscribers)',spl)

    def test_build_is_bounded_and_projection_reproducible(self):
        self.assertEqual(self.data,c5.build.build())
        c5.build.generate(check=True)
        self.assertEqual(self.data['executable_incident_count'],25)
