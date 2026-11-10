#!/usr/bin/env bash
# Pulls evidence (per Splunk version, plus the build report) from the instance through the bucket into the repo, verifying sha256. Safe to re-run.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); . "$HERE/env.sh"; . "$HERE/ssm.sh"
W=/opt/p17; DEST="$P17_REPO/docs/verification/evidence/phase17/aws-native-x86_64/run2-1d60daa"; mkdir -p "$DEST"
ssm_run "set -e; export AWS_DEFAULT_REGION=$AWS_REGION; cd $W/harness; tar -czf $W/evidence_all.tgz docs/verification/evidence/phase17/aws-native-x86_64/run2-1d60daa; sha256sum $W/evidence_all.tgz | tee $W/evidence_all.tgz.sha256; aws s3 cp $W/evidence_all.tgz s3://$P17_BUCKET/out/evidence_all.tgz --only-show-errors" 600 | tee /tmp/p17_collect.txt
aws s3 cp "s3://$P17_BUCKET/out/evidence_all.tgz" /tmp/p17_evidence_all.tgz --only-show-errors
WANT=$(grep -o '^[0-9a-f]\{64\}' /tmp/p17_collect.txt | head -1); GOT=$(shasum -a 256 /tmp/p17_evidence_all.tgz | cut -d' ' -f1)
[ "$WANT" = "$GOT" ] || { echo "evidence checksum mismatch"; exit 1; }
tar -xzf /tmp/p17_evidence_all.tgz -C "$P17_REPO"; echo "evidence extracted into $DEST ($GOT)"
