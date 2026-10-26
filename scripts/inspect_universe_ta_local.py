"""Read-only inventory of installed parsers and explicitly known authorized packages.

Never downloads, installs, extracts packages to disk, or reads inputs/passwords.
"""
import hashlib
import json
from pathlib import Path
import subprocess
import tarfile

ROOT=Path(__file__).resolve().parents[1]
LAB=Path('/Volumes/AI-Storage/Docker-Projects/netspout-splunk-lab')
PACKAGE_DIRS=[LAB/'evidence/ta-ise-1915-download-20261024',LAB/'evidence/escu-cim-install-20261026/packages']
INSPECT_CODE=r'''
import json, pathlib, hashlib, re, configparser
root=pathlib.Path('/opt/splunk/etc/apps')
apps=[]
for path in sorted(root.iterdir()):
 if not path.is_dir():continue
 conf=path/'default/app.conf'
 text=conf.read_text(errors='replace') if conf.is_file() else ''
 version=re.search(r'^version\s*=\s*(.+)$',text,re.M)
 record={'id':path.name,'version':version[1].strip() if version else None}
 if path.name.startswith(('TA','Splunk_TA')):
  record['parser_stanzas']={}
  for rel in ['default/props.conf','local/props.conf']:
   p=path/rel
   if p.is_file():record['parser_stanzas'][rel]=re.findall(r'^\[([^\]]+)\]',p.read_text(errors='replace'),re.M)
 apps.append(record)
ise=root/'Splunk_TA_cisco-ise'
files={}
for rel in ['default/props.conf','default/transforms.conf','default/eventtypes.conf','lookups/cisco_ise_message_catalog_500.csv','default/app.conf']:
 p=ise/rel
 if p.is_file():
  data=p.read_bytes();files[rel]={'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data)}
props=configparser.ConfigParser(interpolation=None,strict=False);props.optionxform=str
props.read(ise/'default/props.conf')
ise_props={k:dict(props[k]) for k in ['cisco:ise','cisco:ise:syslog'] if k in props}
print(json.dumps({'installed_apps':apps,'ise_installed_files':files,'ise_props':ise_props,'configuration_changes':0}))
'''


def main():
 packages=[]
 for directory in PACKAGE_DIRS:
  if not directory.is_dir():continue
  for path in sorted(directory.glob('*.tgz')):
   if path.stat().st_size>250_000_000:raise ValueError('Package read bound exceeded')
   digest=hashlib.sha256()
   with path.open('rb') as handle:
    for chunk in iter(lambda:handle.read(1_048_576),b''):digest.update(chunk)
   configs=[];package_files={}
   with tarfile.open(path,'r:gz') as archive:
    for member in archive:
     allowed={'default/props.conf','default/transforms.conf','default/eventtypes.conf','lookups/cisco_ise_message_catalog_500.csv','default/app.conf'}
     if member.isfile() and member.name.startswith('Splunk_TA_cisco-ise/') and member.name.split('/',1)[1] in allowed:
      if member.size>500_000:raise ValueError('Parser definition read bound exceeded')
      data=archive.extractfile(member).read()
      package_files[member.name.split('/',1)[1]]=hashlib.sha256(data).hexdigest()
     if member.isfile() and member.name.endswith('/default/app.conf'):
      if member.size>500_000:raise ValueError('Config read bound exceeded')
      text=archive.extractfile(member).read().decode(errors='replace')
      import re
      version=re.search(r'^version\s*=\s*(.+)$',text,re.M)
      configs.append(dict(app=member.name.split('/')[0],version=version[1].strip() if version else None))
   packages.append(dict(path=str(path),bytes=path.stat().st_size,sha256=digest.hexdigest(),apps=configs,parser_file_sha256=package_files,installed_by_this_work=False))
 proc=subprocess.run(['docker','exec','--user','0','-i','pf-native-lab','/usr/bin/python3','-'],input='import traceback, json\ntry:\n'+'\n'.join('    '+line for line in INSPECT_CODE.splitlines())+'\nexcept Exception as exc:\n    print(json.dumps({"inventory_error":type(exc).__name__,"line":traceback.extract_tb(exc.__traceback__)[-1].lineno}))',text=True,capture_output=True,timeout=30)
 if proc.returncode:raise RuntimeError('Read-only installed parser inventory failed; no diagnostics containing credentials emitted')
 result=json.loads(proc.stdout)
 if 'inventory_error' in result:raise RuntimeError('Sanitized inventory diagnostic: '+json.dumps(result))
 result['local_authorized_packages']=packages
 for package in packages:
  if package['parser_file_sha256']:
   package['installed_files_match_package']={rel:result['ise_installed_files'].get(rel,{}).get('sha256')==digest for rel,digest in package['parser_file_sha256'].items()}
 result['package_scope']='Only existing ISE download and CIM/ESCU package directories named in prior lab evidence; no backups or credential/config archives opened.'
 result['downloaded_packages']=result['installed_packages']=0
 target=ROOT/'catalog/universe_batch3_ta_inventory.json';target.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps({'installed_ta_apps':[a['id'] for a in result['installed_apps'] if 'parser_stanzas' in a],'local_packages':[{k:p[k] for k in ['bytes','sha256','apps']} for p in packages]}))

if __name__=='__main__':main()
