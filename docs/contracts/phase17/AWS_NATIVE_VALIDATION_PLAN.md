# Phase 17 — AWS native Linux x86_64 validation plan (PROPOSAL: nothing has been created, no AWS charge incurred)

Goal: close the open gates of `PHASE17_VALIDATION_MATRIX.md` that emulation on an arm64 Mac could not: native x86_64 results for the single-package `netspout.spl` (PR #11) on Splunk Enterprise **10.6.1.1** (primary) and **10.2.7** (compatibility), including a full **3,600 s** run at a configured **200 events/s**. PR #11 is not merged or published by any of this.

## 1. What will exist, and what it costs

| Item | Choice |
|---|---|
| Instance | `m6i.2xlarge` (8 vCPU Intel, 32 GiB), Ubuntu 24.04 amd64 (Canonical's SSM-published AMI), Docker running the official `splunk/splunk` amd64 images **pinned by digest** (10.6.1.1: `sha256:2a7cf9d2…`, 10.2.7: `sha256:da47bf2f…`): native x86_64, no emulation |
| Storage | 150 GiB gp3, encrypted, delete-on-termination (3,000 IOPS / 125 MB/s included) |
| Network | default VPC, public IPv4 for **outbound only**; security group with **zero inbound rules**; no key pair; IMDSv2 required |
| Access | AWS Systems Manager (Session Manager / Run Command) only; Splunk listens on `127.0.0.1` inside the instance and the browser tests run headless **on the instance**, so no tunnel and no public or forwarded Splunk port |
| Transfer | one private S3 bucket (public access blocked) for the source archives in and the evidence out; instance role limited to that bucket + `AmazonSSMManagedInstanceCore` |
| Guardrail | `shutdown -h +600` timer with terminate-on-shutdown: the instance deletes itself after 10 h at the latest |

Prices read from the AWS Price List API today (read-only call, no charge), Linux on-demand, shared tenancy:

| | us-east-1 (N. Virginia) | ca-central-1 (Canada Central, your CLI default) |
|---|---|---|
| m6i.2xlarge | $0.3840/h | $0.4280/h |
| gp3 150 GiB | $0.0164/h ($12.00/month) | $0.0181/h ($13.20/month) |
| Public IPv4 | $0.005/h | $0.005/h |
| **Total** | **≈ $0.405/h** | **≈ $0.451/h** |

Expected run ≈ 4–5 h (create/bootstrap/build 0.5 h; 10.6.1.1 suite + 3,600 s load + upgrade ≈ 2 h; 10.2.7 suite + 900 s load ≈ 1.4 h; collection 0.2 h): **≈ $1.7–2.3 (us-east-1) or $1.9–2.5 (ca-central-1)**; budget cap 6 h ≈ $2.43 / $2.71; worst case (guardrail, 10 h) ≈ $4.05 / $4.51. S3, SSM and in-region transfer are cents or free. Making the 10.2.7 load run 3,600 s too adds about 0.75 h (~$0.30). **Pick the region at approval** (us-east-1 is cheaper and was used for the earlier prototype test).

Your account must allow 8 On-Demand standard vCPUs in that region and have a default VPC; `01_create.sh` stops with a message otherwise.

## 2. Scripts (`scripts/aws/`, all syntax-checked; the building blocks they call were exercised locally on 10.2.7 and 10.6.1)

| Script | Runs on | Does |
|---|---|---|
| `env.sh` | laptop | variables (region, approved commit, expected hashes, image digests, durations); creates nothing |
| `01_create.sh` | laptop | prints account/region and the list, **asks you to type CREATE**, then creates bucket, role/profile, security group, instance; records IDs in `~/netspout/p17-aws/<run>.state`; verifies 0 inbound rules and SSM online |
| `ssm.sh` | laptop | `ssm_run`, `ssm_bg`, `ssm_wait`: Run Command helpers (output also stored in the bucket) |
| `run_all.sh stage` | laptop | checks the tree is clean and `netspout/ backend/ src/` + build script at HEAD equal the approved commit `91af353`; checks the v2.0.1 asset sha `53f09e5f…`; uploads `git archive` of the approved commit and of HEAD (harness) and the v2.0.1 asset; downloads them on the instance |
| `remote_bootstrap.sh` | instance | Docker, Python venv + psutil, Node 22 copied out of the repo's own digest-pinned node image (no `curl \| bash`), Playwright Chromium, pulls both Splunk images by digest, sets the 10 h timer |
| `remote_build.sh` | instance | verifies the archive is the approved commit (`git get-tar-commit-id`), builds `netspout.spl` twice (second from an empty wheel cache and touched files), compares the two, and compares with the approved sha256 `4bf1d214…` **and** the approved uncompressed-tar sha256 `99c23bbb…` (gzip bytes can differ across zlib builds with identical content; both are reported, and the artifact tested is the one built here, with its hash recorded) |
| `remote_run_version.sh <label> <image> <sustained_s>` | instance | the whole suite for one Splunk version (steps below); logs PASS/FAIL per step, never aborts |
| `phase17_sustained.py` | instance | the load test (below) |
| `05_collect.sh` | laptop | evidence tarball → bucket → laptop, sha256 verified, extracted into `docs/verification/evidence/phase17/aws-native-x86_64/` |
| `99_cleanup.sh` | laptop | deletes only IDs in the state file after listing them and **asking you to type DELETE**; refuses until evidence is collected; verifies afterwards |

Suite per version (`remote_run_version.sh`): start a fresh container with disposable volumes and generated random credentials (never stored in the repo) → host/runtime probe → install **only** `netspout.spl` through Splunk Web (Playwright upload) → restart → census (one launcher + one engine, no new listening port) → 3-min zero-idle window (events *indexed*, all non-internal indexes) → browser spec (managed status, first-run configuration, tested connection, Generate Data, viewer) → Cisco/Fortinet/Palo Alto events, IOS XR metrics with `mstats`, Palo Alto scenario + dashboard searches, streaming limits, access control → engine kill, launcher kill + Restart engine, `splunk stop`/`start`, restart (events verified after each) → **sustained load** → 3-min idle window → uninstall → install the released v2.0.1, set a legacy Engine URL and a customer macro, upgrade through Splunk Web, compare `local/` byte-for-byte, idle window, first-run UI and workflows → remove the container and volumes.

Sustained test (`phase17_sustained.py`, native mode): one `pan:traffic` run, `duration` mode, `eps=200`, 3,600 s (10.6.1.1) / 900 s (10.2.7, extendable). Measured every 15 s: engine/launcher/splunkd **CPU% (psutil, per process) and RSS**, run counters, rejected/unknown, recent engine errors, search latency, index and filesystem **disk use**. After the run: **indexed events per minute** (by index time, full minutes only), **indexing lag** (`_indextime − _time` percentiles; negative values are possible because the engine stamps events slightly ahead, so it is labelled an upper bound), **seconds from the last event sent until every accepted event is searchable**, **dropped events = accepted − independently indexed**, Splunk's own HEC/listener warnings and blocked-queue counts in the window, engine verification. The host label and `native: true` are stored in the evidence.

Pre-declared reading of the result: the ceiling counts as **reached** only if attempts/s averaged ≥ 190 and 0 events were rejected or dropped; anything lower is reported as the measured number and the matrix keeps the gate open. Nothing in the matrix or support statement is changed except from these files.

## 3. Exact commands (after your approval)

```bash
cd /Users/mahamudc/netspout/phase17-wt/scripts/aws
export P17_REGION=us-east-1            # or ca-central-1; export AWS_PROFILE=<profile> if not default
. ./env.sh                              # prints nothing, creates nothing
./01_create.sh                          # type CREATE when asked; charges start here
. ./env.sh && ./run_all.sh stage        # uploads sources, downloads on the instance
./run_all.sh bootstrap                  # ~10 min
./run_all.sh build                      # reproducibility + hash report (build_report.json)
./run_all.sh primary                    # Splunk 10.6.1.1, 3,600 s load; polls every 2 min; re-runnable with `collect` if your laptop sleeps
./run_all.sh compat                     # Splunk 10.2.7, 900 s load (export P17_SUSTAIN_COMPAT=3600 first for a full hour)
./run_all.sh collect                    # evidence → repo, sha256 verified
# review the evidence, then:
./99_cleanup.sh                         # type DELETE when asked
```
Progress at any time: `. ./env.sh && . ./ssm.sh && ssm_tail run_primary 40`.

## 4. After the run (no further AWS needed)

I update `PHASE17_VALIDATION_MATRIX.md`, `SUPPORT_STATEMENT.md`, `RELEASE_NOTES_DRAFT.md` and the PR body from `aws-native-x86_64/` only, keep the emulated results in their own sections, and mark any gate that did not pass as open. PR #11 stays a draft; nothing is published or merged.

## 5. Cleanup plan

`99_cleanup.sh` terminates the instance (its volume is delete-on-termination; the volume ID is recorded first and checked afterwards), deletes the security group, removes the role from and deletes the instance profile, detaches/deletes role policies and the role, empties and deletes the bucket (only that bucket), then prints the state of each ID and the count of remaining instances tagged `Project=netspout-phase17` (must be 0). It deletes nothing that is not in the state file and touches no pre-existing resource. If anything is left over, the same script is safe to re-run; the 10-hour guardrail also removes the instance and volume on its own.

## 6. Risks and assumptions (stated, not hidden)

- `remote_run_version.sh` is new and has not been executed end-to-end (only syntax-checked); each step logs PASS/FAIL, a failed step does not stop the run, and individual steps can be re-run. The pieces it calls (acceptance driver, census, sustained script, Playwright spec) ran many times locally.
- Downloads at run time come from Ubuntu apt, Docker Hub (Splunk images by digest; anonymous pull limits could delay), PyPI (pinned wheels), the Playwright CDN and Canonical's `aws-cli` snap. None is pinned by hash except the Splunk and Node images.
- The Docker host on EC2 is native x86_64, but Splunk runs in a container; this is the same image used in the earlier validation, not a package installation on the host OS.
- Splunk Web is exercised headless on the instance; no screenshots of a human-driven browser.
- One instance runs both versions one after the other, so the two evidence sets are comparable but not simultaneous.
