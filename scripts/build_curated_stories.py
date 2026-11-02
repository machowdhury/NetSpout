#!/usr/bin/env python3
"""Build catalog/curated_analytic_stories.json: Splunk Analytic Stories whose OWN text names an approved industry as a threat target.

Source: catalog/phase13a_splunk_security_content.json (splunk/security_content, pinned commit recorded there). Basis is NARRATIVE_TARGET_SECTOR:
the story description or narrative explicitly names the sector. That is relevance evidence, not a customer claim, and not an execution claim:
curated stories are NOT executable unless the Explorer reports a runtime-approved detection for them (today only React2Shell).
Every selected story's original research.splunk.com URL is checked (HTTP 200) at build time and the build fails otherwise. Only story id, name,
URL, the matched phrase and detection/replay counts are recorded; no narrative text is copied. Industries with no matching story stay empty.

Run: python scripts/build_curated_stories.py   (needs network once)
"""
import json
import re
import urllib.request
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PER_INDUSTRY = 4
PATTERNS = {
    "banking-financial-services": r"\bbank(s|ing)\b|financial (institutions?|sectors?|services?)",
    "healthcare": r"\bhealthcare\b|\bhospitals?\b",
    "energy-utilities": r"\benergy sector\b|\bpower grid\b|\boil and gas\b|\bcritical infrastructure\b|\bSCADA\b|industrial control systems?|\butility sector\b|manufacturing, utility",
    "telecommunications": r"\btelecom(munications?)?\b",
    "government-public-sector": r"\bgovernment\b|public sector",
    "manufacturing": r"\bmanufactur\w+",
    "education": r"\beducation(al)?\b|\buniversit(y|ies)\b",
    "retail-ecommerce": r"\bretail\b|\be-?commerce\b|point[- ]of[- ]sale",
    "hospitality-travel": r"\bhospitality\b|\bhotels?\b|\bcasinos?\b",
    "transportation-logistics": r"\btransportation\b|\blogistics\b|\bmaritime\b",
    "insurance-insurtech": r"\binsurance\b",
    "aerospace-defense": r"\baerospace\b|\bdefen[cs]e (sector|contractor|industry)\b|\bmilitary\b",
    "technology-saas": r"technology sectors?|software supply chain",
    "media-entertainment": r"\bmedia (sector|industry|compan\w+)\b|\bentertainment\b",
    "legal-compliance-professional-services": r"\blaw firms?\b|\blegal sector\b|\blegal,|professional services",
    "real-estate-proptech-construction": r"\breal estate\b|\bconstruction (sector|industry|compan\w+)\b|, construction,",
    "nonprofit-ngo-global-aid": r"\bnon-?profit\b|\bngos?\b",
    "agriculture-agritech": r"\bagricultur\w+",
}
GOV_SUBDOMAIN = {"gov-national-security": r"\bmilitary\b|\bdefen[cs]e\b|\bintelligence\b", "gov-critical-infrastructure": r"\bcritical infrastructure\b"}


def status(url):
    try:
        return urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=30).status
    except Exception as exc:
        return getattr(exc, "code", str(exc))


def main():
    doc = json.loads((ROOT / "catalog" / "phase13a_splunk_security_content.json").read_text())
    by_story = defaultdict(list)
    for d in doc["detections"]:
        for name in d.get("analytic_stories", []):
            by_story[name].append(d)
    import concurrent.futures as cf
    def link(story):
        return f"https://research.splunk.com/stories/{re.sub(r'.yml$', '', story['file_path'].split('/', 1)[1])}/"
    with cf.ThreadPoolExecutor(12) as ex:  # a story is eligible only if its original research.splunk.com page exists (about 15% do not resolve)
        live = {s["content_id"] for s, code in zip(doc["analytic_stories"], ex.map(lambda x: status(link(x)), doc["analytic_stories"])) if code == 200}
    scored = defaultdict(list)
    for s in doc["analytic_stories"]:
        if s["content_id"] not in live:
            continue
        text = (s.get("description", "") + " " + s.get("narrative", "")).replace("\n", " ")
        dets = by_story.get(s["name"], [])
        replay = sum(bool(d.get("attack_data")) for d in dets)
        for industry, pattern in PATTERNS.items():
            m = re.search(pattern, text, re.I)
            if m:
                scored[industry].append((-replay, -len(dets), s["name"], s, m.group(0)))
    chosen = {}
    for industry, rows in scored.items():
        for _, _, _, s, phrase in sorted(rows, key=lambda r: r[:3])[:PER_INDUSTRY]:
            rec = chosen.setdefault(s["content_id"], {"content_id": s["content_id"], "name": s["name"], "file_path": s["file_path"], "industries": []})
            text = (s.get("description", "") + " " + s.get("narrative", "")).replace("\n", " ")
            sub = [k for k, p in GOV_SUBDOMAIN.items() if industry == "government-public-sector" and re.search(p, text, re.I)]
            rec["industries"].append({"id": industry, "basis": "NARRATIVE_TARGET_SECTOR", "matched_phrase": phrase.lower(), **({"subdomain": sub[0]} if sub else {})})
    stories = []
    for rec in sorted(chosen.values(), key=lambda r: r["name"].casefold()):
        stem = re.sub(r"\.yml$", "", rec["file_path"].split("/", 1)[1])
        url = f"https://research.splunk.com/stories/{stem}/"
        code = status(url)
        if code != 200:
            raise SystemExit(f"research link for {rec['name']} returned {code}: {url}")
        dets = by_story.get(rec["name"], [])
        stories.append({**rec, "research_url": url, "research_url_http_status": code, "detections_total": len(dets),
                        "detections_with_attack_data": sum(bool(d.get("attack_data")) for d in dets),
                        "data_source_names": sorted({n for d in dets for n in d.get("data_source_names", [])})})
    out = {"schema_version": "1.0", "registry_version": "curated-stories-" + date.today().isoformat(),
           "source": {"repository": doc["detections"][0].get("repository"), "commit": doc["detections"][0].get("repository_commit"),
                      "stories_in_snapshot": len(doc["analytic_stories"])},
           "note": "Curated for sector relevance only. Not executable unless the Explorer reports a runtime-approved detection; research links were HTTP-checked at build time.",
           "stories": stories}
    (ROOT / "catalog" / "curated_analytic_stories.json").write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    per = defaultdict(int)
    for s in stories:
        for i in s["industries"]:
            per[i["id"]] += 1
    print(json.dumps({"curated_stories": len(stories), "per_industry": dict(per), "industries_without_story": [i for i in PATTERNS if i not in per]}))


if __name__ == "__main__":
    main()
