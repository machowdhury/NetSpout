#!/usr/bin/env python3
"""Install or remove ONE add-on in the isolated TA-validation lab (container netspout_tavalidation_splunk only).

  python scripts/lab_ta.py install PACKAGE.(spl|tgz|tar.gz) [ENVFILE]     copies the package into the lab container's /tmp and installs it with Splunk's app REST endpoint
  python scripts/lab_ta.py remove APP_ID [ENVFILE]                       removes an installed add-on
  python scripts/lab_ta.py apps [ENVFILE]                                lists installed non-Splunk add-ons

The package stays outside the repository. Refuses to run against any container other than the TA-validation lab.
"""
import json
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts")]
import ta_compat  # noqa: E402

CONTAINER = "netspout_tavalidation_splunk"
ENV = str(ROOT / "tests/lab/ta_validation/.env.lab")
BUILTIN = ("splunk", "SplunkForwarder", "SplunkLightForwarder", "SplunkDeploymentServerConfig", "alert", "appsbrowser", "audit_trail", "introspection", "journald", "launcher", "learned", "legacy", "python_upgrade", "sample_app", "search", "user-prefs", "framework", "gettingstarted")


def main(a):
    cmd = a[0]
    env = a[-1] if a[-1].endswith(".env.lab") else ENV
    lab = ta_compat.Lab(env)
    if cmd == "install":
        pkg = Path(a[1]).expanduser()
        dest = "/tmp/lab_ta_" + pkg.name
        subprocess.run(["docker", "cp", str(pkg), "%s:%s" % (CONTAINER, dest)], check=True)
        r = lab.rest("/services/apps/local?output_mode=json", {"name": dest, "filename": "true", "update": "true"})
        c = r["entry"][0]
        print(json.dumps({"installed": c["name"], "version": c["content"].get("version"), "label": c["content"].get("label"), "disabled": c["content"].get("disabled")}))
    elif cmd == "remove":
        req = urllib.request.Request(lab.mgmt + "/services/apps/local/%s?output_mode=json" % urllib.parse.quote(a[1]), method="DELETE", headers={"Authorization": lab.auth})
        urllib.request.urlopen(req, context=lab.ctx, timeout=300).read()
        print("removed", a[1])
    elif cmd == "apps":
        print(json.dumps(sorted((e["name"], e["content"].get("version")) for e in lab.rest("/services/apps/local?output_mode=json&count=0")["entry"] if not e["name"].startswith(BUILTIN))))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv[1:])
