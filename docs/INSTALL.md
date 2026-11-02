# Install PulseForge

Choose one. You never need to install or run a separate Python engine for either.

- **[A. Docker](#a-docker)**: a complete evaluation environment, including Splunk.
- **[B. Splunk Enterprise app](#b-splunk-enterprise-app)**: one `.spl` into the Splunk you already run.

For Splunk Cloud, read the [Cloud guide](guides/04_SPLUNK_CLOUD_GUIDE.md) instead.

---

## A. Docker

> **Status:** the Compose file validates, and the same stack was exercised in earlier lab runs. A clean-checkout `docker compose up -d` for this exact revision has **not** been repeated yet.

**Prerequisites:** Docker with Compose v2; about 8 GB of free memory and 20 GB of disk (recommended, not measured); a free port 8000. The image is `linux/amd64`, so Apple Silicon runs it under emulation and is slower.

**Install**
1. `git clone https://github.com/machowdhury/NetSpout.git && cd NetSpout`
2. `cp .env.example .env`, then edit `.env` and set:
   - `SPLUNK_PASSWORD`: the Splunk `admin` password **you choose** (at least 8 characters).
   - `SPLUNK_HEC_TOKEN`: any new GUID, for example `python3 -c "import uuid; print(uuid.uuid4())"`.
   `.env` is git-ignored. Never commit it or share it.
3. `docker compose up -d` (the first start builds the image and takes several minutes).
4. `docker compose ps` until `splunk-netspout` shows **healthy**.

**Log in and open PulseForge**
1. Browse to `http://localhost:8000`. User `admin`, password = your `SPLUNK_PASSWORD`.
2. **Change it now:** top-right *Administrator* → *Account settings* → *Change password*.
3. Then update `SPLUNK_PASSWORD` in `.env` to the new value and run `docker compose up -d`, so PulseForge's verification search can still sign in.
4. Open **Apps → NetSpout PulseForge**.

You use PulseForge only through Splunk Web. The engine runs inside the container and is not published. Every published port is bound to `127.0.0.1`; Splunk's management port (8089) is not published.

**Quick check:** the Command Center loads, then follow the [Quickstart](QUICKSTART.md).

**Upgrade:** `git pull && docker compose up -d --build`. Data volumes are kept.
**Uninstall:** `docker compose down` keeps your data; `docker compose down -v` deletes it.

**Troubleshooting**
- Splunk never turns healthy: `docker compose logs splunk-netspout`. A password that is too short or missing is the usual cause.
- Port 8000 busy: stop the other service; the port is fixed in `docker-compose.yml`.
- Anything else: [Troubleshooting](TROUBLESHOOTING.md).

---

## B. Splunk Enterprise app

> **Status:** validated on one host: Splunk Enterprise 10.6.1.1, Ubuntu 24.04, x86_64, using Splunk's bundled Python 3.13. Other versions and platforms are not tested.
> **Which file:** the single-package build is produced by `python scripts/build_single_package_test.py` (output in `build/single_package_test/`). The `netspout.spl` currently in the repository root is the earlier package that needs a separately run engine; it will be replaced after the new build is approved.

**Prerequisites:** Splunk Enterprise 10.6.1.1 on Linux x86_64 and an account that can install apps. HEC enabled with a token for an index you are allowed to write to, if you want to send data to this Splunk.

**Install**
1. Splunk Web → *Apps* → *Manage Apps* → *Install app from file*.
2. Choose the `.spl` and upload. Restart Splunk when asked.
3. Open **Apps → NetSpout PulseForge**. Splunk starts the PulseForge engine itself; there is nothing else to run.

**Who can do what:** `netspout_view` is read-only; `netspout_admin` is needed to start runs and change settings. By default `admin`, `sc_admin` and `power` have `netspout_admin`, and the `user` role has `netspout_view`. Access changes can take about 30 seconds to apply.

**First use:** open **PulseForge Onboarding** (the Setup Wizard & Connection Center) and enter your HEC URL and token, the search endpoint and its credentials, and the indexes PulseForge may use. For HEC on the same Splunk: `https://127.0.0.1:8088/services/collector/event`, and the search endpoint is the full URL `https://127.0.0.1:8089/services/search/jobs/export`. Those two secrets are held in the engine's memory only, so enter them again after the engine restarts.

**Quick check:** the Command Center loads. Optional: `curl -sk -u <user> https://localhost:8089/services/netspout_gateway/api/health` returns `healthy` JSON. Then follow the [Quickstart](QUICKSTART.md).

**Upgrade:** install the newer `.spl` over the old one (*Upgrade app*), then restart Splunk. Settings are kept.
**Uninstall:** *Manage Apps* → *Delete*. The engine stops and your indexes and data stay. To remove PulseForge's own files too, delete `$SPLUNK_HOME/var/lib/netspout`.

**Troubleshooting**
- Pages say the engine is not running: restart Splunk. If the engine process is killed, Splunk does not restart it until Splunk itself restarts.
- Look in `$SPLUNK_HOME/var/log/splunk/splunkd.log` for `pulseforge`.
- A user sees "capability required": give the role `netspout_view` or `netspout_admin`.
- More: [Troubleshooting](TROUBLESHOOTING.md).

You do **not** need a Python environment, `pip`, Uvicorn, a separate engine login, edits to `splunk-launch.conf`, or access to port 8081.
