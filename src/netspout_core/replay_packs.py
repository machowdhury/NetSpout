"""Scenario packs that run on the replay engine: replay phases (authentic recordings) and native phases (existing scenario packs) on one timeline.

Correlation is only what the sources really share. Replayed recordings are never rewritten to fake a shared incident: their cross-source relation is
TEMPORAL_ONLY (the pack's phase offsets). Every event additionally carries HEC indexed fields netspout_scenario_id / netspout_run_id / netspout_phase /
netspout_source_kind / netspout_cycle so one run is searchable as a unit; those fields are not part of _raw. Native phases are regenerated each cycle.
"""
import json
import threading
from pathlib import Path
from typing import Dict, List

from netspout_core.sample_replay import Item, ReplayError, Timeline, build_timeline, TimestampRule

_HERE = Path(__file__).resolve().parent


def _path():
    for d in [_HERE / "catalog_data", _HERE.parents[1] / "catalog", _HERE.parent / "catalog"]:
        if (d / "replay_packs.json").is_file():
            return d / "replay_packs.json"
    raise FileNotFoundError("replay_packs.json missing")


def packs() -> List[Dict]:
    return json.loads(_path().read_text())["packs"]


def get(pack_id: str) -> Dict:
    p = next((x for x in packs() if x["id"] == pack_id), None)
    if not p:
        raise ReplayError("unknown replay pack")
    return p


def correlation_level(pack: Dict) -> str:
    kinds = {ph["source"]["kind"] for ph in pack["phases"]}
    if kinds == {"native"}:
        return "NATIVE_CORRELATED" if len(pack["phases"]) == 1 else "NATIVE_CORRELATED_WITHIN_PACKS_TEMPORAL_BETWEEN"
    return "MIXED_TEMPORAL_ONLY_BETWEEN_SOURCES" if "native" in kinds else "TEMPORAL_ONLY"


def _native_producer(pack_id, run_id, index):
    from netspout_core.authentic_scenario_packs import run_scenario_pack
    cache, lock = {}, threading.Lock()

    def produce(cycle):
        with lock:
            if cycle not in cache:
                cache.clear()   # one cycle at a time; the producer walks items in order
                cache[cycle] = run_scenario_pack(pack_id, "%s-c%d" % (run_id, cycle))
        return cache[cycle][index].raw_log
    return produce


def build_pack_timeline(pack_id: str, *, run_id=None, cycle_gap_s=None) -> Timeline:
    from netspout_core.replay_service import sources, source_text
    from netspout_core.authentic_scenario_packs import run_scenario_pack
    pack = get(pack_id)
    run_id = run_id or "%s-%d" % (pack_id, pack["seed"])
    registry = {s["id"]: s for s in sources()}
    items: List[Item] = []
    for ph in pack["phases"]:
        src, base = ph["source"], float(ph["offset_s"])
        tags = {"netspout_scenario_id": pack_id, "netspout_run_id": run_id, "netspout_phase": ph["id"], "netspout_source_kind": src["kind"]}
        if src["kind"] == "replay":
            entry = registry.get(src["source_id"])
            if not entry:
                raise ReplayError("pack %s names an unknown replay source" % pack_id)
            rule = TimestampRule(**entry["timestamp_rule"])
            tl = build_timeline(source_text(entry), entry["format"], rule, record_start=entry.get("record_start"), max_gap_s=src.get("max_gap_s"))
            chosen = tl.items[:src["max_records"]] if src.get("max_records") else tl.items
            for it in chosen:
                items.append(Item(it.record, it.span, it.original, base + it.offset, rule=rule, sourcetype=entry["sourcetype"], fields=tags))
        elif src["kind"] == "native":
            sample = run_scenario_pack(src["pack"], run_id + "-probe")
            for i, ev in enumerate(sample):
                ftags = {**tags, "netspout_source_pack": src["pack"], "netspout_pack_phase": ev.netspout_phase}
                items.append(Item(None, None, None, base + i * float(src["spacing_s"]), sourcetype=ev.sourcetype, fields=ftags,
                                  producer=_native_producer(src["pack"], run_id, i)))
        else:
            raise ReplayError("unknown phase source kind")
    items.sort(key=lambda it: it.offset)   # stable: equal offsets keep phase then record order
    span = items[-1].offset
    gap = float(cycle_gap_s) if cycle_gap_s is not None else max(5.0, span * 0.1)
    if gap <= 0:
        raise ReplayError("cycle_gap_s must be positive")
    tl = Timeline(items, None, "PACK_SCHEDULE_OVER_SOURCE_SPACING", gap, span)
    tl.pack_id, tl.run_id = pack_id, run_id
    return tl
