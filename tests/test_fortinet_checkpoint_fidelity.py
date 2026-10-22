"""C3B small format-aware checks; no TA-parser or receiver compatibility claims."""
import ast
from datetime import datetime
import ipaddress
import json
from pathlib import Path
import re
import shlex
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import yaml

from netspout_core.catalog_contracts import TelemetryCatalog, project_integration_identities
from netspout_core.log_engine import SplunkLogEngine as Engine

ROOT=Path(__file__).resolve().parents[1]


def fortios_fields(raw):
    """Bounded quoted KV subset used by the repaired IPS formatter."""
    tokens=shlex.split(re.sub(r'^<\d+>', '', raw))
    pairs=[token.split('=',1) for token in tokens]
    if any(len(pair)!=2 for pair in pairs):
        raise ValueError('Malformed KV record')
    if len({pair[0] for pair in pairs})!=len(pairs):
        raise ValueError('Duplicate KV key')
    return dict(pairs)


def cef_record(raw):
    """Validate the fixture's literal header and unescaped extension subset."""
    header=raw.split('|',7)
    if len(header)!=8 or header[0]!='CEF:0' or any(c in raw for c in '\r\n'):
        raise ValueError('Malformed CEF fixture')
    extension=header.pop()
    matches=list(re.finditer(r'(?:^| )([A-Za-z][A-Za-z0-9]*)=', extension))
    if not matches or matches[0].start()!=0:
        raise ValueError('Malformed CEF extension')
    pairs=[(match.group(1), extension[match.end():matches[n+1].start() if n+1<len(matches) else len(extension)])
           for n,match in enumerate(matches)]
    if len({key for key,value in pairs})!=len(pairs):
        raise ValueError('Duplicate CEF key')
    return header,dict(pairs)


class MultivendorRawTests(unittest.TestCase):
    def event(self, **changes):
        device=SimpleNamespace(id='forti-lab',name='FortiGate Lab',type=SimpleNamespace(value='firewall'))
        args=dict(device=device,src_ip='192.0.2.20',dest_ip='198.51.100.30',src_port=52140,
                  dest_port=443,attack='Eicar.Virus.Test.File',action='blocked',status='blocked',signature='synthetic signature')
        args.update(changes)
        with patch('netspout_core.log_engine.datetime') as clock:
            clock.utcnow.return_value=datetime(2026,10,20,12,0,0,125000)
            return Engine.format_fortinet_ips_log(**args)

    def test_fortios_native_subset_unique_fields_and_metadata_separation(self):
        entry=self.event();fields=fortios_fields(entry.raw_log)
        self.assertTrue(entry.raw_log.startswith('<189>date=2026-10-20 time=12:00:00'))
        self.assertEqual(fields['tz'],'+0000')
        for key,value in dict(logid='0419016384',type='utm',subtype='ips',eventtype='signature',
                              action='dropped',proto='6',attack='Eicar.Virus.Test.File',devname='FortiGate Lab').items():
            self.assertEqual(fields[key],value)
        for key in ('srcip','dstip'): ipaddress.ip_address(fields[key])
        for key in ('srcport','dstport'): self.assertTrue(0<int(fields[key])<65536)
        self.assertFalse({'timestamp','device_id','duration','signature','status'} & fields.keys())
        self.assertEqual(entry.signature,'synthetic signature')
        self.assertEqual(entry.sourcetype,'fortinet:fortigate:utm')
        self.assertEqual(self.event().raw_log,entry.raw_log)
        self.assertNotRegex(entry.raw_log,r'\$[A-Za-z_][A-Za-z0-9_]*\$')

    def test_fortios_detection_semantics_and_unsafe_unestablished_escaping(self):
        self.assertEqual(fortios_fields(self.event(action='allowed').raw_log)['action'],'detected')
        for value in ('quote"value','back\\slash','line\nbreak','carriage\rreturn'):
            with self.assertRaises(ValueError): self.event(attack=value)
        with self.assertRaises(ValueError): fortios_fields('action="dropped" action=blocked')

    def test_checkpoint_cef_header_extensions_and_timestamp_units(self):
        path=ROOT/'netspout/appserver/static/samples/checkpoint-cef/checkpoint-cef.yml'
        records=yaml.safe_load(path.read_text())['samples'][0]['lines']
        self.assertEqual(len(records),2)
        for record,action in zip(records,('Drop','Accept')):
            header,fields=cef_record(record['_raw'])
            self.assertEqual(header[:5],['CEF:0','Check Point','VPN-1 & FireWall-1','Check Point','Log'])
            self.assertIn(header[5],('smb','https'));self.assertEqual(header[6],'Unknown')
            self.assertEqual(set(fields),{'act','rt','spt','dpt','cs2Label','cs2','dst','proto','src'})
            self.assertEqual(fields['act'],action)
            self.assertEqual(fields['cs2Label'],'Rule Name')
            self.assertGreater(int(fields['rt']),10**12)
            self.assertEqual(int(fields['rt'])%1000,0)
            for key in ('src','dst'): ipaddress.ip_address(fields[key])
            for key in ('spt','dpt'): self.assertTrue(0<int(fields[key])<65536)
            self.assertEqual(fields['proto'],'6')
            self.assertNotRegex(record['_raw'],r'\$[A-Za-z_][A-Za-z0-9_]*\$|device_id=|signature=|status=')
            self.assertEqual((record['sourcetype'],record['source']),('checkpoint:cef','syslog:udp:514'))
        with self.assertRaises(ValueError): cef_record('time=1|hostname=lab|action=drop')

    def test_candidates_are_not_parser_verified_and_legacy_ids_stable(self):
        raw=json.loads((ROOT/'catalog/telemetry_catalog.json').read_text())
        catalog=TelemetryCatalog.model_validate(raw)
        vendors=json.loads((ROOT/'catalog/vendors.json').read_text())
        old=json.loads(subprocess.check_output(['git','show','HEAD:catalog/vendors.json'],cwd=ROOT,text=True))
        self.assertEqual([v['id'] for v in vendors],[v['id'] for v in old])
        expected={'palo_alto':('7523','4.0.0'),'fortinet':('2846','1.6.10'),'checkpoint':('4293','1.1.6')}
        self.assertEqual(vendors,project_integration_identities(vendors,catalog))
        for before,after in zip(old,vendors):
            if after['id'] in expected:
                for key in before.keys()-{'splunk_app_name','splunkbase_id','splunkbase_url'}:
                    self.assertEqual(before[key],after[key])
                self.assertEqual(after['splunkbase_id'],expected[after['id']][0])
            else: self.assertEqual(before,after)
        for vid,(appid,version) in expected.items():
            profiles=[p for i in catalog.integrations for p in i.profiles if p.vendor_id==vid]
            self.assertEqual(len(profiles),1)
            p=profiles[0];self.assertEqual((p.splunkbase_id,p.app_version),(appid,version))
            self.assertEqual(p.coverage.value,'not_assessed');self.assertFalse(p.validations)
            self.assertFalse(p.sourcetypes)

    def test_pan_raw_and_samples_unchanged(self):
        old=ast.parse(subprocess.check_output(['git','show','HEAD:src/netspout_core/log_engine.py'],cwd=ROOT,text=True))
        new=ast.parse((ROOT/'src/netspout_core/log_engine.py').read_text())
        for name in ('format_palo_alto_log','format_palo_alto_threat_log'):
            find=lambda tree: next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name==name)
            self.assertEqual(ast.dump(find(old)),ast.dump(find(new)))
        files=subprocess.check_output(['git','ls-files','netspout/appserver/static/samples/pan-*/*.yml'],cwd=ROOT,text=True).splitlines()
        self.assertTrue(files)
        for file in files:
            self.assertEqual((ROOT/file).read_bytes(),subprocess.check_output(['git','show','HEAD:'+file],cwd=ROOT))

    def test_generated_core_and_catalogs_match(self):
        source=(ROOT/'src/netspout_core/log_engine.py').read_bytes()
        self.assertEqual(source,(ROOT/'netspout/bin/netspout_core/log_engine.py').read_bytes())
        for folder in ('backend/app','netspout/bin'):
            self.assertTrue((ROOT/folder/'log_engine.py').read_bytes().endswith(source))
        for name in ('vendors.json','telemetry_catalog.json'):
            canonical=(ROOT/'catalog'/name).read_bytes()
            for folder in ('backend/app/catalog_data','netspout/bin/catalog_data',
                           'netspout/bin/netspout_core/catalog_data','netspout/catalog'):
                self.assertEqual(canonical,(ROOT/folder/name).read_bytes())
