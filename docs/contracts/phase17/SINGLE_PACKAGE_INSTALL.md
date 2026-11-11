# NetSpout PulseForge single-package install (Splunk Enterprise) — CANDIDATE, not a release

Status: implementation candidate on branch `feature/single-package-enterprise`. Published pre-release **v2.0.1 is unchanged** and still needs its separate engine; nothing here is published. App version in this build: `2.1.0`.

## Install (Splunk Web only)

1. Download `netspout.spl` (the single-package build).
2. Splunk Web > **Apps > Manage Apps > Install app from file**, choose the file, **Upload**.
3. Restart Splunk when asked.
4. Create the indexes you want to allow (Settings > Indexes). Outside the Docker lab the event index name must start with `dev_`; a metrics index must be a *metrics* index whose name contains `metric`.
5. Open **NetSpout PulseForge > Connections**. The page shows *"PulseForge engine is managed by Splunk (healthy)"*; there is no engine address to enter. Fill in the HEC endpoint and token, the search endpoint and a search user/credential, the allowed indexes, and **Save**. Saving credentials needs an **admin** role (it writes to Splunk's encrypted credential store). Use **Test connection**.
6. **Generate Data** or **Scenarios**. For a non-lab destination tick *"I authorize sending synthetic test data to <index>"* first; nothing is sent until you do. The result says whether Splunk found the events.

No SSH, shell, Docker, Python install or separate engine package is needed.

## Who can do what

| Splunk capability | Allowed |
|---|---|
| `netspout_view` (role `user` and everything that inherits it) | read-only use |
| `netspout_admin` (roles `admin`, `sc_admin`, `power`) | start, stop and configure runs |
| `edit_storage_passwords` (role `admin`) | save the HEC token and search credential |

## What Splunk starts for you

A modular input `pulseforge_engine_launcher` starts one engine process (as the Splunk OS user, on Splunk's bundled Python 3.13, at lower priority) and restarts it if it dies. It listens on a Unix socket (mode 0600) inside `$SPLUNK_HOME/var/lib/netspout`, not on a network port; every request needs a per-install key that only the Splunk gateway holds. The launcher and the idle engine write no events. Streaming is bounded: at most 200 events/s and 3,600 s per stream (an open-ended request gets the 3,600 s limit; the ceiling itself has not been reached in testing, see the validation matrix), at most 4 runs at once.

If the engine is down, Connections says so and offers **Restart engine** (admin).

## Supported and not supported

Supported (tested): Splunk Enterprise **10.6.1** (primary) and 10.2.7, Linux x86_64 image (tested under emulation on an arm64 host), single instance, Python 3.13.
Not supported: **Splunk Cloud**, distributed deployments (the launcher would start on every instance that has the app), Windows, macOS, aarch64 hosts, other Splunk versions (untested), native-hardware performance (untested), native gNMI/SNMP/syslog/IPFIX listeners (not part of this promise).

## Uninstall

Remove the app in Splunk Web. The engine stops; indexed data stays. `$SPLUNK_HOME/var/lib/netspout` (settings, the per-install key) is left behind; delete it if you want a clean slate. Credentials are kept in the app's own `local/passwords.conf`, which is removed with the app directory.
