"""Use Case Explorer: one searchable index over runnable operational scenarios and security analytic stories.

The Explorer is a front door onto existing engines (unified generation, ScenarioRunner, dashboards, security
content lab); it does not generate, ingest or validate anything itself. Every maturity or readiness value is
derived from catalog or evidence data and is never upgraded here: a dashboard is only "ready" when the dashboard
service says so, and a detection is only "verified" when a stored validation record says so.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List, Optional

SCHEMA_VERSION = "1.0.0"

# Dashboard Studio views shipped in the Splunk app, keyed by dashboard pack id. A pack without an entry has no deployed view.
SPLUNK_DASHBOARD_VIEWS = {"scenario-sec-p9-b-dns-anomaly": "pulseforge_dns_anomaly_studio"}

# Normalised maturity tiers, strongest first. Raw values come from three scales (catalog, unified generation, dashboards).
_TIER_BY_RAW = {
    "GOLDEN_PATH_CERTIFIED": "CERTIFIED",
    "GOLDEN": "CERTIFIED",
    "E2E_VALIDATED": "VALIDATED",
    "SPLUNK_VALIDATED": "VALIDATED",
    "FORMAT_VALIDATED": "FORMAT_VALIDATED",
    "CONTRACTED": "CONTRACTED",
}
TIER_ORDER = ["CERTIFIED", "VALIDATED", "FORMAT_VALIDATED", "CONTRACTED", "NOT_ESTABLISHED"]
DEMO_READY_TIERS = {"CERTIFIED", "VALIDATED"}

OPERATIONAL_STEPS = ["SELECT", "CONFIGURE", "GENERATE", "INGEST", "VERIFY", "DASHBOARD"]
SECURITY_STEPS = ["SELECT", "PREREQUISITES", "GENERATE", "INGEST", "ENABLE_DETECTION", "VERIFY"]

# Security readiness, strongest first. Each level is justified by data, never assumed.
SECURITY_LEVELS = ["DETECTION_VERIFIED", "RUNTIME_APPROVED", "REPLAY_ONLY", "CONTENT_ONLY", "NO_DETECTIONS"]
_LEVEL_LABELS = {
    "DETECTION_VERIFIED": "Detection logic verified against replayed data (stored evidence)",
    "RUNTIME_APPROVED": "Full workflow available; no stored verification yet",
    "REPLAY_ONLY": "Attack data can be replayed; detection SPL is not approved for bounded runtime execution",
    "CONTENT_ONLY": "Detection content only; no replay dataset",
    "NO_DETECTIONS": "Story has no detections in the snapshot",
}


def _taxonomy_path() -> Path:
    module = Path(__file__).resolve()
    for candidate in (
        module.parents[2] / "catalog" / "explorer_taxonomy.json",
        module.parent / "catalog_data" / "explorer_taxonomy.json",
        module.parent.parent / "catalog_data" / "explorer_taxonomy.json",
        Path("/opt/splunk/etc/apps/netspout/bin/catalog_data/explorer_taxonomy.json"),
    ):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Use Case Explorer taxonomy is unavailable")


def load_taxonomy(path: Optional[Path] = None) -> Dict[str, Any]:
    doc = json.loads((path or _taxonomy_path()).read_text(encoding="utf-8"))
    ids = [i["id"] for i in doc["industries"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate industry id in taxonomy")
    for m in doc["scenario_industries"]:
        unknown = set(m["industries"]) - set(ids)
        if unknown:
            raise ValueError(f"taxonomy maps {m['scenario_id']} to unknown industries {sorted(unknown)}")
    return doc


def maturity_tier(raw: Optional[str]) -> str:
    return _TIER_BY_RAW.get(raw or "", "NOT_ESTABLISHED")


class UseCaseExplorer:
    def __init__(
        self,
        *,
        taxonomy: Dict[str, Any],
        generation_scenarios: Iterable[Dict[str, Any]],
        generation_sources: Iterable[Dict[str, Any]],
        dashboards: Iterable[Dict[str, Any]],
        catalog_scenarios: Iterable[Dict[str, Any]],
        security_catalog: Any,
        validations: Callable[[], List[Dict[str, Any]]],
        runtime_approved_detections: Iterable[str],
        pack_scenario_ids: Iterable[str] = (),
        runner_scenario_ids: Optional[Iterable[str]] = None,
    ):
        # pack_scenario_ids: authentic observation packs, run through /api/generate/scenario-pack.
        # runner_scenario_ids: scenarios ScenarioRunner can execute; None keeps the legacy "all catalog scenarios runnable".
        self._pack_ids = set(pack_scenario_ids)
        self._runner_ids = None if runner_scenario_ids is None else set(runner_scenario_ids)
        self.taxonomy = taxonomy
        self._industry_ids = [i["id"] for i in taxonomy["industries"]]
        self._validations = validations
        self._approved = set(runtime_approved_detections)
        self._security_catalog = security_catalog

        sources = {s["source_id"]: s for s in generation_sources}
        dashboards = list(dashboards)
        by_scenario: Dict[str, Dict[str, Any]] = {}
        for d in dashboards:
            # Prefer the scenario-bound dashboard over industry-pack dashboards that reuse the same scenario.
            key = d.get("runtime_scenario_id") or d.get("scenario_id")
            if key and (key not in by_scenario or not d.get("industry_id")):
                by_scenario[key] = d
        self._dashboards = by_scenario
        self._industry_dash_basis: Dict[str, List[str]] = {}
        for d in dashboards:
            if d.get("industry_id"):
                self._industry_dash_basis.setdefault(d.get("scenario_id"), []).append(d["industry_id"])

        mapped: Dict[str, List[Dict[str, str]]] = {}
        for m in taxonomy["scenario_industries"]:
            for ind in m["industries"]:
                mapped.setdefault(m["scenario_id"], []).append({"id": ind, "basis": m["basis"]})
        self._industry_map = mapped

        entries: List[Dict[str, Any]] = []
        for s in generation_scenarios:
            entries.append(self._unified_entry(s, sources))
        for s in catalog_scenarios:
            entries.append(self._catalog_entry(s))
        self._operational = entries
        self._security: Optional[List[Dict[str, Any]]] = None

    # ------------------------------------------------------------------ operational
    def _industries_for(self, scenario_id: str) -> List[Dict[str, str]]:
        found = list(self._industry_map.get(scenario_id, []))
        seen = {(i["id"], i["basis"]) for i in found}
        for ind in self._industry_dash_basis.get(scenario_id, []):
            if (ind, "industry_pack") not in seen:
                found.append({"id": ind, "basis": "industry_pack"})
        return [i for i in found if i["id"] in self._industry_ids]

    def _dashboard_ref(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        d = self._dashboards.get(scenario_id)
        if not d:
            return None
        return {
            "dashboard_id": d["dashboard_id"],
            "eligibility": d["state"],
            "dashboard_maturity": d["dashboard_maturity"],
            "reasons": d.get("reasons", []),
            "splunk_view": SPLUNK_DASHBOARD_VIEWS.get(d["dashboard_id"]),
        }

    def _unified_entry(self, s: Dict[str, Any], sources: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        sid = s["scenario_id"]
        dash = self._dashboard_ref(sid)
        raw = (self._dashboards.get(sid) or {}).get("scenario_maturity") or s.get("scenario_maturity") or "NOT_ESTABLISHED"
        vendors = sorted({sources[x]["vendor"] for x in s.get("source_ids", []) if x in sources})
        return self._operational_entry(
            entry_id=f"op:unified:{sid}", engine="unified_generation", scenario_id=sid,
            title=s["title"], summary=s.get("description", ""), domain=s.get("domain", ""),
            category=s.get("category", ""), vendors=vendors, sourcetypes=[], source_ids=list(s.get("source_ids", [])),
            raw_maturity=raw, runnable=bool(s.get("runnable")), blocked_reason=s.get("blocked_reason"),
            dashboard=dash,
        )

    def _catalog_entry(self, s: Dict[str, Any]) -> Dict[str, Any]:
        sid = s["id"]
        engine, runnable, blocked = "scenario_runner", True, None
        if sid in self._pack_ids:
            engine = "scenario_pack"
        elif self._runner_ids is not None and sid not in self._runner_ids:
            runnable, blocked = False, "Contract only in this release: no executable telemetry is implemented for this scenario"
        return self._operational_entry(
            entry_id=f"op:{'pack' if engine == 'scenario_pack' else 'runner'}:{sid}", engine=engine, scenario_id=sid,
            title=s.get("display_name") or s.get("name", sid), summary=s.get("description", ""),
            domain=str(s.get("category", "")).replace("_", " ").title(), category=s.get("category", ""),
            vendors=list(s.get("vendor_scope", [])), sourcetypes=list(s.get("sourcetypes", [])), source_ids=[],
            raw_maturity=s.get("maturity", "NOT_ESTABLISHED"), runnable=runnable, blocked_reason=blocked,
            dashboard=self._dashboard_ref(sid),
        )

    def _operational_entry(self, *, entry_id, engine, scenario_id, title, summary, domain, category, vendors,
                           sourcetypes, source_ids, raw_maturity, runnable, blocked_reason, dashboard):
        tier = maturity_tier(raw_maturity)
        entry = {
            "entry_id": entry_id, "kind": "operational", "engine": engine, "scenario_id": scenario_id,
            "title": title, "summary": summary, "domain": domain, "category": category,
            "industries": self._industries_for(scenario_id), "vendors": vendors,
            "sourcetypes": sourcetypes, "source_ids": source_ids,
            "maturity": {"tier": tier, "raw": raw_maturity, "basis": "catalog"},
            "runnable": runnable, "blocked_reason": blocked_reason,
            "demo_ready": runnable and tier in DEMO_READY_TIERS,
            "dashboard": dashboard,
        }
        entry["workflow"] = self._operational_workflow(entry)
        return entry

    @staticmethod
    def _operational_workflow(e: Dict[str, Any]) -> List[Dict[str, Any]]:
        sid = e["scenario_id"]
        if e["engine"] == "unified_generation":
            body = {"mode": "SCENARIO", "selection_id": sid}
            cfg = ("POST", "/api/generation/preflight", body)
            gen = ("POST", "/api/generation/runs", body)
            ver = ("POST", "/api/generation/runs/{run_id}/observe", None)
            ing_note = "HEC acknowledgement is recorded per required channel (stage SPLUNK_DISPATCHED)"
            ver_note = "Success = SPLUNK_OBSERVED PROVEN for every required channel"
        elif e["engine"] == "scenario_pack":
            cfg = ("GET", "/api/setup", None)
            gen = ("POST", "/api/generate/scenario-pack", {"scenario_id": sid, "dispatch": True})
            ver = ("POST", "/api/explorer/observe", {"run_id": "{run_id}"})
            ing_note = "HEC acceptance is counted per event from the dispatch results (accepted must equal generated)"
            ver_note = "Success = Splunk's run-scoped event count equals the number of events generated (independent search)"
        else:
            cfg = ("GET", f"/api/scenarios/{sid}", None)
            gen = ("POST", f"/api/scenarios/{sid}/run", {"dispatch_telemetry": True})
            ver = ("GET", "/api/scenarios/runs/{run_id}/observation", None)
            ing_note = "HEC dispatch counts are on the run manifest (dispatch_succeeded / dispatch_failed)"
            ver_note = "Success = observation required_evidence_satisfied true (Gate 8 evidence contract v1.0)"
        blocked = None if e["runnable"] else (e["blocked_reason"] or "scenario is not runnable")
        dash = e["dashboard"]
        dash_blocked = None
        if not dash:
            dash_blocked = "no dashboard recipe is bound to this scenario"
        elif dash["eligibility"] != "ELIGIBLE":
            dash_blocked = "; ".join(dash["reasons"]) or "dashboard is not eligible"
        elif e["engine"] != "unified_generation":
            dash_blocked = "dashboard validation requires a unified generation run"
        def step(name, method=None, path=None, body=None, note="", blocked_reason=None):
            return {"step": name, "endpoint": {"method": method, "path": path, "body": body} if path else None,
                    "available": blocked_reason is None, "blocked_reason": blocked_reason, "success_criterion": note}
        return [
            step("SELECT", note="Entry chosen from the Explorer"),
            step("CONFIGURE", *cfg, note="Preflight reports destination/transport readiness; no data is sent", blocked_reason=blocked),
            step("GENERATE", *gen, note="Modeled telemetry is produced and dispatched to the configured destination", blocked_reason=blocked),
            step("INGEST", note=ing_note, blocked_reason=blocked),
            step("VERIFY", *ver, note=ver_note, blocked_reason=blocked),
            step("DASHBOARD", "GET", f"/api/dashboards/{dash['dashboard_id']}?run_id={{run_id}}" if dash else None, None,
                 "Panels are generated for the run; readiness is whatever dashboard validation records, never assumed",
                 blocked_reason=blocked or dash_blocked),
        ]

    # ------------------------------------------------------------------ security
    def _verified_detections(self) -> Dict[str, Dict[str, Any]]:
        ok = {}
        for v in self._validations():
            if v.get("status") == "POSITIVE_CASE_VALIDATED" and v.get("detection_id"):
                ok[v["detection_id"]] = v
        return ok

    def security_entries(self) -> List[Dict[str, Any]]:
        # Rebuilt on every call so newly stored validation evidence is reflected immediately.
        cat = self._security_catalog
        doc = cat.document
        by_story: Dict[str, List[Dict[str, Any]]] = {}
        for d in doc["detections"]:
            for story in d.get("analytic_stories", []):
                by_story.setdefault(story, []).append(d)
        verified = self._verified_detections()
        out = []
        for story in doc["analytic_stories"]:
            dets = by_story.get(story["name"], [])
            det_rows = []
            for d in dets:
                comp = cat.compatibility(d)
                det_rows.append({
                    "replay_datasets": self._replay_datasets(d),
                    "content_id": d["content_id"], "name": d["name"], "detection_type": d.get("detection_type"),
                    "mitre_attack_ids": d.get("mitre_attack_ids", []), "has_attack_data": bool(d.get("attack_data")),
                    "compatibility": comp["status"], "runtime_approved": d["content_id"] in self._approved,
                    "verified": d["content_id"] in verified,
                    "data_source_names": d.get("data_source_names", []),
                })
            level = self._security_level(det_rows)
            mitre = sorted({m for r in det_rows for m in r["mitre_attack_ids"]})
            out.append({
                "entry_id": f"sec:{story['content_id']}", "kind": "security", "story_id": story["content_id"],
                "title": story["name"], "summary": story.get("description", ""),
                "narrative": story.get("narrative", ""), "industries": [], "vendors": [],
                "mitre_attack_ids": mitre, "detections": det_rows,
                "data_sources": sorted({n for r in det_rows for n in r["data_source_names"]}),
                "readiness": {"level": level, "label": _LEVEL_LABELS[level],
                              "detections_total": len(det_rows),
                              "detections_with_replay_data": sum(bool(r["replay_datasets"]) for r in det_rows),
                              "detections_runtime_approved": sum(r["runtime_approved"] for r in det_rows),
                              "detections_verified": sum(r["verified"] for r in det_rows),
                              "production_detection_efficacy": "NOT_ESTABLISHED"},
                "demo_ready": level in ("DETECTION_VERIFIED", "RUNTIME_APPROVED"),
                "workflow": self._security_workflow(level, det_rows),
            })
        return out

    def _replay_datasets(self, detection: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Dataset paths the replay service can actually serve (present in the catalog file index)."""
        found = []
        for item in detection.get("attack_data") or []:
            url = str(item.get("url", ""))
            path = "/" + url.split("/master/", 1)[1] if "/master/" in url else None
            if path and self._security_catalog.get_dataset_file(path) is not None:
                found.append({"dataset_path": path, "sourcetype": item.get("sourcetype")})
        return found

    @staticmethod
    def _security_level(rows: List[Dict[str, Any]]) -> str:
        if not rows:
            return "NO_DETECTIONS"
        if any(r["verified"] for r in rows):
            return "DETECTION_VERIFIED"
        if any(r["runtime_approved"] and r["replay_datasets"] for r in rows):
            return "RUNTIME_APPROVED"
        if any(r["replay_datasets"] for r in rows):
            return "REPLAY_ONLY"
        return "CONTENT_ONLY"

    @staticmethod
    def _security_workflow(level: str, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        replay_blocked = None if level in ("DETECTION_VERIFIED", "RUNTIME_APPROVED", "REPLAY_ONLY") else _LEVEL_LABELS[level]
        enable_blocked = None if level in ("DETECTION_VERIFIED", "RUNTIME_APPROVED") else (
            "no detection in this story is approved for bounded runtime execution" if rows else _LEVEL_LABELS[level])
        def step(name, method=None, path=None, note="", blocked=None):
            return {"step": name, "endpoint": {"method": method, "path": path} if path else None,
                    "available": blocked is None, "blocked_reason": blocked, "success_criterion": note}
        return [
            step("SELECT", note="Analytic story chosen from the Explorer"),
            step("PREREQUISITES", "GET", "/api/explorer/entries/{entry_id}/prerequisites",
                 "Connection Center configured, index authorized, credentials present, detection dependencies resolved"),
            step("GENERATE", "POST", "/api/security-content/datasets/retrieve",
                 "Pinned upstream attack dataset is retrieved and previewable", replay_blocked),
            step("INGEST", "POST", "/api/security-content/replays",
                 "Replay run reports events_sent; Splunk-side count is confirmed by the observe call", replay_blocked),
            step("ENABLE_DETECTION", "POST", "/api/explorer/detections/{detection_id}/enable",
                 "Saved search exists in Splunk and is read back as enabled", enable_blocked),
            step("VERIFY", "POST", "/api/security-content/validations",
                 "POSITIVE_CASE_VALIDATED means the detection SPL matched run-scoped replayed events; "
                 "it does not prove scheduled-alert firing or production efficacy", enable_blocked),
        ]

    # ------------------------------------------------------------------ queries
    def all_entries(self) -> List[Dict[str, Any]]:
        return self._operational + self.security_entries()

    def get(self, entry_id: str) -> Optional[Dict[str, Any]]:
        return next((e for e in self.all_entries() if e["entry_id"] == entry_id), None)

    def industries(self) -> List[Dict[str, Any]]:
        rows = []
        for ind in self.taxonomy["industries"]:
            mine = [e for e in self._operational if any(i["id"] == ind["id"] for i in e["industries"])]
            rows.append({
                **ind,
                "scenarios_total": len(mine),
                "scenarios_demo_ready": sum(e["demo_ready"] for e in mine),
                "bases": sorted({i["basis"] for e in mine for i in e["industries"] if i["id"] == ind["id"]}),
            })
        return rows

    def search(self, *, q: str = "", kind: Optional[str] = None, industry: Optional[str] = None,
               tier: Optional[str] = None, vendor: Optional[str] = None, demo_ready: Optional[bool] = None,
               readiness: Optional[str] = None, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        needle = q.casefold().strip()
        def match(e: Dict[str, Any]) -> bool:
            if kind and e["kind"] != kind:
                return False
            if industry and not any(i["id"] == industry for i in e["industries"]):
                return False
            if tier and e.get("maturity", {}).get("tier") != tier:
                return False
            if readiness and e.get("readiness", {}).get("level") != readiness:
                return False
            if vendor and vendor.casefold() not in [v.casefold() for v in e["vendors"]]:
                return False
            if demo_ready is not None and e["demo_ready"] != demo_ready:
                return False
            if needle:
                hay = " ".join([e["title"], e["summary"], " ".join(e["vendors"]), " ".join(e.get("sourcetypes", [])),
                                " ".join(e.get("mitre_attack_ids", [])), " ".join(e.get("data_sources", [])),
                                e.get("domain", ""), e.get("scenario_id", "")]).casefold()
                if not all(tok in hay for tok in needle.split()):
                    return False
            return True
        hits = [e for e in self.all_entries() if match(e)]
        def rank(e):
            if e["kind"] == "operational":
                return (0 if e["demo_ready"] else 1, TIER_ORDER.index(e["maturity"]["tier"]), e["title"].casefold())
            return (0 if e["demo_ready"] else 1, SECURITY_LEVELS.index(e["readiness"]["level"]), e["title"].casefold())
        hits.sort(key=rank)
        limit = max(1, min(limit, 200))
        # List view omits the heavy per-detection rows; the detail call returns them.
        def slim(e):
            return {k: v for k, v in e.items() if k not in ("detections", "narrative")} if e["kind"] == "security" else e
        return {
            "schema_version": SCHEMA_VERSION, "total": len(hits), "offset": offset, "limit": limit,
            "items": [slim(e) for e in hits[offset: offset + limit]],
        }

    def facets(self) -> Dict[str, Any]:
        ops = self._operational
        sec = self.security_entries()
        def count(rows, key):
            out: Dict[str, int] = {}
            for r in rows:
                out[key(r)] = out.get(key(r), 0) + 1
            return out
        return {
            "schema_version": SCHEMA_VERSION,
            "operational": {"total": len(ops), "demo_ready": sum(e["demo_ready"] for e in ops),
                            "by_tier": count(ops, lambda e: e["maturity"]["tier"]),
                            "vendors": sorted({v.casefold(): v for e in ops for v in e["vendors"]}.values(), key=str.casefold)},
            "security": {"total": len(sec), "demo_ready": sum(e["demo_ready"] for e in sec),
                         "by_readiness": count(sec, lambda e: e["readiness"]["level"])},
            "taxonomy": {"status": self.taxonomy["taxonomy_status"], "version": self.taxonomy["taxonomy_version"],
                         "note": self.taxonomy["taxonomy_note"]},
        }

    # ------------------------------------------------------------------ prerequisites
    def prerequisites(self, entry_id: str, setup: Dict[str, Any], index: Optional[str] = None) -> Dict[str, Any]:
        """Evaluate configuration prerequisites from local state only. No Splunk call is made here, so
        reachability is reported NOT_TESTED rather than inferred."""
        entry = self.get(entry_id)
        if entry is None:
            raise KeyError("Explorer entry not found")
        secrets = setup.get("secret_state") or {}
        checks: List[Dict[str, Any]] = []
        def add(cid, label, ok, detail):
            checks.append({"check_id": cid, "label": label, "state": "PASS" if ok else "FAIL", "detail": detail})
        configured = bool(setup.get("configured"))
        add("connection_center", "Connection Center configured", configured,
            "Destination, credentials and authorized indexes are saved" if configured else "Complete Connection Center setup first")
        indexes = list(setup.get("indexes") or [])
        if index:
            add("index_authorized", f"Index '{index}' authorized", index in indexes,
                "Index is in the authorized list" if index in indexes else f"Authorized indexes: {', '.join(indexes) or 'none'}")
        add("hec_credential", "HEC credential present", bool(secrets.get("hec_token_configured")),
            "Credential presence only; the value is never returned")
        if entry["kind"] == "security":
            add("search_credential", "Splunk search credential present",
                bool(secrets.get("search_secret_configured")),
                "Required to enable and verify detections")
            r = entry["readiness"]
            add("replay_data", "Replay dataset available", r["detections_with_replay_data"] > 0,
                f"{r['detections_with_replay_data']} of {r['detections_total']} detections have curated attack data")
            add("runtime_approved", "Detection approved for bounded runtime execution", r["detections_runtime_approved"] > 0,
                f"{r['detections_runtime_approved']} approved; unapproved SPL is never executed")
        else:
            add("runnable", "Scenario runnable", entry["runnable"], entry["blocked_reason"] or "Scenario has a runnable contract")
        return {"entry_id": entry_id, "checks": checks,
                "ready": all(c["state"] == "PASS" for c in checks),
                "live_reachability": "NOT_TESTED"}
