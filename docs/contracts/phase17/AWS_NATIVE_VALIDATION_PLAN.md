# Phase 17 — AWS native Linux x86_64 validation: authorized run plan (ca-central-1, Splunk 10.6.1.1 only)

Authorized by the user for **one** disposable run. Region **ca-central-1 only**; Splunk Enterprise **10.6.1.1 only** (the 10.2.7 results stay as historical emulated-host compatibility evidence and are not repeated). PR #11 is not merged or published by any of this.

Note on the region: the authorization text named `ca-central-2` in places. That region does not exist for this account (`ec2.ca-central-2.amazonaws.com` does not resolve; the account's Canadian regions are `ca-central-1`, enabled, and `ca-west-1`, not opted in), so the run uses `ca-central-1`, the region named in the request's first instruction and the account's CLI default. If `ca-central-1` was not what was meant, say so and nothing will have been run elsewhere.

## Outcome of the launch attempt (2026-11-09): BLOCKED, nothing was run

`ec2:RunInstances` in ca-central-1 was refused with an **explicit deny in an AWS Organizations service control policy** (policy and organization identifiers redacted) for the operator's IAM user. No instance, volume or Splunk test was started. The bucket, role, instance profile and security group created just before the call were deleted and the deletion verified (0 instances, 0 volumes, 0 tagged security groups, no `p17-` role or bucket remain). No other region or workaround was tried. Charges: none material. Resuming needs the organization administrator to permit this action (or an approved different account/region); then re-run from `01_create.sh`.

## Preflight (read-only, done before provisioning)

| Check | Result |
|---|---|
| ca-central-1 enabled and accessible | yes (`opt-in-not-required`; AZs 1a, 1b, 1d available); account `…1985`, IAM user |
| `m6i.2xlarge` offered | yes, in 1a, 1b, 1d |
| Ubuntu 24.04 amd64 AMI | `ami-09074533a25da4dd1`, Canonical (099720109477), `ubuntu-noble-24.04-amd64-server-20261108`, x86_64, available |
| Capacity / network | vCPU quota 1,152; default VPC `vpc-251c764d`; no existing instances in the region; no existing `p17*` buckets |

## Price (AWS Price List API, ca-central-1, Linux on-demand, shared tenancy)

m6i.2xlarge **$0.428/h**; gp3 **$0.088/GB-month** × 150 GiB = $13.20/month = **$0.0181/h**; public IPv4 **$0.005/h**. **Total ≈ $0.451/h.** Expected run (one version): create/bootstrap/build/checks ≈ 1 h, suite + 3,600 s load + upgrade ≈ 2 h, collection ≈ 0.2 h → **≈ 3.2 h ≈ $1.45**. Budget cap 6 h = $2.71; the 10-hour self-termination guardrail bounds the worst case at **$4.51**. This is below the previously described budget ($1.9–2.5 for two versions, cap $2.71), so no re-approval is needed; S3, Session Manager and in-region transfer are cents.

## What will exist

`m6i.2xlarge`, Ubuntu 24.04 amd64, 150 GiB gp3 (encrypted, delete-on-termination); Docker running the official `splunk/splunk:10.6.1` amd64 image **pinned by digest** `sha256:2a7cf9d2…` (Splunk 10.6.1.1): native x86_64, no emulation; default VPC, public IPv4 for outbound only, security group with **zero inbound rules**, **no key pair**, IMDSv2 required; Session Manager only (Splunk binds to 127.0.0.1; the browser tests run headless on the instance); one private S3 bucket (public access blocked) for source in / evidence out; instance role = `AmazonSSMManagedInstanceCore` + that bucket; `shutdown -h +600` with terminate-on-shutdown (self-deletes within 10 h). All IDs are recorded in a state file; cleanup deletes only those.

## Scripts (`scripts/aws/`)

`env.sh` (refuses any region but ca-central-1) · `01_create.sh` · `ssm.sh` · `run_all.sh stage|bootstrap|build|checks|primary|collect` · `remote_bootstrap.sh` · `remote_build.sh` · `remote_appinspect.sh` · `remote_regression.sh` · `remote_run_version.sh` · `05_collect.sh` · `99_cleanup.sh`, plus `phase17_sustained.py`, `phase17_hostinfo.py`, `phase17_probe.py`.

## Validation run (all on the instance)

1. **Build and reproducibility:** rebuild `netspout.spl` from the approved commit `91af353` twice (second from an empty wheel cache and touched files); compare with each other and with the approved sha256 `4bf1d214…` and uncompressed-tar sha256 `99c23bbb…`. The artifact tested is the one built on the instance; its sha256 is recorded.
2. **Checks:** AppInspect 4.4.0 (precert and cloud tags) on the released v2.0.1 and the new package with a disposition per failing check; the documented regression selection plus the whole `tests/` tree (except `tests/lab`), with failures compared against the nine known v2.0.1 failures.
3. **Splunk 10.6.1.1, fresh container, disposable random credentials:** install only `netspout.spl` through Splunk Web → restart → census (1 launcher + 1 engine, no new listening port) → 3-min zero-idle window → browser spec (managed status, first-run setup, tested connection, Generate Data, viewer) → Cisco/Fortinet/Palo Alto events, IOS XR metrics with `mstats`, Palo Alto scenario + dashboard searches, streaming limits, authentication/authorization → engine kill, launcher kill + Restart engine, `splunk stop`/`start`, restart → **3,600 s at 200 events/s** → 3-min idle window → uninstall → install the released v2.0.1 (sha `53f09e5f…`), legacy Engine URL + customer macro, upgrade through Splunk Web, `local/` byte comparison, idle window, first-run UI and workflows.

## Pass criteria for the sustained load (declared before the run, evaluated by `phase17_sustained.py`)

1. Average **indexed** events/s ≥ **190** (independently indexed count ÷ run time).
2. **Zero** rejected, unknown or dropped events (accepted − indexed = 0).
3. **No unresolved backlog**: every accepted event searchable ≤ 60 s after the last event was sent, and no blocked Splunk queues in the window.
4. **No uncontrolled restarts**: engine restart counter unchanged and state healthy.
5. **No significant instability**: engine RSS growth (last quarter vs second quarter) ≤ 15 %, splunkd ≤ 25 %.
Measured and recorded regardless: indexed events/s per minute, indexing lag (`_indextime − _time`, an upper bound because the engine stamps events slightly ahead), per-process CPU% and RSS every 15 s, index and filesystem disk use, errors, Splunk HEC/listener warnings.

## Commands

```bash
cd /Users/mahamudc/netspout/phase17-wt/scripts/aws && export P17_REGION=ca-central-1
. ./env.sh && echo CREATE | ./01_create.sh      # explicit approval given; charges start here
. ./env.sh && ./run_all.sh stage && ./run_all.sh bootstrap && ./run_all.sh build
./run_all.sh checks                              # AppInspect + regression
./run_all.sh primary                             # Splunk 10.6.1.1 suite + 3,600 s load; evidence collected afterwards
./run_all.sh collect
echo DELETE | ./99_cleanup.sh                    # only after evidence is collected and reviewed
```

## Cleanup

Terminate the instance (volume ID recorded first and checked afterwards), delete the security group, instance profile, role policies and role, empty and delete the bucket, then verify each ID is gone and that 0 instances tagged `Project=netspout-phase17` remain. Nothing outside the state file is touched; the 10-hour guardrail removes the instance and volume on its own.

## Limits

The suite script is new and has been syntax-checked, not run end-to-end before this run; steps log PASS/FAIL and do not abort. Downloads at run time come from Ubuntu apt, Docker Hub, PyPI, the Playwright CDN and the `aws-cli` snap. Splunk runs in a container on a native x86_64 host (not a package install on the host OS). One instance, one run: no repeat for variance.
