"""Fetch the explicitly selected public RAW fixtures; no vendor discovery or TA download.

Network is opt-in by executing this script. Runtime and offline builds never fetch.
"""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
REF = '37ef1a028f3cc4b049779fa20578f7ee6f3cddbe'
TARGETS = {
 'vault': 'hashicorp_vault/data_stream/audit/_dev/test/pipeline/test-audit.log',
 'traefik': 'traefik/data_stream/access/_dev/test/pipeline/test-format-json.log',
 'claroty': 'claroty_ctd/data_stream/event/_dev/test/pipeline/test-event.json',
 'mongodb': 'mongodb/data_stream/log/_dev/test/pipeline/test-mongodb-ubuntu-4-4-4.log',
 'confluence': 'atlassian_confluence/data_stream/audit/_dev/test/pipeline/test-audit-cloud.log',
 'nginx': 'nginx/data_stream/access/_dev/test/pipeline/test-access.log',
 'proofpoint': 'proofpoint_tap/data_stream/message_blocked/_dev/test/pipeline/test-message-blocked.log',
 'cyberark': 'cyberarkpas/data_stream/audit/_dev/test/pipeline/test-legacysyslog.log',
 'veeam': 'veeam/data_stream/event/_dev/test/pipeline/test-veeam-event-backup-sample.log',
 'veeam_malware': 'veeam/data_stream/event/_dev/test/pipeline/test-veeam-event-malware-sample.log',
}

def main():
    dest = ROOT / 'catalog/raw_reference/universe_batch2'
    dest.mkdir(parents=True, exist_ok=True)
    refs = []
    for name, path in TARGETS.items():
        url = f'https://raw.githubusercontent.com/elastic/integrations/{REF}/packages/{path}'
        with urlopen(url, timeout=20) as response:
            data = response.read(1_000_001)
        if len(data) > 1_000_000:
            raise ValueError(f'Fixture exceeds bounded size: {name}')
        rel = f'catalog/raw_reference/universe_batch2/{name}.bin'
        (ROOT / rel).write_bytes(data)
        refs.append(dict(id=name, url=url, commit=REF, raw_reference_file=rel,
                         bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                         evidence_level='INTEGRATION_TEST_RAW',
                         upstream='elastic/integrations',
                         limitation='Public integration test fixture; not a vendor production capture or installed Splunk TA verification.'))
        if name == 'cyberark':
            refs[-1]['evidence_level'] = 'REJECTED_CUSTOM_ELASTIC_FORMAT'
            refs[-1]['limitation'] = 'Custom Elastic syslog output template; excluded from native generator graduation.'
        print(name, len(data), flush=True)
    license_url = f'https://raw.githubusercontent.com/elastic/integrations/{REF}/LICENSE.txt'
    with urlopen(license_url, timeout=20) as response:
        license_data = response.read(50000)
    (dest / 'UPSTREAM_LICENSE.txt').write_bytes(license_data)
    documented = ('sep/15 09:54:33 system,info,account user admin logged in from 10.1.101.212 via winbox\n'
                  '11:11:43 route,ospf,debug SEND: Hello Packet 10.255.255.1 -> 224.0.0.5 on lo0\n')
    (dest / 'mikrotik.bin').write_text(documented)
    refs.append(dict(id='mikrotik', url='https://help.mikrotik.com/docs/spaces/ROS/pages/328094/Log',
                     raw_reference_file='catalog/raw_reference/universe_batch2/mikrotik.bin',
                     bytes=len(documented.encode()), sha256=hashlib.sha256(documented.encode()).hexdigest(),
                     evidence_level='VENDOR_DOCUMENTED', excerpt='Log messages and Topics code blocks; console records only', fetched_utc='2026-10-26'))
    (dest / 'references.json').write_text(json.dumps(refs, indent=2) + '\n')

if __name__ == '__main__':
    main()
