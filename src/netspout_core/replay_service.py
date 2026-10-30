"""Replay session registry for the backend: sources, creation limits, lifecycle, restart safety and independent verification.

Destination authorization is NOT decided here: the caller passes a sink built from the authorized Connection Center destination.
Sessions live in memory; their summaries are persisted (when a state file is given) so that after a process restart a session that was
RUNNING or PAUSED is reported INTERRUPTED and is never resumed or re-sent automatically.
"""
import json
import re
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, Optional

from netspout_core.sample_replay import (DEFAULT_HOST, DEFAULT_INDEX, FORMATS, ReplayError, ReplaySession, TimestampRule, build_timeline,
                                         preview as preview_timeline)

MAX_SESSIONS = 4
MAX_UPLOAD_BYTES = 2_000_000
LIMITS = {"speed": (0.01, 1000.0), "eps_limit": (0.1, 2000.0), "queue_size": (1, 10000), "loops": (1, 1_000_000)}
HOST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
SOURCE_RE = re.compile(r"^[A-Za-z0-9:_.-]{1,160}$")
_HERE = Path(__file__).resolve().parent


def _registry_path():
    for d in [_HERE / "catalog_data", _HERE.parents[1] / "catalog", _HERE.parent / "catalog"]:
        if (d / "replay_sources.json").is_file():
            return d / "replay_sources.json"
    raise FileNotFoundError("replay_sources.json missing")


def _root():
    p = _registry_path().resolve()
    return p.parents[1] if p.parent.name == "catalog" else None


def sources():
    return json.loads(_registry_path().read_text())["sources"]


def source_text(src) -> str:
    """Registry sample text. Vendored samples are read from the repository checkout (catalog/raw_reference); packaged copies lack them."""
    for base in [_root(), _HERE.parents[1], _HERE.parents[2]]:
        if base and (base / src["file"]).is_file():
            text = (base / src["file"]).read_bytes().decode("utf-8")
            break
    else:
        raise ReplayError("sample file not available in this deployment: " + src["file"])
    if src.get("drop_last_record"):
        text = text[:text.rstrip("\n").rfind("\n")]
    return text


def _bounded(name, value, default):
    if value is None:
        return default
    lo, hi = LIMITS[name]
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not lo <= value <= hi:
        raise ReplayError("%s must be between %s and %s" % (name, lo, hi))
    return value


def resolve(params: Dict):
    """-> (text, format, rule, sourcetype, label, record_start) from a registry id or an uploaded sample with an explicit rule."""
    if params.get("source_id"):
        src = next((s for s in sources() if s["id"] == params["source_id"]), None)
        if not src:
            raise ReplayError("unknown replay source")
        return (source_text(src), src["format"], TimestampRule(**src["timestamp_rule"]), src.get("sourcetype") or params.get("sourcetype"),
                src["id"], src.get("record_start"))
    text = params.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ReplayError("provide source_id or sample text")
    if len(text.encode("utf-8")) > MAX_UPLOAD_BYTES:
        raise ReplayError("sample exceeds %d bytes" % MAX_UPLOAD_BYTES)
    if params.get("format") not in FORMATS:
        raise ReplayError("format must be one of " + ", ".join(FORMATS))
    rule = params.get("timestamp_rule")
    rule = TimestampRule(**rule) if rule else None
    if not params.get("sourcetype"):
        raise ReplayError("sourcetype is required for an uploaded sample")
    return text, params["format"], rule, params["sourcetype"], "upload", params.get("record_start")


def _timeline(params, text, fmt, rule, record_start):
    fixed = params.get("fixed_interval_s")
    return build_timeline(text, fmt, rule, on_bad_record=params.get("on_bad_record", "fail"), loop_gap_s=params.get("loop_gap_s"),
                          fixed_interval_s=fixed, record_start=record_start, max_gap_s=params.get('max_gap_s'))


def preview(params: Dict):
    text, fmt, rule, _, _, rs = resolve(params)
    out = preview_timeline(text, fmt, rule, count=int(min(max(params.get("count", 5), 1), 20)), speed=_bounded("speed", params.get("speed"), 1.0),
                           on_bad_record=params.get("on_bad_record", "fail"), loop_gap_s=params.get("loop_gap_s"),
                           fixed_interval_s=params.get("fixed_interval_s"), record_start=rs, max_gap_s=params.get("max_gap_s"))
    out["sourcetype"] = resolve(params)[3]
    return out


class ReplayService:
    def __init__(self, state_file: Optional[Path] = None):
        self._sessions: Dict[str, ReplaySession] = {}
        self._lock = threading.Lock()
        self._state = Path(state_file) if state_file else None
        self._history: Dict[str, Dict] = {}
        self._recover()

    # persistence / restart safety --------------------------------------------------------------------------------------
    def _recover(self):
        if not self._state or not self._state.is_file():
            return
        try:
            data = json.loads(self._state.read_text())
        except (OSError, ValueError):
            return
        for sid, s in data.items():
            if s.get("state") in ("RUNNING", "PAUSED", "CREATED", "STOPPING"):
                s["state"] = "INTERRUPTED"
                s["note"] = "process restarted while the session was active; it is NOT resumed and nothing is re-sent"
            self._history[sid] = s
        self._save()

    def _save(self):
        if self._state:
            snap = dict(self._history)
            snap.update({sid: s.status() for sid, s in self._sessions.items()})
            self._state.parent.mkdir(parents=True, exist_ok=True)
            self._state.write_text(json.dumps(snap, indent=1))

    # lifecycle ------------------------------------------------------------------------------------------------------------
    def create(self, params: Dict, sink_factory: Callable[[str, str, str, str], object], *, index=DEFAULT_INDEX, host=DEFAULT_HOST) -> ReplaySession:
        if not HOST_RE.match(host):
            raise ReplayError("invalid host")
        text, fmt, rule, sourcetype, label, rs = resolve(params)
        if not sourcetype:
            raise ReplayError("sourcetype is required: this source has none recorded")
        tl = _timeline(params, text, fmt, rule, rs)
        loops = params.get("loops")
        if params.get("continuous"):
            loops = None
        elif loops is None:
            loops = 1
        loops = _bounded("loops", loops, None) if loops is not None else None
        with self._lock:
            if sum(1 for s in self._sessions.values() if s.state in ("RUNNING", "PAUSED", "CREATED", "STOPPING")) >= MAX_SESSIONS:
                raise ReplayError("too many active replay sessions (limit %d)" % MAX_SESSIONS)
            session = ReplaySession(tl, None, source_label=label, sourcetype=sourcetype, index=index, host=host,
                                    speed=_bounded("speed", params.get("speed"), 1.0), eps_limit=_bounded("eps_limit", params.get("eps_limit"), None),
                                    loops=loops, queue_size=_bounded("queue_size", params.get("queue_size"), 1000))
            if not SOURCE_RE.match(session.source):
                raise ReplayError("invalid source label")
            session.sink = sink_factory(session.source, sourcetype, index, host)
            self._sessions[session.id] = session
        session.start()
        self._save()
        return session

    def get(self, sid: str) -> ReplaySession:
        s = self._sessions.get(sid)
        if not s:
            raise KeyError(sid)
        return s

    def status(self, sid: str) -> Dict:
        if sid in self._sessions:
            return self._sessions[sid].status()
        if sid in self._history:
            return self._history[sid]
        raise KeyError(sid)

    def list(self):
        rows = {sid: s for sid, s in self._history.items()}
        rows.update({sid: s.status() for sid, s in self._sessions.items()})
        return list(rows.values())

    def control(self, sid: str, action: str) -> Dict:
        s = self.get(sid)
        {"pause": s.pause, "resume": s.resume, "stop": s.stop}[action]()
        self._save()
        return s.status()

    def stop_all(self):
        for s in list(self._sessions.values()):
            s.stop()

    # independent verification -----------------------------------------------------------------------------------------------
    def verify(self, sid: str, search: Callable[[str], tuple]) -> Dict:
        """Counts what Splunk actually holds for this session's unique `source`, through an independent search (never from sender counters)."""
        s = self.get(sid)
        query = ('search index="%s" source="%s" earliest=-30d latest=+1d | stats count as indexed, min(_time) as first_time, max(_time) as last_time'
                 % (s.index, s.source))
        rows, error = search(query)
        if error:
            return {"session_id": sid, "verified": False, "error": error}
        row = rows[0] if rows else {}
        indexed = int(float(row.get("indexed", 0) or 0))
        counts = s.counts
        return {"session_id": sid, "verified": True, "indexed": indexed, "accepted": counts["accepted"], "delivered": counts["delivered"],
                "complete": s.state in ("COMPLETED", "STOPPED") and indexed == counts["accepted"],
                "first_time": row.get("first_time"), "last_time": row.get("last_time"), "query": query,
                "note": "indexed is read from Splunk for source=%s; it can trail accepted until indexing catches up" % s.source}
