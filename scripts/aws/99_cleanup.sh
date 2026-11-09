#!/usr/bin/env bash
# Deletes ONLY the resources recorded in $P17_STATE by 01_create.sh (instance, its volume, security group, instance profile, role, bucket). Lists them first; type DELETE to proceed.
# Refuses if evidence has not been collected (set FORCE=1 to override). Never lists or deletes anything by wildcard.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd); . "$HERE/env.sh"
for l in splunk-10.6.1.1 splunk-10.2.7; do [ -f "$P17_REPO/docs/verification/evidence/phase17/aws-native-x86_64/$l/steps.log" ] || [ "${FORCE:-0}" = 1 ] || { echo "no collected evidence for $l (run run_all.sh collect, or FORCE=1)"; exit 1; }; done
echo "About to delete (from $P17_STATE):"; grep '^export' "$P17_STATE"
[ -n "${P17_INSTANCE:-}" ] && aws ec2 describe-instances --instance-ids "$P17_INSTANCE" --query 'Reservations[0].Instances[0].BlockDeviceMappings[].Ebs.VolumeId' --output text > "$P17_STATE.volumes" 2>/dev/null || true
read -r -p "Type DELETE: " ok; [ "$ok" = DELETE ] || { echo aborted; exit 1; }
if [ -n "${P17_INSTANCE:-}" ]; then aws ec2 terminate-instances --instance-ids "$P17_INSTANCE" >/dev/null; aws ec2 wait instance-terminated --instance-ids "$P17_INSTANCE"; fi
if [ -n "${P17_SG:-}" ]; then for i in $(seq 1 12); do aws ec2 delete-security-group --group-id "$P17_SG" 2>/dev/null && break || sleep 10; done; fi
if [ -n "${P17_PROFILE:-}" ]; then aws iam remove-role-from-instance-profile --instance-profile-name "$P17_PROFILE" --role-name "$P17_ROLE" || true; aws iam delete-instance-profile --instance-profile-name "$P17_PROFILE" || true; fi
if [ -n "${P17_ROLE:-}" ]; then aws iam detach-role-policy --role-name "$P17_ROLE" --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore || true; aws iam delete-role-policy --role-name "$P17_ROLE" --policy-name bucket || true; aws iam delete-role --role-name "$P17_ROLE" || true; fi
if [ -n "${P17_BUCKET:-}" ]; then aws s3 rm "s3://$P17_BUCKET" --recursive --only-show-errors; aws s3api delete-bucket --bucket "$P17_BUCKET"; fi
echo "--- verification (all should report gone/empty)"
[ -n "${P17_INSTANCE:-}" ] && aws ec2 describe-instances --instance-ids "$P17_INSTANCE" --query 'Reservations[0].Instances[0].State.Name' --output text
for v in $(cat "$P17_STATE.volumes" 2>/dev/null); do aws ec2 describe-volumes --volume-ids "$v" --query 'Volumes[0].State' --output text 2>&1 | head -1; done
[ -n "${P17_SG:-}" ] && { aws ec2 describe-security-groups --group-ids "$P17_SG" 2>&1 | head -1 || true; }
[ -n "${P17_ROLE:-}" ] && { aws iam get-role --role-name "$P17_ROLE" 2>&1 | head -1 || true; }
[ -n "${P17_BUCKET:-}" ] && { aws s3api head-bucket --bucket "$P17_BUCKET" 2>&1 | head -1 || true; }
aws ec2 describe-instances --filters Name=tag:Project,Values=netspout-phase17 Name=instance-state-name,Values=pending,running,stopping,stopped --query 'length(Reservations)' --output text | sed 's/^/remaining tagged instances: /'
mv "$P17_STATE" "$P17_STATE.cleaned.$(date -u +%s)"
