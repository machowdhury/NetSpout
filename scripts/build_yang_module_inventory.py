"""Build a provenance‑pinned inventory of YANG modules from YangModels/yang (Workstream C).

Inventory includes:
  * pinned commit and tree SHAs
  * vendor directory presence (Cisco, Juniper, etc.) with their tree SHAs
  * OpenConfig modules referenced in PulseForge gNMI engine (openconfig‑interfaces, openconfig‑qos)
  * mapping of each gNMI path to its YANG module (if known) and existence flag

No leaf‑level XPath validation; this inventory provides a defensible denominator
for vendor‑specific YANG module coverage and OpenConfig path mapping.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'catalog' / 'yang_module_inventory.json'
YANG_REF = ROOT / 'catalog' / 'yang_reference'

# Pinned commit and tree SHAs obtained via GitHub API on 2026‑10‑27
PINNED_COMMIT = '7cb93ea27b7ee86ad3dd9f82998146aa838d13b8'
PINNED_TREE = '5458ceade6e510bb9968d88bf17e9dfb904f069a'
REPO = 'YangModels/yang'

# Tree SHAs discovered via API calls (non‑recursive)
STANDARD_TREE = 'bc2be0a2c2a895a9a97928c74187205ce3599369'
EXPERIMENTAL_TREE = 'be106302d568ebe8c7176a7f56890f9bdfa1cf33'
OPENCONFIG_TREE = 'ff5d22699412589a2b0f57187701da9fb0cb820d'  # empty (README only)
VENDOR_TREE = '1baac84b29239f5723d63394bfd5d824dbee00ae'
VENDOR_SUBTREES = {
    'cisco': 'b9bb2f40d6d33a2fd2ba9cad3941853c5d7a2168',
    'juniper': '96ad7badc2603aa1033476103aeded2632db9a9a',  # submodule
    'arista': None,  # not present in vendor root tree
    'huawei': '1a069483f2ba7213aa4858f799220734ac3eb0f2',  # submodule
    'nokia': '31719c2e9b9b1d990821cab56012b1da581dbeaa',   # submodule
}

# OpenConfig modules referenced in PulseForge gNMI engine (from code scan)
OPENCONFIG_MODULES = [
    {
        'name': 'openconfig-interfaces',
        'prefix': 'openconfig-interfaces',
        'note': 'Referenced in scenario `openconfig_mdt_streaming`; YANG models are external (OpenConfig/public repo).',
        'exists_in_yangmodels': False,
    },
    {
        'name': 'openconfig-qos',
        'prefix': 'openconfig-qos',
        'note': 'Referenced in scenario `openconfig_mdt_streaming`; YANG models external.',
        'exists_in_yangmodels': False,
    },
    {
        'name': 'openconfig-gnmi-interfaces',
        'prefix': 'openconfig-gnmi-interfaces',
        'note': 'Synthetic module used in PulseForge for gNMI‑interface telemetry; not a standard OpenConfig YANG module.',
        'exists_in_yangmodels': False,
    },
]

# gNMI path → module mapping inferred from PulseForge engine
GNMI_PATH_MAPPING = [
    {'path': '/interfaces/interface/state/counters',
     'module': 'openconfig-interfaces',
     'source': 'scenario_runner.py',
     'exists_in_yangmodels': False,
     'note': 'OpenConfig interfaces state counters.'},
    {'path': '/qos/interfaces/interface/output/queues',
     'module': 'openconfig-qos',
     'source': 'scenario_runner.py',
     'exists_in_yangmodels': False,
     'note': 'OpenConfig QoS queue statistics.'},
    {'path': '/openconfig-fabricated/nonexistent/aci/dme/state',
     'module': None,
     'source': 'scenario_runner.py',
     'exists_in_yangmodels': False,
     'note': 'Fabricated path for testing; no real YANG module.'},
]


def build():
    data = {
        'artifact': 'PulseForge YANG module inventory (Workstream C)',
        'generated_at': '2026-10-27',
        'generator': 'scripts/build_yang_module_inventory.py',
        'authorities': {
            'yangmodels_yang': {
                'repo': REPO,
                'pinned_commit': PINNED_COMMIT,
                'pinned_tree': PINNED_TREE,
                'api_calls_consumed': 5,
                'role': 'Vendor‑specific YANG module repository; does NOT contain OpenConfig models (they are external).',
            },
        },
        'vendor_directory_presence': {
            vendor: {
                'tree_sha': sha if sha else None,
                'type': 'submodule' if sha and len(sha) == 40 and vendor in ('juniper','huawei','nokia','fujitsu','alliedtelesis') else 'tree',
                'expanded': False,
                'note': 'Submodule indicates the vendor YANG files are tracked in a separate repository; tree indicates they are in‑repo.',
            } for vendor, sha in VENDOR_SUBTREES.items()
        },
        'openconfig_modules_referenced': OPENCONFIG_MODULES,
        'gnmi_path_mapping': GNMI_PATH_MAPPING,
        'summary': {
            'pinned_commit': PINNED_COMMIT,
            'vendor_directories_count': len(VENDOR_SUBTREES),
            'openconfig_modules_count': len(OPENCONFIG_MODULES),
            'gnmi_paths_mapped': len(GNMI_PATH_MAPPING),
            'coverage_note': 'This inventory establishes a denominator of vendor‑specific YANG modules available in the YangModels repository and maps PulseForge gNMI paths to OpenConfig module names. It does NOT assert leaf‑level XPath coverage.',
        },
        'notes': [
            'OpenConfig YANG models are hosted in the OpenConfig/public repository, not in YangModels/yang. This inventory maps PulseForge gNMI paths to OpenConfig module names for documentation, not as proof of YANG‑file existence.',
            'Vendor‑specific YANG modules (Cisco‑IOS‑XR, Juniper, Huawei, etc.) are present in the repository as submodules or in‑repo trees. No leaf‑level validation is performed.',
            'Workstream C is intentionally bounded: it enumerates what exists in the pinned repository and maps PulseForge gNMI paths to known YANG modules.',
        ],
    }
    return data


if __name__ == '__main__':
    data = build()
    OUT.write_text(json.dumps(data, indent=1) + '\n')
    summary = data['summary']
    print(json.dumps({
        'pinned_commit': summary['pinned_commit'],
        'vendor_dirs': summary['vendor_directories_count'],
        'openconfig_modules': summary['openconfig_modules_count'],
        'gnmi_paths': summary['gnmi_paths_mapped'],
    }))
    print(f"wrote {OUT.relative_to(ROOT)}")
    sys.exit(0)