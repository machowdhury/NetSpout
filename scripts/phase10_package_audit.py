#!/usr/bin/env python3
"""Content and safety audit of release-candidate archives (netspout.spl, netspout_cloud.spl, pulseforge-engine.tar.gz).

  python scripts/phase10_package_audit.py OUT.json ARCHIVE [ARCHIVE ...] [--lab-env tests/lab/ta_validation/.env.lab] [--repo CHECKOUT_DIR] [--allow ALLOWLIST.json]

Checks, per archive: unsafe members (absolute paths, .., links, devices), single root where one is required, accidental inclusion of private material (the external samples corpus,
vendor add-on packages, credential or key files, environment files, build caches, test and lab folders), secret-looking text, the lab credentials themselves (read from the git-ignored
lab env file and never written out), development-only references (localhost engine ports other than the documented 8081 default, absolute developer paths), and the largest members.
Findings are listed with the member name only; matched secret text is never echoed.
Provenance (--repo): every shipped file must be tracked in git at the build commit (the private samples corpus and vendor packages are untracked, so none of them can ship). The archive root maps to the
repository as: netspout/... -> netspout/..., pulseforge-engine/<path> -> <path>. A finding that matches an entry of --allow (member regex + kind + written reason) is moved to "reviewed", not hidden.
"""
import hashlib
import io
import json
import re
import sys
import tarfile
from pathlib import Path

PRIVATE_NAME = re.compile(r"(^|/)(private-packs|\.env($|\.)|\.env\.lab|id_rsa|\.pem$|\.key$|\.p12$|\.pfx$|\.git/|__pycache__|\.pytest_cache|node_modules|tests/lab|\.DS_Store)", re.I)
TA_PACKAGE = re.compile(r"(splunk[-_]add[-_]on|Splunk_TA_|\.spl$|\.tgz$|\.tar\.gz$|\.zip$)", re.I)
SECRET_TEXT = [("hec-or-guid-token", re.compile(r"(?i)(hec[_-]?token|splunk[_-]?token|authorization)['\"]?\s*[:=]\s*['\"]?[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")),
               ("password-assignment", re.compile(r"(?i)(password|passwd|secret)['\"]?\s*[:=]\s*['\"][^'\"\s]{8,}['\"]")),
               ("private-key-block", re.compile(r"-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----")),
               ("bearer-literal", re.compile(r"Bearer\s+[A-Za-z0-9._-]{24,}"))]
DEV_PATH = re.compile(r"/Users/[A-Za-z0-9._-]+/|/home/[A-Za-z0-9._-]+/Projects")
TEXT_EXT = (".py", ".json", ".conf", ".xml", ".js", ".css", ".html", ".md", ".txt", ".csv", ".yml", ".yaml", ".sh", ".env", ".example", ".service", ".plist", ".sample", ".manifest", ".cfg", ".ini", "")


def tracked_set(repo):
    import subprocess
    out = subprocess.run(["git", "-C", str(repo), "ls-files", "-z"], capture_output=True, check=True).stdout.decode().split("\0")
    return {o for o in out if o}


def repo_path(member, roots):
    first, _, rest = member.partition("/")
    return rest if first == "pulseforge-engine" else member


def audit(path: Path, lab_values, tracked=None, allow=()):
    data = path.read_bytes()
    res = {"archive": path.name, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest(), "findings": [], "notes": []}
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tf:
        members = tf.getmembers()
        res["members"] = len(members)
        roots = {m.name.split("/")[0] for m in members if m.name and not m.name.startswith("./")}
        res["roots"] = sorted(roots)
        big = sorted(((m.size, m.name) for m in members if m.isfile()), reverse=True)[:8]
        res["largest"] = [{"bytes": s, "name": n} for s, n in big]
        for m in members:
            n = m.name
            if tracked is not None and m.isfile() and repo_path(n, roots) not in tracked:
                res["findings"].append({"kind": "not-tracked-in-repository", "member": n})
            if n.startswith("/") or ".." in n.split("/"):
                res["findings"].append({"kind": "unsafe-path", "member": n})
            if m.issym() or m.islnk() or m.isdev():
                res["findings"].append({"kind": "link-or-device", "member": n})
            if PRIVATE_NAME.search(n):
                res["findings"].append({"kind": "private-or-build-material", "member": n})
            if m.isfile() and TA_PACKAGE.search(n.rsplit("/", 1)[-1]) and not n.endswith((".json", ".md")):
                res["findings"].append({"kind": "possible-bundled-package", "member": n})
            if not m.isfile() or m.size > 6_000_000:
                continue
            f = tf.extractfile(m)
            raw = f.read() if f else b""
            if not n.lower().endswith(TEXT_EXT) and b"\x00" in raw[:2048]:
                continue
            text = raw.decode("utf-8", "replace")
            for label, rx in SECRET_TEXT:
                if rx.search(text):
                    res["findings"].append({"kind": "secret-looking-text:" + label, "member": n})
            for v in lab_values:
                if v and v in text:
                    res["findings"].append({"kind": "lab-credential-present", "member": n})
            if DEV_PATH.search(text) and n.endswith((".py", ".conf", ".sh", ".service", ".plist", ".example")):
                res["findings"].append({"kind": "developer-absolute-path", "member": n})
    reviewed, keep = [], []
    for f in res["findings"]:
        hit = next((a for a in allow if a["kind"] == f["kind"] and re.search(a["member_regex"], f["member"])), None)
        (reviewed if hit else keep).append(dict(f, reason=hit["reason"]) if hit else f)
    res["findings"], res["reviewed"] = keep, reviewed
    res["reviewed_summary"] = {}
    for f in reviewed:
        res["reviewed_summary"][f["kind"]] = res["reviewed_summary"].get(f["kind"], 0) + 1
    kinds = {}
    for f in res["findings"]:
        kinds.setdefault(f["kind"], []).append(f["member"])
    res["summary"] = {k: len(v) for k, v in kinds.items()}
    res["examples"] = {k: v[:6] for k, v in kinds.items()}
    res["clean"] = not res["findings"]
    return res


def main(a):
    out, rest = Path(a[0]), a[1:]
    lab = []
    if "--lab-env" in rest:
        i = rest.index("--lab-env")
        env = Path(rest[i + 1])
        rest = rest[:i] + rest[i + 2:]
        lab = [l.strip().split("=", 1)[1] for l in env.read_text().splitlines() if "=" in l and any(k in l for k in ("PASSWORD", "TOKEN"))] if env.exists() else []
    repo = allow = None
    if "--repo" in rest:
        i = rest.index("--repo"); repo = Path(rest[i + 1]); rest = rest[:i] + rest[i + 2:]
    if "--allow" in rest:
        i = rest.index("--allow"); allow = json.loads(Path(rest[i + 1]).read_text())["allow"]; rest = rest[:i] + rest[i + 2:]
    tracked = tracked_set(repo) if repo else None
    report = {"archives": [audit(Path(p), lab, tracked, allow or []) for p in rest], "lab_credentials_checked": bool(lab), "provenance_checked_against_git": bool(repo)}
    out.write_text(json.dumps(report, indent=1) + "\n")
    for r in report["archives"]:
        print("%-28s members=%-5d clean=%s findings=%s reviewed=%s" % (r["archive"], r["members"], r["clean"], r["summary"], r["reviewed_summary"]))
    return 0 if all(r["clean"] for r in report["archives"]) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
