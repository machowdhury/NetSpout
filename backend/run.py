import os
import sys
import argparse
import uvicorn

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
_src_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if os.path.isdir(_src_dir) and _src_dir not in sys.path:
    sys.path.insert(0, _src_dir)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="NetSpout Fast Simulation Engine")
    parser.add_argument("--host", default=os.environ.get("FAST_SIMULATION_HOST", "0.0.0.0"), help="Bind host")
    parser.add_argument("--port", type=int, default=int(os.environ.get("FAST_SIMULATION_PORT", "8081")), help="Bind port")
    parser.add_argument("--reload", action="store_true", default=False, help="Enable auto-reload")
    args = parser.parse_args()

    uvicorn.run("app.main:app", host=args.host, port=args.port, reload=args.reload, log_level="info")
