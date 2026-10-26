"""Opt-in download of selected commit-pinned public RAW fixtures, never TA packages."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
REF='37ef1a028f3cc4b049779fa20578f7ee6f3cddbe'
TARGETS={
 'pfsense':'pfsense/data_stream/log/_dev/test/pipeline/test-pfsense-bsd.log',
 'sysdig':'sysdig/data_stream/event/_dev/test/pipeline/test-event.log',
 'sailpoint':'sailpoint_identity_sc/data_stream/events/_dev/test/pipeline/test-event.log',
 'imperva':'imperva/data_stream/securesphere/_dev/test/pipeline/test-securesphere.json',
 'barracuda':'barracuda/data_stream/waf/_dev/test/pipeline/test-web-firewall.log',
 'oracle':'oracle/data_stream/database_audit/_dev/test/pipeline/test-oracle-database-audit.log',
 'darktrace':'darktrace/data_stream/model_breach_alert/_dev/test/pipeline/test-model-breach-alert.log',
 'beyondtrust':'beyondinsight_password_safe/data_stream/useraudit/_dev/test/pipeline/test-useraudits.json',
 'tenable':'tenable_io/data_stream/audit/_dev/test/pipeline/test-audit.log',
 'ibmmq':'ibmmq/data_stream/errorlog/_dev/test/pipeline/test-errorlog-9-4.log',
}

def main():
 dest=ROOT/'catalog/raw_reference/universe_batch3';dest.mkdir(parents=True,exist_ok=True)
 refs=[]
 for name,path in TARGETS.items():
  url=f'https://raw.githubusercontent.com/elastic/integrations/{REF}/packages/{path}'
  with urlopen(url,timeout=20) as response:data=response.read(1_000_001)
  if len(data)>1_000_000:raise ValueError('Bounded fixture size exceeded')
  rel=f'catalog/raw_reference/universe_batch3/{name}.bin';(ROOT/rel).write_bytes(data)
  refs.append(dict(id=name,url=url,pinned_commit=REF,raw_reference_file=rel,bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),evidence_level='INTEGRATION_TEST_RAW',limitation='Public integration test reference, not a production capture or installed Splunk TA validation.'))
  print(name,len(data),flush=True)
 # Reuse the same already-pinned upstream license notice rather than refetching it.
 (dest/'UPSTREAM_LICENSE.txt').write_bytes((ROOT/'catalog/raw_reference/universe_batch2/UPSTREAM_LICENSE.txt').read_bytes())
 (dest/'references.json').write_text(json.dumps(refs,indent=2)+'\n')

if __name__=='__main__':main()
