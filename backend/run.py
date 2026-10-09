import os
import sys
import argparse
import uvicorn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_src_candidates = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"),
    "/opt/netspout-src",
    "/opt/splunk/etc/apps/netspout/bin",
    "/opt/splunk-etc/apps/netspout/bin",
]
for _candidate in _src_candidates:
    if os.path.isdir(_candidate) and _candidate not in sys.path:
        sys.path.insert(0, _candidate)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NetSpout Fast Simulation Engine")
    parser.add_argument("--host", default=os.environ.get("FAST_SIMULATION_HOST", "127.0.0.1"), help="Bind host")
    parser.add_argument("--port", type=int, default=int(os.environ.get("FAST_SIMULATION_PORT", "8081")), help="Bind port")
    parser.add_argument("--reload", action="store_true", default=False, help="Enable auto-reload")
    args = parser.parse_args()

    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload, log_level="info")
