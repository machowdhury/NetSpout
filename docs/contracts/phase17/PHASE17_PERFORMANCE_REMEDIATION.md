# Phase 17 performance remediation (screening only; no AWS run yet)

Baseline = source at `4c75092` (package gzip `4bf1d214…`, rebuilt locally and byte-identical to the approved artifact). Candidate = working tree on top of it (uncommitted until reviewed; screening package gzip `ff1d19bc…`, py313-linux-x86_64 variant only).

## Where the time went (cProfile of the real `ContinuousRun` worker, fake HEC, rate limiter off)
Per event, baseline: generation (template, random fields, timestamp) about 29 µs, HEC payload build 5 µs, JSON 2 µs, **HEC send about 6 ms**. 99% of wall time is the send:
- `ssl.create_default_context()` rebuilt for every event: 10.6 s of 20.1 s (53%, `set_default_verify_paths`).
- A new TCP connection and TLS handshake for every event: about 4.3 s (22%); the rest is urllib request/proxy setup and socket reads.
Not hot: recipe rendering, random fields, timestamps, serialization, batching (events are produced in chunks of 25), Unix-socket IPC (a poll every 15 s), per-event state updates. A pacing defect was found by screening: a late tick was forgotten, so a requested 200 events/s ran at ~172 even with the CPU 90% idle.
Evidence: `docs/verification/evidence/phase17/perf/baseline.json`, `step1.json`, `step2.json`.

## Changes (src/netspout_core, synced to backend/app and netspout/bin)
1. One shared TLS context per verification mode (`_hec_ssl_context`). Same verification policy.
2. `hec_keepalive` scope used only by `ContinuousRun` (single-sourcetype streams): one reused HTTP(S) connection per destination. Same payload, token, TLS policy and outcome classes. A connection idle more than 5 s is replaced before use; a failure on an open connection is UNKNOWN and is never re-sent; connect failures fall back to the unchanged path and its alternative endpoints; proxied destinations keep urllib. Scenario and finite runs are unchanged.
3. Pacer keeps its schedule (`nxt += gap`, resynchronising after a stall over 1 s) so the average equals the request and never exceeds it. The 200 events/s cap, 3,600 s cap and the authorisation checks are untouched. No concurrency was added.
Tests added: `tests/test_hec_keepalive.py` (11: reuse, outcome classes identical to the urllib path, idle replacement, closing servers, drop-after-send is UNKNOWN and not re-sent, unreachable, TLS context) and `tests/test_stream_pacer.py` (2). Related existing tests (2,963 across delivery, dispatcher and run routes): same result with and without the change (one pre-existing order-dependent failure, `test_gate6_integrity::test_07_successful_hec`, fails on the baseline too in that combined run and passes alone).

## Benchmarks
Screening A, engine worker natively on an arm64 Mac, python 3.15, disposable local HTTPS fake HEC, un-profiled:

| | requested | achieved eps | CPU of one core | CPU ms/event | peak RSS | rejected/unknown | distinct events | send→receive lag p99 |
|---|---|---|---|---|---|---|---|---|
| baseline 4c75092 | 200 | 158.9 | 72.8% | 4.58 | 236 MB | 0/0 | 9550/9550 | 21 ms |
| baseline | 2000 | 155.9 | 72.5% | 4.65 | 231 MB | 0/0 | 4700/4700 | 22 ms |
| candidate | 200 | **200.0** | 11.2% | 0.56 | 194 MB | 0/0 | 12025/12025 | 2 ms |
| candidate | 2000 | **2000.0** | 28.9% | 0.14 | 183 MB | 0/0 | 60000/60000 | 0.7 ms |

Every received event had the sourcetype, index, host and run id; event times were non-decreasing.

Screening B, real Splunk 10.6.1 (amd64 under emulation, Docker Desktop), package installed through Splunk Web, configured in the UI, 300 s at 200 events/s, same machine, back to back (absolute rates are not comparable to native; the comparison is):

| | indexed eps (per full minute min/mean/max) | accepted / indexed | dropped | seconds to all indexed | engine RSS first→last quarter | idle events |
|---|---|---|---|---|---|---|
| baseline `4bf1d214` | 141.7 / 143.7 / 146.1 | 43,250 / 43,250 | 0 | 0.4 | 276→312 MB | not re-measured |
| candidate `ff1d19bc` | **200.0 / 200.0 / 200.0** | 60,025 / 60,025 | 0 | 0.4 | 229.4→229.6 MB | not re-measured |

All five declared criteria pass for the candidate in this 300 s screen (the baseline fails the ≥190 one). engine CPU% there is `ps` lifetime average under emulation, relative only (baseline 43%, candidate 17%). Event correctness: the screens check count, distinctness, timestamps and run id on the wire (A) and accepted = indexed (B); an event-content comparison against the baseline output was not run.

## Not done / limits
- Not run: idle-generation test on the candidate (the change touches only the send path of a started run, but it was not measured), 10.2.7, the full browser/lifecycle suite, a long run. Screening is 300 s, not 3,600 s.
- Native Linux CPU per event will differ from this Mac; the CPU-bound baseline reached 124.5 events/s on the m6i.2xlarge. A 4-8x reduction in CPU per event is the expectation, not a result.
