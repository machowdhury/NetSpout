#!/usr/bin/env python3
"""
Acceptance of the product journey through the INSTALLED Splunk Web UI with a REAL run (no mocks):
  Scenarios -> run -> HEC accepted -> independently indexed -> Overview observation -> Live Runs -> Investigate (Splunk Search with the
  exact run, index and time range) -> matching dashboard with the same run context -> Validate -> the 6-step run (Observe, Investigate).

Point it at an isolated Splunk (never the demo environment): it starts real runs, which write events.
  python scripts/acceptance_ux_live.py ENVFILE OUTDIR [--web 28000] [--mgmt 28089]
ENVFILE holds SPLUNK_PASSWORD=... (private, never printed). Screenshots and result.json are written to OUTDIR; exit code 1 if any check fails.
"""
import base64
import json
import re
import ssl
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

env = dict(l.strip().split("=", 1) for l in open(sys.argv[1]) if "=" in l)
OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
arg = lambda k, d: sys.argv[sys.argv.index(k) + 1] if k in sys.argv else d
WEB, MGMT = int(arg("--web", 28000)), int(arg("--mgmt", 28089))
B = "http://127.0.0.1:%d" % WEB
CTX = ssl._create_unverified_context()
AUTH = "Basic " + base64.b64encode(("admin:" + env["SPLUNK_PASSWORD"]).encode()).decode()
checks, result = [], {}


def check(name, ok, detail=""):
    checks.append({"check": name, "ok": bool(ok), "detail": str(detail)[:300]})
    print(("PASS " if ok else "FAIL ") + name + ((" | " + str(detail)[:160]) if detail else ""))


def spl(q, earliest="-3h"):
    d = urllib.parse.urlencode({"search": "search " + q, "exec_mode": "oneshot", "output_mode": "json", "count": "50", "earliest_time": earliest}).encode()
    r = urllib.request.urlopen(urllib.request.Request("https://127.0.0.1:%d/services/search/jobs" % MGMT, data=d, headers={"Authorization": AUTH}), context=CTX, timeout=120)
    return json.loads(r.read())["results"]


def frame(pg):
    return next((f for f in pg.frames if f != pg.main_frame and "dist/index.html" in f.url), None)


def goto(pg, path, wait=9000):
    pg.goto(B + path, wait_until="load", timeout=90000); pg.wait_for_timeout(wait)


with sync_playwright() as p:
    br = p.chromium.launch(); pg = br.new_context(viewport={"width": 1500, "height": 1000}).new_page()
    pg.goto(B + "/en-US/account/login", wait_until="load"); pg.fill('input[name="username"]', "admin"); pg.fill('input[name="password"]', env["SPLUNK_PASSWORD"]); pg.keyboard.press("Enter"); pg.wait_for_timeout(7000)

    # 0. navigation: five primary destinations in ONE row
    goto(pg, "/en-US/app/netspout/pulseforge_command_center", 12000); pg.screenshot(path=str(OUT / "01_overview_nav.png"))
    labels = ["Overview", "Scenarios", "Live Runs", "Investigate", "Dashboards", "More"]
    pos = {}
    for l in labels:
        loc = pg.locator("a, button", has_text=re.compile("^\\s*%s\\s*$" % l)).first
        if loc.count() and loc.is_visible(): pos[l] = loc.bounding_box()
    check("Splunk bar shows the five primary destinations plus More", set(pos) == set(labels), sorted(pos))
    ys = {round(b["y"] / 10) for b in pos.values() if b}
    check("the destinations sit in a single row", len(ys) == 1, sorted(ys))

    # 1. real run from Scenarios
    goto(pg, "/en-US/app/netspout/use_case_explorer", 12000); f = frame(pg)
    f.fill('input[type="search"], input[placeholder*="Search"]', "NF-SEC-06-DDOS"); pg.wait_for_timeout(3000)
    f.get_by_role("button", name=re.compile("Open scenario workflow")).first.click(); pg.wait_for_timeout(4000)
    cb = f.get_by_role("checkbox", name=re.compile("IPFIX over UDP", re.I))
    if cb.count() and cb.first.is_checked(): cb.first.uncheck()
    f.get_by_role("button", name=re.compile("Run scenario with live delivery monitor")).first.click()
    run_id, t0 = None, time.time()
    while time.time() - t0 < 150:
        pg.wait_for_timeout(2500); txt = f.inner_text("body")
        m = re.search(r"run (run-[0-9a-f]+)", txt); run_id = m.group(1) if m else run_id
        if re.search(r"COMPLETED", txt) and re.search(r"Indexed \(verified\)\s*\n?\s*820", txt): break
    pg.wait_for_timeout(4000); pg.screenshot(path=str(OUT / "02_run_monitor.png"), full_page=True)
    txt = f.inner_text("body")
    check("monitor shows 820 generated, accepted and indexed (verified)", all(re.search(p_ + r"\s*\n?\s*820", txt) for p_ in ("Generated", "HEC accepted", "Indexed \\(verified\\)")))
    check("monitor shows no stale 'Engine unreachable' banner for the finished run", "Engine unreachable" not in txt)
    result["run_id"] = run_id

    # 2. independent Splunk evidence for that exact run
    rows = spl('index=* netspout_run_id="%s" | stats count by index sourcetype' % run_id)
    result["splunk_by_index_sourcetype"] = rows
    check("an independent Splunk search finds 820 events for the run (index, sourcetype recorded)", rows and sum(int(r["count"]) for r in rows) == 820, rows)

    # 3. Overview reports that evidence
    goto(pg, "/en-US/app/netspout/pulseforge_command_center", 12000); f = frame(pg); pg.screenshot(path=str(OUT / "03_overview_after_run.png"), full_page=True)
    ov = f.inner_text("body"); i = ov.find("Splunk observation")
    check("Overview 'Splunk observation' reflects the run (VERIFIED, 820 of 820)", "VERIFIED" in ov[i:i + 700] and "820 of 820" in ov[i:i + 700], re.sub(r"\s+", " ", ov[i:i + 400]))

    # 4. Live Runs lists the run with its counters
    goto(pg, "/en-US/app/netspout/pulseforge_live_runs", 12000); f = frame(pg); pg.screenshot(path=str(OUT / "04_live_runs.png"), full_page=True)
    lr = f.inner_text("body")
    check("Live Runs lists the run with 820 / 820 / 820", run_id in lr and "820 / 820 / 820" in lr)

    # 5. Investigate: validation + Splunk Search for the exact run
    f.locator("tr", has_text=run_id).get_by_role("button", name="Investigate").first.click(); pg.wait_for_timeout(5000)
    pg.screenshot(path=str(OUT / "05_investigate.png"), full_page=True)
    inv = f.inner_text("body")
    check("Investigate validation states the verified evidence", "Verified by an independent Splunk search: 820 of 820" in inv, re.sub(r"\s+", " ", inv[inv.find("Validation"):][:200]))
    link = f.get_by_role("link", name="All events of this run").first
    href = link.get_attribute("href")
    result["search_href"] = href
    check("the search link carries the run's index, run id and time range", href and run_id in urllib.parse.unquote(href) and "index%3D%22" in href and "earliest=" in href, urllib.parse.unquote(href or "")[:200])
    link.click(); pg.wait_for_timeout(15000)
    got_it = pg.get_by_role("button", name="Got it!")   # Splunk's one-time product-usage notice, shown to a first-time admin session
    if got_it.count(): got_it.first.click(); pg.wait_for_timeout(2000)
    pg.screenshot(path=str(OUT / "06_splunk_search_opened.png"))
    body = pg.inner_text("body")
    check("Splunk Search opens and shows the run's 820 events", re.search(r"\b820 events\b", body) is not None, re.search(r"[\d,]+ events", body).group(0) if re.search(r"[\d,]+ events", body) else "no event count")

    # 6. matching dashboard, same run context
    goto(pg, "/en-US/app/netspout/pulseforge_investigate", 12000); f = frame(pg)
    f.locator("select").first.select_option(value=run_id); pg.wait_for_timeout(6000)
    dl = f.get_by_role("link", name=re.compile("matching dashboard")).first
    dh = dl.get_attribute("href"); result["dashboard_href"] = dh
    check("dashboard link carries run_tok and index_tok of the same run", dh and ("form.run_tok=" + run_id) in dh and "form.index_tok=" in dh, dh)
    dl.click(); pg.wait_for_timeout(30000); pg.screenshot(path=str(OUT / "07_dashboard_same_run.png"), full_page=True)
    dtxt = pg.inner_text("body")
    check("dashboard is bound to the run and shows its 820 flows", run_id in pg.url and re.search(r"Flows\s*\n?\s*820", dtxt) is not None)

    # 7. the 6-step run: Observe observes by itself, Investigate searches the right index
    goto(pg, "/en-US/app/netspout/pulseforge_command_center", 9000); f = frame(pg)
    f.get_by_role("button", name=re.compile("^Run in 6 Steps")).first.click(); pg.wait_for_timeout(4000)
    f.get_by_role("button", name=re.compile("^Scenario Generate")).first.click(); pg.wait_for_timeout(2000)
    f.get_by_role("button", name=re.compile("^Modeled Link-State")).first.click(); pg.wait_for_timeout(3000)
    for b_ in ("Preview", "Configure", "Run Preflight", "Continue to Run"):
        f.get_by_role("button", name=b_, exact=True).first.click(); pg.wait_for_timeout(8000 if b_ == "Run Preflight" else 4000)
    f.get_by_role("button", name=re.compile("^run$", re.I)).first.click(); pg.wait_for_timeout(15000)
    f.get_by_role("button", name=re.compile("Observe Evidence")).first.click(); pg.wait_for_timeout(20000)
    pg.screenshot(path=str(OUT / "08_observe_auto.png"), full_page=True)
    ob = re.sub(r"\s+", " ", f.locator("main").inner_text())
    check("Observe step proves SPLUNK OBSERVED without a manual refresh", re.search(r"SPLUNK OBSERVED\s+\d+\s+PROVEN", ob) is not None, ob[ob.find("SPLUNK OBSERVED"):][:80])
    f.locator("main").get_by_role("button", name=re.compile("INVESTIGATE", re.I)).last.click(); pg.wait_for_timeout(4000)
    q = f.locator("pre").first.inner_text()
    check("the guided investigation query uses the run's actual index", 'index="dev_test_replay"' in q and "idx_network_ops" not in q, q[:140])
    f.get_by_role("button", name=re.compile("Run in Splunk")).first.click(); pg.wait_for_timeout(12000)
    pg.screenshot(path=str(OUT / "09_guided_investigation.png"), full_page=True)
    res = re.sub(r"\s+", " ", f.locator("main").inner_text())
    check("Run in Splunk returns results (no false success)", re.search(r"SUCCEEDED · [1-9]\d* results", res) is not None, res[-160:])
    check("an 'Open in Splunk Search' link is offered", f.get_by_role("link", name="Open in Splunk Search").count() > 0)

    # 8. Guided Workflow no longer errors with an HTML-as-JSON failure
    f.get_by_role("button", name=re.compile("^Guided Workflow")).first.click(); pg.wait_for_timeout(6000)
    gw = f.inner_text("body"); pg.screenshot(path=str(OUT / "10_guided_workflow.png"), full_page=True)
    check("Guided Workflow loads without the 'Unexpected token <' error", "Unexpected token" not in gw)

    # 9. sidebar: no placeholder pages
    side = f.locator("nav").inner_text()
    check("sidebar offers no PLANNED / RESEARCH REQUIRED placeholder pages", "PLANNED" not in side and "RESEARCH REQUIRED" not in side, re.sub(r"\s+", " ", side)[:200])
    br.close()

result["checks"] = checks
(OUT / "result.json").write_text(json.dumps(result, indent=1))
failed = [c for c in checks if not c["ok"]]
print("\n%d checks, %d failed" % (len(checks), len(failed)))
sys.exit(1 if failed else 0)
