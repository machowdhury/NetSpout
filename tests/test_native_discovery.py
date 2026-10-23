"""C5 offline contracts, generated relationships and native browser behavior."""
import importlib.util
import json
from pathlib import Path
import subprocess
import unittest
from xml.etree import ElementTree as ET
from netspout_core.dashboard_recipes import DashboardRecipeRegistry

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('c5_build', ROOT/'scripts/build_discovery_catalog.py')
build=importlib.util.module_from_spec(spec);spec.loader.exec_module(build)

class NativeDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=build.build();cls.entries=cls.data['entries']
        cls.recipes=json.loads((ROOT/'catalog/dashboard_recipes.json').read_text())

    def test_projection_is_reproducible_and_not_a_registry(self):
        self.assertEqual(self.data,build.build())
        build.generate(check=True)
        self.assertIn('Generated from canonical',self.data['provenance'])

    def test_all_native_incidents_have_primary_dashboard(self):
        native=[x for x in self.entries if x['kind']=='scenario' and x['id'].startswith(('network_','telco_'))]
        self.assertEqual(len(native),37)
        self.assertTrue(all(x['dashboard_ids'] for x in native))
        self.assertTrue(all(x['readiness']=='Executable custom simulation' for x in native))
        self.assertEqual(next(x for x in native if x['id']=='network_08_firewall_policy')['dashboard_ids'][0],'discovery-security')

    def test_bidirectional_source_and_dashboard_links(self):
        by={(x['kind'],x['id']):x for x in self.entries}
        for row in self.entries:
            for sid in row.get('scenario_ids',[]): self.assertIn(('scenario',sid),by)
            for did in row.get('dashboard_ids',[]): self.assertIn(('dashboard',did),by)
            for st in row.get('sourcetypes',[]): self.assertIn(('sourcetype',st),by)
            if row['kind']=='scenario':
                for st in row['sourcetypes']: self.assertIn(row['id'],by['sourcetype',st]['scenario_ids'])

    def test_research_attribution_not_promoted_to_schema(self):
        refs=[r for r in self.entries if r['kind']=='use_case']
        self.assertEqual(len(refs),36)
        self.assertTrue(all(r['sourcetypes']==[] and r['evidence'][0]['reference'].startswith('https://raw.githubusercontent.com/fenre/') for r in refs))
        self.assertFalse(any('integration_verified'==r['readiness'] for r in refs))
        text=json.dumps(self.data).lower()
        self.assertNotIn('phantom',text);self.assertNotIn('soar',text)

    def test_catalog_contract_and_legacy_recipes(self):
        registry=DashboardRecipeRegistry.model_validate(self.recipes)
        self.assertEqual(len([r for r in registry.recipes if r.native_view]),4)
        baseline=json.loads(subprocess.check_output(['git','show','HEAD:catalog/dashboard_recipes.json'],cwd=ROOT))
        self.assertEqual([r for r in self.recipes['recipes'] if not r.get('native_view')],[r for r in baseline['recipes'] if not r.get('native_view')])

    def test_navigation_and_dashboard_queries(self):
        nav=ET.parse(ROOT/'netspout/default/data/ui/nav/default.xml')
        views={v.attrib['name'] for v in nav.iter('view')}
        for name in ['pulseforge_discovery','pulseforge_security','pulseforge_network','pulseforge_application','pulseforge_telecom']:
            self.assertIn(name,views)
            tree=ET.parse(ROOT/'netspout/default/data/ui/views'/ (name+'.xml'))
            if name=='pulseforge_discovery': continue
            for query in tree.iter('query'):
                self.assertTrue('index=$index|s$' in query.text or 'index=$metric_index|s$' in query.text)
                self.assertIn('netspout_run_id=$run_id|s$',query.text)
                self.assertNotIn('makeresults',query.text)
            self.assertIn('MISSING_FIELDS',ET.tostring(tree.getroot(),encoding='unicode'))
            self.assertEqual(len(list(tree.iter('earliest'))),6 if name=='pulseforge_telecom' else 5)
            self.assertTrue(all(e.text=='$window$' for e in tree.iter('earliest')))

    def test_query_fields_exist_in_incident_producers(self):
        for recipe in self.recipes['recipes']:
            if not recipe.get('native_view'): continue
            for field in recipe['required_fields']:
                # Telecom-specific fields must exist in their declared producer,
                # not in the unrelated network producer as well.
                provenance=recipe['field_provenance'][field]
                producer=provenance.split(':')[0]
                self.assertIn(field,(ROOT/producer).read_text())

    def test_generated_core_and_catalog_mirrors(self):
        source=(ROOT/'src/netspout_core/dashboard_recipes.py').read_bytes()
        for path in ('backend/app/dashboard_recipes.py','netspout/bin/dashboard_recipes.py','netspout/bin/netspout_core/dashboard_recipes.py'):
            self.assertTrue((ROOT/path).read_bytes().endswith(source))
        source=(ROOT/'catalog/dashboard_recipes.json').read_bytes()
        for base in ('backend/app/catalog_data','netspout/bin/catalog_data','netspout/bin/netspout_core/catalog_data','netspout/catalog'):
            self.assertEqual((ROOT/base/'dashboard_recipes.json').read_bytes(),source)

    def test_browser_search_and_detail_behavior(self):
        result=subprocess.run(['node',str(ROOT/'tests/native_discovery_browser.cjs')],cwd=ROOT,text=True,capture_output=True,timeout=20)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('browser assertions passed',result.stdout)
