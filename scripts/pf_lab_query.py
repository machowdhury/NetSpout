#!/usr/bin/env python3
"""Splunk lab query helpers for PulseForge Phase 4C acceptance.

Everything here is read-only. Credentials come from the environment only;
nothing is hardcoded and nothing is scraped from the lab container (§3.6 of
docs/verification/pulseforge_phase4c_recovery.md).
"""
from __future__ import annotations

import base64
import json
import os
import ssl
import urllib.error
import urllib.parse
import urllib.request

MGMT = os.environ.get("PF_MGMT", "https://127.0.0.1:18089")
HEC = os.environ.get("PF_HEC_URL", "https://127.0.0.1:18088/services/collector")

_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE


def spl_admin():
    """Return (user, password) for the authorized lab search API.

    Resolution order is environment-first, and the credential is never scraped
    from the container:

    1. ``NETSPOUT_SPLUNK_PASSWORD`` -- the documented NetSpout/Splunk-app
       convention used by ``docs/QUICKSTART.md`` and ``docs/SECURITY.md``.
    2. ``SPLUNK_PASSWORD`` -- the name the sanitized scripts and the gitignored
       lab env file use.

    A previous version fell back to ``docker exec pf-native-lab printenv
    SPLUNK_PASSWORD``. That is wrong in a way that only appears after a
    password rotation: the container variable is the *build-time* value read
    once by the entrypoint, and changing the Splunk account through Splunk's
    own authentication layer never updates it. The scrape therefore quietly
    resurrects the retired credential and produces a baffling HTTP 401 while
    the real, current credential is sitting in the environment. Docker is a
    development harness here, not the source of truth for who can log in, so a
    missing variable must be an error the operator can act on.
    """
    user = os.environ.get("NETSPOUT_SPLUNK_USER") or os.environ.get("SPLUNK_USER") or "admin"
    pw = os.environ.get("NETSPOUT_SPLUNK_PASSWORD") or os.environ.get("SPLUNK_PASSWORD") or ""
    if not pw:
        raise RuntimeError(
            "Splunk management credentials are not configured: set "
            "NETSPOUT_SPLUNK_PASSWORD (or SPLUNK_PASSWORD) in the environment. "
            "The lab container's own SPLUNK_PASSWORD is intentionally not used, "
            "because it is the build-time value and stays stale after a "
            "password rotation."
        )
    return user, pw


def lab_hec_token():
    tok = os.environ.get("PULSEFORGE_LAB_HEC_TOKEN", "")
    if not tok:
        raise RuntimeError("PULSEFORGE_LAB_HEC_TOKEN is not set")
    return tok


def _auth_header():
    user, pw = spl_admin()
    return "Basic " + base64.b64encode(f"{user}:{pw}".encode()).decode()


def run_spl(spl, earliest="-2h@h", latest="now", timeout=200):
    """Synchronous read-only search. Works for both SPL and `| mstats`.

    Returns a list of result-row dicts. Raises on FATAL search messages.
    """
    if not (spl.lstrip().startswith("|") or spl.lstrip().startswith("search ")):
        spl = "search " + spl
    data = urllib.parse.urlencode({
        "search": spl, "output_mode": "json",
        "earliest_time": earliest, "latest_time": latest}).encode()
    req = urllib.request.Request(f"{MGMT}/services/search/jobs/export", data=data,
                                 headers={"Authorization": _auth_header()})
    try:
        body = urllib.request.urlopen(req, context=_CTX, timeout=timeout).read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"SPL dispatch failed ({exc.code}): {exc.read().decode()[:400]}") from exc
    rows = []
    for line in body.splitlines():
        line = line.strip().rstrip(",")
        if not line or line in ("{", "}", '"results": [', '"results":', "],", '""'):
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(d, dict):
            continue
        if d.get("messages"):
            fatal = [m for m in d["messages"] if m.get("type") == "FATAL"]
            if fatal:
                raise RuntimeError("search FATAL: " + "; ".join(m.get("text", "") for m in fatal))
            continue
        rows.append(d.get("result", d))
    return rows


def metric_names_from_mstats(rows):
    """Collect the distinct metric names returned by an `mstats avg(*)` row set."""
    names = set()
    for r in rows:
        for k in r:
            if k.startswith("avg(") and k.endswith(")"):
                names.add(k[4:-1])
    return sorted(names)


def count_metric_points(rows):
    return sum(
        1 for r in rows for k in r
        if k.startswith("avg(") and k.endswith(")") and r[k] not in (None, "")
    )
