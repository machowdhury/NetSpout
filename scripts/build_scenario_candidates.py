#!/usr/bin/env python3
"""Build catalog/scenario_candidates.json: documented, research-backed scenario candidates for the 18 approved industries.

Nothing here is executable and nothing is telemetry. Each candidate is a CATALOGED definition with stable ID, provenance, industry mapping
(with its basis) and an explicit dependency statement. Sources:

  community-uc   fenre/splunk-monitoring-use-cases (MIT) pinned to a commit. Only the SELECTED entries below are recorded: id, title,
                 criticality, the upstream industry label, URL and the upstream `dataSources` text as an unverified hint. No SPL, runbooks or
                 descriptions are copied. Upstream TA/sourcetype claims are hints, never authority.
  cisco-100      the repository's own catalog/cisco_100_scenarios.json (96 definitions that are not execution-enabled).

Industry mapping basis: SOURCE_LABEL (the source's own industry label/category names the industry), EDITORIAL_TITLE (the title names the
industry's workload), EDITORIAL_DOMAIN (the source's domain implies it). Editorial mappings are judgment, never customer-validated.
Government subdomains are assigned only where the title clearly supports one. Industries with no documented source entry stay empty on purpose.

Run: python scripts/build_scenario_candidates.py   (needs network once; output is deterministic for the pinned commit)
"""
import concurrent.futures as cf
import json
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SHA = "8d26053d49a5648a9a9ebb233fd8a2c8e87ac869"
RAW = "https://raw.githubusercontent.com/fenre/splunk-monitoring-use-cases/%s/%s"
BLOB = "https://github.com/fenre/splunk-monitoring-use-cases/blob/%s/%s"
CAT_DIRS = {1: "cat-01-server-compute", 2: "cat-02-virtualization", 3: "cat-03-containers-orchestration", 4: "cat-04-cloud-infrastructure",
            5: "cat-05-network-infrastructure", 6: "cat-06-storage-backup", 7: "cat-07-database-data-platforms", 8: "cat-08-application-infrastructure",
            9: "cat-09-identity-access-management", 10: "cat-10-security-infrastructure", 12: "cat-12-devops-ci-cd", 13: "cat-13-observability-monitoring-stack",
            14: "cat-14-iot-operational-technology-ot", 15: "cat-15-data-center-physical-infrastructure", 17: "cat-17-network-security-zero-trust",
            21: "cat-21-industry-verticals", 22: "cat-22-regulatory-compliance"}

# industry id -> [(UC id, basis, optional subdomain / source sub-industry)]
S, T, D = "SOURCE_LABEL", "EDITORIAL_TITLE", "EDITORIAL_DOMAIN"
SELECTION = {
    "banking-financial-services": [("21.11.1", S), ("21.11.2", S), ("21.11.13", S), ("21.11.14", S), ("21.11.18", S), ("21.11.21", S), ("21.11.10", S), ("22.5.2", T)],
    "insurance-insurtech": [("21.10.1", S), ("21.10.2", S), ("21.10.5", S), ("21.10.6", S), ("21.10.8", S), ("21.10.9", S)],
    "healthcare": [("21.3.1", S), ("21.3.2", S), ("21.3.3", S), ("21.3.4", S), ("21.3.5", S), ("21.3.12", S)],
    "retail-ecommerce": [("21.6.1", S), ("21.6.2", S), ("21.6.3", S), ("21.6.5", S), ("21.6.6", S), ("21.6.10", S)],
    "manufacturing": [("21.2.1", S), ("21.2.2", S), ("21.2.3", S), ("21.2.4", S), ("21.2.11", S), ("21.2.12", S), ("14.2.1", T), ("14.2.2", T)],
    "energy-utilities": [("21.1.1", S), ("21.1.2", S), ("21.1.7", S), ("21.1.8", S), ("21.1.12", S), ("21.5.1", S, "Oil, Gas and Mining"), ("21.5.8", S, "Oil, Gas and Mining"),
                         ("21.9.1", S, "Water and Wastewater"), ("21.9.3", S, "Water and Wastewater"), ("21.9.4", S, "Water and Wastewater")],
    "telecommunications": [("21.8.1", S), ("21.8.2", S), ("21.8.3", S), ("21.8.4", S), ("21.8.5", S), ("21.8.6", S), ("21.8.8", S), ("21.8.20", S)],
    "transportation-logistics": [("21.4.1", S), ("21.4.4", S), ("21.4.6", S), ("21.4.9", S), ("21.4.10", S), ("21.4.12", S),
                                 ("21.7.1", S, "Aviation"), ("21.7.3", S, "Aviation"), ("21.7.7", S, "Aviation"), ("21.7.10", S, "Aviation")],
    "education": [("21.13.1", S), ("21.13.2", S), ("21.13.10", S), ("21.13.13", S), ("21.13.17", S), ("21.13.18", S), ("21.12.10", T), ("21.12.11", T), ("21.12.13", T)],
    "government-public-sector": [("21.12.1", S), ("21.12.2", S), ("21.12.16", S), ("21.12.17", S), ("21.12.18", S), ("21.12.19", S), ("21.12.20", S), ("21.12.21", S)],
    "technology-saas": [("13.4.5", T), ("3.2.7", T), ("8.1.1", T), ("8.3.1", T), ("21.14.1", T, "Contact Center and CX Operations")],
    "media-entertainment": [("4.2.19", T), ("5.8.26", T), ("5.9.32", T), ("4.3.15", T)],
    "hospitality-travel": [("5.4.30", T), ("17.1.4", T), ("21.7.5", T, "Aviation"), ("21.7.9", T, "Aviation"), ("21.7.2", T, "Aviation")],
    "aerospace-defense": [("22.20.4", T), ("22.20.8", T), ("22.20.6", T), ("22.20.7", T)],
    "legal-compliance-professional-services": [("22.7.44", T), ("22.5.2", T), ("22.1.4", T), ("22.5.16", T), ("22.5.15", T)],
    "agriculture-agritech": [("14.3.11", T), ("14.3.9", T), ("21.4.10", T)],
    "real-estate-proptech-construction": [("14.1.1", T), ("14.1.37", T), ("14.1.42", T), ("14.1.29", T), ("15.3.36", T)],
    "nonprofit-ngo-global-aid": [("22.1.5", T), ("22.1.16", T), ("22.8.7", T), ("21.13.12", T), ("21.12.12", T)],
}
# Secondary, editorial placements (a use case can serve more than one industry): (UC id, industry, basis, subdomain)
SECONDARY = [
    ("21.1.1", "government-public-sector", T, "gov-critical-infrastructure"), ("21.9.6", "government-public-sector", T, "gov-critical-infrastructure"),
    ("21.9.6", "energy-utilities", S, None), ("21.7.10", "government-public-sector", T, "gov-critical-infrastructure"),
    ("21.12.17", "government-public-sector", T, "gov-state-local"), ("21.12.18", "government-public-sector", T, "gov-state-local"),
    ("21.12.19", "government-public-sector", T, "gov-state-local"), ("21.12.20", "government-public-sector", T, "gov-state-local"),
    ("21.12.21", "government-public-sector", T, "gov-state-local"), ("21.5.1", "government-public-sector", T, "gov-critical-infrastructure"),
    ("21.7.1", "hospitality-travel", T, None), ("21.4.10", "healthcare", T, None),
]
CISCO_CATEGORY_INDUSTRY = {
    "FINANCIAL_SERVICES": [("banking-financial-services", S, None)], "TELECOMMUNICATIONS": [("telecommunications", S, None)],
    "UTILITIES": [("energy-utilities", S, None), ("government-public-sector", T, "gov-critical-infrastructure")],
    "ENERGY": [("energy-utilities", S, None), ("government-public-sector", T, "gov-critical-infrastructure")],
    "MANUFACTURING": [("manufacturing", S, None)], "HEALTHCARE": [("healthcare", S, None)], "TRANSPORTATION": [("transportation-logistics", S, None)],
    "PUBLIC_SECTOR": [("government-public-sector", S, None)], "OT_ICS": [("manufacturing", T, None), ("energy-utilities", T, None)],
    "REMOTE_INFRASTRUCTURE": [("energy-utilities", T, None)], "SOVEREIGN_CLOUD": [("government-public-sector", D, "gov-national-security")],
    "CRITICAL_COMMUNICATIONS": [("government-public-sector", D, "gov-national-security")], "SOVEREIGN_NETWORK": [("government-public-sector", D, "gov-national-security")],
    "EVIDENCE_DEBT": [("government-public-sector", D, "gov-critical-infrastructure")],
}


def fetch(uc):
    major = int(uc.split(".")[0])
    path = "content/%s/UC-%s.json" % (CAT_DIRS[major], uc)
    last = None
    for _ in range(3):
        try:
            d = json.loads(urllib.request.urlopen(RAW % (SHA, path), timeout=40).read())
            return uc, {"title": d["title"], "criticality": d.get("criticality"), "upstream_industry": d.get("industry"), "path": path,
                        "upstream_data_sources_hint": d.get("dataSources"), "upstream_app_hint": d.get("app")}
        except Exception as exc:  # network flake: retry, then fail loudly (never write a partial registry)
            last = exc
    raise SystemExit("could not fetch UC-%s: %s" % (uc, last))


def main():
    wanted = sorted({e[0] for rows in SELECTION.values() for e in rows} | {s[0] for s in SECONDARY}, key=lambda u: [int(x) for x in u.split(".")])
    with cf.ThreadPoolExecutor(12) as ex:
        meta = dict(ex.map(fetch, wanted))
    by_id = {}
    for industry, rows in SELECTION.items():
        for entry in rows:
            uc, basis = entry[0], entry[1]
            sub = entry[2] if len(entry) > 2 else None
            c = by_id.setdefault(uc, {"industries": []})
            c["industries"].append({"id": industry, "basis": basis, **({"source_subindustry": sub} if sub else {})})
    for uc, industry, basis, subdomain in SECONDARY:
        c = by_id.setdefault(uc, {"industries": []})
        if not any(i["id"] == industry and i.get("subdomain") == subdomain for i in c["industries"]):
            c["industries"].append({"id": industry, "basis": basis, **({"subdomain": subdomain} if subdomain else {})})
    candidates = []
    for uc in wanted:
        m, c = meta[uc], by_id[uc]
        candidates.append({
            "candidate_id": "UCR-" + uc, "source_id": "community-uc", "source_ref": "UC-" + uc, "url": BLOB % (SHA, m["path"]),
            "title": m["title"], "kind": "operational" if int(uc.split(".")[0]) not in (22,) else "compliance", "criticality": m["criticality"],
            "upstream_industry": m["upstream_industry"], "industries": c["industries"], "status": "CATALOGED",
            "dependencies": {"upstream_data_sources_hint": m["upstream_data_sources_hint"], "upstream_app_hint": m["upstream_app_hint"],
                             "netspout": "No NetSpout scenario contract, generator or telemetry exists for this entry; upstream data-source text is an unverified hint."}})
    cisco = json.loads((ROOT / "catalog" / "cisco_100_scenarios.json").read_text())
    rows = next(v for v in cisco.values() if isinstance(v, list) and v and isinstance(v[0], dict) and "scenario_id" in v[0])
    promoted = {x["scenario_id"] for x in json.loads((ROOT / "catalog" / "phase8c_scenario_promotions.json").read_text())["promotions"]}
    for r in rows:
        if r.get("execution_enabled") or r["scenario_id"] in promoted:
            continue  # already an executable scenario (runtime reference implementation): listing it again would double count
        inds = CISCO_CATEGORY_INDUSTRY.get(r["category"], [])
        if r["domain"] == "Service Provider & Carrier":
            inds = [("telecommunications", D, None)]
        candidates.append({
            "candidate_id": r["scenario_id"], "source_id": "cisco-100", "source_ref": r["scenario_id"],
            "url": None, "title": r["title"], "kind": "operational", "criticality": None, "upstream_industry": r["category"],
            "industries": [{"id": i, "basis": b, **({"subdomain": sd} if sd else {})} for i, b, sd in inds], "status": "CATALOGED", "domain": r["domain"],
            "dependencies": {"sourcetypes": r.get("sourcetypes", []), "research_gaps": r.get("research_gaps", []), "limitations": r.get("limitations", []),
                             "netspout": "Cisco 100 contract (maturity %s): definition exists, not execution-enabled." % r.get("maturity")}})
    ids = [c["candidate_id"] for c in candidates]
    assert len(ids) == len(set(ids)), "candidate ids must be unique"
    doc = {"schema_version": "1.0", "registry_version": "scenario-candidates-" + date.today().isoformat(),
           "note": "Documented candidates only: CATALOGED means a research-backed definition exists. It does not mean NetSpout can generate telemetry for it.",
           "sources": [
               {"source_id": "community-uc", "name": "Splunk monitoring use cases (community)", "repository": "https://github.com/fenre/splunk-monitoring-use-cases", "commit": SHA,
                "license": "MIT, copyright 2026 Fredrik Lima Sudmann; preserve the notice if substantial content is reused", "recorded": "id, title, criticality, upstream industry label, URL, data-source hint only"},
               {"source_id": "cisco-100", "name": "NetSpout Cisco 100 scenario catalog", "repository": "catalog/cisco_100_scenarios.json", "commit": None, "license": "project",
                "recorded": "definitions that are not execution-enabled"}],
           "candidates": candidates}
    (ROOT / "catalog" / "scenario_candidates.json").write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"candidates": len(candidates), "community_uc": sum(c["source_id"] == "community-uc" for c in candidates), "cisco_100": sum(c["source_id"] == "cisco-100" for c in candidates)}))


INCIDENT_PACK_INDUSTRIES = {
    # Only packs whose title names an industry workload; generic network incidents are deliberately NOT mapped to fill industries.
    "network_16_retail_uplink": ["retail-ecommerce"], "network_17_hospital_mac_auth": ["healthcare"],
    "network_18_payment_deny": ["banking-financial-services", "retail-ecommerce"],
    **{"telco_%02d_%s" % (i, n): ["telecommunications"] for i, n in [(1, "ran_cell"), (2, "registration_auth"), (3, "slice_sla"), (4, "ims_volte"),
       (5, "mobile_transport"), (6, "broadband_cpe"), (7, "sdwan_service"), (8, "roaming_mobility"), (9, "core_user_plane"), (10, "cross_layer")]},
}


def merge_taxonomy_mappings():
    """Add the title-specific incident pack mappings to the approved taxonomy file (editorial basis, deduplicated, idempotent)."""
    path = ROOT / "catalog" / "explorer_taxonomy.json"
    tax = json.loads(path.read_text(encoding="utf-8"))
    known = {i["id"] for i in tax["industries"]}
    have = {(m["scenario_id"], tuple(m["industries"])) for m in tax["scenario_industries"]}
    added = 0
    for sid, inds in INCIDENT_PACK_INDUSTRIES.items():
        assert set(inds) <= known, (sid, inds)
        if (sid, tuple(inds)) not in have and not any(m["scenario_id"] == sid for m in tax["scenario_industries"]):
            tax["scenario_industries"].append({"scenario_id": sid, "basis": "editorial", "industries": inds})
            added += 1
    path.write_text(json.dumps(tax, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return added


if __name__ == "__main__":
    main()
    print(json.dumps({"taxonomy_mappings_added": merge_taxonomy_mappings()}))
