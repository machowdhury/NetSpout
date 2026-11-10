#!/usr/bin/env bash
# Local screening of a candidate package on a DISPOSABLE Splunk container (127.0.0.1:18000/18088/18089 only): install through Splunk Web, configure through the UI, then a short sustained run.
#   phase17_local_screen.sh <label> <package.spl> <sustained_seconds>
# Docker Desktop on arm64 runs the amd64 image under emulation, so absolute rates are only comparable between two runs of this script on the same machine.
set -u
LABEL=$1; PKG=$2; SUS=$3
ROOT=$(cd "$(dirname "$0")/.." && pwd); PY=/Users/mahamudc/netspout/venv17/bin/python
IMAGE=splunk/splunk:10.6.1; C=p17s-$LABEL; M=https://127.0.0.1:18089; SEC=/Users/mahamudc/netspout/p17/screen_$LABEL; mkdir -p $SEC; chmod 700 $SEC; umask 077
OUT=$ROOT/docs/verification/evidence/phase17/screening/$LABEL; mkdir -p $OUT; LOG=$OUT/steps.log; : > $LOG
$PY -c "import secrets;print(secrets.token_urlsafe(18)+'Aa1')" > $SEC/pw; $PY -c "import secrets;print(secrets.token_urlsafe(14)+'Aa1')" > $SEC/viewer; PW=$(cat $SEC/pw)
export P17_MGMT=$M P17_PASSWORD_FILE=$SEC/pw P17_TARGET=screening/$LABEL PLAYWRIGHT_BASE_URL=http://127.0.0.1:18000
step() { n=$1; shift; if "$@" >> $OUT/step_$n.log 2>&1; then echo "$(date -u +%FT%TZ) PASS $n" | tee -a $LOG; else echo "$(date -u +%FT%TZ) FAIL $n" | tee -a $LOG; fi; }
sget() { curl -sk -u admin:$PW -m 120 "$M$1" "${@:2}"; }
HECTOK=$($PY -c 'import uuid;print(uuid.uuid4())')
step container_start bash -c "docker rm -f $C 2>/dev/null; docker volume rm ${C}_etc ${C}_var 2>/dev/null; docker run -d --name $C --platform linux/amd64 -p 127.0.0.1:18000:8000 -p 127.0.0.1:18089:8089 -p 127.0.0.1:18088:8088 -e SPLUNK_START_ARGS=--accept-license -e SPLUNK_GENERAL_TERMS=--accept-sgt-current-at-splunk-com -e SPLUNK_PASSWORD='$PW' -e SPLUNK_HEC_TOKEN=$HECTOK -v ${C}_etc:/opt/splunk/etc -v ${C}_var:/opt/splunk/var $IMAGE && until [ \"\$(docker inspect -f '{{.State.Health.Status}}' $C)\" = healthy ]; do sleep 10; done"
step users_and_indexes bash -c "$(declare -f sget); PW='$PW'; M=$M; sget /services/authentication/users -d name=p17_viewer -d password=\$(cat $SEC/viewer) -d roles=user -o /dev/null; sget /services/data/indexes -d name=dev_test_replay -d datatype=event -o /dev/null; sget /services/data/indexes -d name=dev_test_replay_metrics -d datatype=metric -o /dev/null"
step install_via_splunk_web bash -c "cd $ROOT/frontend && P17_PASSWORD_FILE=$SEC/pw P17_UPLOAD=$PKG npx playwright test tests/phase17-splunk-web.spec.ts -g 'install netspout.spl' --reporter=line"
step restart bash -c "$(declare -f sget); PW='$PW'; M=$M; sget /services/server/control/restart -X POST -o /dev/null; sleep 30; until [ \"\$(curl -sk -o /dev/null -w '%{http_code}' -u admin:$PW $M/services/server/info)\" = 200 ]; do sleep 10; done; sleep 90; curl -sk -u admin:$PW $M/services/netspout_gateway/engine"
step idle_fresh bash -c "cd $ROOT && P17_LABEL=fresh_install_unconfigured $PY scripts/phase17_acceptance.py idle:2"
step browser_spec_configure bash -c "cd $ROOT/frontend && rm -rf test-results && P17_PASSWORD_FILE=$SEC/pw P17_VIEWER_PASSWORD=\$(cat $SEC/viewer) P17_HEC_TOKEN=$HECTOK npx playwright test tests/phase17-splunk-web.spec.ts --reporter=list"
step acceptance_focused bash -c "cd $ROOT && $PY scripts/phase17_acceptance.py events metrics authz"
step sustained bash -c "cd $ROOT && $PY scripts/phase17_sustained.py $C $SUS 'local arm64 Mac, emulated amd64 Splunk (screening: $LABEL)'"
step idle_after_load bash -c "cd $ROOT && P17_LABEL=after_sustained $PY scripts/phase17_acceptance.py idle:2"
cp $ROOT/docs/verification/evidence/phase17/screening/$LABEL/sustained_200eps.json $OUT/ 2>/dev/null
step container_stop bash -c "docker rm -f $C; docker volume rm ${C}_etc ${C}_var"
echo "$(date -u +%FT%TZ) DONE $LABEL" | tee -a $LOG
