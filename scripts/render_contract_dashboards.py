#!/usr/bin/env python3
"""
Render Dashboard Studio views of sampled scenario runs in a real browser against an isolated lab Splunk Web, and record what is visible.

Per view: the page is opened with the run bound (form.run_tok) and the lab index, the panels get time to search, then a screenshot is saved and the page text is scanned
for "No results" and error text. This script records machine facts only. A view counts as VISUALLY VERIFIED only if a person (or the model) has looked at its screenshot and said so
in docs/verification/evidence/dashboards/contract_visual_inspection.json; this script never writes that file.

  python scripts/render_contract_dashboards.py ENVFILE RUN_MAP.json [--web 28000] [--ids a,b]
"""
import json
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
EVID = ROOT / "docs" / "verification" / "evidence" / "dashboards"
SHOTS = EVID / "screens_contract"


def main():
    env = dict(l.strip().split("=", 1) for l in open(sys.argv[1]) if "=" in l)
    run_map = json.loads(Path(sys.argv[2]).read_text())
    web = int(sys.argv[sys.argv.index("--web") + 1]) if "--web" in sys.argv else 28000
    ids = sys.argv[sys.argv.index("--ids") + 1].split(",") if "--ids" in sys.argv else list(run_map)
    suffix = sys.argv[sys.argv.index("--suffix") + 1] if "--suffix" in sys.argv else ""
    SHOTS.mkdir(parents=True, exist_ok=True)
    base, rows = "http://127.0.0.1:%d" % web, []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_context(viewport={"width": 1500, "height": 2300}).new_page()
        page.goto(base + "/en-US/account/login", wait_until="networkidle", timeout=120000)
        page.fill('input[name="username"]', "admin")
        page.fill('input[name="password"]', env["SPLUNK_PASSWORD"])
        page.keyboard.press("Enter")
        page.wait_for_timeout(8000)
        for cid in ids:
            url = "%s/en-US/app/netspout/pf_%s?form.run_tok=%s&form.index_tok=dev_test_replay" % (base, cid, run_map[cid])
            page.goto(url, wait_until="networkidle", timeout=120000)
            page.wait_for_timeout(20000)   # Dashboard Studio panels run their searches after load
            tabs = [t for t in ("Overview", "Investigation", "NOC", "Engineer", "Evidence") if page.locator("[role=tab]:has-text('%s')" % t).count()]
            shots, nores, errs, chars = [], 0, 0, 0
            for t in tabs:
                page.locator("[role=tab]:has-text('%s')" % t).first.click()
                page.wait_for_timeout(10000)
                text = page.inner_text("body")
                if t in ("Engineer", "Investigation"):   # the tab with the phase-story and metric panels; every tab's text is still scanned below
                    shot = SHOTS / ("%s%s__%s.jpg" % (cid, suffix, t))
                    page.screenshot(path=str(shot), full_page=True, type="jpeg", quality=55)
                    shots.append(str(shot.relative_to(ROOT)))
                nores += len(re.findall(r"No results", text))
                errs += len(re.findall(r"(?i)search (error|failed)|error in |unknown search command|could not", text))
                chars += len(text)
            rows.append({"scenario_id": cid, "run_id": run_map[cid], "title": page.title(), "tabs": tabs, "screenshots": shots, "no_results_text": nores, "error_text": errs, "page_text_chars": chars})
            print("%-26s tabs=%s no_results=%d errors=%d" % (cid, tabs, nores, errs))
        browser.close()
    (EVID / ("contract_dashboard_render%s.json" % suffix)).write_text(json.dumps({"environment": "isolated lab Splunk Web (docker splunk/splunk:10.2), headless Chromium via Playwright", "rendered": len(rows), "rows": rows}, indent=1) + "\n")


if __name__ == "__main__":
    main()
