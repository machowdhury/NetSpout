from netspout_core import universal_search as us

ST = [{"id": "aws-ct", "splunk_sourcetype": "aws:cloudtrail", "display_name": "AWS CloudTrail", "vendor_id": "aws", "generation_mode": "STATEFUL", "protocol": "https"},
      {"id": "x-none", "splunk_sourcetype": "x:none", "display_name": "Unsupported X", "vendor_id": "x", "generation_mode": None}]
EN = [{"entry_id": "op:1", "title": "BGP Peer Flap", "scenario_id": "NET-1", "runnable": True, "sourcetypes": ["cisco:ios"], "dashboard": {"splunk_view": "pf_NET-1"}, "maturity": {"tier": "CERTIFIED"}, "industries": [{"id": "telecom"}]},
      {"entry_id": "op:2", "title": "Catalog Only Story", "runnable": False, "blocked_reason": "no generator", "sourcetypes": [], "industries": []}]
DB = [{"view": "pf_NET-1", "title": "PulseForge · BGP flap", "description": "peer health", "maturity": None}]


def recs():
    return us.build_records(ST, EN, DB)


def test_all_kinds_searchable_and_unsupported_not_hidden():
    r = us.search(recs())
    assert r["counts"] == {"sourcetype": 2, "scenario": 2, "dashboard": 1}
    x = us.search(recs(), "unsupported")["items"][0]
    assert x["runnable"] is False and "Catalog entry only" in x["next_action"]


def test_catalog_only_scenario_is_not_advertised_as_executable():
    s = [i for i in us.search(recs(), kind="scenario")["items"] if not i["runnable"]][0]
    assert s["next_action"].startswith("Catalog only")


def test_ranking_filters_and_dashboard_link():
    r = us.search(recs(), "bgp")
    assert r["total"] == 2 and {i["kind"] for i in r["items"]} == {"scenario", "dashboard"}
    assert us.search(recs(), filters={"runnable": True}, kind="scenario")["total"] == 1
    d = us.search(recs(), kind="dashboard")["items"][0]
    assert d["related_scenarios"] == ["op:1"] and d["related_sourcetypes"] == ["cisco:ios"]
    assert us.search(recs(), "zzzz")["total"] == 0
