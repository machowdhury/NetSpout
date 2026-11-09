#!/usr/bin/env bash
# Runs ON the instance: AppInspect 4.4.0 (precert and cloud tags) on the released v2.0.1 package and on the package built here; writes full reports and a disposition summary.
set -u
W=/opt/p17; OUT=$W/harness/docs/verification/evidence/phase17/aws-native-x86_64/appinspect; mkdir -p $OUT
cp $W/baseline_netspout.spl $OUT/baseline_netspout.spl; cp $W/build/netspout.spl $OUT/single_netspout.spl
cat > $OUT/run.sh <<'IN'
set -e
apt-get update -qq >/dev/null 2>&1; apt-get install -y -qq libmagic1 >/dev/null 2>&1
pip install -q splunk-appinspect==4.4.0 2>&1 | tail -1
for n in baseline single; do
  splunk-appinspect inspect /w/${n}_netspout.spl --mode precert --output-file /w/${n}_precert.json --data-format json > /w/${n}_precert.log 2>&1 || true
  splunk-appinspect inspect /w/${n}_netspout.spl --mode precert --included-tags cloud --output-file /w/${n}_cloud.json --data-format json > /w/${n}_cloud.log 2>&1 || true
done
IN
docker run --rm -v "$OUT:/w" python:3.12-slim bash /w/run.sh
python3 - "$OUT" <<'PY'
import json, sys
out = sys.argv[1]; rows = {}
for n in ("baseline_precert", "single_precert", "baseline_cloud", "single_cloud"):
    d = json.load(open("%s/%s.json" % (out, n))); o = {}
    for g in d["reports"][0]["groups"]:
        for c in g["checks"]:
            if c["result"] in ("failure", "error"):
                o[c["name"]] = len(c.get("messages", []))
    rows[n] = {"summary": d["summary"], "failing_checks": o}
base, new = set(rows["baseline_precert"]["failing_checks"]), set(rows["single_precert"]["failing_checks"])
rows["disposition"] = {"shared_with_released_v2_0_1": sorted(base & new), "added_by_single_package": sorted(new - base), "fixed_vs_v2_0_1": sorted(base - new)}
json.dump(rows, open(out + "/appinspect_summary.json", "w"), indent=1)
print(json.dumps(rows["disposition"], indent=1), {k: rows[k]["summary"]["failure"] for k in rows if k != "disposition"})
PY
rm -f $OUT/*.spl $OUT/run.sh
