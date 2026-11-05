# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/yaml_sample_replay.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""Structured sample replay.

A sample file is a YAML configuration. Only three documented fields carry telemetry; everything else (names, intervals, counts,
token definitions, descriptions, ...) is configuration and is never emitted:

  samples[].lines[]._raw     inline events                         (adapter "lines")
  samples[].fromRaw          file next to the YAML, one event per line   (adapter "fromRaw")
  samples[].fromSample       CSV next to the YAML with a `_raw` column   (adapter "fromSample")

Tokens defined in samples[].tokens are rendered at emit time. `format: template` replaces `$name$`; `format: regex` replaces the
regular expression in `token:`. A token type or feature without an explicit implementation raises UnsupportedSampleError; an event
that still contains a `$name$` placeholder after rendering raises UnresolvedPlaceholderError. Nothing is guessed or fabricated.
"""
import csv
import os
import random
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import yaml

MAX_YAML_BYTES = 8 * 1024 * 1024
MAX_RAW_BYTES = 8 * 1024 * 1024
_PLACEHOLDER = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)\$")


class SampleError(ValueError):
    code = "SAMPLE_ERROR"


class SampleFormatError(SampleError):
    code = "SAMPLE_FORMAT"


class UnsupportedSampleError(SampleError):
    code = "SAMPLE_UNSUPPORTED"


class UnresolvedPlaceholderError(SampleError):
    code = "SAMPLE_UNRESOLVED_PLACEHOLDER"

    def __init__(self, names):
        self.names = sorted(set(names))
        super().__init__("unresolved placeholders: " + ", ".join(self.names))


# ---------------------------------------------------------------- timestamps
_GO = re.compile(r"January|Monday|2006|Jan|Mon|MST|-07:00|-0700|Z07:00|[.,](?:0+|9+)|01|02|_2|15|03|04|05|06|PM|pm|2|1|3|4|5")


def _go_time(dt: datetime, layout: str) -> str:
    def sub(m):
        t = m.group(0)
        if t[0] in ".," and len(t) > 1:
            n = len(t) - 1
            return t[0] + ("%06d" % dt.microsecond)[:n].ljust(n, "0")
        return {"January": dt.strftime("%B"), "Monday": dt.strftime("%A"), "2006": "%04d" % dt.year, "Jan": dt.strftime("%b"), "Mon": dt.strftime("%a"),
                "MST": "UTC", "-07:00": "+00:00", "-0700": "+0000", "Z07:00": "Z", "01": "%02d" % dt.month, "02": "%02d" % dt.day, "_2": "%2d" % dt.day,
                "15": "%02d" % dt.hour, "03": "%02d" % (dt.hour % 12 or 12), "04": "%02d" % dt.minute, "05": "%02d" % dt.second, "06": "%02d" % (dt.year % 100),
                "PM": "AM" if dt.hour < 12 else "PM", "pm": "am" if dt.hour < 12 else "pm", "2": str(dt.day), "1": str(dt.month),
                "3": str(dt.hour % 12 or 12), "4": str(dt.minute), "5": str(dt.second)}[t]
    return _GO.sub(sub, layout)


def _strftime(dt: datetime, fmt: str) -> str:
    fmt = fmt.replace("%3N", "%03d" % (dt.microsecond // 1000)).replace("%f", "%06d" % dt.microsecond)
    return dt.strftime(fmt)


_JAVA = re.compile(r"'[^']*'|yyyy|yy|MM|dd|HH|mm|ss|SSS|[A-Za-z]")


def _java_time(dt: datetime, pattern: str) -> str:
    def sub(m):
        t = m.group(0)
        if t.startswith("'"):
            return t[1:-1]
        table = {"yyyy": "%04d" % dt.year, "yy": "%02d" % (dt.year % 100), "MM": "%02d" % dt.month, "dd": "%02d" % dt.day, "HH": "%02d" % dt.hour,
                 "mm": "%02d" % dt.minute, "ss": "%02d" % dt.second, "SSS": "%03d" % (dt.microsecond // 1000)}
        if t not in table:
            raise UnsupportedSampleError("unsupported javatimestamp pattern letter %r in %r" % (t, pattern))
        return table[t]
    return _JAVA.sub(sub, pattern)


# -------------------------------------------------------------------- tokens
@dataclass
class Token:
    name: str
    type: str
    regex: Optional[str]
    spec: Dict[str, Any]
    base: str
    choices: Optional[List[str]] = None

    def apply(self, text: str, val: str) -> str:
        if not self.regex:
            return re.sub(r"\$" + re.escape(self.name) + r"\$", lambda _m: val, text)
        rx = re.compile(self.regex)
        if rx.groups == 0:
            return rx.sub(lambda _m: val, text)           # no capture group: the whole match is replaced
        # one capture group: only that group is replaced, the text around it is kept

        def sub(m):
            a, b = m.span(1)
            return m.group(0)[: a - m.start()] + val + m.group(0)[b - m.start():] if a >= 0 else m.group(0)
        return rx.sub(sub, text)

    def value(self, rng: random.Random, now: datetime) -> str:
        t, s = self.type, self.spec
        if t == "gotimestamp":
            return _go_time(now, str(s.get("replacement", "2006-01-02T15:04:05Z")))
        if t == "timestamp":
            return _strftime(now, str(s.get("replacement", "%Y-%m-%dT%H:%M:%S.%fZ")))
        if t == "epochtimestamp":
            if s.get("replacement") not in (None, ""):
                raise UnsupportedSampleError("epochtimestamp replacement %r" % s.get("replacement"))
            return str(int(now.timestamp()))
        if t == "javatimestamp":
            r = s.get("replacement")
            return str(int(now.timestamp() * 1000)) if r in (None, "") else _java_time(now, str(r))
        if t == "static":
            return str(s.get("replacement", ""))
        if t == "choice":
            return rng.choice(self.choices)
        if t == "weightedChoice":
            items = s["weightedChoice"]
            return str(rng.choices([i["choice"] for i in items], weights=[float(i.get("weight", 1)) for i in items])[0])
        if t == "random":
            kind = s.get("replacement")
            if kind == "int":
                return str(rng.randint(int(s["lower"]), int(s["upper"])))
            if kind == "float":
                return "%.*f" % (int(s.get("precision", 2)), rng.uniform(float(s["lower"]), float(s["upper"])))
            if kind == "string":
                return "".join(rng.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(int(s.get("length", 8))))
            if kind == "hex":
                return "".join(rng.choice("0123456789abcdef") for _ in range(int(s.get("length", 8))))
            if kind == "guid":
                return str(uuid.UUID(int=rng.getrandbits(128), version=4))
            if kind == "ipv4":
                return ".".join(str(rng.randint(1, 254)) for _ in range(4))
            if kind == "ipv6":
                return ":".join("%x" % rng.randint(0, 65535) for _ in range(8))
            if kind == "mac":
                return ":".join("%02x" % rng.randint(0, 255) for _ in range(6))
            raise UnsupportedSampleError("random replacement %r" % kind)
        raise UnsupportedSampleError("token type %r" % t)


_SUPPORTED = {"gotimestamp", "timestamp", "epochtimestamp", "javatimestamp", "static", "choice", "weightedChoice", "random"}


def _compile_token(raw: Any, base: str) -> Token:
    if not isinstance(raw, dict) or "name" not in raw or "type" not in raw:
        raise SampleFormatError("token without name/type: %r" % (raw,))
    ttype = str(raw["type"])
    if ttype not in _SUPPORTED:
        raise UnsupportedSampleError("token type %r (token %s)" % (ttype, raw["name"]))
    fmt = raw.get("format")
    if fmt not in ("template", "regex"):
        raise SampleFormatError("token %s has format %r (expected template or regex)" % (raw["name"], fmt))
    regex = None
    if fmt == "regex":
        regex = raw.get("token")
        if not isinstance(regex, str) or not regex:
            raise SampleFormatError("regex token %s has no `token` pattern" % raw["name"])
        try:
            groups = re.compile(regex).groups
        except re.error as exc:
            raise SampleFormatError("regex token %s: %s" % (raw["name"], exc))
        if groups > 1:
            raise UnsupportedSampleError("regex token %s has %d capture groups; which group is replaced is not defined" % (raw["name"], groups))
    choices = None
    if ttype == "choice":
        if isinstance(raw.get("choice"), list) and raw["choice"]:
            choices = [str(c) for c in raw["choice"]]
        elif isinstance(raw.get("sample"), str):
            p = os.path.join(base, raw["sample"].strip())
            if not os.path.isfile(p) or os.path.getsize(p) > MAX_RAW_BYTES:
                raise SampleFormatError("choice sample file missing or too large: %s" % raw["sample"])
            with open(p, encoding="utf-8", errors="replace") as fh:
                choices = [ln.rstrip("\r\n") for ln in fh if ln.strip()]
        if not choices:
            raise SampleFormatError("choice token %s has no values" % raw["name"])
    if ttype == "weightedChoice" and not (isinstance(raw.get("weightedChoice"), list) and raw["weightedChoice"]):
        raise SampleFormatError("weightedChoice token %s has no items" % raw["name"])
    if ttype == "random" and raw.get("replacement") == "int" and ("lower" not in raw or "upper" not in raw):
        raise SampleFormatError("random int token %s needs lower and upper" % raw["name"])
    return Token(name=str(raw["name"]), type=ttype, regex=regex, spec=raw, base=base, choices=choices)


# ------------------------------------------------------------------ templates
@dataclass
class Template:
    raw: str
    adapter: str
    sample_name: str
    tokens: List[Token] = field(default_factory=list)
    sourcetype: Optional[str] = None
    source: Optional[str] = None
    host: Optional[str] = None
    index: Optional[str] = None

    def render(self, rng: random.Random, now: datetime) -> str:
        out = self.raw
        for tok in self.tokens:
            # one value per token per event, so a token that repeats within an event repeats its value
            val = tok.value(rng, now)
            out = tok.apply(out, val)
        left = _PLACEHOLDER.findall(out)
        if left:
            raise UnresolvedPlaceholderError(left)
        return out


class SampleSet:
    def __init__(self, path: str, templates: List[Template]):
        self.path = path
        self.templates = templates

    def __len__(self):
        return len(self.templates)

    def sourcetypes(self):
        return sorted({t.sourcetype for t in self.templates if t.sourcetype})

    def restrict_to(self, sourcetype: str) -> "SampleSet":
        """Templates that claim `sourcetype`. Templates with no claim are kept; templates claiming another sourcetype are dropped, never relabelled."""
        kept = [t for t in self.templates if t.sourcetype in (None, sourcetype)]
        if not kept:
            raise SampleFormatError("sample file claims %s, not %s" % (self.sourcetypes(), sourcetype))
        return SampleSet(self.path, kept)

    def render_one(self, rng: Optional[random.Random] = None, now: Optional[datetime] = None) -> str:
        rng = rng or random.Random()
        return rng.choice(self.templates).render(rng, now or datetime.now(timezone.utc))

    def render_all(self, rng: Optional[random.Random] = None, now: Optional[datetime] = None) -> List[str]:
        rng = rng or random.Random()
        now = now or datetime.now(timezone.utc)
        return [t.render(rng, now) for t in self.templates]


def _text(v: Any, where: str) -> str:
    if not isinstance(v, str) or not v.strip():
        raise SampleFormatError("%s is not a non-empty string" % where)
    return v[:-1] if v.endswith("\n") else v


def load_sample_set(path: str) -> SampleSet:
    """Parse one sample YAML into templates. Raises SampleError subclasses; never returns configuration text as telemetry."""
    if os.path.getsize(path) > MAX_YAML_BYTES:
        raise SampleFormatError("OVERSIZE: %s is larger than %d bytes; not parsed" % (os.path.basename(path), MAX_YAML_BYTES))
    base = os.path.dirname(os.path.abspath(path))
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            doc = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise SampleFormatError("invalid YAML: %s" % str(exc).splitlines()[0])
    if not isinstance(doc, dict) or not isinstance(doc.get("samples"), list) or not doc["samples"]:
        raise SampleFormatError("no `samples` list (configuration without telemetry)")
    templates: List[Template] = []
    for i, smp in enumerate(doc["samples"]):
        if not isinstance(smp, dict):
            raise SampleFormatError("samples[%d] is not a mapping" % i)
        name = str(smp.get("name", "sample%d" % i))
        toks = [_compile_token(t, base) for t in (smp.get("tokens") or [])]
        found = 0
        meta: List[Dict[str, Any]] = []     # lines[] entries without _raw only declare sourcetype/source/host/index for fromRaw/fromSample events
        external = bool(smp.get("fromRaw") or smp.get("fromSample"))
        for j, line in enumerate(smp.get("lines") or []):
            if not isinstance(line, dict):
                raise SampleFormatError("samples[%d].lines[%d] is not a mapping" % (i, j))
            if external and not str(line.get("_raw") or "").strip():
                meta.append(line)
                continue
            if "_raw" not in line:
                raise SampleFormatError("samples[%d].lines[%d] has no _raw" % (i, j))
            templates.append(Template(_text(line["_raw"], "samples[%d].lines[%d]._raw" % (i, j)), "lines", name, toks, line.get("sourcetype"), line.get("source"), line.get("host"), line.get("index")))
            found += 1
        claims = {str(m["sourcetype"]) for m in meta if m.get("sourcetype")}
        if len(claims) > 1:
            raise SampleFormatError("samples[%d] declares several sourcetypes (%s) for externally supplied events; which applies to which is not defined" % (i, sorted(claims)))
        m0 = meta[0] if meta else {}
        ext_meta = (m0.get("sourcetype"), m0.get("source"), m0.get("host"), m0.get("index"))
        if smp.get("fromRaw"):
            p = os.path.join(base, str(smp["fromRaw"]).strip())
            if not os.path.isfile(p):
                raise SampleFormatError("fromRaw file missing: %s" % smp["fromRaw"])
            if os.path.getsize(p) > MAX_RAW_BYTES:
                raise SampleFormatError("OVERSIZE: fromRaw %s larger than %d bytes; not parsed" % (smp["fromRaw"], MAX_RAW_BYTES))
            with open(p, encoding="utf-8", errors="replace") as fh:
                for ln in fh:
                    if ln.strip():
                        templates.append(Template(ln.rstrip("\r\n"), "fromRaw", name, toks, *ext_meta))
                        found += 1
        if smp.get("fromSample"):
            p = os.path.join(base, str(smp["fromSample"]).strip())
            if not os.path.isfile(p):
                raise SampleFormatError("fromSample file missing: %s" % smp["fromSample"])
            if os.path.getsize(p) > MAX_RAW_BYTES:
                raise SampleFormatError("OVERSIZE: fromSample %s larger than %d bytes; not parsed" % (smp["fromSample"], MAX_RAW_BYTES))
            try:
                with open(p, encoding="utf-8", errors="replace", newline="") as fh:
                    rd = csv.DictReader(fh)
                    if not rd.fieldnames or "_raw" not in rd.fieldnames:
                        raise SampleFormatError("fromSample %s has no _raw column" % smp["fromSample"])
                    for row in rd:
                        if (row.get("_raw") or "").strip():
                            templates.append(Template(row["_raw"], "fromSample", name, toks, row.get("sourcetype") or ext_meta[0], row.get("source") or ext_meta[1], row.get("host") or ext_meta[2], row.get("index") or ext_meta[3]))
                            found += 1
            except csv.Error as exc:
                raise SampleFormatError("fromSample %s is not valid CSV: %s" % (smp["fromSample"], exc))
        if not found:
            raise SampleFormatError("samples[%d] (%s) has no telemetry-bearing field (lines/_raw, fromRaw, fromSample)" % (i, name))
    return SampleSet(path, templates)


def validate_sample_file(path: str, limit: int = 5000) -> Dict[str, Any]:
    """Load and dry-render up to `limit` templates. Returns a status record; used by the corpus inventory and the regression tests."""
    rec: Dict[str, Any] = {"path": path, "status": "REPLAYABLE", "events": 0, "adapters": [], "sourcetypes": [], "error": None, "unresolved": []}
    try:
        ss = load_sample_set(path)
    except UnsupportedSampleError as exc:
        return dict(rec, status="UNSUPPORTED", error=str(exc))
    except SampleFormatError as exc:
        msg = str(exc)
        return dict(rec, status="OVERSIZE" if msg.startswith("OVERSIZE") else "CONFIG_ONLY" if msg.startswith("no `samples` list") else "INVALID", error=msg)
    rec.update(events=len(ss), adapters=sorted({t.adapter for t in ss.templates}), sourcetypes=ss.sourcetypes())
    rng, now = random.Random(0), datetime.now(timezone.utc)
    unresolved = set()
    try:
        for t in ss.templates[:limit]:
            try:
                t.render(rng, now)
            except UnresolvedPlaceholderError as exc:
                unresolved.update(exc.names)
    except UnsupportedSampleError as exc:
        return dict(rec, status="UNSUPPORTED", error=str(exc))
    if unresolved:
        rec.update(status="UNRESOLVED_PLACEHOLDER", unresolved=sorted(unresolved), error="unresolved placeholders: " + ", ".join(sorted(unresolved)))
    return rec
