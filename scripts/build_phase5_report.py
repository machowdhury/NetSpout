#!/usr/bin/env python3
"""Writes docs/contracts/phase5/PHASE5_REPORT.md from the JSON outputs of build_phase5_matrix.py (no new analysis here)."""
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
P5 = ROOT / "docs/contracts/phase5"
J = lambda n: json.loads((P5 / n).read_text())


def table(head, rows):
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(str(c) for c in r) + " |" for r in rows])


def main():
    m, vc, top, mism, ing, inv = J("master_matrix.json"), J("vendor_coverage.json"), J("top10_shortlist.json"), J("sourcetype_mismatches.json"), J("ingestion_classification.json"), J("package_inventory.json")
    t, rows = m["summary"], m["rows"]
    exact = [r for r in rows if r["match_type"] == "exact"]
    cats = Counter(c for a in ing for c in a["categories"])
    dist = Counter(a["package_type"] for a in ing)
    o = ["# Phase 5 — inventory of all downloaded Splunk packages and mapping to the NetSpout catalog", "",
         "Derived metadata only. Package contents, the external sample corpus and credentials are not in this repository. Nothing was installed, downloaded or sent to any Splunk instance in this phase. "
         "Inventory is not compatibility: a name in this matrix is never a claim that NetSpout supports that product.", "",
         "## 1. Inventory", "", table(["measure", "value"], [
             ["regular files in ~/netspout/private-packs", t["package_files"]], ["inspected", t["files_inspected"]], ["failed", t["files_failed"]],
             ["byte-identical duplicate files (each keeps its own row)", t["byte_identical_duplicate_files"]], ["unique files by SHA-256", inv["summary"]["unique_files_by_sha256"]],
             ["distinct app identities (id + version)", t["distinct_app_identities"]], ["distinct app ids", t["distinct_app_ids"]],
             ["distinct vendors by monitored product (rule-based; see limitations)", t["distinct_vendor_groups_by_monitored_product"]], ["distinct publishers (app.conf author field)", t["distinct_publishers_app_conf_author"]],
             ["distinct TA sourcetype names (literal)", t["ta_sourcetype_names_literal"]], ["wildcard/pattern stanzas (not counted as names)", t["ta_sourcetype_patterns"]]]), "",
         "The directory holds %d files, not 172. Package types (per app identity): %s." % (t["package_files"], ", ".join("%s %d" % kv for kv in dist.most_common())), "",
         "## 2. NetSpout catalog mapping", "", "NetSpout catalog: %d vendors, %d products, %d sourcetypes (docs/reference/sourcetype_coverage.json, reconciled with catalog/vendors.json)." % (t["catalog_vendors"], t["catalog_products"], t["catalog_sourcetypes"]), "",
         table(["match type", "catalog sourcetypes", "meaning"], [
             ["exact", t["match_types"].get("exact", 0), "name literally defined by a downloaded add-on (file:stanza recorded)"],
             ["conflict", t["match_types"].get("conflict", 0), "add-on defines a close but different name, or only renames the catalog's name (naming conflict)"],
             ["candidate", t["match_types"].get("candidate", 0), "an add-on names the vendor/product, but none of its sourcetypes corresponds"],
             ["none", t["match_types"].get("none", 0), "no downloaded add-on covers the vendor"]]), "",
         table(["measure", "value"], [
             ["exact matches with a payload-format conflict", t["exact_with_payload_conflict"]], ["exact matches with a routing (metric/event) conflict", t["exact_with_routing_conflict"]], ["naming conflicts", t["naming_conflicts"]],
             ["catalog sourcetypes with a generator that really produces events", "%d of %d" % (t["generators_valid"], t["catalog_sourcetypes"])], ["...of which exact matches", t["generators_valid_exact"]],
             ["sample-backed catalog sourcetypes (shipped YAML or external corpus)", t["sample_backed"]], ["format verification", ", ".join("%s %d" % kv for kv in t["format_verification"].items())],
             ["ingestion support of the exact matches", ", ".join("%s %d" % kv for kv in t["ingestion_support_exact_rows"].items())],
             ["live Splunk-verified (Phase 4 evidence only)", t["live_verified"]], ["catalog sourcetypes with no covering package", t["catalog_sourcetypes_without_covering_package"]],
             ["catalog sourcetypes not defined by any package", t["catalog_sourcetypes_not_defined_by_any_package"]], ["TA sourcetype names absent from the NetSpout catalog", t["ta_sourcetypes_absent_from_netspout"]]]), "",
         "Live-verified (unchanged, evidence in docs/verification/evidence/ta_compat): " + ", ".join(sorted(r["catalog_sourcetype"] + " (" + r["ta_app_id"] + " " + r["package_version"] + ")" for r in rows if r["live_verification"].startswith("SPLUNK"))) + ".", "",
         "Reconciliation with Phase 4: the 14 Phase 4 packages define %d catalog names; Phase 5 finds the same %d (equal=%s). Phase 5 re-classifies add-on legacy names that the add-on renames as naming conflicts, so its exact count is lower than Phase 4's literal-name count." % (
             t["reconciliation_with_phase4"]["phase4_exact_names_in_14_packages"], t["reconciliation_with_phase4"]["phase5_catalog_names_defined_by_the_same_14_packages"], t["reconciliation_with_phase4"]["equal"]), "",
         "## 3. Ingestion mechanisms (per app identity; config-declared first, README mentions are weaker evidence)", "", table(["mechanism category", "app identities"], cats.most_common()), "",
         "NetSpout delivers HEC JSON events/metrics and syslog, and has NetFlow/IPFIX, SNMP and gNMI exporters. It does not emulate vendor REST APIs, host agents, scripted inputs, JDBC or the Stream collector. "
         "`SUBSTITUTE_VIA_HEC` means the add-on's real input is one of those and NetSpout could only deliver equivalent events over HEC; it does not mean the integration works.", "",
         "Routing conflicts (catalog promises a metric index, add-on defines an event sourcetype): " + (", ".join("`%s`" % x["catalog"] for x in mism["routing_conflicts"]) or "none") + ".", "",
         "## 4. Vendor coverage", "", table(["vendor", "products", "ST", "add-ons", "exact", "naming conf.", "payload/route conf.", "valid gen.", "sample", "live", "specialized ingest", "main blockers"],
             [[v["vendor"], v["products"], v["catalog_sourcetypes"], v["downloaded_matching_addons"], v["exact_canonical_matches"], v["naming_conflicts"], v["payload_or_routing_conflicts"], v["valid_generators"], v["sample_backed"], v["live_verified"], v["specialized_ingestion_required"], "; ".join(v["main_blockers"])] for v in vc["vendors"]]), "",
         "Vendors with no downloaded add-on: %d of %d." % (sum(1 for v in vc["vendors"] if not v["downloaded_matching_addons"]), len(vc["vendors"])), "",
         "## 5. Top 10 next integrations to repair", "", "Ranking: exact name, working generator and a replayable sample or native generator, delivery NetSpout already performs, scenario references, then risk. Number of sourcetypes an add-on defines is not a factor. "
         "None is verified; each is a candidate for the Phase 4 method (spec, one add-on at a time in the validation lab).", "",
         table(["#", "integration", "add-on", "ready sourcetypes (first 4)", "evidence", "complexity", "risks"], [[s["rank"], s["vendor"], "%s %s" % (s["ta_app_id"], s["package_version"]), ", ".join(s["exact_sourcetypes_ready"][:4]) + (" (+%d)" % (s["exact_ready_count"] - 4) if s["exact_ready_count"] > 4 else ""), s["evidence"], s["estimated_complexity"], "; ".join(s["risks"]) or "none found"] for s in top]), "",
         "Files: master_matrix.json/.csv, vendor_coverage.json/.csv, sourcetype_mismatches.json, ingestion_classification.json, top10_shortlist.json, package_inventory.json/.csv, ta_sourcetype_index.csv (every TA sourcetype with its defining file:stanza).", "",
         "## 6. Limitations", "",
         "- The inventory reads configuration only. No package was installed or executed, so modular-input behaviour, lookups' contents, scripts and search-time behaviour were not observed.",
         "- Sourcetype lists come from props.conf stanzas, transforms.conf routing rules, inputs.conf and rename targets. Sourcetypes assigned inside modular-input code (bin/) are not visible; the true list for API add-ons can be larger.",
         "- Catalog-vendor to add-on mapping is a by-name identification (VENDOR_PACKAGES in scripts/build_phase5_matrix.py). It yields `candidate`, never a support claim; `exact` needs a defined sourcetype.",
         "- 'Distinct vendors by monitored product' uses rules over app labels (scripts/build_phase5_matrix.py); publishers in app.conf are inconsistent, so both numbers are given.",
         "- FORMAT_VERIFIED means NetSpout's rendered events satisfy the add-on's own regex/DELIMS extractions as evaluated by Python `re` (a stand-in for Splunk's PCRE); STRUCTURE_ONLY means JSON parses but field names were not compared; none of this is live evidence.",
         "- Ingestion support is inferred from inputs.conf stanza types, README mentions and sourcetype shape. A README that only mentions OpenTelemetry/CEF as framework boilerplate is ignored unless the app is a telemetry collector.",
         "- CIM data-model validation, non-UTC time zones, and every sourcetype other than the four Phase 4 integrations remain unverified in Splunk.",
         "- Catalog metadata quirks are reported, not fixed (for example, `cisco:sdwan:sytem:logs` and `cisco:sdwan:system:logs` both exist; Windows data uses sourcetype `XmlWinEventLog` with source `XmlWinEventLog:Security`).", ""]
    (P5 / "PHASE5_REPORT.md").write_text("\n".join(o))
    print(len("\n".join(o)), "bytes")


if __name__ == "__main__":
    main()
