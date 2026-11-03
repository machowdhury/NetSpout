#!/usr/bin/env python3
"""Read-only inventory of Splunk add-on packages (.spl, .tgz, .tar.gz). Nothing is extracted to disk and nothing inside a package is executed.

Archive members are read in memory. Absolute paths, '..' components, links and devices are counted and skipped; only small configuration members are read.
The output records identity, classification, sourcetypes and file:stanza references. It does not copy configuration text (regexes, searches) out of the packages.

  python scripts/ta_inventory.py [PACKS_DIR] [OUT.json] [--all]

By default only the 14 packages named in the Phase 4 task are inventoried; other files in the directory are ignored. --all inventories every archive in it.
"""
import hashlib
import json
import re
import sys
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts")]
from ta_compat import parse_conf  # noqa: E402

MAX_MEMBER = 8 * 1024 * 1024
MAX_MEMBERS = 250000                 # archive-bomb guards: a package past any of these is reported as FAILED_SAFETY and not read further
MAX_DECLARED_BYTES = 12 * 1024 ** 3  # sum of the sizes the archive headers declare (the largest real package here declares well under this)
MAX_CONFIG_TOTAL = 96 * 1024 * 1024  # bytes of configuration text held in memory for one package
PHASE4_PACKAGES = ("arista-networks-telemetry-for-splunk_202.tgz", "cisco-enterprise-networking-add-on-for-splunk_4060.tgz", "cisco-enterprise-networking-netflow-add-on-for-splunk_400.tgz",
                   "cisco-intersight-add-on-for-splunk_322.spl", "cisco-meraki-add-on-for-splunk_350.tgz", "cisco-secure-access-add-on-for-splunk_1057.tar.gz", "cisco-security-cloud_373.tar.gz",
                   "cisco-thousandeyes-app-for-splunk_090.tar.gz", "fortinet-fortigate-add-on-for-splunk_1610.tar.gz", "splunk-add-on-for-cisco-asa_612.spl", "splunk-add-on-for-cisco-esa_180.spl",
                   "splunk-add-on-for-cisco-wsa_500.tgz", "splunk-add-on-for-juniper_161.spl", "splunk-add-on-for-palo-alto-networks_400.spl")
WANT = ("app.conf", "web.conf", "limits.conf", "collections.conf", "data_models.conf", "props.conf", "transforms.conf", "inputs.conf", "eventtypes.conf", "tags.conf", "indexes.conf", "app.manifest", "inputs.conf.spec", "restmap.conf",
        "datamodels.conf", "macros.conf", "savedsearches.conf", "authorize.conf", "default.meta", "README.txt", "readme.txt", "README.md", "alert_actions.conf")
_SPECIAL = re.compile(r"^(source::|host::|rule::|delayedrule::)")


def _safe(name):
    p = PurePosixPath(name)
    return not (p.is_absolute() or ".." in p.parts or name.startswith(("/", "\\")))


class UnsafeArchive(Exception):
    pass


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(chunk), b""):
            h.update(b)
    return h.hexdigest()


def _wanted(base):
    return base in WANT or base.endswith(".conf.spec")


def read_package(path):
    """-> (files: {member: text} for small config members, stats). Unsafe members are skipped and counted, never read. Nothing is written to disk.
    Raises UnsafeArchive when a bomb guard trips (too many members, too much declared size, too much config text)."""
    files, st = {}, {"members": 0, "unsafe_path": 0, "links_or_devices": 0, "oversize_config": 0, "pickled_or_binary_not_read": 0, "declared_bytes": 0, "config_bytes_read": 0, "format": None}

    def take(name, size, reader):
        base = name.rsplit("/", 1)[-1]
        if not _wanted(base):
            st["pickled_or_binary_not_read"] += 1
            return
        if size > MAX_MEMBER:
            st["oversize_config"] += 1
            return
        data = reader()
        st["config_bytes_read"] += len(data)
        if st["config_bytes_read"] > MAX_CONFIG_TOTAL:
            raise UnsafeArchive("configuration members exceed %d bytes" % MAX_CONFIG_TOTAL)
        files[name] = data.decode("utf-8", "replace")

    def count(size):
        st["members"] += 1
        st["declared_bytes"] += max(size, 0)
        if st["members"] > MAX_MEMBERS:
            raise UnsafeArchive("more than %d members" % MAX_MEMBERS)
        if st["declared_bytes"] > MAX_DECLARED_BYTES:
            raise UnsafeArchive("declared size exceeds %d bytes" % MAX_DECLARED_BYTES)

    if zipfile.is_zipfile(path):
        st["format"] = "zip"
        with zipfile.ZipFile(path) as zf:
            for i in zf.infolist():
                count(i.file_size)
                if not _safe(i.filename):
                    st["unsafe_path"] += 1
                elif i.is_dir():
                    continue
                elif (i.external_attr >> 16) & 0o170000 == 0o120000:
                    st["links_or_devices"] += 1
                else:
                    take(i.filename, i.file_size, lambda i=i: zf.open(i).read(MAX_MEMBER + 1))
        return files, st
    st["format"] = "tar"
    with tarfile.open(path) as tf:
        for m in tf:
            count(m.size)
            if not _safe(m.name):
                st["unsafe_path"] += 1
                continue
            if m.issym() or m.islnk() or m.isdev() or m.isfifo():
                st["links_or_devices"] += 1
                continue
            if m.isfile():
                take(m.name, m.size, lambda m=m: tf.extractfile(m).read(MAX_MEMBER + 1))
    return files, st


def app_roots(files):
    roots = sorted({n.rsplit("/default/app.conf", 1)[0] for n in files if n.endswith("/default/app.conf")} | {n.rsplit("/app.manifest", 1)[0] for n in files if n.endswith("/app.manifest")})
    return [r for r in roots if r]


def _g(files, root, rel):
    return files.get("%s/%s" % (root, rel), "")


_README_SIGNALS = (("syslog", r"\bsyslog\b"), ("hec", r"HTTP Event Collector|\bHEC\b"), ("netflow_ipfix", r"net\s*flow|\bipfix\b"), ("sflow", r"\bsflow\b"), ("opentelemetry", r"open\s*telemetry|\botel\b"),
                   ("streaming_telemetry", r"streaming telemetry|\bgnmi\b|model[- ]driven telemetry"), ("snmp", r"\bsnmp\b"), ("cef", r"\bCEF\b"), ("rest_api", r"\bREST(ful)? API|\bAPI (key|token|endpoint)"),
                   ("cloud_pull", r"\bS3\b|\bSQS\b|Pub/?Sub|Event ?Hub|Kinesis|Azure Monitor"), ("database", r"\bJDBC\b|DB Connect"), ("universal_forwarder_files", r"\bmonitor stanza|\bUniversal Forwarder\b"))
_INPUT_KIND = (("monitor", "file monitoring"), ("udp", "syslog/network listener (udp)"), ("tcp", "syslog/network listener (tcp)"), ("splunktcp", "forwarder receiving"), ("http", "HEC input"),
               ("script", "scripted input"), ("WinEventLog", "Windows event log input"), ("perfmon", "Windows performance counters"), ("WinRegMon", "Windows registry monitor"), ("MonitorNoHandle", "Windows file monitor"))


def ingestion_signals(inputs, modinputs, readme, metric_sig, in_types):
    """Evidence-tagged ingestion mechanisms: 'config' = declared in inputs.conf/spec/props/indexes, 'readme' = only documented. Not a claim that the mechanism was exercised."""
    out = []
    kinds = dict(_INPUT_KIND)
    for t in in_types:
        if t in kinds:
            out.append({"mechanism": kinds[t], "basis": "config", "evidence": "default/inputs.conf:[%s://...]" % t})
    for m in modinputs:
        out.append({"mechanism": "modular input", "scheme": m, "basis": "config", "evidence": "README/inputs.conf.spec:[%s://]" % m})
    if metric_sig["metric_indexes"] or metric_sig["props_metric_schema"] or metric_sig["transforms_metric_schema"]:
        out.append({"mechanism": "metrics (metric index or metric schema)", "basis": "config", "evidence": "indexes.conf/props.conf/transforms.conf metric definitions"})
    for key, rx in _README_SIGNALS:
        if re.search(rx, readme, re.I):
            out.append({"mechanism": key, "basis": "readme", "evidence": "README text mentions it"})
    return out


def inventory_app(files, root):
    app = parse_conf(_g(files, root, "default/app.conf"))
    try:
        man = json.loads(_g(files, root, "app.manifest") or "{}")
    except ValueError:
        man = {}
    props, trans = parse_conf(_g(files, root, "default/props.conf")), parse_conf(_g(files, root, "default/transforms.conf"))
    inputs, evt, tags = parse_conf(_g(files, root, "default/inputs.conf")), parse_conf(_g(files, root, "default/eventtypes.conf")), parse_conf(_g(files, root, "default/tags.conf"))
    idx, spec = parse_conf(_g(files, root, "default/indexes.conf")), parse_conf(_g(files, root, "README/inputs.conf.spec"))
    readme = "\n".join(v for k, v in files.items() if k.startswith(root + "/") and k.rsplit("/", 1)[-1].lower().startswith("readme") and "README/" not in k)[:200000]

    sts = {}
    source_keyed = sum(1 for k in props if _SPECIAL.match(k))

    def add(name, kind, where):
        sts.setdefault(name, {"sourcetype": name, "declared_by": [], "props": None})["declared_by"].append({"kind": kind, "where": where})

    for stanza, kv in props.items():
        if stanza in ("default",) or _SPECIAL.match(stanza):
            continue
        add(stanza, "props.conf stanza", "default/props.conf:[%s]" % stanza)
        if "rename" in kv:
            add(kv["rename"], "props.conf rename target", "default/props.conf:[%s] rename" % stanza)
    for stanza, kv in trans.items():
        m = re.match(r"sourcetype::(.+)$", kv.get("FORMAT", ""))
        if kv.get("DEST_KEY") == "MetaData:Sourcetype" and m:
            add(m.group(1), "transforms.conf sourcetype override", "default/transforms.conf:[%s]" % stanza)
    for stanza, kv in inputs.items():
        if kv.get("sourcetype"):
            add(kv["sourcetype"], "inputs.conf sourcetype", "default/inputs.conf:[%s]" % stanza)
    for name, rec in sts.items():
        p = props.get(name)
        if p:
            keys = list(p)
            rec["props"] = {"stanza": "default/props.conf:[%s]" % name, "rename": p.get("rename"), "TIME_FORMAT": p.get("TIME_FORMAT"), "TIME_PREFIX": p.get("TIME_PREFIX"), "TZ": p.get("TZ"), "KV_MODE": p.get("KV_MODE"),
                            "SHOULD_LINEMERGE": p.get("SHOULD_LINEMERGE"), "LINE_BREAKER": bool(p.get("LINE_BREAKER")), "INDEXED_EXTRACTIONS": p.get("INDEXED_EXTRACTIONS"),
                            "report_transforms": sorted({n.strip() for k in keys if k.startswith("REPORT-") for n in p[k].split(",") if n.strip()}),
                            "extract_count": sum(k.startswith("EXTRACT-") for k in keys), "eval_count": sum(k.startswith("EVAL-") for k in keys),
                            "fieldalias_count": sum(k.startswith("FIELDALIAS-") for k in keys), "lookup_count": sum(k.startswith("LOOKUP-") for k in keys),
                            "index_time_transforms": sorted({n.strip() for k in keys if k.startswith("TRANSFORMS-") for n in p[k].split(",") if n.strip()}),
                            "metric_schema": [p[k] for k in keys if k.startswith("METRIC-SCHEMA-TRANSFORMS")]}
    # eventtypes referencing sourcetypes
    et_refs = {}
    for et, kv in evt.items():
        for s in re.findall(r"sourcetype\s*=\s*\"?([A-Za-z0-9_:.\-*]+)", kv.get("search", "")):
            et_refs.setdefault(s, []).append(et)
    for name, rec in sts.items():
        rec["eventtypes"] = sorted(et_refs.get(name, []))
    modinputs = sorted(k.split("://")[0] for k in spec if "://" in k)
    in_types = sorted({k.split("://")[0] if "://" in k else k for k in inputs if k not in ("default",)})
    metric_idx = sorted(k for k, v in idx.items() if v.get("datatype") == "metric")
    metric_sig = {"metric_indexes": metric_idx,
                  "props_metric_schema": sorted(n for n, r in sts.items() if r["props"] and r["props"]["metric_schema"]),
                  "transforms_metric_schema": sorted(k for k, v in trans.items() if any(x.startswith("METRIC") for x in v) or k.startswith("metric")),
                  "readme_mentions_metrics_index": bool(re.search(r"metrics?\s+index", readme, re.I))}
    has_bin = any(n.startswith(root + "/bin/") for n in files) or any("/bin/" in n for n in files if n.startswith(root + "/"))
    kinds = []
    if sts and (props or trans):
        kinds.append("TA (parsing/extraction)" if any(r["props"] and (r["props"]["report_transforms"] or r["props"]["extract_count"] or r["props"]["eval_count"]) for r in sts.values()) else "sourcetype definitions")
    if modinputs:
        kinds.append("modular input (%s)" % ", ".join(modinputs[:6]))
    if any(t in ("udp", "tcp", "splunktcp") for t in in_types) or re.search(r"net\s*flow|ipfix", readme, re.I) and "netflow" in str(root).lower():
        kinds.append("network collector input")
    if any("/data/ui/views/" in n or "/appserver/" in n for n in files if n.startswith(root + "/")) or _g(files, root, "default/data/ui/nav/default.xml"):
        kinds.append("app UI")
    manifest_deps = man.get("dependencies") or {}
    info = man.get("info", {})
    return {"root": root, "id": (app.get("package", {}) or {}).get("id") or (info.get("id") or {}).get("name") or app.get("id", {}).get("name") or root.rsplit("/", 1)[-1],
            "label": (app.get("ui", {}) or {}).get("label") or info.get("title"), "version": (app.get("launcher", {}) or {}).get("version") or (info.get("id") or {}).get("version") or (app.get("id", {}) or {}).get("version"),
            "classification": kinds or ["unclassified (no props/inputs/modular input)"], "conf_files_present": sorted({n.rsplit("/", 1)[-1] for n in files if n.startswith(root + "/")}),
            "sourcetypes": sorted(sts.values(), key=lambda r: r["sourcetype"]), "inputs": [{"stanza": k, "sourcetype": v.get("sourcetype"), "index": v.get("index")} for k, v in inputs.items() if k != "default"][:60],
            "modular_input_schemes": modinputs, "indexes_declared": {k: v.get("datatype", "event") for k, v in idx.items()}, "metrics_signals": metric_sig,
            "tags": {k: sorted(kk for kk, vv in v.items() if vv == "enabled") for k, v in tags.items()}, "eventtypes": sorted(evt),
            "dependencies": {"manifest": manifest_deps, "mentions_other_apps_in_readme": sorted(set(re.findall(r"(Splunk_TA_[A-Za-z0-9_\-]+|Splunk_SA_CIM|Splunk Common Information Model)", readme)))[:10]},
            "publisher": (app.get("launcher", {}) or {}).get("author") or ((info.get("author") or [{}])[0].get("name") if isinstance(info.get("author"), list) and info.get("author") else None),
            "description": ((app.get("launcher", {}) or {}).get("description") or (app.get("ui", {}) or {}).get("description") or info.get("description") or "")[:300] or None,
            "source_keyed_props_stanzas": source_keyed, "ingestion": ingestion_signals(inputs, modinputs, readme, metric_sig, in_types), "datamodels_conf": bool(_g(files, root, "default/datamodels.conf") or _g(files, root, "default/data_models.conf")),
            "savedsearches": len(parse_conf(_g(files, root, "default/savedsearches.conf"))), "supported_products_documented": sorted(set(re.findall(r"(?:supports?|compatible with|collects? data from)[^.\n]{0,80}", readme, re.I)))[:3],
            "cim_hints": {"cim_in_readme": bool(re.search(r"\bCIM\b|Common Information Model", readme)), "tag_stanzas": len(tags)}, "has_bin_scripts": has_bin}


def main(packs, out, only=PHASE4_PACKAGES):
    res = []
    for pkg in sorted(packs.iterdir()):
        if not pkg.name.endswith((".spl", ".tgz", ".tar.gz")) or (only is not None and pkg.name not in only):
            continue
        rec = {"package": pkg.name, "bytes": pkg.stat().st_size, "status": "INSPECTED", "error": None}
        try:
            files, st = read_package(str(pkg))
            rec["archive_safety"] = st
            rec["apps"] = [inventory_app(files, r) for r in app_roots(files)]
            if not rec["apps"]:
                rec["status"], rec["error"] = "NO_APP_FOUND", "no default/app.conf or app.manifest in the archive"
        except Exception as exc:  # corrupt archive etc.: reported, never hidden
            rec.update(status="ERROR", error="%s: %s" % (type(exc).__name__, exc))
        res.append(rec)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps({"packages": res}, indent=1) + "\n")
    for r in res:
        print("%-62s %-9s apps=%d sourcetypes=%d" % (r["package"], r["status"], len(r.get("apps", [])), sum(len(a["sourcetypes"]) for a in r.get("apps", []))))
    return 0


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if x != "--all"]
    sys.exit(main(Path(a[0] if a else "~/netspout/private-packs").expanduser(), a[1] if len(a) > 1 else str(ROOT / "docs/verification/evidence/ta_inventory/packages.json"), None if "--all" in sys.argv else PHASE4_PACKAGES))
