# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/delivery_monitor.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""Live event delivery monitor: one snapshot schema for every kind of run.

Kinds: replay sessions (ReplaySession), monitored batches (native packs, incident packs, single-sourcetype generation) and synchronous runs whose engine only reports at
the end (ScenarioRunner, unified generation). Every number comes from a real counter incremented where the event is delivered:

  generated     events built and ready (batches build everything first; replay counts produced events)
  attempts      events handed to the transport (delivered or not)
  accepted      the transport's own acknowledgement (HEC success body, code 0); this is NOT proof of indexing
  rejected      the transport refused the event or the send failed
  unknown       the answer could not be read; the event is never re-sent
  pending       generated - attempts
  indexed       found by an independent Splunk search for this run (None until a verification has been run)

Nothing is ever reset or invented: after an engine restart a run that was active is reported INTERRUPTED with the counters it last persisted.
"""
import contextvars
import json
import threading
import time
import uuid
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

ACTIVE = ("CREATED", "RUNNING", "PAUSED", "STOPPING")
FINAL = ("COMPLETED", "STOPPED", "FAILED", "INTERRUPTED")
RECENT_ERRORS = 20
_SECRET_HINTS = ("token", "authorization", "password", "secret")


def _now():
    return datetime.now(timezone.utc)


def clean_error(text) -> str:
    """Error text for display: bounded, single line, never containing credential-looking assignments."""
    t = " ".join(str(text or "").split())[:240]
    return "error text withheld (credential-like content)" if any(h in t.lower() for h in _SECRET_HINTS) and "=" in t else t


class Item:
    __slots__ = ("sourcetype", "phase", "send", "datapoints")

    def __init__(self, sourcetype: str, phase: Optional[str], send: Callable[[], tuple], datapoints: int = 0):
        self.sourcetype, self.phase, self.send, self.datapoints = sourcetype, phase, send, datapoints   # datapoints > 0 marks a metric event


def _rate_series(samples, window=120):
    """Per-second delivery rate from cumulative (t, attempts) samples over the last `window` seconds."""
    if len(samples) < 2:
        return []
    end = samples[-1][0]
    buckets = Counter()
    for (t0, c0), (t1, c1) in zip(samples, samples[1:]):
        if end - t1 <= window:
            buckets[int(t1)] += c1 - c0
    return [{"t": datetime.fromtimestamp(t, timezone.utc).isoformat(), "eps": n} for t, n in sorted(buckets.items())]


def _current_eps(samples, horizon=5.0):
    if len(samples) < 2:
        return 0.0
    t_end, c_end = samples[-1]
    start = next(((t, c) for t, c in samples if t_end - t <= horizon), samples[0])
    return round((c_end - start[1]) / max(t_end - start[0], 1e-6), 2) if t_end > start[0] else 0.0


class DeliveryRun:
    """A monitored, finite batch delivered one event at a time with exact accounting; supports pause, resume and stop."""

    def __init__(self, kind: str, target: str, title: str, destination: str, index: str, items: List[Item], eps_limit: Optional[float] = None,
                 key_field: str = "netspout_run_id", run_id: Optional[str] = None, links: Optional[dict] = None, metric_index: Optional[str] = None):
        self.id = run_id or "run-" + uuid.uuid4().hex[:12]
        self.kind, self.target, self.title, self.destination, self.index, self.metric_index = kind, target, title, destination, index, metric_index
        self.items, self.eps, self.key_field, self.links = items, eps_limit, key_field, links or {}
        self.counts = dict(generated=len(items), attempts=0, accepted=0, rejected=0, unknown=0)
        self.by_st: Dict[str, Counter] = {}
        self.by_phase: Dict[str, Counter] = {}
        for it in items:
            self.by_st.setdefault(it.sourcetype, Counter())["total"] += 1
            if it.phase:
                self.by_phase.setdefault(it.phase, Counter())["total"] += 1
        self.metric = {"events": 0, "datapoints": 0}   # accepted metric events and the datapoints they carry (an mstats search counts datapoints, not events)
        self.errors = deque(maxlen=RECENT_ERRORS)
        self.samples = deque(maxlen=2000)
        self.state, self.started, self.ended, self.error = "CREATED", None, None, None
        self.indexed = None
        self.verification = {"status": "NOT_RUN"}
        self._lock, self._cancel, self._run = threading.Lock(), threading.Event(), threading.Event()
        self._run.set()
        self._paused_total, self._paused_at, self._thread, self._persist = 0.0, None, None, None

    # control -----------------------------------------------------------------------------------------------------------
    def start(self, persist=None):
        self._persist = persist
        self.state, self.started = "RUNNING", _now()
        self._t0 = time.monotonic()
        self.samples.append((time.time(), 0))
        self._thread = threading.Thread(target=self._work, daemon=True)
        self._thread.start()
        return self

    def pause(self):
        with self._lock:
            if self.state != "RUNNING":
                raise ValueError("only a running run can be paused")
            self.state, self._paused_at = "PAUSED", time.monotonic()
            self._run.clear()

    def resume(self):
        with self._lock:
            if self.state != "PAUSED":
                raise ValueError("only a paused run can be resumed")
            self._paused_total += time.monotonic() - self._paused_at
            self.state, self._paused_at = "RUNNING", None
            self._run.set()

    def stop(self, timeout=10):
        with self._lock:
            if self.state in FINAL:
                return
            self.state = "STOPPING"
        self._cancel.set()
        self._run.set()
        if self._thread:
            self._thread.join(timeout)

    def wait(self, timeout=None):
        if self._thread:
            self._thread.join(timeout)
        return self.state

    # worker ------------------------------------------------------------------------------------------------------------
    def _work(self):
        gap = 1.0 / self.eps if self.eps else 0.0
        nxt = time.monotonic()
        try:
            for it in self.items:
                while not self._run.is_set() and not self._cancel.is_set():
                    self._run.wait(0.05)
                if self._cancel.is_set():
                    break
                if gap:
                    wait = nxt - time.monotonic()
                    if wait > 0 and self._cancel.wait(wait):
                        break
                    nxt = max(nxt, time.monotonic()) + gap
                try:
                    state, err = it.send()
                except Exception as exc:   # a sender fault is a rejected event with a visible reason, never a silent loss
                    state, err = "rejected", "%s" % type(exc).__name__
                self._account(it.sourcetype, it.phase, state, err, it.datapoints)
                if self._persist and self.counts["attempts"] % 25 == 0:
                    self._persist()
        except Exception as exc:
            self.error = "worker: %s" % type(exc).__name__
            self.state = "FAILED"
        finally:
            with self._lock:
                self.samples.append((time.time(), self.counts["attempts"]))
                if self.state != "FAILED":
                    self.state = "STOPPED" if self._cancel.is_set() and self.counts["attempts"] < self.counts["generated"] else "COMPLETED"
                self.ended = _now()
            if self._persist:
                self._persist()

    def _account(self, sourcetype, phase, state, err, datapoints=0):
        with self._lock:
            self.counts["attempts"] += 1
            key = state if state in ("accepted", "rejected") else "unknown"
            self.counts[key] += 1
            if key == "accepted" and datapoints:
                self.metric["events"] += 1
                self.metric["datapoints"] += datapoints
            self.by_st.setdefault(sourcetype, Counter())[key] += 1
            if phase:
                self.by_phase.setdefault(phase, Counter())[key] += 1
            if key != "accepted":
                self.errors.append({"at": _now().isoformat(), "sourcetype": sourcetype, "outcome": key, "message": clean_error(err)})
            now = time.time()
            if not self.samples or now - self.samples[-1][0] >= 0.5:
                self.samples.append((now, self.counts["attempts"]))

    # view --------------------------------------------------------------------------------------------------------------
    def snapshot(self) -> dict:
        with self._lock:
            c = dict(self.counts)
            elapsed = ((self.ended or _now()) - self.started).total_seconds() - self._paused_total - (time.monotonic() - self._paused_at if self._paused_at else 0) if self.started else 0.0
            elapsed = max(elapsed, 0.0)
            avg = round(c["attempts"] / elapsed, 2) if elapsed > 0 else 0.0
            remaining = c["generated"] - c["attempts"]
            cur = _current_eps(list(self.samples)) if self.state == "RUNNING" else 0.0
            return {
                "run_id": self.id, "kind": self.kind, "target": self.target, "title": self.title, "state": self.state, "error": self.error,
                "destination": {"name": self.destination, "index": self.index, "metric_index": self.metric_index}, "mode": "finite",
                "started_at": self.started.isoformat() if self.started else None, "ended_at": self.ended.isoformat() if self.ended else None, "elapsed_s": round(elapsed, 1),
                "progress": {"total": c["generated"], "done": c["attempts"], "pct": round(100.0 * c["attempts"] / c["generated"], 1) if c["generated"] else 0.0},
                "counters": {"generated": c["generated"], "attempts": c["attempts"], "accepted": c["accepted"], "rejected": c["rejected"], "unknown": c["unknown"], "pending": remaining, "indexed": self.indexed},
                "rate": {"current_eps": cur, "average_eps": avg, "limit_eps": self.eps},
                "eta_s": round(remaining / cur, 1) if self.state == "RUNNING" and cur > 0 and remaining > 0 else (0 if remaining == 0 else None),
                "by_sourcetype": {k: dict(v) for k, v in self.by_st.items()}, "by_phase": [{"phase": k, **dict(v)} for k, v in self.by_phase.items()],
                "throughput": _rate_series(list(self.samples)), "recent_errors": list(self.errors)[-RECENT_ERRORS:],
                "controls": {"pause": self.state == "RUNNING", "resume": self.state == "PAUSED", "stop": self.state in ("RUNNING", "PAUSED")},
                "verification": self.verification, "links": self.links, "key_field": self.key_field, "metric_accepted": dict(self.metric),
                "accounting_note": "accepted is the transport acknowledgement, not proof of indexing; indexed comes only from an independent Splunk search",
            }

    def persisted(self) -> dict:
        return self.snapshot()


_observer = contextvars.ContextVar("pf_delivery_observer", default=None)


def observe_dispatch(sourcetype, phase, result):
    """Called by the dispatcher after every delivery attempt; a no-op unless an ObservedRun is active in this context."""
    obs = _observer.get()
    if obs is not None:
        obs.record(sourcetype, phase, result)


class ObservedRun(DeliveryRun):
    """A synchronous runner (ScenarioRunner, unified generation) instrumented at the delivery boundary. Counters come only from real dispatch results.
    The runner owns the loop, so pause, resume and stop are reported as unsupported and a total is shown only when the runner declares one."""

    def __init__(self, kind, target, title, destination, index, expected: Optional[int] = None, **kw):
        super().__init__(kind, target, title, destination, index, [], **kw)
        self.expected = expected
        self.counts["generated"] = 0

    def start(self, persist=None):
        self._persist = persist
        self.state, self.started = "RUNNING", _now()
        self._t0 = time.monotonic()
        self.samples.append((time.time(), 0))
        return self

    def record(self, sourcetype, phase, result):
        h = (result or {}).get("hec")
        with self._lock:
            self.counts["generated"] += 1
            self.by_st.setdefault(sourcetype, Counter())["total"] += 1
            if phase:
                self.by_phase.setdefault(phase, Counter())["total"] += 1
        if not isinstance(h, dict):
            with self._lock:
                self.errors.append({"at": _now().isoformat(), "sourcetype": sourcetype, "outcome": "not_attempted", "message": "no HEC delivery was attempted for this event"})
            return
        st = str(h.get("state") or "").upper()
        if st:
            key = {"ACCEPTED": "accepted", "FAILED": "rejected"}.get(st, "unknown")
        else:
            key = "accepted" if h.get("success") else ("rejected" if h.get("success") is False else "unknown")
        self._account(sourcetype, phase, key, None if key == "accepted" else (h.get("message") or h.get("error_class") or "not accepted"))

    def finish(self, error=None):
        with self._lock:
            self.samples.append((time.time(), self.counts["attempts"]))
            self.error = clean_error(error) if error else None
            self.state = "FAILED" if error else "COMPLETED"
            self.ended = _now()
        if self._persist:
            self._persist()

    def snapshot(self) -> dict:
        snap = super().snapshot()
        c = snap["counters"]
        total = self.expected if self.state == "RUNNING" else c["generated"]
        snap["mode"] = "observed"
        snap["progress"] = {"total": total, "done": c["attempts"], "pct": round(100.0 * c["attempts"] / total, 1) if total else (None if self.state == "RUNNING" else 0.0)}
        snap["controls"] = {"pause": False, "resume": False, "stop": False}
        snap["controls_note"] = "This runner executes synchronously inside the engine; pause, resume and stop are not supported. Counters are read at the delivery boundary."
        snap["eta_s"] = None
        return snap


_service: Optional["RunMonitorService"] = None


def set_service(service):
    global _service
    _service = service


def observed_id() -> Optional[str]:
    obs = _observer.get()
    return obs.id if obs is not None else None


def observed_run(kind: str, target: str, run_id: str, transport, expected: Optional[int] = None):
    """Instrument a synchronous runner. A no-op when no monitor service is registered or this context is already observed (nested runners count once)."""
    import contextlib
    from urllib.parse import urlparse
    if _service is None or _observer.get() is not None:
        return contextlib.nullcontext()
    host = urlparse(getattr(transport, "hec_url", "") or "").netloc or "no HEC destination"
    return _service.observe(ObservedRun(kind, target, target, host, getattr(transport, "hec_index", None) or "", expected, run_id=run_id))


def replay_snapshot(session, destination: str, links: Optional[dict] = None, verification: Optional[dict] = None) -> dict:
    """The same schema for a ReplaySession, from its real counters (generated = produced, attempts = delivered)."""
    c = dict(session.counts)
    now = time.time()
    started = session.started_at
    ended = session.ended_at
    elapsed = ((ended or _now()) - started).total_seconds() if started else 0.0
    samples = list(session.samples)
    cur = _current_eps(samples) if session.state == "RUNNING" else 0.0
    total = session.total_expected
    finite = total is not None
    attempts = c["delivered"]
    verification = verification or {"status": "NOT_RUN"}
    return {
        "run_id": session.id, "kind": "replay", "target": session.source, "title": session.title if hasattr(session, "title") else session.source, "state": session.state, "error": session.error,
        "destination": {"name": destination, "index": session.index, "host": session.host}, "mode": "finite" if finite else "continuous",
        "started_at": started.isoformat() if started else None, "ended_at": ended.isoformat() if ended else None, "elapsed_s": round(elapsed, 1),
        "progress": ({"total": total, "done": attempts, "pct": round(100.0 * attempts / total, 1) if total else 0.0} if finite else {"total": None, "done": attempts, "pct": None}),
        "counters": {"generated": c["generated"], "attempts": attempts, "accepted": c["accepted"], "rejected": c["rejected"], "unknown": c["unknown"],
                     "pending": c["generated"] - attempts, "indexed": verification.get("indexed")},
        "rate": {"current_eps": cur, "average_eps": round(attempts / elapsed, 2) if elapsed > 0 else 0.0, "limit_eps": session.eps},
        "eta_s": round((total - attempts) / cur, 1) if finite and cur > 0 and total > attempts and session.state == "RUNNING" else None,
        "by_sourcetype": {k: dict(v) for k, v in session.by_sourcetype.items()}, "by_phase": [{"phase": k, **dict(v)} for k, v in session.by_phase.items()],
        "throughput": _rate_series(samples), "recent_errors": list(session.errors), "queue_depth": session._q.qsize(), "backpressure_waits": c["backpressure_waits"],
        "discarded_on_stop": c["discarded_on_stop"],
        "controls": {"pause": session.state == "RUNNING", "resume": session.state == "PAUSED", "stop": session.state in ("RUNNING", "PAUSED")},
        "verification": verification, "links": links or {}, "key_field": "netspout_replay_session",
        "accounting_note": "accepted is the transport acknowledgement, not proof of indexing; indexed comes only from an independent Splunk search",
    }


class RunMonitorService:
    """Registry of monitored batches with restart-safe persistence (summaries only; an active run found after a restart becomes INTERRUPTED)."""

    def __init__(self, state_file: Optional[Path] = None):
        self._runs: Dict[str, DeliveryRun] = {}
        self._history: Dict[str, dict] = {}
        self._state = Path(state_file) if state_file else None
        self._lock = threading.Lock()
        if self._state and self._state.is_file():
            try:
                for rid, s in json.loads(self._state.read_text()).items():
                    if s.get("state") in ACTIVE:
                        s["state"] = "INTERRUPTED"
                        s["controls"] = {"pause": False, "resume": False, "stop": False}
                        s["interrupted_note"] = "the engine restarted while this run was active; counters are the last persisted values and the run is not resumed"
                    self._history[rid] = s
            except (OSError, ValueError):
                pass

    def _save(self):
        if self._state:
            with self._lock:
                data = dict(self._history)
                data.update({rid: r.snapshot() for rid, r in self._runs.items()})
                self._state.parent.mkdir(parents=True, exist_ok=True)
                tmp = self._state.with_suffix(".tmp")
                tmp.write_text(json.dumps(data))
                tmp.replace(self._state)

    def start(self, run: DeliveryRun, max_active=4) -> DeliveryRun:
        if sum(1 for r in self._runs.values() if r.state in ACTIVE) >= max_active:
            raise ValueError("too many active runs (limit %d)" % max_active)
        self._runs[run.id] = run
        run.start(persist=self._save)
        self._save()
        return run

    def observe(self, run: ObservedRun):
        """Context manager: register an ObservedRun and attribute every dispatch in this context to it."""
        svc = self

        class _Ctx:
            def __enter__(self_):
                svc._runs[run.id] = run
                run.start(persist=svc._save)
                self_.token = _observer.set(run)
                svc._save()
                return run

            def __exit__(self_, exc_type, exc, tb):
                _observer.reset(self_.token)
                run.finish(exc_type.__name__ + ": " + str(exc) if exc_type else None)
                svc._save()
                return False
        return _Ctx()

    def run_in_background(self, run: ObservedRun, fn: Callable[[], object], max_active=4) -> ObservedRun:
        """Register the run, then execute the synchronous runner on a worker thread so the caller can poll it. Counters still come only from the dispatch boundary."""
        if sum(1 for r in self._runs.values() if r.state in ACTIVE) >= max_active:
            raise ValueError("too many active runs (limit %d)" % max_active)
        self._runs[run.id] = run
        run.start(persist=self._save)
        self._save()

        def work():
            token = _observer.set(run)
            try:
                fn()
                err = None
            except Exception as exc:
                err = "%s: %s" % (type(exc).__name__, exc)
            finally:
                _observer.reset(token)
            run.finish(err)
            self._save()
        threading.Thread(target=work, daemon=True).start()
        return run

    def get(self, rid: str) -> Optional[DeliveryRun]:
        return self._runs.get(rid)

    def history(self, rid: str) -> Optional[dict]:
        return self._history.get(rid)

    def snapshot(self, rid: str) -> Optional[dict]:
        if rid in self._runs:
            return self._runs[rid].snapshot()
        return self._history.get(rid)

    def list(self) -> List[dict]:
        rows = dict(self._history)
        rows.update({rid: r.snapshot() for rid, r in self._runs.items()})
        return sorted(rows.values(), key=lambda s: s.get("started_at") or "", reverse=True)

    def control(self, rid: str, action: str) -> dict:
        r = self._runs.get(rid)
        if not r:
            raise KeyError(rid)
        {"pause": r.pause, "resume": r.resume, "stop": r.stop}[action]()
        self._save()
        return r.snapshot()
