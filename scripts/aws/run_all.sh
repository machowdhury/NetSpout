#!/usr/bin/env bash
# Orchestrates the validation from your laptop through Session Manager. Run the stages in order, or re-run one:
#   run_all.sh stage | bootstrap | build | checks | primary | collect
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); . "$HERE/env.sh"; . "$HERE/ssm.sh"
: "${P17_INSTANCE:?run 01_create.sh first}"
W=/opt/p17
LBL_PRIMARY=splunk-10.6.1.1

stage() {
  cd "$P17_REPO"
  git diff --quiet && git diff --cached --quiet || { echo "working tree not clean"; exit 1; }
  git diff --quiet "$P17_APPROVED_COMMIT" HEAD -- netspout backend src scripts/build_single_package.py scripts/single_package_lock.json || { echo "package inputs at HEAD differ from the approved commit"; exit 1; }
  [ "$(shasum -a 256 "$P17_BASELINE_SPL" | cut -d' ' -f1)" = "$P17_BASELINE_SHA" ] || { echo "baseline v2.0.1 netspout.spl sha mismatch"; exit 1; }
  echo "harness commit $(git rev-parse HEAD); approved package commit $P17_APPROVED_COMMIT" | tee "$P17_STATE.commits"
  T=$(mktemp -d)
  git archive --format=tar "$P17_APPROVED_COMMIT" | gzip -n > "$T/approved-src.tar.gz"
  git archive --format=tar HEAD | gzip -n > "$T/harness.tar.gz"
  cp "$P17_BASELINE_SPL" "$T/baseline_netspout.spl"
  aws s3 cp "$T/approved-src.tar.gz" "s3://$P17_BUCKET/stage/approved-src.tar.gz" --only-show-errors
  aws s3 cp "$T/harness.tar.gz" "s3://$P17_BUCKET/stage/harness.tar.gz" --only-show-errors
  aws s3 cp "$T/baseline_netspout.spl" "s3://$P17_BUCKET/stage/baseline_netspout.spl" --only-show-errors
  rm -rf "$T"
  ssm_run "set -e; snap install aws-cli --classic >/dev/null 2>&1 || true; mkdir -p $W; export AWS_DEFAULT_REGION=$AWS_REGION; for f in approved-src.tar.gz harness.tar.gz baseline_netspout.spl; do aws s3 cp s3://$P17_BUCKET/stage/\$f $W/\$f --only-show-errors; done; echo '$P17_BASELINE_SHA  $W/baseline_netspout.spl' | sha256sum -c -" 900
}
bootstrap() { ssm_bg bootstrap "set -e; mkdir -p $W/harness; tar -xzf $W/harness.tar.gz -C $W/harness scripts/aws/remote_bootstrap.sh && bash $W/harness/scripts/aws/remote_bootstrap.sh $P17_DEADMAN_MIN $P17_IMG_PRIMARY"; ssm_wait bootstrap || { ssm_tail bootstrap 60; exit 1; }; }
build() { ssm_bg build "bash $W/harness/scripts/aws/remote_build.sh $P17_APPROVED_COMMIT $P17_EXPECTED_GZ $P17_EXPECTED_TAR"; ssm_wait build || true; ssm_tail build 40; }
primary() { ssm_bg run_primary "bash $W/harness/scripts/aws/remote_run_version.sh $LBL_PRIMARY $P17_IMG_PRIMARY $P17_SUSTAIN_PRIMARY"; ssm_wait run_primary || true; ssm_run "tail -n 60 $W/harness/docs/verification/evidence/phase17/aws-native-x86_64/run2-bdc4084/$LBL_PRIMARY/steps.log" 60; collect; }
checks() { ssm_bg checks "bash $W/harness/scripts/aws/remote_appinspect.sh && bash $W/harness/scripts/aws/remote_regression.sh"; ssm_wait checks || true; ssm_tail checks 30; collect; }
collect() { bash "$HERE/05_collect.sh"; }
"${1:?stage|bootstrap|build|checks|primary|collect}"
