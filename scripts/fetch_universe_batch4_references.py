"""Opt-in download of selected commit-pinned public RAW fixtures for Batch 4.

Same discipline as Batches 2 and 3: only explicitly selected upstream integration
test fixtures, one bounded GET per target, never TA packages, no runtime fetching.
"""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[1]
REF = '37ef1a028f3cc4b049779fa20578f7ee6f3cddbe'
TARGETS = {
    'slack': 'slack/data_stream/audit/_dev/test/pipeline/test-audit.log',
    'github': 'github/data_stream/audit/_dev/test/pipeline/test-enterprise-audit-json.log',
    'gitlab': 'gitlab/data_stream/audit/_dev/test/pipeline/test-audit.log',
    'cybereason': 'cybereason/data_stream/malop_process/_dev/test/pipeline/test-malop-process.log',
    'qualys': 'qualys_vmdr/data_stream/user_activity/_dev/test/pipeline/test-yes-preserve-custom.log',
    'rapid7': 'rapid7_insightvm/data_stream/asset_vulnerability/_dev/test/pipeline/test-asset-vulnerability.log',
    'sentinelone': 'sentinel_one/data_stream/threat/_dev/test/pipeline/test-pipeline-threat.log',
    'tanium': 'tanium/data_stream/discover/_dev/test/pipeline/test-discover.log',
    'trellix': 'trellix_epo_on_prem/data_stream/threat_event/_dev/test/pipeline/test-threat-event.log',
    'bitdefender': 'bitdefender/data_stream/push_notifications/_dev/test/pipeline/test-push-notification.json',
    'ibm_qradar': 'ibm_qradar/data_stream/offense/_dev/test/pipeline/test-offense.log',
    'elasticsearch': 'elasticsearch/data_stream/server/_dev/test/pipeline/test-server-logs.log',
}


def main():
    dest = ROOT / 'catalog/raw_reference/universe_batch4'
    dest.mkdir(parents=True, exist_ok=True)
    refs = []
    for name, path in TARGETS.items():
        url = f'https://raw.githubusercontent.com/elastic/integrations/{REF}/packages/{path}'
        with urlopen(url, timeout=30) as response:
            data = response.read(1_000_001)
        if len(data) > 1_000_000:
            raise ValueError(f'Fixture exceeds bounded size: {name}')
        rel = f'catalog/raw_reference/universe_batch4/{name}.bin'
        (ROOT / rel).write_bytes(data)
        refs.append(dict(id=name, url=url, pinned_commit=REF, upstream='elastic/integrations',
                         raw_reference_file=rel, bytes=len(data),
                         sha256=hashlib.sha256(data).hexdigest(),
                         evidence_level='INTEGRATION_TEST_RAW',
                         limitation='Public integration test reference, not a production capture or installed Splunk TA validation.'))
        print(name, len(data), refs[-1]['sha256'][:12], flush=True)
    (dest / 'UPSTREAM_LICENSE.txt').write_bytes((ROOT / 'catalog/raw_reference/universe_batch3/UPSTREAM_LICENSE.txt').read_bytes())
    (dest / 'references.json').write_text(json.dumps(refs, indent=2) + '\n')


if __name__ == '__main__':
    main()
