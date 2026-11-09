# Source after env.sh. ssm_run "<shell>" [timeout_s]: run a command on the instance through Session Manager's Run Command (no SSH, no inbound port); full output also lands in the bucket under ssm-logs/.
ssm_run() {
  local to=${2:-900} id st
  id=$(aws ssm send-command --instance-ids "$P17_INSTANCE" --document-name AWS-RunShellScript --timeout-seconds "$to" \
       --parameters "$(python3 -c 'import json,sys;print(json.dumps({"commands":[sys.argv[1]],"executionTimeout":[sys.argv[2]]}))' "$1" "$to")" \
       --output-s3-bucket-name "$P17_BUCKET" --output-s3-key-prefix ssm-logs --query Command.CommandId --output text)
  while :; do st=$(aws ssm get-command-invocation --command-id "$id" --instance-id "$P17_INSTANCE" --query Status --output text 2>/dev/null || echo Pending); case $st in Pending|InProgress|Delayed) sleep 5;; *) break;; esac; done
  aws ssm get-command-invocation --command-id "$id" --instance-id "$P17_INSTANCE" --query '[StandardOutputContent,StandardErrorContent]' --output text
  [ "$st" = Success ]
}
# ssm_bg NAME "<shell>": run detached on the instance (logs /opt/p17/logs/NAME.log, exit code /opt/p17/status/NAME.rc); ssm_wait NAME polls cheaply.
ssm_bg() { ssm_run "mkdir -p /opt/p17/logs /opt/p17/status; rm -f /opt/p17/status/$1.rc; nohup bash -c '$2; echo \$? > /opt/p17/status/$1.rc' > /opt/p17/logs/$1.log 2>&1 & echo started $1" 60; }
ssm_wait() { local rc; while :; do rc=$(ssm_run "cat /opt/p17/status/$1.rc 2>/dev/null || echo running" 60 | tail -1); [ "$rc" != running ] && { echo "$1 finished rc=$rc"; return "$rc"; }; sleep 120; done; }
ssm_tail() { ssm_run "tail -n ${2:-40} /opt/p17/logs/$1.log" 60; }
