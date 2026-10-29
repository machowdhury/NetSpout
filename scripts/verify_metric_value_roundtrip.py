"""Verify metric VALUE round-trip, not just metric name presence.

A run that reports the right number of events but the wrong numbers is not
integrated -- it is noise. This script replays the scenario's generation
offline under the same seed, computes the arithmetic mean each metric name
should have, and compares it against what ``| mstats avg(*)`` actually returned
from Splunk for that run_id.

Usage
-----
    PYTHONPATH=src:backend ./backend/venv/bin/python \\
        scripts/verify_metric_value_roundtrip.py \\
        --scenario network_security_correlation --seed 51002 \\
        --evidence docs/verification/pulseforge_phase4c_xsrc_correlation.json

Exit code 0 only when every metric name round-trips within tolerance.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from statistics import mean
from typing import Any, Dict, List

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.join(REPO, "backend"))

from netspout_core.catalog import catalog_instance          # noqa: E402
from netspout_core.graph_engine import TopologyGraph        # noqa: E402
from netspout_core.models import ScenarioContract           # noqa: E402
from netspout_core.scenario_runner import ScenarioRunner    # noqa: E402
from netspout_core.telemetry_dispatcher import is_metric_sourcetype  # noqa: E402

#: Relative tolerance for a float round-trip through HEC -> index -> mstats.
REL_TOLERANCE = 1e-6


def replay_metric_values(scenario_id: str) -> Dict[str, List[float]]:
    """Regenerate offline and collect every emitted metric value by name.

    The values are captured from the *real* HEC payload that
    ``TelemetryDispatcher.dispatch_log`` builds (with the network call stubbed
    out), so the metric names here already went through the production mapping
    -- for example ``queue_depth_bytes`` -> ``queue_depth``. Re-implementing
    that mapping in a test script would prove nothing about the shipped path.

    The generator is seeded from the scenario id, so this reproduces exactly
    what the live run emitted, independent of the run_id (which the engine
    stamps itself and cannot be injected).
    """
    from netspout_core.models import TelemetryTransportConfig
    from netspout_core.telemetry_dispatcher import TelemetryDispatcher

    runner = ScenarioRunner()
    raw = catalog_instance.get_scenario(scenario_id)
    if not raw:
        raise SystemExit(f"scenario {scenario_id!r} not in canonical catalog")
    contract = ScenarioContract(**raw)
    topology = runner._get_topology_for_scenario(contract)
    graph = TopologyGraph(topology)

    dispatcher = TelemetryDispatcher()
    transport = TelemetryTransportConfig(
        hec_enabled=True,
        hec_url="https://stub.invalid/services/collector",
        hec_token="offline-replay-no-credential",
        hec_index="idx_network_ops",
        hec_metric_index="idx_performance_metrics",
    )

    collected: Dict[str, List[float]] = {}
    for phase_def in contract.phases:
        for entry in runner._generate_phase_telemetry(
            phase_def.phase.value, contract, topology, graph
        ):
            if not is_metric_sourcetype(entry.sourcetype):
                continue
            payloads: List[Dict[str, Any]] = []
            dispatcher.emit_hec = (
                lambda p, u, t, **k: (payloads.append(p), (True, "stubbed"))[1]
            )
            dispatcher.dispatch_log(entry, transport)
            for payload in payloads:
                if payload.get("event") != "metric":
                    continue
                for key, value in payload.get("fields", {}).items():
                    if key.startswith("metric_name:"):
                        collected.setdefault(key.split(":", 1)[1], []).append(float(value))
    return collected


def observed_from_evidence(path: str) -> Any:
    with open(path) as fh:
        evidence = json.load(fh)
    rows: List[Dict[str, Any]] = evidence.get("indexed_metric_rows") or []
    if not rows:
        raise SystemExit(f"{path}: no indexed_metric_rows -- nothing round-tripped")
    observed: Dict[str, float] = {}
    for row in rows:
        for key, value in row.items():
            if key.startswith("avg(") and key.endswith(")"):
                observed[key[4:-1]] = float(value)
    return observed, evidence


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--evidence", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    replayed = replay_metric_values(args.scenario)
    observed, evidence = observed_from_evidence(args.evidence)

    results: Dict[str, Dict[str, Any]] = {}
    failures = 0
    print(f"\n=== metric value round-trip: {args.scenario} (seed {args.seed}) ===")
    print(f"  run_id {evidence.get('run_id')} | "
          f"expected from offline replay vs observed from mstats\n")
    print(f"  {'metric name':32s} {'expected avg':>22s} {'observed avg':>22s}  match")
    for name in sorted(set(replayed) | set(observed)):
        exp_vals = replayed.get(name)
        obs = observed.get(name)
        if not exp_vals:
            print(f"  {name:32s} {'(none replayed)':>22s} {obs!r:>22}  MISSING-EXPECTED")
            results[name] = {"expected": None, "observed": obs, "match": False}
            failures += 1
            continue
        if obs is None:
            print(f"  {name:32s} {mean(exp_vals)!r:>22} {'(absent)':>22}  MISSING-OBSERVED")
            results[name] = {"expected": mean(exp_vals), "observed": None, "match": False}
            failures += 1
            continue
        exp = mean(exp_vals)
        denom = abs(exp) if abs(exp) > 1e-12 else 1.0
        rel = abs(obs - exp) / denom
        ok = rel <= REL_TOLERANCE
        if not ok:
            failures += 1
        print(f"  {name:32s} {exp:>22.6f} {obs:>22.6f}  {'TRUE' if ok else 'FALSE'} "
              f"(rel_err {rel:.2e}, n={len(exp_vals)})")
        results[name] = {
            "expected_avg": exp,
            "observed_avg": obs,
            "samples": len(exp_vals),
            "relative_error": rel,
            "match": ok,
        }

    summary = {
        "scenario_id": args.scenario,
        "seed": args.seed,
        "run_id": evidence.get("run_id"),
        "metric_index": evidence.get("metric_index"),
        "tolerance": REL_TOLERANCE,
        "metrics_checked": len(results),
        "all_values_match": failures == 0,
        "failures": failures,
        "per_metric": results,
        "note": (
            "Values are modeled SNMP-derived measurements replayed from the "
            "seeded generator; no device was polled."
        ),
    }
    print(f"\n  metrics checked : {len(results)}")
    print(f"  all values match: {failures == 0}")

    if args.out:
        with open(args.out, "w") as fh:
            json.dump(summary, fh, indent=2)
            fh.write("\n")
        print(f"  [out] {args.out}")

    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
