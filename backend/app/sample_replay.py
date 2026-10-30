# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/sample_replay.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""Continuous historical sample replay.

Authentic recorded events are re-emitted on the current clock. Only the bytes of the explicitly selected timestamp field change; every other
byte of every record is emitted exactly as recorded. Chronological spacing between source events is preserved (divided by `speed`).

Timeline rules
  * offsets are source timestamps minus the first source timestamp; a source record that is OLDER than its predecessor is clamped to the
    predecessor's offset (counted in `out_of_order`), so the emitted timeline never goes backwards.
  * loop gap: loop k+1 starts `loop_gap_s` after the last event of loop k (default: the median positive source spacing, at least 1 ms; 1 s when the
    source has no spacing). Loop-boundary timestamps therefore never overlap or regress.
  * a source with no timestamp rule is REFUSED unless the caller explicitly selects `fixed_interval` (then records are emitted unmodified, with no
    rewritten timestamp, and the chronology is labelled USER_SPECIFIED_INTERVAL). No chronology is invented silently.
  * pause freezes the virtual clock and holds delivery: events already queued keep their schedule stamps and are delivered after resume.
  * emitted timestamp = session start + scheduled offset / speed (+ paused time); EPS throttling or backpressure can delay *delivery* but never
    reorders events or rewrites the stamp.
Limits: syslog timestamps carry no year (assumed `assume_year`, a leap year by default) and a source spanning a year boundary is not unwrapped.
"""
import csv
import io
import json
import queue
import re
import statistics
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterator, List, Optional
from zoneinfo import ZoneInfo

FORMATS = ("syslog", "csv", "json", "jsonl", "apache", "windows_xml", "text")
DEFAULT_INDEX = "dev_test_replay"
DEFAULT_HOST = "replayed-log-generator"
_MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
_SYSLOG = re.compile(r"([A-Z][a-z]{2})( +)(\d{1,2}) (\d\d):(\d\d):(\d\d)")
_ISO = re.compile(r"^(\d{4})-(\d\d)-(\d\d)([T ])(\d\d):(\d\d):(\d\d)(?:[.,](\d{1,9}))?\s*(Z|[+-]\d\d:?\d\d)?$")
_MAX_RECORDS = 200_000


class ReplayError(ValueError):
    pass


@dataclass
class TimestampRule:
    """kind: regex (locator = pattern with ONE capture group), json_path (dotted path, e.g. "id.time"), csv_column (header name).
    fmt: iso8601 | epoch_s | epoch_ms | epoch_us | syslog3164 | any strptime format. tz applies only when the text carries no offset."""
    kind: str
    locator: str
    fmt: str
    tz: str = "UTC"
    assume_year: int = 2000

    def __post_init__(self):
        if self.kind not in ("regex", "json_path", "csv_column"):
            raise ReplayError("unknown timestamp rule kind")
        ZoneInfo(self.tz)


# ------------------------------------------------------------------------------------------------------------------ record splitting
def _csv_rows(lines: List[str]):
    rows, buf = [], ""
    for line in lines:
        buf = line if not buf else buf + "\n" + line
        if buf.count('"') % 2 == 0:
            if buf.strip():
                rows.append(buf)
            buf = ""
    if buf:
        raise ReplayError("CSV ends inside a quoted field")
    return rows


def split_records(text: str, fmt: str, record_start: Optional[str] = None):
    """-> (records, header). Each record is the exact recorded text (no trailing newline). A truncated final record is refused, never repaired."""
    if fmt not in FORMATS:
        raise ReplayError("unsupported format: " + fmt)
    header = None
    if fmt in ("syslog", "apache", "text"):
        records = [l for l in text.splitlines() if l.strip()]
        if record_start:  # multiline records: a line that does not start a record continues the previous one, byte for byte
            start, joined = re.compile(record_start), []
            for line in text.splitlines():
                if not line.strip() and not joined:
                    continue
                if start.search(line) or not joined:
                    joined.append(line)
                else:
                    joined[-1] += "\n" + line
            records = [r.rstrip("\n") for r in joined if r.strip()]
    elif fmt == "jsonl":
        records = [l for l in text.splitlines() if l.strip()]
        for n, l in enumerate(records, 1):
            try:
                json.loads(l)
            except ValueError as exc:
                raise ReplayError("JSON Lines record %d is not valid JSON" % n) from exc
    elif fmt == "csv":
        rows = _csv_rows(text.splitlines())
        if len(rows) < 2:
            raise ReplayError("CSV needs a header and at least one row")
        header, records = next(csv.reader([rows[0]])), rows[1:]
    elif fmt == "windows_xml":
        records = re.findall(r"<Event\b.*?</Event>", text, re.S)
        if not records:
            raise ReplayError("no complete <Event> records")
    else:  # json: a top-level array (each element kept byte-exact) or a single object
        dec, i, n = json.JSONDecoder(), 0, len(text)
        while i < n and text[i].isspace():
            i += 1
        try:
            if text[i] == "[":
                records, i = [], i + 1
                while True:
                    while text[i].isspace() or text[i] == ",":
                        i += 1
                    if text[i] == "]":
                        break
                    _, end = dec.raw_decode(text, i)
                    records.append(text[i:end])
                    i = end
            else:
                _, end = dec.raw_decode(text, i)
                records = [text[i:end]]
        except (ValueError, IndexError) as exc:
            raise ReplayError("JSON is not a complete array or object") from exc
    if not records:
        raise ReplayError("no records")
    if len(records) > _MAX_RECORDS:
        raise ReplayError("too many records (limit %d)" % _MAX_RECORDS)
    return records, header


# ------------------------------------------------------------------------------------------------------------------ timestamp span
def _json_span(record: str, path: str):
    """Span of the value at `path`, found at the right nesting depth (a same-named key in another object is never matched)."""
    dec, num = json.JSONDecoder(), re.compile(r"-?\d+(?:\.\d+)?")

    def skip(i):
        while record[i].isspace() or record[i] == ",":
            i += 1
        return i

    def walk(i, keys):
        i = skip(i + 1)
        while record[i] != "}":
            key, i = dec.raw_decode(record, i)
            i = skip(record.index(":", i) + 1)
            if key == keys[0]:
                if len(keys) > 1:
                    return walk(i, keys[1:]) if record[i] == "{" else None
                if record[i] == '"':
                    _, end = dec.raw_decode(record, i)
                    return i + 1, end - 1
                m = num.match(record, i)
                return (i, m.end()) if m else None
            _, i = dec.raw_decode(record, i)
            i = skip(i)
        return None

    try:
        start = skip(0)
        return walk(start, path.split(".")) if record[start] == "{" else None
    except (ValueError, IndexError):
        return None


def _csv_span(record: str, header: List[str], column: str):
    if column not in header:
        return None
    want, idx, i, n = header.index(column), 0, 0, len(record)
    while idx <= want:
        start, quoted = i, i < n and record[i] == '"'
        if quoted:
            i += 1
            while i < n and not (record[i] == '"' and record[i + 1:i + 2] != '"'):
                i += 2 if record[i] == '"' else 1
            end = i
            i += 2
            if idx == want:
                return start + 1, end
        else:
            while i < n and record[i] != ",":
                i += 1
            if idx == want:
                return start, i
            i += 1
        idx += 1
    return None


def find_span(record: str, rule: TimestampRule, header=None):
    if rule.kind == "regex":
        m = re.search(rule.locator, record)
        return (m.start(1), m.end(1)) if m and m.re.groups >= 1 else None
    if rule.kind == "json_path":
        return _json_span(record, rule.locator)
    return _csv_span(record, header or [], rule.locator)


# ------------------------------------------------------------------------------------------------------------------ parse / render
def parse_ts(text: str, rule: TimestampRule) -> datetime:
    tz = ZoneInfo(rule.tz)
    try:
        if rule.fmt in ("epoch_s", "epoch_ms", "epoch_us"):
            div = {"epoch_s": 1, "epoch_ms": 1e3, "epoch_us": 1e6}[rule.fmt]
            return datetime.fromtimestamp(float(text) / div, timezone.utc)
        if rule.fmt == "syslog3164":
            m = _SYSLOG.fullmatch(text)
            dt = datetime(rule.assume_year, _MON.index(m[1]) + 1, int(m[3]), int(m[4]), int(m[5]), int(m[6]), tzinfo=tz)
            return dt.astimezone(timezone.utc)
        if rule.fmt == "iso8601":
            m = _ISO.match(text.strip())
            frac = int((m[8] or "0").ljust(6, "0")[:6])
            if m[9] in (None, ""):
                off = tz
            elif m[9] == "Z":
                off = timezone.utc
            else:
                s = m[9].replace(":", "")
                off = timezone(timedelta(hours=int(s[:3]), minutes=int(s[0] + s[3:5])))
            return datetime(*[int(m[i]) for i in (1, 2, 3, 5, 6, 7)], frac, tzinfo=off).astimezone(timezone.utc)
        fmt = rule.fmt if "%Y" in rule.fmt or "%y" in rule.fmt else "%Y " + rule.fmt
        src = text if fmt == rule.fmt else "%d %s" % (rule.assume_year, text)
        dt = datetime.strptime(src, fmt)
        return (dt if dt.tzinfo else dt.replace(tzinfo=tz)).astimezone(timezone.utc)
    except (ValueError, TypeError, AttributeError, KeyError, OverflowError) as exc:
        raise ReplayError("timestamp %r does not match format %s" % (text[:40], rule.fmt)) from exc


def render_ts(when: datetime, original: str, rule: TimestampRule) -> str:
    """The same textual shape as the recorded value (precision, separators, offset style) with the new instant."""
    tz = ZoneInfo(rule.tz)
    if rule.fmt in ("epoch_s", "epoch_ms", "epoch_us"):
        scale = {"epoch_s": 1, "epoch_ms": 1e3, "epoch_us": 1e6}[rule.fmt]
        value = when.timestamp() * scale
        return "%.*f" % (len(original.split(".")[1]), value) if "." in original else str(int(value))
    if rule.fmt == "syslog3164":
        m, local = _SYSLOG.fullmatch(original), when.astimezone(tz)
        pad = " " if local.day >= 10 else m[2]
        return "%s%s%d %02d:%02d:%02d" % (_MON[local.month - 1], pad, local.day, local.hour, local.minute, local.second)
    if rule.fmt == "iso8601":
        m = _ISO.match(original.strip())
        if m[9] in (None, ""):
            local, suffix = when.astimezone(tz), ""
        elif m[9] == "Z":
            local, suffix = when, "Z"
        else:
            s = m[9].replace(":", "")
            local = when.astimezone(timezone(timedelta(hours=int(s[:3]), minutes=int(s[0] + s[3:5]))))
            suffix = m[9]
        digits = len(m[8]) if m[8] else 0
        frac = ("." + ("%09d" % (local.microsecond * 1000))[:digits]) if digits else ""
        return "%04d-%02d-%02d%s%02d:%02d:%02d%s%s" % (local.year, local.month, local.day, m[4], local.hour, local.minute, local.second, frac, suffix)
    # strptime format: offset literal kept when the format carries %z, otherwise the rule tz
    if "%z" in rule.fmt:
        mo = re.search(r"[+-]\d\d:?\d\d$", original.strip())
        s = mo[0].replace(":", "") if mo else "+0000"
        local = when.astimezone(timezone(timedelta(hours=int(s[:3]), minutes=int(s[0] + s[3:5]))))
    else:
        local = when.astimezone(tz)
    out = local.strftime(rule.fmt)
    if "%f" in rule.fmt:
        fm = re.search(r"(?<=[.,])(\d{1,9})", original)
        if fm and len(fm[1]) < 6:
            full = "%06d" % local.microsecond
            out = out.replace(full, full[:len(fm[1])], 1)
    return out


# ------------------------------------------------------------------------------------------------------------------ timeline
@dataclass
class Item:
    record: str
    span: Optional[tuple]
    original: Optional[str]
    offset: float


@dataclass
class Timeline:
    items: List[Item]
    rule: Optional[TimestampRule]
    chronology: str
    loop_gap_s: float
    span_s: float
    out_of_order: int = 0
    skipped: List[str] = field(default_factory=list)
    compressed_s: float = 0.0   # total idle time removed by the opt-in max_gap_s (0 = spacing is exactly the source's)

    @property
    def period_s(self):
        return self.span_s + self.loop_gap_s


def build_timeline(text: str, fmt: str, rule: Optional[TimestampRule], *, on_bad_record="fail", loop_gap_s=None,
                   fixed_interval_s=None, record_start: Optional[str] = None, max_gap_s=None) -> Timeline:
    records, header = split_records(text, fmt, record_start)
    if rule is None:
        if not fixed_interval_s or fixed_interval_s <= 0:
            raise ReplayError("source has no trustworthy timestamp rule: refusing to invent a chronology "
                              "(select fixed_interval with an explicit interval_s to replay it unmodified)")
        items = [Item(r, None, None, i * float(fixed_interval_s)) for i, r in enumerate(records)]
        return Timeline(items, None, "USER_SPECIFIED_INTERVAL", float(loop_gap_s or fixed_interval_s), items[-1].offset)
    if on_bad_record not in ("fail", "skip"):
        raise ReplayError("on_bad_record must be fail or skip")
    parsed, skipped = [], []
    for n, rec in enumerate(records, 1):
        span = find_span(rec, rule, header)
        try:
            if span is None:
                raise ReplayError("timestamp field not found")
            when = parse_ts(rec[span[0]:span[1]], rule)
            if rule.kind == "json_path":  # the located literal must be the value the JSON parser sees
                node = json.loads(rec)
                for k in rule.locator.split("."):
                    node = node[k]
                if str(node) != rec[span[0]:span[1]].replace('\\"', '"'):
                    raise ReplayError("located timestamp is not the addressed JSON value")
        except (ReplayError, ValueError, KeyError, TypeError) as exc:
            if on_bad_record == "fail":
                raise ReplayError("record %d: %s" % (n, exc)) from exc
            skipped.append("record %d: %s" % (n, exc))
            continue
        parsed.append((rec, span, when))
    if not parsed:
        raise ReplayError("no record carries a parseable timestamp")
    if max_gap_s is not None and max_gap_s <= 0:
        raise ReplayError("max_gap_s must be positive")
    first, prev, ooo, items, shrunk, src_prev = parsed[0][2], 0.0, 0, [], 0.0, parsed[0][2]
    for rec, span, when in parsed:
        off = (when - first).total_seconds() - shrunk      # idle gaps longer than max_gap_s (opt-in) are shortened; all shorter spacing is exact
        if max_gap_s is not None and off - prev > max_gap_s:
            shrunk += off - prev - max_gap_s
            off = prev + max_gap_s
        if off < prev:
            off, ooo = prev, ooo + 1
        prev = off
        items.append(Item(rec, span, rec[span[0]:span[1]], off))
    gaps = [b.offset - a.offset for a, b in zip(items, items[1:]) if b.offset > a.offset]
    gap = float(loop_gap_s) if loop_gap_s is not None else max(statistics.median(gaps), 0.001) if gaps else 1.0
    if gap <= 0:
        raise ReplayError("loop_gap_s must be positive")
    tl = Timeline(items, rule, "SOURCE_TIMESTAMPS", gap, items[-1].offset, ooo, skipped)
    tl.compressed_s = shrunk
    return tl


def transform(item: Item, rule: Optional[TimestampRule], when: datetime) -> str:
    if rule is None:
        return item.record
    a, b = item.span
    return item.record[:a] + render_ts(when, item.original, rule) + item.record[b:]


def iter_transformed(tl: Timeline, anchor: datetime, *, speed=1.0, loops: Optional[int] = 1, start_loop=0) -> Iterator[tuple]:
    """Pure schedule: yields (loop, index, wall_offset_s, emitted_timestamp, raw). loops=None runs forever."""
    if speed <= 0:
        raise ReplayError("speed must be positive")
    k = start_loop
    while loops is None or k < start_loop + loops:
        for i, item in enumerate(tl.items):
            off = (k * tl.period_s + item.offset) / speed
            stamp = anchor + timedelta(seconds=off)
            yield k, i, off, stamp, transform(item, tl.rule, stamp)
        k += 1


def preview(text, fmt, rule, *, count=5, **kw):
    tl = build_timeline(text, fmt, rule, **{k: v for k, v in kw.items() if k in ("on_bad_record", "loop_gap_s", "fixed_interval_s", "record_start", "max_gap_s")})
    anchor = kw.get("anchor") or datetime.now(timezone.utc)
    rows = []
    for k, i, off, stamp, raw in iter_transformed(tl, anchor, speed=kw.get("speed", 1.0), loops=2):
        if len(rows) >= count and k == 0:
            break
        rows.append({"loop": k, "index": i, "offset_s": round(off, 6), "original": tl.items[i].record, "transformed": raw,
                     "changed_only_timestamp": (tl.rule is None) or (raw != tl.items[i].record)})
        if len(rows) >= count + 2 and k == 1:
            break
    return {"records": len(tl.items), "chronology": tl.chronology, "span_s": tl.span_s, "loop_gap_s": tl.loop_gap_s, "period_s": tl.period_s,
            "out_of_order_clamped": tl.out_of_order, "idle_time_compressed_s": tl.compressed_s, "skipped": tl.skipped[:10], "rows": rows}


# ------------------------------------------------------------------------------------------------------------------ session
class HecSink:
    """Delivers one record per HEC event using the existing dispatcher. `accepted` means HEC answered with success code 0."""

    def __init__(self, hec_url, token, index, host, source, sourcetype, ssl_verify=True, allow_insecure_tls=False):
        from netspout_core.telemetry_dispatcher import TelemetryDispatcher
        self._d, self._u, self._t = TelemetryDispatcher(), hec_url, token
        self._m = dict(index=index, host=host, source=source, sourcetype=sourcetype)
        self._v, self._i = ssl_verify, allow_insecure_tls

    def send(self, raw: str, when: datetime) -> str:
        outcome = self._d.emit_hec({"time": round(when.timestamp(), 6), "event": raw, **self._m}, self._u, self._t, self._v, self._i)
        return {"ACCEPTED": "accepted", "FAILED": "rejected"}.get(str(outcome.state).upper(), "unknown")


STATES = ("CREATED", "RUNNING", "PAUSED", "STOPPING", "STOPPED", "COMPLETED", "FAILED", "INTERRUPTED")


class ReplaySession:
    def __init__(self, timeline: Timeline, sink, *, source_label, sourcetype, index=DEFAULT_INDEX, host=DEFAULT_HOST, speed=1.0, eps_limit=None,
                 loops: Optional[int] = None, queue_size=1000, clock=time.monotonic, session_id=None):
        if speed <= 0 or (eps_limit is not None and eps_limit <= 0) or queue_size < 1 or (loops is not None and loops < 1):
            raise ReplayError("speed, eps_limit, queue_size and loops must be positive")
        self.id = session_id or "rp-" + uuid.uuid4().hex[:12]
        self.tl, self.sink, self.speed, self.eps, self.loops = timeline, sink, speed, eps_limit, loops
        self.index, self.host, self.sourcetype = index, host, sourcetype
        self.source = "pulseforge:replay:%s:%s" % (source_label, self.id)  # unique per session: the key for independent verification
        self._clock, self._q = clock, queue.Queue(queue_size)
        self._cancel, self._run, self._lock = threading.Event(), threading.Event(), threading.Lock()
        self._run.set()
        self.state, self.error = "CREATED", None
        self.counts = dict(generated=0, delivered=0, accepted=0, rejected=0, unknown=0, discarded_on_stop=0, backpressure_waits=0)
        self.last_emitted = None
        self.started_at = self.ended_at = None
        self._paused_total, self._paused_at, self._threads = 0.0, None, []

    # control ---------------------------------------------------------------------------------------------------------
    def start(self):
        with self._lock:
            if self.state != "CREATED":
                raise ReplayError("session already started")
            self.state, self.started_at = "RUNNING", datetime.now(timezone.utc)
        self._t0 = self._clock()
        self._threads = [threading.Thread(target=self._produce, daemon=True), threading.Thread(target=self._consume, daemon=True)]
        for t in self._threads:
            t.start()
        return self

    def pause(self):
        with self._lock:
            if self.state != "RUNNING":
                raise ReplayError("only a running session can be paused")
            self.state, self._paused_at = "PAUSED", self._clock()
            self._run.clear()

    def resume(self):
        with self._lock:
            if self.state != "PAUSED":
                raise ReplayError("only a paused session can be resumed")
            self._paused_total += self._clock() - self._paused_at
            self.state, self._paused_at = "RUNNING", None
            self._run.set()

    def stop(self, timeout=10):
        with self._lock:
            if self.state in ("STOPPED", "COMPLETED", "FAILED", "INTERRUPTED"):
                return
            self.state = "STOPPING"
        self._cancel.set()
        self._run.set()
        for t in self._threads:
            t.join(timeout)

    def wait(self, timeout=None):
        for t in self._threads:
            t.join(timeout)
        return self.state

    # workers ---------------------------------------------------------------------------------------------------------
    def _due_wait(self, wall_offset):
        while not self._cancel.is_set():
            self._run.wait(0.05)
            if not self._run.is_set():
                continue
            remaining = self._t0 + self._paused_total + wall_offset - self._clock()
            if remaining <= 0:
                return True
            self._cancel.wait(min(remaining, 0.05))
        return False

    def _produce(self):
        try:
            anchor = self.started_at
            for k, i, off, stamp, raw in iter_transformed(self.tl, anchor, speed=self.speed, loops=self.loops):
                if not self._due_wait(off):
                    break
                # the stamp was computed from the schedule; add time spent paused so the emitted clock stays "current"
                stamp = stamp + timedelta(seconds=self._paused_total)
                raw = transform(self.tl.items[i], self.tl.rule, stamp)
                item = (raw, stamp)
                try:
                    self._q.put_nowait(item)
                except queue.Full:
                    self.counts["backpressure_waits"] += 1  # the consumer is behind: the producer now blocks (no drops)
                    while not self._cancel.is_set():
                        try:
                            self._q.put(item, timeout=0.05)
                            break
                        except queue.Full:
                            continue
                    else:
                        break
                self.counts["generated"] += 1
        except Exception as exc:  # a producer fault must be visible, never swallowed
            self.error, self.state = "producer: %s" % type(exc).__name__, "FAILED"
            self._cancel.set()
        finally:
            self._q.put(None) if not self._cancel.is_set() else None

    def _consume(self):
        gap = 1.0 / self.eps if self.eps else 0.0
        nxt = 0.0
        while True:
            try:
                item = self._q.get(timeout=0.05)
            except queue.Empty:
                if self._cancel.is_set():
                    break
                continue
            if item is None:
                break
            while not self._run.is_set() and not self._cancel.is_set():  # paused: hold delivery too (queued items keep their schedule stamps)
                self._run.wait(0.05)
            if self._cancel.is_set():
                self.counts["discarded_on_stop"] += 1
                break
            if gap:
                wait = nxt - self._clock()
                if wait > 0 and self._cancel.wait(wait):
                    self.counts["discarded_on_stop"] += 1
                    break
                nxt = max(nxt, self._clock()) + gap
            raw, stamp = item
            try:
                result = self.sink.send(raw, stamp)
            except Exception:
                result = "rejected"
            self.counts["delivered"] += 1
            self.counts[{"accepted": "accepted", "rejected": "rejected"}.get(result, "unknown")] += 1
            self.last_emitted = stamp
        while True:
            try:
                if self._q.get_nowait() is not None:
                    self.counts["discarded_on_stop"] += 1
            except queue.Empty:
                break
        with self._lock:
            if self.state not in ("FAILED",):
                self.state = "STOPPED" if self._cancel.is_set() else "COMPLETED"
            self.ended_at = datetime.now(timezone.utc)

    # status ----------------------------------------------------------------------------------------------------------
    def status(self):
        return {"session_id": self.id, "state": self.state, "error": self.error, "source": self.source, "sourcetype": self.sourcetype,
                "index": self.index, "host": self.host, "speed": self.speed, "eps_limit": self.eps, "loops": self.loops, "queue_depth": self._q.qsize(),
                "chronology": self.tl.chronology, "loop_gap_s": self.tl.loop_gap_s, "records": len(self.tl.items), "counts": dict(self.counts),
                "started_at": self.started_at.isoformat() if self.started_at else None, "ended_at": self.ended_at.isoformat() if self.ended_at else None,
                "last_emitted": self.last_emitted.isoformat() if self.last_emitted else None,
                "indexed_confirmed": None, "note": "indexed_confirmed is set only by an independent Splunk search (verify)"}
