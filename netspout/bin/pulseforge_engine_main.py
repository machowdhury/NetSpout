"""
PulseForge engine bootstrap for the Splunk-managed (single-package) architecture. Phase 1 prototype.

Runs under whichever Python launches it (Splunk's bundled Python when started by the launcher). Third-party packages are taken from
a vendored directory inside the app (bin/lib/<tag>), so no virtual environment or pip is needed. The listener is private by
construction: a Unix socket (mode 0600) or 127.0.0.1; any other host is refused. In the managed architecture a gateway key is
mandatory: without one this process exits instead of serving an unauthenticated API.

    python pulseforge_engine_main.py --uds <path>      (managed engine)
    python pulseforge_engine_main.py --port <port>     (loopback TCP, for tests and developers)
"""
import argparse
import os
import platform
import signal
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent


def platform_tag():
    """e.g. py313-linux-x86_64: the directory name under bin/lib holding wheels built for this interpreter and platform."""
    return "py%d%d-%s-%s" % (sys.version_info[0], sys.version_info[1], platform.system().lower(), platform.machine().lower())


def bootstrap_paths():
    """Put the vendored dependencies and the engine sources on sys.path; returns the entries added (for diagnostics and tests)."""
    added = []
    for p in (HERE / "lib" / platform_tag(), HERE / "engine", HERE.parent.parent / "backend", HERE.parent.parent / "src"):
        if p.is_dir() and str(p) not in sys.path:
            sys.path.insert(0, str(p))
            added.append(str(p))
    return added


def exit_when_orphaned(parent_pid, poll=2.0):
    """splunkd does not restart a launcher that is killed (observed on Splunk 10.6.1.1), and a surviving engine would be an unsupervised orphan
    that a later launcher could duplicate; so the engine shuts itself down gracefully (SIGTERM) as soon as its launcher is gone."""
    def watch():
        while os.getppid() == parent_pid:
            time.sleep(poll)
        os.kill(os.getpid(), signal.SIGTERM)
    threading.Thread(target=watch, daemon=True).start()


def main(argv=None):
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--uds", help="Unix socket path (preferred: no TCP port)")
    g.add_argument("--port", type=int, help="loopback TCP port")
    ap.add_argument("--host", default="127.0.0.1", help="refused unless loopback")
    a = ap.parse_args(argv)
    if a.host not in ("127.0.0.1", "::1", "localhost"):
        print("pulseforge-engine: refusing to listen on %s; the managed engine is loopback or socket only" % a.host, file=sys.stderr)
        return 2
    os.environ["PULSEFORGE_REQUIRE_GATEWAY_KEY"] = "1"
    if not os.environ.get("PULSEFORGE_GATEWAY_KEY"):
        print("pulseforge-engine: PULSEFORGE_GATEWAY_KEY is required in the managed architecture; not starting", file=sys.stderr)
        return 2
    bootstrap_paths()
    os.umask(0o077)  # the socket and any state file this process creates are private to the Splunk user
    import uvicorn
    from app.main import app
    if a.uds:
        # uvicorn chmods a socket it creates itself to 0666; bind it here at 0600 and hand it over as a file descriptor
        import socket
        if os.path.exists(a.uds):
            os.unlink(a.uds)
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.bind(a.uds)
        os.chmod(a.uds, 0o600)
        sock.listen(128)
        kwargs = {"fd": sock.fileno()}
    else:
        kwargs = {"host": a.host, "port": a.port}
    if a.uds:
        exit_when_orphaned(os.getppid())
    uvicorn.run(app, log_level="warning", **kwargs)  # uvicorn turns SIGTERM into a graceful shutdown (runs the app's lifespan exit)
    return 0


if __name__ == "__main__":
    sys.exit(main())
