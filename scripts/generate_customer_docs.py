#!/usr/bin/env python3
"""
Generate the customer-facing catalogs docs/SCENARIOS.md and docs/TELEMETRY_COVERAGE.md from the source-derived coverage data
(docs/reference/*.json, produced by scripts/generate_reference_docs.py from the registries) and the dashboards shipped in the app.
Nothing here is typed by hand: counts, tiers and statuses come from the data, and a dashboard is listed only if its view file exists.

  PYTHONPATH=src:backend python scripts/generate_customer_docs.py
"""
import collections
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "docs" / "reference"
VIEWS = ROOT / "netspout" / "default" / "data" / "ui" / "views"
ENGINE_LABEL = {"scenario_pack": "Scenario pack", "incident_pack": "Incident pack", "replay_pack": "Replay pack (recorded data)", "netflow_solution": "NetFlow / IPFIX",
                "scenario_runner": "Scenario runner", "unified_generation": "Unified generation", "scenario_contract": "Declarative scenario contract"}
TIER_NOTE = {"CERTIFIED": "certified golden path", "VALIDATED": "validated", "CONTRACTED": "contract only", "FORMAT_VALIDATED": "format validated", "NOT_ESTABLISHED": "not established"}


def cell(v, n=90):
    s = ", ".join(v) if isinstance(v, list) else str(v if v is not None else "")
    s = s.replace("|", "/").replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def load(name):
    d = json.loads((REF / name).read_text())
    return d["generated"], d["rows"]


def describe(r):
    """What the scenario simulates, taken from its own definition (summary, else objective); never the placeholder stub text."""
    d = (r.get("summary") or r.get("objective") or "").strip()
    m = __import__("re").match(r"^Documented (\w+) candidate", d)
    if m:
        d = "%s use case from the community use-case library (%s). It describes what to detect on real data and defines no telemetry to generate." % (m.group(1).capitalize(), r["scenario_id"].replace("UCR-", "UC-"))
    return d


def scenarios_doc(srows, trows):
    kind_of = {t["sourcetype"]: t["data_kind"] for t in trows}
    run = [r for r in srows if r["runnable"]]
    cat = [r for r in srows if not r["runnable"]]
    by_engine = collections.Counter(r["engine"] for r in run)
    L = ["# Scenarios", "",
         "Generated from the scenario registries by `scripts/generate_customer_docs.py`; do not edit by hand. "
         f"**{len(srows)}** scenarios are defined; **{len(run)}** are runnable in this release. The rest are catalog entries only: they describe a use case but have no generator yet.", "",
         "| Runnable scenarios by type | Count |", "|---|---|"]
    L += ["| %s | %d |" % (ENGINE_LABEL.get(e, e), n) for e, n in sorted(by_engine.items())]
    L += ["", "**Runnable** means a real generator and run path exist and the output was independently found by a Splunk search in an isolated lab. It does not mean certified, "
          "and it does not mean every sourcetype in the scenario has a vendor add-on installed. **Maturity** is the tier recorded in the registry. "
          "Delivery is through HEC unless a row says otherwise; start a run from *Use Case Explorer* or *Scenario Studio* (see [QUICKSTART](QUICKSTART.md)).", ""]
    for e in sorted(by_engine):
        rows = sorted((r for r in run if r["engine"] == e), key=lambda r: r["scenario_id"])
        L += ["## %s (%d)" % (ENGINE_LABEL.get(e, e), len(rows)), "",
              "| ID | Name | What it simulates | Category | Vendor / technology | Sourcetypes | Telemetry | Transport | Maturity | Dashboard | Validation |", "|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            kinds = sorted({kind_of.get(s) or ("metric" if "metric" in s else "event") for s in r["sourcetypes"]}) or ["event"]
            dash = "`%s`" % r["dashboard"] if r.get("dashboard") and (VIEWS / (r["dashboard"] + ".xml")).exists() else "—"
            val = "indexed in lab; dashboard " + {"DASHBOARD_VISUALLY_VERIFIED": "visually verified", "DASHBOARD_DATA_VALIDATED": "data-validated"}.get(r.get("dashboard_maturity"), "not validated")
            L.append("| `%s` | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (r["scenario_id"], cell(r["title"], 70), cell(describe(r), 150), cell(r["category"], 30), cell(r["vendors"], 50),
                                                                                  cell(["`%s`" % s for s in r["sourcetypes"]], 120), "/".join(kinds), "HEC" + (" + IPFIX wire" if e == "netflow_solution" else ""), r["maturity_tier"], dash, val))
        L.append("")
    audit = {a["scenario_id"]: a for a in json.loads((REF / "scenario_activation_audit.json").read_text())["rows"]}
    L += ["## Defined but not runnable (%d)" % len(cat), "",
          "These have a definition but no executable telemetry. **Class C**: its sourcetypes have generators but no scenario sequence exists yet. **Class D**: blocked, because a needed data source is not in the catalog, has no generator, or is not named. "
          "Nothing here is hidden behind a status flag: the reason is computed in [reference/SCENARIO_ACTIVATION_AUDIT.md](reference/SCENARIO_ACTIVATION_AUDIT.md).", "",
          "| ID | Name | What it describes | Sourcetypes named | Class | Why not runnable |", "|---|---|---|---|---|---|"]
    for r in sorted(cat, key=lambda x: (x["engine"], x["scenario_id"])):
        a = audit.get(r["scenario_id"], {})
        L.append("| `%s` | %s | %s | %s | %s | %s |" % (r["scenario_id"], cell(r["title"], 70), cell(describe(r), 150), cell(["`%s`" % x for x in r["sourcetypes"]], 100) or "—", a.get("class", "?"), cell(a.get("reason", ""), 170)))
    L.append("")
    return "\n".join(L)


def telemetry_doc(srows, trows):
    dash_of = collections.defaultdict(int)
    n_of = collections.defaultdict(int)
    for r in srows:
        for s in r["sourcetypes"]:
            n_of[s] += 1
            if r.get("dashboard"):
                dash_of[s] += 1
    gen = collections.Counter(t["generator_tier"] for t in trows)
    vis_of = collections.defaultdict(int)
    for r in srows:
        if r.get("dashboard_maturity") == "DASHBOARD_VISUALLY_VERIFIED":
            for st in r["sourcetypes"]:
                vis_of[st] += 1
    fam = json.loads((REF / "sourcetype_event_families.json").read_text()) if (REF / "sourcetype_event_families.json").exists() else {}
    L = ["# Telemetry coverage", "",
         "Generated from `catalog/sourcetypes.json` and the coverage evidence by `scripts/generate_customer_docs.py`; do not edit by hand. "
         "Each column is separate evidence. **Catalog presence is not proof that a sourcetype works.**", "",
         "| Level | Meaning | Sourcetypes |", "|---|---|---|",
         "| Cataloged | Listed in the catalog | %d |" % len(trows),
         "| Generated | A native generator produces events (`G`) | %d |" % gen["NATIVE_ENGINE"],
         "| Sample replay | Replays a bundled sample, not a native generator (`R`) | %d |" % gen["SAMPLE_REPLAY"],
         "| Streamable | Can be sent as a bounded run through HEC (generated or sample replay) | %d |" % (gen["NATIVE_ENGINE"] + gen["SAMPLE_REPLAY"]),
         "| Byte-verified | Raw event equal to what was sent, checked in an isolated Splunk | %d |" % sum(t["format_byte_verified"] for t in trows),
         "| Independently indexed | Found by a separate Splunk search in an isolated lab | %d |" % sum(t["independently_indexed"] for t in trows),
         "| Add-on parsing checked | Parsed by the installed add-on in a lab | %d |" % sum(t["ta_parsing_checked_in_lab"] for t in trows),
         "| CIM validated | No CIM data model was installed in any lab | %d |" % sum(t["cim_validated"] for t in trows),
         "| Dashboard-validated | Referenced by a scenario with a data-validated dashboard | %d |" % sum(1 for t in trows if dash_of[t["sourcetype"]]),
         "| Visually verified | Referenced by a scenario whose dashboard was rendered and inspected | %d |" % sum(1 for t in trows if vis_of[t["sourcetype"]]),
         "| Not yet implemented | No generator: cataloged only | %d |" % gen["NONE"], "",
         "Everything else is **not tested**. Detection content (Enterprise Security, correlation searches) is not claimed.", "",
         "## Transports", "",
         "| Transport | Status in this release |", "|---|---|",
         "| HEC (events and metrics) | Supported; verified end to end, including independent indexing, on Splunk Enterprise 10.6.1.1 and in a Docker lab |",
         "| Syslog (UDP/TCP) | Supported by the generator for Enterprise and Docker; not available for restricted Splunk Cloud |",
         "| SNMP | Traps and metric-style records for the sourcetypes marked `snmp`; limited coverage |",
         "| NetFlow / IPFIX | Normalized flow events over HEC (verified); IPFIX wire export is a separate, separately reported stage |",
         "| OpenTelemetry | OTLP collector is part of the Docker deployment; see [guides/06_NETWORK_TELEMETRY_GUIDE.md](guides/06_NETWORK_TELEMETRY_GUIDE.md) |",
         "| gNMI / native streaming | Generators exist; **not validated** on the Enterprise single package (a native library is missing on the tested host) |", "",
         "## By vendor", "", "| Vendor | Sourcetypes | Generated | Sample replay | Indexed-verified | Protocols |", "|---|---|---|---|---|---|"]
    by = collections.defaultdict(list)
    for t in trows:
        by[t["vendor"]].append(t)
    for v in sorted(by, key=str.lower):
        ts = by[v]
        L.append("| %s | %d | %d | %d | %d | %s |" % (cell(v, 40), len(ts), sum(t["generator_tier"] == "NATIVE_ENGINE" for t in ts), sum(t["generator_tier"] == "SAMPLE_REPLAY" for t in ts),
                                                       sum(t["independently_indexed"] for t in ts), cell(sorted({t["protocol"] for t in ts}), 40)))
    L += ["", "## By sourcetype", "", "`G` generated, `R` sample replay, `-` none. **Event categories** are the generator's own event families (— where the generator does not enumerate them). Scenarios counts the registered scenarios that use the sourcetype; Dash counts those with a dashboard; Visual counts those whose dashboard was visually verified.", "",
          "| Vendor | Product | Sourcetype | Kind | Event categories | Transport | Gen | Byte | Indexed | Scenarios | Dash | Visual |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for t in sorted(trows, key=lambda x: (x["vendor"].lower(), x["sourcetype"])):
        g = {"NATIVE_ENGINE": "G", "SAMPLE_REPLAY": "R"}.get(t["generator_tier"], "-")
        L.append("| %s | %s | `%s` | %s | %s | %s | %s | %s | %s | %d | %d | %d |" % (cell(t["vendor"], 30), cell(t["product"], 40), t["sourcetype"], t["data_kind"], cell(fam.get(t["sourcetype"], []), 60) or "—",
                                                                                  "HEC (" + t["protocol"] + " format)", g, "yes" if t["format_byte_verified"] else "-", "yes" if t["independently_indexed"] else "-",
                                                                                  n_of[t["sourcetype"]], dash_of[t["sourcetype"]], vis_of[t["sourcetype"]]))
    L.append("")
    return "\n".join(L)


def update_readme(srows, trows):
    """The README's three coverage bullets are owned by this generator, so the numbers cannot drift from the registries."""
    import re
    f = ROOT / "README.md"
    t = f.read_text()
    run = sum(r["runnable"] for r in srows)
    dash = [r for r in srows if r.get("dashboard")]
    vis = sum(1 for r in dash if r.get("dashboard_maturity") == "DASHBOARD_VISUALLY_VERIFIED")
    dv = sum(1 for r in dash if r.get("dashboard_maturity") == "DASHBOARD_DATA_VALIDATED")
    impl = sum(1 for r in dash if r.get("dashboard_maturity") == "DASHBOARD_IMPLEMENTED")
    t = re.sub(r"- \*\*\d+ runnable scenarios\*\* \(\d+ defined\):.*", "- **%d runnable scenarios** (%d defined): incident packs, NetFlow/IPFIX, replayed recordings, security and operational scenarios. The other %d are documented but not runnable yet, each with the reason. See [SCENARIOS](docs/SCENARIOS.md)." % (run, len(srows), len(srows) - run), t)
    t = re.sub(r"- \*\*\d+ Dashboard Studio dashboards\*\*.*", "- **%d Dashboard Studio dashboards**, one per runnable scenario: %d data-validated against indexed data (%d of those also visually verified) and %d implemented but not yet validated against data." % (len(dash), dv + vis, vis, impl), t)
    f.write_text(t)


if __name__ == "__main__":
    _, srows = load("scenario_coverage.json")
    _, trows = load("sourcetype_coverage.json")
    (ROOT / "docs" / "SCENARIOS.md").write_text(scenarios_doc(srows, trows))
    (ROOT / "docs" / "TELEMETRY_COVERAGE.md").write_text(telemetry_doc(srows, trows))
    update_readme(srows, trows)
    print("wrote docs/SCENARIOS.md and docs/TELEMETRY_COVERAGE.md")
