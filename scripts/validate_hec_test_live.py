#!/usr/bin/env python3
"""Live check of the External HEC Connection Test against the isolated Docker lab only (never Splunk Cloud, never the demo lab).
Valid and allowlist cases go through the running engine (saved destination); failure cases run the same code in-process against deliberately wrong settings.
Credentials come from the git-ignored tests/lab/ta_validation/.env.lab and are never printed or written. Evidence: docs/verification/evidence/monitor/hec_test.json"""
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
import validate_ta_windows as lab  # noqa: E402
from netspout_core.hec_connection_test import run_test  # noqa: E402

ENGINE = os.environ.get("NETSPOUT_ENGINE", "http://127.0.0.1:8091")
TOKEN, PASSWORD = lab.ENV["LAB_HEC_TOKEN"], lab.ENV["LAB_SPLUNK_PASSWORD"]
BASE = {"hec_url": "https://127.0.0.1:%s/services/collector" % lab.ENV["LAB_HEC_PORT"], "deployment_mode": "DOCKER_LAB", "allow_insecure_tls": True}


def engine_test(index):
    req = urllib.request.Request(ENGINE + "/api/setup/test-connection", method="POST", data=json.dumps({"test_index": index}).encode(), headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read() or b"{}")


def brief(res):
    return {"overall": res["overall"], "statuses": res["statuses"], "error": res["error"], "steps": [(s["id"], s["status"]) for s in res["steps"]]}


def main():
    out, fast = {}, dict(connect_timeout=2.0, http_timeout=4.0, polls=1, interval=0.5)
    code, res = engine_test("dev_test_replay")
    out["valid_with_search"] = {"http": code, **brief(res)}
    code, res = engine_test("main")
    out["disallowed_index_via_engine"] = {"http": code, **brief(res)}
    marker = res["test_id"]
    rows = lab.search('search index=* "%s" | stats count' % marker, "-1h")
    out["disallowed_index_via_engine"]["events_found_anywhere"] = int((rows[0].get("count") if rows else 0) or 0)
    allowed = ["dev_test_replay", "dev_missing_index"]
    out["accepted_without_search"] = brief(run_test(BASE, TOKEN, "dev_test_replay", allowed, None, None, **fast))
    out["invalid_token"] = brief(run_test(BASE, "00000000-0000-0000-0000-000000000000", "dev_test_replay", allowed, None, None, **fast))
    out["unreachable"] = brief(run_test(dict(BASE, hec_url="https://127.0.0.1:1/services/collector"), TOKEN, "dev_test_replay", allowed, None, None, **fast))
    out["dns_failure"] = brief(run_test(dict(BASE, hec_url="https://hec.invalid/services/collector"), TOKEN, "dev_test_replay", allowed, None, None, **fast))
    out["tls_certificate_not_trusted"] = brief(run_test(dict(BASE, allow_insecure_tls=False), TOKEN, "dev_test_replay", allowed, None, None, **fast))
    # a nonexistent index that is on the allowlist: this lab HEC acknowledges the event (acceptance), but an independent search must not find it in that index
    out["accepted_but_not_indexed_missing_index"] = brief(run_test(BASE, TOKEN, "dev_missing_index", allowed, lambda q: (lab.search(q, "-15m"), None), "x", connect_timeout=2.0, http_timeout=4.0, polls=2, interval=3.0))
    blob = json.dumps(out)
    out["secret_leak_scan"] = {"hec_token_in_evidence": TOKEN in blob, "password_in_evidence": PASSWORD in blob}
    want = {"valid_with_search": ("FULLY_VERIFIED", None), "accepted_without_search": ("ACCEPTED_NOT_VERIFIED", None), "invalid_token": ("FAILED", "AUTH"), "unreachable": ("FAILED", "REFUSED"),
            "tls_certificate_not_trusted": ("FAILED", "TLS_CERTIFICATE"), "accepted_but_not_indexed_missing_index": ("ACCEPTED_NOT_VERIFIED", None)}
    for k, (overall, cat) in want.items():
        r = out[k]
        r["expected"] = {"overall": overall, "category": cat}
        r["ok"] = r["overall"] == overall and (cat is None or (r["error"] or {}).get("category") == cat or cat in json.dumps(r["error"]))
    out["disallowed_index_via_engine"]["ok"] = out["disallowed_index_via_engine"]["error"]["category"] == "INDEX_NOT_ALLOWED" and out["disallowed_index_via_engine"]["events_found_anywhere"] in (0, None)
    out["dns_failure"]["ok"] = out["dns_failure"]["overall"] == "FAILED"
    OUT = ROOT / "docs/verification/evidence/monitor/hec_test.json"
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"generated_utc": datetime.now(timezone.utc).isoformat(), "destination": "isolated Docker lab (loopback)", "cases": out}, indent=1) + "\n")
    for k, v in out.items():
        if k != "secret_leak_scan":
            print(("PASS " if v.get("ok") else "FAIL ") + k + ("" if v.get("ok") else " " + json.dumps(v)[:500]))
    print("leak scan", out["secret_leak_scan"])


main()
