#!/usr/bin/env bash
# Runs ON the instance: (1) the documented regression selection (39 files from Phase 16 + the files added or touched by Phase 17), (2) the whole tests/ tree except tests/lab.
# Known v2.0.1 failures are listed so any NEW failure stands out.
set -u
W=/opt/p17; H=$W/harness; OUT=$H/docs/verification/evidence/phase17/aws-native-x86_64/run2-bdc4084/regression; mkdir -p $OUT
python3 -m venv $W/venv-test && $W/venv-test/bin/pip install -q -r $H/backend/requirements.txt pytest pytest-timeout pyyaml
cd $H
SEL="$(sed 's#^#tests/#' docs/verification/evidence/phase16/python_selection_files.txt | tr '\n' ' ') tests/test_phase17_secrets.py tests/test_phase17_limits.py tests/test_gateway_capabilities.py tests/test_gateway_key.py tests/test_no_secret_in_get_responses.py tests/test_engine_launcher.py tests/test_phase101_gateway_engine.py tests/test_phase4f_splunk_app_surface.py tests/test_phase13_release_candidate.py"
$W/venv-test/bin/python -m pytest $SEL -q -p no:cacheprovider --timeout=600 > $OUT/selection.txt 2>&1
$W/venv-test/bin/python -m pytest tests --ignore=tests/lab -q -p no:cacheprovider --timeout=600 > $OUT/full_tests_tree.txt 2>&1
python3 - "$OUT" <<'PY'
import json, re, sys
out = sys.argv[1]
known = ("tests/test_gate6_integrity.py::TestGate6Integrity::test_07_successful_hec", "tests/test_gate9_5_telemetry_semantics.py::", "tests/test_phase12_agentic_supply_chain.py::Phase12SecurityPackTests::test_dashboard_recipe_families_integrate_without_regression")
res = {"known_v2_0_1_failures": list(known)}
for name in ("selection", "full_tests_tree"):
    t = open("%s/%s.txt" % (out, name)).read()
    failed = sorted(set(re.findall(r"^FAILED (\S+)", t, re.M)) | set(re.findall(r"^ERROR (\S+)", t, re.M)))
    last = [l for l in t.splitlines() if re.search(r"\d+ (passed|failed)", l)][-1:]
    res[name] = {"summary_line": last[0] if last else None, "failed_or_error_ids": failed, "not_in_known_list": [f for f in failed if not any(f.startswith(k) for k in known)]}
json.dump(res, open(out + "/regression_summary.json", "w"), indent=1)
print(json.dumps({k: (v["summary_line"], len(v["not_in_known_list"])) for k, v in res.items() if k != "known_v2_0_1_failures"}))
PY
