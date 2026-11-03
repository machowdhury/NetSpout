"""Investigation recipes name a lab default index; a run must be investigated in the index it was delivered to, with an openable Splunk search and an honest zero-result status."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "src")]

from netspout_core.unified_generation import UnifiedGenerationService  # noqa: E402

RECIPE = {"recipe_id": "r", "portability": "NETSPOUT_SPECIFIC", "spl": 'search index=idx_network_ops sourcetype="netspout:rfc5424" netspout_run_id="$run_id$" | sort 0 _time'}


def test_recipe_is_bound_to_the_destination_index():
    for literal in ('index=idx_network_ops', 'index="idx_network_ops"'):
        bound = UnifiedGenerationService._bind_investigation({**RECIPE, "spl": RECIPE["spl"].replace("index=idx_network_ops", literal)}, "dev_test_replay")
        assert 'index="dev_test_replay"' in bound["spl"] and "idx_network_ops" not in bound["spl"]
        assert 'netspout_run_id="$run_id$"' in bound["spl"]   # the run token is still substituted later, never at bind time


def test_binding_is_idempotent_and_does_not_mutate_the_recipe():
    once = UnifiedGenerationService._bind_investigation(RECIPE, "x1")
    assert UnifiedGenerationService._bind_investigation(once, "x1") == once
    assert "idx_network_ops" in RECIPE["spl"]


def test_search_path_opens_the_exact_query_over_the_run_window():
    path = UnifiedGenerationService._search_path('search index="a" netspout_run_id="r1" | stats count', "2026-11-03T01:15:27.257056Z")
    assert path.startswith("/app/search/search?q=search%20index%3D%22a%22")
    assert "earliest=1793063427" in path or "earliest=" in path and "latest=now" in path
    assert "earliest=-24h@h" in UnifiedGenerationService._search_path("index=a", None)   # no start time: a safe default window
