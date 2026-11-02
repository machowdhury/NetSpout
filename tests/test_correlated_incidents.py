"""C7A: six custom correlated incidents, no vendor-native/parser claims."""
import json
from pathlib import Path
import subprocess
import types
import unittest
import test_network_incidents as existing
import test_native_discovery as discovery

pack=existing.pack
ROOT=Path(__file__).resolve().parents[1]
NEW={
 '16_retail_uplink':1,'17_hospital_mac_auth':2,'18_payment_deny':5,
 '19_ips_service':6,'20_backend_link':8,'21_partial_pool':9}

class CorrelatedIncidentTests(unittest.TestCase):
    def test_six_registered_executable_descriptors(self):
        self.assertEqual(len(pack.CATALOG),27)
        for slug,proposal in NEW.items():
            with self.subTest(slug=slug):
                p=existing.FOLDER/('scenario_network_'+slug+'.yml')
                self.assertEqual(pack.descriptor(p)['pulseforge_incident'],slug)
                self.assertEqual(pack.CATALOG[slug][13]['proposal'],proposal)

    def test_lifecycle_correlation_business_kpis_and_bounds(self):
        for slug in NEW:
            with self.subTest(slug=slug):
                events=pack.generate(slug,42,1700000000,existing.RUN,10)
                self.assertEqual(events,pack.generate(slug,42,1700000000,existing.RUN,10))
                self.assertEqual(len(events),40)
                self.assertEqual([e['time'] for e in events],sorted(set(e['time'] for e in events)))
                self.assertLess(events[-1]['time']-events[0]['time'],4)
                self.assertEqual({e['sourcetype'] for e in events},{'netspout:network:syslog','netspout:network:metric'})
                self.assertTrue(all(e['fields']['contract_kind']=='pulseforge_custom' for e in events))
                self.assertTrue(all(e['fields']['simulation']=='true' for e in events))
                self.assertEqual(len({e['fields']['netspout_incident_id'] for e in events}),1)
                self.assertEqual(len({e['fields']['dependency_path'] for e in events}),1)
                for i,phase in enumerate(pack.PHASES):
                    logs=events[i*4:i*4+3]
                    self.assertEqual(len({e['host'] for e in logs}),3)
                    self.assertTrue(all(e['fields']['netspout_phase']==phase for e in logs))
                    self.assertTrue(all('SIMULATED' in e['raw'] for e in logs))
                base,failure,recovery=events[3]['metrics'],events[15]['metrics'],events[-1]['metrics']
                self.assertEqual(base,recovery)
                self.assertTrue(all(failure[k]>base[k] for k in base))
                self.assertIn('simulated_action',events[24]['fields']['evidence_kind'])
                self.assertIn('Operator',events[24]['raw'])
                for protocol in ('syslog','snmp','forwarding'):
                    self.assertEqual(len(pack.select_events(events,protocol,{})),30)
                self.assertEqual(len(pack.select_events(events,'otlp',{'otlp_signal':'metrics'})),10)

    def test_original_25_outputs_unchanged(self):
        source=subprocess.check_output(['git','show','3699554a68e46a8858bce3ca5190d1b9734c4273:netspout/bin/network_incidents.py'],cwd=ROOT,text=True)
        old=types.ModuleType('previous_incidents');exec(compile(source,'previous_incidents','exec'),old.__dict__)
        original=set(old.CATALOG)|set(old.telecom_incidents.CATALOG)
        self.assertEqual(len(original),25)
        for slug in original:
            with self.subTest(slug=slug):
                self.assertEqual(pack.generate(slug,42,1700000000,existing.RUN,10),old.generate(slug,42,1700000000,existing.RUN,10))

    def test_all_31_discovery_and_dashboard_relationships(self):
        data=discovery.build.build();self.assertEqual(data['executable_incident_count'],37)
        entries=data['entries'];recipes={r['recipe_id']:r for r in discovery.build.read('catalog/dashboard_recipes.json')['recipes']}
        for slug in NEW:
            row=next(r for r in entries if r['kind']=='scenario' and r['id']=='network_'+slug)
            self.assertTrue(row['executable']);self.assertTrue(row['modeled_products'])
            recipe=recipes[row['primary_dashboard_id']]
            self.assertEqual(recipe['domain'],row['domain'])
            self.assertIn(row['id'],recipe['selectors'])
            self.assertTrue(set(recipe['required_sourcetypes'])<=set(row['incident_contract']['log_sourcetypes']))
            self.assertTrue(set(recipe['required_fields'])<=set(row['incident_contract']['log_fields']))
            for uc in row['incident_contract']['external_use_cases']:
                ref=next(r for r in entries if r['kind']=='use_case' and r['id']=='UC-'+uc)
                self.assertIn(row['id'],ref['scenario_ids'])
            self.assertIn('custom',row['readiness'])
            self.assertFalse(any(r.get('executable') for r in entries if r['kind']=='use_case'))

    def test_industry_and_product_scope(self):
        self.assertTrue(all(slug in pack.CATALOG for slug in NEW))
        self.assertEqual({pack.CATALOG[s][13]['industry'] for s in NEW},
                         {'Retail','Healthcare','Financial services','Cross-industry'})
