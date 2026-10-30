"""Phase 4F: the Splunk app ships the nav entries, the Dashboard Studio view and a locked-down gateway."""
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT / "src"), str(ROOT / "netspout" / "bin")):
    if _p not in sys.path:
        sys.path.insert(0, _p)

APP = ROOT / "netspout"
VIEWS = APP / "default" / "data" / "ui" / "views"


def test_nav_has_command_center_default_and_explorer_and_views_exist():
    nav = ET.parse(APP / "default/data/ui/nav/default.xml").getroot()
    views = {v.get("name"): v for v in nav.iter("view")}
    assert views["pulseforge_command_center"].get("label") == "PulseForge Command Center"
    assert views["pulseforge_command_center"].get("default") == "true"
    assert views["use_case_explorer"].get("label") == "Use Case Explorer"
    for name in ("pulseforge_command_center", "use_case_explorer", "pulseforge_dns_anomaly_studio", "netspout_canvas"):
        assert name in views and (VIEWS / f"{name}.xml").exists()


def test_dns_studio_view_is_a_valid_v2_dashboard_with_real_searches():
    root = ET.parse(VIEWS / "pulseforge_dns_anomaly_studio.xml").getroot()
    assert root.get("version") == "2"
    definition = json.loads(root.find("definition").text)
    from netspout_core.dashboard_recipes import DashboardRecipeService
    result = DashboardRecipeService.validate_export(definition, list(definition["visualizations"]))
    assert result["valid"], result["failures"]
    queries = [d["options"]["query"] for d in definition["dataSources"].values()]
    assert len(definition["visualizations"]) >= 10 and all("idx_network_ops" in q for q in queries)
    assert not any(re.search(r"\|\s*(makeresults|inputlookup|outputlookup)", q) for q in queries), "no synthetic or static data"
    assert {"run_tok", "phase_tok", "client_tok", "global_time"} <= {o["options"]["token"] for o in definition["inputs"].values()}


def test_gateway_rejects_non_api_paths_and_unprivileged_writes(monkeypatch):
    import netspout_gateway as g
    gw = g.NetSpoutGateway()
    call = lambda **kw: gw.handle(json.dumps({"session": {"authtoken": "k"}, **kw}))
    assert call(method="GET", path_info="/etc/passwd")["status"] == 404
    assert call(method="GET", path_info="/api/../x")["status"] == 404
    assert call(method="DELETE", path_info="/api/setup")["status"] == 404
    assert gw.handle(json.dumps({"method": "GET", "path_info": "/api/setup", "session": {}}))["status"] == 401
    monkeypatch.setattr(g, "_roles", lambda _k: {"user"})
    assert call(method="POST", path_info="/api/setup", payload="{}")["status"] == 403
    monkeypatch.setattr(g, "_roles", lambda _k: (_ for _ in ()).throw(RuntimeError("splunkd down")))
    assert call(method="POST", path_info="/api/setup", payload="{}")["status"] == 403, "unknown role fails closed"
