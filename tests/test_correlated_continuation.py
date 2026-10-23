"""Remaining six C7 proposals; owned simulation contracts only."""
import json
from pathlib import Path
import subprocess
import types
import unittest
import test_network_incidents as fixtures
import test_native_discovery as discovery

pack=fixtures.pack
ROOT=Path(__file__).resolve().parents[1]
NEW={'22_authentication_storm':3,'23_containment_request':4,'24_policy_disagreement':7,
     '25_mpls_recovery':10,'26_maintenance':11,'27_stale_sessions':12}

class CorrelatedContinuationTests(unittest.TestCase):
    def events(self,slug,seed=42):return pack.generate(slug,seed,1700000000,fixtures.RUN,10)

    def test_six_distinct_descriptors_and_proposals(self):
        self.assertEqual(len(pack.CATALOG),27)
        for slug,proposal in NEW.items():
            with self.subTest(slug=slug):
                self.assertEqual(pack.descriptor(fixtures.FOLDER/('scenario_network_'+slug+'.yml'))['pulseforge_incident'],slug)
                self.assertEqual(pack.CATALOG[slug][13]['proposal'],proposal)

    def test_executable_correlated_lifecycle_and_kpis(self):
        for slug in NEW:
            with self.subTest(slug=slug):
                events=self.events(slug)
                self.assertEqual(events,self.events(slug))
                self.assertNotEqual(events,self.events(slug,43))
                self.assertEqual(len(events),40)
                self.assertEqual(sum('metrics' in e for e in events),10)
                self.assertEqual([e['time'] for e in events],sorted(set(e['time'] for e in events)))
                self.assertLess(events[-1]['time']-events[0]['time'],4)
                self.assertEqual({e['sourcetype'] for e in events},{'netspout:network:syslog','netspout:network:metric'})
                self.assertTrue(all(e['fields']['simulation']=='true' and e['fields']['contract_kind']=='pulseforge_custom' for e in events))
                self.assertEqual(len({e['fields']['netspout_incident_id'] for e in events}),1)
                self.assertEqual(len({e['fields']['dependency_path'] for e in events}),1)
                for n,phase in enumerate(pack.PHASES):
                    logs=events[4*n:4*n+3]
                    self.assertEqual(len({e['host'] for e in logs}),3)
                    self.assertTrue(all(e['fields']['netspout_phase']==phase for e in logs))
                    self.assertTrue(all('SIMULATED' in e['raw'] for e in logs))
                self.assertNotEqual(events[3]['metrics'],events[15]['metrics'])
                self.assertEqual(events[3]['metrics'],events[-1]['metrics'])

    def test_containment_is_not_enforcement(self):
        events=self.events('23_containment_request')
        self.assertTrue(any('acknowledgement unknown' in e['raw'] for e in events))
        self.assertTrue(any('not observed CoA enforcement' in e['raw'] for e in events))
        self.assertTrue(any('cancels requests' in e['raw'] for e in events))
        self.assertFalse(any(e['fields'].get('enforcement_confirmed') for e in events))

    def test_maintenance_variants_discriminate_incident_impact(self):
        unplanned,planned=self.events('26_maintenance',42),self.events('26_maintenance',43)
        self.assertTrue(all(e['fields']['maintenance_scope']=='planned' for e in planned))
        self.assertTrue(all(e['fields']['maintenance_scope']=='unplanned' for e in unplanned))
        self.assertEqual(planned[15]['metrics']['business.unplanned.impact.percent'],0)
        self.assertGreater(planned[15]['metrics']['application.failure.percent'],0)
        self.assertGreater(unplanned[15]['metrics']['business.unplanned.impact.percent'],0)

    def test_stale_sessions_recover_after_authentication(self):
        events=self.events('27_stale_sessions')
        intervention=events[27]['metrics']
        self.assertEqual(intervention['authentication.failure.percent'],0)
        self.assertGreater(intervention['service.access.failure.percent'],0)
        self.assertEqual(events[-1]['metrics']['service.access.failure.percent'],0)

    def test_previous_31_outputs_preserved(self):
        source=subprocess.check_output(['git','show','9ee494a3bf36d57a0b96117264072d835e121653:netspout/bin/network_incidents.py'],cwd=ROOT,text=True)
        old=types.ModuleType('c7a_checkpoint');exec(compile(source,'c7a_checkpoint','exec'),old.__dict__)
        slugs=set(old.CATALOG)|set(old.telecom_incidents.CATALOG)
        self.assertEqual(len(slugs),31)
        for slug in slugs:self.assertEqual(self.events(slug),old.generate(slug,42,1700000000,fixtures.RUN,10))

    def test_all_37_dashboard_discovery_and_research_links(self):
        data=discovery.build.build();self.assertEqual(data['executable_incident_count'],37)
        entries=data['entries'];recipes={r['recipe_id']:r for r in discovery.build.read('catalog/dashboard_recipes.json')['recipes']}
        for slug in NEW:
            r=next(e for e in entries if e['kind']=='scenario' and e['id']=='network_'+slug)
            self.assertTrue(r['executable']);self.assertTrue(r['modeled_products']);self.assertTrue(r['industries'])
            self.assertEqual(recipes[r['primary_dashboard_id']]['domain'],r['domain'])
            self.assertIn(r['id'],recipes[r['primary_dashboard_id']]['selectors'])
            for uc in r['incident_contract']['external_use_cases']:
                ref=next(e for e in entries if e['kind']=='use_case' and e['id']=='UC-'+uc)
                self.assertIn(r['id'],ref['scenario_ids'])
                self.assertFalse(ref.get('executable',False))
            for field in recipes[r['primary_dashboard_id']]['required_fields']:
                self.assertIn(field,r['incident_contract']['log_fields'])
        self.assertEqual(len({r['recipe_id'] for r in discovery.build.read('catalog/dashboard_recipes.json')['recipes'] if r.get('native_view')}),4)
