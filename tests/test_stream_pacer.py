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


def test_a_stall_is_not_followed_by_a_catch_up_burst():
    stamps, first = [], [True]

    def send():
        stamps.append(time.monotonic())
        if first[0]:
            first[0] = False
            time.sleep(0.6)                  # a long stall: the missed 30 slots must not be replayed at full speed
        return "accepted", None
    r = DeliveryRun("t", "t", "t", "d", "i", [Item("s", None, send) for _ in range(120)], eps_limit=50)
    r.start().wait(30)
    worst = max(sum(1 for u in stamps if t <= u < t + 1.0) for t in stamps)
    assert worst <= 50 + 5 + 2, worst        # request + _MAX_CATCHUP_S worth of events (+ rounding)


def test_no_one_second_window_exceeds_the_request_with_jittery_sends():
    import random
    rnd, stamps = random.Random(7), []

    def send():
        stamps.append(time.monotonic())
        time.sleep(rnd.choice([0, 0, 0.001, 0.004, 0.012, 0.03]))     # irregular latency, some sends longer than the 20 ms slot
        return "accepted", None
    eps = 50
    r = DeliveryRun("t", "t", "t", "d", "i", [Item("s", None, send) for _ in range(200)], eps_limit=eps)
    r.start().wait(30)
    worst = max(sum(1 for u in stamps if t <= u < t + 1.0) for t in stamps)
    assert worst <= eps + 0.1 * eps + 2, worst      # sliding window: request + at most _MAX_CATCHUP_S of recovery
    assert len(stamps) / (stamps[-1] - stamps[0]) <= eps * 1.05
