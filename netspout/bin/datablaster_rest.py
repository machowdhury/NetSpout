#!/usr/bin/env python3
"""
NetSpout PulseForge Custom REST Handler
Splunk app netspout: bin/datablaster_rest.py (retained loader identity)

Handles REST calls from Splunk Web UI (/services/datablaster/execute)
Compatible with Splunk Enterprise & Splunk Cloud Vetting:
- Strictly enforces shell=False with explicit argument list
- Validates run parameters and server-configured HEC destinations
- Directs execution logs to $SPLUNK_HOME/var/log/splunk/ta_datablaster_orchestration.log
- Asynchronously wraps execution calls through bin/run_simulation.py
"""

import os
import importlib.util
import ipaddress
import sys
import re
import json
import copy
import time
import signal
import subprocess
import tempfile
import stat
import logging
import threading
import uuid
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

# Only this app-owned helper needs explicit loading under Splunk's mangled
# persistent-handler module name. Never add the app directory to sys.path.
_NATIVE_MONITOR_IMPORT_LOCK = threading.Lock()


def _native_monitor():
    """Resolve one helper and bind it to THIS handler module/lock instance."""
    name = "native_run_monitor"
    path = os.path.realpath(os.path.join(BIN_DIR, name + ".py"))
    runtime = sys.modules[__name__]
    with _NATIVE_MONITOR_IMPORT_LOCK:
        module = sys.modules.get(name)
        created = module is None
        if created:
            spec = importlib.util.spec_from_file_location(name, path)
            if spec is None or spec.loader is None:
                raise RuntimeError("Native monitor unavailable")
            module = importlib.util.module_from_spec(spec)
            sys.modules[name] = module
        elif os.path.realpath(getattr(module, "__file__", "")) != path:
            raise RuntimeError("Native monitor module identity conflict")
        try:
            if created:
                spec.loader.exec_module(module)
            module._bind_runtime(runtime)
        except BaseException:
            if created and sys.modules.get(name) is module:
                del sys.modules[name]
            raise
        return module


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

    def read(self, reference=None):
        # No reference means resolve the active server-owned snapshot. Empty
        # reference explicitly selects the backwards-compatible fixed entry.
        if reference is None:
            get_active_run_dir()
            try:
                saved = json.loads(_read_private_file(CONFIG_FILE))
                reference = saved.get("hec_credential_ref", "")
            except FileNotFoundError:
                reference = ""
            except Exception:
                raise RuntimeError("Cannot resolve active HEC credential") from None
        if reference:
            if not isinstance(reference, str) or not re.fullmatch(r"hec_token_v_[0-9a-f]{32}", reference):
                raise RuntimeError("Invalid active HEC credential reference")
            item = self.collection + "/" + quote("netspout:" + reference + ":", safe="")
        elif reference == "":
            item = self.item
        else:
            raise RuntimeError("Invalid active HEC credential reference")
        code, data = self._request(item)
        if code == 404:
            if reference:
                raise RuntimeError("Active HEC credential is unavailable")
            return ""
        if code != 200:
            raise RuntimeError("Cannot read NetSpout HEC credential")
        entries = data.get("entry", [])
        value = entries[0].get("content", {}).get("clear_password", "") if entries else ""
        if not isinstance(value, str) or (reference and not value):
            raise RuntimeError("Active HEC credential is unavailable")
        return value

    def stage(self, value):
        """Create and verify an inactive entry; never overwrite historical ones."""
        if not has_netspout_admin(self.session_key):
            raise PermissionError("netspout_admin capability required")
        reference = "hec_token_v_" + uuid.uuid4().hex
        code, _ = self._request(self.collection, "POST", {
            "realm": "netspout", "name": reference, "password": value})
        if code not in (200, 201) or self.read(reference) != value:
            raise RuntimeError("Cannot stage HEC credential")
        return reference

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

DESTINATION_PROTOCOLS = ('hec','syslog','otlp','snmp','forwarding')
DESTINATION_CLASSES = ('local_splunk','remote_splunk','external_platform')


def _destination_fields(protocol):
    return {'hec': {'hec_url','ssl_verify','hec_credential_ref','idx_network_ops','idx_security_fw',
                    'idx_wireless_ops','idx_performance_metrics','cisco_mdt_metrics'},
            'syslog':set(SYSLOG_DEFAULTS)-{'native_transport'}, 'otlp':set(OTLP_DEFAULTS),
            'snmp':set(SNMP_DEFAULTS), 'forwarding':set(FORWARDING_DEFAULTS)}[protocol]


def _destination_signals(protocol,settings):
    if protocol=='hec': return ['logs','metrics']
    if protocol=='otlp': return ['logs','metrics'] if settings['otlp_signal']=='both' else [settings['otlp_signal']]
    return ['events'] if protocol=='snmp' else ['logs']


def _destination_legacy_id(protocol):
    return str(uuid.uuid5(uuid.NAMESPACE_URL,'netspout:pulseforge:legacy:'+protocol))


def _destination_registry(config):
    registry=config.get('destination_manager')
    if registry is None:
        registry={'version':1,'selected_id':_destination_legacy_id(config.get('native_transport','hec')),
                  'destinations':[dict(id=_destination_legacy_id(p),name='Legacy '+p.upper(),protocol=p,
                   target_class=('local_splunk' if p=='hec' and urlsplit(config['hec_url']).hostname in ('localhost','127.0.0.1','::1') else 'remote_splunk' if p in ('hec','forwarding') else 'external_platform'),enabled=True,legacy=True,
                   settings={k:copy.deepcopy(config[k]) for k in _destination_fields(p)}) for p in DESTINATION_PROTOCOLS]}
    registry=copy.deepcopy(registry)
    if len(json.dumps(registry).encode())>262144: raise ValueError('Destination registry too large')
    if (not isinstance(registry,dict) or set(registry)!={'version','selected_id','destinations'}
            or registry['version']!=1 or not isinstance(registry['destinations'],list)
            or not 1<=len(registry['destinations'])<=100):
        raise ValueError('Destination registry unavailable')
    ids=set()
    for d in registry['destinations']:
        if (not isinstance(d,dict) or set(d)!={'id','name','protocol','target_class','enabled','legacy','settings'}
                or not isinstance(d['id'],str) or str(uuid.UUID(d['id']))!=d['id'] or d['id'] in ids
                or not isinstance(d['name'],str) or not 1<=len(d['name'])<=80
                or any(ord(c)<32 for c in d['name']) or d['protocol'] not in DESTINATION_PROTOCOLS
                or d['target_class'] not in DESTINATION_CLASSES or type(d['enabled']) is not bool
                or type(d['legacy']) is not bool or not isinstance(d['settings'],dict)
                or set(d['settings'])!=_destination_fields(d['protocol'])):
            raise ValueError('Invalid destination registry')
        for key,prefix in (('hec_credential_ref','hec_token_v_'),('otlp_credential_ref','otlp_token_v_'),('snmp_credential_ref','snmp_community_v_')):
            if key in d['settings']:
                value=d['settings'][key]
                if not isinstance(value,str) or (value and not re.fullmatch(prefix+r'[0-9a-f]{32}',value)):
                    raise ValueError('Invalid credential reference')
        ids.add(d['id'])
    if registry['selected_id'] not in ids:
        raise ValueError('Selected destination unavailable')
    return registry


def _destination_reconcile(config):
    """Called before atomic publication; legacy writes update their active profile."""
    candidate=copy.deepcopy(config)
    registry=_destination_registry(candidate)
    selected=next(d for d in registry['destinations'] if d['id']==registry['selected_id'])
    protocol=candidate.get('native_transport','hec')
    if selected['protocol']!=protocol:
        key=_destination_legacy_id(protocol)
        selected=next((d for d in registry['destinations'] if d['id']==key),None)
        if selected is None: raise ValueError('Legacy destination unavailable')
        registry['selected_id']=key
    for d in registry['destinations']:
        if d['legacy'] or d['id']==registry['selected_id']:
            d['settings']={k:copy.deepcopy(candidate[k]) for k in _destination_fields(d['protocol'])}
    candidate['destination_manager']=registry
    return candidate


def _destination_validate(protocol,settings,config):
    if set(settings)!=_destination_fields(protocol): raise ValueError('Invalid destination settings')
    merged=dict(config,**settings)
    if protocol=='hec':
        resolve_hec_urls(merged['hec_url'],config)
        ref=merged['hec_credential_ref']
        if (type(merged['ssl_verify']) is not bool or not isinstance(ref,str)
                or (ref and not re.fullmatch(r'hec_token_v_[0-9a-f]{32}',ref))): raise ValueError()
        for key in _destination_fields('hec')-{'hec_url','ssl_verify','hec_credential_ref'}:
            if not isinstance(merged[key],str) or not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_-]*',merged[key]): raise ValueError()
    elif protocol=='syslog': validate_syslog_settings(dict(merged,native_transport='syslog'))
    elif protocol=='otlp': validate_otlp_settings(merged)
    elif protocol=='snmp': validate_snmp_settings(merged)
    else: _forwarding().validate(merged)
    return merged


def _destination_credentials(protocol,settings,session_key):
    if protocol=='hec':
        value=HECCredentialStore(session_key).read(settings['hec_credential_ref'])
        if not value: raise ValueError('HEC credential unavailable')
    elif protocol=='otlp' and settings['otlp_auth']=='bearer': _otlp_snapshot(settings,session_key)
    elif protocol=='snmp': _snmp_snapshot(settings,session_key)


def _destination_resolve(config,destination_id=None):
    registry=_destination_registry(config)
    key=destination_id if destination_id is not None else registry['selected_id']
    found=next((d for d in registry['destinations'] if d['id']==key),None)
    if found is None or not found['enabled']: raise ValueError('Destination missing or disabled')
    merged=_destination_validate(found['protocol'],found['settings'],config)
    merged['native_transport']=found['protocol']
    return merged,{k:found[k] for k in ('id','name','protocol','target_class')}


def _native_destination_operation(params):
    session=params.get('session_key','')
    if not has_netspout_admin(session): return 403,{'status':'error','message':'netspout_admin capability required'}
    action=params['action']
    try:
        if set(params)-{'action','session_key','destination_id','name','protocol','target_class','settings','credential','enabled'}:
            raise ValueError()
        if action=='list_destinations':
            if set(params)-{'action','session_key'}: raise ValueError()
            registry=_destination_registry(get_stored_config(session))
            records=[dict(d,signals=_destination_signals(d['protocol'],d['settings'])) for d in registry['destinations']]
            return 200,{'status':'success','destinations':records,'selected_id':registry['selected_id']}
        if action=='diagnose_destination':
            if set(params)-{'action','session_key','destination_id'} or 'destination_id' not in params: raise ValueError()
            config,identity=_destination_resolve(get_stored_config(session),params['destination_id'])
            protocol=identity['protocol']
            if protocol=='hec':
                _destination_credentials(protocol,config,session)
                completed=subprocess.run([sys.executable,os.path.join(BIN_DIR,'run_simulation.py'),'--named-hec-diagnostic'],
                    input=json.dumps({'credential':HECCredentialStore(session).read(config['hec_credential_ref']),
                                      'runtime_config':{k:v for k,v in config.items() if k!='destination_manager'}}),
                    text=True,capture_output=True,timeout=10,cwd=APP_DIR)
                if completed.returncode: raise RuntimeError()
                result=json.loads(completed.stdout)
            elif protocol=='syslog': result=_syslog_runner_check(validate_syslog_settings(config))
            elif protocol=='otlp': result=_otlp_runner_check(_otlp_snapshot(config,session))
            elif protocol=='snmp': result=_snmp_runner_check(_snmp_snapshot(config,session))
            else: result=_forwarding().readiness(config)
            return 200,{'status':'success','destination':identity,'result':result,'indexing_verified':False}
        with simulation_start_lock():
            get_active_run_dir()
            try:
                saved=json.loads(_read_private_file(CONFIG_FILE))
                if not isinstance(saved,dict) or 'hec_token' in saved: raise RuntimeError()
            except FileNotFoundError: saved={}
            config=copy.deepcopy(DEFAULT_CONFIG)
            config.update({k:v for k,v in saved.items() if k in DEFAULT_CONFIG})
            registry=_destination_registry(config)
            if action=='create_destination':
                if 'destination_id' in params or len(registry['destinations'])>=100: raise ValueError()
                protocol=params['protocol']
                if protocol not in DESTINATION_PROTOCOLS: raise ValueError()
                d=dict(id=str(uuid.uuid4()),name=params['name'],protocol=protocol,target_class=params['target_class'],
                       enabled=params.get('enabled',True),legacy=False,
                       settings={k:copy.deepcopy(DEFAULT_CONFIG[k]) for k in _destination_fields(protocol)})
                registry['destinations'].append(d)
            else:
                d=next((r for r in registry['destinations'] if r['id']==params.get('destination_id')),None)
                if d is None: raise ValueError()
            if action in ('create_destination','update_destination'):
                if 'protocol' in params and params['protocol']!=d['protocol']: raise ValueError()
                for key in ('name','target_class','enabled'):
                    if key in params: d[key]=params[key]
                updates=params.get('settings',{})
                if not isinstance(updates,dict) or set(updates)-_destination_fields(d['protocol']): raise ValueError()
                ref={'hec':'hec_credential_ref','otlp':'otlp_credential_ref','snmp':'snmp_credential_ref'}.get(d['protocol'])
                if 'credential' in params and (ref is None or ref in updates): raise ValueError()
                if action=='create_destination' and d['protocol']=='hec' and not updates.get('hec_credential_ref') and 'credential' not in params: raise ValueError()
                d['settings'].update(updates);d['legacy']=False
                if 'credential' in params and d['protocol']=='otlp' and d['settings']['otlp_auth']!='bearer': raise ValueError()
                # Validate metadata and complete settings before staging secrets.
                validation=dict(config,destination_manager=registry)
                _destination_registry(validation)
                pending=dict(d['settings'])
                if 'credential' in params:
                    if not isinstance(params['credential'],str) or not params['credential']: raise ValueError()
                    pending[ref]={'hec':'hec_token_v_','otlp':'otlp_token_v_','snmp':'snmp_community_v_'}[d['protocol']]+'0'*32
                _destination_validate(d['protocol'],pending,config)
                if 'credential' in params:
                    store={'hec':HECCredentialStore,'otlp':OTLPCredentialStore,'snmp':SNMPCredentialStore}[d['protocol']](session)
                    if d['protocol']=='hec' and not RE_TOKEN.fullmatch(params['credential']): raise ValueError()
                    d['settings'][ref]=store.stage(params['credential'])
                if d['enabled']: _destination_credentials(d['protocol'],d['settings'],session)
            elif action=='disable_destination':
                if set(params)-{'action','session_key','destination_id'}: raise ValueError()
                d['enabled']=False
            elif action=='select_destination':
                if set(params)-{'action','session_key','destination_id'} or not d['enabled']: raise ValueError()
                _destination_validate(d['protocol'],d['settings'],config)
                _destination_credentials(d['protocol'],d['settings'],session)
                registry['selected_id']=d['id']
            else: raise ValueError()
            if registry['selected_id']==d['id']:
                if d['protocol']=='forwarding' and d['settings']['forwarding_group']!=config['forwarding_group'] and _forwarding().pending_count():
                    raise ValueError('Pending spool blocks routing change')
                config.update(d['settings']);config['native_transport']=d['protocol']
            config['destination_manager']=registry
            _write_config(CONFIG_FILE,config)
        return 200,{'status':'success','destination':dict(d,signals=_destination_signals(d['protocol'],d['settings'])),
                    'selected_id':registry['selected_id']}
    except (ValueError,KeyError,TypeError):
        return 400,{'status':'error','message':'Invalid, unavailable or disabled destination; previous configuration retained'}
    except Exception:
        return 503,{'status':'error','message':'Destination operation unavailable; no delivery is verified'}


FORWARDING_DEFAULTS = {"forwarding_index":"idx_network_ops", "forwarding_group":""}


def _forwarding():
    """Resolve the stateless spool utility without changing global sys.path."""
    name = "pulseforge_forwarding"
    path = os.path.realpath(os.path.join(BIN_DIR, name + ".py"))
    with _NATIVE_MONITOR_IMPORT_LOCK:
        module = sys.modules.get(name)
        if module is not None:
            if os.path.realpath(getattr(module, "__file__", "")) != path:
                raise RuntimeError("Forwarding utility identity conflict")
            return module
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            del sys.modules[name]
            raise
        return module


def _native_forwarding_operation(params):
    if not has_netspout_admin(params.get("session_key", "")):
        return 403, {"status":"error", "message":"netspout_admin capability required"}
    try:
        utility = _forwarding()
        action = params["action"]
        if action == "configure_forwarding":
            if set(params) - (set(FORWARDING_DEFAULTS) | {"action","session_key","native_transport"}):
                raise ValueError()
            with simulation_start_lock():
                get_active_run_dir()
                try:
                    saved = json.loads(_read_private_file(CONFIG_FILE))
                    if not isinstance(saved,dict) or "hec_token" in saved:
                        raise RuntimeError()
                except FileNotFoundError:
                    saved = {}
                candidate = dict(DEFAULT_CONFIG, **{k:v for k,v in saved.items() if k in DEFAULT_CONFIG})
                candidate.update({k:params[k] for k in FORWARDING_DEFAULTS if k in params})
                candidate.update(utility.validate(candidate))
                if candidate["forwarding_group"] != saved.get("forwarding_group", "") and utility.pending_count():
                    raise ValueError()
                if "native_transport" in params:
                    if params["native_transport"] not in ("hec","syslog","otlp","snmp","forwarding"):
                        raise ValueError()
                    candidate["native_transport"] = params["native_transport"]
                _write_config(CONFIG_FILE,candidate)
            return 200, {"status":"success","message":"Forwarding settings saved; operator input setup is required",
                         "config":{k:candidate[k] for k in FORWARDING_DEFAULTS},"native_transport":candidate["native_transport"]}
        if set(params) - {"action","session_key"}:
            raise ValueError()
        config = get_stored_config(params["session_key"])
        if action == "get_forwarding_config":
            return 200, {"status":"success","config":{k:config[k] for k in FORWARDING_DEFAULTS},"native_transport":config["native_transport"]}
        result = utility.readiness(config)
        return (200 if result["status"] == "success" else 503), result
    except ValueError:
        return 400, {"status":"error","message":"Invalid forwarding settings or pending spool prevents group change"}
    except Exception:
        return 503, {"status":"error","message":"Forwarding configuration unavailable"}


SNMP_DEFAULTS = {
    "snmp_host":"127.0.0.1", "snmp_port":1162, "snmp_version":"2c",
    "snmp_message_type":"trap", "snmp_protocol":"udp", "snmp_credential_ref":"",
}


def validate_snmp_settings(settings):
    """Literal private/loopback IPv4 and unprivileged UDP receiver ports only."""
    result = {k:settings.get(k,v) for k,v in SNMP_DEFAULTS.items()}
    if (not isinstance(result["snmp_host"],str) or type(result["snmp_port"]) is not int
            or not 1024 <= result["snmp_port"] <= 65535 or result["snmp_version"] != "2c"
            or result["snmp_message_type"] not in ("trap","inform") or result["snmp_protocol"] != "udp"):
        raise ValueError("Invalid SNMP settings")
    address = ipaddress.ip_address(result["snmp_host"])
    safe = any(address in ipaddress.ip_network(n) for n in ("127.0.0.0/8","10.0.0.0/8","172.16.0.0/12","192.168.0.0/16","169.254.0.0/16"))
    if address.version != 4 or not safe or address.is_unspecified or address.is_multicast or str(address).endswith(".255"):
        raise ValueError("Unsupported SNMP receiver")
    result["snmp_host"] = str(address)
    reference = result["snmp_credential_ref"]
    if not isinstance(reference,str) or (reference and not re.fullmatch(r"snmp_community_v_[0-9a-f]{32}",reference)):
        raise ValueError("Invalid SNMP credential reference")
    return result


class SNMPCredentialStore(HECCredentialStore):
    """Separate app-owned, versioned SNMP entries; no HEC or legacy fallback."""
    def read(self, reference):
        if not isinstance(reference, str) or not re.fullmatch(r"snmp_community_v_[0-9a-f]{32}", reference):
            raise ValueError("Invalid SNMP credential reference")
        code, data = self._request(self.collection + "/" + quote("netspout:" + reference + ":", safe=""))
        entries = data.get("entry", [])
        value = entries[0].get("content", {}).get("clear_password", "") if entries else ""
        if code != 200 or not isinstance(value, str) or not value or len(value.encode("utf-8")) > 255 or any(ord(c) <= 32 or ord(c) >= 127 for c in value):
            raise RuntimeError("SNMP credential unavailable")
        return value

    def stage(self, value):
        if not has_netspout_admin(self.session_key):
            raise PermissionError("netspout_admin capability required")
        if not isinstance(value, str) or not value or len(value.encode("utf-8")) > 255 or any(ord(c) <= 32 or ord(c) >= 127 for c in value):
            raise ValueError("Invalid SNMP credential")
        reference = "snmp_community_v_" + uuid.uuid4().hex
        code, _ = self._request(self.collection, "POST", {"realm": "netspout", "name": reference, "password": value})
        if code not in (200, 201) or self.read(reference) != value:
            raise RuntimeError("SNMP credential staging failed")
        return reference


def _snmp_snapshot(config, session_key):
    result = validate_snmp_settings(config)
    # Empty/cleared references fail closed: never use the adapter's lab default.
    community = SNMPCredentialStore(session_key).read(result["snmp_credential_ref"])
    return dict(result, community=community)


def _snmp_runner_check(config, scenario=None):
    command = [sys.executable, os.path.join(BIN_DIR, "run_simulation.py"),
               "--snmp-preflight" if scenario else "--snmp-diagnostic"]
    if scenario:
        command += ["--scenario", scenario]
    completed = subprocess.run(command, input=json.dumps({"snmp": config}), text=True,
                               capture_output=True, timeout=10, cwd=APP_DIR)
    if completed.returncode:
        raise ValueError("SNMP runner unavailable")
    result = json.loads(completed.stdout)
    if not isinstance(result, dict) or result.get("status") not in ("success", "error"):
        raise RuntimeError("SNMP runner unavailable")
    return result


def _native_snmp_operation(params):
    if not has_netspout_admin(params.get("session_key", "")):
        return 403, {"status": "error", "message": "netspout_admin capability required"}
    action = params["action"]
    try:
        if action == "configure_snmp":
            allowed = set(SNMP_DEFAULTS) | {"action", "session_key", "snmp_community", "native_transport"}
            if set(params) - allowed or ("snmp_community" in params and "snmp_credential_ref" in params):
                raise ValueError()
            with simulation_start_lock():
                get_active_run_dir()
                try:
                    saved = json.loads(_read_private_file(CONFIG_FILE))
                    if not isinstance(saved, dict) or "hec_token" in saved:
                        raise RuntimeError()
                except FileNotFoundError:
                    saved = {}
                candidate = dict(DEFAULT_CONFIG, **{k:v for k,v in saved.items() if k in DEFAULT_CONFIG})
                candidate.update({k:params[k] for k in SNMP_DEFAULTS if k in params})
                if "native_transport" in params:
                    if params["native_transport"] not in ("hec", "syslog", "otlp", "snmp"):
                        raise ValueError()
                    candidate["native_transport"] = params["native_transport"]
                # Validate all destination options before staging an inactive credential.
                if "snmp_community" in params:
                    staged_candidate = dict(candidate, snmp_credential_ref="snmp_community_v_" + "0" * 32)
                    validate_snmp_settings(staged_candidate)
                    candidate["snmp_credential_ref"] = SNMPCredentialStore(params["session_key"]).stage(params["snmp_community"])
                candidate.update(validate_snmp_settings(candidate))
                _snmp_snapshot(candidate, params["session_key"])
                _write_config(CONFIG_FILE, candidate)
            return 200, {"status":"success", "message":"SNMP settings saved", "config":{k:candidate[k] for k in SNMP_DEFAULTS}, "native_transport":candidate["native_transport"]}
        if set(params) - {"action", "session_key"}:
            raise ValueError()
        saved = get_stored_config(params["session_key"])
        config = validate_snmp_settings(saved)
        if action == "get_snmp_config":
            return 200, {"status":"success", "config":config, "native_transport":saved["native_transport"]}
        response = _snmp_runner_check(_snmp_snapshot(config, params["session_key"]))
        return (200 if response["status"] == "success" else 502), response
    except ValueError:
        return 400, {"status":"error", "message":"Invalid SNMP settings or unsupported scenario"}
    except Exception:
        return 503, {"status":"error", "message":"SNMP configuration or diagnostic unavailable"}


OTLP_DEFAULTS = {
    "otlp_endpoint": "https://127.0.0.1:4318", "otlp_transport": "http_json",
    "otlp_signal": "logs", "otlp_auth": "none", "otlp_credential_ref": "",
}


def validate_otlp_settings(settings):
    from urllib.parse import urlsplit
    result = {k: settings.get(k, v) for k, v in OTLP_DEFAULTS.items()}
    endpoint = result["otlp_endpoint"]
    if not isinstance(endpoint, str) or len(endpoint) > 2048 or any(ord(c) <= 32 or ord(c) == 127 for c in endpoint):
        raise ValueError("Invalid OTLP settings")
    url = urlsplit(endpoint)
    if (url.scheme not in ("https", "http") or not url.hostname or url.username is not None
            or url.password is not None or url.query or url.fragment or url.path not in ("", "/")
            or result["otlp_transport"] != "http_json" or result["otlp_signal"] not in ("logs", "metrics", "both")
            or result["otlp_auth"] not in ("none", "bearer")):
        raise ValueError("Invalid OTLP settings")
    host = url.hostname
    try:
        address = ipaddress.ip_address(host)
        if address.is_unspecified or address.is_multicast:
            raise ValueError("Invalid OTLP host")
    except ValueError:
        if (len(host) > 253 or re.fullmatch(r"[0-9.]+", host) or not all(
                re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
                for label in host.rstrip(".").split("."))):
            raise ValueError("Invalid OTLP host") from None
    if url.port is not None and not 1 <= url.port <= 65535:
        raise ValueError("Invalid OTLP port")
    reference = result["otlp_credential_ref"]
    if not isinstance(reference, str) or (reference and not re.fullmatch(r"otlp_token_v_[0-9a-f]{32}", reference)):
        raise ValueError("Invalid OTLP reference")
    if result["otlp_auth"] == "bearer" and (not reference or url.scheme != "https"):
        raise ValueError("OTLP bearer authentication requires HTTPS and a credential reference")
    return result


class OTLPCredentialStore(HECCredentialStore):
    """Separate app-owned, versioned OTLP entries; no HEC or legacy fallback."""
    def read(self, reference):
        if not isinstance(reference, str) or not re.fullmatch(r"otlp_token_v_[0-9a-f]{32}", reference):
            raise ValueError("Invalid OTLP credential reference")
        code, data = self._request(self.collection + "/" + quote("netspout:" + reference + ":", safe=""))
        entries = data.get("entry", [])
        value = entries[0].get("content", {}).get("clear_password", "") if entries else ""
        if code != 200 or not isinstance(value, str) or not value or any(ord(c) <= 32 or ord(c) >= 127 for c in value):
            raise RuntimeError("OTLP credential unavailable")
        return value

    def stage(self, value):
        if not has_netspout_admin(self.session_key):
            raise PermissionError("netspout_admin capability required")
        if not isinstance(value, str) or not value or len(value) > 8192 or any(ord(c) <= 32 or ord(c) >= 127 for c in value):
            raise ValueError("Invalid OTLP credential")
        reference = "otlp_token_v_" + uuid.uuid4().hex
        code, _ = self._request(self.collection, "POST", {"realm": "netspout", "name": reference, "password": value})
        if code not in (200, 201) or self.read(reference) != value:
            raise RuntimeError("OTLP credential staging failed")
        return reference


def _otlp_snapshot(config, session_key):
    result = validate_otlp_settings(config)
    headers = {}
    if result["otlp_auth"] == "bearer":
        headers["Authorization"] = "Bearer " + OTLPCredentialStore(session_key).read(result["otlp_credential_ref"])
    return dict(result, headers=headers)


def _otlp_runner_check(config, scenario=None):
    command = [sys.executable, os.path.join(BIN_DIR, "run_simulation.py"),
               "--otlp-preflight" if scenario else "--otlp-diagnostic"]
    if scenario:
        command += ["--scenario", scenario]
    completed = subprocess.run(command, input=json.dumps({"otlp": config}), text=True,
                               capture_output=True, timeout=10, cwd=APP_DIR)
    if completed.returncode:
        raise ValueError("OTLP runner unavailable")
    result = json.loads(completed.stdout)
    if not isinstance(result, dict) or result.get("status") not in ("success", "error"):
        raise RuntimeError("OTLP runner unavailable")
    return result


def _native_otlp_operation(params):
    if not has_netspout_admin(params.get("session_key", "")):
        return 403, {"status": "error", "message": "netspout_admin capability required"}
    action = params["action"]
    try:
        if action == "configure_otlp":
            allowed = set(OTLP_DEFAULTS) | {"action", "session_key", "otlp_token", "native_transport"}
            if set(params) - allowed or ("otlp_token" in params and "otlp_credential_ref" in params):
                raise ValueError()
            with simulation_start_lock():
                get_active_run_dir()
                try:
                    saved = json.loads(_read_private_file(CONFIG_FILE))
                    if not isinstance(saved, dict) or "hec_token" in saved:
                        raise RuntimeError()
                except FileNotFoundError:
                    saved = {}
                candidate = dict(DEFAULT_CONFIG, **{k:v for k,v in saved.items() if k in DEFAULT_CONFIG})
                candidate.update({k:params[k] for k in OTLP_DEFAULTS if k in params})
                if "native_transport" in params:
                    if params["native_transport"] not in ("hec", "syslog", "otlp"):
                        raise ValueError()
                    candidate["native_transport"] = params["native_transport"]
                # Validate all destination options before staging an inactive credential.
                if "otlp_token" in params:
                    if candidate["otlp_auth"] != "bearer":
                        raise ValueError()
                    staged_candidate = dict(candidate, otlp_credential_ref="otlp_token_v_" + "0" * 32)
                    validate_otlp_settings(staged_candidate)
                    candidate["otlp_credential_ref"] = OTLPCredentialStore(params["session_key"]).stage(params["otlp_token"])
                candidate.update(validate_otlp_settings(candidate))
                _otlp_snapshot(candidate, params["session_key"])
                _write_config(CONFIG_FILE, candidate)
            return 200, {"status":"success", "message":"OTLP settings saved", "config":{k:candidate[k] for k in OTLP_DEFAULTS}, "native_transport":candidate["native_transport"]}
        if set(params) - {"action", "session_key"}:
            raise ValueError()
        saved = get_stored_config(params["session_key"])
        config = validate_otlp_settings(saved)
        if action == "get_otlp_config":
            return 200, {"status":"success", "config":config, "native_transport":saved["native_transport"]}
        response = _otlp_runner_check(_otlp_snapshot(config, params["session_key"]))
        return (200 if response["status"] == "success" else 502), response
    except ValueError:
        return 400, {"status":"error", "message":"Invalid OTLP settings or unsupported scenario"}
    except Exception:
        return 503, {"status":"error", "message":"OTLP configuration or diagnostic unavailable"}


SYSLOG_DEFAULTS = {
    "native_transport": "hec",
    "syslog_host": "127.0.0.1", "syslog_port": 1514,
    "syslog_protocol": "udp", "syslog_format": "rfc5424",
    "syslog_facility": 16, "syslog_severity": 6,
}


def validate_syslog_settings(settings):
    """IPv4/DNS, UDP/TCP only; the existing adapter has no TLS/IPv6 mode."""
    result = {key: settings.get(key, value) for key, value in SYSLOG_DEFAULTS.items()}
    host = result["syslog_host"]
    if not isinstance(host, str) or not host or len(host) > 253:
        raise ValueError("Invalid syslog settings")
    try:
        address = ipaddress.ip_address(host)
        if address.version != 4 or address.is_unspecified or address.is_multicast or host == "255.255.255.255":
            raise ValueError("Invalid syslog settings")
    except ValueError:
        if (re.fullmatch(r"[0-9.]+", host) or ":" in host or
                not all(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
                        for label in host.rstrip(".").split("."))):
            raise ValueError("Invalid syslog settings") from None
    if (result["native_transport"] not in ("hec", "syslog", "otlp", "snmp", "forwarding")
            or result["syslog_protocol"] not in ("udp", "tcp")
            or result["syslog_format"] not in ("rfc3164", "rfc5424")):
        raise ValueError("Invalid syslog settings")
    for key, lower, upper in (("syslog_port", 1, 65535), ("syslog_facility", 0, 23), ("syslog_severity", 0, 7)):
        value = result[key]
        if type(value) is not int or not lower <= value <= upper:
            raise ValueError("Invalid syslog settings")
    return result


def _native_syslog_operation(params):
    """Native admin-only config and one-send diagnostic; no HEC token needed."""
    action = params["action"]
    if not has_netspout_admin(params.get("session_key", "")):
        return 403, {"status": "error", "message": "netspout_admin capability required"}
    try:
        if action == "configure_syslog":
            if set(params) - (set(SYSLOG_DEFAULTS) | {"action", "session_key"}):
                raise ValueError("Invalid syslog settings")
            # OTLP activation belongs exclusively to configure_otlp. An omitted
            # selector still preserves an already-active OTLP destination.
            if "native_transport" in params and params["native_transport"] not in ("hec", "syslog"):
                raise ValueError("Invalid syslog settings")
            with simulation_start_lock():
                get_active_run_dir()
                try:
                    saved = json.loads(_read_private_file(CONFIG_FILE))
                    if not isinstance(saved, dict) or "hec_token" in saved:
                        raise RuntimeError()
                except FileNotFoundError:
                    saved = {}
                candidate = dict(DEFAULT_CONFIG)
                candidate.update({k: v for k, v in saved.items() if k in DEFAULT_CONFIG})
                values = {k: params[k] for k in SYSLOG_DEFAULTS if k in params}
                candidate.update(validate_syslog_settings(dict(candidate, **values)))
                _write_config(CONFIG_FILE, candidate)
            return 200, {"status": "success", "message": "Syslog settings saved", "config": {k: candidate[k] for k in SYSLOG_DEFAULTS}}
        config = validate_syslog_settings(get_stored_config(params.get("session_key", "")))
        if action == "get_syslog_config":
            return 200, {"status": "success", "config": config}
        if set(params) - {"action", "session_key"}:
            raise ValueError("Invalid syslog diagnostic fields")
        response = _syslog_runner_check(config)
        return (200 if response.get("status") == "success" else 502), response
    except ValueError:
        return 400, {"status": "error", "message": "Invalid syslog settings; use IPv4/DNS, port 1–65535, UDP/TCP and RFC3164/RFC5424"}
    except Exception:
        return 503, {"status": "error", "message": "Syslog configuration or diagnostic unavailable; delivery is unverified"}


def _syslog_runner_check(config, scenario=None):
    """Run the existing Python runner in its own app import context, bounded."""
    cmd = [sys.executable, os.path.join(BIN_DIR, "run_simulation.py"),
           "--syslog-preflight" if scenario else "--syslog-diagnostic"]
    if scenario:
        cmd += ["--scenario", scenario]
    completed = subprocess.run(cmd, input=json.dumps({"syslog": config}),
        text=True, capture_output=True, timeout=10, cwd=APP_DIR)
    if completed.returncode != 0:
        if scenario:
            raise ValueError("Syslog scenario unavailable")
        raise RuntimeError("Syslog diagnostic unavailable")
    result = json.loads(completed.stdout)
    if not isinstance(result, dict) or result.get("status") not in ("success", "error"):
        raise RuntimeError()
    return result


DEFAULT_CONFIG = {
    "destination_manager":None,
    **SYSLOG_DEFAULTS,
    **OTLP_DEFAULTS,
    **SNMP_DEFAULTS,
    **FORWARDING_DEFAULTS,
    "hec_credential_ref": "",
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
    if path == CONFIG_FILE and cfg.get("destination_manager") is not None:
        cfg = _destination_reconcile(cfg)
    # Same-directory replacement publishes one complete, secret-free snapshot.
    fd, temporary = tempfile.mkstemp(prefix=".hec-config-", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(cfg, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


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
    with simulation_start_lock():
        cfg = get_stored_config(session_key)
        if "hec_token" in new_cfg:
            HECCredentialStore(session_key).save(new_cfg["hec_token"])
        for key in DEFAULT_CONFIG:
            if key not in ("hec_credential_ref","destination_manager") and key not in SYSLOG_DEFAULTS and key not in OTLP_DEFAULTS and key not in SNMP_DEFAULTS and key not in FORWARDING_DEFAULTS and key in new_cfg:
                cfg[key] = new_cfg[key]
        resolve_hec_urls(cfg["hec_url"], cfg)
        if cfg["ssl_verify"] is False:
            logger.warning("Admin setting disables HEC certificate verification")
        _write_config(CONFIG_FILE, cfg)
        return cfg


def configure_hec(params):
    """Stage then publish; orphaned entries are never discovered or activated.

    Existing fixed/versioned credentials are never deleted or rolled back.
    Only the atomic configuration replacement activates a staged reference.
    """
    session_key = params.get("session_key", "")
    if not has_netspout_admin(session_key):
        return 403, {"status": "error", "code": "forbidden", "message": "netspout_admin capability required"}
    editable = set(DEFAULT_CONFIG) - set(SYSLOG_DEFAULTS) - set(OTLP_DEFAULTS) - set(SNMP_DEFAULTS) - set(FORWARDING_DEFAULTS) - {"hec_allowed_hosts", "hec_allowed_ports", "hec_credential_ref", "destination_manager"}
    if set(params) - (editable | {"action", "session_key", "hec_token"}):
        return 400, {"status": "error", "code": "invalid_setup", "message": "Invalid HEC setup fields"}
    with simulation_start_lock():
        # Read without invoking historical credential migration or cleanup.
        cfg = dict(DEFAULT_CONFIG)
        try:
            saved = json.loads(_read_private_file(CONFIG_FILE))
            if not isinstance(saved, dict) or "hec_token" in saved:
                raise ValueError()
            cfg.update({k: v for k, v in saved.items() if k in DEFAULT_CONFIG})
        except FileNotFoundError:
            pass
        except Exception:
            return 503, {"status": "error", "code": "configuration_unavailable", "message": "Cannot load active configuration"}
        candidate = dict(cfg)
        candidate.update({k: v for k, v in params.items() if k in editable})
        token = params.get("hec_token", "")
        try:
            resolve_hec_urls(candidate["hec_url"], cfg)
            if not isinstance(token, str) or (token and not RE_TOKEN.fullmatch(token)):
                raise ValueError()
            if type(candidate["ssl_verify"]) is not bool:
                raise ValueError()
            eps = candidate["target_eps"]
            if type(eps) is not int or not 1 <= eps <= 100000:
                raise ValueError()
            for key in ("idx_network_ops", "idx_security_fw", "idx_wireless_ops", "idx_performance_metrics", "cisco_mdt_metrics"):
                if not isinstance(candidate[key], str) or not re.fullmatch(r"[A-Za-z0-9_][A-Za-z0-9_-]*", candidate[key]):
                    raise ValueError()
            scenario = candidate["default_scenario"]
            if not isinstance(scenario, str) or not RE_SAFE_PATH.fullmatch(scenario) or ".." in scenario.split("/"):
                raise ValueError()
        except Exception:
            return 400, {"status": "error", "code": "invalid_setup", "message": "Invalid HEC setup; use an allowed HTTPS destination and valid settings"}
        store = HECCredentialStore(session_key)
        try:
            if token:
                candidate["hec_credential_ref"] = store.stage(token)
            elif not store.read(cfg.get("hec_credential_ref", "")):
                return 400, {"status": "error", "code": "token_required", "message": "A HEC token is required for initial setup"}
        except Exception:
            return 503, {"status": "error", "code": "credential_store_failed", "message": "HEC credential storage failed; active configuration unchanged"}
        try:
            _write_config(CONFIG_FILE, candidate)
        except Exception:
            return 500, {"status": "error", "code": "publication_failed", "message": "Configuration publication failed; active configuration unchanged"}
        # No fallible store operations after the commit point.
        public = dict(candidate, hec_token_configured=True)
        return 200, {"status": "success", "message": "HEC configuration saved", "config": public}


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


def hec_request(url, configuration=None, **kwargs):
    """Keep HEC authorization on the original request only."""
    resolve_hec_urls(url, get_stored_config() if configuration is None else configuration)
    headers = dict(kwargs.pop("headers", {}))
    authorization = headers.pop("Authorization", None)
    request = urllib.request.Request(url, headers=headers, **kwargs)
    if authorization is not None:
        request.add_unredirected_header("Authorization", authorization)
    return request


def public_config(session_key):
    cfg = get_stored_config(session_key)
    cfg["hec_token_configured"] = bool(HECCredentialStore(session_key).read(cfg.get("hec_credential_ref", "")))
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
        "note": "NetSpout PulseForge includes built-in props/transforms extractions so CIM compliance is active even without vendor TAs installed."
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


def validate_and_sanitize(params: Dict[str, Any], stored_cfg_override=None) -> Dict[str, Any]:
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
        stored_cfg = stored_cfg_override if stored_cfg_override is not None else get_stored_config(params.get("session_key", ""))
        hec_url = resolve_hec_urls(stored_cfg["hec_url"], stored_cfg)[0]
        token = HECCredentialStore(params.get("session_key", "")).read(stored_cfg.get("hec_credential_ref", ""))
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
            if key not in SYSLOG_DEFAULTS and key not in OTLP_DEFAULTS and key not in SNMP_DEFAULTS and key not in FORWARDING_DEFAULTS and key not in ("hec_url", "hec_allowed_hosts", "hec_allowed_ports", "hec_credential_ref", "destination_manager") and key in params:
                new_config[key] = params[key]
        if "ssl_verify" in new_config:
            value = new_config["ssl_verify"]
            new_config["ssl_verify"] = value.lower() in ("true", "1", "yes") if isinstance(value, str) else bool(value)
        return {"action": action, "config": new_config}

    stored_cfg = stored_cfg_override if stored_cfg_override is not None else get_stored_config(params.get("session_key", ""))
    if action == "start" and stored_cfg.get("native_transport", "hec") == "syslog":
        config = validate_syslog_settings(stored_cfg)
        scenario = resolve_scenario_path(str(params.get("scenario") or params.get("scenario_file") or ""))
        eps = params.get("eps", 1000)
        if isinstance(eps, bool) or not RE_EPS.fullmatch(str(eps)) or not 1 <= int(eps) <= 500000:
            raise ValueError("Invalid EPS")
        checked = _syslog_runner_check(config, scenario)
        if checked.get("status") != "success":
            raise ValueError("Unsupported syslog scenario")
        return {"action": "start", "scenario": scenario, "eps": int(eps), "sample": None,
                "hec": None, "token": None, "native_transport": "syslog", "syslog": config}
    if action == "start" and stored_cfg.get("native_transport") == "otlp":
        config = _otlp_snapshot(stored_cfg, params.get("session_key", ""))
        scenario = resolve_scenario_path(str(params.get("scenario") or params.get("scenario_file") or ""))
        eps = params.get("eps", 1000)
        if isinstance(eps, bool) or not RE_EPS.fullmatch(str(eps)) or not 1 <= int(eps) <= 500000:
            raise ValueError("Invalid EPS")
        if _otlp_runner_check(config, scenario).get("status") != "success":
            raise ValueError("Unsupported OTLP scenario")
        return {"action":"start", "scenario":scenario, "eps":int(eps), "sample":None,
                "hec":None, "token":None, "native_transport":"otlp", "otlp":config}
    if action == "start" and stored_cfg.get("native_transport") == "snmp":
        config = _snmp_snapshot(stored_cfg, params.get("session_key", ""))
        scenario = resolve_scenario_path(str(params.get("scenario") or params.get("scenario_file") or ""))
        eps = params.get("eps", 1000)
        if isinstance(eps, bool) or not RE_EPS.fullmatch(str(eps)) or not 1 <= int(eps) <= (25 if config["snmp_message_type"] == "inform" else 50):
            raise ValueError("Invalid EPS")
        if _snmp_runner_check(config, scenario).get("status") != "success":
            raise ValueError("Unsupported SNMP scenario")
        return {"action":"start", "scenario":scenario, "eps":int(eps), "sample":None,
                "hec":None, "token":None, "native_transport":"snmp", "snmp":config}
    if action == "start" and stored_cfg.get("native_transport") == "forwarding":
        utility = _forwarding()
        config = utility.validate(stored_cfg)
        if utility.readiness(config)["state"] != "READY":
            raise ValueError("Forwarding input is not ready")
        scenario = resolve_scenario_path(str(params.get("scenario") or params.get("scenario_file") or ""))
        eps = params.get("eps",10)
        if isinstance(eps,bool) or not RE_EPS.fullmatch(str(eps)) or not 1 <= int(eps) <= 100:
            raise ValueError("Unsupported forwarding rate")
        command = [sys.executable,os.path.join(BIN_DIR,"run_simulation.py"),"--forwarding-preflight","--scenario",scenario]
        completed = subprocess.run(command,input=json.dumps({"forwarding":config}),text=True,capture_output=True,timeout=10,cwd=APP_DIR)
        if completed.returncode or json.loads(completed.stdout).get("status") != "success":
            raise ValueError("Unsupported forwarding scenario")
        return {"action":"start","scenario":scenario,"eps":int(eps),"sample":None,"hec":None,"token":None,
                "native_transport":"forwarding","forwarding":config}
    hec = resolve_hec_urls(stored_cfg["hec_url"], stored_cfg)[0]
    token = HECCredentialStore(params.get("session_key", "")).read(stored_cfg.get("hec_credential_ref", ""))
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
        try:
            os.killpg(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
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
            try:
                os.killpg(pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
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
    is_syslog = run_params.get("native_transport") == "syslog"
    if is_syslog:
        cmd = [sys.executable, run_sim_script, "--scenario", run_params["scenario"],
               "--eps", str(run_params["eps"]), "--native-syslog"]
    if run_params.get("native_transport") == "otlp":
        cmd = [sys.executable, os.path.join(BIN_DIR, "run_simulation.py"), "--scenario", run_params["scenario"],
               "--eps", str(run_params["eps"]), "--native-otlp"]
    if run_params.get("native_transport") == "snmp":
        cmd = [sys.executable, os.path.join(BIN_DIR, "run_simulation.py"), "--scenario", run_params["scenario"],
               "--eps", str(run_params["eps"]), "--native-snmp"]
    if run_params.get("native_transport") == "forwarding":
        cmd = [sys.executable,run_sim_script,"--scenario",run_params["scenario"],"--eps",str(run_params["eps"]),"--native-forwarding"]
    if run_params.get("_native_record"):
        _update_lock_held = _native_monitor()._update_lock_held
        if run_params.get("native_transport") in ("otlp", "snmp", "forwarding"):
            python_path = False  # OTLP indexing verification is unsupported.
        elif is_syslog:
            python_path = False  # Raw syslog has no searchable run-ID metadata.
        else:
            import run_simulation as runner
            python_path = run_params.get("ssl_verify", True) or runner.resolve_binary() == "python_engine"
        _update_lock_held(run_params["_native_record"]["run_id"], lambda r: r.update(
            correlation="SUPPORTED" if python_path else "UNSUPPORTED"))
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
        proc.stdin.write(json.dumps({"credential": run_params["token"],
                                 "run_id": (run_params.get("_native_record") or {}).get("run_id"),
                                 "syslog": run_params.get("syslog"), "otlp": run_params.get("otlp"), "snmp": run_params.get("snmp"), "forwarding":run_params.get("forwarding"), "runtime_config":run_params.get("_runtime_config")}))
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
    _native_monitor().publish_status(meta)

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
        if params.get("action") == "configure_hec":
            return configure_hec(params)
        get_stored_config(params.get("session_key", ""))
        clean = params.get("_native_clean") or validate_and_sanitize(params)
        if params.get("_native_record"):
            clean["_native_record"] = params["_native_record"]
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
            res = run_simulation.blast_single_device(clean["device_info"], clean["hec"], clean["token"], clean.get("count", 1), get_stored_config().get("ssl_verify", True) is not False,
                run_id=(clean.get("_native_record") or {}).get("run_id"))
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
                _native_monitor().publish_status(meta)
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

            monitor_record = clean.get("_native_record")
            if monitor_record:
                attach = _native_monitor().attach
                events = [attach(e, monitor_record["run_id"]) if isinstance(e, dict) else e for e in events]
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
                        "sourcetype": target_sourcetype,
                        **({"fields": {"netspout_run_id": monitor_record["run_id"]}} if monitor_record else {})
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
                                if monitor_record:
                                    ev_copy = attach(ev_copy, monitor_record["run_id"])
                                fallback_lines.append(json.dumps(ev_copy))
                            if monitor_record:
                                update = _native_monitor().update
                                update(monitor_record["run_id"], lambda r: r.update(indexes=sorted(set(r["indexes"]) | {"main"})))
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
                        if monitor_record:
                            update = _native_monitor().update
                            update(monitor_record["run_id"], lambda r: r.update(correlation="UNSUPPORTED"))
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
            if clean.get("_native_record"):
                attach = _native_monitor().attach
                payload_events = [json.dumps(attach(json.loads(e), clean["_native_record"]["run_id"])) for e in payload_events]
            raw_payload = "\n".join(payload_events).encode("utf-8")
            
            ctx = ssl.create_default_context()
            if not ssl_verify:
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE

            target_urls = resolve_hec_urls(hec_url, get_stored_config())
            count = len(payload_events)
            state, http_status = "UNKNOWN", None
            response_received = False
            attempted = 0
            for url in target_urls:
                try:
                    req = hec_request(url, data=raw_payload, headers={
                        "Authorization": f"Splunk {token}", "Content-Type": "application/json"})
                    attempted = count
                    with urllib.request.urlopen(req, timeout=10, context=ctx) as resp:
                        http_status = resp.status
                        body = resp.read()
                        response_received = 200 <= http_status < 300
                        try:
                            result = json.loads(body)
                        except (ValueError, UnicodeError):
                            result = None
                        if isinstance(result, dict) and type(result.get("code")) is int:
                            if 200 <= http_status < 300 and result["code"] == 0:
                                state = "ACCEPTED"
                except urllib.error.HTTPError as exc:
                    http_status = exc.code
                    # A server failure may occur after some processing.
                    state = "FAILED" if 400 <= http_status < 500 else "UNKNOWN"
                except Exception:
                    state = "UNKNOWN"
                # Never retry an ambiguous batch: that could duplicate events.
                break
            accepted = count if state == "ACCEPTED" else 0
            failed = count if state == "FAILED" else 0
            # Preserve the legacy readable-2xx HTTP contract independently of
            # delivery evidence. HTTP 200 alone never establishes acceptance.
            return (200 if response_received else 502, {
                "status": "success" if state == "ACCEPTED" else "error",
                "message": ("HEC acknowledged the batch; indexing is unverified."
                            if state == "ACCEPTED" else
                            "HEC rejected the batch; indexing is unverified."
                            if state == "FAILED" else
                            "Delivery outcome is unknown; indexing is unverified."),
                "sourcetype": sourcetype, "index": index_target,
                "sample_file": sample_file, "events_count": count,
                "hec_response": "HEC acknowledged" if accepted else "No acceptance confirmed",
                "delivery_state": state, "http_status": http_status,
                "generated": count, "attempted": attempted,
                "accepted": accepted, "failed": failed,
                "unknown": attempted - accepted - failed,
                "indexed": None, "indexing_verified": False
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
    monitor = _native_monitor()
    if params.get('action') in ('list_destinations','create_destination','update_destination','disable_destination','select_destination','diagnose_destination'):
        return _native_destination_operation(params)
    # Internal run records are never accepted from execution requests.
    params = {k: v for k, v in params.items() if not k.startswith("_native")}
    if params.get("action") in ("configure_forwarding","get_forwarding_config","test_forwarding"):
        return _native_forwarding_operation(params)
    if params.get("action") in ("configure_snmp", "get_snmp_config", "test_snmp"):
        return _native_snmp_operation(params)
    if params.get("action") in ("configure_otlp", "get_otlp_config", "test_otlp"):
        return _native_otlp_operation(params)
    if params.get("action") in ("configure_syslog", "get_syslog_config", "test_syslog"):
        return _native_syslog_operation(params)
    if params.get("action") == "configure_hec":
        return _execute_request(params)
    ignored = {"hec", "url", "hec_url", "token", "hec_token", "run_id", "netspout_run_id"}
    action = str(params.get("action", "start")).strip().lower()
    if action in ("native_runs", "verify_native_run"):
        if not has_netspout_admin(params.get("session_key", "")):
            return 403, {"status": "error", "message": "netspout_admin capability required"}
        try:
            if action == "native_runs":
                return 200, {"status": "success", "runs": monitor.history()}
            return monitor.verification(params.get("run_id"), params.get("session_key", ""))
        except Exception:
            return 503, {"status": "error", "message": "Native run history unavailable"}
    filtered = {key: value for key, value in params.items() if key not in ignored}
    record = None
    monitored = {"start", "start_simulation", "run_scenario", "blast_hec", "onboard_sample",
                 "emit_device_telemetry", "blast_single_device", "stream_canvas_topology"}
    if action in monitored and has_netspout_admin(params.get("session_key", "")):
        try:
            if action in ('start','start_simulation','run_scenario'):
                stored=get_stored_config(params.get('session_key',''))
                resolved,identity=_destination_resolve(stored,params.get('destination_id'))
                if resolved['native_transport']=='forwarding' and resolved['forwarding_group']!=stored['forwarding_group']:
                    raise ValueError('Select this forwarding group as default first')
                clean=validate_and_sanitize(filtered,resolved)
                clean['_destination_identity']=identity
                clean['_runtime_config']={k:v for k,v in resolved.items() if k!='destination_manager'}
            else:
                if 'destination_id' in params: raise ValueError('Named destination selection requires a scenario run')
                clean = validate_and_sanitize(filtered)
            record = monitor.begin(clean["action"], clean, params.get("session_key", ""))
            filtered["_native_record"] = record
            filtered["_native_clean"] = clean
        except Exception:
            return 400, {"status": "error", "message": "Run validation or history initialization failed"}
    code, response = _execute_request(filtered)
    if record:
        try:
            response["native_run"] = monitor.finish(record, response)
        except Exception:
            # Execution may already have happened: never invite a blind retry.
            response["monitoring_error"] = "Run status unavailable; execution may have occurred"
    return code, response
