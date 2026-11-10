"""The stream pacer holds the requested average rate: not below it (it used to lose every late tick) and not above it."""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for _p in (str(ROOT / "src"), str(ROOT / "backend")):
    if _p not in sys.path:
        sys.path.insert(0, _p)
from netspout_core.delivery_monitor import DeliveryRun, Item  # noqa: E402


def run(eps, n, send_s):
    def send():
        time.sleep(send_s)
        return "accepted", None
    r = DeliveryRun("t", "t", "t", "d", "i", [Item("s", None, send) for _ in range(n)], eps_limit=eps)
    t = time.monotonic()
    r.start().wait(30)
    return n / (time.monotonic() - t), r


def test_late_sends_are_made_up_so_the_average_is_the_requested_rate():
    rate, r = run(100, 100, 0.004)           # each send takes 40% of the 10 ms slot plus timer overshoot
    assert r.state == "COMPLETED" and r.counts["accepted"] == 100
    assert 94 <= rate <= 101, rate


def test_rate_never_exceeds_the_request():
    rate, _ = run(50, 50, 0)
    assert rate <= 51, rate
