#!/usr/bin/env python3
"""Builds NetSpout_PulseForge_Demo.pptx from the screenshots/ and diagram PNGs next to it.
   python build_deck.py   (needs python-pptx and Pillow). Every text, callout and picture is a native, editable object."""
from pathlib import Path
from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Inches, Pt

H = Path(__file__).resolve().parent
SH = H / "screenshots"
NAVY, TEAL, ORANGE, INK, MUTE, LIGHT, WHITE, LINE = (RGBColor.from_string(x) for x in ("0B2E3B", "1C7293", "D9480F", "1F2D33", "5B6B72", "EEF4F6", "FFFFFF", "C9D6DB"))
HEAD, BODY = "Cambria", "Calibri"
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
N = [0]


def tb(sl, x, y, w, h, text="", size=16, bold=False, color=INK, font=BODY, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, italic=False):
    s = sl.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h)); tf = s.text_frame; tf.word_wrap = True; tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    p = tf.paragraphs[0]; p.alignment = align; r = p.add_run(); r.text = text
    f = r.font; f.size, f.bold, f.italic, f.name = Pt(size), bold, italic, font; f.color.rgb = color
    return s


def para(tf, text, size=16, bold=False, color=INK, space=8, first=False, font=BODY, runs=None):
    p = tf.paragraphs[0] if first else tf.add_paragraph(); p.space_after = Pt(space)
    for t, b, c in (runs or [(text, bold, color)]):
        r = p.add_run(); r.text = t; r.font.size, r.font.bold, r.font.name = Pt(size), b, font; r.font.color.rgb = c
    return p


def box(sl, x, y, w, h, fill=LIGHT, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE, lw=1.0, radius=0.06):
    s = sl.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None: s.fill.background()
    else: s.fill.solid(); s.fill.fore_color.rgb = fill
    if line is None: s.line.fill.background()
    else: s.line.color.rgb = line; s.line.width = Pt(lw)
    s.shadow.inherit = False
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE: s.adjustments[0] = radius
    return s


def new(title=None, dark=False, source=None, notes=""):
    sl = prs.slides.add_slide(BLANK); N[0] += 1
    bg = sl.background.fill; bg.solid(); bg.fore_color.rgb = NAVY if dark else WHITE
    if title: tb(sl, 0.6, 0.38, 12.1, 0.8, title, 32, True, WHITE if dark else NAVY, HEAD, anchor=MSO_ANCHOR.MIDDLE)
    if source: tb(sl, 0.6, 7.08, 11.0, 0.25, source, 10, color=MUTE if not dark else LINE)
    tb(sl, 12.2, 7.08, 0.6, 0.25, str(N[0]), 10, color=MUTE if not dark else LINE, align=PP_ALIGN.RIGHT)
    sl.notes_slide.notes_text_frame.text = notes.strip()
    return sl


def pic(sl, name, x, y, maxw, maxh, alt, border=True):
    w, h = Image.open(SH / name if (SH / name).exists() else H / name).size
    k = min(maxw / w, maxh / h); pw, ph = w * k, h * k
    p = sl.shapes.add_picture(str(SH / name if (SH / name).exists() else H / name), Inches(x), Inches(y), Inches(pw), Inches(ph))
    p._element.nvPicPr.cNvPr.set("descr", alt)
    if border: p.line.color.rgb = LINE; p.line.width = Pt(0.75)
    return x, y, pw, ph


def callouts(sl, rect, items, start=1):
    """items: (fx, fy, fw, fh) fractions of the picture; draws an outline and a numbered marker."""
    x, y, w, h = rect
    for i, it in enumerate(items, start):
        fx, fy, fw, fh = it[:4]; pos = it[4] if len(it) > 4 else 0; above = pos == 1
        o = box(sl, x + fx * w, y + fy * h, fw * w, fh * h, None, ORANGE, MSO_SHAPE.RECTANGLE, 2.25)
        o.name = "callout %d outline" % i
        m = sl.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x + fx * w if pos else max(x + fx * w - 0.40, 0.1)), Inches(y + fy * h - 0.36 if above else (y + (fy + fh) * h + 0.04 if pos == 2 else y + fy * h)), Inches(0.3), Inches(0.3))
        m.fill.solid(); m.fill.fore_color.rgb = ORANGE; m.line.color.rgb = WHITE; m.line.width = Pt(1); m.shadow.inherit = False; m.name = "callout %d marker" % i
        tf = m.text_frame; tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER; r = p.add_run(); r.text = str(i); r.font.size = Pt(11); r.font.bold = True; r.font.color.rgb = WHITE; r.font.name = BODY


def tag(sl, text, x, y, w, color=NAVY):
    s = box(sl, x, y, w, 0.3, color, None, radius=0.5); tf = s.text_frame; tf.margin_top = tf.margin_bottom = 0; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER; r = p.add_run(); r.text = text; r.font.size = Pt(11); r.font.bold = True; r.font.color.rgb = WHITE; r.font.name = BODY


def numbered(sl, x, y, w, items, size=15, gap=0.12, start=1):
    """Numbered explanation rows that match the callout markers."""
    for i, (head, body) in enumerate(items, start):
        m = sl.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y + 0.02), Inches(0.32), Inches(0.32)); m.fill.solid(); m.fill.fore_color.rgb = ORANGE; m.line.fill.background(); m.shadow.inherit = False
        tf = m.text_frame; tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER; r = p.add_run(); r.text = str(i); r.font.size = Pt(12); r.font.bold = True; r.font.color.rgb = WHITE; r.font.name = BODY
        t = tb(sl, x + 0.45, y, w - 0.45, 1.0, "", size)
        tf = t.text_frame; para(tf, "", size, first=True, space=0, runs=[(head, True, NAVY)])
        para(tf, body, size - 1, color=INK, space=0)
        lines = 1 + (len(body) // int((w - 0.45) * 11.0)) + 1
        y += 0.26 + 0.2 * lines + gap
    return y


# ---------------------------------------------------------------- 1 title
sl = new(dark=True, notes="""
Source environment: none (positioning slide). The hero image is the Command Center of the released app in the demo Splunk (localhost:18000), captured read-only on 2026-11-02.
Say: PulseForge lets you pick an incident, run it, and prove in Splunk what arrived. Today is a live walk-through of the released app on the lab Splunk, plus what is merged to main and not yet installed here.
Validation status: the app is the released package; browser-checked in the 2026-11-01 and 2026-11-02 acceptance runs.""")
tb(sl, 0.7, 1.5, 6.0, 0.4, "NETSPOUT PULSEFORGE", 16, True, RGBColor.from_string("7FC4D8"))
tb(sl, 0.7, 2.0, 6.0, 2.4, "Simulate the enterprise. Verify it in Splunk.", 44, True, WHITE, HEAD)
tb(sl, 0.7, 4.55, 5.8, 1.0, "A Splunk-native lab that generates telemetry for runnable incident scenarios and proves what was indexed.", 18, color=LINE)
tb(sl, 0.7, 6.5, 6.0, 0.3, "Live demonstration  ·  November 3, 2026", 14, color=LINE)
pic(sl, "01_command_center.png", 6.9, 1.6, 5.9, 3.93, "PulseForge Command Center in Splunk Web")
tag(sl, "LIVE DEMO ENVIRONMENT · released app", 6.9, 5.75, 3.4, TEAL)

# ---------------------------------------------------------------- 2 problem
sl = new("Realistic telemetry is hard to get on demand", notes="""
Source environment: none (framing slide, no product claims beyond positioning).
Say: three frictions every observability and security team knows. Incidents are rare and unsafe to rehearse. Detections and dashboards need the right fields and sequence, not random events. And lab data rarely tells you what is real, what is modeled and what actually reached Splunk. PulseForge is built around closing those three gaps.
Validation status: n/a.""")
cards = [("1", "Incidents are rare and unsafe to rehearse", "You cannot break production to test a dashboard, a runbook or a detection."),
         ("2", "Content needs data with the right shape", "Fields, sourcetypes and event order matter. Random samples do not exercise them."),
         ("3", "Lab data hides its provenance", "Teams cannot tell what is vendor-native, what is modeled, and what reached the index.")]
for i, (n, h, b) in enumerate(cards):
    x = 0.6 + i * 4.1; box(sl, x, 1.6, 3.9, 3.2, LIGHT)
    c = box(sl, x + 0.3, 1.9, 0.6, 0.6, TEAL, None, MSO_SHAPE.OVAL); tf = c.text_frame; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER; r = p.add_run(); r.text = n; r.font.size = Pt(22); r.font.bold = True; r.font.color.rgb = WHITE; r.font.name = BODY
    tb(sl, x + 0.3, 2.75, 3.3, 0.9, h, 22, True, NAVY, HEAD); tb(sl, x + 0.3, 3.6, 3.3, 1.1, b, 16, color=INK)
box(sl, 0.6, 5.2, 12.1, 1.4, NAVY)
tb(sl, 0.95, 5.35, 11.4, 1.0, "PulseForge answer: pick a runnable scenario, send labeled telemetry to Splunk, and count an event as indexed only when an independent search finds it.", 22, True, WHITE, HEAD, anchor=MSO_ANCHOR.MIDDLE)

# ---------------------------------------------------------------- 3 enables
sl = new("What PulseForge enables", source="Counts: demo engine /api/catalog (349 sourcetypes, 88 vendors); docs/SCENARIOS.md (372 defined and runnable on main); demo runbook (148 in the released app).", notes="""
Source environment: counts from the demo engine API on localhost:8091 (349 sourcetypes, 88 vendors, checked 2026-11-02) and docs/SCENARIOS.md on main (372 scenarios defined, 372 runnable).
Say: the app's own flow is Choose, Run, Observe, Correlate, Investigate. Be precise on counts: 372 is current main; the released app in this demo exposes 148 runnable scenarios. The 224 additional scenarios are on main, validated in an isolated lab, and not installed in this demo.
Validation status: counts are generated from registries and checked by tests; they are not a claim of vendor certification.""")
steps = [("Choose", "Find a scenario, sourcetype or dashboard in the Use Case Explorer."), ("Run", "Generate phased telemetry and deliver it through HEC or native protocols."),
         ("Observe", "Watch generated, accepted and indexed counts update live."), ("Investigate", "Pivot into Splunk Search and run-bound dashboards.")]
for i, (h, b) in enumerate(steps):
    x = 0.6 + i * 3.1; box(sl, x, 1.5, 2.9, 2.3, LIGHT)
    tb(sl, x + 0.25, 1.7, 2.4, 0.4, "0%d" % (i + 1), 14, True, ORANGE); tb(sl, x + 0.25, 2.1, 2.4, 0.5, h, 26, True, NAVY, HEAD); tb(sl, x + 0.25, 2.6, 2.4, 1.1, b, 15)
stats = [("349", "sourcetypes in the catalog"), ("88", "vendors"), ("372", "scenarios defined and runnable on main"), ("148", "runnable in the released app (this demo)")]
for i, (n, l) in enumerate(stats):
    x = 0.6 + i * 3.1; tb(sl, x, 4.3, 2.9, 1.0, n, 54, True, TEAL, HEAD); tb(sl, x, 5.3, 2.8, 0.8, l, 16, color=INK)

# ---------------------------------------------------------------- 4 mind map
sl = new("The application at a glance", source="Technical version: NetSpout_Application_Mindmap.png / .svg, editable source diagrams/mindmap_technical.mmd.", notes="""
Source environment: repository at main 3f2e63f. Every branch was checked against the code: the app (netspout/), the engine (backend/app, src/netspout_core), catalog files and the install guides.
Say: seven branches. Experience is the Splunk Web app. Catalog is what we can emit. Scenarios are the stories. Generate is the engine. Deliver is HEC and native protocols. Splunk is where it is searched and visualised. Operate is how you install it.
Be careful: the single-package installer shown in the Operate branch is experimental and not in the released install.
Validation status: diagram is documentation; the technical map lists the repo evidence per branch.""")
r = pic(sl, "../NetSpout_Application_Mindmap_Executive.png", 0.6, 1.3, 12.1, 5.0, "Executive mind map of PulseForge: experience, catalog, scenarios, generate, deliver, Splunk, operate", border=False)
tb(sl, 0.6, 6.45, 12.1, 0.5, "Seven branches. The single-package installer under Operate is experimental and not part of the released install.", 15, color=MUTE, italic=True, align=PP_ALIGN.CENTER)

# ---------------------------------------------------------------- 5 workflow
sl = new("One workflow, from choice to evidence", source="Diagram source: diagrams/workflow.mmd. Components: netspout_gateway (restmap.conf), engine /api/runs, delivery monitor.", notes="""
Source environment: architecture of the released app and engine on main; the demo Splunk (localhost:18000) and engine (localhost:8091) run this flow.
Say: nine steps. The two orange steps are the point. Step 6: HEC acknowledging a batch does not mean it is searchable. Step 8: the app reports indexed only when a separate Splunk search finds events carrying that run ID. That is why the counters you will see can lag, and why they can be trusted.
Validation status: this exact flow was exercised live on 2026-11-01 and rehearsed 2026-11-02 for NF-SEC-06-DDOS (820 generated, 820 accepted, 820 indexed).""")
r = pic(sl, "../NetSpout_End_to_End_Workflow.png", 0.6, 1.4, 12.1, 3.7, "Nine-step workflow: choose, configure, start run, engine, generate, deliver, monitor, verify, investigate", border=False)
for i, (h, b) in enumerate([("Splunk to engine", "The app talks to the engine through the netspout_gateway REST handler, so users stay inside Splunk Web."),
                            ("Delivered is not indexed", "HEC acknowledgement and indexing are separate events. The monitor shows both."),
                            ("Indexed means searched", "Only an independent search by run ID produces the indexed count.")]):
    x = 0.6 + i * 4.1; box(sl, x, 5.3, 3.9, 1.55, LIGHT); tb(sl, x + 0.25, 5.45, 3.4, 0.4, h, 17, True, ORANGE if i else TEAL, HEAD); tb(sl, x + 0.25, 5.9, 3.4, 0.9, b, 14)

# ---------------------------------------------------------------- 6 command center
SRC = "Source: demo Splunk localhost:18000, released app, captured 2026-11-02. "
sl = new("Command Center: one place to start", source=SRC + "Live demo environment.", notes="""
Source environment: demo Splunk (container netspout_phase4e_splunk, localhost:18000), released NetSpout PulseForge app, page /en-US/app/netspout/pulseforge_command_center. Captured 2026-11-02 by a read-only browser session as admin; nothing was changed.
Say: this is the app inside Splunk Web. The perspective tabs show honest status: NetOps is available, SecOps and Observability are partial, ITOps and Supply Chain are planned. The five-step strip is the workflow. The Telemetry trust panel is the provenance idea: native contract, Splunk contract, NetSpout schema.
Do not worry if the Runtime evidence panel says Splunk observation NOT AVAILABLE: that is the pre-run state of the page, before any run is observed.
Validation status: the page is the released app, browser-checked in the 2026-11-01 and 2026-11-02 acceptance runs.""")
numbered(sl, 0.6, 1.5, 4.6, [("Honest perspectives", "NetOps is available; SecOps and Observability are partial; others are labeled planned."), ("Two ways to begin", "Choose a scenario, or Quick generate for one sourcetype."),
                             ("The workflow, visible", "Choose, Run, Observe, Correlate, Investigate."), ("Telemetry trust", "Native, Splunk and NetSpout-schema contracts are labeled separately.")], 15)
r = pic(sl, "01_command_center.png", 5.45, 1.45, 7.4, 5.5, "PulseForge Command Center in Splunk Web")
callouts(sl, r, [(0.187, 0.287, 0.766, 0.054), (0.187, 0.371, 0.55, 0.264), (0.187, 0.653, 0.766, 0.143), (0.706, 0.812, 0.246, 0.19)])
tag(sl, "LIVE DEMO ENVIRONMENT · released app", 9.4, 1.1, 3.4)

# ---------------------------------------------------------------- 7 catalog
sl = new("Vendor and sourcetype catalog", source=SRC + "Catalog counts: engine /api/catalog, checked 2026-11-02.", notes="""
Source environment: demo Splunk, Use Case Explorer (/en-US/app/netspout/use_case_explorer), search term cloudtrail. Counts 349 sourcetypes and 88 vendors come from the demo engine API on localhost:8091. Generator tiers (159 native engine, 143 recorded sample replay, 47 with no generator yet) come from docs/reference/sourcetype_coverage.json on main.
Say: the catalog is searchable by title, vendor, sourcetype or MITRE ID. Searching cloudtrail returns dashboards, scenarios and sourcetypes together, each with its maturity label. 47 catalog sourcetypes have no generator yet, and the app says so rather than inventing data.
Validation status: the search result and labels are live in the demo; DATA_VALIDATED is the app's own dashboard maturity level.""")
numbered(sl, 0.6, 1.5, 4.6, [("Search across everything", "One box finds dashboards, scenarios and sourcetypes: 22 results for cloudtrail."), ("Maturity is visible", "Each result carries its recorded status, for example DASHBOARD_DATA_VALIDATED.")], 15)
for i, (n, l) in enumerate([("349", "sourcetypes"), ("88", "vendors")]):
    tb(sl, 0.6 + i * 2.3, 4.2, 2.1, 0.9, n, 48, True, TEAL, HEAD); tb(sl, 0.6 + i * 2.3, 5.1, 2.1, 0.4, l, 15)
tb(sl, 0.6, 5.65, 4.6, 1.2, "Generator tiers: 159 native engine, 143 recorded sample replay, 47 with no generator yet (shown as such, never faked).", 14, color=MUTE)
r = pic(sl, "02_catalog_cloudtrail.png", 5.45, 1.45, 7.4, 5.5, "Use Case Explorer search for cloudtrail")
callouts(sl, r, [(0.187, 0.607, 0.766, 0.058), (0.187, 0.676, 0.766, 0.152)])
tag(sl, "LIVE DEMO ENVIRONMENT · released app", 9.4, 1.1, 3.4)

# ---------------------------------------------------------------- 8 explorer
sl = new("Scenario Explorer: find a story to run", source=SRC + "Live demo environment.", notes="""
Source environment: demo Splunk, Use Case Explorer, search term volumetric DDoS. Captured 2026-11-02.
Say: this is the entry point for the live demo. Searching volumetric DDoS returns the dashboard and the scenario NF-SEC-06-DDOS. It is labeled RUNNABLE and independently indexed, and it notes that it is a NetFlow profile of SEC-P9-A-TRAFFIC-FLOOD. Click Open scenario workflow to configure it.
The counters at the top (372 operational, 365 security stories) are catalog entries, not all runnable in this demo. The released app here runs 148 scenarios; the explorer's own labels (RUNNABLE or catalog only) tell you which.
Validation status: NF-SEC-06-DDOS: 820 generated, 820 accepted, 820 indexed on five runs between 2026-11-01 and 2026-11-02; dashboard DASHBOARD_VISUALLY_VERIFIED.""")
numbered(sl, 0.6, 1.5, 4.6, [("Search and filter", "Type a title, vendor, sourcetype or MITRE ID; narrow by type and dashboard status."), ("Dashboard with evidence", "pf_NF-SEC-06-DDOS is marked DASHBOARD_VISUALLY_VERIFIED."),
                             ("Runnable scenario", "NF-SEC-06-DDOS, independently indexed. Open scenario workflow starts the demo."), ("Catalog counters", "Entries in the catalog, not a runnable count; each card is labeled.")], 15)
r = pic(sl, "03_scenario_explorer.png", 5.45, 1.45, 7.4, 5.5, "Use Case Explorer showing NF-SEC-06-DDOS volumetric DDoS scenario")
callouts(sl, r, [(0.187, 0.607, 0.766, 0.04), (0.187, 0.676, 0.766, 0.152), (0.187, 0.829, 0.766, 0.17), (0.741, 0.417, 0.212, 0.102, 1)])
tag(sl, "LIVE DEMO ENVIRONMENT · released app", 9.4, 1.1, 3.4)

# ---------------------------------------------------------------- 9 contracts
sl = new("Declarative scenario contracts", source="Lab validation of work merged to main (PR #4). Not installed in the demo environment. Evidence: docs/verification/evidence/scenario_contracts/.", notes="""
Source environment: isolated lab Splunk (docker splunk/splunk 10.2), NOT the demo environment. Screenshot: scenario service_provider_mixed, Engineer tab, run run-f8889be11f7b, captured 2026-11-02 during validation of PR #4 (merged to main as 3f2e63f). The demo Splunk runs the released app and does not have these dashboards.
Say: a contract is data, not code: shared nodes, ordered phases, and streams that bind a formatter to a node. Add a contract and you get a phased scenario with tags for run, scenario, phase and parent event. This scenario is MIXED: real Nokia SR-OS and Juniper Junos events plus modeled context.
Fidelity of the 224 contract scenarios: 10 vendor-native, 30 mixed, 184 modeled. Modeled means the labeled netspout:scenario:state schema; it is not vendor-authentic and the app labels it that way.
Validation status: 224/224 live-indexed in the lab (4,994 events accepted, 0 rejected); 224/224 dashboards pass Splunk's parser and return data; 24 rendered in a browser, 11 visually inspected. Do not present these as installed in this demo.""")
tag(sl, "LAB VALIDATION · on main, not installed in the demo", 0.6, 1.2, 4.9, ORANGE)
t = tb(sl, 0.6, 1.75, 4.7, 2.6, "", 15); tf = t.text_frame
para(tf, "", 16, first=True, space=6, runs=[("A contract declares", True, NAVY)])
for s in ("Shared nodes: name, type, IP", "Ordered phases (rounds)", "Streams: a formatter bound to a node, with per-phase parameters"): para(tf, "•  " + s, 15, space=4)
para(tf, "", 16, space=6, runs=[("Every event is tagged with", True, NAVY)]); para(tf, "•  run, scenario, phase, event and parent event IDs", 15, space=4)
for i, (n, l, c) in enumerate([("10", "vendor-native", TEAL), ("30", "mixed", TEAL), ("184", "modeled", ORANGE)]):
    tb(sl, 0.6 + i * 1.6, 4.75, 1.5, 0.8, n, 40, True, c, HEAD); tb(sl, 0.6 + i * 1.6, 5.55, 1.5, 0.4, l, 14)
tb(sl, 0.6, 6.05, 4.8, 0.9, "372 runnable on main = 148 released + 224 contract scenarios. Modeled events are labeled NetSpout schema, not vendor logs.", 13, color=MUTE)
r = pic(sl, "08_lab_contract_dashboard.png", 5.75, 1.5, 7.0, 5.45, "Lab dashboard for the mixed-vendor service provider contract scenario")
callouts(sl, r, [(0.01, 0.32, 0.49, 0.206), (0.01, 0.54, 0.98, 0.208), (0.02, 0.76, 0.97, 0.235)])
tb(sl, 0.6, 3.95, 4.7, 0.5, "Callouts: 1 phase story, 2 metric-index panels, 3 impact events", 12, color=ORANGE, italic=True)

# ---------------------------------------------------------------- 10 running
sl = new("Running a scenario with a live monitor", source="Source: demo Splunk, run run-563343473f86 captured 2026-11-01 (the same scenario was re-run 2026-11-02).", notes="""
Source environment: demo Splunk (localhost:18000), NF-SEC-06-DDOS, run run-563343473f86, captured 2026-11-01 from the live monitor. The same scenario was re-run on 2026-11-02 (run-41ff3797e6ad and run-cfcfd30d23f8), each 820 generated, 820 accepted, 820 indexed.
Say: the configure panel shows the run plan: phases traffic 100, syn-flood 560, udp-flood 160, 820 events, destination index idx_network_ops. Run scenario with live delivery monitor starts it. The monitor counts generated, HEC accepted, rejected and Indexed (verified); that last number comes from a search, not from HEC.
Live: you will start a fresh run; expect about 20 seconds end to end. The IPFIX over UDP checkbox is optional; the HEC path is what the monitor counts.
Validation status: 820/820/820 reconciled; collector evidence 820 exported = 820 decoded, 0 collector errors in the 2026-11-02 rehearsal.""")
numbered(sl, 0.6, 1.5, 4.6, [("Start the run", "One button: Run scenario with live delivery monitor."), ("Run state", "COMPLETED here; RUNNING while events are produced."),
                             ("Reconciled counts", "Generated 820, HEC accepted 820, rejected 0, pending 0."), ("Indexed (verified)", "820, confirmed by an independent search, not by HEC.")], 15)
r = pic(sl, "04_run_monitor.png", 5.45, 1.7, 7.4, 3.45, "Live delivery monitor showing 820 generated, 820 accepted and 820 indexed")
callouts(sl, r, [(0.36, 0.446, 0.209, 0.05), (0.882, 0.56, 0.077, 0.035, 1), (0.36, 0.69, 0.615, 0.195), (0.498, 0.816, 0.105, 0.068, 2)])
tag(sl, "LIVE DEMO ENVIRONMENT · released app", 9.4, 1.3, 3.4)
box(sl, 5.45, 5.4, 7.4, 1.4, LIGHT); tb(sl, 5.7, 5.55, 6.9, 1.1, "Phases: traffic (100)  →  syn-flood (560)  →  udp-flood (160)\nDestination: idx_network_ops · sourcetype netflow:collector", 16, False, NAVY, anchor=MSO_ANCHOR.MIDDLE)

# ---------------------------------------------------------------- 11 search
sl = new("The events, as Splunk indexed them", source=SRC + "Run run-cfcfd30d23f8, read-only search.", notes="""
Source environment: demo Splunk, Search & Reporting. Run run-cfcfd30d23f8 (2026-11-02 12:24 UTC). The search is read-only; a one-time Splunk product-usage notice appears for a first-time admin session and was hidden in this capture only.
SPL shown: index=idx_network_ops sourcetype="netflow:collector" netspout_scenario_id="NF-SEC-06-DDOS" netspout_run_id="run-cfcfd30d23f8" | head 8 | table _time src dest dest_port transport tcp_flags_text packets bytes netspout_phase netspout_run_id
Say: these are the actual indexed events. The netspout_phase column shows the story: traffic first, then syn-flood from many sources to a single destination, 192.0.2.80 on port 443. Source addresses are RFC 5737 documentation ranges; this is synthetic traffic and the dashboard says so.
Validation status: 820 events for this run in idx_network_ops, same count as generated and accepted.""")
numbered(sl, 0.6, 1.5, 4.6, [("Real SPL, real index", "Scoped by scenario ID and run ID in idx_network_ops."), ("Event count", "The count matches what the monitor reported."),
                             ("The story is in the data", "netspout_phase moves from traffic to syn-flood."), ("Tagged by run", "Every event carries netspout_run_id, so runs never mix.")], 15)
r = pic(sl, "05_search_events.png", 5.45, 1.55, 7.4, 3.1, "Splunk Search results of indexed NetFlow events for the DDoS scenario")
callouts(sl, r, [(0.0125, 0.214, 0.79, 0.098), (0.0125, 0.33, 0.285, 0.03), (0.755, 0.57, 0.115, 0.38, 2), (0.876, 0.512, 0.12, 0.44, 2)])
tag(sl, "LIVE DEMO ENVIRONMENT · released app", 9.4, 1.18, 3.4)
box(sl, 5.45, 4.95, 7.4, 1.85, LIGHT)
t = tb(sl, 5.7, 5.1, 6.9, 1.6, "", 13); tf = t.text_frame
para(tf, "", 15, first=True, space=4, runs=[("Safe to run live", True, NAVY)])
para(tf, 'index=idx_network_ops sourcetype="netflow:collector" netspout_scenario_id="NF-SEC-06-DDOS" | stats count by netspout_run_id', 12, color=INK, space=4, font="Courier New")
para(tf, "Seven runs of 820 flows each are indexed in this demo (2026-11-01 and 2026-11-02).", 13, color=MUTE, space=0)

# ---------------------------------------------------------------- 12 dashboard
sl = new("Dashboard Studio: a populated investigation", source=SRC + "Run run-cfcfd30d23f8, dashboard pf_NF-SEC-06-DDOS.", notes="""
Source environment: demo Splunk, dashboard pf_NF-SEC-06-DDOS (NetFlow / IPFIX menu), bound to run run-cfcfd30d23f8 via form.run_tok. URL: http://localhost:18000/en-US/app/netspout/pf_NF-SEC-06-DDOS?form.run_tok=run-cfcfd30d23f8&form.index_tok=idx_network_ops
Say: the question is on the page: where is the packet rate peaking, which protocols and TCP flags dominate, and which assets are targeted. Panels: packet rate with a peak of 61 packets/s for this run; 820 flows; 68.3% SYN-only flows; 258 distinct sources; one destination receiving SYN-only flows. SYN counts grow across the run; 192.0.2.80 is the main target; sources escalate over time. The Limits line is honest: synthetic flood patterns; flow data cannot prove loss of availability.
Numbers vary run to run (peak was 88 on the 2026-11-01 run); describe the shape, not the digits, if they differ.
Validation status: DASHBOARD_VISUALLY_VERIFIED in the app's maturity scale; panels searched and returned data on every one of the seven indexed runs checked during acceptance.""")
numbered(sl, 0.6, 1.5, 4.6, [("Run-bound", "Scenario run picker and index; every panel filters by run ID."), ("The headline numbers", "820 flows, 68.3% SYN-only, 258 distinct sources, one targeted destination."),
                             ("Who and how", "TCP flags over time, protocol mix, and targeted assets (192.0.2.80 leads)."), ("Escalation and evidence", "Distinct sources climb through the attack; click a source for flow evidence.")], 15)
r = pic(sl, "06_dashboard_ddos_full.png", 5.75, 1.4, 7.1, 5.6, "Dashboard Studio view of the volumetric DDoS scenario run")
callouts(sl, r, [(0.012, 0.05, 0.5, 0.045), (0.024, 0.4226, 0.95, 0.078), (0.024, 0.515, 0.95, 0.202), (0.024, 0.7317, 0.95, 0.181)])
tag(sl, "LIVE DEMO ENVIRONMENT · released app", 9.4, 1.05, 3.4)

# ---------------------------------------------------------------- 13 visualization
sl = new("NetFlow and metric visualization", source="Top: demo Splunk, run run-cfcfd30d23f8 (live demo environment). Bottom: isolated lab validation, not installed in the demo.", notes="""
Source environment: top image is the demo Splunk dashboard pf_NF-SEC-06-DDOS (released app, 2026-11-02). Bottom image is from the isolated lab Splunk during PR #4 validation (scenario service_provider_mixed, run run-f8889be11f7b): mstats panels reading the metric index. The demo Splunk has no metrics index, so metric dashboards cannot be shown live in this lab.
Say: NetFlow flows are events in an event index and show up as time series and rankings. Gauge metrics are different: they go to a metric index and are verified with mstats. We show the metric view from the lab to explain the design; it is not available in the demo environment.
Validation status: NetFlow panels live in the demo. mstats panels were validated in the lab for 224 contract scenarios (results returned data; 11 dashboards visually inspected). Known limits recorded in the evidence: byte counters dominate chart scale, and some time trends are single points.""")
tag(sl, "LIVE DEMO ENVIRONMENT · NetFlow events", 5.45, 1.15, 3.6, TEAL)
pic(sl, "07_ddos_kpis.png", 5.45, 1.55, 7.4, 2.25, "NetFlow packet rate chart and KPI tiles for the DDoS run")
tag(sl, "LAB VALIDATION · metric index (mstats)", 5.45, 4.0, 3.6, ORANGE)
pic(sl, "09_lab_metric_panels.png", 5.45, 4.4, 7.4, 1.6, "Lab mstats panels showing gauge metrics before, during and after an incident")
numbered(sl, 0.6, 1.5, 4.6, [("Flows are events", "Packet rate, TCP flags and targets come from netflow:collector events."), ("Gauges are metrics", "They go to a metric index and are read with mstats."),
                             ("Be explicit in the room", "The metric view is shown from lab validation. This demo Splunk has no metrics index.")], 15)

# ---------------------------------------------------------------- 14 evidence
sl = new("Deployment options, evidence and limits", source="Evidence: docs/INSTALL.md, docs/LIMITATIONS.md, docs/verification/evidence/. Counts are from main 3f2e63f.", notes="""
Source environment: repository at main 3f2e63f; install guides; validation evidence JSON files under docs/verification/evidence.
Say: three released ways to run: the Splunk app plus the engine tarball (verified end to end on Splunk Enterprise 10.2.7 in an isolated lab); the Docker evaluation stack (the Compose file validates; a clean-checkout run for this exact release has not been repeated); and the Splunk Cloud package with its own guide. A single-package installer exists as an experiment: it was validated once on Splunk 10.6.1.1 on AWS, is not merged and is not part of the released install.
Distinguish: 372 runnable on main; 148 previously validated in the released app; 224 newly activated by contracts, independently indexed in the lab (224/224). Dashboards: implemented 224, search-validated 224/224, rendered 24, visually inspected 11.
Limits to say out loud: 184 of the 224 new scenarios are modeled (not vendor logs); 47 catalog sourcetypes have no generator; the demo environment does not have the new scenarios; metric dashboards need a metric index.
Validation status: as stated per column.""")
cols = [("Deployment", TEAL, ["Released: Splunk app (netspout.spl) + engine tarball; verified on Splunk Enterprise 10.2.7 in an isolated lab", "Released: Docker evaluation stack; Compose file validates, clean-checkout run not repeated", "Released: netspout_cloud.spl, dashboards only; Splunk Cloud itself was not validated", "Experimental, not released: single-package installer (validated once on Splunk 10.6.1.1)"]),
        ("Evidence", NAVY, ["148 scenarios validated in the released app", "224 new scenarios: 224/224 independently indexed in the lab (4,994 events, 0 rejected)", "224/224 dashboards pass the Splunk parser and return data", "24 rendered in a browser, 11 visually inspected"]),
        ("Limits", ORANGE, ["184 of the 224 new scenarios are modeled, not vendor logs", "47 catalog sourcetypes have no generator yet", "This demo runs the released app; the new scenarios are on main, not installed here", "Metric dashboards need a metric index; the demo has none"])]
for i, (h, c, items) in enumerate(cols):
    x = 0.6 + i * 4.1; box(sl, x, 1.4, 3.9, 4.35, LIGHT); b = box(sl, x, 1.4, 3.9, 0.65, c, None); tf = b.text_frame; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER; r = p.add_run(); r.text = h; r.font.size = Pt(20); r.font.bold = True; r.font.color.rgb = WHITE; r.font.name = HEAD
    t = tb(sl, x + 0.25, 2.25, 3.4, 3.4, "", 16); tf = t.text_frame
    for j, s in enumerate(items): para(tf, "•  " + s, 16, first=(j == 0), space=10)
box(sl, 0.6, 5.95, 12.1, 0.95, NAVY)
tb(sl, 0.9, 6.0, 11.5, 0.85, "372 runnable on main = 148 in the released app + 224 declarative-contract scenarios. Say which one you are showing.", 20, True, WHITE, HEAD, anchor=MSO_ANCHOR.MIDDLE)

# ---------------------------------------------------------------- 15 close
sl = new(dark=True, notes="""
Source environment: demo Splunk localhost:18000 and engine localhost:8091.
Say: that was the story. Now the live demo. Five moves: open the Use Case Explorer, search volumetric DDoS, open the scenario workflow and run it, watch the monitor reach Indexed, then Search and the dashboard. If anything stalls, switch to the prepared run run-cfcfd30d23f8 which is already indexed; the dashboard URL is in the cheat sheet.
Close: PulseForge makes incidents repeatable and the evidence checkable. Invite questions; the Q&A section of the presenter script lists the expected ones.
Validation status: the same flow ran cleanly on 2026-11-01 and was rehearsed on 2026-11-02.""")
tb(sl, 0.7, 0.9, 6, 0.4, "LIVE DEMO", 16, True, RGBColor.from_string("7FC4D8"))
tb(sl, 0.7, 1.4, 6.2, 1.8, "Pick it. Run it. Prove it in Splunk.", 42, True, WHITE, HEAD)
steps = ["Explorer: search “volumetric DDoS”", "Open scenario workflow NF-SEC-06-DDOS", "Run with live monitor, wait for Indexed 820", "Splunk Search: the events by run ID", "Dashboard pf_NF-SEC-06-DDOS, run-bound"]
for i, s in enumerate(steps):
    y = 3.5 + i * 0.62; c = box(sl, 0.7, y, 0.42, 0.42, ORANGE, None, MSO_SHAPE.OVAL); tf = c.text_frame; tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0; tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER; r = p.add_run(); r.text = str(i + 1); r.font.size = Pt(14); r.font.bold = True; r.font.color.rgb = WHITE; r.font.name = BODY
    tb(sl, 1.3, y, 5.6, 0.42, s, 17, color=WHITE, anchor=MSO_ANCHOR.MIDDLE)
pic(sl, "06_dashboard_ddos_full.png", 7.6, 0.6, 5.1, 6.3, "Populated PulseForge dashboard", border=False)
tb(sl, 0.7, 6.75, 6, 0.3, "Questions?", 16, True, WHITE)

prs.core_properties.title = "NetSpout PulseForge Demo"; prs.core_properties.author = "NetSpout PulseForge"
out = H / "NetSpout_PulseForge_Demo.pptx"; prs.save(out); print("saved", out, N[0], "slides")
