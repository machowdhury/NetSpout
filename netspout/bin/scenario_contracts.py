# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/scenario_contracts.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""
Declarative scenario contracts.

A contract is data (catalog/scenario_contracts.json), not code: shared topology nodes, ordered phases, and streams that bind a documented generator
(a SplunkLogEngine formatter) to a node with per-phase parameters. The same loop runs every contract, so a scenario no longer needs its own
hundreds of lines of phase logic.

What this layer guarantees, and what it does not:
  * Events come from the existing vendor formatters called with the contract's shared Node and entity parameters. Nothing here writes a vendor
    log line; a contract can only bind a formatter that exists and can only pass parameters that formatter accepts (checked against its signature).
  * Every stream declares its sourcetype and the emitted sourcetype must match it (checked at validation and at run time).
  * Correlation is by shared entities (device names, IP addresses, interfaces) inside the raw events, and by the netspout_* metadata fields that
    every event carries (run id, scenario id, phase, event id, parent event id). The engines stamp events with generation time: phases are ordered,
    not back-dated.
  * Generation is deterministic in structure for a given (contract, run id, seed); timestamps inside raw events are not.
"""
import hashlib
import inspect
import json
import random
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from netspout_core.log_engine import SplunkLogEngine
    from netspout_core.models import LogEntry, Node, NodeType
    from netspout_core import modeled_telemetry
except ImportError:  # pragma: no cover
    try:
        from app.log_engine import SplunkLogEngine
        from app.models import LogEntry, Node, NodeType
        from app import modeled_telemetry
    except ImportError:
        from log_engine import SplunkLogEngine
        from models import LogEntry, Node, NodeType
        import modeled_telemetry

_HERE = Path(__file__).resolve().parent
MAX_EVENTS = 5000


class ContractError(ValueError):
    pass


def _path() -> Path:
    for d in [_HERE / "catalog_data", _HERE.parents[1] / "catalog", _HERE.parent / "catalog"]:
        if (d / "scenario_contracts.json").is_file():
            return d / "scenario_contracts.json"
    raise FileNotFoundError("scenario_contracts.json missing")


def contracts() -> Dict[str, Dict[str, Any]]:
    data = json.loads(_path().read_text())["contracts"]
    return {c["id"]: c for c in data}


def ids() -> List[str]:
    return sorted(contracts())


def get(contract_id: str) -> Dict[str, Any]:
    try:
        return contracts()[contract_id]
    except KeyError:
        raise ContractError("unknown scenario contract: " + contract_id) from None


_CONFIG_LINE = __import__("re").compile(r"^[A-Za-z_][\w.\-]*:\s")


def _is_recorded_event(text: str) -> bool:
    """The sample loader also returns eventgen YAML configuration lines (`randomizeEvents: true`, `replacement: ...`). Those are not telemetry. JSON samples must parse, and an
    HEC envelope (a dict with `event` and `sourcetype` keys) is a delivery wrapper, not a vendor event, so it is not replayed as event text."""
    text = text.strip()
    if text.startswith("{"):
        try:
            doc = json.loads(text)
        except ValueError:
            return False
        return not (isinstance(doc, dict) and {"event", "sourcetype"} <= set(doc))
    return not _CONFIG_LINE.match(text)


def grounded_sample(device: Node, sourcetype: str, vendor_id: str, sample_index: int = 0) -> LogEntry:
    """A verbatim vendor sample for a sourcetype that has recorded samples but no formatter. The raw event is NOT rewritten (so it cannot carry the contract's
    entities); it is tagged with the node it is attributed to, and the contract must not claim entity correlation through it."""
    try:
        from netspout_core.generator_modes import generator_service
    except ImportError:  # pragma: no cover
        from app.generator_modes import generator_service
    samples, _, _ = generator_service.get_grounded_samples(sourcetype, vendor_id=vendor_id)
    samples = [x for x in samples if _is_recorded_event(x)]
    if not samples:
        raise ContractError("no verified sample exists for %s" % sourcetype)
    return LogEntry(timestamp=datetime.now(timezone.utc).isoformat(), device_id=device.name, src_ip=device.ip_address, dest_ip=device.ip_address, protocol="n/a", duration="0ms",
                    action="streamed", signature="GROUNDED_SAMPLE", status="normal", raw_log=samples[int(sample_index) % len(samples)], node_type=device.type.value, node_id=device.id,
                    vendor=vendor_id, sourcetype=sourcetype)


def formatter(name: str):
    """A SplunkLogEngine vendor formatter, the verbatim grounded-sample replay, or the labeled modeled-state generator (modeled_telemetry)."""
    fn = grounded_sample if name == "grounded_sample" else (modeled_telemetry.FORMATTERS.get(name) or getattr(SplunkLogEngine, name, None))
    if not (name.startswith("format_") or name == "grounded_sample") or not callable(fn):
        raise ContractError("formatter %r is not a SplunkLogEngine format_* generator" % name)
    return fn


def fidelity(contract: Dict[str, Any]) -> str:
    """VENDOR_NATIVE (only vendor formatters), MODELED (only the modeled schema) or MIXED. Derived from the streams, never declared."""
    modeled = {s["formatter"] in modeled_telemetry.FORMATTERS for s in contract["streams"]}
    return "MODELED" if modeled == {True} else "VENDOR_NATIVE" if modeled == {False} else "MIXED"


def _node(n: Dict[str, Any]) -> Node:
    try:
        ntype = NodeType[n["type"]]
    except KeyError:
        raise ContractError("node %s has unknown type %r" % (n.get("id"), n.get("type"))) from None
    return Node(id=n["id"], name=n["name"], type=ntype, x=float(n.get("x", 0)), y=float(n.get("y", 0)), ip_address=n["ip"], vendor=n.get("vendor", "generic"))


def _resolve(value: Any, nodes: Dict[str, Dict[str, Any]], round_no: int) -> Any:
    """'@node-id' -> that node's IP, '@node-id.name' -> its name; a list cycles by round, so a phase can walk several entities."""
    if isinstance(value, list):
        return _resolve(value[round_no % len(value)], nodes, round_no)
    if isinstance(value, str) and value.startswith("@"):
        ref, _, attr = value[1:].partition(".")
        if ref not in nodes:
            raise ContractError("parameter references unknown node %r" % ref)
        return nodes[ref]["name"] if attr == "name" else nodes[ref]["ip"]
    return value


def _params(stream: Dict[str, Any], phase_id: str, nodes: Dict[str, Dict[str, Any]], round_no: int) -> Dict[str, Any]:
    merged = dict(stream.get("params", {}))
    merged.update(stream.get("phase_params", {}).get(phase_id, {}))
    return {k: _resolve(v, nodes, round_no) for k, v in merged.items()}


def _active(stream: Dict[str, Any], phase_id: str) -> bool:
    only = stream.get("phases")
    return not only or phase_id in only


def validate(contract: Dict[str, Any]) -> List[str]:
    """Static checks (no events are generated). Returns problems; empty means the contract is well formed."""
    bad: List[str] = []
    for key in ("id", "title", "description", "nodes", "phases", "streams"):
        if not contract.get(key):
            bad.append("missing " + key)
    if bad:
        return bad
    nodes = {n["id"]: n for n in contract["nodes"]}
    if len(nodes) != len(contract["nodes"]):
        bad.append("duplicate node id")
    for n in contract["nodes"]:
        try:
            _node(n)
        except (ContractError, KeyError) as exc:
            bad.append(str(exc))
    phases = [p["id"] for p in contract["phases"]]
    if len(set(phases)) != len(phases):
        bad.append("duplicate phase id")
    sids = [s["id"] for s in contract["streams"]]
    if len(set(sids)) != len(sids):
        bad.append("duplicate stream id")
    for s in contract["streams"]:
        tag = "stream " + s.get("id", "?")
        if s.get("node") not in nodes:
            bad.append(tag + ": unknown node " + str(s.get("node")))
        if not s.get("sourcetype"):
            bad.append(tag + ": sourcetype not declared")
        try:
            fn = formatter(s["formatter"])
        except (ContractError, KeyError) as exc:
            bad.append(tag + ": " + str(exc))
            continue
        for p in (s.get("phases") or []):
            if p not in phases:
                bad.append(tag + ": unknown phase " + p)
        sig = inspect.signature(fn)
        for ph in phases:
            if not _active(s, ph):
                continue
            try:
                args = _params(s, ph, nodes, 0)
                sig.bind(device=None, **args)
            except (TypeError, ContractError) as exc:
                bad.append("%s phase %s: %s" % (tag, ph, exc))
    return bad


def _seed(contract_id: str, run_id: str, seed: Optional[int]) -> int:
    return int(hashlib.sha256(("%s|%s|%s" % (contract_id, run_id, seed)).encode()).hexdigest()[:12], 16)


def generate(contract_id: str, run_id: Optional[str] = None, seed: Optional[int] = None, scale: float = 1.0) -> List[LogEntry]:
    """The ordered LogEntry list for one run. Every event is tagged with run, scenario, phase and causal parent."""
    c = get(contract_id)
    problems = validate(c)
    if problems:
        raise ContractError("contract %s is invalid: %s" % (contract_id, "; ".join(problems)))
    run_id = run_id or "pf-contract-" + uuid.uuid4().hex[:12]
    nodes = {n["id"]: n for n in c["nodes"]}
    built = {i: _node(n) for i, n in nodes.items()}
    state = random.getstate()
    random.seed(_seed(contract_id, run_id, seed))
    out: List[LogEntry] = []
    try:
        prev = None
        for phase in c["phases"]:
            rounds = max(1, int(round(phase.get("rounds", 1) * scale)))
            for r in range(rounds):
                for s in c["streams"]:
                    if not _active(s, phase["id"]):
                        continue
                    count = int(s.get("phase_per_round", {}).get(phase["id"], s.get("per_round", 1)))   # a stream can run hotter in one phase (a spike)
                    for k in range(count):
                        entry = formatter(s["formatter"])(device=built[s["node"]], **_params(s, phase["id"], nodes, r * count + k))
                        if entry.sourcetype != s["sourcetype"]:
                            raise ContractError("stream %s declares %s but the formatter emitted %s" % (s["id"], s["sourcetype"], entry.sourcetype))
                        eid = "%s-%s-%d" % (contract_id, phase["id"], len(out) + 1)
                        entry.netspout_run_id, entry.netspout_scenario_id, entry.netspout_phase = run_id, contract_id, phase["id"]
                        entry.netspout_event_id, entry.netspout_parent_event_id = eid, prev
                        entry.netspout_device_id = built[s["node"]].name
                        entry.netspout_ground_truth = "synthetic_observation"
                        prev = eid
                        out.append(entry)
                        if len(out) > MAX_EVENTS:
                            raise ContractError("contract would emit more than %d events" % MAX_EVENTS)
    finally:
        random.setstate(state)
    return out


def sourcetypes(contract: Dict[str, Any]) -> List[str]:
    return sorted({s["sourcetype"] for s in contract["streams"]})


def preview(contract_id: str, sample: int = 1) -> Dict[str, Any]:
    """Phases, streams, expected counts and the first raw event per stream; nothing is sent."""
    c = get(contract_id)
    events = generate(contract_id, run_id="preview", scale=1.0)
    per_stream: Dict[str, List[str]] = {}
    for e in events:
        per_stream.setdefault(e.sourcetype, []).append(e.raw_log)
    counts = {p["id"]: sum(1 for e in events if e.netspout_phase == p["id"]) for p in c["phases"]}
    return {"scenario_id": contract_id, "title": c["title"], "description": c["description"], "assumptions": c.get("assumptions", []),
            "phases": [{"id": p["id"], "label": p.get("label", p["id"]), "events": counts[p["id"]]} for p in c["phases"]], "total_events": len(events),
            "nodes": [{"id": n["id"], "name": n["name"], "type": n["type"], "ip": n["ip"]} for n in c["nodes"]], "sourcetypes": sourcetypes(c),
            "sample": {st: raws[:sample] for st, raws in per_stream.items()}}


def catalog() -> List[Dict[str, Any]]:
    """Registry rows for the Explorer, dashboards and documentation."""
    rows = []
    for cid, c in sorted(contracts().items()):
        rows.append({"scenario_id": cid, "title": c["title"], "description": c["description"], "category": c.get("category", ""), "vendors": c.get("vendors", []),
                     "sourcetypes": sourcetypes(c), "phases": [p["id"] for p in c["phases"]], "nodes": len(c["nodes"]), "generator_family": c.get("generator_family", "scenario_contract"),
                     "assumptions": c.get("assumptions", []), "kind": c.get("kind", "operational"), "fidelity": fidelity(c), "source": c.get("source", "authored")})
    return rows
