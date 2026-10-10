# =========================================================================
# AUTO-GENERATED PACKAGED COPY — DO NOT EDIT DIRECTLY!
# Authoritative Source of Truth: src/netspout_core/release_candidate.py
# Re-generate using: python3 scripts/sync_core.py
# =========================================================================
"""Phase 13 release-candidate services shared by every deployment adapter."""

from __future__ import annotations

import json
import os
import re
import stat
import tempfile
import base64
import ssl
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse


SOURCE_STATUSES = {
    "IMPLEMENTED_AND_VALIDATED",
    "IMPLEMENTED_NOT_VALIDATED",
    "PARTIAL",
    "RESEARCH_REQUIRED",
    "NOT_IMPLEMENTED",
    "UNSUPPORTED",
}
RUNNABLE_SOURCE_STATUSES = {
    "IMPLEMENTED_AND_VALIDATED",
    "IMPLEMENTED_NOT_VALIDATED",
}
DEPLOYMENT_MODES = {"DOCKER_LAB", "SPLUNK_ENTERPRISE", "SPLUNK_CLOUD"}
AUTH_METHODS = {"HEC_TOKEN_AND_BASIC_SEARCH", "HEC_TOKEN_AND_SPLUNK_TOKEN"}
INDEX_NAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,79}$")


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _catalog_path() -> Path:
    module_dir = Path(__file__).resolve().parent
    candidates = (
        module_dir.parent.parent / "catalog" / "phase13_security_source_coverage.json",
        module_dir / "catalog_data" / "phase13_security_source_coverage.json",
        module_dir.parent / "catalog_data" / "phase13_security_source_coverage.json",
        Path("/opt/splunk/etc/apps/netspout/bin/catalog_data/phase13_security_source_coverage.json"),
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("Phase 13 security source coverage catalog is unavailable")


class SecuritySourceCatalog:
    """Read-only audited source coverage; it never upgrades runtime maturity."""

    def __init__(self, path: Optional[Path] = None):
        self.path = path or _catalog_path()
        self.document = json.loads(self.path.read_text(encoding="utf-8"))
        self._validate()

    def _validate(self) -> None:
        identifiers = set()
        for source in self.document.get("sources", []):
            source_id = source.get("coverage_id")
            if not source_id or source_id in identifiers:
                raise ValueError("Security source coverage IDs must be unique and non-empty")
            identifiers.add(source_id)
            if source.get("status") not in SOURCE_STATUSES:
                raise ValueError(f"Unsupported source coverage status for {source_id}")
            if source.get("sample_generation", {}).get("runnable"):
                if source["status"] not in RUNNABLE_SOURCE_STATUSES:
                    raise ValueError(f"Non-implemented source {source_id} cannot be runnable")
                if not (source.get("catalog_source_ids") or source.get("scenario_ids")):
                    raise ValueError(f"Runnable source {source_id} requires a catalog source or scenario")

    def list_sources(self) -> List[Dict[str, Any]]:
        return list(self.document["sources"])

    def get_source(self, coverage_id: str) -> Optional[Dict[str, Any]]:
        return next(
            (item for item in self.document["sources"] if item["coverage_id"] == coverage_id),
            None,
        )

    def summary(self) -> Dict[str, Any]:
        sources = self.document["sources"]
        return {
            "schema_version": self.document["schema_version"],
            "catalog_version": self.document["catalog_version"],
            "source_count": len(sources),
            "status_counts": dict(Counter(item["status"] for item in sources)),
            "domain_counts": dict(Counter(item["domain"] for item in sources)),
            "runnable_count": sum(
                bool(item.get("sample_generation", {}).get("runnable")) for item in sources
            ),
        }


def _is_loopback(hostname: Optional[str]) -> bool:
    return hostname in {"localhost", "127.0.0.1", "::1"}


def validate_splunk_endpoint(value: str, *, allow_loopback_http: bool = False) -> str:
    parsed = urlparse(value)
    if parsed.username or parsed.password:
        raise ValueError("Credentials must not be embedded in endpoint URLs")
    if parsed.scheme not in {"https", "http"} or not parsed.hostname:
        raise ValueError("Endpoint must be an absolute HTTP(S) URL")
    if parsed.scheme == "http" and not (allow_loopback_http and _is_loopback(parsed.hostname)):
        raise ValueError("TLS is required except for an explicitly selected loopback lab endpoint")
    if parsed.hostname in {"0.0.0.0", "::"}:
        raise ValueError("Wildcard listener addresses are not valid destinations")
    return value.rstrip("/")


@dataclass
class ConnectionSecretState:
    hec_token: Optional[str] = None
    search_secret: Optional[str] = None

    def clear(self) -> None:
        self.hec_token = None
        self.search_secret = None


class ReleaseCandidateConfiguration:
    """Persists non-secret setup metadata and keeps submitted secrets in memory only."""

    def __init__(self, config_dir: Optional[str] = None):
        root = config_dir or os.environ.get("NETSPOUT_CONFIG_DIR")
        if not root:
            root = os.path.join(tempfile.gettempdir(), "netspout")
        self.config_dir = Path(root)
        self.path = self.config_dir / "connection.json"
        self.secrets = ConnectionSecretState(
            hec_token=os.environ.get("NETSPOUT_HEC_TOKEN"),
            search_secret=(
                os.environ.get("NETSPOUT_SPLUNK_TOKEN")
                or os.environ.get("NETSPOUT_SPLUNK_PASSWORD")
            ),
        )

    def load(self) -> Dict[str, Any]:
        if not self.path.is_file():
            return {
                "configured": False,
                "deployment_mode": None,
                "secret_state": self.secret_state(),
            }
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        payload["configured"] = True
        payload["secret_state"] = self.secret_state()
        return payload

    def secret_state(self) -> Dict[str, bool]:
        return {
            "hec_token_configured": bool(self.secrets.hec_token),
            "search_secret_configured": bool(self.secrets.search_secret),
        }

    def save(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        mode = payload.get("deployment_mode")
        auth_method = payload.get("auth_method")
        if mode not in DEPLOYMENT_MODES:
            raise ValueError("Unsupported deployment mode")
        if auth_method not in AUTH_METHODS:
            raise ValueError("Unsupported authentication method")
        allow_lab_http = mode == "DOCKER_LAB"
        hec_url = validate_splunk_endpoint(
            str(payload.get("hec_url", "")),
            allow_loopback_http=allow_lab_http,
        )
        search_url = validate_splunk_endpoint(
            str(payload.get("search_url", "")),
            allow_loopback_http=allow_lab_http,
        )
        indexes = sorted(
            {
                str(item).strip()
                for item in payload.get("indexes", [])
                if str(item).strip()
            }
        )
        if not indexes:
            raise ValueError("At least one authorized index is required")
        if any(not INDEX_NAME_PATTERN.fullmatch(index) for index in indexes):
            raise ValueError(
                "Index names may contain only letters, numbers, underscores, and hyphens"
            )

        hec_token = str(payload.get("hec_token") or "").strip()
        search_secret = str(payload.get("search_secret") or "").strip()
        current = self.load()
        destination_changed = not current.get("configured") or any(
            current.get(field) != value
            for field, value in (
                ("hec_url", hec_url),
                ("search_url", search_url),
                ("auth_method", auth_method),
            )
        )
        if destination_changed and (not hec_token or not search_secret):
            raise ValueError(
                "Re-enter both credentials when configuring or changing Splunk endpoints"
            )
        if hec_token:
            self.secrets.hec_token = hec_token
        if search_secret:
            self.secrets.search_secret = search_secret
        if not self.secrets.hec_token or not self.secrets.search_secret:
            raise ValueError("Both ingestion and search credentials must be configured")

        safe = {
            "schema_version": "1.0.0",
            "deployment_mode": mode,
            "splunk_deployment_type": payload.get("splunk_deployment_type", mode),
            "hec_url": hec_url,
            "search_url": search_url,
            "auth_method": auth_method,
            "search_username": str(payload.get("search_username") or "").strip() or None,
            "indexes": indexes,
            "collectors": sorted(set(payload.get("collectors", []))),
            "guided_sample": bool(payload.get("guided_sample", True)),
            "allow_insecure_tls": bool(payload.get("allow_insecure_tls", False)),
        }
        if safe["allow_insecure_tls"]:
            parsed_hosts = {urlparse(hec_url).hostname, urlparse(search_url).hostname}
            if not all(_is_loopback(host) for host in parsed_hosts):
                raise ValueError("TLS verification can be disabled only for loopback lab endpoints")

        self.config_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        temporary = self.path.with_suffix(".tmp")
        temporary.write_text(json.dumps(safe, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(temporary, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(temporary, self.path)
        return self.load()

    def reset(self) -> Dict[str, Any]:
        self.secrets.clear()
        if self.path.exists():
            self.path.unlink()
        return self.load()

    def validate_connection(self) -> Dict[str, Any]:
        config = self.load()
        if not config.get("configured"):
            return {"status": "BLOCKED", "checks": [{"id": "configuration", "status": "FAIL", "detail": "Setup is incomplete."}]}

        checks = []
        context = ssl.create_default_context()
        if config.get("allow_insecure_tls"):
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

        opener = urllib.request.build_opener(
            urllib.request.HTTPHandler(),
            urllib.request.HTTPSHandler(context=context),
            NoRedirectHandler(),
        )

        def request(
            url: str,
            authorization: str,
            *,
            data: Optional[bytes] = None,
            content_type: Optional[str] = None,
        ) -> tuple[bool, str]:
            headers = {"Authorization": authorization}
            if content_type:
                headers["Content-Type"] = content_type
            req = urllib.request.Request(url, data=data, headers=headers)
            try:
                with opener.open(req, timeout=5) as response:
                    return 200 <= response.status < 300, f"HTTP {response.status}"
            except (urllib.error.URLError, TimeoutError, OSError) as exc:
                return False, str(exc.reason if isinstance(exc, urllib.error.URLError) else exc)

        hec_ok, hec_detail = request(
            config["hec_url"].rstrip("/") + "/event",
            f"Splunk {self.secrets.hec_token}",
            data=json.dumps(
                {
                    "event": {
                        "event_type": "netspout_setup_probe",
                        "purpose": "authorized_ingestion_validation",
                    },
                    "index": config["indexes"][0],
                    "sourcetype": "netspout:setup:probe",
                }
            ).encode("utf-8"),
            content_type="application/json",
        )
        checks.append(
            {
                "id": "hec",
                "status": "PASS" if hec_ok else "FAIL",
                "detail": (
                    f"{hec_detail}; authorized bounded probe accepted"
                    if hec_ok
                    else hec_detail
                ),
            }
        )

        if config["auth_method"] == "HEC_TOKEN_AND_SPLUNK_TOKEN":
            search_authorization = f"Bearer {self.secrets.search_secret}"
        else:
            username = config.get("search_username") or ""
            encoded = base64.b64encode(
                f"{username}:{self.secrets.search_secret}".encode("utf-8")
            ).decode("ascii")
            search_authorization = f"Basic {encoded}"
        search_ok, search_detail = request(
            config["search_url"],
            search_authorization,
            data=urllib.parse.urlencode(
                {
                    "search": "| makeresults | head 1",
                    "output_mode": "json",
                }
            ).encode("utf-8"),
            content_type="application/x-www-form-urlencoded",
        )
        checks.append({"id": "search", "status": "PASS" if search_ok else "FAIL", "detail": search_detail})
        index_ok, index_detail = request(
            config["search_url"],
            search_authorization,
            data=urllib.parse.urlencode(
                {
                    "search": (
                        f'search index="{config["indexes"][0]}" earliest=-5m '
                        "| head 1"
                    ),
                    "output_mode": "json",
                }
            ).encode("utf-8"),
            content_type="application/x-www-form-urlencoded",
        )
        checks.append(
            {
                "id": "indexes",
                "status": "PASS" if index_ok else "FAIL",
                "detail": (
                    f"{index_detail}; queried authorized index {config['indexes'][0]}"
                    if index_ok
                    else index_detail
                ),
            }
        )
        return {
            "status": "PASS" if all(item["status"] == "PASS" for item in checks) else "BLOCKED",
            "checks": checks,
            "secret_state": self.secret_state(),
        }

    def execute_read_only_search(
        self, query: str, *, timeout: float = 8.0, result_limit: int = 200
    ) -> tuple[List[Dict[str, Any]], Optional[str]]:
        """Execute bounded SPL against the configured destination without exposing secrets."""
        config = self.load()
        if not config.get("configured") or not self.secrets.search_secret:
            return [], "authenticated Splunk search is not configured"
        if timeout <= 0 or timeout > 30 or result_limit < 1 or result_limit > 500:
            return [], "search bounds are outside policy"
        context = ssl.create_default_context()
        if config.get("allow_insecure_tls"):
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
        if config["auth_method"] == "HEC_TOKEN_AND_SPLUNK_TOKEN":
            authorization = f"Bearer {self.secrets.search_secret}"
        else:
            username = config.get("search_username") or ""
            encoded = base64.b64encode(
                f"{username}:{self.secrets.search_secret}".encode("utf-8")
            ).decode("ascii")
            authorization = f"Basic {encoded}"
        request = urllib.request.Request(
            config["search_url"],
            data=urllib.parse.urlencode(
                {"search": query, "output_mode": "json"}
            ).encode("utf-8"),
            headers={
                "Authorization": authorization,
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        opener = urllib.request.build_opener(
            urllib.request.HTTPHandler(),
            urllib.request.HTTPSHandler(context=context),
            NoRedirectHandler(),
        )
        rows: List[Dict[str, Any]] = []
        try:
            with opener.open(request, timeout=timeout) as response:
                for line in response:
                    try:
                        payload = json.loads(line.decode("utf-8"))
                    except (UnicodeDecodeError, json.JSONDecodeError):
                        continue
                    result = payload.get("result")
                    if isinstance(result, dict):
                        rows.append(result)
                    if len(rows) >= result_limit:
                        break
            return rows, None
        except (urllib.error.URLError, TimeoutError, OSError, ssl.SSLError) as exc:
            return [], type(exc).__name__
