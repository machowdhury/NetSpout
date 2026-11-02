import json
import os
import sys
import tarfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from netspout_core.release_candidate import (
    ReleaseCandidateConfiguration,
    SecuritySourceCatalog,
    validate_splunk_endpoint,
)


ROOT = Path(__file__).resolve().parents[1]


def test_security_source_catalog_covers_required_domains_and_fails_closed():
    catalog = SecuritySourceCatalog(
        ROOT / "catalog" / "phase13_security_source_coverage.json"
    )
    sources = catalog.list_sources()
    assert len(sources) >= 29
    assert {
        "Network security",
        "Endpoint security",
        "Identity security",
        "Cloud security",
        "Application security",
        "AI and software supply chain",
    } <= {source["domain"] for source in sources}
    for source in sources:
        if source["status"] in {
            "PARTIAL",
            "RESEARCH_REQUIRED",
            "NOT_IMPLEMENTED",
            "UNSUPPORTED",
        }:
            assert source["sample_generation"]["runnable"] is False


def test_setup_persists_only_metadata_with_owner_permissions(tmp_path):
    service = ReleaseCandidateConfiguration(str(tmp_path))
    saved = service.save(
        {
            "deployment_mode": "DOCKER_LAB",
            "splunk_deployment_type": "DOCKER_BUNDLED_ENTERPRISE",
            "hec_url": "https://127.0.0.1:8088/services/collector",
            "search_url": "https://127.0.0.1:8089/services/search/jobs/export",
            "auth_method": "HEC_TOKEN_AND_BASIC_SEARCH",
            "search_username": "least-privilege-user",
            "hec_token": "runtime-supplied-hec-value",
            "search_secret": "runtime-supplied-search-value",
            "indexes": ["idx_network_ops"],
            "collectors": ["HEC"],
            "guided_sample": True,
            "allow_insecure_tls": True,
        }
    )
    raw = service.path.read_text(encoding="utf-8")
    assert "runtime-supplied" not in raw
    assert saved["secret_state"] == {
        "hec_token_configured": True,
        "search_secret_configured": True,
    }
    assert service.path.stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize(
    "url",
    [
        "file:///etc/passwd",
        "https://user:credential@example.invalid/services/collector",
        "http://example.invalid/services/collector",
        "https://0.0.0.0:8088/services/collector",
    ],
)
def test_setup_endpoint_validation_rejects_unsafe_destinations(url):
    with pytest.raises(ValueError):
        validate_splunk_endpoint(url, allow_loopback_http=True)


def test_setup_endpoint_validation_allows_explicit_loopback_lab_http():
    assert (
        validate_splunk_endpoint(
            "http://127.0.0.1:8088/services/collector",
            allow_loopback_http=True,
        )
        == "http://127.0.0.1:8088/services/collector"
    )


def test_setup_requires_credentials_again_when_destination_changes(tmp_path):
    service = ReleaseCandidateConfiguration(str(tmp_path))
    base = {
        "deployment_mode": "SPLUNK_ENTERPRISE",
        "splunk_deployment_type": "SPLUNK_ENTERPRISE",
        "hec_url": "https://splunk.example.invalid:8088/services/collector",
        "search_url": "https://splunk.example.invalid:8089/services/search/jobs/export",
        "auth_method": "HEC_TOKEN_AND_BASIC_SEARCH",
        "search_username": "operator",
        "hec_token": "runtime-hec-value",
        "search_secret": "runtime-search-value",
        "indexes": ["idx_network_ops"],
    }
    service.save(base)

    changed = dict(base)
    changed.update(
        {
            "hec_url": "https://attacker.example.invalid/services/collector",
            "search_url": "https://attacker.example.invalid/services/search/jobs/export",
            "hec_token": "",
            "search_secret": "",
        }
    )
    with pytest.raises(ValueError, match="Re-enter both credentials"):
        service.save(changed)


def test_setup_rejects_spl_injection_in_index_name(tmp_path):
    service = ReleaseCandidateConfiguration(str(tmp_path))
    with pytest.raises(ValueError, match="Index names"):
        service.save(
            {
                "deployment_mode": "SPLUNK_ENTERPRISE",
                "hec_url": "https://splunk.example.invalid/services/collector",
                "search_url": "https://splunk.example.invalid/services/search/jobs/export",
                "auth_method": "HEC_TOKEN_AND_SPLUNK_TOKEN",
                "hec_token": "runtime-hec-value",
                "search_secret": "runtime-search-value",
                "indexes": ['main" | delete'],
            }
        )


def test_phase13_api_never_returns_submitted_secrets(monkeypatch, tmp_path):
    sys.path.insert(0, str(ROOT / "backend"))
    from app import main

    service = ReleaseCandidateConfiguration(str(tmp_path))
    monkeypatch.setattr(main, "release_candidate_configuration", service)
    with TestClient(main.app) as client:
        response = client.post(
            "/api/setup",
            json={
                "deployment_mode": "DOCKER_LAB",
                "splunk_deployment_type": "DOCKER_BUNDLED_ENTERPRISE",
                "hec_url": "https://127.0.0.1:8088/services/collector",
                "search_url": "https://127.0.0.1:8089/services/search/jobs/export",
                "auth_method": "HEC_TOKEN_AND_BASIC_SEARCH",
                "search_username": "operator",
                "hec_token": "submitted-only-at-runtime",
                "search_secret": "submitted-search-secret",
                "indexes": ["idx_network_ops"],
                "collectors": ["HEC"],
                "allow_insecure_tls": True,
            },
        )
        assert response.status_code == 200
        assert "submitted-" not in response.text
        source_response = client.get("/api/security-sources")
        assert source_response.status_code == 200
        assert source_response.json()["summary"]["source_count"] >= 29


def test_distribution_defaults_bind_administrative_ports_to_loopback():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    for port in ("8000", "8081", "8088", "8089", "514"):
        assert f'127.0.0.1:{port}:' in compose
    assert "SPLUNK_PASSWORD=${SPLUNK_PASSWORD:?" in compose
    assert "SPLUNK_HEC_TOKEN=${SPLUNK_HEC_TOKEN:?" in compose
    assert 'FAST_SIMULATION_HOST", "127.0.0.1"' in (
        ROOT / "backend" / "run.py"
    ).read_text(encoding="utf-8")


def test_splunk_app_defaults_do_not_provision_credentials_or_local_state():
    inputs = (ROOT / "netspout" / "default" / "inputs.conf").read_text(encoding="utf-8")
    assert "token =" not in inputs
    assert "[http://" not in inputs
    assert not (ROOT / "netspout" / "local").exists()


def test_built_package_layout_when_archive_exists():
    archive = ROOT / "netspout.spl"
    if not archive.exists():
        pytest.skip("Package is built by the release validation stage")
    with tarfile.open(archive, "r:gz") as package:
        names = package.getnames()
    assert "netspout/app.manifest" in names
    assert "netspout/default/app.conf" in names
    assert "netspout/default/data/ui/nav/default.xml" in names
    assert not any("/local/" in name for name in names)


def test_environment_example_contains_names_only():
    contents = (ROOT / ".env.example").read_text(encoding="utf-8")
    for line in contents.splitlines():
        if line.startswith(("SPLUNK_PASSWORD=", "SPLUNK_HEC_TOKEN=")):
            assert line.endswith("=")
