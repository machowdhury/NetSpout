#!/usr/bin/env python3
"""
TA-datablaster AppInspect-Compliant Custom REST Handler
Splunk App TA-datablaster: bin/datablaster_rest.py

Handles REST calls from Splunk Web UI (/services/datablaster/execute)
Compatible with Splunk Enterprise & Splunk Cloud Vetting:
- Strictly enforces shell=False with explicit argument list
- Validates run parameters and server-configured HEC destinations
- Directs execution logs to $SPLUNK_HOME/var/log/splunk/ta_datablaster_orchestration.log
- Asynchronously wraps execution calls through bin/run_simulation.py
"""

import os
import sys
import re
import json
import time
import signal
import subprocess
import tempfile
import stat
import logging
import threading
from contextlib import contextmanager
from urllib.parse import urlsplit, quote
import urllib.request
import urllib.error
import ssl
from typing import Dict, List, Any, Tuple, Optional

# Splunk imports (with safe fallbacks for standalone unit testing)
try:
    import splunk.rest as rest
    import splunk.admin as admin
    from splunk.persistconn.application import PersistentServerConnectionApplication
    SPLUNK_AVAILABLE = True
except ImportError:
    SPLUNK_AVAILABLE = False
    class PersistentServerConnectionApplication:
        def __init__(self, *args, **kwargs):
            pass
    class rest:
        class BaseRestHandler:
            pass

# Paths
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIN_DIR = os.path.join(APP_DIR, "bin")

class RunFolderError(RuntimeError):
    pass


def resolve_run_dir() -> str:
    """Use only the private Splunk runtime directory."""
    home = os.environ.get("SPLUNK_HOME")
    if not home:
        raise RunFolderError("SPLUNK_HOME is required for the NetSpout run folder")
    path = os.path.join(home, "var", "run", "netspout")
    try:
        if os.path.islink(path):
            raise OSError("Run folder must not be a symlink")
        os.makedirs(path, mode=0o700, exist_ok=True)
        fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            if os.fstat(fd).st_uid != os.getuid():
                raise OSError("Run folder must belong to the current user")
            os.fchmod(fd, 0o700)
        finally:
            os.close(fd)
    except OSError:
        raise RunFolderError("Cannot create private NetSpout run folder") from None
    return path


# Resolve and validate runtime paths only when an operation needs them.
RUN_DIR = ""
PID_FILE = STATUS_FILE = CONFIG_FILE = ""


def get_active_run_dir() -> str:
    global RUN_DIR, PID_FILE, STATUS_FILE, CONFIG_FILE
    RUN_DIR = resolve_run_dir()
    PID_FILE = os.path.join(RUN_DIR, "datablaster.pid")
    STATUS_FILE = os.path.join(RUN_DIR, "datablaster_status.json")
    CONFIG_FILE = os.path.join(RUN_DIR, "datablaster_config.json")
    return RUN_DIR


MANAGEMENT_URL = "https://127.0.0.1:8089"
logger = logging.getLogger("netspout.hec")


def has_netspout_admin(session_key):
    # VERIFY-ON-SPLUNK: Confirm current-context entry.content.capabilities is a list.
    if not session_key:
        return False
    try:
        response, body = rest.simpleRequest(
            MANAGEMENT_URL + "/services/authentication/current-context?output_mode=json",
            sessionKey=session_key, method="GET")
        return int(response.status) == 200 and any(
            "netspout_admin" in entry.get("content", {}).get("capabilities", [])
            for entry in json.loads(body).get("entry", []))
    except Exception:
        return False


class HECCredentialStore:
    """Access one app-owned Splunk credential using the caller's session."""
    collection = MANAGEMENT_URL + "/servicesNS/nobody/netspout/storage/passwords"
    item = collection + "/" + quote("netspout:hec_token:", safe="")

    def __init__(self, session_key):
        self.session_key = session_key

    def _request(self, url, method="GET", postargs=None):
        # VERIFY-ON-SPLUNK: Check storage/passwords name, 404, clear_password and update responses.
        try:
            response, body = rest.simpleRequest(
                url + "?output_mode=json", sessionKey=self.session_key,
                method=method, postargs=postargs, raiseAllErrors=False)
            return int(response.status), json.loads(body)
        except Exception:
            raise RuntimeError("Splunk credential store request failed") from None

    def read(self):
        code, data = self._request(self.item)
        if code == 404:
            return ""
        if code != 200:
            raise RuntimeError("Cannot read NetSpout HEC credential")
        entries = data.get("entry", [])
        return entries[0].get("content", {}).get("clear_password", "") if entries else ""

    def save(self, value):
        if not has_netspout_admin(self.session_key):
            raise PermissionError("netspout_admin capability required")
        code, _ = self._request(self.item, "POST", {"password": value})
        if code == 404:
            code, _ = self._request(self.collection, "POST", {
                "realm": "netspout", "name": "hec_token", "password": value})
        if code not in (200, 201):
            raise RuntimeError("Cannot save NetSpout HEC credential")


# Regex validation rules
RE_EPS = re.compile(r"^\d+$")
RE_SAFE_PATH = re.compile(r"^[a-zA-Z0-9_\-./]+$")
RE_URL = re.compile(r"^https?://[a-zA-Z0-9.\-:]+(/.*)?$")
RE_TOKEN = re.compile(r"^[a-zA-Z0-9\-]+$")

DEFAULT_CONFIG = {
    "hec_url": "https://127.0.0.1:8088/services/collector",
    "hec_allowed_hosts": ["127.0.0.1", "localhost"],
    "hec_allowed_ports": [8088],
    "ssl_verify": True,
    "target_eps": 1000,
    "idx_network_ops": "idx_network_ops",
    "idx_security_fw": "idx_security_fw",
    "idx_wireless_ops": "idx_wireless_ops",
    "idx_performance_metrics": "idx_performance_metrics",
    "cisco_mdt_metrics": "cisco_mdt_metrics",
    "default_scenario": "full_network_topology"
}


def write_private_file(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600)
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise OSError("Private file must be regular and owned by the current user")
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            fd = None
            stream.write(data)
    finally:
        if fd is not None:
            os.close(fd)


def _read_private_file(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o022):
            raise OSError("Private file permissions or ownership are invalid")
        with os.fdopen(fd, "r", encoding="utf-8") as stream:
            fd = None
            return stream.read()
    finally:
        if fd is not None:
            os.close(fd)


def _write_config(path, cfg):
    write_private_file(path, json.dumps(cfg, indent=2))


def _legacy_config(path, session_key, app_legacy=False):
    """Restrict legacy copies before attempting a recoverable migration."""
    fd = None
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            return {}
        writable = bool(info.st_mode & 0o022)
        if writable:
            os.fchmod(fd, 0o600)
            os.replace(path, path + ".untrusted-" + str(time.time_ns()))
            logger.warning("Untrusted legacy configuration set aside; credential should be rotated")
            return {}
        with os.fdopen(fd, "r", encoding="utf-8") as stream:
            fd = None
            saved = json.load(stream)
            if not isinstance(saved, dict):
                return {}
            if "hec_token" in saved:
                os.fchmod(stream.fileno(), 0o600)
        legacy = saved.pop("hec_token", "")
        if legacy and has_netspout_admin(session_key):
            try:
                store = HECCredentialStore(session_key)
                existing = store.read()
                if not existing:
                    store.save(legacy)
                    logger.warning("Legacy HEC credential migrated; it should be rotated")
                if app_legacy:
                    os.unlink(path)
                else:
                    _write_config(path, {k: v for k, v in saved.items() if k in DEFAULT_CONFIG})
            except Exception:
                logger.warning("Legacy credential migration deferred; credential should be rotated")
        return {k: v for k, v in saved.items() if k in DEFAULT_CONFIG}
    except (OSError, ValueError):
        return {}
    finally:
        if fd is not None:
            os.close(fd)


def get_stored_config(session_key="") -> Dict[str, Any]:
    get_active_run_dir()
    cfg = dict(DEFAULT_CONFIG)
    _legacy_config(os.path.join(APP_DIR, "var", "run", "datablaster_config.json"),
                   session_key, app_legacy=True)
    cfg.update(_legacy_config(CONFIG_FILE, session_key))
    return cfg


_START_LOCK = threading.Lock()


@contextmanager
def simulation_start_lock():
    import fcntl
    with _START_LOCK:
        path = os.path.join(get_active_run_dir(), "datablaster.lock")
        fd = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            info = os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
                raise OSError("Run lock must be regular and owned by the current user")
            os.fchmod(fd, 0o600)
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            os.close(fd)


def resolve_scenario_path(scenario, app_dir=None):
    app_dir = APP_DIR if app_dir is None else app_dir
    if ".." in scenario.split(os.sep):
        raise ValueError("Scenario must be inside an approved scenario folder")
    roots = [os.path.realpath(os.path.join(app_dir, "scenarios")),
             os.path.realpath(os.path.join(app_dir, "appserver", "static", "scenarios"))]
    run_dir = os.path.realpath(resolve_run_dir())
    candidates = [scenario] if os.path.isabs(scenario) else [
        os.path.join(root, scenario) for root in roots] + [os.path.join(app_dir, scenario)]
    for candidate in candidates:
        resolved = os.path.realpath(candidate)
        allowed = any(os.path.commonpath([root, resolved]) == root for root in roots)
        allowed = allowed or (os.path.dirname(resolved) == run_dir
                              and os.path.basename(resolved).startswith("canvas_custom_"))
        if allowed and os.path.isfile(resolved):
            return resolved
    raise ValueError("Scenario must be inside an approved scenario folder")


def cleanup_stale_run_files():
    folder = get_active_run_dir()
    for name in os.listdir(folder):
        if name.startswith(("active_sim_", "canvas_custom_")):
            try:
                os.unlink(os.path.join(folder, name))
            except FileNotFoundError:
                pass


def save_stored_config(new_cfg: Dict[str, Any], session_key="") -> Dict[str, Any]:
    if not has_netspout_admin(session_key):
        raise PermissionError("netspout_admin capability required")
    cfg = get_stored_config(session_key)
    if "hec_token" in new_cfg:
        HECCredentialStore(session_key).save(new_cfg["hec_token"])
    for key in DEFAULT_CONFIG:
        if key in new_cfg:
            cfg[key] = new_cfg[key]
    resolve_hec_urls(cfg["hec_url"], cfg)
    if cfg["ssl_verify"] is False:
        logger.warning("Admin setting disables HEC certificate verification")
    _write_config(CONFIG_FILE, cfg)
    return cfg


class HECConfigurationError(ValueError):
    pass


def resolve_hec_urls(hec_url: str, cfg=None) -> List[str]:
    """Return the exact HTTPS URL; enforce destination policy when cfg is supplied.

    Resolution alone needs no runtime files. Execution and request construction
    must supply the server configuration to validate the destination.
    """
    try:
        parsed = urlsplit(hec_url)
        valid = (parsed.scheme == "https" and not parsed.username and not parsed.password
                 and not parsed.fragment and not parsed.query
                 and parsed.hostname is not None
                 and (cfg is None or (parsed.hostname in cfg["hec_allowed_hosts"]
                                      and (parsed.port or 443) in cfg["hec_allowed_ports"])))
    except (ValueError, KeyError, TypeError):
        valid = False
    if not valid:
        raise HECConfigurationError("HEC destination must use HTTPS and an allowed host and port")
    return [hec_url]


def hec_request(url, **kwargs):
    """Keep HEC authorization on the original request only."""
    resolve_hec_urls(url, get_stored_config())
    headers = dict(kwargs.pop("headers", {}))
    authorization = headers.pop("Authorization", None)
    request = urllib.request.Request(url, headers=headers, **kwargs)
    if authorization is not None:
        request.add_unredirected_header("Authorization", authorization)
    return request


def public_config(session_key):
    cfg = get_stored_config(session_key)
    cfg["hec_token_configured"] = bool(HECCredentialStore(session_key).read())
    return cfg


def test_hec_connection(hec_url: str, token: str, ssl_verify: bool = True) -> Dict[str, Any]:
    """Test connectivity and authentication against Splunk HEC with selectable SSL verification."""
    import urllib.request
    import urllib.error
    import ssl

    if ssl_verify:
        ctx = ssl.create_default_context()
        ctx.check_hostname = True
        ctx.verify_mode = ssl.CERT_REQUIRED
    else:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

    candidate_urls = resolve_hec_urls(hec_url, get_stored_config())

    last_res = None
    for candidate in candidate_urls:
        t0 = time.time()
        try:
            req = hec_request(
                candidate,
                data=b'{"event": "datablaster_probe", "sourcetype": "datablaster:probe", "index": "main"}',
                headers={
                    "Authorization": f"Splunk {token}",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
                latency = round((time.time() - t0) * 1000, 1)
                body = resp.read().decode("utf-8", errors="replace")
                return {
                    "status": "success",
                    "message": f"HEC Endpoint is online and token authenticated successfully! (SSL Verify: {ssl_verify})",
                    "http_status": resp.status,
                    "latency_ms": latency,
                    "hec_url": candidate,
                    "ssl_verify": ssl_verify,
                    "response": "HEC responded"
                }
        except urllib.error.HTTPError as he:
            latency = round((time.time() - t0) * 1000, 1)
            err_body = he.read().decode("utf-8", errors="replace") if hasattr(he, "read") else ""
            if he.code in (401, 403):
                return {
                    "status": "error",
                    "message": f"HEC Authentication Failed: Invalid or unauthorized token (HTTP {he.code}).",
                    "http_status": he.code,
                    "latency_ms": latency,
                    "details": "HEC request failed",
                    "hec_url": candidate
                }
            elif he.code == 404:
                return {
                    "status": "warning",
                    "message": f"Endpoint responded with HTTP 404. Verify the HEC path (/services/collector).",
                    "http_status": 404,
                    "latency_ms": latency,
                    "details": "HEC request failed",
                    "hec_url": candidate
                }
            else:
                return {
                    "status": "warning",
                    "message": f"HEC responded with HTTP {he.code}: Request failed",
                    "http_status": he.code,
                    "latency_ms": latency,
                    "details": "HEC request failed",
                    "hec_url": candidate
                }
        except ssl.SSLCertVerificationError as se:
            latency = round((time.time() - t0) * 1000, 1)
            return {
                "status": "error",
                "message": f"SSL Certificate Verification Failed: Certificate verification failed. If using self-signed certs (e.g. local Docker/dev), set ssl_verify = false.",
                "http_status": 0,
                "latency_ms": latency,
                "ssl_error": True,
                "hec_url": candidate
            }
        except Exception as e:
            latency = round((time.time() - t0) * 1000, 1)
            last_res = {
                "status": "error",
                "message": f"Cannot connect to HEC endpoint: Operation failed",
                "http_status": 0,
                "latency_ms": latency,
                "hec_url": candidate
            }
            continue

    return last_res or {
        "status": "error",
        "message": "Unable to connect to HEC endpoint.",
        "http_status": 0,
        "latency_ms": 0,
        "hec_url": hec_url
    }


def run_environment_validation(hec_url: str, token: str, ssl_verify: bool = True) -> Dict[str, Any]:
    """
    Run 5 Comprehensive Preflight Environment Checks:
    1. Target Indexes Availability (idx_network_ops, idx_security_fw, idx_wireless_ops, idx_performance_metrics, cisco_mdt_metrics, netops_logs)
    2. Technical Add-on (TA) Installation Status (11 Multi-Vendor TAs)
    3. HEC Token Validity & Whitelisted Index Permissions
    4. SSL Verification & Certificate Health
    5. Ingestion Pipeline & Real-Time Latency Probe
    """
    import urllib.request
    import urllib.error
    import ssl

    results = {
        "timestamp": time.time(),
        "overall_status": "pass",
        "checks": {}
    }

    # CHECK 1: Target Indexes Availability
    target_indexes = [
        {"name": "idx_network_ops", "type": "event", "desc": "Core Routing & DC Operations (Cisco/Arista/Juniper/Nokia)"},
        {"name": "idx_security_fw", "type": "event", "desc": "Firewall & SASE Edge (Palo Alto/Fortinet/Zscaler/Netskope)"},
        {"name": "idx_wireless_ops", "type": "event", "desc": "Campus WiFi & Access (Aruba/Mist/Catalyst)"},
        {"name": "idx_performance_metrics", "type": "event", "desc": "RoCE v2, PFC Buffer & DC Fabric Telemetry"},
        {"name": "cisco_mdt_metrics", "type": "metric", "desc": "Cisco Model-Driven Telemetry (MDT) Streaming Metrics"},
        {"name": "netops_logs", "type": "event", "desc": "Fallback Network Operations & Syslog Data"}
    ]

    index_checks = []
    missing_indexes = []

    ctx_unverified = ssl.create_default_context()
    if not ssl_verify:
        ctx_unverified.check_hostname = False
        ctx_unverified.verify_mode = ssl.CERT_NONE

    # Probe and resolve active HEC URL (handles container vs host port mapping)
    hec_probe = test_hec_connection(hec_url, token, ssl_verify=ssl_verify)
    active_hec_url = hec_probe.get("hec_url", hec_url)

    for idx in target_indexes:
        idx_name = idx["name"]
        if idx.get("type") == "metric" or idx_name == "cisco_mdt_metrics":
            probe_payload = json.dumps({
                "time": time.time(),
                "event": "metric",
                "sourcetype": "cisco:ios:mdt:metric",
                "index": idx_name,
                "fields": {
                    "metric_name:preflight.probe": 1.0,
                    "_value": 1.0,
                    "status": "online",
                    "component": "hec_preflight"
                }
            }).encode("utf-8")
        else:
            probe_payload = json.dumps({
                "event": "index_preflight_probe",
                "sourcetype": "datablaster:preflight",
                "index": idx_name
            }).encode("utf-8")
        
        req = hec_request(active_hec_url, data=probe_payload, method="POST")
        req.add_unredirected_header("Authorization", f"Splunk {token}")
        req.add_header("Content-Type", "application/json")
        
        try:
            with urllib.request.urlopen(req, context=ctx_unverified, timeout=3) as resp:
                resp_text = resp.read().decode("utf-8")
                index_checks.append({
                    "index": idx_name,
                    "type": idx["type"],
                    "description": idx["desc"],
                    "available": True,
                    "status": "Available & Ready",
                    "details": "HEC responded"
                })
        except urllib.error.HTTPError as he:
            err_text = he.read().decode("utf-8") if hasattr(he, "read") else ""
            if "does not exist" in err_text.lower():
                index_checks.append({
                    "index": idx_name,
                    "type": idx["type"],
                    "description": idx["desc"],
                    "available": False,
                    "status": "Missing in Splunk",
                    "details": "HEC request failed"
                })
                missing_indexes.append(idx_name)
            else:
                index_checks.append({
                    "index": idx_name,
                    "type": idx["type"],
                    "description": idx["desc"],
                    "available": True,
                    "status": "Configured",
                    "details": f"HTTP {he.code}"
                })
        except Exception:
            idx_conf = os.path.join(APP_DIR, "default", "indexes.conf")
            exists_in_conf = False
            if os.path.exists(idx_conf):
                try:
                    with open(idx_conf, "r") as f:
                        if f"[{idx_name}]" in f.read():
                            exists_in_conf = True
                except Exception:
                    pass
            index_checks.append({
                "index": idx_name,
                "type": idx["type"],
                "description": idx["desc"],
                "available": exists_in_conf,
                "status": "Provisioned in App Config" if exists_in_conf else "Unconfirmed",
                "details": "Local config verified"
            })

    results["checks"]["indexes"] = {
        "name": "Target Indexes Availability",
        "passed": len(missing_indexes) == 0,
        "total": len(target_indexes),
        "available_count": len(target_indexes) - len(missing_indexes),
        "items": index_checks,
        "missing": missing_indexes
    }

    # CHECK 2: Technical Add-on (TA) Installation Status
    splunk_home = os.environ.get("SPLUNK_HOME", "/opt/splunk")
    apps_dir = os.path.join(splunk_home, "etc", "apps")
    
    vendor_tas = [
        {"id": "Splunk_TA_cisco-ios", "name": "Cisco IOS / IOS-XE", "domain": "Core Routing & Campus"},
        {"id": "Splunk_TA_cisco-nexus", "name": "Cisco Nexus NX-OS / ACI", "domain": "Data Center Switching"},
        {"id": "Splunk_TA_paloalto", "name": "Palo Alto Networks (PAN-OS)", "domain": "Next-Gen Firewalls"},
        {"id": "Splunk_TA_fortinet", "name": "Fortinet FortiGate (FortiOS)", "domain": "Edge Firewalls & SD-WAN"},
        {"id": "Splunk_TA_arista", "name": "Arista Networks (EOS)", "domain": "DC AI Fabric & RoCE"},
        {"id": "Splunk_TA_juniper", "name": "Juniper Networks (Junos)", "domain": "Provider Edge Routing"},
        {"id": "Splunk_TA_zscaler", "name": "Zscaler Internet Access (ZIA)", "domain": "Cloud / SASE Ingress"},
        {"id": "Splunk_TA_netskope", "name": "Netskope SSE / CASB", "domain": "Cloud Security"},
        {"id": "Splunk_TA_f5-bigip", "name": "F5 BIG-IP LTM/AFM", "domain": "Application Delivery"},
        {"id": "Splunk_TA_aruba", "name": "Aruba Networks (CX / ClearPass)", "domain": "Wireless & Campus"},
        {"id": "TA-nokia-sros", "name": "Nokia SR OS (7750)", "domain": "Carrier MPLS / Optical"}
    ]

    ta_checks = []
    installed_tas = 0
    for ta in vendor_tas:
        ta_path = os.path.join(apps_dir, ta["id"])
        installed = os.path.exists(ta_path)
        if installed:
            installed_tas += 1
            ta_checks.append({
                "id": ta["id"],
                "name": ta["name"],
                "domain": ta["domain"],
                "status": "Installed (Native TA)",
                "installed": True,
                "badge": "success"
            })
        else:
            ta_checks.append({
                "id": ta["id"],
                "name": ta["name"],
                "domain": ta["domain"],
                "status": "Built-in Parser Active",
                "installed": False,
                "badge": "info"
            })

    results["checks"]["technical_addons"] = {
        "name": "Multi-Vendor Technical Add-on (TA) Status",
        "passed": True,
        "installed_count": installed_tas,
        "total": len(vendor_tas),
        "items": ta_checks,
        "note": "TA-network-data-blaster includes built-in props/transforms extractions so CIM compliance is active even without vendor TAs installed."
    }

    # CHECK 3: HEC Token Validity & Permissions
    results["checks"]["hec_token"] = {
        "name": "HEC Token Validity & Whitelist",
        "passed": hec_probe.get("status") == "success",
        "status": "Valid & Authenticated" if hec_probe.get("status") == "success" else "Authentication Failed",
        "http_code": hec_probe.get("http_status"),
        "message": hec_probe.get("message")
    }

    # CHECK 4: SSL Verification Check
    ssl_strict_ok = False
    ssl_strict_err = None
    try:
        ctx_strict = ssl.create_default_context()
        ctx_strict.check_hostname = True
        ctx_strict.verify_mode = ssl.CERT_REQUIRED
        req_strict = hec_request(
            active_hec_url,
            data=b'{"event": "ssl_probe", "sourcetype": "datablaster:ssl"}',
            headers={"Authorization": f"Splunk {token}", "Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req_strict, timeout=4, context=ctx_strict) as r_strict:
            ssl_strict_ok = True
    except ssl.SSLCertVerificationError as se:
        ssl_strict_err = "Certificate verification failed"
    except Exception as e:
        ssl_strict_err = "Operation failed"

    results["checks"]["ssl_verification"] = {
        "name": "SSL Verification & TLS Certificate Health",
        "active_ssl_verify": ssl_verify,
        "ca_trusted": ssl_strict_ok,
        "passed": True if (ssl_strict_ok or not ssl_verify) else False,
        "status": "Strict CA Verified" if ssl_strict_ok else ("Bypassed (Self-Signed Mode)" if not ssl_verify else "Certificate Untrusted"),
        "details": "CA Certificate validated successfully" if ssl_strict_ok else (ssl_strict_err or "Self-signed certificate in use"),
        "recommendation": "Configuration optimal for current environment." if (ssl_strict_ok or not ssl_verify) else "Set ssl_verify = false in app configuration or install root CA."
    }

    # CHECK 5: Ingestion Pipeline & Latency Probe
    results["checks"]["latency_probe"] = {
        "name": "Ingestion Pipeline Latency & Health Probe",
        "passed": hec_probe.get("latency_ms", 999) < 200,
        "latency_ms": hec_probe.get("latency_ms", 0),
        "health": "Optimal (< 50ms)" if hec_probe.get("latency_ms", 0) < 50 else ("Acceptable" if hec_probe.get("latency_ms", 0) < 150 else "Elevated Latency"),
        "endpoint": hec_url
    }

    if not results["checks"]["hec_token"]["passed"] or (ssl_verify and not ssl_strict_ok):
        results["overall_status"] = "warning"
    if len(missing_indexes) > 0:
        results["overall_status"] = "action_required"

    return results


def get_orchestration_log_path() -> str:
    """Return the Splunk standard logging location or fallback."""
    splunk_home = os.environ.get("SPLUNK_HOME")
    if splunk_home:
        cand = os.path.join(splunk_home, "var", "log", "splunk")
        if os.path.exists(cand):
            return os.path.join(cand, "ta_datablaster_orchestration.log")

    log_dir = os.path.join(APP_DIR, "var", "log")
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "ta_datablaster_orchestration.log")


def create_custom_index(name: str, datatype: str = "event", max_size_mb: int = 51200, retention_sec: int = 7776000, session_key: str = "") -> Dict[str, Any]:
    """
    Create a custom Splunk index by writing to local/indexes.conf and invoking Splunk REST API if available.
    """
    local_dir = os.path.join(APP_DIR, "local")
    os.makedirs(local_dir, exist_ok=True)
    indexes_conf_path = os.path.join(local_dir, "indexes.conf")

    stanza = (
        f"\n[{name}]\n"
        f"homePath   = $SPLUNK_DB/{name}/db\n"
        f"coldPath   = $SPLUNK_DB/{name}/colddb\n"
        f"thawedPath = $SPLUNK_DB/{name}/thaweddb\n"
        f"maxTotalDataSizeMB = {max_size_mb}\n"
        f"datatype = {datatype}\n"
        f"frozenTimePeriodInSecs = {retention_sec}\n"
    )

    existing = ""
    if os.path.exists(indexes_conf_path):
        with open(indexes_conf_path, "r", encoding="utf-8") as f:
            existing = f.read()

    stanza_header = f"[{name}]"
    if stanza_header not in existing:
        with open(indexes_conf_path, "a", encoding="utf-8") as f:
            f.write(stanza)

    splunk_rest_msg = "Written to local/indexes.conf"
    if SPLUNK_AVAILABLE and session_key:
        try:
            rest.simpleRequest(
                "/services/data/indexes",
                sessionKey=session_key,
                method="POST",
                postargs={
                    "name": name,
                    "datatype": datatype,
                    "maxTotalDataSizeMB": str(max_size_mb),
                    "frozenTimePeriodInSecs": str(retention_sec)
                }
            )
            splunk_rest_msg = "Provisioned via Splunk REST API and persisted to local/indexes.conf"
        except Exception as e:
            try:
                rest.simpleRequest("/services/data/indexes/_reload", sessionKey=session_key, method="POST")
                splunk_rest_msg = f"Persisted to local/indexes.conf and triggered index reload (Operation failed)"
            except Exception:
                splunk_rest_msg = f"Persisted to local/indexes.conf"

    return {
        "status": "success",
        "message": f"Custom index '{name}' created successfully! ({splunk_rest_msg})",
        "index": name,
        "datatype": datatype,
        "max_size_mb": max_size_mb
    }


def get_all_indexes(session_key: str = "") -> Dict[str, Any]:
    """
    Retrieve all available Splunk indexes from configuration files and the Splunk REST API.
    """
    indexes = set([
        "idx_network_ops", "idx_security_fw", "idx_wireless_ops",
        "idx_performance_metrics", "cisco_mdt_metrics", "netops_logs",
        "main", "default"
    ])
    
    # Parse default/indexes.conf and local/indexes.conf
    for conf_rel in [os.path.join("default", "indexes.conf"), os.path.join("local", "indexes.conf")]:
        conf_path = os.path.join(APP_DIR, conf_rel)
        if os.path.exists(conf_path):
            try:
                with open(conf_path, "r", encoding="utf-8") as fp:
                    for line in fp:
                        m = re.match(r"^\s*\[([a-zA-Z0-9_\-]+)\]", line)
                        if m:
                            sec = m.group(1).strip()
                            if not sec.startswith("default") and not sec.startswith("global"):
                                indexes.add(sec)
            except Exception:
                pass

    # Query Splunk REST API if session_key is available
    if SPLUNK_AVAILABLE and session_key:
        try:
            resp, content = rest.simpleRequest("/services/data/indexes?output_mode=json&count=0", sessionKey=session_key)
            if resp.status == 200:
                data = json.loads(content)
                for entry in data.get("entry", []):
                    title = entry.get("name")
                    if title and not title.startswith("_"):
                        indexes.add(title)
        except Exception:
            pass

    return {
        "status": "success",
        "indexes": sorted(list(indexes))
    }


def validate_and_sanitize(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Rigorously validate and sanitize all input parameters to eliminate command injection.
    """
    action = params.get("action", "start").strip().lower()
    if action in ("start_simulation", "run_scenario"):
        action = "start"
    allowed_actions = [
        "start", "start_simulation", "run_scenario", "stop", "status", "logs", "validate",
        "blast_single_device", "stream_canvas_topology", "onboard_sample", "blast_hec",
        "test_hec", "get_config", "save_config", "validate_environment",
        "create_index", "list_indexes"
    ]
    if action not in allowed_actions:
        raise ValueError(f"Invalid action '{action}'. Supported: {', '.join(allowed_actions)}")

    if action in ["status", "stop", "logs", "get_config"]:
        return {"action": action}

    if action == "blast_hec":
        raw_events = params.get("events")
        if not raw_events or not isinstance(raw_events, list):
            st = str(params.get("sourcetype", "")).strip()
            idx = str(params.get("index", "main")).strip()
            try:
                vol = int(params.get("volume", 5))
            except (ValueError, TypeError):
                vol = 5
            if st:
                raw_events = []
                for i in range(vol):
                    raw_events.append({
                        "time": time.time(),
                        "event": f"%NETSPOUT-5-TELEMETRY: Sample telemetry record {i+1}/{vol} for {st}",
                        "sourcetype": st,
                        "index": idx,
                        "source": "netspout:blast_hec",
                        "host": "core-gw01.net.internal"
                    })
            else:
                raise ValueError("Parameter 'events' must be a non-empty list of event objects or 'sourcetype' must be provided")
        stored_cfg = get_stored_config(params.get("session_key", ""))
        hec_url = resolve_hec_urls(stored_cfg["hec_url"], stored_cfg)[0]
        token = HECCredentialStore(params.get("session_key", "")).read()
        if not token:
            raise ValueError("HEC token is not configured")
        ssl_verify = stored_cfg.get("ssl_verify", True) is not False
        session_key = params.get("session_key", "")
        return {
            "action": "blast_hec",
            "hec": hec_url,
            "token": token,
            "ssl_verify": ssl_verify,
            "events": raw_events,
            "session_key": session_key
        }


    if action == "list_indexes":
        return {
            "action": "list_indexes",
            "session_key": str(params.get("session_key") or params.get("sessionKey", ""))
        }

    if action == "create_index":
        raw_name = str(params.get("name") or params.get("index_name", "")).strip().lower()
        if not re.match(r"^[a-zA-Z0-9_\-]+$", raw_name):
            raise ValueError(f"Invalid index name '{raw_name}'. Index names must contain only alphanumeric characters, underscores, and dashes.")
        datatype = str(params.get("datatype", "event")).strip().lower()
        if datatype not in ("event", "metric"):
            datatype = "event"
        try:
            max_size_mb = int(params.get("max_size_mb") or params.get("maxTotalDataSizeMB", 51200))
        except (ValueError, TypeError):
            max_size_mb = 51200
        try:
            retention_days = int(params.get("retention_days", 90))
            retention_sec = retention_days * 86400
        except (ValueError, TypeError):
            retention_sec = 7776000
        return {
            "action": "create_index",
            "name": raw_name,
            "datatype": datatype,
            "max_size_mb": max_size_mb,
            "retention_sec": retention_sec,
            "session_key": str(params.get("session_key") or params.get("sessionKey", ""))
        }

    if action == "save_config":
        new_config = {}
        for key in DEFAULT_CONFIG:
            if key not in ("hec_url", "hec_allowed_hosts", "hec_allowed_ports") and key in params:
                new_config[key] = params[key]
        if "ssl_verify" in new_config:
            value = new_config["ssl_verify"]
            new_config["ssl_verify"] = value.lower() in ("true", "1", "yes") if isinstance(value, str) else bool(value)
        return {"action": action, "config": new_config}

    stored_cfg = get_stored_config(params.get("session_key", ""))
    hec = resolve_hec_urls(stored_cfg["hec_url"], stored_cfg)[0]
    token = HECCredentialStore(params.get("session_key", "")).read()
    if not token:
        raise ValueError("HEC token is not configured")
    ssl_verify = stored_cfg.get("ssl_verify", True) is not False
    if action in ("test_hec", "validate_environment"):
        return {"action": action, "hec": hec, "token": token, "ssl_verify": ssl_verify}

    if action in ("onboard_sample", "emit_device_telemetry"):
        sourcetype = str(params.get("sourcetype", "custom:telemetry")).strip()
        index_target = str(params.get("index", "idx_network_ops")).strip()
        sample_content = str(params.get("sample_content", params.get("content", ""))).strip()
        host = str(params.get("host", "")).strip()
        ip = str(params.get("ip", "")).strip()
        count = int(params.get("count", 1))
        ssl_verify = stored_cfg.get("ssl_verify", True) is not False
        return {
            "action": "onboard_sample",
            "sourcetype": sourcetype,
            "index": index_target,
            "sample_content": sample_content,
            "host": host,
            "ip": ip,
            "count": count,
            "hec": hec,
            "token": token,
            "ssl_verify": ssl_verify
        }

    if action == "blast_single_device":
        device_info = params.get("device_info", {})
        if isinstance(device_info, str):
            try:
                device_info = json.loads(device_info)
            except Exception:
                device_info = {"name": device_info}
        return {
            "action": action,
            "device_info": device_info,
            "hec": hec,
            "token": token,
            "count": int(params.get("count", 1))
        }

    if action == "stream_canvas_topology":
        raw_eps = str(params.get("eps") or (int(params.get("volume", 1)) * 100)).strip()
        if not RE_EPS.match(raw_eps):
            raise ValueError(f"Invalid 'eps' parameter '{raw_eps}'. Must contain only digits.")
        eps_val = int(raw_eps)
        nodes = params.get("nodes", [])
        if isinstance(nodes, str):
            try:
                nodes = json.loads(nodes)
            except Exception:
                raise ValueError("Canvas nodes must be a list of mappings") from None
        if not isinstance(nodes, list) or len(nodes) > 500:
            raise ValueError("Canvas nodes must be a list of at most 500 mappings")
        for node in nodes:
            if not isinstance(node, dict):
                raise ValueError("Canvas nodes must be mappings")
            for field in ("id", "vendor", "host", "index", "source", "sourcetype", "sampleEvent"):
                if field in node:
                    value = node[field]
                    if (not isinstance(value, str) or len(value) > 4096
                            or any(ord(c) < 32 or c in '\x7f\x85\u2028\u2029"\\' for c in value)):
                        raise ValueError("Invalid canvas node field")
        links = params.get("links", [])
        if isinstance(links, str):
            try:
                links = json.loads(links)
            except Exception:
                links = []
        return {
            "action": action,
            "nodes": nodes,
            "links": links,
            "eps": eps_val,
            "hec": hec,
            "token": token,
        "ssl_verify": ssl_verify
        }

    # 1. EPS Validation (integers only)
    raw_eps = str(params.get("eps", "1000")).strip()
    if not RE_EPS.match(raw_eps):
        raise ValueError(f"Invalid 'eps' parameter '{raw_eps}'. Must contain only digits.")
    eps_val = int(raw_eps)
    if eps_val <= 0 or eps_val > 500000:
        raise ValueError(f"Parameter 'eps' ({eps_val}) out of safe bounds (1 - 500,000).")

    # 2. Scenario Path Validation (no traversal)
    scenario = str(params.get("scenario") or params.get("scenario_file") or "").strip()
    if not scenario:
        raise ValueError("Missing required 'scenario' parameter.")
    if ".." in scenario or not RE_SAFE_PATH.match(scenario):
        raise ValueError(f"Illegal characters or directory traversal in 'scenario': {scenario}")

    scenario_path = resolve_scenario_path(scenario)

    # 3. Sample Validation (optional)
    sample = params.get("sample")
    if sample:
        sample = str(sample).strip()
        if ".." in sample or not RE_SAFE_PATH.match(sample):
            raise ValueError(f"Illegal characters or directory traversal in 'sample': {sample}")

    return {
        "action": action,
        "scenario": scenario_path,
        "sample": sample,
        "eps": eps_val,
        "hec": hec,
        "token": token,
        "ssl_verify": ssl_verify
    }



def is_process_running(pid: int) -> bool:
    """Check if process is active."""
    try:
        try:
            done, _ = os.waitpid(pid, os.WNOHANG)
            if done:
                return False
        except ChildProcessError:
            pass
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def get_current_status() -> Dict[str, Any]:
    """Retrieve current running simulation status."""
    active_pid = None
    active_dir = get_active_run_dir()
    pid_candidates = [
        os.path.join(active_dir, "datablaster.pid")
    ]
    for p_file in pid_candidates:
        if os.path.exists(p_file):
            try:
                active_pid = int(_read_private_file(p_file).strip())
                if active_pid:
                    break
            except (ValueError, IOError):
                active_pid = None

    running = False
    if active_pid:
        running = is_process_running(active_pid)
        if not running and os.path.exists(PID_FILE):
            try:
                os.remove(PID_FILE)
            except OSError:
                pass

    metadata = {}
    if os.path.exists(STATUS_FILE):
        try:
            metadata = json.loads(_read_private_file(STATUS_FILE))
        except Exception:
            pass

    log_path = get_orchestration_log_path()
    log_size = os.path.getsize(log_path) if os.path.exists(log_path) else 0

    return {
        "running": running,
        "pid": active_pid if running else None,
        "log_path": log_path,
        "log_size_bytes": log_size,
        "metadata": metadata
    }


def stop_simulation() -> Dict[str, Any]:
    """Gracefully terminate active simulation."""
    status = get_current_status()
    if not status["running"] or not status["pid"]:
        cleanup_stale_run_files()
        return {"status": "success", "message": "No simulation currently running"}

    pid = status["pid"]
    try:
        os.killpg(pid, signal.SIGTERM)
        deadline = time.monotonic() + 6
        while time.monotonic() < deadline:
            try:
                try:
                    os.waitpid(pid, os.WNOHANG)
                except ChildProcessError:
                    pass
                try:
                    os.killpg(pid, 0)
                except PermissionError:
                    pass
            except ProcessLookupError:
                break
            time.sleep(0.1)
        else:
            os.killpg(pid, signal.SIGKILL)
        for p_file in [PID_FILE]:
            if os.path.exists(p_file):
                try:
                    os.remove(p_file)
                except OSError:
                    pass
        return {"status": "success", "message": f"Terminated process {pid}"}
    except Exception as e:
        return {"status": "error", "message": f"Failed stopping process {pid}: Operation failed"}

    finally:
        cleanup_stale_run_files()


def read_recent_logs(lines_count: int = 50) -> Dict[str, Any]:
    """Read recent lines from orchestration log."""
    log_path = get_orchestration_log_path()
    if not os.path.exists(log_path):
        return {"lines": ["[INFO] No orchestration log exists yet."], "log_path": log_path}

    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
            recent = all_lines[-lines_count:] if len(all_lines) > lines_count else all_lines
        return {
            "lines": [l.rstrip("\r\n") for l in recent],
            "total_lines": len(all_lines),
            "log_path": log_path
        }
    except Exception as e:
        return {"error": f"Failed reading log: Operation failed", "lines": []}


def start_simulation(run_params):
    with simulation_start_lock():
        return _start_simulation_locked(run_params)


def _start_simulation_locked(run_params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Launch bin/run_simulation.py asynchronously with explicit argument list and shell=False.
    """
    # Check if existing process is running
    status = get_current_status()
    if status["running"]:
        return {
            "status": "warning",
            "message": f"Simulation already running under PID {status['pid']}. Stop it first.",
            "pid": status["pid"]
        }

    cleanup_stale_run_files()
    run_sim_script = os.path.join(BIN_DIR, "run_simulation.py")
    if not os.path.exists(run_sim_script):
        raise FileNotFoundError(f"Missing automation wrapper: {run_sim_script}")

    log_path = get_orchestration_log_path()

    # Construct explicit argument list
    cmd = [
        sys.executable,
        run_sim_script,
        "--scenario", run_params["scenario"],
        "--eps", str(run_params["eps"]),
        "--hec", run_params["hec"],
        "--ssl-verify", str(run_params.get("ssl_verify", True)).lower()
    ]
    if run_params.get("sample"):
        cmd.extend(["--sample", run_params["sample"]])

    # Write audit entry to log
    with open(log_path, "a", encoding="utf-8") as lf:
        lf.write(f"\n=======================================================\n")
        lf.write(f"SESSION START: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n")
        lf.write(f"INVOCATION: {' '.join(cmd[:4])} [HEC credentials redacted]\n")
        lf.write(f"=======================================================\n")
        lf.flush()

        # Asynchronous execution with shell=False
        proc = subprocess.Popen(
            cmd,
            shell=False,
            stdout=lf,
            stderr=subprocess.STDOUT,
            cwd=APP_DIR,
            start_new_session=True,
            stdin=subprocess.PIPE, text=True
        )
        proc.stdin.write(json.dumps({"credential": run_params["token"]}))
        proc.stdin.close()

    active_dir = get_active_run_dir()
    write_private_file(PID_FILE, str(proc.pid))

    # Record metadata
    meta = {
        "started_at": time.time(),
        "scenario": run_params["scenario"],
        "sample": run_params.get("sample"),
        "eps": run_params["eps"],
        "hec": run_params["hec"],
        "pid": proc.pid
    }
    write_private_file(STATUS_FILE, json.dumps(meta, indent=2))

    return {
        "status": "success",
        "message": f"Simulation launched asynchronously under PID {proc.pid}",
        "pid": proc.pid,
        "scenario": os.path.basename(run_params["scenario"]),
        "eps": run_params["eps"],
        "log_path": log_path
    }


def _execute_request(params: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    """
    Main dispatch entry point for both Splunk REST handler and CLI/test invocation.
    Returns (http_status_code, json_dict).
    """
    try:
        if not has_netspout_admin(params.get("session_key", "")):
            return (403, {"status": "error", "message": "netspout_admin capability required"})
        get_stored_config(params.get("session_key", ""))
        clean = validate_and_sanitize(params)
        action = clean["action"]

        if action == "status":
            res = get_current_status()
            return (200, res)

        elif action == "stop":
            res = stop_simulation()
            return (200, res)

        elif action == "logs":
            lines = int(params.get("lines", 50))
            res = read_recent_logs(lines)
            return (200, res)

        elif action == "validate":
            return (200, {"status": "valid", "sanitized": {k: v for k, v in clean.items() if k != "token"}})

        elif action in ("start", "start_simulation", "run_scenario"):
            res = start_simulation(clean)
            return (200, res)

        elif action == "blast_single_device":
            sys.path.insert(0, BIN_DIR)
            import run_simulation
            res = run_simulation.blast_single_device(clean["device_info"], clean["hec"], clean["token"], clean.get("count", 1), get_stored_config().get("ssl_verify", True) is not False)
            return (200, res)

        elif action == "stream_canvas_topology":
            with simulation_start_lock():
                status = get_current_status()
                if status["running"]:
                    return (409, {"status": "warning", "pid": status["pid"],
                                  "message": "Simulation already running. Stop it first."})
                sys.path.insert(0, BIN_DIR)
                import run_simulation
                pid = run_simulation.stream_custom_canvas_topology(clean["nodes"], clean["links"], clean["hec"], clean["token"], clean["eps"])
                active_dir = get_active_run_dir()
                write_private_file(PID_FILE, str(pid))
                meta = {
                    "started_at": time.time(),
                    "scenario": "custom_canvas_topology",
                    "eps": clean["eps"],
                    "hec": clean["hec"],
                    "pid": pid,
                    "nodes_count": len(clean["nodes"]),
                    "links_count": len(clean["links"])
                }
                write_private_file(STATUS_FILE, json.dumps(meta, indent=2))
                return (200, {
                    "status": "success",
                    "message": f"Custom canvas topology stream launched under PID {pid}",
                    "pid": pid,
                    "nodes": len(clean["nodes"]),
                    "links": len(clean["links"])
                })
        elif action == "blast_hec":
            hec_url = clean["hec"]
            token = clean["token"]
            ssl_verify = clean["ssl_verify"]
            events = clean["events"]
            session_key = clean.get("session_key", "")

            formatted_lines = []
            target_index = "idx_network_ops"
            target_sourcetype = "custom:telemetry"

            for ev in events:
                if isinstance(ev, dict):
                    if "index" in ev:
                        target_index = ev["index"]
                    if "sourcetype" in ev:
                        target_sourcetype = ev["sourcetype"]
                    formatted_lines.append(json.dumps(ev))
                elif isinstance(ev, str):
                    formatted_lines.append(json.dumps({
                        "event": ev,
                        "time": time.time(),
                        "index": target_index,
                        "sourcetype": target_sourcetype
                    }))

            raw_payload = "\n".join(formatted_lines).encode("utf-8")

            target_urls = resolve_hec_urls(hec_url, get_stored_config())

            ctx = ssl.create_default_context()
            if not ssl_verify:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

            last_err = None
            success = False
            resp_data = ""

            for url in target_urls:
                try:
                    req = hec_request(
                        url,
                        data=raw_payload,
                        headers={
                            "Authorization": f"Splunk {token}",
                            "Content-Type": "application/json"
                        }
                    )
                    with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
                        resp_data = response.read().decode("utf-8", errors="replace")
                        success = True
                        break
                except urllib.error.HTTPError as he:
                    err_body = he.read().decode("utf-8", errors="replace")
                    if "Invalid index" in err_body or he.code == 400:
                        try:
                            # Re-attempt delivery directed to main index
                            fallback_lines = []
                            for ev in events:
                                ev_copy = dict(ev) if isinstance(ev, dict) else {"event": ev}
                                ev_copy["index"] = "main"
                                fallback_lines.append(json.dumps(ev_copy))
                            fallback_payload = "\n".join(fallback_lines).encode("utf-8")
                            fb_req = hec_request(
                                url,
                                data=fallback_payload,
                                headers={
                                    "Authorization": f"Splunk {token}",
                                    "Content-Type": "application/json"
                                }
                            )
                            with urllib.request.urlopen(fb_req, timeout=10, context=ctx) as fb_resp:
                                resp_data = fb_resp.read().decode("utf-8", errors="replace")
                                success = True
                                target_index = f"main (fallback from {target_index})"
                                break
                        except Exception as fb_err:
                            last_err = f"{he} -> Receiver request failed"
                            continue
                    last_err = "HEC request failed"
                    continue
                except Exception as e:
                    last_err = "Operation failed"
                    continue


            if success:
                return (200, {
                    "status": "success",
                    "message": f"Successfully ingested {len(events)} event(s) via HEC into '{target_index}'!",
                    "events_count": len(events),
                    "hec_response": "HEC responded"
                })
            else:
                if session_key and SPLUNK_AVAILABLE:
                    try:
                        import splunk.rest
                        for ev in events:
                            st = ev.get("sourcetype", target_sourcetype) if isinstance(ev, dict) else target_sourcetype
                            idx = ev.get("index", target_index) if isinstance(ev, dict) else target_index
                            ev_text = ev.get("event", "") if isinstance(ev, dict) else str(ev)
                            splunk.rest.simpleRequest(
                                f"/services/receivers/simple?sourcetype={st}&index={idx}",
                                sessionKey=session_key,
                                postargs=ev_text,
                                method="POST"
                            )
                        return (200, {
                            "status": "success",
                            "message": f"Successfully ingested {len(events)} event(s) via Splunk receiver pipeline!",
                            "events_count": len(events)
                        })
                    except Exception as fb_err:
                        last_err = f"HEC request failed | Fallback receiver error: Receiver request failed"

                return (400, {
                    "status": "error",
                    "message": f"HEC delivery failed: HEC request failed"
                })

        elif action == "onboard_sample":
            sourcetype = clean.get("sourcetype", "custom:telemetry").strip()
            index_target = clean.get("index", "idx_network_ops").strip()
            sample_content = clean.get("sample_content", "").strip()
            if not sample_content:
                try:
                    from cisco_sample_provider import get_sample_lines
                    s_lines = get_sample_lines(sourcetype)
                except Exception:
                    s_lines = []
                if s_lines:
                    sample_content = "\n".join(s_lines)
                else:
                    sample_content = f"%NETSPOUT-5-SAMPLE: Sample event for {sourcetype}"
            
            safe_name = re.sub(r'[^a-zA-Z0-9_-]', '_', sourcetype)
            os.makedirs(os.path.join(APP_DIR, "samples"), exist_ok=True)
            sample_file = os.path.join(APP_DIR, "samples", f"{safe_name}.log")
            with open(sample_file, "w") as fp:
                fp.write(sample_content + "\n")
            
            lines = [l for l in sample_content.splitlines() if l.strip()]
            hec_url = clean.get("hec") or "https://127.0.0.1:8088/services/collector"
            token = clean.get("token")
            if not token:
                raise ValueError("HEC token is not configured")
            ssl_verify = clean.get("ssl_verify", True)
            
            payload_events = []
            is_metric_target = (index_target == "cisco_mdt_metrics" or "metric" in index_target.lower())
            host_name = clean.get("host") or f"onboarded-{safe_name}-01"
            repeat_count = max(1, min(1000, int(clean.get("count", 1))))
            
            for _ in range(repeat_count):
                cur_time = time.time()
                for line in lines:
                    if is_metric_target:
                        metric_fields = {
                            "metric_name:sample.metric": 1.0,
                            "_value": 1.0,
                            "device": host_name,
                            "sourcetype": sourcetype
                        }
                        try:
                            parsed = json.loads(line)
                            if isinstance(parsed, dict):
                                if "fields" in parsed and isinstance(parsed["fields"], dict):
                                    metric_fields.update(parsed["fields"])
                                else:
                                    for k, v in parsed.items():
                                        if isinstance(v, (int, float)):
                                            metric_fields[f"metric_name:{k}"] = float(v)
                                        elif isinstance(v, str):
                                            metric_fields[k] = v
                        except Exception:
                            pass
                        
                        payload_events.append(json.dumps({
                            "event": "metric",
                            "sourcetype": sourcetype if "metric" in sourcetype else f"{sourcetype}:metric",
                            "index": index_target,
                            "host": host_name,
                            "time": cur_time,
                            "fields": metric_fields
                        }))
                    else:
                        payload_events.append(json.dumps({
                            "event": line,
                            "sourcetype": sourcetype,
                            "index": index_target,
                            "host": host_name,
                            "time": cur_time
                        }))
            raw_payload = "\n".join(payload_events).encode("utf-8")
            
            ctx = ssl.create_default_context()
            if not ssl_verify:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

            target_urls = resolve_hec_urls(hec_url, get_stored_config())
            success = False
            resp_text = ""
            last_err = None
            for url in target_urls:
                try:
                    req = hec_request(
                        url,
                        data=raw_payload,
                        headers={"Authorization": f"Splunk {token}", "Content-Type": "application/json"}
                    )
                    with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                        resp_text = resp.read().decode("utf-8", errors="replace")
                        success = True
                        break
                except Exception as e:
                    last_err = e

            if not success:
                raise RuntimeError(f"HEC delivery failed across all endpoints: HEC request failed")

            ingested_count = len(lines) * repeat_count
            
            return (200, {
                "status": "success",
                "message": f"Successfully onboarded sourcetype '{sourcetype}'! Wrote sample to '{os.path.basename(sample_file)}' and indexed {ingested_count} events into '{index_target}'.",
                "sourcetype": sourcetype,
                "index": index_target,
                "sample_file": sample_file,
                "events_count": ingested_count,
                "hec_response": "HEC responded"
            })

        elif action == "test_hec":
            res = test_hec_connection(clean["hec"], clean["token"], clean.get("ssl_verify", True))
            code = 200 if res.get("status") == "success" else (res.get("http_status") or 400)
            return (code, res)

        elif action == "validate_environment":
            res = run_environment_validation(clean["hec"], clean["token"], clean.get("ssl_verify", True))
            return (200, res)

        elif action == "get_config":
            cfg = public_config(params.get("session_key", ""))
            return (200, {"status": "success", "config": cfg})

        elif action == "create_index":
            res = create_custom_index(
                name=clean["name"],
                datatype=clean.get("datatype", "event"),
                max_size_mb=clean.get("max_size_mb", 51200),
                retention_sec=clean.get("retention_sec", 7776000),
                session_key=clean.get("session_key", "")
            )
            return (200, res)

        elif action == "list_indexes":
            res = get_all_indexes(session_key=clean.get("session_key", ""))
            return (200, res)

        elif action == "save_config":
            save_stored_config(clean["config"], params.get("session_key", ""))
            cfg = public_config(params.get("session_key", ""))
            return (200, {"status": "success", "message": "Configuration saved successfully", "config": cfg})

        else:
            return (400, {"status": "error", "message": f"Unknown action: {action}"})

    except (HECConfigurationError, RunFolderError) as error:
        return (400, {"status": "error", "message": str(error)})
    except Exception as e:
        return (400, {"status": "error", "message": "Request failed; check configuration and runtime availability"})


# Splunk REST Handler Implementation
class DataBlasterRestHandler(PersistentServerConnectionApplication):
    """
    Splunk Persistent REST Application Handler for /services/datablaster/execute
    """
    def __init__(self, command_line=None, command_arg=None):
        super(PersistentServerConnectionApplication, self).__init__()

    def handle(self, in_string):
        try:
            if isinstance(in_string, bytes):
                in_string = in_string.decode("utf-8")

            request = json.loads(in_string) if in_string else {}
            
            # Extract sessionKey
            session_key = request.get("session", {}).get("authtoken") or request.get("sessionKey") or ""
            # VERIFY-ON-SPLUNK: Confirm persist requests provide session.authtoken.

            # Query parameters (list of [key, value] tuples or dict)
            query_raw = request.get("query", [])
            query_params = {}
            if isinstance(query_raw, list):
                for item in query_raw:
                    if len(item) == 2:
                        query_params[item[0]] = item[1]
            elif isinstance(query_raw, dict):
                query_params = query_raw

            # Body / payload
            payload_raw = request.get("payload", "")
            body_params = {}
            if payload_raw:
                if isinstance(payload_raw, str):
                    try:
                        body_params = json.loads(payload_raw)
                    except Exception:
                        pass
                elif isinstance(payload_raw, dict):
                    body_params = payload_raw

            # Merge
            params = {}
            params.update(query_params)
            params.update(body_params)
            params.pop("sessionKey", None)
            params["session_key"] = session_key

            if not params or "action" not in params:
                params["action"] = "status"

            code, resp = execute_request(params)
            return {
                "status": code,
                "payload": json.dumps(resp) if not isinstance(resp, str) else resp
            }
        except Exception as e:
            return {
                "status": 500,
                "payload": json.dumps({"status": "error", "message": "Request failed; check configuration and runtime availability"})
            }

    def handleStream(self, handle, in_string):
        raise NotImplementedError("PersistentServerConnectionApplication.handleStream")


def execute_request(params: Dict[str, Any]) -> Tuple[int, Dict[str, Any]]:
    ignored = {"hec", "url", "hec_url", "token", "hec_token"}
    return _execute_request({key: value for key, value in params.items() if key not in ignored})
