# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/cisco_sample_provider.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""
NetSpout Cisco Sample Provider
Provides real Cisco log samples extracted from production telemetry captures.
"""

import os
import random
import time
import re

def _find_samples_dir():
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples"),
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "netspout", "samples"),
        "/opt/splunk/etc/apps/netspout/samples",
        "/opt/splunk/etc/apps/TA-network-data-blaster/samples"
    ]
    for c in candidates:
        if os.path.isdir(c):
            return c
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "samples")

SAMPLES_DIR = _find_samples_dir()

_CACHE = {}

def get_available_sourcetypes():
    if not os.path.exists(SAMPLES_DIR):
        return []
    files = [f for f in os.listdir(SAMPLES_DIR) if f.endswith(".sample") or f.endswith(".log")]
    sourcetypes = []
    for f in files:
        st = f.replace(".sample", "").replace(".log", "").replace("_", ":")
        sourcetypes.append(st)
    return sorted(sourcetypes)

def get_sample_lines(sourcetype: str, max_lines: int = 50):
    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', sourcetype)
    candidates = [
        f"{safe_name}.sample",
        f"{safe_name}.log",
        f"{sourcetype}.sample",
        f"{sourcetype}.log"
    ]
    
    if safe_name in _CACHE:
        lines = _CACHE[safe_name]
        return random.sample(lines, min(len(lines), max_lines)) if lines else []

    sample_file = None
    for cand in candidates:
        p = os.path.join(SAMPLES_DIR, cand)
        if os.path.exists(p):
            sample_file = p
            break

    if not sample_file:
        return []

    try:
        with open(sample_file, "r", encoding="utf-8", errors="ignore") as fp:
            lines = [l.strip() for l in fp if l.strip()]
        _CACHE[safe_name] = lines
        return random.sample(lines, min(len(lines), max_lines)) if lines else []
    except Exception:
        return []

def get_sample_event(sourcetype: str):
    lines = get_sample_lines(sourcetype, max_lines=5)
    if lines:
        return random.choice(lines)
    return None
