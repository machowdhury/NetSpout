# Install PulseForge

Choose one.

- **[A. Docker](#a-docker)**: a complete evaluation environment, including Splunk.
- **[B. Splunk Enterprise app](#b-splunk-enterprise-app)**: the app in a Splunk you already run, with the PulseForge engine on a host it can reach.

For Splunk Cloud, read the [Cloud guide](guides/04_SPLUNK_CLOUD_GUIDE.md) instead.

---

## A. Docker

> **Status:** the Compose file validates and the same stack was exercised in earlier lab runs. A clean-checkout `docker compose up -d` for this exact release has **not** been repeated yet.

**Prerequisites:** Docker with Compose v2; about 8 GB of free memory and 20 GB of disk (recommended, not measured); free port 8000. The image is `linux/amd64`, so Apple Silicon runs it under emulation and is slower.

**Install**
1. `git clone https://github.com/machowdhury/NetSpout.git && cd NetSpout`
2. `cp .env.example .env`, then edit `.env` and set:
   - `SPLUNK_PASSWORD`: the Splunk `admin` password **you choose**: at least 8 characters, letters and digits only (`$ # " '` and spaces break Docker Compose). For example `python3 -c "import secrets; print('Ns' + secrets.token_hex(12))"`.
   - `SPLUNK_HEC_TOKEN`: any new GUID, for example `python3 -c "import uuid; print(uuid.uuid4())"`.
   Both are required; Compose refuses to start with either empty. `.env` is git-ignored. Never commit it or share it.
   **Splunk stores the password the first time it starts with a new data volume, and the value in `.env` must match it from then on.** Do not edit it between starts without also changing it in Splunk (see below).
3. `docker compose up -d` (the first start builds the image and takes several minutes). **Let the first start finish: do not stop, restart or interrupt it until step 4 shows healthy.**
4. `docker compose ps` until `splunk-netspout` shows **healthy**.

**Log in and open PulseForge**
1. Browse to `http://localhost:8000`. User `admin`, password = your `SPLUNK_PASSWORD`.
2. **Change it now:** top-right *Administrator* → *Account settings* → *Change password*.
3. Then update `SPLUNK_PASSWORD` in `.env` to the new value and run `docker compose up -d`, so PulseForge's verification search can still sign in.
4. Open **Apps → NetSpout PulseForge**.

Use PulseForge through Splunk Web. The file also publishes the engine's own API and Splunk's management port on `127.0.0.1` only (8081 and 8089); you do not need them. Every published port is loopback-only.

**Quick check:** the Command Center loads, then follow the [Quickstart](QUICKSTART.md).
**Upgrade:** `git pull && docker compose up -d --build`. Data volumes are kept.
**Uninstall:** `docker compose down` keeps your data; `docker compose down -v` deletes it.

**Troubleshooting:** if Splunk never turns healthy, run `docker compose logs splunk-netspout`. `401 Unauthorized` and a container that keeps restarting mean `.env` no longer matches the password Splunk stored (or the first start was interrupted): fix `.env` to the right password, or, on a new install with nothing to keep, run `docker compose down -v`, edit `.env` and `docker compose up -d`. A short password is the other usual cause. More in [Troubleshooting](TROUBLESHOOTING.md).

---

## B. Splunk Enterprise app

> **Status:** verified end to end on Splunk Enterprise 10.2.7 in an isolated Docker lab. A VM or physical-host install follows the same steps but was not run.

This release has **two parts**: the app (`netspout.spl`, a versioned release artifact: it is not stored in Git, see [Release artifacts](RELEASE_ARTIFACTS.md)) and the PulseForge engine, which generates the telemetry. You run the engine yourself. Splunk starts nothing for you.

**Prerequisites:** Splunk Enterprise and an account that can install apps; a host for the engine with Python 3.11 or newer; HEC enabled with a token for an index you are allowed to write to.

**Install the app**
1. Splunk Web → *Apps* → *Manage Apps* → *Install app from file*, choose the `netspout.spl` you downloaded (verify it against `SHA256SUMS`), restart Splunk if asked.

**Install and start the engine** (from `pulseforge-engine.tar.gz`)
```bash
sudo tar xzf pulseforge-engine.tar.gz -C /opt
/opt/pulseforge-engine/deploy/engine/install.sh
sudo install -m 600 /opt/pulseforge-engine/deploy/engine/engine.env.example /etc/pulseforge/engine.env   # edit: port, state directory, secrets
/opt/pulseforge-engine/deploy/engine/pulseforge-engine
```
The engine listens on `127.0.0.1:8081` by default. Enter its URL once under **Connections > PulseForge Engine** in the app (there is no default and no environment variable; see the upgrade notes in `contracts/phase11/PHASE11_UPGRADE.md`); a systemd unit and the other steps are in [the installation guide](guides/03_INSTALLATION.md). **You use PulseForge through Splunk Web, not through the engine's port.**

**Who can do what:** the Splunk roles `admin`, `sc_admin` and `power` can start runs and change settings; other roles are read-only.

**First use:** open **PulseForge Onboarding** (the Setup Wizard & Connection Center) and enter your HEC URL and token, the search endpoint and its credentials, and the indexes PulseForge may use.

**Upgrade:** install the newer `netspout.spl` over the old one, restart Splunk, and keep the engine's state directory.
**Uninstall:** *Manage Apps* → *Delete*, stop the engine, and delete its state directory. Your indexes and data stay.
**Troubleshooting:** pages say the engine is unreachable → check that it is running and that the URL under Connections > PulseForge Engine is right ([Troubleshooting](TROUBLESHOOTING.md)).
