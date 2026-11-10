#!/usr/bin/env bash
# Runs ON the EC2 instance (native Linux x86_64, Docker). Full Phase 17 suite for one Splunk version. Steps never abort the run: each PASS/FAIL is logged and the next step runs.
#   remote_run_version.sh <label e.g. splunk-10.6.1.1> <image@sha256:digest> <sustained_seconds>
# Nothing here talks to any Splunk except the disposable container it starts on 127.0.0.1.
set -u
LABEL=$1; IMAGE=$2; SUSTAIN=${3:-3600}
W=/opt/p17; H=$W/harness; PY=$W/venv/bin/python; PKG=$W/build/netspout.spl; BASE=$W/baseline_netspout.spl
SEC=$W/secrets/$LABEL; mkdir -p "$SEC"; chmod 700 "$W/secrets" "$SEC"
OUTREL=docs/verification/evidence/phase17/aws-native-x86_64/run2-1d60daa/$LABEL; OUT=$H/$OUTREL; mkdir -p "$OUT"
C=p17n-${LABEL//[^a-zA-Z0-9]/-}; M=https://127.0.0.1:18089; BASEURL=http://127.0.0.1:18000
RES=$OUT/steps.log; : > "$RES"
umask 077
python3 -c "import secrets;print(secrets.token_urlsafe(18)+'Aa1')" > $SEC/pw; python3 -c "import secrets;print(secrets.token_urlsafe(14)+'Aa1')" > $SEC/viewer
PW=$(cat $SEC/pw)
export P17_MGMT=$M P17_PASSWORD_FILE=$SEC/pw P17_TARGET=aws-native-x86_64/run2-1d60daa/$LABEL P17_NATIVE=1 PLAYWRIGHT_BASE_URL=$BASEURL
HOSTLABEL="AWS EC2 $(curl -s -m 3 -H "X-aws-ec2-metadata-token: $(curl -s -m 3 -X PUT http://169.254.169.254/latest/api/token -H 'X-aws-ec2-metadata-token-ttl-seconds: 60')" http://169.254.169.254/latest/meta-data/instance-type) $(uname -m) native, Docker $(docker --version | cut -d' ' -f3 | tr -d ,)"

step() { local n=$1; shift; local t=$(date -u +%FT%TZ); if "$@" >> $OUT/step_$n.log 2>&1; then echo "$t PASS $n" | tee -a $RES; else echo "$t FAIL $n (rc=$?)" | tee -a $RES; fi; }
sget() { curl -sk -u admin:$PW -m ${T:-120} "$M$1" "${@:2}"; }
gw() { curl -sk -u admin:$PW -m 120 "$M/services/netspout_gateway$1" "${@:2}"; }
wait_splunk() { sleep 25; until [ "$(curl -sk -o /dev/null -w '%{http_code}' -u admin:$PW $M/services/server/info)" = 200 ]; do sleep 10; done; sleep 60; }
restart_splunk() { sget /services/server/control/restart -X POST -o /dev/null; wait_splunk; }
ports() { docker exec -u root $C sh -c 'cat /proc/net/tcp /proc/net/tcp6' | awk '$4=="0A"{print $2}' | sed 's/.*://' | sort -u | while read h; do v=$((16#$h)); [ $v -lt 32000 ] && printf "%d " $v; done; echo; }
nprocs() { docker exec -u root $C ps -eo args | grep -c "[p]ulseforge_engine"; }
pw_ui() { # playwright spec runner; extra env via caller
  ( cd $H/frontend && rm -rf test-results && P17_PASSWORD_FILE=$SEC/pw P17_VIEWER_PASSWORD=$(cat $SEC/viewer) P17_HEC_TOKEN=$HEC npx playwright test tests/phase17-splunk-web.spec.ts --reporter=list "$@" ); }
acc() { ( cd $H && $PY scripts/phase17_acceptance.py "$@" ); }
keep() { cp $OUT/events.json $OUT/events_$1.json; }

# 1. container ---------------------------------------------------------------------------------------------------------
step container_start bash -c "docker rm -f $C 2>/dev/null; docker volume rm p17n_${C}_etc p17n_${C}_var 2>/dev/null; docker run -d --name $C --platform linux/amd64 -p 127.0.0.1:18000:8000 -p 127.0.0.1:18089:8089 -p 127.0.0.1:18088:8088 \
  -e SPLUNK_START_ARGS=--accept-license -e SPLUNK_GENERAL_TERMS=--accept-sgt-current-at-splunk-com -e SPLUNK_PASSWORD='$PW' -e SPLUNK_HEC_TOKEN=\$(python3 -c 'import uuid;print(uuid.uuid4())') \
  -v p17n_${C}_etc:/opt/splunk/etc -v p17n_${C}_var:/opt/splunk/var $IMAGE && until [ \"\$(docker inspect -f '{{.State.Health.Status}}' $C)\" = healthy ]; do sleep 10; done"
step host_and_runtime_probe bash -c "$PY $H/scripts/phase17_hostinfo.py $C '$IMAGE' '$HOSTLABEL' > $OUT/host.json && docker cp $H/scripts/phase17_probe.py $C:/tmp/p.py && docker exec -e LD_LIBRARY_PATH=/opt/splunk/lib $C /opt/splunk/bin/python3.13 /tmp/p.py > $OUT/runtime_probe.txt && cat $OUT/host.json $OUT/runtime_probe.txt"
HEC=$(sget "/servicesNS/nobody/splunk_httpinput/data/inputs/http?output_mode=json&count=0" | python3 -c "import sys,json;print(json.load(sys.stdin)['entry'][0]['content']['token'])"); export HEC
ports > $W/ports_before_$LABEL.txt; echo "ports before: $(cat $W/ports_before_$LABEL.txt)" > $W/ports_before_$LABEL.fmt
step users_and_indexes bash -c "$(declare -f sget); PW='$PW'; M=$M; sget /services/authentication/users -d name=p17_viewer -d password=\$(cat $SEC/viewer) -d roles=user -o /dev/null; sget /services/data/indexes -d name=dev_test_replay -d datatype=event -o /dev/null; sget /services/data/indexes -d name=dev_test_replay_metrics -d datatype=metric -o /dev/null"

# 2. install through Splunk Web, restart, census, idle ------------------------------------------------------------------
step install_via_splunk_web bash -c "cd $H/frontend && P17_PASSWORD_FILE=$SEC/pw P17_UPLOAD=$PKG npx playwright test tests/phase17-splunk-web.spec.ts -g 'install netspout.spl' --reporter=line && cp test-results/phase17-upload.png $OUT/splunk_web_install_app_from_file.png"
step restart_after_install bash -c "$(declare -f sget wait_splunk); PW='$PW'; M=$M; sget /services/server/control/restart -X POST -o /dev/null; wait_splunk; curl -sk -u admin:$PW $M/services/netspout_gateway/engine"
step census bash -c "cd $H && $PY scripts/phase17_census.py $C aws-native-x86_64/run2-1d60daa/$LABEL $W/ports_before_$LABEL.fmt $(sha256sum $PKG | cut -d' ' -f1) '$HOSTLABEL'"
P17_LABEL=fresh_install_unconfigured step idle_fresh acc idle:3

# 3. UI and API acceptance ----------------------------------------------------------------------------------------------
step browser_spec pw_ui
cp $H/frontend/test-results/*.png $H/frontend/test-results/*.txt $OUT/ 2>/dev/null
step acceptance_events_metrics_scenario_stream_authz acc events metrics scenario stream authz
keep first_run

# 4. lifecycle -----------------------------------------------------------------------------------------------------------
EP=$(docker exec -u root $C pgrep -f pulseforge_engine_main | head -1); docker exec -u root $C sh -c "kill -9 $EP"; sleep 15
docker exec -u root $C cat /opt/splunk/var/lib/netspout/engine.json > $OUT/engine_after_kill.json
step events_after_engine_kill acc events; keep after_engine_kill
LP=$(docker exec -u root $C pgrep -f pulseforge_engine_launcher | head -1); docker exec -u root $C sh -c "kill -9 $LP"; sleep 8; echo "procs after launcher kill: $(nprocs)" > $OUT/launcher_kill.txt
gw /engine >> $OUT/launcher_kill.txt; gw /engine/restart -X POST >> $OUT/launcher_kill.txt; sleep 40; gw /engine >> $OUT/launcher_kill.txt
step events_after_launcher_recovery acc events; keep after_launcher_recovery
docker exec -u splunk $C /opt/splunk/bin/splunk stop > $OUT/splunk_stop.txt 2>&1; sleep 5; echo "procs after stop: $(nprocs)" >> $OUT/splunk_stop.txt
docker exec -u splunk $C /opt/splunk/bin/splunk start --accept-license --answer-yes --no-prompt >> $OUT/splunk_stop.txt 2>&1; sleep 60
step events_metrics_after_stop_start acc events metrics; keep after_stop_start
restart_splunk; docker exec -u root $C cat /opt/splunk/var/lib/netspout/engine.json > $OUT/engine_after_restart.json
step events_after_restart acc events; keep after_restart

# 5. sustained load at the 200 events/s ceiling, then idle ------------------------------------------------------------
step sustained_200eps bash -c "cd $H/scripts && $PY phase17_sustained.py $C $SUSTAIN '$HOSTLABEL'"
P17_LABEL=after_runs_lifecycle_and_sustained step idle_after_load acc idle:3

# 6. uninstall, then upgrade from the released v2.0.1 ---------------------------------------------------------------
B=$(sget /services/apps/local/netspout -o /dev/null -w '%{http_code}' -X DELETE); sleep 25
echo "{\"uninstall_http\": \"$B\", \"procs_after\": $(nprocs), \"app_dir_present\": $(docker exec -u root $C ls /opt/splunk/etc/apps | grep -c '^netspout$'), \"state_dir_left\": \"$(docker exec -u root $C ls /opt/splunk/var/lib/netspout | tr '\n' ' ')\"}" > $OUT/uninstall.json
docker exec -u root $C rm -rf /opt/splunk/var/lib/netspout
UP=$OUT/upgrade_from_2.0.1; mkdir -p $UP
step install_v2_0_1_via_splunk_web bash -c "cd $H/frontend && P17_PASSWORD_FILE=$SEC/pw P17_UPLOAD=$BASE npx playwright test tests/phase17-splunk-web.spec.ts -g 'install netspout.spl' --reporter=line"
restart_splunk
{ echo "v2.0.1 version: $(sget '/servicesNS/nobody/system/apps/local/netspout?output_mode=json' | python3 -c "import sys,json;print(json.load(sys.stdin)['entry'][0]['content']['version'])")"; gw /engine -X POST -H 'Content-Type: application/json' -d '{"url":"http://engine.example.invalid:8081"}'; } > $UP/v2_0_1_state.txt
sget /servicesNS/nobody/netspout/properties/macros -d __stanza=p17_customer_macro -o /dev/null; sget /servicesNS/nobody/netspout/properties/macros/p17_customer_macro -d definition=customer_value_kept -o /dev/null
docker exec -u root $C sh -c 'cd /opt/splunk/etc/apps/netspout/local && ls && md5sum * | sort' > $UP/before_upgrade_state.txt
step upgrade_via_splunk_web bash -c "cd $H/frontend && P17_UPGRADE=1 P17_PASSWORD_FILE=$SEC/pw P17_UPLOAD=$PKG npx playwright test tests/phase17-splunk-web.spec.ts -g 'install netspout.spl' --reporter=line && cp test-results/phase17-upload.png $UP/splunk_web_upgrade_app.png"
restart_splunk
docker exec -u root $C sh -c 'cd /opt/splunk/etc/apps/netspout/local && ls && md5sum * | sort' > $UP/after_upgrade_state.txt
diff $UP/before_upgrade_state.txt $UP/after_upgrade_state.txt > $UP/local_diff.txt && echo "LOCAL_CONFIG_IDENTICAL" >> $UP/local_diff.txt
{ echo "version now: $(sget '/servicesNS/nobody/system/apps/local/netspout?output_mode=json' | python3 -c "import sys,json;print(json.load(sys.stdin)['entry'][0]['content']['version'])")"; gw /engine; } > $UP/after_upgrade_engine.txt
step census_after_upgrade bash -c "cd $H && $PY scripts/phase17_census.py $C aws-native-x86_64/run2-1d60daa/$LABEL/upgrade_from_2.0.1 $W/ports_before_$LABEL.fmt $(sha256sum $PKG | cut -d' ' -f1) '$HOSTLABEL'"
P17_TARGET=aws-native-x86_64/run2-1d60daa/$LABEL/upgrade_from_2.0.1 P17_LABEL=after_upgrade_unconfigured step idle_after_upgrade acc idle:3
step browser_spec_after_upgrade pw_ui -g "Connections|first-run|Generate Data"
cp $H/frontend/test-results/*.png $H/frontend/test-results/*.txt $UP/ 2>/dev/null
P17_TARGET=aws-native-x86_64/run2-1d60daa/$LABEL/upgrade_from_2.0.1 step acceptance_after_upgrade acc events metrics scenario

# 7. wrap up (the container and its volumes are disposable) -------------------------------------------------------------
docker stop $C >/dev/null 2>&1; docker rm $C >/dev/null 2>&1; docker volume rm p17n_${C}_etc p17n_${C}_var >/dev/null 2>&1
echo "$(date -u +%FT%TZ) DONE $LABEL" | tee -a $RES
tar -C $H -czf $W/evidence_$LABEL.tgz $OUTREL && sha256sum $W/evidence_$LABEL.tgz > $W/evidence_$LABEL.tgz.sha256
