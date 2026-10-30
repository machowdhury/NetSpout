"""Continuous sample replay: record fidelity, timestamp transformation, timeline, loop boundaries, session control and counters."""
import json
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT / 'src'), str(ROOT / 'backend')):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from netspout_core.sample_replay import (ReplayError, ReplaySession, TimestampRule as R, build_timeline, find_span, iter_transformed, parse_ts, preview,
                                         render_ts, split_records)

ANCHOR = datetime(2026, 11, 1, 12, 0, 0, 250000, tzinfo=timezone.utc)
SYSLOG = "May  6 17:23:50 h k: a\nMay  6 17:23:52 h k: b\nMay  6 17:24:00 h k: c\n"
SYSLOG_R = R('regex', r'^([A-Z][a-z]{2} +\d{1,2} \d\d:\d\d:\d\d)', 'syslog3164')
JSONL = '{"timestamp":"2024-08-02T14:21:23.992673+0000","n":1}\n{"timestamp":"2024-08-02T14:21:25.100000+0000","n":2}\n'
JSONL_R = R('json_path', 'timestamp', '%Y-%m-%dT%H:%M:%S.%f%z')


def test_split_every_supported_format_keeps_record_bytes():
    assert split_records(SYSLOG, 'syslog')[0][1] == "May  6 17:23:52 h k: b"
    arr = '[ {"a": 1,\n  "b": [1, 2]} ,{"a":2} ]'
    assert split_records(arr, 'json')[0] == ['{"a": 1,\n  "b": [1, 2]}', '{"a":2}']
    recs, header = split_records('t,msg\n2026-01-01T00:00:00Z,"two\nlines, with comma"\n2026-01-01T00:00:01Z,x\n', 'csv')
    assert header == ['t', 'msg'] and len(recs) == 2 and recs[0].endswith('with comma"')
    xml = "<Event a='1'><S>x</S>\n</Event>\n<Event><S>y</S></Event>"
    assert len(split_records(xml, 'windows_xml')[0]) == 2
    assert split_records('1.2.3.4 - - [10/Oct/2000:13:55:36 -0700] "GET / HTTP/1.0" 200 2\n', 'apache')[0]
    with pytest.raises(ReplayError):
        split_records('{"a":1}\nnot json\n', 'jsonl')
    with pytest.raises(ReplayError):
        split_records('[{"a":1},{"a":', 'json')  # truncated: refused, not repaired
    with pytest.raises(ReplayError):
        split_records('a,b\n1,"open\n', 'csv')


CASES = [  # (record, rule, header) - parse then render round-trip must reproduce the exact original text of the field
    ('{"time":"2022-10-13T20:57:35.833Z"}', R('json_path', 'time', 'iso8601'), None),
    ('{"id":{"time":"2022-10-13T20:57:35.833Z"},"time":"x"}', R('json_path', 'id.time', 'iso8601'), None),
    ('{"t":1658918559.957,"k":1}', R('json_path', 't', 'epoch_s'), None),
    ('{"EventSecond":1744752707}', R('json_path', 'EventSecond', 'epoch_s'), None),
    ('{"ms":1744752707123}', R('json_path', 'ms', 'epoch_ms'), None),
    ('{"t":"2025-09-30T20:01:00.367-04:00"}', R('json_path', 't', 'iso8601'), None),
    ("<Event><TimeCreated SystemTime='2021-12-21T12:50:11.1234567Z'/></Event>", R('regex', r"SystemTime='([^']+)'", 'iso8601'), None),
    ('1.2.3.4 - - [10/Oct/2000:13:55:36 -0700] "GET / HTTP/1.0" 200', R('regex', r'\[([^\]]+)\]', '%d/%b/%Y:%H:%M:%S %z'), None),
    ('msg=audit(02/20/2025 13:07:46.504:118908) : x', R('regex', r'audit\(([^:]+:\d\d:\d\d\.\d+)', '%m/%d/%Y %H:%M:%S.%f'), None),
    ('SESSION|05/14/2024 17:40:50.250|[HTTPS]', R('regex', r'\|(\d\d/\d\d/\d{4} \d\d:\d\d:\d\d\.\d+)\|', '%m/%d/%Y %H:%M:%S.%f', tz='America/New_York'), None),
    ('May  6 17:23:50 h k: a', SYSLOG_R, None),
    ('2026-01-01 10:00:00,beta', R('csv_column', 't', '%Y-%m-%d %H:%M:%S', tz='Europe/Berlin'), ['t', 'v']),
]


@pytest.mark.parametrize('rec,rule,header', CASES, ids=range(len(CASES)))
def test_parse_render_roundtrip_and_only_the_timestamp_bytes_change(rec, rule, header):
    a, b = find_span(rec, rule, header)
    original = rec[a:b]
    when = parse_ts(original, rule)
    # datetimes hold microseconds: a 7-digit Windows tick fraction round-trips to 6 digits plus a zero (documented limit)
    assert render_ts(when, original, rule) == original.replace('1234567Z', '1234560Z')
    new = ANCHOR + timedelta(seconds=7)
    out = rec[:a] + render_ts(new, original, rule) + rec[b:]
    assert out[:a] == rec[:a] and out[len(out) - (len(rec) - b):] == rec[b:]
    na, nb = find_span(out, rule, header)
    got = parse_ts(out[na:nb], rule)
    got = got.replace(year=new.year) if rule.fmt == 'syslog3164' else got   # syslog stamps carry no year
    assert abs((got - new).total_seconds()) < 1.0  # fractional precision of the source limits exactness


def test_precision_offset_style_and_timezone_are_preserved_in_the_rendering():
    z = R('json_path', 't', 'iso8601')
    assert render_ts(ANCHOR, '2022-10-13T20:57:35.833Z', z) == '2026-11-01T12:00:00.250Z'
    assert render_ts(ANCHOR, '2025-09-30T20:01:00-04:00', z) == '2026-11-01T08:00:00-04:00'
    ny = R('regex', 'x', '%m/%d/%Y %H:%M:%S.%f', tz='America/New_York')
    assert render_ts(ANCHOR, '05/14/2024 17:40:50.250', ny) == '11/01/2026 07:00:00.250'   # DST ended 06:00 UTC that day, so EST (-5): the tz database is applied, not a fixed offset
    assert render_ts(ANCHOR, '1658918559.957', R('regex', 'x', 'epoch_s')) == '%.3f' % ANCHOR.timestamp()


def test_relative_spacing_and_loop_boundaries_are_monotonic():
    tl = build_timeline(SYSLOG, 'syslog', SYSLOG_R)
    assert [i.offset for i in tl.items] == [0, 2, 10] and tl.loop_gap_s == 5.0 and tl.period_s == 15.0   # median of positive spacings [2, 8]
    rows = list(iter_transformed(tl, ANCHOR, loops=3))
    offs = [r[2] for r in rows]
    assert offs == [0, 2, 10, 15, 17, 25, 30, 32, 40] and all(b > a for a, b in zip(offs, offs[1:]))
    assert rows[3][3] - rows[2][3] == timedelta(seconds=5)  # boundary gap == documented loop gap, never zero or negative
    assert [r[3] for r in rows] == sorted(r[3] for r in rows)
    assert tl.items[0].record.split(' h ')[1] == rows[0][4].split(' h ')[1]  # everything after the timestamp is untouched
    assert build_timeline(SYSLOG, 'syslog', SYSLOG_R, loop_gap_s=0.5).period_s == 10.5
    assert [r[2] for r in iter_transformed(tl, ANCHOR, speed=2, loops=1)] == [0, 1, 5]


def test_out_of_order_source_is_clamped_not_reordered_and_counted():
    tl = build_timeline("May  6 17:00:10 a\nMay  6 17:00:05 b\nMay  6 17:00:20 c\n", 'syslog', SYSLOG_R)
    assert [i.offset for i in tl.items] == [0, 0, 10] and tl.out_of_order == 1


def test_source_without_a_trustworthy_timestamp_is_refused_unless_an_interval_is_explicit():
    with pytest.raises(ReplayError, match='refusing to invent'):
        build_timeline('a\nb\n', 'text', None)
    tl = build_timeline('a\nb\n', 'text', None, fixed_interval_s=2)
    assert tl.chronology == 'USER_SPECIFIED_INTERVAL' and [r[4] for r in iter_transformed(tl, ANCHOR, loops=1)] == ['a', 'b']


def test_bad_records_fail_closed_or_are_reported_when_skipping():
    text = SYSLOG + "no timestamp here\n"
    with pytest.raises(ReplayError, match='record 4'):
        build_timeline(text, 'syslog', SYSLOG_R)
    tl = build_timeline(text, 'syslog', SYSLOG_R, on_bad_record='skip')
    assert len(tl.items) == 3 and tl.skipped and 'record 4' in tl.skipped[0]
    with pytest.raises(ReplayError):
        build_timeline('{"timestamp":"not a time"}\n', 'jsonl', JSONL_R)


def test_json_lines_with_nested_and_decoy_fields_rewrites_only_the_addressed_value():
    rec = '{"meta":{"timestamp":"decoy"},"timestamp":"2024-08-02T14:21:23.992673+0000"}'
    tl = build_timeline(rec + "\n", 'jsonl', JSONL_R)
    out = next(iter_transformed(tl, ANCHOR))[4]
    assert json.loads(out)['meta'] == {'timestamp': 'decoy'} and json.loads(out)['timestamp'].startswith('2026-11-01T12:00:00.25')


def test_preview_shows_original_transformed_and_the_second_loop():
    p = preview(SYSLOG, 'syslog', SYSLOG_R, count=3, anchor=ANCHOR)
    assert p['records'] == 3 and p['period_s'] == 15.0 and {r['loop'] for r in p['rows']} == {0, 1}
    assert all(r['changed_only_timestamp'] for r in p['rows'])


class ListSink:
    def __init__(self, delay=0, fail_every=0, result='accepted'):
        self.got, self.delay, self.fail_every, self.result, self.lock = [], delay, fail_every, result, threading.Lock()

    def send(self, raw, when, meta=None):
        time.sleep(self.delay)
        with self.lock:
            self.got.append((raw, when, time.monotonic()))
            if self.fail_every and len(self.got) % self.fail_every == 0:
                raise RuntimeError('boom')
        return self.result


def make(sink, text=SYSLOG, **kw):
    tl = build_timeline(text, 'syslog', SYSLOG_R, loop_gap_s=kw.pop('gap', 0.1))
    return ReplaySession(tl, sink, source_label='t', sourcetype='linux:syslog', **kw)


def test_finite_replay_delivers_every_record_in_order_with_exact_counters():
    sink = ListSink()
    s = make(sink, speed=100, loops=3).start()
    assert s.wait(10) == 'COMPLETED'
    c = s.status()['counts']
    assert c['generated'] == c['delivered'] == c['accepted'] == 9 and c['rejected'] == c['unknown'] == c['discarded_on_stop'] == 0
    stamps = [g[1] for g in sink.got]
    assert stamps == sorted(stamps) and len(set(stamps)) == 9                      # strictly increasing across loop boundaries
    assert s.status()['indexed_confirmed'] is None and s.source.startswith('pulseforge:replay:t:rp-')


def test_wall_clock_pacing_preserves_spacing_at_speed():
    sink = ListSink()
    s = make(sink, speed=20, loops=1).start()           # offsets 0, 2, 10 s  ->  0, 0.1, 0.5 s of wall time
    s.wait(10)
    t = [g[2] for g in sink.got]
    assert 0.07 <= t[1] - t[0] <= 0.25 and 0.3 <= t[2] - t[1] <= 0.65


def test_eps_limit_throttles_delivery():
    sink = ListSink()
    s = make(sink, speed=1000, loops=2, eps_limit=20).start()   # 6 records at <=20/s
    s.wait(10)
    t = [g[2] for g in sink.got]
    assert len(t) == 6 and t[-1] - t[0] >= 0.2


def test_backpressure_blocks_the_producer_and_drops_nothing():
    sink = ListSink(delay=0.05)
    s = make(sink, speed=1000, loops=3, queue_size=1).start()
    assert s.wait(20) == 'COMPLETED'
    c = s.status()['counts']
    assert c['backpressure_waits'] > 0 and c['generated'] == c['delivered'] == 9 and c['discarded_on_stop'] == 0


def test_sink_failures_and_unknown_outcomes_are_counted_separately():
    s = make(ListSink(fail_every=2), speed=1000, loops=2).start()
    s.wait(10)
    c = s.status()['counts']
    assert c['delivered'] == 6 and c['rejected'] == 3 and c['accepted'] == 3
    u = make(ListSink(result='unknown'), speed=1000, loops=1).start()
    u.wait(10)
    assert u.status()['counts']['unknown'] == 3 and u.status()['counts']['accepted'] == 0


def test_continuous_replay_runs_until_stopped_and_stop_is_prompt():
    sink = ListSink()
    s = make(sink, speed=200, loops=None, gap=0.2).start()
    time.sleep(0.6)
    assert s.state == 'RUNNING' and len(sink.got) > 6          # more than one loop: it loops
    t0 = time.monotonic()
    s.stop()
    assert time.monotonic() - t0 < 2 and s.state == 'STOPPED'
    n = len(sink.got)
    time.sleep(0.3)
    assert len(sink.got) == n                                      # nothing after stop
    stamps = [g[1] for g in sink.got]
    assert stamps == sorted(stamps) and len(set(stamps)) == len(stamps)


def test_pause_freezes_the_clock_and_resume_continues_without_burst_or_gap_collapse():
    sink = ListSink()
    s = make(sink, speed=10, loops=None, gap=2.0).start()
    time.sleep(0.5)
    s.pause()
    assert s.state == 'PAUSED'
    time.sleep(0.15)
    n = len(sink.got)
    time.sleep(0.5)
    assert len(sink.got) == n                                      # nothing delivered while paused (queued items are held too)
    s.resume()
    assert s.state == 'RUNNING'
    time.sleep(0.5)
    s.stop()
    assert len(sink.got) > n
    stamps = [g[1] for g in sink.got]
    assert stamps == sorted(stamps) and len(set(stamps)) == len(stamps)
    # emitted stamps follow the schedule plus paused time: the stamp of the first post-resume event is not earlier than "now - small"
    assert (datetime.now(timezone.utc) - stamps[-1]).total_seconds() < 1.0


def test_invalid_control_transitions_and_parameters_are_rejected():
    s = make(ListSink(), loops=1)
    with pytest.raises(ReplayError):
        s.pause()
    s.start()
    with pytest.raises(ReplayError):
        s.start()
    with pytest.raises(ReplayError):
        s.resume()
    s.stop()
    s.stop()  # idempotent
    for bad in ({'speed': 0}, {'eps_limit': 0}, {'queue_size': 0}, {'loops': 0}):
        with pytest.raises(ReplayError):
            make(ListSink(), **bad)


def test_multiline_records_are_joined_byte_for_byte_with_a_record_start_pattern():
    text = "2026-01-01T00:00:00Z ERROR boom\n  at a.b(C.java:1)\n  at d.e(F.java:2)\n2026-01-01T00:00:03Z INFO ok\n"
    rule = R('regex', r'^(\S+)', 'iso8601')
    tl = build_timeline(text, 'text', rule, record_start=r'^\d{4}-')
    assert len(tl.items) == 2 and tl.items[0].record.count('\n') == 2 and tl.items[1].offset == 3
    out = [r[4] for r in iter_transformed(tl, ANCHOR, loops=1)]
    assert out[0].split('\n')[1:] == ['  at a.b(C.java:1)', '  at d.e(F.java:2)'] and out[0].startswith('2026-11-01T12:00:00Z ERROR')


def test_registry_sources_all_parse_and_truncated_excerpts_drop_the_partial_record():
    reg = json.loads((ROOT / 'catalog' / 'replay_sources.json').read_text())['sources']
    assert len(reg) >= 10 and {s['format'] for s in reg} >= {'syslog', 'apache', 'jsonl', 'windows_xml', 'text'}
    for s in reg:
        data = (ROOT / s['file']).read_text()
        if s['drop_last_record']:
            data = data[:data.rstrip('\n').rfind('\n')]
        tl = build_timeline(data, s['format'], R(**s['timestamp_rule']))
        assert len(tl.items) == s['records'] and tl.chronology == 'SOURCE_TIMESTAMPS'


def test_idle_gaps_are_compressed_only_when_asked_and_short_spacing_stays_exact():
    text = "May  6 17:00:00 a\nMay  6 17:00:02 b\nMay  7 17:00:00 c\nMay  7 17:00:03 d\n"
    exact = build_timeline(text, 'syslog', SYSLOG_R)
    assert exact.items[2].offset == 86400 and exact.compressed_s == 0
    packed = build_timeline(text, 'syslog', SYSLOG_R, max_gap_s=30)
    assert [i.offset for i in packed.items] == [0, 2, 32, 35] and packed.compressed_s == 86398 - 30
    assert [i.offset for i in packed.items][1] - [i.offset for i in packed.items][0] == 2
    with pytest.raises(ReplayError):
        build_timeline(text, 'syslog', SYSLOG_R, max_gap_s=0)
