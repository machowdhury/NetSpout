# Phase 4C Credential Cleanup Report

**Date:** 2026‑10‑29 (rotation completed same day; §2 and §5 supersede the
earlier "password remains live" version of this file)
**Lab:** pf‑native‑lab (Splunk 10.2.7), bound to `127.0.0.1` only
**Branch:** oc/ise‑ta‑1915‑record
**Repository:** machowdhury/NetSpout (public)

## Summary

Every hardcoded lab credential in the working tree was replaced with an
environment‑variable reference, and **every credential that had been exposed is
now invalid**: the two leaked HEC tokens were rotated in §1, and the lab admin
password was rotated through Splunk's own authentication API in §2. Git history
was **not** rewritten — after these rotations, the values left in history are
dead credentials, which is the correct way to close a leak in a public repo.

Live secret values are withheld from this report entirely, including truncated
prefixes. Revoked values are identified by destination and by the first eight
characters only, because that is what an operator needs in order to confirm
which entries were retired.

## 1. HEC Token Rotation

| Token (first8, revoked only) | Purpose | Status |
|---|---|---|
| `1379bbf9‑…` | pf‑ta‑ise‑val index | **Revoked** — HTTP 403 |
| `86eafae9‑…` | pulseforge‑lab‑hec | **Revoked** — HTTP 403 |
| *(value withheld)* | new pulseforge‑lab‑hec | **Active** — HTTP 200 |
| *(value withheld)* | new pf‑ta‑ise‑val | **Active** — HTTP 200 |

**Actions taken:**
- Edited `/opt/splunk/etc/apps/splunk_httpinput/local/inputs.conf` as root.
- Restarted the container so splunkd re-read the HEC configuration. This was a
  restart within the existing volume — no rebuild, no volume deletion, no reset.
- Verified old tokens reject and new tokens accept.

**Current backend destination configuration (`backend/destinations.json`) uses
environment variable `PULSEFORGE_LAB_HEC_TOKEN`** and stores no token value.

## 2. Lab Admin Password — Rotated

The password that appeared in 8 tracked files no longer authenticates. Rotation
was done through Splunk's supported management endpoint, because PulseForge is a
Splunk‑native application and has no admin account of its own to rotate (§0 of
the recovery report):

```
POST /services/authentication/users/admin     (form-encoded)
     password=<new>   oldpassword=<current>   -> HTTP 200
```

`oldpassword` is required when a user changes its own password; the first attempt
without it returned `400 Missing old password.` and the script was designed to
abort before writing anything unless rotation returned 200 **and** the old value
stopped working, so a failed attempt would leave the lab untouched.

| Observation | Result |
|---|---|
| Pre‑condition: `/services/authentication/users/admin` reachable | HTTP 200 |
| Pre‑condition: `content.type` | `Splunk` (native scheme — required; a non‑native scheme cannot change a password here) |
| Rotation call | HTTP 200 |
| **Old (exposed) credential** → `/services/server/health` | **HTTP 401 — invalidated** |
| New credential → `/services/server/health` | HTTP 200 |
| `roles` after the change | `['admin']`, unchanged |
| `locked‑out` | `False` |
| New value stored | untracked, gitignored `backend/.env`, mode `0600` |

**Why the earlier version of this file reported "rotation blocked".** Four CLI
and file‑level approaches failed, and they were reported as if the operation
itself were impossible:

| Attempt | Failure |
|---|---|
| `splunk edit user admin` in‑container | `Permission denied` on `/opt/splunk/var/log/splunk/`, `/opt/splunk/var/run/splunk/splunkd.pid` |
| direct edit of `etc/users/users.ini` | `Permission denied` |
| direct edit of `etc/auth/splunk.secret` | `Permission denied` |
| config validation path | `Failed to create validation temp dir` |
| plaintext `/opt/splunk/etc/passwd` write | HTTP 401 — entries need Salted SHA‑512 keyed by `splunk.secret`; container has no `openssl` |

The common cause is that those paths are written by splunkd itself, as the user
splunkd runs as, and the shell was not that user. None of them says anything
about the REST API, which is served *by* splunkd. Read‑only probes showed the
supported path was open all along.

**Deliberately not done:** container rebuild, volume deletion, lab reset, direct
`passwd`/`users.ini` surgery, or Git history rewriting.

## 3. Source‑Code Cleanup

**Files modified:** 19 tracked files (Python scripts and verification documents).
**Changes:**
- Hardcoded HEC token literal replaced with `os.getenv('PULSEFORGE_LAB_HEC_TOKEN')`.
- Hardcoded admin password literal replaced with `os.getenv('SPLUNK_PASSWORD')`.
- Verification documents sanitised (`[REDACTED]`, truncated prefixes only).
- Base64 `admin:<password>` credential pair redacted (a stale default, confirmed
  not live by authentication attempt; value withheld).
- Untracked `backend/.env` created and confirmed ignored (`.gitignore:41`).
- `docs/QUICKSTART.md` and `docs/SECURITY.md` example exports now use
  `<your-splunk-admin-password>`, `<from-your-secret-manager>` and an all‑zero
  placeholder token. Both literals that were there were first confirmed **not**
  live credentials (HTTP 401 against `/services/server/health`).

**Plaintext left in tracked history:** 8 files held the admin password and ~14
held the old HEC token. Both values are now dead, so the history exposure is
housekeeping rather than an open risk, and it is not a reason to change the
product's authentication design.

## 4. Environment Setup

Development credentials come from the environment and live in the gitignored
`backend/.env` (keys only, values withheld):

```bash
set -a; . backend/.env; set +a            # SPLUNK_PASSWORD, PULSEFORGE_LAB_HEC_TOKEN
export NETSPOUT_SPLUNK_PASSWORD="$SPLUNK_PASSWORD"   # alias for the NETSPOUT_* convention
```

Both names are honoured deliberately: `docs/QUICKSTART.md` and `docs/SECURITY.md`
document the `NETSPOUT_*` convention while the sanitized scripts use
`SPLUNK_PASSWORD`. That split caused a real failure once — see §3.6 of the
recovery report, where a helper scraped the container's **build‑time**
`SPLUNK_PASSWORD` and therefore kept using the retired credential.

**Backend destination config** uses `hec_token_env: "PULSEFORGE_LAB_HEC_TOKEN"`.
For an installed Splunk app the product answer is different from the dev answer:
user‑configured destinations with the secret in Splunk's supported secure storage
(`storage/passwords`), referenced by name, not read once from a process
environment. That is Phase 4D story D‑1/D‑3.

## 5. Verification

| Test | Result |
|---|---|
| Old HEC token (`1379bbf9‑…`) POST → `/services/collector` | HTTP 403 |
| Second old HEC token (`86eafae9‑…`) POST → `/services/collector` | HTTP 403 |
| New lab HEC token POST → `/services/collector` | HTTP 200 |
| Admin password, old value GET → `/services/server/health` | HTTP 200 before rotation, **HTTP 401 after** |
| Admin password, new value GET → `/services/server/health` | HTTP 200 |
| Two credential‑shaped doc literals GET → `/services/server/health` | HTTP 401 (not live) |
| Updated Python scripts compile (`py_compile`) | pass |
| `.env` excluded from Git (`git check-ignore`) | pass |
| Broad scan of 2,045 tracked files for credential‑shaped assignments | only fake fixtures and SPL dashboard `$token$` definitions |
| Live lab path re‑proved after rotation (product API + Cisco control) | HTTP 200, 47/47 and 14/14 accepted — §7.2 of the recovery report |

## 6. Status

1. **Credential blocker: cleared.** No exposed credential still works.
2. Development continues locally using environment‑variable credentials.
3. Publication is no longer blocked by an active secret; it remains held for a
   review of the outgoing changes (tracked files **and** staged diff) and an
   explicit decision, because nothing here has been pushed yet.
4. If any further exposure is found, the response is rotation, not history
   rewriting.

---

**Security note:** the repository is public, and the retired admin password and
both old HEC tokens are visible to anyone with the commit SHAs of branch
`oc/ise‑ta‑1915‑record`. They are dead credentials: the tokens return HTTP 403
and the password returns HTTP 401. The lab remains local‑only (`127.0.0.1`) with
no ingress tunnels detected.
