# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/universal_search.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""One search across sourcetypes, scenarios (Explorer entries) and installed dashboards, built only from the existing registries.

Nothing here upgrades a status: runnable/dashboard/maturity values are copied from the source records, and catalog-only or
unsupported items stay in the results with their status so they are never presented as executable.
"""
import html
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

_TOKEN = re.compile(r"[a-z0-9]+")
_LABEL = re.compile(r"<label>(.*?)</label>", re.S)
_DESC = re.compile(r"<description>(.*?)</description>", re.S)


def _tokens(text: str) -> List[str]:
    return _TOKEN.findall(text.lower())


def dashboard_views(views_dir: Path, maturity: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Installed pf_* Dashboard Studio views; title/description come from the view XML, maturity from stored evidence only."""
    out = []
    for f in sorted(views_dir.glob("pf_*.xml")):
        xml = f.read_text(encoding="utf-8")
        label, desc = _LABEL.search(xml), _DESC.search(xml)
        view = f.stem
        out.append({"view": view, "title": html.unescape(label.group(1).strip()) if label else view,
                    "description": html.unescape(desc.group(1).strip()) if desc else "",
                    "maturity": (maturity.get(view[3:]) or {}).get("maturity")})
    return out


def build_records(sourcetypes: Iterable[Dict[str, Any]], entries: Iterable[Dict[str, Any]], dashboards: Iterable[Dict[str, Any]], streamable: Optional[Dict[str, str]] = None) -> List[Dict[str, Any]]:
    """streamable maps a sourcetype to the grounded path that can stream it (native or grounded_sample); when given, only those are runnable."""
    entries = list(entries)
    by_view: Dict[str, List[Dict[str, Any]]] = {}
    for e in entries:
        v = (e.get("dashboard") or {}).get("splunk_view")
        if v:
            by_view.setdefault(v, []).append(e)
    st_scen: Dict[str, List[str]] = {}
    for e in entries:
        for s in list(e.get("sourcetypes") or []) + list(e.get("source_ids") or []):
            st_scen.setdefault(s, []).append(e["entry_id"])
    recs: List[Dict[str, Any]] = []
    for s in sourcetypes:
        name = s.get("splunk_sourcetype") or s.get("sourcetype") or s["id"]
        generated = (name in streamable) if streamable is not None else s.get("generation_mode") not in (None, "", "NONE", "UNSUPPORTED")
        recs.append({
            "kind": "sourcetype", "id": s["id"], "title": name, "subtitle": s.get("display_name"),
            "vendor": s.get("vendor_id"), "category": s.get("category"), "protocol": s.get("protocol"),
            "data_format": s.get("data_kind"), "execution_mode": (streamable or {}).get(name) or s.get("generation_mode"),
            "status": s.get("status"), "runnable": generated,
            "related_scenarios": st_scen.get(name, []) + st_scen.get(s["id"], []),
            "next_action": "Stream continuously or for a count/duration" if generated else "Catalog entry only: no authentic generator or verified sample is available",
            "_text": [(name, 5), (s.get("display_name") or "", 4), (s.get("vendor_id") or "", 3), (s.get("category") or "", 2), (s.get("protocol") or "", 2), (s.get("data_kind") or "", 1), (" ".join(s.get("aliases") or []), 2)],
        })
    for e in entries:
        dash = e.get("dashboard") or {}
        recs.append({
            "kind": "scenario", "id": e["entry_id"], "title": e["title"], "subtitle": e.get("scenario_id"),
            "vendor": ", ".join(e.get("vendors") or []), "category": e.get("category"), "industries": [i["id"] for i in e.get("industries") or []],
            "execution_mode": e.get("engine"), "maturity": (e.get("maturity") or {}).get("tier"), "runnable": bool(e.get("runnable")),
            "relation": "; ".join(("NetFlow profile of " if r["relation"] == "parent_pack" else "Has NetFlow profile ") + r["scenario_id"] for r in e.get("related") or []) or None,
            "blocked_reason": e.get("blocked_reason"), "dashboard_view": dash.get("splunk_view"), "dashboard_available": bool(dash.get("splunk_view")),
            "independently_indexed": bool(e.get("live_verified")), "related_sourcetypes": list(e.get("sourcetypes") or []) + list(e.get("source_ids") or []),
            "next_action": "Review, run and monitor" if e.get("runnable") else "Catalog only: " + (e.get("blocked_reason") or "not executable"),
            "_text": [(e["title"], 5), (e.get("scenario_id") or "", 5), (e.get("summary") or "", 1), (e.get("domain") or "", 2), (e.get("category") or "", 2), (" ".join(e.get("vendors") or []), 3), (" ".join(i["id"] for i in e.get("industries") or []), 2), (" ".join(e.get("sourcetypes") or []), 2)],
        })
    for d in dashboards:
        rel = by_view.get(d["view"], [])
        recs.append({
            "kind": "dashboard", "id": d["view"], "title": d["title"], "subtitle": d["view"], "maturity": d["maturity"], "runnable": False,
            "dashboard_available": True, "dashboard_view": d["view"], "related_scenarios": [e["entry_id"] for e in rel],
            "related_sourcetypes": sorted({s for e in rel for s in (e.get("sourcetypes") or [])}),
            "next_action": "Open dashboard (may be empty until its scenario is indexed)",
            "_text": [(d["title"], 5), (d["view"], 4), (d["description"], 2), (" ".join(e["title"] for e in rel), 2)],
        })
    return recs


def search(records: List[Dict[str, Any]], q: str = "", kind: Optional[str] = None, filters: Optional[Dict[str, Any]] = None, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
    filters = {k: v for k, v in (filters or {}).items() if v not in (None, "")}
    terms = _tokens(q)
    hits = []
    for r in records:
        if kind and r["kind"] != kind:
            continue
        if any(not _match(r, k, v) for k, v in filters.items()):
            continue
        score = 0
        for t in terms:
            best = 0
            for text, w in r["_text"]:
                toks = _tokens(text)
                if t in toks:
                    best = max(best, w * 2)
                elif any(x.startswith(t) for x in toks):
                    best = max(best, w * 1.5)
                elif t in text.lower():
                    best = max(best, w)
            if not best:
                score = -1
                break
            score += best
        if score >= 0:
            hits.append((score, r))
    hits.sort(key=lambda h: (-h[0], h[1]["kind"], h[1]["title"]))
    counts: Dict[str, int] = {}
    for _, r in hits:
        counts[r["kind"]] = counts.get(r["kind"], 0) + 1
    page = [{k: v for k, v in r.items() if k != "_text"} for _, r in hits[offset:offset + limit]]
    return {"query": q, "total": len(hits), "counts": counts, "offset": offset, "limit": limit, "items": page}


def _match(r: Dict[str, Any], key: str, value: Any) -> bool:
    if key in ("runnable", "dashboard_available", "independently_indexed"):
        return bool(r.get(key)) == (str(value).lower() in ("1", "true", "yes"))
    if key == "industry":
        return value in (r.get("industries") or [])
    got = r.get(key)
    return got is not None and str(value).lower() in str(got).lower()
