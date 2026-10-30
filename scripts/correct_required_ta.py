#!/usr/bin/env python3
"""Remove the demonstrably wrong `required_ta` ("Splunk Add-on for Unix and Linux") from Cisco sourcetype rows.

Evidence of the error: the Unix and Linux add-on parses *nix operating-system sources; the 100 Cisco rows below (SD-WAN, Catalyst/Catalyst Center,
Intersight, IOS, Duo, ACI) are not *nix sources. The replacement is NOT guessed: the repository records no sourcetype-to-add-on evidence for the
Cisco integrations (catalog/telemetry_catalog.json lists no sourcetypes) and Splunkbase IDs in vendors.json disagree with each other, so the
field becomes null with a `required_ta_review` record holding the previous value and the vendor-level app NAME from vendors.json as an unverified
candidate (no ID). Rows for linux_infrastructure, splunk and sc4snmp are untouched (not shown to be wrong).
Idempotent. Run: python scripts/correct_required_ta.py   then scripts/sync_core.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRONG = "Splunk Add-on for Unix and Linux"
CISCO = {"cisco_sdwan", "cisco_catalyst", "cisco_intersight", "cisco_ios", "cisco_duo", "cisco_aci"}


def main():
    path = ROOT / "catalog" / "sourcetypes.json"
    raw = path.read_text(encoding="utf-8")
    rows = json.loads(raw)
    assert json.dumps(rows, indent=1, ensure_ascii=False) + "\n" == raw, "unexpected file formatting"
    vendors = {v["id"]: v for v in json.loads((ROOT / "catalog" / "vendors.json").read_text(encoding="utf-8"))}
    changed = 0
    for r in rows:
        if r["vendor_id"] in CISCO and r.get("required_ta") == WRONG:
            candidate = (vendors.get(r["vendor_id"]) or {}).get("splunk_app_name")
            r["required_ta"] = None
            r["required_ta_review"] = {"status": "UNVERIFIED", "previous": WRONG, "candidate_name": candidate,
                                       "basis": "Previous value is a Unix/Linux parser for a Cisco source; candidate is the vendor-level app name in vendors.json, not verified for this sourcetype; no Splunkbase ID asserted."}
            changed += 1
    path.write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"rows_corrected": changed}))


def apply_declared():
    """Second step: fill required_ta ONLY where Splunkbase declares that exact sourcetype (docs/verification/evidence/splunkbase/crossref.json). Idempotent."""
    path = ROOT / "catalog" / "sourcetypes.json"
    rows = json.loads(path.read_text(encoding="utf-8"))
    x = json.loads((ROOT / "docs" / "verification" / "evidence" / "splunkbase" / "crossref.json").read_text(encoding="utf-8"))
    declared = {r["sourcetype"]: r["declared_by_uids"] for r in x["sourcetypes"]}
    apps = {a["uid"]: a for a in x["apps"]}
    changed = 0
    for r in rows:
        rv = r.get("required_ta_review")
        uids = declared.get(r["splunk_sourcetype"])
        if rv and rv.get("status") == "UNVERIFIED" and uids:
            r["required_ta"] = " / ".join(apps[u]["csv_name"] for u in uids)
            rv.update({"status": "VERIFIED_DECLARED_BY_SPLUNKBASE", "splunkbase_ids": [int(u) for u in uids],
                       "basis": "Splunkbase release metadata declares this exact sourcetype for the listed app(s) (pinned snapshot 2026-10-26 + v1 API). Declaration only: package not installed, parsing not validated."})
            changed += 1
    path.write_text(json.dumps(rows, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"rows_verified": changed}))


if __name__ == "__main__":
    import sys
    apply_declared() if "--apply-declared" in sys.argv else main()
