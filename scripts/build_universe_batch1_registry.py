"""Universal Vendor Coverage batch-1: provenance append + registry build.

Idempotent: skips already-present universe:batch1 provenance references and
only writes the registry once. RAW evidence = vendor documentation samples
pinned to catalog/raw_reference/universe_batch1/ (sha256 recorded below and
in provenance.json), fetched from public vendor/integration documentation on
2026-10-26; no packages were downloaded or installed.
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROV = REPO_ROOT / "catalog" / "raw_reference" / "provenance.json"
REGISTRY = REPO_ROOT / "catalog" / "universe_batch1.json"
FIXTURE_DIR = REPO_ROOT / "catalog" / "raw_reference" / "universe_batch1"

# (fixture file, doc_url, excerpt_note)
FIXTURES = [
    ("docker_events__head.bin",
     "https://docs.docker.com/engine/reference/commandline/events/",
     "docker events 'Basic example' block, verbatim (container "
     "create/connect/start/kill/die/disconnect/stop lines)"),
    ("bluecoat_proxysg_access_file__head.bin",
     "https://www.elastic.co/docs/reference/integrations/proxysg",
     "Symantec/Broadcom ProxySG main-format access-log record (the ECS "
     "document's event.original), verbatim"),
    ("wazuh_alerts__head.bin",
     "https://documentation.wazuh.com/current/user-manual/capabilities/"
     "malware-detection/rootkits-behavior-detection.html",
     "Wazuh manager alerts.log Rootcheck alert blocks, verbatim"),
    ("nozomi_universal_alert__head.bin",
     "https://www.elastic.co/docs/reference/integrations/nozomi_networks",
     "Nozomi Networks vendor-native alert JSON (the document's "
     "event.original), re-serialized from the documented event"),
]

# (sourcetype, wave_source_id, vendor, generator, families, required_ta)
S = [
    ("docker_events", "docker-events", "docker",
     "format_docker_events_log",
     ["container_lifecycle", "network_connect"],
     "Docker Monitoring (monitoringdocker Add-on)"),
    ("bluecoat:proxysg:access:file", "bluecoat-proxysg-access-file",
     "broadcom_symantec", "format_proxysg_access_log",
     ["proxy_observed", "proxy_denied"],
     "Splunk Add-on for Symantec Blue Coat ProxySG"),
    ("wazuh:alerts", "wazuh-alerts", "wazuh",
     "format_wazuh_alert_log",
     ["rootcheck_hidden_process", "rootcheck_hidden_file"],
     "Wazuh Splunk Integration"),
    ("nozomi:universal_alert", "nozomi-universal-alert", "nozomi_networks",
     "format_nozomi_alert_log",
     ["ot_ids_program_change"],
     "Nozomi Networks Universal Add-on"),
]

UNIVERSE_TAGS_BY_WSID = {
    "docker-events": ["docker_events__head.bin"],
    "bluecoat-proxysg-access-file": ["bluecoat_proxysg_access_file__head.bin"],
    "wazuh-alerts": ["wazuh_alerts__head.bin"],
    "nozomi-universal-alert": ["nozomi_universal_alert__head.bin"],
}


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def append_provenance() -> int:
    with open(PROV) as f:
        prov = json.load(f)
    refs = prov.setdefault("references", [])
    existing = {r.get("raw_reference_file") for r in refs}
    added = 0
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for fname, doc_url, note in FIXTURES:
        full = FIXTURE_DIR / fname
        rel = "catalog/raw_reference/universe_batch1/" + fname
        if rel in existing or not full.exists():
            continue
        d_lm = datetime.fromtimestamp(
            full.stat().st_mtime, tz=timezone.utc).strftime("%Y-%m-%d")
        refs.append({
            "batch": "universe_batch1",
            "added_utc": today,
            "sourcetype_family": {
                "docker_events__head.bin": "docker_events",
                "bluecoat_proxysg_access_file__head.bin":
                    "bluecoat:proxysg:access:file",
                "wazuh_alerts__head.bin": "wazuh:alerts",
                "nozomi_universal_alert__head.bin":
                    "nozomi:universal_alert",
            }[fname],
            "documentation_url": doc_url,
            "documentation_fetched_utc": d_lm,
            "raw_reference_file": rel,
            "fetched_bytes": full.stat().st_size,
            "fetched_sha256": sha256_file(full),
            "fetch_mode": "public vendor/integration documentation excerpt; "
                          "no app packages downloaded, no TA installed",
            "excerpt": note,
            "evidence_role": ("authentic vendor-native RAW fixture for "
                              "Universal Vendor Coverage batch-1 generator"),
        })
        added += 1
    with open(PROV, "w") as f:
        json.dump(prov, f, indent=1)
    return added


def main() -> None:
    added = append_provenance()
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    sources = []
    for (st, wsid, vendor, gen, families, ta) in S:
        fixture_paths = UNIVERSE_TAGS_BY_WSID[wsid]
        source = {
            "batch_source_id": wsid,
            "vendor": vendor,
            "splunk_sourcetype": st,
            "is_new_canonical_row": True,
            "raw_evidence": [
                "pinned vendor documentation fixture: "
                "catalog/raw_reference/universe_batch1/%s" % p
                for p in fixture_paths
            ],
            "evidence_level": "STANDARD_DOCUMENTED",
            "generator": gen,
            "event_families": families,
            "event_family_count": len(families),
            "required_ta": ta,
            "ta_metadata": {
                "broadcom_symantec": {"uid": 2758, "publisher": "Splunk LLC", "version": "3.9.0", "sourcetype_declared_in_snapshot": True},
                "nozomi_networks": {"uid": 6905, "publisher": "Nozomi Networks", "version": "2.2.0", "sourcetype_declared_in_snapshot": True},
                "docker": {"status": "BLOCKED", "reason": "Named monitoringdocker integration and docker_events parser compatibility not established by the pinned Splunkbase snapshot; native Docker CLI format only."},
                "wazuh": {"status": "BLOCKED", "reason": "Native alerts.log documented; required TA package and wazuh:alerts parser compatibility not established by pinned metadata."},
            }[vendor],
        }
        sources.append(source)

    reg = {
        "schema_version": "1.0",
        "registry_version": "universe-batch1-2026-10-26",
        "created_utc": today,
        "purpose": ("First bounded multi-vendor generator batch of the "
                    "Universal Vendor Coverage phase: 4 new canonical "
                    "sourcetypes across 4 vendors recognized from the "
                    "Splunkbase-wide vendor universe registry "
                    "(catalog/vendor_universe.json)."),
        "invariants_respected": [
            "every format is modelled on pinned, sha256-recorded vendor "
            "documentation RAW samples; no fabricated formats",
            "vendor-native RAW preserved; correlation metadata only on HEC "
            "fields",
            "event families are NOT counted as unique sourcetypes",
            "no package downloads, TA installs or Splunk config changes; "
            "bounded live tests via the existing disposable HEC token only",
        ],
        "engine_module": "src/netspout_core/universe_batch1_engine.py",
        "engine_bindings": {
            "sourcetypes": list(UNIVERSE_TAGS_BY_WSID.keys()) and [
                "docker_events", "bluecoat:proxysg:access:file",
                "wazuh:alerts", "nozomi:universal_alert"],
            "generators": {wsid[1]: wsid[3] for wsid in S},
        },
        "raw_reference_corpus": ("catalog/raw_reference/universe_batch1/ + "
                                 "provenance.json (universe:batch1 entries)"),
        "sources": sources,
        "universe_registry": {
            "file": "catalog/vendor_universe.json",
            "vendor_keys_previously_extended": [
                "docker", "broadcom_symantec", "wazuh", "nozomi_networks"],
        },
        "live_verification": {
            "method": ("bounded HEC POST + indexed RAW-equality search "
                       "(disposable token pf-ta-ise-val -> idx_ta_ise_test, "
                       "zero config changes)"),
            "results_file": "catalog/universe_batch1_live_raw_equality_results.json",
            "status": "HISTORICAL_PASS_PRE_RECOVERY",
            "limitation": "Saved summary reports 9/9 PASS for the interrupted implementation. Recovery corrected generators and deferred two unsupported families; revised bytes were not re-ingested. No submitted/indexed payload hashes retained in the original summary.",
        },
        "counts_summary": {
            "new_canonical_sourcetypes": 4,
            "new_canonical_vendors": 4,
            "event_families_distinct_registry_instances":
                sum(s["event_family_count"] for s in sources),
            "scenario_packs": 1,
            "note": "One executable scenario; canonical totals 57 vendors, 317 sourcetypes, 41 scenarios.",
        },
        "ta_parser_verification": {"verified_sourcetypes": 0, "status": "BLOCKED", "reason": "Required Batch 1 TAs and controlled parser evidence unavailable; no TA installation authorized."},
        "detection_validation": {"verified_detections": 0, "status": "NOT_PERFORMED"},
        "bounded_deferrals": [
            {"candidate": "Docker volume_event; Nozomi ot_ids_threat_actor", "reason": "No supporting RAW for these families in the pinned corpus. Excluded from executable families and evidenced counts pending authentic samples."},
            {
                "candidate": "Trellix ePO / Illumio / Veeam vbr / Proofpoint "
                             "pds rows",
                "reason": "vendor RAW samples not recoverable from public "
                          "docs in this batch's bounded evidence window "
                          "(Splunkbase docs carry no samples; SC4S pages "
                          "declare sourcetypes only); deferred to a later "
                          "universe batch",
            },
        ],
    }
    current_file = REPO_ROOT / 'catalog/universe_batch1_current_raw_equality_results.json'
    if current_file.is_file():
        current = json.loads(current_file.read_text())
        reg['current_byte_verification'] = dict(results_file=str(current_file.relative_to(REPO_ROOT)),
                                                passes=current['passes'], posted=current['posted'],
                                                engine_sha256=current['engine_sha256'],
                                                status='PASS' if current['passes']==current['posted'] else 'FAIL')
    with open(REGISTRY, "w") as f:
        json.dump(reg, f, indent=1)
    print("provenance refs appended:", added)
    print("registry sources:", len(sources), "->", REGISTRY)


if __name__ == "__main__":
    main()
