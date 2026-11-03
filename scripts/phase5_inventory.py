#!/usr/bin/env python3
"""Phase 5: read-only inventory of EVERY regular file in the private-packs directory.

  python scripts/phase5_inventory.py [PACKS_DIR] [OUT.json]

Nothing is extracted to disk and nothing inside a package is executed (see ta_inventory.read_package for the archive guards). The output is derived metadata only:
identity, hashes, classification, sourcetypes with file:stanza references, ingestion signals. No configuration text (regexes, searches) is copied out of the packages.
Files are deduplicated by SHA-256 (byte-identical copies) and by app identity (id + version); every original file keeps its own row.
"""
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts")]
from ta_inventory import UnsafeArchive, app_roots, inventory_app, read_package, sha256_file  # noqa: E402

PACKS = Path("~/netspout/private-packs").expanduser()
OUT = ROOT / "docs/verification/evidence/ta_inventory/all_packages.json"


def package_type(app):
    c = " ".join(app["classification"])
    parts = [k for k, t in (("TA", "TA (parsing"), ("sourcetype definitions", "sourcetype definitions"), ("modular input", "modular input"), ("collector", "network collector"), ("app UI", "app UI")) if t in c]
    if not parts:
        return "unclassified"
    return parts[0] if len(parts) == 1 else "mixed (" + ", ".join(parts) + ")"


def inspect(path):
    rec = {"filename": path.name, "bytes": path.stat().st_size, "sha256": sha256_file(path), "status": "INSPECTED", "reason": None, "apps": []}
    try:
        files, st = read_package(str(path))
        rec["archive_safety"] = st
        for r in app_roots(files):
            a = inventory_app(files, r)
            a["package_type"] = package_type(a)
            rec["apps"].append(a)
        if not rec["apps"]:
            rec["status"], rec["reason"] = "NO_APP_FOUND", "archive read, but no default/app.conf or app.manifest"
    except UnsafeArchive as exc:
        rec["status"], rec["reason"] = "FAILED_SAFETY_GUARD", str(exc)
    except Exception as exc:  # corrupt or non-archive file: reported with its reason, never hidden
        rec["status"], rec["reason"] = "FAILED_UNREADABLE", "%s: %s" % (type(exc).__name__, str(exc)[:200])
    return rec


def main(packs=PACKS, out=OUT):
    paths = sorted(p for p in packs.rglob("*") if p.is_file() and not p.is_symlink())
    skipped_links = sum(1 for p in packs.rglob("*") if p.is_symlink())
    with ThreadPoolExecutor(4) as ex:
        res = list(ex.map(inspect, paths))
    for r, p in zip(res, paths):
        r["path"] = str(p.relative_to(packs))
    seen = {}
    for r in res:
        r["duplicate_of"] = seen.get(r["sha256"])
        seen.setdefault(r["sha256"], r["path"])
    ids = {}
    for r in res:
        for a in r["apps"]:
            ids.setdefault((a["id"], a["version"]), []).append(r["path"])
    summary = {"files_found": len(res), "symlinks_skipped": skipped_links, "inspected": sum(r["status"] == "INSPECTED" for r in res), "failed": sum(r["status"].startswith("FAILED") for r in res),
               "no_app_found": sum(r["status"] == "NO_APP_FOUND" for r in res), "byte_identical_duplicates": sum(1 for r in res if r["duplicate_of"]), "unique_files_by_sha256": len(seen),
               "distinct_app_identities_id_version": len(ids), "distinct_app_ids": len({k[0] for k in ids}), "total_bytes": sum(r["bytes"] for r in res)}
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps({"summary": summary, "packages": res}, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    for r in res:
        if r["status"] != "INSPECTED":
            print(r["status"], r["path"], r["reason"])
    return 0


if __name__ == "__main__":
    a = sys.argv[1:]
    sys.exit(main(Path(a[0]).expanduser() if a else PACKS, a[1] if len(a) > 1 else OUT))
