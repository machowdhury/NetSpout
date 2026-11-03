# Renders diagrams/*.mmd to the PNG/SVG files next to this script (needs playwright + network for mermaid@11.4.1 from jsdelivr). python render_diagrams.py
import sys, pathlib
from playwright.sync_api import sync_playwright
D=pathlib.Path(__file__).parent/"diagrams"; jobs=[("mindmap_technical","NetSpout_Application_Mindmap",{"fontSize":20}),("mindmap_executive","NetSpout_Application_Mindmap_Executive",{"fontSize":24}),("workflow","NetSpout_End_to_End_Workflow",{"fontSize":18})]
with sync_playwright() as p:
    b=p.chromium.launch(); pg=b.new_context(device_scale_factor=3,viewport={"width":2400,"height":1400}).new_page()
    pg.goto("file://"+str((pathlib.Path(__file__).parent/"diagrams"/"render.html").resolve())); pg.wait_for_function("window.mermaid",timeout=60000)
    for src,out,cfg in jobs:
        txt=(D/(src+".mmd")).read_text()
        svg=pg.evaluate("""async ([t,fs])=>{mermaid.initialize({startOnLoad:false,theme:'base',securityLevel:'loose',themeVariables:{fontFamily:'Arial',fontSize:fs+'px',primaryColor:'#e6f2f5',primaryTextColor:'#0b2e3b',lineColor:'#0b3b4f'},mindmap:{padding:18,maxNodeWidth:260},flowchart:{htmlLabels:true,wrappingWidth:600,padding:22,nodeSpacing:40,rankSpacing:60,useMaxWidth:false}});
          const r=await mermaid.render('g'+Math.random().toString(36).slice(2),t); document.getElementById('o').innerHTML=r.svg; return r.svg}""",[txt,cfg["fontSize"]])
        pathlib.Path(out+".svg").write_text(svg)
        pg.locator("#o svg").screenshot(path=out+".png",omit_background=False)
        print(out, len(svg))
    b.close()
